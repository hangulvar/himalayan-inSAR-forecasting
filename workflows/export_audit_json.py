#!/usr/bin/env python
"""
export_audit_json.py — convert the rich _atmospheric_audit.csv into the
minimal audit_log.json schema specified in the Phase 1.3 plan:

    [
      {
        "product": "<HyP3 product folder name>",
        "job_id":  "<HyP3 job UUID, or null if unmapped>",
        "r_squared": <float>,
        "is_atmospherically_contaminated": <bool, True iff r_squared > 0.5>
      },
      ...
    ]

Reads:
  data/qa_masks/_atmospheric_audit.csv
Writes:
  data/qa_masks/audit_log.json

Uses HyP3's job catalogue (matched by product zip filename) to attach the
canonical HyP3 job UUID. If HyP3 auth or the lookup fails, job_id is null
and the rest of the data is preserved.
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path

from config import load_config

# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_CSV = PROJECT_ROOT / "data" / "qa_masks" / "_atmospheric_audit.csv"
JSON_OUT = PROJECT_ROOT / "data" / "qa_masks" / "audit_log.json"

QUARANTINE_R2 = 0.5  # must match phase_elevation_audit.py

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("export_audit_json")


def build_product_to_jobid_map(job_name_prefix: str) -> dict[str, str]:
    """Map each HyP3 product zip stem (under the job-name prefix) to its job_id.

    Failures (no auth, no jobs) return an empty dict — the JSON will then
    have null job_ids but still be well-formed.
    """
    try:
        import hyp3_sdk as sdk
    except ImportError:
        logger.warning("hyp3_sdk not installed; job_ids will be null.")
        return {}

    try:
        hyp3 = sdk.HyP3()
        jobs = [
            j for j in hyp3.find_jobs()
            if j.name and j.name.startswith(job_name_prefix)
        ]
    except Exception as e:
        logger.warning(f"HyP3 auth/lookup failed: {e}. job_ids will be null.")
        return {}

    mapping: dict[str, str] = {}
    for job in jobs:
        if not job.files:
            continue
        fname = job.files[0].get("filename", "")
        if fname.endswith(".zip"):
            stem = fname[:-4]
            mapping[stem] = job.job_id
    logger.info(f"Built product→job_id map for {len(mapping)} HyP3 jobs.")
    return mapping


def main() -> int:
    if not AUDIT_CSV.exists():
        logger.error(f"Audit CSV not found: {AUDIT_CSV}")
        return 1

    rows = list(csv.DictReader(open(AUDIT_CSV, encoding="utf-8")))
    logger.info(f"Read {len(rows)} rows from {AUDIT_CSV.name}.")

    cfg = load_config()
    product_to_jobid = build_product_to_jobid_map(cfg.job_name_prefix)

    records: list[dict] = []
    for r in rows:
        if r.get("status") != "ok":
            # Carry these through with null R² so the JSON inventory matches
            # what's on disk; explicit `null` makes the failure visible.
            records.append({
                "product": r["product"],
                "job_id": product_to_jobid.get(r["product"]),
                "r_squared": None,
                "is_atmospherically_contaminated": False,
            })
            continue
        r2 = float(r["r_squared"])
        records.append({
            "product": r["product"],
            "job_id": product_to_jobid.get(r["product"]),
            "r_squared": r2,
            "is_atmospherically_contaminated": r2 > QUARANTINE_R2,
        })

    JSON_OUT.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    n_contaminated = sum(1 for r in records if r["is_atmospherically_contaminated"])
    n_with_jobid = sum(1 for r in records if r["job_id"])
    logger.info(
        f"Wrote {JSON_OUT.name}: {len(records)} records, "
        f"{n_contaminated} flagged contaminated, "
        f"{n_with_jobid} with HyP3 job_id."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

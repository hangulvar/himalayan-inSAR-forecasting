#!/usr/bin/env python
"""
apply_connectivity_rescues.py

Promote the auto-recommended set of CONCERN products to KEEP so that each
stack's SBAS network becomes solvable. The recommendations are produced by
sbas_network_graph.py (the minimum set of lowest-R2 bridging edges per island
gap) and written to data/qa_masks/_rescue_recommendations.json — this script no
longer hardcodes a Ramban-specific product list, so it works for any AOI.

Inputs : data/qa_masks/_quarantine_list.csv
         data/qa_masks/_rescue_recommendations.json
Outputs: data/qa_masks/_quarantine_list.csv  (rewritten in place)
         data/qa_masks/_rescued_for_connectivity.json (audit trail)

Idempotent: re-running has no effect if the products are already KEEP. Run
`python workflows/sbas_network_graph.py --recommend-only` first to (re)generate
the recommendations. A stack whose islands no CONCERN pair can bridge (e.g. the
period-split case) simply receives no recommendations and is left untouched.
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QA_DIR = PROJECT_ROOT / "data" / "qa_masks"
QUARANTINE_CSV = QA_DIR / "_quarantine_list.csv"
RESCUE_RECOMMENDATIONS = QA_DIR / "_rescue_recommendations.json"
RESCUE_AUDIT = QA_DIR / "_rescued_for_connectivity.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("apply_rescues")


def main() -> int:
    if not QUARANTINE_CSV.exists():
        logger.error(f"Missing {QUARANTINE_CSV}")
        return 1
    if not RESCUE_RECOMMENDATIONS.exists():
        logger.error(
            f"Missing {RESCUE_RECOMMENDATIONS}. Run "
            "`python workflows/sbas_network_graph.py --recommend-only` first."
        )
        return 1

    payload = json.loads(RESCUE_RECOMMENDATIONS.read_text(encoding="utf-8"))
    # Payload is {gate, rescues, stacks}; tolerate a bare list for back-compat.
    rescue_list = payload["rescues"] if isinstance(payload, dict) else payload
    rows = list(csv.DictReader(QUARANTINE_CSV.open(encoding="utf-8")))
    by_product = {r["product"]: r for r in rows}

    promoted, already_keep, not_found = [], [], []
    for entry in rescue_list:
        p = entry["product"]
        if p not in by_product:
            not_found.append(p)
            continue
        current = by_product[p]["decision"]
        if current == "KEEP":
            already_keep.append(p)
            continue
        by_product[p]["decision"] = "KEEP"
        r2 = entry.get("atmos_r2")
        r2_str = f"{r2:.4f}" if isinstance(r2, (int, float)) else "n/a"
        rescue_note = (
            f"RESCUED_FOR_CONNECTIVITY (was {current}, atmos R2={r2_str}, "
            f"bridges: {entry.get('bridges', '')})"
        )
        existing_reasons = by_product[p].get("reasons", "")
        by_product[p]["reasons"] = (
            f"{existing_reasons}; {rescue_note}" if existing_reasons else rescue_note
        )
        promoted.append(p)

    if not_found:
        logger.warning(f"{len(not_found)} rescue targets not in quarantine CSV: {not_found}")

    # Write back the (possibly updated) CSV.
    fieldnames = list(rows[0].keys())
    with QUARANTINE_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    logger.info(f"Updated {QUARANTINE_CSV.name}")

    # Audit trail.
    audit = {
        "rescued": [
            {
                "product": e["product"],
                "stack": e.get("stack"),
                "bridges": e.get("bridges"),
                "atmos_r2": e.get("atmos_r2"),
            }
            for e in rescue_list if e["product"] in by_product
        ],
        "promoted_count": len(promoted),
        "already_keep_count": len(already_keep),
        "not_found_count": len(not_found),
    }
    RESCUE_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    # Summary.
    print(f"Promoted: {len(promoted)}")
    for p in promoted:
        print(f"  + {p}")
    if already_keep:
        print(f"Already KEEP (skipped): {len(already_keep)}")
    if not_found:
        print(f"NOT FOUND in CSV: {len(not_found)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

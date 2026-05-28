#!/usr/bin/env python
"""
apply_connectivity_rescues.py

Promote a hardcoded set of CONCERN products to KEEP so that the SBAS network
becomes solvable. The list was selected by sbas_network_graph.py to be the
minimum set of bridging edges with the lowest atmospheric R² in each case.

Inputs : data/qa_masks/_quarantine_list.csv
Outputs: data/qa_masks/_quarantine_list.csv  (rewritten in place)
         data/qa_masks/_rescued_for_connectivity.json (audit trail)

Idempotent: re-running has no effect if the products are already KEEP.
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUARANTINE_CSV = PROJECT_ROOT / "data" / "qa_masks" / "_quarantine_list.csv"
RESCUE_AUDIT = PROJECT_ROOT / "data" / "qa_masks" / "_rescued_for_connectivity.json"

# Minimum-set rescue list. Each entry is the product folder name (HyP3 zip
# stem, without `.zip`) and the connectivity reason. Atmospheric R² noted
# for traceability; all are <0.5 so reclassified as CLEAN-enough-for-SBAS.
RESCUE_LIST: list[dict] = [
    # ASC_path100_frame102 — bridge Jun 16↔Jun 28 (Island 1↔2)
    {
        "product": "S1AA_20250604T130445_20250628T130444_VVP024_INT80_G_weF_5BA7",
        "stack": "ASC_path100_frame102",
        "bridges": "Island 1 (May–Jun 16) ↔ Island 2 (Jun 28–Aug 3)",
        "atmos_r2": 0.4565,
    },
    # ASC_path100_frame102 — bridge Aug 3↔Aug 15 (Island 2↔3)
    {
        "product": "S1AA_20250803T130443_20250827T130443_VVP024_INT80_G_weF_7725",
        "stack": "ASC_path100_frame102",
        "bridges": "Island 2 (Jun 28–Aug 3) ↔ Island 3 (Aug 15–Oct 26)",
        "atmos_r2": 0.3499,
    },
    # ASC_path27_frame101 — bridge Sep 15↔Sep 27
    {
        "product": "S1AA_20250822T125628_20250927T125629_VVP036_INT80_G_weF_81DD",
        "stack": "ASC_path27_frame101",
        "bridges": "Island 1 (May 6–Sep 15) ↔ Island 2 (Sep 27–Oct 21)",
        "atmos_r2": 0.3532,
    },
    # ASC_path27_frame106 — connect isolated May 6 acquisition
    {
        "product": "S1AA_20250506T125657_20250530T125656_VVP024_INT80_G_weF_5DC6",
        "stack": "ASC_path27_frame106",
        "bridges": "Isolated May 6 ↔ Island 2 (May 18–Oct 21)",
        "atmos_r2": 0.3821,
    },
    # DESC_path34_frame479 — three bridges (Aug 23↔Sep 28, Sep 28↔Oct 10, Sep 28↔Oct 22)
    {
        "product": "S1AA_20250823T005908_20250928T005909_VVP036_INT80_G_weF_58A7",
        "stack": "DESC_path34_frame479",
        "bridges": "Island 2 (Jun 24–Sep 16) ↔ Island 3 (Sep 28)",
        "atmos_r2": 0.4622,
    },
    {
        "product": "S1AA_20250928T005909_20251010T005909_VVP012_INT80_G_weF_CDAC",
        "stack": "DESC_path34_frame479",
        "bridges": "Island 3 (Sep 28) ↔ Island 4 (Oct 10–22)",
        "atmos_r2": 0.3395,
    },
    {
        "product": "S1AA_20250928T005909_20251022T005909_VVP024_INT80_G_weF_CEC0",
        "stack": "DESC_path34_frame479",
        "bridges": "Island 3 (Sep 28) ↔ Island 4 (Oct 10–22) [redundant w/ CDAC]",
        "atmos_r2": 0.4569,
    },
]

# Frame 484 deliberately gets NO rescues. Per Session 2 decision the stack
# will be split into pre-monsoon / post-monsoon time series rather than
# attempting a continuous inversion.

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("apply_rescues")


def main() -> int:
    if not QUARANTINE_CSV.exists():
        logger.error(f"Missing {QUARANTINE_CSV}")
        return 1

    rows = list(csv.DictReader(QUARANTINE_CSV.open(encoding="utf-8")))
    by_product = {r["product"]: r for r in rows}

    promoted, already_keep, not_found = [], [], []
    for entry in RESCUE_LIST:
        p = entry["product"]
        if p not in by_product:
            not_found.append(p)
            continue
        current = by_product[p]["decision"]
        if current == "KEEP":
            already_keep.append(p)
            continue
        by_product[p]["decision"] = "KEEP"
        existing_reasons = by_product[p].get("reasons", "")
        rescue_note = (
            f"RESCUED_FOR_CONNECTIVITY (was {current}, atmos R²="
            f"{entry['atmos_r2']:.4f}, bridges: {entry['bridges']})"
        )
        by_product[p]["reasons"] = (
            f"{existing_reasons}; {rescue_note}" if existing_reasons
            else rescue_note
        )
        promoted.append(p)

    if not_found:
        logger.warning(f"{len(not_found)} rescue targets not in quarantine CSV: {not_found}")

    # Write back
    fieldnames = list(rows[0].keys())
    with QUARANTINE_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    logger.info(f"Updated {QUARANTINE_CSV.name}")

    # Audit JSON
    audit = {
        "rescued": [
            {
                "product": e["product"],
                "stack": e["stack"],
                "bridges": e["bridges"],
                "atmos_r2_before_rescue": e["atmos_r2"],
            }
            for e in RESCUE_LIST if e["product"] in by_product
        ],
        "promoted_count": len(promoted),
        "already_keep_count": len(already_keep),
        "not_found_count": len(not_found),
    }
    RESCUE_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    # Summary
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

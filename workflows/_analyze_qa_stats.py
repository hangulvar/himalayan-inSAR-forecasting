"""One-shot analysis of data/qa_masks/_coherence_mask_stats.csv.

Computes per-stack survivor / coherence stats and flags borderline pairs.
Run from project root with the insar_qa_env conda env active.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

from stacks import load_manifest, stack_for_product

CSV_PATH = Path("data/qa_masks/_coherence_mask_stats.csv")


def main() -> None:
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    manifest = load_manifest()
    by_stack: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["status"] != "ok":
            continue
        by_stack[stack_for_product(r["product"], manifest)].append(r)

    print(f"{'Stack':<24}  {'n':>3}  {'survivor % (min/med/max)':<26}  {'coh of survivors (min/med/max)'}")
    print("-" * 100)
    for stack, items in sorted(by_stack.items()):
        surv = np.array([float(r["surviving_pct"]) for r in items])
        coh = np.array([float(r["mean_coherence_survivors"]) for r in items])
        print(
            f"{stack:<24}  {len(items):>3}  "
            f"{surv.min():>5.1f} / {np.median(surv):>5.1f} / {surv.max():>5.1f}  "
            f"     {coh.min():.3f} / {np.median(coh):.3f} / {coh.max():.3f}"
        )

    # Worst 5 pairs
    print("\nWorst 5 pairs by survivor %:")
    worst = sorted(
        [r for r in rows if r["status"] == "ok"],
        key=lambda r: float(r["surviving_pct"]),
    )[:5]
    for r in worst:
        print(
            f"  {r['product'][:60]:<60}  "
            f"surv={float(r['surviving_pct']):>5.1f}%  "
            f"coh_surv={float(r['mean_coherence_survivors']):.3f}"
        )

    # Borderline: mean coherence of survivors < 0.6
    print("\nPairs where surviving pixels have mean coh < 0.6 (borderline):")
    borderline = [
        r
        for r in rows
        if r["status"] == "ok" and float(r["mean_coherence_survivors"]) < 0.6
    ]
    if not borderline:
        print("  (none)")
    for r in borderline:
        print(
            f"  {r['product'][:60]:<60}  "
            f"coh_surv={float(r['mean_coherence_survivors']):.3f}  "
            f"surv_pct={float(r['surviving_pct']):.1f}%"
        )

    # 24-day baseline pairs (VVP024 — the ones bridging the S1A acquisition gap)
    v24 = [r for r in rows if "VVP024" in r["product"]]
    print(f"\n24-day-baseline pairs (VVP024): {len(v24)}")
    for r in v24:
        print(
            f"  {r['product'][:60]:<60}  "
            f"surv={float(r['surviving_pct']):>5.1f}%  "
            f"coh_surv={float(r['mean_coherence_survivors']):.3f}"
        )

    # Temporal pattern: do later-monsoon pairs show worse coherence?
    print("\nMonthly average (by reference-acquisition month):")
    by_month: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if r["status"] != "ok":
            continue
        m = re.search(r"S1[A-D][A-D]_(\d{4})(\d{2})\d{2}T", r["product"])  # cross-unit S1AD (§61)
        if m:
            by_month[f"{m.group(1)}-{m.group(2)}"].append(float(r["surviving_pct"]))
    for month, vals in sorted(by_month.items()):
        v = np.array(vals)
        print(
            f"  {month}  n={len(v):>2}  "
            f"mean_surv={v.mean():>5.1f}%  median={np.median(v):>5.1f}%"
        )


if __name__ == "__main__":
    main()

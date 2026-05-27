"""One-shot consolidation: combine the coherence + atmospheric audits into
a single quarantine recommendation and per-stack health view.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

COH_CSV = Path("data/qa_masks/_coherence_mask_stats.csv")
ATMOS_CSV = Path("data/qa_masks/_atmospheric_audit.csv")
OUT_CSV = Path("data/qa_masks/_quarantine_list.csv")


def stack_key(name: str) -> str:
    m = re.search(r"S1AA_\d{8}T(\d{6})_", name)
    if not m:
        return "unknown"
    hms = m.group(1)
    if hms.startswith("1304"):
        return "ASC_path100_frame102"
    if hms.startswith("1256"):
        s = int(hms[4:6])
        return "ASC_path27_frame101" if s < 50 else "ASC_path27_frame106"
    if hms.startswith("0059"):
        s = int(hms[4:6])
        return "DESC_path34_frame479" if s < 25 else "DESC_path34_frame484"
    return "unknown"


def main() -> None:
    coh = {r["product"]: r for r in csv.DictReader(open(COH_CSV, encoding="utf-8"))}
    atm = {r["product"]: r for r in csv.DictReader(open(ATMOS_CSV, encoding="utf-8"))}

    products = sorted(set(coh) | set(atm))

    # Build joined view + categorize.
    rows = []
    for p in products:
        c = coh.get(p, {})
        a = atm.get(p, {})
        coh_status = c.get("status", "missing")
        atm_class = a.get("classification", "missing")

        # Reasons:
        reasons = []
        if coh_status != "ok":
            reasons.append(f"coh_status={coh_status}")
        else:
            cs = float(c.get("mean_coherence_survivors", 0) or 0)
            sp = float(c.get("surviving_pct", 0) or 0)
            if cs < 0.6:
                reasons.append(f"low_coh_surv={cs:.3f}")
            if sp < 30:
                reasons.append(f"low_surv_pct={sp:.1f}")
        if atm_class == "QUARANTINE":
            reasons.append(f"atmos_R2={a.get('r_squared')}")
        elif atm_class == "CONCERN":
            reasons.append(f"atmos_concern_R2={a.get('r_squared')}")

        # Final decision:
        if atm_class == "QUARANTINE" or (
            coh_status == "ok"
            and float(c.get("mean_coherence_survivors", 0) or 0) < 0.6
        ):
            decision = "QUARANTINE"
        elif atm_class == "CONCERN":
            decision = "CONCERN"
        else:
            decision = "KEEP"

        rows.append({
            "product": p,
            "stack": stack_key(p),
            "decision": decision,
            "surviving_pct": c.get("surviving_pct", ""),
            "mean_coh_survivors": c.get("mean_coherence_survivors", ""),
            "atmos_r_squared": a.get("r_squared", ""),
            "atmos_class": atm_class,
            "reasons": "; ".join(reasons) if reasons else "",
        })

    # Write
    fieldnames = list(rows[0].keys())
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote: {OUT_CSV}")

    # Overall counts
    from collections import Counter
    decisions = Counter(r["decision"] for r in rows)
    print(f"\nTotal products: {len(rows)}")
    for d, n in decisions.most_common():
        print(f"  {d:<12s}: {n}")

    # Per-stack survivor counts
    print("\nPer-stack quarantine breakdown:")
    print(f"  {'Stack':<22} {'n_total':>7} {'n_keep':>7} {'n_concern':>10} {'n_quarantine':>13}")
    by_stack = defaultdict(list)
    for r in rows:
        by_stack[r["stack"]].append(r)
    for stack, items in sorted(by_stack.items()):
        n = len(items)
        k = sum(1 for x in items if x["decision"] == "KEEP")
        c = sum(1 for x in items if x["decision"] == "CONCERN")
        q = sum(1 for x in items if x["decision"] == "QUARANTINE")
        print(f"  {stack:<22} {n:>7} {k:>7} {c:>10} {q:>13}")

    # Full quarantine list with reasons
    print("\n=== FINAL QUARANTINE LIST ===")
    qs = [r for r in rows if r["decision"] == "QUARANTINE"]
    for r in sorted(qs, key=lambda x: x["stack"]):
        print(
            f"  [{r['stack']}] {r['product']}\n"
            f"     reasons: {r['reasons']}"
        )

    # Concerns
    print("\n=== CONCERN LIST (atmospheric R^2 in 0.3-0.5) ===")
    cs = [r for r in rows if r["decision"] == "CONCERN"]
    for r in sorted(cs, key=lambda x: x["stack"]):
        print(
            f"  [{r['stack']}] {r['product']}\n"
            f"     reasons: {r['reasons']}"
        )

    # Health per stack after quarantine — how many KEEP pairs each stack has
    print("\n=== POST-QUARANTINE STACK HEALTH ===")
    for stack, items in sorted(by_stack.items()):
        keeps = [x for x in items if x["decision"] == "KEEP"]
        concerns = [x for x in items if x["decision"] == "CONCERN"]
        print(
            f"  {stack:<22}  KEEP={len(keeps):>2}  +CONCERN={len(concerns):>2}  "
            f"(time-series will lose {len(items) - len(keeps)} of {len(items)} pairs)"
        )


if __name__ == "__main__":
    main()

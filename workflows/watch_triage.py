#!/usr/bin/env python
"""watch_triage.py — RANK (don't gate) the broad WATCH footprint (RESULTS_AND_KPIS.md §25).

The WATCH tier (§23, m=0.70, 132 zones) is a high-RECALL safety net — its job is to *not miss*
anything. So gating it down by daily wetness (the per-zone gate we use on the validated operational
footprint, §19) would shrink the very breadth that makes WATCH useful, and would apply that gate
outside the validated map where its "can't balloon" safety property no longer holds. So instead we
KEEP every WATCH zone and RANK them, worst-first, by a triage priority that fuses the two per-zone
trust axes we already have:

    priority = (1 - m*)  ×  P
               \fragility/   \confidence/

  - m*  = critical saturation (§19): the wetness at which the slope fails.  (1 - m*) = fragility.
  - P   = detection confidence (§24): P(the creep is real, not noise), combined across looks.

A slope ranks high only if it is BOTH fragile AND confidently moving — the right "AND" for triage
(a fragile-but-probably-noise slope, or a confidently-moving-but-sturdy one, both rank lower).
Nothing is dropped; the operator just reads the top of a 132-long list. Multi-look zones get a
confidence boost (P = 1 - prod(1 - p)), so corroborated places rise — desirable for triage.

  docker compose run --rm insar python workflows/watch_triage.py
  docker compose run --rm insar python workflows/watch_triage.py --footprint monsoon
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402

from config import load_config                                  # noqa: E402
from per_zone_gate import critical_saturation, tier_of          # m* + vulnerability tier (§19)
from velocity_uncertainty import stack_noise, confidence        # noise floor + P (§24)
from run_multistack import MERGE_DEG                            # union-merge distance
from stacks import product_stacks                               # standing-product stacks

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SFX = load_config().data_suffix   # '' for ramban; '_<slug>' so AOIs coexist
HAZ_DIR = PROJECT_ROOT / "data" / f"hazard{_SFX}"
ALERTS_DIR = PROJECT_ROOT / "data" / f"alerts{_SFX}"
MOSAIC_ALERTS_DIR = ALERTS_DIR / "mosaic_asc"


def collect(stacks: list[str], scenario: str) -> list[dict]:
    """Per-stack zones tagged with m* (vulnerability, §19) and per-look confidence p (§24)."""
    rows: list[dict] = []
    for s in stacks:
        af = ALERTS_DIR / s / f"alerts_{scenario}.json"
        fd = HAZ_DIR / f"{s}_FS_dry.tif"
        fsat = HAZ_DIR / f"{s}_FS_saturated.tif"
        if not (af.exists() and fd.exists() and fsat.exists()):
            continue
        sigma = stack_noise(s)
        with rasterio.open(fd) as d:
            fs_dry = d.read(1)
        with rasterio.open(fsat) as d:
            fs_sat = d.read(1)
        for a in json.loads(af.read_text(encoding="utf-8")).get("alerts", []):
            r, c = a["pixel_rowcol"]
            if not (0 <= r < fs_dry.shape[0] and 0 <= c < fs_dry.shape[1]):
                continue
            mstar = critical_saturation(float(fs_dry[r, c]), float(fs_sat[r, c]))
            creep = a.get("mean_velocity_mmyr")
            if mstar is None or creep is None or not sigma:
                continue
            lon, lat = a["centroid_lonlat"]
            rows.append({"stack": s, "lon": round(lon, 5), "lat": round(lat, 5),
                         "severity": a["severity"], "creep_mmyr": creep,
                         "m_star": round(mstar, 3),
                         "p_look": round(confidence(float(creep), sigma), 3)})
    return rows


def merge_rank(rows: list[dict], merge_deg: float) -> list[dict]:
    """Merge per-stack rows at one place (different looks) into union zones — most-vulnerable
    m* (min), combined confidence P = 1 - prod(1 - p) — then rank by priority = (1 - m*)*P."""
    used = [False] * len(rows)
    out: list[dict] = []
    for i, z in enumerate(rows):
        if used[i]:
            continue
        grp = [z]
        used[i] = True
        for j in range(i + 1, len(rows)):
            if used[j]:
                continue
            if (abs(rows[j]["lat"] - z["lat"]) < merge_deg
                    and abs(rows[j]["lon"] - z["lon"]) < merge_deg):
                grp.append(rows[j])
                used[j] = True
        mstar = min(g["m_star"] for g in grp)
        P = 1.0 - float(np.prod([1.0 - g["p_look"] for g in grp]))
        looks = sorted({g["stack"] for g in grp})
        out.append({
            "lon": round(sum(g["lon"] for g in grp) / len(grp), 5),
            "lat": round(sum(g["lat"] for g in grp) / len(grp), 5),
            "severity": "CRITICAL" if any(g["severity"] == "CRITICAL" for g in grp) else "HIGH",
            "n_looks": len(looks),
            "strongest_creep_mmyr": round(min(g["creep_mmyr"] for g in grp), 1),
            "m_star": round(mstar, 3), "vulnerability_tier": tier_of(mstar),
            "detection_confidence": round(P, 3),
            "priority": round((1.0 - mstar) * P, 3),
        })
    out.sort(key=lambda z: z["priority"], reverse=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--footprint", default="watch",
                    help="Scenario footprint to rank (default: watch — the recall tier).")
    ap.add_argument("--stacks", nargs="*", default=None)
    ap.add_argument("--top", type=int, default=15, help="Rows to show in the .md report.")
    args = ap.parse_args()

    stacks = args.stacks or product_stacks(args.footprint)
    rows = collect(stacks, args.footprint)
    if not rows:
        raise SystemExit(f"No '{args.footprint}' zones found — run run_multistack.py first.")
    ranked = merge_rank(rows, MERGE_DEG)

    pri = np.array([z["priority"] for z in ranked])
    from collections import Counter
    tier_counts = Counter(z["vulnerability_tier"] for z in ranked)
    report = {
        "footprint": args.footprint, "method": "RANK not GATE — keep all zones, sort by "
        "priority=(1-m*)*P (fragility x detection confidence)", "stacks": stacks,
        "n_zones": len(ranked), "n_multi_look": int(sum(z["n_looks"] >= 2 for z in ranked)),
        "priority_max": round(float(pri.max()), 3), "priority_median": round(float(np.median(pri)), 3),
        "priority_min": round(float(pri.min()), 3),
        "vulnerability_tiers": dict(tier_counts),
        "top": ranked[:args.top],
    }
    MOSAIC_ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    base = MOSAIC_ALERTS_DIR / f"per_zone_triage_{args.footprint}"
    base.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_csv(base.with_suffix(".csv"), ranked)
    write_md(base.with_suffix(".md"), report, ranked, args.top)
    make_figure(base.with_suffix(".png"), ranked, args.footprint)

    print(f"footprint '{args.footprint}': {len(ranked)} zones RANKED (not gated) "
          f"by priority=(1-m*)*P  [{report['n_multi_look']} multi-look]")
    print(f"priority: max={pri.max():.3f} median={np.median(pri):.3f} min={pri.min():.3f}")
    print(f"vulnerability tiers: {dict(tier_counts)}")
    print(f"  top-{min(args.top, 5)} (worst-first):")
    for i, z in enumerate(ranked[:5], 1):
        print(f"    {i}. [{z['lon']}, {z['lat']}]  priority={z['priority']:.3f}  "
              f"(m*={z['m_star']}, P={z['detection_confidence']}, looks={z['n_looks']}, "
              f"creep={z['strongest_creep_mmyr']})")
    print(f"  -> {base.with_suffix('.json')} , .csv , .md , .png")
    return 0


def write_csv(path: Path, ranked: list[dict]) -> None:
    cols = ["lon", "lat", "severity", "n_looks", "strongest_creep_mmyr", "m_star",
            "vulnerability_tier", "detection_confidence", "priority"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for rank, z in enumerate(ranked, 1):
            w.writerow({k: z[k] for k in cols})


def write_md(path: Path, r: dict, ranked: list[dict], top: int) -> None:
    lines = [
        f"# WATCH triage — ranked (not gated): the {r['footprint']} footprint worst-first (§25)", "",
        "The WATCH tier is a high-recall safety net, so we **keep every zone** and **rank** them instead "
        "of gating them down (gating would shrink the breadth that is the whole point — see §25). Priority "
        "fuses the two per-zone trust axes:", "",
        "**priority = (1 − m\\*) × P**  —  fragility (§19) × detection confidence (§24).", "",
        f"- **{r['n_zones']} zones ranked** ({r['n_multi_look']} multi-look). Priority: max "
        f"**{r['priority_max']}** / median **{r['priority_median']}** / min **{r['priority_min']}**.",
        f"- vulnerability tiers: " + ", ".join(f"**{k}** {v}" for k, v in r["vulnerability_tiers"].items())
        + ".",
        "",
        f"## Top-{top} priority zones (read these first)", "",
        "| rank | lon, lat | looks | creep mm/yr | m* (fragility) | confidence P | **priority** | tier |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, z in enumerate(ranked[:top], 1):
        lines.append(f"| {i} | {z['lon']:.4f}, {z['lat']:.4f} | {z['n_looks']} | "
                     f"{z['strongest_creep_mmyr']} | {z['m_star']} | {z['detection_confidence']} | "
                     f"**{z['priority']}** | {z['vulnerability_tier']} |")
    lines += ["",
              "_Honest scope: ranking keeps all zones (no gating), so the recall safety-net is preserved; "
              "the operator simply starts at the top. Priority multiplies the two axes, so a zone needs to "
              "be BOTH fragile (low m*) AND confidently moving (high P) to rank high — a fragile-but-noisy "
              "or a confident-but-sturdy zone ranks lower. Multi-look corroboration lifts P, so two-look "
              "places rise. m* and P are the §19/§24 quantities; this script only fuses + sorts them._"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figure(path: Path, ranked: list[dict], scenario: str) -> None:
    frag = np.array([1.0 - z["m_star"] for z in ranked])
    conf = np.array([z["detection_confidence"] for z in ranked])
    pri = np.array([z["priority"] for z in ranked])
    looks = np.array([z["n_looks"] for z in ranked])
    fig, ax = plt.subplots(figsize=(8.5, 7))
    sc = ax.scatter(frag, conf, c=pri, s=30 + 60 * (looks >= 2), cmap="YlOrRd",
                    edgecolor="#333", lw=0.3, vmin=0, vmax=max(pri.max(), 0.1))
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("triage priority = (1 − m*) × P")
    # Annotate the top-5 with their rank.
    for i, z in enumerate(ranked[:5], 1):
        ax.annotate(str(i), (1.0 - z["m_star"], z["detection_confidence"]),
                    fontsize=9, fontweight="bold", ha="center", va="center", color="#111")
    ax.set_xlabel("fragility  (1 − m*)  — higher = fails when barely wet")
    ax.set_ylabel("detection confidence  P  — higher = creep is real, not noise")
    ax.set_title(f"WATCH triage space ({scenario}): top-right = act first\n"
                 f"all {len(ranked)} zones kept (ranked, not gated); larger = ≥2-look")
    ax.grid(alpha=0.3)
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
"""velocity_uncertainty.py — propagate the InSAR velocity NOISE FLOOR into a per-zone
DETECTION CONFIDENCE for the alert footprint (RESULTS_AND_KPIS.md §24).

Why: the creep test is v < -15 mm/yr, but the velocity carries a ~30 mm/yr atmosphere-
dominated noise floor (RESULTS §2). So a zone creeping at -18 is far less certain to be REAL
than one at -40. We turn that gap into a probability:

  per-look confidence   p = Phi( (CREEP_THR - v_zone) / sigma_v )   # P(true mean creep < -15)
  combined (multi-look) P = 1 - prod_looks (1 - p)                  # independent corroboration

sigma_v is each stack's robust noise floor (1.4826 * MAD of the high-passed velocity, resistant to
the creeping minority). The zone MEAN inherits ~the pixel noise because the residual (post-high-pass)
atmosphere stays correlated across a sub-km zone (no sqrt-N averaging) — so this is a conservative
floor. A zone seen by two looks at p=0.70 each is 1 - 0.3*0.3 = 0.91 confident: this QUANTIFIES the
project's '>=2-look core is the trustworthy subset' rule (§16c).

Validation arm: writes confidence-filtered copies of the union footprint
(data/alerts/mosaic_asc/alerts_<scenario>_conf{NN}.json) that backtest_inventory.py scores as-is,
to test whether keeping only high-confidence zones lifts the AUC.

  docker compose run --rm insar python workflows/velocity_uncertainty.py
  docker compose run --rm insar python workflows/velocity_uncertainty.py --footprint watch
"""

from __future__ import annotations

import argparse
import csv
import json
from math import erf, sqrt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402

from config import load_config  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SFX = load_config().data_suffix   # '' for ramban; '_<slug>' so AOIs coexist
VEL_DIR = PROJECT_ROOT / "data" / f"velocity{_SFX}"
ALERTS_DIR = PROJECT_ROOT / "data" / f"alerts{_SFX}"
MOSAIC_ALERTS_DIR = ALERTS_DIR / "mosaic_asc"

CREEP_THR = -15.0                                  # mm/yr; Phase-4 creep test (neg = downslope)
CONF_TIERS = [(0.9, "high"), (0.7, "moderate"), (0.0, "low")]
FILTER_TAUS = [0.7, 0.9]                            # confidence cuts written for the validation arm


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def stack_noise(stack: str) -> float | None:
    """Per-stack velocity noise floor sigma_v = 1.4826*MAD of the high-passed velocity
    (robust to the creeping-pixel minority). None if the raster is missing/too small."""
    p = VEL_DIR / f"{stack}_mean_velocity_los_highpass.tif"
    if not p.exists():
        return None
    with rasterio.open(p) as r:
        v = r.read(1).astype("float64")
    v = v[np.isfinite(v)]
    if v.size < 100:
        return None
    mad = float(np.median(np.abs(v - np.median(v))))
    return 1.4826 * mad


def confidence(v_zone: float, sigma_v: float) -> float:
    """P(true mean creep < CREEP_THR | measured v_zone, sigma_v)."""
    return normal_cdf((CREEP_THR - v_zone) / sigma_v)


def tier_of(p: float) -> str:
    for cut, name in CONF_TIERS:
        if p >= cut:
            return name
    return CONF_TIERS[-1][1]


def collect_stack_zones(stacks: list[str], scenario: str, sigma: dict) -> list[dict]:
    """Per-stack alert zones tagged with their per-look detection confidence."""
    zones: list[dict] = []
    for s in stacks:
        af = ALERTS_DIR / s / f"alerts_{scenario}.json"
        if not af.exists() or sigma.get(s) is None:
            continue
        for a in json.loads(af.read_text(encoding="utf-8")).get("alerts", []):
            v = a.get("mean_velocity_mmyr")
            if v is None:
                continue
            lon, lat = a["centroid_lonlat"]
            zones.append({
                "stack": s, "lon": round(lon, 5), "lat": round(lat, 5),
                "severity": a["severity"], "creep_mmyr": v, "n_pixels": a.get("n_pixels"),
                "mean_fs": a.get("mean_fs"), "sigma_v": round(sigma[s], 1),
                "p_look": round(confidence(float(v), sigma[s]), 3),
            })
    return zones


def group_union(stack_zones: list[dict], merge_deg: float) -> list[dict]:
    """Merge per-stack zones at the same place (different looks) and combine their confidence
    by independent corroboration: P = 1 - prod(1 - p_look). Sorted most-confident first."""
    used = [False] * len(stack_zones)
    union: list[dict] = []
    for i, z in enumerate(stack_zones):
        if used[i]:
            continue
        group = [z]
        used[i] = True
        for j in range(i + 1, len(stack_zones)):
            if used[j]:
                continue
            if (abs(stack_zones[j]["lat"] - z["lat"]) < merge_deg
                    and abs(stack_zones[j]["lon"] - z["lon"]) < merge_deg):
                group.append(stack_zones[j])
                used[j] = True
        ps = [g["p_look"] for g in group]
        comb = 1.0 - float(np.prod([1.0 - p for p in ps]))
        lons = [g["lon"] for g in group]
        lats = [g["lat"] for g in group]
        union.append({
            "centroid_lonlat": [round(sum(lons) / len(lons), 5), round(sum(lats) / len(lats), 5)],
            "severity": "CRITICAL" if any(g["severity"] == "CRITICAL" for g in group) else "HIGH",
            "n_looks": len({g["stack"] for g in group}),
            "detected_by_looks": sorted({g["stack"] for g in group}),
            "strongest_creep_mmyr": round(min(g["creep_mmyr"] for g in group), 1),
            "per_look_confidence": [round(p, 3) for p in ps],
            "detection_confidence": round(comb, 3),
            "confidence_tier": tier_of(comb),
        })
    union.sort(key=lambda z: z["detection_confidence"], reverse=True)
    return union


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--footprint", default="operational",
                    help="Scenario whose union footprint to score (operational/watch/monsoon).")
    ap.add_argument("--stacks", nargs="*", default=None)
    args = ap.parse_args()

    import run_multistack
    stacks = args.stacks or run_multistack.connected_stacks()
    sigma = {s: stack_noise(s) for s in stacks}
    if all(v is None for v in sigma.values()):
        raise SystemExit("No high-passed velocity rasters found — run Phase 2 first.")

    stack_zones = collect_stack_zones(stacks, args.footprint, sigma)
    if not stack_zones:
        raise SystemExit(f"No '{args.footprint}' alert zones found — run run_multistack.py first.")
    union = group_union(stack_zones, run_multistack.MERGE_DEG)
    conf = np.array([z["detection_confidence"] for z in union])

    # Validation arm: write the confidence-annotated union + filtered subsets (scoreable as-is).
    MOSAIC_ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    written = {}
    for tau in [0.0] + FILTER_TAUS:
        kept = [z for z in union if z["detection_confidence"] >= tau]
        name = (f"alerts_{args.footprint}_conf.json" if tau == 0.0
                else f"alerts_{args.footprint}_conf{int(tau * 100)}.json")
        (MOSAIC_ALERTS_DIR / name).write_text(
            json.dumps({"scenario": f"{args.footprint}_conf>={tau}",
                        "method": "velocity-noise-floor detection confidence (§24)",
                        "n_zones": len(kept), "zones": kept}, indent=2), encoding="utf-8")
        written[tau] = (name, len(kept))

    n_high = int((conf >= 0.9).sum())
    n_mod = int(((conf >= 0.7) & (conf < 0.9)).sum())
    report = {
        "footprint": args.footprint, "stacks": stacks,
        "sigma_v_mmyr": {s: (round(v, 1) if v is not None else None) for s, v in sigma.items()},
        "creep_threshold_mmyr": CREEP_THR, "n_union_zones": len(union),
        "n_multi_look": int(sum(z["n_looks"] >= 2 for z in union)),
        "confidence_min": round(float(conf.min()), 3),
        "confidence_median": round(float(np.median(conf)), 3),
        "confidence_max": round(float(conf.max()), 3),
        "n_high_ge_0p9": n_high, "n_moderate_0p7_0p9": n_mod,
        "filtered_files": {str(k): {"file": v[0], "n_zones": v[1]} for k, v in written.items()},
        "top10_most_confident": union[:10],
    }
    (MOSAIC_ALERTS_DIR / f"velocity_confidence_{args.footprint}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    write_csv(MOSAIC_ALERTS_DIR / f"velocity_confidence_{args.footprint}.csv", union)
    write_md(MOSAIC_ALERTS_DIR / f"velocity_confidence_{args.footprint}.md", report, union)
    make_figure(MOSAIC_ALERTS_DIR / f"velocity_confidence_{args.footprint}.png", union, sigma)

    print(f"footprint '{args.footprint}': {len(union)} union zones "
          f"({report['n_multi_look']} multi-look)")
    print("sigma_v (noise floor, mm/yr): " +
          ", ".join(f"{s.replace('ASC_', '')}={sigma[s]:.1f}" for s in stacks if sigma[s]))
    print(f"detection confidence: min={conf.min():.3f} median={np.median(conf):.3f} "
          f"max={conf.max():.3f}  ->  HIGH(>=0.9)={n_high}, MODERATE(0.7-0.9)={n_mod}")
    for tau in [0.0] + FILTER_TAUS:
        name, n = written[tau]
        print(f"  conf >= {tau:.2f}: {n:3d} zones -> {name}")
    print("  top-3 most confident:")
    for z in union[:3]:
        print(f"    {z['centroid_lonlat']}  P={z['detection_confidence']:.3f}  "
              f"looks={z['n_looks']} ({[round(p, 2) for p in z['per_look_confidence']]})  "
              f"creep={z['strongest_creep_mmyr']}")
    print(f"  -> {MOSAIC_ALERTS_DIR / f'velocity_confidence_{args.footprint}.json'} , .csv , .md , .png")
    print(f"  validation: score a filtered file, e.g. "
          f"`backtest_inventory.py --alerts data/alerts/mosaic_asc/{written[0.9][0]} "
          f"--inventory data/inventory/gsi_inventory_aoi.geojson`")
    return 0


def write_csv(path: Path, union: list[dict]) -> None:
    cols = ["centroid_lonlat", "severity", "n_looks", "strongest_creep_mmyr",
            "detection_confidence", "confidence_tier", "per_look_confidence"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for z in union:
            w.writerow([z["centroid_lonlat"], z["severity"], z["n_looks"],
                        z["strongest_creep_mmyr"], z["detection_confidence"],
                        z["confidence_tier"], z["per_look_confidence"]])


def write_md(path: Path, r: dict, union: list[dict]) -> None:
    sig = ", ".join(f"{s.replace('ASC_', '')}={v}" for s, v in r["sigma_v_mmyr"].items() if v)
    lines = [
        "# Per-zone detection confidence — propagating the velocity noise floor (§24)", "",
        f"The creep test is v < {r['creep_threshold_mmyr']} mm/yr, but the velocity has an "
        f"atmosphere-dominated **noise floor sigma_v** (per stack, mm/yr: **{sig}**). So each zone's "
        "confidence that its creep is REAL (not noise) is "
        "**p = Phi((−15 − v) / sigma_v)**, and looks combine by independent corroboration "
        "**P = 1 − prod(1 − p)** — so a multi-look zone is more trusted, quantitatively.", "",
        f"- **{r['n_union_zones']} union zones** ({r['n_multi_look']} multi-look). Detection confidence: "
        f"min **{r['confidence_min']}** / median **{r['confidence_median']}** / max **{r['confidence_max']}**.",
        f"- **{r['n_high_ge_0p9']}** HIGH (P ≥ 0.9) · **{r['n_moderate_0p7_0p9']}** MODERATE (0.7–0.9) · "
        f"the rest LOW.",
        "- Confidence-filtered footprints (scoreable by `backtest_inventory.py`): " +
        ", ".join(f"`{v['file']}` ({v['n_zones']})" for v in r["filtered_files"].values()) + ".",
        "",
        "## Top-10 most confident zones", "",
        "| rank | lon, lat | looks | per-look p | combined P | creep mm/yr | tier |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, z in enumerate(union[:10], 1):
        lon, lat = z["centroid_lonlat"]
        lines.append(f"| {i} | {lon:.4f}, {lat:.4f} | {z['n_looks']} | "
                     f"{z['per_look_confidence']} | **{z['detection_confidence']}** | "
                     f"{z['strongest_creep_mmyr']} | {z['confidence_tier']} |")
    lines += ["",
              "_Honest scope: sigma_v is the per-stack robust noise floor (1.4826·MAD of the high-passed "
              "velocity). The zone MEAN keeps ~the pixel noise because the post-high-pass atmospheric "
              "residual stays correlated across a sub-km zone (no sqrt-N averaging) — a conservative floor; "
              "independent-noise averaging would raise confidence. Multi-look combination assumes the looks' "
              "noise is independent (different orbits/dates), which corroboration supports._"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figure(path: Path, union: list[dict], sigma: dict) -> None:
    conf = np.array([z["detection_confidence"] for z in union])
    creep = np.array([z["strongest_creep_mmyr"] for z in union])
    looks = np.array([z["n_looks"] for z in union])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Panel 1: confidence vs creep, multi-look highlighted (corroboration boosts confidence).
    single = looks < 2
    ax1.scatter(creep[single], conf[single], s=30, c="#88a", alpha=0.7, label="1 look")
    ax1.scatter(creep[~single], conf[~single], s=70, c="#cc3333", edgecolor="#000",
                lw=0.4, label="≥2 looks (corroborated)")
    for cut, _ in CONF_TIERS[:-1]:
        ax1.axhline(cut, color="#666", ls="--", lw=0.8)
        ax1.text(creep.min(), cut, f" P={cut}", va="bottom", fontsize=8, color="#444")
    ax1.set_xlabel("strongest creep (mm/yr, more negative = faster)")
    ax1.set_ylabel("detection confidence  P(true creep < −15)")
    ax1.set_title("Per-zone detection confidence vs creep")
    ax1.set_ylim(0, 1.02)
    ax1.legend(fontsize=8, loc="lower left")
    ax1.grid(alpha=0.3)

    # Panel 2: survival curve — how many zones survive a confidence cut.
    taus = np.linspace(0, 1, 101)
    surviving = [int((conf >= t).sum()) for t in taus]
    ax2.plot(taus, surviving, color="#2a6", lw=2)
    for cut in (0.7, 0.9):
        n = int((conf >= cut).sum())
        ax2.axvline(cut, color="#666", ls="--", lw=0.8)
        ax2.text(cut, n, f" {n}@{cut}", fontsize=8, va="bottom")
    ax2.set_xlabel("confidence cut τ")
    ax2.set_ylabel("zones with P ≥ τ")
    ax2.set_title("High-confidence subset size vs cut")
    ax2.grid(alpha=0.3)

    sig = ", ".join(f"{s.replace('ASC_', '')} σ={v:.0f}" for s, v in sigma.items() if v)
    fig.suptitle(f"Velocity-noise-floor detection confidence  ({sig} mm/yr)", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
"""soil_sensitivity_sweep.py — how much do the soil parameters actually matter?

The question this answers (ERRC "Reduce" decision, 2026-07-13): the hand-curated
per-site soil pass (NEW_AOI_PLAYBOOK.md step 3 / M2) is the most laborious manual
step for a new AOI. If the back-test score of the operational alert product barely
moves across the PLAUSIBLE literature range of soil parameters (§37 bracket:
φ 32–43°, c_dry 4.9–27.5 kPa, c_wet 4.5–7.9 kPa, weathering depth 1–3 m; γ ±2
around 19 — the un-bracketed unknown), then global priors + an uncertainty band
suffice for spatial PRIORITIZATION at a new site and the literature pass demotes
to optional. If the score swings, the manual pass stays justified.

Method: FS_dry/FS_saturated are closed-form in the (soil-independent) slope
raster, so for each soil combo we recompute the two end-member FS rasters with
the engine's own `factor_of_safety`, rebuild the per-stack + union alert zones at
the site's OPERATIONAL saturation (config `operational_m`), and score against the
documented-landslide inventory with the same fixed null-point control the m-sweep
uses (`rainfall_selectivity_backtest`). The canonical FS rasters are backed up
before the sweep and byte-restored afterwards (verified by checksum) — the
production hazard/alert products are untouched.

Sanity gate: the `baseline` combo (the config's own soil values) must reproduce
the canonical operational product (§32: same union zone count).

Caveat carried into the report: this measures SPATIAL discrimination only. The
per-zone critical saturation m* = (1-FS_dry)/(FS_sat-FS_dry) (§19) shifts in
absolute terms with soil strength even when the spatial ranking is robust, so the
WHEN-gating calibration still inherits soil uncertainty.

Run (insar image):
  docker compose run --rm insar python workflows/soil_sensitivity_sweep.py
  docker compose run --rm -e INSAR_CONFIG=config/ramban.yaml insar \
      python workflows/soil_sensitivity_sweep.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import agentic_orchestrator as orch                    # noqa: E402
import backtest_inventory as bt                        # noqa: E402
import rainfall_selectivity_backtest as rsb            # noqa: E402
import run_multistack as multi                         # noqa: E402
from geomechanical_engine import factor_of_safety      # noqa: E402
from config import load_config                         # noqa: E402

_CFG = load_config()
_SFX = _CFG.data_suffix
HAZ_DIR = PROJECT_ROOT / "data" / f"hazard{_SFX}"
INV_DIR = PROJECT_ROOT / "data" / "inventory"

# The plausible envelope, one-at-a-time around the config baseline + the two
# adversarial corners. Sources: §37 (VD literature bracket), §20 (Ramban GSI
# calibration); γ is the un-bracketed parameter (±2 kN/m³ spans typical
# colluvium). Keys mirror config.py SoilConfig.
SWEEP = [
    ("baseline",  {}),
    ("phi_32",    {"phi_deg": 32.0}),
    ("phi_40",    {"phi_deg": 40.0}),
    ("phi_43",    {"phi_deg": 43.0}),
    ("cdry_4.9",  {"cohesion_dry_kpa": 4.9}),
    ("cdry_27.5", {"cohesion_dry_kpa": 27.5}),
    ("cwet_4.5",  {"cohesion_wet_kpa": 4.5}),
    ("cwet_7.9",  {"cohesion_wet_kpa": 7.9}),
    ("z_1",       {"depth_m": 1.0}),
    ("z_2",       {"depth_m": 2.0}),
    ("gamma_17",  {"gamma_kn_m3": 17.0}),
    ("gamma_21",  {"gamma_kn_m3": 21.0}),
    ("weakest",   {"phi_deg": 32.0, "cohesion_dry_kpa": 4.9,
                   "cohesion_wet_kpa": 4.5, "gamma_kn_m3": 21.0, "depth_m": 3.0}),
    ("strongest", {"phi_deg": 43.0, "cohesion_dry_kpa": 27.5,
                   "cohesion_wet_kpa": 7.9, "gamma_kn_m3": 17.0, "depth_m": 1.0}),
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fs_paths(stack: str) -> tuple[Path, Path]:
    return HAZ_DIR / f"{stack}_FS_dry.tif", HAZ_DIR / f"{stack}_FS_saturated.tif"


def write_fs(stack: str, slope_rad: np.ndarray, profile: dict, p: dict) -> None:
    """Recompute + write both FS end-members for one soil combo (engine formula)."""
    fs_dry = factor_of_safety(slope_rad, p["cohesion_dry_kpa"], p["phi_deg"],
                              p["gamma_kn_m3"], p["depth_m"], m=0.0)
    fs_sat = factor_of_safety(slope_rad, p["cohesion_wet_kpa"], p["phi_deg"],
                              p["gamma_kn_m3"], p["depth_m"], m=1.0)
    for path, arr in zip(fs_paths(stack), (fs_dry, fs_sat)):
        with rasterio.open(path, "w", **profile) as d:
            d.write(arr, 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory", default=str(rsb.DEFAULT_INVENTORY))
    ap.add_argument("--stacks", nargs="*", default=None)
    ap.add_argument("--buffer-km", type=float, default=2.0)
    ap.add_argument("--n-null", type=int, default=5000)
    ap.add_argument("--null-seed", type=int, default=20260606)
    args = ap.parse_args()

    m_op = _CFG.operational_m
    base_soil = {"cohesion_dry_kpa": _CFG.soil.cohesion_dry_kpa,
                 "cohesion_wet_kpa": _CFG.soil.cohesion_wet_kpa,
                 "phi_deg": _CFG.soil.phi_deg,
                 "gamma_kn_m3": _CFG.soil.gamma_kn_m3,
                 "depth_m": _CFG.soil.depth_m}
    stacks = args.stacks if args.stacks else multi.connected_stacks()
    if not stacks:
        raise SystemExit("No connected stacks.")

    # Fixed inventory + null points, shared across combos (comparable scores).
    inv = bt.load_inventory(Path(args.inventory))
    rings, bbox = bt.aoi_polygon_lonlat(Path(_CFG.aoi_path))
    null_pts = bt.sample_null_points(rings, bbox, args.n_null, args.null_seed)
    inv_lonlat = [(p["lon"], p["lat"]) for p in inv]

    def score(zones):
        cents = [tuple(z["centroid_lonlat"]) for z in zones if z.get("centroid_lonlat")]
        if not cents:
            return None
        real = np.array([bt.nearest_zone_km(lon, lat, cents) for lon, lat in inv_lonlat])
        null = np.array([bt.nearest_zone_km(lon, lat, cents) for lon, lat in null_pts])
        roc, auc, at_buf = bt.roc_from_distances(real, null, bt.DEFAULT_ROC_BUFFERS_KM,
                                                 args.buffer_km)
        return {"auc": round(auc, 3), "at_buf": at_buf}

    # Slope (soil-independent) + raster profile, read once per stack.
    slopes, profiles, backups = {}, {}, {}
    for s in stacks:
        with rasterio.open(HAZ_DIR / f"{s}_slope_deg.tif") as src:
            slopes[s] = np.radians(src.read(1))
        with rasterio.open(fs_paths(s)[0]) as src:
            profiles[s] = dict(src.profile, dtype="float32", count=1,
                               nodata=np.nan, compress="lzw")

    # Backup the canonical FS rasters (refuse to run over a stale backup).
    for s in stacks:
        for p in fs_paths(s):
            bak = p.with_suffix(p.suffix + ".presweep_bak")
            if bak.exists():
                raise SystemExit(f"Stale backup {bak} exists — a previous sweep did "
                                 f"not restore. Resolve (restore or delete) first.")
            backups[p] = (bak, _sha(p))
            shutil.copy2(p, bak)

    n_canon = len(json.loads((multi.MOSAIC_ALERTS_DIR / "alerts_operational.json")
                             .read_text(encoding="utf-8")).get("zones", []))
    print(f"site={_CFG.site_name}  stacks={stacks}  operational m={m_op}")
    print(f"inventory: {len(inv)} pts | null: {len(null_pts)} (seed {args.null_seed}) "
          f"| canonical operational zones: {n_canon}")

    rows = []
    try:
        for label, overrides in SWEEP:
            p = {**base_soil, **overrides}
            scen = f"soil_{label}"
            for s in stacks:
                write_fs(s, slopes[s], profiles[s], p)
                rsb.build_stack_alerts(s, m_op, scen)
            zones = multi.union_alerts(stacks, scen)
            multi.MOSAIC_ALERTS_DIR.mkdir(parents=True, exist_ok=True)
            (multi.MOSAIC_ALERTS_DIR / f"alerts_{scen}.json").write_text(
                json.dumps({"scenario": scen, "soil": p, "saturation": m_op,
                            "source_stacks": stacks, "zones": zones}, indent=1),
                encoding="utf-8")
            core = [z for z in zones if z.get("n_looks", 1) >= 2]
            full_s, core_s = score(zones), score(core)
            rows.append({"label": label, "overrides": overrides, "params": p,
                         "n_zones": len(zones), "n_core": len(core),
                         "full": full_s, "core": core_s})
            ab = (full_s or {}).get("at_buf", {})
            print(f"  {label:<10} zones={len(zones):3d} (core {len(core):2d})  "
                  f"AUC={full_s['auc'] if full_s else None}  "
                  f"spec@{args.buffer_km}={ab.get('specificity')}  "
                  f"| core AUC={core_s['auc'] if core_s else None}")
            if label == "baseline" and len(zones) != n_canon:
                print(f"  !! baseline reproduces {len(zones)} zones vs canonical "
                      f"{n_canon} — investigate before trusting the sweep.")
    finally:
        # Byte-restore the canonical FS rasters, whatever happened above.
        for p, (bak, sha_before) in backups.items():
            if bak.exists():
                bak.replace(p)
            status = "OK" if _sha(p) == sha_before else "MISMATCH"
            if status != "OK":
                print(f"  !! RESTORE MISMATCH for {p} — rerun geomechanical_engine "
                      f"to regenerate.")
        print("canonical FS rasters restored (checksum-verified).")

    write_outputs(rows, args, m_op, n_canon)
    return 0


def _short(k: str) -> str:
    """Compact override names for the report table."""
    return (k.replace("cohesion_dry_kpa", "c_dry").replace("cohesion_wet_kpa", "c_wet")
             .replace("phi_deg", "phi").replace("gamma_kn_m3", "gamma")
             .replace("depth_m", "z"))


def write_outputs(rows, args, m_op, n_canon) -> None:
    base = next(r for r in rows if r["label"] == "baseline")
    b_auc = base["full"]["auc"]
    deltas = [(r, (r["full"]["auc"] - b_auc) if r["full"] else None)
              for r in rows if r["label"] != "baseline"]
    max_d = max((abs(d) for _, d in deltas if d is not None), default=0.0)
    zmin = min(r["n_zones"] for r in rows)
    zmax = max(r["n_zones"] for r in rows)

    lines = [
        "# Soil-sensitivity sweep — back-test score vs plausible soil parameters",
        "",
        f"Site `{_CFG.site_name}`; operational m={m_op}; inventory "
        f"`{Path(args.inventory).name}`; null n={args.n_null} (seed {args.null_seed}); "
        f"buffer {args.buffer_km} km. Envelope = the §37 literature bracket "
        f"(φ 32–43°, c_dry 4.9–27.5, c_wet 4.5–7.9 kPa, z 1–3 m) + γ ±2.",
        "",
        "| combo | overrides | union zones | core | AUC (full) | ΔAUC vs baseline | AUC (core) |",
        "|---|---|---|---|---|---|---|"]
    for r in rows:
        d = "" if r["label"] == "baseline" else (
            f"{r['full']['auc'] - b_auc:+.3f}" if r["full"] else "-")
        ov = ", ".join(f"{_short(k)}={v}"
                       for k, v in r["overrides"].items()) or "(config values)"
        lines.append(f"| {r['label']} | {ov} | {r['n_zones']} | {r['n_core']} | "
                     f"{r['full']['auc'] if r['full'] else '-'} | {d} | "
                     f"{r['core']['auc'] if r['core'] else '-'} |")
    lines += [
        "",
        f"**Baseline AUC {b_auc} ({base['n_zones']} zones; canonical product has "
        f"{n_canon}). Max |ΔAUC| across the envelope: {max_d:.3f}. Union footprint "
        f"range: {zmin}–{zmax} zones.**",
        "",
        "_Spatial discrimination only: per-zone m\\* (§19) still shifts in absolute "
        "terms with soil strength, so WHEN-gating calibration inherits soil "
        "uncertainty even where the spatial ranking is robust._"]
    (INV_DIR / f"soil_sensitivity_report{_SFX}.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    (INV_DIR / f"soil_sensitivity_report{_SFX}.json").write_text(
        json.dumps({"site": _CFG.site_name, "operational_m": m_op,
                    "buffer_km": args.buffer_km, "n_null": args.n_null,
                    "null_seed": args.null_seed, "canonical_zones": n_canon,
                    "rows": rows}, indent=2), encoding="utf-8")
    _plot(INV_DIR / f"soil_sensitivity{_SFX}.png", rows, b_auc)
    print(f"-> {INV_DIR / f'soil_sensitivity_report{_SFX}.md'} , .json , "
          f"soil_sensitivity{_SFX}.png")
    print(f"   baseline AUC {b_auc}; max |dAUC| across envelope {max_d:.3f}; "
          f"zones {zmin}-{zmax}")


def _plot(path: Path, rows, b_auc: float) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    others = [r for r in rows if r["label"] != "baseline"]
    labels = [r["label"] for r in others]
    aucs = [r["full"]["auc"] if r["full"] else np.nan for r in others]
    zones = [r["n_zones"] for r in others]
    y = np.arange(len(others))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
    a1.barh(y, [a - b_auc for a in aucs], color=["#d62728" if a < b_auc else "#2ca02c"
                                                 for a in aucs])
    a1.axvline(0, color="#333", lw=1)
    a1.set_yticks(y, labels)
    a1.set_xlabel(f"AUC - baseline ({b_auc})")
    a1.set_title("Spatial score shift per soil combo")
    a1.grid(alpha=0.3, axis="x")
    a2.barh(y, zones, color="#1f77b4")
    base_zones = next(r["n_zones"] for r in rows if r["label"] == "baseline")
    a2.axvline(base_zones, color="#333", lw=1, ls="--",
               label=f"baseline ({base_zones})")
    a2.set_xlabel("union alert zones")
    a2.set_title("Footprint size per soil combo")
    a2.legend(); a2.grid(alpha=0.3, axis="x")
    fig.suptitle("Soil-parameter sensitivity of the operational alert product")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())

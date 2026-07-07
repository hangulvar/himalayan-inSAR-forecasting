#!/usr/bin/env python
"""rainfall_selectivity_backtest.py — does a rainfall-REALISTIC saturation discriminate
better than the worst-case monsoon (m=1) alert product?  (RESULTS_AND_KPIS.md §16d.)

Context (§16b/§16c): the union monsoon mosaic assumes soil saturation m=1 EVERYWHERE,
which over-flags (AUC 0.409, FPR 0.90 @2 km). But the regional rainfall/antecedent model
(`rainfall_id_threshold.py --threshold nwhimalaya`) only reaches m=1 on 11/214 days — the
median day is m~0.26. The regional ID *curve* is a TEMPORAL gate (which days to issue) and
cannot move a spatial score; the spatial footprint is set by the assumed SATURATION level.

So this sweeps the assumed saturation m and, at each m, rebuilds the AOI union alert mosaic
and scores it against the GSI field-validated inventory (§14) with a null-point control +
distance-ROC (the same `roc_from_distances` the back-test uses). FS is exactly linear in m
(infinite-slope), so FS_real=(1-m)*FS_dry+m*FS_saturated needs no engine re-run — we reuse
the orchestrator's three agents per stack, then `run_multistack.union_alerts`.

m=1.0 reproduces the monsoon mosaic exactly (built-in sanity check vs §16b: 357 zones).

  docker compose run --rm insar python workflows/rainfall_selectivity_backtest.py
  docker compose run --rm insar python workflows/rainfall_selectivity_backtest.py \
      --saturations 0.25,0.4,0.55,0.7,0.85,1.0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import agentic_orchestrator as orch          # noqa: E402
import run_multistack as multi               # noqa: E402
import backtest_inventory as bt              # noqa: E402
from config import load_config               # noqa: E402

_CFG = load_config()
_SFX = _CFG.data_suffix                      # '' for ramban; '_<slug>' so AOIs coexist
INV_DIR = PROJECT_ROOT / "data" / "inventory"
MOSAIC_ALERTS_DIR = multi.MOSAIC_ALERTS_DIR  # slug-scoped (data/alerts<sfx>/mosaic_asc)
# Per-AOI inventory: ramban keeps its original GSI file (grandfathered); other sites
# use the <slug>_documented_landslides.geojson convention (§31).
DEFAULT_INVENTORY = (INV_DIR / "gsi_inventory_aoi.geojson" if _CFG.aoi_slug == "ramban"
                     else INV_DIR / f"{_CFG.aoi_slug}_documented_landslides.geojson")
DEFAULT_SATURATIONS = [0.25, 0.4, 0.55, 0.7, 0.85, 1.0]


def build_stack_alerts(stack: str, m: float, scen: str) -> int:
    """Build the per-stack alert zones at saturation m and write them where
    run_multistack.union_alerts expects them. Returns the zone count."""
    auditor = orch.InSARAuditor(stack, use_vslope=False)
    cfg = {"name": scen, "rainfall_mm_72h": 0, "saturation": round(m, 3),
           "fs_layer": "FS_real"}
    met = orch.MeteorologicalTrigger(stack, scen, cfg)
    reasoner = orch.CascadingReasoner(stack, auditor)
    creep = auditor.creep_mask(orch.VEL_CREEP_THR)
    unstable = met.unstable_mask(orch.FS_FAIL)
    alerts = reasoner.build_alerts(creep, met.fs, unstable, met.cfg)
    out = multi.ALERTS_DIR / stack / f"alerts_{scen}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"scenario": scen, "saturation": m, "stack": stack,
                               "alerts": alerts}, indent=1), encoding="utf-8")
    return len(alerts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory", default=str(DEFAULT_INVENTORY))
    ap.add_argument("--stacks", nargs="*", default=None,
                    help="Explicit stack list (default: connected stacks).")
    ap.add_argument("--saturations", default=None,
                    help=f"Comma-separated m values (default: "
                         f"{','.join(str(x) for x in DEFAULT_SATURATIONS)}).")
    ap.add_argument("--buffer-km", type=float, default=2.0)
    ap.add_argument("--n-null", type=int, default=5000)
    ap.add_argument("--null-seed", type=int, default=20260606)
    ap.add_argument("--aoi-path", default=None)
    args = ap.parse_args()

    sats = ([float(x) for x in args.saturations.split(",")] if args.saturations
            else DEFAULT_SATURATIONS)
    stacks = args.stacks if args.stacks else multi.connected_stacks()
    if not stacks:
        raise SystemExit("No connected stacks.")

    # Fixed inventory + null set, reused across all m so the scores are comparable.
    inv = bt.load_inventory(Path(args.inventory))
    aoi_path = Path(args.aoi_path) if args.aoi_path else None
    if aoi_path is None:
        from config import load_config
        aoi_path = Path(load_config().aoi_path)
    rings, bbox = bt.aoi_polygon_lonlat(aoi_path)
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
        peak = max((r for r in roc if r["lift"] is not None), key=lambda r: r["lift"])
        return {"auc": round(auc, 3), "at_buf": at_buf, "roc": roc,
                "peak_lift": peak["lift"], "peak_lift_km": peak["buffer_km"]}

    print(f"stacks: {stacks}")
    print(f"inventory: {len(inv)} pts | null: {len(null_pts)} pts (seed {args.null_seed})")
    rows = []
    for m in sats:
        scen = f"sat{int(round(m * 100)):03d}"
        for s in stacks:
            build_stack_alerts(s, m, scen)
        zones = multi.union_alerts(stacks, scen)
        MOSAIC_ALERTS_DIR.mkdir(parents=True, exist_ok=True)
        (MOSAIC_ALERTS_DIR / f"alerts_{scen}.json").write_text(
            json.dumps({"scenario": scen, "saturation": m, "source_stacks": stacks,
                        "zones": zones}, indent=1), encoding="utf-8")
        core = [z for z in zones if z.get("n_looks", 1) >= 2]
        full_s, core_s = score(zones), score(core)
        rows.append({"m": m, "scen": scen, "n_zones": len(zones), "n_core": len(core),
                     "full": full_s, "core": core_s})
        ab = full_s["at_buf"] if full_s else {}
        print(f"  m={m:.2f}  zones={len(zones):3d} (core {len(core):2d})  "
              f"AUC={full_s['auc'] if full_s else None}  "
              f"spec@{args.buffer_km}={ab.get('specificity')}  "
              f"lift@{args.buffer_km}={ab.get('lift')}x  "
              f"peak_lift={full_s['peak_lift'] if full_s else None}x@"
              f"{full_s['peak_lift_km'] if full_s else None}km  "
              f"| core AUC={core_s['auc'] if core_s else None}")

    write_outputs(rows, args)
    return 0


def write_outputs(rows, args) -> None:
    base = (1.0, next((r for r in rows if abs(r["m"] - 1.0) < 1e-9), None))
    lines = ["# Rainfall-selectivity sweep — AUC/specificity vs assumed saturation m",
             "",
             f"Inventory `{Path(args.inventory).name}`; null n={args.n_null} (seed "
             f"{args.null_seed}); buffer {args.buffer_km} km. FS_real=(1-m)*FS_dry+m*FS_sat. "
             "m=1.0 == the monsoon worst-case mosaic (§16b).",
             "",
             "| m (saturation) | union zones | >=2-look core | AUC (full) | spec@2km | "
             "lift@2km | peak lift | AUC (core) |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        f, c = r["full"], r["core"]
        ab = f["at_buf"] if f else {}
        lines.append(
            f"| {r['m']:.2f} | {r['n_zones']} | {r['n_core']} | "
            f"{f['auc'] if f else '-'} | {ab.get('specificity', '-')} | "
            f"{ab.get('lift', '-')}x | {f['peak_lift'] if f else '-'}x@"
            f"{f['peak_lift_km'] if f else '-'}km | {c['auc'] if c else '-'} |")
    best = max((r for r in rows if r["full"]), key=lambda r: r["full"]["auc"])
    base_txt = (f"vs **{base[1]['full']['auc']} at m=1.0** ({base[1]['n_zones']} zones, "
                f"the monsoon baseline)" if base[1] and base[1]["full"]
                else "(no m=1.0 baseline in this sweep)")
    lines += ["",
              f"**Best full-union AUC = {best['full']['auc']} at m={best['m']:.2f}** "
              f"({best['n_zones']} zones) {base_txt}.",
              "",
              "_The regional ID curve is a TEMPORAL gate (which days to issue) and cannot move "
              "this spatial score; the saturation level sets the spatial footprint. Lowering m "
              "concentrates the alert on the steepest/most-marginal slopes._"]
    (INV_DIR / f"rainfall_selectivity_report{_SFX}.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    (INV_DIR / f"rainfall_selectivity_report{_SFX}.json").write_text(
        json.dumps({"buffer_km": args.buffer_km, "n_null": args.n_null,
                    "null_seed": args.null_seed, "rows": rows}, indent=2), encoding="utf-8")
    _plot(INV_DIR / f"rainfall_selectivity{_SFX}.png", rows, args.buffer_km)
    print(f"-> {INV_DIR / f'rainfall_selectivity_report{_SFX}.md'} , .json , "
          f"rainfall_selectivity{_SFX}.png")
    print(f"   best full AUC {best['full']['auc']} @ m={best['m']:.2f} "
          f"(baseline m=1.0: {base[1]['full']['auc']})")


def _plot(path: Path, rows, buffer_km) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ms = [r["m"] for r in rows]
    auc_full = [r["full"]["auc"] if r["full"] else np.nan for r in rows]
    auc_core = [r["core"]["auc"] if r["core"] else np.nan for r in rows]
    spec = [r["full"]["at_buf"].get("specificity") if r["full"] else np.nan for r in rows]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
    a1.plot(ms, auc_full, "-o", color="#1f77b4", label="AUC (full union)")
    a1.plot(ms, auc_core, "-s", color="#2ca02c", label="AUC (>=2-look core)")
    a1.axhline(0.5, ls="--", color="#7f7f7f", label="chance (0.5)")
    a1.set_xlabel("assumed saturation m"); a1.set_ylabel("AUC")
    a1.set_title("Discrimination vs saturation"); a1.legend(); a1.grid(alpha=0.3)
    a1.invert_xaxis()  # selective (low m) on the right
    for m, sp in zip(ms, spec):
        a2.scatter(m, sp, color="#d62728")
    a2.plot(ms, spec, "-o", color="#d62728")
    a2.set_xlabel("assumed saturation m"); a2.set_ylabel(f"specificity @ {buffer_km} km")
    a2.set_title("Specificity vs saturation"); a2.grid(alpha=0.3); a2.invert_xaxis()
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())

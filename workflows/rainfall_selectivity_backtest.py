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


def build_stack_alerts(stack: str, m: float, scen: str, kappa: float = 0.0,
                       suction: tuple[float, float] | None = None) -> int:
    """Build the per-stack alert zones at saturation m (optionally TWI-distributed by
    kappa §45, optionally under a van Genuchten suction candidate (alpha,n) §46) and
    write them where run_multistack.union_alerts expects them. Returns the zone count."""
    auditor = orch.InSARAuditor(stack, use_vslope=False)
    cfg = {"name": scen, "rainfall_mm_72h": 0, "saturation": round(m, 3),
           "kappa": kappa, "fs_layer": "FS_real"}
    if suction is not None:                       # explicit candidate (alpha<=0 = OFF);
        cfg["suction_alpha"], cfg["suction_n"] = suction
    # no keys -> the orchestrator falls back to the site config's suction block, so a
    # plain m-sweep always scores the SAME physics the standing product ships with.
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
    ap.add_argument("--kappas", default=None,
                    help="Comma-separated kappa values (§45): sweep the TWI-distributed "
                         "saturation slope at fixed --operational-m INSTEAD of sweeping m. "
                         "kappa=0 reproduces the uniform-m footprint.")
    ap.add_argument("--operational-m", type=float, default=None,
                    help="Fixed saturation for the --kappas sweep (default: config operational_m).")
    ap.add_argument("--suction", default=None,
                    help="Van Genuchten candidate 'alpha_kpa_inv,n' (§46) applied to every "
                         "combo in this run ('0,0' forces the linear model). Default: the "
                         "site config's suction block (absent = linear).")
    ap.add_argument("--tag", default="",
                    help="Suffix appended to scenario names and report stems so experiment "
                         "runs (e.g. per-suction-candidate sweeps) never overwrite the "
                         "standing sweep artifacts.")
    ap.add_argument("--buffer-km", type=float, default=2.0)
    ap.add_argument("--n-null", type=int, default=5000)
    ap.add_argument("--null-seed", type=int, default=20260606)
    ap.add_argument("--aoi-path", default=None)
    args = ap.parse_args()

    stacks = args.stacks if args.stacks else multi.connected_stacks()
    if not stacks:
        raise SystemExit("No connected stacks.")

    # Fixed inventory + null set, reused across all combos so the scores are comparable.
    inv = bt.load_inventory(Path(args.inventory))
    aoi_path = Path(args.aoi_path) if args.aoi_path else None
    if aoi_path is None:
        aoi_path = Path(_CFG.aoi_path)
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

    # A combo is (scenario_name, saturation_m, kappa). The m-sweep varies m at the SITE's
    # adopted kappa (§45 — vary one dial, hold the others at config); the kappa-sweep
    # varies kappa at a fixed operational m. The suction layer (§46) rides along from the
    # config unless --suction pins a candidate for the whole run.
    suction = None
    if args.suction is not None:
        a, n = (float(x) for x in args.suction.split(","))
        suction = (a, n)
    tag = args.tag
    if args.kappas is not None:
        op_m = args.operational_m if args.operational_m is not None else _CFG.operational_m
        kappas = [float(x) for x in args.kappas.split(",")]
        combos = [(f"kap{int(round(k * 1000)):03d}{tag}", op_m, k) for k in kappas]
        sweep = "kappa"
    else:
        sats = ([float(x) for x in args.saturations.split(",")] if args.saturations
                else DEFAULT_SATURATIONS)
        combos = [(f"sat{int(round(m * 100)):03d}{tag}", m, _CFG.kappa) for m in sats]
        sweep = "m"

    print(f"stacks: {stacks}")
    print(f"inventory: {len(inv)} pts | null: {len(null_pts)} pts (seed {args.null_seed})")
    print(f"sweep: {sweep}"
          + (f" at m={combos[0][1]:.2f}" if sweep == "kappa" else f" at kappa={_CFG.kappa:g}")
          + (f" | suction override alpha,n={suction}" if suction else ""))
    rows = []
    for scen, m, kappa in combos:
        for s in stacks:
            build_stack_alerts(s, m, scen, kappa, suction)
        zones = multi.union_alerts(stacks, scen)
        MOSAIC_ALERTS_DIR.mkdir(parents=True, exist_ok=True)
        (MOSAIC_ALERTS_DIR / f"alerts_{scen}.json").write_text(
            json.dumps({"scenario": scen, "saturation": m, "kappa": kappa,
                        "suction_alpha_n": suction,
                        "source_stacks": stacks, "zones": zones}, indent=1), encoding="utf-8")
        core = [z for z in zones if z.get("n_looks", 1) >= 2]
        full_s, core_s = score(zones), score(core)
        rows.append({"m": m, "kappa": kappa, "scen": scen, "n_zones": len(zones),
                     "n_core": len(core), "full": full_s, "core": core_s})
        ab = full_s["at_buf"] if full_s else {}
        lead = f"kappa={kappa:.3f}" if sweep == "kappa" else f"m={m:.2f}"
        print(f"  {lead}  zones={len(zones):3d} (core {len(core):2d})  "
              f"AUC={full_s['auc'] if full_s else None}  "
              f"spec@{args.buffer_km}={ab.get('specificity')}  "
              f"lift@{args.buffer_km}={ab.get('lift')}x  "
              f"peak_lift={full_s['peak_lift'] if full_s else None}x@"
              f"{full_s['peak_lift_km'] if full_s else None}km  "
              f"| core AUC={core_s['auc'] if core_s else None}")

    if sweep == "kappa":
        write_kappa_outputs(rows, args)
    else:
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
    tag = getattr(args, "tag", "")
    (INV_DIR / f"rainfall_selectivity_report{_SFX}{tag}.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    (INV_DIR / f"rainfall_selectivity_report{_SFX}{tag}.json").write_text(
        json.dumps({"buffer_km": args.buffer_km, "n_null": args.n_null,
                    "null_seed": args.null_seed, "suction": args.suction,
                    "rows": rows}, indent=2), encoding="utf-8")
    _plot(INV_DIR / f"rainfall_selectivity{_SFX}{tag}.png", rows, args.buffer_km)
    print(f"-> {INV_DIR / f'rainfall_selectivity_report{_SFX}{tag}.md'} , .json , "
          f"rainfall_selectivity{_SFX}{tag}.png")
    print(f"   best full AUC {best['full']['auc']} @ m={best['m']:.2f} "
          f"(baseline m=1.0: {base[1]['full']['auc']})")


def write_kappa_outputs(rows, args) -> None:
    """§45 kappa sweep report: AUC/spec/lift vs the TWI-distribution slope kappa, with
    kappa=0 (uniform m) as the built-in baseline."""
    base = next((r for r in rows if abs(r["kappa"]) < 1e-9), None)
    m0 = rows[0]["m"] if rows else None
    lines = ["# TWI-distributed saturation sweep (§45) — AUC vs kappa",
             "",
             f"Fixed operational saturation **m={m0:.2f}**; each pixel gets "
             f"m_i = clip(m + kappa*(TWI_i - TWI_mean), 0, 1) (kappa units 1/TWI). "
             f"**kappa=0 = the uniform-m footprint** (regression baseline). Inventory "
             f"`{Path(args.inventory).name}`; null n={args.n_null} (seed {args.null_seed}); "
             f"buffer {args.buffer_km} km.",
             "",
             "| kappa | union zones | >=2-look core | AUC (full) | spec@2km | lift@2km | "
             "peak lift | AUC (core) |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        f, c = r["full"], r["core"]
        ab = f["at_buf"] if f else {}
        lines.append(
            f"| {r['kappa']:.3f} | {r['n_zones']} | {r['n_core']} | "
            f"{f['auc'] if f else '-'} | {ab.get('specificity', '-')} | "
            f"{ab.get('lift', '-')}x | {f['peak_lift'] if f else '-'}x@"
            f"{f['peak_lift_km'] if f else '-'}km | {c['auc'] if c else '-'} |")
    best = max((r for r in rows if r["full"]), key=lambda r: r["full"]["auc"])
    base_txt = (f"vs **{base['full']['auc']} at kappa=0** ({base['n_zones']} zones, the "
                f"uniform-m baseline)" if base and base["full"] else "(no kappa=0 baseline)")
    verdict = ("IMPROVES on" if best["kappa"] != 0 and base and base["full"]
               and best["full"]["auc"] > base["full"]["auc"] else "does NOT beat")
    lines += ["",
              f"**Best full-union AUC = {best['full']['auc']} at kappa={best['kappa']:.3f}** "
              f"({best['n_zones']} zones) {base_txt} — spatial redistribution {verdict} the "
              f"uniform baseline on this inventory.",
              "",
              "_kappa REDISTRIBUTES saturation spatially (wet hollows earlier, dry ridges "
              "later) while preserving the AOI-mean wetness = the rainfall proxy, so the "
              "temporal coupling is unchanged. Judge the winner with validation_stats.py "
              "(§44 CIs + ablation ladder) before adopting._"]
    tag = getattr(args, "tag", "")
    (INV_DIR / f"rainfall_kappa_report{_SFX}{tag}.md").write_text("\n".join(lines) + "\n",
                                                                  encoding="utf-8")
    (INV_DIR / f"rainfall_kappa_report{_SFX}{tag}.json").write_text(
        json.dumps({"buffer_km": args.buffer_km, "n_null": args.n_null,
                    "null_seed": args.null_seed, "operational_m": m0, "rows": rows}, indent=2),
        encoding="utf-8")
    _plot_kappa(INV_DIR / f"rainfall_kappa{_SFX}{tag}.png", rows, args.buffer_km)
    print(f"-> {INV_DIR / f'rainfall_kappa_report{_SFX}{tag}.md'} , .json , "
          f"rainfall_kappa{_SFX}{tag}.png")
    print(f"   best full AUC {best['full']['auc']} @ kappa={best['kappa']:.3f} "
          f"(baseline kappa=0: {base['full']['auc'] if base and base['full'] else 'n/a'})")


def _plot_kappa(path: Path, rows, buffer_km) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ks = [r["kappa"] for r in rows]
    auc_full = [r["full"]["auc"] if r["full"] else np.nan for r in rows]
    auc_core = [r["core"]["auc"] if r["core"] else np.nan for r in rows]
    nz = [r["n_zones"] for r in rows]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
    a1.plot(ks, auc_full, "-o", color="#1f77b4", label="AUC (full union)")
    a1.plot(ks, auc_core, "-s", color="#2ca02c", label="AUC (>=2-look core)")
    a1.axhline(0.5, ls="--", color="#7f7f7f", label="chance (0.5)")
    base = next((r for r in rows if abs(r["kappa"]) < 1e-9), None)
    if base and base["full"]:
        a1.axhline(base["full"]["auc"], ls=":", color="#1f77b4", alpha=0.6,
                   label=f"kappa=0 baseline ({base['full']['auc']})")
    a1.set_xlabel("TWI-distribution slope kappa (1/TWI)"); a1.set_ylabel("AUC")
    a1.set_title("Discrimination vs kappa"); a1.legend(fontsize=8); a1.grid(alpha=0.3)
    a2.plot(ks, nz, "-o", color="#d62728")
    a2.set_xlabel("kappa (1/TWI)"); a2.set_ylabel("union alert zones")
    a2.set_title("Footprint size vs kappa"); a2.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


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

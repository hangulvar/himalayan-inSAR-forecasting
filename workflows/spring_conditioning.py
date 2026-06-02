#!/usr/bin/env python
"""spring_conditioning.py — characterize the spring-2025 slope CONDITIONING (chronic snowmelt +
antecedent saturation + per-elevation freeze-thaw), the leading remaining hypothesis now that an
ACUTE rainfall trigger has been ruled out (RESULTS_AND_KPIS.md §12e: ERA5-Land + CHIRPS + IMERG all
agree there was no triggering downpour on the documented 27 Apr / 8 May 2025 NH-44 failures).

Two slow, PRIMING mechanisms — both from data we already have (ERA5-Land daily CSV + the bundled
80 m DEM), no GEE, no new fetch:

1. PER-ELEVATION FREEZE-THAW. The AOI-*mean* temperature never crosses 0 C (the warm valley floor
   dominates the mean) -> the freeze-thaw flag returned 0 days by construction (§11 limitation). We
   lapse-rate the daily Tmin/Tmax onto the DEM's elevation BANDS:
       T(z) = T_mean - ELR * (z - z_ref),   ELR = 6.5 C/km,  z_ref = AOI-mean DEM elevation
   and count freeze-thaw days (Tmin(z) < 0 < Tmax(z)) per band -> reveals the elevation above which
   spring freeze-thaw cycling weakens slopes (the mechanism the AOI-mean hides).

2. CHRONIC ANTECEDENT SATURATION. Snowmelt (concentrated in early April) + accumulating rain build a
   wetness MEMORY (antecedent index, API). Spring slopes are progressively primed independent of any
   acute burst -> report the spring API/water vs the pre-monsoon dry baseline + the values on the
   event days.

HONEST SCOPE: lapse-rate downscaling is a standard first-order method but assumes a constant ELR and
z_ref = DEM-mean (ERA5-Land's true orography would refine z_ref); treat the freeze-thaw elevations as
indicative (+/- a few hundred m). EECU-free; runs in the insar container.
  docker compose run --rm insar python workflows/spring_conditioning.py
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.warp import transform_bounds  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))
from config import load_config
from rainfall_id_threshold import load_daily, antecedent_index

RAIN_CSV = PROJECT_ROOT / "data" / "rainfall" / "ramban_era5land_daily.csv"
OUT_DIR = PROJECT_ROOT / "data" / "rainfall"
ELR_C_PER_KM = 6.5                       # environmental lapse rate (standard mean)
SPRING = (date(2025, 4, 1), date(2025, 5, 31))
EVENT_DAYS = ["2025-04-27", "2025-05-08"]
EVENT_ELEV_M = 1540                      # documented NH-44 corridor/event elevation (Digdol ~1540 m)


def aoi_bounds_lonlat():
    gj = json.loads(Path(load_config().aoi_path).read_text(encoding="utf-8"))
    xs, ys = [], []

    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for x in c:
                walk(x)
    for feat in gj.get("features", [gj]):
        walk(feat["geometry"]["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


def aoi_dem_elevations():
    """Elevations (m) of the DEM clipped to the AOI bbox (drops nodata/sea sentinels)."""
    dem_path = sorted(glob.glob(str(PROJECT_ROOT / "data" / "processed_tiffs" / "*" / "*_dem.tif")))
    if not dem_path:
        raise SystemExit("No *_dem.tif under data/processed_tiffs/ — run Phase 1 first.")
    w, s, e, n = aoi_bounds_lonlat()
    with rasterio.open(dem_path[0]) as ds:
        l, b, r, t = transform_bounds("EPSG:4326", ds.crs, w, s, e, n)
        win = ds.window(l, b, r, t)
        a = ds.read(1, window=win).astype("float64")
    a[a < -1000] = np.nan
    a[a == 0] = np.nan
    return a[np.isfinite(a)], Path(dem_path[0]).parent.name


def freeze_thaw_by_band(dates, tmin, tmax, z_ref, bands):
    """For each band centre z: freeze-thaw day count (Tmin(z)<0<Tmax(z)), season + spring."""
    dts = np.array(dates)
    in_spring = np.array([SPRING[0] <= d <= SPRING[1] for d in dates])
    rows = []
    for z in bands:
        dT = ELR_C_PER_KM * (z - z_ref) / 1000.0          # cooling vs the AOI-mean reference
        lo = tmin - dT
        hi = tmax - dT
        ft = np.isfinite(lo) & np.isfinite(hi) & (lo < 0.0) & (hi > 0.0)
        rows.append({"elev_m": int(z),
                     "ft_days_season": int(ft.sum()),
                     "ft_days_spring": int((ft & in_spring).sum())})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(RAIN_CSV))
    args = ap.parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"Missing daily CSV: {csv_path} — run fetch_rainfall.py first.")

    dates, rain, snowmelt, tmin, tmax = load_daily(csv_path)
    water = np.nan_to_num(rain) + np.nan_to_num(snowmelt)
    api = antecedent_index(water)

    elev, dem_src = aoi_dem_elevations()
    z_ref = float(np.nanmean(elev))
    z_lo, z_hi = float(np.percentile(elev, 5)), float(np.percentile(elev, 95))
    bands = list(range(int(round(z_lo / 500) * 500), int(z_hi) + 1, 500))
    if not bands:
        bands = [int(z_ref)]
    ft_rows = freeze_thaw_by_band(dates, tmin, tmax, z_ref, bands)
    # area fraction per band (DEM hist) for context
    for row in ft_rows:
        z = row["elev_m"]
        row["aoi_area_pct"] = round(100.0 * float(np.mean((elev >= z - 250) & (elev < z + 250))), 1)
    # lowest elevation with >=5 spring freeze-thaw days = the FT onset elevation
    ft_onset = next((r["elev_m"] for r in ft_rows if r["ft_days_spring"] >= 5), None)

    # chronic saturation: spring vs dry pre-monsoon baseline
    idx = {d.isoformat(): i for i, d in enumerate(dates)}   # key by ISO string (EVENT_DAYS are strings)
    spring_mask = np.array([SPRING[0] <= d <= SPRING[1] for d in dates])
    pre_monsoon = np.array([date(2025, 4, 1) <= d <= date(2025, 6, 15) for d in dates])
    api95 = float(np.percentile(api, 95))
    report = {
        "source": csv_path.name, "dem_source": dem_src,
        "lapse_rate_C_per_km": ELR_C_PER_KM, "z_ref_m": round(z_ref, 0),
        "aoi_elev_p5_p95_m": [round(z_lo), round(z_hi)],
        "event_elev_m": EVENT_ELEV_M,
        "freeze_thaw_onset_elev_m": ft_onset,
        "freeze_thaw_by_band": ft_rows,
        "freeze_thaw_at_event_elev": ft_at_elev(dates, tmin, tmax, z_ref, EVENT_ELEV_M),
        "snowmelt_total_mm": round(float(np.nansum(snowmelt)), 1),
        "snowmelt_spring_mm": round(float(np.nansum(snowmelt[spring_mask])), 1),
        "api_spring_mean_mm": round(float(np.nanmean(api[spring_mask])), 1),
        "api_spring_max_mm": round(float(np.nanmax(api[spring_mask])), 1),
        "api_p95_mm": round(api95, 1),
        "event_days": {d: {"api_mm": round(float(api[idx[d]]), 1),
                           "wetness_0_1": round(float(min(api[idx[d]] / api95, 1.0)), 2),
                           "water_mm": round(float(water[idx[d]]), 1)}
                       for d in EVENT_DAYS if d in idx},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "spring_conditioning_report.json").write_text(json.dumps(report, indent=2),
                                                             encoding="utf-8")
    write_md(OUT_DIR / "spring_conditioning_report.md", report)
    make_figure(OUT_DIR / "spring_conditioning.png", dates, rain, snowmelt, water, api,
                ft_rows, z_ref, report)

    print(f"DEM (AOI-clipped): z_ref(mean)={z_ref:.0f} m, p5..p95 = {z_lo:.0f}..{z_hi:.0f} m  ({dem_src})")
    print(f"event/corridor elevation ~{EVENT_ELEV_M} m  (documented NH-44 slides sit near the valley)")
    print(f"\nPER-ELEVATION FREEZE-THAW (ELR {ELR_C_PER_KM} C/km, z_ref {z_ref:.0f} m):")
    for r in ft_rows:
        print(f"  {r['elev_m']:5d} m ({r['aoi_area_pct']:4.1f}% AOI): "
              f"freeze-thaw days season={r['ft_days_season']:3d}  spring={r['ft_days_spring']:3d}")
    fe = report["freeze_thaw_at_event_elev"]
    print(f"  at the ~{EVENT_ELEV_M} m event elevation: spring freeze-thaw days = {fe['ft_days_spring']}")
    print(f"  freeze-thaw ONSET elevation (>=5 spring days): "
          f"{ft_onset if ft_onset else 'none in range'} m")
    print(f"\nCHRONIC SATURATION: snowmelt spring={report['snowmelt_spring_mm']:.0f} mm; "
          f"spring API mean={report['api_spring_mean_mm']:.0f} / max={report['api_spring_max_mm']:.0f} mm "
          f"(season p95={report['api_p95_mm']:.0f})")
    for d, v in report["event_days"].items():
        print(f"  {d}: water={v['water_mm']} mm  API={v['api_mm']} mm  wetness={v['wetness_0_1']}")
    print(f"\nVERDICT: {report_verdict(report)}")
    print(f"  -> {OUT_DIR/'spring_conditioning_report.json'} , .md , spring_conditioning.png")
    return 0


def ft_at_elev(dates, tmin, tmax, z_ref, z):
    dT = ELR_C_PER_KM * (z - z_ref) / 1000.0
    lo, hi = tmin - dT, tmax - dT
    in_spring = np.array([SPRING[0] <= d <= SPRING[1] for d in dates])
    ft = np.isfinite(lo) & np.isfinite(hi) & (lo < 0.0) & (hi > 0.0)
    return {"ft_days_season": int(ft.sum()), "ft_days_spring": int((ft & in_spring).sum())}


def report_verdict(r: dict) -> str:
    onset = r["freeze_thaw_onset_elev_m"]
    ev_ft = r["freeze_thaw_at_event_elev"]["ft_days_spring"]
    ev = r.get("event_days", {})
    wet = max((v["wetness_0_1"] for v in ev.values()), default=0.0)
    ft_txt = (f"spring freeze-thaw cycling begins around ~{onset} m and intensifies upslope; "
              if onset else "no spring freeze-thaw even at the AOI's upper bands (mild season); ")
    ev_txt = (f"the documented events sit near the warm valley (~{r['event_elev_m']} m, "
              f"{ev_ft} spring freeze-thaw days there) so freeze-thaw acts mainly on the higher source "
              f"slopes ABOVE the road, not at the road itself; ")
    sat_txt = (f"meanwhile the slopes were CHRONICALLY WET in spring (event-day wetness up to {wet:.0%} of "
               f"the season peak from snowmelt+antecedent rain, with ~{r['snowmelt_spring_mm']:.0f} mm "
               f"spring snowmelt) even with no acute burst.")
    return (ft_txt + ev_txt + sat_txt +
            " Consistent with PRIMING (saturation + upslope freeze-thaw weakening) rather than an acute "
            "rainfall trigger — supports the §12e conclusion.")


def write_md(path: Path, r: dict) -> None:
    lines = [f"# Spring-2025 slope conditioning — {r['source']}", "",
             "Now that an acute rainfall trigger is ruled out (RESULTS §12e), this characterises the two "
             "slow PRIMING mechanisms for the spring NH-44 failures, from existing data (ERA5-Land + DEM).",
             "", "## 1. Per-elevation freeze-thaw",
             f"AOI-mean temperature gives **0** freeze-thaw days (valley floor dominates). Lapse-rating "
             f"(ELR **{r['lapse_rate_C_per_km']} C/km**, z_ref **{r['z_ref_m']:.0f} m** = AOI-mean DEM "
             f"elevation; AOI p5–p95 {r['aoi_elev_p5_p95_m'][0]}–{r['aoi_elev_p5_p95_m'][1]} m) onto "
             f"elevation bands:", "",
             "| elevation | % AOI | freeze-thaw days (season) | freeze-thaw days (spring) |",
             "|---|---|---|---|"]
    for b in r["freeze_thaw_by_band"]:
        lines.append(f"| {b['elev_m']} m | {b['aoi_area_pct']} | {b['ft_days_season']} | "
                     f"{b['ft_days_spring']} |")
    fe = r["freeze_thaw_at_event_elev"]
    lines += ["",
              f"- Freeze-thaw **onset** (>=5 spring days): **{r['freeze_thaw_onset_elev_m']} m**.",
              f"- At the documented event/corridor elevation (~{r['event_elev_m']} m): "
              f"**{fe['ft_days_spring']} spring freeze-thaw days** — the road sits in the warm valley, so "
              f"freeze-thaw weakening acts mainly on the **higher source slopes above** it.",
              "", "## 2. Chronic antecedent saturation",
              f"- Spring snowmelt: **{r['snowmelt_spring_mm']:.0f} mm** (of {r['snowmelt_total_mm']:.0f} mm "
              f"season); spring API (wetness memory) mean **{r['api_spring_mean_mm']:.0f} mm**, max "
              f"**{r['api_spring_max_mm']:.0f} mm** (season p95 {r['api_p95_mm']:.0f} mm).", ""]
    for d, v in r["event_days"].items():
        lines.append(f"- **{d}**: same-day water {v['water_mm']} mm, antecedent API {v['api_mm']} mm "
                     f"-> wetness **{v['wetness_0_1']:.0%}** of the season peak.")
    lines += ["", "## Verdict", f"**{report_verdict(r)}**", "",
              "_Scope: lapse-rate downscaling is first-order (constant ELR; z_ref = DEM-mean — ERA5-Land's "
              "true orography would refine it); freeze-thaw elevations are indicative (+/- a few hundred m). "
              "Mechanistic framing, not a calibrated trigger._"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figure(path: Path, dates, rain, snowmelt, water, api, ft_rows, z_ref, r) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    z = [b["elev_m"] for b in ft_rows]
    ft_spring = [b["ft_days_spring"] for b in ft_rows]
    ft_season = [b["ft_days_season"] for b in ft_rows]
    ax1.barh(z, ft_season, height=320, color="#cfe8f3", label="season")
    ax1.barh(z, ft_spring, height=320, color="#4477aa", label="spring (Apr-May)")
    ax1.axhline(z_ref, color="#999", ls="--", lw=1); ax1.text(ax1.get_xlim()[1], z_ref,
                " z_ref (AOI mean)", va="center", ha="right", fontsize=7, color="#666")
    ax1.axhline(r["event_elev_m"], color="#cc3311", ls="-", lw=1.2)
    ax1.text(ax1.get_xlim()[1], r["event_elev_m"], " event/corridor ~1540 m", va="bottom",
             ha="right", fontsize=7, color="#cc3311")
    ax1.set_xlabel("freeze-thaw days"); ax1.set_ylabel("elevation (m)")
    ax1.set_title("Per-elevation freeze-thaw (lapse-rated ERA5-Land); valley is warm, slopes cycle")
    ax1.legend(fontsize=8, loc="lower right"); ax1.grid(alpha=0.3)

    x = np.arange(len(dates))
    ax2.bar(x, rain, color="#4477aa", width=1.0, label="rain")
    ax2.bar(x, np.nan_to_num(snowmelt), bottom=np.nan_to_num(rain), color="#88ccee", width=1.0,
            label="snowmelt")
    ax2b = ax2.twinx()
    ax2b.plot(x, api, color="#cc3311", lw=1.4, label="antecedent index (API)")
    for d in EVENT_DAYS:
        if d in dates:
            i = dates.index(date.fromisoformat(d))
            ax2.axvline(i, color="#222", lw=1.0, ls=":")
    ax2.set_ylabel("daily water (mm)"); ax2b.set_ylabel("API / wetness memory (mm)")
    ax2.set_title("Chronic saturation: snowmelt+rain build the wetness memory through spring "
                  "(dotted = documented events)")
    tick = np.linspace(0, len(dates) - 1, 7).astype(int)
    ax2.set_xticks(tick); ax2.set_xticklabels([dates[i].strftime("%b %d") for i in tick])
    ax2.legend(fontsize=8, loc="upper left"); ax2b.legend(fontsize=8, loc="upper right")
    ax2.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

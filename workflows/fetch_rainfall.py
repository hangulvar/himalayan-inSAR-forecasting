#!/usr/bin/env python
"""fetch_rainfall.py — real daily WATER INPUT (rain + snowmelt) and freeze-thaw
temperature for the AOI from ERA5-Land (CDS), to drive the landslide trigger with
the actual weather instead of the mock dry/monsoon/extreme scenarios.

Three ERA5-Land variables (the back-test exposed that rainfall ALONE missed the
documented Apr-May 2025 Ramban failures — the NW-Himalaya snowmelt / freeze-thaw
season — so we add the two missing physical drivers):
  * total_precipitation (tp) — accumulated from 00 UTC (m). Day D's total is the
    00:00-UTC value of day D+1.  *1000 -> mm.
  * snowmelt (smlt) — accumulated from 00 UTC (m water-equivalent), same valid-time
    rule as tp. Added to rain as the effective WATER INPUT loading the slope.
  * 2m_temperature (2t) — instantaneous (K). Sampled at 00/06/12/18 UTC to derive a
    daily Tmin/Tmax -> a freeze-thaw flag (Tmin<0<Tmax), the spring slope-weakening
    mechanism that pairs with snowmelt.

Window default extended to APRIL (the documented 2025-04-27 event preceded the old
2025-05-01 start). Runs in the MintPy image (cdsapi + ~/.cdsapirc + pygrib; GDAL here
has no GRIB/netCDF driver):
  docker compose run --rm mintpy python workflows/fetch_rainfall.py --test
  docker compose run --rm mintpy python workflows/fetch_rainfall.py --start 2025-04-01 --end 2025-10-31
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import json

import numpy as np
from osgeo import gdal

gdal.UseExceptions()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
AOI = PROJECT_ROOT / "ramban_aoi.geojson"
OUT_DIR = PROJECT_ROOT / "data" / "rainfall"

TEMP_HOURS = ["00:00", "06:00", "12:00", "18:00"]   # bracket the diurnal min/max


def aoi_bbox(pad: float = 0.15):
    """(N, W, S, E) bounding box of the AOI in degrees, padded for ERA5-Land's 0.1 deg grid."""
    gj = json.loads(AOI.read_text(encoding="utf-8"))
    xs, ys = [], []

    def walk(coords):
        if isinstance(coords[0], (int, float)):
            xs.append(coords[0]); ys.append(coords[1])
        else:
            for c in coords:
                walk(c)
    for feat in gj.get("features", [gj]):
        walk(feat["geometry"]["coordinates"])
    return (max(ys) + pad, min(xs) - pad, min(ys) - pad, max(xs) + pad)


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def retrieve(variables, days, times, area, out: Path) -> Path:
    """Fetch ERA5-Land `variables` for `days` at `times` as GRIB (pygrib is the only
    reader in this image; GDAL lacks GRIB/netCDF drivers)."""
    import cdsapi
    cdsapi.Client().retrieve("reanalysis-era5-land", {
        "variable": variables,
        "year": sorted({f"{d.year}" for d in days}),
        "month": sorted({f"{d.month:02d}" for d in days}),
        "day": sorted({f"{d.day:02d}" for d in days}),
        "time": times,
        "area": [round(x, 2) for x in area],   # N, W, S, E
        "data_format": "grib",
        "download_format": "unarchived",
    }, str(out))
    return out


def read_messages(grib: Path):
    """Per-message (long_name, valid_datetime, AOI-mean value), sorted by valid time.

    Use the GRIB *validity* keys, not pygrib's `.validDate`: ERA5-Land encodes each
    step against the analysis date (`dataDate`+`dataTime`, always 00:00), so `.validDate`
    mis-dates the steps. `validityDate`+`validityTime` carry the true valid timestamp —
    e.g. a day's 00:00 reading is delivered as step-24 of the previous analysis day."""
    import pygrib
    rows = []
    with pygrib.open(str(grib)) as grbs:
        for g in grbs:
            vals = np.asarray(g.values, dtype=np.float64)
            v = vals[np.isfinite(vals)]
            mean = float(np.nanmean(v)) if v.size else float("nan")
            vd, vt = int(g.validityDate), int(g.validityTime)   # YYYYMMDD, HHMM
            dt = datetime(vd // 10000, (vd // 100) % 100, vd % 100, vt // 100, vt % 100)
            rows.append((g.name, dt, mean))
    return sorted(rows, key=lambda r: r[1])


def _classify(name: str) -> str:
    n = name.lower()
    if "snowmelt" in n or "snow melt" in n:
        return "smlt"
    if "precipitation" in n:
        return "tp"
    if "temperature" in n:
        return "t2m"
    return "?"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2025-04-01")
    ap.add_argument("--end", default="2025-10-31")
    ap.add_argument("--test", action="store_true",
                    help="Fetch only the first 3 days of each variable and print the "
                         "per-message AOI-mean to verify units/accumulation before a full run.")
    ap.add_argument("--probe", action="store_true",
                    help="Report which GRIB/netCDF readers are available, then exit.")
    args = ap.parse_args()
    if args.probe:
        for mod in ("pygrib", "cfgrib", "xarray", "netCDF4"):
            try:
                __import__(mod); print(f"  {mod}: OK")
            except Exception as e:  # noqa: BLE001
                print(f"  {mod}: -- ({type(e).__name__})")
        drv = [gdal.GetDriver(i).ShortName for i in range(gdal.GetDriverCount())]
        print(f"  GDAL GRIB driver:   {'GRIB' in drv}")
        print(f"  GDAL netCDF driver: {'netCDF' in drv}")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    area = aoi_bbox()
    print(f"AOI bbox (N,W,S,E) = {tuple(round(x,3) for x in area)}")

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    # Accumulated vars (tp, smlt): day D's total lives at 00:00 UTC of D+1.
    accum_days = list(daterange(start + timedelta(days=1), end + timedelta(days=1)))
    temp_days = list(daterange(start, end))                   # instantaneous, same-day
    if args.test:
        accum_days, temp_days = accum_days[:3], temp_days[:3]

    suffix = "_test" if args.test else ""
    accum_grib = OUT_DIR / f"ramban_era5land_water{suffix}.grib"
    temp_grib = OUT_DIR / f"ramban_era5land_temp{suffix}.grib"
    retrieve(["total_precipitation", "snowmelt"], accum_days, ["00:00"], area, accum_grib)
    retrieve(["2m_temperature"], temp_days, TEMP_HOURS, area, temp_grib)

    acc_rows = read_messages(accum_grib)
    temp_rows = read_messages(temp_grib)

    if args.test:
        print("\nACCUMULATED (00:00 step holds the previous day's total; m -> mm):")
        for name, vd, val in acc_rows:
            print(f"  {_classify(name):4s} valid {vd:%Y-%m-%d %H:%M} -> {val*1000:8.3f} mm  "
                  f"(daily total for {(vd - timedelta(days=1)):%Y-%m-%d})")
        print("\nTEMPERATURE (instantaneous; K -> C):")
        for name, vd, val in temp_rows:
            print(f"  t2m  valid {vd:%Y-%m-%d %H:%M} -> {val-273.15:6.2f} C")
        print("\nIf rain/snowmelt are plausible daily mm and temps are plausible C, "
              "units + accumulation are correct.")
        return 0

    # --- accumulated -> daily rain & snowmelt (mm), mapped D+1 -> D, clamped to window
    rain: dict[date, float] = {}
    melt: dict[date, float] = {}
    for name, vd, val in acc_rows:
        d = (vd - timedelta(days=1)).date()
        if not (start <= d <= end):
            continue
        kind = _classify(name)
        if kind == "tp":
            rain[d] = val * 1000.0
        elif kind == "smlt":
            melt[d] = val * 1000.0

    # --- temperature -> daily Tmin / Tmax (C)
    tbucket: dict[date, list] = defaultdict(list)
    for name, vd, val in temp_rows:
        d = vd.date()
        if start <= d <= end:
            tbucket[d].append(val - 273.15)
    tmin = {d: min(v) for d, v in tbucket.items()}
    tmax = {d: max(v) for d, v in tbucket.items()}

    days = list(daterange(start, end))
    lines = ["date,rain_mm,snowmelt_mm,tmin_c,tmax_c"]
    for d in days:
        r = rain.get(d, float("nan"))
        s = melt.get(d, float("nan"))
        lo = tmin.get(d, float("nan"))
        hi = tmax.get(d, float("nan"))
        lines.append(f"{d.isoformat()},{r:.3f},{s:.3f},{lo:.2f},{hi:.2f}")
    csv = OUT_DIR / "ramban_era5land_daily.csv"
    csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rain_tot = float(np.nansum(list(rain.values())))
    melt_tot = float(np.nansum(list(melt.values())))
    print(f"wrote {csv}  ({len(days)} days)")
    print(f"  rain total     {rain_tot:7.0f} mm  (max day {max(rain.values()):.1f} mm)")
    print(f"  snowmelt total {melt_tot:7.0f} mm  (max day {max(melt.values()):.1f} mm)")
    print(f"  water total    {rain_tot+melt_tot:7.0f} mm  = rain + snowmelt")
    return 0


if __name__ == "__main__":
    sys.exit(main())

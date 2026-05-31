#!/usr/bin/env python
"""fetch_rainfall.py — real daily rainfall for the AOI from ERA5-Land (CDS), to
replace the mock dry/monsoon/extreme scenarios with the actual rainfall history.

ERA5-Land `total_precipitation` is ACCUMULATED from 00 UTC each day (units: m). The
correct daily total for day D is the accumulation at 00:00 UTC of day D+1. We request
the 00:00 step for every day in [start, end]+1 and difference is unnecessary — the
00:00 value already holds the previous day's full accumulation. We verify this in
--test mode before trusting it.

Runs in the MintPy image (cdsapi + ~/.cdsapirc auto-mounted + GDAL to read netCDF):
  docker compose run --rm mintpy python workflows/fetch_rainfall.py --test
  docker compose run --rm mintpy python workflows/fetch_rainfall.py --start 2025-05-01 --end 2025-10-31
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from osgeo import gdal

gdal.UseExceptions()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
AOI = PROJECT_ROOT / "ramban_aoi.geojson"
OUT_DIR = PROJECT_ROOT / "data" / "rainfall"


def aoi_bbox(pad: float = 0.15):
    """(N, W, S, E) bounding box of the AOI in degrees, padded for ERA5-Land's 0.1° grid."""
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


def retrieve(days: list[date], area, out: Path) -> Path:
    """Fetch ERA5-Land total_precipitation at 00:00 UTC for each requested day, as GRIB
    (pygrib is the only reader available in this image; GDAL lacks GRIB/netCDF drivers)."""
    import cdsapi
    years = sorted({f"{d.year}" for d in days})
    months = sorted({f"{d.month:02d}" for d in days})
    dom = sorted({f"{d.day:02d}" for d in days})
    cdsapi.Client().retrieve("reanalysis-era5-land", {
        "variable": ["total_precipitation"],
        "year": years, "month": months, "day": dom,
        "time": ["00:00"],
        "area": [round(x, 2) for x in area],   # N, W, S, E
        "data_format": "grib",
        "download_format": "unarchived",
    }, str(out))
    return out


def read_tp_mean(grib: Path):
    """Per-message AOI-mean total_precipitation. Returns [(valid_date, mm), ...] sorted
    by valid time. ERA5-Land tp is in metres; *1000 -> mm."""
    import pygrib
    rows = []
    with pygrib.open(str(grib)) as grbs:
        for g in grbs:
            vals = np.asarray(g.values, dtype=np.float64)
            v = vals[np.isfinite(vals)]
            mm = float(np.nanmean(v) * 1000.0) if v.size else float("nan")
            rows.append((g.validDate, mm))
    return sorted(rows, key=lambda r: r[0])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2025-05-01")
    ap.add_argument("--end", default="2025-10-31")
    ap.add_argument("--test", action="store_true",
                    help="Fetch only 3 days and print the per-step AOI-mean to verify "
                         "the accumulation/units before a full run.")
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
    # day D's total lives at 00:00 UTC of D+1, so request [start+1 .. end+1].
    req_days = list(daterange(start + timedelta(days=1), end + timedelta(days=1)))
    if args.test:
        req_days = req_days[:3]

    grib = OUT_DIR / ("_test.grib" if args.test else "ramban_era5land.grib")
    retrieve(req_days, area, grib)
    rows = read_tp_mean(grib)                       # [(valid_datetime, mm)] sorted

    if args.test:
        print("per-message AOI-mean total_precipitation (00:00 step holds the previous day's total):")
        for vd, mm in rows:
            print(f"  valid {vd:%Y-%m-%d %H:%M} -> {mm:8.3f} mm  "
                  f"(daily total for {(vd - timedelta(days=1)):%Y-%m-%d})")
        print("If these are plausible daily mm (0..~100), units + accumulation are correct.")
        return 0

    # CDS returns the full month x day cross-product, so clamp to the requested window.
    daily = [((vd - timedelta(days=1)).date(), mm) for vd, mm in rows]
    daily = [(d, mm) for d, mm in daily if start <= d <= end]
    csv = OUT_DIR / "ramban_era5land_daily.csv"
    csv.write_text("date,rain_mm\n" + "\n".join(f"{d.isoformat()},{mm:.3f}" for d, mm in daily),
                   encoding="utf-8")
    tot = float(np.nansum([mm for _, mm in daily]))
    print(f"wrote {csv}  ({len(daily)} days, season total {tot:.0f} mm, "
          f"max day {max(mm for _, mm in daily):.1f} mm)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

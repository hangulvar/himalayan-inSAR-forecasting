#!/usr/bin/env python
"""fetch_chirps.py — daily GAUGE-BLENDED rainfall (CHIRPS) for the AOI via Google
Earth Engine, as a gauge cross-check to ERA5-Land.

WHY: the back-test (backtest_inventory.py) exposed a TEMPORAL MISS — the model's
ERA5-Land trigger (26 Aug) did not match the documented 27 Apr / 8 May 2025 Ramban
failures. Session 9 ruled snowmelt out as the cause; the residual diagnosis is that
ERA5-Land (reanalysis) UNDER-COUNTS orographic rain bursts in this terrain (8 May =
9.3 mm in ERA5-Land vs documented heavy rain). CHIRPS blends satellite estimates with
station gauges, so it should resolve those bursts better.

CHIRPS = Climate Hazards Group InfraRed Precipitation with Stations: daily, 0.05 deg
(~5.5 km), satellite+gauge precipitation. GEE asset `UCSB-CHG/CHIRPS/DAILY`, band
`precipitation` (mm/day). We take the AOI-mean per day (same reduction as the
ERA5-Land script), so the two products are directly comparable.

OUTPUT: data/rainfall/ramban_chirps_daily.csv in the SAME schema as fetch_rainfall.py
(date,rain_mm,snowmelt_mm,tmin_c,tmax_c), so rainfall_id_threshold.py +
backtest_inventory.py consume it UNCHANGED via --csv. CHIRPS carries no snowmelt or
temperature, so those columns are MERGED from the existing ERA5-Land CSV when present
(best-available drivers — snowmelt was a chronic, not acute, signal), else snowmelt=0
and temps=NaN. Only the RAIN is swapped to the gauge product; that isolates the
variable under test.

ONE-TIME HOST SETUP (GEE auth is an interactive browser OAuth — it cannot be scripted):
  1. Register / pick a Google Cloud project with the Earth Engine API enabled
     (https://code.earthengine.google.com -> note the project id).
  2. `earthengine authenticate`   # opens a browser; writes ~/.config/earthengine/credentials
  3. Put the project id in .env:   EE_PROJECT_ID="your-gcp-project-id"
     and (for the container) the host credentials path: EE_CREDENTIALS=C:/Users/<you>/.config/earthengine/credentials
  4. earthengine-api is already in docker/environment.docker.yml -> rebuild once:
        docker compose build insar

RUN (smoke-test auth + one day FIRST, then the full season):
  docker compose run --rm insar python workflows/fetch_chirps.py --check
  docker compose run --rm insar python workflows/fetch_chirps.py --start 2025-04-01 --end 2025-10-31
(Or natively in insar_qa_env with `pip install earthengine-api` — this script does no
heavy numpy linalg, so the Windows BLAS-DLL bug class does not apply.)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

OUT_DIR = PROJECT_ROOT / "data" / "rainfall"
ERA5_CSV = OUT_DIR / "ramban_era5land_daily.csv"   # source of snowmelt/temp columns

CHIRPS_ASSET = "UCSB-CHG/CHIRPS/DAILY"
CHIRPS_BAND = "precipitation"
CHIRPS_SCALE_M = 5566                               # ~0.05 deg native resolution


def load_aoi_geometry():
    """Return the AOI as a GeoJSON geometry dict (EPSG:4326) for ee.Geometry().

    Uses config.yaml's aoi_path (one source of truth); merges multiple features
    into a GeometryCollection so the reduction covers the whole AOI.
    """
    from config import load_config
    aoi_path = load_config().aoi_path
    gj = json.loads(Path(aoi_path).read_text(encoding="utf-8"))
    feats = gj.get("features", [gj])
    geoms = [f["geometry"] for f in feats]
    if len(geoms) == 1:
        return geoms[0]
    return {"type": "GeometryCollection", "geometries": geoms}


def ee_init(project: str | None):
    """Initialize Earth Engine with the project id (arg > EE_PROJECT_ID env)."""
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except Exception:  # noqa: BLE001 — dotenv optional; env may be set already
        pass
    import ee
    proj = project or os.environ.get("EE_PROJECT_ID")
    if not proj or proj.startswith("your-"):
        raise SystemExit(
            "No Earth Engine project id. Set EE_PROJECT_ID in .env (or pass --project).\n"
            "See the header of this file for the one-time GEE setup.")
    try:
        ee.Initialize(project=proj)
    except Exception as e:  # noqa: BLE001
        raise SystemExit(
            f"ee.Initialize(project={proj!r}) failed: {e}\n"
            "Have you run `earthengine authenticate` on the host (writes "
            "~/.config/earthengine/credentials)? For the container, mount it via "
            "EE_CREDENTIALS in .env (see docker-compose.yml).")
    return ee, proj


def fetch_daily_rain(ee, aoi_geom, start: date, end: date) -> dict[date, float]:
    """AOI-mean CHIRPS precipitation (mm/day) per day in [start, end], one round-trip."""
    aoi = ee.Geometry(aoi_geom)
    col = (ee.ImageCollection(CHIRPS_ASSET)
           .filterDate(start.isoformat(), (end + timedelta(days=1)).isoformat())
           .filterBounds(aoi)
           .select(CHIRPS_BAND))

    def reduce_day(img):
        mean = img.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=aoi,
            scale=CHIRPS_SCALE_M, maxPixels=int(1e9), bestEffort=True)
        return ee.Feature(None, {
            "date": img.date().format("YYYY-MM-dd"),
            "rain_mm": mean.get(CHIRPS_BAND),
        })

    feats = col.map(reduce_day).getInfo()["features"]
    rain: dict[date, float] = {}
    for f in feats:
        p = f["properties"]
        v = p.get("rain_mm")
        if v is None:                       # fully-masked day (shouldn't happen on land)
            continue
        rain[date.fromisoformat(p["date"])] = float(v)
    return rain


def load_era5_drivers(path: Path) -> dict[date, tuple[float, float, float]]:
    """date -> (snowmelt_mm, tmin_c, tmax_c) from the ERA5-Land CSV, if present."""
    if not path.exists():
        return {}
    out = {}
    for r in csv.DictReader(path.open(encoding="utf-8")):
        d = date.fromisoformat(r["date"])

        def num(key):
            v = r.get(key)
            return float(v) if v not in (None, "", "nan") else float("nan")
        out[d] = (num("snowmelt_mm"), num("tmin_c"), num("tmax_c"))
    return out


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="2025-04-01")
    ap.add_argument("--end", default="2025-10-31")
    ap.add_argument("--project", default=None, help="GEE project id (overrides EE_PROJECT_ID).")
    ap.add_argument("--out", default=str(OUT_DIR / "ramban_chirps_daily.csv"))
    ap.add_argument("--check", action="store_true",
                    help="Smoke-test: init EE and fetch ONLY the first 3 days, print the "
                         "AOI-mean, then exit. Verifies auth + asset access before a full run.")
    args = ap.parse_args()

    ee, proj = ee_init(args.project)
    aoi_geom = load_aoi_geometry()
    print(f"EE project: {proj}")

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    if args.check:
        chk_end = min(end, start + timedelta(days=2))
        rain = fetch_daily_rain(ee, aoi_geom, start, chk_end)
        print(f"CHIRPS AOI-mean (first {len(rain)} day(s)):")
        for d in sorted(rain):
            print(f"  {d.isoformat()}  {rain[d]:7.3f} mm")
        print("If these are plausible daily mm, auth + asset access are OK -> run the full season.")
        return 0

    rain = fetch_daily_rain(ee, aoi_geom, start, end)
    if not rain:
        raise SystemExit("CHIRPS returned no data for the window — check the AOI / dates.")
    drivers = load_era5_drivers(ERA5_CSV)
    merged = bool(drivers)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.out)
    lines = ["date,rain_mm,snowmelt_mm,tmin_c,tmax_c"]
    rain_tot = 0.0
    n_rain = 0
    for d in daterange(start, end):
        r = rain.get(d, float("nan"))
        sm, lo, hi = drivers.get(d, (0.0, float("nan"), float("nan")))
        lines.append(f"{d.isoformat()},{r:.3f},{sm:.3f},{lo:.2f},{hi:.2f}")
        if r == r:                          # not NaN
            rain_tot += r
            n_rain += 1
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"wrote {out}  ({n_rain} days with CHIRPS rain)")
    print(f"  CHIRPS rain total {rain_tot:7.0f} mm  "
          f"(max day {max(rain.values()):.1f} mm on "
          f"{max(rain, key=rain.get).isoformat()})")
    print(f"  snowmelt/temperature columns: "
          f"{'merged from ' + ERA5_CSV.name if merged else 'snowmelt=0, temps=NaN (no ERA5-Land CSV)'}")
    # Quick gauge-vs-reanalysis headline if ERA5-Land rain is on hand.
    if ERA5_CSV.exists():
        era_rain = {}
        for row in csv.DictReader(ERA5_CSV.open(encoding="utf-8")):
            try:
                era_rain[date.fromisoformat(row["date"])] = float(row["rain_mm"])
            except (ValueError, KeyError):
                pass
        common = [d for d in rain if d in era_rain]
        if common:
            era_tot = sum(era_rain[d] for d in common)
            chp_tot = sum(rain[d] for d in common)
            print(f"  vs ERA5-Land over {len(common)} shared days: "
                  f"CHIRPS {chp_tot:.0f} mm vs ERA5-Land {era_tot:.0f} mm "
                  f"(ratio {chp_tot / era_tot:.2f}x)" if era_tot else "")
    print(f"  next: python workflows/rainfall_id_threshold.py --csv {out} "
          f"--threshold nwhimalaya")
    return 0


if __name__ == "__main__":
    sys.exit(main())

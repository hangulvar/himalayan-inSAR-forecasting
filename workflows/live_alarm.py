#!/usr/bin/env python
"""live_alarm.py — LIVE two-factor warning: bring the CURRENT season's rainfall up to
date and regenerate the operational alarm as-of the newest available day (the Area-6
"make it live" backlog item — replaces the manual fixed-window fetch).

One idempotent command, two stages. The two capabilities live in DIFFERENT container
images, so the script auto-detects what the current environment can do and skips the
rest — run it once in each image and the whole chain completes:

  STAGE 1 — FETCH   (needs cdsapi+pygrib -> the `mintpy` image)
    Incrementally extends data/rainfall/<aoi-slug>_era5land_daily_<year>.csv (the AOI —
    and hence the slug — comes from config.yaml) from its last complete day through
    today. Only contiguous days with actual precipitation data are appended, so
    ERA5-Land's ~5-day publication lag simply means the CSV ends a few days behind
    real time and the next run picks up from there. The base-season back-test CSV
    (<slug>_era5land_daily.csv) is NEVER touched.

  STAGE 2 — ALARM   (needs rasterio+matplotlib -> the `insar` image)
    Re-derives the season wetness m(t) (rainfall_id_threshold.py), refreshes the
    per-zone active set (per_zone_gate.py) and regenerates the operational dashboard
    as-of the newest day (operational_alarm.py), all suffixed _<year> (Ramban,
    grandfathered) or _<slug>_<year> (other AOIs) so the validated
    2025-season artifacts are preserved. Caveats: per_zone_gate's outputs are
    unsuffixed, so the per-zone panel reflects the LATEST run (re-run the 2025 chain to
    restore); the wetness proxy is normalised to the season-so-far 95th percentile, so
    early-season m(t) is provisional.

Usage (run both; each stage no-ops where it can't run or has nothing to do):
  docker compose run --rm mintpy python workflows/live_alarm.py
  docker compose run --rm insar  python workflows/live_alarm.py
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from config import load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = PROJECT_ROOT / "workflows"
RAIN_DIR = PROJECT_ROOT / "data" / "rainfall"
SLUG = load_config().aoi_slug   # per-AOI filename prefix, from config.yaml


def _have(*modules: str) -> bool:
    for m in modules:
        try:
            __import__(m)
        except Exception:  # noqa: BLE001 — any import failure means "not this image"
            return False
    return True


def last_complete_day(csv_path: Path):
    """Last date in the season CSV with real precipitation data, or None."""
    if not csv_path.exists():
        return None
    last = None
    for r in csv.DictReader(csv_path.open(encoding="utf-8")):
        if r.get("rain_mm") and r["rain_mm"].lower() != "nan":
            last = date.fromisoformat(r["date"])
    return last


# ── STAGE 1 — incremental ERA5-Land fetch ────────────────────────────────────────────

def fetch_stage(season_csv: Path, start: date, end: date) -> bool:
    """Append missing days [last+1 .. end] to the season CSV. Returns True if the CSV
    exists (possibly unchanged) afterwards."""
    from fetch_rainfall import (  # reuse — single source of truth for the CDS request
        TEMP_HOURS, aoi_bbox, daterange, read_messages, retrieve, _classify,
    )

    last = last_complete_day(season_csv)
    fetch_start = (last + timedelta(days=1)) if last else start
    if fetch_start > end:
        print(f"fetch: {season_csv.name} already current through {last} — nothing to do")
        return True

    area = aoi_bbox()
    print(f"fetch: extending {season_csv.name} {fetch_start} .. {end} "
          f"(ERA5-Land publishes ~5 days behind — the tail may be unavailable yet)")
    accum_days = list(daterange(fetch_start + timedelta(days=1), end + timedelta(days=1)))
    temp_days = list(daterange(fetch_start, end))
    water_grib = RAIN_DIR / "live_water.grib"
    temp_grib = RAIN_DIR / "live_temp.grib"
    try:
        retrieve(["total_precipitation", "snowmelt"], accum_days, ["00:00"], area, water_grib)
        retrieve(["2m_temperature"], temp_days, TEMP_HOURS, area, temp_grib)
    except Exception as e:  # noqa: BLE001 — usually "no data yet" for a too-recent window
        print(f"fetch: CDS returned no data for the window ({type(e).__name__}: {e})\n"
              f"       -> nothing new yet; re-run later. CSV unchanged.")
        return season_csv.exists()

    rain, melt = {}, {}
    for name, vd, val in read_messages(water_grib):
        d = (vd - timedelta(days=1)).date()          # accumulated: 00:00 of D+1 holds day D
        if fetch_start <= d <= end:
            (rain if _classify(name) == "tp" else melt)[d] = val * 1000.0
    tbucket: dict[date, list] = {}
    for name, vd, val in read_messages(temp_grib):
        d = vd.date()
        if fetch_start <= d <= end:
            tbucket.setdefault(d, []).append(val - 273.15)

    # Append only the CONTIGUOUS run of complete days (gate on tp) — no holes, so the
    # next run resumes cleanly from the new last line.
    new_lines = []
    d = fetch_start
    while d <= end and d in rain:
        s = melt.get(d, float("nan"))
        ts = tbucket.get(d, [])
        lo = min(ts) if ts else float("nan")
        hi = max(ts) if ts else float("nan")
        new_lines.append(f"{d.isoformat()},{rain[d]:.3f},{s:.3f},{lo:.2f},{hi:.2f}")
        d += timedelta(days=1)
    if not new_lines:
        print("fetch: no complete new days available yet — CSV unchanged.")
        return season_csv.exists()

    RAIN_DIR.mkdir(parents=True, exist_ok=True)
    if season_csv.exists():
        body = season_csv.read_text(encoding="utf-8").rstrip("\n")
        season_csv.write_text(body + "\n" + "\n".join(new_lines) + "\n", encoding="utf-8")
    else:
        season_csv.write_text("date,rain_mm,snowmelt_mm,tmin_c,tmax_c\n"
                              + "\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"fetch: +{len(new_lines)} day(s) -> {season_csv.name} now ends "
          f"{new_lines[-1].split(',')[0]}")
    return True


# ── STAGE 2 — regenerate the alarm chain as-of the newest day ────────────────────────

def run(script: str, *args: str) -> None:
    cmd = [sys.executable, str(WORKFLOWS / script), *args]
    print(f"\n=== {script} {' '.join(args)}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)


def alarm_stage(season_csv: Path, suffix: str, threshold: str, start: date) -> None:
    as_of = last_complete_day(season_csv)
    if as_of is None:
        raise SystemExit(f"alarm: {season_csv} missing/empty — run the fetch stage first "
                         f"(mintpy image).")
    wetness_csv = RAIN_DIR / f"{SLUG}_wetness_daily{suffix}.csv"
    run("rainfall_id_threshold.py", "--csv", str(season_csv),
        "--threshold", threshold, "--out-suffix", suffix)
    run("per_zone_gate.py", "--csv", str(wetness_csv),
        "--threshold", threshold, "--as-of", as_of.isoformat())
    # Sub-daily IMERG burst check (imerg_gate.py, experimental §55) — refreshed BEFORE the
    # dashboard so its card is current, but NON-FATAL: GEE down / earthengine-api absent /
    # network trouble must never break the validated daily alarm chain (the card just goes
    # stale or stays absent).
    try:
        run("imerg_gate.py", "--threshold", threshold, "--start", start.isoformat())
    except Exception as e:  # noqa: BLE001 — any failure here is a skipped extra, not an error
        print(f"imerg gate SKIPPED ({type(e).__name__}: {e}) — dashboard renders without/with "
              f"a stale sub-daily card")
    run("operational_alarm.py", "--csv", str(season_csv),
        "--threshold", threshold, "--as-of", as_of.isoformat(), "--out-suffix", suffix)
    print(f"\nLIVE alarm regenerated as-of {as_of} -> "
          f"data/alerts{load_config().data_suffix}/mosaic_asc/"
          f"operational_alarm_dashboard{suffix}.html")


def main() -> int:
    today = datetime.now(timezone.utc).date()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=f"{today.year}-04-01",
                    help="Season start (default: 1 April of the current year).")
    ap.add_argument("--end", default=today.isoformat(),
                    help="Fetch through this day (default: today, UTC).")
    ap.add_argument("--threshold", default="nwhimalaya",
                    help="I-D curve id, passed to every step (default: nwhimalaya).")
    args = ap.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    # Ramban keeps its original "_<year>" artifact names (grandfathered — the 2026
    # season files already exist under them); any other AOI gets "_<slug>_<year>" so
    # the UNPREFIXED outputs keyed by this suffix (id_threshold_report, the alarm
    # report/dashboard) cannot collide across sites in the shared data/ dir.
    suffix = f"_{start.year}" if SLUG == "ramban" else f"_{SLUG}_{start.year}"
    season_csv = RAIN_DIR / f"{SLUG}_era5land_daily{suffix}.csv"

    can_fetch = _have("cdsapi", "pygrib")
    can_alarm = _have("rasterio", "matplotlib")
    print(f"live_alarm: season {start.year} (window {start} .. {end})  "
          f"fetch={'YES' if can_fetch else 'no (needs mintpy image)'}  "
          f"alarm={'YES' if can_alarm else 'no (needs insar image)'}")
    if not (can_fetch or can_alarm):
        raise SystemExit("Neither stage can run here — use the mintpy image (fetch) "
                         "and the insar image (alarm).")

    if can_fetch:
        fetch_stage(season_csv, start, end)
    if can_alarm:
        alarm_stage(season_csv, suffix, args.threshold, start)
    return 0


if __name__ == "__main__":
    sys.exit(main())

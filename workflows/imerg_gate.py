#!/usr/bin/env python
"""imerg_gate.py — the SUB-DAILY rainfall gate (GPM IMERG, half-hourly) for the live season:
the §12c fix, productized from the one-off §12g event test (fetch_gpm_imerg.py).

WHY: the operational gate runs on DAILY AOI-MEAN ERA5-Land, which (a) dilutes localized
convective cloudbursts (the verified 20 Apr 2025 disaster read LOW on daily AOI-mean rain but
E=2.25 on sub-daily IMERG, §12g; the 8 Jul 2026 Himkoti slide read only WATCH, §52) and
(b) publishes ~5-6 days behind real time. GPM IMERG V07 is HALF-HOURLY and, via GEE, only
~1 day behind real time (probed 2026-07-18: newest step 2026-07-17 08:30 UTC) — so this gate
is both SHARPER (30-min bursts) and FRESHER than the daily gate.

WHAT IT PRODUCES, per AOI + season (same suffix rule as live_alarm.py):
  {slug}_imerg_halfhourly{sfx}.csv — the raw half-hourly AOI-mean series (incremental cache:
      each run appends only the missing tail; a re-run is one cheap bounded GEE call).
  {slug}_imerg_daily_E{sfx}.csv    — per day: the PEAK sub-daily exceedance E vs the regional
      I-D curve over trailing windows of D = 0.5..24 h ENDING that day (windows cross
      midnight, so an overnight burst is not split), the best duration, burst depth, level.
  imerg_gate_summary{sfx}.json     — season summary consumed by operational_alarm.py's
      "sub-daily burst check" card.

HONEST FRAMING (also printed on the dashboard card): this is an EXPERIMENTAL SECOND OPINION.
The validated operational alarm remains the ERA5-Land daily gate (§16-§17 lineage); the IMERG
E grades the same regional curve at short durations but has no back-tested operating points of
its own yet. IMERG is ~0.1 deg (~11 km): it resolves 30-minute intensity, not slope-scale rain
(a small AOI averages over ~1-4 pixels). Days with an incomplete half-hourly record — always
including the newest, still-arriving day — are flagged provisional (their E can only rise).

Needs earthengine-api + GEE auth (both already wired for the insar image via .env):
  docker compose run --rm insar python workflows/imerg_gate.py
live_alarm.py's alarm stage runs this automatically but NON-FATALLY (ops never break if GEE
is down); it is skipped quietly wherever earthengine-api is absent.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

from config import load_config  # noqa: E402
from rainfall_id_threshold import THRESHOLDS, threshold_intensity  # noqa: E402

RAIN_DIR = PROJECT_ROOT / "data" / "rainfall"
SLUG = load_config().aoi_slug

IMERG_ASSET = "NASA/GPM_L3/IMERG_V07"
IMERG_BAND = "precipitation"          # mm/hr, half-hourly rate
IMERG_SCALE_M = 11132                 # ~0.1 deg native
STEP_H = 0.5
DUR_H = [0.5, 1, 3, 6, 12, 24]        # trailing-window durations screened per day
STEPS_PER_DAY = 48
CHUNK_DAYS = 15                       # one GEE getInfo per chunk (bounded payloads)
LEVELS = ["DORMANT", "WATCH", "ALERT"]


def season_suffix(year: int) -> str:
    """Same rule as live_alarm.py: ramban grandfathered on _<year>, others _<slug>_<year>."""
    return f"_{year}" if SLUG == "ramban" else f"_{SLUG}_{year}"


# ── incremental half-hourly fetch (GEE) ──────────────────────────────────────────────

def read_series(cache: Path) -> list[tuple[datetime, float]]:
    if not cache.exists():
        return []
    rows = list(csv.DictReader(cache.open(encoding="utf-8")))
    return [(datetime.strptime(r["t"], "%Y-%m-%d %H:%M:%S"), float(r["r"])) for r in rows]


def append_series(cache: Path, new: list[tuple[datetime, float]]) -> None:
    RAIN_DIR.mkdir(parents=True, exist_ok=True)
    fresh = not cache.exists()
    with cache.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if fresh:
            w.writerow(["t", "r"])
        for t, r in new:
            w.writerow([t.strftime("%Y-%m-%d %H:%M:%S"), f"{r:.4f}"])


def fetch_incremental(cache: Path, start: date, end: date, project: str | None) -> list:
    """Extend the cached half-hourly series through `end` (exclusive of nothing — GEE just
    returns whatever exists; IMERG's ~1-day latency bounds the tail). Returns the full series."""
    from fetch_chirps import ee_init, load_aoi_geometry   # reuse — one GEE init, one AOI source
    series = read_series(cache)
    fetch_from = (series[-1][0] + timedelta(minutes=30)) if series else \
        datetime(start.year, start.month, start.day)
    fetch_to = datetime(end.year, end.month, end.day) + timedelta(days=1)
    if fetch_from >= fetch_to:
        print(f"imerg fetch: {cache.name} already current through {series[-1][0]} — nothing to do")
        return series

    ee, proj = ee_init(project)
    aoi = ee.Geometry(load_aoi_geometry())
    col_all = ee.ImageCollection(IMERG_ASSET).select(IMERG_BAND)

    def reduce_step(img):
        mean = img.reduceRegion(ee.Reducer.mean(), aoi, IMERG_SCALE_M,
                                maxPixels=int(1e8), bestEffort=True)
        return ee.Feature(None, {"t": img.date().format("YYYY-MM-dd HH:mm:ss"),
                                 "r": mean.get(IMERG_BAND)})

    print(f"imerg fetch: extending {cache.name} {fetch_from} .. {fetch_to} (EE project {proj})")
    added = []
    lo = fetch_from
    while lo < fetch_to:
        hi = min(lo + timedelta(days=CHUNK_DAYS), fetch_to)
        feats = (col_all.filterDate(lo.strftime("%Y-%m-%dT%H:%M:%S"),
                                    hi.strftime("%Y-%m-%dT%H:%M:%S"))
                 .map(reduce_step).getInfo()["features"])
        chunk = []
        for f in feats:
            p = f["properties"]
            if p.get("r") is not None:
                chunk.append((datetime.strptime(p["t"], "%Y-%m-%d %H:%M:%S"), float(p["r"])))
        chunk.sort(key=lambda x: x[0])
        added += chunk
        lo = hi
    if added:
        append_series(cache, added)
        print(f"imerg fetch: +{len(added)} half-hourly steps -> now ends {added[-1][0]}")
    else:
        print("imerg fetch: no new steps available yet (IMERG latency) — cache unchanged")
    return series + added


# ── the sub-daily daily-E computation (pure numpy — unit-tested) ─────────────────────

def daily_subdaily_E(series: list[tuple[datetime, float]], a: float, b: float) -> list[dict]:
    """Per calendar day: the peak exceedance E = max_D peakI(D)/thr(D) over trailing windows
    of D hours ENDING in that day (the continuous cumsum spans days, so overnight bursts are
    not split at midnight). Days with fewer than STEPS_PER_DAY steps are flagged provisional
    (their E is a lower bound — more data can only raise it)."""
    if not series:
        return []
    times = [t for t, _ in series]
    depth = np.array([r * STEP_H for _, r in series])           # mm per 30-min step
    csum = np.insert(np.cumsum(depth), 0, 0.0)
    day_of = np.array([t.date() for t in times])
    out = []
    for d in sorted(set(day_of)):
        idx = np.where(day_of == d)[0]
        best_E, best = 0.0, None
        for D in DUR_H:
            k = max(1, int(round(D / STEP_H)))
            thr_I = float(threshold_intensity(np.array([D]), a, b)[0])
            for i in idx:                                       # window ENDS at step i
                j0 = max(0, i + 1 - k)
                accum = float(csum[i + 1] - csum[j0])
                E = (accum / D) / thr_I
                if E > best_E:
                    best_E = E
                    best = {"duration_h": D, "burst_mm": round(accum, 1),
                            "peak_mmph": round(accum / D, 2),
                            "window_end": times[i].strftime("%Y-%m-%d %H:%M")}
        lvl = "ALERT" if best_E >= 2.0 else "WATCH" if best_E >= 1.0 else "DORMANT"
        out.append({"date": d.isoformat(), "n_steps": int(idx.size),
                    "provisional": bool(idx.size < STEPS_PER_DAY),
                    "total_mm": round(float(depth[idx].sum()), 1),
                    "max_E": round(best_E, 2), "level": lvl, **(best or {})})
    return out


# ── outputs ──────────────────────────────────────────────────────────────────────────

def write_outputs(days: list[dict], sfx: str, thr_id: str, a: float, b: float) -> Path:
    daily_csv = RAIN_DIR / f"{SLUG}_imerg_daily_E{sfx}.csv"
    cols = ["date", "n_steps", "provisional", "total_mm", "max_E", "level",
            "duration_h", "burst_mm", "peak_mmph", "window_end"]
    with daily_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for d in days:
            w.writerow({c: d.get(c, "") for c in cols})

    complete = [d for d in days if not d["provisional"]]
    counts = {lv: sum(1 for d in days if d["level"] == lv) for lv in LEVELS}
    top = max(days, key=lambda d: d["max_E"], default=None)
    latest = days[-1] if days else None
    summary = {
        "slug": SLUG, "asset": IMERG_ASSET,
        "threshold_id": thr_id,
        "threshold": f"{THRESHOLDS[thr_id]['label']} I={a}*D^-{b}",
        "durations_h": DUR_H,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "season": {"start": days[0]["date"], "end": days[-1]["date"],
                   "days": len(days), "complete_days": len(complete)},
        "level_counts": counts,
        "latest": latest, "top_burst_day": top,
        "alert_days": [d["date"] for d in days if d["level"] == "ALERT"],
    }
    (RAIN_DIR / f"imerg_gate_summary{sfx}.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return daily_csv


def main() -> int:
    today = datetime.now(timezone.utc).date()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threshold", choices=sorted(THRESHOLDS), default="nwhimalaya")
    ap.add_argument("--start", default=f"{today.year}-04-01",
                    help="Season start (default 1 April, matching live_alarm).")
    ap.add_argument("--end", default=today.isoformat(),
                    help="Fetch through this day (default today UTC; IMERG lag bounds the tail).")
    ap.add_argument("--project", default=None, help="GEE project id (default: EE_PROJECT_ID).")
    args = ap.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    thr = THRESHOLDS[args.threshold]
    a, b = thr["a"], thr["b"]
    sfx = season_suffix(start.year)
    cache = RAIN_DIR / f"{SLUG}_imerg_halfhourly{sfx}.csv"

    series = fetch_incremental(cache, start, end, args.project)
    if not series:
        raise SystemExit("imerg_gate: no IMERG data returned — check GEE auth / window.")
    days = daily_subdaily_E(series, a, b)
    daily_csv = write_outputs(days, sfx, args.threshold, a, b)

    counts = {lv: sum(1 for d in days if d["level"] == lv) for lv in LEVELS}
    latest, top = days[-1], max(days, key=lambda d: d["max_E"])
    print(f"imerg gate ({thr['label']}): {days[0]['date']} .. {latest['date']} "
          f"({len(days)} days; newest {'PROVISIONAL' if latest['provisional'] else 'complete'})")
    print(f"  sub-daily levels: DORMANT {counts['DORMANT']} · WATCH {counts['WATCH']} · "
          f"ALERT {counts['ALERT']}")
    print(f"  latest day {latest['date']}: E={latest['max_E']} ({latest['level']})"
          + (f"  best {latest.get('duration_h')}h burst {latest.get('burst_mm')} mm"
             if latest.get("duration_h") else ""))
    print(f"  top burst day {top['date']}: E={top['max_E']} ({top['level']}) — "
          f"{top.get('burst_mm')} mm in {top.get('duration_h')} h ending {top.get('window_end')}")
    print(f"  -> {daily_csv.name} , imerg_gate_summary{sfx}.json , {cache.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

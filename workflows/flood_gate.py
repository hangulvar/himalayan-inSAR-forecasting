#!/usr/bin/env python
"""flood_gate.py — F1 of the Flash-Flood Expansion Plan (docs/references/
FLOOD_EXPANSION_PLAN_2026-07-28.md): the flood-TRIGGER arm.

WHAT IT ADDS over the existing burst gate: `imerg_gate.py` grades half-hourly rainfall averaged
over the whole AOI BOX. Flash-flood response at a point is governed by rain over the CATCHMENT
draining to it — a different polygon, usually higher and further away than the AOI (the reason
the plan needed a "hydrological support domain" at all). This arm grades each F0 catchment on
its own rainfall, over a trailing window MATCHED to that catchment's response time instead of a
fixed menu of durations.

WHAT IT IS NOT: an inundation model. It publishes a staged LEVEL per catchment
(FLOOD-DORMANT / FLOOD-WATCH / FLOOD-ALERT) and the exceedance E_f behind it. It never
publishes a water depth, a discharge, or an inundated area — the plan §1 says plainly that
those need gauges and bathymetry we do not have, and a number we cannot defend is exactly the
failure mode §65 exists to prevent.

THRESHOLDS ARE INHERITED, NOT FLOOD-CALIBRATED. FLOOD_WATCH_K / FLOOD_ALERT_K are IMPORTED
from imerg_gate (the §64-adopted burst constants), so the inheritance is literal in the code
and cannot drift into a look-alike copy. There is no flood ground truth yet, so this arm ships
EXPERIMENTAL — the same posture the burst arm held from §55 until §63/§64 earned its operating
points, and the dashboard card says so.

THE GUARD (§65 rule): a catchment whose rainfall series is empty, all-void, or too short to
cover its own response window is ABORTED with a written reason. It is never graded DORMANT —
"no data" and "no rain" are different answers, and conflating them is how a void gets published
as a result.

Inputs:  data/flood/flood_domain_{slug}.json (F0)  +  GPM IMERG half-hourly via GEE.
Outputs: data/flood/flood_catchment_E{sfx}.csv, data/flood/flood_gate_summary{sfx}.json,
         per-catchment half-hourly caches under data/flood/_rain/.

  docker compose run --rm insar python workflows/flood_gate.py
  docker compose run --rm -e INSAR_CONFIG=config/vaishnodevi.yaml insar python workflows/flood_gate.py

NOTE (deliberate deviation, flagged to the user 2026-07-28): the plan's F1 bullet mentions a
non-fatal hook in live_alarm.py, but plan §5 lists the sanctioned touch-points in existing
files as EXACTLY two — operational_alarm.py and build_3d_dashboard.py — and says "the ONLY
ones". The stricter constraint wins: this script is standalone-runnable and nothing calls it
automatically. Wiring it into live_alarm.py is a one-line addition awaiting the user's call.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

from config import load_config  # noqa: E402
from flood_domain import load_flood_config  # noqa: E402
# Inherited grading constants + fetch plumbing — imported so the inheritance is literal.
from imerg_gate import (  # noqa: E402
    BURST_ALERT_K as FLOOD_ALERT_K,
    BURST_WATCH_K as FLOOD_WATCH_K,
    IMERG_ASSET, IMERG_BAND, IMERG_SCALE_M, STEP_H, STEPS_PER_DAY,
    append_series, read_series,
)
from rainfall_id_threshold import THRESHOLDS, threshold_intensity  # noqa: E402

FLOOD_DIR = PROJECT_ROOT / "data" / "flood"
RAIN_CACHE = FLOOD_DIR / "_rain"
LEVELS = ["FLOOD-DORMANT", "FLOOD-WATCH", "FLOOD-ALERT"]
# Trailing windows this arm may choose from. Bounded at 6 h by the plan: beyond that the event
# is a sustained wet spell, which is the validated DAILY arm's job, not a flash-flood window.
DUR_CHOICES = [0.5, 1.0, 3.0, 6.0]
MIN_STEPS_FOR_WINDOW = 2          # a window graded on one step is noise, not a burst


# ── window matching ──────────────────────────────────────────────────────────────────
def match_durations(tc_hours: float | None, choices: list[float] = None) -> list[float]:
    """The trailing windows to grade a catchment on: every offered window at least as long as
    its time of concentration (always at least one).

    t_c sets where the range STARTS, it does not select a single window. Rain lasting less than
    t_c has not yet produced the catchment's peak flow, so shorter windows under-read the flood
    signal — but longer ones are not noise, they are the larger-volume events, and a flash flood
    is perfectly capable of arriving on the back of a 6-hour soaking.

    THIS WAS THE F1 GATE FAILURE (§71). Grading a SINGLE t_c-matched window meant every one of
    our 22 catchments (t_c 0.07-0.12 h) was screened at 0.5 h only — structurally blind to
    longer accumulations. On the 22 Jul 2026 fatal event, whose signal sits at D = 6 h, the arm
    read FLOOD-WATCH where the validated AOI-mean arm read ALERT: the new arm DOWNGRADED a
    fatal day. Screening the range and taking the max fixes that, and has a second benefit —
    E_f becomes the same max-over-durations statistic imerg_gate's k was calibrated on, so the
    inherited threshold is no longer being applied across a change of statistic.
    """
    # `choices=[]` deliberately falls back to the module default rather than returning an empty
    # set: a caller computing an empty duration list must not silently produce a catchment that
    # is graded on nothing (which would read as DORMANT). Pinned by test.
    ch = sorted(choices or DUR_CHOICES)
    if tc_hours is None or not np.isfinite(tc_hours) or tc_hours <= 0:
        return list(ch)                       # unknown response time -> screen everything
    out = [d for d in ch if d >= tc_hours]
    return out or [ch[-1]]                    # t_c beyond the cap -> the longest window


# ── health guard (the §65 abort-don't-fabricate rule) ────────────────────────────────
def series_health(series, duration_h: float) -> tuple[bool, str | None, dict]:
    """(ok, reason, stats) for a catchment's half-hourly series.

    Refuses: an empty series; one that is entirely non-finite; one whose finite values are all
    negative (an IMERG fill-value read); and one shorter than the trailing window it would be
    graded on. A refusal is an ABORT with a reason — never a DORMANT.
    """
    vals = np.array([r for _, r in series], dtype=float) if series else np.array([])
    finite = np.isfinite(vals)
    stats = {"n_steps": int(vals.size), "n_finite": int(finite.sum()),
             "pct_finite": round(100.0 * finite.sum() / vals.size, 1) if vals.size else 0.0,
             "max_rate_mmph": round(float(np.nanmax(vals)), 3) if finite.any() else None}
    need = max(MIN_STEPS_FOR_WINDOW, int(round(duration_h / STEP_H)))
    if vals.size == 0:
        return False, "no rainfall steps returned for this catchment", stats
    if not finite.any():
        return False, f"all {vals.size} rainfall steps are non-finite (void, not dry)", stats
    if float(np.nanmax(vals[finite])) < 0:
        return False, "every finite value is negative — fill values, not rainfall", stats
    if vals.size < need:
        return False, (f"series has {vals.size} steps but the {duration_h} h window needs "
                       f"{need} — too short to grade"), stats
    return True, None, stats


# ── the graded series (pure numpy — hermetically unit-tested) ────────────────────────
def catchment_daily_E(series, a: float, b: float, durations_h) -> list[dict]:
    """Per calendar day: the peak exceedance E_f over trailing windows ENDING that day, screened
    across `durations_h` and graded against the regional I-D curve. The winning duration is
    recorded per day, so the report says WHICH window carried the signal.

    This is imerg_gate.daily_subdaily_E's math over a catchment-matched duration RANGE instead
    of the fixed AOI menu. It is not a copy by convenience: the shared science —
    `threshold_intensity` — is imported, and tests/test_flood_gate.py PINS this function against
    imerg_gate.daily_subdaily_E (they must agree exactly when run over imerg_gate's own menu),
    so the two cannot silently diverge.

    Windows cross midnight, so an overnight burst is credited to the day it ends in rather
    than split at 00:00 — the same invariant the daily-E series already honours.
    """
    if not series:
        return []
    durs = [float(d) for d in (durations_h if isinstance(durations_h, (list, tuple))
                               else [durations_h])]
    times = [t for t, _ in series]
    rates = np.array([r for _, r in series], dtype=float)
    depth = np.nan_to_num(rates, nan=0.0) * STEP_H            # mm per 30-min step
    csum = np.insert(np.cumsum(depth), 0, 0.0)
    day_of = np.array([t.date() for t in times])
    out = []
    for d in sorted(set(day_of)):
        idx = np.where(day_of == d)[0]
        best_E, best = 0.0, None
        for D in durs:
            k = max(1, int(round(D / STEP_H)))
            thr_I = float(threshold_intensity(np.array([D]), a, b)[0])
            for i in idx:                                      # window ENDS at step i
                j0 = max(0, i + 1 - k)
                accum = float(csum[i + 1] - csum[j0])
                E = (accum / D) / thr_I
                if E > best_E:
                    best_E = E
                    best = {"duration_h": D, "burst_mm": round(accum, 1),
                            "peak_mmph": round(accum / D, 2),
                            "window_end": times[i].strftime("%Y-%m-%d %H:%M")}
        lvl = ("FLOOD-ALERT" if best_E >= FLOOD_ALERT_K else
               "FLOOD-WATCH" if best_E >= FLOOD_WATCH_K else "FLOOD-DORMANT")
        out.append({"date": d.isoformat(), "n_steps": int(idx.size),
                    "provisional": bool(idx.size < STEPS_PER_DAY),
                    "E_f": round(best_E, 2), "level": lvl,
                    **(best or {"duration_h": durs[0], "burst_mm": 0.0, "peak_mmph": 0.0,
                                "window_end": None})})
    return out


def sampling_scale_m(bbox_lonlat, native_m: float = IMERG_SCALE_M,
                     floor_m: float = 500.0) -> float:
    """The scale to reduce IMERG at over a catchment bbox.

    WHY THIS IS NOT JUST `native_m` (measured 2026-07-28, and it cost three catchments):
    Earth Engine's reduceRegion returns **null** when a region smaller than `scale` happens to
    contain no pixel CENTRE. A Regime-A catchment is ~0.007 deg across against IMERG's 0.1 deg
    cell, so whether a box catches a centre is a lottery on position — three of Ramban's eight
    catchments returned an empty series at the native scale while two boxes of the SAME SIZE
    returned data. Probed directly: those three yield null at 11132 m and a real value at
    2000/500 m.

    Sampling finer makes the reducer place sample points inside the region and resample the
    same coarse pixels onto them. It adds NO information — the underlying observation is still
    an ~11 km average, and every product this arm writes says so (`imerg_pixels`, the card's
    resolution note). It only stops a measurable catchment from being reported as unmeasurable.
    """
    lo1, la1, lo2, la2 = bbox_lonlat
    lat = math.radians((la1 + la2) / 2.0)
    span_m = min(abs(lo2 - lo1) * 111320.0 * math.cos(lat), abs(la2 - la1) * 110540.0)
    if span_m >= 2 * native_m:          # comfortably larger than a pixel: nothing to fix
        return float(native_m)
    return float(max(floor_m, min(native_m, span_m / 4.0)))


def imerg_pixels_spanned(bbox_lonlat: list[float]) -> int:
    """How many ~0.1 deg IMERG cells the catchment bbox covers. Printed on every product: at
    Regime-A sizes this is often 1, which means the 'catchment mean' is really one satellite
    pixel — an honest resolution note, the same one §55/§58-1a made for the AOI-mean arm."""
    if not bbox_lonlat:
        return 0
    lo1, la1, lo2, la2 = bbox_lonlat
    return max(1, int(round((abs(lo2 - lo1) / 0.1) + 0.5)) * int(round((abs(la2 - la1) / 0.1) + 0.5)))


# ── rainfall fetch (GEE; one incremental cache per catchment) ────────────────────────
def fetch_catchment_series(cache: Path, bbox_lonlat, start: date, end: date, project=None):
    """Extend this catchment's cached half-hourly IMERG mean through `end`. Mirrors
    imerg_gate.fetch_incremental (same asset/band/scale/chunking) but reduces over the
    CATCHMENT bbox rather than the AOI."""
    from fetch_chirps import ee_init
    series = read_series(cache)
    fetch_from = (series[-1][0] + timedelta(minutes=30)) if series else \
        datetime(start.year, start.month, start.day)
    fetch_to = datetime(end.year, end.month, end.day) + timedelta(days=1)
    if fetch_from >= fetch_to:
        return series
    ee, _proj = ee_init(project)
    lo1, la1, lo2, la2 = bbox_lonlat
    geom = ee.Geometry.Rectangle([lo1, la1, lo2, la2])
    scale = sampling_scale_m(bbox_lonlat)
    col = ee.ImageCollection(IMERG_ASSET).select(IMERG_BAND)

    def reduce_step(img):
        mean = img.reduceRegion(ee.Reducer.mean(), geom, scale,
                                maxPixels=int(1e8), bestEffort=True)
        return ee.Feature(None, {"t": img.date().format("YYYY-MM-dd HH:mm:ss"),
                                 "r": mean.get(IMERG_BAND)})

    added, lo = [], fetch_from
    while lo < fetch_to:
        hi = min(lo + timedelta(days=15), fetch_to)
        feats = (col.filterDate(lo.strftime("%Y-%m-%dT%H:%M:%S"),
                                hi.strftime("%Y-%m-%dT%H:%M:%S"))
                 .map(reduce_step).getInfo()["features"])
        chunk = [(datetime.strptime(f["properties"]["t"], "%Y-%m-%d %H:%M:%S"),
                  float(f["properties"]["r"]))
                 for f in feats if f["properties"].get("r") is not None]
        chunk.sort(key=lambda x: x[0])
        added += chunk
        lo = hi
    if added:
        RAIN_CACHE.mkdir(parents=True, exist_ok=True)
        append_series(cache, added)
    return series + added


# ── outputs ──────────────────────────────────────────────────────────────────────────
def build_summary(slug: str, per_catchment: list[dict], thr_id: str, a: float, b: float,
                  season: dict) -> dict:
    graded = [c for c in per_catchment if not c.get("aborted")]
    # CURRENT state = the newest day, per catchment. This is what the dashboard leads with.
    # Counting catchments by their SEASON PEAK instead would report "every catchment on ALERT"
    # for any site that saw one bad half-hour in four months — measured 2026-07-28: all 22
    # catchments peak at ALERT while ~84% of their individual days are DORMANT. Peak and
    # present are different questions and are reported as different fields.
    latest_rows = [{"catchment": c["catchment"], "zone": c["zone"], **c["latest"]}
                   for c in graded if c.get("latest")]
    worst_latest = max(latest_rows, key=lambda r: r["E_f"], default=None)
    counts = {lv: 0 for lv in LEVELS}
    for r in latest_rows:
        counts[r["level"]] = counts.get(r["level"], 0) + 1
    season_peak = max(graded, key=lambda c: c["E_f"], default=None)
    # Season texture: how many ALERT-grade days each catchment actually had.
    alert_days = {c["catchment"]: sum(1 for d in c.get("days", [])
                                      if d["level"] == "FLOOD-ALERT") for c in graded}
    return {
        "slug": slug, "experimental": True,
        "aborted": not graded,
        "abort_reason": (None if graded else
                         "no catchment had a gradeable rainfall series — see per_catchment"),
        "asset": IMERG_ASSET,
        "threshold_id": thr_id, "threshold": f"{THRESHOLDS[thr_id]['label']} I={a}*D^-{b}",
        "flood_watch_k": FLOOD_WATCH_K, "flood_alert_k": FLOOD_ALERT_K,
        "thresholds_inherited_from": "imerg_gate.BURST_WATCH_K / BURST_ALERT_K (§64) — "
                                     "NOT flood-calibrated; no flood ground truth exists yet",
        "durations_h": DUR_CHOICES,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "season": season,
        "n_catchments": len(per_catchment), "n_staged": len(graded),
        "n_aborted": len(per_catchment) - len(graded),
        # CURRENT state (the newest day) — what the card headlines.
        "level_counts": counts,
        "latest": worst_latest,
        "latest_date": worst_latest["date"] if worst_latest else None,
        # SEASON PEAK (the worst half-hour anywhere this season) — context, not current state.
        "season_peak": ({"catchment": season_peak["catchment"], "zone": season_peak["zone"],
                         "level": season_peak["level"], "E_f": season_peak["E_f"],
                         "date": season_peak["date"], "duration_h": season_peak["duration_h"],
                         "burst_mm": season_peak["burst_mm"],
                         "area_km2": season_peak["area_km2"],
                         "tc_hours": season_peak["tc_hours"],
                         "imerg_pixels": season_peak["imerg_pixels"]} if season_peak else None),
        "alert_days_per_catchment": alert_days,
        "catchments": per_catchment,
    }


def write_outputs(summary: dict, sfx: str) -> Path:
    FLOOD_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = FLOOD_DIR / f"flood_catchment_E{sfx}.csv"
    cols = ["catchment", "zone", "area_km2", "tc_hours", "duration_h", "imerg_pixels",
            "date", "E_f", "level", "burst_mm", "peak_mmph", "window_end", "provisional",
            "aborted", "abort_reason"]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for c in summary["catchments"]:
            w.writerow({k: c.get(k, "") for k in cols})
    (FLOOD_DIR / f"flood_gate_summary{sfx}.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return csv_path


def event_flood_level(slug: str, event_iso: str) -> dict | None:
    """This arm's verdict on ONE day, for the Tier-3c temporal-skill table (§60 3c/§63).

    Returns the WORST catchment's grade that day plus how many catchments reached FLOOD-ALERT,
    or None when this arm has no season record covering the day. None means "not measured" and
    must render as an EMPTY cell — never as DORMANT, which would read as "the flood arm saw the
    day and found it quiet" (the §70 mistake, in a different costume).

    Lives here rather than in imerg_calibration so the flood logic stays inside the flood
    module; the calibration script only imports and calls it.
    """
    year = int(event_iso[:4])
    f = FLOOD_DIR / f"flood_gate_summary{season_suffix(slug, year)}.json"
    if not f.exists():
        return None
    try:
        s = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a corrupt summary is "not measured", not a crash
        return None
    rows = []
    for c in s.get("catchments", []):
        if c.get("aborted"):
            continue
        for d in c.get("days", []):
            if d["date"] == event_iso:
                rows.append((c["catchment"], d["E_f"], d["level"], d.get("duration_h")))
    if not rows:
        return None
    name, e_f, lvl, dur = max(rows, key=lambda r: r[1])
    return {"catchment": name, "E_f": e_f, "level": lvl, "duration_h": dur,
            "n_catchments": len(rows),
            "n_alert": sum(1 for r in rows if r[2] == "FLOOD-ALERT")}


def season_suffix(slug: str, year: int) -> str:
    """The project-wide suffix rule (live_alarm/imerg_gate): ramban is grandfathered onto the
    plain _<year> form, every other site carries its slug."""
    return f"_{year}" if slug == "ramban" else f"_{slug}_{year}"


# ── main ─────────────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    today = datetime.now(timezone.utc).date()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None, help="Registry YAML (default: the active AOI).")
    ap.add_argument("--threshold", choices=sorted(THRESHOLDS), default="nwhimalaya")
    ap.add_argument("--start", default=f"{today.year}-04-01")
    ap.add_argument("--end", default=today.isoformat())
    ap.add_argument("--project", default=None, help="GEE project id.")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    if load_flood_config(cfg) is None:
        print(f"flood_gate: no `flood:` block in {Path(cfg.source_path).name} — "
              f"the flood arm is DISABLED for this AOI. Nothing written.")
        return 0

    slug = cfg.aoi_slug
    domain_path = FLOOD_DIR / f"flood_domain_{slug}.json"
    if not domain_path.exists():
        print(f"flood_gate: no F0 geometry at {domain_path.name} — run flood_domain.py first. "
              f"Nothing written.")
        return 0
    domain = json.loads(domain_path.read_text(encoding="utf-8"))

    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    thr = THRESHOLDS[args.threshold]
    a, b = thr["a"], thr["b"]
    sfx = season_suffix(slug, start.year)

    per_catchment = []
    for z in domain["zones"]:
        cm = z.get("catchment")
        if not cm:
            continue
        name = f"catchment_zone{z['zone']}"
        base = {"catchment": name, "zone": z["zone"], "area_km2": cm.get("area_km2"),
                "tc_hours": cm.get("tc_hours"), "regime": cm.get("regime"),
                "imerg_pixels": imerg_pixels_spanned(cm.get("bbox_lonlat")),
                "imerg_sampling_scale_m": (round(sampling_scale_m(cm["bbox_lonlat"]))
                                           if cm.get("bbox_lonlat") else None)}
        if not cm.get("stageable"):
            per_catchment.append({**base, "aborted": True, "duration_h": None,
                                  "abort_reason": cm.get("refusal") or "not stageable (F0)"})
            print(f"  {name}: ABORT — {base['abort_reason'] if 'abort_reason' in base else cm.get('refusal')}")
            continue
        durs = match_durations(cm.get("tc_hours"))
        base["durations_h"] = durs
        cache = RAIN_CACHE / f"{slug}_zone{z['zone']}_halfhourly{sfx}.csv"
        try:
            series = fetch_catchment_series(cache, cm["bbox_lonlat"], start, end, args.project)
        except Exception as e:  # noqa: BLE001 — a fetch failure is an abort with a reason
            per_catchment.append({**base, "aborted": True, "duration_h": None,
                                  "abort_reason": f"rainfall fetch failed: {type(e).__name__}: {e}"})
            print(f"  {name}: ABORT — fetch failed ({type(e).__name__})")
            continue
        ok, reason, stats = series_health(series, min(durs))
        if not ok:
            per_catchment.append({**base, "aborted": True, "duration_h": None,
                                  "abort_reason": reason, "series_stats": stats})
            print(f"  {name}: ABORT — {reason}")
            continue
        days = catchment_daily_E(series, a, b, durs)
        peak = max(days, key=lambda d: d["E_f"])
        per_catchment.append({**base, "aborted": False, "duration_h": peak["duration_h"],
                              "abort_reason": None, "series_stats": stats,
                              "n_days": len(days), "date": peak["date"], "E_f": peak["E_f"],
                              "level": peak["level"], "burst_mm": peak["burst_mm"],
                              "peak_mmph": peak["peak_mmph"],
                              "window_end": peak["window_end"],
                              "provisional": peak["provisional"],
                              "latest": days[-1], "days": days})
        print(f"  {name}: {peak['level']} E_f={peak['E_f']} on {peak['date']} "
              f"(best {peak['duration_h']} h of {durs}, {base['area_km2']} km^2, "
              f"{base['imerg_pixels']} IMERG px)")

    if not per_catchment:
        print("flood_gate: F0 found no catchment to grade — nothing written.")
        return 0
    graded = [c for c in per_catchment if not c["aborted"]]
    season = {"start": start.isoformat(), "end": end.isoformat(),
              "days": (graded[0]["n_days"] if graded else 0)}
    summary = build_summary(slug, per_catchment, args.threshold, a, b, season)
    csv_path = write_outputs(summary, sfx)
    if summary["aborted"]:
        print("flood_gate: ABORTED — no catchment produced a gradeable series; "
              "no level published (reasons in the summary).")
    else:
        lt, sp = summary["latest"], summary["season_peak"]
        c = summary["level_counts"]
        print(f"flood gate ({thr['label']}): {summary['n_staged']}/{summary['n_catchments']} "
              f"catchments staged")
        print(f"  TODAY ({lt['date']}{', provisional' if lt.get('provisional') else ''}): "
              f"worst {lt['catchment']} {lt['level']} E_f={lt['E_f']} | "
              f"ALERT {c['FLOOD-ALERT']} · WATCH {c['FLOOD-WATCH']} · "
              f"DORMANT {c['FLOOD-DORMANT']}")
        print(f"  season peak: {sp['catchment']} {sp['level']} E_f={sp['E_f']} on {sp['date']}")
    print(f"  -> {csv_path.name} , flood_gate_summary{sfx}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

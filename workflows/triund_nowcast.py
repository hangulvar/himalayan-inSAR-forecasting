#!/usr/bin/env python
"""triund_nowcast.py — refresh the WHEN half of the Triund trek screening
(RESULTS_AND_KPIS.md §87 + its 2026-09-15 addendum).

WHY THIS EXISTS: §87's terrain findings (runout cones, exposed segments, drainage
crossings) do not change — they come from a DEM. The rainfall half does, and the
Triund dashboard is a LIVE published page about a dated decision. A page whose
weather is a week old is the §85 staleness defect wearing a different hat, so
this recomputes the figures and rewrites the ONE line of the dashboard that
carries them.

WHAT IT TOUCHES: exactly the `const NC = {...};` line in
`data/triund_screening/triund_dashboard.html`. Everything else in that file —
the 1.3 MB terrain payload, the map, the profile, the cone cross-section, the
verification ledger — is left byte-for-byte alone, and the script asserts that.

HONEST SCOPE (inherited from §87D): CHIRPS is 0.05 deg and IMERG/ERA5-Land
0.1 deg, over an AOI 3.5 km wide. All three see the Dhauladhar scarp as one or
two pixels. These are regional context, never a site measurement — and the
CHIRPS/IMERG disagreement on P(wet) is part of the answer, not noise to average.

  python workflows/triund_nowcast.py                 # recompute + rewrite NC
  python workflows/triund_nowcast.py --dry-run       # print, change nothing

Needs GEE credentials (EE_PROJECT_ID in .env). No heavy numpy linalg, so the
Windows BLAS-DLL bug class does not apply — it runs natively or in the container.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import ee
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASH = PROJECT_ROOT / "data" / "triund_screening" / "triund_dashboard.html"

# The AOI polygon, straight from the registry file (never re-typed).
AOI_PATH = PROJECT_ROOT / "config" / "aoi" / "triund_aoi.geojson"

# The project's adopted NW-Himalaya frequentist I-D trigger curve, as cumulative
# depths (RESULTS_AND_KPIS.md; I = 2.9993 * D^-0.4152, mm/h with D in hours).
ID_CUM = {1: 19.0, 2: 29.0, 3: 37.0, 5: 49.0, 7: 60.0}

TREK = dt.date(2026, 9, 26)
SEASON_START = "2026-06-01"


def init_ee(project: str | None = None) -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass
    proj = project or os.environ.get("EE_PROJECT_ID")
    if not proj:
        raise SystemExit("No Earth Engine project id. Set EE_PROJECT_ID in .env "
                         "(or pass --project).")
    ee.Initialize(project=proj)


def aoi_geometry() -> ee.Geometry:
    gj = json.loads(AOI_PATH.read_text(encoding="utf-8"))
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    return ee.Geometry(feats[0]["geometry"], None, False)


def daily(aoi, coll_id, band, scale, mult, start, end, agg="sum") -> dict[str, float]:
    """AOI-mean daily series. Returns {} when the collection is empty for the span."""
    c = ee.ImageCollection(coll_id).filterDate(start, end).filterBounds(aoi).select(band)
    if c.size().getInfo() == 0:
        return {}
    n = ee.Date(end).difference(ee.Date(start), "day")
    days = ee.List.sequence(0, n.subtract(1))

    def one(k):
        d0 = ee.Date(start).advance(k, "day")
        sub = c.filterDate(d0, d0.advance(1, "day"))
        img = ee.Algorithms.If(sub.size().gt(0),
                               sub.sum() if agg == "sum" else sub.mean(),
                               ee.Image.constant(-999))
        v = ee.Image(img).reduceRegion(ee.Reducer.mean(), aoi, scale,
                                       bestEffort=True).values().get(0)
        return ee.Feature(None, {"d": d0.format("YYYY-MM-dd"), "v": v})

    rows = (ee.FeatureCollection(days.map(one)).filter(ee.Filter.notNull(["v"]))
            .reduceColumns(ee.Reducer.toList(2), ["d", "v"]).get("list").getInfo())
    return {r[0]: float(r[1]) * mult for r in rows if float(r[1]) > -900}


def breaches(series: dict[str, float], days_back: int) -> list[str]:
    """Dates in the trailing window where any I-D duration is exceeded."""
    keys = sorted(series)
    vals = [series[k] for k in keys]
    hit = []
    for i in range(max(0, len(vals) - days_back), len(vals)):
        for dur, thr in ID_CUM.items():
            if i - dur + 1 >= 0 and sum(vals[i - dur + 1:i + 1]) >= thr:
                hit.append(keys[i])
                break
    return hit


def window_sum(series: dict[str, float], end: dt.date, days: int) -> float:
    lo = end - dt.timedelta(days=days - 1)
    return sum(v for k, v in series.items() if lo <= dt.date.fromisoformat(k) <= end)


def excl(d: dt.date) -> str:
    """`daily()` treats `end` as EXCLUSIVE. Any historical window compared against
    a current one must therefore be asked for with end+1 — otherwise history is a
    day shorter than today, the normal is biased low and every anomaly is biased
    high. (Caught 2026-09-15 when this script's +33% disagreed with the +32% the
    session had already derived a different way.)"""
    return str(d + dt.timedelta(days=1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="compute and print; do not touch the dashboard")
    ap.add_argument("--project", default=None, help="GEE project id (overrides EE_PROJECT_ID)")
    ap.add_argument("--today", default=None, help="override 'today' (ISO) for testing")
    args = ap.parse_args(argv)

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    init_ee(args.project)
    aoi = aoi_geometry()
    end = str(today + dt.timedelta(days=1))
    print(f"Triund nowcast — {today}  ({(TREK - today).days} days to the trek on {TREK})")

    im = daily(aoi, "NASA/GPM_L3/IMERG_V07", "precipitation", 11132, 0.5, SEASON_START, end)
    er = daily(aoi, "ECMWF/ERA5_LAND/DAILY_AGGR", "total_precipitation_sum", 11132, 1000.0,
               SEASON_START, end, agg="mean")
    ch = daily(aoi, "UCSB-CHG/CHIRPS/DAILY", "precipitation", 5566, 1.0, SEASON_START, end)
    if not im:
        raise SystemExit("IMERG returned nothing — aborting rather than publishing a blank.")

    im_last = dt.date.fromisoformat(max(im))
    br = breaches(im, 21)
    last_br = dt.date.fromisoformat(max(br)) if br else None

    # --- CHIRPS season anomaly against the SAME window in 1991-2025 -------------
    ch_stats = None
    if ch:
        ch_last = dt.date.fromisoformat(max(ch))
        cur = sum(ch.values())
        hist = []
        for y in range(1991, today.year):
            s = daily(aoi, "UCSB-CHG/CHIRPS/DAILY", "precipitation", 5566, 1.0,
                      f"{y}-06-01", excl(dt.date(y, ch_last.month, ch_last.day)))
            if s:
                hist.append(sum(s.values()))
        if hist:
            m = float(np.mean(hist))
            ch_stats = {"through": str(ch_last), "total": cur, "normal": m,
                        "anom": 100 * (cur - m) / m,
                        "rank": int(sum(1 for h in hist if h < cur)) + 1,
                        "n": len(hist) + 1}

    # --- is the trailing 10-day block unusual FOR THIS TIME OF YEAR? -----------
    # (§87 addendum: a trend inside one season is not a finding until it is
    #  ranked against the same window in other seasons.)
    b_end, b_start = im_last, im_last - dt.timedelta(days=9)
    cur_blk = window_sum(im, b_end, 10)
    blk_hist = []
    for y in range(2001, today.year):
        s = daily(aoi, "NASA/GPM_L3/IMERG_V07", "precipitation", 11132, 0.5,
                  f"{y}-{b_start.month:02d}-{b_start.day:02d}",
                  excl(dt.date(y, b_end.month, b_end.day)))
        if s:
            blk_hist.append(sum(s.values()))
    blk = None
    if blk_hist:
        rank = sum(1 for h in blk_hist if h < cur_blk) + 1
        blk = {"cur": cur_blk, "median": float(np.median(blk_hist)), "rank": rank,
               "n": len(blk_hist) + 1,
               "pct_wetter": 100 * (rank - 1) / len(blk_hist)}

    # --- the three products on IDENTICAL dates -------------------------------
    # The season rows quote different products over different spans, which invites
    # reading them as comparable. They are not: over this scarp the wettest product
    # runs several times the driest on the SAME days. Compute that spread so the
    # page can say so instead of leaving the reader to infer a trend from it.
    common = sorted(set(im) & set(er) & set(ch)) if (er and ch) else []
    spread = None
    if len(common) >= 30:
        tot = {"IMERG": sum(im[k] for k in common),
               "ERA5-Land": sum(er[k] for k in common),
               "CHIRPS": sum(ch[k] for k in common)}
        lo_k = min(tot, key=tot.get)
        hi_k = max(tot, key=tot.get)
        spread = {"days": len(common), "from": common[0], "to": common[-1],
                  "lo": round(tot[lo_k]), "lo_name": lo_k,
                  "hi": round(tot[hi_k]), "hi_name": hi_k,
                  "ratio": round(tot[hi_k] / tot[lo_k], 1)}
        print(f"  same-window spread ({len(common)} shared days): "
              f"{lo_k} {tot[lo_k]:.0f} mm .. {hi_k} {tot[hi_k]:.0f} mm "
              f"= {spread['ratio']}x")

    NC = {
        "computed": str(today), "trek": str(TREK), "days_to_trek": (TREK - today).days,
        "spread": spread,
        "imerg_through": str(im_last), "imerg_lag": (today - im_last).days,
        "imerg_season": round(sum(im.values())),
        "imerg_last7": round(window_sum(im, im_last, 7), 1),
        "imerg_last15": round(window_sum(im, im_last, 15), 1),
        "breaches": br, "n_breaches": len(br),
        "last_breach": str(last_br) if last_br else None,
        "days_since_breach": (today - last_br).days if last_br else None,
        "era_through": max(er) if er else None,
        "era_lag": (today - dt.date.fromisoformat(max(er))).days if er else None,
        "era_season": round(sum(er.values())) if er else None,
        "chirps_through": ch_stats["through"] if ch_stats else None,
        "chirps_season": round(ch_stats["total"]) if ch_stats else None,
        "chirps_normal": round(ch_stats["normal"]) if ch_stats else None,
        "chirps_anom": round(ch_stats["anom"]) if ch_stats else None,
        "chirps_rank": ch_stats["rank"] if ch_stats else None,
        "chirps_n": ch_stats["n"] if ch_stats else None,
        "blk_cur": round(blk["cur"], 1) if blk else None,
        "blk_med": round(blk["median"], 1) if blk else None,
        "blk_rank": blk["rank"] if blk else None,
        "blk_n": blk["n"] if blk else None,
        "blk_pct_wetter": round(blk["pct_wetter"]) if blk else None,
    }

    print(f"  IMERG through {NC['imerg_through']} (lag {NC['imerg_lag']} d), "
          f"season {NC['imerg_season']} mm, last 7 d {NC['imerg_last7']} mm")
    print(f"  trigger-line crossings in the last 21 d: {NC['n_breaches']}"
          + (f", most recent {NC['last_breach']} "
             f"({NC['days_since_breach']} d ago)" if last_br else ""))
    if ch_stats:
        print(f"  CHIRPS season to {NC['chirps_through']}: {NC['chirps_season']} mm, "
              f"{NC['chirps_anom']:+d}% vs normal (rank {NC['chirps_rank']}/{NC['chirps_n']})")
    if blk:
        print(f"  trailing 10 d = {NC['blk_cur']} mm, wetter than {NC['blk_pct_wetter']}% of the "
              f"same window since 2001 (median {NC['blk_med']} mm)")

    if args.dry_run:
        print("\n--dry-run: dashboard not modified")
        print(json.dumps(NC, indent=1))
        return 0

    if not DASH.exists():
        raise SystemExit(f"Missing {DASH} — build the dashboard before refreshing it.")
    html = DASH.read_text(encoding="utf-8")
    pat = re.compile(r"const NC = \{.*?\};\n", re.S)
    if not pat.search(html):
        raise SystemExit("No `const NC = {...};` line in the dashboard — this page predates the "
                         "nowcast slot; rebuild it rather than patching.")
    before_len = len(html)
    payload = "const NC = " + json.dumps(NC, separators=(",", ":")) + ";\n"
    new = pat.sub(lambda _: payload, html, count=1)

    # GUARD: the terrain payload must be untouched. Anything else is a bug.
    def terrain_blob(s: str) -> str:
        i = s.find("const D = {")
        return s[i:s.find("\n", i)]
    assert terrain_blob(new) == terrain_blob(html), "terrain payload changed — aborting"
    assert new.count("const NC =") == 1, "NC line duplicated"

    DASH.write_text(new, encoding="utf-8")
    print(f"\nrewrote the nowcast line in {DASH.name} "
          f"({before_len} -> {len(new)} chars; terrain payload unchanged)")
    print("Republish the artifact to push this live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

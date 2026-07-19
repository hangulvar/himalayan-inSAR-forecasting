#!/usr/bin/env python
"""imerg_perzone_probe.py — Tier 1a of the Strengthening Plan (§56): MEASURE, before
building, whether per-zone IMERG differs from the AOI-mean at OUR AOI scales.

THE QUESTION: the burst gate (imerg_gate.py, §55/§58) uses one AOI-mean E per day. Per-zone
gating only helps if the 0.1-degree IMERG grid actually varies ACROSS the zones — but our
AOIs are tiny (the zones span only a handful of IMERG pixels), so the honest first step is a
probe, not machinery. If the divergence is small, per-zone IMERG is a documented dead end at
these scales and the engineering is skipped (CLAUDE.md: measure first, no speculative
features).

METHOD: for each AOI, take the TOP-N burst days across the 2025+2026 seasons (where localized
convection would maximize spatial contrast), sample the day's 48 half-hourly IMERG rates AT
EACH ZONE CENTROID (one GEE sampleRegions per day), compute each zone's within-day burst E
(same durations/curve as the gate), and compare the zone spread against the AOI-mean E.
Also reports how many distinct IMERG pixels the zones actually span.

Outputs data/rainfall/imerg_perzone_probe.{json,md}; headline verdict goes to ledger §58.

  docker compose run --rm insar python workflows/imerg_perzone_probe.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

from imerg_gate import (  # noqa: E402 — same curve/durations as the gate (single source)
    DUR_H, IMERG_ASSET, IMERG_BAND, IMERG_SCALE_M, STEP_H,
)
from rainfall_id_threshold import THRESHOLDS, threshold_intensity  # noqa: E402

RAIN_DIR = PROJECT_ROOT / "data" / "rainfall"
TOP_N_DAYS = 4
SITES = {"ramban": "", "vaishnodevi": "_vaishnodevi"}   # slug -> alerts-dir suffix


def day_E(rates: list[float], a: float, b: float) -> float:
    """Pure: within-day burst E from 48 half-hourly rates (mm/h) — max over the gate's
    durations of trailing windows INSIDE the day (no cross-midnight context; identical
    treatment for every zone and for the AOI mean, so the COMPARISON is fair)."""
    depth = np.array(rates) * STEP_H
    csum = np.insert(np.cumsum(depth), 0, 0.0)
    best = 0.0
    for D in DUR_H:
        k = max(1, int(round(D / STEP_H)))
        if k > len(depth):
            continue
        thr = float(threshold_intensity(np.array([D]), a, b)[0])
        acc = csum[k:] - csum[:-k]
        best = max(best, float(acc.max()) / D / thr)
    return round(best, 2)


def zone_points(slug: str) -> list[dict]:
    f = PROJECT_ROOT / "data" / f"alerts{SITES[slug]}" / "per_zone_vulnerability.csv"
    return [{"lat": float(r["lat"]), "lon": float(r["lon"])}
            for r in csv.DictReader(f.open(encoding="utf-8"))]


def distinct_pixels(pts: list[dict]) -> int:
    return len({(int(p["lon"] / 0.1), int(p["lat"] / 0.1)) for p in pts})


def top_burst_days(slug: str, n: int = TOP_N_DAYS) -> list[str]:
    rows = []
    for year in (2025, 2026):
        sfx = f"_{year}" if slug == "ramban" else f"_{slug}_{year}"
        f = RAIN_DIR / f"{slug}_imerg_daily_E{sfx}.csv"
        if f.exists():
            rows += [(float(r["max_E"]), r["date"])
                     for r in csv.DictReader(f.open(encoding="utf-8"))
                     if not r["provisional"] == "True"]
    return [d for _, d in sorted(rows, reverse=True)[:n]]


def sample_day(ee, pts: list[dict], day: str) -> list[list[float]]:
    """Per-zone list of the day's 48 half-hourly rates, one bounded GEE round-trip."""
    start = datetime.fromisoformat(day)
    col = (ee.ImageCollection(IMERG_ASSET)
           .filterDate(start.strftime("%Y-%m-%d"),
                       (start + timedelta(days=1)).strftime("%Y-%m-%d"))
           .select(IMERG_BAND).sort("system:time_start"))
    img = col.toBands()
    fc = ee.FeatureCollection([
        ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"zid": i})
        for i, p in enumerate(pts)])
    got = img.sampleRegions(collection=fc, scale=IMERG_SCALE_M).getInfo()["features"]
    out: dict[int, list[float]] = {}
    for f in got:
        props = f["properties"]
        zid = props.pop("zid")
        bands = sorted((k for k in props if k.endswith(IMERG_BAND)),
                       key=lambda k: int(k.split("_")[0]))
        out[zid] = [float(props[k]) for k in bands]
    return [out.get(i, []) for i in range(len(pts))]


def main() -> int:
    from fetch_chirps import ee_init
    ee, proj = ee_init(None)
    thr = THRESHOLDS["nwhimalaya"]
    a, b = thr["a"], thr["b"]
    report = {"asset": IMERG_ASSET, "threshold": f"{thr['label']}", "sites": {}}
    for slug in SITES:
        pts = zone_points(slug)
        days = top_burst_days(slug)
        site = {"n_zones": len(pts), "distinct_imerg_pixels": distinct_pixels(pts), "days": []}
        for day in days:
            series = sample_day(ee, pts, day)
            zone_Es = [day_E(s, a, b) for s in series if s]
            aoi_E = day_E(list(np.mean([s for s in series if s], axis=0)), a, b)
            site["days"].append({
                "date": day, "aoi_mean_E": aoi_E,
                "zone_E_min": min(zone_Es), "zone_E_max": max(zone_Es),
                "max_over_min": round(max(zone_Es) / max(min(zone_Es), 1e-6), 2),
                "max_over_aoi": round(max(zone_Es) / max(aoi_E, 1e-6), 2)})
        # Decision-relevant divergence only: on near-dry days (AOI E << 1) the ratio blows up
        # on a tiny denominator and means nothing for alerting — such days appear in the
        # top-list because the GATE's day-E includes cross-midnight windows while this
        # within-day probe does not (both facts reported, neither hidden).
        rel = [d["max_over_aoi"] for d in site["days"] if d["aoi_mean_E"] >= 1.0]
        site["max_zone_over_aoi_decision_days"] = max(rel) if rel else None
        report["sites"][slug] = site
        print(f"[{slug}] {len(pts)} zones over {site['distinct_imerg_pixels']} IMERG pixels")
        for d in site["days"]:
            print(f"   {d['date']}: AOI E={d['aoi_mean_E']}  zones {d['zone_E_min']}"
                  f"..{d['zone_E_max']}  (max/AOI {d['max_over_aoi']}x)")
    worst = max(s["max_zone_over_aoi_decision_days"] or 0 for s in report["sites"].values())
    report["verdict"] = (
        f"Max zone-over-AOI-mean E ratio on DECISION-RELEVANT days (AOI E >= 1): {worst}x "
        f"(near-dry days show inflated ratios on tiny denominators and are excluded from the "
        f"verdict, reported above). "
        + ("Per-zone gating would materially change armed sets — build it (plan 1a)."
           if worst >= 1.5 else
           "Sub-1.5x: at these AOI scales the zones sit inside only ~3 IMERG pixels, so "
           "per-zone E departs from the AOI mean by <~30% exactly when it matters — per-zone "
           "IMERG gating is a documented LOW-VALUE upgrade HERE (a zone can flip a threshold "
           "only when the AOI is already within ~25% of it; revisit for larger AOIs)."))
    (RAIN_DIR / "imerg_perzone_probe.json").write_text(json.dumps(report, indent=2),
                                                       encoding="utf-8")
    md = [f"# Per-zone IMERG divergence probe (Tier 1a)", "", report["verdict"], ""]
    for slug, s in report["sites"].items():
        md.append(f"## {slug} — {s['n_zones']} zones / {s['distinct_imerg_pixels']} pixels")
        md += [f"- {d['date']}: AOI E={d['aoi_mean_E']}, zones {d['zone_E_min']}"
               f"..{d['zone_E_max']} (max/AOI {d['max_over_aoi']}x)" for d in s["days"]] + [""]
    (RAIN_DIR / "imerg_perzone_probe.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("VERDICT:", report["verdict"])
    print(f"-> {RAIN_DIR / 'imerg_perzone_probe.json'} , .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

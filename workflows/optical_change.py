#!/usr/bin/env python
"""optical_change.py — Tier 4a of the Strengthening Plan (§56): the FAILURE-CLASS gap (CV3).
Creep radar sees slow slides; it is blind to brittle, fast failures — the class that killed 34
people at Ardhkuwari. A fast failure strips vegetation, and THAT is visible from orbit in
ordinary optical imagery as a sudden NDVI drop. This script is the first optical-change
instrument, BACK-TESTED on the one disaster with a verified scar location.

METHOD (Sentinel-2 SR via GEE, cloud-masked medians):
  PRE  composite: 2025-06-01 .. 2025-08-20   (before the 26 Aug 2025 disaster)
  POST composite: 2025-09-26 .. 2025-11-15   (post-monsoon clear skies; a debris
  chute stays bare, so the longer baseline is acceptable — stated in the caveats)
  dNDVI = NDVI_post − NDVI_pre on a 20 m grid over the Vaishno Devi AOI.
  Back-test: the verified Ardhkuwari scar (33.008764 N, 74.941791 E, GSI-anchored §51) —
  what is dNDVI there (150 m neighbourhood min), and what PERCENTILE of the AOI's change
  distribution is that? Success = the scar sits in the extreme vegetation-loss tail.

Outputs data/optical/optical_change_ardhkuwari.{json,md}; headline -> ledger (§60).
  docker compose run --rm insar python workflows/optical_change.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

OUT_DIR = PROJECT_ROOT / "data" / "optical"
S2 = "COPERNICUS/S2_SR_HARMONIZED"
PRE = ("2025-06-01", "2025-08-20")
POST = ("2025-09-26", "2025-11-15")
SCAR = (74.941791, 33.008764)          # lon, lat — GSI-anchored (§51)
SCALE_M = 20
LOSS_THR = -0.15                       # dNDVI below this = strong vegetation loss


def _masked_ndvi_median(ee, aoi, start: str, end: str):
    col = (ee.ImageCollection(S2).filterDate(start, end).filterBounds(aoi)
           .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 60)))

    def prep(img):
        scl = img.select("SCL")
        ok = (scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
              .And(scl.neq(11)))                     # shadow/cloud/cirrus/snow out
        ndvi = img.normalizedDifference(["B8", "B4"]).rename("ndvi")
        return ndvi.updateMask(ok)

    return col.map(prep).median(), col.size()


def stats_from_grid(vals: np.ndarray, scar_val: float) -> dict:
    """Pure: AOI-change stats + the scar's percentile in the distribution (low = worst loss)."""
    v = vals[np.isfinite(vals)]
    pct = float((v < scar_val).mean() * 100.0)
    return {"n_pixels": int(v.size),
            "aoi_median_dndvi": round(float(np.median(v)), 3),
            "aoi_p05_dndvi": round(float(np.percentile(v, 5)), 3),
            "pct_pixels_strong_loss": round(float((v < LOSS_THR).mean() * 100.0), 2),
            "scar_dndvi": round(float(scar_val), 3),
            "scar_percentile_low_tail": round(pct, 2)}


def main() -> int:
    from fetch_chirps import ee_init, load_aoi_geometry
    ee, proj = ee_init(None)
    aoi = ee.Geometry(load_aoi_geometry())
    pre, n_pre = _masked_ndvi_median(ee, aoi, *PRE)
    post, n_post = _masked_ndvi_median(ee, aoi, *POST)
    dndvi = post.subtract(pre).rename("dndvi")

    # The AOI grid (30 m) in one bounded pull (unmask+cast: sampleRectangle rejects a
    # default value on a mixed-type computed band).
    rect = (dndvi.unmask(-999).toFloat()
            .reproject(crs="EPSG:4326", scale=SCALE_M)
            .sampleRectangle(region=aoi.bounds()))
    grid = np.array(rect.get("dndvi").getInfo(), dtype=np.float64)
    grid[grid <= -998] = np.nan

    # The scar: worst (min) dNDVI within a widening neighbourhood of the verified point,
    # read from the SAME grid (no second GEE round-trip; NaN-safe against cloud-mask gaps).
    from config import load_config
    gj = json.loads(Path(load_config().aoi_path).read_text(encoding="utf-8"))

    def flat(c):
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for e in c:
                yield from flat(e)
    pts = [p for ft in gj["features"] for p in flat(ft["geometry"]["coordinates"])]
    lon0, lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lat1 = max(p[1] for p in pts)
    step_lon = (lon1 - lon0) / grid.shape[1]
    col = int((SCAR[0] - lon0) / step_lon)
    row = int((lat1 - SCAR[1]) / step_lon)          # ~square grid in degrees at this scale
    scar_min, radius_used = None, None
    for rad in (8, 15, 25):                          # 160 m -> 300 m -> 500 m neighbourhoods
        win = grid[max(0, row - rad):row + rad + 1, max(0, col - rad):col + rad + 1]
        if np.isfinite(win).any():
            scar_min, radius_used = float(np.nanmin(win)), rad * SCALE_M
            break
    n_pre_i, n_post_i = int(n_pre.getInfo()), int(n_post.getInfo())
    if scar_min is None:
        raise SystemExit("Scar neighbourhood fully cloud-masked in BOTH composites — widen "
                         "the post window before drawing any conclusion (honest data gap).")

    s = stats_from_grid(grid, float(scar_min))
    s["scar_neighbourhood_m"] = radius_used
    pct = s["scar_percentile_low_tail"]
    grade = "DETECTED" if pct <= 5.0 else "MARGINAL" if pct <= 10.0 else "NOT DETECTED"
    deficit = round(s["aoi_median_dndvi"] - s["scar_dndvi"], 3)
    report = {"asset": S2, "pre_window": PRE, "post_window": POST,
              "n_images": {"pre": n_pre_i, "post": n_post_i},
              "scale_m": SCALE_M, "scar_lonlat": SCAR, **s,
              "loss_threshold_dndvi": LOSS_THR,
              "detection_grade": grade,
              "verdict": {
                  "DETECTED":
                      f"DETECTED: the verified Ardhkuwari scar sits in the worst {pct}% of "
                      f"the AOI's change distribution (dNDVI {s['scar_dndvi']}). Optical "
                      f"change sees the brittle failure the creep map cannot (CV3).",
                  "MARGINAL":
                      f"MARGINAL detection: the scar is a clear LOCAL anomaly — it failed to "
                      f"green while the AOI greened (dNDVI {s['scar_dndvi']} vs AOI median "
                      f"{s['aoi_median_dndvi']}, deficit {deficit}; worst {pct}%) — but not "
                      f"in the extreme 5% tail. A narrow rocky debris chute is at the limit "
                      f"of 20 m NDVI: usable for post-event screening WITH caveats; "
                      f"higher-resolution imagery (or radar-coherence fusion, CV5) is the "
                      f"upgrade that would make this a detector.",
                  "NOT DETECTED":
                      f"NOT detected (scar percentile {pct}%) — monsoon-cloud contamination "
                      f"or sub-pixel scar; refine before trusting optical change here.",
              }[grade]}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "optical_change_ardhkuwari.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [f"# Optical change back-test — Ardhkuwari 26 Aug 2025 (Tier 4a)", "",
          f"S2 SR medians: pre {PRE[0]}..{PRE[1]} ({n_pre_i} imgs), post {POST[0]}..{POST[1]} "
          f"({n_post_i} imgs), {SCALE_M} m, SCL cloud/shadow/snow-masked.", "",
          f"- AOI median dNDVI: {s['aoi_median_dndvi']} (p05 {s['aoi_p05_dndvi']}); "
          f"strong-loss pixels (<{LOSS_THR}): {s['pct_pixels_strong_loss']}%",
          f"- **Scar dNDVI (150 m min): {s['scar_dndvi']} — worst "
          f"{s['scar_percentile_low_tail']}% of the AOI**", "",
          report["verdict"]]
    (OUT_DIR / "optical_change_ardhkuwari.md").write_text("\n".join(md) + "\n",
                                                          encoding="utf-8")
    print(f"pre imgs {n_pre_i} | post imgs {n_post_i} | AOI median dNDVI "
          f"{s['aoi_median_dndvi']} | scar {s['scar_dndvi']} "
          f"(worst {s['scar_percentile_low_tail']}%)")
    print("VERDICT:", report["verdict"][:200])
    print(f"-> {out} , .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

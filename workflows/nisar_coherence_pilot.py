#!/usr/bin/env python
"""nisar_coherence_pilot.py — Tier 2b of the Strengthening Plan (§56): THE decision
experiment for our #1 stated weakness. C-band (Sentinel-1) loses coherence over vegetated
Himalayan slopes, which is why the velocity field covers only a fraction of each AOI and why
"unmeasured ≠ safe" has to be stamped on every product. NISAR is L-band — 4x the wavelength,
which penetrates canopy and should HOLD coherence where C-band dies. This pilot measures that
claim on OUR ground with the winter sample (§56), instead of trusting the literature.

METHOD (single matched winter 12-day pair, first-order by design):
  L-band: the NISAR GUNW 27 Dec 2025 x 08 Jan 2026 (track 156 ASC) coherenceMagnitude grid.
  C-band: our own HyP3 INT80 12-day pairs bracketing the same window (01→13 Jan path 27,
          06→18 Jan path 100), chosen per AOI from the stack manifest (the AOI's own stacks).
  For each AOI: sample the L grid at every C-band 80 m pixel centre (both geocoded UTM;
  nearest-neighbour), keep pixels valid in BOTH, then:
    - median coherence L vs C over the common area;
    - the strata that matter: where C FAILS (γ_C < 0.35 — the decorrelation class our QA
      masks discard), what is the median γ_L, and what fraction of those pixels does L
      RECOVER to usable coherence (γ_L ≥ 0.35)?

Outputs data/nisar/nisar_coherence_pilot.{json,md}. Headline numbers -> ledger (§59).
Caveats stated in the report: one pair per band (not a season statistic), pair windows offset
by 5-6 days, L is 40 m posting vs C 80 m, winter (least vegetation contrast — a LOWER bound
on the summer advantage).

Needs h5py + gdal + pyproj -> the mintpy image:
  docker compose run --rm mintpy python workflows/nisar_coherence_pilot.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

NISAR_H5 = (PROJECT_ROOT / "data" / "nisar" /
            "NISAR_L2_PR_GUNW_008_156_A_018_009_4000_SH_20251227T001346_20251227T001420_"
            "20260108T001346_20260108T001421_X05010_N_F_J_001.h5")
COH_PATH = "science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram/HH"
MANIFEST = PROJECT_ROOT / "data" / "qa_masks" / "_stack_manifest.json"
TIFF_DIR = PROJECT_ROOT / "data" / "processed_tiffs"
C_FAIL = 0.35                      # the QA decorrelation threshold class
# The C-band winter pairs bracketing the NISAR window, per AOI (from the manifest's stacks).
C_PAIRS = {
    "ramban": ["20260101", "20260113", "20260106", "20260118"],
    "vaishnodevi": ["20260101", "20260113", "20260106", "20260118"],
}
AOI_SFX = {"ramban": "", "vaishnodevi": "_vaishnodevi"}


def load_l_band():
    import h5py
    f = h5py.File(NISAR_H5, "r")
    g = f[COH_PATH]
    coh = g["coherenceMagnitude"][:]
    x = g["xCoordinates"][:]
    y = g["yCoordinates"][:]
    epsg = int(g["projection"][()])
    return coh, x, y, epsg


def aoi_bbox(slug: str):
    gj = json.loads((PROJECT_ROOT / "config" / "aoi" / f"{slug}_aoi.geojson")
                    .read_text(encoding="utf-8"))

    def flat(c):
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for e in c:
                yield from flat(e)
    pts = [p for ft in gj["features"] for p in flat(ft["geometry"]["coordinates"])]
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def c_band_pairs(slug: str):
    """This AOI's winter corr GeoTIFFs: products in the AOI's source stacks whose pair dates
    are the bracketing winter 12-day pairs."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fp = (PROJECT_ROOT / "data" / f"alerts{AOI_SFX[slug]}" / "mosaic_asc" /
          "alerts_operational.json")
    stacks = set(json.loads(fp.read_text(encoding="utf-8")).get("source_stacks", []))
    d = C_PAIRS[slug]
    out = []
    for name, meta in man.items():
        if meta.get("stack") in stacks and (
                (d[0] in name and d[1] in name) or (d[2] in name and d[3] in name)):
            corr = TIFF_DIR / name / f"{name}_corr.tif"
            if corr.exists():
                out.append((meta["stack"], corr))
    return out


def sample_l_at_c(corr_tif: Path, lx, ly, lcoh, l_epsg, bbox_ll):
    """C-band corr over the AOI bbox + L-band coherence sampled at the same pixel centres."""
    from osgeo import gdal, osr
    gdal.UseExceptions()
    ds = gdal.Open(str(corr_tif))
    gt = ds.GetGeoTransform()
    sr = osr.SpatialReference(wkt=ds.GetProjection())
    sr.AutoIdentifyEPSG()
    c_epsg = int(sr.GetAuthorityCode(None))
    import pyproj
    to_c = pyproj.Transformer.from_crs(4326, c_epsg, always_xy=True)
    x0, y0 = to_c.transform(bbox_ll[0], bbox_ll[1])
    x1, y1 = to_c.transform(bbox_ll[2], bbox_ll[3])
    xmin, xmax = sorted((x0, x1))
    ymin, ymax = sorted((y0, y1))
    col0 = max(0, int((xmin - gt[0]) / gt[1]))
    col1 = min(ds.RasterXSize, int((xmax - gt[0]) / gt[1]) + 1)
    row0 = max(0, int((ymax - gt[3]) / gt[5]))
    row1 = min(ds.RasterYSize, int((ymin - gt[3]) / gt[5]) + 1)
    if col1 <= col0 or row1 <= row0:
        return None, None
    c = ds.GetRasterBand(1).ReadAsArray(col0, row0, col1 - col0, row1 - row0)
    cols = np.arange(col0, col1)
    rows = np.arange(row0, row1)
    cx = gt[0] + (cols + 0.5) * gt[1]
    cy = gt[3] + (rows + 0.5) * gt[5]
    CX, CY = np.meshgrid(cx, cy)
    if c_epsg != l_epsg:
        t = pyproj.Transformer.from_crs(c_epsg, l_epsg, always_xy=True)
        LXq, LYq = t.transform(CX, CY)
    else:
        LXq, LYq = CX, CY
    # Nearest-neighbour indices into the (regular) L grid.
    lix = np.round((LXq - lx[0]) / (lx[1] - lx[0])).astype(int)
    liy = np.round((LYq - ly[0]) / (ly[1] - ly[0])).astype(int)
    ok = (lix >= 0) & (lix < lx.size) & (liy >= 0) & (liy < ly.size)
    l = np.full(c.shape, np.nan, dtype=np.float32)
    l[ok] = lcoh[liy[ok], lix[ok]]
    return c.astype(np.float32), l


def main() -> int:
    lcoh, lx, ly, l_epsg = load_l_band()
    lcoh = np.where(np.isfinite(lcoh) & (lcoh > 0), lcoh, np.nan)
    report = {"l_band": {"file": NISAR_H5.name,
                         "pair": "2025-12-27 x 2026-01-08 (12 d, track 156 ASC)",
                         "epsg": l_epsg, "grid": list(lcoh.shape)},
              "c_fail_threshold": C_FAIL, "sites": {}}
    for slug in ("ramban", "vaishnodevi"):
        bbox = aoi_bbox(slug)
        per_pair = []
        for stack, corr in c_band_pairs(slug):
            c, l = sample_l_at_c(corr, lx, ly, lcoh, l_epsg, bbox)
            if c is None:
                continue
            valid = np.isfinite(l) & np.isfinite(c) & (c > 0)
            if valid.sum() < 100:
                continue
            cv, lv = c[valid], l[valid]
            cfail = cv < C_FAIL
            per_pair.append({
                "stack": stack, "pair_tif": corr.parent.name[:44],
                "n_pixels": int(valid.sum()),
                "median_c": round(float(np.median(cv)), 3),
                "median_l": round(float(np.median(lv)), 3),
                "pct_c_fail": round(100.0 * cfail.mean(), 1),
                "median_l_where_c_fails": (round(float(np.median(lv[cfail])), 3)
                                           if cfail.any() else None),
                "pct_recovered_by_l": (round(100.0 * (lv[cfail] >= C_FAIL).mean(), 1)
                                       if cfail.any() else None),
            })
        report["sites"][slug] = per_pair
        if not per_pair:
            report.setdefault("site_notes", {})[slug] = (
                "NOT COMPARABLE: this AOI's C-band stacks hold no winter pairs (its 4-pair "
                "baselines start May 2026 — onboarded mid-season), so no contemporaneous "
                "L-vs-C match exists. The Ramban result covers the same paths/terrain class; "
                "re-run for this AOI when a winter season accumulates in its stacks.")
    # Aggregate verdict.
    allp = [p for ps in report["sites"].values() for p in ps]
    if not allp:
        raise SystemExit("No overlapping valid pixels — check pair selection/AOI coverage.")
    med_gain = np.median([p["median_l"] - p["median_c"] for p in allp])
    rec = [p["pct_recovered_by_l"] for p in allp if p["pct_recovered_by_l"] is not None]
    report["verdict"] = {
        "median_coherence_gain_L_minus_C": round(float(med_gain), 3),
        "median_pct_of_C_fail_pixels_recovered_by_L": round(float(np.median(rec)), 1) if rec else None,
        "reading": (
            "L-band holds usable coherence over a large share of the ground C-band loses — "
            "the step-change case is CONFIRMED on our own slopes; plan the operational L-band "
            "stack for when the forward stream arrives."
            if rec and np.median(rec) >= 50 else
            "L-band recovers only a modest share of C-band's lost ground on this winter pair "
            "— re-test on a monsoon-season pair before investing (winter is the least "
            "vegetation-contrast season, so this is a lower bound)."),
        "caveats": "One pair per band; windows offset 5-6 d; L 40 m vs C 80 m posting; "
                   "winter = minimum vegetation contrast (summer advantage should be larger).",
    }
    out = PROJECT_ROOT / "data" / "nisar" / "nisar_coherence_pilot.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [f"# NISAR L-band vs Sentinel-1 C-band coherence pilot (Tier 2b) — {date.today()}",
          "", f"L pair: {report['l_band']['pair']} · C fail threshold {C_FAIL}", ""]
    for slug, ps in report["sites"].items():
        md.append(f"## {slug}")
        for p in ps:
            md.append(f"- **{p['stack']}** ({p['n_pixels']} px): median γ C **{p['median_c']}**"
                      f" vs L **{p['median_l']}**; C fails on {p['pct_c_fail']}% — there, "
                      f"median γ_L {p['median_l_where_c_fails']}, recovered "
                      f"**{p['pct_recovered_by_l']}%**")
        md.append("")
    v = report["verdict"]
    md += [f"**Median coherence gain (L−C): {v['median_coherence_gain_L_minus_C']}** · "
           f"**median recovery of C-fail pixels: {v['median_pct_of_C_fail_pixels_recovered_by_L']}%**",
           "", v["reading"], "", f"_Caveats: {v['caveats']}_"]
    (PROJECT_ROOT / "data" / "nisar" / "nisar_coherence_pilot.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")
    for slug, ps in report["sites"].items():
        for p in ps:
            print(f"[{slug}] {p['stack']}: C {p['median_c']} vs L {p['median_l']} | "
                  f"C-fail {p['pct_c_fail']}% -> L recovers {p['pct_recovered_by_l']}%")
    print("VERDICT:", v["reading"])
    print(f"-> {out} , .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

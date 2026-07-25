#!/usr/bin/env python
"""nisar_coherence_pilot.py — Tier 2b of the Strengthening Plan (§56): THE decision
experiment for our #1 stated weakness. C-band (Sentinel-1) loses coherence over vegetated
Himalayan slopes, which is why the velocity field covers only a fraction of each AOI and why
"unmeasured ≠ safe" has to be stamped on every product. NISAR is L-band — 4x the wavelength,
which penetrates canopy and should HOLD coherence where C-band dies. This pilot measures that
claim on OUR ground with the winter sample (§56), instead of trusting the literature.

TWO SEASONS, one method (`--season winter|monsoon`; winter is the default and reproduces §59
byte-identically). §59 measured this in WINTER and said so honestly: winter is the season of
minimum vegetation contrast, so its answer is a LOWER BOUND on the advantage that matters. The
NISAR forward stream reached this region in Jul 2026 (§56 Tier 2c watch), so the monsoon pair —
peak canopy, the condition the whole L-band case rests on — is now measurable (§65).

METHOD (single matched 12-day pair per band per season, first-order by design):
  L-band: a NISAR GUNW on track 156 ASC frame 018 — the SAME track both seasons, so geometry
          is held constant and only the season varies.
  C-band: our own HyP3 INT80 **12-day** pairs bracketing the same window, chosen per AOI from
          the stack manifest. Baseline length is held at 12 days for both bands and both
          seasons: a shorter pair decorrelates less, so mixing one in would bias the result.
  For each AOI: sample the L grid at every C-band 80 m pixel centre (both geocoded UTM;
  nearest-neighbour), keep pixels valid in BOTH, then:
    - median coherence L vs C over the common area;
    - the strata that matter: where C FAILS (γ_C < 0.35 — the decorrelation class our QA
      masks discard), what is the median γ_L, and what fraction of those pixels does L
      RECOVER to usable coherence (γ_L ≥ 0.35)?

Outputs data/nisar/nisar_coherence_pilot{,_monsoon}.{json,md}; headline numbers -> ledger
(§59 winter, §65 monsoon). Caveats stated in the report: one pair per band (not a season
statistic), the pair windows are offset by days, L is 40 m posting vs C 80 m.

Needs h5py + gdal + pyproj -> the mintpy image:
  docker compose run --rm mintpy python workflows/nisar_coherence_pilot.py
  docker compose run --rm mintpy python workflows/nisar_coherence_pilot.py --season monsoon
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

NISAR_DIR = PROJECT_ROOT / "data" / "nisar"
COH_PATH = "science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram/HH"
MANIFEST = PROJECT_ROOT / "data" / "qa_masks" / "_stack_manifest.json"
TIFF_DIR = PROJECT_ROOT / "data" / "processed_tiffs"
C_FAIL = 0.35                      # the QA decorrelation threshold class
AOI_SFX = {"ramban": "", "vaishnodevi": "_vaishnodevi"}

# --- L-band coverage guard (§65) ---------------------------------------------------------
# NISAR provisional GUNWs carry large NaN VOIDS: NASA's own QA reports ~46-63% NaN per layer
# and still PASSES, because its threshold only trips above 99% NaN. A product-level PASS
# therefore says nothing about whether YOUR AOI has data. The first monsoon granule over these
# AOIs is 100% NaN over Ramban while its connectedComponents layer claims valid unwrapped data
# there — and scoring it produced a confident, entirely fabricated "L recovers 0.0%".
# So: refuse to score an AOI whose L window is mostly void, and say why.
MIN_L_VALID_PCT = 40.0             # % of the AOI window that must carry finite, >0 coherence
MIN_L_MEDIAN = 0.05                # below this the window is noise, not low coherence

# Two matched 12-day L-band pairs on the SAME NISAR track (156 ASC frame 018), one per season.
# `winter` is §59's original run and is the DEFAULT, so that result reproduces byte-identically.
# `monsoon` answers §59's own stated limitation ("winter = minimum vegetation contrast, a LOWER
# bound on the summer advantage") using the forward stream that started Jul 2026 (§56 Tier 2c).
#
# extra_stacks: the May-2026 Sentinel-1 frame renumber (§61) means Ramban's June C-band pairs sit
# on the RENAMED continuation frames (f105/f103) rather than the frames its standing product was
# built from (f106/f102/f101). §61 established that renumber is a label shift over the same
# ground (the bridge interferogram is coherent), so those stacks are admitted explicitly. It is a
# no-op for Vaishno Devi, whose standing product is already built on f105/f103.
SEASONS = {
    "winter": {
        "h5": ("NISAR_L2_PR_GUNW_008_156_A_018_009_4000_SH_20251227T001346_20251227T001420_"
               "20260108T001346_20260108T001421_X05010_N_F_J_001.h5"),
        "label": "2025-12-27 x 2026-01-08 (12 d, track 156 ASC)",
        "c_pairs": {"ramban": ["20260101", "20260113", "20260106", "20260118"],
                    "vaishnodevi": ["20260101", "20260113", "20260106", "20260118"]},
        "extra_stacks": [],
        "tag": "",
        "offset_note": "windows offset 5-6 d",
        "season_note": "winter = minimum vegetation contrast (summer advantage should be larger)",
    },
    "monsoon": {
        "h5": ("NISAR_L2_PR_GUNW_023_156_A_018_024_4000_SH_20260625T001346_20260625T001421_"
               "20260707T001345_20260707T001420_P05023_N_F_J_001.h5"),
        "label": "2026-06-25 x 2026-07-07 (12 d, track 156 ASC)",
        # The newest 12-day C-band pairs in the library: 06->18 Jun (path 27, f105) and
        # 11->23 Jun (path 100, f103). The 7-day S1AxS1D seam pair (18->25 Jun) is deliberately
        # EXCLUDED: a shorter temporal baseline decorrelates less, so mixing it in would bias
        # the comparison IN FAVOUR of C-band. Both bands stay at 12 days.
        "c_pairs": {"ramban": ["20260606", "20260618", "20260611", "20260623"],
                    "vaishnodevi": ["20260606", "20260618", "20260611", "20260623"]},
        "extra_stacks": ["ASC_path27_frame105", "ASC_path100_frame103"],
        "tag": "_monsoon",
        "offset_note": "windows offset 2-14 d",
        "season_note": "peak monsoon = maximum canopy, the season the advantage is claimed for",
    },
}


def load_l_band(h5_path: Path):
    import h5py
    f = h5py.File(h5_path, "r")
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


def l_window_health(lcoh, lx, ly, bbox_ll, l_epsg) -> dict:
    """Pure-ish: is the L-band grid actually populated over this AOI? Returns the window's
    valid fraction + median, and a verdict. `lcoh` must already have invalid pixels as NaN.

    This is the guard between "L-band lost coherence here" (a result) and "this granule has
    no data here" (a void). The two are indistinguishable downstream — both look like low
    numbers — which is exactly how a void becomes a published finding.
    """
    import pyproj
    t = pyproj.Transformer.from_crs(4326, l_epsg, always_xy=True)
    (x0, y0), (x1, y1) = t.transform(bbox_ll[0], bbox_ll[1]), t.transform(bbox_ll[2], bbox_ll[3])
    ix = np.where((lx >= min(x0, x1)) & (lx <= max(x0, x1)))[0]
    iy = np.where((ly >= min(y0, y1)) & (ly <= max(y0, y1)))[0]
    if ix.size == 0 or iy.size == 0:
        return {"valid_pct": 0.0, "median": None, "ok": False,
                "reason": "AOI falls outside the L-band grid entirely"}
    sub = lcoh[np.ix_(iy, ix)]
    fin = np.isfinite(sub)
    valid_pct = round(100.0 * float(fin.mean()), 1)
    med = round(float(np.median(sub[fin])), 3) if fin.any() else None
    if valid_pct < MIN_L_VALID_PCT:
        return {"valid_pct": valid_pct, "median": med, "ok": False,
                "reason": (f"L-band DATA VOID over this AOI: only {valid_pct}% of the window "
                           f"carries finite coherence (need >={MIN_L_VALID_PCT}%). Not a "
                           f"coherence result — there is no data to score.")}
    if med is not None and med < MIN_L_MEDIAN:
        return {"valid_pct": valid_pct, "median": med, "ok": False,
                "reason": (f"L-band window is numerically dead (median {med} < "
                           f"{MIN_L_MEDIAN}) — consistent with void fringe, not terrain.")}
    return {"valid_pct": valid_pct, "median": med, "ok": True, "reason": "ok"}


def c_band_pairs(slug: str, season: dict):
    """This AOI's corr GeoTIFFs for the season: products in the AOI's source stacks (plus any
    `extra_stacks` the season admits) whose pair dates are the bracketing 12-day pairs."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fp = (PROJECT_ROOT / "data" / f"alerts{AOI_SFX[slug]}" / "mosaic_asc" /
          "alerts_operational.json")
    stacks = set(json.loads(fp.read_text(encoding="utf-8")).get("source_stacks", []))
    stacks |= set(season["extra_stacks"])
    d = season["c_pairs"][slug]
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
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--season", choices=sorted(SEASONS), default="winter",
                    help="Which matched L/C pair set to score (default: winter — §59's run).")
    args = ap.parse_args()
    season = SEASONS[args.season]
    h5 = NISAR_DIR / season["h5"]
    if not h5.exists():
        raise SystemExit(f"Missing NISAR GUNW for season '{args.season}': {h5.name}\n"
                         f"Download it from ASF into data/nisar/ first.")

    lcoh, lx, ly, l_epsg = load_l_band(h5)
    lcoh = np.where(np.isfinite(lcoh) & (lcoh > 0), lcoh, np.nan)
    report = {"season": args.season,
              "l_band": {"file": h5.name, "pair": season["label"],
                         "epsg": l_epsg, "grid": list(lcoh.shape)},
              "c_fail_threshold": C_FAIL, "sites": {}}
    for slug in ("ramban", "vaishnodevi"):
        bbox = aoi_bbox(slug)
        # GUARD (§65): never score an AOI the L granule has no data over — a void and a
        # decorrelated slope are indistinguishable in the output numbers.
        health = l_window_health(lcoh, lx, ly, bbox, l_epsg)
        report.setdefault("l_coverage", {})[slug] = health
        if not health["ok"]:
            report["sites"][slug] = []
            report.setdefault("site_notes", {})[slug] = health["reason"]
            continue
        per_pair = []
        for stack, corr in c_band_pairs(slug, season):
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
                f"NOT COMPARABLE: this AOI's C-band stacks hold no {args.season} pairs "
                f"matching {season['c_pairs'][slug]}, so no contemporaneous L-vs-C match "
                f"exists. Re-run for this AOI once such a pair accumulates in its stacks.")
    # Aggregate verdict. A run where no AOI survived the coverage guard is an honest ABORT,
    # not a result: it writes the evidence and exits without a verdict (§65).
    allp = [p for ps in report["sites"].values() for p in ps]
    if not allp:
        report["verdict"] = {
            "status": "ABORTED — no scoreable AOI",
            "reading": ("This granule yields NO L-vs-C measurement over these AOIs. See "
                        "l_coverage/site_notes for the per-AOI reason. This is a data-"
                        "availability outcome and says NOTHING about L-band performance; "
                        "do not read it as a negative result."),
            "caveats": f"{season['offset_note']}; {season['season_note']}.",
        }
        out = NISAR_DIR / f"nisar_coherence_pilot{season['tag']}.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        for slug, note in report.get("site_notes", {}).items():
            print(f"[{slug}] {note}")
        print(f"ABORTED — no verdict written. Evidence -> {out}")
        return 0
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
            "L-band recovers only a modest share of C-band's lost ground on this pair "
            "— re-test on another season before investing."),
        "caveats": f"One pair per band; {season['offset_note']}; L 40 m vs C 80 m posting; "
                   f"{season['season_note']}.",
    }
    tag = season["tag"]
    out = NISAR_DIR / f"nisar_coherence_pilot{tag}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [f"# NISAR L-band vs Sentinel-1 C-band coherence pilot (Tier 2b) — {date.today()}",
          "", f"Season: **{args.season}** · L pair: {report['l_band']['pair']} · "
          f"C fail threshold {C_FAIL}", ""]
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
    (NISAR_DIR / f"nisar_coherence_pilot{tag}.md").write_text(
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

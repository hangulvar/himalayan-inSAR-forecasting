#!/usr/bin/env python
"""
prep_mintpy.py — assemble a MintPy HyP3 work directory for one stack.

MintPy's prep_hyp3 / smallbaselineApp need, per interferogram, the HyP3 `.txt`
metadata plus the GeoTIFF layers, all clipped to a COMMON grid. Our
`data/processed_tiffs/` has the `.tif`s but not the `.txt` (Phase-1 extracted only
GeoTIFFs), and pairs have slightly different extents.

For a stack's KEEP pairs this script writes into `data/mintpy/<stack>/hyp3/`:
  1. each of {unw_phase, corr, dem, lv_theta, lv_phi, water_mask}, clipped (nearest,
     no value alteration) to the grid of the custom inverter's velocity raster — so
     MintPy and our custom result share an IDENTICAL grid for cross-validation;
  2. each pair's `<product>.txt` HyP3 metadata, extracted from `data/raw_zips/`.
Idempotent: skips outputs already present.

Then run:
  docker compose run --rm mintpy bash -lc \
    'prep_hyp3.py data/mintpy/<stack>/hyp3/*_clip.tif'
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import zipfile
from pathlib import Path

from osgeo import gdal, ogr, osr

gdal.UseExceptions()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUARANTINE_CSV = PROJECT_ROOT / "data" / "qa_masks" / "_quarantine_list.csv"
PROCESSED = PROJECT_ROOT / "data" / "processed_tiffs"
RAW = PROJECT_ROOT / "data" / "raw_zips"
VEL = PROJECT_ROOT / "data" / "velocity"

# HyP3 layers MintPy uses: unw + cor are stacked per pair; dem/inc/az/water are the
# (per-pair-identical) geometry layers MintPy reads one of.
SUFFIXES = ["_unw_phase", "_corr", "_dem", "_lv_theta", "_lv_phi", "_water_mask"]


def keep_products(stack: str) -> list[str]:
    rows = list(csv.DictReader(QUARANTINE_CSV.open(encoding="utf-8")))
    return sorted(r["product"] for r in rows
                  if r["stack"] == stack and r["decision"] == "KEEP")


def aoi_bounds_in_epsg(aoi_path: Path, epsg: str):
    """AOI polygon bounds reprojected into EPSG:<epsg> (meters). osgeo-only so this
    stays runnable in the lean MintPy image (no geopandas)."""
    ds = ogr.Open(str(aoi_path))
    if ds is None:
        sys.exit(f"Cannot open AOI: {aoi_path}")
    lyr = ds.GetLayer()
    src = lyr.GetSpatialRef()
    dst = osr.SpatialReference()
    dst.ImportFromEPSG(int(epsg))
    src.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ct = osr.CoordinateTransformation(src, dst)
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for feat in lyr:
        g = feat.GetGeometryRef().Clone()
        g.Transform(ct)
        x0, x1, y0, y1 = g.GetEnvelope()
        minx, maxx = min(minx, x0), max(maxx, x1)
        miny, maxy = min(miny, y0), max(maxy, y1)
    return minx, miny, maxx, maxy


def grid_from_products(products: list[str], aoi_path: Path, buffer_km: float):
    """Products' common extent ∩ (AOI + buffer), snapped to the first product's grid.
    Mirrors custom_sbas_inverter.compute_clipped_grid so a DESC stack with no custom
    velocity raster gets the SAME footprint as the ASC stacks (just in its own LOS
    geometry) — the basis for later ASC/DESC decomposition. gdalwarp (-te/-ts/near)
    in main() forces every product onto this exact grid."""
    lefts, rights, tops, bottoms = [], [], [], []
    res, epsgs = set(), set()
    anchor = None
    for p in products:
        src = PROCESSED / p / f"{p}_unw_phase.tif"
        if not src.exists():
            sys.exit(f"Missing {src} — cannot derive grid.")
        ds = gdal.Open(str(src))
        gt = ds.GetGeoTransform()
        w, h = ds.RasterXSize, ds.RasterYSize
        rx, ry = gt[1], -gt[5]
        left, top = gt[0], gt[3]
        lefts.append(left); rights.append(left + w * rx)
        tops.append(top); bottoms.append(top - h * ry)
        res.add((round(rx, 4), round(ry, 4)))
        epsgs.add(ds.GetSpatialRef().GetAuthorityCode(None))
        if anchor is None:
            anchor = (left, top)
    if len(res) != 1 or len(epsgs) != 1:
        sys.exit(f"Inconsistent res/epsg across products: res={res} epsg={epsgs}")
    rx, ry = list(res)[0]
    epsg = list(epsgs)[0]

    left, right = max(lefts), min(rights)        # intersection of all products
    top, bottom = min(tops), max(bottoms)

    minx, miny, maxx, maxy = aoi_bounds_in_epsg(aoi_path, epsg)
    buf = buffer_km * 1000.0
    left = max(left, minx - buf); right = min(right, maxx + buf)
    top = min(top, maxy + buf); bottom = max(bottom, miny - buf)
    if right <= left or top <= bottom:
        sys.exit("AOI does not overlap the product footprint.")

    ax, ay = anchor                              # snap to the native pixel grid
    left = ax + round((left - ax) / rx) * rx
    top = ay + round((top - ay) / ry) * ry
    width = max(1, int(round((right - left) / rx)))
    height = max(1, int(round((top - bottom) / ry)))
    right, bottom = left + width * rx, top - height * ry
    return (left, bottom, right, top), width, height, epsg, \
        f"AOI+{buffer_km:g}km grid from {len(products)} products"


def target_grid(stack: str, products: list[str], aoi_path: Path, buffer_km: float):
    """(te=(xmin,ymin,xmax,ymax), width, height, epsg, source).

    Prefer the custom velocity grid when present (ASC stacks — gives MintPy an
    IDENTICAL grid for cross-validation). For a stack with no custom result (a
    disconnected DESC stack only MintPy can invert), derive the equivalent
    AOI+buffer grid directly from the products."""
    ref = VEL / f"{stack}_mean_velocity_los_highpass.tif"
    if ref.exists():
        ds = gdal.Open(str(ref))
        gt = ds.GetGeoTransform()
        w, h = ds.RasterXSize, ds.RasterYSize
        left, top = gt[0], gt[3]
        right, bottom = left + w * gt[1], top + h * gt[5]
        epsg = ds.GetSpatialRef().GetAuthorityCode(None)
        return (left, bottom, right, top), w, h, epsg, "custom-velocity grid"
    return grid_from_products(products, aoi_path, buffer_km)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stack", default="ASC_path27_frame106")
    ap.add_argument("--aoi", default=str(PROJECT_ROOT / "ramban_aoi.geojson"),
                    help="AOI polygon (EPSG:4326); used only when the stack has no "
                         "custom velocity raster (e.g. disconnected DESC stacks).")
    ap.add_argument("--buffer-km", type=float, default=3.0,
                    help="AOI buffer (km) for the derived grid; matches the custom "
                         "inverter's --buffer-km default.")
    args = ap.parse_args()
    stack = args.stack

    out = PROJECT_ROOT / "data" / "mintpy" / stack / "hyp3"
    out.mkdir(parents=True, exist_ok=True)

    products = keep_products(stack)
    if not products:
        sys.exit(f"No KEEP products for stack {stack} in {QUARANTINE_CSV}.")
    te, w, h, epsg, gsrc = target_grid(stack, products, Path(args.aoi), args.buffer_km)
    print(f"{stack}: {len(products)} KEEP pairs -> {out}")
    print(f"target grid {w}x{h} EPSG:{epsg} ({gsrc}) te={tuple(round(x,1) for x in te)}")

    n_warp = n_skip = n_txt = n_missing = 0
    for p in products:
        srcdir = PROCESSED / p
        for suf in SUFFIXES:
            src = srcdir / f"{p}{suf}.tif"
            dst = out / f"{p}{suf}_clip.tif"
            if not src.exists():
                n_missing += 1
                continue
            if dst.exists():
                n_skip += 1
                continue
            subprocess.run(
                ["gdalwarp", "-q", "-overwrite",
                 "-t_srs", f"EPSG:{epsg}",
                 "-te", *[str(x) for x in te],
                 "-ts", str(w), str(h),
                 "-r", "near",
                 str(src), str(dst)],
                check=True,
            )
            n_warp += 1
        txt_dst = out / f"{p}.txt"
        if not txt_dst.exists():
            # Prefer the copy extracted into processed_tiffs (Phase 1 keeps it there
            # since 2026-07-15, so the raw zips are disposable); zip = legacy fallback.
            txt_src = PROCESSED / p / f"{p}.txt"
            if txt_src.exists():
                txt_dst.write_bytes(txt_src.read_bytes())
            else:
                with zipfile.ZipFile(RAW / f"{p}.zip") as z:
                    txt_dst.write_bytes(z.read(f"{p}/{p}.txt"))
            n_txt += 1

    print(f"warped={n_warp} skipped={n_skip} txt_extracted={n_txt} missing_src={n_missing}")
    print(f"NEXT: prep_hyp3.py {out}/*_clip.tif")
    return 0


if __name__ == "__main__":
    sys.exit(main())

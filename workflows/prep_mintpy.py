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

from osgeo import gdal

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


def target_grid(stack: str):
    """(te=(xmin,ymin,xmax,ymax), width, height, epsg) from the custom velocity grid."""
    ref = VEL / f"{stack}_mean_velocity_los_highpass.tif"
    if not ref.exists():
        sys.exit(f"Custom velocity raster missing: {ref} — run Phase 2 first.")
    ds = gdal.Open(str(ref))
    gt = ds.GetGeoTransform()
    w, h = ds.RasterXSize, ds.RasterYSize
    left, top = gt[0], gt[3]
    right, bottom = left + w * gt[1], top + h * gt[5]
    epsg = ds.GetSpatialRef().GetAuthorityCode(None)
    return (left, bottom, right, top), w, h, epsg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stack", default="ASC_path27_frame106")
    args = ap.parse_args()
    stack = args.stack

    out = PROJECT_ROOT / "data" / "mintpy" / stack / "hyp3"
    out.mkdir(parents=True, exist_ok=True)

    products = keep_products(stack)
    te, w, h, epsg = target_grid(stack)
    print(f"{stack}: {len(products)} KEEP pairs -> {out}")
    print(f"target grid {w}x{h} EPSG:{epsg} te={tuple(round(x,1) for x in te)}")

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
            with zipfile.ZipFile(RAW / f"{p}.zip") as z:
                txt_dst.write_bytes(z.read(f"{p}/{p}.txt"))
            n_txt += 1

    print(f"warped={n_warp} skipped={n_skip} txt_extracted={n_txt} missing_src={n_missing}")
    print(f"NEXT: prep_hyp3.py {out}/*_clip.tif")
    return 0


if __name__ == "__main__":
    sys.exit(main())

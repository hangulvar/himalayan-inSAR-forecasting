#!/usr/bin/env python
"""inspect_mintpy_velocity.py — summarize a MintPy ERA5 velocity field on its own
terms (coverage, velocity distribution, temporal coherence). Used for the
disconnected DESC stacks, where there is NO custom-inverter result to cross-validate
against (crossval_mintpy.py covers the ASC case). gdal+numpy only — runs in either
image.

  docker compose run --rm mintpy python workflows/inspect_mintpy_velocity.py --stack DESC_path34_frame479
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from osgeo import gdal

gdal.UseExceptions()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read(path: Path, band: int = 1) -> np.ndarray:
    ds = gdal.Open(str(path))
    b = ds.GetRasterBand(band)
    a = b.ReadAsArray().astype(np.float64)
    nd = b.GetNoDataValue()
    if nd is not None:
        a[a == nd] = np.nan
    a[~np.isfinite(a)] = np.nan
    return a


def stats(label: str, v: np.ndarray) -> None:
    f = np.isfinite(v)
    n = int(f.sum())
    if n == 0:
        print(f"  {label}: no valid px")
        return
    vv = v[f]
    p1, p5, p50, p95, p99 = np.percentile(vv, [1, 5, 50, 95, 99])
    print(f"  {label}: n={n:,}  mean={vv.mean():+.1f}  std={vv.std():.1f}  "
          f"p1/5/50/95/99={p1:+.0f}/{p5:+.0f}/{p50:+.0f}/{p95:+.0f}/{p99:+.0f} mm/yr")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stack", default="DESC_path34_frame479")
    ap.add_argument("--coh-thr", type=float, default=0.7)
    ap.add_argument("--flag-velocity", type=float, default=100.0,
                    help="Report (do NOT remove) coh-masked pixels above this |mm/yr|.")
    args = ap.parse_args()

    mp = PROJECT_ROOT / "data" / "mintpy" / args.stack / "mintpy_out"
    vel = read(mp / "velocity_mintpy_era5.tif") * 1000.0   # m/yr -> mm/yr
    coh = read(mp / "temporalCoherence_mintpy.tif")
    if vel.shape != coh.shape:
        sys.exit(f"grid mismatch: vel={vel.shape} coh={coh.shape}")

    ny, nx = vel.shape
    cohmask = coh >= args.coh_thr
    print(f"stack={args.stack}  grid=({ny}, {nx})  coh_thr={args.coh_thr}")
    print(f"  velocity valid px       : {int(np.isfinite(vel).sum()):,} / {ny * nx:,}")
    print(f"  temporalCoherence>={args.coh_thr:.2f} : {int(cohmask.sum()):,}")
    stats("velocity (all valid)   ", vel)
    stats(f"velocity (coh>={args.coh_thr:.2f})    ", np.where(cohmask, vel, np.nan))
    fast = np.isfinite(vel) & cohmask & (np.abs(vel) > args.flag_velocity)
    print(f"  |v|>{args.flag_velocity:.0f} mm/yr & coh>={args.coh_thr:.2f} : "
          f"{int(fast.sum()):,} px (sanity flag — disconnected-network bias possible)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

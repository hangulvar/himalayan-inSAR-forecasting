#!/usr/bin/env python
"""crossval_mintpy.py — cross-validate the MintPy velocity against our custom SBAS
inverter on the shared grid, the FAIR way: mask MintPy by its own
temporalCoherence >= 0.7 (the custom result is already coh>=0.7 masked + high-passed).

Reads GeoTIFFs only (gdal + numpy + scipy), so it runs in either the `insar` or the
`mintpy` image. Inputs share the custom 309x353 grid because prep_mintpy.py clipped
MintPy's layers to it.

  docker compose run --rm mintpy python workflows/crossval_mintpy.py

[A] reproduces the step-2 comparison set (custom-valid pixels, MintPy unmasked) so
    the ERA5 effect is visible against the step-2 baseline (r=+0.28 raw / +0.39 hp).
[B] is the fair test: MintPy coh>=0.7 masked, over the common (custom-valid AND
    MintPy-coh>=0.7) pixels, vs custom raw / high-pass, plus a both-high-passed r.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from osgeo import gdal
from scipy.ndimage import gaussian_filter

gdal.UseExceptions()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read(path: Path, band: int = 1) -> np.ndarray:
    ds = gdal.Open(str(path))
    b = ds.GetRasterBand(band)
    a = b.ReadAsArray().astype(np.float32)
    nd = b.GetNoDataValue()
    if nd is not None:
        a[a == nd] = np.nan
    a[~np.isfinite(a)] = np.nan
    return a


def nan_gaussian_highpass(arr: np.ndarray, sigma: float) -> np.ndarray:
    """Same nan-aware high-pass as custom_sbas_inverter.nan_gaussian_highpass."""
    mask = np.isfinite(arr).astype(np.float32)
    filled = np.where(mask > 0, arr, 0.0).astype(np.float32)
    num = gaussian_filter(filled, sigma=sigma, mode="nearest")
    den = gaussian_filter(mask, sigma=sigma, mode="nearest")
    with np.errstate(invalid="ignore", divide="ignore"):
        low = np.where(den > 1e-3, num / den, np.nan).astype(np.float32)
    hp = (arr - low).astype(np.float32)
    hp[mask == 0] = np.nan
    return hp


def pearson(a: np.ndarray, b: np.ndarray, m: np.ndarray) -> float:
    x = a[m].astype(np.float64)
    y = b[m].astype(np.float64)
    x = x - x.mean()
    y = y - y.mean()
    denom = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / denom) if denom > 0 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stack", default="ASC_path27_frame106")
    ap.add_argument("--coh-thr", type=float, default=0.7)
    ap.add_argument("--hp-sigma-px", type=float, default=30.0)
    ap.add_argument("--mintpy-vel", default="velocity_mintpy_era5.tif",
                    help="MintPy velocity GeoTIFF under data/mintpy/<stack>/mintpy_out/")
    args = ap.parse_args()
    stack = args.stack

    vel = PROJECT_ROOT / "data" / "velocity"
    mp = PROJECT_ROOT / "data" / "mintpy" / stack / "mintpy_out"

    custom_raw = read(vel / f"{stack}_mean_velocity_los.tif")            # mm/yr, coh>=0.7
    custom_hp = read(vel / f"{stack}_mean_velocity_los_highpass.tif")    # band1 = high-pass
    mintpy_vel = read(mp / args.mintpy_vel) * 1000.0                     # m/yr -> mm/yr
    mintpy_coh = read(mp / "temporalCoherence_mintpy.tif")

    shapes = {custom_raw.shape, custom_hp.shape, mintpy_vel.shape, mintpy_coh.shape}
    if len(shapes) != 1:
        sys.exit(f"grid mismatch across rasters: {shapes}")

    custom_valid = np.isfinite(custom_raw)
    mp_cohmask = np.isfinite(mintpy_vel) & (mintpy_coh >= args.coh_thr)
    common = custom_valid & mp_cohmask & np.isfinite(custom_hp)

    print(f"stack={stack}  grid={custom_raw.shape}  coh_thr={args.coh_thr}")
    print(f"custom-valid (coh>=0.7) px : {int(custom_valid.sum()):,}")
    print(f"mintpy coh>={args.coh_thr:.2f} px        : {int(mp_cohmask.sum()):,}")
    print(f"common px                  : {int(common.sum()):,}")

    # [A] ERA5 velocity, NO MintPy mask, over the step-2 set (custom-valid pixels).
    setA = custom_valid & np.isfinite(mintpy_vel)
    setA_hp = setA & np.isfinite(custom_hp)
    print("\n[A] ERA5 vel, NO coh-mask  (step-2 baseline was no-tropo r=+0.28 raw / +0.39 hp):")
    print(f"    vs custom RAW : n={int(setA.sum()):,}  r={pearson(mintpy_vel, custom_raw, setA):+.3f}")
    print(f"    vs custom HP  : n={int(setA_hp.sum()):,}  r={pearson(mintpy_vel, custom_hp, setA_hp):+.3f}")

    # [B] ERA5 velocity, MintPy coh>=0.7 masked — the fair comparison.
    mintpy_masked = np.where(mp_cohmask, mintpy_vel, np.nan).astype(np.float32)
    mintpy_hp = nan_gaussian_highpass(mintpy_masked, args.hp_sigma_px)
    d = (mintpy_vel[common] - custom_raw[common]).astype(np.float64)
    d = d - d.mean()
    rms = float(np.sqrt((d * d).mean()))
    print("\n[B] ERA5 vel, MintPy coh>=0.7 masked  (FAIR test):")
    print(f"    vs custom RAW         : r={pearson(mintpy_vel, custom_raw, common):+.3f}   "
          f"RMS(offset-removed)={rms:.1f} mm/yr")
    print(f"    vs custom HP          : r={pearson(mintpy_vel, custom_hp, common):+.3f}")
    print(f"    mintpy_HP vs custom HP: r={pearson(mintpy_hp, custom_hp, common):+.3f}")
    print(f"    std  mintpy={np.nanstd(mintpy_vel[common]):.1f}  "
          f"custom_raw={np.nanstd(custom_raw[common]):.1f}  "
          f"custom_hp={np.nanstd(custom_hp[common]):.1f}  (mm/yr)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

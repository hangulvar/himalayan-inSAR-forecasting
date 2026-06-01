#!/usr/bin/env python
"""slope_velocity.py — project the LOS velocity onto the downslope direction (V_slope).

WHY: our InSAR velocity is one-dimensional — the component of motion ALONG the radar
line-of-sight (LOS). A creeping slope actually moves DOWNHILL, so the landslide-relevant
quantity is the slope-parallel velocity. With a single look (ASC only; the DESC stacks
were dumped as too noisy) we cannot do a full 3-D decomposition, but we CAN project the
LOS velocity onto the steepest-descent direction under the standard assumption that the
motion is downslope (Cascini et al. 2010; Notti et al. 2014):

    V_slope = V_LOS / C ,    C = d . l

where l is the unit LOS vector (ground->satellite, from HyP3 lv_theta/lv_phi) and d is the
unit downslope vector (downhill + downward, from the DEM slope+aspect). C is the "LOS
sensitivity": |C|~1 where the downslope faces along the LOS (well observed), |C|~0 where the
downslope is perpendicular to the LOS (a BLIND SPOT for this geometry). We mask |C| < c-min
as ill-conditioned. Because |C|<=1, the projection de-projects (amplifies) the LOS magnitude,
sharpening both the creep magnitude and the inverse-velocity TTF; the sensitivity map makes
the ASC single-look blind spots explicit. This is the cheap single-look approximation of the
(DESC-deferred) ASC/DESC vertical+EW decomposition.

Sign convention: V_LOS<0 = motion away from sensor = downslope; for a slope whose downhill
faces away from the satellite, d.l<0, so V_slope = V_LOS/C > 0 (downslope speed positive).

LOS geometry: l_E=cos(lv_theta)cos(lv_phi), l_N=cos(lv_theta)sin(lv_phi), l_U=sin(lv_theta)
(lv_theta = elevation from horizontal, lv_phi = azimuth CCW from East, both radians; ASF HyP3).

Outputs per stack -> data/velocity/:
  *_v_slope.tif          slope-parallel velocity (mm/yr; + = downslope)
  *_los_sensitivity.tif  |C| in [0,1] (downslope observability)
  *_v_slope_report.{json,md}   creep counts LOS vs slope-parallel + blind-spot fraction

  docker compose run --rm insar python workflows/slope_velocity.py
  python workflows/slope_velocity.py --stack ASC_path27_frame106
"""

from __future__ import annotations

import os
import sys

# BLAS DLL bootstrap (see custom_sbas_inverter.py / error_history_log.md).
if sys.platform == "win32":
    _dll = [os.path.join(sys.prefix, "Library", "bin"),
            os.path.join(sys.prefix, "Library", "mingw-w64", "bin"),
            os.path.join(sys.prefix, "Scripts")]
    os.environ["PATH"] = os.pathsep.join([d for d in _dll if os.path.isdir(d)]
                                         + [os.environ.get("PATH", "")])

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

from geomechanical_engine import find_dem_for_stack, load_master_grid

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VEL_DIR = PROJECT_ROOT / "data" / "velocity"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(LOG_DIR / "slope_velocity.log", encoding="utf-8")],
)
logger = logging.getLogger("vslope")

CREEP_THR = -15.0      # LOS creep threshold (mm/yr), matches the orchestrator


def reproject_to_grid(src_path: Path, transform, crs, w, h) -> np.ndarray:
    """Bilinear-resample a single-band raster onto the master grid (no value clamp)."""
    dst = np.full((h, w), np.nan, dtype=np.float32)
    with rasterio.open(src_path) as src:
        reproject(source=rasterio.band(src, 1), destination=dst,
                  src_transform=src.transform, src_crs=src.crs,
                  dst_transform=transform, dst_crs=crs,
                  resampling=Resampling.bilinear,
                  src_nodata=src.nodata, dst_nodata=np.nan)
    return dst


def downslope_unit(dem: np.ndarray, pixel_m: float):
    """Unit downslope vector (E,N,U), pointing downhill + downward, and slope (rad)."""
    filled = np.nan_to_num(dem, nan=np.nanmean(dem))
    dz_dy, dz_dx = np.gradient(filled, pixel_m, pixel_m)   # d/drow, d/dcol
    dz_dE = dz_dx
    dz_dN = -dz_dy                                          # row increases southward
    g = np.hypot(dz_dE, dz_dN)                             # = tan(slope)
    slope = np.arctan(g)
    cosS, sinS = np.cos(slope), np.sin(slope)
    with np.errstate(invalid="ignore", divide="ignore"):
        hE = np.where(g > 0, -dz_dE / g, 0.0)             # downhill horizontal unit (E)
        hN = np.where(g > 0, -dz_dN / g, 0.0)
    dE = cosS * hE
    dN = cosS * hN
    dU = -sinS
    for a in (dE, dN, dU, slope):
        a[np.isnan(dem)] = np.nan
    return dE, dN, dU, slope


def los_unit(lv_theta: np.ndarray, lv_phi: np.ndarray):
    """Unit LOS vector (ground->satellite) in ENU from HyP3 lv_theta/lv_phi (radians)."""
    ct = np.cos(lv_theta)
    return ct * np.cos(lv_phi), ct * np.sin(lv_phi), np.sin(lv_theta)


def write_raster(path: Path, arr: np.ndarray, transform, crs):
    prof = {"driver": "GTiff", "height": arr.shape[0], "width": arr.shape[1],
            "count": 1, "dtype": "float32", "crs": crs, "transform": transform,
            "nodata": np.nan, "compress": "deflate"}
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(arr.astype(np.float32), 1)


def process_stack(stack: str, c_min: float, min_slope_deg: float,
                  velocity_name: str) -> dict:
    vel_path = VEL_DIR / f"{stack}_{velocity_name}.tif"
    if not vel_path.exists():
        raise SystemExit(f"velocity not found: {vel_path}")
    _, transform, crs, w, h = load_master_grid(vel_path)
    pixel_m = abs(transform.a)

    with rasterio.open(vel_path) as s:
        vlos = s.read(1)
        if s.nodata is not None:
            vlos = np.where(vlos == s.nodata, np.nan, vlos)

    dem_path = find_dem_for_stack(stack)              # _dem.tif of the first KEEP product
    prod_dir, prod = dem_path.parent, dem_path.stem.rsplit("_dem", 1)[0]
    lv_theta = reproject_to_grid(prod_dir / f"{prod}_lv_theta.tif", transform, crs, w, h)
    lv_phi = reproject_to_grid(prod_dir / f"{prod}_lv_phi.tif", transform, crs, w, h)
    dem = reproject_to_grid(dem_path, transform, crs, w, h)
    dem[(dem < -100) | (dem > 9000)] = np.nan

    dE, dN, dU, slope = downslope_unit(dem, pixel_m)
    lE, lN, lU = los_unit(lv_theta, lv_phi)
    C = dE * lE + dN * lN + dU * lU                   # LOS sensitivity to downslope motion
    sens = np.abs(C)

    valid = np.isfinite(vlos) & np.isfinite(C) & np.isfinite(slope)
    well_obs = valid & (sens >= c_min) & (np.degrees(slope) >= min_slope_deg)

    vslope = np.full_like(vlos, np.nan, dtype=np.float32)
    with np.errstate(invalid="ignore", divide="ignore"):
        vslope[well_obs] = (vlos[well_obs] / C[well_obs]).astype(np.float32)

    sens_out = np.where(valid, sens, np.nan).astype(np.float32)
    write_raster(VEL_DIR / f"{stack}_v_slope.tif", vslope, transform, crs)
    write_raster(VEL_DIR / f"{stack}_los_sensitivity.tif", sens_out, transform, crs)

    los_creep = valid & (vlos < CREEP_THR)
    slope_creep = well_obs & (vslope > -CREEP_THR)    # +ve = downslope
    amp = (np.abs(vslope[los_creep & well_obs]) /
           np.maximum(np.abs(vlos[los_creep & well_obs]), 1e-6))
    rep = {
        "stack": stack, "velocity_layer": velocity_name,
        "c_min": c_min, "min_slope_deg": min_slope_deg,
        "n_valid_px": int(valid.sum()),
        "n_well_observed_px": int(well_obs.sum()),
        "blind_fraction": round(float(1 - well_obs.sum() / max(valid.sum(), 1)), 3),
        "median_abs_sensitivity": round(float(np.nanmedian(sens[valid])), 3),
        "los_creep_px": int(los_creep.sum()),
        "slope_creep_px": int(slope_creep.sum()),
        "median_amplification": round(float(np.nanmedian(amp)), 2) if amp.size else None,
        "max_v_slope_mm_yr": round(float(np.nanmax(np.abs(vslope))), 1)
        if np.isfinite(vslope).any() else None,
    }
    logger.info(f"[{stack}] valid={rep['n_valid_px']:,} well-observed={rep['n_well_observed_px']:,} "
                f"(blind {rep['blind_fraction']*100:.0f}%) | LOS-creep={rep['los_creep_px']:,} "
                f"-> slope-creep={rep['slope_creep_px']:,} | median |C|={rep['median_abs_sensitivity']} "
                f"amp x{rep['median_amplification']}")
    write_md(VEL_DIR / f"{stack}_v_slope_report.md", rep)
    (VEL_DIR / f"{stack}_v_slope_report.json").write_text(json.dumps(rep, indent=2),
                                                          encoding="utf-8")
    return rep


def write_md(path: Path, r: dict) -> None:
    lines = [
        f"# Slope-parallel velocity (V_slope) — {r['stack']}", "",
        "LOS velocity projected onto the downslope direction (V_slope = V_LOS / (d.l)).",
        f"Velocity layer: `{r['velocity_layer']}`. Masks: |C| < {r['c_min']} (blind) and "
        f"slope < {r['min_slope_deg']} deg.", "",
        f"- valid pixels: **{r['n_valid_px']:,}**; well-observed (kept): **{r['n_well_observed_px']:,}** "
        f"-> **{r['blind_fraction']*100:.0f}%** of valid ground is a single-look BLIND SPOT "
        f"(downslope ~perpendicular to LOS).",
        f"- median |C| (downslope observability): **{r['median_abs_sensitivity']}**.",
        f"- creep pixels: **{r['los_creep_px']:,}** in LOS (< {CREEP_THR} mm/yr) -> "
        f"**{r['slope_creep_px']:,}** downslope (V_slope > {-CREEP_THR} mm/yr, well-observed).",
        f"- median de-projection amplification |V_slope|/|V_LOS| over LOS-creeping px: "
        f"**x{r['median_amplification']}** (peak |V_slope| {r['max_v_slope_mm_yr']} mm/yr).", "",
        "_Honest scope: ASC single-look projection ASSUMES motion is purely downslope; it cannot "
        "see motion on slopes facing across the LOS (the blind fraction above). A true vertical+EW "
        "decomposition needs the (currently dumped) descending stacks or persistent scatterers._",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def stacks_with_velocity(velocity_name: str):
    return sorted(p.name[: -(len(velocity_name) + 5)]
                  for p in VEL_DIR.glob(f"*_{velocity_name}.tif"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stack", help="single stack label (default: all ASC stacks with velocity)")
    ap.add_argument("--velocity-name", default="mean_velocity_los_highpass",
                    help="velocity raster suffix to project (default: high-pass)")
    ap.add_argument("--c-min", type=float, default=0.3,
                    help="mask |C| below this (ill-conditioned / blind to downslope)")
    ap.add_argument("--min-slope-deg", type=float, default=10.0)
    args = ap.parse_args()

    stacks = ([args.stack] if args.stack
              else [s for s in stacks_with_velocity(args.velocity_name) if s.startswith("ASC")])
    if not stacks:
        raise SystemExit("no stacks found")
    for st in stacks:
        process_stack(st, args.c_min, args.min_slope_deg, args.velocity_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

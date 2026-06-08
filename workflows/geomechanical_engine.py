#!/usr/bin/env python
"""
geomechanical_engine.py — Phase 3: from velocity to a hazard map (MVP).

Turns terrain + InSAR velocity into a slope-stability hazard map over the
pathfinder stack's footprint. Pipeline:

  1. Use the velocity raster's grid as the master grid (EPSG:32643, 80 m).
  2. Reproject the bundled HyP3 DEM onto that exact grid.
  3. Slope angle (β) from the DEM via numpy gradients.
  4. Topographic Wetness Index (TWI) via a simple D8 flow accumulation
     (where water tends to collect — wetter ground is weaker).
  5. Infinite-Slope Factor of Safety (FS) for two end-member saturations:
        FS = [ c' + (γ − m·γ_w)·z·cos²β·tanφ' ] / [ γ·z·sinβ·cosβ ]
     - m = 0  → FS_dry (dry-season baseline)
     - m = 1  → FS_saturated (monsoon worst case)
     FS < 1 ⇒ the slope is theoretically unstable.
  6. HAZARD FUSION (the headline output): combine the *physics* (FS) with the
     *observation* (measured InSAR creep) into a 3-class hazard map, matching
     the project's Phase-4 rule "FS < 1.0 AND velocity < −15 mm/yr".

DESIGN NOTES (MVP):
  * DEM is the 80 m bundled HyP3 DEM — already co-registered, no GEE/download.
    LIMITATION: 80 m under-resolves slope in steep terrain, biasing FS toward
    "stable". Upgrading to the 12.5 m ALOS DEM is a documented production task.
  * InSAR velocity is a SEPARATE evidence layer, not a term inside FS (the
    physically honest reading of "active stress multiplier").
  * Soil parameters are literature defaults for Himalayan colluvium, all
    CLI-overridable. They are assumptions, not measurements.

Sign convention: LOS velocity negative = motion away from sensor
(subsidence / downslope) = the "creep" direction we flag.

Usage:
    python workflows/geomechanical_engine.py
    python workflows/geomechanical_engine.py --phi 35 --cohesion-kpa 8 \
        --soil-depth-m 4 --vel-creep-thr -15
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
import csv
import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QA_DIR = PROJECT_ROOT / "data" / "qa_masks"
QUARANTINE_CSV = QA_DIR / "_quarantine_list.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed_tiffs"
VEL_DIR = PROJECT_ROOT / "data" / "velocity"
OUT_DIR = PROJECT_ROOT / "data" / "hazard"
LOG_DIR = PROJECT_ROOT / "logs"

GAMMA_W = 9.81  # unit weight of water, kN/m³

LOG_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(LOG_DIR / "geomechanical_engine.log", encoding="utf-8")],
)
logger = logging.getLogger("geomech")


# ------------------------------------------------------------------------------
def find_dem_for_stack(stack: str) -> Path:
    """Return the _dem.tif of the first KEEP product of a stack."""
    rows = list(csv.DictReader(QUARANTINE_CSV.open(encoding="utf-8")))
    keep = sorted(r["product"] for r in rows
                  if r["stack"] == stack and r["decision"] == "KEEP")
    if not keep:
        raise SystemExit(f"No KEEP products for {stack}")
    dem = PROCESSED_DIR / keep[0] / f"{keep[0]}_dem.tif"
    if not dem.exists():
        raise SystemExit(f"DEM not found: {dem}")
    return dem


def load_master_grid(vel_path: Path):
    with rasterio.open(vel_path) as s:
        return s.profile.copy(), s.transform, s.crs, s.width, s.height


def reproject_dem(dem_path: Path, dst_transform, dst_crs, w, h) -> np.ndarray:
    """Resample the DEM onto the master grid (bilinear)."""
    dst = np.full((h, w), np.nan, dtype=np.float32)
    with rasterio.open(dem_path) as src:
        src_nodata = src.nodata
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform, src_crs=src.crs,
            dst_transform=dst_transform, dst_crs=dst_crs,
            resampling=Resampling.bilinear,
            src_nodata=src_nodata, dst_nodata=np.nan,
        )
    # Mask implausible elevations (DEM nodata sentinels / water artifacts).
    dst[(dst < -100) | (dst > 9000)] = np.nan
    return dst


# ------------------------------------------------------------------------------
def compute_slope(dem: np.ndarray, pixel_m: float) -> np.ndarray:
    """Slope angle (radians) from DEM via central differences."""
    # np.gradient returns d/drow, d/dcol; spacing = pixel size in metres.
    dz_dy, dz_dx = np.gradient(np.nan_to_num(dem, nan=np.nanmean(dem)), pixel_m, pixel_m)
    slope = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope[np.isnan(dem)] = np.nan
    return slope.astype(np.float32)


def compute_twi(dem: np.ndarray, slope_rad: np.ndarray, pixel_m: float) -> np.ndarray:
    """Topographic Wetness Index = ln( a / tanβ ) via a simple D8 accumulation.

    a = upslope contributing area per unit contour width. This is an MVP-grade
    D8 (steepest-descent, no rigorous depression filling) — adequate for the
    small, steep AOI; documented as approximate.
    """
    h, w = dem.shape
    valid = np.isfinite(dem)
    elev = np.where(valid, dem, -9e9).astype(np.float64)

    # D8 neighbour offsets and distances.
    nbrs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    dist = [np.sqrt(2), 1, np.sqrt(2), 1, 1, np.sqrt(2), 1, np.sqrt(2)]

    accum = np.ones((h, w), dtype=np.float64)  # each cell starts with itself
    # Process from highest to lowest so flow cascades downslope in one pass.
    order = np.argsort(elev.ravel())[::-1]
    rows, cols = np.unravel_index(order, (h, w))
    for r, c in zip(rows, cols):
        if not valid[r, c]:
            continue
        z0 = elev[r, c]
        best_drop, best = 0.0, None
        for (dr, dc), dd in zip(nbrs, dist):
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w and valid[rr, cc]:
                drop = (z0 - elev[rr, cc]) / dd
                if drop > best_drop:
                    best_drop, best = drop, (rr, cc)
        if best is not None:
            accum[best] += accum[r, c]

    a = accum * pixel_m  # area per unit contour width (cells × cellwidth)
    tan_b = np.tan(np.clip(slope_rad, np.radians(0.5), None))
    twi = np.log(a / tan_b)
    twi[~valid] = np.nan
    return twi.astype(np.float32)


def factor_of_safety(slope_rad, c_kpa, phi_deg, gamma, z, m):
    """Infinite-slope FS for saturation fraction m (0=dry, 1=saturated)."""
    b = slope_rad
    cosb, sinb = np.cos(b), np.sin(b)
    tan_phi = np.tan(np.radians(phi_deg))
    num = c_kpa + (gamma - m * GAMMA_W) * z * cosb**2 * tan_phi
    den = gamma * z * sinb * cosb
    with np.errstate(invalid="ignore", divide="ignore"):
        fs = np.where(den > 1e-6, num / den, np.nan).astype(np.float32)
    # Near-flat ground isn't a translational-slide hazard → mark very stable.
    fs[np.degrees(b) < 2.0] = 5.0
    fs[np.isnan(slope_rad)] = np.nan
    return np.clip(fs, 0, 5).astype(np.float32)


# ------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stack", default="ASC_path27_frame106")
    # --- Soil shear-strength parameters -------------------------------------------------
    # CALIBRATED (2026-06-03) from the GSI meso-scale (1:10,000) landslide-susceptibility
    # field study of the NH-244 Batote(Chakwa Nala)->Ganpat Bridge corridor, Ramban/Doda,
    # J&K (GSI 2024-25 field season; brief in Research/LandslideInventory/). That study
    # measured a friction angle of phi = 36.4-39.1 deg on site overburden (silty colluvium/
    # scree/RBM, 0.5-20 m thick, >75% fines, moisture-sensitive) -> we adopt phi=36 deg
    # (conservative end), replacing the generic literature 32 deg. gamma=19 and z=3 m sit
    # within the measured ranges.
    #
    # MATRIC-SUCTION DRY/WET COHESION SPLIT (2026-06-08, Area 7 #4 — was deferred, now done):
    # the same study reports good DRY strength but "significant reduction when wet" + "rapid
    # strength loss during saturation" (low-plasticity fines). Unsaturated soil carries an
    # APPARENT cohesion from matric suction that VANISHES as it saturates (extended Mohr-
    # Coulomb / Fredlund). So we split cohesion into a DRY end-member (c' + suction) and a
    # WET one (c' alone): the engine builds FS_dry with c_dry and FS_saturated with c_wet.
    # Because cohesion interpolates linearly in m, FS stays EXACTLY linear in m, so the
    # downstream FS_real=(1-m)*FS_dry+m*FS_saturated coupling (orchestrator, per-zone m*) is
    # unchanged. c_dry = GSI dry-cohesion magnitude (brief: "mean 18.5 kg/cm2"; taken
    # literally that is ~1814 kPa = rock-like and implausible for this silty colluvium, so we
    # INTERPRET the magnitude as ~18.5 kPa — physically credible for suction-enhanced dry
    # fines; FLAG for confirmation vs the source PDF). c_wet = 5 kPa (the prior conservative
    # wet value; FS_saturated is therefore UNCHANGED from the pre-split model). A nonlinear
    # soil-water-retention (van Genuchten) suction curve is the next refinement.
    ap.add_argument("--cohesion-dry-kpa", type=float, default=18.5,
                    help="dry/unsaturated cohesion kPa = c' + matric-suction apparent cohesion "
                         "(GSI LSM dry, magnitude-interpreted; used for FS_dry)")
    ap.add_argument("--cohesion-wet-kpa", type=float, default=5.0,
                    help="saturated effective cohesion kPa (suction gone; used for FS_saturated)")
    ap.add_argument("--phi", type=float, default=36.0,
                    help="friction angle deg (GSI LSM Ramban/Doda: 36.4-39.1; default = conservative 36)")
    ap.add_argument("--gamma", type=float, default=19.0, help="soil unit weight kN/m³")
    ap.add_argument("--soil-depth-m", type=float, default=3.0,
                    help="failure depth z (GSI LSM overburden 0.5-20 m; 3 m = shallow translational)")
    ap.add_argument("--fs-fail", type=float, default=1.0)
    ap.add_argument("--fs-marginal", type=float, default=1.3)
    ap.add_argument("--vel-creep-thr", type=float, default=-15.0,
                    help="LOS velocity mm/yr below which a pixel counts as creeping")
    ap.add_argument("--use-vslope", action="store_true",
                    help="Fuse creep from the slope-parallel velocity (*_v_slope.tif, downslope-"
                         "projected, blind pixels excluded) instead of raw LOS. Writes a distinct "
                         "*_hazard_class_vslope.tif (FS/slope/twi are velocity-independent and kept "
                         "canonical), so the LOS hazard baseline is preserved.")
    args = ap.parse_args()

    stack = args.stack
    logger.info(f"=== Geomechanical engine for {stack} ===")
    logger.info(f"Soil: c_dry={args.cohesion_dry_kpa} kPa (w/ matric suction), "
                f"c_wet={args.cohesion_wet_kpa} kPa (saturated), phi={args.phi}°, "
                f"gamma={args.gamma} kN/m³, z={args.soil_depth_m} m")

    vel_hp = VEL_DIR / f"{stack}_mean_velocity_los_highpass.tif"
    if not vel_hp.exists():
        raise SystemExit(f"Velocity raster missing: {vel_hp} — run Phase 2 first.")

    profile, transform, crs, w, h = load_master_grid(vel_hp)
    pixel_m = abs(transform.a)
    logger.info(f"Master grid: {w}x{h} @ {pixel_m} m, {crs}")

    dem = reproject_dem(find_dem_for_stack(stack), transform, crs, w, h)
    logger.info(f"DEM reprojected. Valid pixels: {np.isfinite(dem).sum():,}/{w*h:,}")

    slope = compute_slope(dem, pixel_m)
    slope_deg = np.degrees(slope)
    sd = slope_deg[np.isfinite(slope_deg)]
    logger.info(f"Slope (deg): median={np.median(sd):.1f} p95={np.percentile(sd,95):.1f} "
                f"max={sd.max():.1f}")

    twi = compute_twi(dem, slope, pixel_m)

    # Matric-suction split: dry uses suction-enhanced cohesion, saturated uses c' (suction gone).
    fs_dry = factor_of_safety(slope, args.cohesion_dry_kpa, args.phi, args.gamma,
                              args.soil_depth_m, m=0.0)
    fs_sat = factor_of_safety(slope, args.cohesion_wet_kpa, args.phi, args.gamma,
                              args.soil_depth_m, m=1.0)
    for name, fs in (("dry", fs_dry), ("saturated", fs_sat)):
        v = fs[np.isfinite(fs)]
        frac_fail = 100.0 * np.mean(v < args.fs_fail)
        logger.info(f"FS_{name}: median={np.median(v):.2f} "
                    f"%<1.0 (unstable)={frac_fail:.1f}%")

    # --- Hazard fusion: physics (FS_saturated) + observation (InSAR creep) ---
    creep_src = (VEL_DIR / f"{stack}_v_slope.tif") if args.use_vslope else vel_hp
    if not creep_src.exists():
        raise SystemExit(f"Creep velocity raster missing: {creep_src} — "
                         f"run {'slope_velocity.py' if args.use_vslope else 'Phase 2'} first.")
    with rasterio.open(creep_src) as s:
        vel = s.read(1)  # mm/yr, same grid; NaN where no measurement
    if args.use_vslope:
        vel = -vel       # +downslope -> negative, matching the creep-threshold sign
    creep = np.isfinite(vel) & (vel < args.vel_creep_thr)
    unstable = np.isfinite(fs_sat) & (fs_sat < args.fs_fail)
    marginal = np.isfinite(fs_sat) & (fs_sat < args.fs_marginal)

    hazard = np.full((h, w), np.nan, dtype=np.float32)
    defined = np.isfinite(fs_sat)
    hazard[defined] = 0.0                              # LOW
    hazard[marginal | creep] = 1.0                     # WATCH (low FS OR creep)
    hazard[unstable & creep] = 2.0                     # HIGH (low FS AND creep)

    n_low = int(np.sum(hazard == 0))
    n_watch = int(np.sum(hazard == 1))
    n_high = int(np.sum(hazard == 2))
    n_creep = int(np.sum(creep))
    logger.info(f"Hazard classes — LOW={n_low:,} WATCH={n_watch:,} HIGH={n_high:,} "
                f"(creep pixels observed: {n_creep:,})")

    # --- Write outputs ---
    prof = dict(profile, dtype="float32", count=1, nodata=np.nan, compress="lzw")
    if args.use_vslope:
        # FS/slope/twi are velocity-independent (identical to the LOS run); write only the
        # creep-fused hazard, to a distinct name so the LOS baseline raster stands.
        outputs = {"hazard_class_vslope": hazard}
    else:
        outputs = {
            "slope_deg": slope_deg.astype(np.float32),
            "twi": twi,
            "FS_dry": fs_dry,
            "FS_saturated": fs_sat,
            "hazard_class": hazard,
        }
    for name, arr in outputs.items():
        path = OUT_DIR / f"{stack}_{name}.tif"
        with rasterio.open(path, "w", **prof) as d:
            d.write(arr, 1)
        logger.info(f"Wrote {path.name}")

    logger.info("Hazard class legend: 0=LOW, 1=WATCH (low FS OR creep), "
                "2=HIGH (low FS AND creep), NaN=undefined.")
    if n_high > 0:
        logger.info(f"*** {n_high} HIGH-hazard pixel(s): unstable slope WITH "
                    f"measured creep — these are the Phase-4 alert candidates. ***")
    return 0


if __name__ == "__main__":
    sys.exit(main())

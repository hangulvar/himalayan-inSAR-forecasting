#!/usr/bin/env python
"""
phase_elevation_audit.py — Phase 1.2 Part B: Atmospheric Contamination Detection

Test each masked LOS displacement raster for tropospheric contamination by
correlating per-pixel displacement against per-pixel elevation.

Physics:
  Water vapor in the lower troposphere slows radar propagation. The integrated
  delay along each ray path depends on the column of air it traverses, which
  scales with elevation: low-lying pixels see more atmosphere than ridge-top
  pixels. When the troposphere differs significantly between the two scenes of
  an interferogram, the residual phase delay manifests as a *displacement
  signal that correlates with the DEM*. Real ground motion (slope creep,
  subsidence) does not in general correlate with topography, so a high
  correlation is the telltale sign that we are seeing atmosphere, not motion.

Thresholds (per the project context):
  R^2 > 0.5     → strongly contaminated; QUARANTINE.
  R^2 in 0.3-0.5 → moderate; flag as CONCERN.
  R^2 < 0.3     → atmospherically clean enough.

For each product we report:
  - Pearson r and r^2 between masked displacement and DEM elevation.
  - Best-fit slope (m per metre of elevation) and intercept.
  - Number of valid pixels (must survive coherence mask AND have valid DEM).
  - Elevation range over which the correlation was measured (to flag cases
    where surviving pixels cluster at one altitude, making the r unreliable).

Outputs:
  data/qa_masks/_atmospheric_audit.csv
"""

from __future__ import annotations

import csv
import gc
import logging
import sys
from pathlib import Path

import numpy as np
import rasterio

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MASKED_DIR = PROJECT_ROOT / "data" / "qa_masks"
PRODUCT_DIR = PROJECT_ROOT / "data" / "processed_tiffs"
LOG_DIR = PROJECT_ROOT / "logs"
AUDIT_CSV = MASKED_DIR / "_atmospheric_audit.csv"

# Quarantine thresholds. The project context specifies R^2 > 0.5 as the strict
# quarantine line; 0.3 is a more conservative "watch list" threshold.
QUARANTINE_R2 = 0.5
CONCERN_R2 = 0.3

# A correlation computed on fewer than this many pixels is statistically weak;
# we still record it but flag low_sample=True.
MIN_VALID_PIXELS = 1000
# A correlation across a narrow elevation band is geophysically suspect — there
# isn't enough vertical relief for atmosphere to express itself.
MIN_ELEVATION_RANGE_M = 200.0

# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "phase_elevation_audit.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("phase_elevation_audit")


# ------------------------------------------------------------------------------
# Core
# ------------------------------------------------------------------------------
def find_inputs(product_name: str) -> tuple[Path | None, Path | None]:
    """Return (masked_disp_path, dem_path) for a single product."""
    masked = MASKED_DIR / product_name / f"{product_name}_masked_disp.tif"
    dem_candidates = list((PRODUCT_DIR / product_name).glob("*_dem.tif"))
    dem = dem_candidates[0] if dem_candidates else None
    return (masked if masked.exists() else None), dem


def classify(r2: float, n_valid: int, elev_range: float) -> str:
    """Map numeric audit result to a categorical label."""
    if n_valid < MIN_VALID_PIXELS or elev_range < MIN_ELEVATION_RANGE_M:
        return "INSUFFICIENT_DATA"
    if r2 >= QUARANTINE_R2:
        return "QUARANTINE"
    if r2 >= CONCERN_R2:
        return "CONCERN"
    return "CLEAN"


def audit_product(product_name: str) -> dict:
    """Compute the displacement-vs-elevation correlation for a single product."""
    masked_path, dem_path = find_inputs(product_name)
    if masked_path is None or dem_path is None:
        return {
            "product": product_name,
            "status": "missing_inputs",
            "masked_disp_found": masked_path is not None,
            "dem_found": dem_path is not None,
        }

    with rasterio.open(masked_path) as src:
        disp = src.read(1)  # float32, NaN on masked pixels
        disp_nodata = src.nodata

    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype(np.float32, copy=False)
        dem_nodata = src.nodata

    if disp.shape != dem.shape:
        return {
            "product": product_name,
            "status": f"shape_mismatch_disp={disp.shape}_dem={dem.shape}",
        }

    # Build the valid-pixel mask: both arrays must have real values.
    disp_valid = ~np.isnan(disp)
    dem_valid = (
        ~np.isnan(dem)
        if dem_nodata is None or np.isnan(dem_nodata)
        else (dem != dem_nodata) & ~np.isnan(dem)
    )
    both_valid = disp_valid & dem_valid

    n_valid = int(np.sum(both_valid))
    if n_valid < 2:
        return {
            "product": product_name,
            "status": "no_valid_overlap",
            "n_valid_pixels": n_valid,
        }

    d = disp[both_valid].astype(np.float64, copy=False)
    z = dem[both_valid].astype(np.float64, copy=False)

    elev_min = float(z.min())
    elev_max = float(z.max())
    elev_range = elev_max - elev_min

    # Pearson r computed manually, NOT via np.corrcoef.
    # On Windows with numpy 2.x + MKL, np.corrcoef -> np.cov crashes with
    # Windows fatal exception 0xC06D007F on multi-million-element inputs.
    # The manual formula is just sums + products, no LAPACK call.
    z_mean = float(z.mean())
    d_mean = float(d.mean())
    z_dev = z - z_mean
    d_dev = d - d_mean
    cov_zd = float(np.mean(z_dev * d_dev))
    var_z = float(np.mean(z_dev * z_dev))
    var_d = float(np.mean(d_dev * d_dev))
    if var_z > 0 and var_d > 0:
        r = cov_zd / (np.sqrt(var_z) * np.sqrt(var_d))
        slope = cov_zd / var_z
        intercept = d_mean - slope * z_mean
    else:
        r = float("nan")
        slope = float("nan")
        intercept = float("nan")
    r2 = r * r if not np.isnan(r) else float("nan")

    label = classify(r2, n_valid, elev_range)

    # Cleanup
    del disp, dem, disp_valid, dem_valid, both_valid, d, z, z_dev, d_dev
    gc.collect()

    return {
        "product": product_name,
        "status": "ok",
        "n_valid_pixels": n_valid,
        "elev_min_m": round(elev_min, 1),
        "elev_max_m": round(elev_max, 1),
        "elev_range_m": round(elev_range, 1),
        "pearson_r": round(r, 4),
        "r_squared": round(r2, 4),
        "slope_m_per_m": round(slope, 6),
        "intercept_m": round(intercept, 6),
        "classification": label,
    }


# ------------------------------------------------------------------------------
# Driver
# ------------------------------------------------------------------------------
def main() -> int:
    if not MASKED_DIR.exists():
        logger.error(f"Masked products dir missing: {MASKED_DIR}")
        return 1

    product_names = sorted(
        d.name for d in MASKED_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    )
    logger.info(f"Found {len(product_names)} masked product directories.")

    results: list[dict] = []
    counts = {"QUARANTINE": 0, "CONCERN": 0, "CLEAN": 0, "INSUFFICIENT_DATA": 0, "FAIL": 0}

    for i, name in enumerate(product_names, start=1):
        result = audit_product(name)
        results.append(result)
        if result["status"] != "ok":
            counts["FAIL"] += 1
            logger.warning(f"[{i:>2}/{len(product_names)}] FAIL {name} ({result['status']})")
            continue
        cls = result["classification"]
        counts[cls] += 1
        logger.info(
            f"[{i:>2}/{len(product_names)}] {cls:<18s} {name}  "
            f"R^2={result['r_squared']:.3f}  "
            f"n={result['n_valid_pixels']:>8d}  "
            f"elev={result['elev_min_m']:.0f}-{result['elev_max_m']:.0f}m"
        )

    # --- Write CSV ---
    if results:
        fieldnames: list[str] = []
        for r in results:
            for k in r.keys():
                if k not in fieldnames:
                    fieldnames.append(k)
        with open(AUDIT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in results:
                w.writerow(row)
        logger.info(f"Wrote audit CSV: {AUDIT_CSV}")

    # --- Summary ---
    logger.info("-" * 60)
    logger.info("Classification summary:")
    for label in ("CLEAN", "CONCERN", "QUARANTINE", "INSUFFICIENT_DATA", "FAIL"):
        logger.info(f"  {label:<18s} : {counts[label]:>3d}")

    if counts["QUARANTINE"] > 0:
        logger.info("Quarantine candidates (R^2 > 0.5):")
        for r in results:
            if r.get("classification") == "QUARANTINE":
                logger.info(
                    f"  {r['product']}  R^2={r['r_squared']:.3f}  "
                    f"slope={r['slope_m_per_m']:.6f} m/m"
                )

    return 0 if counts["FAIL"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

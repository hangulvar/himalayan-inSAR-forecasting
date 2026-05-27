#!/usr/bin/env python
"""
feature_engineering.py — Phase 1.2 Part A: Coherence Masking

For each HyP3 INSAR_GAMMA product under data/processed_tiffs/, this script:

  1. Opens the unwrapped phase + coherence GeoTIFFs (iteratively, one product
     at a time, to keep RAM well under 16 GB on a single-host machine).
  2. Converts unwrapped phase (radians) to Line-of-Sight displacement (metres)
     using the Sentinel-1 C-band wavelength. ASF/HyP3 sign convention:
         displacement = -phase * (lambda / 4*pi)
     so positive displacement = ground moving TOWARD the sensor.
  3. Builds a strict boolean mask: `(coh < 0.4) OR isnan(coh)`. Masked pixels
     become NaN in the output displacement raster.
  4. Writes the masked LOS displacement to
         data/qa_masks/<product_name>/<product_name>_masked_disp.tif
     preserving CRS, transform, and pixel grid.
  5. Records per-product survivor statistics into
         data/qa_masks/_coherence_mask_stats.csv
     This CSV is the key input to the Phase 1.2 Part B decision (which pairs
     to quarantine, and whether to upgrade chain → SBAS).

Run from the project root with `conda activate insar_qa_env`.
"""

from __future__ import annotations

import csv
import gc
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "data" / "processed_tiffs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "qa_masks"
LOG_DIR = PROJECT_ROOT / "logs"
STATS_CSV = OUTPUT_DIR / "_coherence_mask_stats.csv"

COHERENCE_THRESHOLD = 0.4
# Sentinel-1 C-band radar wavelength in metres (5.5465763 cm). Used to convert
# unwrapped phase (radians) into LOS displacement (m).
SENTINEL1_WAVELENGTH_M = 0.055465763

# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------
LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "feature_engineering.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("feature_engineering")


# ------------------------------------------------------------------------------
# Per-product processing
# ------------------------------------------------------------------------------
def find_inputs(product_dir: Path) -> tuple[Optional[Path], Optional[Path]]:
    """Locate the unw_phase and corr GeoTIFFs in a single product folder."""
    phase = next(iter(product_dir.glob("*_unw_phase.tif")), None)
    corr = next(iter(product_dir.glob("*_corr.tif")), None)
    return phase, corr


def phase_to_los_displacement(phase_rad: np.ndarray) -> np.ndarray:
    """Convert unwrapped interferometric phase (rad) → LOS displacement (m).

    ASF / HyP3 sign convention: positive displacement = motion toward sensor.
    """
    return -phase_rad * SENTINEL1_WAVELENGTH_M / (4.0 * np.pi)


def process_product(product_dir: Path) -> dict:
    """Mask one product and return a stats dict for the CSV."""
    name = product_dir.name
    phase_path, corr_path = find_inputs(product_dir)

    if phase_path is None or corr_path is None:
        return {"product": name, "status": "missing_inputs"}

    out_subdir = OUTPUT_DIR / name
    out_subdir.mkdir(parents=True, exist_ok=True)
    out_path = out_subdir / f"{name}_masked_disp.tif"

    if out_path.exists() and out_path.stat().st_size > 0:
        return {"product": name, "status": "skipped_exists"}

    # --- Load coherence ---
    with rasterio.open(corr_path) as src:
        coh = src.read(1)  # already float32 on disk

    # --- Load unwrapped phase ---
    with rasterio.open(phase_path) as src:
        phase = src.read(1)
        profile = src.profile.copy()

    if coh.shape != phase.shape:
        return {
            "product": name,
            "status": f"shape_mismatch_coh={coh.shape}_phase={phase.shape}",
        }

    # --- Convert phase to LOS displacement (metres) ---
    disp = phase_to_los_displacement(phase).astype(np.float32, copy=False)

    # --- Build the mask ---
    # NaN < 0.4 evaluates to False in NumPy, so we explicitly OR-in isnan
    # to ensure already-bad coherence pixels are also masked.
    mask = (coh < COHERENCE_THRESHOLD) | np.isnan(coh)
    disp_masked = np.where(mask, np.nan, disp).astype(np.float32, copy=False)

    # --- Stats (computed before del-ing arrays) ---
    total = int(disp_masked.size)
    n_nan_coh = int(np.sum(np.isnan(coh)))
    n_below_threshold = int(np.sum((coh < COHERENCE_THRESHOLD) & ~np.isnan(coh)))
    n_survivors = int(np.sum(~np.isnan(disp_masked)))
    survivor_pct = 100.0 * n_survivors / total
    mean_coh_all = float(np.nanmean(coh)) if np.any(~np.isnan(coh)) else float("nan")
    # Coherence of surviving pixels only:
    coh_of_survivors = np.where(~np.isnan(disp_masked), coh, np.nan)
    mean_coh_survivors = (
        float(np.nanmean(coh_of_survivors))
        if np.any(~np.isnan(coh_of_survivors))
        else float("nan")
    )

    # --- Write the output GeoTIFF ---
    profile.update(
        dtype=rasterio.float32,
        nodata=np.nan,
        compress="lzw",
        count=1,
    )
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(disp_masked, 1)

    # --- Explicit cleanup per user spec ---
    del coh, phase, disp, mask, disp_masked, coh_of_survivors
    gc.collect()

    return {
        "product": name,
        "status": "ok",
        "total_pixels": total,
        "nan_in_coh": n_nan_coh,
        "masked_below_threshold": n_below_threshold,
        "surviving_pixels": n_survivors,
        "surviving_pct": round(survivor_pct, 2),
        "mean_coherence_all": round(mean_coh_all, 4),
        "mean_coherence_survivors": round(mean_coh_survivors, 4),
    }


# ------------------------------------------------------------------------------
# Driver
# ------------------------------------------------------------------------------
def main() -> int:
    if not INPUT_DIR.exists():
        logger.error(f"Input dir does not exist: {INPUT_DIR}")
        return 1

    product_dirs = sorted(d for d in INPUT_DIR.iterdir() if d.is_dir())
    logger.info(f"Found {len(product_dirs)} product directories.")

    all_stats: list[dict] = []
    n_ok = n_skipped = n_failed = 0

    for i, product_dir in enumerate(product_dirs, start=1):
        result = process_product(product_dir)
        all_stats.append(result)
        status = result["status"]
        if status == "ok":
            n_ok += 1
            logger.info(
                f"[{i:>2}/{len(product_dirs)}] OK  {product_dir.name}  "
                f"survivors={result['surviving_pct']:.1f}%  "
                f"mean_coh_survivors={result['mean_coherence_survivors']:.3f}"
            )
        elif status == "skipped_exists":
            n_skipped += 1
            logger.info(f"[{i:>2}/{len(product_dirs)}] SKIP {product_dir.name}  (exists)")
        else:
            n_failed += 1
            logger.warning(f"[{i:>2}/{len(product_dirs)}] FAIL {product_dir.name}  ({status})")

    # --- Write CSV ---
    if all_stats:
        # Union of keys across all rows so missing-input rows still write.
        fieldnames: list[str] = []
        for r in all_stats:
            for k in r.keys():
                if k not in fieldnames:
                    fieldnames.append(k)
        with open(STATS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in all_stats:
                writer.writerow(row)
        logger.info(f"Wrote stats CSV: {STATS_CSV}")

    # --- Aggregate summary ---
    ok_rows = [r for r in all_stats if r["status"] == "ok"]
    if ok_rows:
        survivor_pcts = np.array([r["surviving_pct"] for r in ok_rows])
        coh_survivors = np.array([r["mean_coherence_survivors"] for r in ok_rows])
        logger.info("-" * 60)
        logger.info(
            f"Summary: ok={n_ok}  skipped={n_skipped}  failed={n_failed}  "
            f"total={len(all_stats)}"
        )
        logger.info(
            f"Survivor %  — min={survivor_pcts.min():.1f}  "
            f"median={np.median(survivor_pcts):.1f}  "
            f"mean={survivor_pcts.mean():.1f}  "
            f"max={survivor_pcts.max():.1f}"
        )
        logger.info(
            f"Coh of survivors — min={coh_survivors.min():.3f}  "
            f"median={np.median(coh_survivors):.3f}  "
            f"mean={coh_survivors.mean():.3f}  "
            f"max={coh_survivors.max():.3f}"
        )

    return 0 if n_failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

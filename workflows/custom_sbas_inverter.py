#!/usr/bin/env python
"""
custom_sbas_inverter.py — Phase 2: SBAS time-series inversion (pathfinder stack).

Converts a connected stack of masked LOS-displacement interferograms into:
  1. A per-pixel cumulative displacement time-series (one band per acquisition
     date, mm), and
  2. A per-pixel mean LOS velocity (mm/year) from a linear fit of that series.

Design:
  * The design matrix G maps cumulative displacement at each acquisition date
    (reference date fixed at 0) to the observed pairwise displacement of each
    interferogram.
  * PER-PIXEL VARIABLE NETWORK: every pixel is inverted over whatever subset of
    pairs survived the coherence mask, provided that subset still spans all
    dates (its sub-design-matrix is full column rank). Pixels are grouped by
    their NaN pattern so each distinct pattern's pseudo-inverse is computed once
    and applied to the whole group as a batched matmul — fast and memory-cheap.
    This recovers far more pixels than a single all-pairs pinv (which would
    require a pixel to survive in EVERY interferogram).
  * CLIPPED TO AOI + buffer: HyP3 products are full Sentinel-1 frames (~294 km);
    we only need the ~20 km Ramban box. We invert on the AOI bounds plus a
    buffer (for the spatial high-pass halo), keeping runs near-instant and the
    reference pixel local so orbital ramps don't dominate.
  * Block-streamed with rasterio.windows; the full 3-D cube is never resident.
  * All heavy arrays are float32.
  * A NaN-aware spatial high-pass (scipy.ndimage.gaussian_filter) is applied to
    the assembled 2-D velocity map as a post-pass to strip broad regional
    atmospheric phase screens (sigma large → removes only broad APS, preserves
    localized landslide signal). Run after assembly to avoid block-edge seams.

Data note: HyP3 pairs within one frame share CRS, 80 m resolution and a
pixel-aligned origin grid but have slightly different extents. We invert on
their common intersection (clipped to the AOI) using integer-offset windows.

Sign convention (from Phase 1): displacement is already metres, positive =
toward sensor; so subsidence / downslope motion (away from sensor) is negative,
matching the deliverable.

Usage:
    python workflows/custom_sbas_inverter.py
    python workflows/custom_sbas_inverter.py --stack ASC_path27_frame106 \
        --buffer-km 3 --hp-sigma-px 30 --min-pairs 8
"""

from __future__ import annotations

import os
import sys

# --- BLAS/LAPACK DLL bootstrap (Windows) --------------------------------------
# numpy's BLAS/LAPACK DLLs live in <env>/Library/bin (+ mingw-w64/bin). When
# this script is launched by a full python.exe path WITHOUT `conda activate`,
# those directories are not on PATH, numpy's delay-loaded BLAS DLL fails to
# load, and EVERY matmul / np.linalg call hard-crashes with Windows fatal
# exception 0xC06D007F. (This — not a "numpy 2.x large-array bug" — was the true
# cause of the earlier np.corrcoef and matplotlib crashes; see
# error_history_log.md.) Prepending the env's DLL dirs to PATH before importing
# numpy makes the BLAS findable, exactly as `conda activate` would.
if sys.platform == "win32":
    _dll_dirs = [
        os.path.join(sys.prefix, "Library", "bin"),
        os.path.join(sys.prefix, "Library", "mingw-w64", "bin"),
        os.path.join(sys.prefix, "Scripts"),
    ]
    os.environ["PATH"] = os.pathsep.join(
        [d for d in _dll_dirs if os.path.isdir(d)] + [os.environ.get("PATH", "")]
    )

import argparse
import csv
import logging
import re
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.windows import Window
from scipy.ndimage import gaussian_filter

from config import load_config

# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
QA_DIR = PROJECT_ROOT / "data" / "qa_masks"
QUARANTINE_CSV = QA_DIR / "_quarantine_list.csv"
_SFX = load_config().data_suffix   # '' for ramban; '_<slug>' so AOIs coexist
OUT_DIR = PROJECT_ROOT / "data" / f"velocity{_SFX}"
LOG_DIR = PROJECT_ROOT / "logs"

DAYS_PER_YEAR = 365.25
# Sentinel-1 C-band wavelength (m) — to convert displacement residuals back to
# phase for the temporal-coherence quality metric. Matches Phase 1.2.
SENTINEL1_WAVELENGTH_M = 0.055465763

# ------------------------------------------------------------------------------
LOG_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "custom_sbas_inverter.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("sbas_inverter")


# ------------------------------------------------------------------------------
# Inputs
# ------------------------------------------------------------------------------
def parse_pair_dates(product_name: str) -> tuple[datetime, datetime]:
    # S1[A-D][A-D]: accept cross-unit HyP3 pairs (S1AD, S1DD…) from the June-2026
    # constellation handover, not just same-unit S1AA (ledger §56/§61).
    m = re.search(r"S1[A-D][A-D]_(\d{8})T(\d{6})_(\d{8})T(\d{6})_", product_name)
    if not m:
        raise ValueError(f"cannot parse dates from {product_name}")
    fmt = "%Y%m%dT%H%M%S"
    return (
        datetime.strptime(m.group(1) + "T" + m.group(2), fmt),
        datetime.strptime(m.group(3) + "T" + m.group(4), fmt),
    )


def load_keep_products(stack: str) -> list[str]:
    rows = list(csv.DictReader(QUARANTINE_CSV.open(encoding="utf-8")))
    keep = [r["product"] for r in rows
            if r["stack"] == stack and r["decision"] == "KEEP"]
    if not keep:
        raise SystemExit(f"No KEEP products for stack {stack!r} in {QUARANTINE_CSV}")
    return sorted(keep)


def masked_disp_path(product: str) -> Path:
    return QA_DIR / product / f"{product}_masked_disp.tif"


# ------------------------------------------------------------------------------
# Design matrix
# ------------------------------------------------------------------------------
def build_design_matrix(products: list[str]):
    """Return (G float64, dates, t_days, vel_weights float32, pairs).

    G is (n_pairs x n_dates-1): row r has -1 at the earlier date's column and
    +1 at the later date's column. The earliest date is the fixed reference
    (cumulative displacement 0) and is excluded as an unknown.
    """
    pairs = []
    date_set = set()
    for p in products:
        d1, d2 = parse_pair_dates(p)
        ref, sec = sorted((d1, d2))
        pairs.append((p, ref, sec))
        date_set.add(ref)
        date_set.add(sec)

    dates = sorted(date_set)
    n_dates = len(dates)
    date_idx = {d: i for i, d in enumerate(dates)}

    G = np.zeros((len(pairs), n_dates - 1), dtype=np.float64)
    for r, (_, ref, sec) in enumerate(pairs):
        i_ref, i_sec = date_idx[ref], date_idx[sec]
        if i_ref > 0:
            G[r, i_ref - 1] = -1.0
        if i_sec > 0:
            G[r, i_sec - 1] = +1.0

    t_days = np.array([(d - dates[0]).days for d in dates], dtype=np.float64)
    t_centered = t_days - t_days.mean()
    vel_weights = (t_centered / float(np.sum(t_centered**2))).astype(np.float32)

    logger.info(
        f"Design matrix: {len(pairs)} pairs, {n_dates} dates "
        f"({dates[0].date()} … {dates[-1].date()}), "
        f"full-network rank = {np.linalg.matrix_rank(G)} / {n_dates - 1}"
    )
    return G, dates, t_days, vel_weights, pairs


# ------------------------------------------------------------------------------
# Per-pixel variable-network inversion (mask-grouped)
# ------------------------------------------------------------------------------
class PixelInverter:
    """Caches a pseudo-inverse per distinct NaN-pattern (validity mask)."""

    def __init__(self, G: np.ndarray, n_unknowns: int, min_pairs: int):
        self.G = G
        self.n_unknowns = n_unknowns
        self.min_pairs = min_pairs
        self._cache: dict[bytes, np.ndarray | None] = {}

    def pinv_for_mask(self, mask: np.ndarray) -> np.ndarray | None:
        """Return (n_unknowns x n_valid) pinv for this mask, or None if the
        valid pairs are too few or do not span all dates (rank-deficient)."""
        key = mask.tobytes()
        if key in self._cache:
            return self._cache[key]
        n_valid = int(mask.sum())
        result: np.ndarray | None = None
        if n_valid >= self.min_pairs:
            Gv = self.G[mask]
            if np.linalg.matrix_rank(Gv) == self.n_unknowns:
                result = np.linalg.pinv(Gv).astype(np.float32)
        self._cache[key] = result
        return result

    def invert_block(self, obs2d: np.ndarray, n_dates: int):
        """obs2d: (n_pairs, n_px) float32 with NaN.

        Returns (ts, gamma):
          ts    : (n_dates, n_px) cumulative displacement (m), NaN where unsolved.
          gamma : (n_px,) temporal coherence in [0,1], NaN where unsolved. It is
                  |mean(exp(i * phase_residual))| over the pixel's valid pairs,
                  where phase_residual comes from (obs - G@ts) converted to
                  radians. Near 1 = the time-series reproduces the observed pairs
                  (self-consistent); low = unwrapping errors / noise.
        """
        n_px = obs2d.shape[1]
        ts = np.full((n_dates, n_px), np.nan, dtype=np.float32)
        gamma = np.full(n_px, np.nan, dtype=np.float32)
        disp_to_phase = 4.0 * np.pi / SENTINEL1_WAVELENGTH_M

        finite = np.isfinite(obs2d)
        uniq, inv = np.unique(finite.T, axis=0, return_inverse=True)
        inv = inv.ravel()
        for u_idx in range(uniq.shape[0]):
            mask = uniq[u_idx]
            if not mask.any():
                continue
            pinv = self.pinv_for_mask(mask)
            if pinv is None:
                continue
            cols = np.nonzero(inv == u_idx)[0]
            sub = obs2d[np.ix_(mask, cols)]            # (n_valid, n_group) finite
            unknowns = pinv @ sub                       # (n_unknowns, n_group)
            ts[0, cols] = 0.0
            ts[1:, cols] = unknowns
            # Model misfit -> temporal coherence
            model = self.G[mask] @ unknowns             # (n_valid, n_group)
            resid_phase = (sub - model) * disp_to_phase
            gamma[cols] = np.abs(
                np.mean(np.exp(1j * resid_phase), axis=0)
            ).astype(np.float32)
        return ts, gamma


# ------------------------------------------------------------------------------
# Common grid (clipped to AOI + buffer)
# ------------------------------------------------------------------------------
def compute_clipped_grid(products: list[str], aoi_path: Path, buffer_km: float):
    """Intersection of all products' extents, clipped to AOI bounds + buffer.

    Returns (transform, width, height, crs, per_product_offsets) where offsets
    map the clipped grid's origin into each product's array (integer pixels).
    """
    lefts, rights, tops, bottoms = [], [], [], []
    res, crs, meta = set(), set(), {}
    for p in products:
        with rasterio.open(masked_disp_path(p)) as s:
            b = s.bounds
            lefts.append(b.left); rights.append(b.right)
            tops.append(b.top); bottoms.append(b.bottom)
            res.add((round(s.res[0], 4), round(s.res[1], 4)))
            crs.add(str(s.crs))
            meta[p] = s.transform
    if len(res) != 1 or len(crs) != 1:
        raise SystemExit(f"Inconsistent res/crs: res={res} crs={crs}")
    rx, ry = list(res)[0]
    product_crs = list(crs)[0]

    # Intersection of all products
    left, right = max(lefts), min(rights)
    top, bottom = min(tops), max(bottoms)

    # AOI bounds in product CRS, expanded by buffer
    aoi = gpd.read_file(aoi_path).to_crs(product_crs)
    minx, miny, maxx, maxy = aoi.total_bounds
    buf = buffer_km * 1000.0
    minx -= buf; miny -= buf; maxx += buf; maxy += buf

    # Clip intersection to AOI+buffer
    left = max(left, minx); right = min(right, maxx)
    top = min(top, maxy); bottom = max(bottom, miny)
    if right <= left or top <= bottom:
        raise SystemExit("AOI does not overlap the product footprint.")

    # Snap origin to the common pixel grid (use first product's grid as anchor)
    anchor = meta[products[0]]
    left = anchor.c + round((left - anchor.c) / rx) * rx
    top = anchor.f + round((top - anchor.f) / ry) * ry
    width = int(round((right - left) / rx))
    height = int(round((top - bottom) / ry))
    transform = rasterio.transform.from_origin(left, top, rx, ry)

    offsets = {}
    for p in products:
        ptf = meta[p]
        col_off = (left - ptf.c) / rx
        row_off = (ptf.f - top) / ry
        if abs(col_off - round(col_off)) > 1e-3 or abs(row_off - round(row_off)) > 1e-3:
            raise SystemExit(f"{p} not pixel-aligned to common grid.")
        offsets[p] = (int(round(col_off)), int(round(row_off)))

    logger.info(
        f"Clipped grid: {width} x {height} px @ {rx} m "
        f"(AOI + {buffer_km} km buffer) {product_crs}"
    )
    return transform, width, height, product_crs, offsets


def read_block(product: str, offsets, win: Window) -> np.ndarray:
    col_off, row_off = offsets[product]
    src_win = Window(win.col_off + col_off, win.row_off + row_off,
                     win.width, win.height)
    with rasterio.open(masked_disp_path(product)) as s:
        arr = s.read(1, window=src_win, boundless=True, fill_value=np.nan).astype(np.float32)
        nodata = s.nodata
    if nodata is not None and not np.isnan(nodata):
        arr = np.where(arr == nodata, np.nan, arr)
    return arr


def fit_deramp_planes(products, offsets, width, height, max_samples=60000):
    """Fit a 2-D plane a*col + b*row + c to each interferogram over the clipped
    grid (valid pixels only). Subtracting it removes the per-interferogram
    constant offset (arbitrary unwrapping reference) AND the orbital /
    long-wavelength atmospheric ramp — the standard SBAS pre-processing we must
    do before inversion. A first-order plane cannot absorb localized (sub-km)
    deformation, so the landslide signal is preserved.

    Returns {product: (a, b, c) float32}.
    """
    rng = np.random.default_rng(0)
    planes: dict[str, np.ndarray] = {}
    full = Window(0, 0, width, height)
    for p in products:
        arr = read_block(p, offsets, full)
        fin = np.isfinite(arr)
        rr, cc = np.nonzero(fin)
        vals = arr[fin]
        if rr.size < 100:
            planes[p] = np.array([0, 0, 0], dtype=np.float32)
            continue
        if rr.size > max_samples:
            idx = rng.choice(rr.size, max_samples, replace=False)
            rr, cc, vals = rr[idx], cc[idx], vals[idx]
        A = np.column_stack([cc, rr, np.ones_like(cc)]).astype(np.float64)
        coef, *_ = np.linalg.lstsq(A, vals.astype(np.float64), rcond=None)
        planes[p] = coef.astype(np.float32)
    logger.info(f"Fitted deramp planes for {len(planes)} interferograms.")
    return planes


def apply_deramp(arr: np.ndarray, plane, col0: int, row0: int,
                 col_step: float = 1.0, row_step: float = 1.0) -> np.ndarray:
    """Subtract plane (a*col + b*row + c) evaluated at the block's global
    clipped-grid coordinates. col_step/row_step handle decimated reads."""
    a, b, c = plane
    h, w = arr.shape
    cols = col0 + np.arange(w, dtype=np.float32) * col_step
    rows = row0 + np.arange(h, dtype=np.float32) * row_step
    ramp = (a * cols[None, :] + b * rows[:, None] + c).astype(np.float32)
    return arr - ramp


# ------------------------------------------------------------------------------
# Reference pixel (auto-select within the clipped grid)
# ------------------------------------------------------------------------------
def auto_select_reference(products, offsets, width, height, inverter, n_dates,
                          vel_weights, planes, decim=4):
    """Coarse pre-pass: pick the most stable, well-connected pixel in the grid
    (now == AOI + buffer). Returns (ref_row, ref_col) at full resolution and the
    reference time-series. Operates on DERAMPED data for consistency."""
    cw, ch = max(width // decim, 1), max(height // decim, 1)
    col_step, row_step = width / cw, height / ch
    cube = np.empty((len(products), ch * cw), dtype=np.float32)
    for k, p in enumerate(products):
        with rasterio.open(masked_disp_path(p)) as s:
            col_off, row_off = offsets[p]
            src_win = Window(col_off, row_off, width, height)
            a = s.read(1, window=src_win, out_shape=(ch, cw), boundless=True,
                       fill_value=np.nan,
                       resampling=rasterio.enums.Resampling.nearest).astype(np.float32)
            if s.nodata is not None and not np.isnan(s.nodata):
                a = np.where(a == s.nodata, np.nan, a)
            a = apply_deramp(a, planes[p], 0, 0, col_step=col_step, row_step=row_step)
            cube[k] = a.ravel()

    ts, _gamma = inverter.invert_block(cube, n_dates)  # (n_dates, ch*cw)
    net = np.abs(ts[-1] - ts[0])                       # total |displacement|
    n_valid = np.sum(np.isfinite(cube), axis=0)
    solvable = np.isfinite(ts[1])                      # got a solution
    # Prefer stable (small net), well-observed (many pairs), near centre.
    yy, xx = np.mgrid[0:ch, 0:cw]
    dist = np.sqrt((yy - ch / 2.0) ** 2 + (xx - cw / 2.0) ** 2).ravel()
    score = np.where(solvable & (n_valid >= inverter.min_pairs),
                     net + 0.5 * dist / max(cw, ch), np.inf)
    if not np.any(np.isfinite(score)):
        raise SystemExit("No solvable reference candidate in AOI — relax --min-pairs.")
    best = int(np.argmin(score))
    cr, cc = divmod(best, cw)
    ref_row = min(cr * decim + decim // 2, height - 1)
    ref_col = min(cc * decim + decim // 2, width - 1)

    # Invert the chosen full-res pixel exactly
    win = Window(ref_col, ref_row, 1, 1)
    obs = np.array(
        [apply_deramp(read_block(p, offsets, win), planes[p], ref_col, ref_row)[0, 0]
         for p in products],
        dtype=np.float32,
    ).reshape(-1, 1)
    ref_ts_2d, _ = inverter.invert_block(obs, n_dates)
    ref_ts = ref_ts_2d[:, 0]
    if not np.isfinite(ref_ts[1]):
        raise SystemExit("Chosen reference pixel not solvable at full res.")
    logger.info(f"Auto reference pixel: row={ref_row}, col={ref_col} "
                f"(coarse net |disp|={net[best]*1000:.1f} mm, "
                f"{int(n_valid[best])}/{len(products)} pairs)")
    return ref_row, ref_col, ref_ts


# ------------------------------------------------------------------------------
# NaN-aware spatial high-pass
# ------------------------------------------------------------------------------
def nan_gaussian_highpass(arr: np.ndarray, sigma: float):
    mask = np.isfinite(arr).astype(np.float32)
    filled = np.where(mask > 0, arr, 0.0).astype(np.float32)
    num = gaussian_filter(filled, sigma=sigma, mode="nearest")
    den = gaussian_filter(mask, sigma=sigma, mode="nearest")
    with np.errstate(invalid="ignore", divide="ignore"):
        low = np.where(den > 1e-3, num / den, np.nan).astype(np.float32)
    hp = (arr - low).astype(np.float32)
    hp[mask == 0] = np.nan
    return hp, low


# ------------------------------------------------------------------------------
# Driver
# ------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None,
                    help="Path to config.yaml (default: project-root config.yaml).")
    ap.add_argument("--stack", default="ASC_path27_frame106")
    ap.add_argument("--block", type=int, default=1024)
    ap.add_argument("--buffer-km", type=float, default=3.0)
    ap.add_argument("--min-pairs", type=int, default=8,
                    help="Minimum surviving pairs for a pixel to be inverted.")
    ap.add_argument("--hp-sigma-px", type=float, default=30.0,
                    help="Gaussian sigma (px) for spatial high-pass; 30 px @ 80 m ~= 2.4 km.")
    ap.add_argument("--temporal-coherence-thr", type=float, default=0.7,
                    help="Mask pixels whose model-fit temporal coherence is below "
                         "this (default 0.7, the conventional SBAS threshold).")
    ap.add_argument("--flag-velocity", type=float, default=100.0,
                    help="Report (do NOT remove) surviving pixels with |velocity| "
                         "above this mm/yr as a sanity check.")
    ap.add_argument("--no-deramp", dest="deramp", action="store_false",
                    help="Disable per-interferogram plane deramping (default: on).")
    ap.add_argument("--max-date", default=None, metavar="YYYY-MM-DD",
                    help="PERIOD SPLIT: drop pairs whose secondary acquisition is after this "
                         "date, then invert the remaining period alone. Use when a stack is "
                         "disconnected and its LATER island is too short to solve: without this "
                         "the whole stack is rank-deficient and the inverter refuses, so the "
                         "stack falls out of the union mosaic entirely (§78 — a quarantined "
                         "monsoon pair stranded a 2-scene tail and emptied VD's ALERT map).")
    ap.set_defaults(deramp=True)
    args = ap.parse_args()

    cfg = load_config(args.config)
    stack = args.stack
    logger.info(f"=== SBAS inversion for stack {stack} ===")

    products = load_keep_products(stack)
    if args.max_date:
        # Compare CALENDAR DATES, not datetimes: an acquisition on the cutoff day carries a
        # time-of-day (~12:55 here), so a naive datetime compare would silently drop the very
        # pair the operator named as the period's last acquisition.
        cutoff = datetime.strptime(args.max_date, "%Y-%m-%d").date()
        kept = [p for p in products if max(parse_pair_dates(p)).date() <= cutoff]
        dropped = len(products) - len(kept)
        if not kept:
            raise SystemExit(f"--max-date {args.max_date} drops every KEEP pair of {stack!r}.")
        logger.info(f"PERIOD SPLIT at {args.max_date}: {dropped} pair(s) after the cutoff "
                    f"dropped; inverting the {len(kept)}-pair period that remains.")
        products = kept
    logger.info(f"{len(products)} KEEP interferograms")

    G, dates, t_days, vel_weights, pairs = build_design_matrix(products)
    n_dates = len(dates)
    n_unknowns = n_dates - 1
    # A short-chain stack (e.g. a 4-pair single-season frame) can never satisfy a
    # min-pairs above its own pair count — clamp so small stacks invert at their
    # physical limit (all pairs valid; zero redundancy, so treat outputs with care).
    min_pairs = min(args.min_pairs, len(products))
    if min_pairs < args.min_pairs:
        logger.info(f"--min-pairs {args.min_pairs} exceeds stack size "
                    f"({len(products)} pairs) — clamped to {min_pairs}.")
    inverter = PixelInverter(G, n_unknowns, min_pairs)

    transform, width, height, crs, offsets = compute_clipped_grid(
        products, cfg.aoi_path, args.buffer_km
    )

    planes = (fit_deramp_planes(products, offsets, width, height)
              if args.deramp else {p: np.zeros(3, np.float32) for p in products})

    ref_row, ref_col, ref_ts = auto_select_reference(
        products, offsets, width, height, inverter, n_dates, vel_weights, planes
    )

    vel_path = OUT_DIR / f"{stack}_mean_velocity_los.tif"
    ts_path = OUT_DIR / f"{stack}_displacement_timeseries.tif"
    tcoh_path = OUT_DIR / f"{stack}_temporal_coherence.tif"
    vel_profile = dict(driver="GTiff", height=height, width=width, count=1,
                       dtype="float32", crs=crs, transform=transform,
                       nodata=np.nan, compress="lzw")
    ts_profile = dict(vel_profile, count=n_dates)

    thr = args.temporal_coherence_thr
    n_solvable = 0      # pixels with a solution (pre-quality-mask)
    n_kept = 0          # pixels passing the temporal-coherence threshold
    n_px_total = width * height

    with rasterio.open(vel_path, "w", **vel_profile) as vel_dst, \
         rasterio.open(ts_path, "w", **ts_profile) as ts_dst, \
         rasterio.open(tcoh_path, "w", **vel_profile) as tcoh_dst:
        for i, d in enumerate(dates, start=1):
            ts_dst.set_band_description(i, d.strftime("%Y-%m-%d"))

        for row0 in range(0, height, args.block):
            for col0 in range(0, width, args.block):
                h = min(args.block, height - row0)
                w = min(args.block, width - col0)
                win = Window(col0, row0, w, h)

                obs = np.empty((len(products), h, w), dtype=np.float32)
                for k, p in enumerate(products):
                    obs[k] = apply_deramp(read_block(p, offsets, win),
                                          planes[p], col0, row0)
                obs2d = obs.reshape(len(products), h * w)

                ts, gamma = inverter.invert_block(obs2d, n_dates)
                n_solvable += int(np.sum(np.isfinite(gamma)))

                # Quality mask: drop low temporal-coherence pixels (unwrapping
                # errors / noise) from BOTH velocity and time-series.
                bad = ~(gamma >= thr)
                ts[:, bad] = np.nan

                ts_ref = ts - ref_ts[:, None]                  # reference
                vel = (vel_weights @ ts_ref) * 1000.0 * DAYS_PER_YEAR  # mm/yr
                n_kept += int(np.sum(np.isfinite(vel)))

                ts_dst.write((ts_ref * 1000.0).reshape(n_dates, h, w).astype(np.float32), window=win)
                vel_dst.write(vel.reshape(1, h, w).astype(np.float32), window=win)
                tcoh_dst.write(gamma.reshape(1, h, w), window=win)

    n_masks = len(inverter._cache)
    n_solvable_masks = sum(1 for v in inverter._cache.values() if v is not None)
    logger.info(
        f"Inversion done. Solvable pixels: {n_solvable:,} "
        f"({100*n_solvable/n_px_total:.1f}% of grid). "
        f"After temporal-coherence >= {thr}: {n_kept:,} kept "
        f"({100*n_kept/n_px_total:.1f}% of grid, "
        f"{100*n_kept/max(n_solvable,1):.1f}% of solvable). "
        f"{n_solvable_masks}/{n_masks} distinct NaN-patterns solvable."
    )

    # --- Post-pass spatial high-pass ---
    with rasterio.open(vel_path) as s:
        vel_map = s.read(1)
    hp, low = nan_gaussian_highpass(vel_map, sigma=args.hp_sigma_px)
    hp_path = OUT_DIR / f"{stack}_mean_velocity_los_highpass.tif"
    aps_path = OUT_DIR / f"{stack}_aps_component.tif"
    with rasterio.open(hp_path, "w", **vel_profile) as d:
        d.write(hp.astype(np.float32), 1)
    with rasterio.open(aps_path, "w", **vel_profile) as d:
        d.write(low.astype(np.float32), 1)

    finite = np.isfinite(vel_map)
    if np.any(finite):
        v = vel_map[finite]
        hpv = hp[np.isfinite(hp)]
        logger.info("Velocity raw (mm/yr): "
                    f"min={v.min():.1f} p5={np.percentile(v,5):.1f} "
                    f"median={np.median(v):.1f} p95={np.percentile(v,95):.1f} "
                    f"max={v.max():.1f}")
        logger.info("Velocity high-passed (mm/yr): "
                    f"std_raw={v.std():.2f} -> std_hp={hpv.std():.2f} "
                    f"median={np.median(hpv):.1f} "
                    f"p5={np.percentile(hpv,5):.1f} p95={np.percentile(hpv,95):.1f}")
        n_flag = int(np.sum(np.abs(v) > args.flag_velocity))
        logger.info(f"Sanity flag: {n_flag} of {v.size} kept pixels exceed "
                    f"|{args.flag_velocity:.0f}| mm/yr "
                    f"({100*n_flag/v.size:.1f}%) — NOT removed.")
    logger.info(f"Wrote:\n  {vel_path.name}\n  {ts_path.name} ({n_dates} bands)\n"
                f"  {tcoh_path.name}\n  {hp_path.name}\n  {aps_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

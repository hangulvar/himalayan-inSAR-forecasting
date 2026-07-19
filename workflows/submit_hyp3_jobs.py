#!/usr/bin/env python
"""
submit_hyp3_jobs.py

End-to-end ASF HyP3 submission pipeline for landslide monitoring over the
Ramban (Jammu & Kashmir) NH-44 corridor.

Pipeline:
    1. Parse the configured AOI polygon (config/aoi/<slug>_aoi.geojson) with geopandas.
    2. Query the ASF catalog (asf_search) for Sentinel-1 SLC IW scenes
       intersecting the AOI between May 1 2025 and Oct 31 2025
       (covers the heavy monsoon and immediate post-monsoon window).
    3. STRICTLY partition results by flightDirection (ASCENDING vs
       DESCENDING). Cross-orbit pairs are never built because mixing
       look directions over Ramban's steep ridges destroys phase
       unwrapping.
    4. Build CONSECUTIVE pairs per orbit (N -> N+1), respecting the
       Sentinel-1 12-day revisit cadence. Pairs exceeding a configurable
       max temporal baseline are dropped.
    5. Submit INSAR_GAMMA jobs via hyp3_sdk with:
         - duplicate detection against existing HyP3 jobs (by granule pair)
         - exponential backoff on transient API / rate-limit errors
         - dry-run mode by default; pass --submit to actually queue jobs.

Auth:
    Uses NASA Earthdata credentials from ~/_netrc (Windows) or ~/.netrc.

Usage:
    python workflows/submit_hyp3_jobs.py              # dry-run preview
    python workflows/submit_hyp3_jobs.py --submit     # actually queue jobs
    python workflows/submit_hyp3_jobs.py --submit --orbit ASCENDING
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

import geopandas as gpd
from dotenv import load_dotenv
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

import asf_search as asf
import hyp3_sdk as sdk
from hyp3_sdk.exceptions import HyP3Error

from config import load_config

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed_tiffs"

# AOI path, search window, job-name prefix and baseline rules come from
# config.yaml (see workflows/config.py). Pass --config to target another AOI.

# Retry policy for transient API errors / rate limiting.
MAX_RETRIES = 5
INITIAL_BACKOFF_SEC = 5.0
INTER_SUBMIT_PAUSE_SEC = 1.0  # tiny gap between successful submissions

# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------
load_dotenv()
LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "hyp3_processing.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("hyp3_pipeline")


# ------------------------------------------------------------------------------
# 1. AOI parsing
# ------------------------------------------------------------------------------
def load_aoi_geometry(geojson_path: Path) -> BaseGeometry:
    """Load AOI GeoJSON and return a single shapely geometry in EPSG:4326."""
    if not geojson_path.exists():
        raise FileNotFoundError(f"AOI not found: {geojson_path}")

    gdf = gpd.read_file(geojson_path)
    if gdf.empty:
        raise ValueError(f"AOI is empty: {geojson_path}")

    if gdf.crs is None:
        logger.warning("AOI has no CRS; assuming EPSG:4326.")
        gdf = gdf.set_crs(4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    # Dissolve multiple features into a single geometry for catalog query.
    # union_all() replaces the deprecated unary_union attribute in geopandas 1.x.
    geom = gdf.geometry.union_all()
    logger.info(f"AOI loaded: {geom.geom_type}, bounds={geom.bounds}")
    return geom


# ------------------------------------------------------------------------------
# 2. ASF catalog query
# ------------------------------------------------------------------------------
def search_sentinel1_slc(
    aoi: BaseGeometry, start: datetime, end: datetime
) -> list[asf.ASFProduct]:
    """Query the ASF catalog for Sentinel-1 SLC IW scenes intersecting AOI."""
    aoi_wkt = aoi.wkt
    logger.info(
        f"Querying ASF catalog: {start.date()} -> {end.date()} over AOI..."
    )

    results = asf.search(
        # ALL Sentinel-1 units, not [S1A, S1B]: the constellation handed over in June 2026
        # (S1A end-of-operations 29 Jun 2026; S1C/S1D now fly the same reference orbits, and
        # ASF already carries S1D scenes on our paths). The old A/B whitelist would silently
        # return NOTHING ever again — see error log 2026-07-18 / ledger §56.
        platform=[asf.PLATFORM.SENTINEL1],
        processingLevel=asf.PRODUCT_TYPE.SLC,
        beamMode=asf.BEAMMODE.IW,
        intersectsWith=aoi_wkt,
        start=start,
        end=end,
    )
    logger.info(f"Catalog returned {len(results)} Sentinel-1 SLC scenes.")
    return list(results)


# ------------------------------------------------------------------------------
# 3. Strict flight-direction partitioning
# ------------------------------------------------------------------------------
def partition_by_flight_direction(
    scenes: Iterable[asf.ASFProduct],
) -> dict[str, list[asf.ASFProduct]]:
    """Group scenes by flightDirection, pathNumber, AND frameNumber.

    Three rules:
      * Mixing ASCENDING + DESCENDING is physically invalid (opposite look
        vectors), so direction is the hardest split.
      * Different relative orbits (paths) image the AOI from different
        geometries — pair only within the same path.
      * The AOI can straddle a frame boundary, returning multiple adjacent
        frames per acquisition. Pairing across frames produces interferograms
        only over the small overlap region; we keep frames separated so each
        bucket covers a consistent footprint.
    """
    buckets: dict[str, list[asf.ASFProduct]] = {}
    for scene in scenes:
        props = scene.properties
        direction = (props.get("flightDirection") or "UNKNOWN").upper()
        path = props.get("pathNumber")
        frame = props.get("frameNumber")
        key = f"{direction}_path{path}_frame{frame}"
        buckets.setdefault(key, []).append(scene)

    # Sort each bucket chronologically by start time (ascending).
    for key, items in buckets.items():
        items.sort(key=lambda s: s.properties["startTime"])
        logger.info(f"  {key}: {len(items)} scenes")
    return buckets


# ------------------------------------------------------------------------------
# 4. Consecutive pair construction
# ------------------------------------------------------------------------------
def _parse_iso(ts: str) -> datetime:
    """Parse an ASF ISO timestamp (handles trailing Z)."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def build_sbas_pairs(
    scenes_sorted: list[asf.ASFProduct],
    max_baseline_days: int,
    n_neighbors: int = 1,
) -> list[tuple[asf.ASFProduct, asf.ASFProduct]]:
    """Build the (reference, secondary) pair list for SBAS-style networks.

    For each scene i, pair it with scenes i+1, i+2, ..., i+n_neighbors,
    subject to the same-frame ordering and the temporal-baseline cutoff.
    `n_neighbors=1` reproduces the original chain network (N → N+1 only).
    """
    pairs: list[tuple[asf.ASFProduct, asf.ASFProduct]] = []
    n = len(scenes_sorted)
    for i in range(n):
        for offset in range(1, n_neighbors + 1):
            j = i + offset
            if j >= n:
                break
            ref = scenes_sorted[i]
            sec = scenes_sorted[j]
            t_ref = _parse_iso(ref.properties["startTime"])
            t_sec = _parse_iso(sec.properties["startTime"])
            dt_days = abs((t_sec - t_ref).days)
            if dt_days == 0:
                continue  # same acquisition (different frame already filtered)
            if dt_days > max_baseline_days:
                logger.debug(
                    f"  skip {ref.properties['sceneName']} -> "
                    f"{sec.properties['sceneName']}: {dt_days}d > {max_baseline_days}d"
                )
                continue
            pairs.append((ref, sec))
    return pairs


# ------------------------------------------------------------------------------
# 5. Dedupe against existing HyP3 jobs
# ------------------------------------------------------------------------------
def fetch_existing_pair_signatures(hyp3: sdk.HyP3, name_prefix: str) -> set[frozenset]:
    """Return a set of {granule1, granule2} frozensets for jobs whose name starts
    with the given prefix.

    NOTE: hyp3_sdk's `find_jobs(name=X)` does EXACT-name match server-side, not
    prefix match. Since our submission names are e.g. `Ramban_NH44_ASCENDING_
    path100_frame102`, server-side filtering by `Ramban_NH44` would return zero
    jobs. We therefore fetch all jobs and prefix-filter client-side. Cheap for
    an account with <few-thousand historical jobs; revisit if this grows.
    """
    signatures: set[frozenset] = set()
    try:
        jobs = hyp3.find_jobs()
    except Exception as e:
        logger.warning(f"Could not fetch existing jobs for dedupe: {e}")
        return signatures

    matched = 0
    fail_counts: dict[frozenset, int] = {}
    for job in jobs:
        if not (job.name and job.name.startswith(name_prefix)):
            continue
        granules = job.job_parameters.get("granules") if job.job_parameters else None
        if not granules or len(granules) < 2:
            continue
        sig = frozenset(granules[:2])
        if job.status_code == "FAILED":
            # ONE failure gets retried on the next run (transient ASF hiccups); a pair
            # that failed TWICE fails deterministically inside the processor (e.g. the
            # frame106 Jan pair's "mcf reference point outside image segment") — PARK
            # it rather than re-buying the same failure on every idempotent re-run.
            fail_counts[sig] = fail_counts.get(sig, 0) + 1
            continue
        matched += 1
        signatures.add(sig)
    parked = {s for s, n in fail_counts.items() if n >= 2 and s not in signatures}
    for s in parked:
        logger.warning(f"PARKED (failed {fail_counts[s]}× at ASF — deterministic; "
                       f"investigate before resubmitting manually): {sorted(s)}")
    signatures |= parked
    logger.info(
        f"Dedupe scan: {matched} existing jobs under prefix '{name_prefix}', "
        f"{len(signatures)} unique pair signatures ({len(parked)} parked as "
        f"permanently failing)."
    )
    return signatures


# ------------------------------------------------------------------------------
# 6. Submission with retry/backoff
# ------------------------------------------------------------------------------
def submit_with_retry(
    hyp3: sdk.HyP3,
    reference_granule: str,
    secondary_granule: str,
    job_name: str,
) -> sdk.Job | None:
    """Submit a single InSAR job, retrying transient failures with exponential backoff."""
    backoff = INITIAL_BACKOFF_SEC
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            job = hyp3.submit_insar_job(
                granule1=reference_granule,
                granule2=secondary_granule,
                name=job_name,
                include_dem=True,
                include_look_vectors=True,
                include_wrapped_phase=False,
                apply_water_mask=True,
            )
            return job
        except HyP3Error as e:
            msg = str(e).lower()
            transient = any(t in msg for t in ("rate", "throttl", "timeout", "503", "504", "502"))
            if attempt == MAX_RETRIES or not transient:
                logger.error(f"Submission failed ({reference_granule} / {secondary_granule}): {e}")
                return None
            logger.warning(
                f"Transient error on attempt {attempt}/{MAX_RETRIES}: {e}. "
                f"Backing off {backoff:.1f}s..."
            )
            time.sleep(backoff)
            backoff *= 2
        except Exception as e:
            logger.error(f"Non-recoverable error: {e}")
            return None
    return None


# ------------------------------------------------------------------------------
# Driver
# ------------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config.yaml (default: project-root config.yaml).",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Actually submit jobs (default: dry-run preview only).",
    )
    parser.add_argument(
        "--orbit",
        choices=["ASCENDING", "DESCENDING", "BOTH"],
        default="BOTH",
        help="Restrict submission to one orbit direction (default: BOTH).",
    )
    parser.add_argument(
        "--max-baseline-days",
        type=int,
        default=None,
        help="Max temporal baseline for a pair (default: config baseline.max_temporal_baseline_days).",
    )
    parser.add_argument(
        "--sbas-neighbors",
        type=int,
        default=None,
        help=(
            "Number of forward neighbors each scene is paired with "
            "(default: config baseline.sbas_neighbors). "
            "1 = consecutive chain. 3 = SBAS N=3 (each scene pairs with the "
            "next 3 within --max-baseline-days). When >1, you almost always "
            "want to bump --max-baseline-days; e.g. for N=3 with the "
            "Sentinel-1 12-day cadence, use --max-baseline-days 40."
        ),
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    max_baseline_days = (
        args.max_baseline_days if args.max_baseline_days is not None
        else cfg.baseline.max_temporal_baseline_days
    )
    n_neighbors = (
        args.sbas_neighbors if args.sbas_neighbors is not None
        else cfg.baseline.sbas_neighbors
    )

    # --- 1. AOI ----------------------------------------------------------------
    aoi = load_aoi_geometry(cfg.aoi_path)

    # --- 2. Catalog query ------------------------------------------------------
    scenes = search_sentinel1_slc(aoi, cfg.search_start, cfg.search_end)
    if not scenes:
        logger.error("No Sentinel-1 scenes found in the search window.")
        return 1

    # --- 3. Partition by flight direction (and path) ---------------------------
    logger.info("Partitioning scenes by flightDirection + path:")
    buckets = partition_by_flight_direction(scenes)

    if args.orbit != "BOTH":
        buckets = {k: v for k, v in buckets.items() if k.startswith(args.orbit)}
        logger.info(f"Restricted to orbit={args.orbit}; {len(buckets)} bucket(s) remain.")

    # --- 4. Build SBAS-style pairs per bucket ---------------------------------
    logger.info(
        f"Pair construction: n_neighbors={n_neighbors}, "
        f"max_baseline_days={max_baseline_days}"
    )
    all_pairs: list[tuple[str, asf.ASFProduct, asf.ASFProduct]] = []
    for bucket_key, items in buckets.items():
        pairs = build_sbas_pairs(
            items, max_baseline_days, n_neighbors=n_neighbors
        )
        logger.info(f"  {bucket_key}: {len(pairs)} pair(s) within baseline")
        for ref, sec in pairs:
            all_pairs.append((bucket_key, ref, sec))

    if not all_pairs:
        logger.error("No valid pairs to submit. Check baseline / orbit filters.")
        return 1

    logger.info(f"TOTAL planned interferograms: {len(all_pairs)}")

    # --- 5. Auth + dedupe ------------------------------------------------------
    # In dry-run mode, HyP3 auth and dedupe are best-effort — the user mainly
    # wants to preview the planned pair list. Auth must succeed for --submit.
    hyp3: sdk.HyP3 | None = None
    existing: set[frozenset] = set()
    auth_error: str | None = None

    logger.info("Authenticating with ASF HyP3...")
    try:
        hyp3 = sdk.HyP3()
        user_id = hyp3.my_info().get("user_id", "<unknown>")
        logger.info(f"Authenticated as: {user_id}")
    except Exception as e:
        auth_error = str(e)
        if args.submit:
            logger.critical(
                "HyP3 auth failed and --submit was requested. Fix NASA Earthdata "
                f"credentials in ~/_netrc (Windows) or ~/.netrc. Detail: {e}"
            )
            return 1
        logger.warning(
            f"HyP3 auth failed (non-fatal in dry-run): {e}. "
            "Dedupe and quota checks will be skipped."
        )

    if hyp3 is not None:
        try:
            credits = hyp3.check_credits()
            logger.info(
                f"Remaining HyP3 credits: {credits}  (planned jobs: {len(all_pairs)})"
            )
        except Exception as e:
            logger.warning(f"Could not check credits: {e}")
        existing = fetch_existing_pair_signatures(hyp3, cfg.job_name_prefix)

    # --- 6. Submit (or dry-run) ------------------------------------------------
    submitted = 0
    skipped_dupes = 0
    failed = 0

    for bucket_key, ref, sec in all_pairs:
        ref_name = ref.properties["sceneName"]
        sec_name = sec.properties["sceneName"]
        sig = frozenset({ref_name, sec_name})

        if sig in existing:
            logger.info(f"[SKIP duplicate] {bucket_key}  {ref_name} -> {sec_name}")
            skipped_dupes += 1
            continue

        job_name = f"{cfg.job_name_prefix}_{bucket_key}"

        if not args.submit:
            logger.info(f"[DRY-RUN]      {bucket_key}  {ref_name} -> {sec_name}")
            continue

        assert hyp3 is not None  # guaranteed: --submit + failed auth returns earlier
        logger.info(f"[SUBMIT]       {bucket_key}  {ref_name} -> {sec_name}")
        job = submit_with_retry(hyp3, ref_name, sec_name, job_name)
        if job is None:
            failed += 1
            continue
        submitted += 1
        time.sleep(INTER_SUBMIT_PAUSE_SEC)

    # --- 7. Summary ------------------------------------------------------------
    logger.info("-" * 60)
    if args.submit:
        logger.info(f"Submitted: {submitted}   Skipped (dupes): {skipped_dupes}   Failed: {failed}")
        logger.info(
            "Jobs are now queued at ASF. Monitor via the HyP3 dashboard "
            "or hyp3.find_jobs(); products will be downloaded by a separate step."
        )
    else:
        logger.info(
            f"DRY-RUN complete. {len(all_pairs)} pair(s) planned, "
            f"{skipped_dupes} would be skipped as duplicates."
        )
        if auth_error:
            logger.warning(
                "Dedupe was SKIPPED because HyP3 auth failed. Fix this before "
                "running --submit, or duplicate jobs will be queued. "
                f"Detail: {auth_error}"
            )
        logger.info("Re-run with --submit to actually queue jobs.")

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

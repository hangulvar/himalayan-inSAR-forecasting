#!/usr/bin/env python
"""
submit_hyp3_jobs.py

End-to-end ASF HyP3 submission pipeline for landslide monitoring over the
Ramban (Jammu & Kashmir) NH-44 corridor.

Pipeline:
    1. Parse the AOI polygon from ramban_aoi.geojson with geopandas.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import geopandas as gpd
from dotenv import load_dotenv
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

import asf_search as asf
import hyp3_sdk as sdk
from hyp3_sdk.exceptions import HyP3Error

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
AOI_PATH = PROJECT_ROOT / "ramban_aoi.geojson"
LOG_DIR = PROJECT_ROOT / "logs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed_tiffs"

# Monsoon window — captures the physical changes driven by 2025 heavy rainfall.
SEARCH_START = datetime(2025, 5, 1, tzinfo=timezone.utc)
SEARCH_END = datetime(2025, 10, 31, tzinfo=timezone.utc)

# Sentinel-1 nominal revisit is 12 days. Allow up to 24 to tolerate a single
# missed acquisition before decorrelation makes the pair useless in vegetation.
MAX_TEMPORAL_BASELINE_DAYS = 24

# HyP3 job-name prefix — also used for de-duplication lookups.
JOB_NAME_PREFIX = "Ramban_NH44"

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
    geom = gdf.geometry.unary_union
    logger.info(f"AOI loaded: {geom.geom_type}, bounds={geom.bounds}")
    return geom


# ------------------------------------------------------------------------------
# 2. ASF catalog query
# ------------------------------------------------------------------------------
def search_sentinel1_slc(
    aoi: BaseGeometry, start: datetime, end: datetime
) -> list[asf.ASFProduct]:
    """Query the ASF catalog for Sentinel-1A/B SLC IW scenes intersecting AOI."""
    aoi_wkt = aoi.wkt
    logger.info(
        f"Querying ASF catalog: {start.date()} -> {end.date()} over AOI..."
    )

    results = asf.search(
        platform=[asf.PLATFORM.SENTINEL1A, asf.PLATFORM.SENTINEL1B],
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
    """Group scenes by flightDirection AND by pathNumber within each direction.

    Mixing ASCENDING + DESCENDING in a single interferogram is physically
    invalid (opposite look vectors). We also split by relative orbit (path)
    because frames from different paths cover different ground geometry.
    """
    buckets: dict[str, list[asf.ASFProduct]] = {}
    for scene in scenes:
        props = scene.properties
        direction = (props.get("flightDirection") or "UNKNOWN").upper()
        path = props.get("pathNumber")
        key = f"{direction}_path{path}"
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


def build_consecutive_pairs(
    scenes_sorted: list[asf.ASFProduct], max_baseline_days: int
) -> list[tuple[asf.ASFProduct, asf.ASFProduct]]:
    """Yield (reference, secondary) pairs for consecutive scenes within baseline."""
    pairs: list[tuple[asf.ASFProduct, asf.ASFProduct]] = []
    for ref, sec in zip(scenes_sorted, scenes_sorted[1:]):
        t_ref = _parse_iso(ref.properties["startTime"])
        t_sec = _parse_iso(sec.properties["startTime"])
        dt_days = abs((t_sec - t_ref).days)
        if dt_days == 0:
            continue  # same acquisition, skip
        if dt_days > max_baseline_days:
            logger.debug(
                f"  skipping pair {ref.properties['sceneName']} -> "
                f"{sec.properties['sceneName']}: {dt_days}d > {max_baseline_days}d"
            )
            continue
        pairs.append((ref, sec))
    return pairs


# ------------------------------------------------------------------------------
# 5. Dedupe against existing HyP3 jobs
# ------------------------------------------------------------------------------
def fetch_existing_pair_signatures(hyp3: sdk.HyP3, name_prefix: str) -> set[frozenset]:
    """Return a set of {granule1, granule2} frozensets already submitted."""
    signatures: set[frozenset] = set()
    try:
        jobs = hyp3.find_jobs(name=name_prefix)
    except Exception as e:
        logger.warning(f"Could not fetch existing jobs for dedupe: {e}")
        return signatures

    for job in jobs:
        granules = job.job_parameters.get("granules") if job.job_parameters else None
        if granules and len(granules) >= 2:
            signatures.add(frozenset(granules[:2]))
    logger.info(f"Found {len(signatures)} existing job signatures under prefix '{name_prefix}'.")
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
        default=MAX_TEMPORAL_BASELINE_DAYS,
        help=f"Max temporal baseline for a pair (default: {MAX_TEMPORAL_BASELINE_DAYS}).",
    )
    args = parser.parse_args()

    # --- 1. AOI ----------------------------------------------------------------
    aoi = load_aoi_geometry(AOI_PATH)

    # --- 2. Catalog query ------------------------------------------------------
    scenes = search_sentinel1_slc(aoi, SEARCH_START, SEARCH_END)
    if not scenes:
        logger.error("No Sentinel-1 scenes found in the search window.")
        return 1

    # --- 3. Partition by flight direction (and path) ---------------------------
    logger.info("Partitioning scenes by flightDirection + path:")
    buckets = partition_by_flight_direction(scenes)

    if args.orbit != "BOTH":
        buckets = {k: v for k, v in buckets.items() if k.startswith(args.orbit)}
        logger.info(f"Restricted to orbit={args.orbit}; {len(buckets)} bucket(s) remain.")

    # --- 4. Build consecutive pairs per bucket ---------------------------------
    all_pairs: list[tuple[str, asf.ASFProduct, asf.ASFProduct]] = []
    for bucket_key, items in buckets.items():
        pairs = build_consecutive_pairs(items, args.max_baseline_days)
        logger.info(f"  {bucket_key}: {len(pairs)} consecutive pair(s) within baseline")
        for ref, sec in pairs:
            all_pairs.append((bucket_key, ref, sec))

    if not all_pairs:
        logger.error("No valid pairs to submit. Check baseline / orbit filters.")
        return 1

    logger.info(f"TOTAL planned interferograms: {len(all_pairs)}")

    # --- 5. Auth + dedupe ------------------------------------------------------
    logger.info("Authenticating with ASF HyP3...")
    try:
        hyp3 = sdk.HyP3()
        logger.info(f"Authenticated as: {hyp3.username}")
    except Exception as e:
        logger.critical(
            "HyP3 auth failed. Ensure NASA Earthdata credentials are in "
            f"~/_netrc (Windows) or ~/.netrc. Detail: {e}"
        )
        return 1

    try:
        quota = hyp3.check_quota()
        logger.info(f"Remaining HyP3 credits: {quota}  (planned jobs: {len(all_pairs)})")
    except Exception as e:
        logger.warning(f"Could not check quota: {e}")

    existing = fetch_existing_pair_signatures(hyp3, JOB_NAME_PREFIX)

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

        job_name = f"{JOB_NAME_PREFIX}_{bucket_key}"

        if not args.submit:
            logger.info(f"[DRY-RUN]      {bucket_key}  {ref_name} -> {sec_name}")
            continue

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
        logger.info("Re-run with --submit to actually queue jobs.")

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""
download_hyp3_products.py

Companion to submit_hyp3_jobs.py. Watches the HyP3 job queue for jobs that
match the Ramban_NH44 name prefix, downloads completed products into
data/raw_zips, and extracts the GeoTIFFs needed for QA + geomechanics
(coherence, unwrapped displacement, DEM, look vectors) into
data/processed_tiffs/<job_name>/.

Default behavior is a STATUS REPORT only (no downloads), so re-running is
safe and gives you a snapshot of the queue. Pass --watch to block until
everything in-flight finishes, --download to actually pull zips, or
--extract to unpack and trim each zip to the GeoTIFFs we care about.

Usage:
    python workflows/download_hyp3_products.py                 # status snapshot
    python workflows/download_hyp3_products.py --download      # download all SUCCEEDED jobs
    python workflows/download_hyp3_products.py --watch --download --extract
    python workflows/download_hyp3_products.py --name Ramban_NH44_ASCENDING_path100_frame102
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
import zipfile
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

import hyp3_sdk as sdk
from hyp3_sdk.exceptions import HyP3Error

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
RAW_DIR = PROJECT_ROOT / "data" / "raw_zips"
TIFF_DIR = PROJECT_ROOT / "data" / "processed_tiffs"

DEFAULT_NAME_PREFIX = "Ramban_NH44"

# Watch loop: poll the HyP3 API every N seconds. ASF docs recommend >= 60s
# to avoid hammering the service; jobs typically finish in 30-90 min.
WATCH_POLL_SEC = 90
WATCH_TIMEOUT_HOURS = 8

# GeoTIFF suffixes we care about for downstream QA + the geomechanics engine.
# HyP3 INSAR_GAMMA naming convention is documented at
# https://hyp3-docs.asf.alaska.edu/guides/insar_product_guide/
WANTED_TIFF_SUFFIXES = (
    "_unw_phase.tif",   # unwrapped phase -> convert to LOS displacement
    "_corr.tif",        # interferometric coherence (used for the 0.4 mask)
    "_dem.tif",         # co-registered DEM in radar geometry
    "_lv_theta.tif",    # look-vector incidence angle
    "_lv_phi.tif",      # look-vector azimuth angle
    "_water_mask.tif",  # water mask
)


# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------
load_dotenv()
LOG_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)
TIFF_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "hyp3_download.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("hyp3_download")


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def authenticate() -> sdk.HyP3:
    """Authenticate to HyP3 — fatal on failure (download requires creds)."""
    try:
        hyp3 = sdk.HyP3()
        user_id = hyp3.my_info().get("user_id", "<unknown>")
        logger.info(f"Authenticated as: {user_id}")
        return hyp3
    except Exception as e:
        logger.critical(
            "HyP3 auth failed. Ensure NASA Earthdata credentials are in "
            f"~/_netrc (Windows) or ~/.netrc, and the file is readable by "
            f"your user account. Detail: {e}"
        )
        sys.exit(1)


def fetch_jobs(hyp3: sdk.HyP3, name_filter: str | None) -> sdk.Batch:
    """Fetch jobs matching the given name prefix (None = all under the account).

    NOTE: hyp3_sdk's `find_jobs(name=X)` does EXACT-name match server-side, so
    we always fetch all jobs and prefix-filter client-side.
    """
    try:
        jobs = hyp3.find_jobs()
    except HyP3Error as e:
        logger.error(f"find_jobs failed: {e}")
        sys.exit(1)
    if name_filter:
        filtered = sdk.Batch([j for j in jobs if j.name and j.name.startswith(name_filter)])
        logger.info(
            f"Fetched {len(jobs)} jobs total; {len(filtered)} match prefix {name_filter!r}."
        )
        return filtered
    logger.info(f"Fetched {len(jobs)} jobs (no name filter).")
    return jobs


def report_status(jobs: sdk.Batch) -> Counter:
    """Print a status histogram and return the Counter."""
    by_status = Counter(j.status_code for j in jobs)
    logger.info("Status histogram:")
    for status, count in sorted(by_status.items()):
        logger.info(f"  {status:<12s} : {count}")
    return by_status


def watch_until_done(hyp3: sdk.HyP3, jobs: sdk.Batch) -> sdk.Batch:
    """Poll until every job leaves PENDING/RUNNING, or timeout fires."""
    deadline = time.time() + WATCH_TIMEOUT_HOURS * 3600
    while time.time() < deadline:
        # Refresh status from the API. sdk.Batch.refresh() returns a new Batch.
        try:
            jobs = hyp3.refresh(jobs)
        except HyP3Error as e:
            logger.warning(f"Refresh hit transient error: {e}. Retrying in {WATCH_POLL_SEC}s...")
            time.sleep(WATCH_POLL_SEC)
            continue

        in_flight = [j for j in jobs if j.status_code in ("PENDING", "RUNNING")]
        report_status(jobs)
        if not in_flight:
            logger.info("All jobs finished (or failed). Exiting watch loop.")
            return jobs

        logger.info(
            f"{len(in_flight)} job(s) still in flight. Sleeping {WATCH_POLL_SEC}s..."
        )
        time.sleep(WATCH_POLL_SEC)

    logger.error(f"Watch timeout after {WATCH_TIMEOUT_HOURS}h. Some jobs still pending.")
    return jobs


def download_succeeded(jobs: sdk.Batch) -> list[Path]:
    """Download .zip products for SUCCEEDED jobs; skip any zip already on disk."""
    succeeded = [j for j in jobs if j.status_code == "SUCCEEDED"]
    if not succeeded:
        logger.warning("No SUCCEEDED jobs to download.")
        return []

    new_files: list[Path] = []
    for job in succeeded:
        expected_name = f"{job.files[0]['filename']}" if job.files else None
        if expected_name:
            existing = RAW_DIR / expected_name
            if existing.exists() and existing.stat().st_size > 0:
                logger.info(f"[SKIP exists] {existing.name}")
                continue
        try:
            paths = job.download_files(location=RAW_DIR)
            for p in paths:
                logger.info(f"[DOWNLOAD]   {p.name} ({p.stat().st_size / 1e6:.1f} MB)")
                new_files.append(Path(p))
        except Exception as e:
            logger.error(f"Download failed for job {job.job_id} ({job.name}): {e}")
    return new_files


def extract_tiffs(zip_paths: list[Path]) -> None:
    """Unpack the wanted GeoTIFFs from each downloaded zip into TIFF_DIR/<stem>/."""
    if not zip_paths:
        # Allow --extract to operate on previously-downloaded zips too.
        zip_paths = sorted(RAW_DIR.glob("*.zip"))
        if not zip_paths:
            logger.warning("No zips found to extract.")
            return

    for zip_path in zip_paths:
        out_dir = TIFF_DIR / zip_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path) as zf:
                wanted = [
                    n for n in zf.namelist()
                    if n.lower().endswith(WANTED_TIFF_SUFFIXES)
                ]
                if not wanted:
                    logger.warning(f"[NO TIFFs] {zip_path.name}")
                    continue
                for member in wanted:
                    target = out_dir / Path(member).name
                    if target.exists() and target.stat().st_size > 0:
                        logger.info(f"  [skip existing] {target.name}")
                        continue
                    with zf.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())
                    logger.info(f"  [extract] {target.name}")
        except zipfile.BadZipFile:
            logger.error(f"Corrupt zip: {zip_path.name} — re-download required.")


# ------------------------------------------------------------------------------
# Driver
# ------------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--name",
        default=DEFAULT_NAME_PREFIX,
        help=f"Job name prefix to filter on (default: {DEFAULT_NAME_PREFIX!r}).",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Poll until all in-flight jobs finish before downloading.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download zip products for SUCCEEDED jobs.",
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Extract wanted GeoTIFFs from downloaded zips into data/processed_tiffs/.",
    )
    args = parser.parse_args()

    hyp3 = authenticate()

    try:
        credits = hyp3.check_credits()
        logger.info(f"Remaining HyP3 credits: {credits}")
    except Exception as e:
        logger.warning(f"Could not check credits: {e}")

    jobs = fetch_jobs(hyp3, args.name)
    if len(jobs) == 0:
        logger.info("No matching jobs found. Have you submitted with submit_hyp3_jobs.py --submit?")
        return 0

    if args.watch:
        jobs = watch_until_done(hyp3, jobs)
    else:
        report_status(jobs)

    new_zips: list[Path] = []
    if args.download:
        new_zips = download_succeeded(jobs)

    if args.extract:
        # If --download just ran, use the freshly downloaded set; otherwise
        # extract whatever is already in data/raw_zips.
        extract_tiffs(new_zips)

    if not (args.download or args.extract or args.watch):
        logger.info(
            "Status report only. Re-run with --download (and optionally "
            "--extract or --watch) to act on the queue."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())

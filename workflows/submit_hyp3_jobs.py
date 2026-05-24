#!/usr/bin/env python
"""
submit_hyp3_jobs.py

Template pipeline for submitting Interferometric SAR (InSAR) processing jobs to
the Alaska Satellite Facility (ASF) Hybrid Pluggable Processing Pipeline (HyP3)
focusing on landslide monitoring and slope deformation in the sensitive Ramban
region (Jammu and Kashmir) along the NH-44 highway.

Authenticates seamlessly using the NASA Earthdata Login configured in your .netrc
(or _netrc on Windows) home directory.

Prerequisites:
  1. Set up your ~/.netrc or ~/_netrc file.
  2. Activate the himalayas-geospatial environment:
     conda activate himalayas-geospatial
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import hyp3_sdk as sdk

# ------------------------------------------------------------------------------
# 1. SETUP LOGGING & PATHS
# ------------------------------------------------------------------------------
# Load environment variables (fallback configuration)
load_dotenv()

# Setup log directory and logger
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "hyp3_processing.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("hyp3_pipeline")

# Output directory for processed geotiff outputs
OUTPUT_DIR = Path("data/processed_tiffs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------
# 2. AUTHENTICATE WITH ASF HYP3
# ------------------------------------------------------------------------------
logger.info("Initializing ASF HyP3 SDK...")

try:
    # sdk.HyP3() automatically searches for NASA Earthdata credentials in:
    # 1. ~/.netrc (or ~/_netrc on Windows)
    # 2. Environment variables (EARTHDATA_USERNAME, EARTHDATA_PASSWORD)
    hyp3 = sdk.HyP3()
    logger.info(f"Successfully authenticated with HyP3. Account: {hyp3.username}")
except Exception as e:
    logger.critical(
        "Authentication failed. Please verify that your NASA Earthdata credentials "
        "are correctly added to your ~/.netrc (Mac/Linux) or ~/_netrc (Windows) file.\n"
        f"Detailed Error: {e}"
    )
    sys.exit(1)

# ------------------------------------------------------------------------------
# 3. DEFINE SENTINEL-1 GRANULE PAIRS FOR INSAR (RAMBAN, J&K)
# ------------------------------------------------------------------------------
# Reference and Secondary Granule pair selection (Sentinel-1 Single Look Complex - SLC)
# These represent Sentinel-1 SLC frames over the Ramban / Jammu & Kashmir region
# You can find exact granule IDs using the ASF Vertex UI (vertex.daac.asf.alaska.edu)
REFERENCE_GRANULE = "S1A_IW_SLC__1SDV_20230501T130124_20230501T130151_048341_05D0D5_7D22"
SECONDARY_GRANULE = "S1A_IW_SLC__1SDV_20230513T130125_20230513T130152_048516_05D6E1_6B34"

logger.info(f"Preparing Ramban InSAR Job submission:")
logger.info(f"  - Reference: {REFERENCE_GRANULE}")
logger.info(f"  - Secondary: {SECONDARY_GRANULE}")

# ------------------------------------------------------------------------------
# 4. SUBMIT PROCESSING JOB
# ------------------------------------------------------------------------------
# Set run_submission to True to actually submit the job.
# Note: ASF provides a free tier quota of processing credits for research.
run_submission = False

if not run_submission:
    logger.warning("Submission flag 'run_submission' is set to False.")
    logger.info("To submit actual jobs, change 'run_submission = True' in this script.")
    logger.info("Demonstrating how to check quota and existing active jobs instead...")
    
    # Check remaining credits quota
    try:
        quota = hyp3.check_quota()
        logger.info(f"Remaining HyP3 processing credits: {quota}")
    except Exception as e:
        logger.error(f"Failed to check quota: {e}")
        
    # List previously submitted jobs under your account
    try:
        my_jobs = hyp3.find_jobs()
        logger.info(f"Found {len(my_jobs)} historical/active jobs in your account.")
        if my_jobs:
            logger.info("Most recent job status:")
            logger.info(my_jobs[0])
    except Exception as e:
        logger.error(f"Failed to fetch historical jobs: {e}")
        
    sys.exit(0)

# Submit the InSAR processing job
try:
    logger.info("Submitting InSAR job to ASF...")
    # Other parameters can be configured (e.g. looks, water_masking, etc.)
    job = hyp3.submit_insar_job(
        granule1=REFERENCE_GRANULE,
        granule2=SECONDARY_GRANULE,
        name="Ramban_Landslide_InSAR",
        include_dem=True,
        include_look_vectors=True,
        include_wrapped_phase=False,
        apply_water_mask=True
    )
    logger.info(f"Job submitted successfully! Job ID: {job.job_id}")
    logger.info(f"Job status: {job.status_code} ({job.name})")

except Exception as e:
    logger.error(f"Job submission failed: {e}")
    sys.exit(1)

# ------------------------------------------------------------------------------
# 5. WATCH JOB & AUTOMATICALLY DOWNLOAD PRODUCTS
# ------------------------------------------------------------------------------
try:
    logger.info("Monitoring job progress. This block will wait until the job completes...")
    # hyp3.watch() will poll the API and block until processing finishes.
    # Safe to run in terminal; has a built-in progress indicator.
    completed_jobs = hyp3.watch(job)
    logger.info("Processing complete!")
    
    # Download processed datasets
    logger.info(f"Downloading GeoTIFF products to: {OUTPUT_DIR}/")
    downloaded_files = completed_jobs.download_files(dest_dir=OUTPUT_DIR)
    
    for file_path in downloaded_files:
        logger.info(f"Downloaded: {file_path.name}")
        
except Exception as e:
    logger.error(f"Error during job monitoring/download: {e}")
    sys.exit(1)

logger.info("HyP3 workflow pipeline finished successfully.")

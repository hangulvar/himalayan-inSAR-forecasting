#!/usr/bin/env bash
# Run MintPy SBAS on frame106 WITH ERA5 tropospheric correction (MintPy step 3),
# then export velocity + temporalCoherence GeoTIFFs to data/mintpy/<stack>/mintpy_out/.
#
# MUST run inside the insar-mintpy image (pyaps3 + ~/.cdsapirc auto-mounted):
#   docker compose run --rm mintpy bash /app/workflows/run_mintpy_era5_f106.sh
# Prereq: workflows/prep_mintpy.py already built data/mintpy/<stack>/hyp3/.
#
# The work dir is the container-local /tmp — the OneDrive/WSL2 bind mount cannot
# utime, which crashes MintPy's metadata-preserving copies (error_history_log
# 2026-05-31). Inputs are read from /app (reads are fine); only outputs are copied
# back. Idempotent only via overwrite: it rm -rf's the /tmp work dir each run.
LOG=/app/logs/mintpy_era5_f106.log
mkdir -p /app/logs
exec > >(tee "${LOG}") 2>&1
set -euo pipefail

STACK=ASC_path27_frame106
CFG=/app/workflows/mintpy_f106_era5.cfg
W=/tmp/sbas_f106_era5
OUT=/app/data/mintpy/${STACK}/mintpy_out

mkdir -p "${OUT}"
rm -rf "${W}"
mkdir -p "${W}/weather"
cd "${W}"

echo "=== ERA5 SBAS run start $(date -u) ==="
smallbaselineApp.py "${CFG}" --end velocity
save_gdal.py velocity.h5 -d velocity -o velocity_mintpy_era5.tif
save_gdal.py temporalCoherence.h5 -o temporalCoherence_mintpy.tif
cp velocity.h5 "${OUT}/velocity_era5.h5"
cp velocity_mintpy_era5.tif temporalCoherence_mintpy.tif "${OUT}/"
echo "ERA5_RUN_DONE $(date -u)"

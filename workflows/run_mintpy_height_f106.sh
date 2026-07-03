#!/usr/bin/env bash
# Run MintPy SBAS on frame106 with the EMPIRICAL height-correlation tropospheric
# correction (Doin et al. 2009), the third arm of the tropo-method comparison
# (Bekaert et al. 2015). Exports velocity_mintpy_height.tif to mintpy_out/.
#
# MUST run inside the insar-mintpy image:
#   docker compose run --rm mintpy bash /app/workflows/run_mintpy_height_f106.sh
# Prereq: workflows/prep_mintpy.py already built data/mintpy/<stack>/hyp3/ (same data
# the no-tropo + ERA5 runs used). No external download (unlike ERA5/GACOS).
#
# Work dir is the container-local /tmp (the bind mount cannot utime -> crashes MintPy's
# metadata copies; error_history_log 2026-05-31). Inputs read from /app; only the
# velocity output is copied back. temporalCoherence is identical across tropo methods
# (it comes from the network inversion, BEFORE the tropo step) so we do NOT re-export it.
LOG=/app/logs/mintpy_height_f106.log
mkdir -p /app/logs
exec > >(tee "${LOG}") 2>&1
set -euo pipefail

STACK=ASC_path27_frame106
CFG=/app/workflows/mintpy_f106_height.cfg
W=/tmp/sbas_f106_height
OUT=/app/data/mintpy/${STACK}/mintpy_out

mkdir -p "${OUT}"
rm -rf "${W}"
mkdir -p "${W}"
cd "${W}"

echo "=== height-correlation SBAS run start $(date -u) ==="
smallbaselineApp.py "${CFG}" --end velocity
save_gdal.py velocity.h5 -d velocity -o velocity_mintpy_height.tif
cp velocity.h5 "${OUT}/velocity_height.h5"
cp velocity_mintpy_height.tif "${OUT}/"
echo "HEIGHT_RUN_DONE $(date -u)"

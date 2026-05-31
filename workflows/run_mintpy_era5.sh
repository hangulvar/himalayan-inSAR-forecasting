#!/usr/bin/env bash
# Run MintPy SBAS WITH ERA5 tropospheric correction for ANY prepared stack
# (generalises run_mintpy_era5_f106.sh). Usage, inside the insar-mintpy image:
#   docker compose run --rm mintpy bash /app/workflows/run_mintpy_era5.sh <STACK>
# Prereq: workflows/prep_mintpy.py --stack <STACK> built data/mintpy/<STACK>/hyp3/.
#
# Work dir is the container-local /tmp — the OneDrive/WSL2 bind mount cannot utime,
# which crashes MintPy's metadata-preserving copies (error_history_log 2026-05-31).
# pyaps3 reads ~/.cdsapirc (auto-mounted) and hits the new CDS endpoint.
#
# NOTE on DESC stacks: their KEEP date-network is temporally DISCONNECTED (multiple
# islands). Running the FULL network lets MintPy SVD-resolve the inter-island offsets,
# but that biases the velocity badly (frame479 full-network: std 57 mm/yr, 9k px
# >100 mm/yr — physically implausible). So we PERIOD-SPLIT: restrict the network to one
# fully-connected island via NET_START_DATE/NET_END_DATE — a well-posed least-squares
# with no SVD bias. (frame484 had only 0.8% usable pixels at any reference → dumped.)
#
# Optional env vars (pass with `docker compose run -e NAME=VAL ...`):
#   NET_START_DATE / NET_END_DATE = YYYYMMDD — keep only interferograms inside this
#     window (period-split to one connected island). Default: full network.
# There is no custom-inverter result for DESC stacks, so there is no cross-validation;
# inspect coverage + temporalCoherence + the velocity distribution instead.
LOG_STACK="${1:?usage: run_mintpy_era5.sh <STACK>  (opt env: NET_START_DATE/NET_END_DATE)}"
NET_START_DATE="${NET_START_DATE:-}"
NET_END_DATE="${NET_END_DATE:-}"
LOG=/app/logs/mintpy_era5_${LOG_STACK}.log
mkdir -p /app/logs
exec > >(tee "${LOG}") 2>&1
set -euo pipefail

STACK="${LOG_STACK}"
IN=/app/data/mintpy/${STACK}/hyp3
OUT=/app/data/mintpy/${STACK}/mintpy_out
W=/tmp/sbas_${STACK}

mkdir -p "${OUT}"
rm -rf "${W}"
mkdir -p "${W}/weather"
cd "${W}"

cat > "${W}/${STACK}_era5.cfg" <<EOF
mintpy.load.processor      = hyp3
mintpy.load.unwFile        = ${IN}/*_unw_phase_clip.tif
mintpy.load.corFile        = ${IN}/*_corr_clip.tif
mintpy.load.connCompFile   = no
mintpy.load.demFile        = ${IN}/*_dem_clip.tif
mintpy.load.incAngleFile   = ${IN}/*_lv_theta_clip.tif
mintpy.load.azAngleFile    = ${IN}/*_lv_phi_clip.tif
mintpy.load.waterMaskFile  = ${IN}/*_water_mask_clip.tif
mintpy.compute.cluster     = no
mintpy.troposphericDelay.method       = pyaps
mintpy.troposphericDelay.weatherModel = ERA5
mintpy.troposphericDelay.weatherDir   = ${W}/weather
EOF

if [ -n "${NET_START_DATE}" ]; then
  echo "mintpy.network.startDate = ${NET_START_DATE}" >> "${W}/${STACK}_era5.cfg"
fi
if [ -n "${NET_END_DATE}" ]; then
  echo "mintpy.network.endDate   = ${NET_END_DATE}" >> "${W}/${STACK}_era5.cfg"
fi
if [ -n "${NET_START_DATE}${NET_END_DATE}" ]; then
  echo "NOTE: period-split network to [${NET_START_DATE:-min}, ${NET_END_DATE:-max}] for ${STACK}"
fi

echo "=== ERA5 SBAS run start $(date -u) for ${STACK} ==="
smallbaselineApp.py "${W}/${STACK}_era5.cfg" --end velocity
save_gdal.py velocity.h5 -d velocity -o velocity_mintpy_era5.tif
save_gdal.py temporalCoherence.h5 -o temporalCoherence_mintpy.tif
cp velocity.h5 "${OUT}/velocity_era5.h5"
cp velocity_mintpy_era5.tif temporalCoherence_mintpy.tif "${OUT}/"
echo "ERA5_RUN_DONE ${STACK} $(date -u)"

# syntax=docker/dockerfile:1

# ─────────────────────────────────────────────────────────────────────────────
# Himalayan InSAR hazard pipeline — Linux runtime image (environment only).
#
# WHY THIS EXISTS: nearly every multi-hour bug in this project was Windows-
# specific (the 0xC06D007F BLAS-DLL crash, the matplotlib draw crash, conda-4.12
# solver hangs, cp1252 logging, _netrc-as-a-folder). A Linux container removes
# that entire class and is the platform MintPy is developed/tested on. See
# InSAR_hazard_forecasting_Context.md (Roadmap 0a) and error_history_log.md.
#
# SCOPE: reproduces the CURRENT Phase 1-4 pipeline. The image carries the conda
# environment ONLY; the project (code + the ~73 GB data/ dir + config/)
# is BIND-MOUNTED at /app at run time (see ../docker-compose.yml), so nothing
# large or machine-specific is baked into the image.
# ─────────────────────────────────────────────────────────────────────────────

# micromamba: small, fast, conda-forge-native base. Pinned tag for
# reproducibility — adjust if this exact tag is unavailable on your registry.
FROM mambaorg/micromamba:1.5.10

# Conda-forge-only, version-pinned spec (mirrors environment.yml for linux-64).
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.docker.yml /tmp/environment.docker.yml

# Install into the BASE env so micromamba's _entrypoint.sh auto-activates it for
# every `docker run` / compose command. That auto-activation is precisely what
# makes the Windows activation bug (numpy unable to find its BLAS libraries)
# structurally impossible inside this container.
RUN micromamba install -y -n base -f /tmp/environment.docker.yml \
    && micromamba clean --all --yes

# Activate base for the remaining build steps, so `pip` below is base's pip.
ARG MAMBA_DOCKERFILE_ACTIVATE=1

# Cloud-API Python clients (Phase 1 ASF submit/download + GEE for fetch_chirps.py).
# Pinned here rather than in the conda spec to keep pip deps explicit and avoid
# env-file pip-section ambiguity under micromamba. earthengine-api matches the
# spec in requirements.txt; it is a thin REST client (no heavy native deps).
RUN pip install --no-cache-dir hyp3_sdk==7.7.6 asf_search==12.2.2 "earthengine-api>=0.1.300"

WORKDIR /app

# Default to an interactive shell. Override per run, e.g.:
#   docker compose run --rm insar python workflows/custom_sbas_inverter.py
CMD ["bash"]

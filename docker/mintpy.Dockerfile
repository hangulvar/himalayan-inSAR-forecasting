# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# MintPy image — the field-standard SBAS migration (Roadmap §1).
#
# Separate from the lean `insar` image (docker/Dockerfile): MintPy's deps are
# heavy, so we isolate them rather than bloat the pipeline image. At run time the
# project (HyP3 products + outputs) is bind-mounted at /app and the CDS/ERA5
# credentials (~/.cdsapirc) are mounted read-only — see ../docker-compose.yml
# (CDSAPI_RC in .env). Build context is ./docker (tiny).
#
# Installs into the BASE env so micromamba's entrypoint auto-activates it (same
# pattern as the insar image — no manual activation, so numpy/BLAS just work).
# ─────────────────────────────────────────────────────────────────────────────
FROM mambaorg/micromamba:1.5.10

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.mintpy.yml /tmp/environment.mintpy.yml
RUN micromamba install -y -n base -f /tmp/environment.mintpy.yml \
    && micromamba clean --all --yes

ARG MAMBA_DOCKERFILE_ACTIVATE=1
# Fail the build early if the key tools are missing; report the CLI location.
RUN python -c "import mintpy, pyaps3, cdsapi; print('mintpy + pyaps3 + cdsapi import OK')" \
    && python -c "import shutil; print('smallbaselineApp.py ->', shutil.which('smallbaselineApp.py'))"

WORKDIR /app
CMD ["bash"]

# 🐳 Running the pipeline in Docker (Linux)

A reproducible Linux container for the Himalayan InSAR hazard pipeline.

## Why this exists

Nearly every multi-hour bug in this project has been **Windows-specific**: the
`0xC06D007F` BLAS-DLL crash, the matplotlib draw crash, conda-4.12 solver hangs,
cp1252 logging errors, `_netrc`-as-a-folder. A Linux container eliminates that
**entire class** of problems, is the platform MintPy is developed and tested on,
and *is* the "separate env" done reproducibly. It doubles as the project's
public-release reproducibility artifact. (See
[`InSAR_hazard_forecasting_Context.md`](../InSAR_hazard_forecasting_Context.md)
Roadmap §0a and [`error_history_log.md`](../error_history_log.md).)

The in-script Windows DLL bootstrap (`if sys.platform == "win32"`) becomes a
harmless no-op inside the container.

## What's in the image (and what isn't)

- **In the image:** the conda environment only — `gdal`, `rasterio`, `geopandas`,
  `shapely`, `numpy`, `scipy`, `matplotlib-base`, `python-dotenv`, plus pip
  `hyp3_sdk` and `asf_search`. Installed into the **base** env so it
  auto-activates on every command (no manual `conda activate`, so the activation
  bug cannot occur).
- **Not in the image — bind-mounted at run time:** the project code, the ~73 GB
  `data/` directory, `logs/`, and `ramban_aoi.geojson`. Nothing large or
  machine-specific is baked in.
- **Deliberate deviations from `environment.yml`:** conda-forge **only** (no
  `defaults` channel); `matplotlib-base` instead of `matplotlib` (headless, no
  GUI deps — scripts emit SVG/HTML, not interactive plots); `jupyterlab` omitted
  (dev-only, unused by any pipeline script). Versions are pinned in
  [`environment.docker.yml`](environment.docker.yml).

## Prerequisites

1. **Docker Desktop running** (WSL2 backend on Windows). If `docker info` errors
   with *"failed to connect to the docker API"*, start Docker Desktop first.
2. Run all commands **from the project root** (where `docker-compose.yml` lives),
   not from `docker/`.

## Build

```powershell
docker compose build
```

First build solves the geospatial env and downloads packages — expect several
minutes. Subsequent builds are cached.

## Run

Open an interactive shell (the base env is already active):

```powershell
docker compose run --rm insar
# then, inside the container:
python workflows/custom_sbas_inverter.py
```

Or run a single phase directly (no shell):

```powershell
# Phase 2 — SBAS velocity inversion
docker compose run --rm insar python workflows/custom_sbas_inverter.py

# Phase 3 — geomechanical hazard engine
docker compose run --rm insar python workflows/geomechanical_engine.py

# Phase 4A — agentic warning system
docker compose run --rm insar python workflows/agentic_orchestrator.py

# Phase 4B — interactive 3-D dashboard
docker compose run --rm insar python workflows/build_3d_dashboard.py

# Plumbing smoke test (stdlib only)
docker compose run --rm insar python tests/test_plumbing.py
```

Outputs land in the bind-mounted `data/` on the host, exactly as on Windows.

> **Note:** Phases 2–4 re-run against the existing `data/` and need no
> credentials. Phase 1 (ASF submit/download) needs `~/.netrc` — see below.

## Phase 1 (ASF) — mounting credentials

Phase 1 (`submit_hyp3_jobs.py`, `download_hyp3_products.py`) needs NASA Earthdata
credentials. The ASF libraries read `~/.netrc` (Linux), which is
`/home/mambauser/.netrc` in this image. To enable:

1. In `docker-compose.yml`, uncomment the netrc volume line.
2. Point `NETRC_PATH` at your host credentials file and run, e.g. (PowerShell):

   ```powershell
   $env:NETRC_PATH = "$env:USERPROFILE\.netrc"
   docker compose run --rm insar python workflows/submit_hyp3_jobs.py
   ```

   (On Windows the file may be `_netrc`; mount whichever you maintain to
   `/home/mambauser/.netrc`.)

## Reproducibility lockfile (do once, after the first successful build)

The spec (`environment.docker.yml`) pins minor versions; the **byte-exact**
artifact is an explicit lock generated from the built env. Generate and commit it
so future builds are identical:

```powershell
docker compose run --rm --no-TTY insar micromamba env export --name base --explicit > docker/conda-linux-64.lock
```

Commit `docker/conda-linux-64.lock` alongside the Dockerfile. (A later step can
switch the Dockerfile to build from this lock for fully pinned rebuilds.)

## Troubleshooting

| Symptom | Fix |
|---|---|
| `failed to connect to the docker API` | Start Docker Desktop (WSL2 backend). |
| `manifest unknown` / image tag not found | Adjust the `mambaorg/micromamba` tag in [`Dockerfile`](Dockerfile) to an available version. |
| Phase 1 auth errors | Mount `~/.netrc` (see above) and confirm the Earthdata OAuth app is approved (root `README.md` Step 3). |
| Slow file access on `data/` | Expected for OneDrive/Windows paths over the WSL2 bind mount; functional but not fast. |

# 🏔️ Geospatial Analysis & Hazard Monitoring in the Western Himalayas

A geospatial data science project that detects landslide-prone slopes from space and turns the measurement into ranked, explainable **decision support**: which slopes deserve inspection, and when vigilance should rise. Two live case studies in Jammu & Kashmir: the **NH-44 corridor through Ramban** (the original build) and the **Vaishno Devi pilgrimage corridor on the Trikuta massif** (the point-anywhere replication — disaster-validated, and in live WATCH through the 2026 monsoon).

### 🎉 Status: a validated two-site decision-support prioritization prototype

**The claim, precisely:** this product **ranks WHERE to inspect and WHEN to heighten vigilance**, scored against verified landslide inventories. It is **not a warning system** — it does not predict individual landslides, and no safety, travel, or evacuation decision should rest on it. That smaller claim is the honest one, and every number behind it is validated and committed.

The full chain — built and hardened on Ramban, then re-pointed at a second AOI by editing one config file:

> **raw Sentinel-1 radar → clean, audited data → ground-movement velocity → physics-based hazard map → explainable, rainfall-gated prioritization (two-tier ALERT/WATCH) + browser dashboard (with a plain-language Guide tab).**

| Phase | What it does | Status |
|---|---|---|
| **1 — Data pipeline & integrity** | Fetch Sentinel-1, mask noise, audit atmosphere, verify network | ✅ Both sites |
| **2 — SBAS velocity inversion** | Interferograms → LOS displacement time-series + mean velocity | ✅ Multi-stack union |
| **3 — Geomechanical engine** | Slope + TWI + Infinite-Slope Factor of Safety, fused with creep | ✅ Site-calibrated soils |
| **4A — Agentic decision support** | Two-tier ALERT/WATCH footprints × rainfall gate × per-zone ranking | ✅ Live at both sites |
| **4B — Interactive UIs** | 3-D hazard explorer + publish-ready operational dashboard | ✅ Complete |

#### Beyond the MVP — the validation and operations arc

Full detail + every headline number lives in the **committed** [RESULTS_AND_KPIS.md](RESULTS_AND_KPIS.md) (cited below by §); live state in [SESSION_REVIEW.md](SESSION_REVIEW.md):

- **Reproducibility & scale:** Dockerized; AOI-parameterized (`config.yaml` points the whole pipeline at a new site); ascending stacks inverted into a **union hazard mosaic**; the descending stacks evaluated and honestly **rejected** as too noisy. **MintPy + ERA5** cross-check corroborates the custom SBAS engine (§9).
- **The operational warning (Ramban, §16–§25):** a **two-tier ALERT/WATCH** product with per-zone detection confidence, triage ranking, and a regional intensity–duration **rainfall gate** — the scored back-test beats chance, and a worked self-correction (a wrong news date had inverted a conclusion — §12g) set the project's verified-ground-truth rule.
- **The second site (Vaishno Devi, §26–§32):** the entire pipeline re-pointed at the Trikuta shrine corridor; **validated against the 26 Aug 2025 Ardhkuwari disaster** (temporal Δ=0 catch + beats-chance spatial score, §31) with operating points earned by a local sweep (§32), on a 12.5 m DEM (§30).
- **Route exposure & field targets (§28, §33–§34):** per-segment track exposure, a 2-track-confirmed creep target with field briefs + GPS KMLs, and a **fast-failure toolkit** for the brittle rockfall class — per-cycle coherence-drop tripwire, energy-line runout screen (the shrine complex sits in the LIKELY cone), and an institutional-records cross-check.
- **Soil parameters site-corroborated (§36–§38):** site literature (incl. a pathway back-analysis paper) brackets every strength value in use — the "borrowed soils" caveat is retired; temporal validation now rests on **two independent fatal events, both caught on the day** (Ardhkuwari §31 + the 21 Jul 2025 Banganga landslide §38).
- **Live operations (§35):** a routine radar-cadence cycle (resubmit → QA → invert → re-score) plus a rainfall-refresh loop; the monsoon onset flipped the VD site **DORMANT → WATCH** on 2026-07-04, with all vulnerable zones active — the per-zone gate doing exactly what it was built for.

This honest style — every result tagged `[MOCK]`/`[REAL]`/`[MEASURED]`, negatives reported as plainly as positives, **and conclusions revised when the evidence changes** — is the project's scientific posture. The dashboard is a **decision-support prioritization prototype — not a warning system**: it ranks where to inspect and when vigilance should rise, does not predict individual landslides, and says so prominently.

**New here? Read [SESSION_REVIEW.md](SESSION_REVIEW.md) first** (the living "start here" dashboard), then [milestone.md](milestone.md) for the plain-language story. Deep detail lives in [session_journey.md](session_journey.md) (decisions) and [error_history_log.md](error_history_log.md) (bugs + fixes). The science is in [Research/Foundations - Physics and Maths Primer.md](Research/Foundations%20-%20Physics%20and%20Maths%20Primer.md).

---

## 📁 Repository Structure

```tree
Geospatial Analysis Himalayas/
│
├── README.md                       # This file
├── NEW_AOI_PLAYBOOK.md             # Deterministic recipe for onboarding a new AOI
├── CLAUDE.md                       # Behavioural rules for AI-assisted dev
├── SESSION_REVIEW.md               # 🚦 "Start here" living dashboard (read first)
├── milestone.md                    # Plain-language story of each milestone (for humans)
├── session_journey.md              # Session-by-session decisions and reasoning
├── error_history_log.md            # Every bug + root cause + fix from this project
├── InSAR_hazard_forecasting_Context.md  # Original project vision + roadmap
│
├── .gitignore                      # Blocks credentials and large rasters from Git
├── .netrc.template                 # NASA Earthdata + CDSE + USGS credential setup
├── .env.template                   # Optional API keys (Mapbox, GEE, etc.)
├── environment.yml                 # Conda-forge environment spec (insar_qa_env)
├── requirements.txt                # Pip fallback (NOT recommended for geospatial)
├── ramban_aoi.geojson              # Area-of-Interest polygon (Ramban / NH-44)
│
├── workflows/                      # Pipeline scripts (by phase)
│   ├── submit_hyp3_jobs.py             # P1: ASF HyP3 InSAR submission (SBAS N=3)
│   ├── download_hyp3_products.py       # P1: watch + download + extract (zip-verified)
│   ├── feature_engineering.py          # P1.2: coherence masking → LOS displacement
│   ├── phase_elevation_audit.py        # P1.3: atmospheric (phase-elevation) audit
│   ├── export_audit_json.py            # P1.3: minimal audit_log.json
│   ├── _consolidate_quarantine.py      # P1: merge coherence + atmospheric audits
│   ├── _analyze_qa_stats.py            # P1: per-stack QA statistics
│   ├── sbas_network_graph.py           # P1.4: SBAS connectivity check + SVG diagrams
│   ├── apply_connectivity_rescues.py   # P1.4: rescue bridging CONCERN pairs
│   ├── custom_sbas_inverter.py         # P2: SBAS time-series inversion → velocity
│   ├── geomechanical_engine.py         # P3: slope + TWI + Factor of Safety + hazard fusion
│   ├── agentic_orchestrator.py         # P4A: 3-agent warning system → alerts + dashboard
│   ├── build_3d_dashboard.py           # P4B: interactive 3-D hazard explorer (HTML)
│   ├── aoi_status.py                   # Multi-AOI status dashboard + next-step guide
│   ├── proj_pipeline_AOI.md            # Future AOI shortlist
│   └── .gitkeep
│
├── tests/
│   └── test_plumbing.py            # Stdlib-only plumbing assertions
│
├── data/                           # Outputs (Git-ignored)
│   ├── raw_zips/                       # HyP3 product zips (183 × ~200 MB)
│   ├── processed_tiffs/                # Extracted GeoTIFFs per product (incl. DEM)
│   ├── qa_masks/                       # P1: NaN-masked LOS displacement + QA artifacts
│   │   ├── <product>/<product>_masked_disp.tif
│   │   ├── _coherence_mask_stats.csv  _atmospheric_audit.csv  audit_log.json
│   │   ├── _quarantine_list.csv  _rescued_for_connectivity.json
│   │   └── _network_graphs/            # baseline SVGs + index.html + report
│   ├── velocity/                       # P2: mean velocity, time-series, temporal coherence
│   ├── hazard/                         # P3: slope, TWI, FS_dry, FS_saturated, hazard_class
│   └── alerts/                         # P4A: alerts_*.json, alert_report_*.md, dashboard_*.html
│
├── logs/                           # Run logs from every workflow script
│
├── Research/                       # Background literature + the science primer
│   ├── Foundations - Physics and Maths Primer.md   # Beginner science base (Phases 1–4A)
│   ├── Joshimath InSAR.pdf  ·  Meteorology.md  ·  ...
│
├── src/                            # Reserved for reusable modules (currently empty)
└── config/                         # ★ Per-AOI config REGISTRY (one YAML per site)
    ├── ramban.yaml                     # Ramban NH-44 (the original build)
    └── vaishnodevi.yaml                # Vaishno Devi — Trikuta corridor
```

---

## ✈️ Pre-Flight Checklist

Before writing any analysis code, get the infrastructure right. Two things below caused multi-hour delays earlier in this project — read these first to avoid them.

### 1. NEVER create the conda environment inside a cloud-sync folder

This project lives inside OneDrive (`C:\Users\<you>\OneDrive\...`). Conda envs contain thousands of small files; OneDrive's file-watcher locks them as conda writes them, corrupting the env mid-install. **Always use a named env (`-n insar_qa_env`)** so it lands in `~/.conda/envs/`, NOT a project-local `.conda/`.

### 2. Use a modern conda (libmamba solver) — NOT old miniconda 4.x

The classic solver in conda 4.12 (released 2022) hangs for hours on the geospatial dependency graph. This project uses `C:\ProgramData\anaconda3\` (conda 24.x with libmamba). Check `conda --version`; if it's < 23.0, install a newer Anaconda/Miniconda before going further.

### 3. Authentication has FOUR distinct setup steps

NASA Earthdata's OAuth has a one-time browser approval step that's easy to miss. See the [Authentication section](#-authentication--api-setup) below — all four steps are mandatory.

### 4. Folder hierarchy

* Raw HyP3 zips → `data/raw_zips/`
* Extracted GeoTIFFs → `data/processed_tiffs/<product>/`
* Masked + audited displacement rasters → `data/qa_masks/<product>/`
* Diagnostic CSVs, JSON, SVG → `data/qa_masks/_*.{csv,json,html}` and `_network_graphs/`
* Run logs → `logs/`

The leading underscore on diagnostic files keeps them out of the per-product directory walkers used by the masker and tests.

---

## 🛠️ Environment Setup

### Docker (recommended) — reproducible Linux container

The whole pipeline now runs in a reproducible **Linux container**, which eliminates
the Windows-specific issues (notably the `0xC06D007F` BLAS-DLL crash). Build once,
then run any phase; the project (code + the ~73 GB `data/`) is bind-mounted at `/app`
so nothing large is baked into the image.

```bash
docker compose build                                  # builds insar-himalaya:latest
docker compose run --rm insar python workflows/agentic_orchestrator.py
```

Full build/run/credentials guide: **[`docker/README.md`](docker/README.md)**. MintPy
(field-standard SBAS, heavier deps) has its **own** image: `docker compose build mintpy`.

### Conda (native, alternative)

```bash
# From the project root (which is inside OneDrive — that's fine for source code,
# just not for the env itself):
conda env create -f environment.yml
conda activate insar_qa_env
```

The env builds to `~/.conda/envs/insar_qa_env/` by default — outside OneDrive, immune to sync collisions.

**If env creation fails with memory errors or hangs:** you're probably using the old miniconda 4.12 solver. Invoke a newer conda by full path:

```bash
"C:\ProgramData\anaconda3\Scripts\conda.exe" env create -f environment.yml
```

### Verifying the env

```bash
python -c "import geopandas, rasterio, asf_search, hyp3_sdk; \
print('geopandas', geopandas.__version__); \
print('rasterio', rasterio.__version__); \
print('asf_search', asf_search.__version__); \
print('hyp3_sdk', hyp3_sdk.__version__)"
```

Expected versions (as of this commit): geopandas 1.1.3, rasterio 1.4.3, asf_search 12.2.2, hyp3_sdk 7.7.6. Python 3.10.20.

### Pip fallback — NOT recommended

`requirements.txt` exists but is fragile on Windows. Use it only if you absolutely cannot install conda. Geospatial libs (GDAL, PROJ, GEOS) wrap C/C++ binaries that the conda-forge channel ships pre-compiled — pip wheels for these are inconsistent across platforms.

---

## 🔐 Authentication & API Setup

Four distinct steps. **All four are required** before any HyP3 submission will succeed.

### Step 1: Create accounts

| Service | URL | What you'll need it for |
|---|---|---|
| **NASA Earthdata Login** | https://urs.earthdata.nasa.gov/ | ASF HyP3 (primary) |
| **Copernicus Data Space** | https://dataspace.copernicus.eu/ | Sentinel-1/2 raw access (optional) |
| **USGS EarthExplorer** | https://earthexplorer.usgs.gov/ | Landsat, USGS DEMs (optional) |

### Step 2: Configure `~/.netrc`

Copy `.netrc.template` to `~/.netrc` (Mac/Linux) or `C:\Users\<you>\.netrc` (Windows — note the leading dot, NOT underscore, despite legacy convention).

**Critical:** the file must be a regular FILE, not a folder. Verify with:

```powershell
Get-Item ~/.netrc | Select-Object Attributes      # should show "Archive", NOT "Directory"
```

Then strip everything except machine entries. Python's stdlib `netrc` parser rejects comment-heavy files with a misleading "bad toplevel token" error — keep the file minimal:

```
machine urs.earthdata.nasa.gov
  login YOUR_EARTHDATA_USERNAME
  password YOUR_EARTHDATA_PASSWORD
machine dataspace.copernicus.eu
  login YOUR_COPERNICUS_USERNAME
  password YOUR_COPERNICUS_PASSWORD
machine ers.cr.usgs.gov
  login YOUR_USGS_USERNAME
  password YOUR_USGS_PASSWORD
```

Verify Python can read it:

```bash
python -c "import netrc, os; print(netrc.netrc(os.path.expanduser('~/.netrc')).hosts.keys())"
# Expected: dict_keys(['urs.earthdata.nasa.gov', 'dataspace.copernicus.eu', 'ers.cr.usgs.gov'])
```

### Step 3: Authorize the HyP3 OAuth app (one-time, per Earthdata account)

Open this URL in a browser while logged into Earthdata, then click **Approve**:

> https://urs.earthdata.nasa.gov/approve_app?client_id=BO_n7nTIlMljdvU6kRRB3g

Without this step, every `hyp3_sdk.HyP3()` call will fail with `AuthenticationError: Pre authorization required`. Once approved, every future SDK call authenticates silently.

### Step 4: (Optional) `.env` for non-Earthdata services

Copy `.env.template` to `.env` and fill in Mapbox / GEE / Sentinel Hub keys if you'll use those. The `.gitignore` is pre-configured to never commit `.env`. `.env` also records the **host paths** of your credential files (`NETRC_PATH`, `CDSAPI_RC`) so the Docker containers auto-mount them.

### Step 5: (Optional) Copernicus CDS / ERA5 — for the MintPy tropospheric correction

Only needed for MintPy's ERA5 atmospheric correction. Copy `.cdsapirc.template` to `~/.cdsapirc` (Windows `%USERPROFILE%\.cdsapirc`) and paste your **CDS Personal Access Token** from https://cds.climate.copernicus.eu/how-to-api (new-CDS format: `url:` + `key:`), then accept the *"ERA5 hourly data on pressure levels"* licence on the CDS site. Set `CDSAPI_RC=<that path>` in `.env` so the `mintpy` container mounts it read-only. The real `.cdsapirc` is git-ignored. Full notes: `SESSION_REVIEW.md` §4.

### Step 6: (Optional) Google Earth Engine — for CHIRPS gauge rainfall

Only needed for `workflows/fetch_chirps.py` (gauge-blended CHIRPS daily rainfall, the cross-check to ERA5-Land). One-time host setup: (1) have a Google Cloud project with the **Earth Engine API** enabled (https://code.earthengine.google.com); (2) run `earthengine authenticate` — opens a browser, writes `~/.config/earthengine/credentials`; (3) set `EE_PROJECT_ID` in `.env`, and `EE_CREDENTIALS=<host path to that credentials file>` so the `insar` container mounts it read-only (falls back to a harmless placeholder so all other scripts run without GEE). `earthengine-api` is already in the `insar` image — **rebuild once** after pulling: `docker compose build insar`. The real credentials file is git-ignored.

### Step 7: (Optional, **deferred** — manual external-data fetches) GACOS & GSI Bhukosh

> These two are **manual, user-side downloads** (interactive portals / email-delivered files, not scriptable APIs — both are unreachable from the container/CI). No API key needed. Documented here so they can be picked up later; **expect each to take time**, and **verify the portal/URL is current** (Indian government geoportals in particular get reorganized — search for the live entry point).

**(a) GACOS** — a free no-MATLAB **weather-model tropospheric correction**, the cross-check/alternative to the MintPy ERA5 path (`RESULTS_AND_KPIS.md` §13; Yu et al. 2018). Steps: (1) at **http://www.gacos.net/** submit a request with the AOI bounding box (Ramban ≈ 75.1–75.4 °E, 33.1–33.4 °N) and the **list of SAR acquisition dates** (frame106 ≈ 15 dates, pass ≈ 12:56 UTC — read them off the HyP3 product names); (2) GACOS emails a link to the per-date `.ztd` zenith-delay maps; (3) drop them in a folder and run MintPy with `mintpy.troposphericDelay.method = gacos` + `mintpy.troposphericDelay.gacosDir = <folder>`, then re-run `workflows/compare_tropo_methods.py` to add a `gacos` column. *Status: not done — needs the manual request + email turnaround.*

**(b) GSI landslide inventory** — the **authoritative field-validated inventory** (~302 mapped Ramban-sub-basin landslides) for a *scored* precision/recall back-test (`RESULTS_AND_KPIS.md` §12g; the date-correction lesson shows exactly why verified ground truth matters). Steps: (1) register (free) and log in. As of **2025** the inventory is uploaded to the **NGDR portal** (National Geoscience Data Repository, Ministry of Mines — **https://geodataindia.gov.in**, the *current/newer* entry point) **and** the **Bhukosh** portal (**https://bhukosh.gsi.gov.in/Bhukosh/Public**); the **Bhusanket** portal (**https://bhusanket.gsi.gov.in**) carries the operational landslide *forecast bulletins* + susceptibility maps. ⚠️ **These portals get reorganized** — if a link is dead, search "**geodataindia** landslide" / "GSI **NGDR** landslide inventory download" / "Bhukosh shapefile", or try ISRO **Bhuvan** (bhuvan.nrsc.gov.in) landslide layers, or NASA **COOLR** as a sparse stopgap. (2) Navigate to the Jammu & Kashmir / Ramban toposheets, select the **Landslide Inventory (field-validated)** layer, download as **shapefile/KML**. (3) Drop it in `data/inventory/` — `backtest_inventory.py` is built to ingest it (a small polygon→centroid adapter is the only code step). *Status: not done — needs the manual portal login + interactive download (firewalled from the agent).*

---

## 🚀 The Pipeline (Phases 1 – 4A) — How To Reproduce

Each phase produces a verifiable artifact the next phase consumes. The data
products from a completed run already live under `data/`, so Phases 2–4A can be
re-run independently (Phase 1 needs ASF auth + ~hours of cloud processing).

```bash
conda activate insar_qa_env   # ALWAYS activate — see Known Issues (BLAS DLLs)

# ── PHASE 1 — clean, audited data ─────────────────────────────────────────────
python workflows/submit_hyp3_jobs.py                                    # dry-run preview
python workflows/submit_hyp3_jobs.py --sbas-neighbors 3 \
    --max-baseline-days 40 --submit                                     # queue jobs at ASF
python workflows/download_hyp3_products.py --watch --download --extract # waits, pulls, extracts
python workflows/feature_engineering.py                                 # 1.2 coherence mask
python workflows/phase_elevation_audit.py                               # 1.3 atmospheric audit
python workflows/export_audit_json.py
python workflows/_consolidate_quarantine.py                             # KEEP/CONCERN/QUARANTINE
python workflows/sbas_network_graph.py                                  # 1.4 connectivity check
python workflows/apply_connectivity_rescues.py                          # rescue bridging pairs
python tests/test_plumbing.py                                           # 10 assertions (stdlib)

# ── PHASE 2 — SBAS velocity inversion (pathfinder stack) ─────────────────────
python workflows/custom_sbas_inverter.py        # → data/velocity/  (mean velocity + time-series)

# ── PHASE 3 — geomechanical hazard engine ────────────────────────────────────
python workflows/geomechanical_engine.py        # → data/hazard/  (slope, TWI, FS, hazard_class)

# ── PHASE 4A — agentic warning system ────────────────────────────────────────
python workflows/agentic_orchestrator.py        # → data/alerts/  (alerts + dashboards, all scenarios)

# ── PHASE 4B — interactive 3-D hazard explorer ───────────────────────────────
python workflows/build_3d_dashboard.py           # → data/alerts/dashboard_3d.html
```

**See the demo:** open `data/alerts/dashboard_monsoon.html` (2-D, per scenario)
or `data/alerts/dashboard_3d.html` (interactive 3-D) in any browser.

### Configuration, multi-stack & MintPy (current)

- **The AOI config registry (`config/*.yaml`)** — one YAML per site holds everything
  site-specific: AOI polygon, job-name prefix, time window, **soil shear-strength
  (`soil:` block)**, operating points (`operational_m`/`watch_m`), baseline rules and
  the connectivity-rescue gate. The root **`config.yaml` is a one-line
  `active_config:` pointer** selecting the default site; target any other site
  per-command with `-e INSAR_CONFIG=config/<aoi>.yaml` (works for every script) or
  `--config` where exposed. Point the pipeline at a new valley with **zero code
  edits** — full recipe incl. the manual steps: **[NEW_AOI_PLAYBOOK.md](NEW_AOI_PLAYBOOK.md)**.
- **Multi-AOI status dashboard:** `python workflows/aoi_status.py` — one card per
  registry site: stage checklist (incl. manual steps), current alarm level / live
  zones / rainfall freshness, and the exact next command. Writes
  `data/aoi_status.html` + `.json`; read-only and env-light (runs natively).
- **One-time (existing Ramban data):** seed the product→stack manifest with
  `python workflows/stacks.py --seed-legacy` (new AOIs get it from the downloader).
- **Automated, quality-gated connectivity rescue:**
  `python workflows/sbas_network_graph.py --recommend-only` →
  `python workflows/apply_connectivity_rescues.py` (offline; only clean bridges).
- **Multi-stack driver (Phases 2–4 + AOI union):** `python workflows/run_multistack.py`
  — inverts all connectable stacks, builds per-look hazard and a **union** hazard/alert
  product (`data/mosaic/`, `data/alerts/mosaic_asc/`) for four scenarios: the mock
  `dry`/`monsoon`/`extreme` what-if cascade **plus** `operational` — the **rainfall-realistic
  standing product** (saturation **m=0.50** under the matric-suction FS physics §20 + the 12.5 m ALOS DEM
  §21) that scores **AUC 0.64 [0.60–0.68], p=0.0001 — the project's best** in the back-test
  (`RESULTS_AND_KPIS.md` §16d/§20/§21; interval + permutation p from §44).
  Add `--use-vslope`
  for the parallel downslope-projected product (`data/mosaic_vslope/`).
- **MintPy (field-standard SBAS, separate image):** `python workflows/prep_mintpy.py
  --stack <stack>`, then `smallbaselineApp.py` in the `mintpy` container — see
  [`docker/README.md`](docker/README.md) and `SESSION_REVIEW.md` §4.
- **Tropospheric-correction method comparison (noise-floor attack, TRAIN-style):**
  `docker compose run --rm mintpy bash /app/workflows/run_mintpy_era5_f106.sh` +
  `run_mintpy_height_f106.sh` (ERA5 weather-model vs empirical height-correlation), then
  `docker compose run --rm insar python workflows/compare_tropo_methods.py` → ERA5 cuts
  velocity scatter **−31 %** (the empirical topo-only method does not); `RESULTS_AND_KPIS.md` §13.
- **Forecasting / rainfall trigger (real-weather-driven):**
  `python workflows/fetch_rainfall.py` (ERA5-Land water + temperature; `mintpy` image) **or**
  `python workflows/fetch_chirps.py` (CHIRPS gauge rainfall via GEE; needs Step 6 auth) →
  `python workflows/rainfall_id_threshold.py --csv <daily.csv> --threshold {caine1980|nwhimalaya}`
  (global vs regional Himalayan I-D curve) →
  `python workflows/rainfall_specificity.py --csv <daily.csv>` (sensitivity/selectivity trade-off) and/or
  `python workflows/fetch_gpm_imerg.py` (half-hourly GPM IMERG sub-daily-intensity test; needs Step 6 auth) →
  `python workflows/agentic_orchestrator.py --rainfall-timeline` (couples rain into FS) →
  `python workflows/backtest_inventory.py --inventory data/inventory/gsi_inventory_aoi.geojson
  --alerts data/alerts/mosaic_asc/alerts_operational.json` (**scored** validation vs the GSI
  field-validated inventory: null-point control + distance-ROC/**AUC**, `--min-looks N` for the
  multi-look core; `RESULTS_AND_KPIS.md` §16b–e). `inverse_velocity_ttf.py` screens for
  accelerating creep. Add `--use-vslope` to the orchestrator/TTF for the downslope basis.
- **Rainfall-realistic operating point (the saturation that beats chance):**
  `python workflows/rainfall_selectivity_backtest.py` — sweeps the assumed soil saturation,
  rebuilds + scores the AOI union mosaic at each, and shows AUC rising 0.41→0.55 as m falls
  from worst-case 1.0 to the realistic ~0.25–0.40 (`RESULTS_AND_KPIS.md` §16d). The chosen
  point (m=0.50 under the matric-suction physics §20 + 12.5 m DEM §21) is wired in as `operational` above.
- **Two-tier hazard product (recall complement, §23):** the `watch` scenario (m=0.70) builds a broader,
  higher-recall monitoring footprint beside the precise `operational` ALERT map — `run_multistack.py` emits
  both. Score the WATCH map with `python workflows/backtest_inventory.py
  --alerts data/alerts/mosaic_asc/alerts_watch.json --inventory data/inventory/gsi_inventory_aoi.geojson
  [--min-looks 2]` (132 zones, recall 0.63, AUC 0.50; ≥2-look core AUC 0.59 beats chance — vs ALERT's
  12 zones / recall 0.25 / AUC 0.64). ALERT = act now; WATCH = monitor wider. Both tiers are shown side by
  side in the operational dashboard's WHERE panel (scored numbers read live from the back-test reports).
- **Two-factor operational warning (WHERE × WHEN):**
  `python workflows/operational_alarm.py --threshold nwhimalaya` — gates the validated operational
  footprint by the regional rainfall curve graded by exceedance E (DORMANT/WATCH/ALERT). Cuts the raw
  112/214-day trigger to 27 ALERT days (4.1×) and catches the 20 Apr cloudburst at Δ=0 (§17). Writes a
  self-contained dashboard `data/alerts/mosaic_asc/operational_alarm_dashboard.html` (`--as-of <date>` for
  the "current state" banner).
- **Per-zone gating (which zones are live today):** `python workflows/per_zone_gate.py` — each operational
  zone's critical saturation m\*=(1−FS_dry)/(FS_sat−FS_dry); on a regional WATCH/ALERT day the active set =
  zones whose m\* the day's saturation has reached (53–95 of 95, ranked by vulnerability, capped at the
  validated footprint — no ballooning) (§19).
- **Per-zone detection confidence (uncertainty quantification, §24):** `python workflows/velocity_uncertainty.py
  [--footprint operational|watch]` — propagates each stack's velocity noise floor (σ_v 14–24 mm/yr) into a
  per-zone confidence p=Φ((−15−v)/σ_v) that the creep is real (not noise), with multi-look corroboration
  P=1−Π(1−p). Writes confidence-filtered `alerts_<scenario>_conf{,70,90}.json` (scoreable by
  `backtest_inventory.py`). Honest finding: this measurement confidence is orthogonal to inventory AUC — a
  triage axis, not a spatial ranker.
- **Validation statistics — CIs, significance, and the ablation ladder (§44):**
  `python workflows/validation_stats.py [--scenario operational|watch]` — bootstrap 95% CIs on
  AUC/recall (inventory resampled, B=10,000), a permutation p-value for "beats chance", and a
  dumb-baseline **ablation ladder** (slope-only, logistic slope+TWI, physics-only, creep-only)
  scored with the identical zone/centroid/distance-ROC protocol. Headline claims cite the
  interval, not the point: Ramban operational **AUC 0.64 [0.60–0.68], p=0.0001, beats every
  ladder rung**; Vaishno Devi operational **0.71 [0.66–0.75], p=0.0001**, beats every
  physics/InSAR rung but is statistically indistinguishable from a tuned slope-only map on its
  corridor inventory — the honest limits are in the ledger. Dashboards read the intervals live.
- **WATCH triage — rank, don't gate (§25):** `python workflows/watch_triage.py` — the recall-tier WATCH
  footprint (132 zones) is a "don't-miss-anything" net, so it is **kept whole and sorted** worst-first by
  `priority = (1−m*)×P` (fragility §19 × detection confidence §24) rather than narrowed by the §19 gate
  (which would shrink its breadth and apply it outside the validated map). Writes a ranked
  `data/alerts/mosaic_asc/per_zone_triage_watch.{csv,md,png}`; a zone tops the list only if it is both
  fragile and confidently moving (multi-look zones get a confidence boost).
- **ERA5-velocity hazard cross-check (frame106):** `python workflows/hazard_era5_compare.py` — rolls the
  MintPy ERA5-tropo-corrected velocity through the creep→hazard fusion vs the custom velocity (§18).

Any command runs in Docker too, e.g. `docker compose run --rm insar python workflows/run_multistack.py`.

> ℹ️ The status table and per-script notes here describe the original Phase 1–4A
> pathfinder run. For the **latest state** (Docker, multi-stack union, MintPy) always
> read **`SESSION_REVIEW.md`** first.

### What each script produces

| Script | Phase | Writes |
|---|---|---|
| `submit_hyp3_jobs.py` | 1 | HyP3 jobs queued at ASF (SBAS N=3, 5 stacks) |
| `download_hyp3_products.py` | 1 | `data/raw_zips/*.zip`, `data/processed_tiffs/<product>/*.tif` |
| `feature_engineering.py` | 1.2 | `data/qa_masks/<product>/<product>_masked_disp.tif` + coherence stats |
| `phase_elevation_audit.py` | 1.3 | `data/qa_masks/_atmospheric_audit.csv` |
| `_consolidate_quarantine.py` | 1 | `data/qa_masks/_quarantine_list.csv` (KEEP/CONCERN/QUARANTINE) |
| `sbas_network_graph.py` | 1.4 | `data/qa_masks/_network_graphs/*.svg`, `index.html`, report |
| `apply_connectivity_rescues.py` | 1.4 | promotes CONCERN→KEEP; `_rescued_for_connectivity.json` |
| `custom_sbas_inverter.py` | 2 | `data/velocity/*_mean_velocity_los*.tif`, `*_displacement_timeseries.tif`, `*_temporal_coherence.tif` |
| `geomechanical_engine.py` | 3 | `data/hazard/*_{slope_deg,twi,FS_dry,FS_saturated,hazard_class}.tif` |
| `agentic_orchestrator.py` | 4A | `data/alerts/alerts_*.json`, `alert_report_*.md`, `dashboard_*.html` |
| `build_3d_dashboard.py` | 4B | `data/alerts/dashboard_3d.html` |

### What the pipeline produced (current state, pathfinder stack `ASC_path27_frame106`)

- **Phase 1:** 183 INSAR_GAMMA pairs, 5 stacks (3 ASC + 2 DESC) → 105 KEEP / 24 CONCERN / 54 QUARANTINE after coherence + atmospheric + connectivity audits.
- **Phase 2:** per-pixel LOS velocity (deramped, temporal-coherence ≥ 0.7), ~14% AOI coverage, ~30 mm/yr noise floor.
- **Phase 3:** slope (median 28°), Factor of Safety — 13% unstable dry vs **73% unstable saturated** (the monsoon flip).
- **Phase 4A:** rainfall-driven alerts — **dry → 29 zones, monsoon → 222** — each geolocated with plain-English reasoning + a downstream-risk (LLOF) flag.

See `milestone.md` (plain language) and `session_journey.md` (per-phase rationale + honest caveats).

---

## ⚠️ Known Issues on This Environment

These are documented in detail in [error_history_log.md](error_history_log.md). The summary:

| Issue | Workaround |
|---|---|
| **`0xC06D007F` crash on ANY numpy BLAS/LAPACK call** (matmul, svd, pinv) | **The big one.** It's a DLL-load failure, not a numerical bug — numpy can't find its BLAS DLLs when `python.exe` is run without `conda activate`. **Always activate the env**, or rely on the in-script DLL bootstrap that all Phase 2–4 scripts carry (prepends `<env>\Library\bin` to PATH). |
| Implausible SBAS velocities (±300 mm/yr) | Deramp each interferogram (subtract a 2-D plane) **before** inversion — done in `custom_sbas_inverter.py`. |
| `matplotlib.savefig` historically crashed (same DLL family) | New plots emit stdlib SVG / browser HTML instead — see `sbas_network_graph.py`, the dashboards. |
| `hyp3_sdk` downloads silently truncate ~2% of the time | Downloader verifies via `zipfile.testzip()` and retries once. |
| `hyp3.find_jobs(name=X)` does exact-match, not prefix | Both submit and download scripts filter client-side. |
| `UnicodeEncodeError` writing `→` to the Windows console log | Keep `logging` messages ASCII; reserve unicode for UTF-8 files. |
| OneDrive corrupts conda envs created in-project | Always use `-n insar_qa_env` (named env), never `-p .conda`. |

---

## 📡 Remote Sensing & Data Sources

| Provider | Product | Use case | Auth |
|---|---|---|---|
| **NASA Earthdata / ASF** | Sentinel-1 IW SLC → HyP3 INSAR_GAMMA | InSAR displacement, time-series velocity | `.netrc` + OAuth approve |
| **Copernicus CDSE** | Sentinel-1 raw, Sentinel-2 multispectral | Raw access if HyP3 unavailable; vegetation indices | `.netrc` |
| **NASA Earthdata** | ALOS PALSAR / SRTM DEM | Topographic correction, slope/aspect, geomechanics | `.netrc` |
| **USGS EarthExplorer** | Landsat 8/9 | Historical comparison, land change | `.netrc` |
| **Microsoft Planetary Computer** | Sentinel/Landsat catalog | Fast cloud-free queries | `.env` API key |
| **Google Earth Engine** | Global EO repository | Large-scale serverless compute | `.env` project ID |

---

## 📈 Analysis Focus Areas

1. **Atmospheric Forensics** ✅ — phase-elevation correlation + coherence masking to keep only real ground motion (Phase 1).
2. **InSAR time-series velocity** ✅ — Sentinel-1 SBAS over Ramban; landslide creep at mm/yr precision (Phase 2, pathfinder stack).
3. **Geomechanical Modelling** ✅ — LOS velocity + DEM-derived slope/TWI → Infinite-Slope Factor of Safety + hazard fusion (Phase 3).
4. **Agentic decision support** ✅ (Part A) — rainfall-scenario-driven cascading reasoner emits geolocated, explainable, ranked alerts (Phase 4A).
5. **Meteorological Triggers (live)** ✅ — real ERA5-Land rainfall auto-fetched per season (`live_alarm.py`), graded by a verified regional intensity–duration curve into DORMANT/WATCH/ALERT (§17, §35); remaining hardening = sub-daily per-zone rain (IMERG).

---

## 🤝 Contribution Guidelines

- **Data stays out of Git.** Raw zips, processed TIFFs, masked rasters, and CSVs are all `.gitignore`'d. If your branch shows `.tif` or `.zip` files in `git status`, something is wrong.
- **Credentials never leave your machine.** `.netrc`, `.env`, and `_netrc` are all blocked by `.gitignore`. Double-check before pushing.
- **Workflow scripts are idempotent.** Re-running any of them should be safe — they skip already-done work where possible. If you add a new workflow script, preserve this property.
- **One file per architectural concern.** New extractions, audits, or analysis steps should be their own `workflows/<name>.py` rather than getting bolted onto an existing script.
- **Log decisions, not actions.** `session_journey.md` is for *why* we chose something; `error_history_log.md` is for *what broke and how it was fixed*. Day-to-day actions don't need to be journaled.

---

## 📚 Where To Read More

- [SESSION_REVIEW.md](SESSION_REVIEW.md) — 🚦 the "start here" living dashboard (read first each session)
- [NEW_AOI_PLAYBOOK.md](NEW_AOI_PLAYBOOK.md) — onboarding a new AOI, step by step (automated + manual)
- [milestone.md](milestone.md) — plain-language story of each milestone (for humans, no jargon)
- [Research/Foundations - Physics and Maths Primer.md](Research/Foundations%20-%20Physics%20and%20Maths%20Primer.md) — beginner science base; how to confidently discuss the project
- [InSAR_hazard_forecasting_Context.md](InSAR_hazard_forecasting_Context.md) — original vision + full roadmap
- [session_journey.md](session_journey.md) — what decisions were made, when, and why
- [error_history_log.md](error_history_log.md) — every bug we've hit, with root cause + fix
- [CLAUDE.md](CLAUDE.md) — behavioural rules for AI-assisted development on this repo
- [Research/](Research/) — background literature and meteorological notes

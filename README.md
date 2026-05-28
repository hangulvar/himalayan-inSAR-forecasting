# 🏔️ Geospatial Analysis & Hazard Monitoring in the Western Himalayas

A geospatial data science project monitoring atmospheric dynamics, extreme weather, and geological hazards (landslides, slope deformation, glacio-hydrology) across the Western Himalayas. The current case study is the **NH-44 corridor through Ramban, Jammu & Kashmir** — a known landslide-prone segment with documented historical failures.

Phase 1 (clean, audited InSAR data extraction) is **complete**. See [session_journey.md](session_journey.md) for the full decision log and [error_history_log.md](error_history_log.md) for every bug we hit and how it was resolved.

---

## 📁 Repository Structure

```tree
Geospatial Analysis Himalayas/
│
├── README.md                       # This file
├── CLAUDE.md                       # Behavioural rules for AI-assisted dev
├── session_journey.md              # Session-by-session decisions and reasoning
├── error_history_log.md            # Every bug + root cause + fix from this project
├── InSAR hazard forecasting Context.md  # Original project vision
│
├── .gitignore                      # Blocks credentials and large rasters from Git
├── .netrc.template                 # NASA Earthdata + CDSE + USGS credential setup
├── .env.template                   # Optional API keys (Mapbox, GEE, etc.)
├── environment.yml                 # Conda-forge environment spec (insar_qa_env)
├── requirements.txt                # Pip fallback (NOT recommended for geospatial)
├── ramban_aoi.geojson              # Area-of-Interest polygon (Ramban / NH-44)
│
├── workflows/                      # Pipeline scripts (numbered by phase)
│   ├── submit_hyp3_jobs.py             # Phase 1.1: ASF HyP3 InSAR submission
│   ├── download_hyp3_products.py       # Phase 1.1: watch + download + extract
│   ├── feature_engineering.py          # Phase 1.2A: coherence masking
│   ├── phase_elevation_audit.py        # Phase 1.2B + 1.3: atmospheric audit
│   ├── export_audit_json.py            # Phase 1.3: minimal audit_log.json
│   ├── sbas_network_graph.py           # Phase 1.4: SBAS connectivity check + SVG plots
│   ├── apply_connectivity_rescues.py   # Phase 1.4: rescue bridging CONCERN pairs
│   ├── _consolidate_quarantine.py      # Helper: merge coherence + atmospheric audits
│   ├── _analyze_qa_stats.py            # Helper: per-stack QA statistics
│   ├── proj_pipeline_AOI.md            # Future AOI shortlist
│   └── .gitkeep
│
├── tests/
│   └── test_plumbing.py            # Stdlib-only Phase 1.4 plumbing assertions
│
├── data/                           # Outputs (Git-ignored)
│   ├── raw_zips/                       # HyP3 product zips (183 × ~200 MB)
│   ├── processed_tiffs/                # Extracted GeoTIFFs per product
│   ├── qa_masks/                       # NaN-masked LOS displacement rasters
│   │   ├── <product>/<product>_masked_disp.tif
│   │   ├── _coherence_mask_stats.csv
│   │   ├── _atmospheric_audit.csv
│   │   ├── audit_log.json
│   │   ├── _quarantine_list.csv
│   │   ├── _rescued_for_connectivity.json
│   │   └── _network_graphs/
│   │       ├── *.svg                   # 5 baseline diagrams (one per stack)
│   │       ├── index.html              # Single-page network report
│   │       └── _connectivity_report.md
│   └── ...
│
├── logs/                           # Run logs from every workflow script
│
├── Research/                       # Background literature and notes
│   ├── Joshimath InSAR.pdf
│   ├── Meteorology.md
│   └── ...
│
├── src/                            # Reserved for reusable modules (currently empty)
└── config/                         # Reserved for parameter specs (currently empty)
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

### Conda (required)

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

Copy `.env.template` to `.env` and fill in Mapbox / GEE / Sentinel Hub keys if you'll use those. The `.gitignore` is pre-configured to never commit `.env`.

---

## 🚀 Phase 1 Pipeline — How To Reproduce

Phase 1 takes an AOI polygon, fetches every Sentinel-1 interferometric pair within a time window, masks low-coherence pixels, audits for tropospheric contamination, and produces a connected SBAS network ready for velocity inversion (Phase 2).

### One-shot run (assuming auth is configured):

```bash
conda activate insar_qa_env

# 1.1 — Discover scenes, build SBAS N=3 network, submit to ASF HyP3
python workflows/submit_hyp3_jobs.py                                    # dry-run preview
python workflows/submit_hyp3_jobs.py --sbas-neighbors 3 \
    --max-baseline-days 40 --submit                                     # actually queue jobs

# Wait ~1–4 hours for HyP3 to process, then:
python workflows/download_hyp3_products.py --watch --download --extract # waits, pulls, extracts

# 1.2 — Coherence masking
python workflows/feature_engineering.py

# 1.3 — Atmospheric audit + JSON export
python workflows/phase_elevation_audit.py
python workflows/export_audit_json.py

# Helper: consolidate the two audits into a single quarantine decision
python workflows/_consolidate_quarantine.py

# 1.4 — SBAS network connectivity check
python workflows/sbas_network_graph.py
# If any stack is disconnected, rescue bridging concerns:
python workflows/apply_connectivity_rescues.py
python workflows/sbas_network_graph.py    # confirm fix

# Plumbing test (10 assertions, stdlib-only — no pytest install required):
python tests/test_plumbing.py
```

### What each script produces

| Script | Reads | Writes |
|---|---|---|
| `submit_hyp3_jobs.py` | `ramban_aoi.geojson` | HyP3 jobs queued at ASF |
| `download_hyp3_products.py` | HyP3 job catalogue | `data/raw_zips/*.zip`, `data/processed_tiffs/<product>/*.tif` |
| `feature_engineering.py` | `data/processed_tiffs/` | `data/qa_masks/<product>/<product>_masked_disp.tif`, `_coherence_mask_stats.csv` |
| `phase_elevation_audit.py` | `data/qa_masks/`, DEMs | `data/qa_masks/_atmospheric_audit.csv` |
| `export_audit_json.py` | `_atmospheric_audit.csv` | `data/qa_masks/audit_log.json` (minimal schema) |
| `_consolidate_quarantine.py` | both audit CSVs | `data/qa_masks/_quarantine_list.csv` (KEEP/CONCERN/QUARANTINE) |
| `sbas_network_graph.py` | `_quarantine_list.csv`, asf_search baselines | `data/qa_masks/_network_graphs/*.svg`, `index.html`, `_connectivity_report.md` |
| `apply_connectivity_rescues.py` | hardcoded rescue list | promotes CONCERN→KEEP in `_quarantine_list.csv`, audit at `_rescued_for_connectivity.json` |

### What Phase 1 produced (final state)

- 183 INSAR_GAMMA pairs across 5 stacks (3 ascending + 2 descending)
- 105 KEEP, 24 CONCERN, 54 QUARANTINE after the full audit
- 3 stacks ready for least-squares SBAS, 1 ready for SVD pseudoinverse, 1 split into independent pre-/in-/post-monsoon time series
- See `session_journey.md` for the per-stack rationale.

---

## ⚠️ Known Issues on This Environment

These are documented in detail in [error_history_log.md](error_history_log.md). The summary:

| Issue | Workaround |
|---|---|
| `np.corrcoef` crashes on ~5M-element arrays (Win + numpy 2.x + MKL) | Use manual Pearson r — see `phase_elevation_audit.py` |
| `matplotlib.savefig` crashes inside `patches.draw` | Don't use matplotlib for new plots; emit stdlib SVG — see `sbas_network_graph.py` |
| `hyp3_sdk` downloads silently truncate ~2% of the time | The downloader now verifies via `zipfile.testzip()` and retries once |
| `hyp3.find_jobs(name=X)` does exact-match, not prefix | Both submit and download scripts filter client-side |
| OneDrive corrupts conda envs created in-project | Always use `-n insar_qa_env` (named env), never `-p .conda` |

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

1. **InSAR time-series velocity** — Sentinel-1 SBAS over Ramban; landslide creep detection at mm/yr precision (Phase 2 next session).
2. **Atmospheric Forensics** — Phase-elevation correlation to distinguish real motion from tropospheric artefacts (Phase 1.3, done).
3. **Geomechanical Modelling** — Combine LOS velocity with DEM-derived slope and TWI, run the Infinite Slope Factor-of-Safety calculation (Phase 3).
4. **Meteorological Triggers** — Cross-reference with monsoon precipitation forecasts to identify cascading-failure conditions (Phase 4).

---

## 🤝 Contribution Guidelines

- **Data stays out of Git.** Raw zips, processed TIFFs, masked rasters, and CSVs are all `.gitignore`'d. If your branch shows `.tif` or `.zip` files in `git status`, something is wrong.
- **Credentials never leave your machine.** `.netrc`, `.env`, and `_netrc` are all blocked by `.gitignore`. Double-check before pushing.
- **Workflow scripts are idempotent.** Re-running any of them should be safe — they skip already-done work where possible. If you add a new workflow script, preserve this property.
- **One file per architectural concern.** New extractions, audits, or analysis steps should be their own `workflows/<name>.py` rather than getting bolted onto an existing script.
- **Log decisions, not actions.** `session_journey.md` is for *why* we chose something; `error_history_log.md` is for *what broke and how it was fixed*. Day-to-day actions don't need to be journaled.

---

## 📚 Where To Read More

- [InSAR hazard forecasting Context.md](InSAR%20hazard%20forecasting%20Context.md) — original project vision and methodology
- [session_journey.md](session_journey.md) — what decisions were made, when, and why
- [error_history_log.md](error_history_log.md) — every bug we've hit, with root cause + fix
- [CLAUDE.md](CLAUDE.md) — behavioural rules for AI-assisted development on this repo
- [Research/](Research/) — background literature and meteorological notes

# 🏔️ Geospatial Analysis & Hazard Monitoring in the Western Himalayas

A comprehensive, state-of-the-art Geospatial Data Science repository dedicated to monitoring atmospheric dynamics, extreme weather occurrences, and geological hazards (such as land subsidence, landslides, and glacio-hydrological events) across the ecologically sensitive and tectonically active Western Himalayan region.

This project integrates satellite remote sensing (InSAR, SAR, multispectral), meteorological datasets, and terrain models to assess environmental vulnerability, with a particular focus on case studies like **landslides and slope deformation in the sensitive Ramban district (Jammu & Kashmir)** and extreme precipitation hazards.

---

## 📁 Repository Structure

```tree
Geospatial Analysis Himalayas/
│
├── .gitignore                   # Safe Git configuration for large rasters & credentials
├── .netrc.template              # Config guide for NASA Earthdata, CDSE, and USGS
├── .env.template                # Local environment variables and API keys
├── environment.yml              # Conda environment specifications (conda-forge)
├── requirements.txt             # Pip dependencies list (fallback)
│
├── config/                      # Parameter specs, analysis bounds, sensor configs
│   └── .gitkeep
│
├── data/                        # Structured data storage (Git ignored)
│   ├── raw_zips/                # Incoming raw zipped satellite archives
│   ├── processed_tiffs/         # Transformed GeoTIFF rasters (InSAR, etc.)
│   └── qa_masks/                # Quality assurance validation masks
│
├── logs/                        # Processing run logs and error files
│   └── .gitkeep
│
├── Research/                    # Literature reviews, PDFs, and background docs
│   ├── Joshimath InSAR.pdf      # Reference paper on InSAR analysis methods
│   ├── Meteorology.md           # Meteorological frameworks and learning assets
│   └── ...                      # Additional weather event reports & drafts
│
├── src/                         # Modular, reusable Python source code
│   └── .gitkeep
│
└── workflows/                   # Pipelines, orchestrations, and cron recipes
    └── .gitkeep
```

---

## ✈️ The Pre-Flight Checklist: Before You Write a Single Line of Code

Before writing any analysis code, you must establish the solid infrastructure required to handle geospatial data smoothly. In geospatial data science, library conflicts between GDAL, Rasterio, and system dependencies can halt progress. Follow these strict guidelines:

### 1. Environment Isolation (The Conda-Forge Rule)
* **Rule**: **Do NOT use standard pip** to install your core geospatial libraries from scratch. You must use Miniconda or Anaconda.
* **Conda-Forge Channel**: Create a strict isolated environment using packages solely from the `conda-forge` channel.
* **Compilation Order**: If building or adding packages manually, the installation order matters to compile C++ binaries correctly for your machine without overloading standard RAM limits (e.g. 16GB RAM):
  1. `gdal` (C++ geospatial data abstraction library)
  2. `rasterio` (georeferenced raster data access)
  3. `geopandas` (spatial operations on geometric types)
  4. `hyp3_sdk` (Alaska Satellite Facility Hybrid Pluggable Processing Pipeline)

### 2. Authentication & Key Management (NASA Earthdata & ASF)
* **NASA Earthdata Account**: You need a registered NASA Earthdata account (create it at [urs.earthdata.nasa.gov](https://urs.earthdata.nasa.gov/)).
* **Silent Failures**: The Alaska Satellite Facility (ASF) API (used by `hyp3_sdk` for processing radar arrays) will **silently fail** to authenticate if it cannot seamlessly find your Earthdata credentials.
* **Storage**: You must configure a secure `.netrc` file (or `_netrc` on Windows) in your user home directory to store these credentials.

### 3. Rigid Folder Hierarchy
* **Rule**: You must strictly segregate incoming raw data from transformed datasets. Do not allow raw zipped satellite packets to mix with final grids.
* **Directories**: Store raw archives in `data/raw_zips/`, intermediate GeoTIFF rasters in `data/processed_tiffs/`, QA layers in `data/qa_masks/`, and processing run diagnostics under `logs/`.

---

## 🛠️ Environment Setup & Installation Options

### Option A: Conda/Mamba Setup (Highly Recommended)

1. Open your terminal or Anaconda Prompt and navigate to the project directory:
   ```bash
   cd "Geospatial Analysis Himalayas"
   ```

2. Create the environment from `environment.yml` (this will install Python 3.10 and all necessary dependencies from the `conda-forge` channel):
   ```bash
   conda env create -f environment.yml
   ```

3. Activate the environment:
   ```bash
   conda activate himalayas-geospatial
   ```

### Option B: Standard Virtualenv (Pip Fallback)

If you have a pre-configured python environment or are running on an OS with pre-installed binary wheels (such as Linux or macOS with Homebrew):

```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 🔐 Credentials & API Setup

Many Earth Observation data sources require authentication for automated API or bulk downloads. We use standardized, secure mechanisms that store credentials outside of version control.

### 1. `.netrc` (or `_netrc` on Windows) Configuration
Historically used by `curl`, `sentinelsat`, and NASA's `earthaccess` to fetch data securely.

* **Step 1**: Locate the [.netrc.template](.netrc.template) file at the root.
* **Step 2**: Copy this file to your User Home directory:
  * **On Windows**: Copy to `C:\Users\<YourUsername>\_netrc` (Note the leading underscore!)
  * **On Mac/Linux**: Copy to `~/.netrc` (Note the leading dot!)
* **Step 3**: Fill in your accounts for **NASA Earthdata Login**, **Copernicus CDSE**, and **USGS EarthExplorer**.
* **Step 4**: (Linux/Mac only) Restrict file access: `chmod 600 ~/.netrc`

### 2. Local `.env` Configuration
Used for specific developer access keys (Mapbox, Sentinel Hub, GCP/Google Earth Engine).

* **Step 1**: Copy [.env.template](.env.template) to a new file named `.env` in the root directory.
* **Step 2**: Insert your private keys (e.g. `MAPBOX_API_TOKEN` or `EE_PROJECT_ID`). The project's `.gitignore` is pre-configured to ensure this `.env` is never committed to GitHub.

### 3. Alaska Satellite Facility (ASF) HyP3 API Setup
The **HyP3 API** is used to request cloud-based InSAR (Interferometric Synthetic Aperture Radar) processing to measure terrain changes and land subsidence.

* **Authentication**: It relies on your **NASA Earthdata Account**. The `hyp3_sdk` will automatically search and read credentials from your home directory's `.netrc` (or `_netrc` on Windows) file.
* **Automation Template**: A ready-to-run pipeline script is located at [workflows/submit_hyp3_jobs.py](workflows/submit_hyp3_jobs.py).
* **Running the Pipeline**:
  ```bash
  # Activate the environment
  conda activate himalayas-geospatial
  
  # Run the checker / submission demonstration
  python workflows/submit_hyp3_jobs.py
  ```
  *Note: Open `workflows/submit_hyp3_jobs.py` and set `run_submission = True` to submit actual jobs. It will automatically submit Sentinel-1 IW SLC image pairs, wait for cloud processing to finish, and download the resulting unwrapped interferograms and coherence grids directly into `data/processed_tiffs/`.*

---

## 📡 Remote Sensing & Data Sources

| Provider / Platform | Data Catalog / Product | Primary Use Case | Credentials Needed? |
| :--- | :--- | :--- | :--- |
| **Copernicus CDSE** | Sentinel-1 (C-band SAR) | Land subsidence, InSAR displacement maps, Flood mapping | CDSE login (`.netrc`) |
| **Copernicus CDSE** | Sentinel-2 (Multispectral) | Land cover classification, NDSI (Snow Index), NDVI (Vegetation) | CDSE login (`.netrc`) |
| **NASA Earthdata** | ALOS PALSAR / SRTM DEM | Topographic correction, slope aspect, digital elevation models | Earthdata Login (`.netrc`) |
| **USGS EarthExplorer** | Landsat 8/9, Sentinel-2 | Historical hazard comparisons, land change patterns | USGS login (`.netrc`) |
| **Planetary Computer** | Sentinel/Landsat catalog | High-speed cloud-free spatio-temporal catalog queries | PC API Key (`.env`) |
| **Google Earth Engine** | Global EO repository | Serverless cloud-based large-scale geospatial computing | GEE Project ID (`.env`) |

---

## 📈 Analysis Focus Areas

1. **Synthetic Aperture Radar (SAR) & InSAR**:
   - Utilize Sentinel-1 IW SLC data to process InSAR pairs (using tools like GMTSAR, SNAP, or MintPy) for land surface displacement tracking over the landslide-prone zones of Ramban (J&K) and other active geological faults in the Himalayas.
2. **Meteorological Hazard Indicators**:
   - Trace atmospheric water vapor, convective indicators, and extreme rainfall events linked to flash floods and cloudburst events in high-altitude catchments.
3. **Terrain Stability Modeling**:
   - Combine elevation derivatives (slope, aspect, curvature, wetness index) with geologic structural layers to model landslide susceptibility.

---

## 🤝 Contribution Guidelines

- **Keep Data Separate**: Always store incoming raw files under the `data/raw_zips/` directory and transformed grids under `data/processed_tiffs/`. Do not commit geospatial data files or archives to the Git repository.
- **Secrets Management**: Never commit active API tokens, `.env` files, or `.netrc` files.
- **Modular Code**: Develop core operations under `src/` as modular functions or classes, keeping notebooks in the root or `workflows/` directory for visualization and presentation only.

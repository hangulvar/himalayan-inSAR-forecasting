# Project Error & Environment Resolution Log

This log tracks major environment issues, package conflicts, system quirks, and configuration challenges encountered during the development of the **Himalayan InSAR Forecasting** project, along with their root causes, impacts, and solutions.

---

## Active Environment Reference
- **Environment Name:** `insar_qa_env`
- **Location:** `C:\Users\varun\.conda\envs\insar_qa_env\` (Immune to OneDrive sync locking)
- **Active Core Packages:**
  - Python: `3.10.20`
  - GDAL: `3.10.3`
  - Rasterio: `1.4.3`
  - Geopandas: `1.1.3`
  - Shapely: `2.1.2`
  - ASF Search: `12.2.2`
  - HyP3 SDK: `7.7.6`
  - NumPy: `2.2.6`
  - SciPy: `1.15.2`
  - Matplotlib: `3.10.9`

---

## Log Entries

### [2026-05-27] Conda Environment Creation Failure (Memory Error & OneDrive Sync Lock)

* **Symptom:**
  Running `conda env create -f environment.yml` resulted in a `CondaMemoryError: The conda process ran out of memory` or hung indefinitely during the `Solving environment` phase.

* **Root Causes:**
  1. **OneDrive Sync Interference:** The project directory resides within OneDrive (`C:\Users\varun\OneDrive\Documents\AI Proj\Data science Proj\Geospatial Analysis Himalayas`). When creating a project-local environment inside `.conda/`, OneDrive's background file-watcher immediately began locking the thousands of tiny newly-installed dependency files mid-installation. This sync collision corrupted the environment, halting the build after installing only 21 packages (failing to ever reach `gdal` or `rasterio`).
  2. **Outdated Conda Path Resolution:** An ancient version of Miniconda (v4.12.0) on the system `PATH` was being invoked. This older version relied on the classic Python-based dependency solver, which is highly inefficient and runs out of memory when attempting to resolve complex geospatial dependency graphs (like `gdal` mixed with `conda-forge` packages).

* **Resolution:**
  1. **Clean Up:** Removed the corrupted, partial local `.conda/` directory from the project root.
  2. **Relocation:** Created the active Conda environment outside the OneDrive sync path at `C:\Users\varun\.conda\envs\insar_qa_env\`.
  3. **Engine Upgrade:** Utilized the modern global Anaconda3 installation (v24.11.3) located at `C:\ProgramData\anaconda3\`, which uses the C++ compiled `libmamba` solver.

* **Verification:**
  - The environment solved and built successfully.
  - An end-to-end pipeline dry-run smoke test succeeded (correctly identifying and processing 73 scenes, 5 stacks, and 68 pairs), performing identically to the pip-installed pipeline.

---

### [2026-05-25] Conda Base Environment Package Conflict (`UnsatisfiableError`)

* **Symptom:**
  Running `conda install -n base conda-libmamba-solver` failed with `UnsatisfiableError: The following specifications were found to be incompatible...`

* **Root Cause:**
  The base Conda environment on the old Miniconda installation was severely congested with older packages and mixed-channel histories. The classic solver could not find a valid resolution path to update the base environment's core packages to accommodate the new solver plugin.

* **Resolution:**
  1. **Bypassed Base Updates:** Stopped attempting to force updates on the broken base environment.
  2. **Constraint Relaxation:** Temporarily relaxed the strict version constraints in `environment.yml` (specifically changing `gdal=3.6.*` to `gdal`) to reduce solving complexity for standard solvers.
  3. **Alternative Engine:** Ultimately bypassed by switching to the modern `anaconda3` solver at `C:\ProgramData\anaconda3\`.

---

### [2026-05-24] Netrc Credentials File Access in Windows

* **Symptom:**
  Authentication issues when attempting to pull remote SAR data from the Alaska Satellite Facility (ASF) archive via command-line utilities.

* **Root Cause:**
  Geospatial retrieval libraries and core Windows request APIs (like Python's `requests` or `netrc` module) look for the `.netrc` file inside the user's home directory (`%USERPROFILE%` / `C:\Users\varun`) by default. Placing the credential file inside the project directory is both insecure (creating a leakage risk for git repositories) and unrecognized by standard authentication libraries.

* **Resolution:**
  Configured a single, secure `.netrc` file in the user home directory (`C:\Users\varun\.netrc`). This keeps the secrets out of version control and allows all Python/Conda processes to automatically authenticate securely.

---

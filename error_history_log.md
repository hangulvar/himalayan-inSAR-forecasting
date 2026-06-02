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

### [2026-06-02] Native `earthengine-api` + numpy/matplotlib crashes hard on Windows (exit 127) → run GEE+numpy scripts in the container

* **Symptom:**
  `workflows/fetch_gpm_imerg.py` (imports `ee` **and** numpy + matplotlib) run with the native
  `insar_qa_env` python **aborted immediately after `import ee`** with **exit code 127**, no Python
  traceback, no error message — only the google.api_core FutureWarning was printed. `fetch_chirps.py`
  (also native, also `ee`) had worked fine; a standalone native numpy+matplotlib import also worked fine.

* **Root Cause:**
  The crash only happens when `earthengine-api` (which pulls **gRPC / protobuf** native extensions) is
  loaded in the **same process** as **numpy/matplotlib (MKL/BLAS)**. On this Windows env the two native
  stacks conflict at the C-DLL level → a hard process abort (Git Bash surfaces the Windows exception as
  exit 127), not a catchable Python exception. `fetch_chirps.py` survived *only because it imports no
  numpy*; the standalone numpy test survived because it loaded no gRPC. It is the same class of
  Windows-native-DLL fragility as the historical `0xC06D007F` BLAS crash — exactly what the Linux
  container exists to eliminate.

* **Resolution:**
  Run any script that needs **both** GEE and numpy/matplotlib **in the `insar` Docker container**, not
  native. `earthengine-api` is already in `docker/Dockerfile`; rebuild once (`docker compose build
  insar`) and the compose `EE_CREDENTIALS` mount + `EE_PROJECT_ID` (from the bind-mounted `.env`) make
  `ee.Initialize` work in-container (validated end-to-end). Native is fine only for GEE-without-numpy
  (e.g. `fetch_chirps.py`). Lesson: GEE+numpy = container; don't mix gRPC and MKL in a native Windows
  process. **Related gotcha (same session):** in `docker compose run`, Git Bash **path-mangles a leading
  `/app/...`** argument into `C:/Program Files/Git/app/...` → pass **container-relative** paths
  (`data/rainfall/x.csv`), since the container working dir is already `/app`.

---

### [2026-06-01] pygrib `validDate` mis-dates multi-step ERA5-Land messages → use `validityDate`/`validityTime`

* **Symptom:**
  Extending `fetch_rainfall.py` to fetch `2m_temperature` at 00/06/12/18 UTC, the `--test` print
  showed every daily sample stamped **00:00** and a **stray 2025-03-31** entry when only Apr 1–3 were
  requested. Bucketing temperature by day for the daily Tmin/Tmax would mix one day's daytime samples
  with the next day's midnight sample (and drop/duplicate at the boundary) → corrupt freeze-thaw flag.

* **Root Cause:**
  ERA5-Land encodes each step against the **analysis** time: `dataDate`+`dataTime` is the model-init
  (always 00:00), while the true valid time lives in `validityDate`+`validityTime`. A day's 00:00
  reading is delivered as **step-24 of the previous analysis day** (e.g. dataDate 0331, step 24 →
  validity 0401 00:00). pygrib's `.validDate` returned the analysis date here, not the validity time,
  so the hour was lost and the midnight sample slid to the wrong calendar day. (The earlier
  accumulated-only `tp` fetch happened to look right because it requested a single 00:00 step.)

* **Resolution:**
  In `read_messages`, build the valid datetime from `int(g.validityDate)` + `int(g.validityTime)`
  instead of `g.validDate`. The existing day-mapping then works unchanged: accumulated vars (tp/smlt,
  validityTime 0, step 24) → day = validity − 1 day; temperature → bucket by validity calendar day
  (all 4 hourly samples of day D carry validityDate D). Verified on the cached test gribs: each day
  has exactly 4 distinct-hour samples with sensible Tmin/Tmax, no stray dates. Lesson: for GRIB, trust
  the `validity*` keys, never the analysis `dataDate`/`.validDate`, whenever steps/forecast hours are in play.

---

### [2026-05-31] CDS returns GRIB (not netCDF); MintPy GDAL has no GRIB/netCDF driver → read with pygrib

* **Symptom:**
  `fetch_rainfall.py` requested ERA5-Land `total_precipitation` as `data_format=netcdf`, but the
  downloaded `.nc` was actually GRIB, and GDAL refused it: *"recognized by driver GRIB, but plugin
  gdal_GRIB.so is not available."* A probe showed the MintPy image's GDAL has **neither** the GRIB
  **nor** the netCDF driver (both plugin-split and absent), and `cfgrib`/`xarray`/`netCDF4` are all
  missing. Only **pygrib** is installed (it ships with pyaps3).

* **Root Cause:**
  The new CDS endpoint hands back GRIB for ERA5-Land regardless of the requested format on this
  path, and this conda-forge GDAL build ships GRIB/netCDF as optional plugins that aren't included.

* **Resolution:**
  Request `data_format=grib` and read with **pygrib** (`grbs = pygrib.open(...)`; `g.values`,
  `g.validDate`) — the one reader guaranteed present. ERA5-Land `tp` is metres-accumulated from
  00 UTC, so a day's total is the **00:00-of-next-day** message (×1000 → mm). Separately, the CDS
  year/month/day request returns the full month×day **cross-product**, so clamp the result to
  [start, end]. (If netCDF is ever needed here: `conda install -c conda-forge libgdal-grib
  libgdal-netcdf`, but pygrib avoids touching the image.)

---

### [2026-05-31] Inverse-velocity TTF v1 reported false "failures" — noise dressed as signal

* **Symptom:**
  The first run of `inverse_velocity_ttf.py` flagged **7 alert zones as ACCELERATING with a
  failure in 11–51 days**. But each flagged zone had a **positive** net velocity
  (+37 / +14 / +11 mm/yr) — i.e. moving *toward* the sensor, the opposite of a downslope
  failure. A confident "fails in 11 days" on a slope that isn't even moving the failure way.

* **Root Cause (three compounding):**
  1. **Window dilution** — averaging a 5×5 window around a ~3-pixel zone mixed the creep
     signal with stable neighbours, so the series didn't represent the zone (the orchestrator
     reports these zones creeping at ≤ −15 mm/yr, but the diluted window read positive).
  2. **No direction gate** — the inverse-velocity fit used the negative *sub-intervals* of a
     net-positive, noisy series (cherry-picking), manufacturing a spurious decreasing 1/|v|.
  3. **Raw vs high-pass mismatch** — the creep mask used `*_mean_velocity_los.tif` while the
     orchestrator defines creep from `*_mean_velocity_los_highpass.tif`, so the wrong pixels
     were selected (and 66 zones came back INSUFFICIENT).

* **Resolution:**
  Mask the window to creep pixels using the **high-pass** velocity (orchestrator-consistent);
  HARD-gate before any TTF — the zone must be genuinely creeping (**net ≤ −15 mm/yr**) AND move
  **consistently** in the failure direction (≥70% of smoothed velocities negative); keep
  R²≥0.5 on the 1/|v| fit. Result: **0 accelerating, all STEADY** across all 3 ASC stacks — the
  honest outcome. Lesson: an extrapolation method (inverse velocity) will *always* return a
  number; the discipline is the GATES — require consistent failure-direction motion and match
  the upstream signal definition before trusting it. Same "noise dressed as signal" class as
  the DESC velocity bias above; caught here in our own output.

---

### [2026-05-31] MintPy on the disconnected DESC stacks — quality traps that led to dumping both

Not bugs — data-quality findings worth recording so we don't repeat the evaluation.

* **frame484 — auto reference-point fails (`No pixel ... > 0.85`).**
  `smallbaselineApp.py` aborted at `reference_point`: `RuntimeError: No pixel with average
  spatial coherence > 0.85 are found for automatic reference point selection!`. Root cause:
  the stack is pervasively decorrelated (19/33 pairs QUARANTINE). Lowering
  `mintpy.reference.minCoherence` to 0.6 lets it proceed, but then only **858/109,077 px
  (0.8%)** are invertible against a random edge-pixel reference → junk. **Resolution: DUMP
  the stack.** Lesson: a failed 0.85 auto-reference on a whole frame is itself strong
  evidence the stack is unusable; lowering the floor is a *probe*, not a fix.

* **frame479 — disconnected-network velocity is biased; period-split made it WORSE.**
  MintPy handles the 3-island disconnect natively (`***WARNING: the network is NOT fully
  connected … Continue to use SVD to resolve the offset between different subsets`,
  `L2 min-norm on: deformation velocity`) and inverts 99.3% of pixels — but the velocity is
  physically implausible (std **57 mm/yr**, 9,016 px >100 mm/yr). Period-splitting to the
  connected monsoon island (`mintpy.network.startDate/endDate`) removed the disconnect but
  made velocity *worse* (std **137 mm/yr**, 30,378 px >100). Root cause: (1) the ~84-day
  window amplifies velocity noise (velocity = displacement/time → short baseline ≈ 2× the
  noise); (2) monsoon decorrelation. **Resolution: DUMP the stack.** Two lessons: **(a) high
  temporalCoherence (good inversion *fit*) does NOT imply a trustworthy *velocity*** on a
  short or disconnected network; **(b) min-norm-velocity can *look* cleaner only because it
  regularizes cross-gap motion toward zero** — a fiction, not a measurement. Compare to the
  ASC stacks (std 21–30 mm/yr, ~0 implausible px) to judge.

---

### [2026-05-31] Multi-line bash / heredocs through PowerShell -> docker -> bash get mangled

* **Symptom:**
  Two failures while running MintPy step 3 via `docker compose run --rm mintpy bash -lc
  '<multi-line script>'` from PowerShell. (1) A `python - <<PY ... PY` heredoc lost its
  inner double-quotes and bash reported `here-document ... delimited by end-of-file` +
  `python: command not found`. (2) A `{ ...; } 2>&1 | tee` block failed with
  `-c: line 8: syntax error: unexpected end of file` (exit 2) — MintPy never started.

* **Root Cause:**
  Passing a complex multi-line single-quoted argument through the PowerShell ->
  docker-compose -> `bash -lc` chain does not preserve the script verbatim (heredoc
  bodies, `{ }` grouping, and embedded quotes get re-tokenised). It is a quoting/transport
  problem, not a MintPy or bash bug.

* **Resolution:**
  **Never inline multi-line shell/python through this chain — put it in a committed file
  and invoke with a trivial one-liner.** For step 3: `workflows/mintpy_f106_era5.cfg` (the
  MintPy config, so no heredoc is needed to write it), `workflows/run_mintpy_era5_f106.sh`
  (the run + export sequence; `bash /app/workflows/run_mintpy_era5_f106.sh`), and
  `workflows/crossval_mintpy.py`. This is quoting-safe, reproducible, and reviewable. For
  one-off Python checks, prefer a small `workflows/*.py` over `python -c "..."`.

---

### [2026-05-31] MintPy 1.6.2 inversion crash on Python 3.14 / numpy 2.4 (array-vs-scalar strictness)

* **Symptom:**
  `smallbaselineApp.py` loaded our HyP3 stack, built the network, picked a reference,
  and began `invert_network` (95,178/109,077 px) — then crashed:
  `TypeError: only 0-dimensional arrays can be converted to Python scalars` →
  `ValueError: setting an array element with a sequence` at
  `ifgram_inversion.py: inv_quality[idx] = inv_quali`.

* **Root Cause:**
  The unpinned `environment.mintpy.yml` solved to **Python 3.14.5 + numpy 2.4.6**
  (both bleeding-edge, late-2025) with **MintPy 1.6.2** (Jul-2025). numpy 2.x removed
  the implicit size-1-array → scalar conversion MintPy's inversion-quality code
  relied on, so assigning a size-1 array to a scalar slot now raises.

* **Resolution:**
  Pin a tested generation in `docker/environment.mintpy.yml`: `python=3.11.*` and
  `numpy<2` (1.26 restores the old auto-conversion). Rebuild `insar-mintpy`. (MintPy
  uses its own image, so this numpy pin doesn't affect the `insar` env's numpy 2.2.)

---

### [2026-05-31] MintPy work dir on the OneDrive bind mount → PermissionError on `utime`

* **Symptom:**
  `smallbaselineApp.py` from a work dir under `/app/data/...` (the OneDrive/WSL2 bind
  mount) crashed immediately: `PermissionError: [Errno 1] Operation not permitted:
  '.../smallbaselineApp.cfg'` inside `shutil.copy2` → `copystat` → `utime`.

* **Root Cause:**
  MintPy preserves file metadata (`copy2`/`copystat` sets timestamps via `utime`);
  the drvfs bind mount of the OneDrive-backed Windows folder does not permit `utime`
  by the container user. Plain reads/writes work; only metadata-timestamp ops fail.

* **Resolution:**
  Run MintPy with its **work dir on the container-local fs** (`/tmp/...`), reading the
  clipped inputs from the bind mount (reads are fine) and copying only the final
  outputs (velocity.h5 / GeoTIFF) back to `data/mintpy/<stack>/`. Verified: load /
  network / reference / inversion-start all succeed from `/tmp`.

---

### [2026-05-31] MintPy `prep_hyp3.py` requires the HyP3 `.txt` metadata file (we only extracted `.tif`s)

* **Symptom:**
  Planning the MintPy ingestion (`prep_hyp3.py`) — its `--help` shows that, per
  interferogram, it needs the HyP3 **`.txt` metadata** file (e.g.
  `S1AA_..._74C2.txt`) alongside `_unw_phase.tif`, `_corr.tif`, plus `_dem.tif` and
  `_lv_theta.tif`. But `data/processed_tiffs/<product>/` contains only the `.tif`s.

* **Root Cause:**
  Phase-1's extractor (`download_hyp3_products.py`, `WANTED_TIFF_SUFFIXES`)
  deliberately extracted only the GeoTIFFs we needed for our custom pipeline; the
  HyP3 `.txt` metadata (orbit/baseline/etc., which MintPy reads for the `.rsc`) was
  never unpacked from `data/raw_zips/*.zip`.

* **Resolution (planned for MintPy step 2):**
  Before `prep_hyp3.py`, extract the `.txt` for each frame106 KEEP pair from
  `data/raw_zips/` into a MintPy work dir (alongside unw_phase/corr/dem/lv_theta).
  Not a bug in the existing pipeline — a known input requirement for the MintPy path.

---

### [2026-05-31] `.gitignore`: inline comments unsupported; broad `.env.*` was hiding `.env.template`

* **Symptom:**
  After adding `!.env.template` with a trailing `# comment` on the same line, the
  template was *still* git-ignored. Separately, `.env.template` (a committable doc)
  had never been trackable.

* **Root Causes:**
  1. `.gitignore` does **not** support inline comments — `!.env.template   # ...` is
     parsed as a literal pattern (filename incl. the spaces and `#`), so the negation
     never applied.
  2. The broad pattern `.env.*` matches `.env.template`, so the convention doc was
     silently excluded from version control.

* **Resolution:**
  Put the comment on its own line and the negation alone: a `# comment` line followed
  by `!.env.template` (placed AFTER `.env.*`). Verified: `.env.template` is now
  trackable while the real `.env` stays ignored. (Gotcha for any future `!negation`.)

---

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

### [2026-05-25] Python 3.13 on PATH had no `pip` module

* **Symptom:**
  Trying to install asf_search / hyp3_sdk into the default-PATH Python returned `No module named pip`.

* **Root Cause:**
  The default Python on the user's PATH was 3.13 from the Windows installer, but pip had not been bootstrapped into it. The project standard (`environment.yml`) targets Python 3.10, but no conda env had been created yet, so neither the 3.13 install nor any conda env had the project deps.

* **Resolution:**
  Used the `py -3.10` launcher to invoke the Python 3.10 install (which did have pip) and pip-installed packages there as a temporary unblock for the dry-run. The permanent fix landed later via the `insar_qa_env` conda environment.

* **Lesson:**
  Always check `python --version` and `python -m pip --version` before assuming the interpreter on PATH is the one the project targets. Use `py -0` on Windows to list every installed Python.

---

### [2026-05-25] `geopandas.unary_union` deprecation in 1.x

* **Symptom:**
  Dry-run printed `DeprecationWarning: The 'unary_union' attribute is deprecated, use the 'union_all()' method instead.`

* **Root Cause:**
  geopandas 1.x renamed `GeoSeries.unary_union` (attribute) to `GeoSeries.union_all()` (method). The submitter script was written against the older API.

* **Resolution:**
  Replaced `gdf.geometry.unary_union` with `gdf.geometry.union_all()` in `workflows/submit_hyp3_jobs.py`.

* **Lesson:**
  geopandas crossed a major-version boundary at 1.0 with several API renames. Audit deprecation warnings the first time a script runs against a freshly-pinned environment.

---

### [2026-05-25] Frame-boundary scenes produced cross-frame interferograms

* **Symptom:**
  Dry-run output showed interferogram pairs whose member granule names had different start-time seconds within the same orbit pass — e.g. `S1A...20250507T005937 -> S1A...20250519T005911`. This means the two scenes are different Sentinel-1 *frames* of the same satellite pass, not the same frame across two dates.

* **Root Cause:**
  The scene-partitioning logic in `submit_hyp3_jobs.py` grouped only by `(flightDirection, pathNumber)`. The Ramban AOI straddles a frame boundary, so each pass returned 2 adjacent frames per acquisition. Pure-chronological pair building then mixed frame-A on day 1 with frame-B on day 13. InSAR pairs across frames produce interferograms only over the small overlap region — wasteful at best, geometrically incorrect at worst.

* **Resolution:**
  Added `frameNumber` to the partition key so buckets are `{direction}_path{path}_frame{frame}`. Each frame now has its own clean time-series. Verified by spot-checking that every pair member shares the same start-time-of-second within a bucket.

* **Verification:**
  Pair count grew from 41 to 68 because previously-valid same-day-different-frame siblings (5 stacks instead of 3) had been dropped by the `dt_days == 0` guard. The 68-pair output now represents 5 internally-consistent stacks: 3 ASCENDING + 2 DESCENDING.

* **Lesson:**
  When an AOI straddles satellite frame or path boundaries, partition on every dimension that matters for radar geometry: direction, path, AND frame. Don't trust pair lists until you've confirmed members share the same observation geometry.

---

### [2026-05-25] HyP3 auth made fatal in dry-run unnecessarily

* **Symptom:**
  Dry-run exited with `[CRITICAL] HyP3 auth failed` even though no submission was attempted — preventing pair-count preview while credentials were being repaired.

* **Root Cause:**
  Script treated HyP3 authentication as a fatal precondition regardless of `--submit`. Auth + dedupe is only needed for actual submission; for dry-run preview, scene + pair counts can be computed without credentials.

* **Resolution:**
  Restructured the script so HyP3 auth is fatal only under `--submit`. In dry-run, auth is attempted (to enable dedupe + quota display when possible) and degrades to a warning on failure. The final summary surfaces the auth error so the user knows dedupe was skipped.

* **Lesson:**
  Don't gate read-only preview / planning steps on credentials that are only needed for write steps. Defer the auth requirement to the moment of the actual side-effect.

---

### [2026-05-25] `gdal=3.6.*` pin in environment.yml no longer solvable

* **Symptom:**
  When the libmamba solver ran, it picked GDAL 3.10.3 instead of the 3.6.x pin requested in `environment.yml`. No hard error — silent version upgrade.

* **Root Cause:**
  GDAL 3.6.x is from 2022. conda-forge has moved on, and a 3.6.x build matching the rest of the pinned versions (Python 3.10, current rasterio, etc.) no longer exists in current channel snapshots.

* **Resolution:**
  Accepted GDAL 3.10.3. rasterio is built against it and the API is backward-compatible for all read/write operations the project uses.

* **Lesson:**
  Pinning to a specific minor of a fast-moving C library like GDAL inside a Python env will eventually become unsolvable. Pin only when a known incompatibility forces it; otherwise let the solver pick the newest compatible.

---

### [2026-05-27] `_netrc` was a directory, not a file

* **Symptom:**
  `Get-Content ~/_netrc` reported `Access to the path 'C:\Users\varun\_netrc' is denied` even though the user owned the path with FullControl on the ACL. Python's `netrc.netrc()` raised `PermissionError: [Errno 13] Permission denied`. `icacls` showed correct permissions, deepening the mystery.

* **Root Cause:**
  The user (or some tool) had created `_netrc` as a **directory** containing a file named `.netrc` (1791 bytes) inside it. PowerShell and Python both refuse to read a directory as a file. Discovered by checking `Get-Item ~/_netrc | Select Attributes`, which printed `Directory` instead of `Archive`.

* **Resolution:**
  Copied the inner `C:\Users\varun\_netrc\.netrc` to `C:\Users\varun\.netrc` (canonical Windows-portable location). Verified Python could parse it. Removed the misplaced `_netrc/` directory.

* **Lesson:**
  "Access denied" on a credential file with correct ACLs is suspicious — first check whether the path is actually a file. The `.netrc.template` now spells out the file-vs-folder check.

---

### [2026-05-27] Python's `netrc` parser rejected the comment-heavy file

* **Symptom:**
  ```
  netrc.NetrcParseError: bad toplevel token '---' (C:\Users\varun/.netrc, line 3)
  ```
  The error pointed to line 3, but line 3 of the file contained no `---` — only `# =====`. Line numbers were misleading.

* **Root Cause:**
  Python's stdlib `netrc` parser uses `shlex` with comments disabled (`lexer.commenters = ''`). A hand-rolled `#`-handling branch exists in the parse loop, but it can misreport `lineno` when comments precede the first `machine` block and contain other punctuation. The actual offending token (`---`, from a comment further down) appeared while shlex's internal pointer was already past the first valid block.

* **Resolution:**
  Wrote a one-shot script (`workflows/_fix_netrc.py`, since deleted) that backed up the original to `~/.netrc.bak`, stripped every `#`-prefixed line, kept only `machine`/`login`/`password` lines, and rewrote the file. Parsed clean. Backup remains in case manual recovery is needed.

* **Lesson:**
  Keep `.netrc` files minimal: one credential block per machine, no comments, no decorative separators. The Python parser is more brittle than the .netrc spec implies. `.netrc.template` has been rewritten to make this explicit.

---

### [2026-05-27] HyP3 OAuth application required one-time pre-authorization

* **Symptom:**
  First call to `hyp3_sdk.HyP3()` after fixing the netrc failed with:
  ```
  hyp3_sdk.exceptions.AuthenticationError: Pre authorization required for this application,
  please authorize by visiting the resolution url:
  https://urs.earthdata.nasa.gov/approve_app?client_id=BO_n7nTIlMljdvU6kRRB3g
  ```

* **Root Cause:**
  NASA Earthdata's OAuth model requires every Earthdata user to explicitly authorize each downstream application against their account, once per `(user, app)` pair. The HyP3 SDK is a registered OAuth client. Until the user clicks "Approve" at the resolution URL, every SDK call fails — even with correct credentials and a valid `.netrc`.

* **Resolution:**
  User opened the URL in a browser while logged into Earthdata and clicked Approve. After that, every subsequent SDK call authenticates silently with no further interactive steps.

* **Lesson:**
  OAuth-based scientific data APIs (Earthdata, Copernicus Data Space, Sentinel Hub) all share this pattern: a one-time browser approval per app on first use. Now documented in `.netrc.template` Step 4 so future setup doesn't get blocked here.

---

### [2026-05-27] `hyp3_sdk.HyP3.username` attribute removed in 7.x

* **Symptom:**
  ```
  AttributeError: 'HyP3' object has no attribute 'username'
  ```

* **Root Cause:**
  Older hyp3_sdk versions exposed `hyp3.username` as a convenience attribute. The 7.x rewrite removed it; user identity is now fetched via `hyp3.my_info()`, which returns a dict keyed by `user_id`.

* **Resolution:**
  Replaced every occurrence in `workflows/submit_hyp3_jobs.py` and `workflows/download_hyp3_products.py`:
  ```python
  user_id = hyp3.my_info().get("user_id", "<unknown>")
  ```

* **Lesson:**
  Major-version SDK upgrades silently rename or remove attributes. When pinning to `>=2.0` (as `requirements.txt` does for hyp3-sdk), audit the changelog for breaking changes — the SDK landed a substantial rework at 7.0.

---

### [2026-05-29] `UnicodeEncodeError` writing `→` to the Windows console logger

* **Symptom:**
  `workflows/agentic_orchestrator.py` printed repeated `--- Logging error ---`
  blocks: `UnicodeEncodeError: 'charmap' codec can't encode character '→'`.
  The script still completed and all output files were correct.

* **Root Cause:**
  The logging `StreamHandler` writes to stdout, which on Windows uses the legacy
  `cp1252` ('charmap') code page — it cannot encode the `→` (U+2192) arrow used
  in some log messages. The `FileHandler` (explicit `encoding="utf-8"`) wrote the
  same messages fine; only the console stream failed. Non-fatal (Python's logging
  catches it and prints the error block) but noisy.

* **Resolution:**
  Replaced the unicode arrows in *log strings* with ASCII (`->`). Unicode is
  retained where it belongs — the HTML/Markdown/JSON output files, which are
  written with explicit `encoding="utf-8"`.

* **Lesson:**
  Keep `logging` messages ASCII-only on Windows (or reconfigure stdout to UTF-8).
  Reserve unicode for files you write with an explicit UTF-8 encoding. This is
  the third Windows-console encoding gotcha in the project (cf. the UTF-16 Tee
  logs) — on this platform, assume the console is cp1252 unless proven otherwise.

---

### [2026-05-29] SBAS velocities implausible (±300 mm/yr) — missing per-interferogram deramp

* **Symptom:**
  First working SBAS inversion of ASC_path27_frame106 produced LOS velocities of ±100–400 mm/yr (real landslide creep is mm-to-cm/yr). A temporal-coherence quality mask at γ≥0.7 *removed 99% of pixels yet the survivors were still wild* — the tell that the problem was NOT random unwrapping noise.

* **Root Cause:**
  We inverted the masked displacement interferograms **without the standard SBAS pre-processing**: each HyP3 unwrapped-phase interferogram carries (a) an arbitrary additive constant (its unwrapping reference is per-pair) and (b) a long-wavelength orbital + atmospheric ramp. Direct inspection of 6 pairs confirmed it: 12-day pairs had non-zero medians (−53…+21 mm) and large spatial spread (std 22–49 mm, p5–p95 ≈ 150 mm) where real 12-day motion should be ~0 mm at mm-scale. The least-squares inversion faithfully integrated those per-pair ramps into huge fake velocities. Referencing the *time-series* after inversion (which we did) cannot remove a *per-interferogram* ramp. High temporal coherence just meant the ramped interferograms were mutually consistent.

* **Resolution:**
  Added `fit_deramp_planes()` + `apply_deramp()` to `custom_sbas_inverter.py`: fit a 2-D plane `a·col + b·row + c` to each interferogram over the clipped AOI and subtract it **before** inversion. This removes both the constant offset and the orbital/long-wavelength ramp, while a first-order plane cannot absorb sub-km localized deformation (the landslide signal is preserved). Applied consistently in the block loop, the coarse reference pre-pass, and the full-res reference pixel read.

* **Verification (before → after deramp):**
  - Pixels passing γ≥0.7: 230 → **14,045** (0.9% → 57% of solvable) — removing per-pair ramps made the network self-consistent, which is exactly what temporal coherence measures.
  - Raw velocity p5–p95: −81…+197 → **−25…+81 mm/yr**.
  - High-passed std: 84 → **29 mm/yr**; strict-AOI median 0.0, p5–p95 ±50, coverage 13.6%.
  - Pixels exceeding |100| mm/yr: 29.6% → **1.7%**.

* **Lesson:**
  Always deramp (and spatially reference) each interferogram BEFORE SBAS inversion. Unreferenced HyP3 unwrapped phase contains large non-deformation components. A quality filter that nukes most pixels but leaves the survivors implausible is a signature of a *systematic input* error, not random noise — inspect the raw inputs before adding more filters.

---

### [2026-05-29] ROOT CAUSE of all BLAS/LAPACK crashes: env not activated, BLAS DLLs not on PATH

* **Supersedes the diagnoses in the two entries below.** The earlier entries blamed a "numpy 2.x + MKL large-array bug." That was **wrong**. The real cause is simpler and explains every case.

* **Symptom:**
  `np.linalg.svd`, `np.linalg.pinv`, `np.linalg.inv`, and even a plain `A @ b` matmul all hard-crash with `Windows fatal exception: code 0xC06D007F` — on arrays as small as 31×14. Elementwise numpy ops (add, multiply, `np.mean`, boolean masks) work fine.

* **Root Cause:**
  We were launching scripts with the **full python.exe path** (`& "C:\Users\varun\.conda\envs\insar_qa_env\python.exe" script.py`) and manually setting only `GDAL_DATA`/`PROJ_LIB` — **without running `conda activate`**. numpy's BLAS/LAPACK lives in a DLL under `<env>\Library\bin` (plus dependencies in `Library\mingw-w64\bin`). Those directories are added to `PATH` by `conda activate`, but we never did that. Without them, numpy's delay-loaded BLAS DLL fails to load at the first BLAS/LAPACK call, producing the `0xC06D007F` delay-load fatal exception. Elementwise ops live in numpy's self-contained `_multiarray` and don't need the external BLAS, which is why they always worked — and why we misread the pattern as "only large arrays crash."

* **Proof:**
  Prepending `<env>\Library\bin` + `Library\mingw-w64\bin` to `PATH` before `import numpy` → matmul, inv, svd, pinv all return `OK`, exit 0. `os.add_dll_directory(Library\bin)` alone was NOT sufficient (the BLAS DLL's transitive dependencies need the broader PATH search).

* **Resolution:**
  1. **Correct invocation:** run compute scripts with the env activated, or prepend the env DLL dirs to `PATH`. `conda run -n insar_qa_env python ...` also works.
  2. **In-script self-heal:** `custom_sbas_inverter.py` now prepends `<sys.prefix>\Library\bin`, `Library\mingw-w64\bin`, and `Scripts` to `PATH` *before* importing numpy. Any heavy-linalg script should include this bootstrap.

* **Implication for prior workarounds:**
  The manual-Pearson-r (in `phase_elevation_audit.py`) and stdlib-SVG (in `sbas_network_graph.py`) workarounds were treating a symptom. They still work and we're leaving them in place (surgical-changes rule — they're correct and not worth churning), but `np.linalg` and matplotlib would now both function if those scripts used the DLL bootstrap or were run under an activated env.

* **Lesson:**
  On Windows conda, ALWAYS activate the environment (or replicate the PATH that activation sets) before running anything that touches numpy's BLAS/LAPACK. A `0xC06D007F` on a tiny array is a DLL-load failure, not a numerical bug — check the DLL search path before assuming a library bug.

---

### [2026-05-28] Matplotlib `savefig` crashes inside `patches.draw` on numpy 2.x + Windows

* **Symptom:**
  Any matplotlib `savefig()` call in `workflows/sbas_network_graph.py` produced:
  ```
  Windows fatal exception: code 0xc06d007f

  Current thread 0x... (most recent call first):
    File ".../matplotlib/transforms.py", line 2437 in get_affine
    File ".../matplotlib/transforms.py", line 2438 in get_affine    (recursive)
    File ".../matplotlib/patches.py", line 641 in draw
    File ".../matplotlib/figure.py", line 3263 in draw
    File ".../matplotlib/backends/backend_agg.py", line 382 in draw
    File ".../matplotlib/figure.py", line 3497 in savefig
  ```
  Verified with a three-point `ax.plot([1,2,3],[1,4,9])` smoke test — even the most trivial plot crashes during the savefig draw phase. The Python process exits with status `-1066598273` and no Python traceback unless `python -X faulthandler` is enabled.

* **Root Cause:**
  matplotlib 3.10.x on the conda-forge build picks up the same Intel MKL stack that broke `np.corrcoef` in the audit script (see prior entry). `patches.draw` calls into `transforms.get_affine`, which recurses through affine composition — that path includes a 2×2 matrix inversion that lands in LAPACK. On Windows with numpy 2.x + MKL the LAPACK call aborts at C level, regardless of the matplotlib backend (Agg, SVG, or PyQt5 all crash the same way). PyQt5 also isn't installed in this env, which produced a separate but cosmetic 0xC0000139 on the first invocation.

* **Resolution:**
  Sidestepped matplotlib entirely for `sbas_network_graph.py`. Rewrote the renderer to emit standalone SVG via stdlib string concatenation — no LAPACK in the draw path, no font metrics computation, no backend selection. Outputs are `data/qa_masks/_network_graphs/<stack>.svg` plus a self-contained `index.html` that embeds all 5 SVGs.

  Tradeoffs accepted: no `tight_layout` (used explicit `subplots_adjust`-style margins in SVG instead), no built-in legend object (rendered manually with `<line>` + `<text>`), no interactive picking (added `<title>` tooltips per node instead — show on hover in any browser).

* **Why we didn't downgrade matplotlib/numpy instead:**
  The conda env was just stabilised after weeks of resolving the OneDrive sync issue and the old conda 4.12 solver hangs. Downgrading numpy below 2.0 would cascade into rasterio, geopandas, scipy, and asf_search version pins that all depend on numpy ≥2. Rolling our own SVG was 200 lines and one debugging cycle vs an indefinite env-rebuild rabbit hole. Documenting the workaround is cheaper than fighting the binary stack.

* **Lesson:**
  When a heavy plotting library crashes at C level inside graphics primitives on a specific platform, generating SVG from stdlib is often less effort than the chain of dependency-pinning needed to make the library work. SVG also has the side benefit of being scriptable, scalable, scriptable, and InSAR-community standard for baseline diagrams.

---

### [2026-05-28] Silent zip corruption from HyP3 downloader (~2% rate)

* **Symptom:**
  Across two sessions and 184 downloads, **4 zips arrived truncated** but the downloader reported success. The corrupt files were 60-189 MB on disk while the real products were 210-228 MB. Subsequent extraction failed with `BadZipFile: File is not a zip file`. Affected products:
  - Session 1: `S1AA_20250628T130444_20250710T130443_..._F190` (60 MB / actual 211 MB)
  - Session 2: `S1AA_20250519T005937_20250612T005936_..._737E` (136 MB / actual 221 MB)
  - Session 2: `S1AA_20250628T130444_20250803T130443_..._D7ED` (168 MB / actual 212 MB)
  - Session 2: `S1AA_20250928T005934_20251022T005935_..._8241` (189 MB / actual 220 MB)

* **Root Cause:**
  `hyp3_sdk.Job.download_files()` writes the response stream to disk and returns the path without verifying integrity. If the underlying HTTP connection drops mid-transfer (network blip, ASF rate-limit reset, OneDrive sync interference, etc.), the partial file persists on disk with a believable-looking size. The downloader's `existing.stat().st_size > 0` skip check then preserves the corrupt file across reruns. The 2% failure rate is consistent enough across sessions to suggest it's a systemic issue with long-lived HTTP downloads on this network, not a one-off.

* **Resolution:**
  Patched `workflows/download_hyp3_products.py`:
  1. Added `_verify_zip(path)` that runs `zipfile.ZipFile(path).testzip()` — reads the central directory and CRCs every entry.
  2. Added `_download_one_with_retry(job, dest_dir, retries=1)` which downloads, verifies, and on corruption deletes + retries once before giving up.
  3. In `extract_tiffs()`, a `BadZipFile` now triggers `zip_path.unlink()` so the next `--download` run picks up the gap automatically.
  
  Net effect: the pipeline is now self-healing for the common case (one bad transfer) and surfaces an explicit error for the rare case (two bad transfers in a row).

* **Lesson:**
  Trust HTTP downloads only after CRC-level verification of the result. The standard `stat().st_size > 0` skip heuristic is dangerous when the corruption mode is "got most of the bytes" rather than "got zero bytes". For any pipeline pulling >100 large files over a flaky network, integrity verification + automatic re-fetch is mandatory infrastructure, not a nice-to-have.

---

### [2026-05-27] `np.corrcoef` crashes with Windows fatal exception 0xC06D007F on large arrays

* **Symptom:**
  In `workflows/phase_elevation_audit.py`, calling `np.corrcoef(d, z)` where `d` and `z` are ~5.5M-element float64 arrays produced:
  ```
  Windows fatal exception: code 0xc06d007f

  Current thread 0x00006ce4 (most recent call first):
    File ".../numpy/lib/_function_base_impl.py", line 2893 in cov
    File ".../numpy/lib/_function_base_impl.py", line 3037 in corrcoef
  ```
  The Python interpreter aborted without raising a Python exception; the script exited with code `-1066598273` (= `0xC07A18FF` unsigned), which masked the underlying C-level crash. No log lines were written for the first product, only the initial INFO line.

* **Root Cause:**
  `np.corrcoef` calls into `np.cov`, which on the conda-forge numpy 2.x build links to a LAPACK implementation that crashes on multi-million-element single-pass covariance computations on Windows. The crash is at C level — not in Python — so it bypasses `try/except` and produces no traceback unless `python -X faulthandler` is enabled. Reported intermittently in numpy/MKL on large geospatial workloads.

* **Resolution:**
  Replaced the call with manual Pearson r computation using only sum/mean/sqrt primitives:
  ```python
  z_dev = z - z.mean()
  d_dev = d - d.mean()
  cov_zd = float(np.mean(z_dev * d_dev))
  var_z = float(np.mean(z_dev * z_dev))
  var_d = float(np.mean(d_dev * d_dev))
  r = cov_zd / (np.sqrt(var_z) * np.sqrt(var_d))
  ```
  These ops route through numpy's element-wise kernels, not LAPACK, and never crashed across all 68 products in the subsequent run.

* **Diagnostic technique that saved time:**
  When a Python script exits with a Windows status code but no traceback, run it with `python -X faulthandler` to force a C-level stack trace to stderr. This is how we located the offending `np.cov` line.

* **Lesson:**
  For large-array statistics on Windows + numpy 2.x, prefer manual formulas over LAPACK-backed convenience functions. Single-pass element-wise arithmetic is both more robust and trivially auditable.

---

### [2026-05-27] `hyp3.find_jobs(name=X)` does exact-match, not prefix-match (dedupe silently broken)

* **Symptom:**
  After successfully submitting 68 jobs named `Ramban_NH44_ASCENDING_path100_frame102`, `Ramban_NH44_DESCENDING_path34_frame484`, etc., a verification call to `hyp3.find_jobs(name='Ramban_NH44')` returned 0 jobs, even though all 68 were visibly queued in the HyP3 dashboard and credits had been correctly debited (8000 → 7320).

* **Root Cause:**
  The `name` parameter on `hyp3_sdk.HyP3.find_jobs()` passes through to the HyP3 REST API which does **exact** string equality, not prefix or substring matching. Our submitter named jobs with bucket-specific suffixes (`{prefix}_{bucket_key}`), so a search for the bare prefix returned nothing. The submitter's `fetch_existing_pair_signatures` had been relying on this same call to populate the dedupe set — meaning **the dedupe was a silent no-op the entire time**. This run wasn't affected (the account had zero prior `Ramban_NH44_*` jobs), but any future re-submission would have re-queued duplicate pairs and double-charged credits.

* **Resolution:**
  Changed both scripts to call `hyp3.find_jobs()` with no `name` filter and prefix-filter client-side:
  - `workflows/submit_hyp3_jobs.py` — `fetch_existing_pair_signatures` now iterates `job.name.startswith(prefix)` after fetching all jobs.
  - `workflows/download_hyp3_products.py` — `fetch_jobs` does the same. Status report now shows `Fetched N total; M match prefix 'X'`.
  Verified post-fix: the downloader correctly reports `68 match prefix 'Ramban_NH44'`.

* **Lesson:**
  When an SDK exposes a `name=`-style filter parameter, never assume prefix semantics. Test by submitting one known-suffixed job and confirming the filter finds it before relying on the filter for deduplication or any other correctness-critical logic. Always cross-check API-side filters against client-side filtering on a small sample.

---

### [2026-05-27] `hyp3.check_quota()` deprecated in favor of `check_credits()`

* **Symptom:**
  ```
  DeprecationWarning: This method is deprecated and will be removed in a future release.
  Please use `HyP3.check_credits` instead.
  ```

* **Root Cause:**
  ASF renamed the user-visible "quota" concept to "credits" because the underlying cost model is now multi-currency — different product types cost different amounts. The functional behavior is identical.

* **Resolution:**
  Replaced `hyp3.check_quota()` with `hyp3.check_credits()` in both workflow scripts. Local variable `quota` renamed to `credits` for consistency with the new vocabulary.

* **Lesson:**
  Run the workflow scripts against a real account at least once after every SDK upgrade — deprecation warnings only fire at runtime, not import time.

---

### [2026-05-27] Conda command not recognized in VS Code terminal

* **Symptom:**
  Running conda commands (like `conda activate`) in the VS Code terminal returned the error:
  ```
  conda : The term 'conda' is not recognized as the name of a cmdlet, function, script file, or operable program.
  ```

* **Root Cause:**
  When VS Code opens a new PowerShell or command prompt terminal on Windows, it doesn't automatically load the path to the Anaconda/Miniconda installation unless it's explicitly initialized for that shell or the VS Code workspace is configured with the correct Python interpreter.

* **Resolution:**
  1. Opened the official **Anaconda Prompt** (which has `conda` configured on startup).
  2. Ran `conda init powershell` to register conda commands globally for Windows PowerShell.
  3. Closed and restarted VS Code, allowing it to load the updated PowerShell profile.
  4. (Alternative) Used the VS Code Command Palette (`Ctrl+Shift+P` -> `Python: Select Interpreter`) to select the `insar_qa_env` environment directly, allowing VS Code to handle activation silently under the hood.

* **Lesson:**
  Standard Windows terminals do not expose the `conda` command by default. Always use `conda init <shell>` to integrate conda with your default shells, or rely on VS Code's native Python interpreter selector to automate environment activation.

---

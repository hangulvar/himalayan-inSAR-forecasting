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

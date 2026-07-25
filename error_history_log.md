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

### [2026-07-22] `S1AA_`-hardcoded date parsers silently drop cross-unit products (S1AD seam un-invertible)

* **Symptom:** `custom_sbas_inverter.py` raised `ValueError: cannot parse dates from
  S1AD_20260618T125635_20260625T125553_...` when the S1A×S1D seam product was fed to the
  SBAS inversion — the rebuild literally could not invert the cross-unit pair.
* **Root cause:** five date-parsing regexes were hardcoded to the `S1AA_` prefix
  (`custom_sbas_inverter`, `sbas_network_graph`, `stacks`, `coherence_watch`,
  `_analyze_qa_stats`). They pre-date the June-2026 S1 constellation handover (§56), which now
  ships cross-unit HyP3 products named `S1AD` (and eventually `S1DD`). The manifest ingested the
  seam correctly only because it reads path/frame from HyP3 **job metadata**, not the filename —
  which masked the bug until the inverter parsed the filename.
* **Fix:** broadened all five to `S1[A-D][A-D]_` (matches every A/B/C/D pairing; still matches
  all existing `S1AA`). New regression test `test_pair_date_parsers_accept_cross_unit_products`
  in `tests/test_science_verification.py` pins both a same-unit and a cross-unit name through
  both inversion-path parsers. Battery 98 green. (2 GACOS-path references — a `gacos_request`
  docstring + a `_gacos_crosscheck` glob — left for the separate GACOS workstream.)

### [2026-07-22] Bash tool mangles `/app/...` container paths (MSYS path translation) — failed background poll

* **Symptom:** a background `docker compose run insar python /app/_tmp_watch_jobs.py` exited
  immediately with `python: can't open file '/app/C:/Program Files/Git/app/_tmp_watch_jobs.py'`.
* **Root cause:** the Bash tool runs Git Bash (MSYS), which auto-translates a leading-slash
  argument like `/app/...` into a Windows path (`C:\Program Files\Git\app\...`) *before* it
  reaches the container. The path never resolved inside the container; the poll never ran (no
  time lost — the ASF jobs were still processing).
* **Fix / rule:** run docker via the **PowerShell tool** (no MSYS translation), or pass the
  script path **relative** to the compose `working_dir` (`/app`) — i.e. `python
  _tmp_watch_jobs.py`, not `/app/...`. Relaunched via PowerShell with the relative path and the
  poll ran correctly. (Contrast: `docker compose run ... python workflows/foo.py` already worked
  because `workflows/...` is relative.)

### [2026-07-13] PowerShell 5.1 breaks on BOM-less UTF-8 .ps1 with em-dashes (monsoon_cycle.ps1 parser error)

* **Symptom:** first run of the new `workflows/monsoon_cycle.ps1` died with
  `ParserError: The string is missing the terminator: "` pointing at the last line — a line with
  perfectly balanced quotes.

* **Root Cause:** the file was written as UTF-8 **without BOM**. Windows PowerShell 5.1 reads
  BOM-less scripts as ANSI/cp1252, so each em-dash (`—`, bytes E2 80 94) decodes to `â€`+**0x94 =
  a cp1252 smart double-quote** — a QUOTE character to the parser. Every em-dash inside a string
  toggled string state; the "missing terminator" surfaced at EOF, far from the real cause.

* **Resolution:** script rewritten ASCII-only (em/en-dashes → `-`) AND saved with a UTF-8 BOM
  (either alone fixes it; both = belt and braces). Runs clean.

* **Lesson:** any `.ps1` this repo generates must be ASCII-clean or BOM'd — the prose habit of
  em-dashes is a live syntax hazard in PowerShell 5.1 (this is the shell Task Scheduler invokes,
  regardless of what wrote the file).

---

### [2026-07-13] per_zone_gate followed the LIVE connectivity snapshot, not the standing product — Ramban's live alarm broke silently after VD's radar cycle

* **Symptom:** `live_alarm.py` (insar stage) for Ramban aborted: `per_zone_gate.py` exited with
  "No operational zones found — run run_multistack.py first", even though Ramban's canonical union
  product (12 zones) and per-stack alerts all exist on disk. VD's identical chain ran fine minutes
  earlier.

* **Root Cause:** `per_zone_gate.py` derived its stack list from `run_multistack.connected_stacks()`
  — the **current shared qa_masks network snapshot**, which the session-18 VD radar cycle had
  rewritten to list only the VD stacks (f103/f105) as connected. Ramban's per-stack alert files
  exist for its own three ASC stacks, so the intersection was empty → zero zones. A latent
  multi-AOI failure class: **any consumer of the live connectivity snapshot silently follows the
  last AOI whose QA chain ran.** Ramban's live alarm had actually been broken since 2026-07-10; the
  claim-repositioning dashboard regen was simply the first Ramban run to hit it.

* **Resolution:** new `product_stacks()` in `per_zone_gate.py` — read the stack list off the
  standing union product's own `source_stacks` (in `alerts_operational.json`), falling back to the
  live snapshot only when no product exists yet. VD behavior unchanged (its union stacks == the
  snapshot). Gating now follows the validated product, not the mutable shared state.

* **Lesson:** in a multi-AOI world, the shared connectivity state is a *per-run scratch value*, not
  a site property — anything operating on a site's standing product must take provenance (like
  `source_stacks`) from the product itself. Same failure family as the hardcoded-183 test constant
  (2026-07-12): single-site assumptions hiding in shared state.

* **Follow-up (same day):** the same exposure existed in the four other standing-product consumers —
  `coherence_watch.py`, `watch_triage.py`, `velocity_uncertainty.py`, `polygon_stats.py` (all
  correct for VD today, silently wrong after any other AOI's QA run). Fixed centrally: the helper
  moved to `stacks.py` as the shared `product_stacks(scenario)` (scenario-aware — watch_triage and
  velocity_uncertainty pass their `--footprint`), all five consumers now import it;
  `run_multistack.py` and the m/soil sweeps intentionally keep the live snapshot (they BUILD new
  products). Verified: helper returns each site's own stacks under both configs; both sites'
  triage/uncertainty chains + Ramban's live_alarm run end-to-end in-container.

---

### [2026-07-12] test_plumbing pinned the product count to 183 — stale since the VD pull (caught by the regression run)

* **Symptom:** `tests/test_plumbing.py` in the insar container: 8/10 PASS but
  `test_zip_count_matches_expected` and `test_audit_json_exists_and_parses` FAIL with "expected 183,
  found 235". All cross-consistency tests (zips == product dirs == masked dirs == audit records)
  passed — the *data* was coherent; the *expectation* was stale.

* **Root Cause:** `EXPECTED_PRODUCT_COUNT = 183` was hardcoded in the single-AOI (Ramban SBAS N=3)
  era. The radar library is shared and grows — VD's 49 pairs (§26) and the 2026-07-10 backfill
  (§35) brought it to 235 — so any absolute count is guaranteed to go stale on every AOI pull or
  radar-cadence cycle.

* **Resolution:** expected count now READ FROM `data/qa_masks/_stack_manifest.json` (the
  metadata-derived manifest every download updates — the pipeline's own belief about what exists),
  with a `MIN_PRODUCT_COUNT = 183` floor so genuine data loss still fails. 10/10 PASS in-container.

* **Lesson:** in a multi-AOI world, tests must assert *consistency between artifacts* (or derive
  expectations from the pipeline's own metadata), never absolute counts of a growing shared
  library. Same class as the grandfathered-suffix gotchas: single-site assumptions hide in
  constants.

---

### [2026-07-12] `--config` only exists on 4 scripts — most read config at IMPORT time (near-miss, caught pre-commit)

* **Symptom:** while writing `NEW_AOI_PLAYBOOK.md`, the draft commands used
  `--config config/<slug>.yaml` on `run_multistack.py`, `live_alarm.py`, `fetch_rainfall.py`,
  `rainfall_selectivity_backtest.py` — **none of which accept the flag**. Following the draft
  would have silently run those steps against the *active* (pointer) AOI instead of the intended
  one, with per-AOI suffixes hiding the mistake until outputs landed in the wrong site's dirs.

* **Root Cause:** most workflow scripts call `load_config()` **at module level**
  (`_SFX = load_config().data_suffix` etc.), i.e. before any argparse runs — so a `--config` flag
  cannot ever reach them without restructuring every script. Only the 4 scripts that defer config
  loading into `main()` (submitter, downloader, inverter, network graph) expose the flag. The
  `config.py` docstring's old claim ("each script's `--config`") overstated reality.

* **Resolution:** added an **`INSAR_CONFIG` env var override** in `load_config()` (one change
  covers every script, import-time loads included; explicit `path` still wins):
  `docker compose run --rm -e INSAR_CONFIG=config/<aoi>.yaml insar python ...` — verified in-container.
  Playbook + `aoi_status.py` next-step commands use the correct mechanism per script.

* **Lesson:** grep for the flag before documenting it — a runbook is code and deserves the same
  verification; and module-level config loading is the structural reason per-AOI targeting must be
  an *environment* concern, not an *argument* concern.

---

### [2026-07-10] Passing `--help` to the Phase-1 QA scripts EXECUTES them (no argparse)

* **Symptom:** a "print the usage of the five QA-chain scripts" probe (`python workflows/<script> --help`)
  silently **ran** `feature_engineering.py`, `phase_elevation_audit.py`, `_consolidate_quarantine.py` and
  `apply_connectivity_rescues.py` end-to-end (~15 min of masking + audits + a quarantine-list rewrite and
  10 rescue re-promotions). Only `sbas_network_graph.py` printed usage.

* **Root Cause:** four of the five Phase-1 scripts have **no argparse** — their `main()` takes no CLI
  arguments, so any argument (including `--help`) is ignored and the script just runs.

* **Resolution:** no damage — the scripts are idempotent by house rule (masking skipped all existing
  products; the audit is deterministic on unchanged inputs; the re-applied rescues were the same 10),
  and the intended real run followed minutes later anyway. Verified state by re-running the chain
  properly and checking the cascade reproduced §32 exactly.

* **Lesson:** don't probe these scripts with `--help`; read the docstring instead. This is also a live
  demonstration of WHY the "workflow scripts are idempotent" house rule exists — an accidental
  double-run must be a no-op. If a new workflow script is added, either give it argparse or keep it
  argument-free AND idempotent.

### [2026-07-08] Overpass API returns 406 to PowerShell's hashtable POST body — urlencode it yourself

* **Symptom:** `Invoke-RestMethod -Uri overpass-api.de/api/interpreter -Method Post -Body @{data=$q}`
  → HTTP **406 Not Acceptable** (and a second symptom: the query "succeeding" but returning 1 element).
* **Root cause:** PowerShell's automatic form-encoding of a hashtable body mangles the Overpass QL
  quoted filter `["building"]`, and no User-Agent is sent — Overpass rejects the request. Separately,
  the first bbox (33.005–33.05 N) was too narrow: the AOI's only mapped building cluster (Panchari Gali,
  ~33.057 N) sits just outside it, so even a fixed request undercounted.
* **Fix:** build the body explicitly — `'data=' + [System.Net.WebUtility]::UrlEncode($q)` with
  `-ContentType 'application/x-www-form-urlencoded'` and a `User-Agent` header; widen the bbox to the
  full massif (33.00–33.075 N). 63 buildings returned, cached at
  `data/osm/vaishnodevi_buildings_overpass.json`.
* **Lesson:** for non-trivial POST bodies, never hand PowerShell a hashtable — encode the string
  yourself. And sanity-check a spatial query's *count* against what you already know before trusting it
  (we knew ~62 buildings existed near Area A from the 2026-07-07 session).

### [2026-07-07] Sweep report writer assumed an m=1.0 baseline row — crashed on a refinement sweep

* **Symptom:** `rainfall_selectivity_backtest.py --saturations 0.33,...,0.48` (the VD refinement pass)
  computed all rows, then died in `write_outputs`: f-string over `base[1]['full']` with `base[1] = None`.
* **Root cause:** the report writer looked up the m=1.0 row for its "vs monsoon baseline" sentence and
  assumed it always exists — true for the default saturation list, false for any focused refinement sweep.
* **Fix:** baseline sentence is now conditional ("no m=1.0 baseline in this sweep"). Run-1 artifacts were
  unaffected (the crash happened before any file write).
* **Lesson:** report writers are code too — a "always in the default run" row is an input assumption;
  refinement/partial runs are the norm once a tool is actually used.

### [2026-07-06] The frame106 Jan pair fails DETERMINISTICALLY at ASF — retry-then-park added

* **Symptom:** the resubmitted `VaishnoDevi_Trikuta_ASCENDING_path27_frame106` pair
  (2026-01-13→2026-01-25) FAILED again — both attempts, ~2 h apart, identical pair.
* **Root cause (from the job's processing log):** hyp3-gamma dies in unwrapping —
  `mcf: ERROR: range position of phase reference point outside of image segment: 3384  bounds: 0 3384`.
  The deep-winter pair has so little coherent area that GAMMA's auto-chosen phase reference point falls
  outside the usable segment. Nothing on our side can fix it (no reference-point control in the
  INSAR_GAMMA job API); resubmitting the identical job fails forever.
* **Interaction with the 2026-07-03 dedupe fix:** skipping FAILED jobs in dedupe made re-runs resubmit
  failed pairs — correct for transient failures, but a *deterministic* failure would now be re-bought
  (10 credits) on EVERY idempotent re-run.
* **Fix:** retry-then-park in `fetch_existing_pair_signatures()` — a pair with ONE failure is retried on
  the next run; a pair with ≥2 failures (and no success) is treated as done and logged loudly as
  `PARKED (failed 2× at ASF — deterministic)`. Verified: dry-run now plans 49, skips 49 (48 succeeded +
  1 parked), submits 0.
* **Impact:** none on the product — the pair's frame101 twin was QUARANTINE (R²=0.83) and the whole
  winter-2026 chain is quarantined anyway (§26); the VD product is built from the clean spring stacks.
* **Lesson:** idempotent retry logic needs BOTH halves — retry what might be transient, park what is
  proven deterministic — or a self-healing loop becomes a money-burning loop.

### [2026-07-03b] First cross-AOI run surfaced three latent "only-works-for-Ramban" assumptions

* **Symptom:** `run_multistack.py` under the Vaishno Devi config failed twice in sequence:
  (1) `custom_sbas_inverter.py`: "No solvable reference candidate in AOI — relax --min-pairs";
  (2) after fixing that, `geomechanical_engine.py`: `IndexError` in `np.percentile` on an empty slope
  array, preceded by "DEM (ALOS 12.5 m …) reprojected. Valid pixels: 0/34,608".
* **Root causes (all latent single-AOI assumptions, invisible while only Ramban existed):**
  1. **`--min-pairs` default 8 is unreachable by a 4-pair stack** — the new spring chains have 4
     interferograms, so *no* pixel could ever qualify. Fix: clamp `min_pairs` to the stack's pair
     count (logged when clamped); Ramban's 30–40-pair stacks unaffected.
  2. **The 12.5 m ALOS DEM is a single per-AOI tile** (user-fetched for Ramban, §21) but
     `find_dem_for_stack()` preferred it unconditionally → reprojection onto the Katra grid gave 0
     valid pixels → NaN slope → crash. Fix: zero-coverage check + WARN + fallback to the HyP3
     product DEM (`find_dem_for_stack(stack, prefer_alos=False)`).
  3. **`slope_velocity.py` never adapted to §21's signature change** — it still used
     `find_dem_for_stack`'s return as a bare Path (it became a `(path, is_fine)` tuple on
     2026-06-10). Latent because V_slope was never re-run post-§21. Fix: unpack the tuple AND pass
     `prefer_alos=False` — it needs the *product* `_dem.tif` anyway, since it derives the
     lv_theta/lv_phi look-vector paths from the product directory.
* **Lessons:** (a) a second AOI is a free integration test — defaults tuned on one site's data
  volume (min-pairs, DEM tiles) must degrade gracefully, not die; (b) when a function's return shape
  changes, grep ALL callers — an un-rerun caller stays silently broken; (c) prefer fallback-with-WARN
  over hard preference for per-site optional upgrades.

### [2026-07-03] HyP3 dedupe counted FAILED jobs as "done" — re-runs never resubmitted them

* **Symptom:**
  The Vaishno Devi Phase-1 pull came back 48/49 (one pair FAILED server-side at ASF:
  `ASC_path27_frame106` 2026-01-13→2026-01-25). Re-running `submit_hyp3_jobs.py --submit` — the
  documented idempotent recovery — reported `Skipped (dupes): 49, Submitted: 0`: the missing pair
  was never re-ordered.
* **Root cause:**
  `fetch_existing_pair_signatures()` builds the dedupe set from **every** job under the name prefix,
  regardless of `status_code` — so a FAILED job's granule pair looked "already submitted" forever.
  A latent idempotency gap (same class as the Session-13 scenario-staleness sentinel): invisible until
  the first genuine ASF-side failure, because every earlier job had succeeded.
* **Fix:** skip `status_code == "FAILED"` jobs in the dedupe scan (`submit_hyp3_jobs.py`). Verified:
  the next `--submit` run skipped 48 and resubmitted exactly the 1 failed pair (10 credits).
* **Lesson:** dedupe/skip logic must key on *successful* prior work, not mere existence — "a job was
  submitted" and "the work is done" are different predicates; test recovery paths with at least one
  synthetic failure.

### [2026-06-08] MintPy CLI tools "command not found" under `bash -lc` in the micromamba image

* **Symptom:**
  Chaining the ERA5 run for new stacks, the step
  `docker compose run --rm mintpy bash -lc 'prep_hyp3.py …/*_clip.tif'` failed with
  `bash: line 1: prep_hyp3.py: command not found` — even though `run_mintpy_era5.sh` (run via
  `docker compose run --rm mintpy bash /app/workflows/…`) calls `smallbaselineApp.py`/`save_gdal.py`
  with no path and works fine.
* **Root cause:**
  The `insar-mintpy` image is micromamba-based; its entrypoint **activates** the conda env (puts
  `/opt/conda/bin` on `PATH`) and then execs the command. A **login** shell (`bash -l`) re-sources
  `/etc/profile` + profile.d, which **resets `PATH`** and drops the activated env — so the MintPy
  console scripts vanish. A non-login shell inherits the entrypoint-activated `PATH`.
* **Fix:** use **`bash -c`** (not `bash -lc`) for one-off MintPy commands:
  `docker compose run --rm mintpy bash -c 'prep_hyp3.py /app/data/mintpy/<S>/hyp3/*_clip.tif'`.
  Verified `which prep_hyp3.py` → `/opt/conda/bin/prep_hyp3.py` under `bash -c`. (The proven
  `bash <script.sh>` form already worked because it is also non-login.) Keep `MSYS_NO_PATHCONV=1`
  on Git Bash so `/app/...` isn't mangled.

### [2026-06-02] Validation error of judgement — a wrong inventory DATE inverted a scientific conclusion

* **Symptom:**
  The back-test concluded the documented **Apr–May 2025** NH-44 spring failures were **not** rainfall-
  triggered: on the inventory's dates (27 Apr / 8 May) ERA5-Land, CHIRPS, and half-hourly IMERG all showed
  little/no acute rain, so we wrote "rainfall ruled out; the slopes were merely *primed*." This was
  **published into the committed ledger and the primer** before it was found to be wrong.

* **Root Cause:**
  The landslide inventory used **news-derived, approximate event dates** with no field/authoritative
  verification. The real major April event was the **20 April 2025 Ramban cloudburst** (peer-reviewed —
  Springer *Landslides* 10.1007/s10346-025-02580-1; 3 deaths at Seri Bagna; NH-44 washed out at 5 sites;
  **40 mm/3 hr, ~100 mm/1 hr localized**). Our inventory had **27 Apr** — which was merely the *publication
  date* of a follow-up news article about the 20 Apr disaster — and **omitted 20 April entirely**. Two
  compounding traps: (a) confusing an article's *publication* date with the *event* date; (b) a localized
  cloudburst cell is **diluted by AOI-mean** rainfall (ERA5-Land logged only ~27 mm AOI-mean on 20 Apr), so
  the daily area-average looked benign even though point rainfall was extreme.

* **Resolution:**
  Cross-checked the events against peer-reviewed papers + multiple news sources, corrected the inventory
  (added the 20 Apr cloudburst at Seri Bagna + Kela Morh; flagged the 27 Apr entry low-confidence), and
  re-ran. **The conclusion reversed:** temporal back-test **Caine 0/4 → regional 4/4** with 20 Apr at
  **Δ=0**, and the IMERG sub-daily screen on 20 Apr is a **clear crossing (E=2.25)** — so the deadly event
  *was* acute-rainfall-triggered and the model *does* detect it (the AOI-mean daily products just under-read
  the localized cell; sub-daily/point rain resolves it). Documented openly (append-don't-overwrite): new
  `RESULTS_AND_KPIS.md` **§12g** + ↪corrected pointers on §11/§12d/§12e; corrected README, primer, Context,
  inventory GeoJSON, and the two scripts. **Lessons:** verify event dates/coords against authoritative
  sources (GSI Bhukosh) before trusting a back-test; separate publication-date from event-date; use
  sub-daily/point rain (not AOI-mean) before declaring "no rain"; and revise a documented conclusion openly
  when the evidence changes. (Also in `CLAUDE.md` §5.)

---

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

### [2026-07-13] VD dashboard displayed a stale back-test AUC (0.696/n=41) after the inventory grew to n=46

* **Symptom:** the ledger's current VD operational baseline was AUC 0.707 (n=46 inventory, §42),
  but the live VD dashboard still showed 0.696 — the value from the superseded n=41 inventory.

* **Root Cause:** the dashboard's `load_tier()` reads `backtest_<scenario>_report.json`, a
  one-shot artifact that is NOT regenerated when the inventory grows. The §39 inventory refresh
  updated the ledger (via the soil-sweep baseline) but nobody re-ran `backtest_inventory.py`, so
  the report file — and every dashboard regeneration reading it — silently carried the stale point.

* **Resolution:** `validation_stats.py` (§44) writes `validation_stats_<scenario><sfx>.json`;
  `load_tier()` now prefers it when present, taking the AUC/recall point AND the 95% CI + permutation
  p from the SAME run — the displayed number and its interval can no longer come from different
  inventories. Both sites' dashboards regenerated and verified.

* **Lesson:** any user-facing surface that reads a *scored* artifact inherits that artifact's
  staleness. When a validation input (inventory) changes, re-run the scorers the same session — or
  better, make the surface read the newest-protocol report, as done here.

### [2026-07-13] run_multistack --force / touch triggered a Ramban Phase-2 rerun that FAILS ("No solvable reference candidate")

* **Symptom:** rebuilding Phase-4 alerts at the new kappa (§45) by touching the hazard rasters and
  running `run_multistack.py` made Ramban re-enter **Phase 2 (SBAS inversion)**, which died with
  `No solvable reference candidate in AOI — relax --min-pairs` (exit 1). VD rebuilt fine.

* **Root Cause:** two things. (1) `run_multistack._stale(vel, QUARANTINE_CSV)` had gone true for
  Ramban independently of the kappa work — the quarantine CSV's mtime was newer than the velocity
  rasters, a false-positive staleness (velocity content is correct and kappa-independent). (2) The
  current Ramban reference-pixel search can't re-solve from scratch in this container state, so the
  rerun fails rather than reproducing the existing (good) velocity. The touch of `hazard_class.tif`
  correctly staled Phase 4, but run_multistack re-checks Phase 2/3 for the same stack in one pass.

* **Resolution:** did NOT let Phase 2 rerun. Drove Phase 4 + union DIRECTLY at the new kappa via a
  throwaway script calling `agentic_orchestrator.run_scenario(stack, sc, ...)` for operational/watch
  then `run_multistack.write_union_alerts(stacks)` — reads the unchanged FS/TWI rasters + config
  kappa, never touches Phase 2/3. The failed SBAS attempt wrote nothing (it dies before output), so
  the standing Ramban velocity is intact.

* **Lesson:** to rebuild ONLY Phase 4 (e.g. after a config-only change like kappa that the mtime
  staleness can't see), call the orchestrator + `write_union_alerts` directly rather than
  `run_multistack --force`/touch — the latter also re-checks Phase 2/3 and can trip a fragile
  reference-pixel re-solve. A config-change-aware staleness signal would be the real fix.

### [2026-07-13] kappa (§45) shipped with two silent non-consumers: hazard_timeline and watch_triage ignored the TWI layer

* **Symptom:** none visible — found by a deliberate deep-verification grep for every site that
  interpolates FS_real or computes m* manually. The season timeline (`agentic_orchestrator.py
  hazard_timeline`, line ~525) still built each day's FS as `(1-m)*FS_dry + m*FS_sat` with the
  scalar m, and `watch_triage.py` ranked by the intrinsic m* — both silently diverging from the
  kappa=0.06 standing product and the per-zone gate's m*_eff firing order.

* **Root Cause:** §45's first cut edited the FS_real construction in ONE consumer (the
  MeteorologicalTrigger) and the m* shift in ONE consumer (per_zone_gate), but the "FS at wetness
  m" math existed in four places. Copy-paste physics: each new layer must be hand-carried to every
  copy, and two copies were missed.

* **Resolution:** NEW `workflows/fs_real.py` — single source of truth for `m_field` /
  `fs_field(fs_dry, fs_sat, m, twi, kappa)` / `critical_saturation` / `effective_mstar`. All four
  consumers (MeteorologicalTrigger, hazard_timeline, per_zone_gate, watch_triage) now import it;
  per_zone_gate re-exports `critical_saturation` for backward compatibility. Verified by a 22-check
  battery on both sites: config load + default gate, zero-sum/clip quantification (operational m
  exact; watch m: VD −0.0015 mean shift / 2.9% clipped, Ramban −0.0009 / 1.7%), kappa=0 bitwise
  identity on all 5 stacks, fs_field cluster counts == standing per-stack alert counts, m*_eff
  FS-crossing roots to ±2e-3, double-build determinism. Triage + VD route exposure regenerated
  (CORE 0.80 km unchanged; WATCH 7.92→7.84 km).

* **Lesson:** when adding a physics layer, FIRST grep for every consumer of the quantity being
  changed and centralize before editing — the §45 review's "one point change" was only true of the
  standing product path. Any future layer (van Genuchten suction is next) goes into fs_real.py, and
  its consumers stay import-only.

### [2026-07-13] Third kappa non-consumer: soil_sensitivity_sweep rebuilt alerts at kappa=0 through a default argument

* **Symptom:** none visible until the §42 sweep would next run — found by reading the tool before
  re-running it on the kappa=0.06 product. `soil_sensitivity_sweep.py` calls
  `rainfall_selectivity_backtest.build_stack_alerts(s, m_op, scen)` whose `kappa` parameter
  DEFAULTED to 0.0 and was written into the scenario cfg explicitly — so every soil combo (and its
  baseline sanity gate) would have been built at kappa=0, silently mismatching the standing
  product (the gate would flag 21 vs 14 zones at VD, but only at run time).

* **Root Cause:** same bug class as the fs_real centralization entry above, one call level deeper:
  the physics layer was threaded as an OPTIONAL ARGUMENT whose default ("0.0") encoded a physics
  choice instead of "inherit the site's adopted value". Every caller that didn't know about the
  new layer silently opted out of it.

* **Resolution:** `build_stack_alerts` now takes `kappa=None` / `suction=None` meaning "the site
  config's adopted value" — the cfg key is only set when a sweep explicitly overrides (0.0 remains
  a valid explicit override). The soil sweep inherits the standing physics with no change to its
  own code; its baseline gate then reproduces the canonical product exactly (VD: 14 zones,
  AUC 0.757, verified 2026-07-13; FS rasters checksum-restored).

* **Lesson:** a physics layer must never be an optional argument with a value-default. Defaults
  encode "no opinion", so they must mean "whatever the site config says" (None-sentinel), not a
  particular physics setting. When adding a layer, audit every CALLER of the build path, not just
  every copy of the math.

---

### [2026-07-15] Docker Desktop killed abruptly leaves stale unix-socket files that CRASH the next start (and a GUI-only kill lets the VM restart itself)

* **Symptom:** three intertwined failure modes found while hardening the monsoon cycle. (1) After
  `Stop-Process 'Docker Desktop'`, the engine reappeared minutes later — `com.docker.backend`
  survives a GUI-only kill and can restart the WSL2 VM. (2) The FIRST `Docker Desktop.exe` launch
  right after an abrupt teardown dies silently (observed twice; the monsoon cycle's 5-min wait
  expired and it toasted "cycle SKIPPED"); an immediate relaunch succeeds in ~20 s. (3) Worst case:
  Docker Desktop showed "unexpected error … initializing Inference manager: remove
  C:/Users/varun/AppData/Local/Docker/run/dockerInference: The file cannot be accessed by the
  system" and refused to start AT ALL — stale unix-socket **reparse points** in
  `%LOCALAPPDATA%\Docker\run\` cannot be deleted by `del`, `Remove-Item`, or `[IO.File]::Delete`.

* **Root Cause:** force-killing Docker's processes skips its socket/teardown cleanup. Unix-socket
  files on Windows are reparse points that normal file APIs refuse to touch, so Docker's own
  startup `remove()` fails too and it aborts.

* **Resolution:** (1) `monsoon_cycle.ps1` shutdown now kills `Docker Desktop` + `com.docker.backend`
  + `com.docker.build` before `wsl -t docker-desktop`, then VERIFIES `docker info` fails and logs a
  warning otherwise. (2) The start wait-loop relaunches once at the 150 s mark if the GUI process
  vanished. (3) For the stale-socket crash: **rename the whole `run` dir**
  (`run` → `run_stale_<date>`) — Docker recreates it clean on next start; the renamed dir's socket
  files stay undeletable but are 0 bytes and inert.

* **Lesson:** never assume killing a GUI killed the service behind it — enumerate the process tree.
  And when Windows refuses to delete a file "the system cannot access", stop fighting the file and
  rename its PARENT directory; the recreating app neither knows nor cares.

* **ROOT FIX (2026-07-16, supersedes the process-kill approach entirely):** the crash is
  DETERMINISTIC — every force-kill strands the socket and every next start hits the error dialog
  (confirmed by the user's screenshot; it also explains the "silent death" starts — the app was
  sitting on a dialog that headless polling can't see). Docker Desktop 4.37+ ships a CLI:
  **`docker desktop stop`** (clean teardown, no stranded sockets) and **`docker desktop start`**
  (headless start). `monsoon_cycle.ps1` now uses ONLY these; `Stop-Process`/`Start-Process` on
  Docker are banned in this repo. If a brick already happened: quit the dialog, rename
  `%LOCALAPPDATA%\Docker\run`, then `docker desktop start`.

---

### [2026-07-15] Docker bind mounts silently do NOT resolve NTFS junctions — container saw an empty project subdir

* **Symptom:** after relocating the raw-zip store (`data\raw_zips` → NTFS junction →
  `C:\InSAR_data\raw_zips`), everything worked natively (reads, writes, git, the plumbing suite) —
  but `docker compose run insar python -c "Path('/app/data/raw_zips').exists()"` returned **False**:
  inside the container the junction is not followed, the path simply doesn't exist. Any
  containerized Phase-1 `--download`/`--extract` or `prep_mintpy` zip-fallback would have failed.
  Found only because the junction test battery included a container-side check.

* **Root Cause:** Docker Desktop's Windows file-sharing (gRPC-FUSE/virtiofs) serves directory
  entries but does not traverse NTFS reparse points that lead outside the shared subtree being
  bind-mounted; the junction shows up as nothing at all in the container.

* **Resolution:** explicit nested bind in `docker-compose.yml` for BOTH services —
  `C:/InSAR_data/raw_zips:/app/data/raw_zips` mounts the real folder over the junction's path in
  the container. Verified: both images see the dir, and a container-side write appears at
  `C:\InSAR_data\raw_zips` on the host.

* **Lesson:** an NTFS junction is a host-side illusion — every non-native consumer (containers, WSL,
  some backup tools) must be tested against it explicitly. When a junction sits inside a
  bind-mounted tree, add a nested bind for the junction target; the container path then works no
  matter what the host-side link does.

### [2026-07-17] Results hub missed the real live dashboards (glob one level too shallow)

* **Symptom:** the new control panel's results hub listed only `data/alerts*/` top-level HTML
  (old scenario dashboards) — the actual per-AOI LIVE operational dashboards never appeared.

* **Root Cause:** `operational_alarm.py` writes its dashboard one level deeper, under
  `alerts<sfx>/mosaic_asc/operational_alarm_dashboard_*.html`; the hub's `glob("*.html")` on the
  alerts dir can't see subdirectories. Found only when a REAL refresh-cycle run printed the
  output path into the panel's own log.

* **Resolution:** hub now globs `alerts<sfx>/mosaic_asc/operational_alarm_dashboard*.html` and
  lists it FIRST ("★ Live operational alarm dashboard"); regression test added
  (`test_live_operational_dashboard_listed_first_when_present`).

* **Lesson:** when building a UI over existing artifacts, derive the artifact list from what the
  producers WRITE (read their output paths/logs), not from what a directory listing happens to
  show — and always run the real producer once before declaring the consumer done.

### [2026-07-17] Restructure landmines: path-anchored .gitignore rules invert silently on `git mv`

* **Symptom (pre-empted, not hit):** moving `Research/` → `docs/` would have (a) broken the
  `!Research/*_Watchlist/*.kml` re-include (future KMLs silently ignored) and (b) moved the
  untracked `Research/Archive/*` stash OUT of its ignore rule — `git add -A` would then have
  committed old LLM-synthesis research notes that were deliberately excluded from the repo.

* **Root Cause:** `.gitignore` rules that embed directory paths are coupled to the tree layout;
  a restructure changes rule semantics without touching the rules.

* **Resolution:** grepped `.gitignore` for every path-anchored rule BEFORE moving; updated both
  (`!docs/briefs/*_Watchlist/*.kml`, `docs/archive/local/*`) in the same change; verified with
  `git check-ignore` (probe files) that re-includes work and the local archive stays ignored.

* **Lesson:** a repo restructure is also a `.gitignore` migration. Before any `git mv`, grep the
  ignore file for the old paths, and verify the NEW layout with `git check-ignore` probes both
  ways (tracked stays tracked, excluded stays excluded).

### [2026-07-17] Verification grep's own exclusion filter hid a whole directory of stale refs

* **Symptom:** a repo-wide sweep for stale `Research/` references came back clean, but files
  under `docs/` still contained stale paths (runnable commands in briefs, the context doc's
  primer link).

* **Root Cause:** the sweep piped `grep -rn` through `grep -v 'docs/guides|docs/briefs|…'` to
  drop already-correct NEW paths — but `grep -rn` prefixes every hit with its file path, so ANY
  hit inside `docs/` matched the exclusion by virtue of its filename prefix and was dropped.

* **Resolution:** re-ran the docs/ sweep separately with the path prefix stripped (`sed
  's|^docs/||'`) before filtering; found and fixed 8 more stale references.

* **Lesson:** when filtering `grep -rn` output, remember the match line CONTAINS the file path —
  exclusion patterns meant for line content will also match paths. Strip or split the path field
  first, or use `--include`/`--exclude-dir` instead of post-filtering.

### [2026-07-18] New committable data files silently swallowed by the data/inventory/* blanket ignore

* **Symptom:** the two new curated historical-events JSONs (`data/inventory/*_historical_events.json`)
  did not appear in `git status` at all — they would have shipped as local-only files, making the
  dashboard's Past-events record non-robust (same failure class as headline numbers living only in
  git-ignored journals).

* **Root Cause:** `.gitignore` ignores `data/inventory/*` wholesale and re-includes ONLY the two
  back-test inventory geojsons by exact name; any new file in that directory is ignored by default.

* **Resolution:** added explicit `!data/inventory/*_historical_events.json` re-includes (both
  sites), verified with `git check-ignore` + `git status`.

* **Lesson:** third instance of the gitignore bug class (see 2026-07-17 entries): whenever a NEW
  file is meant to be committed from under `data/`, run `git check-ignore -v <path>` immediately
  after creating it — the blanket rules win silently.

### [2026-07-18] Test counted a phrase in prose, not the marker it meant

* **Symptom:** `test_hist_panel_html` failed: `html.count("pending review")` exceeded the number
  of review-flagged events.

* **Root Cause:** the panel's intro sentence legitimately contains the words "pending review", so
  counting the raw phrase counted prose + badges together.

* **Resolution:** count the exact structural badge marker (`>pending review</span>`) instead.

* **Lesson:** when asserting counts against rendered HTML, count unambiguous structural markers,
  never phrases that can also occur in prose.

### [2026-07-18] Browser preview pane pinned to the first file:// snapshot — JS checks ran against a stale page

* **Symptom:** after `navigate` to the Ramban dashboard file, in-page JS still reported the
  Vaishno Devi page (title unchanged) — even with a forced reload.

* **Root Cause:** files outside the preview's project root render as one-shot static snapshots;
  navigating the pane to a different file:// path does not actually load it.

* **Resolution:** asserted `document.title` before trusting any in-page check (which is how the
  staleness was caught), then verified the second dashboard by parsing its HTML on disk instead.

* **Lesson:** when driving the preview browser across multiple file:// artifacts, verify document
  identity (title) first; fall back to on-disk HTML parsing — the rendered behavior is identical
  generated code, so one live page + N parsed pages is sufficient coverage.

### [2026-07-18] Undated article URL misattributed to the wrong year's event cluster

* **Symptom:** the curated Digdol–Khooni Nallah row cited an undated Greater Kashmir "SSP
  traffic" article as a source for a supposed 27 Apr 2025 slide (graded LOW, duplicate-suspect).
  User review + a fresh search showed the row's event actually happened 7 Apr 2026 — and that
  same undated URL appears in the 2026 event's coverage cluster, not 2025's.

* **Root Cause:** the article URL carries no date; it was attributed by topical similarity to the
  2025 cluster during curation. An undated source can silently attach to whichever event you are
  currently researching.

* **Resolution:** row resolved to 2026-04-07 (HIGH — four independently dated 2026 outlets),
  correction recorded in the row's confidence_reason + the inventory feature's date_correction;
  the Kashmir Vision 27 Apr 2025 piece reclassified as follow-up coverage of the 20 Apr 2025
  cloudburst (§12g). Ledger §52.

* **Lesson:** extension of the §12g/§36 date rules — an UNDATED source URL must never anchor an
  event's date; only sources with their own visible date (URL path or byline) can. The
  LOW/pending-review grading did exactly its job here: the doubtful row was quarantined until
  reviewed, never presented as settled.

### [2026-07-18] Staleness-guard escalation branch left the previous tier's styling behind

* **Symptom:** while exercising the new banner staleness guard's tiers by re-running the page's
  own script with rewound as-of dates, returning to the normal (<=8 d) tier kept the previous
  tier's red background — only the text reset.

* **Root Cause:** the script set `el.style.background` in the amber/red branches but the normal
  branch never touched it. Unreachable in production (the script runs once per page load with a
  fixed as-of date), but a latent trap for any future re-run of the logic.

* **Resolution:** normal branch now resets `el.style.background = ''` (falls back to the CSS
  class). One-line fix, re-verified.

* **Lesson:** verify browser escalation logic by re-evaluating the PAGE'S OWN embedded script
  against synthetic inputs, not a re-implementation of it — that is exactly how this
  branch-asymmetry surfaced. And in any state-styling if/else, every branch must fully specify
  the state it claims, not just the delta from the branch you expect to precede it.

### [2026-07-18] User saw a red staleness pill with "normal" text — stale test-tab DOM, not the artifact

* **Symptom:** the user's screenshot showed the new staleness pill with the >14-day red
  background but the <=8-day "Normal for this system" text — an impossible combination for a
  fresh page load.

* **Root Cause:** the screenshot was of the in-app preview tab used for tier testing. The §53
  escalation probe had rewound the page's as-of date and re-run the page's own (pre-fix) script,
  which left the red background behind when the real date was restored — the exact
  branch-asymmetry bug found and fixed that round. The mutated DOM stayed visible in the open
  tab; the regenerated file on disk was always correct.

* **Resolution:** force-reloaded the page and screenshot-confirmed the correct light pill; no
  code change needed (the underlying style-reset bug was already fixed in the same session).

* **Lesson:** after mutating a live page during in-browser testing, reload it before leaving it
  on screen — a test-mutated DOM left visible reads as a product bug to anyone who glances at
  it. When a report contradicts the code, first ask "which surface is being looked at?" before
  hunting the logic.

### [2026-07-18] Sentinel-1 unit whitelist would have silently starved the pipeline forever

* **Symptom:** "July S1 passes still not at ASF" persisted for weeks (§35 → §43 → today) and
  was tracked as an upstream delay. Today's check showed the truth: Sentinel-1A ENDED
  OPERATIONS on 29 Jun 2026 (constellation handover), Sentinel-1D is already acquiring our
  exact paths (CDSE: 25/30 Jun, 7/12 Jul; ASF has 25 Jun) — and our catalog query
  `platform=[SENTINEL1A, SENTINEL1B]` could never have returned an S1C/S1D scene. Had the
  filter stayed, the pipeline would have reported "no new data" indefinitely while data flowed.

* **Root Cause:** a satellite-unit whitelist written in the two-unit era (2025) plus treating
  "no new scenes" as someone else's delay instead of investigating which layer was empty
  (acquisition vs archive vs OUR QUERY).

* **Resolution:** `submit_hyp3_jobs.py` now queries `PLATFORM.SENTINEL1` (all units), with a
  comment carrying the handover fact; verified live (the all-units query returns the S1D
  scenes the A/B query missed). Ledger §56; plan doc Tier 0.

* **Lesson:** never whitelist satellite units — query at constellation level and let
  downstream QA reject what doesn't pair. And when a data feed "goes quiet", binary-search the
  layers (source catalog → mirror → your own filter) before attributing delay upstream: two of
  the three layers had data the whole time.

### [2026-07-18] D8 router sent edge cells to out-of-bounds indices (infinite drop to a -inf pad)

* **Symptom:** first run of flow_routing_probe.py crashed with IndexError: a flow target index
  beyond the array.

* **Root Cause:** neighbours outside the frame were padded with -inf elevation; drop = z-(-inf)
  = +inf made the off-grid cell the "steepest descent" — and its flat index was out of bounds.

* **Resolution:** drop is defined only where BOTH cells are finite (else -inf), so edge and
  nodata cells become off-map sinks; a synthetic-valley unit test now pins the behaviour
  (including a NaN-hole DEM).

* **Lesson:** padding with sentinel values changes the ARGMAX, not just the values — any
  "pick the best neighbour" kernel must exclude sentinel cells from candidacy explicitly, and
  edge behaviour deserves its own test case.

### [2026-07-25] The committed temporal-skill table had silently gone stale — a hand-typed derived artifact

* **Symptom:** `data/inventory/temporal_skill_table.csv` still held 6 events while the §62
  Gangroo–Ramsu strike (22 Jul 2026, 2 deaths) had been verified, ledgered, and folded into
  `ramban_historical_events.json` the day before. Its schema test passed the whole time.

* **Root Cause:** the table was **hand-maintained** even though every field in it is derivable
  from records already on disk (the IMERG daily-E CSVs + the daily alarm calendars). A schema
  test can only check the rows that exist; nothing could notice a row that was never typed.

* **Resolution:** `imerg_calibration.py` now GENERATES the table (`temporal_skill_rows` +
  `write_temporal_skill_table`) from the same `EVENTS` list the rest of the report uses, so
  adding an event to one place updates both. Ledger §63.

* **Lesson:** if every column of a committed artifact is derivable, generate it — a hand-typed
  derived file drifts silently, and a schema test guards the shape, never the completeness.
  The test that would have caught this is "the artifact regenerates byte-identical", which is
  only possible once there is a generator.

### [2026-07-25] A windowed skill metric manufactured a "catch" past the end of the record

* **Symptom:** scoring the validated daily arm against the 22 Jul 2026 event returned
  *caught* at the ±10-day window — but that arm's 2026 season record **ends 19 Jul** (ERA5-Land
  publication latency), so it had no data on the event day at all.

* **Root Cause:** the ±W attribution window was applied without reference to the record's own
  span. A flagged day near the end of the series sits within W days of an event that occurs
  *after* the series stops, so the metric credited a verdict the arm never rendered.

* **Resolution:** `false_alarm_profile` restricts the event tally to events inside
  `[first_day, last_day]` of the record and counts the rest as `n_events_outside_record` —
  reported as *pending*, neither catch nor miss (matching §62's framing of the latency case).
  A dedicated hermetic test pins both directions.

* **Lesson:** any ±window skill metric must be clipped to the record's edges, or it invents
  skill exactly where the data ends — the most tempting place to overclaim, because a
  latency-blind arm looks identical to a silent one.

### [2026-07-25] "Nearest ALERT" reported an unrelated storm 85 days away as a lead time

* **Symptom:** the new `burst_alert_lead_days` column read **85** for the 7 Apr 2026 Digdol
  event and **16** for 8 May 2025 — presented as if the gate had warned about them.

* **Root Cause:** the statistic was an unbounded nearest-neighbour search over the whole
  season, so with no nearby ALERT it silently returned the closest one anywhere in the record.

* **Resolution:** bounded to the attribution horizon (±10 d, `max(FA_WINDOWS_D)`); beyond it
  the column is blank because the nearest ALERT is a different storm, not a lead time.

* **Lesson:** a nearest-neighbour statistic without a bound always returns *something* — the
  bound is what turns it into a claim. Same class of trap as an unclipped window (above).

### [2026-07-25] Grandfathered filename rule nearly merged two seasons into one profile

* **Symptom:** the first `_daily_arm_rows` returned 324 rows for Ramban 2026 (110 expected).

* **Root Cause:** Ramban's 2025 alarm calendar keeps the grandfathered *unsuffixed* name
  (`operational_alarm_calendar.csv`) while 2026 is `..._2026.csv`, so both are candidate paths
  for the site and the loader concatenated them. The per-date lookup it was refactored from
  never noticed, because it stopped at the first matching date.

* **Resolution:** the loader filters rows to the requested season's year.

* **Lesson:** the project's grandfathered-suffix rule (ramban unsuffixed) is safe for a keyed
  lookup and unsafe for a bulk read — when refactoring "find one" into "load all", re-check
  every path-resolution rule that the single-item version happened to tolerate.

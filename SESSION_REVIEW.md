# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It is a living
dashboard, **overwritten at the end of each working session** to always reflect
the *current* state — not a historical log. (For history, see
`session_journey.md`.)

_Last updated: 2026-06-02 (Session 10, branch `mvp-expansion`). **Current state:** the full MVP
(radar → audited data → SBAS velocity → physics hazard → explainable rainfall-driven warning,
plus a 3-D UI) is COMPLETE, Dockerized, point-anywhere, and multi-stack. **Session 10** did the
gauge-rainfall step (Area 7 #3): **(1) Regional Himalayan I–D curve** — `rainfall_id_threshold.py` is
now `--threshold {caine1980|nwhimalaya}`; the researched regional curve **I = 2.9993·D⁻⁰·⁴¹⁵²** (J.
Earth Syst. Sci. 2025 134:97; AOI cross-check Shah et al. 2024 Nat. Hazards 120, NH-44 ~14.35 mm/day)
is ~5× more sensitive than global Caine (~19 vs ~103 mm 1-day). **On the SAME ERA5-Land data the
regional curve flips the temporal back-test 0/2 → 2/2** (27 Apr Δ0; 8 May Δ5) — so the Apr–May miss was
**substantially a threshold problem**, confirmed on unchanged data. **Loud caveat:** it fires **112/214
days** (sensitive, not selective) → still needs CHIRPS precision for the *acute* 8 May burst + a
percentile/antecedent filter. Curve coefficients + units now **VERIFIED** (2026-06-02) vs the JESS-2025
regional family + numeric cross-checks; default kept at Caine only to avoid re-baselining the `[MOCK]` KPIs.
**(2) GEE CHIRPS fetch — BUILT *and RAN*** (`workflows/fetch_chirps.py`; auth done 2026-06-02, project
`tutorial-project-472812` in git-ignored `.env`; ran natively, no image rebuild needed). **The gauge
hypothesis is REFUTED:** CHIRPS is *drier* than ERA5-Land here (998 vs 1,350 mm), and on the event days
**27 Apr 0.0 mm / 8 May 4.2 mm** (vs ERA5 0.1 / 9.3) — event rarity E even *lower* (0.70 / 0.57). **Two
independent ~5–9 km products agree there was little grid-scale acute rain on the documented spring dates**
→ the Apr–May miss is NOT a wrong-rainfall-product problem. **(3) Specificity-filter prototype**
(`rainfall_specificity.py`): sweeps stringency k + antecedent dials; on both ERA5-Land and CHIRPS **no
selective (<20% season) setting catches both events**. **(4) GPM IMERG sub-daily test**
(`fetch_gpm_imerg.py`, half-hourly): **27 Apr E=0.0, 8 May E=1.09 (marginal)**, 26 Aug control E≈12 (method
validated) → **rainfall is now CONCLUSIVELY RULED OUT**: three independent products (daily reanalysis, daily
gauge-blend, half-hourly satellite) agree there was no acute spring triggering rain. Also: regional curve
coefficients **VERIFIED** (literature triangulation + numeric reproduction). **(5) Spring conditioning**
(`spring_conditioning.py`, EECU-free): per-elevation freeze-thaw (onset ~2500 m; valley/event level ~1540 m =
**0** days → freeze-thaw works the upper source slopes) + chronic saturation (event-day wetness 33%/20% of
season peak despite ~0 acute rain) → spring slopes were **PRIMED, not storm-triggered** (explains
susceptibility, not the discrete date). **Next:** the remaining spring leads are **non-rainfall** → **GSI
Bhukosh** for verified dates/coords + scored back-test; NHAI-construction angle. KPIs in committed
`RESULTS_AND_KPIS.md` §12–§12f (+ §10–§11). Detail: §2 / §5._

---

## 1. Read these documents, in this order

| # | Document | Why read it | How much |
|---|---|---|---|
| 1 | **SESSION_REVIEW.md** (this file) | Current state, open questions, next step | All — it's short |
| 2 | **`RESULTS_AND_KPIS.md`** | **Committed** ledger of every headline KPI/finding (mock + real), with provenance | Skim the tables |
| 3 | `README.md` | Project overview, repo layout, full-pipeline run guide, known env issues | Skim |
| 4 | `milestone.md` | Plain-language story of progress (Milestones 1–14) | Top to current |
| 5 | `session_journey.md` | Detailed decisions & reasoning; **read the top (newest) entry** | Newest 1–2 entries |
| 6 | `error_history_log.md` | Every bug + root cause + fix — **check before debugging anything** | Scan headings |
| 7 | `docker/README.md` | How to build/run the pipeline in the Linux container | As needed |
| 8 | `Research/Foundations - Physics and Maths Primer.md` | The science (Phases 1–4 + forecasting/rainfall/validation) | As needed |
| 9 | `InSAR_hazard_forecasting_Context.md` | Original vision / full expansion roadmap | Reference |

**Also re-read `CLAUDE.md`** — behavioural rules + the post-phase documentation ritual (§5).

> **Committed vs local-only (important):** `CLAUDE.md`, `SESSION_REVIEW.md`, `session_journey.md`,
> and `milestone.md` are **git-ignored** (local-only working notes), as is most of `data/`. The
> **committed**, version-controlled docs are `README.md`, `RESULTS_AND_KPIS.md`,
> `error_history_log.md`, the Foundations primer, and `InSAR_hazard_forecasting_Context.md` — so a
> fresh *clone* has the KPIs (ledger) + science + roadmap but NOT these journals. The user commits
> manually; uncommitted work from this session is listed in §7.

---

## 2. Where we are right now

🎉 **The full end-to-end MVP is COMPLETE and demonstrable, including a 3-D UI**, and
as of Session 8 it now **runs in a reproducible Linux Docker container**.

- **Phase 1 (clean data): COMPLETE** → `data/qa_masks/`
- **Phase 2 (SBAS velocity): 3 ASC stacks inverted** (multi-stack, custom inverter);
  2 DESC (frame479/484) pending MintPy SVD/period-split → `data/velocity/`
- **Phase 3 (geomechanical engine): per-stack for the 3 ASC stacks** → `data/hazard/`
- **Phase 4A (agentic warning): per-stack + AOI union** → `data/alerts/<stack>/`, `data/alerts/mosaic_asc/`
- **Phase 4B (interactive 3-D explorer): COMPLETE** (frame106) → `data/alerts/dashboard_3d.html`
- **Infra 0a (Docker containerization): COMPLETE & VERIFIED** → `docker/`, `docker-compose.yml` (committed `99552db`)
- **Infra 0b (AOI parameterization): COMPLETE** → `config.yaml` + `workflows/config.py`
  (parts 1-2, `35c5b6e`), gated auto-rescue + coverage-first (part 3, `97f9a2d` + later
  commit), and **multi-stack driver + union mosaic** (part 4, `workflows/run_multistack.py`,
  `556c396`). All 3 ASC stacks run end-to-end → union hazard + union alerts.
- **MintPy migration: STEPS 1-4 DONE** — image `insar-mintpy:latest` (pinned
  **py3.11 + numpy<2**, mintpy 1.6.3 / pyaps3 0.3.7 / cdsapi 0.7.7). frame106 run
  end-to-end via `workflows/prep_mintpy.py` + `smallbaselineApp.py` (in a `/tmp` work
  dir — bind mount can't `utime`). **Step 3 (ERA5 tropo ON):** `troposphericDelay.method
  = pyaps`; pyaps3 smoke-tested vs the new CDS endpoint first (`workflows/smoke_pyaps3.py`),
  then the full run fetched 15 ERA5 gribs → dry+wet delay subtracted →
  `mintpy_out/velocity_mintpy_era5.tif` (+ `temporalCoherence_mintpy.tif`; no-tropo
  `velocity_mintpy.tif` kept for before/after). **Fair re-validation**
  (`workflows/crossval_mintpy.py`, MintPy coh≥0.7 masked): r **+0.28 → +0.55** (same
  14,045-px set), **+0.587** raw on the masked common set; MintPy velocity std **39 → 21
  mm/yr** (now below custom 31). Two independent SBAS engines now corroborate at
  r≈0.55–0.59. **Step 4 (DESC stacks): both EVALUATED and DUMPED** (user-steered, quality-
  first). `prep_mintpy.py` gained `grid_from_products()` (osgeo-only AOI+buffer grid for
  stacks with no custom raster) → both DESC on the same 309×353 grid. `run_mintpy_era5.sh
  <stack>` (generalised; `NET_START_DATE/END_DATE` period-split env vars). **frame484** =
  decorrelated: no pixel >0.85 avg-spatial-coh anywhere, forcing ref→0.6 gives only
  858/109,077 px (0.8%) → unusable, never run to velocity. **frame479** inverts 99.3% but
  velocity is physically implausible: full SVD-bridged network std **57 mm/yr** (9,016 px
  >100); period-split to the connected monsoon island (Jun24–Sep16) is WORSE, std **137**
  (30,378 px >100) — short-baseline noise amplification + monsoon decorrelation, NOT a
  disconnect artifact. Both fail the bar (ASC: std 21–30, ~0 implausible px). `DUMPED.md`
  marker in each `data/mintpy/DESC_*/`. **ASC/DESC vertical+EW decomposition DEFERRED**
  (needs better DESC data: longer connected series / PS / phase-linking).
- **Forecasting + validation layer (this session — all on the 3 ASC stacks):**
  **inverse-velocity TTF** (`inverse_velocity_ttf.py`; 0 accelerating, all steady →
  `data/alerts/<stack>/ttf_report.*`); **real rainfall + Caine ID thresholds**
  (`fetch_rainfall.py` ERA5-Land via CDS + `rainfall_id_threshold.py`; 1 trigger = 26 Aug →
  `data/rainfall/`) **coupled** into the orchestrator (`agentic_orchestrator.py --date` /
  `--rainfall-timeline`; `FS_real=(1−m)·FS_dry+m·FS_saturated`; mock scenarios preserved →
  `data/alerts/hazard_timeline.*`); **back-test** vs a documented inventory
  (`backtest_inventory.py` → `data/inventory/`; spatial 8/9 OK, temporal MISS). KPIs:
  `RESULTS_AND_KPIS.md` §6–§9.
- **Session 9 — the two ★★★ physics borrows (Area 7 #1–2):**
  **(1) V_slope** (`workflows/slope_velocity.py`): LOS velocity projected onto downslope
  (`V_slope = V_LOS/(d·l)`; `l` from HyP3 `lv_theta`/`lv_phi`, `d` from DEM slope+aspect). Per ASC
  stack → `data/velocity/*_v_slope.tif`, `*_los_sensitivity.tif`, `*_v_slope_report.{json,md}`.
  Blind-spot 24–42%, median |C| 0.40–0.61, creep amplified ×1.4–1.6. **Wired in opt-in:**
  `agentic_orchestrator.py --use-vslope` + `inverse_velocity_ttf.py --use-vslope` detect creep from
  `-v_slope` (off by default → LOS baselines preserved). frame106 monsoon: 222 (LOS) → **236** (V_slope).
  **(2) Snowmelt + freeze-thaw + April window** (`fetch_rainfall.py` + `rainfall_id_threshold.py`):
  window → **2025-04-01**; trigger screens **water = rain+snowmelt**; freeze-thaw flag (Tmin<0<Tmax);
  wetness/API water-based (kept `rain_mm`/`wetness_0_1` cols → orchestrator/back-test unchanged).
  Honest negative: snowmelt 59 mm, 0 new acute trigger, 0 freeze-thaw days (AOI-mean), back-test
  still 0/2 temporal → diagnosis sharpened to ERA5-Land orographic under-count. KPIs:
  `RESULTS_AND_KPIS.md` §10–§11. **GRIB gotcha fixed:** use `validityDate`/`validityTime`, not
  pygrib `.validDate` (analysis date) — see error_history_log 2026-06-01.

**Active branch: `mvp-expansion`** — all post-MVP work happens here, not `master`.

**Data state this session:** the gated rescues were adopted (quarantine CSV now
**103/26/54**) and all 3 ASC stacks were inverted via `run_multistack.py`. The
rescue gate now uses **coverage-first bridge selection** (see §4 Part 3), which
restored frame106 to its full coverage (14,045 px, 5DC6 bridge) — the root demo was
**refreshed** to current frame106 (**29/222**, no longer stale). Outputs: per-stack
in `data/alerts/<stack>/`; **AOI union** in `data/alerts/mosaic_asc/` (+
`data/mosaic/MOSAIC_ASC_hazard_class.tif`) → mosaic HIGH=**5,268** (291 confirmed
by ≥2 looks); monsoon union zones=**405** (26 multi-look-confirmed).

**One-time setup for EXISTING Ramban data:** the stack manifest is git-ignored
(under `data/`); seed it once with `python workflows/stacks.py --seed-legacy`.
New AOIs get it automatically from `download_hyp3_products.py`. Run the whole
multi-stack pipeline with `python workflows/run_multistack.py`.

**The demos:** open `data/alerts/dashboard_3d.html` (interactive 3-D) or
`dashboard_monsoon.html` (2-D). Cascade: **dry → 29 alert zones; monsoon → 222.**

**The container:** `docker compose build` then e.g.
`docker compose run --rm insar python workflows/agentic_orchestrator.py`. The image
carries the env only; the project (code + `data/`) is bind-mounted at `/app`.

---

## 3. CRITICAL environment gotcha (read before running anything)

**Two ways to run, pick one — don't mix:**

- **In Docker (preferred, Session 8+):** `docker compose run --rm insar python …`.
  numpy/BLAS work natively; activation is automatic; the Windows bug class below
  cannot occur. Needs Docker Desktop (WSL2) running. See `docker/README.md`.
- **Native Windows (legacy):** run compute scripts with the **conda env activated**,
  or rely on the in-script DLL bootstrap that all Phase 2–4 scripts carry. Launching
  `python.exe` by full path *without* activation → numpy can't find its BLAS DLLs →
  **every matrix/linalg call hard-crashes with `0xC06D007F`** (a DLL-load failure,
  NOT a numerical bug). Also keep `logging` messages **ASCII** (Windows console is
  cp1252); put unicode only in UTF-8 files. See `error_history_log.md` (2026-05-29).

- Env (native): `insar_qa_env` at `C:\Users\varun\.conda\envs\insar_qa_env\`.
- HyP3 credits: ~6,170. Disk: ~73 GB used in `data/`. Image: ~328 MB.

---

## 4. Open questions — "deepen trust" or "scale/deploy"

The core vision is fully built. Remaining work:

0. **Infrastructure & portability:**
   - **0a. Containerize on Linux (Docker). ✅ DONE (Session 8).** Reproduces the
     current Phase 1–4 pipeline; eliminated the Windows-specific bug class.
   - **0b. AOI-parameterization refactor (in progress).**
     - ✅ **Part 1 — `config.yaml` + `workflows/config.py`** (AOI path, job prefix,
       time window, baseline rules). Done.
     - ✅ **Part 2 — `workflows/stacks.py`** derives stack labels from product
       **metadata** (a product→stack manifest written from HyP3 job names); the
       duplicated time-of-day `stack_key()` is removed from the 3 QA files and the
       `Ramban_NH44`/`ramban_aoi.geojson` hardwiring is gone. Verified: 0/183
       mismatches vs the existing Ramban labels. Done.
     - ✅ **Part 3 — automated connectivity-rescue + scientific quality gate.**
       `sbas_network_graph.py` emits a minimum-set of bridging CONCERN pairs that
       clear a **quality GATE** (`rescue_gate` in config: atmos R²≤0.45 + coh≥0.6 =
       noise gates; surv%≥15 = coverage sanity floor). A bridge is an unredundant
       single point of failure, so a gap whose only bridges fail the gate is left
       broken (→ SVD/period-split) rather than ingesting noise. `--recommend-only`
       runs offline; emits per-stack diagnostics + **rejected-bridge reasons** for
       fine-tuning; `apply_connectivity_rescues.py` consumes the JSON; idempotent +
       deterministic. `exclude_from_rescue` is now an empty-default manual override
       (the gate excludes frame484's 0680 R²=0.50 automatically). Output =
       **103/26/54** (5 rescues; frame479→SVD, frame484→period-split, both via the
       gate). **Bridge SELECTION is coverage-first:** among gate-passing (already
       atmospherically clean) candidates, pick the **highest surviving_pct** (R² as
       tiebreak), because a bridge gates network-wide solvability. (A frame106 A/B
       showed lowest-R²-only picked a 36-day bridge that halved usable pixels;
       coverage-first restored 14,045 px.) Done & adopted on disk.
     - ✅ **Part 4 — multi-stack driver + union mosaic.** `workflows/run_multistack.py`
       runs Phases 2–4 across the connected stacks (idempotent, mtime-gated) and
       builds the AOI product by UNION at the hazard/alert level (no cross-look
       velocity averaging). Ran all 3 ASC stacks → union HIGH=**5,268** (**291** ≥2-look),
       monsoon union zones=**405** (**26** multi-look-confirmed). frame479/484
       auto-skipped (need SVD/period-split). Done.
     - Fold in the still-unenforced <150 m perpendicular-baseline rule here too.
   - **AOI guidance (targeting, NOT precision):** a better AOI improves *which ground
     we measure*, not data quality — it won't touch the ~30 mm/yr noise floor, the
     80 m resolution, or vegetation gaps (those need 12.5 m DEM + APS + MintPy). Draw
     a domain-informed polygon over the NH-44 corridor + slopes above the road +
     Chenab reach. Draw in Google Earth Pro → `.kml` → GeoJSON. **Bundle with the next
     HyP3 pull** — a new AOI forces a full Phase-1 re-run (credits + hours).
1. **Production hardening — MintPy migration ✅ COMPLETE (all steps; kept here for the detailed record).** The next major hardening items are the *accuracy backlog* (12.5 m DEM, full APS, uncertainty, calibrated soil) and **validation (GSI Bhukosh)** — see §5. MintPy detail:
   - **MintPy migration**, run **inside its own container image** (heavy deps:
     cartopy/pyresample/pyaps3/h5py/dask — do NOT add to the lean `insar` image;
     never touch `insar_qa_env`). Sub-tasks, in order:
     1. ✅ **DONE — separate MintPy image / compose service.** `docker/mintpy.Dockerfile`
        + `docker/environment.mintpy.yml` → `insar-mintpy:latest`; `mintpy` service in
        `docker-compose.yml` with the CDS creds auto-mounted (CDSAPI_RC). Smoke-tested:
        **MintPy 1.6.2**, GDAL 3.13.0, `smallbaselineApp.py` + `prep_hyp3.py` on PATH,
        `~/.cdsapirc` auto-mounted. (Lock to `docker/conda-mintpy-linux-64.lock` later.)
     2. ✅ **DONE — `prep_hyp3` + `smallbaselineApp` on frame106 + cross-validation.**
        `workflows/prep_mintpy.py` clips the 6 HyP3 layers per KEEP pair to the custom
        grid + extracts the `.txt` (the gap) → `data/mintpy/<stack>/hyp3/`; `prep_hyp3.py`
        → 186 `.rsc`; `smallbaselineApp.py --end velocity` (run in a **/tmp** work dir —
        the bind mount can't `utime`) → `velocity.h5` → `mintpy_out/velocity_mintpy.tif`.
        Cross-val vs custom (309x353, offset-removed): **r=+0.28 raw / +0.39 high-pass**,
        same sign. WEAK but expected — no ERA5 + MintPy velocity not coherence-masked
        (both atmosphere-dominated). Recipe in session_journey (2026-05-31).
     3. ✅ **DONE — ERA5 tropospheric correction + FAIR re-validation.** Smoke-tested
        pyaps3 vs the new CDS endpoint first (`workflows/smoke_pyaps3.py`: pyaps3 0.3.7 +
        cdsapi 0.7.7 read the endpoint from `~/.cdsapirc`, one live ERA5 grib downloaded).
        Then `mintpy.troposphericDelay.method = pyaps` via `workflows/mintpy_f106_era5.cfg`
        + `workflows/run_mintpy_era5_f106.sh` (15 ERA5 gribs → dry+wet delay subtracted).
        FAIR re-validation (`workflows/crossval_mintpy.py`, MintPy coh≥0.7-masked):
        agreement **nearly doubled — r +0.28 → +0.55** (same 14,045-px set), **+0.587**
        raw on the masked common set; **MintPy velocity std 39 → 21 mm/yr** (now below
        custom 31). The atmosphere WAS the dominant disagreement. Recipe + honest caveats
        in session_journey (2026-05-31). Outputs: `mintpy_out/velocity_mintpy_era5.tif`,
        `temporalCoherence_mintpy.tif`, `velocity_era5.h5`.
     4. ✅ **DONE — 2 DESC stacks EVALUATED via MintPy, then DUMPED (quality-first).**
        `prep_mintpy.py` gained an osgeo-only `grid_from_products()` (AOI+buffer grid for a
        stack with no custom raster); `run_mintpy_era5.sh <stack>` generalises the ERA5 run
        (`NET_START_DATE/END_DATE` env vars period-split to one connected island);
        `inspect_mintpy_velocity.py` reads out coverage/velocity/coherence (no custom ref to
        cross-val against). MintPy DOES handle the disconnect natively (logs *"network is NOT
        fully connected … Continue to use SVD to resolve the offset"*) — but the result
        fails quality: **frame484** has no pixel >0.85 avg-spatial-coh (0.8% usable at ref
        0.6) → unusable; **frame479** velocity is physically implausible (full network std
        **57 mm/yr**/9,016 px >100; period-split **137**/30,378 — short-baseline noise +
        monsoon decorrelation, not a disconnect artifact) vs ASC's 21–30. **Both DUMPED**
        (`DUMPED.md` in each dir). The "MintPy subsumes SVD/period-split" assumption is
        **refuted by the data** for these stacks. `run_multistack.py` already skips them.
        **ASC/DESC decomposition DEFERRED** (needs better DESC: longer connected series / PS
        / phase-linking). Full detail: session_journey + error_history_log (2026-05-31).
   - **CDS / ERA5 setup (needed only for step 3; user HAS a Copernicus CDS account).**
     Verified against ECMWF "How to install and use CDS API on Windows" (fetched
     2026-05-30). Template: `.cdsapirc.template` (repo root).
     **✅ Credential path SMOKE-TESTED 2026-05-31** — in a throwaway container,
     `cdsapi` read `~/.cdsapirc`, authenticated to the new CDS endpoint (no 401),
     the ERA5 pressure-levels licence was accepted (no 403), and a minimal request
     went accepted→successful and downloaded a GRIB in ~15 s. **✅ Now FULLY PROVEN
     end-to-end (2026-05-31):** pyaps3 0.3.7 (in the MintPy image) downloaded ERA5 from
     the new endpoint and MintPy applied the tropospheric correction on frame106 (step 3
     above). The CDS/ERA5 path is complete — no remaining blockers.
     1. Logged in, copy the **2-line credentials** from
        https://cds.climate.copernicus.eu/how-to-api ("Set up the CDS API personal
        access token" box). **New-CDS format** (post-2024 migration — a single
        Personal Access Token, NOT the old `UID:KEY`):
            url: https://cds.climate.copernicus.eu/api
            key: <your-personal-access-token>
     2. Save to `~/.cdsapirc` — on Windows `%USERPROFILE%\.cdsapirc`
        (`C:\Users\varun\.cdsapirc`). For the **container** MintPy run, mount that
        host file **read-only** into the MintPy image (e.g. `/home/<user>/.cdsapirc`),
        same pattern as `~/.netrc`.
     3. Inside the MintPy image: `pip install "cdsapi>=0.7.2"`. **Caveat:** `pyaps3`
        (MintPy's ERA5 downloader) must target the NEW CDS endpoint — pin a recent
        `pyaps3` + `cdsapi` when building and smoke-test one ERA5 fetch first.
     4. **Accept the dataset Terms of Use** for "ERA5 hourly data on pressure levels"
        (+ any others MintPy requests) — required per dataset on the CDS site.
     **User can do now (optional, host-side):** steps 1, 2, 4. Step 3 waits for the
     MintPy image. `.cdsapirc` is git-ignored; never commit the real token.
   - **12.5 m ALOS DEM** → sharper slope → more discriminating FS.
   - **Soil-parameter calibration / sensitivity test.**
   - **Perpendicular-baseline gate on rescues** (needs the ASF bperp cache) +
     enforce the still-outstanding <150 m Bperp rule from Phase 1.
2. **Visualization:**
   - **Combined interactive 3-D dashboard over the UNION mosaic** (current
     `dashboard_3d.html` is frame106-only; per-stack dashboards + union JSON/MD +
     `MOSAIC_ASC_hazard_class.tif` exist, but no single union dashboard yet).
   - **ASC/DESC vertical+EW decomposition** — DEFERRED: both DESC stacks were evaluated
     via MintPy and dumped as too noisy (step 4). Needs better descending data first
     (longer connected series / persistent scatterers / phase-linking).
3. **Make it live / smarter:**
   - Real Copernicus CDS *rainfall* (replace mock scenarios) — separate from the
     ERA5/CDS *tropospheric* use above, but same account.
   - Real flow-routing for the LLOF flag (replace the TWI proxy).
   - Upgrade the deterministic agents to a real/hybrid LLM ("rules decide, LLM
     narrates" is the low-risk first step).
4. **Deploy/polish:** optional hosted Streamlit version of the 3-D dashboard.
5. **Housekeeping:** README run-sequence note for the new steps (`stacks.py
   --seed-legacy`, `sbas_network_graph.py --recommend-only`, `run_multistack.py`).
6. **CONCERN pairs — include with downweighting or exclude?** Still open (Phase 1).

---

## 5. Recommended next step

**MintPy migration steps 1-4 COMPLETE** (image + frame106 inversion + cross-check + ERA5
correction [the big win, r +0.28→+0.55] + DESC evaluation [both dumped, quality-first]).
The MintPy push has delivered its headline: a field-standard, ERA5-corrected velocity that
independently corroborates our custom engine on frame106.

**Inverse-velocity time-to-failure (Fukuzono/Voight, §6 Area 3) — BUILT.**
`workflows/inverse_velocity_ttf.py` screens every alert zone (creep-masked window, hard
direction/consistency gates after a self-caught noise false-positive). Honest result across
all 3 ASC stacks: **0 accelerating, all STEADY** (frame106 222/222, frame102 206/206,
frame101 5/5) — correct for a short, noisy 3.5-mo series; the screen auto-projects dates once
the data accelerates. Outputs `data/alerts/<stack>/ttf_report.{json,md}`.

**Live rainfall + ID thresholds + COUPLING (§6 Area 3/5, priority #3) — DONE (increments 1 & 2).**
`fetch_rainfall.py` (ERA5-Land via CDS; GRIB + pygrib — GDAL has no GRIB/netCDF driver here) +
`rainfall_id_threshold.py` (Caine 1980): real 2025 rainfall (1,233 mm) flags **one trigger day,
26 Aug (~134 mm/1 d, 183 mm/2 d)**. **Coupled into `agentic_orchestrator.py`:** FS is exactly
linear in saturation m, so **FS_real = (1−m)·FS_dry + m·FS_saturated** (interpolate the end-member
rasters, no recompute). `--date 2025-08-26` → real 196 mm/72h → m=1 → 222 zones (labelled FS_real);
`--rainfall-timeline` → season alert-zone curve (peaks 222 on 26 Aug, decays as soil dries) →
`data/alerts/hazard_timeline.{csv,png}`. Mock scenarios preserved (run_multistack unaffected).

**Back-test vs landslide inventory (§6 Area 4) — DONE (first pass).** `backtest_inventory.py` vs
`data/inventory/ramban_documented_landslides.geojson` (9 documented hotspots + 2025 events,
**approximate** coords). **Spatial: 8/9 within 2 km** of a flagged zone (indicative — we flag a lot).
**Temporal: 0/2 MISS** — trigger 26 Aug vs documented **27 Apr / 8 May 2025**. Finding: spatially
plausible, **trigger timing not yet validated**. KPIs → `RESULTS_AND_KPIS.md` §9. (NASA GLC is
2007–2018, no 2025; GSI Bhukosh ~302 Ramban slides = the authoritative source, not pulled this session.)

**Session 9 — the two ★★★ physics borrows, DONE (Area 7 #1–2):**
- **V_slope (Area 7 #2) — `workflows/slope_velocity.py`.** LOS→downslope projection. Blind-spot
  24–42%, creep amplified ×1.4–1.6 across the 3 ASC stacks. Standalone rasters/reports written; NOT
  yet wired into the orchestrator creep mask or `inverse_velocity_ttf.py` (the natural follow-up).
- **Snowmelt/freeze-thaw + April window (Area 7 #1) — `fetch_rainfall.py` + `rainfall_id_threshold.py`.**
  Honest negative: snowmelt 59 mm (≪ rain 1,350), **0 new acute trigger** (still 26 Aug), **0
  freeze-thaw days** (AOI-mean temp never < 0 °C), back-test **still 0/2 temporal**. Diagnosis
  sharpened: the Apr–May miss is **ERA5-Land orographic rain under-count**, not missing snowmelt.

**Recommended next (Session 10 ran the full rainfall investigation — RAINFALL IS CONCLUSIVELY RULED OUT):**
1. ✅ **DONE — the rainfall-source question is CLOSED (3 independent products agree).** Regional I–D curve
   done + **VERIFIED** (`--threshold nwhimalaya`; coefficients/units triangulated + numerically reproduced —
   §12 verification block); **CHIRPS** fetched/screened/back-tested/specificity-analysed (§12d: drier than
   ERA5-Land on the spring dates); **GPM IMERG** half-hourly sub-daily test (§12e: 27 Apr E=0.0, 8 May E=1.09
   marginal, 26 Aug control E≈12). All three — daily reanalysis, daily gauge-blend, half-hourly satellite —
   agree **there was no acute triggering rain on the documented spring dates**. So the spring trigger is
   **NOT a rainfall problem.**
   - ✅ **DONE — spring conditioning (`spring_conditioning.py`, §12f):** per-elevation freeze-thaw (lapse-rate
     onto the DEM) shows onset ~2500 m while the valley/event level (~1540 m) = **0** freeze-thaw days → it
     weakens the **upper source slopes above the road**; chronic saturation = event-day wetness 33%/20% of the
     season peak despite ~0 acute rain. ⇒ spring slopes were **PRIMED, not storm-triggered** — explains
     *susceptibility* but not the discrete date.
   - The remaining spring leads are therefore **non-rainfall**: (a) **GSI Bhukosh inventory** for **verified
     dates/coords** (news-derived dates may be imprecise — IMERG found a 20 Apr burst with *no* reported
     failure) + a scored spatial back-test; (b) probe the **NHAI tunnel/road-construction** angle at
     Digdol/Khooni Nallah; (c) refine §12f with ERA5-Land true orography if a *calibrated* freeze-thaw is
     wanted. The verified regional curve is ready to become the default monsoon trigger when re-baselining the
     `[MOCK]` KPIs (only residual: exact-digit confirm from the paywalled primary PDF).
2. **Per-elevation freeze-thaw** — the AOI-mean masks high-slope freezing; needs per-cell ERA5-Land
   temperature + DEM elevation bands (the current freeze-thaw flag returns 0 by construction).
3. ✅ **DONE (Session 9 cont.) — V_slope wired through the whole pipeline** as opt-in `--use-vslope`
   (orchestrator + `inverse_velocity_ttf.py` + `geomechanical_engine.py` + `run_multistack.py`); LOS
   stays the default and is built+preserved. `run_multistack.py --use-vslope` builds a **parallel
   area-wide product** in `data/mosaic_vslope/` + `data/alerts/mosaic_asc_vslope/`: union HIGH **5,268→5,493**,
   **≥2-look HIGH 291→399 (+37%)** (downslope projection improves cross-geometry corroboration),
   monsoon zones 405→433. Optional follow-up: make V_slope the hard default once ready to re-baseline
   the `[MOCK]` KPIs; per-elevation freeze-thaw; the GSI Bhukosh scored back-test.
4. **Ingest the GSI Bhukosh inventory (~302 Ramban landslides)** for a *scored* (precision/recall)
   spatial validation — `backtest_inventory.py` ingests it unchanged.
5. **FS-hardening bundle**: 12.5 m ALOS DEM + **K_sn** conditioning factor (Area 7 #3) +
   spatially-varying soil + **matric-suction/Bishop FS refinement** (Area 7 #4) + calibrated m.
6. **Smaller committable items:** roll the ERA5-corrected frame106 velocity through the
   hazard/alert chain; README run-sequence note (now also `slope_velocity.py` + the updated
   `fetch_rainfall.py`/`rainfall_id_threshold.py` water+snowmelt signature); union 3-D dashboard.

_Data-upgrade note: **NISAR (NASA-ISRO, L+S band)** added to §6 Area 1 as the top future SAR upgrade
(L-band recovers coherence over vegetation — our worst enemy); not yet in the pipeline, track ASF availability._

**Exception to MVP-first (always):** fix correctness/data-integrity bugs
immediately; defer quality-only improvements until shown to matter.

---

## 6. Expansion roadmap — areas of exploration toward a robust forecasting tool

§4 is the *near-term hardening backlog*; this is the broader strategic menu. Each
**AREA is self-contained** and can be picked up independently. The current system
is a demonstrable MVP of the full vision (radar → audited data → velocity →
physics hazard → explainable rainfall-driven warning); these areas take it from
MVP to a **defensible forecasting tool**. ⚠️ *Durability:* this file is overwritten
each session — **mirror this section into `InSAR_hazard_forecasting_Context.md`** so
the roadmap is preserved long-term.

**Where the MVP is weakest today (what these areas fix):** ~30 mm/yr velocity noise
floor; single-look (no true 3-D motion); assumed/uniform soil strength + dry/sat
end-members + TWI-proxy downstream flag; *mock* rainfall; a *static* hazard map (no
failure-timing); and no validation against real events.

### Area 1 — Noise reduction (measurement accuracy; the ~30 mm/yr floor)
- **MintPy ERA5 tropospheric correction** (in progress, §4) — physically subtracts
  atmospheric delay; the biggest single lever. **GACOS** (free web service) as an
  alternative / cross-check.
- **DEM-error correction + coherence-weighted inversion** (MintPy native).
- **Phase-linking / distributed-scatterer methods** (MintPy phase-linking,
  SqueeSAR-style) — recover coherence in *partially* vegetated Himalayan slopes; the
  biggest local win against our worst enemy (vegetation decorrelation).
- **Enforce the <150 m perpendicular-baseline rule** (outstanding from Phase 1).
- *Payoff:* trust slower/smaller motions; fewer false creep flags.

### Area 2 — Signal strengthening (interpretation power)
- **All 5 stacks → ASC/DESC decomposition into vertical + east-west motion** —
  removes line-of-sight ambiguity; measure *real* slope movement, not a projection.
- **Persistent-scatterer (PS) points** on rock outcrops + NH-44 infrastructure —
  mm-precision anchors that survive where distributed scattering fails.
- **Longer time series + seasonal vs steady-creep decomposition** — separate
  reversible seasonal swelling from progressive creep (avoid seasonal false alarms).

### Area 3 — From hazard MAP to FORECAST (the biggest conceptual upgrade)
- ★ **Inverse-velocity time-to-failure (Fukuzono/Voight)** — accelerating creep →
  1/velocity falls linearly toward zero → **predict failure timing**. Uses the
  per-pixel time-series we ALREADY produce. **Highest value for the least new data.**
- **Rainfall intensity–duration (ID) thresholds** — field-standard landslide
  trigger; couple measured creep with exceeded rainfall thresholds.
- **Calibrated, spatially-varying soil strength** (lithology/soil maps) + **distributed
  saturation** from real rainfall + soil moisture (replace dry/sat end-members + TWI proxy).
- **Real flow-routing / debris-runout modelling** for the LLOF flag (replace the TWI stand-in).
- *Payoff:* time-resolved, physically-grounded forecasts instead of a static map.

### Area 4 — Validation & uncertainty (credibility)
- **Back-test flagged zones against a landslide inventory** — documented Ramban
  failures; NASA Global Landslide Catalog; GSI Bhukosh (India). This is the step that
  converts "rough hazard map" → "validated forecast."
- **Uncertainty quantification** — per-pixel velocity error bars; propagate into FS/alerts.
- **Susceptibility model** (logistic regression / random forest on conditioning
  factors) trained + validated on the inventory → independent corroboration of physics.

### Area 5 — Multi-sensor corroboration via GEE & free services (robustness)
- ⚠️ **GEE cannot do InSAR** (no SLC phase / interferometry) — InSAR stays on
  ASF/HyP3/MintPy; GEE adds everything *around* it. Robustness = stop relying on one
  sensor + one assumption.
- **Rainfall (live trigger + ID thresholds):** CHIRPS (daily), GPM IMERG (~30-min),
  ERA5-Land — all in GEE. Replaces the mock scenarios.
- **Soil moisture / saturation:** SMAP (~9 km), ASCAT → real wetness state.
- **Soil / lithology for spatial strength:** SoilGrids (250 m) → varying cohesion/φ.
- **DEM upgrade:** Copernicus GLO-30 / NASADEM / AW3D30 (30 m, GEE) for slope/TWI/HAND;
  true 12.5 m ALOS RTC from ASF.
- **Vegetation / where InSAR is trustworthy:** ESA WorldCover (10 m), Dynamic World,
  Sentinel-2 NDVI time series.
- **Optical change / independent validation:** Sentinel-2, Landsat, Planet NICFI
  (free, tropics) → detect fresh scarps/scars; corroborate InSAR-flagged zones.
- **Inventory + large-area susceptibility:** NASA Global Landslide Catalog + GEE
  imagery → susceptibility over the whole NH-44 corridor, then focus InSAR where high.
- **Other free services:** GACOS (tropo correction), COMET-LiCSAR (free pre-made
  Sentinel-1 interferograms — independent cross-check), OpenTopography (LiDAR/high-res
  DEM where available), GSI Bhukosh (Indian geology + landslide data).

### Area 6 — Operationalize / deploy / smarter
- **Real-time rainfall ingestion** (CHIRPS/GPM) → continuously-updating live alerts.
- **Hybrid LLM agent** ("rules decide, LLM narrates" — low-risk first step).
- **Hosted dashboard** (Streamlit) + the **combined union 3-D dashboard** over the
  multi-track mosaic (today's 3-D view is the single frame106 patch).

### Suggested priority (highest leverage first)
1. **Finish MintPy + ERA5** (Area 1) — also unlocks SVD/DESC for Area 2.
2. **Inverse-velocity time-to-failure** (Area 3) — turns hazard → forecast using
   existing data; biggest scientific + narrative jump for least cost.
3. **Live rainfall (GEE CHIRPS/GPM) + ID thresholds** (Areas 3/5) — real trigger.
4. **GEE corroboration + inventory validation** (Areas 4/5) — multi-sensor robustness.

**Robustness in one line:** corroborate InSAR creep with optical change, real
rainfall, soil moisture, and a validated landslide inventory — never trust a single
sensor or a single physics assumption.

---

## 7. End-of-session checklist

Documentation ritual for 2026-06-02 (Session 10) — **all done**:
- [x] `session_journey.md` — Session 10 entry with Pushes 1–7 (CHIRPS plumbing → regional curve →
      specificity prototype → CHIRPS ran/refuted → literature verification → GPM IMERG → spring conditioning).
- [x] `milestone.md` — Milestones 17 (Himalaya-tuned trigger + gauge pipe), **18 (GPM IMERG: rainfall ruled
      out)**, **19 (spring conditioning: "slowly-primed slope")** added (plain language).
- [x] `Research/Foundations - Physics and Maths Primer.md` — CF5 (gauge vs reanalysis; CHIRPS refuted; IMERG
      closes it) + **CF3 update (freeze-thaw resolved by elevation)**, interview Q, limitation bullets.
- [x] **`RESULTS_AND_KPIS.md`** (committed) — §12 regional curve + verification (curve VERIFIED), §12b/§12c
      CHIRPS + specificity, §12d CHIRPS REFUTED, §12e GPM IMERG → rainfall CLOSED, **§12f spring conditioning**.
- [x] `workflows/fetch_gpm_imerg.py` + `workflows/spring_conditioning.py` (**new, uncommitted**).
- [x] `README.md` — Step 6 (GEE auth) + forecasting run-sequence bullet (now incl. specificity + IMERG).
- [x] **`SESSION_REVIEW.md`** (this file) — refreshed to current state for a clean cold start.
- [ ] `error_history_log.md` — no new entry, but THREE reusable gotchas surfaced (worth an entry if you keep
      one): (1) **native `ee`+numpy crashes hard on Windows** (exit 127, gRPC/MKL DLL conflict) → run GEE+numpy
      scripts in the `insar` container, not native; (2) **Git Bash mangles `/app/...`** paths in
      `docker compose run` → use container-RELATIVE paths; (3) keying a dict by `date` objects then looking up
      with ISO strings silently misses → key by `.isoformat()`.

**Git state (user commits manually, in parallel).** Committed so far: `1c69fe7` (CHIRPS fetch + regional
curve + specificity prototype) and `cf1d485` (CHIRPS-refuted result + verification). **STILL UNCOMMITTED at
session close:** `workflows/fetch_gpm_imerg.py` + `workflows/spring_conditioning.py` (new), plus IMERG +
conditioning doc updates to the committed files `RESULTS_AND_KPIS.md` (§12e/§12f + header), `README.md` (IMERG
bullet), `Research/Foundations - Physics and Maths Primer.md` (CF5 IMERG close + CF3 elevation update).
Git-ignored/local (NOT committable): `SESSION_REVIEW.md`, `session_journey.md`, `milestone.md`, `CLAUDE.md`;
**`.env`** (real `EE_PROJECT_ID=tutorial-project-472812` + `EE_CREDENTIALS`); all `data/` outputs
(`ramban_chirps_daily.csv`, `imerg_*` + `spring_conditioning_*` reports/PNGs, cached `imerg_raw_*.csv`,
suffixed trigger/specificity reports, `backtest_report.*` [restored to Caine baseline]). ⚠️ The real `.env` +
`~/.config/earthengine/credentials` must NEVER be committed (both ignored). **Host (not in git):**
`earthengine-api 1.7.29` in `insar_qa_env`; `insar` image rebuilt with earthengine-api; GEE token at
`~/.config/earthengine/credentials`.

**Recommended first action next session:** rainfall is **ruled out** (§12d/§12e) and spring conditioning is
characterized (§12f: priming, not a discrete trigger) — both spring leads now point **off rainfall/weather**.
Pick one of: (1) **GSI Bhukosh inventory** for **verified
dates/coords** (the news-derived 27 Apr/8 May may be imprecise — IMERG found a 20 Apr burst with *no* reported
failure) + a scored spatial back-test; (2) optionally probe the **NHAI construction** angle (Digdol/Khooni
Nallah tunnelling). Run GEE+numpy scripts **in the `insar` container** (native crashes — see §7). The verified
`nwhimalaya` curve can become the default whenever you re-baseline the `[MOCK]` KPIs. See §5.

# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`docs/archive/local/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 25 · branch `aoi-vaishnodevi` · updated 2026-07-17

## Current state

- **★ NEW (§49, M45) — full-product audit: ZERO bugs.** Three axes (math/science,
  scripts/structure, data/references), 60+ checks: the standing FS rasters reproduce an
  independently re-written infinite-slope formula **pixel-exact** at both sites; ID-threshold
  trigger days recomputed from raw sums match the product; all rasters/inventories/season
  artifacts internally consistent and matching this ledger. Made permanent as
  `tests/test_science_verification.py` — suites now FOUR: **7/7 + 10/10 + 11/11 + 12/12**.
  Two documented observations (§49): frame103's noisy 4-pair chain (already σ_v-gated, §24) and
  the kappa artifact holding only the adopted point. **Bonus: the 07-17 scheduled cycle was the
  first fully-unattended clean run** (headless start/stop, 4:12, quiet).
- **(§48, M44) — storage & automation overhaul:** the scheduled monsoon cycle was cleared of
  the "huge ASF download" suspicion (its whole fetch is ~KB of ERA5; the slowdown was an uncapped
  WSL2 VM + a stale Docker autostart + the missed-08:00 catch-up firing on logon — all fixed).
  Cycle re-measured end-to-end after hardening; ~56 GB of disk recovered. **Raw HyP3 zips are now
  DISPOSABLE staging** (Drive-archived by the user, deleted locally): the HyP3 metadata txt lives in
  `processed_tiffs/`, `prep_mintpy` reads it there (zip = fallback), and `data\raw_zips` is an NTFS
  junction to `C:\InSAR_data\raw_zips` with an explicit compose bind for containers (Docker does NOT
  resolve junctions — found by test). `test_plumbing` rewritten to the new invariant; suites
  **11/11 + 7/7 + 10/10**. Two new ops bug classes in the error log (2026-07-15).
- **§47 (M-carried) — soil verdict re-measured at kappa=0.06: HOLDS + SHARPENS at BOTH sites;**
  playbook M2 stays required (depth z is the #1 field number); both sites carry a standing
  sensitivity artifact. Third kappa non-consumer fixed at the root (None-default = site config).
- **§46 (M43) — van Genuchten suction: mechanism SHIPPED config-gated, adoption REJECTED** ((α,n)
  not identifiable from a spatial inventory); all wetness→FS physics centralized in
  `workflows/fs_real.py`. **§45 (M42) — kappa=0.06 ADOPTED both sites** (VD beat its §44 slope-only
  tie). **§44 (M41) — bootstrap CIs + permutation p + ablation ladder standing**
  (`validation_stats.py`). The Science Upgrade Plan's top 3 are ALL RESOLVED.
- **BOTH sites in WATCH** (as-of 2026-07-11 data; cycle ran unattended 2026-07-17, §49): VD 18/18
  zones active, 0 ALERT days (23 WATCH+); Ramban 8/8 active, 4 April ALERT days (28 WATCH+).
  Next scheduled cycle **19 Jul 08:00**. **The cycle no longer starts/stops Docker (user decision
  2026-07-16):** it checks Docker is running, waits up to 10 min (toast) for the user to start
  it, then skips quietly — start Docker Desktop at logon and the cycle takes care of itself.
- **★ NEW (2026-07-16) — GACOS request-helper + tarball-ingest pair** (`workflows/gacos_request.py`
  stdlib-only + `workflows/gacos_ingest.py`): the §40 "second pull" manual step is now
  copy-paste-form → email → one ingest command. Verified against the real 2026-07-11 delivery
  (byte-identical to the §40 files; classic .ztd+.rsc fallback also tested).
- **Radar side (§35/§43):** July S1 passes still not at ASF as of 07-10 — chains can't extend yet;
  the §43 f106 bridge swap (151 m → 102 m/24 d) applies at the next rebuild. **NISAR:** too few
  products (§33); recheck ~early Aug.
- **Ramban: COMPLETE, scored, LIVE** (§21b, CIs §44). **Vaishno Devi: full second AOI, validated
  and site-tuned** (§26–§32, §44 caveat). Merge `aoi-vaishnodevi` → `master` remains the user's call.
- **Deliverables:** route exposure + NE-flank creep target (§30/§33), Bhavan-overhang fast-failure
  toolkit (§34), multi-AOI registry + status board + playbook (§41).
- **Honest limits carried:** creep core 0 vs corridor inventory (CV3); 598 m miss at the disaster
  site (§31 addendum — the calibration target); soils literature-corroborated not lab-measured
  (§37/§39/§42/§47); fast-failure tools unproven-in-anger; §40 GACOS discrepancy pair open.
- **⚠ Archival note (§48):** the Google Drive copy of the 235 raw zips is now the ONLY archival
  source (ASF server copies expired; re-creation costs HyP3 credits ≈7,460 remaining).

## Recommended next step

The product roadmap is unchanged (STABLE §3/§4): **radar cadence when July passes land** (resubmit →
download → QA → multistack → re-score, applying the §43 f106 bridge swap), then the failure-class
gap (Sentinel-2 optical change) and sub-daily IMERG. User-side: field check of the NE-flank CORE
target; merge to `master`; publish the dashboard. Ops is now hands-off: react to toasts only.

## Uncommitted delta

Sessions ≤24 committed through `95b2d79`; session 25's first batch committed by the user as
`a290ae9` (monsoon cycle no longer manages Docker; GACOS request/ingest pair, gold-tested).

Still uncommitted (this wrap):
- NEW: `tests/test_science_verification.py` (the §49 audit made permanent — 12 tests).
- MODIFIED: `RESULTS_AND_KPIS.md` (§49), `milestone.md` (M45), primer (Part D verification Q),
  `SESSION_REVIEW.md` (this block).
- Git-ignored as usual: journey entry (S25); audit scratch scripts live in the session scratchpad.
- System-side carried from S24: `.wslconfig` caps, `data\raw_zips` junction, Drive-archived zips.

---

# STABLE — edit only when a fact changes (never rewrite per session)

## 1. Read these documents, in this order

| # | Document | Why read it | How much |
|---|---|---|---|
| 1 | **SESSION_REVIEW.md** (this file) | Current state, open questions, next step | LIVE block + skim STABLE |
| 2 | **`RESULTS_AND_KPIS.md`** | **Committed** ledger of every headline KPI/finding (mock + real), with provenance | Skim; read the newest §§ |
| 3 | `README.md` | Project overview, repo layout, full-pipeline run guide, known env issues | Skim |
| 4 | `milestone.md` | Plain-language story of progress | Top to current |
| 5 | `session_journey.md` | Slim per-session bullets (what/why/dead-ends); older entries are long-form | Newest 1–2 entries |
| 6 | `error_history_log.md` | Every bug + root cause + fix — **check before debugging anything** | Scan headings |
| 7 | `docker/README.md` | How to build/run the pipeline in the Linux container | As needed |
| 8 | `docs/guides/Foundations - Physics and Maths Primer.md` | The science (Phases 1–4 + forecasting/rainfall/validation) | As needed |
| 9 | `InSAR_hazard_forecasting_Context.md` | Original vision / full expansion roadmap | Reference |

**Also re-read `CLAUDE.md`** — behavioural rules + the documentation ritual (§5: run `/wrap-session` before stopping).

> **Committed vs local-only (verified 2026-06-07 via `git ls-files`):** `CLAUDE.md` and
> `session_journey.md` are **git-ignored / untracked** (local-only working notes), as is most of `data/`.
> **`SESSION_REVIEW.md` (this file), `milestone.md`, and `.claude/commands/` are TRACKED** — a fresh clone
> gets this dashboard, the milestones, and the `/wrap-session` command, alongside the always-committed
> `README.md`, `RESULTS_AND_KPIS.md`, `error_history_log.md`, the Foundations primer, and
> `InSAR_hazard_forecasting_Context.md` — but NOT `session_journey.md`/`CLAUDE.md`. The user commits manually.

## 2. CRITICAL environment gotcha (read before running anything)

**Two ways to run, pick one — don't mix:**

- **In Docker (preferred):** `docker compose run --rm insar python …`. numpy/BLAS work natively;
  activation automatic; the Windows bug class below cannot occur. Needs Docker Desktop (WSL2) running.
  **NOTE: matplotlib `savefig` crashes NATIVELY (exit 127) — run anything that plots in Docker** (the
  scored back-test + the rainfall sweep both plot, so always run them in the container).
- **Native Windows (legacy):** run compute scripts with the **conda env activated**, or rely on the
  in-script DLL bootstrap. Launching `python.exe` by full path *without* activation → numpy can't find
  its BLAS DLLs → **`0xC06D007F`** (DLL-load failure, not a numerical bug). Keep `logging` ASCII.
  Native `gdalwarp` etc. live in `C:\Users\varun\.conda\envs\insar_qa_env\Library\bin` (prepend to PATH).

- Env (native): `insar_qa_env` at `C:\Users\varun\.conda\envs\insar_qa_env\`.
- HyP3 credits: ~7,460 as of 2026-07-10 (§35; ≈ enough for one more AOI's full Phase-1 pull). Disk: ~46 GB in `data/` (§48 — raw zips Drive-archived + deleted 2026-07-15).
- The container: `docker compose build` then e.g.
  `docker compose run --rm insar python workflows/agentic_orchestrator.py`. Code + `data/` bind-mounted at `/app`.
- **WSL2/Docker resource caps live in `C:\Users\varun\.wslconfig`** (6 GB / 6 CPU, added 2026-07-15 §48) —
  raise temporarily for heavy MintPy sessions, then `wsl --shutdown`.
- **`data\raw_zips` is an NTFS junction → `C:\InSAR_data\raw_zips`.** Containers can't see through
  junctions — compose nested-binds the real folder (both services).
- **Start/stop Docker ONLY via `docker desktop start` / `docker desktop stop` (CLI, 4.37+).**
  Force-killing the processes DETERMINISTICALLY bricks the next start (stale unix socket in
  `%LOCALAPPDATA%\Docker\run\` → error dialog). If already bricked: quit the dialog, rename that
  `run` dir, `docker desktop start` (error log 2026-07-15/16).

## 3. Open questions — "deepen trust" or "scale/deploy"

The core vision is fully built and scored above chance. Remaining work:

0. **Infrastructure & portability:** Infra 0a/0b DONE. **Multi-AOI productization DONE (2026-07-12):**
   per-AOI config registry (`config/*.yaml`, root `config.yaml` = one-line `active_config` pointer),
   `INSAR_CONFIG` env override (per-command AOI targeting for every script), soil parameters moved into
   config (`soil:` block — no more silent Ramban-default inheritance), `workflows/aoi_status.py`
   (multi-AOI stage/alarm dashboard + deterministic next step), `docs/runbooks/NEW_AOI_PLAYBOOK.md` (onboarding
   runbook), `tests/test_config_registry.py`. ~~Fold the <150 m perpendicular-baseline gate into
   rescues~~ ✅ DONE 2026-07-13 (§43 — one standing f106 bridge measured 151 m; a better
   replacement is queued and applies at the next radar-cadence rebuild). Still: AOI guidance
   (a better polygon improves *targeting*, not the noise floor).
   **New-AOI replication readiness:** infra replicability HIGH (config-driven, Dockerized, multi-stack);
   scientific transferability MEDIUM — a new AOI needs (a) ~2–3 months of S1 acquisitions for a velocity
   baseline, (b) a site soil check (Ramban field-calibrated §20; VD literature-corroborated §37 — each
   new site needs its own pass, now recorded in its registry file; **measured to be load-bearing, §42 —
   failure depth especially**), (c) a local inventory for validation
   — the three manual steps the playbook and status dashboard track explicitly.
0b. **GACOS second pull — tooling ready (2026-07-16):** `workflows/gacos_request.py` prints the
   exact form values (bbox, per-track UTC time, missing dates only); `workflows/gacos_ingest.py`
   turns the email tarball into cross-check-ready tifs + the STACKS snippet. The remaining §40
   work is: submit the form, wait for the email, run ingest, run `_gacos_crosscheck.py`.
1. **Accuracy backlog — the ranked plan is COMPLETE:** see `docs/archive/Science Upgrade Plan - Top 3
   (2026-07-13).md` — ~~(1) bootstrap CIs + ablation-baseline ladder~~ ✅ DONE (§44,
   `validation_stats.py`), ~~(2) TWI-distributed saturation m_i~~ ✅ DONE (§45, kappa=0.06 adopted
   both sites; broke VD's §44 slope-only tie), ~~(3) nonlinear van-Genuchten suction curve~~ ✅
   RESOLVED (§46 — mechanism shipped config-gated, adoption rejected: (α,n) not identifiable from a
   spatial inventory; linear stands on evidence). Still behind those:
   lab confirmation of c_dry/c_wet; per-stack ERA5 reference-pixel + unwrapping QC (rescue
   frame102/101, §22).
2. **Visualization:** combined interactive 3-D dashboard over the UNION mosaic; ASC/DESC vertical+EW
   decomposition (DEFERRED — needs better DESC: longer connected series / PS / phase-linking).
3. **Make it live / smarter:** ✅ live rainfall ingestion DONE (`live_alarm.py` incremental ERA5-Land
   + one-command alarm regen; 2–3-day runbook 2026-07-11 — remaining upgrade is sub-daily/per-zone
   IMERG, LIVE roadmap #5). Still open: real flow-routing for LLOF (replace TWI proxy); hybrid LLM
   ("rules decide, LLM narrates").
4. **Deploy/polish:** hosted Streamlit version of the 3-D dashboard.
5. **NISAR (next-season step-change):** launched Jul 2025; L-band global since Aug 2025; 100k+ products on
   ASF Feb 2026; **calibrated forward processing at 1–3 day latency from Jul 2026**. L-band recovers
   coherence over vegetation (our worst enemy) + ships geocoded interferograms via ASF (feeds this
   pipeline). Track ASF availability; start ingestion to build an L-band baseline for the Jul-2026 window.

**Exception to MVP-first (always):** fix correctness/data-integrity bugs immediately; defer quality-only
improvements until shown to matter.

## 4. Expansion roadmap — areas of exploration toward a robust forecasting tool

§3 above is the *near-term hardening backlog*; this is the broader strategic menu (mirrored in
`InSAR_hazard_forecasting_Context.md` for durability). Each **AREA is self-contained**.

**Where the MVP is weakest today:** ~30 mm/yr velocity noise floor; single-look (no true 3-D motion);
uniform soil strength (site-corroborated §20/§37, but one value per AOI) + dry/sat end-members +
TWI-proxy downstream flag; AOI-mean daily rainfall (live, but not sub-daily/per-zone); a
static-vs-worst-case hazard map; recall-limited validation on two small AOIs.

- **Area 1 — Noise reduction:** MintPy ERA5 (done on frame106), ✅ GACOS cross-check (VD, §40 — mixed
  first result, worth a second pull), DEM-error +
  coherence-weighted inversion, phase-linking/DS methods (recover vegetated slopes), <150 m Bperp rule.
- **Area 2 — Signal strengthening:** ASC/DESC → vertical+EW (needs better DESC), PS points on rock/infra,
  longer series → seasonal vs steady-creep split.
- **Area 3 — Map → FORECAST:** inverse-velocity TTF (built), regional ID thresholds (built/verified),
  TWI-distributed saturation ✅ DONE (§45, kappa=0.06); still: calibrated spatially-varying soil,
  real flow-routing for LLOF.
- **Area 4 — Validation & uncertainty:** scored back-test DONE (§16); uncertainty quantification DONE (§24);
  next = a susceptibility model (LR/RF) cross-check + a verified-date temporal test.
- **Area 5 — Multi-sensor corroboration (GEE):** CHIRPS/IMERG/ERA5-Land rainfall, SMAP/ASCAT soil moisture,
  SoilGrids strength, DEM upgrades, WorldCover/NDVI veg masks, Sentinel-2/Landsat optical change, NASA GLC.
- **Area 6 — Operationalize:** ✅ live rainfall ingestion (done — `live_alarm.py` + runbook); hybrid LLM,
  hosted + union 3-D dashboard.
- **Area 7 (physics borrows):** #1 snowmelt/freeze-thaw (done), #2 V_slope (done), #3 regional ID + K_sn,
  #4 matric-suction FS split (done §20; nonlinear van-Genuchten curve BUILT + evaluated §46 —
  rejected on identifiability, config-gated for when lab/temporal data exists).
- **Data upgrade — NISAR (NASA-ISRO, L+S band):** the top future SAR upgrade (L-band beats vegetation
  decorrelation, our worst enemy); operational window from Jul 2026.

**Suggested priority:** (1) ✅ operational two-factor warning + per-zone (§16–§19); (2) ✅ physics/data
upgrades (§20–§21); (3) ✅ recall two-tier + uncertainty + triage (§23–§25); (4) ✅ live rainfall
(`live_alarm.py` + runbook); (5) NISAR ingestion as it matures; (6) susceptibility cross-check
(~~nonlinear suction~~ ✅ resolved §46 — rejected on evidence).

**Robustness in one line:** corroborate InSAR creep with optical change, real rainfall, soil moisture, and a
validated inventory — never trust a single sensor or a single physics assumption.

## 5. End-of-session ritual

Run **`/wrap-session`** before stopping — it appends KPIs to `RESULTS_AND_KPIS.md`, logs bugs, writes the
slim `session_journey.md` entry, adds milestone/primer entries on a completed phase, regenerates the LIVE
block above, and drafts the commit message (the user commits manually). Per-session checklists no longer
accumulate here — that history lives in `session_journey.md` + `git log` (older checklists: see the
archived pre-streamline snapshot).

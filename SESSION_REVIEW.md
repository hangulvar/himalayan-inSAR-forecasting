# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`docs/archive/local/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 27 · branch `aoi-vaishnodevi` · updated 2026-07-18

## Current state

- **★ NEW (§51, M47) — Past-events dashboard tab + curated historical-damage records, verified
  live.** Both dashboards now carry a third tab: each site's documented landslide history ranked
  by damage, every row with a Google Maps link, confidence badge + sources, and its CURRENT alert
  standing (nearest hazard zone + live m*/FS/creep). Records live in NEW committed files
  (`data/inventory/*_historical_events.json`) — the back-test inventories are deliberately
  untouched so the validated scores stay earned. Verified two rounds: 11-test new suite
  (`tests/test_historical_events.py`), full battery ×2 green, idempotent regen, browser
  click-through, 12/12 cross-links, live source-URL checks (all in §51).
- **★ NEW (§52) — two review rows RESOLVED → the gate's first two in-season 2026 catches, both
  Δ=0.** Digdol was a REAL separate slide, 7 Apr 2026 (user verdict + 4 independently dated
  outlets) — and 7 Apr was an **ALERT day (E=2.13)**: alarm raised the day NH-44 was buried. New
  verified VD event 8 Jul 2026 (Himkoti new track, battery-car suspended) fell on a **WATCH day
  (E=1.06)** — armed, proportionate to a no-casualty blockage. Both folded into the temporal
  inventories (§38 precedent, no spatial re-score). All dashboard links now open in NEW tabs
  (`<base target="_blank">`).
- **⚠ USER REVIEW still open (§51/§52): 2 rows** — VD 2008 Bhawan date (GSI Aug-vs-Dec internal
  discrepancy; resolve via Kumar 2009a) and the VD undated pre-2017 Himkoti casualty rockfall.
  Both render as "pending review" on the dashboard until settled.
- **★ NEW (§53) — live staleness guard on the alarm banner.** The static snapshot now computes
  its own age against the VIEWER's clock at open time: 🕐 normal ≤8 d (the stated ~5-day ERA5
  lag + cycle cadence), ⚠ amber >8 d (refresh likely missed), red >14 d "TREAT THE ALARM STATE
  AS UNKNOWN". Verified with the page's own script at 7/10/20 days; suite asserts the element +
  thresholds.
- **§38's fabricated-event exclusion is now TEST-enforced** (closure-window + no-future-date
  assertions) — the immunization records became executable checks.
- **(§50, M46 carried):** control panel + results hub live; repo restructured (`docs/INDEX.md`
  maps old→new); suites now SEVEN all green (**7 + 12 + 10 + 11 + 12 + 11 + compose valid**).
- **(§49–§44 carried):** full-product audit zero bugs; zips disposable; kappa=0.06 adopted both
  sites; CIs + ablation ladder standing — Science Upgrade Plan top 3 ALL RESOLVED.
- **BOTH sites in WATCH** (as-of 2026-07-11 data, re-confirmed by this session's regen runs):
  VD 18/18 zones active, 0 ALERT days; Ramban 8/8 active, 4 April ALERT days. Next scheduled
  cycle **19 Jul 08:00**; the cycle checks Docker (10-min grace), never manages it.
- **GACOS pair ready (§0b):** submit the form → ingest → crosscheck remain. **Radar (§35/§43):**
  July S1 passes still pending at ASF; §43 f106 bridge swap applies at next rebuild. **NISAR:**
  recheck ~early Aug (§33).
- **Ramban: COMPLETE, scored, LIVE** (§21b, CIs §44). **Vaishno Devi: validated + site-tuned**
  (§26–§32, §44 caveat). Merge `aoi-vaishnodevi` → `master` remains the user's call.
- **Honest limits carried:** creep core 0 vs corridor inventory (CV3); 598 m miss at the disaster
  site (§31 addendum) — now VISIBLE on the dashboard itself (§51: 4/5 Ramban historical damage
  sites outside today's footprint, stated with the unmeasured≠safe caveat); soils
  literature-corroborated not lab-measured (§37/§39/§42/§47); §40 GACOS discrepancy pair open.
- **⚠ Archival note (§48):** the Google Drive copy of the 235 raw zips is the ONLY archival
  source (ASF server copies expired; re-creation costs HyP3 credits ≈7,460 remaining).

## Recommended next step

First: **user reviews the 2 remaining flagged rows (§52)** — settle or drop them. Then the
product roadmap is unchanged (STABLE §3/§4): **radar cadence when July passes land** (resubmit →
download → QA → multistack → re-score, applying the §43 f106 bridge swap), then the failure-class
gap (Sentinel-2 optical change) and sub-daily IMERG. User-side: field check of the NE-flank CORE
target; merge to `master`; publish the dashboard. Day-to-day ops: start Docker at logon, then
either let the scheduled cycle run or double-click `control_panel.bat` and press the button.

## Uncommitted delta

Session 27's earlier batches are already committed by the user: `c618ca2` (Past-events tab +
curated records + first 10 tests), `6066cb0` (wrap: §51, M47), `dc6ff7d` (§52 review round:
Digdol resolved, Himkoti added, both Δ=0 catches, new-tab links).

Still uncommitted (the §53 staleness-guard batch + this wrap):
- MODIFIED: `workflows/operational_alarm.py` (staleness element + view-time escalation script),
  `tests/test_historical_events.py` (staleness assertions), `RESULTS_AND_KPIS.md` (§53),
  `error_history_log.md` (1 entry, 2026-07-18), `SESSION_REVIEW.md` (this block).
- Git-ignored as usual: journey entry (S27 cont. 2). Primer + milestone unchanged (minor
  hardening, no new science concepts; M47 already tells this feature's story).

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

> **Docs restructured 2026-07-17:** all reading material (guides, runbooks, field briefs,
> references, archive) now lives under `docs/` — start at `docs/INDEX.md`, which also maps every
> old path to its new home. The functional docs in the table above stay at the project root.

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

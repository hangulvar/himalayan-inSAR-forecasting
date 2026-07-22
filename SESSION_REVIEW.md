# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`docs/archive/local/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 28 · branch `aoi-vaishnodevi` · updated 2026-07-22

## Current state

- **★ NEW (§61) — the Ramban cadence rebuild FIRED: 30 credits spent, 3 products QA-passed, the
  S1A×S1D cross-unit seam DE-RISKED.** User authorised the 3-pair manifest; all queued (credits
  7,460→7,430, verified), all SUCCEEDED, downloaded + extracted + QA'd. **Both gates passed for
  all 3 — including the S1A×S1D 7-day seam (usable coherence + atmospherically clean):
  cross-satellite interferometry works over Ramban's terrain** (the §56 handover's biggest risk).
  Radar library 235→238; all QA artifacts re-synced. Numbers §61.
- **★ Seam-velocity cross-check DONE (§61), S1D seam DROPPED, full rescore DEFERRED (user).**
  Frame renumber f106→f105 / f102→f103 = SAFE (coherent bridge IFG). S1A→S1D handover carries a
  clean **−18.6 mm** offset (no spatial distortion but unvalidated first cross-unit pair) →
  **rebuild S1A-only through 18 Jun**, revisit S1D later. Cross-unit `S1AA_`-parser bug found +
  fixed across 5 files (+ test; **battery 98 green**). The faithful S1A-only rescore needs the
  REAL pipeline (`consolidate → apply_connectivity_rescues → run_multistack → GSI rescore`) — a
  non-destructive sandbox can't reconstruct the rescue-aware network (confirmed 3×). Deferred to a
  focused next session; validated product stays live + untouched. Scripts in `data/rebuild/`.
- **★ NEW (§60-cont., committed `50f4df3`) — routed-LLOF swap SHIPPED config-gated.**
  `llof_routing: twi|d8` (default `twi` = validated products byte-identical, probe re-run
  hash-verified); d8 reuses the probe's exact criterion. Post-merge swap = uncomment `d8` per
  site + regenerate + re-score. A latent window-clamp bug was caught by the new tests + fixed.
- **★ NEW — submitter hardened:** prefix-AGNOSTIC dedupe (shared library — the prefix-filtered
  scan would have re-bought 9 already-processed products, ~90 credits) + `--pair` mode for
  frame-drift/seam bridges. New suite `tests/test_submit_pairs.py`. Battery now TEN suites,
  **97 green**.
- **⚠ USER REVIEW still open (§52): 2 rows, evidence now gathered.** Himkoti casualty row →
  recommend **30 Jun 2017** (SMVDSB request letter is same-day as the fatal boulder; 2 outlets).
  2008 Bhawan Aug-vs-Dec → **cannot be settled online** (dead-ends at the unpublished Kumar 2009a
  GSI report; compendium §5.4.4 body=30 Aug adopted, heading=30 Dec) — recommend keep 30 Aug or
  keep flagged pending a GSI report request. Inventory rows untouched pending the user's verdict.
- **(§55–§59 carried):** sub-daily IMERG burst gate shipped experimental (ALERT E≥3, §58);
  NISAR pilot confirms L-band recovers 75–87% of C-band's failure-class pixels (§59); radar
  watcher + freshness pill live (§57). Active plan: `docs/references/STRENGTHENING_PLAN_2026-07-18.md`.
- **(§60, M50, CF15 carried):** susceptibility cross-check exposes corridor bias (the ML map
  mostly reads the road); optical change screening-grade; temporal-skill table committed + tested.
- **BOTH sites in WATCH (§54): as-of 2026-07-12** (VD 18/18 zones active, 0 ALERT; Ramban 8/8,
  4 April ALERT days). The scheduled cycle checks Docker (10-min grace), never manages it.
- **Ramban: COMPLETE, scored, LIVE** (§21b, §44) — the rebuild will *re-score* it, not replace
  the standing product until then. **Vaishno Devi: validated + site-tuned** (§26–§32).
  Merge `aoi-vaishnodevi` → `master` remains the user's call.
- **Honest limits carried:** creep core 0 vs corridor inventory (CV3); 598 m miss at the disaster
  site (§31/§51); soils literature-corroborated not lab-measured (§37/§39/§42/§47); §40 GACOS
  discrepancy pair open. Archival (§48): the Drive copy of the raw zips is the only archival source.

## Recommended next step

**The deferred S1A-only rebuild rescore (§61) — a focused next session.** The seam check is done
and S1D is dropped, so the rebuild is unambiguous: (1) back up `data/qa_masks/_quarantine_list.csv`
+ `_stack_manifest.json` (revert path), (2) run the REAL pipeline — `consolidate →
apply_connectivity_rescues` (applies the §43 f106 bridge swap) `→ run_multistack` (invert→hazard→
alerts→mosaic, **S1A-only: the two frame bridges + f105/f103 chains through 18/23 Jun, NOT the
S1D seam**) `→ GSI rescore`, (3) **compare new AUC/recall vs §21b/§44 as the pre/post** before
accepting; revert via the backup if it regresses. In parallel: **user settles the 2 §52 rows**
(evidence §61/journey), and optionally flips `llof_routing: d8` as its own scored swap. User-side
(standing): GACOS form + soil lab; merge to `master`; publish the dashboard.

## Uncommitted delta

Session 28's Task 1–3 batch is **already committed by the user** (`50f4df3`: LLOF swap + manifest
+ §52 evidence). Uncommitted now (the rebuild-execution + wrap batch):
- MODIFIED (tracked) — two logical batches:
  - **Parser fix:** `workflows/{custom_sbas_inverter,sbas_network_graph,stacks,coherence_watch,
    _analyze_qa_stats}.py` (`S1AA_`→`S1[A-D][A-D]_`) + `tests/test_science_verification.py`
    (new cross-unit parse test).
  - **Docs/wrap:** `RESULTS_AND_KPIS.md` (§61 + seam-check + deferred plan), `error_history_log.md`
    (parser bug + Bash path-mangling), `docs/references/RAMBAN_REBUILD_MANIFEST_2026-07-19.md`
    (SUBMITTED + QA, cites §61), `SESSION_REVIEW.md` (this block).
- Git-ignored (data/ + journals): the 3 new products under `data/processed_tiffs/` +
  `data/raw_zips/`, re-synced `data/qa_masks/{_stack_manifest.json,_coherence_mask_stats.csv,
  _atmospheric_audit.csv,audit_log.json}`, `data/rebuild/` (window yaml + `seam_check.py`/
  `sandbox_velocity.py` diagnostics + their reports), the S28 journey entry.
- **Next:** the deferred S1A-only rebuild rescore (§61) — a focused next session.

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
- HyP3 credits: **~7,430 as of 2026-07-22** (§61 — 30 spent on the Ramban rebuild; was 7,460). Radar library 238 products. Disk: ~46 GB in `data/` (§48 — raw zips Drive-archived + deleted 2026-07-15).
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
   + one-command alarm regen; 2–3-day runbook 2026-07-11). ✅ **Sub-daily IMERG burst gate DONE
   2026-07-18 (§55, experimental second opinion** — `imerg_gate.py` + dashboard card + non-fatal
   live_alarm hook; remaining: per-zone IMERG from the 0.1° grid + earning this arm back-tested
   operating points). Still open: real flow-routing for LLOF (replace TWI proxy); hybrid LLM
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
TWI-proxy downstream flag; rainfall now two-arm (daily AOI-mean validated + sub-daily IMERG
experimental §55) but still not per-zone, and the burst arm lacks back-tested operating points; a
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

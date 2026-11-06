# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`docs/archive/local/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 40 · branch `aoi-vaishnodevi` · updated 2026-11-06

## Current state

- **✅ Python 3.12 upgrade DONE** in the native env and the `insar` image; MintPy stays on 3.11 with
  numpy<2 by design (§89A). Rollback: `insar_qa_env_py310_old`, `insar-himalaya:py310-backup`,
  `insar-mintpy:pre-upgrade-backup`.
- **✅ Battery green in the container and natively** (§89A), closing §88's "not run in Docker" gap.
  pip-audit clean on native and `insar`. **Open:** MintPy's `tornado` advisories (no compatible build
  yet; low risk) and Docker OS packages (unscanned).
- **✅ 2026 season refreshed to 30 Oct at all sites**, live chain proven on the new images, Copernicus
  login verified by use (§89C). Both live sites DORMANT.
- **⚠ Unscored:** whether anything failed on VD's 19–20 Aug ALERT days, or anywhere Aug–Oct. Needs a
  verified late-season inventory pass.
- **★ §20's unit flag closed, and 3 new soil caveats opened** (§89B): the GSI report doubts its own
  lab data, carries two φ ranges, and its density ≈15.7 kN/m³ vs the model's 19. No value changed.
- **Radar is still stale** (Ramban library May, VD August); the rebuild decision is unchanged, with
  new counts in §89C. NISAR volume gate met; all products checked in §88D still provisional.
- **✅ Plotly tamper pin is live** in both 3-D dashboards; only the tag and date stamp changed (§89D).
- **Freeze re-baselined at 140** after a 4-file, documented-cause change. **↪ It was never 116 by §88**;
  corrected in §89D.
- **New for the user:** `docs/guides/Soil and Inventory - A Plain Guide.md`.
- **Carried honest limits unchanged:** VD WHERE below chance (§80); NISAR monsoon unmeasured (§82);
  inventory records REPORTS (§60/§83); ~30 mm/yr noise floor (§78); Triund has no AUC by design (§87).

## Recommended next step

**All remaining items are the user's.** Status report §5, in order, skipping the two now done:

1. **Ramban radar rebuild go/no-go** (§89C). Extend `search_end` past the newest scene before the
   dry-run; fold in the §61 rescore; add a **γ=16 sensitivity run** (§89B).
2. **The 2 VD history rows** pending review.
3. **NISAR monsoon pilot**, labelled provisional.
4. **Tosh:** soil pass + inventory using the new guide, radar decision before ~Feb. First exercise:
   verify the Jeera Nullah slide (§89E).
5. **Delete the 4 unused keys from `.env`**; decide Triund archive vs new date.
6. Retry the `tornado>=6.6` pin in MintPy; once happy, delete the rollback env and image tags.

**Do NOT:**
- republish the Triund dashboard without `check_dashboard_render.py`;
- treat the 2–3-day rainfall cadence as needed before 2027-04-01 (season start);
- wire NISAR live while every product is `PR`;
- change Ramban's γ or φ on §89B alone — those are questions, not findings;
- loosen the control-panel guards — each one encodes a probed exploit;
- re-enable the scheduled task without answering the missed-slot and Docker-down questions.

## Uncommitted delta

Code / specs:
- `docker/Dockerfile`, `docker/mintpy.Dockerfile`, `docker/environment.docker.yml`,
  `docker/conda-linux-64.lock`, `environment.yml`.

Docs:
- NEW `docs/guides/Soil and Inventory - A Plain Guide.md` + `docs/INDEX.md`, playbook links;
- `RESULTS_AND_KPIS.md` §89 (+ ↪ on §88A);
- `error_history_log.md` (2026-11-06);
- `milestone.md` M70;
- primer Part E (+1 limit);
- status report (update note + 140 correction);
- this LIVE block + 1 STABLE fact;
- `session_journey.md` (git-ignored).

Outside git:
- `data/`: refreshed season files, `aoi_status.*`, `radar_watch.json`, both `dashboard_3d.html`, new
  freeze baseline;
- `logs/refresh_cycle_2026-11-06.log`;
- the Windows task "InSAR Monsoon Watch Cycle" is still **Disabled**.

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
| 9 | `docs/guides/InSAR_hazard_forecasting_Context.md` | Original vision / full expansion roadmap — **read it before judging whether a proposed change is a deviation** (§83: the "pivot" turned out to be Area 4/5 work already in the plan) | Reference |

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

- Env (native): `insar_qa_env` at `C:\Users\varun\.conda\envs\insar_qa_env\` — **Python 3.12 since
  2026-11-06** (§89A); no jupyterlab. The old 3.10 env is parked as `insar_qa_env_py310_old`.
- **Two condas on this machine:** the user-level `C:\Users\varun\miniconda3` is **4.12** (the solver
  that hangs); do env work with `C:\ProgramData\anaconda3\Scripts\conda.exe` (24.11, libmamba). Use
  `conda create -p … --override-channels -c conda-forge` — `conda env create` rejects channel flags.
- HyP3 credits: **8,000 verified 2026-10-25** (§88D; monthly allotment — ~7,900 on 2026-08-08 after §77). Radar library **248 products** (238 + 10 §77). Disk: **56 GB** in `data/` measured 2026-08-11 (§48/§77/§83 — raw zips Drive-archivable; +~3 GB from the §77 refresh, and **`data/nisar/` is now 5.7 GB** across 3 granules plus ~160 MB of adapted rasters).
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
   runbook), `tests/test_config_registry.py`. **Registry holds FOUR sites since 2026-09-07 —
   `ramban`, `vaishnodevi`, `tosh` (upper Parvati Valley, §84) and `triund` (Dhauladhar, §87).
   Both new sites sit at playbook step 2: Tosh blocked on its soil pass (M2), its inventory (M4)
   and the user's go/no-go on ~34 HyP3 jobs; Triund blocked on the same three plus M3, and
   additionally the only site whose published product carries NO validation score by design.**
   ~~Fold the <150 m perpendicular-baseline gate into
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
   live_alarm hook). ~~earning this arm back-tested operating points~~ ✅ DONE 2026-07-25 (§63 —
   false-alarm rate measured against the validated arm on one yardstick; §64 — ALERT k lowered
   3.0→2.4 on that evidence, all 4 fatal events now caught at Δ=0). Remaining: per-zone IMERG
   from the 0.1° grid. Still
   open: real flow-routing for LLOF (replace TWI proxy); hybrid LLM ("rules decide, LLM narrates").
4. **Deploy/polish:** hosted Streamlit version of the 3-D dashboard.
5. **NISAR (step-change): the forward stream ARRIVED 2026-07 as predicted (§65).** L-band recovers
   coherence over vegetation (our worst enemy, §59: 75–87% of C-band's failure class) + ships
   geocoded interferograms via ASF. **Now the freshest radar over Ramban by ~10 weeks.** ~~Track ASF
   availability~~ ✅ done (watcher). **Open:** the monsoon L-vs-C confirmation is blocked by NaN
   voids over both AOIs in the provisional (`_PR_`/`P05023`) granules — n=2, systematic. Re-check
   after NASA reprocesses, or when an acquisition lands with our footprint outside the void; scoring
   is one command (`nisar_coherence_pilot.py --season monsoon`) and aborts honestly if still void.
   (2026-07-28 §68: the publicized "fresh batch" = the 20 Jul public release of this same stream —
   nothing new over our AOIs yet.) **2026-10-25 §88D: 22 GUNWs over both AOIs — the ≥8-acquisition
   volume gate is MET (ASC track 156/frame 018: 11 dates; DESC track 135/frame 072: 12), the
   final-product gate is NOT (all `PR`).** The monsoon pilot is runnable now, labelled provisional.
   Also newly available and unexploited: **DESC track-135 L-band GUNWs** — a possible route back to
   the ASC/DESC vertical+EW decomposition that C-band DESC was too noisy for (Area 2).

**Exception to MVP-first (always):** fix correctness/data-integrity bugs immediately; defer quality-only
improvements until shown to matter.

## 4. Expansion roadmap — areas of exploration toward a robust forecasting tool

§3 above is the *near-term hardening backlog*; this is the broader strategic menu (mirrored in
`InSAR_hazard_forecasting_Context.md` for durability). Each **AREA is self-contained**.

**Where the MVP is weakest today:** ~30 mm/yr velocity noise floor; single-look (no true 3-D motion);
uniform soil strength (site-corroborated §20/§37, but one value per AOI) + dry/sat end-members +
TWI-proxy downstream flag; rainfall now two-arm (daily AOI-mean validated + sub-daily IMERG
experimental §55) but still not per-zone, and the burst arm's operating points rest on n=7 events
(its alarm COST is now measured, §63; its skill is still a small calibration set, not a
validation); a static-vs-worst-case hazard map; recall-limited validation on two small AOIs.

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
- **Area 6 — Operationalize:** ✅ live rainfall ingestion (done — `live_alarm.py` + runbook);
  ✅ affected-area layer (done 2026-08-11, §84 — zone outlines + downstream corridors as
  GeoJSON/KML/dashboard card/3-D toggle, `exposure_footprint.py`); hybrid LLM, hosted + union
  3-D dashboard.
- **Area 7 (physics borrows):** #1 snowmelt/freeze-thaw (done), #2 V_slope (done), #3 regional ID + K_sn,
  #4 matric-suction FS split (done §20; nonlinear van-Genuchten curve BUILT + evaluated §46 —
  rejected on identifiability, config-gated for when lab/temporal data exists).
- **Area 8 — Flash-flood & undercut arm (PLANNED 2026-07-28, §68):** additive, config-gated,
  Regime-A-only (tributary flash floods / toe erosion); plan of record =
  `docs/references/FLOOD_EXPANSION_PLAN_2026-07-28.md` (F0–F3 phases, scope exclusions, test contract).
- **Data upgrade — NISAR (NASA-ISRO, L+S band):** the top future SAR upgrade (L-band beats vegetation
  decorrelation, our worst enemy); operational window from Jul 2026. **PROVEN on our own ground
  2026-08-11 (§81) and the ingestion path is BUILT (§83,
  `docs/references/NISAR_INGESTION_DESIGN.md`)** — no longer a "future" item but a data-gated one:
  the adapter waits on acquisition volume (≥8 on one track/frame) and on final, non-provisional
  products.

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

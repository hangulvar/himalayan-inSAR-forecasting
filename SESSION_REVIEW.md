# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`docs/archive/local/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 32 · branch `aoi-vaishnodevi` · updated 2026-08-08

## Current state

- **★★ NEWEST (§79) — the §78 plan's items 1 & 2 are DONE, and item 2 changed the verdict on the
  product.** Re-scoring the rebuilt VD map against the inventory returned **AUC 0.326 with 0/47
  documented locations detected** — and **random null points sit CLOSER to the flagged zones
  (2.55 km) than real landslides do (3.58 km)**. Both tiers now score **below chance** (≥2-look
  core 0.303). This is independent confirmation of §78's noise-limited diagnosis.
- **⚠⚠ THE HEADLINE FOR THE PRODUCT:** VD's **WHERE** map is currently **unusable on its own
  merits** — ALERT is empty, WATCH scores below chance. The dashboard now says both plainly. The
  **WHEN** arm (rainfall / burst / flood) is unaffected and still validated. **The fix is not a
  threshold, it is more radar** (§78 item 3).
- **★ (§79) The period split is STICKY — the silent-regression footgun is CLOSED.** New registry
  key `period_split: {stack: YYYY-MM-DD}` (validated at load), honoured by
  `run_multistack.connected_stacks()` and passed through as `--max-date` so it survives `--force`.
  Verified both ways; a plain `run_multistack` now keeps path27 and reproduces the union
  bit-for-bit. 3 tests incl. a negative control.
- **★ (§79) Four honesty defects fixed, all on a page read as a warning:** hard-coded "beats
  chance"/"≈chance" replaced by a verdict **derived** from the AUC (renders "BELOW chance" now); a
  stale `validation_stats` overlay that was masking the fresher, worse score now checks the
  footprint it measured; an empty footprint no longer **takes down the whole daily arm**
  (`per_zone_gate` publishes the empty state and exits 0); and "no zone data at this site *yet*"
  (reads as *never mapped*) is now "today's mapped footprint is empty".
- **★ (§78 carried) ROOT CAUSE of the empty ALERT tier — noise-limited, not broken.** 844 `FS<1`
  px vs ~4–5k creep px → **5–7 overlapping px, 0 clusters**; σ(hp velocity) 45–75 mm/yr puts the
  −15 mm/yr creep threshold at **0.20–0.33σ**, selecting ~37% of pixels. The old 14-zone map
  deserves the same scepticism.
- **★ (§77/§78 carried) The cadence refresh itself was a success:** 10 new pairs, **both S1A→S1D
  seams CLEAN**, hazard map advanced 06-25 → **08-05**, freshness pill cleared, live 2026 page
  correct (`data-acq=2026-08-05`, `data-asof=2026-08-02`).
- **Battery 184 → 190 green, 14/14 suites.** Freeze re-verified and re-frozen at **116** (10
  changed: 8 mine + **2 Ramban files written by the scheduled `monsoon_cycle` at 14:21**, proven by
  mtime; 0 missing/added).
- **⚠ Ramban carries the standing staleness warning:** 16 new ASC scenes through 08-05, rebuild
  UNBLOCKED — the loop now proven on VD, and it folds in the deferred §61 S1A-only rescore.
- **Flood arm (§69–§76) complete**; **F2** (creep×flood undercut coupling) is its next phase.
- **Carried honest limits:** VD WHERE below chance / ALERT empty (§79); ~30 mm/yr noise floor
  (§78); creep core 0 vs corridor inventory; 598 m miss (§31/§51); soils literature-corroborated
  not lab; §40 GACOS open; Drive copy of raw zips is the only archival source (§48).
  **⚠ Standing:** §52 — 2 inventory rows pending verdict; §66 LOW web findings.

## Recommended next step

**Item 3 of the §78 plan is now the ONLY thing that fixes the product — everything cheaper is
done.** In order:

1. **Cut the velocity noise floor — invert the LONG stacks.** `ASC_path100_frame102`,
   `ASC_path27_frame101`, `ASC_path27_frame106` hold **49 products each** (vs 8–9 in the
   frame103/105 pair currently carrying the map). They are marked *disconnected*, so the newly
   built `period_split:` mechanism is exactly the tool: pick each one's cutoff from
   `_connectivity_report.md`, add it to the registry, re-run. Longer series → smaller σ → a creep
   mask that is signal rather than noise. **Re-score after** — that is the pass/fail.
2. **Do NOT tune m / the creep threshold to make zones reappear** — with σ this large that is
   manufacturing a result. Recorded here so a future session does not "fix" it that way.
3. **Then** the Ramban cadence refresh (+ §61 rescore), or flood **F2**.

User-side (standing): settle the 2 §52 rows; GACOS form + soil lab; merge `aoi-vaishnodevi` →
`master`; publish the dashboard — **note the VD WHERE map should not be published as a hazard
product until item 1 lands.**

## Uncommitted delta

`config/vaishnodevi.yaml` `search_end` → 08-08 is committed (`e50cce3`). Uncommitted:
- `workflows/config.py` — NEW `period_split` field + `_period_split()` load-time validator.
- `workflows/run_multistack.py` — `connected_stacks()` includes period-split stacks;
  `run_phases_per_stack` passes `--max-date` (survives `--force`).
- `workflows/custom_sbas_inverter.py` — `--max-date` period split (+ date-vs-datetime fix).
- `workflows/operational_alarm.py` — `scored_zones` + score withdrawal; `_chance_verdict()`;
  `validation_stats` overlay gated on `n_zones`; `mapped_but_empty` caption.
- `workflows/per_zone_gate.py` — empty footprint publishes the empty state and exits 0.
- `config/vaishnodevi.yaml` — `period_split: {ASC_path27_frame105: 2026-07-07}` (load-bearing,
  commented as such).
- `tests/` — `test_config_registry.py` 9→12, `test_historical_events.py` 15→19. **184 → 190.**
- `RESULTS_AND_KPIS.md` §79 (+§78, +3 ↪ corrections on §77); `error_history_log.md` (+5 defects);
  `milestone.md` M60 + correction; `session_journey.md` (git-ignored); this file.
- **Git-ignored data:** VD velocity/hazard/alerts/mosaic rebuilt, **backtest_watch reports
  re-scored**, 2026 daily-arm + dashboard regenerated, `_baseline_freeze.json` re-frozen (116).

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
- HyP3 credits: **~7,900 as of 2026-08-08** (§77 — 8000 verified pre-refresh, ~100 on the VD cadence refresh; the §61 7,430 balance replenished since). Radar library **248 products** (238 + 10 §77). Disk: ~49 GB in `data/` (§48/§77 — raw zips Drive-archivable; +~3 GB from the §77 refresh).
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
   nothing new over our AOIs yet.)
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
- **Area 6 — Operationalize:** ✅ live rainfall ingestion (done — `live_alarm.py` + runbook); hybrid LLM,
  hosted + union 3-D dashboard.
- **Area 7 (physics borrows):** #1 snowmelt/freeze-thaw (done), #2 V_slope (done), #3 regional ID + K_sn,
  #4 matric-suction FS split (done §20; nonlinear van-Genuchten curve BUILT + evaluated §46 —
  rejected on identifiability, config-gated for when lab/temporal data exists).
- **Area 8 — Flash-flood & undercut arm (PLANNED 2026-07-28, §68):** additive, config-gated,
  Regime-A-only (tributary flash floods / toe erosion); plan of record =
  `docs/references/FLOOD_EXPANSION_PLAN_2026-07-28.md` (F0–F3 phases, scope exclusions, test contract).
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

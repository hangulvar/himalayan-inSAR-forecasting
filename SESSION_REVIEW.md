# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`docs/archive/local/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 33 · branch `aoi-vaishnodevi` · updated 2026-08-11

## Current state

- **★★ NEWEST (§80) — item 3 is DONE, and it settles the question.** More radar history fixed the
  MEASUREMENT (scatter σ **75 → 25 mm/yr**; absurd-speed pixels **46–60% → 2–4%**) but did **NOT**
  fix the MAP. Five scored configurations — the 4-angle union, the ≥2-look core, and each history
  alone — **all score below chance and all detect 0/47** documented landslides.
- **★★ The deeper finding: clean the noise and the creep signal largely disappears.** The cleanest
  history (`frame101`) flags **zero** zones; the next cleanest (`frame102`) flags 4, ~8 km from the
  nearest documented failure. The 2026 zones were substantially noise — removing it removes the
  zones rather than relocating them onto real landslides. **There is little or no detectable C-band
  creep over this AOI** — the measured form of the standing "creep core 0 vs corridor inventory"
  caveat.
- **★ Structural lesson worth carrying (§80):** a union across looks **propagates the worst look's
  noise** — adding two clean histories left the union's score bit-identical, because "flag if ANY
  look flags" is an OR over false positives too. Requiring ≥2-look confirmation did not rescue it
  either. *More evidence only helps if the combining rule can REJECT, not just accept.*
- **⚠⚠ VERDICT ON THE VD "WHERE" PRODUCT — do not publish it as a hazard product.** C-band creep
  does not identify this AOI's failures at any history length or confirmation level we can build.
  The dashboard says so in plain words ("BELOW chance — random points score better than this map").
  **The WHEN arm (rainfall / burst / flood) is untouched and remains validated.**
- **★ (§80) Two long 2025 histories are now IN the product** (`frame102`, `frame101` via
  `period_split:`), kept on evidence: 3× less scatter and cross-confirmed hazard pixels
  **150 → 246**, even though the score is unchanged. `frame106` is deliberately excluded — its
  network is fine but it has too few usable pixels over this AOI to anchor a solution; a comment in
  the registry says so, and says NOT to "fix" it by lowering `--min-pairs`.
- **★ Side benefit, pinned by a test:** VD now has **2 winter C-band pairs** (was 0), so it can join
  the **NISAR L-vs-C** comparison it was a documented not-comparable case for.
- **★ (§79 carried) The period-split rescue is STICKY and the page is honest:** config-driven,
  survives `--force`; chance verdicts are derived not asserted; a stale `validation_stats` overlay
  can no longer mask a fresher worse score; an empty footprint no longer takes down the daily arm.
- **★ (§77/§78 carried) The cadence refresh itself was a success:** 10 new pairs, both S1A→S1D seams
  clean, map current to **2026-08-05**, freshness pill cleared.
- **Battery 190 green, 14/14 suites. Freeze re-set 116 → 140** (24 new protected artifacts = the two
  added histories' products; 8 changed, 2 of them Ramban daily-arm files written by the scheduled
  `monsoon_cycle` at 15:42, proven by mtime; 0 missing).
- **⚠ Ramban still carries its staleness warning:** 16 new ASC scenes through 08-05, rebuild
  unblocked; folds in the deferred §61 S1A-only rescore.
- **Carried honest limits:** VD WHERE below chance at every configuration (§80); ~30 mm/yr noise
  floor now measured (§78); 598 m miss (§31/§51); soils literature-corroborated not lab; §40 GACOS
  open; Drive copy of raw zips is the only archival source (§48). **⚠ Standing:** §52 — 2 inventory
  rows pending verdict; §66 LOW web findings.

## Recommended next step

**The cheap fixes are exhausted — the WHERE product now needs a change of SENSOR or of METHOD, not
more C-band.** Two candidates, either is a proper piece of work:

1. **NISAR L-band (the sensor route).** Long-wavelength radar sees through vegetation, which is our
   worst enemy here (§59) and the most likely reason C-band sees nothing. VD is **newly comparable**
   (2 winter pairs, §80), the forward stream has arrived (§65), and `nisar_coherence_pilot.py`
   already runs the C-vs-L comparison in one command. **Start here** — it directly tests the
   suspected cause.
2. **A terrain-susceptibility model (the method route).** Rank slopes on terrain + rainfall history
   and validate directly against the inventory, using creep as ONE input rather than a gate. This is
   the long-standing "susceptibility cross-check" (roadmap Area 4) and it does not depend on
   detecting creep at all.

**Do NOT** loosen `m`, the creep threshold, or the cluster size to make zones reappear — five
honest failing scores beat one fitted number, and this is now written into the ledger.

Then: the **Ramban cadence refresh** (+ §61 rescore), or flood **F2**. User-side (standing): settle
the 2 §52 rows; GACOS form + soil lab; merge `aoi-vaishnodevi` → `master`. **Publishing the VD
dashboard should wait** for one of the two routes above.

## Uncommitted delta

- `CLAUDE.md` (**git-ignored**, local-only) — NEW section 0: explain in plain language (chat +
  decisions, not just docs).
- `config/vaishnodevi.yaml` — `period_split:` extended with the two long 2025 histories + a
  commented exclusion for `frame106`.
- `tests/test_radar_watch.py` — the NISAR pair-selection test now pins VD's new 2 winter pairs
  (was 0) and that VD's set is a strict subset of Ramban's.
- `RESULTS_AND_KPIS.md` §80; `milestone.md` M62; `session_journey.md` (git-ignored) S33;
  this file.
- **Git-ignored data:** velocity + hazard + per-stack alerts for `frame102`/`frame101` (NEW),
  union mosaic + alerts rebuilt from 4 angles, `backtest_watch*` re-scored, 5 `probe_*` scoring
  reports (scratch evidence, not protected), dashboard + daily-arm regenerated,
  `_baseline_freeze.json` re-frozen at **140**.

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

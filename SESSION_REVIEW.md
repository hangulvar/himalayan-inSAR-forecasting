# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`Research/Archive/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 21 · branch `aoi-vaishnodevi` · updated 2026-07-13

## Current state

- **★ NEW (§45, M42) — TWI-distributed saturation, kappa=0.06 ADOPTED (Science Upgrade Plan #2 DONE):**
  each pixel now gets m_i = clip(m + kappa·(TWI_i − TWI_mean), 0, 1) in the FS_real build (config
  `kappa` key, default 0 = uniform/§44, byte-identical regression gate). Swept via
  `rainfall_selectivity_backtest.py --kappas`; **both AOIs independently peaked at kappa=0.06**.
  **VD operational 0.707→0.757 — now BEATS its §44 slope-only ablation tie** (14 zones vs 155);
  Ramban 0.640→0.676; both WATCH tiers held/improved (VD watch recall 0.913→0.957). Honest limits
  (§45): ALERT-AUC CIs overlap (win = footprint economy + breaking the tie, not a decisive jump);
  ALERT recall trades down (WATCH carries recall); kappa is spatial, can't change the §17 ALERT-day
  count. Adopted in both configs; dashboards/per-zone/validation_stats regenerated at 0.06.
- **★ (§44, M41) — validation statistics (Science Upgrade Plan #1 DONE):**
  `workflows/validation_stats.py` — bootstrap 95% CIs (B=10k), permutation p for "beats chance"
  (B=10k), and a dumb-baseline **ablation ladder** (slope / logistic slope+TWI / physics-only /
  creep-only) scored with the identical zone-centroid distance-ROC protocol, every rung tuned to
  its own best score. Both ALERT maps beat chance at p=0.0001; both WATCH tiers ≈chance (recall
  nets, as always stated). **Ramban: the fusion beats every rung** (its two ingredients are each
  ≈chance alone). At κ=0 VD **tied** slope≥40° on the corridor n=46 inventory — the §45 kappa
  upgrade (above) later broke that tie. The ladder is the fixed bar every upgrade is judged against;
  a stale VD dashboard AUC (0.696/n=41) was found and structurally fixed (error log 2026-07-13).
- **BOTH sites are in WATCH (as-of 2026-07-07, chains regenerated this session at κ=0.06 via
  `live_alarm.py`):** VD 18/18 per-stack active (was 29 at κ=0 — tighter footprint), 0 ALERT days;
  Ramban 8/8 active, 4 April ALERT days. The scheduled monsoon cycle (roadmap item 0) covers the
  cadence; manual fallback per
  `Research/Monsoon Watch Runbook (2026-07-11).md`.
- **Multi-AOI productization (§41, M39) + soil pass load-bearing (§42, M40):** config registry +
  `INSAR_CONFIG` override + `aoi_status.py` + playbook; the §42 sweep proved soil (especially
  failure depth z) can erase the product — M2 stays required, depth is the #1 field-visit number.
- **Radar side (§35):** July S1 passes still not at ASF as of 07-10 — operational chains (f103/f105)
  can't extend yet; §43 f106 bridge swap (151 m → 102 m/24 d) queued for the next rebuild.
- **Ramban: COMPLETE, scored, LIVE** — two-tier + confidence + triage + temporal gate, project-best
  operating point (§21b, now with CI §44). Merge `aoi-vaishnodevi` → `master` is the user's call.
- **Vaishno Devi: full second AOI, VALIDATED and site-tuned** (§26–§32, M31–M37; §44 caveat above),
  12.5 m ALOS DEM, disaster-validated (§31), site-swept operating points (§32).
- **Deliverables:** route exposure + NE-flank creep target (§30/§33; field brief + KML shipped) and
  the Bhavan-overhang fast-failure toolkit (§34, M38).
- **Validation fronts (§38–§40, §44):** temporal 2/2 fatal events at Δ=0 (§38); inventory n=46
  primary-verified (§39); GACOS mixed first result (§40); statistics + ladder now standing (§44).
- **Honest limits carried:** creep core 0 vs corridor inventory (CV3); disaster site 598 m from
  nearest zone (§31 addendum — the calibration target); VD raw spatial AUC tied by a tuned slope
  map (§44); soils literature-corroborated not lab-measured (§37/§39/§42); fast-failure tools
  unproven-in-anger (Part E); §40 discrepancy pair open.
- **NISAR (§33):** too few products for a chain — recheck ~early Aug. ⭐ **Demos:** VD + Ramban
  `operational_alarm_dashboard*_2026.html` (now showing AUC [CI], p) and `data/aoi_status.html`.

## Recommended next steps — the product-improvement roadmap (2026-07-10)

Ranked by value-per-effort; the §31-addendum **598 m miss at the disaster site** is the calibration target.
**Recommended next session: Science Upgrade Plan #3 — nonlinear van-Genuchten matric-suction curve**
(`Research/Science Upgrade Plan - Top 3 (2026-07-13).md`; #1 ✅ §44, #2 ✅ §45 (kappa=0.06 adopted) —
#3 is judged against the same §44 ladder + CIs, on top of the §45 kappa field).

0. **Monsoon watch — now SCHEDULED (2026-07-13, was a manual runbook):** Windows task
   **"InSAR Monsoon Watch Cycle"** runs `workflows/monsoon_cycle.ps1` every 2 days at 08:00 —
   both sites, fetch → alarm → status board, toast ONLY on ALERT/state-change/failure; season-gated
   Apr–Oct. User's job shrinks to: react to a toast (dashboard, then the runbook's escalation
   section — field briefs / `coherence_watch` after storms). Manual commands in
   `Research/Monsoon Watch Runbook (2026-07-11).md` stay valid as the fallback.
1. **Radar cadence (agent, ~1 cmd/2 weeks):** cycle ran 2026-07-10 (§35) — July S1 passes still absent;
   when they land: resubmit (dedupe+park handle the rest) → download → QA → multistack → route_exposure →
   live_alarm → coherence_watch. Every cycle lengthens the chains and drops the σ_v noise floor.
   **⚠ Next rebuild also applies the §43 f106 bridge swap** (151 m bridge → the 102 m/24-day
   replacement) — expect a small f106/Ramban-union shift; re-score and ledger it as part of the cycle.
   **NISAR:** 8 GSLC/RSLC/GCOV + 3 GUNW over the AOI (checked 2026-07-07); too few for a chain — recheck
   monthly, build the GUNW adapter when ~8+ same-track pairs exist.
2. ✅ **DONE (2026-07-07) — VD operating-point sweep (§32, M37):** per-site `operational_m`/`watch_m`
   config keys wired; re-sweep when the inventory grows or chains lengthen.
3. ✅ **LARGELY DONE (2026-07-11) — site-specific soil pass (§37):** Kumar & Anbalagan 2013 (in hand) +
   GSI-derived overburden ranges bracket every engine value → values kept, provenance upgraded, no
   re-run needed. Remaining: primary-source confirmation of the soil ranges, Trikuta γ, on-site lab.
4. **Failure-class gap (research, larger):** corridor rockfall ≠ SBAS creep. ✅ coherence-drop detection
   BUILT (§34) — remaining candidates: Sentinel-2 optical change (the DROP-flag follow-up; could also run
   post-storm proactively) and a steep-cut-slope proxy layer in the reasoner. This axis is what closes the
   598 m miss, not more creep tuning.
5. **Per-zone WHEN (agent, medium):** sub-daily/point IMERG so ALERT varies per zone — the extreme-season
   over-firing (59 ALERT days in VD-2025) is the §17 limitation writ large.
6. ✅ **DONE (2026-07-07) — Docs debt:** primer covers M31–M38 (CV1–CV5, Part D/E refreshed).
7. **User-side:** field check of the NE-flank CORE target (brief: `Research/Field Brief - Bhairon NE flank
   creep target (2026-07-07).md` + `bhairon_core_creep.kml`; overhang step zero = request SMVDSB/THDCIL
   as-builts); merge `aoi-vaishnodevi` → `master`; publish the dashboard (user-side steps in the
   Publishing Checklist); soil primary sources (GSI Kumar FSP report / EGCON-2022, §39).

> **⏸ Deferred user-side manual setups (audited 2026-07-11):** ~~(1) GACOS tropo cross-check~~ ✅
> **DONE, first result (§40)** — mixed: 1 of 2 audit-flagged pairs strongly corroborated (R²=0.59),
> 1 not; a second pull (more epochs / a monsoon pair) would sharpen the trend. (2) soil parameters:
> **primary-source confirmation of the §37 overburden ranges + on-site lab** (literature
> second-source ✅ DONE §37; GSI Kumar FSP report / EGCON-2022 are the last live leads, §39); (3) merge
> **`aoi-vaishnodevi` → `master`** (supersedes the stale "merge mvp-expansion" item — mvp-expansion is
> fully contained in this branch; ~~snapshot a `config_ramban.yaml`~~ ✅ DONE 2026-07-12 as
> `config/ramban.yaml` with `site_name: Ramban NH-44`, §41). ~~(4) ALOS 12.5 m tile for Trikuta~~ ✅ DONE (§30).

## Uncommitted delta

Sessions ≤20 are **all committed** through `0a5943f` (validation statistics §44, M41, plan #1).

Session 21 (this wrap) — **TWI-distributed saturation (§45, M42, plan #2 — kappa=0.06 adopted):**
- NEW config key `kappa` (`config.py`, default 0.0 = uniform); `config/{ramban,vaishnodevi}.yaml`
  set `kappa: 0.06`.
- MODIFIED: `agentic_orchestrator.py` (FS_real build → per-pixel m_i from TWI when kappa≠0;
  `else` branch = original line, byte-identical at kappa=0), `rainfall_selectivity_backtest.py`
  (`--kappas`/`--operational-m` sweep + `write_kappa_outputs`/`_plot_kappa`), `per_zone_gate.py`
  (m*_eff = clip(m* − kappa·(TWI−TWI_mean),0,1); TWI + m_star_eff columns; kappa in report),
  `README.md` (headline AUCs + kappa mechanism bullet), `RESULTS_AND_KPIS.md` (§45), plan doc
  (#2 ✅), `SESSION_REVIEW.md` (this block + roadmap), `error_history_log.md` (Phase-2 staleness
  gotcha), `milestone.md` (M42), primer (CF12 + Part D Q + Part E update).
- Verified: κ swept {0,.03,.06,.10,.15,.20}, both sites peak κ=0.06; standing operational+watch
  footprints rebuilt at κ=0.06 (Phase 4 only — Phase 2/3 untouched); re-scored (backtest +
  validation_stats) both sites both tiers; dashboards + per-zone regenerated (both WATCH as-of
  07-07). Suites 10/10 + 7/7.
- Git-ignored as usual: `session_journey.md` entries (S20+S21), regenerated `data/` artifacts
  (`validation_stats_*`, `backtest_*`, `rainfall_kappa_*`, footprints, dashboards, per_zone_*).

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
| 8 | `Research/Foundations - Physics and Maths Primer.md` | The science (Phases 1–4 + forecasting/rainfall/validation) | As needed |
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

- Env (native): `insar_qa_env` at `C:\Users\varun\.conda\envs\insar_qa_env\`.
- HyP3 credits: ~7,460 as of 2026-07-10 (§35; ≈ enough for one more AOI's full Phase-1 pull). Disk: ~74 GB in `data/`.
- The container: `docker compose build` then e.g.
  `docker compose run --rm insar python workflows/agentic_orchestrator.py`. Code + `data/` bind-mounted at `/app`.

## 3. Open questions — "deepen trust" or "scale/deploy"

The core vision is fully built and scored above chance. Remaining work:

0. **Infrastructure & portability:** Infra 0a/0b DONE. **Multi-AOI productization DONE (2026-07-12):**
   per-AOI config registry (`config/*.yaml`, root `config.yaml` = one-line `active_config` pointer),
   `INSAR_CONFIG` env override (per-command AOI targeting for every script), soil parameters moved into
   config (`soil:` block — no more silent Ramban-default inheritance), `workflows/aoi_status.py`
   (multi-AOI stage/alarm dashboard + deterministic next step), `NEW_AOI_PLAYBOOK.md` (onboarding
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
1. **Accuracy backlog — now a ranked plan:** see `Research/Science Upgrade Plan - Top 3
   (2026-07-13).md` — ~~(1) bootstrap CIs + ablation-baseline ladder~~ ✅ DONE (§44,
   `validation_stats.py`), ~~(2) TWI-distributed saturation m_i~~ ✅ DONE (§45, kappa=0.06 adopted
   both sites; broke VD's §44 slope-only tie), (3) nonlinear van-Genuchten suction curve (α,n; fixes
   m\* placement, judged through #1's statistics on top of the §45 kappa field). Still behind those:
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
  #4 matric-suction FS split (done §20; nonlinear van-Genuchten curve remains).
- **Data upgrade — NISAR (NASA-ISRO, L+S band):** the top future SAR upgrade (L-band beats vegetation
  decorrelation, our worst enemy); operational window from Jul 2026.

**Suggested priority:** (1) ✅ operational two-factor warning + per-zone (§16–§19); (2) ✅ physics/data
upgrades (§20–§21); (3) ✅ recall two-tier + uncertainty + triage (§23–§25); (4) ✅ live rainfall
(`live_alarm.py` + runbook); (5) NISAR ingestion as it matures; (6) susceptibility cross-check +
nonlinear suction.

**Robustness in one line:** corroborate InSAR creep with optical change, real rainfall, soil moisture, and a
validated inventory — never trust a single sensor or a single physics assumption.

## 5. End-of-session ritual

Run **`/wrap-session`** before stopping — it appends KPIs to `RESULTS_AND_KPIS.md`, logs bugs, writes the
slim `session_journey.md` entry, adds milestone/primer entries on a completed phase, regenerates the LIVE
block above, and drafts the commit message (the user commits manually). Per-session checklists no longer
accumulate here — that history lives in `session_journey.md` + `git log` (older checklists: see the
archived pre-streamline snapshot).

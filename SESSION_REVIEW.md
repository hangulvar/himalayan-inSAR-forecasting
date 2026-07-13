# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`Research/Archive/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 20 · branch `aoi-vaishnodevi` · updated 2026-07-13

## Current state

- **★ NEW (§44, M41) — validation statistics (Science Upgrade Plan #1 DONE):**
  `workflows/validation_stats.py` — bootstrap 95% CIs (B=10k), permutation p for "beats chance"
  (B=10k), and a dumb-baseline **ablation ladder** (slope / logistic slope+TWI / physics-only /
  creep-only) scored with the identical zone-centroid distance-ROC protocol, every rung tuned to
  its own best score. Both ALERT maps beat chance at p=0.0001; both WATCH tiers ≈chance (recall
  nets, as always stated). **Ramban: the fusion beats every rung** (its two ingredients are each
  ≈chance alone). **VD, the honest tie:** slope≥40° matches the raw AUC on the corridor n=46
  inventory — the earned VD claims are footprint economy (21 vs 155 zones at higher precision),
  the Δ=0 temporal catches, and per-zone ranking (§44). The ladder is now the fixed bar for
  plan #2/#3. Dashboards + README cite intervals live; a stale VD dashboard AUC (0.696/n=41 vs
  the current 0.707/n=46) was found and structurally fixed (error log 2026-07-13).
- **BOTH sites are in WATCH (as-of 2026-07-07, chains regenerated this session via
  `live_alarm.py`):** VD 29/29 per-zone active, 0 ALERT days; Ramban 12/12 active, 4 April ALERT
  days. The scheduled monsoon cycle (roadmap item 0) covers the cadence; manual fallback per
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
**Recommended next session: Science Upgrade Plan #2 — TWI-distributed saturation m_i** (`Research/Science
Upgrade Plan - Top 3 (2026-07-13).md`; #1 ✅ DONE §44 — #2 and #3 are now judged against the §44 ladder + CIs).

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

Sessions ≤19 are **all committed** through `e30ca60` (science upgrade plan).

Session 20 (this wrap), one logical batch — **validation statistics (§44, M41, plan #1)**:
- NEW: `workflows/validation_stats.py` (bootstrap CIs B=10k, permutation p B=10k, ablation
  ladder scored with the identical zone/centroid/distance-ROC protocol; plain-numpy IRLS for the
  LR rung — no new dependency).
- MODIFIED: `workflows/operational_alarm.py` (`load_tier` prefers `validation_stats_*.json` —
  displayed AUC/recall + 95% CI + p come from one run; fixes the stale VD 0.696/n=41 display),
  `README.md` (headline cites interval + p; new validation-statistics bullet),
  `RESULTS_AND_KPIS.md` (§44), `Research/Science Upgrade Plan - Top 3 (2026-07-13).md` (#1 ✅ +
  outcome note), `SESSION_REVIEW.md` (this LIVE block + STABLE §3 item 1 fact update),
  `error_history_log.md` (stale-AUC entry), `milestone.md` (M41), primer (CF11 + Part D
  statistics Q + Part E error-bars/slope-tie limitation).
- Verified: suites 10/10 + 7/7 in-container; Ramban op AUC reproduces §21b (0.640≈0.641,
  float-path rounding); VD op reproduces §42 (0.707 exact); both sites' live dashboards
  regenerated as-of 2026-07-07 (both WATCH) and show `AUC x.xx [lo–hi] (beats chance, p=…)`.
- Git-ignored as usual: `session_journey.md` entry (Session 20), regenerated `data/` artifacts,
  `data/inventory/validation_stats_*`.

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
   (2026-07-13).md` — ~~(1) bootstrap CIs + ablation-baseline ladder~~ ✅ DONE 2026-07-13 (§44,
   `validation_stats.py`; VD raw-AUC tie vs slope≥40° is the standing yardstick),
   (2) TWI-distributed saturation m_i (one swept κ; κ=0 = today), (3) nonlinear van-Genuchten
   suction curve (α,n; fixes m\* placement, judged through #1's statistics). Still behind those:
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
  calibrated spatially-varying soil + distributed saturation, real flow-routing for LLOF.
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

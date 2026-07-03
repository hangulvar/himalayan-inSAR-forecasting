# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`Research/Archive/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 13 · branch `mvp-expansion` · updated 2026-07-03

## Current state

- **The full MVP is COMPLETE and demonstrable:** radar → audited data → SBAS velocity (3 ASC stacks; DESC dumped, quality-first) → physics hazard → explainable rainfall-driven warning + 3-D UI. Dockerized, point-anywhere (`config.yaml`), multi-stack + union mosaic. Plain-language story: `milestone.md` M1–M30.
- **Validation is scored and beats chance.** CURRENT operating point = the **m=0.50 ALERT** product — project-best AUC (§21b). Scoring method: null-point control + distance-ROC/AUC (§16b).
- **Two-tier product (§23):** precise **ALERT** map beside a higher-recall **WATCH** map (m=0.70); its ≥2-look core also beats chance. Both tiers surfaced in the dashboard's WHERE panel, scores read live from the back-test reports (self-updating).
- **Per-zone detection confidence (§24):** velocity noise floor (σ_v, robust MAD) → P(creep is real, not noise); a *triage* axis, orthogonal to inventory AUC. Colour-coded column in the dashboard's per-zone panel.
- **WATCH triage (§25):** the 132-zone net is *ranked, not gated* (priority = fragility m\* × confidence P); top-5 "read first" shortlist inside the dashboard's WATCH card.
- **Two-factor warning WHERE×WHEN:** regional-curve temporal gate (§17, catches the 20 Apr 2025 cloudburst at Δ=0) + per-zone critical-saturation gating m\* (§19).
- **Physics upgrades in force:** φ=36° GSI-calibrated friction (§15/§16a) + matric-suction dry/wet cohesion split (§20) + 12.5 m ALOS DEM slope (§21) — each removed an assumption AND raised the score.
- **ERA5 tropo velocity:** frame106 good (§13/§18 — trust the multi-look core); frame102/101 honestly QC-stopped (§22), mosaic stays on custom velocities.
- ⭐ **Headline demo:** `data/alerts/mosaic_asc/operational_alarm_dashboard.html` — WHERE (two tiers) × WHEN (alarm calendar) × WHICH ZONES (ranked triage panel + confidence column; `--as-of <date>`). Also `data/alerts/dashboard_3d.html` (3-D) and per-stack `dashboard_operational.html`.
- **Data state:** all 3 ASC stacks at φ=36° + suction + 12.5 m DEM; zone counts per scenario → §23. (V_slope mosaics NOT refreshed since §16c — still pre-DEM.)

## Recommended next step

Top remaining items (each needs external data / compute / per-stack tuning — see STABLE §3 for the full menu):
(a) nonlinear van-Genuchten suction curve (§20 is first-order linear); (b) lab confirmation of c_dry/c_wet
(the 18.5 unit question, §20); (c) per-stack ERA5 reference-pixel + unwrapping QC to rescue frame102/101
(§22 fix path); (d) live rainfall ingestion (replace manual fetch); (e) NISAR ingestion as it matures
(operational window from Jul 2026); (f) **new-AOI replication before monsoon** — point `config.yaml` +
start the S1/HyP3 pull early (velocity needs a time series).

> **⏸ Deferred user-side manual setups (both documented in `README.md` Step 7):** (1) GACOS tropo
> cross-check; (2) GSI Bhukosh verified-date inventory (dropped as a blocker — the CSV suffices spatially).

## Uncommitted delta

- Working tree **clean at `737e739`**; all Session-13 work committed (B1 `39c723c`, B2 `1314682`+`a4b5db6`, B3 `d7535f6`, B4 `737e739`).
- **[2026-07-03] NEW this session — documentation-ritual streamline:** `.claude/commands/wrap-session.md` (one-command end-of-session ritual), this restructured LIVE/STABLE SESSION_REVIEW (verbose snapshot archived), CLAUDE.md §5 ritual rules updated (CLAUDE.md itself is untracked). Suggested commit:
  `git add .claude/commands/wrap-session.md SESSION_REVIEW.md && git commit -m "Streamline documentation ritual: /wrap-session command + LIVE/STABLE SESSION_REVIEW"`

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
- HyP3 credits: ~6,170 (≈ enough for one more AOI's full Phase-1 pull). Disk: ~73 GB used in `data/`.
- The container: `docker compose build` then e.g.
  `docker compose run --rm insar python workflows/agentic_orchestrator.py`. Code + `data/` bind-mounted at `/app`.

## 3. Open questions — "deepen trust" or "scale/deploy"

The core vision is fully built and scored above chance. Remaining work:

0. **Infrastructure & portability:** Infra 0a/0b DONE. Still: fold the <150 m perpendicular-baseline
   gate into rescues; AOI guidance (a better polygon improves *targeting*, not the noise floor).
   **New-AOI replication readiness:** infra replicability HIGH (config-driven, Dockerized, multi-stack);
   scientific transferability MEDIUM — a new AOI needs (a) ~2–3 months of S1 acquisitions for a velocity
   baseline, (b) site soil calibration (φ=36° is Ramban-specific), (c) a local inventory for validation.
1. **Accuracy backlog:** nonlinear van-Genuchten suction curve; lab confirmation of c_dry/c_wet;
   per-stack ERA5 reference-pixel + unwrapping QC (rescue frame102/101, §22).
2. **Visualization:** combined interactive 3-D dashboard over the UNION mosaic; ASC/DESC vertical+EW
   decomposition (DEFERRED — needs better DESC: longer connected series / PS / phase-linking).
3. **Make it live / smarter:** live rainfall ingestion (CHIRPS/GPM auto, replace manual fetch); real
   flow-routing for LLOF (replace TWI proxy); hybrid LLM ("rules decide, LLM narrates").
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
assumed/uniform soil strength (φ now site-calibrated) + dry/sat end-members + TWI-proxy downstream flag;
manual (not live) rainfall; a static-vs-worst-case hazard map; recall-limited validation on one small AOI.

- **Area 1 — Noise reduction:** MintPy ERA5 (done on frame106), GACOS cross-check, DEM-error +
  coherence-weighted inversion, phase-linking/DS methods (recover vegetated slopes), <150 m Bperp rule.
- **Area 2 — Signal strengthening:** ASC/DESC → vertical+EW (needs better DESC), PS points on rock/infra,
  longer series → seasonal vs steady-creep split.
- **Area 3 — Map → FORECAST:** inverse-velocity TTF (built), regional ID thresholds (built/verified),
  calibrated spatially-varying soil + distributed saturation, real flow-routing for LLOF.
- **Area 4 — Validation & uncertainty:** scored back-test DONE (§16); uncertainty quantification DONE (§24);
  next = a susceptibility model (LR/RF) cross-check + a verified-date temporal test.
- **Area 5 — Multi-sensor corroboration (GEE):** CHIRPS/IMERG/ERA5-Land rainfall, SMAP/ASCAT soil moisture,
  SoilGrids strength, DEM upgrades, WorldCover/NDVI veg masks, Sentinel-2/Landsat optical change, NASA GLC.
- **Area 6 — Operationalize:** live rainfall ingestion, hybrid LLM, hosted + union 3-D dashboard.
- **Area 7 (physics borrows):** #1 snowmelt/freeze-thaw (done), #2 V_slope (done), #3 regional ID + K_sn,
  #4 matric-suction FS split (done §20; nonlinear van-Genuchten curve remains).
- **Data upgrade — NISAR (NASA-ISRO, L+S band):** the top future SAR upgrade (L-band beats vegetation
  decorrelation, our worst enemy); operational window from Jul 2026.

**Suggested priority:** (1) ✅ operational two-factor warning + per-zone (§16–§19); (2) ✅ physics/data
upgrades (§20–§21); (3) ✅ recall two-tier + uncertainty + triage (§23–§25); (4) live rainfall;
(5) NISAR ingestion as it matures; (6) susceptibility cross-check + nonlinear suction.

**Robustness in one line:** corroborate InSAR creep with optical change, real rainfall, soil moisture, and a
validated inventory — never trust a single sensor or a single physics assumption.

## 5. End-of-session ritual

Run **`/wrap-session`** before stopping — it appends KPIs to `RESULTS_AND_KPIS.md`, logs bugs, writes the
slim `session_journey.md` entry, adds milestone/primer entries on a completed phase, regenerates the LIVE
block above, and drafts the commit message (the user commits manually). Per-session checklists no longer
accumulate here — that history lives in `session_journey.md` + `git log` (older checklists: see the
archived pre-streamline snapshot).

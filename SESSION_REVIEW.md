# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`Research/Archive/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 15 · branch `aoi-vaishnodevi` · updated 2026-07-06

## Current state

- **The Ramban product is COMPLETE, scored, and LIVE:** two-tier ALERT/WATCH warning (§23) with per-zone confidence (§24) + triage (§25), temporal gate (§17), physics-upgraded to the project-best operating point (§21b). Story: `milestone.md` M1–M30. `mvp-expansion` is ready to merge to `master` (user's call).
- **Live rainfall ingestion (Area 6) SHIPPED:** `live_alarm.py` — one idempotent command (run once in each image) extends the season CSV through today and regenerates the alarm dashboard; Ramban's 2026 season verified current through 26 Jun (4 April ALERT days; ~5-day ERA5-Land lag is by design).
- **Second AOI — Vaishno Devi (Katra) pilgrimage corridor — Phase 1 COMPLETE (§26, M31):** OSM-anchored Trikuta-route polygon; 49 pairs / 8 stacks submitted (490 credits, 7,510 left); 48 products QA'd; the 1 ASF-side failure resubmitted after fixing a dedupe gap (FAILED jobs counted as done — `error_history_log.md` 2026-07-03).
- **Key structural fact:** Katra shares Sentinel-1 frames with Ramban (path27/100/34) — the 2025 archive covers the new site for free; May–Jun 2026 acquisitions landed in new frame labels (f105, f103) via frame drift.
- **QA verdict for the new site:** winter-2026 pairs mostly QUARANTINED (phase-elev R² ≤0.85, snow/atmo); the **spring chains connect fully after rescue** (f105, f103) — the monsoon-relevant baseline is clean. Season-gap disconnections (Nov 25–Jan 26 hole) go to the SVD/period-split path.
- **AOI-coexistence layer SHIPPED:** whole rainfall/trigger chain is config-driven (`aoi_slug`-prefixed files; Ramban names grandfathered byte-identical), and Phase 2–4 output dirs are slug-scoped (`data/*_vaishnodevi/` vs Ramban's plain dirs) — 12 scripts, 20/20 dir resolutions verified in-container. Rationale: shared frames mean stack labels can't separate the sites.
- **Vaishno Devi Phases 2–4 COMPLETE (§27, M32):** both connected spring stacks inverted (2 ASC tracks, 4 pairs each) → hazard (φ=36° borrowed, HyP3 30 m DEM via new ALOS-fallback) → alert zones + dashboards + union mosaic in `data/*_vaishnodevi/` (Ramban's dirs verified untouched). Union: **operational 27 zones (4 crit, 6 multi-look) / watch 72 / monsoon 185**; HIGH 2,705 px, **≥2-track core 411 px — the trust-first set**. `[UNVALIDATED]` — no local inventory; ~7-week baseline, high noise floor (§27 caveats).
- **Cross-AOI stress test paid off:** three latent single-AOI assumptions found+fixed (min-pairs clamp, ALOS-tile zero-coverage fallback, `slope_velocity` un-rerun §21 signature break) — `error_history_log.md` 2026-07-03b.
- ⭐ **Headline demos:** Ramban `data/alerts/mosaic_asc/operational_alarm_dashboard.html` (+ `_2026.html` live season); Vaishno Devi `data/alerts_vaishnodevi/<stack>/dashboard_operational.html` + union `alerts_*.json`. Cosmetic gap: dashboards still titled "Ramban NH-44" pending a `site_name` config field.

- **Route exposure DONE (§28, M33) — the deliverable:** `route_exposure.py` + OSM-real `vaishnodevi_route.geojson`. Headline: **1 CORE segment (680 m of path above Bhairon top, 2-track-confirmed — read first)**; **0 OPERATIONAL** segments (standing product's zones are off-track); WATCH 7 segs/7.3 km (Himkoti + Hathimata variants pass through zones; shrine complex + ropeway within ~200 m); MONSOON-only 8 segs (classic Track); **Katra + trek start CLEAR**. Also fixed: `.gitignore` was silently ignoring `*_aoi.geojson` — **`vaishnodevi_aoi.geojson` was never actually committed**; re-included, needs `git add`.

- **VD is LIVE (§29, M34):** two-factor alarm running on the real 2026 season — **DORMANT as-of 2026-06-30** (13 April trigger days gated to 0 ALERT). Cross-AOI honesty guards shipped: suffix-scoped back-test lookups (a site can never wear another's AUC), "not yet back-tested at this site" cards, per-AOI inventory convention, `site_name` config field (VD dashboards correctly titled; **add `site_name: Ramban NH-44` to Ramban's config at merge**).
- **VD upgraded to the 12.5 m ALOS DEM (§30, M35):** user-fetched Trikuta tile (100 % AOI coverage, health-checked); `ALOS_DEM_DIR` slug-scoped. Slope median 18→21.9°; **2-track core 411→567 px**; operational 27→37 zones; **the CORE route segment above Bhairon top now runs 800 m THROUGH core pixels (0 m)**; op product still off-track; alarm still DORMANT. §27/§28 counts superseded.

## Recommended next step

Field-facing: get the CORE segment (route_exposure.md row 1) eyeballed on the ground / on recent optical
imagery. Pipeline: **refresh cadence** — re-run `live_alarm.py` (both images) as the monsoon builds, and
bump `search_end` + resubmit every ~2 weeks to extend the S1 chains (noise floor drops as chains lengthen).
The frame106 Jan pair is CLOSED: it fails deterministically at ASF (mcf reference-point error) and is now
auto-PARKED after its 2nd failure (§26 addendum) — Phase 1 final state 48/49. User-side: Trikuta ALOS
12.5 m tile (§21 path). Ramban backlog unchanged (STABLE §3).

> **⏸ Deferred user-side manual setups:** (1) GACOS tropo cross-check (gacos.net); (2) soil-cohesion
> lab/second-source confirmation; (3) merge `mvp-expansion` → `master`; (4) ALOS 12.5 m tile for Trikuta
> (ASF Vertex, like the Ramban one).

## Uncommitted delta

- Committed on `aoi-vaishnodevi` through `735b552` (VD Phases 2–4 + route exposure).
- **[2026-07-06] NEW this batch — VD live alarm + honesty guards:** `config.py` + `config.yaml` (`site_name`), `operational_alarm.py` (suffix-scoped back-test lookups, per-AOI inventory, unscored tier cards), `agentic_orchestrator.py` / `build_3d_dashboard.py` (config-driven titles), `live_alarm.py` (dashboard-path print), `RESULTS_AND_KPIS.md` §29, `milestone.md` M34, this LIVE block. Suggested commit:
  `git add workflows/ config.yaml RESULTS_AND_KPIS.md milestone.md SESSION_REVIEW.md && git commit -m "VD live two-factor alarm (DORMANT as-of 2026-06-30) + cross-AOI honesty guards: suffix-scoped scores, unscored cards, site_name titles (§29, M34)"`
- **[2026-07-06b] Loose end closed — frame106 Jan pair:** `submit_hyp3_jobs.py` (retry-then-park: ≥2 ASF failures → skip with warning; dry-run verified 49 planned / 49 skipped / 1 parked), `RESULTS_AND_KPIS.md` §26 addendum, `error_history_log.md` 2026-07-06. Suggested commit:
  `git add workflows/submit_hyp3_jobs.py RESULTS_AND_KPIS.md error_history_log.md SESSION_REVIEW.md && git commit -m "Retry-then-park for HyP3 pairs: frame106 Jan pair fails deterministically (mcf ref-point) — parked after 2nd failure, re-runs stop re-buying it (§26 addendum)"`
- **[2026-07-06c] VD 12.5 m DEM:** `geomechanical_engine.py` (`ALOS_DEM_DIR` slug-scoped), user tile in `data/dem_alos_12m_vaishnodevi/` (git-ignored), full `--force` re-run + route exposure + alarm refreshed, `RESULTS_AND_KPIS.md` §30 (+§27/§28 superseded tags), `milestone.md` M35, this LIVE block. Suggested commit:
  `git add workflows/geomechanical_engine.py RESULTS_AND_KPIS.md milestone.md SESSION_REVIEW.md && git commit -m "VD on the 12.5m ALOS DEM: slug-scoped ALOS_DEM_DIR; 2-track core 411->567px, CORE route segment now 800m through core px; alarm still DORMANT (§30, M35)"`

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

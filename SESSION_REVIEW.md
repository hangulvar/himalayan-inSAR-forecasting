# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`Research/Archive/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 17 · branch `aoi-vaishnodevi` · updated 2026-07-08

## Current state

- **Ramban: COMPLETE, scored, LIVE** — two-tier ALERT/WATCH (§23) + per-zone confidence (§24) + triage (§25) + temporal gate (§17), project-best operating point (§21b); live 2026 alarm via `live_alarm.py`. `mvp-expansion` ready to merge to `master` (user's call; add `site_name: Ramban NH-44` at merge).
- **Vaishno Devi: a full second AOI, VALIDATED and site-tuned** (§26–§32, M31–M37): 12.5 m ALOS DEM, disaster-validated (Δ=0 peak-day catch + beats-chance spatial, §31), operating points earned by the local m-sweep (ALERT m=0.40 / WATCH m=0.75, §32) as per-site config keys.
- **The deliverable — route exposure (§28, M33):** CORE finding is the **NE-flank creep target** (2-track-confirmed, §30; abuts a settlement, §33). Field brief + GPS KML shipped 2026-07-07.
- **★ NEW (§34, M38) — the fast-failure toolkit for the Bhavan overhang (CV3 class):** `coherence_watch.py` (NEW) is the pipeline's **first fast-failure detector** — per-polygon 12-day coherence timelines, AOI-relative drop gating (a scene-wide rain drop was demonstrably filtered on first run); current verdict **OK/quiet** on the overhang + both creep polygons. Re-run every radar cycle.
- **★ NEW (§34) — rockfall runout screen:** `rockfall_runout.py` (NEW), energy-line cone on the 12.5 m DEM — **the Bhavan shrine complex is INSIDE the LIKELY (≥32°) band (33.2°)**, ropeway ghati station POSSIBLE, ~2.3 km of route LIKELY; bands exported as Google-Earth KML. First-order screen, caveats on record.
- **★ NEW (§34) — records cross-check:** the overhang's slope system is institutionally KNOWN — GSI Table-7.1 planar/wedge locs 315–440 m from the polygon edge, a treated 12 Mar 2016 failure at the Bhawan complex (37 deep anchors), SMVDSB+THDCIL programme since 2012. **Field step zero: request treatment as-builts.** Full brief incl. joint tell-tale protocol: `Research/Vaishno_Devi_Watchlist/Field Brief - Bhavan overhang (2026-07-08).md`.
- **Honest limits carried:** creep core scores 0 vs the corridor inventory (CV3); disaster site 598 m from nearest zone (§31 addendum) — still the calibration target (coherence watch addresses the *class*, not this miss retroactively); VD still borrows Ramban's φ/c; fast-failure tools are unproven-in-anger (Part E, M38).
- **NISAR (§33):** real L-band products over the AOI (3 GUNW + 8 GSLC/RSLC/GCOV) but too few for a chain — recheck monthly.
- ⭐ **Demos:** Ramban `data/alerts/mosaic_asc/operational_alarm_dashboard.html` (+ `_2026`); VD `..._vaishnodevi_2026.html` (DORMANT as-of 30 Jun) + route/creep/runout/coherence artefacts in `data/alerts_vaishnodevi/mosaic_asc/`.

## Recommended next steps — the product-improvement roadmap (2026-07-07)

Ranked by value-per-effort; the §31-addendum **598 m miss at the disaster site** is the calibration target.

1. **Radar cadence (agent, ~1 cmd/2 weeks):** early-July S1 passes not yet in the archive (checked
   2026-07-07) — when they land: resubmit (dedupe+park handle the rest) → download → QA → multistack →
   route_exposure → live_alarm. Every cycle lengthens the chains and drops the σ_v noise floor.
   **NISAR (checked 2026-07-07): REAL L-band products now exist over the VD AOI** — 8 GSLC/RSLC/GCOV
   scenes (Nov 25–Jan 26) and **3 GUNW interferograms** (Nov–Dec 25) via `asf_search dataset=NISAR`.
   Too few for a velocity chain yet; the 1–3-day forward-processing window opened Jul 2026 — **recheck
   monthly**, build the GUNW ingestion adapter when ~8+ same-track pairs exist (L-band = vegetation
   coherence, our worst enemy). **Field target upgraded:** Area A abuts a settlement (62 OSM buildings
   ≤1.5 km, closest 87 m; Panchari Gali 810 m) — coords independently re-verified; brief updated.
   **New tool:** `polygon_stats.py` (user-drawn KML/GeoJSON polygons → per-polygon risk stats; self-tested
   on the creep clusters).
2. ✅ **DONE (2026-07-07) — VD operating-point sweep (§32, M37):** sweep script AOI-parameterized; 16-value
   sweep → **ALERT m=0.40** (plateau, AUC 0.696/spec 0.654/lift 2.11×, 21 zones — spike at 0.35 rejected as
   cliff-adjacent) + **WATCH m=0.75** (recall 0.927 = 38/41, 105 zones — perfect recall @0.85 declined).
   Wired as per-site config keys `operational_m`/`watch_m` (Ramban defaults unchanged); full cascade
   regenerated + re-scored; Δ=0 disaster catch intact. Re-sweep when the inventory grows or chains lengthen.
3. **Site-specific soil pass (agent + user sources, medium):** φ/c for Trikuta carbonates + Vaishnodevi-Fm
   scree (GSI-note geology) replacing the Batote–Doda values; re-run + re-score (§20/§21 pattern).
4. **Failure-class gap (research, larger):** corridor rockfall ≠ SBAS creep. ✅ **coherence-drop change
   detection BUILT (2026-07-08, §34)** — remaining candidates: Sentinel-2 optical change (the DROP-flag
   follow-up; could also run post-storm proactively) and a steep-cut-slope proxy layer in the reasoner.
   This axis is what closes the 598 m miss, not more creep tuning.
5. **Per-zone WHEN (agent, medium):** sub-daily/point IMERG so ALERT varies per zone — the extreme-season
   over-firing (59 ALERT days in VD-2025) is the §17 limitation writ large.
6. ✅ **DONE (2026-07-07) — Docs debt:** primer updated for M31–M36 (new Part C-quinquies CV1–CV4:
   transferability, route exposure, failure classes, single-event validation; +4 Part-D Q&As; Part E
   refreshed incl. the consolidated VD-caveats bullet; pitch now covers both sites).
7. **User-side:** field check of the NE-flank CORE target — **full brief with polygons, checklist and
   safety notes: `Research/Field Brief - Bhairon NE flank creep target (2026-07-07).md`** (+ GPS-loadable
   `data/alerts_vaishnodevi/mosaic_asc/bhairon_core_creep.kml`); merge `mvp-expansion` → `master`
   (+ add `site_name: Ramban NH-44` to Ramban's config); optional GACOS + soil-cohesion sources.

> **⏸ Deferred user-side manual setups:** (1) GACOS tropo cross-check (gacos.net); (2) soil-cohesion
> lab/second-source confirmation; (3) merge `mvp-expansion` → `master`; (4) ALOS 12.5 m tile for Trikuta
> (ASF Vertex, like the Ramban one).

## Uncommitted delta

Prior batches (through §33/M37 + the 2026-07-07 wrap) all committed through `c450299`.

- **[2026-07-08] Fast-failure toolkit (§34, M38):** NEW `workflows/coherence_watch.py` +
  `workflows/rockfall_runout.py`; NEW `Research/Vaishno_Devi_Watchlist/Field Brief - Bhavan overhang
  (2026-07-08).md`; watchlist `README.md` ideas #3/#4/#6/#7 marked ✅ with pointers; `RESULTS_AND_KPIS.md`
  **§34**; wrap docs (error log Overpass-406 entry, Session-17 journey entry, milestone M38, primer CV5 +
  Part D Q&A + Part E refresh incl. retiring the stale "Ramban-tuned dials" caveat, this LIVE block).
  Git-ignored outputs: `coherence_watch_*`, `rockfall_runout_*` in `data/alerts_vaishnodevi/mosaic_asc/`,
  cached `data/osm/vaishnodevi_buildings_overpass.json`. Suggested commit: see wrap-session close-out
  (one commit: scripts + brief + README + docs).`

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

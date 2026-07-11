# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`Research/Archive/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 18 · branch `aoi-vaishnodevi` · updated 2026-07-10

## Current state

- **★ NEW (§35) — the VD site is now in WATCH:** the first routine radar-cadence cycle (roadmap #1) ran
  end-to-end 2026-07-10; `live_alarm.py` (fetch in the mintpy image) brought ERA5-Land to 07-04 and the
  monsoon onset flipped the site **DORMANT → WATCH, all vulnerable zones active** (§35; 0 ALERT days —
  the acute trigger has not fired). **Re-run `live_alarm.py` every few days through the monsoon** (mintpy
  image for fetch, then insar image for the dashboard).
- **Radar side of the cycle (§35):** July S1 passes STILL not at ASF (latest scenes 18–23 Jun; lag >17
  days) — the operational chains (f103/f105) can't extend yet. A backfilled 2 Mar path-27 scene yielded 4
  new mid-chain pairs (f101/f106 baseline densified; f106 islands 6→4, f101 unchanged — new bridges failed
  the rescue gate by a hair, kept out on purpose). Regenerated cascade **reproduces §32 exactly**;
  `coherence_watch` verdict **OK/quiet** on overhang + creep polygons.
- **Ramban: COMPLETE, scored, LIVE** — two-tier ALERT/WATCH (§23) + per-zone confidence (§24) + triage
  (§25) + temporal gate (§17), project-best operating point (§21b). `mvp-expansion` ready to merge to
  `master` (user's call; add `site_name: Ramban NH-44` at merge).
- **Vaishno Devi: a full second AOI, VALIDATED and site-tuned** (§26–§32, M31–M37): 12.5 m ALOS DEM,
  disaster-validated (§31), operating points earned by the local m-sweep (§32) as per-site config keys.
- **The deliverable — route exposure (§28, M33):** CORE finding is the **NE-flank creep target**
  (2-track-confirmed, §30; abuts a settlement, §33). Field brief + GPS KML shipped 2026-07-07.
- **Fast-failure toolkit for the Bhavan overhang (§34, M38):** `coherence_watch.py` (first fast-failure
  detector, re-run every cycle — done this cycle), `rockfall_runout.py` (shrine complex in the LIKELY
  cone), records cross-check (face institutionally KNOWN; field step zero = request treatment as-builts;
  brief in `Research/Vaishno_Devi_Watchlist/`).
- **Honest limits carried:** creep core scores 0 vs the corridor inventory (CV3); disaster site 598 m from
  nearest zone (§31 addendum) — still the calibration target; VD φ/c now literature-corroborated (§37 —
  "borrowed" caveat retired; lab confirmation + γ still open); fast-failure tools are unproven-in-anger
  (Part E, M38).
- **NISAR (§33):** real L-band products over the AOI but too few for a chain — recheck ~early Aug.
- ⭐ **Demos:** Ramban `data/alerts/mosaic_asc/operational_alarm_dashboard.html` (+ `_2026`); VD
  `..._vaishnodevi_2026.html` (**WATCH as-of 04 Jul**, §35) + route/creep/runout/coherence artefacts in
  `data/alerts_vaishnodevi/mosaic_asc/`.
- **Ops learning (error log 2026-07-10):** 4 of the 5 Phase-1 QA scripts have no argparse — `--help`
  EXECUTES them (harmless: idempotency held, verified against §32).

## Recommended next steps — the product-improvement roadmap (2026-07-10)

Ranked by value-per-effort; the §31-addendum **598 m miss at the disaster site** is the calibration target.

0. **Monsoon watch (user or agent, minutes, every few days):** the site is in WATCH (§35) — re-run
   `live_alarm.py` (mintpy fetch → insar alarm) every ~3 days; escalate per the field briefs if ALERT
   fires or `coherence_watch` flags a DROP after a storm.
1. **Radar cadence (agent, ~1 cmd/2 weeks):** cycle ran 2026-07-10 (§35) — July S1 passes still absent;
   when they land: resubmit (dedupe+park handle the rest) → download → QA → multistack → route_exposure →
   live_alarm → coherence_watch. Every cycle lengthens the chains and drops the σ_v noise floor.
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
   creep target (2026-07-07).md` + `bhairon_core_creep.kml`); merge `mvp-expansion` → `master` (+ add
   `site_name: Ramban NH-44` to Ramban's config); optional GACOS + soil-cohesion sources.

> **⏸ Deferred user-side manual setups:** (1) GACOS tropo cross-check (gacos.net); (2) soil-cohesion
> lab/second-source confirmation; (3) merge `mvp-expansion` → `master`; (4) ALOS 12.5 m tile for Trikuta
> (ASF Vertex, like the Ramban one).

## Uncommitted delta

Prior batches (through §34/M38 + the 2026-07-08 wrap) all committed through `f0c6883`.

- **[2026-07-10] Radar-cadence cycle #1 (§35):** NO code changes — docs only: `RESULTS_AND_KPIS.md`
  **§35**, `error_history_log.md` (no-argparse `--help` footgun), this LIVE block (+ git-ignored
  Session-18 journey entry). Git-ignored data outputs: 4 new products in `data/processed_tiffs/`,
  refreshed rainfall CSV + alarm report/dashboard (WATCH), `per_zone_vulnerability.*`,
  `coherence_watch_*`, `route_exposure.*`. Suggested commit: see wrap-session close-out.
- **[2026-07-10/11] Dashboard UX (post-wrap):** `workflows/operational_alarm.py` — Guide tab
  (plain-language how-to-read cards) + per-card subtitles; every coordinate is a click-to-Google-Maps
  link; per-stack map links derived from disk (fixes dead Ramban links on VD); site-aware footer/blurbs.
  VD dashboard regenerated + browser-verified (identical numbers).
- **[2026-07-11] Web-publishing readiness (user wants to post the dashboard on LinkedIn/X):**
  `operational_alarm.py` — research-prototype DISCLAIMER strip + footer echo, license-required data
  attributions (Copernicus/ESA, C3S ERA5-Land, JAXA ALOS, GSI, OSM/ODbL), `viewport` meta (mobile was
  broken), OG/Twitter unfurl tags (og:url/og:image left as placeholders until hosted), About+credits
  guide card, events-table "None"→"before this season's data window", card-level table scroll;
  verified at 375 px (no horizontal overflow). Remaining user-side steps in NEW
  `Research/Publishing Checklist - Live Dashboard (2026-07-11).md` (hosting, og:image, author credit,
  post framing, staleness plan, relative per-stack links caveat).
- **[2026-07-11] Soil-parameter groundwork (§36, roadmap #3):** NEW
  `Research/Vaishno_Devi_Watchlist/Soil Parameter Research Brief (2026-07-10).md` (deep-research
  handoff, updated with leads + date-verification rule); `RESULTS_AND_KPIS.md` **§36** — compendium
  §5.3.1 has NO soil params (SMR-based) but independently corroborates the §31 Ardhkuwari/new-track
  High zone; new dated 30 Dec 2008 Bhawan event for the inventory; Chenab-gouge (same Sirban
  formation) + Ramban–Gool analogue c/φ/γ; future-dated "Sept 2026" claim flagged.
- **[2026-07-11] Temporal validation doubled (§38) + README refresh:** VD inventory grew 1→4 dated
  events (all source-verified per §12g rule; the "2 Sep 2025" deep-research claim EXCLUDED as
  fabricated — yatra was closed then). **21 Jul 2025 Banganga caught at Δ=0 (E=2.51)** alongside
  Ardhkuwari → 2/2 in-window fatal events. 2008 Bhawan rockfall (source-internal Aug/Dec
  discrepancy, flagged) + 2016 Bhawan failure recorded as historical features. 2025+2026 alarm
  products regenerated; spatial re-score/m-sweep deliberately NOT re-run. Committed README rewritten
  (two-site status, §-cited arc, stale "live rainfall pending" line fixed) ahead of public linking.
- **[2026-07-11] Soil parameters RESOLVED (§37):** user obtained Kumar & Anbalagan 2013 (PDF in
  watchlist folder) + deep-research synthesis (soil numbers recovered from its embedded base64
  images). Site envelope brackets every engine value (φ 32–43° vs 36; c 4.9–27.5/4.5–7.9 kPa vs
  18.5/5; weathering 1–3 m vs z=3) → **values kept, "borrowed φ/c" caveat retired**; rock-joint set
  (c_J≈28.4 kPa, φ_J=46°, seismic FS 0.98) recorded for the CV3 class. Provenance comment in
  `geomechanical_engine.py`; site_notes updated in `operational_alarm.py` + VD dashboard
  regenerated; primer Part E caveat (a) rewritten; brief lead #1 marked obtained.

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

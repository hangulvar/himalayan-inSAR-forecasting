# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`docs/archive/local/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 34 · branch `aoi-vaishnodevi` · updated 2026-08-11

## Current state

- **★★ The hazard map now publishes GROUND, not dots (§84).** New `exposure_footprint.py` draws each
  zone's actual outline plus the corridor debris would travel below it, and exports it four ways:
  GeoJSON, **KML for Google Earth**, a card on the live dashboard (top-5 with clickable
  coordinates), and an **"Affected area: ON/OFF"** toggle in the 3-D explorer. Both rankings the
  operator asked for ship side by side and are **named apart**: vulnerability (m\*, §19) and triage
  priority ((1−m\*)×P, §25).
- **★★ It invents no science and cannot drift.** The outline is the *published* alert cluster
  re-derived and **verified pixel-for-pixel** against `alerts_<footprint>.json` — a mismatch aborts
  the run. The corridor is `flood_domain.d8_targets` (routing) truncated by `rockfall_runout.BANDS`
  (energy line) — both **imported**, never copied.
- **★★ The layer never flatters the map under it.** The verdict is read through
  `operational_alarm.load_tier` + `_chance_verdict`, so it inherits the §79 staleness guard and the
  derived wording. Three of four footprints therefore render **wearing** their status (VD ALERT =
  *not measured*; VD WATCH = *below chance*; Ramban WATCH = *≈chance*, which gets its own wording,
  not the withdrawn one). Ramban ALERT is the one that beats chance.
- **★ The identity gate caught MY bug on its first hard input** — the 106-zone WATCH map aborted
  because the orchestrator sorts on the *rounded* speed and I sorted the raw means (11 of 65 zones
  tie once rounded). Fixed + pinned behaviourally; logged 2026-08-11.
- **★ A pre-existing §78-class defect fixed in passing:** `aoi_status.py` printed a back-test AUC one
  line under "operational zones: none". It now reads **NOT MEASURED** when the map has moved, pinned
  by a two-directional test. §79 fixed this in the dashboard and nobody grepped the other renderer.
- **★★ AOI #3 — Tosh (upper Parvati Valley) — onboarded through playbook step 2.**
  `config/aoi/tosh_aoi.geojson` + `config/tosh.yaml`; placement **verified** against an independent
  published coordinate, not assumed. Radar dry-run: **38 pairs / 7 stacks, 34 new + 4 already
  held**; three stacks alone clear the velocity-baseline minimum. **Nothing submitted.**
- **⚠ Tosh is blocked on the three things that SHOULD block it** — the `soil:` block is deliberately
  absent (§42: inheriting the wrong soils swings the footprint 0–118 zones), there is no local
  inventory, and spending credits is the user's call.
- **★ Deliberately NOT built: a VD 3-D explorer.** It would have showcased a withdrawn map; the
  standing instruction to publish VD's WHEN arm only still holds.
- **Battery 197 → 220 green across 16 suites** (new `test_exposure_footprint.py` ×22, registry ×+1);
  flood freeze R1 reports identical re-writes only.
- **Carried honest limits unchanged** (VD WHERE below chance §80; NISAR monsoon unmeasured §82;
  inventory records REPORTS §60/§83; ~30 mm/yr noise floor §78; 598 m miss §31/§51; soils
  literature-corroborated not lab; §40 GACOS open). **§84 adds two:** the corridor is a **lower
  bound** (rockfall angles on a debris path), and a shape does not upgrade an unvalidated map.
  **⚠ Standing:** §52 — 2 inventory rows pending; §66 LOW web findings; Ramban's staleness warning
  (16 new ASC scenes through 08-05) + its deferred §61 rescore.

## Recommended next step

**Task order is unchanged by this session — except that Tosh now has a cheap, high-value fork.**

1. **Tosh M2 (site soil pass)** — the one blocking step, and it is a literature pass (GSI Kullu
   reports, Parvati/Malana hydel geotechnical studies), not fieldwork. Until it lands, nothing
   downstream at that site should be believed. *Then* the user's go/no-go on ~34 HyP3 jobs.
2. **Susceptibility model as a CORROBORATOR** (§83's verdict) — elevation-ablated AUC is the
   headline, never the raw one (§60).
3. **NISAR when the data allows** — trigger unchanged: ≥8 acquisitions on one track/frame, or NASA
   clearing the monsoon void.

**Do NOT:** present the affected-area shapes as a warning product at Vaishno Devi; lower the reach
angles to make corridors look longer; give Tosh another site's soils; or submit Tosh's jobs without
the user saying so.

## Uncommitted delta

Code (all new work, tree was clean at `16019ea`):
- **NEW** `workflows/exposure_footprint.py` — the affected-area layer.
- **NEW** `tests/test_exposure_footprint.py` (22 tests, incl. an escaping negative control).
- `workflows/build_3d_dashboard.py` — draped outline/corridor traces + the ON/OFF control (scenario
  buttons now restyle **explicit** trace indices so they cannot flip the new layer).
- `workflows/operational_alarm.py` — `load_exposure` + `_exposure_card` (pure insertion; parity
  tested).
- `workflows/live_alarm.py` — non-fatal hook so the layer refreshes before the dashboard renders.
- `workflows/aoi_status.py` + `tests/test_config_registry.py` — the stale-AUC fix and its test.
- **NEW** `config/tosh.yaml`, `config/aoi/tosh_aoi.geojson` (the source `.kml` is git-ignored by
  policy — it lives at `config/aoi/tosh_and_others.kml` locally; provenance is recorded inside the
  GeoJSON).

Docs: `RESULTS_AND_KPIS.md` **§84**; `error_history_log.md` (2 defects); `milestone.md` **M65**;
primer **CV6** + 2 Part-D answers + 2 Part-E limits; `session_journey.md` (git-ignored);
this LIVE block.

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

- Env (native): `insar_qa_env` at `C:\Users\varun\.conda\envs\insar_qa_env\`.
- HyP3 credits: **~7,900 as of 2026-08-08** (§77 — 8000 verified pre-refresh, ~100 on the VD cadence refresh; the §61 7,430 balance replenished since). Radar library **248 products** (238 + 10 §77). Disk: **56 GB** in `data/` measured 2026-08-11 (§48/§77/§83 — raw zips Drive-archivable; +~3 GB from the §77 refresh, and **`data/nisar/` is now 5.7 GB** across 3 granules plus ~160 MB of adapted rasters).
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
   runbook), `tests/test_config_registry.py`. **Registry holds THREE sites since 2026-08-11 —
   `ramban`, `vaishnodevi` and `tosh` (upper Parvati Valley, §84); Tosh sits at playbook step 2,
   blocked on its soil pass (M2), its inventory (M4) and the user's go/no-go on ~34 HyP3 jobs.**
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

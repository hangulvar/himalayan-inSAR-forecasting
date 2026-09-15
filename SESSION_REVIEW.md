# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It has two blocks:

- **LIVE** — regenerated at the end of each session (by `/wrap-session`): current state, next step, uncommitted delta.
- **STABLE** — read order, environment gotchas, open questions, roadmap: edited only when a fact changes, never rewritten per session.

**House rule: no headline KPI/score is restated in this file.** Every number lives once, in
`RESULTS_AND_KPIS.md` — this file cites the § only. (Pre-streamline verbose version archived at
`docs/archive/local/SESSION_REVIEW_pre-streamline_2026-07-03.md` and in git history.)

---

# LIVE — Session 37 · branch `aoi-vaishnodevi` · updated 2026-09-07

## Current state

- **★★ AOI #4 — Triund (Dhauladhar) — onboarded to playbook step 2, and used immediately to answer
  a user question with a DATE on it** (trek on 26 Sep 2026). Full numbers: `RESULTS_AND_KPIS.md`
  **§87**. Polygon verified against 12 OSM-authoritative waypoints (12/12 inside) and the **tightest
  in the registry**; DEM validated against surveyed spot heights before anything was built on it.
- **★★ This is the first registry site that publishes a product with NO validation score, on
  purpose.** Radar could not contribute — a velocity baseline needs 2–3 months and the AOI was 19
  days old — so the deliverable is terrain + rainfall only: **no soil pass, no inventory, no FS map,
  no AUC.** The registry file records *why* radar cannot help so nobody re-asks. It must never be
  cited alongside the scored sites.
- **★ New method: the runout cone as a whole-landscape raster** (§87C, primer **CV7**). CV5's energy
  line swept from one polygon; this computes every cone at once as a max-plus chamfer transform,
  **restricted to downhill propagation so a cone cannot climb a ridge** — the gap CV5 explicitly
  named. Validated against exact brute force: **0 cells where it over-reaches**, 77 where it is more
  cautious. The approximation is provably conservative.
- **★ The headline for the user:** the Galu Devi → Triund climb is **100% inside some cone, zero
  clear metres**; the longest continuous exposed run independently reproduces the elevation band
  local guides call the "22 Curves". The approach below the checkpost and the stretch above Snowline
  are entirely clear (§87C).
- **★ An AI-generated risk report supplied by the user was verified line by line — §36–§38 repeated
  exactly** (§87E). Sound on geology; its September rainfall figure is **2.3× low** for this AOI and
  is what its "safe window" verdict rests on; two events excluded as unsupported; two citations do
  not support their sentences. **The most decision-relevant fact was cited but unread** — a standing
  6 Jan 2026 Kangra DDMA order requiring SP permission for the Triund route and banning trekking
  above 3,000 m. Lesson recorded: *when auditing a synthesis, read its sources, not its sentences.*
- **6 defects logged, all mine, none in production code** (`error_history_log.md` 2026-09-07). The
  serious one: distance along the trail summed **chords** between 25 m samples, under-measuring the
  route **8%** — ~400 m of error heading into a file a person carries up a mountain. Caught only
  because two code paths disagreed on one percentage. Also: a 61%-flagging source threshold that
  discriminated nothing, and a waypoint narrated from memory that put the summit 0.9 km off.
- **Battery: 14/16 suites green natively.** `test_flood_gate` + `test_tier34` cannot run natively
  (documented matplotlib **exit 127, zero output**) — Docker was down and deliberately not started
  (§85 / CLAUDE.md 16). **`test_config_registry` 13/13** with the fourth AOI, which is the guard that
  actually protects the registry. **These two suites still owe a Docker run.**
- **Carried honest limits unchanged** (VD WHERE below chance §80; NISAR monsoon unmeasured §82;
  inventory records REPORTS §60/§83; ~30 mm/yr noise floor §78; §84's two; §86's portability limit).
  **§87 adds one:** a site whose rainfall context comes from 5–11 km products over a 3.5 km-wide
  scarp — CHIRPS and IMERG disagree on P(wet) 31% vs 60%, and that spread *is* the answer.
- **⚠ Standing:** §52 2 inventory rows; §66 LOW web findings; Ramban's staleness warning + deferred
  §61 rescore; **Tosh still blocked on soil pass (M2), inventory (M4) and your credit decision —
  now the recommended next step for a third consecutive session.**

## Recommended next step

**Unchanged, and now overdue — Tosh is the bottleneck, not Triund.**

1. **Tosh M2 (site soil pass)**, then your go/no-go on ~34 HyP3 jobs. *(§86's literature search
   found no Parvati-specific geotechnical source — neighbouring districts scatter φ≈0–36° — so
   expect a bracketed, explicitly provisional pass.)*
2. **Susceptibility model as a CORROBORATOR** (§83) — elevation-ablated AUC is the headline.
3. **NISAR when the data allows** — ≥8 acquisitions on one track/frame, or the monsoon void clearing.

**Triund needs nothing before 26 Sep** — the screening is what the data honestly supports. Its
backlog (M2 soil, M3 ALOS DEM, M4 inventory, radar go/no-go) is next-season work.

**Do NOT:** present Triund's screening as a validated product or quote an AUC for it; re-enable the
scheduled task without answering the missed-slot/Docker-down questions; add a CSP without deciding
the CDN question; present VD's shapes as a warning product.

## Uncommitted delta

Code: **none** — no production script changed this session.

New (untracked, to commit): `config/triund.yaml`, `config/aoi/triund_aoi.geojson`,
`config/aoi/triund_route.geojson`.

Docs: `RESULTS_AND_KPIS.md` **§87** (A–F); `error_history_log.md` (2026-09-07, 6 entries + a
"what held" block); `milestone.md` **M67**; primer **CV7** + 2 Part-D answers + 1 Part-E limitation;
`session_journey.md` (git-ignored); this LIVE block.

Artifacts (git-ignored, `data/triund_screening/`): `triund_dashboard.html` (published Artifact),
`triund_screening.kml` (**475/475 placemarks carry the caveat**), `triund_screening.geojson`.

Machine state (outside git, unchanged): the Windows task **"InSAR Monsoon Watch Cycle" is
Disabled**.

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

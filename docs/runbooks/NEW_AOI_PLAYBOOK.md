# 🧭 NEW AOI PLAYBOOK — point the pipeline at a new site

The deterministic, end-to-end recipe for onboarding a **new Area of Interest**,
distilled from doing it twice (Ramban → Vaishno Devi). Every automated step names
its command, container image, and the artifact that proves it ran; every **manual
step (M1–M5)** says exactly what a human must fetch or decide, and why it cannot
be automated.

**What you are building (the claim to carry):** a **decision-support
prioritization prototype** for the new site — it ranks WHERE slopes deserve
inspection and WHEN vigilance should rise, validated against a local inventory.
It is not a warning system and must never be presented as one.

**Companion tools:**

- `python workflows/aoi_status.py` — the multi-AOI dashboard: shows every site's
  stage checklist, current alarm state, and **the next command to run** (this
  playbook's steps, automated as far as they can be detected). Writes
  `data/aoi_status.html` + `.json`.
- `config/` — the AOI registry, one YAML per site. Three ways to target a site,
  in precedence order:
  1. `--config config/<aoi>.yaml` on the scripts that expose the flag
     (submitter, downloader, inverter, network graph);
  2. the **`INSAR_CONFIG` env var** — works for *every* script:
     `docker compose run --rm -e INSAR_CONFIG=config/<aoi>.yaml insar python ...`
     (natively: `$env:INSAR_CONFIG='config/<aoi>.yaml'`);
  3. the root `config.yaml` — a one-line `active_config:` pointer selecting the
     default AOI (edit it to switch the whole pipeline).

**Ground rules that keep two (or ten) AOIs from colliding:**

- Each AOI has a unique **slug** (from `aoi_path`: `<slug>_aoi.geojson`) and a
  unique `job_name_prefix`. The slug drives per-AOI output separation:
  Phase 2–4 dirs get `_<slug>` suffixes (`data/velocity_<slug>`, `data/hazard_<slug>`,
  `data/alerts_<slug>`, `data/mosaic_<slug>`, `data/dem_alos_12m_<slug>`), and
  rainfall/alarm files get `<slug>_` prefixes. Ramban is grandfathered on the
  unsuffixed dirs.
- The **Phase-1 radar library is shared** (`data/raw_zips`, `data/processed_tiffs`,
  `data/qa_masks`): products are keyed by Sentinel-1 stack (direction/path/frame)
  in `data/qa_masks/_stack_manifest.json`, so two AOIs on the same frames reuse
  the same downloads — a feature, not a bug.
- Every workflow script is **idempotent** — re-running is always safe.

---

## Phase 0 — Prerequisites (once per machine, not per AOI)

Covered in README ("Authentication & API Setup" + "Environment Setup"): Earthdata
account + `~/.netrc` + HyP3 OAuth approval, Docker images (`docker compose build`,
`docker compose build mintpy`), optional CDS/GEE credentials in `.env`.
Check HyP3 credits before starting: a full Phase-1 pull for one AOI costs roughly
what one AOI's stack count implies (~50–180 pairs; VD's 49-pair pull is the
reference; see SESSION_REVIEW §2 for the current balance).

---

## Step 1 (M1, manual) — Draw the AOI polygon

1. Draw the polygon in Google Earth Pro (or QGIS) around the corridor/slope of
   interest. Keep it tight: a better polygon improves *targeting*, not the noise
   floor. Save as KML → convert to GeoJSON (EPSG:4326).
2. Name it `config/aoi/<slug>_aoi.geojson` (e.g. `config/aoi/chashoti_aoi.geojson`
   — the filename defines the slug).
3. If the deliverable is route safety, also save the route/track as
   `config/aoi/<slug>_route.geojson` (used by `route_exposure.py`).

**Verify:** the file loads in geojson.io and sits where you think it does.

## Step 2 — Create the registry config

Copy `config/vaishnodevi.yaml` → `config/<slug>.yaml` and edit:

- `aoi_path: config/aoi/<slug>_aoi.geojson`, `site_name`, a unique `job_name_prefix`
- `search_start`/`search_end`: ~6 months of pre-monsoon baseline through the
  season of interest (a new AOI needs **~2–3 months of acquisitions minimum**
  for a velocity baseline; longer = lower noise floor)
- Leave `operational_m`/`watch_m` OUT until Step 9 (defaults 0.50/0.70 apply)
- Leave `soil:` OUT until Step 3 tells you otherwise — but do Step 3
- Optionally point the whole pipeline at it: edit `active_config:` in root
  `config.yaml`. Otherwise pass `--config config/<slug>.yaml` per command.

**Verify:** `python workflows/aoi_status.py --aoi <slug>` shows the new card with
Step 1 green and the next command.

## Step 3 (M2, manual) — Site soil pass

The infinite-slope engine needs shear-strength parameters (`c_dry`, `c_wet`, φ,
γ, depth). **Do not silently inherit another site's values** — and this is now
**measured, not just principled** (§42, re-confirmed on the kappa=0.06 physics
§47): across the literature-plausible bracket the operational footprint swings
0–118 zones (0–125 pre-kappa), and in-bracket depth/cohesion values can erase
the alert product entirely. **Failure depth z is the single most load-bearing
number** — prioritize pinning it. Re-tuning the operating point m (or kappa)
cannot substitute (soil strength and m are degenerate spatially, but the
rainfall→m→FS WHEN-gate calibration needs soils to be physically right,
§42/§47 — under kappa the config baseline is the envelope's best scorer, so the
tuned operating point is calibrated to *these* soils specifically).

Process (as done for VD, §37):

1. Search site literature: GSI landslide-susceptibility reports for the district,
   back-analysis papers, geotechnical studies of nearby road/rail projects.
2. Extract soil-mantle (NOT rock-joint) c/φ ranges + overburden depth.
3. Pick conservative values inside the bracket; record provenance as comments in
   the `soil:` block of `config/<slug>.yaml`.
4. If literature is silent, start from the engine defaults (Ramban §20) and mark
   the site's dashboard caveat "borrowed soils" until a local pass exists — and
   treat the map as provisional given §42.

**Verify:** `soil:` block present in the registry file (aoi_status flags it).
After Step 8, also run the per-site sensitivity artifact (seconds,
non-destructive — backs up and checksum-restores the FS rasters):

```bash
docker compose run --rm -e INSAR_CONFIG=config/<slug>.yaml insar \
  python workflows/soil_sensitivity_sweep.py
```

It reports which soil parameters your site's product stands on
(`data/inventory/soil_sensitivity_report_<slug>.md`).

## Step 4 — Phase 1: pull + QA the radar

Image: `insar` (or native env). All idempotent; `--config` as needed.

```bash
python workflows/submit_hyp3_jobs.py --config config/<slug>.yaml            # dry-run preview
python workflows/submit_hyp3_jobs.py --config config/<slug>.yaml --submit   # queue at ASF (~hours)
python workflows/download_hyp3_products.py --watch --download --extract
python workflows/feature_engineering.py        # coherence masking
python workflows/phase_elevation_audit.py      # atmospheric audit
python workflows/export_audit_json.py
python workflows/_consolidate_quarantine.py    # KEEP/CONCERN/QUARANTINE
python workflows/sbas_network_graph.py         # connectivity + rescue recommendations
python workflows/apply_connectivity_rescues.py # quality-gated bridges only
python tests/test_plumbing.py
```

**Verify:** `data/qa_masks/_network_graphs/index.html` shows connected chains for
the new stacks; `_stack_manifest.json` has the new products (metadata-derived).

## Step 5 (M3, manual, recommended) — 12.5 m ALOS DEM tile

The 30 m HyP3 DEM works (the pipeline falls back automatically), but the 12.5 m
ALOS PALSAR RTC DEM sharpens slope and was worth it at both sites (§21, §30).

1. ASF Vertex (https://search.asf.alaska.edu) → dataset **ALOS PALSAR** →
   product **Hi-Res Terrain Corrected** over the AOI → download one tile.
2. Extract the `*.dem.tif` into `data/dem_alos_12m_<slug>/`.

**Verify:** `aoi_status.py` DEM row goes green; the engine logs "ALOS 12.5 m" on
its next run. **Gotcha:** a tile covers ONE site — never reuse another AOI's.

## Step 6 — Phases 2–4: invert, model, alert (one driver)

Image: `insar`.

```bash
docker compose run --rm -e INSAR_CONFIG=config/<slug>.yaml insar python workflows/run_multistack.py
```

Inverts every connectable stack (Phase 2), runs the geomechanical engine with the
config's soils (Phase 3), and builds the per-look + **union** hazard/alert
products for all scenarios including `operational` and `watch` (Phase 4).

**Verify:** `data/alerts_<slug>/mosaic_asc/alerts_operational.json` exists with
zones; `data/mosaic_<slug>/` has the union rasters. Optional UIs:
`build_3d_dashboard.py`, `agentic_orchestrator.py`.

## Step 7 (M4, manual) — Verified landslide inventory

Validation is meaningless against unverified ground truth (§12g — a single wrong
news date once inverted a conclusion; the 2026-07-11 decontamination showed
LLM-synthesis docs fabricate events). Build it the immunized way:

1. Sources: GSI Bhukosh/NGDR portals (field-validated), district disaster
   records, peer-reviewed papers; press only as a *lead*, verified against 2+
   independent outlets, distinguishing event date from publication date.
2. Record every feature with provenance; record **exclusions** explicitly (the
   exclusion notes are immunization records — never delete them).
3. Save as `data/inventory/<slug>_documented_landslides.geojson`.

**Verify:** `ingest_gsi_inventory.py`/`backtest_inventory.py` load it cleanly.

## Step 8 — Scored validation

```bash
docker compose run --rm -e INSAR_CONFIG=config/<slug>.yaml insar \
  python workflows/backtest_inventory.py \
  --alerts data/alerts_<slug>/mosaic_asc/alerts_operational.json \
  --inventory data/inventory/<slug>_documented_landslides.geojson
```

**Verify:** `data/inventory/backtest_operational_<slug>_report.json` — AUC above
0.5 (beats chance) before trusting the map. Repeat for `alerts_watch.json`.
Record headline numbers in `RESULTS_AND_KPIS.md` (append, tag `[REAL]`).

## Step 9 (M5, agent-assisted) — Site-tuned operating points

```bash
docker compose run --rm -e INSAR_CONFIG=config/<slug>.yaml insar \
  python workflows/rainfall_selectivity_backtest.py
```

Sweeps assumed saturation m, scoring each against the inventory. Pick the ALERT
plateau + a WATCH point at high recall (VD: 0.40/0.75, §32) and set
`operational_m`/`watch_m` in `config/<slug>.yaml`. Re-sweep when the inventory
grows or chains lengthen.

## Step 10 — Rainfall + live operations

```bash
# baseline back-test season (once):
docker compose run --rm -e INSAR_CONFIG=config/<slug>.yaml mintpy python workflows/fetch_rainfall.py
# live cycle (every 2–3 days through the season; both images, in this order):
docker compose run --rm -e INSAR_CONFIG=config/<slug>.yaml mintpy python workflows/live_alarm.py
docker compose run --rm -e INSAR_CONFIG=config/<slug>.yaml insar  python workflows/live_alarm.py
```

(Drop the `-e INSAR_CONFIG=...` when the site is already the `active_config`
pointer's target.)

Then follow the control panel (`control_panel.bat`) or scheduled cycle; manual fallback: `docs/archive/Monsoon Watch Runbook (2026-07-11).md` (escalation
triggers, coherence_watch after storms). The radar-cadence cycle (~every 2
weeks; SESSION_REVIEW roadmap #1) keeps chains growing: resubmit → download →
QA → `run_multistack` → `route_exposure` → `live_alarm` → `coherence_watch`.

---

## Operating multiple AOIs at once

- **Status of everything:** `python workflows/aoi_status.py` — one card per
  registry file, each with its own next step. Publish/inspect
  `data/aoi_status.html`.
- **Per-command targeting** beats switching the global pointer: run each AOI's
  cycle with its own `-e INSAR_CONFIG=config/<slug>.yaml`. The suffix/prefix
  scheme guarantees outputs never collide; the shared radar library dedupes
  downloads on shared frames.
- **Live cadence for N sites** is N invocations of the same two `live_alarm`
  commands (each with its own `INSAR_CONFIG`); they're independent and
  idempotent — safe to script sequentially.
- **Docs discipline per site:** headline KPIs go in `RESULTS_AND_KPIS.md`
  (append-only, tagged, cite §), field briefs in `docs/briefs/`, and the site's
  operating points + soils live ONLY in its registry file.

## Scaling architecture (where this design is headed)

- **Config = the unit of scale.** Everything site-specific is in one YAML;
  everything else derives from the slug. Adding AOI #3 is: polygon + registry
  file + M2/M3/M4 manual passes + the same commands.
- **Known debt if AOIs multiply past a handful:** (a) the grandfathered
  unsuffixed Ramban dirs — migrate to `data/<slug>/...` roots in one move when
  it hurts; (b) `per_zone_gate.py` outputs are unsuffixed (last-run-wins,
  noted in `live_alarm.py`); (c) Phase-1 QA CSVs are stack-keyed but live in one
  shared dir — fine while stacks are unique per (path, frame).
- **NISAR (the next sensor):** L-band GSLC/GUNW products land at the same
  architectural seam as HyP3 GAMMA products — a downloader + adapter feeding
  `data/qa_masks/` per stack. Build the GUNW adapter once ~8+ same-track pairs
  exist over any AOI (SESSION_REVIEW roadmap #1); every registry AOI then gets
  it for free, because everything downstream is stack- and config-driven.
- **What stays honest at scale:** each new site still owes its own soil pass
  (M2), its own verified inventory (M4), and its own m-sweep (Step 9). These are
  the scientific-transferability steps — no amount of config plumbing replaces
  them (SESSION_REVIEW §3 "new-AOI replication readiness").

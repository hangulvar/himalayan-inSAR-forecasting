Created: 2026-05-24 · Last reviewed: 2026-05-29
Status: LIVING DOCUMENT — **full end-to-end MVP COMPLETE** (Phases 1–4, pathfinder stack `ASC_path27_frame106`). Body synced to reality 2026-05-29. Future revisions track production hardening (MintPy, all 5 stacks, finer DEM, live weather).
Tags: #insar #hazard #ramban #roadmap #mvp-complete
___
# **InSAR Hazard Forecasting — Project Context & Roadmap**

> **How to read this file.** This is the project's *vision + roadmap*. For the
> live operational state, start with [SESSION_REVIEW.md](SESSION_REVIEW.md). For
> the plain-language story see [milestone.md](milestone.md); for the science see
> [Research/Foundations - Physics and Maths Primer.md](Research/Foundations%20-%20Physics%20and%20Maths%20Primer.md);
> for decisions and bugs see `session_journey.md` and `error_history_log.md`.

In the Himalayas, atmospheric noise is brutal, vegetation causes rapid decorrelation, and phase unwrapping errors will outright lie to you. We approach every deformation map as a flawed hypothesis until the noise has been audited.

---

## 📍 Current Status Snapshot (2026-05-29)

| Phase | Scope | Status |
|---|---|---|
| **Phase 1 — Data Pipeline & Integrity Check** | Extract Sentinel-1, mask noise, audit atmosphere, verify network | ✅ **COMPLETE** |
| **Phase 2 — SBAS Velocity Inversion** | Interferograms → LOS displacement time-series + mean velocity | ✅ **PATHFINDER COMPLETE** (1 of 5 stacks); multi-stack + mosaic pending |
| **Phase 3 — Geomechanical Engine** | Infinite Slope model → Factor of Safety, fused with InSAR velocity into a hazard map | ✅ **PATHFINDER COMPLETE** (1 of 5 stacks) |
| **Phase 4 — Agentic Orchestration & Visualization** | Part A: agentic warning system (alerts + dashboard) ✅ ; Part B: interactive 3-D explorer ✅ | ✅ **PARTS A & B COMPLETE** |

> **🎉 The full end-to-end MVP is complete and demo-able:** raw radar → clean
> data → LOS velocity → hazard map → **automated, explainable alerts → interactive
> 3-D explorer**, on the `ASC_path27_frame106` pathfinder stack. The deterministic
> 3-agent orchestrator (`agentic_orchestrator.py`) turns rainfall scenarios into
> geolocated alerts (dry → 29 zones; monsoon → 222), and `build_3d_dashboard.py`
> renders them on the 3-D terrain. **No new conceptual pieces remain** — all
> remaining work is *hardening* (MintPy, finer DEM, all 5 stacks, full APS) and
> *going live* (real weather, real flow-routing for LLOF, an LLM reasoning layer,
> a hosted UI). See the **Post-MVP Roadmap** at the foot of this document.

**Area of Interest:** the **NH-44 corridor through Ramban, Jammu & Kashmir**
(`ramban_aoi.geojson`, ~20×22 km over the Chenab valley). *(Note: the original
draft of this document proposed the Mandakini/Joshimath valley; we switched to
Ramban for its documented NH-44 slope failures and sharp ridge geometry.)*

**Where the project stands now:** the thin end-to-end MVP is **built and
demonstrable** on the pathfinder stack — raw radar → clean data → velocity →
hazard map → explainable alerts → interactive 3-D explorer. The MVP-first bet
paid off: completing the whole chain on one slice exposed the real weak links
(coarse 80 m slope, ~30 mm/yr velocity noise, sparse coverage) instead of us
guessing.

**Immediate next move (post-MVP):** *deepen trust before scaling presentation.*
The first hardening task is the **MintPy migration** (in a separate env, cross-
validated against the custom inverter on `frame106`), then widen to all 5 stacks
and adopt the 12.5 m DEM. See the consolidated **Post-MVP Roadmap** at the end of
this document, and `SESSION_REVIEW.md` for the live next-step recommendation.

---

### The Novel Idea: Agentic Multi-Modal Hazard Forensics

Current government and academic models largely operate in silos: one team looks at the InSAR displacement, another looks at the ERA5 weather forecasts, and a third looks at the hydrology. They usually only combine these datasets _after_ a disaster occurs to write a forensic report.

The novelty here is to build an **Autonomous Agentic Orchestrator** — a multi-agent system where distinct Python "agents" handle specific domains, audit each other's data, and reason through cascading effects.

- **Agent 1: The InSAR Auditor.** Queries the ASF HyP3 API for Sentinel-1 data and ruthlessly filters bad pixels using the interferometric coherence formula:

    $$\gamma = \frac{|\langle S_1 S_2^* \rangle|}{\sqrt{\langle |S_1|^2 \rangle \langle |S_2|^2 \rangle}}$$

    If $\gamma$ drops below a strict threshold (0.4) due to heavy Himalayan vegetation, it masks that data out and refuses to pass noise downstream.
    *➤ Status: ✅ **BUILT.** Its function is the Phase 1–2 scripts (`submit_hyp3_jobs.py`, `download_hyp3_products.py`, `feature_engineering.py`, `phase_elevation_audit.py`, `custom_sbas_inverter.py`), and it is wrapped as the `InSARAuditor` class inside the Phase-4A orchestrator. Still a deterministic module, not an LLM — an LLM wrapping is a future upgrade.*

- **Agent 2: The Meteorological Trigger.** Monitors the Copernicus CDS API for Western Disturbances and extreme rainfall, downscaling to the DEM grid. *➤ Status: ✅ **BUILT (MVP form).** Implemented as the `MeteorologicalTrigger` class with mock rainfall scenarios (dry / monsoon / extreme) that set assumed saturation and select the matching Factor-of-Safety layer. Live Copernicus CDS ingestion is deferred to hardening.*

- **Agent 3: The Cascading Reasoner.** If Agent 1 detects slope creep (e.g. −25 mm/year) and Agent 2 forecasts heavy rain, Agent 3 runs the Infinite Slope equation. If the slope fails _and_ sits above a river, it flags a potential Landslide Lake Outburst Flood (LLOF) downstream. *➤ Status: ✅ **BUILT.** Implemented as the `CascadingReasoner` class: fuses creep + instability (FS < 1 AND velocity < −15 mm/yr), clusters pixels into geolocated alert zones, and applies a heuristic LLOF flag (TWI valley proxy). Real flow-routing for LLOF is deferred.*

This architecture prevents the "garbage in, garbage out" problem that plagues remote sensing, while pushing the boundaries of automated disaster forecasting. **All three agents now run** as a deterministic, offline, reproducible pipeline (`agentic_orchestrator.py`); upgrading the reasoning layer to a real/hybrid LLM is a documented future step.

---

## Project Execution Plan (renumbered to match reality)

> **Numbering note.** The original draft had a 4-phase plan that went straight
> from data (Phase 1) to the geomechanical engine (Phase 2). In practice,
> turning masked interferograms into a *velocity* required a full SBAS
> time-series inversion — substantial enough to be its own phase. We therefore
> inserted **Phase 2 — SBAS Velocity Inversion**, which shifts the geomechanical
> engine to Phase 3 and the agentic/visualization work to Phase 4. The timeline
> ("weeks") from the original draft is treated as indicative, not binding.

---

### ✅ Phase 1 — The Data Pipeline & Integrity Check  *(COMPLETE)*

**Goal:** before predicting anything, produce clean, reliable, audited data.

**What was actually built and run:**

1. **Spatial/temporal query.** AOI = `ramban_aoi.geojson`. Window: 2025-05-01 →
   2025-10-31 (full monsoon + post-monsoon). 183 Sentinel-1 SLC interferograms
   ordered as `INSAR_GAMMA` products from ASF HyP3.
2. **SBAS N=3 network.** Rather than a simple chain, we built a Small-Baseline
   network (each scene paired with its next 3 neighbours, ≤40-day baseline),
   strictly partitioned into **5 stacks** by `(flightDirection, path, frame)` —
   3 ascending + 2 descending. Ascending and descending are **never mixed**.
3. **Coherence masking** (`feature_engineering.py`): convert unwrapped phase →
   LOS displacement, then `if γ < 0.4 → NaN`. Only persistent scatterers (rock,
   infrastructure, bare earth) survive. RAM-safe, iterative, idempotent.
4. **Atmospheric audit** (`phase_elevation_audit.py`): per-interferogram
   correlation (R²) of displacement vs DEM elevation. R² > 0.5 ⇒ tropospherically
   contaminated ⇒ quarantined. Combined with a coherence-of-survivors check into
   a consolidated KEEP / CONCERN / QUARANTINE decision per pair.
5. **Network connectivity check** (`sbas_network_graph.py`): a union-find graph
   analysis confirming the KEEP edges form a single connected component per stack
   (so the later least-squares inversion is well-posed). Where quarantining broke
   the chain, a minimal set of CONCERN pairs was "rescued" to bridge gaps.

**Outcome:** 183 audited LOS-displacement rasters in `data/qa_masks/`
(105 KEEP / 24 CONCERN / 54 QUARANTINE). Every surviving pixel is real ground,
not trees or clouds.

**Refinements / deviations from the original plan (captured for honesty):**
- AOI changed Mandakini → **Ramban**.
- Added an explicit **SBAS network + connectivity analysis** (original implied a
  simpler chain).
- The **perpendicular-baseline < 150 m rule was NOT strictly enforced** — HyP3
  does not filter on it and we have not yet audited it from metadata. Flagged as
  open technical debt.
- The original listed "LOS *velocity* arrays" as a Phase 1 deliverable; in
  reality velocity required the full Phase 2 inversion, so Phase 1's true output
  is clean *displacement* interferograms, not velocity.

---

### ✅ Phase 2 — SBAS Velocity Inversion  *(PATHFINDER COMPLETE)*

**Goal:** convert the web of relative interferograms into an absolute timeline,
yielding a single **Mean LOS Velocity (mm/year)** per pixel — the dynamic fuel
for the Phase 3 geomechanical model.

**What was built** (`custom_sbas_inverter.py`, run on the cleanest stack
`ASC_path27_frame106`):

1. **Design matrix + least squares.** Solve $A\,d = m$ for cumulative
   displacement at each date (reference date fixed at 0). The connected network
   is full-rank, so Ordinary Least Squares suffices (no SVD needed for the
   ascending stacks).
2. **Per-interferogram deramping** *(critical addition not in the original plan)*:
   each interferogram carries an orbital/atmospheric ramp + arbitrary unwrapping
   constant. We fit and subtract a 2-D plane from each one *before* inversion.
   Skipping this produced physically impossible ±300 mm/yr velocities; adding it
   fixed the result and 10× the usable pixels. *(See `error_history_log.md`.)*
3. **Per-pixel variable-network solve.** Each pixel is inverted over whatever
   pairs survived its mask, provided they still span all dates — far more
   coverage than requiring every pixel to survive every pair.
4. **Temporal-coherence quality mask** (γ_temporal ≥ 0.7): rejects pixels whose
   time-series doesn't reproduce its observed pairs (unwrapping errors).
5. **Spatial high-pass (APS, staged approach):** a NaN-aware Gaussian high-pass
   strips broad atmospheric haze while preserving localized landslide signal. A
   full spatiotemporal APS filter is deferred until we know we need it.
6. **AOI clipping + local reference pixel.** HyP3 products are full ~294 km
   frames; we clip to the AOI + buffer and reference to a stable pixel *inside*
   the AOI so orbital ramps don't dominate.

**Deliverables produced** (in `data/velocity/`, for the pathfinder stack):
- `..._mean_velocity_los.tif` — mean LOS velocity (mm/yr). Negative = motion away
  from the satellite (subsidence / downslope). **This is the Phase 3 input.**
- `..._mean_velocity_los_highpass.tif` — APS-filtered velocity.
- `..._displacement_timeseries.tif` — cumulative displacement (mm), one band per
  date.
- `..._temporal_coherence.tif` — per-pixel quality (for downstream weighting).

**Current quality:** strict-AOI coverage ~13.6 %, high-passed median 0 mm/yr,
noise floor ~30 mm/yr — good for catching dramatic movers, not yet subtle ones.

**Still pending in Phase 2:** invert the other 2 ascending stacks and mosaic;
handle the descending stacks (`frame479` needs SVD; `frame484` is a period-split
case); decide if the noise floor warrants the full APS filter.

**Tooling decision — migrate to MintPy for production (post-MVP).** The custom
inverter (`custom_sbas_inverter.py`) is kept for the MVP because it works and is
fully understood. But **MintPy** — the peer-reviewed field-standard SBAS package
— is the intended production engine: it ingests ASF HyP3 products directly
(`prep_hyp3`) and natively provides what we currently lack (full ERA5
tropospheric correction, DEM-error correction, weighted inversion, and SVD for
the rank-deficient descending stacks). Plan: finish the MVP on the custom
inverter, then make the MintPy migration the **first production-hardening task**,
installed in a **separate env / WSL** (Windows is second-class for it — must not
destabilize `insar_qa_env`) and **cross-validated against the custom result** on
`frame106`. This also strengthens the public-release narrative: *built our own to
learn the mechanics, then migrated to / validated against the standard tool.*

---

### ✅ Phase 3 — The Geomechanical Engine  *(PATHFINDER COMPLETE)*

**Goal:** physicalize the risk — calculate whether a slope is actively failing,
and fuse that physics with the measured InSAR creep.

**What was actually built** (`geomechanical_engine.py`, on `ASC_path27_frame106`):

1. **DEM → master grid.** Reprojected the **bundled 80 m HyP3 DEM** onto the
   Phase-2 velocity grid (no GEE/download for the MVP). *Decision: use the
   already-co-registered 80 m DEM now; the 12.5 m ALOS DEM is a hardening upgrade.*
2. **Slope angle** from the DEM via `numpy` gradients (no `RichDEM`/`xarray-spatial`
   dependency).
3. **Topographic Wetness Index (TWI)** via a self-contained D8 flow accumulation
   (MVP-grade; documented as approximate).
4. **1-D Infinite Slope Factor of Safety** for two saturations —
   `FS = [c' + (γ − m·γ_w)·z·cos²β·tanφ'] / [γ·z·sinβ·cosβ]` — with **m=0 (dry)**
   and **m=1 (saturated/monsoon)**. Soil parameters are literature defaults
   (c'=5 kPa, φ=32°, γ=19 kN/m³, z=3 m), all CLI-overridable.
5. **Hazard fusion (headline):** a 3-class map where **HIGH = FS_saturated < 1.0
   AND measured creep < −15 mm/yr**, WATCH = one condition, LOW = neither.

**Deliverables produced** (in `data/hazard/`): `..._slope_deg.tif`, `..._twi.tif`,
`..._FS_dry.tif`, `..._FS_saturated.tif`, `..._hazard_class.tif`.

**Results:** slope median 28° (steep, sane); **FS_dry 13% unstable vs
FS_saturated 73% unstable** — the monsoon flip *is* the hazard story; ~2,600 HIGH
pixels (unstable AND creeping).

**Refinements / deviations from the original plan:**
- **80 m DEM, not 12.5 m** (MVP) — under-resolves slope, biasing FS toward
  "stable." Documented limitation; 12.5 m is the planned upgrade.
- **Velocity is a separate evidence layer, not a term inside FS** — the honest
  reading of "active stress multiplier," and it matches the Phase-4 alert rule.
- **Soil parameters are assumptions**, so the FS map is a *relative* screening
  tool; we lean on the measured-motion half of the hazard rule.

**Key MVP finding:** the HIGH class is noisy (many isolated single-pixel specks),
because saturated-FS flags 73% of slopes — so the fusion is dominated by "wherever
creep was measured." This *is* the MVP exposing its weak links (coarse slope,
velocity noise). Phase 4A's clustering (≥3 px) addresses the specks.

---

### ✅ Phase 4 — Agentic Orchestration & Visualization (the Warning System)  *(PARTS A & B COMPLETE)*

**Goal:** connect the static models into a dynamic, reasoning system, and surface
its findings.

#### Part A — The Agentic Warning System  *(`agentic_orchestrator.py`)*

A **deterministic** orchestrator (offline, reproducible, no LLM/API keys)
embodying the 3-agent vision as Python classes:
- **InSARAuditor** flags confident creep from the velocity + temporal-coherence rasters.
- **MeteorologicalTrigger** turns a mock rainfall scenario (dry/monsoon/extreme)
  into a saturation assumption → selects the matching FS layer.
- **CascadingReasoner** fires alerts where FS < 1 AND creep, clusters pixels into
  zones (drops < 3 px specks), geolocates each (UTM→lon/lat), writes plain-English
  reasoning, and applies the heuristic LLOF flag.

**Deliverables** (per scenario, in `data/alerts/`): `alerts_<sc>.json` (structured),
`alert_report_<sc>.md` (briefing), `dashboard_<sc>.html` (self-contained 2-D map +
reasoned alert cards). **The cascade is visible:** dry → 29 alert zones,
monsoon → 222.

#### Part B — Interactive 3-D Hazard Explorer  *(`build_3d_dashboard.py`)*

A single self-contained **Plotly.js (CDN) HTML** (`data/alerts/dashboard_3d.html`):
draped 3-D terrain, a toggle-able measured-creep overlay, per-scenario alert
markers with hover reasoning, and scenario buttons.

**Deviation from the literal spec:** built as a static Plotly HTML instead of a
**Streamlit + Pydeck** app — zero new Python deps, never touches `insar_qa_env`,
same WebGL 3-D experience, verifiable as a file. A hosted Streamlit version
remains a future option in a separate env.

**MVP caveats (both parts):** deterministic rules (not yet an LLM); mock rainfall
(not live forecasts); velocity coverage ~14% (unmeasured ≠ safe); LLOF is a TWI
heuristic; single ascending stack.

---

## 🔭 Post-MVP Roadmap (what's next, consolidated)

The core vision is fully built and demonstrable; **no new conceptual pieces remain
to invent.** Remaining work is *infrastructure*, *deepening trust*, and *deployment*:

**0. Infrastructure & portability (do FIRST — assessed Session 7, 2026-05-29):**

0a. **Containerize on Linux (Docker).** Strongly recommended as the opening move,
   ahead of MintPy. Rationale: **nearly every multi-hour bug in
   `error_history_log.md` is Windows-specific** (the `0xC06D007F` BLAS-DLL crash,
   the matplotlib draw crash, conda-4.12 solver hangs, the cp1252 logging error,
   `_netrc`-as-a-folder). A Linux container eliminates that entire class, is the
   platform MintPy is developed/tested on, and **is the "separate env" done
   properly** — reproducible and portable. Notes: base on miniforge/micromamba +
   `environment.yml` + a pinned lockfile; **mount `data/` (~73 GB) as a volume,
   never bake it into the image**; mount `~/.netrc` read-only for Phase-1 ASF
   access; on Windows run via Docker Desktop (WSL2). The Dockerfile + lock also
   becomes the definitive **public-release reproducibility artifact**. (The
   in-script Windows DLL bootstrap becomes a harmless no-op on Linux.)

0b. **AOI-parameterization refactor.** The pipeline is currently **hardwired to
   Ramban** — a new AOI runs the first step then breaks, and even Ramban only runs
   one stack end-to-end today. Needs: (i) a `config.yaml` for AOI path, job-name
   prefix, time window and baseline rules (replacing the hardcoded
   `ramban_aoi.geojson` / `Ramban_NH44`); (ii) a single shared `stacks.py` that
   derives stack labels from product **metadata** (pathNumber/frameNumber) rather
   than the Ramban-orbit-specific acquisition time-of-day codes in `stack_key()`
   (duplicated across ~5 files); (iii) an **automated** connectivity-rescue step —
   `apply_connectivity_rescues.py` currently hardcodes a Ramban product-ID list,
   so it must auto-select lowest-R² bridging CONCERN pairs instead; (iv) a
   **multi-stack driver + mosaic** (Phases 2–4 default to a single stack). Fold in
   the still-unenforced <150 m perpendicular-baseline rule here too.

   **AOI guidance (assessed Session 8) — *targeting, not precision*.** A better
   AOI improves *what ground we look at*, **not** measurement quality. It will
   **not** lower the ~30 mm/yr noise floor, improve the 80 m resolution, or fill
   vegetation coverage gaps (those are fixed by 12.5 m DEM + full APS + MintPy,
   not the polygon). What it *does* improve: scene/stack selection and analysis
   focus. So draw a **domain-informed** polygon that hugs the NH-44 corridor, the
   **slopes above the road**, and the **Chenab river reach** (needed for the
   downstream/LLOF logic) — not an arbitrary rectangle. Notes: bigger ≠ better
   (more frames = more HyP3 credits + more stacks); extra coordinate *precision*
   is irrelevant (Sentinel-1 frames are ~250 km) — *placement and shape* are what
   matter. **Workflow:** draw the polygon in **Google Earth Pro** (Add → Polygon),
   Save As `.kml`, then convert to GeoJSON
   (`geopandas.read_file('aoi.kml').to_file('ramban_aoi.geojson', driver='GeoJSON')`,
   or QGIS as a reliable fallback); GE Pro polygons are already WGS84/EPSG:4326,
   which the submitter expects. **Bundle this with the next HyP3 pull** — changing
   the AOI forces a full Phase-1 re-run (credits + hours of download), so refine
   the AOI *once*, together with this refactor. A refined polygon that stays
   inside the *same* Sentinel-1 frames keeps the current `stack_key` valid; one
   that shifts to new paths/frames is exactly what (ii) above fixes.

**A. Trust / accuracy (after infrastructure):**
1. **MintPy migration** — the first *algorithmic* hardening task, run **inside the
   Linux container** (0a). Field-standard SBAS; ingests HyP3 directly; adds ERA5
   tropospheric + DEM-error correction + weighted inversion + SVD. Cross-validate
   against `custom_sbas_inverter.py` on `frame106`. *Never destabilise `insar_qa_env`.*
2. **All 5 stacks + mosaic** (3 ASC + 2 DESC; `frame479` needs SVD, `frame484` is
   the period-split case).
3. **12.5 m ALOS DEM** → sharper slope → more discriminating FS.
4. **Full spatiotemporal APS** → lower the ~30 mm/yr velocity noise floor.
5. **Calibrate / sensitivity-test soil parameters.**
6. **Enforce / audit the < 150 m perpendicular-baseline rule** (outstanding from Phase 1).

**B. Live / smarter:**
7. **Real Copernicus CDS rainfall** (replace mock scenarios).
8. **Real flow-routing for LLOF** (replace the TWI proxy).
9. **Upgrade the agents to a real/hybrid LLM** ("rules decide, LLM narrates" is the
   low-risk first step).

**C. Deployment / polish:**
10. Optional **hosted Streamlit** version of the 3-D dashboard (separate env).

---

## 🚀 Expansion Roadmap — Areas of Exploration Toward a Robust Forecasting Tool

*(Added 2026-05-31. Extends the Post-MVP Roadmap above with the broader strategic
menu. Status at time of writing: infra 0a Docker ✅ and 0b AOI/multi-stack ✅ done;
MintPy migration STEP 1 ✅ (image + ERA5 credentials); next = MintPy step 2 on
frame106. This is the durable copy mirrored from `SESSION_REVIEW.md` §6.)*

The current system is a demonstrable **MVP** of the full vision (radar → audited
data → velocity → physics hazard → explainable rainfall-driven warning). Each **AREA**
below is self-contained and can be picked up independently; together they take it
from MVP to a **defensible forecasting tool**.

**Where the MVP is weakest today (what these areas fix):** ~30 mm/yr velocity noise
floor; single-look (no true 3-D motion); assumed/uniform soil strength + dry/sat
end-members + TWI-proxy downstream flag; *mock* rainfall; a *static* hazard map (no
failure-timing); and no validation against real events.

### Area 1 — Noise reduction (measurement accuracy; the ~30 mm/yr floor)
- **MintPy ERA5 tropospheric correction** (in progress) — physically subtracts
  atmospheric delay; biggest single lever. **GACOS** (free) as an alternative/cross-check.
- **DEM-error correction + coherence-weighted inversion** (MintPy native).
- **Phase-linking / distributed-scatterer methods** (MintPy phase-linking,
  SqueeSAR-style) — recover coherence in *partially* vegetated Himalayan slopes (the
  biggest local win against vegetation decorrelation).
- **Enforce the <150 m perpendicular-baseline rule** (outstanding from Phase 1).
- *Payoff:* trust slower/smaller motions; fewer false creep flags.

### Area 2 — Signal strengthening (interpretation power)
- **All 5 stacks → ASC/DESC decomposition into vertical + east-west motion** — removes
  line-of-sight ambiguity; measure *real* slope movement, not a projection.
- **Persistent-scatterer (PS) points** on rock outcrops + NH-44 infrastructure —
  mm-precision anchors where distributed scattering fails.
- **Longer time series + seasonal-vs-steady-creep decomposition** — separate
  reversible seasonal swelling from progressive creep (avoid seasonal false alarms).

### Area 3 — From hazard MAP to FORECAST (the biggest conceptual upgrade)
- ★ **Inverse-velocity time-to-failure (Fukuzono/Voight)** — accelerating creep →
  1/velocity falls linearly toward zero → **predict failure timing**. Uses the
  per-pixel time-series we ALREADY produce. **Highest value for the least new data.**
- **Rainfall intensity–duration (ID) thresholds** — field-standard landslide trigger;
  couple measured creep with exceeded rainfall thresholds.
- **Calibrated, spatially-varying soil strength** (lithology/soil maps) + **distributed
  saturation** from real rainfall + soil moisture (replace dry/sat end-members + TWI proxy).
- **Real flow-routing / debris-runout modelling** for the LLOF flag (replace the TWI stand-in).
- *Payoff:* time-resolved, physically-grounded forecasts instead of a static map.

### Area 4 — Validation & uncertainty (credibility)
- **Back-test flagged zones against a landslide inventory** — documented Ramban
  failures; NASA Global Landslide Catalog; GSI Bhukosh (India). This converts "rough
  hazard map" → "validated forecast." *(First pass DONE 2026-06-01 — `backtest_inventory.py`
  vs a small curated inventory: spatially plausible, but the rainfall trigger MISSED the
  Apr–May 2025 events; see `RESULTS_AND_KPIS.md` §9.)*
  - **Enrich with GSI Bhukosh landslide data (recommended next).** GSI's georeferenced
    inventory holds **~302 field-mapped landslides in the Ramban sub-basin** (and is
    nationwide via the NGDR / Bhukosh / Bhusanket portals + WFS) — the authoritative ground
    truth. Ingesting it (the back-test tool takes it unchanged) upgrades the current
    *indicative* coincidence check to a **scored precision/recall** validation. This
    generalizes: **for any new AOI, pull that region's GSI Bhukosh inventory** (NASA GLC is
    only ~2007–2018 and too sparse for a single corridor) to validate before trusting the map.
- **Uncertainty quantification** — per-pixel velocity error bars propagated into FS/alerts.
- **Susceptibility model** (logistic regression / random forest on conditioning factors)
  trained + validated on the inventory → independent corroboration of the physics.

### Area 5 — Multi-sensor corroboration via GEE & free services (robustness)
- ⚠️ **GEE cannot do InSAR** (no SLC phase / interferometry) — InSAR stays on
  ASF/HyP3/MintPy; GEE adds everything *around* it.
- **Rainfall (live trigger + ID thresholds):** CHIRPS (daily), GPM IMERG (~30-min),
  ERA5-Land — all in GEE. Replaces the mock scenarios.
- **Soil moisture / saturation:** SMAP (~9 km), ASCAT.
- **Soil / lithology for spatial strength:** SoilGrids (250 m) → varying cohesion/φ.
- **DEM upgrade:** Copernicus GLO-30 / NASADEM / AW3D30 (30 m, GEE) for slope/TWI/HAND;
  true 12.5 m ALOS RTC from ASF.
- **Vegetation / where InSAR is trustworthy:** ESA WorldCover (10 m), Dynamic World,
  Sentinel-2 NDVI time series.
- **Optical change / independent validation:** Sentinel-2, Landsat, Planet NICFI
  (free, tropics) → detect fresh scarps/scars; corroborate InSAR-flagged zones.
- **Inventory + large-area susceptibility:** NASA Global Landslide Catalog + GEE imagery
  → susceptibility over the whole NH-44 corridor, then focus InSAR where high.
- **Other free services:** GACOS (tropo correction), COMET-LiCSAR (free pre-made
  Sentinel-1 interferograms — independent cross-check), OpenTopography (LiDAR/high-res
  DEM), GSI Bhukosh (Indian geology + landslide data).

### Area 6 — Operationalize / deploy / smarter
- **Real-time rainfall ingestion** (CHIRPS/GPM) → continuously-updating live alerts.
- **Hybrid LLM agent** ("rules decide, LLM narrates" — low-risk first step).
- **Hosted dashboard** (Streamlit) + a **combined union 3-D dashboard** over the
  multi-track mosaic (today's 3-D view is the single frame106 patch).

### Suggested priority (highest leverage first)
1. **Finish MintPy + ERA5** (Area 1) — also unlocks SVD/DESC for Area 2.
2. **Inverse-velocity time-to-failure** (Area 3) — turns hazard → forecast using
   existing data; biggest scientific + narrative jump for least cost.
3. **Live rainfall (GEE CHIRPS/GPM) + ID thresholds** (Areas 3/5) — real trigger.
4. **GEE corroboration + inventory validation** (Areas 4/5) — multi-sensor robustness.

**Robustness in one line:** corroborate InSAR creep with optical change, real rainfall,
soil moisture, and a validated landslide inventory — never trust a single sensor or a
single physics assumption.

---

## 📄 Path to Publication

*(Added 2026-05-31. An honest assessment of publishability + the route to being
taken seriously by the scientific community. Companion to the Expansion Roadmap above.)*

**Current status (be honest about which bar you're aiming at):** a strong,
reproducible **engineering MVP** with a replicable, AOI-portable architecture — **NOT
yet a validated scientific result**. The architecture of the vision is captured; the
data quality (atmosphere), physics calibration, and — above all — *validation* are not.

**What peer reviewers in InSAR / geohazards will check (the bar):**
1. **Validation against independent ground truth** — the #1 gate. A hazard map with no
   check against reality (landslide inventory, GNSS, field reports, optical change, or
   a documented failure event) reads as an unvalidated demo.
2. **Atmospheric correction applied** (ERA5 / GACOS) — the ~30 mm/yr floor *without*
   APS is a near-automatic reviewer flag. (= MintPy step 3.)
3. **Uncertainty / error quantification** — velocity precision, detection limit,
   propagated into the hazard.
4. **Comparison to an established method** — MintPy-vs-custom cross-validation (started).
5. **Justified / sensitivity-tested physics** — the soil parameters can't be arbitrary.
6. **Honest scope** — overclaiming gets rejected; precise modest claims earn respect.
   *Today we clear #4 (partly) + the honesty bar; NOT yet #1–#3, #5.*

**Publication ladder (match the claim to the evidence):**
- **NOW (most realistic):** a **software / reproducibility paper** — **JOSS** (reviews
  the *software*: works, documented, tested, reproducible) or a technical note. Docker
  + open data + open code + tests are a strong fit.
- **AFTER validation + ERA5 + a 2nd AOI:** an applied journal — **Remote Sensing
  (MDPI)**, **Natural Hazards**, **GMD** (model description), or **Landslides**
  (top-tier, hardest).
- **AVOID** claiming "operational forecasting" — the evidence won't support it.

**How to ensure it's taken seriously (highest leverage first):**
1. **Add validation** (even modest: back-test flagged zones vs documented Ramban/NH-44
   failures; corroborate creep vs Sentinel-2 optical change via GEE; compare to the
   NASA Global Landslide Catalog). The single biggest credibility lever.
2. **Finish MintPy + ERA5** and report the cross-validation — removes the two biggest
   reviewer flags at once.
3. **Quantify uncertainty.**
4. **Sensitivity-test the soil parameters.**
5. **Reproducibility as a headline** — public GitHub, a tagged release + **Zenodo DOI**,
   the Docker image, "reproduce in N commands." Aligns with open-science values.
6. **Get a domain co-author / mentor** (InSAR or geohazards researcher — e.g. an IIT,
   WIHG Dehradun, NRSC/ISRO, a university group). Highest-leverage move for a beginner;
   bring them the reproducible repo as your calling card.
7. **Ground in the literature** — Berardino et al. (SBAS, 2002), Ferretti (PS), Yunjun
   et al. (MintPy, 2019), Guzzetti et al. (rainfall ID thresholds), Fukuzono / Voight
   (inverse-velocity time-to-failure), the Joshimath InSAR studies.
8. **Preprint first** (EGUsphere / ESS Open Archive) for community feedback.

**Recommended two-step strategy:** (1) a near-term **JOSS / methods + reproducibility**
paper on the open, containerized, AOI-portable pipeline (achievable with what exists +
tests/docs polish + a 2nd-AOI run); then (2) after MintPy+ERA5 + validation, an applied
**case-study** paper. Keep the honest *"reproducible screening tool, not an operational
forecast"* framing. **Start seeking a co-author now.**

**On being a beginner:** the community judges the *work*, not credentials — beginners
publish when the work meets the bar. The honest-limitations discipline already in
`milestone.md` and the Foundations primer is exactly the scientific maturity reviewers
respect; keep it.

---

## The Guiding Principle

By auditing noise *before* trusting any deformation map, this pipeline avoids the
"garbage in, garbage out" failure that plagues remote-sensing hazard work. Each
phase produces a verifiable artifact the next relies on — and **the full chain now
runs end to end**: Phase 1 → clean interferograms; Phase 2 → trustworthy velocity;
Phase 3 → a physics-based hazard map; Phase 4 → an autonomous, explainable warning
with an interactive 3-D face.

---
# **References**
- Joshimath InSAR case study — `Research/Joshimath InSAR.pdf`
- Meteorological framing — `Research/Meteorology.md`, `Research/Data Sources Meteo.md`
- Extreme weather 2025 — `Research/Extreme Weather events - Himalayas 2025.md`

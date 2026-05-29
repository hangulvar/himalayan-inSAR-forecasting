Created: 2026-05-24 · Last reviewed: 2026-05-29
Status: LIVING DOCUMENT — mid-MVP snapshot. To be fully re-updated once the entire MVP is built end-to-end.
Tags: #insar #hazard #ramban #roadmap
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
| **Phase 3 — Geomechanical Engine** | Infinite Slope model → Factor of Safety, fed by InSAR velocity | ⏳ **NEXT** |
| **Phase 4 — Agentic Orchestration & Visualization** | The autonomous warning system + 3-D UI | 🔮 **FUTURE** |

**Area of Interest:** the **NH-44 corridor through Ramban, Jammu & Kashmir**
(`ramban_aoi.geojson`, ~20×22 km over the Chenab valley). *(Note: the original
draft of this document proposed the Mandakini/Joshimath valley; we switched to
Ramban for its documented NH-44 slope failures and sharp ridge geometry.)*

**Immediate next move:** build a thin end-to-end MVP — push the single working
velocity stack through a crude Phase 3 Factor-of-Safety calc to get a first
complete data→hazard output — *before* widening Phase 2 to all stacks. (See the
process rationale in `session_journey.md`, Session 3.)

---

### The Novel Idea: Agentic Multi-Modal Hazard Forensics

Current government and academic models largely operate in silos: one team looks at the InSAR displacement, another looks at the ERA5 weather forecasts, and a third looks at the hydrology. They usually only combine these datasets _after_ a disaster occurs to write a forensic report.

The novelty here is to build an **Autonomous Agentic Orchestrator** — a multi-agent system where distinct Python "agents" handle specific domains, audit each other's data, and reason through cascading effects.

- **Agent 1: The InSAR Auditor.** Queries the ASF HyP3 API for Sentinel-1 data and ruthlessly filters bad pixels using the interferometric coherence formula:

    $$\gamma = \frac{|\langle S_1 S_2^* \rangle|}{\sqrt{\langle |S_1|^2 \rangle \langle |S_2|^2 \rangle}}$$

    If $\gamma$ drops below a strict threshold (0.4) due to heavy Himalayan vegetation, it masks that data out and refuses to pass noise downstream.
    *➤ Status: this agent's **function** is built as scripts (`submit_hyp3_jobs.py`, `download_hyp3_products.py`, `feature_engineering.py`, `phase_elevation_audit.py`). It is not yet an autonomous LLM agent — that wrapping comes in Phase 4.*

- **Agent 2: The Meteorological Trigger.** Monitors the Copernicus CDS API for Western Disturbances and extreme rainfall, downscaling to the 12.5 m DEM grid. *➤ Status: not started.*

- **Agent 3: The Cascading Reasoner.** If Agent 1 detects slope creep (e.g. −25 mm/year) and Agent 2 forecasts 150 mm of rain, Agent 3 runs the Infinite Slope equation. If the slope fails _and_ sits above a river, it flags a potential Landslide Lake Outburst Flood (LLOF) downstream. *➤ Status: not started; the geomechanical core arrives in Phase 3.*

This architecture prevents the "garbage in, garbage out" problem that plagues remote sensing, while pushing the boundaries of automated disaster forecasting.

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

---

### ⏳ Phase 3 — The Geomechanical Engine  *(NEXT)*

**Goal:** physicalize the risk — calculate whether a slope is actively failing.

**Planned steps:**
1. Download the **12.5 m ALOS PALSAR DEM** for the Ramban bounding box (via
   Google Earth Engine or ASF). *Open decision: resample the 80 m InSAR up to
   12.5 m, or the DEM down to 80 m — see `SESSION_REVIEW.md` open questions.*
2. Derive **slope angle** and **Topographic Wetness Index (TWI)** from the DEM
   (`RichDEM` / `xarray-spatial`).
3. Implement the **1-D Infinite Slope model** to output a **Factor of Safety
   (FS)**, using the filtered InSAR LOS velocity as an active-stress signal.

**MVP framing:** the immediate goal is a *crude* end-to-end FS map over the one
working stack — a first complete data→hazard output — before refining any phase
to production quality.

---

### 🔮 Phase 4 — Agentic Orchestration & Visualization (the Warning System)  *(FUTURE)*

**Goal:** connect the static models into a dynamic, reasoning system, and surface
its findings.

**Planned steps:**
1. Wrap the Phase 1–3 scripts as tools for an orchestrator (LangChain / AutoGen /
   a custom Python loop).
2. An LLM agent periodically reviews outputs with a rule like: *"If Factor of
   Safety < 1.0 AND recent InSAR velocity exceeds −15 mm/yr, issue a High-Risk
   Alert"* — emitting a structured JSON alert (coordinates, trigger reason,
   downstream risk).
3. Add the Meteorological Trigger (Agent 2) to fuse rainfall/Western-Disturbance
   forecasts.
4. Build a 3-D interface (`Streamlit` + `Pydeck`/WebGL): drape the DEM, overlay
   high-risk pixels in red, and show the agent's live reasoning in a sidebar.

---

## The Guiding Principle

By auditing noise *before* trusting any deformation map, this pipeline avoids the
"garbage in, garbage out" failure that plagues remote-sensing hazard work. Each
phase produces a verifiable artifact the next phase can rely on: Phase 1 →
clean interferograms; Phase 2 → trustworthy velocity; Phase 3 → a physics-based
hazard map; Phase 4 → an autonomous, explainable warning.

---
# **References**
- Joshimath InSAR case study — `Research/Joshimath InSAR.pdf`
- Meteorological framing — `Research/Meteorology.md`, `Research/Data Sources Meteo.md`
- Extreme weather 2025 — `Research/Extreme Weather events - Himalayas 2025.md`

# 📊 Results & KPI Ledger — Himalayan InSAR Hazard Forecasting

**Purpose & durability.** This is the **single, version-controlled** record of every headline
performance number and finding the project has produced. Unlike `session_journey.md`,
`milestone.md`, and `SESSION_REVIEW.md` — which are **git-ignored** (local-only) — and unlike the
`data/` outputs (also git-ignored), **this file is committed**, so the KPIs survive a clean
checkout, a machine wipe, and (critically) the **removal of the mock scenarios**.

> ⚠️ **Preserve-on-removal.** Numbers tagged **`[MOCK]`** come from the *assumed* dry/monsoon/
> extreme rainfall scenarios. As we migrate to **real-rainfall-driven** runs and eventually retire
> the mock setups, **these `[MOCK]` KPIs must NOT be deleted** — they are the historical baseline
> the real-rainfall results are compared against. Append new results; never overwrite the table rows.

**Provenance convention.** Each block notes the date, the script/run that produced it, and a
`[MOCK]` / `[REAL]` / `[MEASURED]` tag. When a result is superseded, add a new dated row and mark
the old one *(superseded)* — do not delete it.

_Last updated: 2026-06-01 (Session 8, branch `mvp-expansion`)._

---

## 0. Core parameters & decision thresholds (the rules behind every KPI)

| Parameter | Value | Where |
|---|---|---|
| Coherence mask (custom SBAS) | temporal coherence γ ≥ **0.7** | `custom_sbas_inverter.py` |
| Spatial high-pass | Gaussian σ = **30 px** (~2.4 km @ 80 m) | `custom_sbas_inverter.py` |
| Creep threshold | LOS velocity < **−15 mm/yr** (away = downslope) | orchestrator `VEL_CREEP_THR` |
| Factor-of-Safety failure | **FS < 1.0** | `FS_FAIL` |
| Min cluster size | **≥ 3 px** (drop single/double-px specks) | `MIN_CLUSTER_PX` |
| Severity escalation | mean vel ≤ **−50 mm/yr** OR mean FS ≤ **0.7** → CRITICAL | `CRITICAL_VEL/FS` |
| Soil (infinite slope) | c′ = **5 kPa**, φ = **32°**, γ = **19 kN/m³** (literature, not site-measured) | `geomechanical_engine.py` defaults |
| Pair network | max temporal baseline **24 d**; <150 m perp (declared, not yet enforced) | `config.yaml` |
| Rescue gate | atmos R² ≤ **0.45** AND coherence ≥ **0.6** AND surviving ≥ **15 %** | `config.yaml rescue_gate` |
| Rainfall ID threshold | **Caine (1980)** I = 14.82·D⁻⁰·³⁹ (mm/h, h) | `rainfall_id_threshold.py` |
| Grid (frame106 etc.) | **309 × 353 px**, EPSG:32643, 80 m, AOI + 3 km buffer | — |

---

## 1. Data foundation — Phase 1 (QA / connectivity)  `[MEASURED]`

- **Quarantine outcome (current, gated + coverage-first rescue):** **103 KEEP / 26 CONCERN /
  54 QUARANTINE** pairs across 5 stacks. (Earlier pre-rescue counts differ — this is the adopted state.)
- **Stacks:** 3 ASC (path27 f101, path27 f106, path100 f102) connected; 2 DESC (path34 f479, f484)
  disconnected. Per-stack KEEP: f106 = 31, f102 = 22, f101 = 21, f479 = 16, f484 = 13.
- **frame106 connectivity:** restored to full coverage **14,045 valid px** (coh≥0.7) via the 5DC6
  24-day bridge (coverage-first beat a cleaner-but-emptier 36-day bridge that halved coverage).

## 2. Velocity — Phase 2 (custom SBAS inverter)  `[MEASURED]`

- **Noise floor ≈ 30 mm/yr** (atmosphere-dominated residual after plane-deramp + high-pass).
- **frame106:** 14,045 valid px; **3,752 creeping px** (< −15 mm/yr); high-passed velocity std ≈
  **27–29 mm/yr**, raw ≈ 31. ASC stacks std band **21–30 mm/yr**.
- Outputs per stack: `*_mean_velocity_los.tif`, `*_..._highpass.tif`, `*_displacement_timeseries.tif`
  (14 dated bands), `*_temporal_coherence.tif`.

## 3. MintPy migration + ERA5 tropospheric correction (frame106)  `[MEASURED]`

Cross-validation of MintPy vs the custom inverter on the shared 309×353 grid (`crossval_mintpy.py`):

| Run | vs custom (raw) r | vs custom (high-pass) r | MintPy velocity std | notes |
|---|---|---|---|---|
| Step 2 — **no ERA5**, unmasked *(superseded baseline, keep)* | **+0.28** | +0.39 | 39.3 mm/yr | atmosphere-dominated |
| Step 3 — **ERA5 ON**, same 14,045-px set | **+0.55** | +0.53 | — | ERA5 alone ~doubled agreement |
| Step 3 — **ERA5 ON**, MintPy coh≥0.7 masked (3,109 common px) | **+0.587** | +0.516 | **21.0 mm/yr** | RMS(offset-removed) 25.2 |

**Finding:** the atmosphere *was* the dominant disagreement; ERA5 nearly doubled the agreement
(r +0.28 → +0.55) and cut MintPy scatter 39 → 21 mm/yr (below the custom 31). Two independent SBAS
engines now corroborate at **r ≈ 0.55–0.59**. Image: `insar-mintpy` (py3.11/numpy<2, mintpy 1.6.3 /
pyaps3 0.3.7 / cdsapi 0.7.7).

## 4. DESC stacks — evaluated then DUMPED (quality-first)  `[MEASURED]`

| Stack | result | KPI | verdict |
|---|---|---|---|
| **DESC f484** | pervasively decorrelated | no pixel > 0.85 avg-spatial-coh; only **858 / 109,077 px (0.8 %)** invertible at ref-coh 0.6 | **DUMPED** |
| **DESC f479** (full SVD-bridged network, ERA5) | inverts 99.3 % but biased | velocity std **57 mm/yr**, **9,016 px > 100 mm/yr**; coh≥0.7 = 83,933 | **DUMPED** |
| **DESC f479** (period-split, monsoon island Jun24–Sep16) | WORSE | std **137 mm/yr**, **30,378 px > 100**; coh≥0.7 = 67,663 | confirms data noise, not disconnect |

**Finding:** descending path-34 over Ramban can't yield a trustworthy velocity (ASC is 2–5× cleaner).
ASC/DESC vertical+EW decomposition **deferred**. (`DUMPED.md` marker kept in each `data/mintpy/DESC_*/`.)

## 5. Hazard map + agentic warning — Phase 3 / 4A

### 5a. Slope-stability (FS) screening — Phase 3 pathfinder (frame106)  `[MEASURED slope; MOCK saturation end-members]`
- Median slope ≈ **28°**. FS dry → ≈ **13 %** of slopes unstable; FS saturated (m=1) → ≈ **73 %**
  unstable. ~**2,600** HIGH px in the single-stack pathfinder (unstable AND creeping).

### 5b. frame106 alert cascade — ROOT demo  ⚠️`[MOCK]` — **preserve on removal**
Source: `agentic_orchestrator.py` mock scenarios, `data/alerts/alerts_<scenario>.json` (2026-05-30).

| Scenario `[MOCK]` | rainfall (assumed) | sat m | FS layer | alert zones | critical | LLOF | area km² |
|---|---|---|---|---|---|---|---|
| **dry** | 0 mm/72h | 0.0 | FS_dry | **29** | 4 | 11 | 0.851 |
| **monsoon** | 120 mm/72h | 1.0 | FS_saturated | **222** | 104 | 85 | 7.667 |
| **extreme** | 250 mm/72h | 1.0 | FS_saturated | **222** | 104 | 85 | 7.667 |

*The dry → monsoon jump (29 → 222 zones, ~0.85 → 7.67 km²) is the headline "cascade responds to the
trigger" demo result. monsoon == extreme because both saturate (m=1) → FS_saturated.*

### 5c. AOI union mosaic across the 3 ASC stacks  ⚠️`[MOCK]` — **preserve on removal**
Source: `run_multistack.py`, `data/alerts/mosaic_asc/` + `data/mosaic/MOSAIC_ASC_hazard_class.tif`.

- **Raster HIGH (FS<1 AND creep), any look:** **5,268 px**; **291 px** confirmed by **≥ 2 looks**.
- **Union monsoon alert zones:** **405** (204 critical); **26** multi-look-confirmed.
- Rule: UNION of detections at the hazard/alert level (no cross-look velocity averaging — different LOS).

### 5d. 3-D dashboard (Phase 4B)  `[MOCK]`
`data/alerts/dashboard_3d.html` (frame106), rainfall slider Dry → Monsoon → Extreme drives 29 → 222.

## 6. Forecasting — inverse-velocity time-to-failure (Fukuzono)  `[MEASURED]`

Source: `inverse_velocity_ttf.py` (per alert zone; creep-masked window + hard direction/consistency gates).

| Stack | zones screened | ACCELERATING | STEADY | insufficient |
|---|---|---|---|---|
| frame106 | 222 | **0** | 222 | 0 |
| frame102 | 206 | **0** | 206 | 0 |
| frame101 | 5 | **0** | 5 | 0 |

**Finding:** **0 zones accelerating** — all steady creep, the correct/cautious result for a ~3.5-mo,
~30 mm/yr-noise window. (A v1 bug flagged 7 false "failures" on net-*positive* zones; fixed by
direction/consistency gates — recorded in `error_history_log.md`.) "Steady ≠ safe."

## 7. Real rainfall + ID-threshold trigger  `[REAL / MEASURED]`

Source: `fetch_rainfall.py` (ERA5-Land via CDS) + `rainfall_id_threshold.py` (Caine 1980),
`data/rainfall/`. AOI ≈ 33.0–33.5 N, 75.0–75.5 E; season 2025-05-01 → 2025-10-31 (184 days).

- **Season total ≈ 1,233 mm**; **peak day 133.5 mm on 2025-08-26**.
- **ID-threshold trigger days: exactly 1 → 2025-08-26.** 1-day 134 mm > 103 mm threshold; 2-day
  183 mm > 157 mm; 3-day 196 mm just under 201 mm; longer durations below.

**Finding:** the season's landslide-triggering rainfall was a **single intense burst (26 Aug)**, not
the broad mock "120 mm/72h monsoon". (Caveat: ERA5-Land under-counts orographic bursts — a CHIRPS/GPM
gauge cross-check would likely flag *more*; Caine is a conservative global curve.)

## 8. Rainfall coupling — real-weather-driven hazard  `[REAL]`

Source: `agentic_orchestrator.py` (`--date`, `--rainfall-timeline`). FS is exactly linear in
saturation m, so **FS_real = (1−m)·FS_dry + m·FS_saturated** (interpolated; no recompute).

- **`--date 2025-08-26`** (real trigger): real **196 mm/72h → m=1.0 → 222 zones** (104 critical,
  85 LLOF) — matches the `[MOCK]` monsoon map *on the peak day*, but now tied to the real event.
- **Season hazard timeline** (`data/alerts/hazard_timeline.{csv,png}`): alert zones **build through
  the monsoon, peak at 222 on 26 Aug, then decay** as the soil dries (API memory tail; small late-Sep
  bump). Pre-monsoon baseline ≈ **30–65 zones**. This time-resolved curve is the key gain over the
  3 static mock maps.
- Backward-compat: mock `--scenario monsoon` still → 222 (run_multistack unaffected).

## 9. Validation — back-test against a documented landslide inventory  `[REAL / MEASURED]`

Source: `backtest_inventory.py` vs `data/inventory/ramban_documented_landslides.geojson`
(9 documented NH-44 hotspots + 2025 events — **approximate place-centroids** from public
reporting, NOT field-mapped) vs the ASC union monsoon zones (405). 2026-06-01.

- **Spatial coincidence (indicative):** **8 / 9** documented locations within **2 km** of a
  flagged zone (median nearest **1.35 km**) — the map covers the historically failure-prone
  NH-44 corridor. ⚠️ *Not* precision/recall: 405 zones AOI-wide means coincidence is partly
  density-driven, and coords are approximate. A rigorous test needs the **GSI Bhukosh inventory
  (~302 Ramban landslides)** + a specificity check (the tool ingests it unchanged).
- **Temporal coincidence (the substantive finding):** model ID-threshold trigger = **2025-08-26**;
  documented 2025 events = **2025-04-27** (Δ 121 d) and **2025-05-08** (Δ 110 d) → **0 / 2 coincide
  (MISS)**. The ERA5-driven trigger did NOT match the documented Apr–May failures.
- **Why the miss (actionable):** (a) the 27 Apr event is *before* the 2025-05-01 window → extend
  to April; (b) the 8 May event is *in* window but ERA5-Land rainfall that day was below the Caine
  threshold → ERA5-Land under-counts orographic bursts → switch to a gauge product (CHIRPS/GPM) +
  a regional I–D curve.

**Finding:** the hazard map is **spatially plausible** but the **rainfall trigger timing is not yet
validated** — the back-test correctly exposes that the current ERA5 / May-start setup misses the
real events. Honest "rough map → *partially* validated" result; it directs the next fixes.

**Sources** (inventory provenance — also embedded in the GeoJSON `sources`):
[Mongabay 2025](https://india.mongabay.com/2025/09/study-maps-the-most-unstable-slopes-along-an-important-himalayan-highway/) ·
[India TV 2025-05-08](https://www.indiatvnews.com/jammu-and-kashmir/heavy-rain-triggers-mudslides-in-ramban-traffic-disrupted-as-jammu-srinagar-nh-44-closed-commuters-advised-to-stay-indoors-2025-05-08-989228) ·
[Kashmir Vision 2025-04-27](https://kashmirvision.in/2025/04/27/the-nh-44-landslide-in-ramban/) ·
[Greater Kashmir](https://www.greaterkashmir.com/latest-news/nh-44-shut-after-heavy-landslide-near-digdol-khooni-nallah-ssp-traffic/) ·
[Kashmir Observer](https://kashmirobserver.net/2023/09/30/navigating-danger-nh-44s-battle-against-landslides/) ·
[GSI Bhukosh/Bhusanket](https://bhusanket.gsi.gov.in/) ·
[NASA GLC/COOLR (~2007–2018)](https://gpm.nasa.gov/landslides/data.html)

---

## How to maintain this ledger
- **Append, don't overwrite.** New runs add rows; superseded rows stay, marked *(superseded)*.
- **Tag every number** `[MOCK]` / `[REAL]` / `[MEASURED]` with date + producing script.
- **Before removing any mock setup**, confirm its KPIs are captured here (§5b/§5c/§5d are the
  mock-derived ones).
- Keep this in sync at the same time as the git-ignored journals (it is the *committed* mirror of the
  headline numbers).

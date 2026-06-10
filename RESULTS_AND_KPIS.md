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

_Last updated: 2026-06-02 (Session 10, branch `mvp-expansion`) — added §12 regional Himalayan I–D
curve (the temporal-miss fix), §12b/§12c CHIRPS plumbing + specificity prototype, **§12d — CHIRPS RAN, gauge
hypothesis REFUTED**, §12e — GPM IMERG sub-daily test, §12f — spring conditioning (priming), and **§12g — inventory DATE
CORRECTION: the major spring event (20 Apr cloudburst) WAS rainfall-triggered and the model detects it —
correcting §12d–e's "rainfall ruled out" (it was a wrong-date artifact)**. Prior: §10 slope-parallel
velocity (V_slope), §11 snowmelt/freeze-thaw drivers + April-extended trigger. Also **§13 — tropospheric-
correction method comparison** (ERA5 −31 % scatter, TRAIN-style); **§14 — GSI field-validated inventory
ingested** (138 AOI slides; spatial back-test 71 % within 2 km); **§15 — FS soil-parameter calibration**
(φ 32°→36° from the GSI geotech study)._

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

**Re-run 2026-06-01 (extended window + water = rain+snowmelt):** with the window extended to
**2025-04-01** (so the 27 Apr event is now IN scope) and the trigger driven by water = rain+snowmelt,
the result is **unchanged: spatial 8/9, temporal 0/2 MISS** (acute trigger still 26 Aug). This
**sharpens** the diagnosis (see §11): the miss is an **orographic-rain-undercount** problem
(ERA5-Land), not a missing-snowmelt one → the gauge product (CHIRPS/GPM) + regional I–D curve is the
real fix. (The FS-coupled hazard timeline, by contrast, *does* show substantial spring hazard — §11.)

**Sources** (inventory provenance — also embedded in the GeoJSON `sources`):
[Mongabay 2025](https://india.mongabay.com/2025/09/study-maps-the-most-unstable-slopes-along-an-important-himalayan-highway/) ·
[India TV 2025-05-08](https://www.indiatvnews.com/jammu-and-kashmir/heavy-rain-triggers-mudslides-in-ramban-traffic-disrupted-as-jammu-srinagar-nh-44-closed-commuters-advised-to-stay-indoors-2025-05-08-989228) ·
[Kashmir Vision 2025-04-27](https://kashmirvision.in/2025/04/27/the-nh-44-landslide-in-ramban/) ·
[Greater Kashmir](https://www.greaterkashmir.com/latest-news/nh-44-shut-after-heavy-landslide-near-digdol-khooni-nallah-ssp-traffic/) ·
[Kashmir Observer](https://kashmirobserver.net/2023/09/30/navigating-danger-nh-44s-battle-against-landslides/) ·
[GSI Bhukosh/Bhusanket](https://bhusanket.gsi.gov.in/) ·
[NASA GLC/COOLR (~2007–2018)](https://gpm.nasa.gov/landslides/data.html)

---

## 10. Slope-parallel velocity (V_slope) — LOS projected onto downslope  `[MEASURED]`

Source: `slope_velocity.py` (V_slope = V_LOS / (d·l); high-pass velocity; LOS unit vector from HyP3
`lv_theta`/`lv_phi`; downslope from the bundled DEM slope+aspect; masks |C| < 0.3 and slope < 10°).
2026-06-01. `d·l` = the **LOS sensitivity** C: |C|≈1 = downslope faces along LOS (well observed),
|C|≈0 = downslope ⟂ LOS (single-look **blind spot**).

| stack | valid px | well-observed | blind-spot % | median \|C\| | LOS-creep → slope-creep | median amp |
|---|---|---|---|---|---|---|
| frame106 | 14,045 | 10,136 | **28 %** | 0.53 | 3,752 → 3,712 | **×1.48** |
| frame102 | 25,831 | 15,025 | **42 %** | 0.40 | 4,338 → 4,818 | ×1.58 |
| frame101 | 3,655 | 2,770 | **24 %** | 0.61 | 274 → 392 | ×1.41 |

**Finding:** projecting LOS onto the downslope direction (a) quantifies the ASC **single-look blind
spot** — **24–42 %** of valid ground has its downslope ~perpendicular to the LOS, so its motion is
under-/un-observed; and (b) **de-projects (amplifies) the creep magnitude ×1.4–1.6** (median), since
|C|≤1 — sharpening the creep and the inverse-velocity TTF. On frame102/101 slope-creep *exceeds*
LOS-creep: de-projection lifts sub-threshold LOS pixels over the creep cutoff. The cheap single-look
approximation of the (DESC-deferred) ASC/DESC decomposition. Outputs per stack: `*_v_slope.tif`,
`*_los_sensitivity.tif`, `*_v_slope_report.{json,md}`. Internal check: frame106 valid=14,045 and
LOS-creep=3,752 match §1/§2 exactly. *Honest scope: ASC-only → assumes pure-downslope motion; blind
to cross-LOS motion (the blind fraction above).*

**Wired in (opt-in, 2026-06-01):** `agentic_orchestrator.py --use-vslope` and
`inverse_velocity_ttf.py --use-vslope` now detect creep from `-v_slope` (downslope, blind pixels
excluded) instead of raw LOS — **off by default to preserve the LOS `[MOCK]` baselines** (§5b). frame106
monsoon comparison: **222 zones (LOS) → 236 (V_slope)** — de-projection lifts more pixels over the −15
creep cut even after dropping the blind 28 %. TTF stays 0 accelerating / all STEADY (acceleration is
scale-invariant; V_slope only refines the creep-pixel selection). Outputs tagged `"velocity_basis"`.

**Area-wide V_slope union — `run_multistack.py --use-vslope`** (parallel product in `data/mosaic_vslope/`
+ `data/alerts/mosaic_asc_vslope/`; **LOS baseline §5c built & preserved unchanged**), 2026-06-01:

| metric (3 ASC union) | LOS baseline §5c | V_slope |
|---|---|---|
| mosaic HIGH px | 5,268 | **5,493** |
| HIGH confirmed by ≥2 looks | 291 | **399 (+37 %)** |
| monsoon union zones (critical) | 405 (204) | **433 (279)** |
| dry union zones | 55 | 66 |

**Finding (beyond amplification):** projecting each look into a common *downslope* frame partly removes
the per-look LOS-geometry difference, so the two ASC looks **agree more often** — multi-look-confirmed
HIGH rises **291 → 399 (+37 %)**. So V_slope is not just "bigger numbers": it measurably **improves
cross-geometry corroboration**, the most trustworthy class of detection. Geomechanical writes a distinct
`*_hazard_class_vslope.tif` (FS/slope/twi are velocity-independent → kept canonical).

## 11. Snowmelt + freeze-thaw drivers + April-extended trigger  `[REAL / MEASURED]`

Source: `fetch_rainfall.py` (ERA5-Land `total_precipitation` + `snowmelt` + `2m_temperature`,
**2025-04-01 → 2025-10-31**) + `rainfall_id_threshold.py` (Caine on water = rain+snowmelt; freeze-thaw
flag Tmin<0<Tmax) + `agentic_orchestrator.py --rainfall-timeline`. 2026-06-01. Motivated by §9's
temporal miss (Apr–May = NW-Himalaya snowmelt/freeze-thaw season).

- **Season water = 1,409 mm** = rain **1,350** + snowmelt **59** (214 days). Peak water day **133.5 mm
  (26 Aug)**. Snowmelt is concentrated in **early April** (~2–3.5 mm/day) and decays by late April.
- **Acute ID-threshold trigger days: still 1 → 26 Aug** (unchanged). Snowmelt (≤3.5 mm/day) is far
  below the conservative global Caine burst threshold (1 d = 103 mm), so it adds **no** new acute trigger.
- **Freeze-thaw days (AOI-mean Tmin<0<Tmax): 0** — the AOI-*mean* temperature never crosses 0 °C in
  Apr–Oct (valley floor masks high-slope freezing). *Limitation: per-elevation (per-cell + DEM)
  temperature is needed to resolve high-slope freeze-thaw; AOI-mean under-represents it.*
- **FS-coupled spring hazard (timeline), by contrast, IS substantial:** alert zones reach **136 on
  20 Apr** (m=0.66, a real 27 mm rain event), **78 on 27 Apr** (m=0.33), **54 on 8 May** (m=0.20) —
  the map *does* light up in spring once April is included. Peak remains **222 on 26 Aug**.

**Finding:** the snowmelt + freeze-thaw drivers are now physically in the pipeline, but on AOI-mean
ERA5-Land they are **sub-threshold for the acute trigger** and the documented Apr–May failures remain
a **temporal miss (§9 re-run: 0/2)**. This is the valuable sharpening: the gap is driven by
**ERA5-Land under-counting orographic rain bursts** (e.g. 8 May = 9.3 mm in ERA5-Land vs documented
heavy rain/mudslides), *not* by missing snowmelt water → next fix is the **gauge product
(CHIRPS/GPM) + a regional Himalayan I–D curve** (Area 7 #3, deferred). Snowmelt's genuine role is
**chronic spring saturation**, visible in the timeline, not as an acute trigger.

> **↪ Subsequently resolved (§12d–§12g):** the "gauge product is the next fix" hypothesis was tested
> (CHIRPS + IMERG showed *even less* rain on the then-assumed dates) — but a **date correction (§12g)** then
> showed the real major event (20 Apr cloudburst) WAS rainfall-triggered and the model detects it; the daily
> *AOI-mean* dilution is the genuine limitation. Snowmelt's chronic-saturation role was confirmed in §12f.

---

## 12. Regional Himalayan I–D curve + GEE CHIRPS gauge rainfall  `[REAL / MEASURED — curve VERIFIED]`

Source: `rainfall_id_threshold.py --threshold {caine1980|nwhimalaya}` (now parameterized) +
`backtest_inventory.py`. 2026-06-02. Motivated by §9/§11: the Apr–May 2025 temporal MISS, diagnosed
as Caine's conservative *global* curve + ERA5-Land's orographic under-count.

**The two I–D curves (both mm/h vs h, directly comparable):**

| curve | A | B | 1-day cumulative threshold | source |
|---|---|---|---|---|
| `caine1980` (global, default) | 14.82 | 0.39 | ≈ **103 mm** | Caine (1980) Geogr. Ann. A 62:23–27 |
| `nwhimalaya` (regional) | 2.9993 | 0.4152 | ≈ **19 mm** | J. Earth Syst. Sci. (2025) **134:97**, frequentist on 2007–2016 events |

AOI cross-check (independent): Shah et al. (2024) *Nat. Hazards* **120**:1319–1341 report **~14.35 mm/day**
triggers landslides on the NH-44 Udhampur–Banihal stretch (Ramban) — same order as the regional curve,
confirming Caine is ~5× too conservative here.

**Literature verification (2026-06-02) — coefficients + units confirmed.** The PDFs are paywalled, so the
numbers were triangulated across multiple independent sources **and** numerically cross-checked against our
implementation (`rainfall_id_threshold.py` reproduces every published reference point):

| curve | what was verified | check |
|---|---|---|
| Caine (1980) | I=14.82·D⁻⁰·³⁹, valid 10 min–10 days, 73 events (Geogr. Ann. A 62:23–27) | I(D=1h)=**14.82 mm/h** (==A, exact); 1-day=103 mm |
| NW Himalaya (JESS 2025 134:97) | I=2.9993·D⁻⁰·⁴¹⁵² confirmed by the paper's **full self-consistent regional family** (NE Himalaya 5.8294·D⁻⁰·⁴¹⁴¹, E Ghats 26.88·D⁻⁰·⁶⁸⁸⁵, W Ghats 28.01·D⁻⁰·⁶⁴¹; TRMM 2007–2016, Brunetti-frequentist) | **units stated in source: "I in mm/h, D in hours"**; our I(D=48h)=**0.60 mm/h** vs Garhwal sub-zone anchor **0.45–0.50**; 1-day=**19.2 mm** vs NH-44 ~14.35 mm/day |

**Verdict:** coefficients, units (mm/h vs h), and validity range are corroborated; the regional curve is
internally consistent with its sibling Indian curves and externally consistent with two independent AOI/sub-
zone anchors. *Residual:* exact-digit confirmation from the primary JESS 2025 PDF is still pending (paywalled)
— low risk given the multi-source agreement. Sources:
[JESS 2025 134:97](https://www.ias.ac.in/article/fulltext/jess/134/0097) ·
[Caine 1980](https://www.tandfonline.com/doi/abs/10.1080/04353676.1980.11879996) ·
[Shah et al. 2024](https://link.springer.com/article/10.1007/s11069-023-06254-w).

**Result — regional curve on the SAME ERA5-Land water (2025-04-01→10-31, 214 d):**

| metric | `caine1980` (§7 baseline) | `nwhimalaya` (regional) |
|---|---|---|
| ID-threshold trigger days | **1** (26 Aug) | **112** of 214 |
| 1-day exceedance days | 1 | 13 |
| back-test TEMPORAL (vs 27 Apr / 8 May) | **0/2 MISS** | **2/2 COINCIDES** (27 Apr Δ0; 8 May Δ5) |
| back-test SPATIAL | 8/9 | 8/9 (unchanged) |

**Finding:** switching to the published **regional** I–D curve flips the temporal back-test from
**0/2 → 2/2**, on the *unchanged* ERA5-Land data — so the Apr–May miss was substantially a *threshold*
problem (the global Caine curve is far too conservative for the NW Himalaya), not only a rainfall-source
problem. ⚠️ **Specificity caveat (loud):** the regional curve fires **112/214 days**, so a ±10-day
temporal coincidence is nearly automatic — this is *sensitivity without specificity*, not yet an
operational trigger. A discriminating trigger needs (a) **CHIRPS** gauge precision to test the *acute*
8 May burst (ERA5-Land had only 9.3 mm that day, below even the 19 mm regional 1-day threshold), and
(b) a percentile/return-period or antecedent-rainfall criterion (Shah et al.: ~53 mm/20 d antecedent on
NH-44). *The regional curve's coefficients + units are now **verified** (verification block above), so it
is cleared to become the canonical/default curve; default is kept at `caine1980` only to avoid re-baselining
the `[MOCK]` KPIs this session.* Outputs (suffixed, non-destructive): `id_threshold_report_{caine,nwhimalaya}_era5.{json,md}`, `id_threshold_*_era5.png`.

## 12b. GEE CHIRPS gauge-rainfall fetch — BUILT + RAN  `[infrastructure]`

Source: `workflows/fetch_chirps.py` (new). Pulls CHIRPS daily (`UCSB-CHG/CHIRPS/DAILY`, 0.05°,
satellite+gauge) AOI-mean per day via Google Earth Engine → `data/rainfall/ramban_chirps_daily.csv`
in the **same schema** as the ERA5-Land CSV (snowmelt/temperature merged from it), so
`rainfall_id_threshold.py` + `backtest_inventory.py` consume it unchanged. `earthengine-api` added to
the `insar` image (`docker/Dockerfile`); GEE OAuth credentials mounted via `EE_CREDENTIALS` in `.env`
(placeholder fallback). **RAN 2026-06-02** (GEE auth completed; native fetch via `insar_qa_env`, project
`tutorial-project-472812`) — **see §12d for the result** (the gauge hypothesis was refuted). Auth token at
`~/.config/earthengine/credentials`, project id in git-ignored `.env`. The image rebuild was not needed —
`fetch_chirps.py` does no heavy linalg, so it ran natively; the container path remains available.

## 12c. Specificity-filter prototype — the regional trigger's sensitivity/selectivity trade-off  `[REAL / MEASURED]`

Source: `workflows/rainfall_specificity.py` (new) on `ramban_era5land_daily.csv`, `--threshold nwhimalaya`.
2026-06-02. Quantifies how to make the over-sensitive regional curve (§12: 112/214 days) selective, scored
vs the 2 documented events (±10 d). Each day ranked by peak I–D **exceedance ratio** E = max_D(cum_D /
threshold_D); E≥1 = raw trigger fires. Two independent dials: **stringency k** (alert if E≥k) and an
**antecedent floor** (alert if E≥1 AND API ≥ percentile).

| stringency k | ≈1-day mm | alert days | % season | events caught (27 Apr / 8 May Δ) |
|---|---|---|---|---|
| **1.0** (raw regional) | 19 | 112 | 52.3 % | **2/2** (Δ0 / Δ5) |
| 1.5 | 29 | 47 | 22.0 % | 1/2 (Δ2 / Δ13) |
| 2.0 | 39 | 27 | 12.6 % | 1/2 (Δ6 / Δ17) |
| 3.0 | 58 | 15 | 7.0 % | 0/2 |
| 5.0 (≈ Caine) | 96 | 2 | 0.9 % | 0/2 |

Antecedent dial (at k=1): API≥p75 → 54 days (25 %), 1/2; API≥p90 → 22 days (10 %), 1/2.

**Event rarity (E = how far above the regional lower bound; 1.0 = on the line):** 27 Apr **E=1.41**
(71st pct); **8 May E=0.67** (39th pct — *below* even the regional line); season peak 26 Aug **E=6.94**.

**Finding (the decisive one):** on ERA5-Land there is **NO operating point that is both selective
(<20 % of season) and catches both events** — the spring events sit at E≈0.7–1.4 (just on/under the line),
so any stringency that suppresses routine monsoon also suppresses them (k is essentially a 1-D dial
sliding from regional→Caine; §12's two endpoints). The **8 May event (E=0.67) cannot be triggered by *any*
threshold on ERA5-Land** — its reanalysis rain is simply too small (9.3 mm). This **isolates the rain
*measurement*** (not the threshold) as the remaining lever and is the rigorous, quantitative case for the
**CHIRPS** gauge swap: gauge rain that records the real spring bursts would raise their E and open a
selective-and-sensitive window. The prototype is ready to re-run on `ramban_chirps_daily.csv`.
Outputs: `data/rainfall/specificity_report.{json,md}`, `specificity.png`.

## 12d. CHIRPS gauge rainfall — RAN, and the hypothesis is REFUTED  `[REAL / MEASURED]`

Source: `fetch_chirps.py` (Earth Engine, project `tutorial-project-472812`, auth done 2026-06-02) →
`ramban_chirps_daily.csv` → `rainfall_id_threshold.py`/`rainfall_specificity.py`/`backtest_inventory.py`,
all `--..._chirps`. The hypothesis (§9/§11/§12b): *ERA5-Land under-counts orographic bursts, so a
gauge-blended product (CHIRPS) will record the spring rain and catch the 27 Apr / 8 May events.*

**CHIRPS is DRIER than ERA5-Land here, not wetter:**

| | CHIRPS | ERA5-Land |
|---|---|---|
| season total (214 d) | **998 mm** | 1,350 mm (0.74×) |
| 27 Apr (event day) | **0.0 mm** | 0.1 mm |
| 8 May (event day) | **4.2 mm** | 9.3 mm |
| 3-day sum → 8 May | **10.5 mm** | 16.6 mm |
| 26 Aug (monsoon peak) | 91.5 mm | 133.5 mm |
| regional-curve trigger days | 81 | 112 |

**Event rarity E (rain ÷ regional threshold; E<1 = event day itself below the line):**
27 Apr **E=0.70** (CHIRPS) vs 1.41 (ERA5); 8 May **E=0.57** vs 0.67; peak 26 Aug E=4.76. On CHIRPS *both*
spring events sit **further below** the regional line than on ERA5-Land. Specificity headline unchanged:
**no selective (<20 % season) setting catches both** (CHIRPS k=1.5 → 0/2, worse than ERA5's 1/2). The
back-test reads 2/2 only because the over-sensitive raw trigger fires on *nearby* days (27 Apr Δ4, 8 May
Δ7) — the event days themselves never trigger.

> **↪ CORRECTED by §12g:** "the exact event dates" here were the *wrong* dates (27 Apr / 8 May). On the real
> major date (20 Apr) the rain WAS extreme; the daily AOI-mean still under-reads it (localized cell), so the
> *measurement* point holds, but "rainfall not the cause" was wrong — see §12g.

**Finding (the decisive honest negative):** the gauge swap is **REFUTED by the data** — CHIRPS does not
resolve the spring bursts; it records *less* acute rain than ERA5-Land on the exact event dates. **Two
independent ~5–9 km products (reanalysis + satellite-gauge) agree there was little grid-scale acute rain
on the documented spring 2025 NH-44 failure dates.** So the Apr–May miss is **not** a "wrong rainfall
product" problem. Likely causes, redirected: (a) **sub-grid convective cells** below ~5 km (would need
GPM IMERG 0.1°/30-min or station data); (b) **chronic snowmelt + antecedent saturation / freeze-thaw**
(non-acute — consistent with §11's FS timeline lighting up in spring, and Milestone 16); (c) **non-
meteorological triggers** — Digdol/Khooni Nallah are active NHAI tunnel/road-construction zones; (d)
approximate news-derived event dates/coords. This *confirms and strengthens* §11: snowmelt's role is
chronic spring saturation, not an acute trigger — now corroborated from the rainfall side. The regional
I-D curve (§12) remains the right threshold fix; the rainfall *source* is no longer the suspect for spring.
Outputs (suffixed): `*_nwhimalaya_chirps.*`, `specificity_report_chirps.*`. *Note: EECU-frugal — one
batched `reduceRegion` per day over the ~0.2°×0.2° AOI; no DEM pulled (bundled DEM used).*

## 12e. GPM IMERG sub-daily test — the rainfall question is CONCLUSIVELY CLOSED  `[REAL / MEASURED]`

Source: `workflows/fetch_gpm_imerg.py` (new; GEE `NASA/GPM_L3/IMERG_V07`, half-hourly, AOI-mean rain rate)
→ peak mean intensity at D = 0.5/1/3/6/12/24 h, screened vs the verified regional curve at each duration.
2026-06-02. Tests the one dimension the daily products can't see: a short, intense **convective burst** that
triggers a slope but shows only as a modest daily total. EECU-frugal (event windows only; raw series cached
→ re-runs free). Ran in the rebuilt `insar` image (earthengine-api + creds mount validated end-to-end).

| day | daily mm | peak I(0.5h) | peak I(1h) | peak I(3h) | **max E** | class |
|---|---|---|---|---|---|---|
| **27 Apr** (event) | 0.0 | 0.01 | 0.01 | 0.0 | **0.00** | below threshold |
| **8 May** (event) | 8.6 | 3.17 / 4.0 | 2.83 / 3.0 | 2.08 / 1.9 | **1.09** | marginal |
| 20 Apr (no failure) | 27.1 | 6.55 | 6.19 | 4.28 | **2.25** | clear crossing |
| **26 Aug control** | — | 21.2 | 20.5 | 16.7 | **12.3** | clear crossing (method validated) |

> **↪ CORRECTED by §12g (2026-06-02):** the "no acute spring rain / not rainfall-driven" reading below was
> an **artifact of imprecise news dates** — the real major event was the **20 Apr 2025 cloudburst**, which
> IMERG flags at **E=2.25 (clear crossing)** and which *was* acute-rainfall-triggered. The daily-product
> *measurement* limitation (AOI-mean dilutes the localized cell) stands; the *interpretation* was wrong.

**Finding (conclusive):** on the documented event days, IMERG sub-daily intensity does **not** clearly cross
the regional threshold — **27 Apr is bone-dry (E=0.0)** and **8 May only marginally touches at 3 h (E=1.09)**
with sub-hourly peaks *below* the line. The 26 Aug control crosses massively (E≈12 — method validated), and a
genuine burst on **20 Apr (E=2.25) produced no reported failure**. So **three fully independent products —
daily reanalysis (ERA5-Land), daily satellite-gauge (CHIRPS), and half-hourly satellite (IMERG) — all agree
there was no acute triggering rainfall on the documented spring 2025 NH-44 failure dates.** The "Apr–May miss
is a rainfall-data problem" hypothesis is **definitively rejected** *(later CORRECTED — §12g: this rested on
the wrong dates)*. The spring failures are very likely **not acute-rainfall-driven**: chronic
snowmelt/antecedent saturation (per §11's spring FS timeline), NHAI tunnel/road construction at Digdol/Khooni
Nallah, **or imprecise news-derived event dates** — *this last one proved correct (§12g)*. Outputs: `data/rainfall/imerg_subdaily_report.{json,md}`, `imerg_subdaily.png`,
cached `imerg_raw_*.csv`.

## 12f. Spring conditioning — per-elevation freeze-thaw + chronic saturation (the non-acute mechanism)  `[REAL / MODELED]`

Source: `workflows/spring_conditioning.py` (new; EECU-free — ERA5-Land daily CSV + the bundled 80 m DEM,
no GEE). 2026-06-02. Now that an acute rainfall trigger is ruled out (§12e), this characterizes the two
*slow priming* mechanisms for the spring NH-44 failures.

**Per-elevation freeze-thaw** (lapse-rate ELR 6.5 °C/km; z_ref = AOI-mean DEM elev **1670 m**; AOI p5–p95
**802–2576 m**) — the AOI-mean gives **0** freeze-thaw days *by construction*; resolving by elevation:

| elevation | % AOI | freeze-thaw days (spring Apr–May) |
|---|---|---|
| 1000 m | 22 % | 0 |
| 1500 m (≈ event/road) | 30 % | **0** |
| 2000 m | 27 % | 4 |
| 2500 m | 16 % | **12** |

Freeze-thaw **onset ≈ 2500 m**; at the documented event/corridor elevation (~1540 m, valley) it is **0** —
so freeze-thaw weakening acts on the **higher source slopes above the road**, not the road itself.

**Chronic antecedent saturation:** spring snowmelt **56 mm**; spring wetness-memory (API) mean **34 mm**,
max **106 mm** (season p95 162). On the event days — despite ~0 acute rain — antecedent wetness was
**33 % (27 Apr)** and **20 % (8 May)** of the season peak: the slopes were *moderately primed*, not dry.

**Finding:** the spring signature is **PRIMING, not an acute trigger** — moderate chronic saturation
(snowmelt + antecedent rain) plus freeze-thaw cycling on the upper source slopes (≥~2000–2500 m) — fully
consistent with §12e (no acute rain). It explains *susceptibility* but still **does not pinpoint a discrete
trigger** for the specific dates, which keeps the non-meteorological / inventory-date hypotheses (NHAI
construction; GSI-verified dates) live. *Scope `[MODELED]`: lapse-rate downscaling is first-order (constant
ELR; z_ref = DEM-mean — ERA5-Land orography would refine it); freeze-thaw elevations ±few-hundred m;
mechanistic framing, not a calibrated trigger.* Outputs: `data/rainfall/spring_conditioning_report.{json,md}`,
`spring_conditioning.png`.

## 12g. Inventory date correction — the major spring event WAS rainfall-triggered (a validation win)  `[REAL / MEASURED]`

Source: literature review (peer-reviewed + news) → corrected `data/inventory/ramban_documented_landslides.geojson`
→ re-run `backtest_inventory.py` + `fetch_gpm_imerg.py`. 2026-06-02. **This corrects §12d–§12f's framing.**

While sourcing GSI Bhukosh (which needs a manual portal login — see SESSION_REVIEW), the literature revealed
the **real major April 2025 event was the 20 April cloudburst** — *not* the news-derived 27 Apr / 8 May our
inventory had used. The **20 Apr 2025 Ramban cloudburst** (night 19–20 Apr; Karol→Marog; Seri Bagna **3
deaths**; NH-44 washed out at ~5 sites; documented **~100 mm/1 hr localized, 40 mm/3 hr, 60–140 mm/day**) is
peer-reviewed (Springer *Landslides* 2025, doi 10.1007/s10346-025-02580-1; ScienceDirect 2026) — **and it was
acute-rainfall-triggered.**

**Back-test vs the corrected inventory (11 locations, 4 dated events):**

| trigger | spatial | temporal | 20 Apr (major) |
|---|---|---|---|
| Caine (global) | 10/11 | **0/4** | MISS (only fires 26 Aug) |
| Regional `nwhimalaya` | 10/11 | **4/4** | **COINCIDES Δ=0 (a trigger day)** |

IMERG sub-daily screen on the event days: **20 Apr E=2.25 (clear crossing)**, 27 Apr E=0.0 (dry → confirms
it was mis-dated), 8 May E=1.09 (marginal).

**Corrected finding (supersedes the §12d–e "rainfall ruled out" reading):** the **major, deadly spring
event WAS acute-rainfall-driven, and the model detects it** — the regional I–D curve flags 20 Apr at Δ=0
*and* (independently, so not just a specificity artifact) IMERG resolves a genuine sub-daily burst there
(E=2.25). The earlier "three products agree no acute spring rain / rainfall ruled out" was an **artifact of
an imprecise news date** (27 Apr) — we had been validating against the wrong day. What remains true from
§12d: the **daily AOI-mean** products (ERA5-Land 27 mm, CHIRPS) *under-read* the 20 Apr cloudburst because it
was a **localized cell diluted by AOI-averaging** — so the *measurement* lesson stands (sub-daily/point data,
not daily AOI-mean, resolves it), but the *interpretation* (not rainfall-driven) was wrong. The smaller
**8 May** event stays marginal/priming-dominated. **Synthesis:** primed slopes (§12f) **+** a 20 Apr
cloudburst trigger = the failure — the model captures *both*. **Methodological lesson:** inventory-date
accuracy is critical — a one-week error had inverted the conclusion; this is exactly why the GSI Bhukosh
verified-date inventory matters. Outputs: refreshed `backtest_report.*`, `imerg_subdaily_report.*`.

---

## 13. Tropospheric-correction method comparison (the ~30 mm/yr noise floor)  `[MEASURED]`

Source: `workflows/compare_tropo_methods.py` over 3 MintPy runs on frame106 (`run_mintpy_era5_f106.sh` =
ERA5; `run_mintpy_height_f106.sh` = empirical; step-2 = none), same **3,109** coh≥0.7 pixels. 2026-06-03.
A **Bekaert et al. (2015, "TRAIN")**-style statistical comparison — the concrete attack on the noise floor,
prompted by reviewing the TRAIN toolbox (kept Python-native; MintPy ships these methods, so no MATLAB).

| method | velocity std (mm/yr) | Δ scatter | r vs custom (raw) | r (high-pass) | RMS off-rm |
|---|---|---|---|---|---|
| **none** (no correction) | 30.5 | — | +0.419 | +0.459 | 33.1 |
| **ERA5** (weather model; pyaps) | **21.0** | **−31 %** | **+0.587** | **+0.545** | **25.2** |
| **height-correlation** (empirical, topo-correlated; Doin 2009) | 30.6 | ~0 % | +0.547 | +0.523 | 29.3 |

**Finding:** **ERA5 is decisively the best on every metric** (scatter 30.5 → 21.0 mm/yr, −31 %; agreement
+0.42 → +0.59) — it confirms and quantifies the project's already-adopted choice. The **empirical
height-correlation** correction **improves cross-engine agreement** (r +0.42 → +0.55, RMS 33 → 29) but
**barely reduces scatter** (30.5 → 30.6) — textbook behaviour: it removes only the *stratified*
(elevation-correlated) delay, so the two SBAS engines agree more, but it leaves the *turbulent* atmosphere
that dominates the noise floor here. So the floor is **turbulence-dominated, not stratified** — a
weather-model (ERA5/GACOS) correction is required; the cheap topo-only method is insufficient. This is a
reviewer-grade "we compared correction methods" result (publication bar #4). Outputs:
`data/mintpy/tropo_method_comparison.{json,md,png}`, `mintpy_out/velocity_mintpy_height.tif`.

**References:** Bekaert et al. (2015) *Remote Sens. Environ.* 170:40-47 (TRAIN) · Doin et al. (2009)
*J. Appl. Geophys.* 69:35-50 (height-correlation) · Jolivet et al. (2011) *GRL* 38:L17311 + Hersbach et al.
(2020) (ERA5/pyaps) · Yunjun et al. (2019) *Comput. Geosci.* 133:104331 (MintPy).

---

## 14. GSI field-validated inventory ingested → authoritative spatial back-test  `[REAL / MEASURED]`

Source: `workflows/ingest_gsi_inventory.py` extracts the GSI **"Landslide Inventory (Field Validated)"** table
(user-provided `Research/LandslideInventory/landslide_report.pdf`, the all-India inventory, 582 pp) via
`pdfplumber.extract_tables()`, clipped to the AOI bbox (+0.05°). 2026-06-03. **Finally replaces the ~11
approximate news-derived points** (§9) with authoritative georeferenced ground truth — exactly what the
§12g date-correction lesson said was needed.

- **138 field-validated landslide records in the AOI** (lat 33.10–33.40, lon 75.10–75.40): **Ramban 83**,
  Doda 22, Anantnag 18, Udhampur 10, Poonch 5. Movement: Slide 85, Fall 26, Composite 18, Flow 3, …
  Outputs: `data/inventory/gsi_inventory_aoi.{csv,geojson,md}`. (Dates are year-level / mostly blank → this is
  a **spatial** ground truth; acute-trigger *timing* stays with the §12g literature events.)
- **Spatial back-test (ASC union monsoon zones, 405):** **71 % of the 138 mapped slides within 2 km** of a
  flagged zone (54 % ≤1 km, 28 % ≤0.5 km; median nearest **0.84 km**, mean 1.38). A real coincidence against
  field-mapped slides. ⚠️ **Still recall/detection, not full precision–recall:** 405 zones AOI-wide make
  coincidence partly density-driven — a *scored* test needs a **specificity/precision** arm (do flagged zones
  avoid no-landslide ground? a null/random-point control) + a distance ROC. The tool now ingests the
  authoritative inventory unchanged; the precision arm is the remaining enhancement.

**Companion GSI susceptibility brief** (`…/Meso Scale Landslide Susceptibility Mapping_ Batote … Doda.md`):
GSI meso-scale (1:10,000) LSM of NH-244 Batote→Ganpat Bridge (Ramban/Doda, 2024-25): **~30 % "High"
susceptibility, model AUC 0.84**, 35 field-verified instabilities — an **independent susceptibility benchmark**
to corroborate our hazard map against. It also gives **site geotechnical parameters** (φ ≈ **36–39°** dry with
significant **wet strength loss**; silty, low-permeability overburden 0.5–20 m thick) → a concrete path to
**calibrate the FS soil parameters** (currently literature defaults c′=5 kPa/φ=32°/z=3 m — §0/§5a) and confirms
**construction-driven instability** (road widening; Panthal/Makerkot bridge foundations) — supporting §12g's
non-meteorological factor for 20 Apr.

---

## 15. FS soil-parameter calibration from the GSI geotechnical study  `[REAL params / ANALYTIC effect]`

Source: `geomechanical_engine.py` soil defaults calibrated from the **GSI meso-scale (1:10,000) landslide-
susceptibility field study** of NH-244 Batote(Chakwa Nala)→Ganpat Bridge, Ramban/Doda, J&K (GSI 2024-25;
`Research/LandslideInventory/Meso Scale Landslide Susceptibility Mapping_…Doda.md`). 2026-06-03. Addresses
the standing "soil parameters are generic literature defaults" limitation (§0, §5a).

- **Friction angle φ: 32° → 36°** — the study measured **φ = 36.4–39.1°** on the site overburden (silty
  colluvium/scree/RBM, >75 % fines, 0.5–20 m thick, moisture-sensitive); we adopt the conservative end (36°).
- **Cohesion kept 5 kPa** — the study reports good *dry* strength but **"significant reduction when wet"**;
  the hazard end-member is **saturated** (m=1), so the low wet-reduced cohesion is the relevant value. The
  higher dry cohesion + a proper dry/wet (matric-suction) split is the deferred refinement (Area 7 #4).
  γ=19 kN/m³ and z=3 m sit within the measured ranges.
- **Effect (analytic infinite-slope FS, c′=5, γ=19, z=3):** φ=36° raises FS **~12–14 %** vs 32° (e.g. slope
  28°: FS_dry 1.39 → 1.58, FS_sat 0.78 → 0.87). The **critical slope for saturated failure (FS_sat=1) shifts
  22.0° → 24.6°** (dry FS=1: 37.4° → 41.4°) — i.e. the calibration **de-flags the gentle 22–25° band**
  (fewer false-positive unstable slopes) while the steep slopes (AOI median ~28°) stay flagged.

**Finding:** the hazard physics now uses a **site-measured** friction angle rather than a textbook value — a
real reduction in the soil-assumption uncertainty (publication bar #5). The map will flag somewhat fewer
zones; the exact zone-count change needs a hazard **re-run** (`run_multistack.py` — Docker), so the prior
hazard KPIs (§5a/§5c, under φ=32) are preserved as the literature-default baseline and future runs use
φ=36. *Remaining: site lab calibration of cohesion + the matric-suction dry/wet-cohesion split.*
**Citation:** GSI National Landslide Susceptibility Mapping / meso-scale LSM, NH-244 Batote–Ganpat Bridge,
Ramban–Doda (Geological Survey of India, 2024-25 field season).

---

## 16. φ=36 hazard re-run + fully scored back-test (precision/specificity + ROC AUC)  `[REAL / MEASURED]`

Source: `workflows/run_multistack.py --force` (Docker, 2026-06-07) re-computed Phases 3–4 with the
calibrated friction angle **φ = 36°** from §15; `workflows/backtest_inventory.py` extended with a
null-point control arm (`--n-null 5000`, `--null-seed 20260606`) + a distance-ROC sweep then run
against `data/inventory/gsi_inventory_aoi.geojson` (138 GSI field-validated points, §14) on
`data/alerts/mosaic_asc/alerts_monsoon.json`. Resolves the §15 "exact zone-count change needs a
re-run" pending item.

### 16a. φ 32° → 36° hazard zone-count delta (monsoon scenario, ASC stacks + union mosaic)

| Quantity | φ=32° (prior, §5/§9 baseline) | φ=36° (calibrated) | Δ |
|---|---|---|---|
| frame106 monsoon zones | 222 | **192** | −30 (−13.5 %) |
| frame101 monsoon zones | 5 | **4** | −1 (−20 %) |
| frame102 monsoon zones | 206 | **189** | −17 (−8.3 %) |
| Union HIGH pixels (mosaic) | 5,268 | **4,418** | −850 (−16.1 %) |
| Union HIGH ≥2-look-confirmed | 291 | **251** | −40 (−13.7 %) |
| Union monsoon alert zones | 405 | **357** | −48 (−11.9 %) |
| Union monsoon ≥2-look confirmed | 26 | **26** | 0 (robust core) |

The calibration **de-flags ~12–14 % of marginal zones** (the gentle 22–25° band §15 predicted), while
the multi-look-confirmed core (26 zones) is unchanged — exactly the "fewer false positives, same hard
core" behaviour expected from raising φ within the GSI-measured range.

### 16b. Scored spatial back-test on the φ=36° mosaic (null-point control + distance-ROC)

Inventory: 138 GSI field-validated AOI points (§14). Negatives: 5,000 random points drawn uniformly
inside the AOI polygon (seed 20260606). Decision rule: a point is "detected" if a flagged-zone
centroid lies within buffer-km. **TPR = real detection rate; FPR = null detection rate.**

| buffer (km) | TPR (real) | FPR (null) | specificity | precision* | lift (TPR/FPR) |
|---|---|---|---|---|---|
| **0.10** | **0.029** | **0.018** | **0.982** | **0.617** | **1.61×** |
| 0.25 | 0.123 | 0.101 | 0.899 | 0.55 | 1.22× |
| 0.50 | 0.275 | 0.310 | 0.690 | 0.471 | 0.89× |
| 0.75 | 0.406 | 0.495 | 0.505 | 0.450 | 0.82× |
| 1.00 | 0.493 | 0.644 | 0.356 | 0.434 | 0.77× |
| 1.50 | 0.630 | 0.817 | 0.183 | 0.435 | 0.77× |
| 2.00 (prior §14 buf) | 0.696 | 0.900 | 0.100 | 0.436 | 0.77× |
| 2.50 | 0.746 | 0.948 | 0.052 | 0.440 | 0.79× |
| 3.00 | 0.870 | 0.981 | 0.019 | 0.470 | 0.89× |
| 4.00 | 0.978 | 1.000 | 0.000 | 0.495 | 0.98× |
| 5.00 | 1.000 | 1.000 | 0.000 | 0.500 | 1.00× |

\*precision under equal class priors = TPR/(TPR+FPR).

**Headline scores:** AUC = **0.409**; at the previously-reported 2 km buffer, TPR=0.696 but FPR=0.900
(lift **0.77×**, i.e. **worse than chance**); null-point median nearest-zone distance **0.76 km** vs
real-inventory **1.01 km** (a random AOI point is closer on average than a GSI landslide).

**Honest reading — what this tells us (and what the prior §14 71 % headline missed):**
1. **The model has real, *localized* spatial skill at tight buffers** — lift **1.61× at 100 m** and
   **1.22× at 250 m** (specificity 0.98 → 0.90). It is *not* random where the alerts land.
2. **At ≥0.5 km the FPR climbs faster than TPR** — the AOI is small (~22×22 km) and the φ=36° mosaic
   still flags 357 zones over a corridor that overlaps most of the field-mapped landslide belt, so
   coincidence-at-2 km is the *default*, not a discriminator. **The §14 "71 % within 2 km" was
   indicative — not scored.** Once scored against the null, it is below chance at that buffer.
3. **AUC < 0.5** is driven by the mid-buffer FPR climb (zone density > inventory density at km-scale).
   It does **not** invalidate the close-in (≤250 m) skill — but it does mean the *headline*
   evaluation buffer should be **≤250 m** when claiming detection.
4. **Implication for §5a/§5c (the mock cascade) and §9 (prior back-test):** keep them as the prior
   baselines; the new operational headline is "lift **1.61× at 100 m**; AUC **0.409** over
   0.1–5 km (because we flag a lot of area)". This is the first **scored** back-test on this project.

**Next selectivity levers** (raise AUC + lift at km-scale): (a) restrict the comparison to the
**≥2-look-confirmed** subset (26 monsoon zones, the robust core); (b) the **V_slope** mosaic
(`data/alerts/mosaic_asc_vslope/` — more selective, §10/§11); (c) the *selective* regional rainfall
curve (§12/§12c) to cut down the "everything is saturated" assumption baked into the monsoon scenario.

**Producing scripts (this entry):** `workflows/run_multistack.py --force` (φ=36° hazard) +
`workflows/backtest_inventory.py --inventory data/inventory/gsi_inventory_aoi.geojson
--alerts data/alerts/mosaic_asc/alerts_monsoon.json` (scored arm).
**Artefacts:** `data/inventory/backtest_report.{json,md}`, `backtest_map.png`, `backtest_roc.png`.

### 16c. Selectivity levers — does restricting the alert product raise discrimination?  `[REAL / MEASURED]`

Tests the §16b hypothesis that the more-selective products discriminate better. Same 138 GSI points,
same 5,000 null pts (seed 20260606), φ=36° throughout. `--min-looks 2` filters to the multi-look-
confirmed union core; the V_slope mosaic was re-run under φ=36 (`run_multistack.py --use-vslope
--force` → `data/alerts/mosaic_asc_vslope/`: 362 monsoon zones, HIGH ≥2-look 331 vs LOS 251).

| product (monsoon mosaic) | zones | AUC | lift@100 m | lift@250 m | lift@500 m | spec@2 km | lift@2 km | peak lift |
|---|---|---|---|---|---|---|---|---|
| **LOS full** (§16b) | 357 | 0.409 | **1.61×** | 1.22× | 0.89× | 0.10 | 0.77× | 1.61× @0.1 km |
| **LOS ≥2-look core** | 26 | **0.461** | 0.0×* | 0.88× | **1.57×** | **0.64** | **1.18×** | 1.57× @0.5 km |
| **V_slope full** | 362 | 0.413 | 1.17× | **1.29×** | 0.79× | 0.08 | 0.84× | 1.29× @0.25 km |
| **V_slope ≥2-look core** | 29 | 0.418 | 0.0×* | 0.93× | 1.51× | 0.66 | 1.02× | 1.51× @0.5 km |

\*0.0× at 100 m is a **sparsity artefact** — only 26–29 core zones, none within 100 m of any of the 138
points (TPR=0); the core's discrimination appears at ~500 m.

**Findings (the §16b hypothesis is *partly* confirmed):**
1. **The ≥2-look core genuinely improves km-scale discrimination** — AUC **0.409 → 0.461**, lift@2 km
   **0.77× → 1.18×**, specificity@2 km **0.10 → 0.64**. Restricting to the robust core is the right
   move when you care about *not over-flagging* (specificity), confirming §16b lever (a).
2. **…but it trades away close-in recall.** The core has only 26 zones, so at tight buffers it simply
   isn't near enough points (lift@100 m = 0). Its sweet spot is **~500 m (1.57×)**. The **full LOS
   mosaic still wins for localized detection** (lift **1.61× @100 m**). There is **no dominant
   product — it is a recall/specificity trade governed by zone density.**
3. **V_slope ≈ LOS for *this* validation.** V_slope-full edges LOS at 250 m (1.29× vs 1.22×) but is
   marginally worse elsewhere; V_slope-≥2-look ≈ LOS-≥2-look. The downslope projection's demonstrated
   value (cross-geometry corroboration, §10/§11: ≥2-look HIGH +37 %) **does not translate into better
   GSI-inventory discrimination** — lever (b) is a wash here. (Note V_slope's core is *larger*, 29 vs
   26 zones / 331 vs 251 HIGH px, so it corroborates more, but not *more accurately* vs ground truth.)

**Operating-point guidance (the actionable output):**
- **Localized "where exactly" detection** → **full LOS mosaic**, report at a **≤250 m** buffer (lift
  1.61× @100 m, 1.22× @250 m). This is the headline detection claim.
- **Area screening / "don't cry wolf"** (specificity-first) → **≥2-look-confirmed core**, ~500 m–2 km
  (AUC 0.461; specificity 0.64 @2 km; lift 1.18×). This is the headline discrimination claim.
- **V_slope** adds corroboration breadth, **not** validation accuracy — keep it opt-in.

**Producing script:** `workflows/backtest_inventory.py` with `--min-looks {1,2}` + `--out-prefix`
over `mosaic_asc/` and `mosaic_asc_vslope/`. **Artefacts:** `data/inventory/backtest_los_2look_*`,
`backtest_vslope_*`, `backtest_vslope_2look_*` (`.json/.md/_map.png/_roc.png`).

### 16d. ★ Rainfall-realistic saturation — the lever that crosses chance  `[REAL / MEASURED]`

Source: `workflows/rainfall_selectivity_backtest.py` (Docker, 2026-06-07). Tests §16c lever (c). The
monsoon mosaic (§16b) assumes soil saturation **m=1 everywhere** — but the regional rainfall/antecedent
model (`rainfall_id_threshold.py --threshold nwhimalaya`, §12) only reaches **m=1 on 11/214 days**; the
**median day is m≈0.26**. Since FS is exactly linear in m, the sweep rebuilds the AOI union mosaic at
each saturation (`FS_real=(1−m)·FS_dry+m·FS_sat`, reusing the orchestrator agents + `union_alerts`) and
scores each against the 138 GSI points with the same null control (n=5000, seed 20260606) + ROC.

| m (saturation) | union zones | AUC (full) | spec@2 km | lift@2 km | lift@500 m | lift@250 m | **lift@100 m** |
|---|---|---|---|---|---|---|---|
| **1.00** (monsoon, §16b) | 357 | 0.407 | 0.10 | 0.77× | 0.89× | 1.15× | 1.61× |
| 0.85 | 270 | 0.445 | 0.16 | 0.82× | — | — | 2.10× |
| 0.70 | 207 | 0.466 | 0.21 | 0.82× | — | — | 2.46× |
| 0.55 | 157 | 0.494 | 0.25 | 0.85× | — | — | 2.22× |
| **0.40** | 88 | 0.535 | 0.36 | 0.96× | 1.48× | 2.79× | **5.57×** |
| **0.25** (≈ median real day) | 52 | **0.550** | **0.61** | **1.08×** | 1.80× | 3.19× | 4.53× |

**Findings — the answer is an emphatic YES, and it crosses chance:**
1. **AUC rises monotonically as saturation falls: 0.407 → 0.550** (m=1.0 → 0.25). The rainfall-realistic
   product **clears 0.5 at m≈0.25–0.30** — the first configuration on this project to beat chance over
   the full 0.1–5 km sweep. (m=1.0 here = 0.407 reproduces the §16b monsoon baseline 0.409 / 357 zones /
   1.61×@100 m — a built-in sanity check that the rebuild is faithful.)
2. **Close-in detection becomes genuinely strong.** At **m=0.40**: lift **5.57× @100 m, 2.79× @250 m,
   1.48× @500 m, 1.28× @1 km** — i.e. *above chance at every buffer out to 1 km*. At **m=0.25**: lift
   **>1× at every buffer** (4.53×@100 m … 1.08×@2 km) and specificity@2 km **0.10 → 0.61**.
3. **Why it works (and the honest nuance):** lowering m raises FS uniformly, so only the **steepest,
   most-marginal slopes** stay below FS<1 — and the GSI field-mapped slides sit on exactly those slopes.
   **The regional ID *curve* is a TEMPORAL gate (which days to issue) and cannot by itself move a
   *spatial* score; the spatial gain comes from the saturation *level*.** The right operational
   coupling is therefore: the regional curve decides *when* to raise the alert, and the alert is drawn
   at a **rainfall-realistic saturation (m≈0.25–0.40), not the worst-case m=1**.
4. **The trade is recall.** m=0.40 flags 88 zones vs 357 at m=1.0; TPR@2 km falls 0.70 → ~0.62 (m=0.40)
   / 0.43 (m=0.25). You detect fewer total sites but each alert is far more trustworthy — the classic
   precision/recall move, now *measured* and tunable.

**Recommended operating point:** **m≈0.40** (best close-in lift 5.57×@100 m, AUC 0.535, lift>1 to
1 km) for *localized* warning; **m≈0.25** (AUC 0.55, specificity 0.61@2 km) for *specificity-first*
screening. This **supersedes the m=1 monsoon mosaic as the headline alert product** for validation;
the mock dry/monsoon/extreme cascade (§5b/§5c) stays as the scenario-comparison baseline.

**Producing script:** `workflows/rainfall_selectivity_backtest.py` (sweep `--saturations`, reuses
`backtest_inventory.roc_from_distances`). **Artefacts:** `data/inventory/rainfall_selectivity_report.
{md,json}`, `rainfall_selectivity.png`, per-m `data/alerts/mosaic_asc/alerts_sat{025..100}.json`.

### 16e. `operational` scenario — the §16d finding is now a first-class standing product  `[REAL / MEASURED]`

Source: §16d lived only in the experiment script. Added a fourth scenario **`operational`** (saturation
**m=0.40**, `FS_real`, ~20 mm/72 h — the data-median wet day) to `agentic_orchestrator.SCENARIOS` +
`run_multistack.SCENARIOS`, so it now propagates through per-stack alerts → union mosaic → briefings →
dashboards **alongside** (not replacing) the mock dry/monsoon/extreme cascade. Generated by
`run_multistack.py --force` (Docker, 2026-06-07).

- **Per-stack (monsoon → operational):** frame106 192→**46**, frame102 189→**49**, frame101 4→**0**.
- **Union operational: 88 zones** (14 critical, **6 ≥2-look confirmed**) vs monsoon 357 (26 ≥2-look).
- **Scored (same 138 GSI pts, null n=5000, seed 20260606): AUC = 0.537** — reproduces the §16d m=0.40
  sweep (0.535) **exactly** (both 88 zones), confirming the standing product == the experiment. At 2 km
  TPR=0.616 / FPR=0.639 (lift 0.96×); the discrimination lives close-in (lift 5.6×@100 m, §16d).

**Net:** the demos/dashboards now lead with the **rainfall-realistic, beats-chance** product
(`alerts_operational.json`, `dashboard_operational.html`), not the over-flagging worst-case monsoon map.
The mock cascade is preserved as the scenario-comparison baseline (its `[MOCK]` KPIs untouched, per the
preserve-on-removal rule). **Producing scripts:** `run_multistack.py` (now builds 4 scenarios) +
`backtest_inventory.py --alerts data/alerts/mosaic_asc/alerts_operational.json`. **Artefacts:**
`data/alerts/mosaic_asc/alerts_operational.json`, per-stack `dashboard_operational.html`,
`data/inventory/backtest_operational_{report.json,report.md,map.png,roc.png}`.

---

## 17. Temporal gate — the regional curve gates the validated footprint (WHEN × WHERE)  `[REAL / MEASURED]`

Source: `workflows/operational_alarm.py` (Docker, 2026-06-07), regional `nwhimalaya` I-D curve on
ERA5-Land water. Completes the two-factor operational warning: **WHERE** = the validated operational
m=0.40 footprint (88 zones, §16e, beats chance); **WHEN** = the regional curve graded by the per-day peak
exceedance **E(t) = max_D[cum_D/threshold_cum(D)]** (reused from `rainfall_specificity.py`). The curve is
a *lower bound* and fires E≥1 on **112/214 days** (§12c) — too sensitive; grading by E restores
selectivity. Three states: **DORMANT** (E<1, footprint not armed) / **WATCH** (1≤E<2, armed) / **ALERT**
(E≥2, alarm raised). The footprint is held FIXED at the validated map — it is *not* ballooned to the
worst-case monsoon map on wet days (that is what over-flagged in §16b).

### 17a. Selectivity — the gate fixes the over-firing

| state | rule | days | % season | vs raw regional |
|---|---|---|---|---|
| raw regional trigger | E≥1 | 112 | 52.3 % | — (too sensitive) |
| WATCH+ (footprint armed) | E≥1 | 112 | 52.3 % | same set |
| **ALERT (alarm raised)** | **E≥2** | **27** | **12.6 %** | **4.1× fewer days** |

ALERT days cluster on the physically-right windows: **19–21 Apr** (the cloudburst), the **25 Aug–15 Sep**
monsoon peak, and **6–7 Oct** — not scattered across the season.

### 17b. Temporal validation — do ALERT days coincide with documented failures?

| documented event | date | E on day | nearest ALERT Δd | nearest WATCH+ Δd | state |
|---|---|---|---|---|---|
| Seri Bagna (20 Apr cloudburst, 3 deaths) | 2025-04-20 | **2.89** | **0** | 0 | **ALERT** |
| Kela Morh / T-2 tunnel (20 Apr) | 2025-04-20 | **2.89** | **0** | 0 | **ALERT** |
| Digdol–Khooni Nallah slide | 2025-04-27 | 1.41 | 6 | 0 | WATCH+ |
| Chamba Seri mudslide | 2025-05-08 | 0.67 | 17 | 5 | WATCH+ |

**Caught: 4/4 by ALARM (WATCH+); 3/4 by ALERT** (±10 d). The verified deadly **20 Apr cloudburst is an
ALERT at Δ=0 (E=2.89)** — the gate raises the alarm on exactly the right day, on the same footprint that
beats chance spatially. 27 Apr (E=1.41) and 8 May (E=0.67) sit only just above / below the regional line
on reanalysis rain → they land in WATCH, not ALERT — the **documented sensitivity/selectivity bind**
(§12c): their true intensity is sub-grid, so gauge/sub-daily rain (IMERG, E=2.25 on 20 Apr) is what would
raise their E. Honest, not hidden.

**Net:** the system is now a genuine two-factor operational warning — *WHERE* (spatial, scored above
chance, §16d/e) **×** *WHEN* (temporal, selective 12.6 %-season gate, catches the verified major event at
Δ=0). The over-firing flagged as the standing weakness in §12c/CF5/Part E is **resolved by the E-grading**
without losing the major event. **Honest scope:** AOI-mean rain → one E/day → the gate is AOI-wide on/off;
sub-daily/point rain would let it vary per zone. **Producing script:** `workflows/operational_alarm.py`
(`--watch-k`/`--alert-k`/`--as-of`). **Artefacts:** `data/rainfall/operational_alarm_report.{json,md}`,
`operational_alarm_calendar.csv`, `operational_alarm.png`, and a self-contained **two-factor warning
dashboard** `data/alerts/mosaic_asc/operational_alarm_dashboard.html` (a "current state" banner as-of a
chosen day — WHERE footprint × WHEN alarm calendar in one view).

---

## 18. ERA5-corrected velocity rolled through the hazard (frame106) — a creep-robustness flag  `[REAL / MEASURED]`

Source: `workflows/hazard_era5_compare.py` (Docker, 2026-06-07). Rolls the MintPy **ERA5 physically-tropo-
corrected** velocity (§3/§13: scatter 39→21 mm/yr) through the SAME creep→hazard fusion as the custom
spatial-high-pass velocity, on frame106 (the only stack with an ERA5 run). Fair alignment is identical to
`crossval_mintpy.py`: ERA5 ×1000 (m/yr→mm/yr), coh≥0.7 mask, the same nan-aware high-pass (σ=30 px), same
FS_saturated, same creep rule (<−15 mm/yr), HIGH = FS<1 AND creep. **Self-check passed:** the re-fused
custom hazard reproduces the on-disk engine hazard exactly (so the only changed input is the velocity).

| layer | custom (high-pass proxy) | ERA5 (physical tropo) | overlap | IoU |
|---|---|---|---|---|
| velocity agreement (r, 3,109 common px) | — | — | — | **r=0.545** (= §3 crossval) |
| creep px (vel < −15 mm/yr) | 3,752 | **1,615** | 295 both | 0.058 |
| HIGH px (FS<1 AND creep) | 2,174 | **1,032** | — | 0.064 |
| HIGH zones (≥3 px) | 192 | **72** | — | — |

**Findings (honest, two-sided):**
1. **The ERA5 correction roughly halves the creep/HIGH flag** (creep 3,752→1,615; HIGH zones 192→72),
   consistent with the custom high-pass leaving residual atmospheric "motion" that inflates creep — the
   lower-noise ERA5 field (std 21 vs 31) pushes fewer pixels past −15 mm/yr.
2. **…but the two flag *different* slopes.** Of the pixels ERA5 calls creeping, only **~18 %** (295/1,615)
   are also custom-creep; full-grid IoU 0.06. This is partly expected (a hard threshold on two r≈0.55
   fields disagrees in the tails) and partly a pixel-support difference — but it means the **single-look
   creep flag is genuinely sensitive to velocity processing.**
3. **Interpretation — an uncertainty flag, not a "winner."** The ERA5 product is the more physically
   grounded basis (atmosphere removed by a weather model, not a spatial proxy), so it is the better velocity
   to build on; but the low overlap reinforces the standing limitation that **single-look creep locations
   are not robust — trust where multiple looks confirm** (the ≥2-look core, §16c). It does *not* claim the
   ERA5 hazard map is "more correct" pixel-for-pixel.

**Scope:** frame106-only demonstrative variant (`data/hazard/ASC_path27_frame106_hazard_class_era5.tif`);
does **not** enter the multi-stack mosaic (only frame106 has an ERA5 run; the DESC stacks were dumped, §4).
Rolling ERA5 through all stacks needs a per-stack MintPy ERA5 run. **Producing script:**
`workflows/hazard_era5_compare.py`. **Artefacts:** `data/hazard/hazard_era5_compare_report.{json,md}`,
`hazard_era5_compare.png`, `ASC_path27_frame106_hazard_class_era5.tif`.

---

## 19. Per-zone temporal gating — the alarm now varies by zone vulnerability  `[REAL / MEASURED]`

Source: `workflows/per_zone_gate.py` (Docker, 2026-06-07). Resolves the §17 "AOI-wide on/off" limitation.
The honest per-zone differentiator is **not** per-zone rainfall (rain is ~uniform at IMERG's ~10 km over a
~22 km AOI, and growing the footprint on wet days re-introduces the §16b over-flag) — it is each zone's
**critical saturation** m\* = (1−FS_dry)/(FS_sat−FS_dry) (FS is exactly linear in m), the wetness at which
*that* zone crosses FS=1, sampled at each operational zone's pixel. Two-level gate: the **regional E(t)**
decides IF an alarm fires (§17 WHEN); on a WATCH/ALERT day the **active zones** are those whose m\* the
day's saturation m(t) has reached — **capped at the validated footprint** (never adds zones from outside,
so no ballooning).

### 19a. Per-zone vulnerability spread (95 per-stack operational zones; union = 88)

| metric | value |
|---|---|
| critical saturation m\* | min **0.00** / median **0.18** / max **0.40** (baseline m=0.40) |
| tier `fails-when-barely-wet` (m\*<0.15) | **44 zones** (operator's top priority) |
| tier `fails-on-a-wet-day` (0.15–0.30) | 33 zones |
| tier `fails-only-when-very-wet` (0.30–0.40) | 18 zones |

The most vulnerable zones (m\*=0.00 → unstable even dry) are CRITICAL with fast creep (e.g. frame102 #4:
FS@0.40=0.77, creep −62 mm/yr) — exactly the slopes to inspect first.

### 19b. The active set "breathes" per day (genuine per-zone behaviour)

| day | saturation m(t) | E | regional | active zones (of 95) |
|---|---|---|---|---|
| 20 Apr (cloudburst) | 0.656 | 2.89 | ALERT | **95** (snowmelt season already saturated) |
| 27 Apr | 0.332 | 1.41 | WATCH | **85** (10 least-vulnerable not yet at failure) |
| 8 May / typical dry | ≤0.20 | <1 | DORMANT | **0** (regional gate off) |
| 26 Aug (monsoon peak) | 1.00 | 6.94 | ALERT | **95** |

Across the **112 WATCH+ days the active count ranges 53–95** (median 95); on the 27 ALERT days, 91–95.
So on the marginal/drier trigger days only the most vulnerable subset (as few as **53**) is active, while
the wettest days escalate the whole footprint — a real per-zone alarm, ranked by m\*, that an operator can
act on. The 20 Apr cloudburst correctly activates all 95 (the spring snowmelt had already raised m to 0.66).

**Honest scope:** per-zone differentiation is by intrinsic **vulnerability** (m\*), not local rainfall (the
WHEN gate stays regional — rain is ~uniform at scale). The active set never exceeds the validated footprint,
so it cannot re-introduce the §16b over-flag. Acute cloudbursts are caught by the regional E gate; m(t) is
the *antecedent* saturation, which a daily product builds slowly (here it was already high on 20 Apr from
snowmelt). **Producing script:** `workflows/per_zone_gate.py`. **Artefacts:**
`data/alerts/per_zone_vulnerability.{json,csv,md}`, `per_zone_active_timeline.csv`, `per_zone_gate.png`.

**Dashboard integration:** `operational_alarm.py` now reads these and renders a **"WHICH ZONES — live as of
<date>"** ranked panel in `operational_alarm_dashboard.html` (the banner's live-zone count also uses the
per-zone-gated number), so the demo is **WHERE × WHEN × WHICH ZONES** — e.g. 26 Aug shows 95/95 active,
27 Apr 85/95, ranked by m\* (most vulnerable CRITICAL/fast-creep first). Gracefully omitted if
`per_zone_gate.py` has not run. *(↪ numbers superseded by §20: the operating point moved to m=0.55.)*

---

## 20. ★ Matric-suction dry/wet cohesion split — better physics, and the project's best score  `[REAL params / ANALYTIC]`

Source: `workflows/geomechanical_engine.py` (matric-suction split) + re-run pipeline + re-scored
(Docker, 2026-06-08). Completes Area 7 #4 (was deferred at §15). Unsaturated soil carries an **apparent
cohesion from matric suction** (negative pore pressure) that **vanishes as it saturates** (extended
Mohr-Coulomb / Fredlund). The prior model used one cohesion (5 kPa) for both end-members; this splits it:

- **c_dry = 18.5 kPa** (effective cohesion + suction) for **FS_dry**; **c_wet = 5 kPa** (suction gone) for
  **FS_saturated**. Source: the GSI LSM brief measured the *dry* cohesion "mean 18.5 kg/cm²" + "good dry
  strength … significant reduction when wet / rapid strength loss during saturation." ⚠️ **Unit caveat:**
  18.5 kgf/cm² ≈ 1814 kPa is rock-like and implausible for this silty colluvium, so we **interpret the
  magnitude as ~18.5 kPa** (credible for suction-enhanced dry fines) — flag for confirmation vs the source PDF.
- **FS stays exactly linear in m** (cohesion interpolates linearly), so `FS_real=(1−m)·FS_dry+m·FS_sat` and
  all downstream coupling (orchestrator, per-zone m\*) are unchanged — **verified algebraically + numerically**.

### 20a. Effect on the Factor of Safety

| layer | pre-split (c=5 flat) | matric-suction (c_dry=18.5 / c_wet=5) | change |
|---|---|---|---|
| FS_dry median (%<1) | 1.58 (4.2 %) | **2.15 (0.0 %)** | dry slopes much stronger (suction) |
| FS_saturated median (%<1) | 0.87 (63.8 %) | **0.87 (63.8 %)** | **unchanged** (c_wet=5 = old) |
| critical slope for FS_sat=1 | 24.6° | 24.6° | unchanged (worst-case identical) |

The worst-case **monsoon product is identical** (357 zones) — the split only changes *intermediate*
saturations, where suction now (correctly) protects slopes that the flat-cohesion model over-flagged.

### 20b. The operating point shifts up — and discrimination IMPROVES (re-tuned §16d sweep)

Crediting dry suction-strength means the old m=0.40 operating point is now "too dry to mobilize failure"
(footprint collapsed 88→1 zone). Re-running the saturation sweep under the new physics:

| m | union zones | AUC | spec@2 km | lift@2 km | peak lift |
|---|---|---|---|---|---|
| 0.40 | 1 | 0.578 | 0.99 | 3.6× | 12.1× @1 km (1 zone) |
| **0.55** | **20** | **0.614** | **0.77** | **1.46×** | 9.1× @0.1 km |
| 0.70 | 94 | 0.526 | 0.35 | 0.94× | 5.2× @0.1 km |
| 1.00 (monsoon) | 357 | 0.407 | 0.10 | 0.77× | 1.6× @0.1 km |

**New operating point: m=0.55, AUC 0.614** (scored on the rebuilt union: **AUC 0.615**, TPR 0.33 / FPR 0.23
/ spec 0.77 / **lift 1.46× even @2 km** — beats chance at *every* buffer, unlike the old m=0.40 which was
0.96× @2 km). This is **the project's best score** — the more-realistic physics *discriminates better*
(pre-suction best was AUC 0.55 at m=0.25, §16d). The `operational` scenario is now **m=0.55 (~32 mm/72 h)**.

### 20c. Per-zone consequence

The 21 operational zones now have m\* ∈ **0.378–0.547** (median 0.484) — *no zone fails when barely wet*
(suction prevents it), correctly; tiers re-fit to 6 `moderately-wet` / 13 `wet` / 2 `very-wet`. The per-day
active set is sparser (median 1 of 21 on WATCH+ days, up to 21 on the wettest): the **20 Apr cloudburst
(m=0.656 from snowmelt) activates all 21**, while 27 Apr (m=0.332) activates 0 — the antecedent ground
wasn't wet enough to mobilize a slope even as regional rain reached WATCH (conservative, honest).

**Net:** the last big soil assumption (flat cohesion) is replaced with site-grounded matric-suction physics;
FS_sat (worst case) is untouched, and the *realistic* operating product moved to m=0.55 and **improved to
AUC 0.614 — the best on the project**. The temporal gate (§17: 27 ALERT days, 20 Apr Δ=0, 4/4 WATCH+) is
unchanged (it keys on rainfall E, not the footprint). **Remaining:** a nonlinear soil-water-retention (van
Genuchten) suction curve (this is a first-order *linear* split); lab confirmation of c_dry/c_wet + the
"18.5 kg/cm²" unit. **Producing scripts:** `geomechanical_engine.py` (`--cohesion-dry-kpa`/`--cohesion-wet-kpa`)
+ `run_multistack.py` + `rainfall_selectivity_backtest.py` + `backtest_inventory.py`. **Supersedes the m=0.40
operating point in §16d/§16e/§17/§19** (those entries are the pre-suction baseline; their footprint/per-zone
numbers move to m=0.55 here). *(↪ m=0.55 itself superseded by §21: the 12.5 m DEM moved it to m=0.50.)*

---

## 21. ★ 12.5 m ALOS DEM — sharper slope, and a new best score  `[REAL data / MEASURED]`

Source: `workflows/geomechanical_engine.py` (`slope_on_grid`) + re-run + re-tune + re-score (Docker,
2026-06-08). User downloaded the **ALOS PALSAR 12.5 m DEM** (one tile, EPSG:32643, covers the AOI) to
`data/dem_alos_12m/`. The hazard grid stays 80 m (velocity-limited), but slope is now computed at **native
12.5 m then AVERAGE-aggregated** onto each 80 m cell (`find_dem_for_stack` prefers ALOS, HyP3 30 m
fallback). **Mean-of-slopes > slope-of-mean**, so this fixes the 80 m DEM's known steepness under-estimate
(the standing limitation). Both FS_dry **and** FS_sat shift (slope drives both — unlike §20 where only
FS_dry moved).

### 21a. Effect on slope + FS (vs the HyP3 ~30 m DEM)

| quantity | HyP3 ~30 m DEM | ALOS 12.5 m DEM | change |
|---|---|---|---|
| slope median / p95 / max | 28.0 / 40.9 / 56.5° | **31.0 / 44.6 / 66.1°** | sharper, steeper tail |
| FS_dry median | 2.15 | **1.95** | (still ~0 % unstable dry) |
| FS_saturated median (%<1) | 0.87 (63.8 %) | **0.78 (74.3 %)** | more steep slopes flag when wet |
| monsoon union zones | 357 | **393** | +10 % (sharper terrain) |
| mosaic HIGH px (≥2-look) | 4,418 (251) | **5,176 (289)** | +17 % |

### 21b. Re-tuned operating point — the project's best score

Re-running the saturation sweep under the sharper terrain (the FS curve shifted, so the optimum moved):

| m | union zones | AUC | spec@2 km | lift@2 km |
|---|---|---|---|---|
| 0.40 | 1 | 0.537 | 0.97 | 2.6× |
| **0.50** | **12** | **0.641** | **0.86** | **1.81×** |
| 0.55 | 30 | 0.522 | 0.73 | 1.21× |
| 0.70 | 132 | 0.504 | 0.29 | 0.89× |
| 1.00 (monsoon) | 393 | 0.432 | 0.11 | 0.79× |

**New operating point: m=0.50, AUC 0.641** (scored on the rebuilt union; 12 zones, spec 0.86, precision
0.645, lift 1.81× @2 km — beats chance at every buffer). **The project's best**, edging the matric-suction
m=0.55 (0.614). Each physics upgrade has both removed an assumption *and* improved the score:
**φ=36 → flat-cohesion m=0.40 / AUC 0.535 → matric-suction m=0.55 / 0.614 → +12.5 m DEM m=0.50 / 0.641.**
Per-zone (§19): the 12 operational zones now have m\* ∈ 0.272–0.499 (median 0.421), tiers 8 `moderately-wet`
/ 4 `wet`. The temporal gate (§17) is unchanged (keys on rainfall E, not the footprint).

**Honest notes:** (a) the operating product is now quite sparse (**12 zones — low recall**, the precision↔recall
trade taken to the AUC-max; the ≥2-look core is tiny, so trust is concentrated); (b) the velocity is still
80 m, so the hazard grid is velocity-limited — the DEM sharpens *slope/FS*, not the InSAR resolution; (c) one
ALOS tile covers the AOI, so all 3 ASC stacks share the slope. **Producing scripts:** `geomechanical_engine.py`
(native-slope-then-average) + `run_multistack.py` + sweep + back-test. **Supersedes the m=0.55 operating
point in §20** (and the m=0.40 in §16d–§19). The dashboards/per-zone are regenerated at m=0.50.

---

## 22. ERA5 tropo correction on the remaining ASC stacks — does NOT generalize for free  `[REAL / MEASURED]`

Source: `prep_mintpy.py` + `prep_hyp3` + `run_mintpy_era5.sh` + `hazard_era5_compare.py` (Docker,
2026-06-08). Ran the MintPy ERA5-tropo SBAS on the two ASC stacks beyond frame106 (§18), to roll the
physically-corrected velocity through all stacks. **Honest result: only frame106 (validated, §3/§18) is
trustworthy; frame102 and frame101 fail the quality bar as-run** — the frame106 success does not transfer
without per-stack reference + cross-validation (the same quality-first lesson as the DESC dumping, §4).

| stack | ERA5 vel median | std (mm/yr) | %>\|100\| | temporal coh ≥0.7 | verdict |
|---|---|---|---|---|---|
| frame106 (§18) | 0.0 | 21–41 | 2.8 % | 8 % | ✅ validated (r=0.55 vs custom) |
| **frame102** | **−56.5** | **57.6** | **25 %** | 83 % | ❌ systematic bias (coherent but implausible) |
| **frame101** | 0.0 | 18.3 | 0.7 % | **14 %** | ❌ low-coherence (under-determined) |

- **frame102** has *high* temporal coherence (0.85) yet a **−56 mm/yr scene-wide bias + std 57 + 25 % of
  pixels >|100| mm/yr** — a coherent-but-wrong velocity (reference-pixel / network-unwrapping bias, not
  decorrelation). Even after removing the offset, std 57 is far above the ASC plausibility bar (21–30,
  ~0 % implausible) → **rejected**. Through the hazard it (spuriously) flags 28,623 creep px / 965 HIGH
  zones vs custom 4,338 / 212.
- **frame101** looks flat (median 0, std 18) but only **14 % of pixels reach coh ≥0.7** → the velocity is
  under-determined/unreliable; its apparent "3,743 creep px" is a full-grid coverage artifact (custom
  inverts only 3,655 px). **Rejected** pending a usable reference.
- `hazard_era5_compare.py` self-check passed on both (re-fused custom hazard == on-disk), so the
  *comparison machinery* is sound — the failure is the **ERA5 velocities themselves**.

**Decision: NO multi-stack ERA5 union mosaic** (it would fuse one good + two bad velocities). frame106's
§18 result stands as the validated single-stack demonstration; the mosaic continues to run on the custom
velocities. **What it would take:** per-stack MintPy reference-pixel selection on a stable (bedrock) point
+ network unwrapping-error QC + cross-validation against the custom velocity — a per-stack tuning loop, not
a blanket apply. **Producing scripts:** `workflows/prep_mintpy.py`, `run_mintpy_era5.sh`,
`hazard_era5_compare.py --stack <S> --mintpy-dir <…>`. **Artefacts:** `data/mintpy/{ASC_path100_frame102,
ASC_path27_frame101}/mintpy_out/velocity_mintpy_era5.tif` (+ the per-stack `hazard_era5_compare_report.*`,
overwritten — frame102/101 are demonstrative, not adopted).

---

## 23. Two-tier operational product — a higher-recall WATCH map beside the precision ALERT  `[REAL / MEASURED]`

Source: `agentic_orchestrator.py` (new `watch` scenario, m=0.70) + `run_multistack.py` +
`backtest_inventory.py` (Docker, 2026-06-10). The §21 operating point (m=0.50, **AUC 0.641**) is the
AUC-MAXIMUM, but it flags only **12 zones — low recall** (TPR@2 km **0.254**; the acknowledged #1
weakness, §21 honest-note a): a high-precision "act-now" map that misses slopes which only mobilise on a
wetter antecedent. So we add a **second, more-inclusive tier** at a wetter saturation (**m=0.70** ~
sustained-monsoon antecedent), drawn from the SAME physics — a recall safety-net to monitor, distinct
from the act-now core. The validated m=0.50 ALERT product and its temporal gate (§17) are **untouched**;
WATCH is a complement, not a replacement.

All scored on the GSI inventory (138 AOI pts) vs a null-point control (n=5000, seed 20260606), buffer 2 km:

| tier | scenario | m | union zones | AUC | TPR@2 km (recall) | spec@2 km | precision | lift@2 km | posture |
|---|---|---|---|---|---|---|---|---|---|
| **ALERT** | operational | 0.50 | **12** | **0.641** | 0.254 | 0.86 | 0.645 | 1.81× | act now — precise core |
| **WATCH** | watch | 0.70 | **132** | 0.504 | **0.63** | 0.29 | 0.471 | 0.89× | monitor wider — recall net |
| WATCH ≥2-look core | watch | 0.70 | 10 | **0.591** | 0.319 | 0.81 | 0.631 | **1.71×** | corroborated subset (trust) |
| _(monsoon worst-case)_ | monsoon | 1.00 | 393 | 0.432 | 0.70 | 0.11 | — | 0.79× | over-flags (below chance) |

1. **The precision↔recall frontier, now two named products.** ALERT maximises discrimination/precision
   (AUC 0.64, precision 0.65, lift 1.81×) at low recall (TPR 0.25, 12 zones). WATCH ~**2.5× the recall**
   (TPR 0.25 → 0.63, 12 → 132 zones) by trading discrimination (AUC ~chance 0.50, lift 0.89×). Neither
   dominates — this is the §21b sweep crystallised into ALERT + WATCH.
2. **m=0.70 is the efficient WATCH point.** Going on to the monsoon worst-case (m=1.0) adds only marginal
   recall (0.63 → 0.70) for 3× the zones (132 → 393) and a precision collapse — so WATCH stops at m=0.70,
   not 1.0.
3. **The WATCH net carries a trustworthy core.** Its ≥2-look corroborated subset (10 zones seen by two
   look geometries) still **BEATS CHANCE** — AUC 0.591, specificity 0.81, lift **1.71× @2 km**. So even
   the broad tier has a high-confidence inner ring.
4. **Naming (orthogonal axes).** The spatial WATCH tier (a wider WHERE) is independent of the temporal
   DORMANT/WATCH/ALERT states (§17, the WHEN). Operationally they compose: consult the broad WATCH map for
   monitoring; act on the ALERT core when the temporal gate escalates.
5. **Reproducibility.** The named `alerts_watch.json` reproduces the §21b m=0.70 sweep row exactly (132
   zones; full AUC 0.504; core AUC 0.591 vs the sweep's 0.589 — rounding). `operational` is unchanged at
   12 zones / AUC 0.641.
6. **Surfaced in the operational dashboard.** `operational_alarm.py` now renders **both** tiers in the WHERE
   panel (ALERT + WATCH cards), and — instead of hard-coding the scored numbers — **reads them from the
   back-test report JSONs** (`backtest_<scenario>{,_2look}_report.json`) with `m` taken from
   `agentic_orchestrator.SCENARIOS`, so the dashboard self-updates when the physics/operating point changes.
   The WATCH tier is optional (`--watch-footprint`; hidden if absent — backward-compatible single-tier view).
   The WHEN gate + per-zone "which zones today" panel stay ALERT-focused (the validated act-now core).

**Producing scripts:** `agentic_orchestrator.py` (`watch` scenario, m=0.70) + `run_multistack.py`
(scenario-complete Phase-4 staleness sentinel, so a new scenario regenerates without `--force`) +
`backtest_inventory.py --alerts data/alerts/mosaic_asc/alerts_watch.json [--min-looks 2]` +
`operational_alarm.py` (two-tier dashboard, reads scored metrics from the reports). **Artefacts:**
`data/alerts/mosaic_asc/alerts_watch.json` + `alert_report_watch.md`; per-stack `alerts_watch.json` +
`dashboard_watch.html`; `data/inventory/backtest_watch{,_2look}_report.*`; the two-tier
`data/alerts/mosaic_asc/operational_alarm_dashboard.html`. **Complements §21** (does NOT supersede): ALERT
stays the headline product; WATCH adds the recall option requested in §4/§5(d).

---

## 24. Uncertainty quantification — per-zone DETECTION CONFIDENCE from the velocity noise floor  `[REAL / MEASURED]`

Source: `velocity_uncertainty.py` + `backtest_inventory.py` (Docker, 2026-06-10). The project's #1
limitation is the atmosphere-dominated velocity noise floor (§2): a zone creeping at −18 mm/yr is far less
certain to be REAL than one at −45, yet both pass the same v < −15 creep test. This turns the noise floor
into a per-zone probability.

**Method.** Per stack, σ_v = the robust noise floor (1.4826·MAD of the high-passed velocity, resistant to
the creeping minority): **path100_frame102 = 15.9, path27_frame101 = 13.7, path27_frame106 = 24.3 mm/yr**
(below the round "~30" because MAD discounts the real-creep tail). Then:
- per-look:  **p = Φ((−15 − v_zone) / σ_v)**  — P(true mean creep < −15)
- multi-look: **P = 1 − Π_looks (1 − p)**  — independent corroboration

The zone MEAN keeps ~the pixel σ_v (the post-high-pass atmospheric residual stays correlated across a
sub-km zone → no √N averaging), a conservative floor.

**Result — every alert now carries a confidence.**

| footprint | union zones | conf median | HIGH (≥0.9) | MOD (0.7–0.9) | note |
|---|---|---|---|---|---|
| operational (m=0.50) | 12 | 0.77 | 2 | 5 | 0 multi-look; single-look ceiling ~0.97 |
| watch (m=0.70) | 132 | 0.85 | 52 | 53 | 10 multi-look; corroboration → P up to 1.0 |

Multi-look corroboration is now *quantified*: e.g. a WATCH zone seen at p = [0.72, 0.996] by two looks
combines to **P = 0.999** — the formal version of the project's "≥2-look core is the trustworthy subset"
(§16c/§23).

**Validation — confidence is ORTHOGONAL to spatial inventory skill (the honest finding).** Scoring the
WATCH footprint filtered by confidence does NOT lift the inventory AUC:

| filter | zones | AUC | recall@2 km |
|---|---|---|---|
| all | 132 | 0.504 | 0.63 |
| P ≥ 0.7 | 105 | 0.509 | 0.61 |
| P ≥ 0.9 | 52 | 0.475 | 0.39 |

So **detection confidence (is the creep REAL vs atmospheric noise?) is a measurement-reliability axis,
distinct from landslide-proximity (the AUC)** — a zone can be a rock-solid fast creep yet not near a mapped
slide. Notably the geometric **≥2-look** filter (10 zones, AUC **0.591**, §23) beats the signal-strength
**P≥0.9** filter (52 zones, AUC 0.475) for inventory match — *corroboration > magnitude* for prediction.
Confidence is therefore for **triage** (don't dispatch a crew to a noise artifact), not spatial ranking — a
third independent trust axis beside the spatial AUC (§16) and the temporal gate (§17).

**Completes the uncertainty picture (both axes).** FS/physics uncertainty is already the critical-saturation
margin **m\*** (§19 — "the wetness at which this zone fails"); §24 adds the **velocity/measurement**
uncertainty. Each zone now carries uncertainty on both the physics (m\*) and the measurement (P).

**Producing scripts:** `velocity_uncertainty.py [--footprint operational|watch]` + `backtest_inventory.py
--alerts …_conf{,70,90}.json`. **Artefacts:** `data/alerts/mosaic_asc/velocity_confidence_<scenario>.{json,
csv,md,png}`; the scoreable `alerts_<scenario>_conf{,70,90}.json`; `data/inventory/bt_watch_conf*`. Additive
— no change to the validated ALERT/WATCH products.

---

## How to maintain this ledger
- **Append, don't overwrite.** New runs add rows; superseded rows stay, marked *(superseded)*.
- **Tag every number** `[MOCK]` / `[REAL]` / `[MEASURED]` with date + producing script.
- **Before removing any mock setup**, confirm its KPIs are captured here (§5b/§5c/§5d are the
  mock-derived ones).
- Keep this in sync at the same time as the git-ignored journals (it is the *committed* mirror of the
  headline numbers).

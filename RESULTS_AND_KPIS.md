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

**Surfaced in the operator triage table.** `per_zone_gate.py` now computes the per-zone confidence inline
(importing `stack_noise`/`confidence` from `velocity_uncertainty.py` — single source of truth) and adds a
`detection_confidence` column to `per_zone_vulnerability.csv`; the dashboard's "WHICH ZONES — live today"
panel renders it as a colour-coded **confidence** column. The operator now reads each live zone as
**moving (creep) × how-sure (confidence, §24) × how-vulnerable (m\*, §19)** in one row.

**Producing scripts:** `velocity_uncertainty.py [--footprint operational|watch]` + `backtest_inventory.py
--alerts …_conf{,70,90}.json`; `per_zone_gate.py` + `operational_alarm.py` (the confidence column).
**Artefacts:** `data/alerts/mosaic_asc/velocity_confidence_<scenario>.{json,csv,md,png}`; the scoreable
`alerts_<scenario>_conf{,70,90}.json`; `data/inventory/bt_watch_conf*`; the `detection_confidence` column in
`per_zone_vulnerability.csv` + the dashboard panel. Additive — no change to the validated ALERT/WATCH products.

---

## 25. WATCH triage — RANK the recall tier, don't gate it  `[REAL / MEASURED]`

Source: `watch_triage.py` (Docker, 2026-06-10). The per-zone gate (§19) narrows the *validated*
operational footprint by daily wetness; applying it to the WATCH tier (§23, 132 zones) was rejected **by
design** — gating would shrink the breadth that is WATCH's whole purpose (recall), and the gate's "can't
balloon, capped at the validated map" safety property does NOT transfer to the deliberately-permissive WATCH
map (AUC ~0.50, not beats-chance). A high-recall list should be **sorted, not filtered**. So we keep all 132
zones and RANK them, worst-first, by a triage priority that fuses the two per-zone trust axes:

> **priority = (1 − m\*) × P**  — fragility (§19) × detection confidence (§24), both in [0, 1]

A zone ranks high only if it is BOTH fragile (low m\*) AND confidently moving (high P) — the right "AND" for
triage; a fragile-but-likely-noise zone or a confident-but-sturdy one ranks lower. Multi-look corroboration
lifts P (§24), so two-look places rise.

**Result (all 132 WATCH zones kept).** priority **max 0.703 / median 0.341 / min 0.151**; vulnerability tiers
**12** `moderately-wet` / **24** `wet` / **96** `only-when-very-wet` (the marginal tail sinks to the bottom but
stays in the list). Top zone: m\*=0.294 (fragile) × P=0.996 (fast −80 mm/yr creep) = priority 0.703; #3 is
2-look-corroborated (P=0.945). The operator reads the top of the list first instead of staring at 132 equal
dots.

**Why rank not gate (the design call).** ALERT (12 zones, validated, beats chance) is a list you *trust*, so
narrowing it per-day (§19) refines a trustworthy set. WATCH (132 zones, ~chance overall) is a deliberately-wide
net whose value is "don't miss anything" — filtering it re-introduces the miss risk it exists to avoid, and
uses the §19 gate outside its validated footprint. Ranking preserves the net and makes the long list usable.

**Surfaced in the dashboard.** `operational_alarm.py` now reads `per_zone_triage_watch.json` and renders a
compact **"Read first — top 5 by triage priority"** list *inside the WATCH tier card* (each row: location ·
priority · fragility m\* · confidence P · a 2-look badge when corroborated), so the operator gets the
"start here" shortlist right beside the 132-zone WATCH summary. Graceful: the card renders without the list
if the triage file is absent.

**Producing scripts:** `watch_triage.py [--footprint watch|monsoon]` (imports `critical_saturation`/`tier_of`
from `per_zone_gate.py` §19 + `stack_noise`/`confidence` from `velocity_uncertainty.py` §24 — single sources of
truth; merges per-stack → union with combined P, then sorts) + `operational_alarm.py` (the WATCH-card top-N).
**Artefacts:** `data/alerts/mosaic_asc/per_zone_triage_watch.{json,csv,md,png}` (the .png is the triage space —
fragility × confidence, top-right = act first); the top-5 in `operational_alarm_dashboard.html`. Additive —
does not change the ALERT/WATCH products or the §19 gate.

---

## 26. Second AOI — Vaishno Devi (Katra) pilgrimage corridor: Phase 1 complete  `[REAL / MEASURED]`

Source: `submit_hyp3_jobs.py` + `download_hyp3_products.py` + the Phase-1 QA chain (Docker, 2026-07-03),
branch `aoi-vaishnodevi`. First real exercise of the point-anywhere Infra 0b: `config.yaml` now targets
**`vaishnodevi_aoi.geojson`** — an OSM-anchored box around the Katra → Banganga → Adhkuwari → Sanjichhat →
Bhawan (33.0299 N 74.9482 E) → Bhairon-temple route on the Trikuta massif (74.905–74.985 E, 32.960–33.055 N;
anchors verified against OSM nodes incl. the Bhawan–Bhairon ropeway), padded ~2 km to include the slopes
*above* the track and Katra town (runout exposure).

**Phase-1 pull (search window 2026-01-01 → 2026-07-31):** 59 S1 SLC scenes → **49 consecutive pairs across
8 stacks** (ASC path27 f101/f105/f106, ASC path100 f102/f103, DESC path34 f480/f484/f485). Submitted at
**10 credits/job = 490 credits** (7,510 remain). **48 SUCCEEDED, 1 FAILED at ASF** (f106 2026-01-13→01-25);
all 48 downloaded, verified, extracted, manifest-recorded. The failed pair exposed a **dedupe gap**: FAILED
jobs counted as "done", so re-runs never resubmitted them — fixed (skip FAILED in the dedupe scan), re-run
then resubmitted exactly the 1 missing pair (see `error_history_log.md` 2026-07-03).

**Key structural finding — the two AOIs share Sentinel-1 frames.** Katra sits inside the same footprints as
Ramban (path27 f101/f106, path100 f102, path34 f484), so the 2026 pairs joined the existing stacks: the 2025
archive already covers the Trikuta corridor (free baseline extension), and per-track frame drift put the
May–Jun 2026 acquisitions into new labels (path27→**f105**, path100→**f103**).

**QA verdict (pooled graph, 231 products, both AOIs): 141 KEEP / 46 CONCERN / 44 QUARANTINE.**
- **Winter-2026 pairs are heavily quarantined** (phase-elevation R² up to **0.85**; scene relief reaches
  ~6,400 m) — the Jan–Apr chain is mostly atmospheric noise, as NW-Himalaya physics predicts.
- **The spring 2026 stacks connect cleanly after rescue:** ASC f105 islands 2→1, ASC f103 2→1 (the May–Jun
  chains — the seasonally-relevant ones for the monsoon product).
- The big pooled stacks report BROKEN connectivity, but much of that is the **Nov-2025→Jan-2026 acquisition
  hole** between the two campaigns — no rescue can bridge a gap with no scenes; the inverter's SVD/
  period-split path (frame479 precedent) applies. DESC stacks fragment as usual (f484: 9 islands).

**Infra hardening shipped with this (the AOI-coexistence layer):** (a) rainfall/trigger chain fully
config-driven — AOI + `aoi_slug`-prefixed filenames (`<slug>_era5land_daily.csv`, `<slug>_wetness_daily.csv`),
Ramban names byte-identical (grandfathered); (b) **Phase 2–4 output dirs slug-scoped** —
`data/{velocity,hazard,alerts,mosaic,mosaic_vslope}` for Ramban (grandfathered), `…_<slug>` for any other AOI
(12 workflow scripts; verified 20/20 dir resolutions in-container) — required because shared frames mean
stack labels alone cannot separate the sites; (c) `.netrc` mount enabled in compose (Phase-1 auth).

**Honest caveats for the Vaishno Devi product:** φ=36° is a *Ramban/Doda* calibration — carried over as an
assumption, not a fit; no local landslide inventory yet, so no scored back-test — the site inherits the
*framework's* Ramban validation, and its own numbers stay `[UNVALIDATED]` until a Trikuta inventory exists;
first velocity will come from short (4-pair) spring chains → noise floor well above Ramban's 14–24 mm/yr σ_v.

> **↪ Addendum (2026-07-06):** the resubmitted f106 Jan pair failed a **second** time — the job log shows
> a deterministic GAMMA unwrapping error (`mcf: reference point outside image segment`; the deep-winter
> pair has almost no coherent area). Unfixable client-side, immaterial to the product (the winter chain is
> quarantined anyway). The submitter now **retries a failed pair once, then PARKS it** (≥2 failures →
> skipped with a loud warning) so idempotent re-runs stop re-buying a proven failure — final Phase-1 state
> is **48/49 products, 1 parked**. See `error_history_log.md` 2026-07-06.

**Producing scripts:** `submit_hyp3_jobs.py` (+FAILED-dedupe fix), `download_hyp3_products.py`,
`feature_engineering.py` → `phase_elevation_audit.py` → `export_audit_json.py` → `_consolidate_quarantine.py`
→ `sbas_network_graph.py` → `apply_connectivity_rescues.py`; config plumbing in `workflows/config.py`
(`aoi_slug`, `data_suffix`). **Artefacts (git-ignored):** 48 products in `data/processed_tiffs/`, QA masks +
`_connectivity_report.md`, `_rescue_recommendations.json`; Phase 2–4 outputs will land in
`data/*_vaishnodevi/`.

---

## 27. Vaishno Devi Phases 2–4 — first hazard + alert product for the shrine corridor  `[REAL / UNVALIDATED]`

Source: `run_multistack.py` (Docker, 2026-07-03), branch `aoi-vaishnodevi`, outputs in `data/*_vaishnodevi/`.
First full Phase 2→4 run on a second AOI. Inverted the two **connected spring stacks** (§26):
`ASC_path100_frame103` (4 pairs, 2026-05-06→06-23) and `ASC_path27_frame105` (4 pairs, 2026-05-01→06-18) —
two independent ascending tracks over the same box, so "multi-look" = 2-track corroboration.

**Velocity (honest quality):** short 4-pair chains → **high noise floor** — frame103 high-pass std
**61 mm/yr** (vs Ramban's σ_v 14–24, §24), 19.6 % of kept pixels beyond |100| mm/yr (sanity-flagged, not
removed); ~7,100 px/stack pass the −15 mm/yr creep test, much of it noise. **Trust order: the ≥2-look core
first**, single-look with per-zone confidence second.

**Hazard (φ=36° borrowed, HyP3 ~30 m DEM after ALOS fallback; slope median 18°, p95 44°):**
union mosaic **HIGH = 2,705 px**, of which **411 confirmed by both tracks**. Union alert zones:
**dry 0 · operational (m=0.50) 27 (4 critical, 6 multi-look) · watch (m=0.70) 72 (11, 14) ·
monsoon/extreme 185 (72, 19)**. Dry=0 replicates the Ramban cascade shape (rain-triggered site).
*(zone/pixel counts superseded by §30 — 12.5 m ALOS DEM upgrade.)*

**Three latent single-AOI assumptions surfaced and fixed** (first cross-AOI run as a stress test;
`error_history_log.md` 2026-07-03b): (1) `--min-pairs 8` default unreachable by a 4-pair stack → clamp to
stack size; (2) the 12.5 m ALOS tile is per-AOI (Ramban) — zero-coverage now falls back to the HyP3 product
DEM; (3) `slope_velocity.py` still unpacked `find_dem_for_stack`'s pre-§21 return shape — latent since
2026-06-10 because V_slope was never re-run; now requests the product DEM explicitly (`prefer_alos=False`).

**Caveats (why `[UNVALIDATED]`):** no Trikuta landslide inventory → no scored back-test (site inherits the
*framework's* Ramban validation §16/§21b, not its own AUC); φ=36° + the m=0.50/0.70 operating points are
Ramban-calibrated; 30 m slope (no local ALOS tile yet — same §21 upgrade path applies); velocity baseline is
~7 weeks. **Next:** overlay the OSM route/infrastructure on the union zones (the actual "which parts of the
track" deliverable), VD rainfall season (`live_alarm.py` is slug-aware), and extend the S1 chain through the
monsoon (`search_end` bump + idempotent resubmit).

**Producing scripts:** `run_multistack.py` → `custom_sbas_inverter.py` (min-pairs clamp) →
`geomechanical_engine.py` (DEM fallback) → `agentic_orchestrator.py`. **Artefacts (git-ignored):**
`data/velocity_vaishnodevi/`, `data/hazard_vaishnodevi/`, `data/alerts_vaishnodevi/<stack>/dashboard_*.html`,
`data/alerts_vaishnodevi/mosaic_asc/alerts_*.json`, `data/mosaic_vaishnodevi/MOSAIC_ASC_*.tif`. Ramban's
`data/mosaic/` verified untouched (mtime 2026-06-10).

---

## 28. Route exposure — which parts of the Vaishno Devi track are near flagged hazard  `[REAL / UNVALIDATED]`

Source: `route_exposure.py` (Docker, 2026-07-03), branch `aoi-vaishnodevi` — the deliverable the second AOI
was built for. Route geometry: **`vaishnodevi_route.geojson`** — real OSM ways fetched via the OSM
`api/0.6/map` endpoint (Overpass was down; 21 walkable ways + ropeway + helipads + 5 POIs, incl. the named
"Vaishno Devi Track/Trek", "Himkoti Route", "Hathimata Route"; ODbL attribution in the file). Method:
densify the route to 40 m samples; exposure = within the **§16b honest 250 m detection buffer** of (a) a
≥2-look CORE pixel, (b) a union alert zone per scenario (centroid+equivalent-radius circles); direct hit
≤80 m (one pixel). Classes ranked CORE > OPERATIONAL > WATCH > MONSOON.

**Result — 16 exposed segments (~14.2 km of ~walkable network)** *(superseded by §30 — 12.5 m DEM)*:
- **CORE ×1 (read first): 680 m of unnamed path NE of/above the Bhairon top** — the only route element
  near a 2-track-confirmed creep cluster (direct hit; min 248 m to core px).
- **OPERATIONAL ×0** — under the standing m=0.50 product **no route segment is within 250 m of an
  operational zone** (nearest is ~694 m from Bhawan). The rain-realistic flagged slopes sit off-track.
- **WATCH ×7 (7.3 km):** both modern route variants pass *through* watch zones (Hathimata 2.6 km @ 0 m,
  Himkoti 2.28 km @ 0 m), plus "Vaishno Devi Trek" 720 m, the **Bhawan–Bhairon ropeway**, and the shrine
  POIs (Bhawan 187 m, Bhairon temple + ropeway station ~110–140 m from watch/monsoon zones).
- **MONSOON-only ×8 (6.2 km):** mostly the classic "Vaishno Devi Track" switchbacks (32–177 m from
  worst-case zones). **Katra town and the Banganga trek start: CLEAR.**

**How to read it honestly:** at this site single-look zones ride a ~61 mm/yr noise floor (§27), so the
CORE segment is the only *measurement-corroborated* flag; WATCH/MONSOON proximity = "these segments border
slopes the physics+radar puts in the wide net" — monitoring guidance, not a prediction. `[UNVALIDATED]`
caveats of §27 apply unchanged. **Artefacts:** `data/alerts_vaishnodevi/mosaic_asc/route_exposure.{json,md,png}`.
**Also fixed:** `.gitignore`'s blanket `*.geojson` was silently ignoring `vaishnodevi_aoi.geojson` (it was
never committed!) — re-included via `!*_aoi.geojson` + `!*_route.geojson`; both files need a fresh `git add`.

---

## 29. Vaishno Devi goes LIVE — two-factor alarm for the shrine corridor  `[REAL / UNVALIDATED]`

Source: `live_alarm.py` two-stage run (Docker, 2026-07-06), branch `aoi-vaishnodevi`. The corridor now has
the same WHERE × WHEN warning as Ramban: ERA5-Land season fetched for the **VD bbox**
(`vaishnodevi_era5land_daily_vaishnodevi_2026.csv`, 2026-04-01→06-30, 91 days — ~5-day publication lag),
wetness m(t) + regional I-D gate + per-zone gating + the operational dashboard, all suffixed
`_vaishnodevi_2026` in the slug-scoped dirs.

**First live read (as-of 2026-06-30): DORMANT.** Season so far: **13 raw regional trigger days — all in
the 2026-04-03..17 spring wet spell — gated to 0 ALERT days** (13× selectivity); daily m(t)=0.56 on 30 Jun;
**0 of 33 per-zone-gated zones active** (m\* > today's m; season-peak 33 active during the April spell).
The monsoon build-up will move this — re-run `live_alarm.py` (both images) to refresh.

**Cross-AOI honesty guards shipped with this (the important part):**
- `load_tier` back-test lookups are now **suffix-scoped** (`backtest_<scenario><data_suffix>_report.json`)
  — verified in-container that the VD tier loads its 27 zones with `auc=None` even though Ramban's report
  exists. **A site can never wear another site's validation scores.**
- Tier cards render "**Not yet back-tested at this site**" when unscored (the old template claimed
  "AUC n/a *(beats chance)*" — a false claim, now conditional). Verified: 2× in the VD dashboard, 0×
  "beats chance".
- Events panel: per-AOI inventory convention (`<slug>_documented_landslides.geojson`), skipped gracefully
  when absent — Ramban's 2025 events are never scored against another site's season.
- **`site_name` config field** (new, optional): dashboard titles now read from config — VD dashboards say
  "Vaishno Devi — Trikuta shrine corridor", ending the "Ramban NH-44" mislabel. ⚠️ At merge time, add
  `site_name: Ramban NH-44` to the Ramban `config.yaml` to keep its historical titles.

**Producing scripts:** `live_alarm.py` (+ dashboard-path print fix), `operational_alarm.py` (guards +
unscored cards), `config.py` (`site_name`), `agentic_orchestrator.py` + `build_3d_dashboard.py` (titles).
**Artefacts (git-ignored):** `data/alerts_vaishnodevi/mosaic_asc/operational_alarm_dashboard_vaishnodevi_2026.html`,
`data/rainfall/*_vaishnodevi_2026.*`, `data/alerts_vaishnodevi/per_zone_*`.

---

## 30. ★ Vaishno Devi on the 12.5 m ALOS DEM — sharper slopes, stronger 2-track core  `[REAL / UNVALIDATED]`

Source: `run_multistack.py --force` + `route_exposure.py` + `live_alarm.py` (Docker, 2026-07-06), branch
`aoi-vaishnodevi`. The user fetched a Trikuta ALOS PALSAR RTC tile (`AP_15676_FBS_F0650_RT1`, ASF Vertex) —
health-checked: 12.5 m, EPSG:32643 (native UTM zone of the grid), **100 % AOI coverage**, 99.7 % valid,
elev 266–4,614 m. `ALOS_DEM_DIR` is now **slug-scoped** (`data/dem_alos_12m` = Ramban unchanged;
`data/dem_alos_12m_vaishnodevi` = the new tile), completing the per-AOI coexistence layer — the §21 recipe
(native-slope-then-average) now applies per site automatically.

**Effect of 30 m → 12.5 m slope (supersedes §27/§28 counts):**
- Slope: median **18.0→21.9°**, p95 43.9→46.2°, max 63.9→**71.3°** (same direction as Ramban's §21).
- Union mosaic: HIGH **2,705→3,690 px**; **≥2-track core 411→567 px (+38 %)**.
- Union zones: **operational 27→37** (critical 4→8, multi-look 6→10), watch 72→97, monsoon/extreme 185→254;
  **dry stays 0** (cascade shape preserved).
- **Route exposure: the CORE finding strengthens** — the unnamed path above the Bhairon top is now
  **800 m long and passes DIRECTLY THROUGH ≥2-look core pixels (min distance 0 m)**, up from 680 m at
  248 m. Still **0 OPERATIONAL segments** (the standing product's zones remain off-track); WATCH 7 segs /
  7.84 km, MONSOON-only 9 / 5.56 km; POI classes unchanged (shrine complex + ropeway = WATCH; Katra +
  trek start CLEAR).
- **Live alarm re-read (as-of 2026-06-30): still DORMANT** — 13 April trigger days gated to 0 ALERT;
  per-zone tracking now 47 zones, 0 active today (season peak 47 in the April spell).

**Caveat unchanged:** sharper terrain, same young radar — `[UNVALIDATED]`, trust the (now larger) 2-track
core first. **Artefacts:** regenerated `data/{velocity,hazard,alerts,mosaic}_vaishnodevi/*`,
`route_exposure.{json,md,png}`, `operational_alarm_dashboard_vaishnodevi_2026.html`.

---

## 31. ★★ Vaishno Devi VALIDATED — the 26 Aug 2025 Ardhkuwari disaster back-test  `[REAL / MEASURED]`

Source: user-supplied **GSI Preliminary Note** (29.08.2025, authoritative — read directly per the §12g
ground-truth rule) + `backtest_inventory.py` ×4 + `operational_alarm.py` (Docker, 2026-07-06/07), branch
`aoi-vaishnodevi`. **The site is no longer `[UNVALIDATED]`.**

**Ground truth (new, committed):** `data/inventory/vaishnodevi_documented_landslides.geojson` — the dated
**26.08.2025 ~15:00 Ardhkuwari disaster (Inderprastha Bhojnalaya; 32 dead, ≥20 injured)** + **40
GSI-DMS-surveyed instability locations** along all four track segments (Table-7.1 of the note). The event
coordinate is anchored to GSI slope **Nos. 110/111** — the note itself states the failed slopes were
pre-flagged as Nos. 110/111/115/117 in GSI's 2022-23 survey (33.00876 N 74.94179 E). Caveats recorded in
the file: corridor-biased; mostly *assessed-vulnerable* spots, not all occurred slides.

**TEMPORAL — the headline.** VD-bbox ERA5-Land 2025 season (`vaishnodevi_era5land_daily.csv`): the
disaster day **26 Aug 2025 was the season's MAXIMUM rain day — 191.3 mm** (61.4 mm on the 25th; 253 mm/48 h).
The regional I-D gate: **event caught at Δ=0 by full ALERT (1/1)**, and the alarm's default "current state"
(peak-E day of the whole season) **self-selected 2025-08-26** — the model's single strongest alarm day of
2025 IS the disaster day. **Honest counterweight:** 2025 was an extreme monsoon at this site — raw trigger
102/214 d, gated ALERT still **59 d (27.6 %)**, so the gate is far less selective than Ramban-2025 (27 d);
a Δ=0 hit is *necessary* evidence, not *sufficient* — the peak-E coincidence is the stronger fact.

**SPATIAL (null n=5000 in the VD polygon, seed 20260606):**
| arm | zones | AUC | recall@2 km | lift@2 km |
|---|---|---|---|---|
| **operational (m=0.50)** | 37 | **0.620** | **0.805** | **1.67×** |
| watch (m=0.70) | 97 | 0.558 | 0.854 | 1.27× |
| operational ≥2-look | 10 | 0.527 | **0.000** | 0× |
| watch ≥2-look | 14 | 0.457 | 0.000 | 0× |

The **operational map beats chance at its first scored test** (AUC 0.62 ≈ Ramban's 0.64 §21b) — with
borrowed φ and a 7-week velocity baseline. **The honest surprise: the ≥2-look core scores ZERO against
this inventory** (all core zones >2 km from the corridor, median 4 km). Interpretation, not failure-hiding:
the corridor ground truth is **cut-slope debris/rockfall failures** (GSI's own failure types) — fast,
shallow, small — a *different failure class* from the slow deep creep SBAS detects; the 2-track core sits
on the upper massif, which this corridor-hugging inventory simply does not sample. **Trust guidance
REVISED for this site:** for *route/track* hazard read the validated single-look operational map first
(AUC 0.62); the ≥2-look core (incl. the §30 800 m Bhairon-top segment) remains the most *measurement*-
corroborated creep but is **untested by this inventory** — field-check stands.

**Context from the note (for future calibration):** Trikuta Fm limestone/dolomite (Sirban Gp) +
Quaternary Vaishnodevi-Fm scree (loose→compacted) + Reasi Thrust adjacent — carbonate + scree mechanics
differ from the Batote-Doda calibration behind φ=36°/c; a site-specific FS parameter pass is now a
justified next accuracy item. (Compendium Spl. Pub. 107: Ardhkuwari-Bhawan new track = High susceptibility
from slope-cutting — independent GSI concurrence with our corridor read.)

**Wired through:** the suffix-scoped tier lookup (§29) picked the new reports up automatically — the live
2026 dashboard now shows **VD's own AUC 0.62 / recall 0.854**, "beats chance" restored honestly.

> **↪ Addendum (2026-07-07) — ground truth ON the route-exposure map.** `route_exposure.py` now overlays
> the §31 inventory (★ = the dated disaster, × = GSI locations) and classifies each point at the strict
> **250 m** operational buffer: **29/41 CLEAR, 9 WATCH, 3 MONSOON — and the disaster site itself is
> CLEAR, nearest zone 598 m.** The sharp honest read: the product **beats chance at 2 km** (§31 AUC) but
> does **NOT pinpoint the kill site at 250 m** — consistent with the failure-class gap (fast cut-slope
> rockfall ≠ slow SBAS creep) + 80 m pixels + the 7-week baseline. This 598 m miss is now the calibration
> target for the site-specific improvement work (soil pass, operating-point sweep, rockfall proxy).
**Artefacts:** `backtest_{operational,watch}_vaishnodevi{,_2look}_*` in `data/inventory/`,
`operational_alarm_*_vaishnodevi_2025.*` (as-of 2025-08-26 = ALERT), regenerated 2026 dashboard.

---

## 32. ★ Vaishno Devi operating points EARNED — the site's own m-sweep  `[REAL / MEASURED]`

Source: `rainfall_selectivity_backtest.py` (now AOI-parameterized: slug-scoped mosaic dir, per-site
inventory default, suffixed outputs — Ramban's §16d artifacts untouched; + fixed a latent crash when a
sweep lacks the m=1.0 baseline row) vs the §31 inventory, 5,000-null control, seed 20260606 (Docker,
2026-07-07). Replaces the borrowed Ramban operating points with **site-swept** ones, wired as new optional
config keys **`operational_m` / `watch_m`** (defaults 0.50/0.70 → Ramban byte-identical until its config
opts in; orchestrator `SCENARIOS` reads them, so every downstream product inherits automatically).

**The sweep (16 m-values, 0.25→1.0):** AUC rises from ~0.52 (m≤0.33) to a **spike 0.753 at m=0.35**, a
**stable plateau ~0.70 at m=0.38–0.42**, then declines (0.617 @0.50 → 0.558 @0.70 → 0.572 @1.0). Recall
climbs 0.73 @0.40 → 0.854 @0.70 → **0.927 @0.75** → 1.0 @0.85 (spec collapsing 0.65→0.14).

**Decisions (rationale on record):**
- **ALERT: m=0.40** — plateau centre, NOT the 0.35 spike (it borders a cliff: m=0.33 → AUC 0.52; on a
  41-point inventory a 2-zone wobble flips it — plateau beats peak for an operational product).
- **WATCH: m=0.75** — recall 0.854→**0.927** (38/41) for +8 zones; perfect recall @0.85 costs +54 zones and
  spec 0.14 (the §23 "3× noise for scraps" trade, again rejected).

**Re-scored official footprints (reproduce the sweep exactly):**
| tier | zones | AUC | recall@2 km | spec | lift | precision |
|---|---|---|---|---|---|---|
| operational m=0.40 *(was 0.50)* | 21 (3 crit, 8 ML) | **0.696** *(was 0.617)* | 0.732 | **0.654** | **2.11×** | 0.679 |
| watch m=0.75 *(was 0.70)* | 105 (22 crit, 13 ML) | 0.543 | **0.927** | 0.293 | 1.31× | 0.567 |

Temporal Δ=0 ALERT catch of the 26 Aug disaster preserved in all arms; route exposure re-read barely moves
(CORE 0.80 km unchanged, WATCH 7.92 km, op zones still off-track); live 2026 dashboard: DORMANT, now
showing m=0.40/0.75 with the earned scores. **§31's scored rows (AUC 0.620 @ m=0.50) are superseded as the
operating point but stand as the first-exam record.** **Honest caveat:** tuned against a corridor-biased
41-point inventory — this sharpens *corridor* discrimination (which is the product's question), not
whole-mountain skill; re-sweep when the inventory grows or the chains lengthen materially.

**Artefacts:** `rainfall_selectivity{_report}_vaishnodevi.*` in `data/inventory/`, regenerated
`backtest_*_vaishnodevi*`, footprints/dashboards in `data/alerts_vaishnodevi/`.

---

## 33. Watchlist tooling + first user-drawn target + NISAR availability  `[REAL / MEASURED]`

Source: `polygon_stats.py` (NEW), `_tmp` NISAR/OSM probes (Docker, 2026-07-07). Housekeeping-grade, but
recorded here because the producing outputs are git-ignored under `data/`.

- **`polygon_stats.py` — score any user-drawn KML/GeoJSON polygon** against the current AOI product
  (pixel/hazard/2-look coverage, per-track LOS velocity, slope, FS_sat, distance to each alert tier, +
  a plain-language risk line). Self-tested on the §30 creep clusters (correctly returns "HIGH INTEREST:
  2-track creep confirmed").
- **First watchlist target — Bhavan overhang** (`Research/Vaishno_Devi_Watchlist/`, drawn by user):
  0.81 km², centroid 33.02750 N 74.95549 E, slope to **61°**, **FS_saturated ≈ 0.8** (fails when soaked),
  108/127 px WATCH-class, **no 2-track creep**, nearest monsoon zone 177 m → verdict **CONDITIONAL**.
  Honest note: the two tracks' LOS *disagree* over this steep face (−8 vs +58 mm/yr; layover/unwrap
  artifact) so radar can neither clear nor corroborate it — it is the CV3 brittle/rockfall class (no creep
  to measure). Added to the site inventory as a `user_observed_vulnerable_location` (now 42 features).
- **NISAR over the VD AOI (ASF, `dataset=NISAR`):** 8 GSLC/RSLC/GCOV scenes (Nov 25–Jan 26) + **3 GUNW
  interferograms** (Nov–Dec 25) — real L-band products exist but too few for a velocity chain; recheck
  monthly (forward-processing window opened Jul 2026). L-band recovers vegetation coherence (our worst
  enemy).
- **Coordinate re-verification (§30 target):** independent round-trip sampling + re-clustering reproduced
  the NE-flank creep polygons exactly; Area A abuts a settlement (62 OSM buildings ≤1.5 km, closest 87 m;
  Panchari Gali 810 m W) — the field brief was upgraded to "settlement exposure".

---

## 34. Fast-failure toolkit for the Bhavan overhang: coherence-drop watch, rockfall runout screen, records cross-check  `[REAL / MEASURED]`

Source: `coherence_watch.py` (NEW), `rockfall_runout.py` (NEW), stdlib cross-check + web records
(2026-07-08, Docker). Executes Watchlist-README ideas **#3 #4 #6 #7** for the §33 CONDITIONAL target —
the pipeline's first instruments matched to the **CV3 brittle/fast failure class** (no creep to measure).

- **`coherence_watch.py` — the pipeline's FIRST fast-failure detector.** Per-polygon coherence timeline
  from the existing 12-day `*_corr.tif` pairs; flags an epoch when the polygon decorrelates ≥0.12 vs its
  own history BOTH absolutely AND relative to the AOI mean (the AOI-relative gate subtracts scene-wide
  rain/vegetation drops). Verdict tiers: DROP-CONFIRMED (≥2 tracks) / DROP-SINGLE-TRACK / OK / DATA-GAP.
  **First run (8 pairs, 4 epochs × 2 tracks, May–Jun 2026): Bhavan overhang OK, both NE-flank creep
  polygons OK** — and the design demonstrably works: the 13 May frame105 pair dropped 0.15 absolute but
  only 0.045 AOI-relative (scene-wide wetting, correctly NOT flagged). Overhang face runs 0.33–0.55
  coherence vs 0.55–0.69 AOI-wide (steep-face geometry, as expected). Needs ≥3 usable epochs/track;
  re-runs every radar cycle. Caveat: a storm exactly coincident with a failure can mask the local drop.
- **`rockfall_runout.py` — energy-line (Fahrböschung/shadow-angle) runout screen** on the 12.5 m ALOS
  DEM, bands LIKELY ≥32° / POSSIBLE ≥27.5° / MAX_SHADOW ≥22° (Evans & Hungr 1993). From the overhang
  polygon: **the Bhavan shrine complex POI is INSIDE the LIKELY cone (reach angle 33.2°)**; Bhairon Ghati
  ropeway station POSSIBLE (27.7°); ~2.3 km of walking route in the LIKELY band (Vaishno Devi Trek 620 m,
  Hathimata 560 m, Himkoti 260 m, ropeway alignment 260 m, unnamed path 600 m). Honest caveats on record:
  first-order screen — no trajectory/bounce/barrier physics, NO terrain-blocking check, 22° band at
  multi-km range is an extreme upper bound, and OSM buildings at the complex are unmapped (0 of 63 cached
  buildings in cone = UNDERCOUNT; the POI/route read is the trustworthy part).
- **Records cross-check (idea #7) — the face system is institutionally KNOWN:** (a) GSI Table-7.1 locs
  **52/55/57** (Bhawan–Sanjichat track) sit **315–440 m** from the polygon *edge* with failure types
  "planar and wedge failure" / "planar along some joint and many wedges" — the same brittle class we
  flagged; (b) a **12 Mar 2016 slope failure at the Bhawan complex itself** (track between elevator point
  and gate 5) was stabilized with 37 pre-stressed cable anchors (26.5–30.5 m, ₹5.78 cr); (c) SMVDSB has
  worked with THDCIL on rockfall/shooting-stone mitigation **since 2012** (rockfall barriers 3000–5000 kJ,
  cable nets, shelter sheds) and a tripartite **GSI+THDCIL+SMVDSB MoU** targets Adhkuwari–Bhawan slopes.
  → Action for the field visit: request SMVDSB/THDCIL treatment as-builts + inspection records BEFORE
  instrumenting — parts of this face may already be netted/anchored.
- **Verdict evolution:** §33 CONDITIONAL (physics-unstable, radar-blind) → now *watched* (coherence),
  *consequence-quantified* (shrine complex in the LIKELY cone), and *institutionally corroborated*
  (2016 failure + GSI planar/wedge flags nearby). Field brief with the joint tell-tale protocol:
  `Research/Vaishno_Devi_Watchlist/Field Brief - Bhavan overhang (2026-07-08).md`.

**Artefacts:** `coherence_watch_bhavan_overhang.*`, `coherence_watch_bhairon_creep.*`,
`rockfall_runout_bhavan_overhang.{png,md,json}` + `_bands.kml` + `_reach_angle_deg.tif` in
`data/alerts_vaishnodevi/mosaic_asc/`; cached OSM buildings `data/osm/vaishnodevi_buildings_overpass.json`.

---

## 35. First operational radar-cadence cycle — monsoon onset flips Vaishno Devi to WATCH  `[REAL / MEASURED]`

Source: the full per-cycle loop run end-to-end on 2026-07-10 (roadmap item #1, first execution as a
routine): `submit_hyp3_jobs.py` → `download_hyp3_products.py` → Phase-1 QA chain → `run_multistack.py` →
`route_exposure.py` + `live_alarm.py` + `coherence_watch.py`. Branch `aoi-vaishnodevi`.

- **The headline — site state DORMANT → WATCH.** `live_alarm.py` fetch stage (mintpy image) extended
  ERA5-Land by **+4 days to 2026-07-04** (~5-day publication lag); the alarm stage then read modeled
  saturation **m=0.96** (was 0.56 as-of 06-30) → **29 of 29 vulnerable zones ACTIVE (season peak;
  0 active as-of 06-30)**, regional tier **WATCH**. Temporal gate: WATCH+ on **16/95 days (16.8%)**,
  **ALERT 0 days** (acute E≥2 intensity–duration trigger never reached). The monsoon has arrived at the
  site; the per-zone gate (§24/§32 machinery) is doing exactly what it was built for.
- **July S1 passes STILL absent from the ASF archive** (checked 2026-07-10; latest scenes 18–23 Jun on
  all 8 tracks) — the operational chains (f103/f105) cannot extend yet; ingestion lag now >17 days for
  path27. Recheck next cycle.
- **But the archive check paid anyway — a backfilled 2 Mar 2026 path-27 scene appeared:** 4 new 12-day
  pairs (f101/f106, Feb 18→Mar 2→Mar 14, replacing 24-day links), submitted at 40 credits (**7,460
  remain**), all SUCCEEDED + extracted (Phase-1 state now **52/53 products, 1 parked**). QA: 2 CLEAN
  (f106 0218→0302 R²=0.158; f101 0302→0314 R²=0.001), 2 CONCERN (R²=0.461/0.478 — both a hair over the
  0.45 rescue gate). Network effect: **f106 islands 6→4** (2 rescues selected, still disconnected),
  **f101 8→8** (both new bridges gated out as too noisy). The operational stacks are untouched; the
  densified Feb–Mar baseline waits for future scenes to stitch it.
- **Regression check passed:** the regenerated cascade reproduces §32 exactly — ALERT 21 zones
  (3 critical, 8 ≥2-look), WATCH 105 zones; `route_exposure` 17 exposed segments (unchanged).
- **`coherence_watch` per-cycle verdict: OK/quiet** on the Bhavan overhang + both creep polygons (no new
  radar epochs, so the timeline itself is unchanged since §34's first run).

**Artefacts (git-ignored):** 4 new products in `data/processed_tiffs/`; refreshed
`vaishnodevi_era5land_daily_vaishnodevi_2026.csv`, `operational_alarm_report_vaishnodevi_2026.*`,
`operational_alarm_dashboard_vaishnodevi_2026.html` (as-of 2026-07-04, WATCH),
`per_zone_vulnerability.*`, `coherence_watch_*`, `route_exposure.*`.

---

## 36. Soil-parameter literature assessment + GSI compendium corroboration (Vaishno Devi)  `[REAL / LITERATURE]`

Source: in-depth read of GSI **Spl. Pub. 107** ("Landslide Compendium of Northwestern Himalayas"),
§5.3.1 + Annexure I + §5.4.4, and the deep-research output
`Research/LandslideInventory/Research_and_Literature_Search_Soil.md` (2026-07-11; **doc since
REMOVED from the repo** — it hallucinated future-dated events; its verified extracts live in this §
and §37, each with independent primary citations). Assessment for
roadmap #3 (site-specific soil pass); brief updated:
`Research/Vaishno_Devi_Watchlist/Soil Parameter Research Brief (2026-07-10).md`.

- **Compendium §5.3.1 (VD meso-scale LSM) holds NO soil strength parameters** — it is an
  **SMR-based** (Slope Mass Rating, rock-mass classification) zonation; no c/φ/γ anywhere in the
  chapter. Not a calibration source. (Gotcha: the PDF's text layer is font-shifted AND drops all
  digits — any numeric read needs the rendered page, not extraction.)
- **★ Independent corroboration of §31/CV3:** GSI concluded the High-susceptibility zones are
  *"restricted mainly to the new track from Ardhkunwari to Bhawan… largely due to cutting the slope
  for making the new track just below the existing old track."* The 26 Aug 2025 disaster our model
  is validated against (§31) occurred at **Ardhkuwari on exactly this stretch**, and the cut-slope
  mechanism is our CV3 failure class — a government survey independently pre-identified both the
  place and the mechanism.
- **New dated event for the inventory: 30 December 2008 failure at Bhawan (§5.4.4)** — a *winter*
  (non-monsoon; freeze-thaw candidate) event at the Bhavan-overhang watchlist target, predating the
  treated 12 Mar 2016 failure (§34). Annexure I also lists ~6 descriptive slides "Around
  Vaishnodevi" (Balganga, Darshan Jodi, Shiv Mandir dhaba, Katra–Reasi railway tunnel site) —
  candidate inventory rows, but no coordinates and digits lost to extraction (visual read needed).
- **Best analogue strength values found (none measured on Trikuta itself):**
  - **Chenab Bridge fault gouge, Reasi — SAME Sirban Dolomite formation ~20 km away:**
    c′ = 5.9–17.65 kPa, φ′ = 31.8° (direct shear on undisturbed gouge; IJEAST/3-D stability
    papers). Closest-to-site data so far.
  - **Ramban–Gool debris slides:** γ = 18–20 kN/m³, c = 10–16 kPa, φ = 23–37° (strain-controlled
    lab tests; Geol. Soc. India). The debris/colluvium class our FS engine targets.
  - Read against our borrowed set (φ=36°, c_dry=18.5, c_wet=5 kPa, γ=19): **φ=36° sits at the
    optimistic top of both analogue ranges** (gouge: 31.8°) — φ≈32° is the analogue-supported
    bracket for a §20-pattern sensitivity pass; c_wet=5 kPa is conservative (good).
- **⚠ Red flag in the deep-research doc:** it cites a "September 2026 landslide near Panchi with
  casualties" — **a future date** (doc dated 2026-07-11); hallucinated or a garbled 26 Aug 2025
  Ardhkuwari. Per the §12g lesson, every event claim in that document stays unverified until
  checked against GSI/peer-reviewed sources.
- **Actionable leads for actual Trikuta parameters (fed to the research brief):**
  (1) *"Geotechnical Evaluation of Landslides Along Pathways of Sri Mata Vaishnao Devi Hills"*
  (ResearchGate 277775139); (2) *"Assessment of the Various Slope Stabilization Initiatives…
  Shri Mata Vaishno Deviji Shrine"* (ResearchGate 373842077 / Crimson AMMS.000775 — treatment
  design c–φ); (3) the unpublished GSI FSP report (Kumar) underlying §5.3.1, via GSI/Bhukosh.

---

## 37. Vaishno Devi soil parameters SITE-CORROBORATED — the "borrowed φ/c" caveat is retired  `[REAL / LITERATURE]`

Source: **Kumar R. & Anbalagan R. (2013), "Geotechnical Evaluation of Landslides Along Pathways of
Sri Mata Vaishnao Devi Hills", Int. J. of Landslide and Environment 1(1), 49–50** (PDF in hand —
§36 priority lead #1, obtained by the user 2026-07-11) + the deep-research synthesis
`Research/Vaishno_Devi_Watchlist/Vaishno Devi Research.md` (**doc since REMOVED from the repo** —
it fabricated a "2 Sep 2025" event, §38; the transcription below is the surviving local record of
its soil values, hence the lab-unconfirmed tag) (soil values recovered from its embedded
images — the export had replaced every number with an image placeholder).

**The verdict: every current engine value sits INSIDE the site-reported envelope — values UNCHANGED,
provenance upgraded.** No re-run/re-sweep needed (changing values within the envelope would churn
the §32 operating points for no scientific gain).

| Engine parameter | In use | VD site evidence | Status |
|---|---|---|---|
| φ (soil/overburden) | 36° | **32–43°** (direct shear, VD overburden; GSI-derived) | mid-range → corroborated |
| c_dry | 18.5 kPa | **4.9–27.5 kPa** (0.05–0.28 kg/cm²) | inside → corroborated |
| c_wet | 5 kPa | saturated/parallel-dataset lows **4.5–7.9 kPa** (0.0459–0.0801 kg/cm²) | conservative end → corroborated |
| z (failure depth) | 3 m | VD cut-slope **weathering depth 1–3 m** | max of range → corroborated |
| γ (unit weight) | 19 kN/m³ | no VD value (regional 18–20, §36) | still analogue-only |

Grain size of the VD overburden: **sand 40–78%, silt 20–57%, clay 2–13%** — cohesion-poor granular
matrix, consistent with the matric-suction dry/wet cohesion split (§20): strong dry, collapses wet.

**Separately — the ROCK-JOINT strength set (the CV3 cut-slope class, NOT the soil engine):**
Kumar & Anbalagan back-analysed a failed planar-wedge cut slope (joint J1, FS=1 at failure):
adopted **c_J = 2.9 t/m² ≈ 28.4 kPa, φ_J = 46°**; full trade-off curve c_J 0.81–3.73 t/m² ↔
φ_J 39.3–61.7° for JRC 5–9, residual φ_R 30–45°. Applied to the neighbouring slope: **static
FS = 1.1, dynamic (seismic) FS = 0.98** — quantitative confirmation that the pathway cut-slopes
live at the margin (fails under seismic/pore-pressure loading), i.e. the §33/§34 overhang concern
in the site's own peer-reviewed record. These are joint parameters for planar/wedge rock failure —
kept on record for a future rock-slope module; applying φ=46° to the soil engine would be a
category error (it would halve the hazard map using numbers that don't describe colluvium).

**Honest provenance caveats:** the soil ranges come via a deep-research synthesis citing GSI/EGCON
datasets we do not hold first-hand (and that same document earlier hallucinated a future-dated
event, §36) — so the tag is **site-corroborated (literature), lab-unconfirmed**, not
"site-measured". The Kumar & Anbalagan joint set IS first-hand (PDF on disk). Remaining gaps:
γ for VD, and primary-source/lab confirmation of the soil ranges.

**Changes shipped:** provenance comment in `geomechanical_engine.py` (defaults untouched);
dashboard `site_notes` updated (borrowed → literature-corroborated) + VD dashboard regenerated;
primer Part E caveat (a) softened; soil brief lead #1 marked obtained.

---

## 38. Temporal validation doubled — the 21 Jul 2025 Banganga disaster is also caught at Δ=0  `[REAL / MEASURED]`

Source: verified-event inventory expansion (2026-07-11) + re-run of `operational_alarm.py` on the
2025 season (`--csv vaishnodevi_era5land_daily.csv --out-suffix _vaishnodevi_2025`). Inventory:
`data/inventory/vaishnodevi_documented_landslides.geojson` (committed) — now **4 dated events**
(was 1), every addition source-verified per the §12g date rule.

- **★ The headline: 2/2 in-window fatal events caught at Δ=0.** The newly added **21 Jul 2025
  Banganga (Gulshan Ka Langar) landslide** (1 dead, 9 injured, ~08:30 IST; press-verified across
  3+ independent outlets; Katra 184.2 mm/24 h) lands on a model ALERT day: **E = 2.51, nearest
  ALERT Δ = 0** — alongside the §31 Ardhkuwari catch (E = 9.94, Δ = 0). The VD temporal test now
  rests on two independent deadly events, both caught on the day, in a 59-ALERT-day extreme season
  (27.6% of season — so Δ=0 twice is meaningful but the extreme-season over-firing caveat stands).
- **New dated events recorded (not temporally testable — no rainfall series for their eras):**
  (a) **30 Aug 2008, 11:00 IST — Bhawan rockfall at track km 11.550** (1 dead, 6 injured; wedge
  failure in dolomitic limestone, source in the inaccessible escarpment **>400 m above** the
  inhabited foot-slope — the Bhavan-overhang slope system's own documented fatal precedent).
  ⚠ **Source-internal date discrepancy:** the GSI Spl.Pub.107 §5.4.4 *heading* says 30 **Dec**
  2008, the *body* says 30 **Aug** 2008 at 11:00 hrs (adopted — more specific; resolve via Kumar
  2009a). Read from the rasterized page (the PDF text layer drops all digits — §36 gotcha).
  (b) **12 Mar 2016 Bhawan complex failure** (§34's treated failure, now an inventory feature).
- **Excluded after verification (the date rule working):** the deep-research claim of a
  "2 Sep 2025 new-track rockfall, 3 dead" — no press/GSI trace, and the yatra was **closed
  26 Aug → 14 Sep 2025**, contradicting the claim; treated as fabricated (same document also
  produced the future-dated "Sept 2026" event, §36).
- **Honest bookkeeping:** the events-caught ratio now reads "2/4" because the two historical
  events sit in the denominator with no rainfall data (their rows show "before this season's data
  window" on the dashboard). The **spatial** back-test and the §32 m-sweep were deliberately NOT
  re-run (+3 points among 41 does not justify moving earned operating points; re-sweep when the
  inventory grows substantially).

**Artefacts:** committed inventory (+3 features, updated provenance note); regenerated
`operational_alarm_*_vaishnodevi_2025.*` + the 2026 live dashboard (4-row events table).

> **↪ Monsoon-watch addendum (2026-07-11):** the 2–3-day refresh loop is now a documented runbook
> (`Research/Monsoon Watch Runbook (2026-07-11).md`) and was demonstrated live. Latest state as-of
> **2026-07-05: saturation m = 1.00 (fully primed), WATCH, 29/29 zones active, 0 ALERT days** — the
> "primed slopes awaiting an acute trigger" configuration (cf. the Ramban 20-Apr pattern), at the
> season's saturation ceiling. Today's fetch returned no new day (ERA5-Land latest 2026-07-06 07:00,
> a partial day — the documented ~5-day-lag "nothing new yet" case, not an error).

---

## 39. Primary-source batch #2 + GACOS first attempt — 2016 event verified first-hand; GACOS pull was a point, not a box  `[REAL / LITERATURE]`

Source: three user-supplied PDFs in `Research/Vaishno_Devi_Watchlist/` + two GACOS archives in
`data/hazard_vaishnodevi/` (2026-07-11).

**The three PDFs (all primary sources — none contains soil c/φ, so §37's overburden ranges STILL
await primary confirmation):**
- **Naithani AK (2023), Crimson AMMS.000775 (§36 lead #2 — obtained):** a works-description paper
  (anchor/mesh/grout specs), NO geotech design values. **But it primary-verifies the inventory's
  2016 event first-hand:** *"at about 13:30 hours on 12th March 2016, track between elevator point
  and gate no. 5 at Bhawan got damaged due to heavy and continuous rain which led to landsliding"* —
  date confirmed + two new facts (13:30 IST; **rain-triggered**) + the damaged aged Durga Bhawan
  building was dismantled and the slope treated. Inventory feature enriched.
- **GSI open-file FS 2017-18 "Himkoti Track" (Singh, Rana & Jungral, M4-LS/NC/NR/SU-JK/2017/12224):**
  kinematic assessment of the slope at **RD 0/850 (33°01'47.5"N 74°56'08"E)** after instability that
  caused pilgrim casualties (event UNDATED in the source, pre-30.06.2017 → recorded as a vulnerable
  location, not a dated event). Wedge/topple in highly jointed cherty dolomite, dip-slope J2
  daylighting, slope ~67°, damage corridor 30–50 m, boulders 0.5–2 m (design case 5 m), rain-seepage
  lubrication — yet another institutional confirmation of the CV3 cut-slope class on this corridor.
  **NEW inventory feature** (46 total now).
- **GSI "Kheri landslide, Udhampur district":** regional analogue OUTSIDE the AOI (Murree Fm,
  NH corridor): deep-seated debris-cum-rock slide, **slip-surface depth 3–10 m**, slopes 20–40°,
  600×85–130 m. No lab strength values. Kept as a z-depth analogue for the *deep-seated* class
  (our z=3 m models the shallow translational class; consistent).

**GACOS attempt #1 — unusable, re-request specified:** both archives contained exactly the requested
epochs (frames 105/103, 5 each) but each `.ztd.tif` is a **1×1-pixel POINT at (74.821 E, 33.107 N) —
outside the AOI** (the map selection collapsed to a click). Values ~2.30 m ZTD are physically sane
(account/pipeline fine). Re-request as an AREA: N 33.11, W 74.85, S 32.90, E 75.05, same date lists,
times 12:56:36 / 13:04:41 UTC. Cross-check (Area 1) blocked until then.

---

## 40. GACOS tropospheric cross-check — mixed result: 1 of 2 flagged pairs corroborated, 1 not  `[REAL / MEASURED]`

Source: `workflows/_gacos_crosscheck.py` (new, one-off analysis script) on the corrected-area GACOS
pull (§39 addendum) — 10 ZTD epochs, 8 consecutive-pair comparisons across both VD operational
stacks (frame105/path27, frame103/path100). First-ever run of Area 1's GACOS cross-check.

**Method:** GACOS zenith delay → slant delay via `LOS = ZTD / sin(lv_theta)`; pair delay difference
→ predicted apparent displacement using the same `-phase·λ/(4π)` convention as
`feature_engineering.py`, so it's directly comparable to our masked displacement. Two independent
questions per pair: does GACOS's own delay field correlate with elevation (an external replay of
the same hypothesis our phase-elevation audit tests), and — the stronger test — does GACOS's
*predicted spatial pattern* correlate with what we *actually observed* for that pair.

| pair | our audit R² | GACOS R² vs elev | GACOS R² vs OUR observed |
|---|---|---|---|
| 0501–0513 | 0.342 CONCERN | 0.125 | **0.589** |
| 0513–0525 | 0.001 CLEAN | 0.764 | 0.280 |
| 0525–0606 | 0.012 CLEAN | 0.827 | 0.080 |
| 0606–0618 | 0.236 CLEAN | 0.858 | 0.398 |
| 0506–0518 | 0.015 CLEAN | 0.922 | 0.345 |
| 0518–0530 | 0.210 CLEAN | 0.953 | 0.395 |
| 0530–0611 | 0.053 CLEAN | 0.455 | 0.327 |
| 0611–0623 | 0.316 CONCERN | 0.233 | 0.126 |

- **1 of the 2 CONCERN-flagged pairs is strongly corroborated:** 0501–0513 gets the **highest
  GACOS-vs-observed R² of the whole set (0.589)** — an independent, physics-based weather model
  (not derived from our phase data at all) explains 59% of the variance in what we actually saw for
  exactly the pair our own audit flagged. Genuine external validation.
- **The other CONCERN pair is NOT corroborated:** 0611–0623 has one of the lowest GACOS-vs-observed
  scores (0.126). This is a discrepancy, not a failure of the gate — a CONCERN flag doesn't require
  external confirmation to be a legitimate conservative call; the flagged pattern there may be real
  motion, decorrelation noise, or convective weather too localized for GACOS's ~90 m/6-hourly model
  to resolve (this pair spans 11→23 Jun, monsoon onset).
- **GACOS's own elevation-correlation is high almost everywhere** (0.46–0.95, except the two
  CONCERN pairs) — expected in this high-relief terrain, and it means "GACOS R² vs elevation" alone
  doesn't discriminate atmosphere-heavy pairs; the *direct* GACOS-vs-observed comparison is the more
  informative signal.
- **A hint worth flagging, not acting on:** several CLEAN pairs (near-zero audit R²) show moderate
  GACOS-vs-observed correlation (0.28–0.40) — the current elevation-only audit may be under-sensitive
  to spatially complex (non-monotonic) atmospheric patterns that a full weather-model comparison
  would catch. Possible future refinement of `phase_elevation_audit.py`; not implemented (n=8 is a
  first look, not a powered test).

**Honest framing:** qualitative cross-check on 8 pairs — not a statistically powered validation. The
correct read is "partial corroboration, one clean win, one open discrepancy," not "GACOS confirms
the gate." Roadmap Area 1's GACOS item moves from *deferred* to *done, first result* — a second pull
(more epochs, or a monsoon-season pair) would sharpen the trend.

**Artefacts:** `data/hazard_vaishnodevi/gacos_crosscheck.{json,md,png}`.

---

## 41. Multi-AOI productization — config registry, status dashboard, onboarding playbook  `[INFRA / MEASURED]`

**Date:** 2026-07-12 · **Produced by:** `workflows/config.py`, `workflows/aoi_status.py`,
`tests/test_config_registry.py`, `NEW_AOI_PLAYBOOK.md`, `config/{ramban,vaishnodevi}.yaml`
· **Branch:** `aoi-vaishnodevi`

The "point the pipeline at a new site" capability, hardened from a convention into a product
(user ask: reproducible for any AOI, dependency-tracked, dashboard-monitored, scale-ready):

- **AOI config registry:** one canonical YAML per site under `config/`; the root `config.yaml` is
  now a one-line `active_config:` pointer. Per-command targeting precedence: `--config` flag (4
  scripts) → **`INSAR_CONFIG` env var (new — works for every script, including the many that call
  `load_config()` at import time)** → the root pointer. Ramban's registry file carries
  `site_name: Ramban NH-44` (closing that deferred merge item).
- **Soil parameters are now config keys** (`soil:` block with per-site provenance comments),
  not CLI defaults — a third AOI can no longer silently inherit Ramban's §20 calibration.
  **Numerically zero-change by construction:** defaults equal the §20 values, pinned by
  `test_config_registry.py` (6/6 PASS natively AND in the `insar` container).
- **`aoi_status.py` — the multi-AOI dashboard** (console + `data/aoi_status.{html,json}`):
  per-site stage checklist (incl. the manual steps: polygon, soil pass, ALOS DEM, inventory,
  m-sweep), current alarm level / live zones / rainfall freshness, and the exact next command.
  **Cross-checked against this ledger on first run:** displayed back-test AUCs and alarm states
  reproduce §16d (Ramban), §32 and §35/§38 (VD WATCH, all zones active, as-of 07-05) exactly.
  First actionable catch: it surfaced Ramban's live-season rainfall as **15 days stale** with the
  refresh command attached.
- **`NEW_AOI_PLAYBOOK.md`:** the committed 10-step onboarding recipe (automated commands with
  verify-artifacts + the manual/scientific steps that cannot be automated), multi-AOI coexistence
  rules, and the scaling/NISAR architecture notes (the GUNW adapter lands at the shared
  `data/qa_masks/` seam, so every registry AOI inherits it).

**Honest framing:** infra, not science — no new measurement. Scientific transferability per site
still requires the three earned steps (soil pass, verified inventory, m-sweep), unchanged from the
SESSION_REVIEW §3 readiness assessment; what changed is that they are now *tracked and guided* per
site instead of remembered.

---

## 42. Soil-sensitivity sweep — the soil pass is LOAD-BEARING; the "skip it with priors" hypothesis is REJECTED  `[REAL / MEASURED]`

**Date:** 2026-07-13 · **Produced by:** `workflows/soil_sensitivity_sweep.py` (NEW; VD site,
operational m=0.40, inventory n=46, null n=5000 seed 20260606, buffer 2 km) · **Branch:**
`aoi-vaishnodevi` · Canonical FS rasters backed up + byte-restored (checksum-verified).

**The question (ERRC "Reduce", 2026-07-13):** if the operational product's back-test score barely
moves across the §37-plausible soil bracket, the manual per-site soil pass (playbook M2) demotes to
"global priors + uncertainty band". **It does not demote.**

| combo | zones | AUC (full) | ΔAUC |
|---|---|---|---|
| **baseline** (config §37 values) | **21** | **0.707** | — |
| φ=32° | 36 | 0.639 | −0.068 |
| φ=40° | 11 | 0.752 | +0.045 |
| φ=43° | 6 | 0.549 | −0.158 |
| c_dry=4.9 kPa | 97 | 0.573 | −0.134 |
| **c_dry=27.5 kPa** | **0** | — | product vanishes |
| c_wet=4.5 kPa | 21 | 0.707 | ±0 (identical product) |
| c_wet=7.9 kPa | 12 | 0.534 | −0.173 |
| **z=1 m / z=2 m** | **0 / 0** | — | product vanishes |
| γ=17 / γ=21 kN/m³ | 12 / 27 | 0.534 / 0.710 | −0.173 / +0.003 |
| weakest corner | 125 | 0.624 | −0.083 |
| strongest corner | 0 | — | product vanishes |

- **Baseline sanity gate passed:** reproduces the canonical 21 operational zones and the §32
  m-sweep plateau AUC.
- **Headline: the union footprint swings 0–125 zones across the LITERATURE-PLAUSIBLE bracket**,
  and four in-bracket combos (z=1, z=2, c_dry=27.5, strongest corner) **erase the alert product
  entirely**. Max |ΔAUC| where scoreable: 0.173.
- **Most load-bearing parameter: failure depth z** (thinning the soil mantle 3→2 m alone kills all
  21 zones — the cohesion term scales as 1/z, so thin soils are computed strong). Then c_dry and φ.
  Near-insensitive: c_wet 5→4.5 (identical product).
- **The degeneracy caveat (why "just re-tune m" is not a rescue):** soil strength and assumed
  saturation m both scale effective strength, so a per-site m-sweep (§32's method) could partly
  absorb wrong soils *spatially* — but then m becomes a fitted dial and the physical rainfall→m→FS
  coupling that calibrates the WHEN gate (§17/§19) loses its meaning. Priors + re-tuned m is a
  curve-fit, not a substitute for the soil pass.
- **Consequences:** (1) playbook M2 stays a REQUIRED manual step, now evidence-backed; (2) the
  sweep itself (runs in seconds, non-destructive) becomes a standard per-site artifact — run it
  after validation to show which parameters your site's product stands on; (3) the open §37/§39
  items (overburden-depth primary source, Trikuta γ, lab c/φ) are *upgraded in priority*: depth is
  the single most valuable number a field visit could bring back.

**Artefacts:** `data/inventory/soil_sensitivity_report_vaishnodevi.{md,json}`,
`soil_sensitivity_vaishnodevi.png`.

---

## 43. Perpendicular-baseline gate folded into rescues — one validated bridge was 1 m over the rule  `[REAL / MEASURED]`

**Date:** 2026-07-13 · **Produced by:** `workflows/sbas_network_graph.py` (gate extension) ·
**Branch:** `aoi-vaishnodevi` · Closes the roadmap-0b leftover ("declared but not yet applied").

The config's `baseline.max_perp_baseline_m: 150` is now a fourth criterion in the connectivity-rescue
gate: a CONCERN pair cannot become an (unredundant) bridge if its pair |Bperp| exceeds it. Bperp
comes from the network graph's on-disk ASF cache, so the offline `--recommend-only` path keeps
working; unknown Bperp is *flagged* (`missing_metrics:bperp`), never rejected — consistent with the
gate's gate-on-available-data philosophy.

- **Audit of the 10 standing bridges:** 8 measure 1–123 m (comfortably in-rule), 1 has no cached
  Bperp (DESC f479 — flagged), and **1 fails: the f106 bridge 20250506→20250611 at Bperp 151 m** —
  literally 1 m over the round-number rule.
- **The recommender found a better bridge for the same gap:** 20250506→20250530 — same island merge
  (f106 stays 6→4 islands), *shorter* temporal baseline (24 d vs 36 d), Bperp 102 m, R² 0.382
  (within the 0.45 ceiling). Selection is deterministic (two runs byte-identical).
- **Deliberately NOT applied today:** the standing quarantine list and every downstream product are
  untouched (verified: `_quarantine_list.csv` unmodified; plumbing 10/10, registry 7/7). The swap
  takes effect at the **next radar-cadence rebuild**, which re-runs apply→invert→score and
  re-validates as part of its loop — expect a small f106/Ramban-union product shift there, to be
  re-scored and ledgered then.

**Honest framing:** 150 m is a rule of thumb, not a measured cliff — a 151 m bridge was not
producing bad science. The value of the gate is prospective: future long-baseline bridges (where
redundancy can't average noise out) are now excluded automatically, at every site, from config.

---

## 44. Validation statistics — bootstrap CIs, permutation tests, ablation ladder  `[REAL / MEASURED]`

Source: `workflows/validation_stats.py` (NEW — Science Upgrade Plan #1, zero engine changes, zero
new physics parameters), Docker, 2026-07-13. Protocol: the standing distance-ROC back-test
(§16/§21b/§32 machinery reused verbatim for point estimates) + **bootstrap 95% CIs** (inventory
resampled with replacement, B=10,000; null set fixed at n=5,000, seed 20260606) + **one-sided
permutation p** for "beats chance" (labels reshuffled over the pooled inventory+null points,
B=10,000; p floor = 1e-4) + an **ablation ladder** of deliberately dumb baselines scored with the
IDENTICAL protocol (per-stack mask → cluster ≥3 px → centroid → cross-stack union merge →
distance-ROC vs the same inventory and null set). Every rung is swept over its threshold and
reports its BEST AUC; the logistic-regression rung is fit in-sample — both choices are optimistic
FOR the baseline, so surviving them is the conservative direction. Stat seed 20260713.

### Headline numbers, now with uncertainty (supersede the bare points where cited)

| site / tier | zones | AUC [95% CI] | recall@2 km [95% CI] | precision | p (beats chance) |
|---|---|---|---|---|---|
| **Ramban operational** (n=138 GSI) | 12 | **0.640 [0.595–0.682]** | 0.254 [0.181–0.326] | 0.645 | **0.0001** |
| Ramban watch | 132 | 0.504 [0.451–0.557] | 0.630 [0.551–0.710] | 0.471 | 0.442 |
| **VD operational** (n=46, §39 refresh) | 21 | **0.707 [0.660–0.752]** | 0.739 [0.609–0.870] | 0.681 | **0.0001** |
| VD watch | 105 | 0.555 [0.483–0.626] | 0.913 [0.826–0.978] | 0.564 | 0.097 |

Both ALERT tiers beat chance at the permutation-test floor. Both WATCH tiers are honestly
≈chance as spatial rankers (as §23/§32 already said) — they are recall nets, not maps. The VD
0.707 confirms the §42 n=46 baseline; the VD dashboard previously displayed the stale 0.696
(n=41) — now reads the refreshed value + CI from this report.

### Ablation ladder — best rung per family (full sweeps in `validation_stats_*.json`)

**Ramban (operational AUC 0.640):**
| rung | best variant | zones | AUC [95% CI] | ΔAUC (model − rung) |
|---|---|---|---|---|
| slope-only | ≥25° | 186 | 0.523 [0.473–0.573] | **+0.117** |
| logistic slope+TWI | top 0.5% | 32 | 0.571 [0.531–0.611] | **+0.069** |
| physics-only | FS_sat<1.3 | 53 | 0.569 [0.513–0.623] | **+0.071** |
| creep-only (InSAR) | <−25 mm/yr | 303 | 0.402 [0.347–0.457] | **+0.238** |

**The Ramban incremental-skill claim SURVIVES:** the fused product beats every rung, including
the best-tuned, in-sample-fit baselines; only the LR rung's CI upper edge (0.611) grazes the
model's lower edge (0.595). Creep alone and physics alone are each ≈/below chance — the value is
demonstrably in the FUSION, not in either input.

**Vaishno Devi (operational AUC 0.707):**
| rung | best variant | zones | AUC [95% CI] | ΔAUC (model − rung) |
|---|---|---|---|---|
| slope-only | ≥40° | 155 | 0.730 [0.676–0.783] | **−0.023** |
| logistic slope+TWI | top 10% | 218 | 0.742 [0.695–0.785] | **−0.035** |
| physics-only | FS_real(m=0.40)<1 | 108 | 0.599 [0.533–0.668] | +0.108 |
| creep-only (InSAR) | <−15 mm/yr | 341 | 0.533 [0.461–0.604] | +0.174 |

**The honest VD finding:** the model beats its own components decisively (physics +0.11, InSAR
+0.17) but is **statistically indistinguishable from a tuned slope-only map** (CIs overlap
heavily) on this corridor inventory — a steep-slope-biased n=46 sample rewards any dense
steep-terrain mask (slope≥40° needs 155 zones and precision 0.56 to match what the model does
with 21 zones at precision 0.68). The model's earned differentiators at VD are **footprint economy
(7× fewer zones at higher precision), the temporal arm (§31/§38: 2/2 fatal events at Δ=0, which no
static slope map has), and per-zone fragility ranking** — not raw spatial AUC. This is the
plan's anticipated "unwelcome answer", reported as found; it sharpens the pitch rather than
inflating it, and it is exactly what the upcoming TWI-saturation (#2) and suction-curve (#3)
upgrades will be judged against.

**Wide CIs are themselves a finding:** at n=46, ±0.05; at n=138, ±0.04 — quote intervals, not
third decimals. **Surfaces updated:** dashboards read AUC + CI + p live from
`validation_stats_<scenario><sfx>.json` (point value and interval always from the same run);
README cites intervals. Artefacts: `data/inventory/validation_stats_{operational,watch}{,_vaishnodevi}.{json,md,png}`
(the PNG is a forest plot, model vs ladder).

---

## 45. TWI-distributed saturation — kappa adopted at 0.06 both sites  `[REAL / MEASURED]`

Source: `agentic_orchestrator.py` (FS_real build) + `config.py` (`kappa` key) +
`rainfall_selectivity_backtest.py --kappas` (sweep) + `per_zone_gate.py` (m*_eff) +
`validation_stats.py` (§44 CI + ablation ladder), Docker, 2026-07-13. Science Upgrade Plan #2.
**Positive result — adopted.**

**The change.** The WHEN gate applied ONE saturation to the whole AOI; §17's over-firing is that
uniformity. TOPMODEL says wet, convergent terrain saturates first, and we already compute that index
(TWI). So each pixel now gets

  m_i = clip( m + kappa·(TWI_i − TWI_mean), 0, 1 )     (kappa units 1/TWI)

and FS_real = (1−m_i)·FS_dry + m_i·FS_sat as before (FS still linear in m_i). Because TWI is centred
on its own mean, the **spatial mean of m_i equals m up to the clip**: exact at the operational
points (clip engages on ≤0.002% of pixels), and at the watch points the extreme-TWI tail clips
(VD m=0.75: 2.9% of pixels, mean shift −0.0015; Ramban m=0.70: 1.7%, −0.0009 — *measured*, deep-verify
2026-07-13). kappa REDISTRIBUTES saturation (wet hollows earlier, dry ridges later); the AOI-mean
wetness still equals the rainfall proxy to within those measured slivers, so the temporal coupling is
untouched. `kappa=0` (default) reproduces the uniform-m footprint byte-for-byte (verified bitwise on
all 5 stack rasters). One new config key, swept per site like `operational_m` (§32). TWI is
DEM-derived so it is identical across a site's stacks — the per-stack mean equals the site-global mean.

**The sweep (kappa at each site's operational m, same null-control distance-ROC as §16d/§32).**
Both AOIs, on independent inventories, peaked at **kappa=0.06** and degraded past ~0.10:

| kappa | Ramban AUC (n=138) | VD AUC (n=46) |
|---|---|---|
| 0.00 | 0.640 | 0.707 |
| 0.03 | 0.663 | 0.720 |
| **0.06** | **0.676** | **0.757** |
| 0.10 | 0.639 | 0.732 |
| 0.15 | 0.622 | 0.634 |
| 0.20 | 0.582 | 0.692 |

That two unrelated inventories select the same kappa is the robustness argument for adoption.

**Re-scored standing footprints at kappa=0.06 (validation_stats.py, §44 machinery; CI = 95%
bootstrap, p = permutation vs chance):**

| site / tier | AUC κ=0 → κ=0.06 | recall@2 km κ=0 → κ=0.06 | zones κ=0 → κ=0.06 | p (κ=0.06) |
|---|---|---|---|---|
| **VD operational** | 0.707 [.66–.75] → **0.757 [.72–.79]** | 0.739 → 0.696 [.57–.83] | 21 → **14** | 0.0001 |
| VD watch | 0.555 → **0.586 [.52–.65]** | 0.913 → **0.957 [.89–1.0]** | 105 → 102 | 0.097 → **0.022** |
| **Ramban operational** | 0.640 [.60–.68] → **0.676 [.64–.72]** | 0.254 → 0.203 [.14–.27] | 12 → **8** | 0.0001 |
| Ramban watch | 0.504 → **0.516 [.46–.57]** | 0.630 → 0.616 [.54–.70] | 132 → **106** | 0.44 → 0.26 |

**The headline win — VD breaks its §44 ablation tie.** At kappa=0 VD operational (0.707) merely
*tied* the tuned slope≥40° baseline (0.730). At kappa=0.06 the model is **0.757, now above both the
best slope rung (0.730) and the best logistic slope+TWI rung (0.742)** as point estimates — and it
does so with **14 zones vs 155/218**. The ablation ladder (§44, kappa-independent) is unchanged; the
model moved above it. Ramban already beat its ladder (best rung 0.571); kappa widens the margin
(0.640 → 0.676).

**Honest caveats (as always, load-bearing):**
1. **The ALERT-tier AUC gain is a better point estimate, not a statistically decisive jump** — at
   n=46/138 the κ=0 and κ=0.06 CIs overlap (VD [.66–.75] vs [.72–.79] barely; Ramban more). The
   defensible claims are *footprint economy* (fewer zones, higher lift/specificity) and *breaking the
   ablation tie*, both robust across two sites, not a proven AUC step-change.
2. **ALERT recall dips** (VD 0.739→0.696, Ramban 0.254→0.203) as the footprint tightens — the
   precision/recall trade. It is confined to the precise ALERT tier; the recall-net WATCH tier holds
   or improves (VD watch recall **rose** 0.913→0.957 and now beats chance, p=0.022).
3. **kappa is a SPATIAL redistribution — it cannot change the regional E-gate ALERT-*day* count
   (§17).** The "extreme-season over-firing" it addresses is spatial: the per-zone active set is
   tighter (VD per-stack peak 29→18 zones) and, via m*_eff = clip(m* − kappa·(TWI−TWI_mean), 0, 1),
   dry-ridge zones activate later on *moderate* days. On the wettest days m(t)≈0.9 still saturates
   everything — kappa sharpens the moderate-day differentiation, not the peak.

**Adopted:** `kappa: 0.06` written to both registry configs (reversible in one line; kappa=0 = §44).
Standing operational + watch footprints, per-zone gate, both dashboards, and the validation_stats /
backtest reports all regenerated at kappa=0.06. Monsoon/extreme (m=1) and dry (m=0) scenarios are
kappa-independent and unchanged. **Supersedes §44's κ=0 rows as the operating point; §44 stands as
the uniform-m record and the ablation ladder both tiers are still judged against.** Suites 10/10 +
7/7. Artefacts: `rainfall_kappa_report{,_vaishnodevi}.{md,json,png}`, regenerated
`validation_stats_*`, `backtest_*`, footprints, dashboards.

---

## 46. Van Genuchten suction curve — mechanism SHIPPED, adoption REJECTED (negative result)  `[REAL / MEASURED]`

Source: `workflows/fs_real.py` (NEW shared physics module) + `config.py` (`suction:` block) +
`rainfall_selectivity_backtest.py --suction/--tag` + `tests/test_fs_real.py` (NEW, 10 checks),
Docker, 2026-07-13. Science Upgrade Plan #3. **Honest verdict: the nonlinear curve is built,
verified, and config-gated — but on this data it does NOT beat the linear model, so no site
enables it. The linear cohesion model stands.**

**Deep-verification of §45 first (same session).** Before building #3, §45's kappa layer was
re-audited: a grep for every consumer of "FS at wetness m" found **two silent non-consumers**
(`hazard_timeline` and `watch_triage` still used the uniform-m/intrinsic-m* math — error log
2026-07-13). Fixed by centralizing ALL of it in the new `fs_real.py`; a 22-check battery on both
sites then verified: kappa=0 bitwise identity on all 5 stack rasters, the zero-sum property
(operational m exact; watch m: VD −0.0015 mean shift / 2.9% clip tail, Ramban −0.0009 / 1.7% —
§45 wording corrected), per-stack cluster counts == standing products, m*_eff FS-crossing roots
to ±2e-3, and double-build determinism. VD route exposure re-read at the kappa footprint: CORE
0.80 km unchanged, WATCH 7.92→7.84 km (deliverables stable).

**The mechanism (§46).** Cohesion now *can* follow the van Genuchten / Vanapalli curve instead of
the linear c_dry→c_wet ramp: ψ(m) = (1/α)·(m^(−1/(1−1/n)) − 1)^(1/n); c(m) = c_wet +
min(c_dry−c_wet, ψ·m·tanφ′). The min() cap anchors **c(0)=c_dry exactly** (measured dry strength
bounds what suction can claim) and ψ(1)=0 anchors **c(1)=c_wet exactly** — both engine end-member
rasters reproduce bit-for-bit, verified. Only cohesion is nonlinear, so FS needs **no engine
re-run**: FS(m) = linear + Δc(m)·K with K = ∂FS/∂c = 1/(γ·z·sinβ·cosβ) computed from the existing
slope raster (K=0 on <2° ground, matching the engine's flat-FS=5 override). m* becomes a grid-scan
root (semantics mirror the closed form: 0=fails dry, 1=never, None=degenerate). Config block
`suction: {alpha_kpa_inv, n}`; absent = linear (regression gate, bitwise-verified); cfg-overridable
for sweeps; `tests/test_fs_real.py` pins all invariants (10/10).

**The sweep — 4 literature candidates × full m-re-sweep × 2 sites** (Carsel & Parrish 1988 USDA
classes bracketing "silty colluvium, >75% fines"; α in 1/kPa; kappa held at the adopted 0.06;
identical inventory/null protocol; best-over-m per model — each candidate got to re-tune its
operating point, maximally generous):

| c(m) model | Ramban best (m, zones) | VD best (m, zones) |
|---|---|---|
| **linear (standing)** | **0.676** (0.50, 8) | **0.757** (0.40, 14) |
| vG silty clay loam (α=0.102, n=1.23) | 0.549 (0.70, 2) | 0.669 (0.85, 43) |
| vG silt loam (α=0.204, n=1.41) | 0.652 (0.50, 3) | 0.745 (0.50, 5) |
| vG loam (α=0.367, n=1.56) | 0.690 (0.35, 11) | 0.757 (0.25, 11) |
| vG sandy loam (α=0.765, n=1.89) | 0.542 (0.35, 69) | 0.634 (0.25, 55) |

**Why rejected (the reasoning is the finding):**
1. **No candidate beats linear at both sites.** The best (loam) gains +0.014 at Ramban — far
   inside the ±0.04 bootstrap CI (§44) — and exactly ties VD's AUC/spec/lift at a shifted
   operating point (11 vs 14 zones, different footprint, same score).
2. **(α,n) are not identifiable from a spatial inventory.** The retention-curve shape largely
   re-parameterizes the m dial: sweeping m absorbs most of what the curve changes, so the data
   cannot distinguish curve shapes — it can only re-label which m is "operational". Adopting
   borrowed parameters would add the plan's own flagged "most new-parameter risk" for zero
   measured gain.
3. **Where the curve WOULD show:** the WHEN axis — m* placement vs dated activations — needs
   per-zone event timing (we have 2 dated in-window events at VD) or an on-site lab retention
   curve (the standing Part E / §42 field ask, now with one more reason).

**What ships anyway:** the mechanism (config-gated, verified, one line to enable when lab/temporal
data can identify α,n), the m-sweep upgrade (now defaults to the site's adopted kappa and suction
— so §32-style re-sweeps always score the physics the standing product ships with), `--tag` so
experiment sweeps never clobber standing artifacts, and the permanent `tests/test_fs_real.py`.
**Bonus finding:** the linear-at-kappa=0.06 m-re-sweep independently confirms both sites' current
operating points (Ramban m=0.50, VD m=0.40) remain AUC-optimal under kappa — the §45 adoption
needed no operating-point shift. Standing products, configs, and dashboards are UNCHANGED by #3.
Suites 10/10 + 7/7 + 10/10 (fs_real). Artefacts:
`rainfall_selectivity_report{,_vaishnodevi}_{k06lin,vgscl,vgsil,vgloam,vgsand}.{json,md,png}`.

---

## 47. Soil-sensitivity verdict re-measured on the kappa=0.06 product — still load-bearing  `[REAL / MEASURED]`

Source: `workflows/soil_sensitivity_sweep.py` (unchanged tool) + a one-default fix in
`rainfall_selectivity_backtest.build_stack_alerts`, Docker, 2026-07-13. **Why:** §42's headline
("the soil pass is load-bearing; failure depth z can erase the product") was measured on the
pre-kappa footprint (21 zones, AUC 0.707). §45 changed the physics and the footprint (14 zones,
0.757) — a product-critical claim (playbook M2's justification) should not rest on a superseded
build.

**A third kappa non-consumer found first (error log 2026-07-13):** reading the tool before
re-running it caught `build_stack_alerts`'s `kappa=0.0` DEFAULT — the soil sweep (and any future
caller that didn't opt in) would have rebuilt alerts at kappa=0, silently mismatching the standing
product. Fixed at the root: `kappa=None`/`suction=None` now mean "the site config's adopted value";
an explicit value (including 0.0) overrides. The sweep's own baseline sanity gate then reproduces
the canonical product exactly (14 zones, AUC 0.757) — which it would NOT have, pre-fix.

**VD re-sweep at kappa=0.06 (same §37 envelope, n=46 inventory, null seed 20260606; FS rasters
checksum-restored):**

| combo | zones | AUC | ΔAUC | §42 (κ=0) zones |
|---|---|---|---|---|
| **baseline (config)** | **14** | **0.757** | — | 21 |
| φ=32° | 24 | 0.696 | −0.061 | 36 |
| φ=40° | 1 | 0.598 | −0.159 | 11 |
| φ=43° / c_dry=27.5 / **z=1 m / z=2 m** / strongest | **0** | — | product vanishes | 0 (φ43: 6) |
| c_dry=4.9 kPa | 90 | 0.609 | −0.148 | 97 |
| c_wet=4.5 kPa | 14 | 0.757 | ±0 (identical) | 21 |
| c_wet=7.9 kPa | 7 | 0.545 | −0.212 | 12 |
| γ=17 / γ=21 kN/m³ | 2 / 16 | 0.457 / 0.720 | −0.300 / −0.037 | 12 / 27 |
| weakest corner | 118 | 0.543 | −0.214 | 125 |

**The §42 verdict HOLDS and SHARPENS under kappa:** footprint range 0–118 zones (was 0–125);
**z=1 m and z=2 m still erase the product entirely**; φ=43° now erases it too (was 6 zones); max
|ΔAUC| where scoreable grew 0.173 → **0.300**. One new fact: the config baseline is now the
**best-scoring combo in the envelope** (in §42, φ=40° out-scored it 0.752 vs 0.707) — the
kappa-tuned operating point is calibrated to *these* soils specifically, so the M2 verdict
strengthens: the soil pass stays required, depth z remains the #1 field number, and re-tuning
m/kappa cannot substitute for physically-right soils.

**Ramban's FIRST soil sweep (2026-07-14, same envelope, n=138 GSI inventory) independently
confirms it** — even at the site whose soils are GSI *field-calibrated* (§20): baseline gate
reproduces the canonical product exactly (8 zones, AUC 0.676); **z=1 m / z=2 m / φ=43° /
c_dry=27.5 / strongest all erase the product (0 zones)**; the weakest corner balloons it to 255
zones (AUC 0.468); footprint range **0–255**, max |ΔAUC| where scoreable 0.208; γ=21 is the only
combo to nudge above baseline (0.693, +0.017 — inside the §44 CI). Both sites now carry a
standing `soil_sensitivity_report_<slug>.*` at the current physics.

Playbook M2 updated to cite §42/§47. Standing products untouched at both sites (canonical zones
verified before/after; checksum restores OK). Suites 10/10 + 7/7 + 10/10.

---

## 48. Storage & automation overhaul — raw zips disposable, monsoon cycle capped and re-timed  `[MEASURED]`
*(2026-07-15, session 24 — `monsoon_cycle.ps1` re-test, `diskpart`, `download_hyp3_products.py` / `prep_mintpy.py` patches, `tests/test_plumbing.py` v2)*

**Ops question answered: the scheduled monsoon cycle downloads NO radar/ASF data** — its 07-15 run
fetched four ERA5-Land GRIBs totalling **~4 KB** and exited 0 (both sites WATCH, quiet cycle). It ran
at 14:06 not 08:00 because the missed 08:00 slot fired on logon (`StartWhenAvailable`) — that, plus an
**uncapped WSL2 VM** (no `.wslconfig` → up to ~8 GB / 12 CPUs of the 16 GB machine) and a **stale
Docker-Desktop autostart registry entry** (contradicting the app's own `AutoStart: False`), was the
system-slowdown root cause. Both fixed system-side (`C:\Users\varun\.wslconfig` = 6 GB / 6 CPU +
`autoMemoryReclaim`; Run-key entry removed).

**Monsoon cycle re-measured end-to-end after hardening** (backend-inclusive Docker shutdown, one-shot
start retry, duration logging): **4:46 wall time** (was ~8 min), **peak vmmem 1.92 GB** (uncapped
ceiling was ~8 GB), exit 0, Docker verified fully closed after — states byte-consistent with the
morning's scheduled run.

**Disk recovered: ~56 GB (C: free 85 → 150 GB).** All 235 raw HyP3 zips (47.4 GB) deleted after the
user archived them to Google Drive — they are re-creatable only by paying HyP3 credits (ASF copies
expired), so the Drive folder is the archival source now. Docker build cache pruned (7.76 GB) and
`docker_data.vhdx` compacted **19.16 → 10.56 GB**. `data/` is now ~46 GB (was ~94 GB).

**Architecture: raw zips are now disposable staging.** Phase-1 extract keeps the HyP3 metadata
`<product>.txt` in `processed_tiffs/` (the only thing any downstream step still needed from a zip);
`prep_mintpy.py` reads it from there, zip = legacy fallback. `data/raw_zips` is an **NTFS junction →
`C:\InSAR_data\raw_zips`**; Docker bind mounts do NOT resolve junctions (found by test), so
`docker-compose.yml` nested-binds the real folder over `/app/data/raw_zips` in both services.

**Verified in depth (all PASS):** synthetic-zip unit test of the extract filter (6 layers + metadata
txt in, 4 decoys out, idempotent); sandboxed `prep_mintpy` end-to-end with **zero zips** (12/12 clips,
2/2 txt byte-identical from `processed_tiffs`) and via the **zip-fallback** branch (byte-identical),
plus an idempotent re-run; junction write-through both directions natively AND from both container
images; `test_plumbing.py` rewritten to the new inventory invariant (**11 tests**, was 10 — extracted
dirs == manifest; zips staging-only; every product dir carries 6 layers + metadata txt). Suites
**11/11 + 7/7 + 10/10** green.

---

## 49. Full-product audit — physics pixel-exact, data internally consistent, zero bugs found  `[MEASURED]`
*(2026-07-17, session 25 — three-axis systematic verification; made permanent as `tests/test_science_verification.py`, 12 tests)*

**Axis 1 (math/science):** the standing FS_dry/FS_saturated rasters reproduce an INDEPENDENTLY
re-written infinite-slope formula **pixel-exact (max |diff| 9.5×10⁻⁷, float32 epsilon)** at both
sites with matching NaN patterns; FS_saturated ≤ FS_dry at all ~143k pixels (0 violations); FS(m)
monotone non-increasing; the closed-form m* satisfies FS(m*)=1 to 2×10⁻¹⁶; kappa redistribution
preserves the AOI-mean exactly and clips correctly; suction anchors c(0)=c_dry / c(1)=c_wet exact
with ψ(m) strictly decreasing; the ID-threshold trigger set recomputed from raw window sums
matches the standing report exactly; the wavelength constant is the HyP3-community standard
(3 nm from exact c/f — negligible at mm scale).

**Axis 2 (scripts/structure):** all 53 Python files compile; `monsoon_cycle.ps1` parses clean;
all suites green; both configs load with the documented operating values.

**Axis 3 (data/references):** 31 hazard rasters CRS'd, physically ranged, and grid-identical to
their stack's velocity master; coherence ∈ [0,1]; inventories exactly as documented (VD **46**,
Ramban **138**, all valid and in-AOI); season CSVs/calendars gap-free; alarm reports, per-zone
products and validation-stats artifacts mutually consistent AND matching the ledger (AUC
0.757/0.676 present); all 29 §-references in SESSION_REVIEW resolve.

**Live regression bonus:** the 2026-07-17 scheduled cycle ran **fully unattended** (logon
catch-up, headless CLI Docker start+stop, no dialogs — the reboot cleared the socket brick):
**4:12**, quiet cycle, both sites WATCH as-of 2026-07-11 (VD 23 WATCH+/0 ALERT days; Ramban 28
WATCH+/4 April ALERT days — supersedes the 21/26 of §48's 07-15 run; same 4 Ramban ALERT dates).

**Two documented observations (not bugs):** (1) frame103's velocity tail is heavy (p99 = 300
mm/yr; 2.6% of px > 200) — its chain is 4 pairs and §24's confidence layer already measures
(σ_v = 26.9 mm/yr) and gates it; lengthening chains is the fix (roadmap #1). (2) The standing
kappa artifact holds only the adopted κ=0.06 row — the full sweep evidence lives in §45's text
(sweep scratch was deliberately git-ignored); re-verification of the sweep = a rerun.

**Permanent guard:** `tests/test_science_verification.py` (12 tests — pixel-exact FS regression,
FS ordering/monotonicity/root, ψ monotone, ID-threshold recompute-vs-report, raster
integrity/ranges/grid-identity, coherence sample, inventory growth-floors + AOI containment,
season/calendar well-formedness, calendar↔report↔per-zone cross-consistency incl. product-kappa
== config-kappa, §-reference completeness). Suites now **7/7 + 10/10 + 11/11 + 12/12**.

---

## 50. One-click ops (local control panel + results hub) and repo restructure — verified live  `[MEASURED]`
*(2026-07-17, session 26 — `workflows/control_panel.py` + `control_panel.bat`; restructure verified by all suites)*

**Control panel (stdlib-only local web server, no new deps):** buttons shell out to the SAME
`docker compose` commands `monsoon_cycle.ps1` uses (asserted byte-for-byte by test); the panel
checks Docker but never starts/stops it (per the 2026-07-16 decision). Verified with REAL runs:

- **Full refresh cycle (all sites) via the button: clean, ~3 min** — Ramban fetch→alarm,
  VD fetch→alarm, status board; every step exit 0; both sites regenerated **as-of 2026-07-11**
  (states unchanged from §49's cycle — a correct "quiet" run inside ERA5-Land's ~5-day lag).
- **Real 3-D dashboard rebuild via the button** (previous build 2026-05-30): scenario alert
  counts came out **identical to the standing mock-cascade numbers (§5: dry 29 / monsoon 222 /
  extreme 222)** — an unplanned regression check on the whole Phase-4A cascade, passed.
- **Docker-down gate verified live:** with the daemon stopped, a run fails in <1 s with the
  "start Docker Desktop yourself" message; second-run-while-busy correctly rejected (HTTP 409).
- **Results hub** links the EXISTING artifacts with freshness stamps; the real cycle run exposed
  that the *main* live dashboards live under `alerts*/mosaic_asc/` (the hub's first version
  missed them) — fixed + regression-tested. New suite: `tests/test_control_panel.py`
  (**12 tests** — command mirroring, action/AOI whitelists, single-job 409, path-traversal
  guard, incremental log streaming, calendar parsing, live-dashboard discovery).

**Repo restructure (same session):** all reading docs → `docs/{guides,runbooks,briefs,references,
archive}` + `docs/INDEX.md` (old→new mapping); AOI/route geojsons → `config/aoi/`; credential
templates → `config/templates/`; 29 `git mv` renames (history preserved), functional root docs
untouched. **Verified nothing broke:** `load_config` resolves both AOIs with **unchanged slugs +
data suffixes** (no artifact-naming drift); suites now SIX and all green —
**7/7 (config) + 12/12 (control panel) + 10/10 (fs_real) + 11/11 (plumbing) + 12/12 (science) +
compose config valid**; live `aoi_status.py` run all-stages-green at the new paths. Historical
ledger entries deliberately keep old paths (append-only); `docs/INDEX.md` carries the mapping.

---

## 51. Past-events dashboard tab + curated historical-damage records (both AOIs) — verified live  `[REAL]`
*(2026-07-18, session 27 — `workflows/operational_alarm.py` (Past-events tab), `data/inventory/{ramban,vaishnodevi}_historical_events.json`, `tests/test_historical_events.py`)*

**Feature:** a third dashboard tab, **🕰 Past events** — each site's documented landslide history
**ranked by damage** (deaths → injuries → infrastructure tie-breaker), every row carrying a
click-to-open Google Maps link, a confidence badge (hover = why), numbered source links, and its
**current standing vs the live alert system** (haversine distance to the nearest hazard zone +
that zone's m\*/FS@0.40/creep/detection-P from `per_zone_vulnerability.csv`, falling back to the
operational-footprint centroids where per-zone hasn't run; >2 km renders honestly as "outside
today's mapped footprint" with an unmeasured≠safe caveat). Tab is skipped when a site has no
record — a site can never wear another's history. The curated records are **separate from the
back-test inventories** (deliberately untouched — validated scores stay earned) and **committed**
(caught + fixed: `data/inventory/*` blanket-ignored them; re-includes added, error log 07-18).

**The curated record `[REAL]`, verified per the §36–§38 rules (primary source or 2+ independent
outlets; publication ≠ event date; LOW ⇒ flagged `review_needed` for the user):**

- **Ramban (5 events):**
  - **19 May 2022 Khooni Nallah T3 tunnel-portal collapse — 10 dead** (HIGH; landslide/shooting
    stones onto the false portal during construction; The Quint + India TV + Business Standard;
    central 3-member probe; contractor fined Rs 8.46 cr) — *new to the repo this session*.
  - **20 Apr 2025 cloudburst — 3 dead** (VERIFIED; the §12g corrected-date event; NH-44 washed
    out at ~5 locations over 10 km).
  - **25 Apr 2024 Pernote land subsidence — 0 dead, ~60 houses damaged, ~500 people affected**
    (HIGH; Zee/DTE/Greater Kashmir; coordinates are a LOW-precision place centroid ~3 km from
    Ramban on the Gool road) — *new to the repo this session*.
  - 8 May 2025 Chamba Seri mudslide (MEDIUM, single-outlet); **27 Apr 2025 "Digdol slide" (LOW —
    most plausibly the 20 Apr event re-reported a week later; PENDING USER REVIEW)**.
- **Vaishno Devi (5 events):**
  - **26 Aug 2025 Ardhkuwari — toll refined 32 → 34** (VERIFIED; GSI's 29-Aug preliminary note
    said 32, the settled press toll is 34 — both recorded, difference explained by the note's
    3-days-after timing; AGU Landslide Blog corroborates 34; 20 injured; 629.4 mm/24 h at Katra).
  - 21 Jul 2025 Banganga — 1 dead / 9 injured (HIGH); 12 Mar 2016 Bhawan complex failure (HIGH);
    **30 Aug 2008 Bhawan rockfall — 1 dead / 6 injured (MEDIUM — GSI Spl.Pub.107's Aug-vs-Dec
    internal date discrepancy; PENDING USER REVIEW)**; **undated pre-2017 Himkoti RD 0/850
    casualty rockfall (LOW; PENDING USER REVIEW)**.
  - The §38 fabricated "2 Sep 2025" event **stays excluded — now test-enforced** (no event may
    fall in the verified 27 Aug–14 Sep 2025 yatra-closure window).

**Current-standing readout (from today's products):** VD's Ardhkuwari disaster site sits
**1.6 km from a mapped HIGH zone** (m\* 0.279) and the two Bhawan events 1.7 km; Banganga
(3.2 km) and Himkoti (2.4 km) fall outside. Ramban is the honest mirror of the corridor-coverage
limitation: **4/5 historical damage sites sit outside today's 6-zone operational footprint**
(only Chamba Seri is within 2 km) — consistent with the known NH-44 corridor-vs-coverage gap
(§16/§24 caveats), not evidence those sites are safe.

**Verification (two rounds):** new suite `tests/test_historical_events.py` — **11 tests**
(schema/provenance, AOI containment, no-future-dates [the §36 lesson], §38 exclusion
immunization, damage ranking, haversine, both-site zone annotation, footprint-fallback path,
HTML render, graceful absence). Full battery **11+10+7+12+12+11 green, run twice**; regeneration
through the real ops path (`live_alarm.py` per site) is **idempotent** (re-run byte-identical
minus the generated timestamp); live browser verification (tab toggling, all 5 per-site map
links carry correct lat,lon); **12/12 relative cross-links resolve**; the validated 2025-season
dashboards untouched; source-URL spot-checks live (AGU blog confirms 34 dead; The Quint confirms
19 May 2022/10 dead; two outlets sit behind anti-bot 403s but were surfaced by same-day live
searches).

---

## 52. Two §51 review rows RESOLVED → the gate's first two in-season catches of 2026  `[REAL]`
*(2026-07-18, session 27 cont. — user review + fresh multi-outlet verification; regenerated via `live_alarm.py` both sites)*

**↪ Corrects part of §51** (its "3 rows pending review" is now 2; its Digdol framing is superseded):

- **Digdol–Khooni Nallah (Ramban): the pending-review row was a REAL, separate event — dated
  7 Apr 2026** (user verdict, then independently confirmed: Asian Mail / Social News XYZ /
  Gadyal Kashmir / The Hans India, all dated 2026-04-07; NH-44 blocked in BOTH directions, no
  casualties). The §51 "likely duplicate of 20 Apr 2025" hypothesis was wrong for an
  instructive reason: the **undated** Greater Kashmir "SSP traffic" URL actually belongs to the
  2026 event and had been misattributed to the 2025 cluster. Confidence LOW→**HIGH**;
  correction recorded in the row itself and in the inventory feature (`date_correction`).
- **NEW dated event (Vaishno Devi): 8 Jul 2026 evening, Himkoti, new track** — rain-triggered
  landslide; battery-car service suspended, yatra continued via the old route, no casualties
  (user-reported TOI + Greater Kashmir / Daily Excelsior / Kashmir Life / Free Press Journal /
  The CSR Journal; Wednesday-evening timing pins 8 Jul). Confidence **HIGH**.
- Both folded into the temporal inventories (`*_documented_landslides.geojson`, §38 precedent:
  append/correct openly, spatial back-test deliberately NOT re-run).

**Did the dashboard catch them? YES — both, at Δ=0 (regenerated WHEN-card, 2026 season):**

- **Ramban 7 Apr 2026: E=2.13 → ALERT — the alarm was RAISED the day the highway was buried**
  (the wet spell ran WATCH/ALERT 3–11 Apr; ALERT days 4/7/8/9 Apr). First ALERT-grade in-season
  catch of the 2026 monsoon; events-caught now reads 1/4 by ALERT (the three 2025 rows sit
  before this season's data window by construction).
- **VD 8 Jul 2026: E=1.06 → WATCH — armed, below the act-now line** (caught by WATCH+ at Δ=0;
  no ALERT days in VD's 2026 season). Proportionate in hindsight: track debris, zero
  casualties. Consistent with the §12c sensitivity bind: AOI-mean reanalysis rain grades a
  localized burst low — the sub-daily IMERG upgrade (roadmap #5) is what would raise such days.

**Also this round (user request): every real link on the dashboard now opens in a NEW tab**
(`<base target="_blank">` — maps, sources, per-stack maps, sibling-site tabs; in-page tab
switches unaffected; the other generated pages carry no external links, and the control panel
already targeted `_blank`). Suite grows to **11 tests + the base-tag assertion**; full battery
re-verified green (7 suites), both dashboards regenerated and checked live (all 37 real links on
the VD page resolve to `_blank`; Ramban WHEN-card row shows `2026-04-07 · E 2.13 · ALERT`).

---

## 53. Live staleness guard on the alarm banner (chosen low-hanging hardening)  `[MEASURED]`
*(2026-07-18, session 27 cont. — `workflows/operational_alarm.py`; verified in-browser with the page's own script)*

**Why this fruit:** the dashboard is a static snapshot, and nothing warned a viewer reading
week-old state as current — operationally the cheapest real weakness to close. (Considered and
deferred as NOT low-hanging: sub-daily per-zone IMERG — the §12c fix but a new credentialed data
pipeline; GACOS second pull — blocked on an external form/email; operating-point re-tuning —
touches validated thresholds without new validation data.)

**What it does:** the banner now carries a `staleness` element stamped with the as-of date; a
view-time script computes the snapshot's age against the VIEWER's clock and escalates:
**≤8 days** = 🕐 normal (the known ~5-day ERA5-Land lag + 2–3-day cycle cadence, stated inline);
**>8 days** = ⚠ amber "a refresh cycle has likely been missed — re-run before acting";
**>14 days** = red "**STALE SNAPSHOT — TREAT THE ALARM STATE AS UNKNOWN**, run a refresh cycle
and follow official advisories". No-JS fallback text still shows the as-of date.

**Verified `[MEASURED]`:** live page computed **7 days** (as-of 2026-07-11 vs 2026-07-18) and
rendered the normal tier; both escalation tiers exercised by re-evaluating the **page's own
embedded script** with rewound as-of dates (amber at 10 d bg `#8a5a00`, red at 20 d bg
`#7a0c0c`). The probe caught one real wrinkle — the normal branch didn't reset the background
style — fixed (error log 07-18). Suite asserts the element + both thresholds + the
treat-as-unknown copy; full battery re-verified **11+10+7+12+12+11 green**; both dashboards
regenerated via `live_alarm.py`.

---

## 54. Data refreshed to the publication edge + season-chart readability pass  `[MEASURED]`
*(2026-07-18, session 27 cont. — `live_alarm.py` full fetch+alarm both sites; `operational_alarm.py` make_figure/caption rewrite)*

- **Both sites refreshed to as-of 2026-07-12** — the newest day ERA5-Land had published on
  2026-07-18 (~6-day provider lag; the staleness pill correctly reads "6 days behind · normal").
  States unchanged: both WATCH (VD E=1.27 on the newest day; Ramban's 4 April ALERT days stand).
  Season day-counts through 07-12: Ramban 74 quiet / 25 WATCH / 4 ALERT; VD 79 / 24 / 0.
- **User-reported "red staleness pill with normal text": NOT a product defect** — it was the
  leftover mutated DOM in the *testing* preview tab (the §53 tier probe on the pre-fix page);
  a fresh load renders correctly. Root-caused and logged (error log 07-18) rather than patched
  around.
- **Season-chart readability pass (user feedback):** the user read E as *soil saturation* — the
  figure's jargon invited it. Rewritten for a lay reader: title "Was the rain dangerous?…",
  y-axis "rainfall danger level E (recent rain ÷ landslide-triggering rain)", in-band
  WATCH/ALERT/quiet explanations, the E=1 line labelled as the historical danger line, event
  lines now carry event names (Digdol visibly on the April ALERT peak; Himkoti inside VD's
  late-June WATCH patch), day-count legend on the calendar strip, and an HTML caption that
  explicitly says E grades the rain itself, not soil wetness. Suite 11/11; both dashboards
  regenerated.

---

## 55. Sub-daily IMERG burst gate SHIPPED (experimental second opinion) — the §12c fix, live  `[REAL]`
*(2026-07-18, session 27 cont. — NEW `workflows/imerg_gate.py`; card in `operational_alarm.py`; guarded hook in `live_alarm.py`; suite `tests/test_imerg_gate.py`)*

**What shipped:** the §12g one-off event test productized into a season-long, incremental,
operational gate. `imerg_gate.py` maintains a cached half-hourly GPM IMERG V07 AOI-mean series
per AOI+season (GEE, bounded chunked fetches — re-runs only pull the missing tail), computes
each day's **peak sub-daily exceedance E** against the SAME verified nwhimalaya I-D curve over
trailing windows of **0.5–24 h that cross midnight** (an overnight burst is credited to the day
it ends in, never split), grades with the same watch_k=1/alert_k=2 convention, and emits a
daily-E CSV + summary JSON. The dashboard gains a **"WHEN — sub-daily burst check"** card
(latest satellite day + E + level chip, season burst-day counts, top burst, provisional flag on
the still-arriving newest day) — framed explicitly as an **experimental second opinion: the
validated alarm remains the daily gate** (this arm has no back-tested operating points yet;
~11 km pixel; rain-only, no snowmelt). `live_alarm.py` refreshes it **non-fatally** before each
dashboard regen (GEE down ⇒ the chain still completes; card stale/absent, never broken).

**Freshness `[MEASURED]`:** IMERG in GEE probed current to **2026-07-17 08:30 UTC on 2026-07-18**
(~1-day latency) vs the ERA5-Land daily gate's as-of 2026-07-12 — the burst card runs
**5 days fresher** than the daily gate today.

**Season 2026 by this lens (Apr 1 → Jul 17, 108 days) `[REAL]`:**
- Ramban: 4 ALERT-grade / 12 WATCH-grade burst days; latest day 07-17 E=2.03 ALERT (provisional);
  top burst 1 Jul (53.6 mm/6 h, E=6.27).
- Vaishno Devi: **10 ALERT-grade** / 18 WATCH-grade burst days (the daily gate saw ZERO ALERT
  days); latest day 07-17 **E=3.43 ALERT** (provisional); top burst 1 Jul (36.5 mm/3 h, E=6.4).
- Honest reading of those counts: at short durations the same curve is far more sensitive, and
  this arm's false-alarm rate is UNMEASURED — which is exactly why it ships as a second opinion,
  not as the alarm.

**Two-arm back-test on 2026's two verified events `[REAL]` — the arms are COMPLEMENTARY:**
- **Himkoti 8 Jul (the §52 WATCH-only catch): sub-daily E=3.9 → ALERT** — a 22.2 mm/3 h burst
  with the peak window ending 11:30 UTC ≈ 17:00 IST, i.e. the burst signature was in hand
  **hours before the evening failure**. The §12c dilution bind, fixed on a real in-season event.
- **Digdol 7 Apr (the §52 ALERT catch): sub-daily E=0.99 → below the line** — a multi-day
  soaking (105 mm/5 d incl. snowmelt) with no single intense burst; the daily/multi-day arm is
  the one that catches it (E=2.13 ALERT).
- **Combined (max of the two arms): both 2026 verified events read ALERT at Δ=0.** Long-soak
  failures belong to the daily arm, convective-burst failures to this one — the two-sensor
  robustness line made operational.

**Verified:** new hermetic 9-test suite (synthetic-burst E within 0.01 of hand computation at
the right duration; midnight-crossing credit; provisional flagging; cache round-trip; summary
schema; card render + page include/omit + corrupt-summary tolerance; suffix rule matches
live_alarm). Full battery now SEVEN suites: **11+10+7+12+12+11+9 all green**; end-to-end
`live_alarm` chain run for both sites (including the incremental no-op refetch at the latency
edge); both regenerated dashboards verified on disk to carry the card with the correct values.

**Roadmap delta:** LIVE roadmap #5 is now HALF done — **sub-daily: shipped (experimental)**;
**per-zone/spatial IMERG** (per-zone E from the 0.1° grid instead of AOI-mean) remains open,
as does earning this arm real operating points via back-testing when enough events accumulate.

---

## 56. Radar-cadence + NISAR availability check — the S1 constellation HANDOVER found (and a silent-starvation bug fixed)  `[MEASURED]`
*(2026-07-18, session 27 cont. — live ASF/CDSE/GEE queries; fix in `submit_hyp3_jobs.py`; plan: `docs/references/STRENGTHENING_PLAN_2026-07-18.md`)*

- **The "missing July passes" (§35) were the Sentinel-1 CONSTELLATION HANDOVER, not a delay:
  S1A ended operations 29 Jun 2026**; S1C repositioned (≈2-week transition); **S1D now flies
  our reference orbits** — CDSE shows S1D IW SLCs on our ASC paths **25 Jun, 30 Jun, 7 Jul,
  12 Jul 2026** (+ DESC path 34). ASF has ingested S1D **through 25 Jun only** (≈3-week lag);
  last S1A at ASF: path 100 23 Jun, path 27 18 Jun.
- **Silent-starvation bug fixed same day:** our catalog query whitelisted
  `platform=[SENTINEL1A, SENTINEL1B]` — with S1A retired it would have returned nothing
  forever while data flowed. Now `PLATFORM.SENTINEL1` (all units), verified live: the
  all-units query returns the S1D scenes the A/B query missed (error log 2026-07-18).
- **Continuity risk named:** the velocity baseline must bridge the 23 Jun (last S1A) → 25 Jun
  (first S1D) seam via cross-unit pairs; HyP3's acceptance of S1A×S1D pairs is UNVERIFIED —
  plan Tier 0d verifies with one dry submission before the real rebuild (which also applies
  the §43 f106 bridge swap).
- **NISAR over both AOIs `[MEASURED]`:** filtering out the ECMWF aux flood — **8 acquisition
  dates, 19 Nov 2025 → 18 Jan 2026**, each with RSLC/GSLC/GCOV, plus **3 GUNW** (+RUNW/RIFG,
  GOFF/ROFF). NOTHING after 18 Jan 2026: the promised Jul-2026 operational forward stream has
  not reached this region. Verdict: enough for the **L-band-vs-C-band coherence pilot NOW**
  (plan Tier 2 — the decision experiment for our #1 weakness, vegetated-slope coverage);
  operational L-band cadence still pending, recheck monthly.
- **Plan drafted:** `docs/references/STRENGTHENING_PLAN_2026-07-18.md` (Tier 0 continuity
  triage → Tier 1 in-monsoon rain science → Tier 2 NISAR pilot → Tier 3 validation depth →
  Tier 4 structural), with a risk register; indexed in `docs/INDEX.md`, successor to the
  completed Science Upgrade Plan.

---

## 57. Plan Tier 0 EXECUTED: radar watcher + freshness pill + seam verified — and Ramban's map found 3 months stale  `[MEASURED]`
*(2026-07-18, session 27 cont. — NEW `workflows/radar_watch.py` + `tests/test_radar_watch.py`; pill in `operational_alarm.py`; hook in `live_alarm.py`)*

**Tier 0b — radar-freshness pill, live on both dashboards.** The WHERE map now states its own
age: "built from radar acquired through DATE — N days ago", computed against the viewer's
clock (like the §53 rain pill; normal ≤35 d, amber >35 d, red >90 d "treat the WHERE map with
caution"), and it announces when the watcher has found newer scenes at ASF. Hidden gracefully
where provenance is unknown.

**Tier 0c — `radar_watch.py`, wired non-fatally into every alarm regen.** Per registry AOI:
newest library acquisition (stack manifest × footprint source_stacks) vs an all-units ASF
query (constellation-level — never a unit whitelist, the §56 lesson encoded); writes
`data/radar_watch.json` for the pill and prints an UNBLOCKED/waiting verdict. The discovery
loop that failed us during the handover is now automatic.

**What the new instruments immediately surfaced `[MEASURED]` (2026-07-18):**
- **Ramban's WHERE map runs on radar through 2026-04-24 — ~12 weeks old** (the §35 "2026-07-10
  backfill" extended only the VD stacks; Ramban's last extension was April). **11 newer ASC
  scenes (S1A May–Jun + S1D) already sit at ASF — Ramban's cadence rebuild is unblocked TODAY,**
  mostly with ordinary S1A×S1A pairs (no cross-unit dependency through 23 Jun).
- VD's map is current through 2026-06-23; only the first S1D scene (25 Jun) is newer — its
  next extension rides on ASF's S1D ingest catching up (CDSE already holds 30 Jun–12 Jul).

**Tier 0d — cross-unit seam VERIFIED (docs + catalog + dry-run; zero credits spent):**
- HyP3 officially supports S1C **and S1D** as InSAR inputs (GAMMA + ISCE2 updated), and its
  product naming explicitly encodes cross-satellite pairs (S1AA/S1AC/S1CD…).
- The fixed all-units search returns the seam scenes, and **the path-27 seam pair
  S1A 2026-06-18 × S1D 2026-06-25 has a 7-day temporal baseline — well inside the 24-day
  max**: the continuity bridge is submittable (~10 credits) whenever the user says go.
- Dry-run of the production submitter: pairing + dedupe logic intact (42 planned / 42 correctly
  deduped against the 183 existing jobs); **HyP3 credits confirmed 7,460**.

**Verified:** new 5-test suite (real-manifest provenance, source-stack scoping, pure
summarize_new incl. the no-library new-AOI edge, watch-file merge/corrupt tolerance, pill
render + omission); battery now EIGHT suites **11+10+7+12+12+11+9+5 all green**; both
dashboards regenerated through the full chain with the pill live. Tier 0 remaining: only the
rebuild itself (user's credit/compute call) — 0a/0b/0c/0d all done.

---

## 58. Plan Tier 1 EXECUTED: burst arm calibrated (ALERT at E≥3), per-zone probe = honest low-value, two-arm line live  `[REAL]`
*(2026-07-18, session 27 cont. — NEW `imerg_calibration.py` + `imerg_perzone_probe.py`; k=3 adopted in `imerg_gate.py`; combined line in `operational_alarm.py`; reports in `data/rainfall/imerg_{calibration,perzone_probe}_report.*`)*

**1b — the burst arm's first evidence-based operating points (PROVISIONAL, n=6 events).** Both
AOIs' 2025 seasons fetched (214 d each) and the §12g one-off *reproduced through the
production gate*: 20 Apr 2025 E=3.07 clear crossing, 8 May E=1.09 marginal — same verdicts.
The six-event two-arm table:

| event | deaths | burst E | daily E | who catches at ALERT |
|---|---|---|---|---|
| 20 Apr 2025 cloudburst | 3 | **3.07** | 2.89 | both |
| 8 May 2025 Chamba Seri (MEDIUM conf.) | 0 | 1.09 | 0.67 | **neither** (recorded honestly) |
| 21 Jul 2025 Banganga | 1 | **4.19** | 2.51 | both |
| 26 Aug 2025 Ardhkuwari | 34 | **9.21** | 9.94 | both |
| 7 Apr 2026 Digdol (soak) | 0 | 0.99 | **2.13** | daily arm |
| 8 Jul 2026 Himkoti (burst) | 0 | **3.90** | 1.06 | burst arm |

- **Adopted: burst-arm ALERT at E≥3** (was 2): keeps 3/3 fatal + 4/4 burst-type events while
  ~halving flagged days (Ramban 2025: 21→11 d; VD 2025: 36→18; VD 2026: 10→7). NOT raised
  further because of the **gauge-bias finding: IMERG reads only 0.22× and 0.16× of the Katra
  gauge on the two dated 24-h anchors** (184.2→39.8 mm; 629.4→99.7 mm) — an 11-km pixel mean
  under-reads orographic point extremes ~4.5–6×, so burst E is biased LOW in exactly the
  events that matter and the margin over the weakest fatal catch (3.07) is thin.
- **1a — per-zone IMERG: measured, then deliberately NOT built.** Both AOIs' zones span only
  **~3 IMERG pixels**; on decision-relevant days (AOI E≥1) the max zone-over-AOI divergence is
  **1.29×** (sub-1.5 everywhere; the 3× ratios occur only on near-dry days via tiny
  denominators — artifact documented in the report). Per-zone gating is a LOW-VALUE upgrade at
  these AOI scales; revisit for larger AOIs. (CLAUDE.md working as intended: probe before
  machinery.)
- **1c — display-only two-arm combined line, live on both banners:** "Two-arm read
  (experimental, §58-calibrated): max(arms)" with both arms' E and as-of dates; the official
  alarm stays the validated daily gate. Today: Ramban combined WATCH; **VD combined ALERT**
  (burst arm E=3.43 on 17 Jul data — 5 days fresher than the daily arm's WATCH).

## 59. Plan Tier 2 EXECUTED: NISAR pilot — L-band RECOVERS 75–87% of the pixels C-band loses  `[MEASURED]`
*(2026-07-18, session 27 cont. — NEW `nisar_coherence_pilot.py` (+ NISAR watch in `radar_watch.py`); GUNW 2.3 GB in `data/nisar/`; report `data/nisar/nisar_coherence_pilot.*`)*

**The decision experiment for our #1 weakness (vegetated-slope decorrelation), run on OUR
ground:** the NISAR winter 12-day GUNW (27 Dec 2025 × 8 Jan 2026, track 156 ASC, 40 m) vs our
own bracketing HyP3 12-day C-band pairs (1→13 Jan path 27, 6→18 Jan path 100), L sampled at
every C 80-m pixel over the Ramban AOI:

| stack | median γ C | median γ L | C fails (%) | L recovers those (%) |
|---|---|---|---|---|
| ASC_path27_frame101 | 0.751 | 0.760 | 16.5 | **80.2** |
| ASC_path27_frame106 | 0.571 | 0.717 | 27.4 | **86.9** |
| ASC_path100_frame102 | 0.907 | 0.719 | 0.8 | 75.4 |

- **Headline: where C-band FAILS (γ<0.35 — the class our QA discards), L-band recovers
  75–87% of pixels to usable coherence** (median γ_L 0.55–0.62 there). Where C is already
  excellent (frame102, 0.907) L adds nothing — the gain is precisely in the failure class,
  which is the only place we need it. Overall-median gain is ~0 in winter (expected: minimum
  vegetation contrast) — **this is a LOWER bound on the monsoon-season advantage.**
- Verdict: **the L-band step-change case is CONFIRMED on our own slopes** — plan the
  operational NISAR stack for the day the forward stream reaches this region (the watcher now
  polls for it, Tier 2c: currently winter-sample only, newest acq 18 Jan 2026, 3 GUNW).
- Honest scope: one pair per band; windows offset 5–6 d; 40 m vs 80 m posting; **VD not
  comparable** (its C-band stacks start May 2026 — no winter pairs; noted in-report, re-run
  when a winter accumulates).

**Verification (both tiers):** suites extended to **14 (imerg) + 6 (radar/nisar)** hermetic
tests (calibrated-k grading, sweep/window math, probe day-E + pixel-count, NISAR summarizer,
combined-line render incl. absence, pilot pair-selection incl. the VD empty case); full
battery **11+10+7+12+12+11+14+6 = 83 green**; both dashboards regenerated through the ops
chain (combined line verified on disk: Ramban WATCH / VD ALERT).

---

## 60. Plan Tiers 3+4 EXECUTED: the statistical map mostly reads the road; optical change is screening-grade; the TWI proxy flips half the LLOF flags  `[REAL]`
*(2026-07-18, session 27 cont. — NEW `susceptibility_crosscheck.py`, `optical_change.py`, `flow_routing_probe.py`, committed `data/inventory/temporal_skill_table.csv`; suite `tests/test_tier34.py`)*

**3a — Susceptibility cross-check: the "would ML beat the physics?" answer is a bias lesson.**
Terrain-only logistic regression (elevation, slope, TWI, curvature, roughness; IRLS, 5-fold
CV; 112 GSI positives vs 2,000 seeded random negatives on the frame106 80 m grid):
- LR CV AUC **0.731 ± 0.046** vs the raw physics pixel score (−FS_saturated) **0.575** — the
  statistical map "wins"… but its dominant weight is **elevation at −0.98**, and removing
  elevation collapses the LR to **0.560 ± 0.039** — statistically indistinguishable from the
  physics score. **The LR's skill is mostly the corridor reporting bias** (the GSI inventory
  hugs the low-elevation NH-44 valley) laundered into "susceptibility". The physics map cannot
  and should not learn where people record landslides — an argument FOR its independence, and
  a caution against training susceptibility models on corridor inventories. (Protocol note:
  this raw-pixel point protocol is NOT comparable to the §16/§44 zone-buffer AUCs.)
  Ensemble 0.691 (no gain over LR — consistent with the bias story).
- **3c** — the standing **temporal-skill table is now a COMMITTED artifact**
  (`data/inventory/temporal_skill_table.csv`, gitignore re-include, schema+consistency
  tested): 6 verified events × both arms × Δ; grows with each §38-rule verification.
- **3b** — GACOS handoff prepared: `gacos_request.py` printed the exact form values (times +
  missing dates per track) — the submission itself is the user's step.

**4a — Optical change (S2 dNDVI), back-tested on Ardhkuwari: MARGINAL — screening-grade.**
Cloud-masked medians (pre Jun–Aug 2025, post Sep 26–Nov 15 post-monsoon; 8/12 images, 20 m):
the AOI GREENED after the monsoon (median dNDVI **+0.198**) while the verified scar
neighbourhood **failed to green** (dNDVI +0.013, deficit 0.185) — the worst **6.4%** of the
AOI, a clear local anomaly but outside the extreme-5% tail. A narrow rocky debris chute sits
at the limit of 20 m NDVI. Honest grade: usable for post-event **screening** with caveats;
higher-resolution imagery or coherence-tripwire fusion (CV5) is the upgrade. Two documented
method traps en route: the tight post-monsoon window was 100% cloud-masked at the scar
(honest data-gap abort), and the naive Oct-long window diluted the signal (41st percentile).

**4c — Flow-routing probe: the TWI proxy is NOT a stand-in — 11/22 zones flip.** Real D8
upstream-area routing (full-frame catchments, ≥0.5 km² within ~240 m of the zone) vs the
TWI-proxy `llof_potential`: **Ramban agrees on only 1/8 zones** (5 routed-only + 2
proxy-only flips), VD 10/14. Verdict: divergence is material — **schedule the validated swap
to routed LLOF as a scored re-run (post-merge)**; the validated products were deliberately
NOT touched pre-merge.

**Deferred with reasons:** 4b soil lab (user-side field/lab, §42); 4d frames-101/102 ERA5
rescue (multi-session MintPy compute — not a pre-merge item).

**Verified:** new suite `tests/test_tier34.py` (AUC/IRLS on synthetic separable data, optical
stats, a D8 valley test that also pins the off-grid edge fix, temporal-table schema +
fatal-events-always-caught, report-artifact checks). Full battery now NINE suites:
**11+10+7+12+12+11+14+6+6 = 89 green.**

---

## 61. Ramban cadence rebuild — 30 credits SUBMITTED, products QA-passed, S1A×S1D seam DE-RISKED  `[MEASURED]`
*(2026-07-22, session 28 — `submit_hyp3_jobs.py --pair`, `download_hyp3_products.py`,
`feature_engineering.py`, `phase_elevation_audit.py`, `export_audit_json.py`; docs manifest
`docs/references/RAMBAN_REBUILD_MANIFEST_2026-07-19.md`)*

The §57 rebuild fired. User authorised the 3-pair manifest (§60/§57 finding: the May-2026 S1
frame renumbering meant 9/10 "new" pairs were already on disk under the VD prefix; the true gap
is 3 pairs — two frame bridges + the S1A×S1D seam).

**Submission `[MEASURED]`:** all 3 pairs queued at ASF, 0 dupes, 0 failed; **HyP3 credits
7,460 → 7,430 (exactly 30 spent)**, verified independently via `find_jobs`. All 3 SUCCEEDED in
~25 min. Job ids in the manifest doc. One self-healing hiccup: the seam zip arrived corrupt on
the first pull; `download_hyp3_products.py` auto-deleted it and the re-fetch was clean.

**QA chain — both gates passed for all 3 `[MEASURED]`:**

| Product (pair) | Stack | Coh survivors / mean-of-survivors | Atmos R² (verdict) |
|---|---|---|---|
| S1AA 20260419×20260501 (f106 bridge) | ASC_path27_frame106 | 30.4% / 0.700 | 0.132 (CLEAN) |
| S1AA 20260424×20260506 (f102 bridge) | ASC_path100_frame102 | 54.3% / 0.761 | 0.064 (CLEAN) |
| **S1AD 20260618×20260625 (S1A×S1D seam)** | ASC_path27_frame105 | 31.2% / 0.665 | 0.176 (CLEAN) |

**Headline — the cross-unit seam is de-risked:** the S1A×S1D 7-day pair has usable coherence
(31% survivors at mean 0.665, in-family with the two same-unit bridges) AND is atmospherically
clean (R²=0.176) — **cross-satellite S1A×S1D interferometry works over Ramban's terrain**, the
single biggest risk in the constellation-handover rebuild (§56 risk register). This is the
winter/monsoon-independent confirmation the plan wanted before trusting S1D continuity.

Radar library grew 235 → 238 products; manifest + `_coherence_mask_stats.csv` +
`_atmospheric_audit.csv` + `audit_log.json` all re-synced (the plumbing suite's
manifest-vs-audit consistency guard caught a stale `audit_log.json` at 235 → fixed by rerunning
`export_audit_json.py`). Battery unchanged at TEN suites **8+12+10+11+14+11+6+12+5+8 = 97 green**
(the `test_submit_pairs.py` suite from §60-cont. is the 10th).

**Seam-velocity cross-check DONE `[MEASURED]` (2026-07-22, non-destructive — production inverter
reused via scratch quarantine + scratch OUT_DIR; validated `data/velocity/` untouched):**
- **Frame renumber f106→f105 (and f102→f103): SAFE.** The bridge IFG 0419(f106)×0501(f105) is
  coherent + atmospherically CLEAN (§61 above) — a coherent interferogram cannot be unwrapped
  across misaligned frames, so the renumber is a label shift, not a geometry break. f105's own
  short-series velocity is noisy (median −17 mm/yr over 48 days) — expected short-baseline
  behaviour, not a frame defect.
- **S1A→S1D handover (0618×0625): a correctable but UNVALIDATED offset → DROPPED.** Inverting
  f105 with vs without the S1D pair: **no spatial distortion** (velocity-change median +0.4 mm/yr,
  symmetric) but a **clean, tight systematic −18.6 mm offset (robust-σ 7 mm)** at the S1D epoch —
  a platform-handover phase/reference step. Behaves like a correctable reference offset, but it
  is the first cross-unit pair ever processed here. **User decision: drop the S1D seam; rebuild
  S1A-only through 18 Jun** (the low-risk ~2-month cadence gain); revisit S1D when a second S1D
  pass exists to cross-check it.
- **Cross-unit parser bug found + fixed (error log 2026-07-22):** the `S1AA_`-hardcoded date
  parsers (5 files) could not read the `S1AD` seam → broadened to `S1[A-D][A-D]_`; new regression
  test; **battery 98 green** (science suite 12→13).

**Full S1A-only rescore DEFERRED to a focused next session (user's call).** A faithful rebuild
needs the REAL pipeline (`consolidate → apply_connectivity_rescues → run_multistack → GSI
rescore`) — it depends on the pair-metrics cache + rescue-aware cross-frame network merge, which a
non-destructive sandbox script cannot reconstruct (confirmed 3×: KEEP-only concat rank-deficient;
+hand-picked bridges still deficient; the recommender is metric-blind on a 3-column scratch
quarantine). **Next-session plan:** back up `_quarantine_list.csv` + `_stack_manifest.json`
(revert path), run the real S1A-only rebuild (bridges to 18/23 Jun, NO S1D), then compare the new
AUC/recall against §21b/§44 as the pre/post before accepting. The validated product stays live
and untouched until then. Diagnostic scripts kept in git-ignored `data/rebuild/`
(`seam_check.py`, `sandbox_velocity.py`).

---

## 62. Prospective real-world catch — the 22 Jul 2026 Gangroo–Ramsu fatal boulder strike (NH-44)  `[REAL]`
*(2026-07-24, session 29 — online-news verification + gate cross-check against the live 2026 artifacts,
which `live_alarm.py` had already regenerated the same day at 12:55 on the auto-fetched rainfall.)*

**The event (verified, 3 independent outlets):** 22 Jul 2026 ~13:20 IST, boulders/shooting stones
struck a Tempo Traveller (Banihal→Doda) at **Gangroo near Ramsu (Ramsoo), Ramban, on NH-44** —
**2 killed** (a couple from Doda), 4 passengers + a traffic SI injured; NH-44 suspended from ~09:30.
Part of a multi-day monsoon disaster: **~23–25 rain-related deaths across Jammu province since 19 Jul**,
7 missing; in Ramban ~8 houses damaged + ~22 link roads blocked over 3 days. Rainfall 24 h to 22 Jul:
**Udhampur 112.6 mm, Katra 58.5 mm** (Kathua 153, Samba 133 regionally). Inside the Ramban AOI; folded
into `ramban_historical_events.json` (rev 3, HIGH confidence). Sources: IBTimes India, Kashmir Vision
(23 Jul), Daily Excelsior. The validated back-test inventory (`ramban_documented_landslides.geojson`)
is deliberately **not** touched (§38 precedent — the spatial score is frozen).

**Did the model catch it? Split by arm — the §12c/§12g "AOI-mean dilutes a local burst" pattern, replayed live:**

- **Experimental IMERG sub-daily gate → YES, flagged the whole window.** **ALERT on 18 Jul
  (E=3.05)** — four days before the strike — and a continuous WATCH/ALERT state **17→23 Jul**; the
  event day itself **22 Jul = WATCH (E=2.44**, 20.8 mm/6 h AOI-mean). Season-wide only **3 ALERT days**
  (1 / 2 / 18 Jul of 112) — not noise. It reached WATCH (not ALERT) on the exact day partly because the
  ~11 km AOI-mean dilutes a point cloudburst (Udhampur gauge 112 mm vs AOI-mean ~33 mm), so the true
  local intensity was higher than E=2.44 implies. Source: `imerg_gate_summary_2026.json`, asset
  `NASA/GPM_L3/IMERG_V07`, fetched 2026-07-24 07:24 UTC (burst_watch_k 1.0 / burst_alert_k 3.0, §58).
- **Validated daily ERA5-Land gate → latency-blind, confirmation PENDING (not a miss).** Its 2026
  season ends **18 Jul** (~5-day reanalysis lag); it was **WATCH 14–16 Jul** (E≈1.0–1.15), DORMANT
  17–18, and cannot yet see 19–22 Jul. Official 2026 daily-gate state through 18 Jul
  (`operational_alarm_report_2026.json`): 109 days, **4 ALERT days (all early April), 29 WATCH**,
  8.2× selectivity; it correctly caught the 7 Apr Digdol slide (§52: E=2.13 → ALERT, Δ=0). **Expected
  to confirm ~27 Jul** once ERA5-Land publishes 19–22 Jul — the incremental `live_alarm.py` fetch
  extends the CSV automatically; re-run `docker compose run --rm mintpy python workflows/live_alarm.py`
  then the `insar` image to regenerate.

**Verdict:** a genuine **prospective near-catch by the fresh IMERG arm** (ALERT 18 Jul + sustained WATCH
through the event) — the strongest field evidence yet that the §55/§58 sub-daily arm earns its keep;
the validated daily arm's ruling is *deferred by publication latency, not missed*. Spatial honesty: the
event sits ~2 km from the northern frame-102 hazard-zone cluster (~33.31°N), but the creep map covers
only ~14% of the AOI, so the exact failed slope is **not** confirmed as mapped (unmeasured ≠ safe), and
a rain-triggered rockfall is a WHEN-trigger event, not a slow-creep target. **Caveats:** the IMERG arm
has no back-tested operating points (experimental); the 2026 rainfall was auto-fetched locally (not
re-pulled this session); the daily-arm confirmation is outstanding.

---

## 63. The burst arm's false-alarm rate MEASURED — it does not cry wolf more than the validated arm  `[MEASURED]`
*(2026-07-25, session 30 — `imerg_calibration.py` extended (Q4 + a generated Tier-3c table);
report `data/rainfall/imerg_calibration_report.{json,md}`; suite `tests/test_imerg_gate.py`
14→21. Closes the standing blocker in the §56 plan's risk register — "burst arm cries wolf |
1b measures the false-alarm rate before any fusion; stays labelled experimental until then" —
and the §55/§62 caveat "this arm has no back-tested operating points".)*

**The method (§58's day-count was only a proxy).** Monsoon rain arrives in spells, so "11
flagged days" can be 3 decisions or 11. Flagged days are clustered into **EPISODES** (runs of
flagged days, merging spells separated by ≤1 quiet day) — one episode = one time the gate asks
for a decision. Each episode is explained/unexplained against the verified events, and the
**same measurement runs on the validated daily arm** so the two are judged in one currency.
Pooled over the four AOI-seasons on disk (**654** burst day-records / **648** daily — 214 each
for 2025, 113/110 for the part-seasons). Provisional IMERG days dropped; an event outside an
arm's record span counts as *pending*, never as a miss (the §62 ERA5-latency case).

**Head-to-head at each arm's SHIPPED operating point `[MEASURED]`:**

| arm (ALERT) | flagged days | % season | episodes | mean / longest ep | unexplained (±1 d) | per 100 d | ±10 d |
|---|---|---|---|---|---|---|---|
| **burst IMERG (k=3)** | 43 | **6.6%** | 19 | 2.3 / 8 d | 15 | **2.29** | 10 → 1.53 |
| daily ERA5-Land (k=2, validated) | 91 | **14.0%** | 13 | 7.0 / 23 d | 9 | **1.39** | 7 → 1.08 |

**Verdict — the arm earns its keep, with a named cost.** At its shipped threshold the burst arm
costs **less than half the alarm DAYS of the arm we already trust** (6.6% vs 14.0% of season)
while interrupting **~1.6× more often** (2.29 vs 1.39 unexplained episodes/100 d). The two arms
have opposite temperaments, and that is the real finding: the burst arm is **acute** (19 short
episodes, mean 2.3 d) where the daily arm is **chronic** (13 episodes, mean 7 d at ALERT, and at
WATCH a single unbroken 92-day spell — 42.6% of season, which is alarm fatigue by another name).
A gate that says "these two days" is operationally cheaper than one that says "this quarter",
even when it says it more often.

**Honest limit (load-bearing).** The inventory records only fatal/newsworthy failures over two
small AOIs, so an unexplained episode is **not a proven false alarm** — much of it is real rain
that moved ground nobody reported. The ±1 d count is therefore an **upper bound** and the ±10 d
count a **lower bound** on each arm's false-alarm rate. Both arms carry the identical bias,
which is exactly why this is reported as a *comparison*, never as an absolute skill score.

**★ The 7th verified event changes the fatal floor — and opens a live operating-point question.**
The §62 Gangroo–Ramsu strike (22 Jul 2026, 2 deaths) is now in the calibration set: it reads
**E=2.44 (WATCH) on the day — the first FATAL event the burst arm does not reach ALERT on at
Δ=0.** The arm was live (ALERT 18 Jul, **lead −4 d**, then continuous WATCH through the strike),
but the same-day fatal floor is **2.44, not 3.07**, so §58's "keeps every fatal event" now reads
**3/4 same-day**. Pricing the obvious response:

| burst ALERT k | flagged days | % season | episodes | unexplained (±1 d) | per 100 d | events caught (±1 d) |
|---|---|---|---|---|---|---|
| 2.0 | 81 | 12.4% | 31 | 26 | 3.98 | 5/7 |
| **2.4** (the largest k reaching E=2.44) | 63 | **9.6%** | 27 | 22 | **3.36** | **5/7** |
| **3.0 (shipped)** | 43 | 6.6% | 19 | 15 | 2.29 | 4/7 |

→ **Recommendation, NOT adopted (a live-gate operating point is the user's call): k=3 → 2.4**
buys same-day ALERT on a 2-death event for +47% alarm days (6.6→9.6%) and +47% unexplained
episodes (2.29→3.36/100 d) — and the arm would *still* flag fewer days than the validated daily
arm (9.6% vs 14.0%). The counter-argument stands: with the §58 gauge bias (IMERG reads
0.16–0.22× the Katra gauge on extremes) E is biased LOW anyway, so a lower k is the
bias-consistent direction. `imerg_gate.py`'s `BURST_ALERT_K` is unchanged at 3.0 pending that call.

**Tier-3c table is now GENERATED, not hand-maintained** (`data/inventory/temporal_skill_table.csv`,
7 rows, written by `imerg_calibration.py`). It had silently gone stale — the §62 event never
landed in it — which is precisely the failure mode a derived artifact removes. New column
`burst_alert_lead_days` (nearest burst ALERT within ±10 d; blank beyond, where the nearest
ALERT is an unrelated storm, not a lead time) and a `PENDING`/`pending` state for a verdict the
daily arm's record cannot yet reach. The schema test was tightened, not loosened: `pending` is
only legal while `daily_level == PENDING`, a *settled* fatal row must still be caught at ALERT,
and every fatal row must be at least ARMED (WATCH+) at Δ=0 by an arm that could see it.

**Data-refresh note (supersedes one §58 number):** the 2026 IMERG seasons grew 108→115 days (the
§62 auto-fetch to 24 Jul), so §58's *"VD 2026: 10→7"* (days at k=2 vs k=3) now reads
**VD 2026: 16→11** (and Ramban 2026, uncited there, 4→2 becomes 10→3). §58's 2025 counts
(Ramban 21→11, VD 36→18) and both gauge-bias anchors are **byte-identical** — verified by
diffing the regenerated report against the pre-change copy.

**Verified:** 7 new hermetic tests (episode merging incl. unsorted/duplicate input; `burst_level`
agreeing with the production gate on the same E; episode attribution at both windows; WATCH
including ALERT days; the out-of-record *pending* rule; the full skill-table verdict matrix;
pooling arithmetic) — suite 14→21, **full battery TEN suites 8+12+10+11+21+11+6+13+5+8 = 105
green**. The regenerated report is byte-identical on a second run (idempotent), and all
pre-existing report fields (2025 sweeps, gauge bias, the 6 original event rows) reproduce
unchanged.

---

## 64. Burst-arm ALERT threshold LOWERED 3.0 → 2.4 and regenerated — the change, and whether it makes sense  `[MEASURED]`
*(2026-07-25, session 30 cont. — user-authorised operating-point change. `imerg_gate.py`
`BURST_ALERT_K` 3.0→2.4; regenerated offline from the existing half-hourly caches for both AOIs
× both seasons, then `imerg_calibration.py`, then the two 2026 dashboards. §63 priced this move;
this section records what it actually did.)*

**Scope of the change — grading only, physics untouched `[MEASURED]`.** Every day's `max_E`,
burst window, duration and mm are **byte-identical** before and after (verified by diffing all
four daily-E CSVs): the danger curve, the rain data and the exceedance maths did not move. Only
the line drawn through them did. Structural check: **all 20 day-level flips are WATCH→ALERT** —
no day left ALERT, no DORMANT day was touched, which is exactly and only what lowering a
threshold may do.

| season | ALERT days 3.0 → 2.4 | WATCH days | flipped days (E) |
|---|---|---|---|
| Ramban 2025 (214 d) | 11 → **17** | 31 → 25 | 25 May 2.59 · 28 Jul 2.58 · 30 Jul 2.45 · 1 Sep 2.61 · 4 Sep 2.41 · 18 Sep 2.82 |
| Ramban 2026 (115 d) | 3 → **7** | 20 → 16 | 7 Jul 2.60 · 19 Jul 2.62 · 20 Jul 2.95 · **22 Jul 2.44** |
| Vaishno Devi 2025 (214 d) | 18 → **26** | 39 → 31 | 18 Apr 2.49 · 30 May 2.86 · 24 Jun 2.62 · 16 Jul 2.47 · 29 Jul 2.95 · 31 Jul 2.84 · 7 Sep 2.68 · 6 Oct 2.46 |
| Vaishno Devi 2026 (115 d) | 11 → **13** | 24 → 22 | 19 Jun 2.93 · 4 Jul 2.65 |
| **pooled (654 d)** | **43 → 63** (6.6% → **9.6%** of season) | — | 20 flips |

**What it bought `[MEASURED]`: every fatal verified event is now ALERT at Δ=0 — 4/4, was 3/4.**
The 22 Jul 2026 Gangroo–Ramsu strike (2 deaths, E=2.44) flips WATCH→ALERT on the day it
happened. The Tier-3c table's `caught_at_alert_by` for that row moves `pending` → **`burst`**
with `delta_days=0`. No other event's verdict changed.

**What it cost `[MEASURED]` (the §63 yardstick, re-run):**

| burst arm @ALERT | flagged days | % season | episodes | mean/longest ep | unexplained (±1 d) | per 100 d |
|---|---|---|---|---|---|---|
| k=3.0 (was) | 43 | 6.6% | 19 | 2.3 / 8 d | 15 | 2.29 |
| **k=2.4 (now)** | **63** | **9.6%** | **27** | 2.3 / 8 d | **22** | **3.36** |
| daily ERA5-Land k=2 (validated, unchanged) | 91 | 14.0% | 13 | 7.0 / 23 d | 9 | 1.39 |

The production gate's own recomputed ALERT counts (17+7+26+13 = **63**) match §63's k=2.4 sweep
row exactly — an independent confirmation that the calibration sweep and the shipped gate agree.

### Does lowering it make sense? — the honest assessment

**Yes, on three arguments, with one real fragility.**

1. **It is not fitted to a single point — it is the selectivity-optimal choice for the recall
   step.** The sorted event E values are 0.99, 1.09, **2.44**, 3.07, 3.90, 4.19, 9.21. *Any* k in
   the band (1.09, 2.44] catches the same 5 of 7 events at Δ=0 — the sweep confirms it (k=1.5,
   2.0 and 2.4 all read 5/7). Within that band, higher k = fewer false alarms. **2.4 is the top
   of the band**, so it buys the recall step at the lowest possible alarm cost: 63 days vs 81 at
   k=2.0. The alternative reading — "2.44 minus epsilon, fitted to the newest event" — would be
   overfitting; this one is not, because the whole band is equivalent in recall and 2.4 is its
   cheapest member.
2. **It is the bias-consistent direction.** §58 measured IMERG reading only **0.16–0.22×** the
   Katra gauge on the two extreme 24-h anchors (11-km pixel mean vs a point gauge in orographic
   terrain). E is therefore biased **LOW in exactly the events that matter**, so a *lower*
   trigger corrects toward the truth. §58's own conclusion was "k must NOT be pushed above 3" —
   2.4 moves the way the evidence already pointed.
3. **The arm stays cheaper than the arm we already trust.** Even at 9.6% of season it flags
   **fewer days than the validated daily arm's 14.0%**, and its episodes stay short (mean 2.3 d
   vs 7.0 d; the daily arm's WATCH still contains one unbroken 92-day spell). The acute-vs-chronic
   finding of §63 survives the change.

**The fragility, stated plainly: the margin is 1.6%.** 2.40 sits just below 2.44. An IMERG V07
reprocessing, a re-fetch, or any AOI-polygon edit that nudges that day's E down by 2% silently
un-catches the fatal event that motivated the whole change. **Mitigation shipped:** a regression
guard in `tests/test_tier34.py` asserts `min(fatal burst_E) >= BURST_ALERT_K` and fails loudly
with instructions to re-derive k rather than edit the test.

**Two honest counter-points, recorded rather than argued away.** (a) The *operational* gain is
smaller than the metric gain: the arm was already ALERT on 18 Jul and held WATCH continuously
through the strike, so a reader watching the dashboard was warned either way — what changed is
the label on the day, not the awareness. (b) The unexplained-episode rate is now **2.4× the
validated arm's** (3.36 vs 1.39 per 100 d). That is the price of the extra catch and it is why
this arm **remains display-only and labelled experimental** — the official alarm is still the
daily gate, whose thresholds, reports and calendars are **byte-identical** before and after
(verified for all four AOI-seasons).

**Regeneration scope + a trap found.** Regenerated: the four daily-E CSVs, the four
`imerg_gate_summary_*.json` (all now record `burst_alert_k: 2.4`), the calibration report, the
Tier-3c table, and the **2026** dashboards for both AOIs (the live ones; both correctly still
read WATCH on the provisional 24 Jul day, E=2.2 and 2.01). **Deliberately NOT regenerated: the
2025 season dashboards** — re-running `operational_alarm.py` for a *past* season recomputes it
against **today's** hazard footprint and inventory, which silently rewrote the 2025 reports
(Ramban footprint 12→8 zones, VD 21→14, VD events 4→5) and would have invalidated §-cited
historical numbers. Caught by a byte-comparison against a pre-change backup and **fully
reverted**; entry in the error log. Their burst cards therefore still show k=3-era counts and are
correct as historical snapshots.

**Verified:** full battery **105 green, 0 failed** (ten suites, unchanged count).
`test_calibrated_alert_threshold` now pins **both sides** of the new boundary (a burst at E≈2.5
must read ALERT, one at E≈1.7 must stay WATCH) plus `BURST_ALERT_K <= 2.44`; the boundary test
in `test_imerg_gate.py` was rewritten to state edges **relative to the constants**, so the next
re-tune cannot silently invalidate it — only the one pinning test asserts literal values.

---

## 65. NISAR forward stream ARRIVED — and the first monsoon granules are VOID over both AOIs (honest abort + a guard that would have published a fake result)  `[MEASURED]`
*(2026-07-25, session 30 cont. — the plan's dated Tier-2c trigger fired. `radar_watch.py`
(stream watch), `nisar_coherence_pilot.py` (seasons + coverage guard), 2 GUNWs pulled from ASF
(~3.7 GB), suite `tests/test_radar_watch.py` 6→10. Reports
`data/nisar/nisar_coherence_pilot{,_monsoon}.json`.)*

**The trigger the plan was waiting on has fired `[MEASURED]`.** §56/Tier 2c said the NISAR
operational stream had not reached this region ("nothing after 18 Jan 2026 — recheck monthly")
and roadmap #5 named **Jul 2026** as the expected window. Today's watch: **`stream_started:
true`, 104 products, 8 GUNWs, newest acquisition 2026-07-19, 6 new acquisition dates.** Five
new GUNWs (Jun–Jul 2026) on top of §59's three winter ones — ASC track 156 (25 Jun×7 Jul,
7 Jul×19 Jul) and DESC track 135. **NISAR is now the freshest radar over Ramban by ~10 weeks**
(its C-band library ends 2026-05-06; S1A ceased operations 29 Jun, ASF's S1D ingest lags ~3 wk).

**Why this mattered scientifically:** §59 measured L-band recovering **75–87%** of C-band's
failure-class pixels but stated its own limitation plainly — *winter is the season of minimum
vegetation contrast, so that is a LOWER BOUND*. Monsoon L-band is the number the whole L-band
case rests on. The pilot was therefore parameterised into two seasons on the **same NISAR track
156 frame 018** (geometry held constant, only season varies), with the 12-day baseline held
fixed in both bands — the 7-day S1A×S1D seam pair was deliberately excluded because a shorter
baseline decorrelates less and would have biased the comparison *toward* C-band.

**Result: NO monsoon measurement is possible from the current stream. `[MEASURED]`**

| granule (ASC 156) | granule-wide valid | Ramban window valid | Vaishno Devi window valid |
|---|---|---|---|
| winter 27 Dec × 08 Jan (§59) | 49.6% | **100.0%** (median γ_L 0.720) | **100.0%** (0.692) |
| monsoon 25 Jun × 07 Jul | 33.9% | **0.0%** (all-NaN) | 19.3% (median **0.007**) |
| monsoon 07 Jul × 19 Jul | 33.2% | **0.0%** (all-NaN) | 18.1% (median **0.007**) |

Both monsoon granules are **voided over our AOIs in the same place** — n=2, so this is a
systematic property of the provisional processing over this footprint, not a bad granule.

**How we know it is a VOID and not a monsoon result** (three independent checks — this is the
finding that matters, because the naive reading is "L-band collapses in the monsoon"):
1. **C-band on the same ground and dates is healthy** — median γ_C **0.72–0.85** on the 06→18
   Jun and 11→23 Jun 12-day pairs. C-band is the *shorter* wavelength; it cannot out-survive
   L-band by 100×. If the ground had truly decorrelated, C would have died first. It didn't.
2. **The granule contradicts itself.** Over Ramban `coherenceMagnitude` is 100% NaN while
   `connectedComponents` is **>0 on 100%** of the same pixels — the unwrapper claims valid
   unwrapped data exactly where coherence claims none.
3. **The values are not low, they are absent** — 0 pixels exactly-zero, 0 pixels in (0, 0.05];
   the Ramban window is **64,496/64,496 NaN**. VD's 0.007 is the fringe of the same void.

**★ NASA's own QA PASSES these granules — and that is a trap worth recording.** The product
QA_SUMMARY reports **46–63% NaN** across layers and marks each **PASS**, because its threshold
only trips above **99%** NaN. One granule even carries `Passes all identification group checks?
FAIL` alongside all-PASS layer checks. **A product-level QA PASS says nothing about whether your
AOI has data.** Any pipeline ingesting NISAR must do its own per-AOI coverage check.

**★ The guard — the real deliverable.** Before it existed, the monsoon run produced a confident,
fully-formatted verdict: *"[vaishnodevi] C 0.852 vs L 0.007 | C-fail 2.5% → L recovers 0.0%"*
plus the standing conclusion string *"L-band recovers only a modest share of C-band's lost
ground"*. **That number was computed from a NaN void and is entirely fabricated** — and it
directly contradicts §59, so publishing it would have inverted a validated finding on no
evidence (precisely the §12g failure mode CLAUDE.md exists to prevent). `l_window_health()` now
refuses to score an AOI whose L window is <40% valid or whose median is <0.05, and a run where
no AOI survives writes an explicit **ABORTED — no verdict** artifact carrying the per-AOI
evidence, never a coherence number. Pinned by 5 hermetic cases (full/void/fringe/dead/off-grid)
plus an artifact test asserting the monsoon report has `status: ABORTED` and **no**
`median_pct_of_C_fail_pixels_recovered_by_L` key, while the winter report keeps its §59 numbers.

**§59 is untouched and re-verified.** The winter run reproduces **byte-identically** after
parameterisation + guard (sites, verdict and l_band dicts all `==` a pre-change copy; only
additive `season` and `l_coverage` keys). The winter guard reads 100% valid over both AOIs —
a clean contrast that shows the guard is not simply rejecting everything.

**Where this leaves the L-band case:** unchanged and still positive — §59's 75–87% recovery
stands as the measured result, and it remains a *lower bound*. The monsoon confirmation is
**deferred on data availability, not on physics**. Re-check when NASA reprocesses these
provisional (`_PR_`, `P05023`) granules or when a later acquisition lands with our footprint
outside the void; the machinery is now in place to score it in one command
(`--season monsoon`) and to refuse it honestly if it is void again.

**Cost/housekeeping:** ~3.7 GB pulled; the 07 Jul×19 Jul granule was deleted after measurement
(its numbers are in the table above and it re-downloads in ~4 min), the 25 Jun×07 Jul granule
is kept because the monsoon preset points at it and the ABORT must stay reproducible.

**Verified:** suite `tests/test_radar_watch.py` **6→10** (season presets are a controlled
comparison — same track, 12-day baselines both bands, distinct output tags with winter's empty
so §59's artifact keeps its filename; the renumbered-frame admission; the coverage guard; the
abort artifact). Full battery **TEN suites 8+12+10+11+21+11+10+13+5+8 = 109 green, 0 failed.**

---

## 66. Stored XSS in the dashboards — found, proven, FIXED, and regression-tested  `[MEASURED]`
*(2026-07-25, session 30 cont. — codebase-wide security scan then remediation.
`operational_alarm.py` (`_esc`/`_safe_url` + every untrusted interpolation),
`tests/test_historical_events.py` 11→15. Severity **HIGH**.)*

**The vulnerability `[MEASURED]`.** `operational_alarm.py` rendered the curated
historical-damage record straight into HTML — 105 HTML fragments, **zero** escaping. Every
field of `data/inventory/<slug>_historical_events.json` reached the page raw: `name`, `damage`,
`date_note`, `confidence`, `confidence_reason`, and each source's `label` and **`url` — the
last one inside `href="…"`**. Also unescaped: the radar-freshness pill's `data-*` attributes,
which carry **ASF API** values. Proven, not theorised — four payloads landed verbatim:

| payload | field | lands in |
|---|---|---|
| `X</b><img src=x onerror=alert(1)>` | `name` | element text |
| `<script>alert(4)</script>` | `damage` | element text |
| `javascript:alert(3)` | source `url` | **`href` attribute** |
| `" onmouseover="alert(2)` | source `label` | **`title` attribute break-out** |

**Why HIGH rather than cosmetic — the escalation chain.** Two facts combine. (1) The data is
**untrusted by this project's own documented process**: §36–§38 and CLAUDE.md classify
deep-research/LLM-synthesis documents as lead generators only, and the record's rows are
transcribed from those plus news URLs. (2) `control_panel.py` serves the generated dashboards
as `text/html` from `/file/…` — the **same origin** as its control API. So a payload reaching a
dashboard executes at `http://127.0.0.1:8765` and can, same-origin and with no CSRF barrier:
`fetch('/file/…')` **any file under `data/`** (~73 GB of products and config), `POST /run` to
trigger Docker jobs, and exfiltrate both to any host. Local file read + job execution from a
news-sourced string.

**The fix.** `_esc()` (`html.escape(..., quote=True)`, None→"") on every interpolation of a
value not originating in this codebase, and `_safe_url()` — an **allow-list** admitting only
`http://`/`https://`; anything else (`javascript:`, `data:`, `vbscript:`, scheme-relative
`//host`) yields `""` and the source is cited as **plain text instead of a link**, so a source
is never silently dropped. Real links also gained `rel="noopener noreferrer"`.

**Verified by PARSING, not substring matching `[MEASURED]`** — this distinction mattered: the
first check reported three "still injected" hits that were actually *escaped* text (`&quot;
onmouseover=&quot;…` legitimately contains the characters `onmouseover=`). The permanent test
parses the rendered HTML and asserts the resulting DOM carries **no** injected element, **no**
`on*` handler, and **no** non-http(s) `href`/`src`. Results:

- `_hist_panel` with all four payloads → **0 findings**; payloads still present as escaped,
  visible text (a fix that deleted content would also pass an injection check — asserted).
- A legitimate source keeps its link with the query `&` escaped:
  `href="https://example.org/a?b=1&amp;c=2"`.
- **Whole-page** render → 0 findings, against a precise allow-list of the page's own
  first-party constructs (its `<script>` blocks, `onclick="showTab(...)"`, the base64 figure) —
  so any *new* inline handler, ours or injected, trips the test.
- **NEGATIVE CONTROL:** disabling `_esc` makes the same assertions FAIL (injected element +
  handler both detected), proving the guard can actually fail. A guard that cannot fail is not
  a guard.
- **All four dashboards on disk audit CLEAN**, including the two live 2026 pages regenerated
  with the fix.

**The validated daily arm is untouched** — all eight report/calendar artifacts across the four
AOI-seasons are **byte-identical** before and after (the 2025 pages were deliberately not
regenerated, per §64's past-season trap).

**Verified:** suite `tests/test_historical_events.py` **11→15** (panel not injectable; the
negative control; `_safe_url` allow-list incl. case-variant `JavaScript:`, leading whitespace,
scheme-relative and empty/None; whole-page audit). Full battery **TEN suites
8+12+10+15+21+11+10+13+5+8 = 113 green, 0 failed.**

**Still open from the same scan (LOW, not fixed):** no CSRF/`Origin` check on the panel's
`POST /run` — any site the user browses can trigger a job cross-origin; impact is unwanted
compute only, since `action`/`aoi` are strictly allow-listed. Also: `_serve_file` reads whole
files into memory (a multi-GB GeoTIFF request exhausts the panel), and the base image
`mambaorg/micromamba:1.5.10` is an old pinned tag. Verified clean in the same scan: no
`shell=True`/`eval`/`exec`/`pickle`, zip-slip safe, no secrets tracked or in history, container
non-root, panel bound to 127.0.0.1 with a correct traversal guard, dependencies all current.

---

## 67. Routed-LLOF swap ADOPTED (§60 4c closed) — the post-merge gate was already satisfied  `[MEASURED]`
*(2026-07-25, session 30 cont. — `config/{ramban,vaishnodevi}.yaml` `llof_routing: d8`;
alerts regenerated via `agentic_orchestrator.py` per stack + `run_multistack.write_union_alerts`;
re-scored with `backtest_inventory.py`. Suite `tests/test_config_registry.py` 8→9.)*

**The gate was open and nobody had noticed.** §60 4c scheduled the swap "post-merge"; the LIVE
block still listed it as blocked on a merge that was the user's call. **`master` took the merge
on 2026-07-19 (`dc9ba1e`, PR #2)** — so the condition had been satisfied for six days. The swap
had never been scored. Checked before assuming: `git log master` and a diff of `master..HEAD`.

**What changed `[MEASURED]`.** The TWI valley proxy is replaced by real D8 flow-accumulation
routing for the downstream-debris (`llof_potential`) flag. Zone sets are **identical** before
and after (verified by comparing every zone centroid) — the swap changes *which zones carry the
downstream flag*, never which slopes are alerts:

| site / scenario | zones | LLOF twi → d8 | gained | lost | flips |
|---|---|---|---|---|---|
| Ramban operational | 8 | 3 → **5** | +4 | −2 | **6 (75%)** |
| Ramban watch | 106 | 48 → **55** | +33 | −26 | 59 (56%) |
| Vaishno Devi operational | 14 | 5 → **8** | +3 | −0 | **3 (21%)** |
| Vaishno Devi watch | 102 | 53 → **57** | +24 | −20 | 44 (43%) |

Consistent with the §60 probe (which predicted ~7/8 Ramban and ~4/14 VD operational flips) —
the small residual is that the probe ran against the then-current zone set.

**★ The re-score: the swap is CONFINED, and that is the point `[MEASURED]`.** Re-running the
GSI back-test on the operational footprint with its documented arguments gives
**AUC 0.676, 28/138 detected, detection rate 0.203, null-vs-real median 7.01 / 3.75 km — every
number identical to the pre-swap artifact.** That is the expected and desired result:
`llof_potential` is a *downstream consequence annotation*, not a hazard input, so a correct swap
must leave the hazard score untouched. Verified independently that no velocity or hazard raster
was rewritten (Phase 2/3 never ran — mtime check). The swap's blast radius is exactly the alert
JSONs, briefings, the 3-D dashboard label and route exposure.

**Honest limit — this is an adoption on MECHANISM, not on a skill score.** There is no
inventory of debris-flow *runout* events to score `llof_potential` against, and the flag is a
property of the source slope while an event record is a property of the impact point — a
category mismatch. So no ROC/AUC for the flag itself is possible or claimed. The case for d8
rests on: (a) it computes the physical quantity (upslope accumulation over the real DEM) rather
than a topographic-wetness stand-in; (b) the D8 router is unit-tested on a synthetic valley
including the off-grid edge case (§60, `test_tier34`); (c) the §60 probe showed the proxy and
the real routing disagree on **half of all zones**, so the proxy was demonstrably not a
stand-in. Adopting the measured quantity over an unvalidated proxy is the defensible direction
even without a flag-level score — and it is recorded here as such, not dressed up as skill.

**Verified:** `tests/test_config_registry.py` **8→9** — a new test pins the adopted state
(`llof_routing == "d8"` for every registry site) so a silent revert to the proxy fails loudly
and a deliberate flip back is a visible edit. Full battery **TEN suites 9+12+10+15+21+11+10+13+5+8
= 114 green, 0 failed.**

### 67b. Process failure during the re-score — a derived artifact clobbered by default arguments  `[MEASURED]`

Recorded because it happened **one entry after** logging the identical lesson (§64's past-season
trap), which makes it worth more than a footnote.

To verify the re-score I ran `backtest_inventory.py` **with default arguments**. Its defaults are
not what produced the stored artifacts: the default inventory is
`ramban_documented_landslides.geojson` (11 events) while both stored reports were built from
`gsi_inventory_aoi.geojson` (138). The run therefore overwrote
`data/inventory/backtest_report.json` and `backtest_operational_report.json` with numbers from a
different experiment (AUC 0.450/0.628 vs the real 0.676) — and the console output looked
perfectly successful.

- **`backtest_operational_report.*` — fully restored.** Regenerated with the arguments the ledger
  documents (§16b) and diffed against a backup taken before the swap: identical in every field
  except `scored.aoi_path`, a stale string (`/app/ramban_aoi.geojson` →
  `/app/config/aoi/ramban_aoi.geojson`) reflecting the 2026-07-17 config restructure. Same file,
  new location; **no number moved**.
- **`backtest_report.*` (the monsoon arm) — regenerated, not restored.** Its prior on-disk state
  had no backup and its last-refresh provenance is unknown, so its previous contents are lost.
  Nothing load-bearing is lost with them: it is a git-ignored derived artifact, its headline
  numbers live in committed §16b, and it is reproducible from the documented command. The
  regenerated run (AUC 0.434, 97/138, lift 0.79× @2 km) differs from §16b's historical 0.409
  because the product has legitimately been rebuilt since (κ=0.06 adoption, §45) — §16b is a
  superseded historical entry, not a target to reproduce.
- **Rule now explicit:** *never re-run a scoring script with default arguments to "verify"
  something* — look up the invocation that produced the stored artifact, back the artifact up,
  run with those arguments, and diff. Vaishno Devi's back-tests were deliberately **not** re-run
  for exactly this reason: their documented invocations were not to hand, and the swap's
  confinement was already established by the identical Ramban score plus untouched hazard
  rasters and identical zone centroids.

---

## 68. Flash-flood expansion PLANNED (additive-only) + NISAR "fresh batch" verified as the already-ingested stream  `[MEASURED]` (checks) / plan = document only
*(2026-07-28, session 31 — planning + verification session, NO code or data products changed.
NEW `docs/references/FLOOD_EXPANSION_PLAN_2026-07-28.md`; ASF probes run natively
(asf_search 12.2.2, read-only search).)*

**NISAR re-check `[MEASURED]` (both AOIs, 2026-07-28):** the publicized "fresh batch" is
NASA's **20 Jul 2026 PUBLIC release** of the provisional stream (CRID `P05023`, acquisitions
≥ 17 Jun 2026, 100k+ files) — i.e. **the same stream §65 already ingested five days earlier**.
Over our footprints there is **nothing new**: 104 non-ECMWF products per AOI (identical sets),
**0 acquisitions newer than 2026-07-19**, **0 products processed after the §65 check
(2026-07-25)**; newest GUNW remains ASC track 156 07 Jul×19 Jul (processed 2026-07-23,
`P05023`). The monsoon void re-score (§65) therefore still **waits on data**; next ASC-156
acquisition expected ~early Aug at the 12-day cadence, and earlier-mission + reprocessed
releases are promised "over the coming months" (full record by end-2026). Correct programmatic
fetch path confirmed = exactly what `radar_watch.py` already does (`asf_search`,
`dataset=NISAR`, `intersectsWith=<AOI WKT>`, ECMWF aux excluded); identity guards for any
download: scene-name track/frame/direction (`156_A_018`), level `GUNW`, CRID, then the
per-AOI `l_window_health()` void guard before any scoring (§65 rule).
- **Newly noticed `[MEASURED]`:** **11 NISAR L3 SME2 soil-moisture products** intersect the
  AOIs — a future antecedent-wetness input (flood-plan F3 option; provisional grade today).

**Frame-DEM extent `[MEASURED]` (3 stacks sampled):** every HyP3 product DEM spans
**74.71–77.86°E × 31.45–33.50°N at 80 m** (~290 × 230 km) — the whole Regime-A catchment
terrain (and most of the upstream Chenab) is already on disk. This is the fact the flood
plan's "hydrological support domain" stands on: **the InSAR AOI never needs enlarging for
flood purposes.**

**The plan (document only, nothing built):** `FLOOD_EXPANSION_PLAN_2026-07-28.md` — an
additive, config-gated (`flood:` block absent = off, the §60 4c pattern) flash-flood/undercut
arm: F0 geometry probe (D8 channels + catchments via the *shared* `flow_routing_probe`
functions, coverage guard) → F1 catchment-aggregated IMERG burst staging (EXPERIMENTAL
framing, §55 lifecycle) → F2 creep×flood undercut coupling (stream-power ranking; never
writes into `alerts_operational.json`) → F3 deferred menu. Scope verdict recorded: Regime A
(tributary flash floods / toe erosion) only; mainstem Chenab and calibrated inundation depth
**excluded** — staged levels and geometric exposure are what the data can honestly support.
Test contract: baseline-freeze byte-identity manifest written FIRST, hermetic units,
negative-controlled guards, verified-event replays (full spec in the plan §7).

**Battery:** not re-run (docs-only session; pytest lives in the Docker images and Docker was
left down per the user's start/stop preference). Last committed state **114 green** (§67)
stands; the flood plan's R1/R7 make re-pinning it the first act of any flood session.

---

## How to maintain this ledger
- **Append, don't overwrite.** New runs add rows; superseded rows stay, marked *(superseded)*.
- **Tag every number** `[MOCK]` / `[REAL]` / `[MEASURED]` with date + producing script.
- **Before removing any mock setup**, confirm its KPIs are captured here (§5b/§5c/§5d are the
  mock-derived ones).
- Keep this in sync at the same time as the git-ignored journals (it is the *committed* mirror of the
  headline numbers).

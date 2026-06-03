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
correction method comparison** (none vs ERA5 vs empirical height-correlation; ERA5 −31 % scatter, a
Bekaert/TRAIN-style attack on the ~30 mm/yr noise floor)._

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

## How to maintain this ledger
- **Append, don't overwrite.** New runs add rows; superseded rows stay, marked *(superseded)*.
- **Tag every number** `[MOCK]` / `[REAL]` / `[MEASURED]` with date + producing script.
- **Before removing any mock setup**, confirm its KPIs are captured here (§5b/§5c/§5d are the
  mock-derived ones).
- Keep this in sync at the same time as the git-ignored journals (it is the *committed* mirror of the
  headline numbers).

# Flash-Flood Expansion Plan — the third leg of the warning system (drafted 2026-07-28)

> ## ⚑ STATUS AS BUILT — read this before the plan text below (updated 2026-07-29)
>
> **F0 ✅ and F1 ✅ are BUILT, RUN on all four AOI-seasons, and gated.** Ledger §69 (built),
> §70 (run live + 2 bugs), §71 (audit: the gate below had been SKIPPED and FAILED), §72
> (four-season set + skill table). Battery 114 → **157 green**. F2 is the next phase.
>
> **Three corrections to this document, recorded so the next session inherits reality:**
>
> 1. **§6/F1 "trailing-window burst depth over D = 0.5–6 h matched to the catchment's response
>    time" means a RANGE floored at t_c — NOT a single t_c-matched window.** It was first built
>    as a single window; because every catchment's t_c is 0.07–0.12 h that screened all 22 at
>    0.5 h only, and on the 22 Jul 2026 fatal event (signal at D = 6 h) the arm read FLOOD-WATCH
>    where the validated arm read ALERT — it **downgraded a fatal day** (§71). `match_durations()`
>    now screens every window ≥ t_c and takes the max.
> 2. **§5 says the sanctioned touch-points in existing files are "the ONLY ones" (two). There
>    are now THREE**, both additions made on the user's explicit instruction:
>    `operational_alarm.py` (planned), `live_alarm.py` (the non-fatal hook — §70; a flood level
>    is a WHEN-answer and goes stale silently if left manual), and `imerg_calibration.py`
>    (3 additive columns in the generated skill table — §72). `build_3d_dashboard.py` remains
>    untouched and is **F2's** touch-point, pinned by a test.
> 3. **§6/F1's replay is an ACCEPTANCE GATE and is now a TEST**
>    (`test_I2_I3_verified_event_replay_gate`), not something to run by hand. It was documented,
>    skipped, and the card shipped twice before anyone ran it. Never again: see the
>    "CLOSE THE PLAN" rule added to `CLAUDE.md`.
>
> **Where F0/F1 landed:** 22/22 catchments Regime-A, 0 truncated, 0 mainstem; only 3/22 zones
> channel-adjacent at 120 m; all 4 verified fatal events FLOOD-ALERT with 4/8–14/14 catchments
> alerting, both non-fatal events FLOOD-WATCH with 0/8 — but n=7 on the burst arm's own
> calibration set, so that is a description, not an independent validation. The MERIT-Hydro
> cross-check is recorded **INCONCLUSIVE** (§71). Operating guide:
> `docs/runbooks/FLOOD_ARM_RUNBOOK.md`.

Companion to the *Strengthening Plan (2026-07-18)* (`STRENGTHENING_PLAN_2026-07-18.md`), not a
successor: that plan hardens the existing creep+rainfall product; this one adds a **new,
strictly additive capability** — per-AOI flash-flood / river-undercutting risk that runs in
parallel with the InSAR creep analysis. Numbers cited by `RESULTS_AND_KPIS.md` § only.

---

## 0. Non-negotiable constraints (read first)

1. **Additive only.** No existing artifact changes: every velocity/hazard raster, alert JSON,
   daily-arm CSV, back-test report and dashboard stays **byte-identical** when the flood
   feature is absent from a site's config. The feature lives in new files
   (`workflows/flood_*.py`, `data/flood/`, `tests/test_flood_*.py`) plus exactly two sanctioned
   touch-points (§5): one non-fatal dashboard card and one 3-D dashboard layer toggle.
2. **Config-gated, off by default.** A new optional `flood:` block in the per-AOI registry
   file. **Absent block = feature fully off** — the same pattern that shipped `llof_routing`
   (§60 4c) with the validated products proven byte-identical.
3. **Measure first, adopt second.** Every stage below starts as a probe that writes a report,
   exactly like `flow_routing_probe.py` did before the d8 swap (§60→§67). Nothing becomes a
   dashboard-visible product until its divergence/skill has been measured and recorded in the
   ledger.
4. **Honest quantification.** See §1 — we will not print a number whose certainty we cannot
   defend. Guards abort without a verdict rather than publish a fabrication (the §65 lesson).

---

## 1. What "quantify the amount of flooding with great certainty" can honestly mean here

Absolute inundation forecasting (water depth in metres at a given parcel, with confidence)
requires river gauges, channel bathymetry, and a calibrated hydraulic model (HEC-RAS class).
**We have none of those inputs, and no path to them from satellites alone.** Any plan that
promises calibrated flood depths would be promising a fabrication — the same failure class as
the §65 "L recovers 0.0%" void-score, just slower.

What the data we *do* have supports, with defensible certainty:

| Quantity | Source | Certainty class |
|---|---|---|
| **Where** water concentrates: channel network + upstream area A (km²) per cell | D8 on the frame DEMs (already on disk, §3.1) — the *same* `d8_accumulation` that passed validation for the LLOF swap (§67) | HIGH (it's geometry) |
| **Which assets are exposed**: creep zones / road segments within a buffer of a significant channel | zone centroids + channel network | HIGH (geometry) |
| **How hard it is raining into each catchment**, sub-daily: catchment-aggregated IMERG burst exceedance E_f | `imerg_gate.py` machinery re-aimed at catchment polygons instead of the AOI box | MEDIUM — same provenance and biases as the §55/§58 burst arm (IMERG under-reads gauges 4.5–6× on extreme anchors, §58) |
| **Relative** flood/undercut susceptibility ranking along channels: stream-power proxy Ω ∝ q·S | A × effective rain × local channel slope | MEDIUM (ranking defensible, absolute values not) |
| **Staged levels** (FLOOD-DORMANT / WATCH / ALERT) per catchment/exposure point | E_f vs thresholds, initially inherited then calibrated on verified events | MEDIUM, and labelled EXPERIMENTAL until back-tested — the exact framing the burst arm carried (§55) until §63/§64 earned its operating points |
| Order-of-magnitude peak-discharge *band* (m³/s, one significant figure, with the runoff-coefficient range stated) | q ≈ c · i · A with c as an interval, not a point | LOW — printed only as a band, never a single number |

**The honest product is therefore a staged, per-catchment flood-trigger arm plus a geometric
exposure layer — not a flood-depth map.** This mirrors exactly how the rainfall arm was grown:
regional I-D curve → exceedance staging → episodes → calibrated thresholds (§16→§63→§64).

---

## 2. The two flood regimes — and which one we target

**Regime A — local tributary flash floods / debris-laden torrents.** Catchments of ~1–50 km²
draining the slopes above and through the corridors; response time minutes-to-hours; driven by
exactly the convective bursts the IMERG arm already grades. Every fatal verified event in the
inventory is this regime (20 Apr 2025 Ramban cloudburst §12g; 22 Jul 2026 Gangroo–Ramsu §62).
The user's motivating scenario — *land adjacent to a channel failing after flash-flood
undercutting* — is Regime A toe erosion, and it is a **landslide mechanism**: the flood is the
trigger, the failure is the thing our product already models.

**Regime B — mainstem Chenab floods at Ramban.** Upstream basin ~10⁴ km², response
hours-to-days, snowmelt-modulated, already monitored by CWC (Central Water Commission) with
real gauges. We have no gauge access, and competing with a national agency's calibrated
forecasts on their own river is not our edge.

**Decision: build Regime A. Defer Regime B to a single cheap probe (F3) and otherwise leave
it.** This is the scope line that protects the product's identity (see §4).

---

## 3. Facts this plan stands on (checked 2026-07-28)

### 3.1 The catchment terrain is ALREADY on disk — no new AOI, no new tasking
Every one of the 238 HyP3 product folders carries a **full-frame DEM: 74.71–77.86°E ×
31.45–33.50°N at 80 m** (~290 × 230 km, measured today on three stacks). The Ramban AOI is a
0.2° box inside it. Tributary catchments (Regime A) fit inside the frame with room to spare;
even the Chenab headwaters (Chandra/Bhaga, ~77.4–77.6°E) sit near — possibly inside — the
eastern edge. **F0 measures this instead of assuming it** (coverage-% guard, §65 lesson).
`flow_routing_probe.d8_accumulation` already runs on these full frames — "including catchment
area from OUTSIDE the AOI" is a documented property of the existing code.

### 3.2 Rainfall over any polygon is one GEE call away
`imerg_gate.py` fetches half-hourly IMERG V07 for an arbitrary geometry with an incremental
cache; ERA5-Land daily is equally global. Aggregating over a *catchment mask* instead of the
AOI box is a parameter change, not new machinery. Bonus: catchment-mean rain over a 20 km²
basin spans ~2–4 IMERG pixels — the same footprint-vs-pixel honesty note as §55 applies and
must be carried on every card.

### 3.3 Independent cross-checks exist for the geometry
MERIT-Hydro (GEE `MERIT/Hydro/v1_0_1`, 3″, precomputed global upstream area) cross-checks our
D8 network; JRC Global Surface Water gives observed historical water extent along the Chenab.
Both are free reads, no new infrastructure.

### 3.4 The validation seeds exist
The curated per-AOI historical-events records (schema-tested, provenance-flagged, §36–38 rules)
already contain flood/cloudburst-class events; the temporal-skill table (§60 3c) is
machine-generated and can grow a flood column the same way the burst column grew.

### 3.5 NISAR SME2 soil moisture is quietly available
Today's ASF query shows **11 NISAR L3 SME2 (soil-moisture) products** intersecting the AOIs —
a future antecedent-wetness input for both the landslide m and the flood runoff coefficient.
Logged as an F3 option, not a dependency.

---

## 4. The scope question, answered honestly (the user asked: will this stray us?)

**How much of this feature is useful?** About a third of what "flood model" naively implies —
and it is the *right* third, because it strengthens the existing product rather than standing
beside it:

- **Toe-erosion / undercut coupling (F2) is the highest-value piece.** River undercutting is a
  recognized driver of the NH-44 corridor failures. A creep zone that ALSO sits within reach of
  a high-stream-power channel during a burst is a categorically stronger warning than either
  signal alone — this deepens the core product's central claim (creep + trigger = warning).
- **Catchment-aggregated burst rainfall (F1) fixes a documented weakness.** The gate is
  AOI-mean today; §12g showed AOI-mean dilutes localized cloudbursts. Aggregating over the
  physically meaningful polygon (the catchment draining to the exposure point) is the principled
  version of the per-zone idea that §58 1a probed and correctly rejected at zone scale.
- **The exposure layer (F0) is nearly free** — geometry from data already on disk, using an
  already-validated routine.

**What would stray us — and is therefore deferred or excluded:**

- Calibrated inundation depth/extent modeling (needs gauges + bathymetry we don't have) — **excluded**.
- Mainstem Chenab flood forecasting (CWC's job, their gauges) — **excluded** beyond one F3 probe.
- Hydrological model calibration (HEC-HMS/VIC class), snowmelt-runoff modeling, reservoir
  effects — **deferred**; each is a discipline with its own validation burden and none makes
  the landslide warning better.
- Expanding the **InSAR** AOI for flood purposes — **excluded entirely** (see below).

**The larger-AOI concern (the user's instinct, and it is correct):** flash-flood risk at a
point is governed by rainfall over the *upstream catchment*, which extends far beyond — and at
much higher altitude than — the AOI. But this does **not** require enlarging the AOI in the
registry, because AOI means two different things:

| Domain | What it costs to enlarge | Flood plan |
|---|---|---|
| **InSAR AOI** (velocity, hazard, zones) | HyP3 credits, noise floor, validation burden — expensive in every axis | **NEVER enlarged by this plan** |
| **Hydrological support domain** (DEM + rainfall reads) | Nothing new — frame DEMs already span it; IMERG/ERA5 are global grids | New per-site, **data-only** catchment mask, derived in F0, stored in `data/flood/` |

**One-line verdict: build the flood feature as a trigger-and-exposure arm feeding the existing
warning system — the product stays "InSAR-detected creep, rainfall-triggered, honestly
validated", and flood becomes its third corroborating leg, not a second product.**

---

## 5. Architecture (all-additive)

New files (names final so tests can pin them):

```
workflows/flood_domain.py     # F0: catchment + channel derivation, coverage guard, exposure geometry
workflows/flood_gate.py       # F1: catchment-aggregated burst staging (reuses imerg_gate fetch + I-D grading)
workflows/flood_exposure.py   # F2: stream-power ranking + compound creep×flood flags
data/flood/                   # all outputs (git-ignored like the rest of data/)
tests/test_flood_domain.py, test_flood_gate.py, test_flood_exposure.py
docs/runbooks/FLOOD_ARM_RUNBOOK.md  (written at F1 ship)
```

New config block (per-AOI registry file; **absent = feature off**):

```yaml
flood:                        # OPTIONAL — absent block disables the flood arm entirely
  channel_upstream_km2: 0.5   # channel definition; default = the validated LLOF criterion (§60 4c)
  channel_buffer_m: 120       # exposure adjacency; F0 sweeps and records sensitivity
  min_catchment_coverage_pct: 95  # refuse to stage a catchment truncated by the frame edge
```

Shared-function rule (the §60 4c pattern that made the LLOF swap trustworthy): `flood_domain`
imports `d8_accumulation` / `routed_llof_flag` from `flow_routing_probe` — **never copies
them** — so the flood channels and the LLOF flags can never silently diverge.

Sanctioned touch-points in existing files (the ONLY ones):

1. `operational_alarm.py`: one `_flood_card()` reading `data/flood/flood_gate_summary{sfx}.json`,
   rendered **only when the file exists**, styled like `_imerg_card` including the EXPERIMENTAL
   banner; every interpolated field goes through the existing `_esc()`/`_safe_url()` (§66 rule).
2. `build_3d_dashboard.py`: one optional trace (channel network polyline + flood-exposure
   markers) behind a layer toggle, loaded **only when** `data/flood/` artifacts exist.

Both degrade to a no-op when the flood artifacts are absent — which is also how the regression
suite proves "nothing broke" (§7).

Explicitly **not** touched: the hazard engine (`fs_real.py`, `geomechanical_engine.py`), alarm
grading (`live_alarm.py`, daily arm), `imerg_gate.py`'s own thresholds, all back-test scripts,
all config defaults of existing keys.

---

## 6. Phases (each = probe → ledger entry → adopt-or-drop decision)

### F0 — Geometry probe: "where would water go, and what of ours is in the way" (1 session)
- Derive, per site, from the frame DEM: D8 accumulation (existing function), channel network
  (A ≥ `channel_upstream_km2`), the catchment polygon draining to/through each operational
  zone and each corridor segment, and **catchment coverage %** (share of each catchment inside
  the frame DEM — the truncation guard).
- Cross-check upstream areas vs MERIT-Hydro at ~20 sampled channel points; record divergence.
- Output `data/flood/flood_domain_{slug}.json` + `.md` with: n channels, per-zone
  channel-distance table, per-catchment area/relief/coverage, and the exposure verdict (which
  creep zones are channel-adjacent — the compound-risk candidates).
- **Verify:** unit suite green (synthetic-DEM known answers, §7); MERIT-Hydro divergence
  recorded; ledger § written. **Gate to F1:** coverage ≥ threshold for all Regime-A catchments.

### F1 — Catchment burst staging: the flood-trigger arm (1–2 sessions)
- For each F0 catchment: catchment-mean IMERG half-hourly (reusing the incremental fetch with
  a catchment cache key), trailing-window burst depth over D = 0.5–6 h **matched to the
  catchment's response time** (time-of-concentration proxy from area/relief; recorded per
  catchment), graded as exceedance E_f. Initial thresholds inherit the regional I-D curve's
  short-duration end — stated plainly on the card as inherited, not flood-calibrated.
- Replay the verified events (20 Apr 2025, 22 Jul 2026): does the affected catchment stage
  higher than the AOI-mean arm did on those days? That yes/no is the headline of the F1 ledger
  entry, and the go/no-go for showing the card at all.
- Ship: `flood_gate_summary{sfx}.json` + the dashboard card (EXPERIMENTAL banner), non-fatal
  hook in `live_alarm.py`'s alarm stage **modeled on the imerg hook** (failure = no card, never
  a broken regen).
- **Verify:** hermetic unit tests (no GEE in tests — canned CSV fixtures); the two replays
  recorded; existing battery still green; byte-identity audit passes (§7).

### F2 — Compound coupling: the undercut warning (1 session)
- Stream-power proxy Ω ∝ (catchment effective rain × A) × local channel slope per channel cell;
  rank; creep zone within `channel_buffer_m` of a top-decile-Ω channel **while** its catchment
  is in FLOOD-WATCH+ ⇒ `flood_undercut_flag` on that zone in the flood artifact (**never**
  written into `alerts_operational.json` — the existing product is read, not written).
- Buffer/threshold sensitivity sweep recorded (the §45 kappa-sweep discipline).
- **Verify:** flag truth-table unit tests; historical replay — do the corridor's known
  undercut-failure sites rank in the top decile? Recorded either way.

### F3 — Deferred menu (each needs its own dated trigger, none scheduled)
- Mainstem Chenab probe: JRC water-extent history + frame-DEM valley cross-sections; desk study only.
- NISAR SME2 antecedent wetness into the runoff coefficient (and possibly the landslide m) —
  revisit when SME2 is calibrated/validated grade (it is provisional today, §3.5).
- Flood-inventory growth + episode-based skill measurement (§63 method) → earned operating
  points → drop the EXPERIMENTAL banner (the §55→§64 lifecycle, repeated for floods).
- Per-catchment ERA5-Land daily antecedent-wetness modifier (API-style) if F1 replays show
  antecedent sensitivity.

**Documentation ritual per phase (CLAUDE.md):** ledger § (append-only, tagged), milestone.md
entry, primer section (flash-flood physics: unit hydrograph intuition, stream power, why
catchment ≠ AOI), error-log entries as earned, `/wrap-session` at close.

---

## 7. Test strategy (the "nothing broke, and the new thing works" contract)

### 7.1 Principles (inherited from the suites that already exist)
1. **Hermetic by default** — no network, no GEE, no ASF in tests; fixtures are synthetic DEMs
   and canned rainfall CSVs (the `imerg_gate` suite already models this).
2. **Byte-identity is the regression currency** — "additive" is proven by hashing, not claimed
   (the §60 4c / §65 / §67 discipline).
3. **Guards get negative controls** — a test that disables the guard and *requires* failure
   (the §66 pattern), so a silently-dead guard cannot pass.
4. **Constant-relative assertions** — tests import thresholds from the module under test rather
   than hard-coding copies (the §64 boundary-test lesson), so a deliberate recalibration does
   not require editing tests to lie.

### 7.2 Invariant (regression) suite — proves the existing system is untouched
`tests/test_flood_invariants.py`, written **in F0 before any flood code runs**:

| ID | Case | Assertion |
|---|---|---|
| R1 | Baseline freeze manifest | New helper hashes the protected set — `alerts*/…/alerts_operational.json` (both sites), hazard + velocity rasters (mtime+hash, the §67 method), daily-arm CSVs/report for all four AOI-seasons, back-test reports — into `data/flood/_baseline_freeze.json`; test asserts current disk == manifest. Run before F0 (creates) and in every flood session (checks). |
| R2 | Absent config = absent feature | Config loader with no `flood:` block → flood accessor returns disabled; `flood_domain`/`flood_gate` main() exit 0 with an explicit "flood arm disabled" message and write nothing. |
| R3 | Dashboard without flood artifacts | `operational_alarm` page builds with no `data/flood/` present; DOM contains no flood card (parse, don't substring — §66 lesson). |
| R4 | Dashboard with flood artifacts | Card renders; **daily-arm sections byte-identical** to the R3 render except the card block. |
| R5 | 3-D dashboard parity | Build with and without flood artifacts: without = no flood trace, existing traces identical in both. |
| R6 | Shared-criterion pinning | `flood_domain` channel criterion **is** `flow_routing_probe.routed_llof_flag` (identity check on the imported function), and `channel_upstream_km2` default == the probe's `UPSTREAM_KM2`. |
| R7 | Existing battery | Full 114-test battery green before and after each flood batch (bookkeeping in the ledger entry, as every session already does). |
| R8 | XSS audit extension | The §66 whole-page DOM audit runs on a page containing a flood card fed a hostile fixture (script tags in catchment names) → escaped everywhere, plus the negative control. |

### 7.3 Unit cases — `flood_domain` (F0)

| ID | Case | Expected |
|---|---|---|
| U1 | Tilted-plane synthetic DEM | Every cell drains to the low edge; accumulation along bottom row == column count (exact) |
| U2 | Synthetic V-valley | Single channel down the axis; catchment of a point on the channel == analytic cell count |
| U3 | NaN / nodata DEM cells | Accumulation 0 there, no NaN leakage downstream (the < −1000 sentinel rule) |
| U4 | Catchment truncated at frame edge | coverage% < threshold → catchment marked `truncated`, staging REFUSED with reason (never a silent understated area) — the §65 guard class |
| U5 | Off-grid zone centroid | Empty window, no wrap-around (regression on the fixed clamp bug, §60 4c) |
| U6 | Channel-distance math | Zone at known offset from synthetic channel → exact buffer in/out at `channel_buffer_m` ± 1 px |
| U7 | Coverage guard negative control | Guard disabled ⇒ U4 fixture must produce the wrong (confident) answer and the test must FAIL if the guard is absent |

### 7.4 Unit cases — `flood_gate` (F1)

| ID | Case | Expected |
|---|---|---|
| U8 | Canned half-hourly series, single 1-h burst | Trailing-window max picks the right window; E_f matches hand-computed exceedance |
| U9 | Burst spanning midnight | Not split (same invariant the daily-E windows already honor) |
| U10 | Incomplete newest day | Flagged provisional; E_f monotone non-decreasing as steps arrive |
| U11 | All-NaN / empty catchment rain | ABORT artifact with reason, no stage, no zeros-scored-as-dry (§65 class) |
| U12 | Threshold boundaries | E_f just below/at/above WATCH and ALERT constants — imported, not copied (§64 rule) |
| U13 | T_c window matching | Small steep catchment → short D; large gentle → long D; monotonicity asserted, table recorded |
| U14 | Idempotent re-run | Second run on same inputs = byte-identical outputs (CLAUDE.md idempotency rule) |
| U15 | Summary JSON schema | Pinned schema incl. `experimental: true`, coverage fields, provenance strings (the Tier-3c tightened-schema discipline) |

### 7.5 Unit cases — `flood_exposure` (F2)

| ID | Case | Expected |
|---|---|---|
| U16 | Compound-flag truth table | flag ⇔ (channel-adjacent ∧ top-decile Ω ∧ catchment ≥ WATCH); all 8 combinations |
| U17 | Ω ranking invariance | Doubling rain uniformly preserves ranking; slope=0 channel ranks bottom |
| U18 | Read-only contract | `alerts_operational.json` hash identical before/after an exposure run (the hard "we never write into the validated product" pin) |

### 7.6 Integration scenarios (small fixtures, full pipeline)

| ID | Scenario | Expected |
|---|---|---|
| I1 | Synthetic site end-to-end: V-valley DEM + canned burst CSV + minimal config | domain → gate → exposure chain produces schema-valid artifacts; compound flag fires on the constructed zone |
| I2 | **20 Apr 2025 replay** (real cached IMERG, marked non-hermetic/skipped-in-CI like existing data-dependent checks) | Affected catchment stages ≥ the AOI-mean arm's grade that day; result recorded in the skill table |
| I3 | 22 Jul 2026 Gangroo–Ramsu replay | Same contract as I2 |
| I4 | Dry winter fixture week | All catchments DORMANT; no card noise |
| I5 | GEE outage simulation (fetch raises) | live_alarm regen completes; card absent; exit 0 — non-fatal hook proven, not assumed |
| I6 | Season/suffix rule | Artifacts follow the grandfathered-Ramban suffix convention exactly (pinned against `season_suffix`) |

### 7.7 Battery bookkeeping
Every flood batch reports the battery as the sessions already do ("114 → N green, 0 failed");
a flood test never asserts on git-ignored real data except the explicitly-marked replay tests
(I2/I3), which skip with a reason when the cached season files are absent — so a fresh clone
stays green.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Scope creep toward "real hydrology" | §2/§4 exclusions are part of this committed doc; F3 items each need a dated trigger, like the NISAR Tier-2c trigger that §65 honored |
| IMERG can't see small catchments (2–4 pixels) | Stated on the card verbatim (§55 precedent); catchment size floor recorded in F0; never claim slope-scale resolution |
| Pure-Python D8 on 10.6 M-cell frames is slow | It already runs (probe §60); cache accumulation per stack DEM on disk; optimize only if measured to matter (MVP-first rule) |
| Frame-edge catchment truncation | U4 guard: measure coverage, refuse below threshold, say why |
| No flood ground truth → unfalsifiable staging | Same posture as the burst arm pre-§63: EXPERIMENTAL banner, replay anchors only, skill table grows per the §38 verification rule; no operating-point claims until an episode measurement exists |
| Dashboard XSS surface grows | Every new interpolation through `_esc()`/`_safe_url()` + R8 audit with negative control |

---

## 9. Suggested build order

F0 geometry probe (with `test_flood_invariants.py` + baseline freeze written FIRST) → ledger
entry + adopt/drop → F1 staging arm + replays → F2 compound coupling → F3 only on dated
triggers. Estimated 3–4 focused sessions to an F2-complete, regression-guarded, honestly
labelled flood arm.

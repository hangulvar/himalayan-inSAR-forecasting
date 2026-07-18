# Strengthening Plan — Data & Science (drafted 2026-07-18, session 27)

Successor to the completed *Science Upgrade Plan — Top 3 (2026-07-13)* (now in `docs/archive/`).
Grounded in the availability checks run this day (ledger §56) and the standing backlog
(SESSION_REVIEW STABLE §3/§4). Numbers cited by ledger § only.

## The facts this plan stands on (checked 2026-07-18, §56)

1. **Sentinel-1 is mid-handover, not broken.** S1A ended operations 29 Jun 2026; S1C was
   repositioned (≈2-week no-acquisition transition); **S1D now flies our reference orbits** —
   CDSE shows S1D IW SLCs on our ASC paths 25 Jun / 30 Jun / 7 Jul / 12 Jul (+ DESC 34).
   **ASF has ingested S1D only through 25 Jun** (≈3-week ingest lag). Our own catalog query
   whitelisted S1A/S1B and would have silently returned nothing forever — **fixed same day**
   (`submit_hyp3_jobs.py` now queries all Sentinel-1 units).
2. **NISAR has a real, complete winter sample over both AOIs**: 8 acquisition dates
   (19 Nov 2025 → 18 Jan 2026) with RSLC/GSLC/GCOV each and **3 ready-made GUNW
   interferograms** — enough for an L-band pilot NOW. The operational 1–3-day forward stream
   has NOT reached this region yet (nothing after 18 Jan 2026); recheck monthly.
3. **The rainfall gate is now two-arm** (§55): daily validated + sub-daily IMERG experimental,
   complementary on 2026's two verified events. The burst arm lacks operating points; the gate
   is AOI-mean, not per-zone.

## Tier 0 — Data-continuity triage — ✅ EXECUTED 2026-07-18 (§57), rebuild pending user go

- **0a ✅:** all-units Sentinel-1 catalog query (the S1A/S1B whitelist bug).
- **0b ✅:** radar-freshness pill live on both dashboards (age vs viewer clock; amber >35 d,
  red >90 d; announces "newer radar at ASF — rebuild unblocked" from the watcher).
- **0c ✅:** `radar_watch.py` runs non-fatally in every alarm regen (all-units ASF query per
  AOI, `data/radar_watch.json`, UNBLOCKED/waiting verdict). Found immediately: **Ramban's map
  is built from radar through 2026-04-24 (~12 weeks old) with 11 newer ASC scenes at ASF —
  its rebuild is unblocked NOW**; VD current through 23 Jun, waiting on ASF's S1D ingest.
- **0d ✅ (zero credits):** HyP3 officially supports S1C/S1D InSAR + cross-satellite pair
  naming; the path-27 seam pair (S1A 18 Jun × S1D 25 Jun, 7-day baseline) is submittable;
  submitter pairing/dedupe verified by dry-run; credits confirmed 7,460.
- **REMAINING (user's call):** run the cadence rebuild — Ramban first (unblocked, mostly
  S1A×S1A pairs + the seam bridge; applies the §43 f106 bridge swap), VD when ASF ingests the
  Jun-30+ S1D passes.

## Tier 1 — In-monsoon rainfall science (1–2 weeks; monsoon is NOW and radar is blocked)

- **1a — Per-zone IMERG E (§55's second half).** Sample the 0.1° grid at zone centroids
  (bilinear), per-zone trailing-window E, and arm zones by their OWN burst E in
  `per_zone_gate.py` (zone live iff m* ≤ m(t) AND [AOI E ≥ 1 OR zone-burst E ≥ 1]). Success:
  per-zone E measurably diverges from AOI-mean on convective days; demo on the 8 Jul Himkoti
  day (was the burst concentrated over the VD zones?).
- **1b — Burst-arm provisional operating points from the 2025 seasons (data already exists).**
  Run `imerg_gate.py` over both AOIs' 2025 windows; screen the verified events (20 Apr —
  must reproduce the §12g E; 21 Jul Banganga; 26 Aug Ardhkuwari) AND count quiet-day
  crossings → a first false-alarm rate; propose burst-arm watch_k/alert_k from that (labelled
  provisional — n is small and says so). Bias check: IMERG vs the two dated Katra gauge
  numbers (§51: 184.2 mm & 629.4 mm/24 h) — is IMERG hot/cold in this terrain?
- **1c — Two-arm fusion, display-only, AFTER 1b.** A labelled "combined vigilance =
  max(arms)" banner line only once the burst arm has provisional points. Never silently
  change the validated alarm.

## Tier 2 — NISAR L-band pilot (1–2 weeks, parallel; the strategic step-change)

- **2a — Ingest the winter sample.** Pull the 3 GUNW + GCOV over the AOIs (Earthdata creds
  already wired); crop/regrid; QA.
- **2b — THE experiment: L-band vs C-band coherence on OUR vegetated slopes.** Same-season
  12-day pairs (Nov–Jan): NISAR coherence vs S1 coherence, histogrammed inside the AOI and
  inside the WorldCover vegetation mask. Success criterion: a quantified coherence gain
  (median γ_L − γ_C over vegetation). Large → plan the operational L-band stack for the day
  forward processing reaches this region (vegetated-slope coverage is our #1 stated
  weakness). Small → documented negative result, C-band remains, claim retired.
- **2c — Watcher.** Extend 0c's poll to the NISAR dataset (monthly): flag when post-Jan-2026
  products appear.

## Tier 3 — Validation depth (2–4 weeks, interleaved)

- **3a — Susceptibility cross-check (Area 4 backlog).** LR/RF on DEM derivatives (slope,
  curvature, TWI, relief, aspect, drainage/road distance) vs the 138-point GSI inventory,
  k-fold AUC under the SAME protocol as the physics map; then the ensemble (physics ∩
  statistical). Answers the reviewer question "does physics beat a statistical map here?" —
  strengthens the claim whichever way it lands.
- **3b — GACOS second pull** (§0b tooling ready; user submits the form, ingest + §40
  crosscheck close the discrepancy pair).
- **3c — Standing temporal-skill table.** Formalize the growing record (event × arm × Δ days:
  Digdol daily-arm ALERT Δ=0; Himkoti burst-arm ALERT Δ=0; the 2025 trio) as a committed
  ledger table that each verified event extends — this is the accumulating evidence base that
  eventually validates the burst arm properly.

## Tier 4 — Structural science (month+; waiting on data or the user)

- **4a — Failure-class gap (CV3):** Sentinel-2/Landsat optical change (NDVI/bare-soil delta)
  as the brittle-failure detector, fused with the coherence tripwire; back-test on the 26 Aug
  2025 Ardhkuwari disaster (before/after imagery exists).
- **4b — Soil M2 lab pass** (user-side; §42 showed failure depth/strength is load-bearing).
- **4c — Flow-routing LLOF:** replace the TWI proxy with D8/D∞ routing on the DEM.
- **4d — Per-stack ERA5 reference-pixel + unwrapping QC** (§22): rescue frames 101/102 →
  deeper multi-look confirmation.
- **4e — Merge `aoi-vaishnodevi` → master; hosted dashboard** (user calls).

## Risk register

| Risk | Mitigation |
|---|---|
| ASF S1D ingest lag persists (~3 wk) | 0c watcher; CDSE shows acquisitions ARE happening — worst case is delay, not loss |
| HyP3 rejects cross-unit pairs | 0d verifies EARLY with one dry submission; fallback: start a fresh S1D-only baseline (loses cross-seam pairs, keeps cadence) |
| Burst arm cries wolf | 1b measures the false-alarm rate before any fusion; stays labelled experimental until then |
| NISAR forward stream stays absent here | 2b makes the winter sample yield the decision-relevant science anyway; 2c watches |
| Velocity baseline seam (S1A→S1D) biases velocities | treat the seam like a §22 reference-pixel problem: cross-check pre/post-seam velocity fields on stable ground before trusting trends |

**Sequencing in one line:** rain science now (monsoon is live, radar is blocked), radar
readiness + watchers this week (so the rebuild fires the day ASF catches up), NISAR pilot in
parallel (winter data is complete), validation depth interleaved, structural items as data and
the user allow.

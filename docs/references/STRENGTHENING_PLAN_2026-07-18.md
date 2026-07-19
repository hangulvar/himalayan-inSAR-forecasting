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

## Tier 1 — In-monsoon rainfall science — ✅ EXECUTED 2026-07-18 (§58)

- **1a ✅ (probe → deliberately NOT built):** zones span only ~3 IMERG pixels; decision-day
  zone-over-AOI divergence ≤1.29× (the ≥3× ratios are a near-dry-day small-denominator
  artifact, documented). Per-zone gating is LOW-VALUE at these AOI scales; revisit for a
  larger AOI. Probe kept: `imerg_perzone_probe.py`.
- **1b ✅:** 2025 seasons fetched; §12g reproduced through the production gate (20 Apr E=3.07,
  8 May E=1.09); six-event two-arm table built; **burst-arm ALERT recalibrated to E≥3**
  (halves flagged days, keeps all fatal catches); **gauge-bias measured: IMERG = 0.16–0.22×
  the Katra gauge on the extreme anchors** → never raise k further. `imerg_calibration.py`.
- **1c ✅:** display-only "Two-arm read (§58-calibrated)" line on both banners (today: Ramban
  WATCH, VD ALERT via the burst arm). The validated daily alarm untouched.

## Tier 2 — NISAR L-band pilot — ✅ EXECUTED 2026-07-18 (§59)

- **2a ✅:** the 12-day winter GUNW (27 Dec × 8 Jan, 2.3 GB) ingested to `data/nisar/`
  (GCOVs deliberately skipped — 7–9 GB of backscatter the pilot doesn't need).
- **2b ✅ — CONFIRMED:** where C-band fails (γ<0.35), **L-band recovers 75–87% of pixels**
  (median γ_L 0.55–0.62 there); gain concentrated exactly in the failure class; winter =
  lower bound on the monsoon advantage. VD not comparable (no winter C pairs — noted;
  re-run when accumulated). `nisar_coherence_pilot.py`.
- **2c ✅:** NISAR stream watch in `radar_watch.py` (non-fatal; currently "winter sample
  only, newest 18 Jan 2026"). Next NISAR action waits on the forward stream.

## Tier 3 — Validation depth — ✅ EXECUTED 2026-07-18 (§60; 3b awaits the user's form)

- **3a ✅ — the bias lesson:** terrain LR 0.731 CV AUC "beats" the raw physics pixel score
  (0.575) — but drop elevation and it collapses to 0.560: the LR mostly learned the
  corridor reporting bias (valley = where landslides get recorded). Argument FOR the physics
  map's independence; caution for any inventory-trained ML map. `susceptibility_crosscheck.py`.
- **3b — USER ACTION:** GACOS form values printed (`gacos_request.py`); submit → ingest →
  §40 crosscheck.
- **3c ✅:** `data/inventory/temporal_skill_table.csv` — committed, schema-tested, grows per
  §38-rule verification (6 events, all 3 fatal caught at Δ=0 by ≥1 arm).

## Tier 4 — Structural science — partially executed 2026-07-18 (§60)

- **4a ✅ (MARGINAL):** S2 dNDVI back-test on Ardhkuwari — the scar failed to green while the
  AOI greened (deficit 0.185, worst 6.4%): screening-grade, not detector-grade at 20 m;
  upgrade = high-res imagery or CV5 coherence fusion. `optical_change.py`.
- **4b — USER ACTION:** soil M2 lab pass (§42 load-bearing).
- **4c ✅ (probe) → swap SCHEDULED post-merge:** real D8 routing flips **11/22** LLOF flags
  (Ramban 1/8 agree) — the TWI proxy is not a stand-in; do the validated swap as a scored
  re-run after the merge. `flow_routing_probe.py`.
- **4d — DEFERRED (multi-session MintPy compute):** frames-101/102 ERA5 rescue.
- **4e — IN PROGRESS:** merge `aoi-vaishnodevi` → master (PR prepared this session);
  hosted dashboard after.

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

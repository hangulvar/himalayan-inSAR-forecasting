# 🎯 Field Brief — Bhavan overhang (exposed formation above the shrine complex)
*(watchlist target of RESULTS_AND_KPIS §33; toolkit results §34 · prepared 2026-07-08 · companion to the
NE-flank brief of 2026-07-07)*

## What this is

The user-drawn 0.81 km² overhanging formation directly above the Bhavan shrine complex
(`Vaishno_Devi_Bhavan_Overhang.kml`, centroid 33.02750 N 74.95549 E). Product verdict is
**CONDITIONAL** (§33): physics-unstable when saturated (FS_sat ≈ 0.8, slope to 61°) but **no creep
signal** — and none is expected: an overhang is the **brittle/fast failure class** (primer CV3). It gives
no slow-motion warning; it either holds or it goes. This brief covers what we have now built and what a
field visit should do.

## What the toolkit now says (2026-07-08, §34)

**1. Consequence — the runout screen (`rockfall_runout.py`).** An energy-line (shadow-angle) cone from
the overhang on the 12.5 m DEM puts **the Bhavan shrine complex inside the LIKELY band** (reach angle
33.2° ≥ the 32° threshold most fragmental rockfall stops within), the **Bhairon Ghati ropeway station in
the POSSIBLE band** (27.7°), and ~2.3 km of walking route in the LIKELY band. Load
`rockfall_runout_bhavan_overhang_bands.kml` (in `data/alerts_vaishnodevi/mosaic_asc/`) into Google Earth
to see the three bands on the terrain. *First-order screen: no bounce/barrier physics, no
terrain-blocking check — it answers "could a rock physically get there", not "will one".* Given the 2016
history below, this is consistent with how SMVDSB itself treats the site.

**2. Watch — the coherence-drop detector (`coherence_watch.py`).** The pipeline's first fast-failure
instrument: if part of the face fails, the failed surface *decorrelates* between two consecutive 12-day
radar pairs. The script tracks the polygon's coherence against the AOI mean and flags localized sudden
drops on either track. **Current verdict: OK** (4 epochs × 2 tracks, May–Jun 2026 — quiet). Re-run it
every radar cycle:

```
docker compose run --rm insar python workflows/coherence_watch.py \
    --polygons "docs/briefs/Vaishno_Devi_Watchlist/Vaishno_Devi_Bhavan_Overhang.kml" \
    --out-name coherence_watch_bhavan_overhang
```

A DROP flag = "look now": Sentinel-2 before/after (fresh scars are bright at 10 m), then field.

**3. The institutional record (idea #7 cross-check) — this face system is KNOWN.**

- **GSI already flags the brittle class here:** Table-7.1 locations **52, 55, 57** (Bhawan–Sanjichat
  track) lie **315–440 m from the polygon edge**, failure types *"vulnerable to planar and wedge
  failure"*, *"planar along some joint and many wedges"*, *"planar failure"* — exactly the kinematic
  modes an overhang produces. (Distances re-measured to the polygon *edge*, not the centroid.)
- **The complex itself has a treated failure:** on **12 March 2016** the track between the elevator
  point and gate no. 5 at Bhawan was damaged after heavy continuous rain; stabilization took RCC
  retaining walls and **37 pre-stressed cable anchors 26.5–30.5 m deep** (₹5.78 cr, THDCIL/IIT-R/NIRM).
- **A standing programme exists:** SMVDSB has worked with THDCIL on rockfall/shooting-stone mitigation
  **since 2012** (3000–5000 kJ rockfall barriers, rolled cable nets, shelter sheds along most of the
  track) and a tripartite **GSI + THDCIL + SMVDSB MoU** targets the Adhkuwari–Bhawan slopes.

**→ Practical consequence: before instrumenting anything, ask SMVDSB/THDCIL for the treatment as-builts
and inspection records for the slopes above Bhavan.** Parts of this face may already be netted or
anchored — knowing which parts are NOT is the highest-value information a records request can produce.

## Joint tell-tale protocol (idea #3 — turns a photo into a rate)

The cheapest instrument that matches this failure mode. Target: the **2–3 widest open joints behind the
overhang crest** (tension cracks separating the overhanging mass from the intact face).

**Setting up (first visit):**
1. **Choose the joints.** Walk the crest line *above* the overhang; pick the widest continuous open
   joints running roughly parallel to the face edge. Photograph each along its length first.
2. **Three measuring stations per joint** (ends + widest point). At each station:
   - **Painted benchmarks:** a straight line of enamel paint across the joint on both faces, plus a
     dot pair at a measured spacing (record it to the millimetre with a steel ruler or vernier caliper).
   - **Tell-tale (optional but better):** a rigid patch bridging the joint — glass microscope slide or a
     ~10 mm plaster/mortar bridge epoxied to *both* sides. A crack in the tell-tale = movement since
     installation; the offset of the two halves = how much.
   - **Feeler-gauge reading:** joint aperture at the marked spot.
3. **Record per station:** GPS point, dated photo *with a scale object* (coin/ruler), aperture (mm),
   benchmark spacing (mm), joint orientation (dip/dip-direction by compass if possible — this also
   feeds the kinematic analysis, idea #1), and the last-72-h rain.

**Re-reading (monthly + within a few days after every major storm):**
- Photograph each station the same way; re-measure the dot spacing and aperture; note any cracked or
  offset tell-tale. **>1–2 mm of opening between visits, or any sheared tell-tale, is a real signal** —
  report to SMVDSB, and treat the coherence watch + Sentinel-2 as the immediate follow-up.
- A null result is valuable: "0 mm over the monsoon" is exactly the kind of statement the radar cannot
  make for this face.

**Log everything** as dated `field_verified` entries in
`data/inventory/vaishnodevi_documented_landslides.geojson` — back-tests and route exposure re-run from
it, and the product learns from every visit.

## Safety — non-negotiable

- **Do not work on or below the face during or within ~48 h after heavy rain** (the 2016 Bhawan failure
  and the 2025 Ardhkuwari disaster were both rain-driven). Check the live dashboard state first.
- The crest of an overhang is the *worst* place to stand: stay back from the free edge, approach joints
  from the uphill side, two people minimum, helmets, agreed escape route. Never work directly above the
  open complex or the track without SMVDSB coordination — a dislodged pebble here lands on people.
- **Coordinate with SMVDSB first in any case** — this is an operating shrine area with its own safety
  authority, and their records request (above) is step zero anyway.

## What we claim / don't claim

- **Claim:** the formation is physics-unstable when saturated (FS_sat ≈ 0.8 on soil-model physics —
  indicative only for jointed rock); the shrine complex below is within the empirical reach of a fall
  from it; the institutional record documents the same failure classes on this slope system.
- **Not claimed:** that failure is imminent or probable — we have **no motion measurement** (the two
  radar tracks disagree over this steep face; geometric distortion) and no joint kinematics yet. The
  tell-tales + kinematic measurements (ideas #1/#3) are precisely what converts this from "credible
  concern" to a defensible stability statement.

*Artefacts: `coherence_watch_bhavan_overhang.{json,md,png}`,
`rockfall_runout_bhavan_overhang.{png,md,json,_bands.kml,_reach_angle_deg.tif}` in
`data/alerts_vaishnodevi/mosaic_asc/`; context: RESULTS_AND_KPIS §33–§34; records sources: GSI
preliminary note 29.08.2025 Table-7.1; Wani et al., Crimson AMMS (slope-stabilization assessment,
SMVDSB/THDCIL); SMVDSB tripartite-MoU press reporting.*

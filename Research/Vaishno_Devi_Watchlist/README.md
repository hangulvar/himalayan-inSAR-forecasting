# Vaishno Devi Watchlist — user-drawn field targets

Hand-drawn polygons (Google Earth Pro → KML) of formations worth watching, scored against the
current radar+physics product with:

```
docker compose run --rm insar python workflows/polygon_stats.py \
    --polygons "Research/Vaishno_Devi_Watchlist/<file>.kml" --out-name <name>
```

Reports land in `data/alerts_vaishnodevi/mosaic_asc/<name>.{md,json}`. To add several polygons at
once, save the whole Google Earth *folder* as one KML.

## Current targets

**Bhavan overhang** (`Vaishno_Devi_Bhavan_Overhang.kml`, drawn 2026-07-07) — 0.81 km² exposed
overhanging formation above the shrine complex, centroid 33.02750 N 74.95549 E. Product verdict
(2026-07-07): **CONDITIONAL** — FS_saturated ≈ 0.8 (fails when soaked), slope to 61°, mostly
WATCH-class pixels, worst-case zone 177 m away, **no 2-track creep** — and the LOS velocities over
this steep face disagree between tracks (geometry distortion), so the radar can neither clear nor
corroborate it. Registered in the site inventory as a `user_observed_vulnerable_location`.

## How to test this location's risk better (ideas, roughly by cost)

An overhang is the **brittle/fast failure class** (primer CV3): it gives no slow creep to measure,
so more InSAR of the same kind won't settle it. What would:

1. **Kinematic rock-slope analysis — the right physics.** Our FS number comes from a *soil*
   infinite-slope model; for jointed rock it is only indicative. Measure joint set orientations
   (field compass, or from photos via structure-from-motion) and test them against the face
   orientation for planar / wedge / toppling feasibility — a half-day exercise that produces a
   defensible stability statement for THIS face.
2. **Repeat photogrammetry.** A phone/drone photo set from fixed viewpoints, repeated monthly and
   after every big storm, run through structure-from-motion → cm-scale 3-D change detection. The
   cheapest instrument that actually matches this failure mode.
3. **Simple joint monitoring.** Tell-tales / painted benchmarks / feeler-gauge readings across the
   2–3 widest joints behind the overhang (same protocol as the NE-flank field brief) — turns a
   photo into a rate.
4. **Radar coherence-drop watch (we can script this).** Fast failures show up as a sudden
   *decorrelation* of the face between consecutive 12-day pairs — the existing `*_corr.tif` products
   already contain the signal; a small per-polygon coherence-timeline script would make this the
   first fast-failure detector in the pipeline (closes part of the CV3 gap).
5. **Post-storm optical pairs.** Sentinel-2 before/after each major burst — fresh rock scars are
   bright and obvious at 10 m.
6. **Rockfall runout model.** A shadow-angle / RocFall-style run from the overhang crest converts
   "unstable face" into "which structures below are in the fall path" — the number SMVDSB would
   actually act on, given the shrine complex sits below.
7. **Institutional cross-check.** GSI's 2022-23 track survey (our inventory's locs 52–70 cover
   Bhawan–Sanjichat) and SMVDSB's own records may already describe this face — ask before
   instrumenting.
8. **Better SAR, eventually.** Tasked high-res SAR (ICEYE/TerraSAR) or NISAR L-band (archive over
   this AOI is just starting — 3 interferograms as of Jul 2026) once a usable stack accumulates.

**Feedback loop:** anything confirmed in the field goes into
`data/inventory/vaishnodevi_documented_landslides.geojson` (dated, `field_verified`) → back-tests
and route exposure re-run → the product learns from every visit.

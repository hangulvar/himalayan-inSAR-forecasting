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
3. ✅ **Simple joint monitoring** *(protocol written 2026-07-08)*. Tell-tales / painted benchmarks /
   feeler-gauge readings across the 2–3 widest joints behind the overhang — full setup + re-reading
   protocol in `Field Brief - Bhavan overhang (2026-07-08).md`. Turns a photo into a rate.
4. ✅ **Radar coherence-drop watch** *(scripted 2026-07-08: `workflows/coherence_watch.py` — the
   pipeline's first fast-failure detector, §34)*. Per-polygon coherence timeline from the 12-day
   `*_corr.tif` pairs; flags localized sudden decorrelation (AOI-relative, so scene-wide rain drops
   don't false-alarm). First run: **OK** on the overhang and both NE-flank creep polygons. Re-run
   every radar cycle (command in the field brief).
5. **Post-storm optical pairs.** Sentinel-2 before/after each major burst — fresh rock scars are
   bright and obvious at 10 m. (The follow-up step whenever #4 flags a DROP.)
6. ✅ **Rockfall runout model** *(scripted 2026-07-08: `workflows/rockfall_runout.py`, §34)*.
   Energy-line cone from the overhang: **the shrine complex is inside the LIKELY (≥32°) band**, the
   ropeway ghati station POSSIBLE, ~2.3 km of route LIKELY. Bands KML for Google Earth:
   `data/alerts_vaishnodevi/mosaic_asc/rockfall_runout_bhavan_overhang_bands.kml`.
7. ✅ **Institutional cross-check** *(done 2026-07-08, §34)*. GSI Table-7.1 locs 52/55/57 sit
   315–440 m from the polygon edge with planar/wedge failure types; the Bhawan complex itself had a
   treated failure on 12 Mar 2016 (37 deep cable anchors); SMVDSB+THDCIL rockfall programme since
   2012 + tripartite GSI MoU. **Ask SMVDSB/THDCIL for treatment as-builts before instrumenting.**
8. **Better SAR, eventually.** Tasked high-res SAR (ICEYE/TerraSAR) or NISAR L-band (archive over
   this AOI is just starting — 3 interferograms as of Jul 2026) once a usable stack accumulates.

**Feedback loop:** anything confirmed in the field goes into
`data/inventory/vaishnodevi_documented_landslides.geojson` (dated, `field_verified`) → back-tests
and route exposure re-run → the product learns from every visit.

# 🎯 Field Inspection Brief — Confirmed-creep target on the Trikuta NE flank
*(the "CORE route segment" of RESULTS_AND_KPIS §30/§32 · prepared 2026-07-07 · InSAR product of 2026-01→06)*

## What this is

Of everything our radar product flags in the Vaishno Devi corridor, this is the **single most
measurement-credible target**: the only place where **two independent Sentinel-1 tracks agree** the ground
is creeping **AND** a mapped footpath passes directly through it. It has **not** been checked against any
ground truth (the GSI inventory doesn't sample this flank) — that is exactly what a field visit provides.

**Location (be precise — earlier notes said "above Bhairon top"; it is actually on the massif's NE
flank):** ~4.2 km NE of the Bhairon temple / ~3.6 km NE of Bhawan, at **1,570–1,615 m elevation**, along
an unnamed mapped footpath (OpenStreetMap `way/1064002141`) that leaves the shrine area heading NE. The
path's exposed stretch is ~800 m starting near `33.05761 N, 74.95863 E`.

## The polygons (WGS-84 lon, lat — load `bhairon_core_creep.kml` into Google Earth / any GPS app)

**AREA A — the primary target (cluster 46).** 5 pixels ≈ **3.2 ha**, slope ~31°, elev 1574–1613 m,
nearest point ~80 m from the path. **Both tracks agree: median −43 and −45 mm/yr** (peaks −56 / −50) —
~4–5 cm/yr of motion away from both satellites, consistent with downslope creep. Corner vertices:

```
74.958437, 33.060908
74.958437, 33.060186
74.960151, 33.060187
74.960152, 33.058744
74.961009, 33.058744
74.961008, 33.060909   (close ring → 74.958437, 33.060908)
centroid: 33.060115 N, 74.960065 E
```

**AREA B — secondary, on the path itself (cluster 49).** 1 pixel ≈ 0.6 ha, slope ~26°, elev ~1576 m,
**0 m from the path** (it crosses it). ⚠️ Lower confidence: the two tracks *disagree* (−100 vs −21 mm/yr)
— one may be an unwrapping artifact. Worth 15 minutes since you'll walk through it anyway.

```
74.961866, 33.057301
74.961866, 33.056579
74.962723, 33.056580
74.962723, 33.057301   (close ring)
centroid: 33.056940 N, 74.962295 E
```

**Honest print on the map's edge:** pixels are **80 m** — treat every polygon edge as ±80 m; walk a
buffer, not a line. **Note on Area A's shape:** the cluster is L-shaped, so its geometric *centroid pin
falls in the notch outside the creeping pixels* — navigate by the polygon outline, not the centre pin.

## ⚠️ SETTLEMENT EXPOSURE (added 2026-07-07, after user review in Google Earth)

**Area A overlaps/abuts a small settlement.** OpenStreetMap shows **62 mapped buildings within 1.5 km of
Area A's centroid — the closest at 87 m** (33.06039 N, 74.96094 E), i.e. within one pixel of the creeping
ground; nearest named locality **Panchari Gali** (810 m W). This upgrades the target from *path exposure*
to *settlement exposure*: the inspection should include the buildings — wall/foundation cracks, doors and
windows that no longer close square, deformed water channels/terraces — and, if residents are present,
their memory of cracks, spring behaviour and past slips (local knowledge is dated ground truth).

**Coordinate verification (2026-07-07):** an independent round-trip re-check sampled every raster at the
published coordinates: Area A interior points return exactly the published values (≥2 looks, HIGH class,
−56/−50 and −50/−45 mm/yr on the two tracks), an independent clustering pass reproduces the polygon
identically, and an off-site control returns background. The coordinates stand.

## What to check (in priority order)

**1. Tension cracks & scarps (the #1 creep indicator).** Walk the slope *above and inside* Area A looking
for arcuate or en-echelon cracks, fresh soil steps, small scarps. For each: GPS point, width (use a coin /
tape for scale in photos), orientation, and whether edges look **fresh** (sharp, unvegetated) or old
(rounded, grassed over).

**2. The toe.** Below Area A: bulging ground, over-steepened fresh faces, disturbed/tilted debris — creep
pushes its toe outward.

**3. Trees & poles ("drunken forest").** Consistently tilted or J-curved trunks = long-lived creep;
freshly leaning trees/poles with cracked root collars = recent acceleration. Note tilt direction — it
should point downslope, matching the radar's motion sense.

**4. The path surface itself (especially through Area B).** Cracks crossing the path, displaced or
rotated steps/kerbs/retaining stones, stretched or sheared fences/railings, repairs that have re-cracked.

**5. Water (the trigger).** Springs, seeps, damp patches on a dry day, blocked or overflowing drains,
ponding above the slope. Wet ground here is the mechanism that turns creep into failure (our FS physics) —
map every seep.

**6. Material.** Note whether the ground is Trikuta dolomite bedrock or **Vaishnodevi-Formation scree**
(loose vs compacted — the GSI note says both occur): scree creeps and fails much more readily. A phone
photo of a fresh exposure is enough.

**7. Rockfall evidence.** Fresh (unweathered, light-coloured) rock scars above, fresh debris on/below the
path.

**8. Leave benchmarks for round two.** Paint marks or pegs on both sides of the 2–3 best cracks, measure
the gap, photograph with date. A repeat visit after the monsoon turns "it's cracked" into "it opened
12 mm in 8 weeks" — which is exactly the number our radar rate (~4–5 cm/yr) can be checked against.

**Record for every observation:** GPS-tagged photo, date/time, and the last-72-h rain (the dashboards log
it; note it in the field too).

## Safety — non-negotiable

- **Do not inspect during or within ~48 h after heavy rain** — this is an active-monsoon site and our own
  alarm concept says rain is the trigger. Check the live dashboard state before departure
  (`operational_alarm_dashboard_vaishnodevi_2026.html`; DORMANT as of 30 Jun 2026).
- Two people minimum; stay off the steep face *below* any fresh crack or scar; agree an escape route
  uphill/laterally before entering the slope; helmets where rock rises above you.
- Coordinate with SMVDSB / local authorities — the GSI note shows they hold prior reports on these tracks.

## What the radar does and doesn't claim (read before concluding anything)

- **Claim:** ~4–5 cm/yr of slow, persistent motion during Jan–Jun 2026, seen independently by two viewing
  geometries (Area A). That is a *creep* signal, not a prediction of failure or a failure date.
- **Not claimed:** imminent failure; the exact boundary (±80 m); the motion's full 3-D direction (we
  measure along the satellites' lines of sight); rates better than ±~2 cm/yr (the chains are only ~7 weeks
  of scenes; the rate will firm up every 12 days).
- **Absence of surface cracks would NOT disprove the signal** (deep-seated creep can show little at the
  surface) — but presence of items 1–5 above would strongly corroborate it.

## What happens with your findings

Confirmed features (cracks/scarps/seeps with GPS) get added as dated, `field_verified` entries to
`data/inventory/vaishnodevi_documented_landslides.geojson` → the back-tests re-run → this becomes the
first *non-corridor* ground truth for the site, testing exactly the part of the product (the 2-track creep
core) the current inventory cannot. A null result is equally valuable — it gets recorded just as plainly.

*Artefacts: `data/alerts_vaishnodevi/mosaic_asc/bhairon_core_creep.{geojson,kml}` (regenerable); context:
RESULTS_AND_KPIS §30–§32, route_exposure.md row 1.*

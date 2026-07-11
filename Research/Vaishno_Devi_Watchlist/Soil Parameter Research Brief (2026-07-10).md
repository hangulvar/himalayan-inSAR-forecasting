# Research Brief — Soil / material shear-strength parameters for the Vaishno Devi (Trikuta) shrine corridor

**Purpose (why this matters).** We run a physics-based landslide hazard model (infinite-slope
Factor of Safety) over the Katra → Banganga → Adhkuwari → Sanjichhat → Bhawan → Bhairon corridor on
the **Trikuta massif, Jammu & Kashmir** (~32.99–33.03 °N, 74.94–74.95 °E, elevation ~800–1,600 m).
Every FS number this site produces currently uses soil strength values **borrowed from a different
site** (the GSI Ramban/Doda NH-244 study, φ≈36°). We want to **replace those borrowed values with
Trikuta-specific ones** so the hazard map is calibrated to this ground, not an assumption. Any
credible measured or site-specific published value is an improvement over what we have.

**Geological setting to target.** The Trikuta hills are dolomitic **limestone/carbonate** of the
Great Himalayan / Sirban–Trikuta belt, mantled by **colluvium, scree, talus and weathered
overburden** on the slopes and along the paved pilgrim track. The failures of concern are **shallow
translational slides, debris/scree slips, and cut-slope/rockfall along the track** — i.e. the
strength of the *overburden and weathered mantle* (0.5–20 m thick) matters more than intact rock.

## The five parameters we need (with the role each plays in the model)

| Parameter | Symbol / units | Currently (borrowed) | What it controls |
|---|---|---|---|
| **Friction angle** | φ, degrees | 36° (GSI Ramban/Doda) | The dominant strength term; sets how steep a slope can stand when saturated. |
| **Dry / unsaturated cohesion** | c_dry, kPa | 18.5 kPa | Apparent cohesion (true cohesion + matric suction) in dry soil — the "strong when dry" end. |
| **Saturated cohesion** | c_wet, kPa | 5 kPa | Effective cohesion once fully wet and suction is gone — the "weak when soaked" end. |
| **Soil unit weight** | γ, kN/m³ | 19 | Bulk density of the overburden (driving weight). |
| **Failure depth** | z, m | 3 m | Depth of the shallow translational failure plane. |

We model wetting explicitly, so the **dry-vs-wet contrast** is especially valuable: any source that
reports how the soil's cohesion / shear strength **degrades on saturation** (e.g. "significant
strength loss when wet", low-plasticity fines) is directly usable.

## What a good answer looks like

For each parameter, please return: **(a)** a value or plausible range, **(b)** units exactly as
reported (watch kPa vs kg/cm² vs kN/m² — flag the unit), **(c)** the material it was measured on
(rock? colluvium? scree? which formation/depth?), and **(d)** the source with enough detail to cite
(author, year, title, DOI/URL, table/page). A range with provenance beats a single confident number.

## Source hierarchy (most trusted first)

1. **Direct geotechnical testing on Trikuta / Katra ground** — triaxial or direct-shear c and φ,
   Atterberg limits, unit weight, SPT. Likely holders: SMVDSB (Shri Mata Vaishno Devi Shrine Board)
   and **THDCIL** slope-stabilisation reports (they have run rockfall/anchor programmes on this
   corridor since 2012); the **Bhawan track cable-anchor design (2016 failure)**; DPRs for the
   Tarakote–Bhawan road, the Katra–Sanjichhat ropeway, and the Udhampur–Srinagar (USBRL) rail works
   nearby.
2. **GSI (Geological Survey of India)** — Bhukosh portal, landslide susceptibility (LSM) memoirs,
   and district resource maps for Reasi/Udhampur that report overburden strength for the
   Trikuta/Sirban carbonates.
3. **Peer-reviewed / thesis literature** on Katra–Reasi or analogous Lesser-Himalaya carbonate
   colluvium slopes (Indian geotechnical & engineering-geology journals, IIT/university theses).
4. **Regional analogues** (only if 1–3 are empty) — measured c/φ for **carbonate-derived colluvium
   and Himalayan scree** in comparable settings, clearly labelled as an analogue, not the site.

## Honest fallback (please do NOT fabricate)

If no Trikuta-specific measurement exists, say so plainly and instead return the **best regional
analogue range** with its provenance — we will keep the value tagged as "borrowed/analogue" rather
than pretend it is site-measured. A confirmed "no site data found" is itself a useful result.

## Already assessed — do NOT re-tread, build on it (added 2026-07-11, see RESULTS_AND_KPIS.md §36)

- **GSI Spl. Pub. 107 §5.3.1** (VD meso-scale LSM): checked in depth — **no c/φ/γ** (SMR-based
  rock-mass zonation, not lab geotech). Useful context only.
- **Best analogues found so far** (cite-able, but NOT measured on Trikuta): Chenab Bridge fault
  gouge, Reasi — *same Sirban Dolomite formation*, c′ = 5.9–17.65 kPa, φ′ = 31.8°; Ramban–Gool
  debris — γ = 18–20 kN/m³, c = 10–16 kPa, φ = 23–37°. Beat these, don't just re-find them.

**Priority leads to chase first (most likely to hold Trikuta-specific values):**
1. *"Geotechnical Evaluation of Landslides Along Pathways of Sri Mata Vaishnao Devi Hills, Jammu,
   India"* — ResearchGate publication 277775139.
2. *"Assessment of the Various Slope Stabilization Initiatives Undertaken along the Pathways of
   Shri Mata Vaishno Deviji Shrine"* — ResearchGate 373842077 / Crimson AMMS.000775 (stabilisation
   *design* reports normally state assumed/measured c–φ for anchors/nets).
3. The unpublished **GSI Field Season Programme report (Kumar)** underlying Spl. Pub. 107 §5.3.1,
   via GSI / Bhukosh.

**⚠ Date-verification rule:** a prior research pass produced an impossible future-dated event
("September 2026 Panchi landslide"). Verify every event date against a primary source before
reporting it; flag anything you cannot verify. (Project has been burned by a wrong date before —
it inverted a conclusion.)

## Bonus (nice to have, not required)

- A **soil / regolith depth** or overburden-thickness map or estimate for the corridor (refines z).
- Any note on **plasticity / fines content** and **saturation-driven strength loss** (calibrates the
  dry→wet cohesion split).
- Whether any stretch is already **engineered** (soil nailing, anchors, shotcrete, rock nets) — such
  as-builts change what "natural" strength means locally.

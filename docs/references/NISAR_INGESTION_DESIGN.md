# 🛰 NISAR L-band Ingestion — Design & Integration Path

*(2026-08-11, §83. Companion to `workflows/nisar_ingest.py` + `tests/test_nisar_ingest.py`.
Ledger: §81 the winter L-vs-C result, §82 the monsoon void, §80 why C-band alone is not enough.)*

## Why this exists

C-band cannot see **29.4%** of Vaishno Devi's path-27 ground; on that blind ground L-band still
reads a median coherence of **0.655** and recovers **86.5%** of it (§81). Meanwhile every C-band
configuration we can build scores **below chance** against the inventory (§80). So the sensor
route is the way out, and this is the plumbing that turns that finding into a product.

**Scope discipline:** the adapter is BUILT and TESTED; NISAR is **not wired into any live
product**. Building further today would be building ahead of the data — see *Triggers* below.

## The core design decision: NISAR is its own STACK

A NISAR GUNW is already a geocoded interferogram, so it does not need a new pipeline — it needs
to look like a Phase-1 product. It then enters the existing chain as an additional **stack**, and
joins the others only at the union mosaic (which already merges stacks across different map
projections).

```
GUNW .h5 ──nisar_ingest.adapt──> data/qa_masks/<product>/<product>_masked_disp.tif   (LOS m)
                                 data/qa_masks/<product>/<product>_corr.tif          (coherence)
                                 data/qa_masks/_stack_manifest.json   (product -> stack)
                                          │
        (unchanged) sbas_network_graph → custom_sbas_inverter --stack NISAR_ASC_track156_frame018
                    → geomechanical_engine → agentic_orchestrator → union mosaic
```

**Why NOT `data/processed_tiffs/`** — the first attempt put the coherence there and the battery
caught it. That directory is the **HyP3 extraction library** and carries a contract:
`test_plumbing.test_product_dirs_carry_all_layers_and_metadata` requires 6 specific layers
(`_unw_phase`, `_corr`, `_dem`, `_lv_theta`, `_lv_phi`, `_water_mask`) plus the HyP3 metadata
`.txt` in every product dir. A GUNW has none of the look-vector or DEM layers, so living there
would mean either breaking that contract or **fabricating layers we do not have**. NISAR
artifacts therefore stay entirely under `qa_masks/`. The manifest is deliberately still shared —
the inverter resolves every product's stack from that one file — so it now carries a `source`
field, and the HyP3-contract tests scope themselves by it.

Stacks are named `NISAR_<ASC|DESC>_track<T>_frame<F>` — prefixed so they can never collide with
an S1 stack name in the shared manifest (a collision would silently mix two bands into one
inversion; pinned by a test).

## What is VERIFIED (measured on the real granules, not assumed)

| fact | value | why it matters |
|---|---|---|
| CRS | **EPSG:32643** | identical to our C-band products — no reprojection |
| Posting | **80 m** | identical — no resampling |
| Wavelength | **0.241963 m** (from `centerFrequency` 1.239 GHz) | **4.36×** the C-band 0.055466 m |
| Adapter output | 14–42 MB/product (LZW) | 3 granules ≈ 165 MB |
| Survivor pixels @ γ≥0.4 | winter **39.9%**, monsoon 15.0% / 14.5% | matches the §82 void story |

**The trap this design avoids.** `feature_engineering.phase_to_los_displacement` multiplies by a
**hardcoded** `SENTINEL1_WAVELENGTH_M`. Routing L-band phase through it would under-report every
displacement by ~4.4× — silently, and with entirely plausible-looking numbers. `nisar_ingest`
therefore does its own conversion with the wavelength **read from the granule**, and
`test_using_the_C_band_constant_on_L_band_would_underreport_4x` pins both the correct factor and
the size of the avoided error.

## Remaining integration steps, each with its TRIGGER

Nothing below should be built before its trigger fires.

| # | Step | Trigger | Effort |
|---|---|---|---|
| 1 | ✅ **Adapter + downloader + tests** | done (§83) | — |
| 2 | **Broaden the pair-date parsers.** `custom_sbas_inverter.parse_pair_dates` matches `S1[A-D][A-D]_…`; the §61 precedent broadened `S1AA`→`S1[A-D][A-D]` across **5 files**. Our product name already satisfies `(?:S1[A-D][A-D]\|NISAR)_<date>T<time>_<date>T<time>_` (test-pinned). | the first NISAR **inversion** | ~1 line × 5 files |
| 3 | **Atmospheric audit exemption.** `phase_elevation_audit.find_inputs` globs `*_dem.tif`, which a GUNW does not carry, so NISAR products are silently skipped. Either write a DEM alongside, or make the audit record `not_applicable` rather than skipping quietly. | same as #2 | small |
| 4 | **Per-band wavelength in `feature_engineering`** — only if NISAR is ever routed through it rather than bypassing it. Today the adapter writes `masked_disp` directly, so this is NOT required. | routing NISAR through Phase 1 | small, but touches a validated script |
| 5 | **Config: opt a site into an L-band stack**, mirroring `period_split:` (registry-driven, so a plain run reproduces it). | when a NISAR stack is worth publishing | small |
| 6 | **Velocity series.** Needs a connected network on ONE track/frame. | **≥8 acquisitions** on `track156/frame018` | the real gate |

## The blocker today is data volume, not code

- **8 GUNW acquisitions** exist over the AOI; on our track/frame we hold **3** granules.
- **All are provisional (`_PR_`); 0 final products exist** (§82).
- Two of the three monsoon granules are **data voids** over both AOIs (§82) — systematic to the
  `P05023` provisional batch, confirmed on two consecutive acquisitions.

So a velocity series is not buildable yet, and the honest position is: **the adapter is ready and
waiting on NASA's cadence and reprocessing**, not on us.

## What NOT to do

- **Do not** route NISAR phase through the C-band converter (step 4's trap).
- **Do not** lower the pilot's 40% coverage floor to score a voided granule (§82).
- **Do not** mix NISAR and S1 products inside one stack — different wavelengths, different
  sensitivity to the same ground motion.
- **Do not** build steps 2–6 before their triggers; with 3 granules there is nothing to invert.

## How to run it

```bash
docker compose run --rm insar  python workflows/nisar_ingest.py --list
docker compose run --rm insar  python workflows/nisar_ingest.py --download <granule>
docker compose run --rm mintpy python workflows/nisar_ingest.py --adapt-all
```

`--list`/`--download` need only `asf_search` (lean image); `--adapt` needs h5py **and** GDAL, which
only the **mintpy** image has together — the lean image carries rasterio but not h5py, which is why
the adapter writes rasters with GDAL rather than rasterio.

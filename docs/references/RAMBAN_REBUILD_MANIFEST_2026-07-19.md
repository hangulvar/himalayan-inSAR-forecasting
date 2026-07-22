# Ramban cadence-rebuild manifest (2026-07-19) — SUBMITTED 2026-07-22

The §57 follow-through: everything needed to run the unblocked Ramban rebuild, verified
through the production submitter in dry-run. **Headline: the rebuild needs 3 submitted
pairs (~30 credits), not the naive 10 (~100) — most "new" radar is already on disk.**

## ✅ SUBMITTED 2026-07-22 (user-authorized 30-credit spend) — jobs RUNNING at ASF

All 3 pairs submitted (0 dupes, 0 failed); **credits 7,460 → 7,430 (exactly 30 spent)**,
verified independently via `find_jobs`. Job ids:

| Job name | Pair | HyP3 job_id |
|---|---|---|
| Ramban_NH44_ASCENDING_path27_frame106 | 20260419 × 20260501 (f106 bridge) | 03d8160a-8069-445c-a2cf-c4e09a16a0c7 |
| Ramban_NH44_ASCENDING_path100_frame102 | 20260424 × 20260506 (f102 bridge) | fb7123a4-53da-468a-99f5-7713a9d88dbf |
| Ramban_NH44_ASCENDING_path27_frame105 | 20260618 × 20260625 (S1A×S1D seam) | 12407651-193e-4f0c-837b-4ec474bfddcb |

**✅ 2026-07-22 — all 3 SUCCEEDED (~25 min), downloaded + extracted + QA'd. Both gates passed
for all 3, incl. the S1A×S1D seam — de-risked. All coherence/atmospheric numbers: ledger §61.**
(One retry: the seam zip arrived corrupt on the first pull; the script auto-deleted it and the
re-fetch was clean — its own idempotent recovery path.) Manifest ingested all 3 with the right
stack labels (bridges extend f106/f102; seam tagged f105); library 235→238.
**Next: the rebuild loop below (inversion + seam-velocity cross-check + re-score) —
judgment-heavy, not run headlessly.**

## What the manifest work found (all `[MEASURED]` 2026-07-19)

1. **Sentinel-1 frame numbering DRIFTED in May 2026** (alongside the §56 constellation
   handover): over our AOIs, path-27 scenes are now framed **105** (was 106+101) and
   path-100 scenes **103** (was 102); DESC path-34 is now 480/485 (was 484/479). The
   per-frame bucket logic therefore starts NEW stacks for new scenes — the reason
   Ramban's map sat "12 weeks stale" while radar kept arriving.
2. **The May–June products already exist in the shared library** — the 2026-07-10 VD
   backfill (§35) processed them under the VD prefix: `ASC_path27_frame105` (5 dates,
   1 May→18 Jun) and `ASC_path100_frame103` (5 dates, 6 May→23 Jun). Their footprints
   **fully contain the Ramban AOI** (f105: 74.47–77.67 E, 32.42–34.53 N; f103:
   72.51–75.64 E, 31.99–34.05 N — verified from the product rasters).
3. **Cross-AOI dedupe blind spot FIXED:** the submitter's dedupe was prefix-filtered, so
   a Ramban-window dry-run planned 9 pairs the VD backfill had already processed
   (~90 credits of duplicates). `fetch_existing_pair_signatures` is now prefix-AGNOSTIC
   (the library is shared — any prefix's job dedupes); regression-verified: the same
   dry-run now reads "10 planned, 9 skipped as duplicates".
4. **New `--pair REF,SEC` submitter mode** (repeatable, dry-run/dedupe/retry as usual;
   job name derives from the REFERENCE scene's direction/path/frame): frame-drift
   bridges and cross-unit seam pairs can never be built by the per-frame bucket logic.
   Suite `tests/test_submit_pairs.py` (5 tests, hermetic).

## The manifest — 3 pairs, all dry-run verified 2026-07-19 (auth OK, credits 7,460)

| # | Purpose | Reference | Secondary | Δt |
|---|---|---|---|---|
| 1 | Path-27 frame bridge (f106→f105) | S1A_IW_SLC__1SDV_20260419T125645_20260419T125712_064149_0812DA_D9E0 | S1A_IW_SLC__1SDV_20260501T125637_20260501T125704_064324_081956_47FF | 12 d |
| 2 | Path-100 frame bridge (f102→f103) | S1A_IW_SLC__1SDV_20260424T130435_20260424T130502_064222_081581_0932 | S1A_IW_SLC__1SDV_20260506T130443_20260506T130510_064397_081BFC_F349 | 12 d |
| 3 | S1A×S1D cross-unit seam (path 27) | S1A_IW_SLC__1SDV_20260618T125635_20260618T125701_065024_083204_0E69 | S1D_IW_SLC__1SDV_20260625T125553_20260625T125620_003393_005F85_8932 | 7 d |

Cost ≈ 10 credits/job ⇒ **~30 credits** (balance 7,460). Optional 4th pair: frame101's
chain also ends 2026-04-19 (S1A_IW_SLC__1SDV_20260419T125620_20260419T125647_064149_0812DA_CEF5
× the same f105 2026-05-01 secondary) — submit only if the rebuild keeps f101 as a
separate stack rather than letting f105 supersede it. DESC bridges (f484→480/485) are
out of scope: the Ramban product is ASC-only.

## To submit (the user's credit call — one command)

```
docker compose run --rm insar python workflows/submit_hyp3_jobs.py \
  --config data/rebuild/ramban_rebuild_window_2026-07.yaml --submit \
  --pair "S1A_IW_SLC__1SDV_20260419T125645_20260419T125712_064149_0812DA_D9E0,S1A_IW_SLC__1SDV_20260501T125637_20260501T125704_064324_081956_47FF" \
  --pair "S1A_IW_SLC__1SDV_20260424T130435_20260424T130502_064222_081581_0932,S1A_IW_SLC__1SDV_20260506T130443_20260506T130510_064397_081BFC_F349" \
  --pair "S1A_IW_SLC__1SDV_20260618T125635_20260618T125701_065024_083204_0E69,S1D_IW_SLC__1SDV_20260625T125553_20260625T125620_003393_005F85_8932"
```

(Drop `--submit` to re-preview. The window config `data/rebuild/ramban_rebuild_window_
2026-07.yaml` is data-local/git-ignored; it is reproduced below in case of a fresh clone.)

## After the products land (the rebuild loop proper)

1. ✅ `download_hyp3_products.py` → QA chain — DONE 2026-07-22 (§61): 3 products QA-passed.
2. ✅ **Seam cross-check DONE (§61, 2026-07-22).** Frame renumber f106→f105 / f102→f103 = SAFE
   (coherent bridge IFG). **S1A→S1D handover carries a clean −18.6 mm offset → DROPPED by user
   decision: rebuild S1A-only through 18 Jun** (bridges to f105/f103, NOT the S1D seam 0618×0625).
   Revisit S1D when a second S1D pass exists. Cross-unit `S1AA_`-parser bug fixed en route
   (error log 2026-07-22).
3. `apply_connectivity_rescues.py` re-run applies the **§43 f106 bridge swap**
   (20250506→20250611 Bperp 151 m → 20250506→20250530 Bperp 102 m) inside its loop.
4. Invert → hazard → union alerts → **re-score vs the GSI inventory** (§16 chain);
   ledger the product shift. The radar-freshness pill clears automatically.

> **DEFERRED to a focused next session (user's call, 2026-07-22).** A faithful S1A-only rescore
> needs the REAL pipeline (steps 3–4) with its pair-metrics cache + rescue-aware cross-frame
> merge — a non-destructive sandbox script cannot reconstruct it (confirmed 3× — see §61 / journey
> S28). **Plan:** back up `data/qa_masks/{_quarantine_list.csv,_stack_manifest.json}` (revert
> path) → `consolidate → apply_connectivity_rescues → run_multistack` (S1A-only) `→ GSI rescore` →
> compare new AUC/recall vs §21b/§44 → accept or restore-and-revert. Diagnostics kept in
> git-ignored `data/rebuild/` (`seam_check.py`, `sandbox_velocity.py`).

## Window config for reproduction (`data/rebuild/ramban_rebuild_window_2026-07.yaml`)

```yaml
aoi_path: config/aoi/ramban_aoi.geojson
site_name: Ramban NH-44
kappa: 0.06
job_name_prefix: Ramban_NH44
search_start: 2026-04-10
search_end: 2026-06-30
soil: {cohesion_dry_kpa: 18.5, cohesion_wet_kpa: 5.0, phi_deg: 36.0,
       gamma_kn_m3: 19.0, depth_m: 3.0}
baseline: {max_temporal_baseline_days: 24, sbas_neighbors: 1, max_perp_baseline_m: 150}
rescue_gate: {max_atmos_r2: 0.45, min_coherence: 0.6, min_surviving_pct: 15}
exclude_from_rescue: []
```

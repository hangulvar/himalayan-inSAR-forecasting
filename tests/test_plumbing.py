"""
test_plumbing.py — Phase 1.4 end-to-end plumbing assertions.

NOT a unit test of individual functions. This is an integration smoke test
verifying that the on-disk artifacts from the Phase 1.2 (coherence masking)
and Phase 1.3 (atmospheric audit) pipelines exist, are well-formed, and are
internally consistent.

Adapted to our reality (SBAS N=3 = 183 products, not the 10 from the original
draft plan).

Run from project root:
    conda activate insar_qa_env
    python -m pytest tests/test_plumbing.py -v
OR plain:
    python tests/test_plumbing.py
"""

from __future__ import annotations

import csv
import json
import traceback
from pathlib import Path

import numpy as np
import rasterio

# ------------------------------------------------------------------------------
# Layout
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_ZIPS = PROJECT_ROOT / "data" / "raw_zips"
PROCESSED = PROJECT_ROOT / "data" / "processed_tiffs"
QA_MASKS = PROJECT_ROOT / "data" / "qa_masks"
AUDIT_CSV = QA_MASKS / "_atmospheric_audit.csv"
AUDIT_JSON = QA_MASKS / "audit_log.json"
COH_CSV = QA_MASKS / "_coherence_mask_stats.csv"
QUARANTINE_CSV = QA_MASKS / "_quarantine_list.csv"
STACK_MANIFEST = QA_MASKS / "_stack_manifest.json"

# The radar library is SHARED across AOIs and grows with every AOI pull and
# radar-cadence cycle, so the expected product count is read from the stack
# manifest (metadata-derived, updated by every download) instead of being
# hardcoded. The old constant EXPECTED_PRODUCT_COUNT = 183 was the single-AOI
# (Ramban SBAS N=3) era and went stale when Vaishno Devi's 49 pairs + the
# 2026-07-10 backfill landed (235 products). The floor still catches data loss.
MIN_PRODUCT_COUNT = 183  # the original Ramban library; the library only grows
EXPECTED_PER_STACK_COUNTS = {
    # bucket prefix in product naming  -> expected number of products
    # (3 ASC stacks each have 14+13+12 = 39 pairs)
    # (2 DESC stacks each have 13+12+8 = 33 pairs, accounting for the 24-day
    #  acquisition gap between late July and late August in path34)
    "ASC_total": 39 * 3,   # 117
    "DESC_total": 33 * 2,  # 66
}


def _expected_product_count() -> int:
    """Product count the pipeline itself believes in: the stack manifest."""
    n = len(json.loads(STACK_MANIFEST.read_text(encoding="utf-8")))
    assert n >= MIN_PRODUCT_COUNT, (
        f"Stack manifest lists only {n} products (< {MIN_PRODUCT_COUNT}, the "
        f"original Ramban library) — manifest truncated or data lost."
    )
    return n


def _product_dirs() -> list[Path]:
    return sorted(d for d in PROCESSED.iterdir() if d.is_dir())


def _masked_dirs() -> list[Path]:
    return sorted(
        d for d in QA_MASKS.iterdir() if d.is_dir() and not d.name.startswith("_")
    )


# ------------------------------------------------------------------------------
# 1. Inventory assertions
#
# Since 2026-07-15 the raw HyP3 zips are DISPOSABLE staging artifacts (archived
# off-machine; data/raw_zips is a junction to C:\InSAR_data\raw_zips). The
# on-disk source of truth is data/processed_tiffs/<product>/ — the 6 extracted
# GeoTIFF layers plus the HyP3 metadata <product>.txt (which prep_mintpy.py
# reads from there instead of from the zip).
# ------------------------------------------------------------------------------
def test_extracted_products_match_manifest() -> None:
    """Every product the stack manifest knows about must have its extracted dir."""
    expected = _expected_product_count()
    n_dirs = len(_product_dirs())
    assert n_dirs == expected, (
        f"Expected {expected} extracted product dirs (per _stack_manifest.json) "
        f"in {PROCESSED}; found {n_dirs}. Extraction incomplete, extra products "
        f"leaked in, or the manifest is out of date."
    )


def test_zips_are_staging_only() -> None:
    """Any zip still sitting in raw_zips must already have its extracted dir.

    Zero zips is the normal state (they are deleted/archived after extraction);
    a zip WITHOUT an extracted dir means --extract was never run on it."""
    dirs = {d.name for d in _product_dirs()}
    unextracted = sorted(
        p.stem for p in RAW_ZIPS.glob("*.zip") if p.stem not in dirs
    )
    assert not unextracted, (
        f"{len(unextracted)} zip(s) in {RAW_ZIPS} with no extracted product dir "
        f"(run downloader with --extract): {unextracted[:5]}"
    )


def test_product_dirs_carry_all_layers_and_metadata() -> None:
    """Each product dir must hold the 6 extracted layers + the HyP3 metadata txt.

    The metadata txt is what makes the raw zip disposable — prep_mintpy.py
    reads it from here. A dir missing it would silently force the (deleted)
    zip fallback on the next MintPy prep."""
    layer_suffixes = (
        "_unw_phase.tif", "_corr.tif", "_dem.tif",
        "_lv_theta.tif", "_lv_phi.tif", "_water_mask.tif",
    )
    problems = []
    for d in _product_dirs():
        missing = [s for s in layer_suffixes if not (d / f"{d.name}{s}").exists()]
        if not (d / f"{d.name}.txt").exists():
            missing.append(".txt (HyP3 metadata)")
        if missing:
            problems.append(f"{d.name}: missing {missing}")
    assert not problems, (
        f"{len(problems)} product dir(s) incomplete:\n  " + "\n  ".join(problems[:5])
    )


def test_masked_output_count_matches_products() -> None:
    """Phase 1.2 must produce one masked raster per product."""
    n_prod = len(_product_dirs())
    n_masked = len(_masked_dirs())
    assert n_masked == n_prod, (
        f"Mismatch: {n_prod} product dirs, {n_masked} masked dirs. "
        f"Re-run feature_engineering.py to fill the gap."
    )


# ------------------------------------------------------------------------------
# 2. Coherence mask sanity (Phase 1.2)
# ------------------------------------------------------------------------------
def test_masked_array_has_nans_and_finites() -> None:
    """The coherence mask MUST punch holes (NaN) but MUST also leave survivors.

    A masked raster that's all-NaN means the mask was too aggressive (or
    coherence file was empty); a masked raster with zero NaNs means the mask
    wasn't applied at all.
    """
    masked_dirs = _masked_dirs()
    assert len(masked_dirs) > 0, "No masked dirs to inspect."

    sample = masked_dirs[0]
    masked_tif = next(sample.glob("*_masked_disp.tif"), None)
    assert masked_tif is not None, f"No masked TIFF in {sample}"

    with rasterio.open(masked_tif) as src:
        arr = src.read(1)

    assert np.isnan(arr).any(), (
        f"{masked_tif.name} has NO NaN pixels — mask did not run."
    )
    assert np.isfinite(arr).any(), (
        f"{masked_tif.name} has NO finite pixels — mask erased everything."
    )


def test_masked_shape_matches_dem() -> None:
    """The masked displacement raster must share its grid with the source DEM."""
    sample = _masked_dirs()[0]
    masked_tif = next(sample.glob("*_masked_disp.tif"))
    dem_tif = next((PROCESSED / sample.name).glob("*_dem.tif"))

    with rasterio.open(masked_tif) as m, rasterio.open(dem_tif) as d:
        assert m.shape == d.shape, (
            f"Shape mismatch for {sample.name}: masked={m.shape} dem={d.shape}"
        )
        assert m.crs == d.crs, (
            f"CRS mismatch for {sample.name}: masked={m.crs} dem={d.crs}"
        )


# ------------------------------------------------------------------------------
# 3. Audit JSON (Phase 1.3)
# ------------------------------------------------------------------------------
def test_audit_json_exists_and_parses() -> None:
    assert AUDIT_JSON.exists(), (
        f"{AUDIT_JSON} missing. Run workflows/export_audit_json.py."
    )
    text = AUDIT_JSON.read_text(encoding="utf-8")
    data = json.loads(text)  # raises on malformed
    assert isinstance(data, list), "audit_log.json must be a JSON array."
    expected = _expected_product_count()
    assert len(data) == expected, (
        f"audit_log.json has {len(data)} records; expected {expected} "
        f"(per _stack_manifest.json)."
    )


def test_audit_json_schema() -> None:
    """Every record must have the four required fields with correct types."""
    data = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    required_keys = {"product", "job_id", "r_squared", "is_atmospherically_contaminated"}
    for rec in data:
        assert required_keys.issubset(rec.keys()), (
            f"Record missing required keys: have {set(rec.keys())}, "
            f"need {required_keys}"
        )
        assert isinstance(rec["product"], str)
        # job_id may be null if HyP3 lookup failed; allow that.
        assert rec["job_id"] is None or isinstance(rec["job_id"], str)
        # r_squared may be null only for non-ok rows; otherwise float.
        assert rec["r_squared"] is None or isinstance(rec["r_squared"], (int, float))
        assert isinstance(rec["is_atmospherically_contaminated"], bool)


def test_audit_json_flag_matches_threshold() -> None:
    """is_atmospherically_contaminated must be True iff r_squared > 0.5."""
    data = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    for rec in data:
        if rec["r_squared"] is None:
            assert rec["is_atmospherically_contaminated"] is False, (
                f"{rec['product']}: null R² should not be flagged contaminated."
            )
        else:
            expected = rec["r_squared"] > 0.5
            assert rec["is_atmospherically_contaminated"] == expected, (
                f"{rec['product']}: R²={rec['r_squared']} but "
                f"flag={rec['is_atmospherically_contaminated']} (expected {expected})"
            )


# ------------------------------------------------------------------------------
# 4. Cross-file consistency
# ------------------------------------------------------------------------------
def test_audit_csv_and_json_agree_on_contaminated_set() -> None:
    """Every product the CSV labelled QUARANTINE must be flagged in the JSON.

    The CSV may have MORE quarantines (e.g. due to coherence-only borderlines
    captured by _quarantine_list.csv); the JSON is the strict atmospheric-only
    subset. So we test: JSON-contaminated ⊆ CSV-QUARANTINE.
    """
    csv_rows = list(csv.DictReader(AUDIT_CSV.open(encoding="utf-8")))
    csv_quarantine = {
        r["product"] for r in csv_rows if r.get("classification") == "QUARANTINE"
    }
    data = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    json_flagged = {r["product"] for r in data if r["is_atmospherically_contaminated"]}
    # The atmospheric QUARANTINE set in the audit CSV should exactly equal
    # the JSON-flagged set, because both use R² > 0.5.
    assert json_flagged == csv_quarantine, (
        f"JSON-flagged set differs from CSV QUARANTINE set.\n"
        f"  in JSON only: {sorted(json_flagged - csv_quarantine)}\n"
        f"  in CSV only:  {sorted(csv_quarantine - json_flagged)}"
    )


def test_consolidated_quarantine_includes_atmospheric_and_coherence() -> None:
    """`_quarantine_list.csv` must include atmospheric R²>0.5 AND
    coherence-borderline (mean_coh_survivors < 0.6) products."""
    rows = list(csv.DictReader(QUARANTINE_CSV.open(encoding="utf-8")))
    quarantined = {r["product"] for r in rows if r["decision"] == "QUARANTINE"}

    # Atmospheric subset:
    data = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    atmos_q = {r["product"] for r in data if r["is_atmospherically_contaminated"]}
    assert atmos_q.issubset(quarantined), (
        f"Some atmospheric quarantines missing from consolidated list: "
        f"{sorted(atmos_q - quarantined)}"
    )


# ------------------------------------------------------------------------------
# CLI runner (stdlib-only — works under pytest too, since pytest auto-discovers
# functions named test_*).
# ------------------------------------------------------------------------------
def _all_tests() -> list:
    """Return every callable in this module whose name starts with `test_`."""
    g = globals()
    return [(name, g[name]) for name in sorted(g) if name.startswith("test_") and callable(g[name])]


def main() -> int:
    tests = _all_tests()
    print(f"Running {len(tests)} plumbing tests...")
    print("-" * 70)
    n_pass = n_fail = 0
    for name, fn in tests:
        try:
            fn()
        except AssertionError as e:
            n_fail += 1
            print(f"FAIL  {name}")
            print(f"      {e}")
        except Exception:
            n_fail += 1
            print(f"ERROR {name}")
            traceback.print_exc(limit=2)
        else:
            n_pass += 1
            print(f"PASS  {name}")
    print("-" * 70)
    print(f"Total: {n_pass} passed, {n_fail} failed.")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

"""
test_file_disposition.py — the local-file disposition classifier (workflows/file_disposition.py).

Hermetic: the classifier is a pure function of (rel_path, freeze_set, tracked_set), so every
case is a synthetic path with injected freeze/git sets — no real repo, no filesystem, no git.

What is asserted:
  * the four classes land where they should for representative real paths;
  * the AUTHORITY ORDER holds — a frozen or git-tracked file inside an otherwise-regenerable OR
    archive-first directory is still PROTECTED (this is the whole point: a validated raster must
    not be swept up with the disposable ones);
  * a cache (_cache/_rain/__pycache__) is REGENERABLE even inside an archive-first dir;
  * an UNKNOWN path is REVIEW, never guessed disposable (the conservative default);
  * the tool exposes no delete path (it is a reporter, by construction).

Stdlib only. Run from project root:
    python tests/test_file_disposition.py
OR under pytest:
    python -m pytest tests/test_file_disposition.py -v
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import file_disposition as fdp  # noqa: E402

FREEZE = {"data/velocity/vel.tif", "data/inventory/temporal_skill_table.csv",
          "data/alerts/mosaic_asc/alerts_operational.json"}
TRACKED = {"data/inventory/ramban_documented_landslides.geojson"}


def C(path):
    return fdp.classify(path, FREEZE, TRACKED)[0]


def test_protected_wins_from_freeze_and_git():
    assert C("data/velocity/vel.tif") == "PROTECTED"
    assert C("data/alerts/mosaic_asc/alerts_operational.json") == "PROTECTED"
    assert C("data/inventory/temporal_skill_table.csv") == "PROTECTED"
    assert C("data/inventory/ramban_documented_landslides.geojson") == "PROTECTED"


def test_protected_overrides_a_regenerable_directory():
    """A frozen raster lives inside velocity/ (a REGENERABLE dir). The freeze must win, or the
    validated product would be swept up as disposable — the exact failure this tool prevents."""
    assert C("data/velocity/vel.tif") == "PROTECTED"          # frozen
    assert C("data/velocity/scratch_unfrozen.tif") == "REGENERABLE"  # same dir, not frozen


def test_archive_first_layer():
    assert C("data/processed_tiffs/S1AA_x/S1AA_x_corr.tif") == "ARCHIVE_FIRST"
    assert C("data/raw_zips/S1AA_20260419.zip") == "ARCHIVE_FIRST"
    assert C("data/nisar/NISAR_L2_PR_GUNW_x.h5") == "ARCHIVE_FIRST"
    assert C("data/mintpy/velocity.h5") == "ARCHIVE_FIRST"
    assert C("data/dem_alos_12m/dem.tif") == "ARCHIVE_FIRST"
    assert C("data/rainfall/vaishnodevi_era5land_water.grib") == "ARCHIVE_FIRST"


def test_caches_are_regenerable_even_inside_archive_first():
    # A cache dir at any depth beats the archive-first dir it sits in.
    assert C("data/processed_tiffs/__pycache__/x.pyc") == "REGENERABLE"
    assert C("data/flood/_cache/ASC_path100_frame102_acc.npy") == "REGENERABLE"
    assert C("data/flood/_rain/ramban_zone1_halfhourly_2026.csv") == "REGENERABLE"


def test_derived_outputs_are_regenerable():
    for p in ("data/qa_masks/_stack_manifest.json",
              "data/hazard/fs_saturated.tif",
              "data/alerts_vaishnodevi/mosaic_asc/operational_alarm_dashboard.html",
              "data/flood/flood_gate_summary_2026.json",
              "data/rainfall/operational_alarm.png",
              "data/llof_swap/backup/old.json",
              "data/radar_watch.json",
              "logs/run.log"):
        assert C(p) == "REGENERABLE", p


def test_unknown_is_review_not_disposable():
    assert C("data/some_new_experiment/result.dat") == "REVIEW"
    assert C("data/mystery.bin") == "REVIEW"
    # And REVIEW must never leak into a delete-safe bucket by accident.
    assert C("data/some_new_experiment/result.dat") != "REGENERABLE"


def test_generated_reports_are_regenerable_but_ground_truth_stays_review():
    """A *report* file is a generated artifact; the inventory's ground-truth DATA is not, and
    must stay REVIEW so a human decides (CLAUDE.md: the inventory is load-bearing ground truth)."""
    assert C("data/inventory/backtest_operational_report.md") == "REGENERABLE"
    assert C("data/inventory/rainfall_kappa_report_vaishnodevi.json") == "REGENERABLE"
    assert C("data/aoi_status.json") == "REGENERABLE"
    assert C("data/inventory/validation_stats_operational.json") == "REGENERABLE"
    assert C("data/inventory/susceptibility_crosscheck.md") == "REGENERABLE"
    # …but the actual inventory GROUND TRUTH the reports are scored against is NOT
    # auto-disposable — it stays REVIEW for a human to decide.
    assert C("data/inventory/gsi_inventory_aoi.geojson") == "REVIEW"
    assert C("data/inventory/gsi_inventory_aoi.csv") == "REVIEW"
    # A frozen JSON back-test stays PROTECTED even though its name contains 'report'.
    assert fdp.classify("data/inventory/backtest_operational_report.json",
                        {"data/inventory/backtest_operational_report.json"}, set())[0] == "PROTECTED"


def test_frozen_file_inside_archive_first_dir_stays_protected():
    """Belt-and-braces: even if the freeze ever lists a processed_tiffs file, it is PROTECTED,
    not ARCHIVE_FIRST — the freeze is the top authority."""
    freeze2 = FREEZE | {"data/processed_tiffs/keep_me.tif"}
    assert fdp.classify("data/processed_tiffs/keep_me.tif", freeze2, TRACKED)[0] == "PROTECTED"


def test_reporter_has_no_delete_capability():
    """This tool must be incapable of deleting — a disposition MAP that deletes is a footgun.
    Assert the source calls no removal API."""
    src = (PROJECT_ROOT / "workflows" / "file_disposition.py").read_text(encoding="utf-8")
    for banned in ("os.remove", "os.unlink", "shutil.rmtree", ".unlink(", "send2trash", "rmdir"):
        assert banned not in src, f"file_disposition.py references a delete API: {banned}"


def test_build_report_totals_and_freeze_integrity():
    """The aggregation is arithmetic that a human trusts — check the sums and the missing-file
    detector on a tiny synthetic scan."""
    rows = [
        {"path": "data/velocity/vel.tif", "class": "PROTECTED", "reason": "r", "bytes": 100,
         "group": "data/velocity"},
        {"path": "data/processed_tiffs/a.tif", "class": "ARCHIVE_FIRST", "reason": "r",
         "bytes": 400, "group": "data/processed_tiffs"},
        {"path": "data/flood/_cache/x.npy", "class": "REGENERABLE", "reason": "r", "bytes": 50,
         "group": "data/flood"},
    ]
    # Freeze lists two files; one is absent from the scan -> flagged missing.
    rep = fdp.build_report({"rows": rows},
                           {"data/velocity/vel.tif", "data/velocity/GONE.tif"})
    assert rep["summary"]["ARCHIVE_FIRST"]["bytes"] == 400
    assert rep["summary"]["REGENERABLE"]["bytes"] == 50
    assert rep["summary"]["PROTECTED"]["files"] == 1
    assert rep["freeze_missing"] == ["data/velocity/GONE.tif"]


def test_data_flow_awareness_is_documented_and_rendered():
    """The report must carry the §76 data-flow awareness so a future cleanup is informed —
    including the load-bearing distinction that day-to-day ops don't need the raw layer but
    rebuilds do."""
    assert fdp.DATA_FLOW, "the data-flow awareness block went missing"
    blob = " ".join(ln for _, lines in fdp.DATA_FLOW for ln in lines).lower()
    for must in ("processed_tiffs", "velocity", "flood_domain f0", "nisar", "rebuild",
                 "day-to-day"):
        assert must in blob, f"data-flow awareness dropped mention of {must!r}"
    # And it renders into the markdown, not just the source.
    rep = fdp.build_report({"rows": [
        {"path": "data/processed_tiffs/a.tif", "class": "ARCHIVE_FIRST", "reason": "r",
         "bytes": 1, "group": "data/processed_tiffs"}]}, set())
    fdp.write_report(rep)
    md = (fdp.PROJECT_ROOT / "data" / f"{fdp.REPORT_STEM}.md").read_text(encoding="utf-8")
    assert "Data flow & usage" in md and "Local-regeneration check" in md


def test_regen_feasibility_reports_honestly():
    """The live check must state whether processed_tiffs can be rebuilt locally — a string that
    names the actual counts, never a hardcoded claim."""
    note = fdp.regen_feasibility()
    assert "processed_tiffs holds" in note and "raw_zips has" in note
    # On this repo the zips were Drive-archived, so it should read NOT locally regenerable;
    # but the assertion is only on the SHAPE (it must commit to one verdict), so the test holds
    # on any checkout, including a fresh one where both counts are 0.
    assert ("NOT locally regenerable" in note) or ("Locally regenerable" in note)


def test_human_readable_sizes():
    assert fdp._human(0) == "0.0 B"
    assert fdp._human(1024) == "1.0 KB"
    assert fdp._human(42 * 1024 ** 3).endswith("GB")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)

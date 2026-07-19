"""
test_radar_watch.py — the radar watcher (radar_watch.py) + the dashboard radar-freshness
pill (operational_alarm.radar_status / write_dashboard). Hermetic except where noted: the ASF
query itself is never called — summarize_new is pure, and the one data-dependent test reads
the local stack manifest (same class of on-disk dependency as test_plumbing).

What is asserted:
  • library_newest returns the youngest acquisition among ONLY the footprint's source stacks,
    parsed from real product names (and both real AOIs yield a sane 2025+ date);
  • summarize_new counts strictly-newer ASC scenes, tracks per-path newest and the new units,
    and handles the no-library edge (new AOI) gracefully;
  • radar_status merges the watcher JSON (newer-at-ASF) with the library edge, tolerates a
    missing/corrupt watch file, and hides entirely when the manifest is unknown;
  • the dashboard embeds the pill with its data-* attributes + the escalation script, and
    omits the pill when radar provenance is unknown.

Run from project root (conda env active, or in the insar container):
    python -m pytest tests/test_radar_watch.py -v
OR plain:
    python tests/test_radar_watch.py
"""

from __future__ import annotations

import base64
import json
import sys
import tempfile
import traceback
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import radar_watch as rw  # noqa: E402
import operational_alarm as oa  # noqa: E402

_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def test_library_newest_real_footprints():
    for sfx in ("", "_vaishnodevi"):
        fp = PROJECT_ROOT / "data" / f"alerts{sfx}" / "mosaic_asc" / "alerts_operational.json"
        d = rw.library_newest(fp)
        assert d is not None and date(2025, 5, 1) <= d <= date.today(), (sfx, d)


def test_library_newest_scopes_to_source_stacks():
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "alerts_operational.json"
        fp.write_text(json.dumps({"source_stacks": ["NO_SUCH_STACK"]}), encoding="utf-8")
        assert rw.library_newest(fp) is None          # no products in those stacks
        assert rw.library_newest(Path(td) / "missing.json") is None


def test_summarize_new():
    scenes = [{"date": "2026-06-23", "path": 100, "unit": "S1A"},
              {"date": "2026-06-25", "path": 27, "unit": "S1D"},
              {"date": "2026-06-06", "path": 27, "unit": "S1A"}]
    s = rw.summarize_new(scenes, date(2026, 6, 23))
    assert s["new_asc_scenes"] == 1 and s["new_units"] == ["S1D"]
    assert s["newest_asc_at_asf"] == "2026-06-25"
    assert s["per_path_newest"] == {"100": "2026-06-23", "27": "2026-06-25"}
    # New-AOI edge: no library yet -> everything counts as new.
    s2 = rw.summarize_new(scenes, None)
    assert s2["new_asc_scenes"] == 3 and s2["library_through"] is None
    assert rw.summarize_new([], date(2026, 1, 1))["newest_asc_at_asf"] is None


def test_radar_status_merges_watch_file():
    real_fp = PROJECT_ROOT / "data" / "alerts_vaishnodevi" / "mosaic_asc" / "alerts_operational.json"
    saved_json, saved_slug = rw.WATCH_JSON, oa.SLUG
    try:
        oa.SLUG = "vaishnodevi"
        with tempfile.TemporaryDirectory() as td:
            # 1. No watch file -> library-only status, no "newer" flag.
            rw.WATCH_JSON = Path(td) / "radar_watch.json"
            st = oa.radar_status(real_fp)
            assert st and st["newer_at_asf"] is None and st["new_scenes"] == 0
            # 2. Watch file with new scenes -> merged.
            rw.WATCH_JSON.write_text(json.dumps({"sites": {"vaishnodevi": {
                "new_asc_scenes": 2, "newest_asc_at_asf": "2026-07-12",
                "new_units": ["S1D"]}}}), encoding="utf-8")
            st2 = oa.radar_status(real_fp)
            assert st2["new_scenes"] == 2 and st2["newer_at_asf"] == "2026-07-12"
            assert st2["new_units"] == "S1D"
            # 3. Corrupt watch file -> falls back to library-only, never raises.
            rw.WATCH_JSON.write_text("{broken", encoding="utf-8")
            assert oa.radar_status(real_fp)["new_scenes"] == 0
            # 4. Unknown footprint -> pill hidden.
            assert oa.radar_status(Path(td) / "nope.json") is None
    finally:
        rw.WATCH_JSON, oa.SLUG = saved_json, saved_slug


def _minimal_page(tmp: Path, radar):
    import numpy as np
    fig = tmp / "f.png"
    fig.write_bytes(_TINY_PNG)
    r = {"season": {"start": "2026-06-01", "end": "2026-06-02", "days": 2},
         "level_counts": {"DORMANT": 1, "WATCH": 1, "ALERT": 0},
         "alert_pct_season": 0.0, "raw_regional_trigger_days": 1,
         "selectivity_gain_raw_to_alert": "1 -> 0 days (1.0x fewer)",
         "events_caught_by_alarm": "0/0", "events_caught_by_alert": "0/0",
         "per_event": [], "footprint_zones": 3}
    tier = {"scenario": "operational", "m": 0.5, "n_zones": 3, "n_crit": 1, "n_multi": 1,
            "auc": None, "recall": None, "spec": None, "lift250": None,
            "core_zones": None, "core_auc": None, "core_lift": None}
    out = tmp / "operational_alarm_dashboard_t.html"
    oa.write_dashboard(out, r, [date(2026, 6, 1), date(2026, 6, 2)], np.array([0.5, 1.2]),
                       ["DORMANT", "WATCH"], 1, fig, tier, radar=radar)
    return out.read_text(encoding="utf-8")


def test_dashboard_radar_pill_and_omission():
    with tempfile.TemporaryDirectory() as td:
        page = _minimal_page(Path(td), {"through": "2026-06-23", "newer_at_asf": "2026-06-25",
                                        "new_scenes": 1, "new_units": "S1D"})
        assert 'id="radar-freshness" data-acq="2026-06-23"' in page
        assert 'data-new="2026-06-25"' in page and 'data-units="S1D"' in page
        for marker in ("cadence rebuild is unblocked", "days > 90", "days > 35"):
            assert marker in page, marker
    with tempfile.TemporaryDirectory() as td:
        page2 = _minimal_page(Path(td), None)
        # The pill ELEMENT is omitted (the script keeps its null-guarded getElementById).
        assert 'id="radar-freshness"' not in page2


def test_nisar_pilot_pair_selection_and_report():
    """Tier 2b plumbing (no gdal/h5py needed): the pilot picks ONLY the AOI's own stacks'
    bracketing winter pairs — 3 for Ramban, 0 for VD (whose stacks start May 2026, a
    documented not-comparable case) — and the produced report carries the decision fields."""
    import nisar_coherence_pilot as ncp
    r_pairs = ncp.c_band_pairs("ramban")
    assert len(r_pairs) == 3 and all(p.exists() for _, p in r_pairs)
    assert {s for s, _ in r_pairs} == {"ASC_path27_frame101", "ASC_path27_frame106",
                                       "ASC_path100_frame102"}
    assert ncp.c_band_pairs("vaishnodevi") == []
    lo_lon, lo_lat, hi_lon, hi_lat = ncp.aoi_bbox("ramban")
    assert 75.0 < lo_lon < hi_lon < 75.5 and 33.0 < lo_lat < hi_lat < 33.5
    rep = PROJECT_ROOT / "data" / "nisar" / "nisar_coherence_pilot.json"
    if rep.exists():                                       # artifact check when the pilot ran
        v = json.loads(rep.read_text(encoding="utf-8"))["verdict"]
        assert "median_pct_of_C_fail_pixels_recovered_by_L" in v and "caveats" in v
        assert v["median_pct_of_C_fail_pixels_recovered_by_L"] > 0


# ------------------------------------------------------------------------------
# Plain-python runner (mirrors the other suites)
# ------------------------------------------------------------------------------
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

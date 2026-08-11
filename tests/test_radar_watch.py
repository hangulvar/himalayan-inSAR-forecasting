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
    bracketing winter pairs, and the produced report carries the decision fields.

    Selection is driven by each site's OWN `source_stacks`, which is why the two sites differ.
    §80 CHANGED VD's answer, deliberately: VD's product used to hold only the 2026 frames
    (103/105), so it had NO winter pairs and was a documented not-comparable case. Adding the
    long 2025 histories (frame102, frame101) gives it 2 — i.e. VD can now take part in the
    NISAR L-vs-C winter comparison it was previously excluded from. If this drops back to 0,
    VD's product has lost those stacks (check `period_split:` in its registry file)."""
    import nisar_coherence_pilot as ncp
    winter = ncp.SEASONS["winter"]
    r_pairs = ncp.c_band_pairs("ramban", winter)
    assert len(r_pairs) == 3 and all(p.exists() for _, p in r_pairs)
    assert {s for s, _ in r_pairs} == {"ASC_path27_frame101", "ASC_path27_frame106",
                                       "ASC_path100_frame102"}
    v_pairs = ncp.c_band_pairs("vaishnodevi", winter)
    assert len(v_pairs) == 2 and all(p.exists() for _, p in v_pairs)
    assert {s for s, _ in v_pairs} == {"ASC_path100_frame102", "ASC_path27_frame101"}
    # Each site still draws only from its own stacks — VD's set is a strict subset of Ramban's.
    assert {s for s, _ in v_pairs} < {s for s, _ in r_pairs}
    lo_lon, lo_lat, hi_lon, hi_lat = ncp.aoi_bbox("ramban")
    assert 75.0 < lo_lon < hi_lon < 75.5 and 33.0 < lo_lat < hi_lat < 33.5
    rep = PROJECT_ROOT / "data" / "nisar" / "nisar_coherence_pilot.json"
    if rep.exists():                                       # artifact check when the pilot ran
        v = json.loads(rep.read_text(encoding="utf-8"))["verdict"]
        assert "median_pct_of_C_fail_pixels_recovered_by_L" in v and "caveats" in v
        assert v["median_pct_of_C_fail_pixels_recovered_by_L"] > 0


def test_l_window_health_separates_a_void_from_a_result():
    """§65 — THE guard. A NaN void and a decorrelated slope produce identical-looking low
    numbers downstream; scoring a void once produced a confident, fabricated 'L recovers
    0.0%'. l_window_health must refuse the void and pass real data."""
    import numpy as np
    import nisar_coherence_pilot as ncp

    # A 1-degree grid in EPSG:4326 so lx/ly are lon/lat directly (identity transform).
    lx = np.linspace(75.0, 75.5, 51)
    ly = np.linspace(33.0, 33.5, 51)
    bbox = (75.1, 33.1, 75.4, 33.4)

    good = np.full((51, 51), 0.7, dtype=np.float32)
    h = ncp.l_window_health(good, lx, ly, bbox, 4326)
    assert h["ok"] and h["valid_pct"] == 100.0 and h["median"] == 0.7

    void = np.full((51, 51), np.nan, dtype=np.float32)
    h = ncp.l_window_health(void, lx, ly, bbox, 4326)
    assert not h["ok"] and h["valid_pct"] == 0.0 and "VOID" in h["reason"]

    # Partly valid but under the floor -> still refused (the Vaishno Devi fringe case).
    fringe = np.full((51, 51), np.nan, dtype=np.float32)
    fringe[:10, :] = 0.6
    h = ncp.l_window_health(fringe, lx, ly, bbox, 4326)
    assert not h["ok"] and h["valid_pct"] < ncp.MIN_L_VALID_PCT

    # Fully covered but numerically dead -> refused as void fringe, not scored as a result.
    dead = np.full((51, 51), 0.007, dtype=np.float32)
    h = ncp.l_window_health(dead, lx, ly, bbox, 4326)
    assert not h["ok"] and "dead" in h["reason"]

    # AOI entirely off the grid -> refused, not silently empty.
    h = ncp.l_window_health(good, lx, ly, (10.0, 10.0, 10.1, 10.1), 4326)
    assert not h["ok"] and h["valid_pct"] == 0.0


def test_nisar_monsoon_run_aborted_without_a_verdict():
    """The monsoon artifact must record an ABORT, never a coherence verdict, while the winter
    artifact keeps its §59 numbers. Guards against a void run being read as a negative result."""
    mon = PROJECT_ROOT / "data" / "nisar" / "nisar_coherence_pilot_monsoon.json"
    if mon.exists():
        m = json.loads(mon.read_text(encoding="utf-8"))
        assert m["season"] == "monsoon"
        assert m["verdict"]["status"].startswith("ABORTED"), m["verdict"]
        assert "median_pct_of_C_fail_pixels_recovered_by_L" not in m["verdict"]
        assert all(not c["ok"] for c in m["l_coverage"].values())
    win = PROJECT_ROOT / "data" / "nisar" / "nisar_coherence_pilot.json"
    if win.exists():
        w = json.loads(win.read_text(encoding="utf-8"))
        assert w["season"] == "winter"
        assert w["verdict"]["median_pct_of_C_fail_pixels_recovered_by_L"] > 0
        assert all(c["ok"] for c in w["l_coverage"].values())


def test_nisar_season_presets_are_a_controlled_comparison():
    """§65: the winter/monsoon presets must differ ONLY in season — same NISAR track, same
    12-day baseline in both bands — or the comparison measures the wrong thing."""
    import re
    import nisar_coherence_pilot as ncp
    from datetime import date as _date

    tracks = set()
    for name, s in ncp.SEASONS.items():
        m = re.search(r"GUNW_\d+_(\d+)_([AD])_(\d+)_", s["h5"])
        assert m, f"{name}: cannot parse track from {s['h5']}"
        tracks.add(m.groups())                      # (track, direction, frame)
        # Every C-band pair in every season is a 12-day baseline — the same as the L pair.
        d = s["c_pairs"]
        for slug, dates in d.items():
            assert len(dates) == 4, f"{name}/{slug}"
            for a, b in ((dates[0], dates[1]), (dates[2], dates[3])):
                span = (_date.fromisoformat(f"{b[:4]}-{b[4:6]}-{b[6:]}")
                        - _date.fromisoformat(f"{a[:4]}-{a[4:6]}-{a[6:]}")).days
                assert span == 12, f"{name}/{slug}: {a}->{b} is {span} d, not 12"
    assert len(tracks) == 1, f"seasons use different NISAR tracks: {tracks}"

    # Output tags must be distinct, and winter's must stay empty so §59's artifact keeps its
    # filename (a tagged winter run would orphan the ledger's cited report).
    tags = [s["tag"] for s in ncp.SEASONS.values()]
    assert len(set(tags)) == len(tags) and ncp.SEASONS["winter"]["tag"] == ""
    assert ncp.SEASONS["monsoon"]["tag"]


def test_nisar_monsoon_admits_the_renamed_continuation_frames():
    """The May-2026 frame renumber (§61) put Ramban's June C-band pairs on f105/f103. The
    monsoon preset must admit those (else Ramban silently scores zero pairs); the winter
    preset must NOT (it would change §59's published selection)."""
    import nisar_coherence_pilot as ncp
    monsoon, winter = ncp.SEASONS["monsoon"], ncp.SEASONS["winter"]
    assert winter["extra_stacks"] == []
    assert set(monsoon["extra_stacks"]) == {"ASC_path27_frame105", "ASC_path100_frame103"}

    for slug in ("ramban", "vaishnodevi"):
        pairs = ncp.c_band_pairs(slug, monsoon)
        assert pairs, f"{slug}: monsoon preset found no C-band pair"
        assert all(p.exists() for _, p in pairs), slug
        # Both AOIs resolve to the SAME two continuation stacks — VD via its own
        # source_stacks, Ramban via the override — so the two sites stay comparable.
        assert {s for s, _ in pairs} == {"ASC_path27_frame105", "ASC_path100_frame103"}, slug


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

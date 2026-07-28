"""
test_flood_gate.py — F1, the catchment flash-flood staging arm (workflows/flood_gate.py).
Cases U8-U15 and integration scenarios I1/I4/I5/I6 of FLOOD_EXPANSION_PLAN_2026-07-28 §7.4/§7.6.

Hermetic: NO network and NO GEE. Every rainfall series is synthetic, the F0 geometry is a
hand-built JSON, and the one end-to-end run (I1) writes a real GeoTIFF DEM into a temp dir and
drives flood_domain -> flood_gate with the fetch stubbed out.

Two assertions here carry more weight than the rest:
  • test_pins_to_the_shared_burst_math — the per-catchment exceedance must equal
    imerg_gate.daily_subdaily_E's answer when run over the same duration menu, so the flood
    arm can never quietly diverge from the validated burst grading;
  • test_U11_* — a void or too-short series ABORTS with a reason and is never graded DORMANT
    ("no data" != "no rain", the §65 rule).

Run from project root:
    python tests/test_flood_gate.py
OR under pytest:
    python -m pytest tests/test_flood_gate.py -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import flood_gate as fg  # noqa: E402
import imerg_gate as ig  # noqa: E402
from rainfall_id_threshold import THRESHOLDS, threshold_intensity  # noqa: E402

A, B = THRESHOLDS["nwhimalaya"]["a"], THRESHOLDS["nwhimalaya"]["b"]


def _series(day0: datetime, n_days: int, rate_at: dict[int, float]):
    """A half-hourly series of n_days*48 steps; rate_at maps step index -> mm/h."""
    return [(day0 + timedelta(minutes=30 * i), rate_at.get(i, 0.0))
            for i in range(n_days * 48)]


# ------------------------------------------------------------------------------
# U8-U10 — the graded series
# ------------------------------------------------------------------------------
def test_U8_known_burst_gives_the_hand_computed_exceedance():
    day0 = datetime(2026, 6, 1)
    days = fg.catchment_daily_E(_series(day0, 2, {20: 30.0, 21: 30.0}), A, B, 1.0)
    d1 = days[0]
    expect = 30.0 / float(threshold_intensity(np.array([1.0]), A, B)[0])   # 30 mm in 1 h
    assert abs(d1["E_f"] - round(expect, 2)) < 0.01, d1
    assert d1["burst_mm"] == 30.0 and d1["duration_h"] == 1.0
    assert d1["level"] == "FLOOD-ALERT", d1
    assert d1["window_end"] == "2026-06-01 10:30"


def test_U9_burst_spanning_midnight_is_not_split():
    day0 = datetime(2026, 6, 1)
    days = fg.catchment_daily_E(_series(day0, 2, {47: 30.0, 48: 30.0}), A, B, 1.0)
    d2 = days[1]
    assert d2["burst_mm"] == 30.0, ("the overnight burst was split at midnight", d2)
    assert d2["level"] == "FLOOD-ALERT"


def test_U10_incomplete_day_is_provisional_and_E_only_rises():
    day0 = datetime(2026, 6, 1)
    partial = _series(day0, 1, {}) + [(day0 + timedelta(days=1, minutes=30 * i), 8.0)
                                      for i in range(6)]
    days = fg.catchment_daily_E(partial, A, B, 1.0)
    assert days[0]["provisional"] is False and days[1]["provisional"] is True
    assert days[1]["n_steps"] == 6
    e_partial = days[1]["E_f"]
    # More of the same day arrives (still raining): E must not fall.
    fuller = partial + [(day0 + timedelta(days=1, minutes=30 * i), 8.0) for i in range(6, 12)]
    e_fuller = fg.catchment_daily_E(fuller, A, B, 1.0)[1]["E_f"]
    assert e_fuller >= e_partial, (e_partial, e_fuller)


def test_U10b_dry_season_is_dormant_everywhere():
    """I4 — a dry week must produce no card noise at all."""
    days = fg.catchment_daily_E(_series(datetime(2026, 1, 5), 7, {}), A, B, 3.0)
    assert len(days) == 7
    assert {d["level"] for d in days} == {"FLOOD-DORMANT"}
    assert max(d["E_f"] for d in days) == 0.0


# ------------------------------------------------------------------------------
# The shared-math pin
# ------------------------------------------------------------------------------
def test_pins_to_the_shared_burst_math():
    """Run the flood grading over imerg_gate's OWN duration menu and take the max: it must
    reproduce daily_subdaily_E's max_E for every day, on several rainfall shapes."""
    day0 = datetime(2026, 6, 1)
    shapes = [
        {20: 30.0, 21: 30.0},                                  # sharp 1 h burst
        {i: 2.0 for i in range(0, 48)},                        # steady all-day rain
        {47: 30.0, 48: 30.0},                                  # overnight
        {10: 5.0, 30: 9.0, 70: 14.0, 90: 3.0},                 # scattered cells
        {},                                                     # bone dry
    ]
    for shape in shapes:
        series = _series(day0, 3, shape)
        ref = ig.daily_subdaily_E(series, A, B)
        mine = {}
        for D in ig.DUR_H:
            for d in fg.catchment_daily_E(series, A, B, float(D)):
                mine[d["date"]] = max(mine.get(d["date"], 0.0), d["E_f"])
        for r in ref:
            assert abs(mine[r["date"]] - r["max_E"]) < 0.011, (
                f"shape {shape}: day {r['date']} flood arm says {mine[r['date']]}, "
                f"validated burst math says {r['max_E']}")


def test_thresholds_are_literally_inherited_not_copied():
    """U12 boundaries, asserted RELATIVE to the imported constants (the §64 rule): a future
    recalibration of the burst arm must flow through, and must never require editing a test."""
    assert fg.FLOOD_ALERT_K is ig.BURST_ALERT_K and fg.FLOOD_WATCH_K is ig.BURST_WATCH_K
    day0 = datetime(2026, 6, 1)
    thr_1h = float(threshold_intensity(np.array([1.0]), A, B)[0])

    def level_for(target_E):
        rate = target_E * thr_1h                     # mm/h sustained for exactly 1 h
        days = fg.catchment_daily_E(_series(day0, 1, {20: rate, 21: rate}), A, B, 1.0)
        return days[0]["level"]

    eps = 0.02
    assert level_for(fg.FLOOD_ALERT_K + eps) == "FLOOD-ALERT"
    assert level_for(fg.FLOOD_ALERT_K - eps) == "FLOOD-WATCH"
    assert level_for(fg.FLOOD_WATCH_K + eps) == "FLOOD-WATCH"
    assert level_for(fg.FLOOD_WATCH_K - eps) == "FLOOD-DORMANT"
    assert fg.LEVELS == ["FLOOD-DORMANT", "FLOOD-WATCH", "FLOOD-ALERT"]


# ------------------------------------------------------------------------------
# U11 — the void/abort guard and its negative control
# ------------------------------------------------------------------------------
def test_U11_void_and_short_series_abort_with_a_reason():
    day0 = datetime(2026, 6, 1)
    cases = [
        ([], "no rainfall steps"),
        ([(day0 + timedelta(minutes=30 * i), float("nan")) for i in range(48)], "non-finite"),
        (_series(day0, 1, {})[:1], "too short"),
    ]
    for series, expect in cases:
        ok, reason, stats = fg.series_health(series, 3.0)
        assert ok is False, f"expected an abort for {expect}"
        assert reason and expect.split()[0] in reason, (expect, reason)
        assert isinstance(stats, dict) and "pct_finite" in stats
    # A healthy series passes and reports honest stats.
    ok, reason, stats = fg.series_health(_series(day0, 1, {10: 4.0}), 3.0)
    assert ok is True and reason is None
    assert stats["n_steps"] == 48 and stats["pct_finite"] == 100.0
    assert stats["max_rate_mmph"] == 4.0


def test_U11b_a_void_is_never_graded_dormant():
    """NEGATIVE CONTROL for the guard: without it, an all-NaN catchment grades as a confident
    FLOOD-DORMANT — a fabricated 'no flood risk' from no data. The guard must be what stops it."""
    day0 = datetime(2026, 6, 1)
    void = [(day0 + timedelta(minutes=30 * i), float("nan")) for i in range(48)]
    graded_anyway = fg.catchment_daily_E(void, A, B, 1.0)
    assert graded_anyway and graded_anyway[0]["level"] == "FLOOD-DORMANT", (
        "the grader no longer produces the dangerous answer — re-check this control")
    ok, _reason, _ = fg.series_health(void, 1.0)
    assert ok is False, "the guard failed to intercept the void the grader would have graded"


# ------------------------------------------------------------------------------
# U13 — response-time window matching
# ------------------------------------------------------------------------------
def test_U13_window_matches_the_catchment_response_time():
    assert fg.match_duration(0.2) == 0.5          # flashy headwater -> shortest window
    assert fg.match_duration(0.5) == 0.5          # exactly on a boundary -> that window
    assert fg.match_duration(0.9) == 1.0
    assert fg.match_duration(2.5) == 3.0
    assert fg.match_duration(99.0) == 6.0         # capped: beyond this it is the daily arm's job
    assert fg.match_duration(None) == 1.0         # unknown t_c -> a stated default, not a guess
    assert fg.match_duration(float("nan")) == 1.0
    # Monotone: a slower catchment never gets a shorter window.
    tcs = [0.1, 0.4, 0.6, 1.5, 4.0, 8.0]
    windows = [fg.match_duration(t) for t in tcs]
    assert windows == sorted(windows), windows


# ------------------------------------------------------------------------------
# U14-U15 — outputs
# ------------------------------------------------------------------------------
def _fake_catchment(name="catchment_zone1", level="FLOOD-WATCH", E=1.4, aborted=False):
    if aborted:
        return {"catchment": name, "zone": 1, "area_km2": 8.4, "tc_hours": 0.9,
                "imerg_pixels": 1, "aborted": True, "duration_h": None,
                "abort_reason": "catchment touches the edge of the DEM's valid data"}
    return {"catchment": name, "zone": 1, "area_km2": 8.4, "tc_hours": 0.9,
            "imerg_pixels": 1, "aborted": False, "abort_reason": None, "duration_h": 1.0,
            "date": "2026-06-02", "E_f": E, "level": level, "burst_mm": 12.3,
            "peak_mmph": 12.3, "window_end": "2026-06-02 14:00", "provisional": False,
            "n_days": 2,
            # The newest day is QUIET even though the season peak was ALERT-grade — the exact
            # shape that made the old season-peak headline misleading (§70).
            "latest": {"date": "2026-06-02", "E_f": 0.0, "level": "FLOOD-DORMANT",
                       "provisional": False, "duration_h": 1.0, "burst_mm": 0.0,
                       "peak_mmph": 0.0, "window_end": None, "n_steps": 48},
            "days": [{"date": "2026-06-01", "level": level, "E_f": E},
                     {"date": "2026-06-02", "level": "FLOOD-DORMANT", "E_f": 0.0}]}


def test_U15_summary_schema_is_pinned():
    s = fg.build_summary("ramban", [_fake_catchment(), _fake_catchment("c2", aborted=True)],
                         "nwhimalaya", A, B, {"start": "2026-06-01", "end": "2026-06-02",
                                              "days": 2})
    for key in ("slug", "experimental", "aborted", "threshold", "flood_watch_k",
                "flood_alert_k", "thresholds_inherited_from", "durations_h", "season",
                "n_catchments", "n_staged", "n_aborted", "level_counts", "latest",
                "latest_date", "season_peak", "alert_days_per_catchment", "catchments"):
        assert key in s, f"summary lost the {key!r} field the dashboard/tests rely on"
    assert s["experimental"] is True, "this arm must never ship claiming to be validated"
    assert s["aborted"] is False and s["n_staged"] == 1 and s["n_aborted"] == 1
    assert s["season_peak"]["catchment"] == "catchment_zone1"
    assert "not flood-calibrated" in s["thresholds_inherited_from"].lower()
    assert s["alert_days_per_catchment"] == {"catchment_zone1": 0}
    # Every catchment aborted -> the whole summary aborts and carries NO level.
    allbad = fg.build_summary("ramban", [_fake_catchment(aborted=True)], "nwhimalaya", A, B,
                              {"start": "2026-06-01", "end": "2026-06-02", "days": 0})
    assert allbad["aborted"] is True and allbad["season_peak"] is None
    assert allbad["latest"] is None and allbad["abort_reason"]


def test_level_counts_describe_TODAY_not_the_season_peak():
    """REGRESSION (§70). The first live run reported '8/8 catchments FLOOD-ALERT' while ~84% of
    each catchment's individual days were DORMANT and the newest day was quiet — because the
    counts were taken over each catchment's SEASON PEAK. On a warning page that reads as
    'everything is on alert right now'. level_counts must describe the newest day."""
    peaked_but_quiet_today = _fake_catchment(level="FLOOD-ALERT", E=8.06)
    s = fg.build_summary("ramban", [peaked_but_quiet_today], "nwhimalaya", A, B,
                         {"start": "2026-06-01", "end": "2026-06-02", "days": 2})
    assert s["level_counts"] == {"FLOOD-DORMANT": 1, "FLOOD-WATCH": 0, "FLOOD-ALERT": 0}, (
        "level_counts followed the season peak instead of the newest day", s["level_counts"])
    assert s["latest"]["level"] == "FLOOD-DORMANT" and s["latest"]["E_f"] == 0.0
    assert s["latest_date"] == "2026-06-02"
    # …while the season peak is still reported, separately and labelled as such.
    assert s["season_peak"]["level"] == "FLOOD-ALERT" and s["season_peak"]["E_f"] == 8.06


def test_U14_outputs_are_idempotent():
    s = fg.build_summary("ramban", [_fake_catchment()], "nwhimalaya", A, B,
                         {"start": "2026-06-01", "end": "2026-06-02", "days": 2})
    saved = fg.FLOOD_DIR
    with tempfile.TemporaryDirectory() as td:
        try:
            fg.FLOOD_DIR = Path(td)
            p1 = fg.write_outputs(s, "_test")
            first = (p1.read_bytes(),
                     (Path(td) / "flood_gate_summary_test.json").read_bytes())
            p2 = fg.write_outputs(s, "_test")
            second = (p2.read_bytes(),
                      (Path(td) / "flood_gate_summary_test.json").read_bytes())
        finally:
            fg.FLOOD_DIR = saved
    assert first == second, "a re-run with identical inputs changed its outputs"


def test_I6_season_suffix_follows_the_project_rule():
    assert fg.season_suffix("ramban", 2026) == "_2026"          # grandfathered
    assert fg.season_suffix("vaishnodevi", 2026) == "_vaishnodevi_2026"
    # Identical to the rule imerg_gate applies for the same slug.
    saved = ig.SLUG
    try:
        for slug in ("ramban", "vaishnodevi"):
            ig.SLUG = slug
            assert fg.season_suffix(slug, 2025) == ig.season_suffix(2025), slug
    finally:
        ig.SLUG = saved


def test_sampling_scale_rescues_sub_pixel_catchments():
    """REGRESSION (2026-07-28, live run): at IMERG's native ~11 km scale, Earth Engine returns
    NULL for a region containing no pixel centre. Three of Ramban's eight real catchments hit
    that and aborted as 'no rainfall steps' — while two boxes of the SAME SIZE returned data,
    which is what exposed it as a position lottery rather than a void. Probed directly: null at
    11132 m, real values at 2000 m and 500 m.

    So: a sub-pixel catchment must be sampled FINER than native, and a comfortably large region
    must still use native (no gratuitous extra computation)."""
    tiny = [75.15033, 33.26973, 75.15721, 33.27983]        # real zone-3 bbox that aborted
    assert fg.sampling_scale_m(tiny) < fg.IMERG_SCALE_M
    assert fg.sampling_scale_m(tiny) >= 500.0, "never sample absurdly fine"
    big = [75.0, 33.0, 76.0, 34.0]                          # ~110 km across
    assert fg.sampling_scale_m(big) == fg.IMERG_SCALE_M
    # Monotone in region size, and never above native.
    spans = [0.005, 0.01, 0.05, 0.2, 1.0]
    scales = [fg.sampling_scale_m([75.0, 33.0, 75.0 + s, 33.0 + s]) for s in spans]
    assert scales == sorted(scales), scales
    assert max(scales) <= fg.IMERG_SCALE_M
    # Every one of the 22 REAL catchments must be sampled at a scale strictly SMALLER than the
    # catchment itself — the minimal condition for the region to contain a sample point.
    # (The decisive evidence is empirical and stronger than any inequality here: with this
    # function in place the live run staged 22/22 catchments with zero null series, where the
    # native scale had aborted 3 of Ramban's 8.)
    for slug in ("ramban", "vaishnodevi"):
        dom = PROJECT_ROOT / "data" / "flood" / f"flood_domain_{slug}.json"
        if not dom.exists():
            continue                                        # fresh clone: nothing to check
        for z in json.loads(dom.read_text(encoding="utf-8"))["zones"]:
            bb = (z.get("catchment") or {}).get("bbox_lonlat")
            if not bb:
                continue
            span_m = min(abs(bb[2] - bb[0]) * 111320.0 * np.cos(np.radians(bb[1])),
                         abs(bb[3] - bb[1]) * 110540.0)
            assert fg.sampling_scale_m(bb) < span_m, (
                f"{slug} zone {z['zone']}: sampling scale {fg.sampling_scale_m(bb)} m is not "
                f"smaller than the catchment span {span_m:.0f} m — it would return null again")


def test_imerg_pixel_span_is_reported_honestly():
    assert fg.imerg_pixels_spanned([75.10, 33.10, 75.13, 33.12]) == 1   # sub-pixel catchment
    assert fg.imerg_pixels_spanned([75.0, 33.0, 75.4, 33.3]) >= 4
    assert fg.imerg_pixels_spanned(None) == 0


# ------------------------------------------------------------------------------
# I1 / I5 — end-to-end on a synthetic site, and the fetch-outage path
# ------------------------------------------------------------------------------
def _write_synthetic_site(tmp: Path):
    """A conical peak as a real GeoTIFF + the footprint flood_domain reads.

    A CONE (not a valley) on purpose: flow runs radially outward, so a zone on the flank has a
    wedge-shaped catchment that never reaches the array border. That makes this an end-to-end
    test of the STAGED path — a valley DEM drains the whole grid and every catchment is
    edge-truncated, which would only ever exercise the abort branch.
    """
    import rasterio
    from rasterio.transform import from_origin
    n, px = 60, 80.0
    ctr = (n - 1) / 2.0
    r_idx, c_idx = np.mgrid[0:n, 0:n]
    dem = 3000.0 - np.hypot(r_idx - ctr, c_idx - ctr) * 25.0
    tif = tmp / "dem.tif"
    with rasterio.open(tif, "w", driver="GTiff", height=n, width=n, count=1,
                       dtype="float32", crs="EPSG:32643",
                       transform=from_origin(300000.0, 3670000.0, px, px)) as ds:
        ds.write(dem.astype("float32"), 1)
    # The zone centroid: a cell on the cone's flank, converted to lon/lat.
    import pyproj
    x, y = 300000.0 + 30 * px, 3670000.0 - 45 * px
    lon, lat = pyproj.Transformer.from_crs(32643, 4326, always_xy=True).transform(x, y)
    fp = tmp / "alerts_operational.json"
    fp.write_text(json.dumps({"scenario": "operational", "zones": [
        {"severity": "HIGH", "centroid_lonlat": [lon, lat],
         "detected_by_looks": ["SYNTH_stack"], "n_looks": 1, "min_fs_any_look": 0.9,
         "strongest_creep_mmyr": -40.0, "max_area_km2": 0.03, "llof_potential": False}]}),
        encoding="utf-8")
    return tif, fp


def test_I1_end_to_end_synthetic_site():
    """domain -> gate on a site built from scratch, with the GEE fetch stubbed. Proves the two
    stages actually hand off (bbox, t_c, stageability) rather than each working in isolation."""
    import flood_domain as fd
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        tif, fp = _write_synthetic_site(tmp)
        saved = (fd.stack_dem, fd.FLOOD_DIR, fd.CACHE_DIR, fg.FLOOD_DIR, fg.RAIN_CACHE,
                 fg.fetch_catchment_series)
        try:
            fd.stack_dem = lambda stack: tif
            fd.FLOOD_DIR = tmp / "flood"
            fd.CACHE_DIR = tmp / "flood" / "_cache"
            fg.FLOOD_DIR = tmp / "flood"
            fg.RAIN_CACHE = tmp / "flood" / "_rain"
            cfg_path = tmp / "synth.yaml"
            cfg_path.write_text(
                f"aoi_path: config/aoi/ramban_aoi.geojson\njob_name_prefix: SYNTH\n"
                f"search_start: 2026-04-01\nsearch_end: 2026-09-30\n"
                f"flood:\n  channel_upstream_km2: 0.05\n  channel_buffer_m: 500\n"
                f"  min_catchment_coverage_pct: 95\n", encoding="utf-8")
            # F0 — point it at our synthetic footprint by patching the path it derives.
            import config as cfgmod
            real_root = fd.PROJECT_ROOT
            fd.PROJECT_ROOT = tmp
            (tmp / "data" / "alerts" / "mosaic_asc").mkdir(parents=True)
            (tmp / "data" / "alerts" / "mosaic_asc" / "alerts_operational.json").write_bytes(
                fp.read_bytes())
            assert fd.main(["--config", str(cfg_path)]) == 0
            fd.PROJECT_ROOT = real_root
            dom = json.loads((tmp / "flood" / "flood_domain_ramban.json").read_text("utf-8"))
            assert dom["n_zones"] == 1
            cm = dom["zones"][0]["catchment"]
            assert cm is not None and cm["regime"] == "A"
            assert cm["area_km2"] > 0 and cm["n_cells"] > 0
            assert cm["bbox_lonlat"] and cm["tc_hours"] is not None
            assert cm["truncated"] is False and cm["stageable"] is True, (
                "the cone fixture must yield an INTERIOR catchment so this test exercises the "
                "graded path, not the abort path", cm)

            # F1 — stub the fetch with a known burst; the gate must grade THAT catchment.
            day0 = datetime(2026, 6, 1)
            fg.fetch_catchment_series = (
                lambda cache, bbox, start, end, project=None:
                _series(day0, 2, {20: 30.0, 21: 30.0}))
            rc = fg.main(["--config", str(cfg_path), "--start", "2026-06-01",
                          "--end", "2026-06-02"])
            assert rc == 0
            summ = json.loads((tmp / "flood" / "flood_gate_summary_2026.json")
                              .read_text("utf-8"))
            if cm["stageable"]:
                assert summ["aborted"] is False and summ["n_staged"] == 1
                assert summ["season_peak"]["level"] == "FLOOD-ALERT", summ["season_peak"]
                # …and the newest day is reported separately from that peak.
                assert summ["latest"] is not None and summ["latest_date"]
                assert summ["experimental"] is True
            else:
                # A truncated synthetic catchment must ABORT, never grade.
                assert summ["aborted"] is True and summ["n_staged"] == 0
                assert summ["catchments"][0]["abort_reason"]
        finally:
            (fd.stack_dem, fd.FLOOD_DIR, fd.CACHE_DIR, fg.FLOOD_DIR, fg.RAIN_CACHE,
             fg.fetch_catchment_series) = saved


def test_I5_fetch_outage_aborts_that_catchment_without_crashing():
    """GEE down must not take the run with it: the catchment records an abort reason and the
    script still exits 0 (the non-fatal posture every live hook in this project uses)."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        saved = (fg.FLOOD_DIR, fg.RAIN_CACHE, fg.fetch_catchment_series)
        try:
            fg.FLOOD_DIR = tmp
            fg.RAIN_CACHE = tmp / "_rain"
            (tmp / "flood_domain_ramban.json").write_text(json.dumps({
                "slug": "ramban", "zones": [{"zone": 1, "severity": "HIGH", "catchment": {
                    "area_km2": 8.4, "tc_hours": 0.9, "regime": "A", "stageable": True,
                    "bbox_lonlat": [75.1, 33.1, 75.2, 33.2], "refusal": None}}]}),
                encoding="utf-8")

            def boom(*a, **k):
                raise RuntimeError("EEException: quota exceeded")
            fg.fetch_catchment_series = boom
            cfg_path = tmp / "c.yaml"
            cfg_path.write_text(
                "aoi_path: config/aoi/ramban_aoi.geojson\njob_name_prefix: T\n"
                "search_start: 2026-04-01\nsearch_end: 2026-09-30\nflood:\n"
                "  channel_upstream_km2: 0.5\n", encoding="utf-8")
            rc = fg.main(["--config", str(cfg_path), "--start", "2026-06-01",
                          "--end", "2026-06-02"])
            assert rc == 0, "a GEE outage must not fail the run"
            s = json.loads((tmp / "flood_gate_summary_2026.json").read_text("utf-8"))
            assert s["aborted"] is True and s["n_staged"] == 0
            assert "quota exceeded" in s["catchments"][0]["abort_reason"]
        finally:
            fg.FLOOD_DIR, fg.RAIN_CACHE, fg.fetch_catchment_series = saved


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

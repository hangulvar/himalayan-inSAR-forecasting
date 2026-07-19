"""
test_tier34.py — the Tier 3/4 strengthening instruments (§60): susceptibility cross-check,
optical change, flow-routing probe, and the committed temporal-skill table. Hermetic maths on
synthetic inputs + schema checks on the committed CSV; report-artifact checks run only when
the corresponding report exists on disk (same pattern as the other suites).

Run from project root (conda env active, or in the insar container):
    python -m pytest tests/test_tier34.py -v
OR plain:
    python tests/test_tier34.py
"""

from __future__ import annotations

import csv
import json
import sys
import traceback
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import susceptibility_crosscheck as sc  # noqa: E402
import optical_change as oc  # noqa: E402
import flow_routing_probe as fr  # noqa: E402


def test_auc_pure():
    y = np.array([0, 0, 0, 1, 1, 1], dtype=float)
    assert sc.auc(np.array([1, 2, 3, 4, 5, 6.0]), y) == 1.0        # perfect separation
    assert sc.auc(np.array([6, 5, 4, 3, 2, 1.0]), y) == 0.0        # perfectly wrong
    mid = sc.auc(np.array([1, 4, 2, 3, 6, 5.0]), y)
    assert 0.5 < mid < 1.0


def test_irls_separates_synthetic():
    rng = np.random.default_rng(7)
    X = rng.normal(size=(400, 3))
    y = (X[:, 0] + 0.5 * X[:, 1] + rng.normal(scale=0.5, size=400) > 0).astype(float)
    w = sc.irls_logistic(X, y)
    s = np.column_stack([np.ones(len(X)), X]) @ w
    assert sc.auc(s, y) > 0.85
    cv, sd = sc.kfold_auc(X, y, k=4, seed=1)
    assert cv > 0.8 and sd < 0.2


def test_optical_stats_pure():
    grid = np.array([[0.2, 0.1, np.nan], [0.0, -0.2, 0.3], [0.1, 0.2, -0.1]])
    s = oc.stats_from_grid(grid, scar_val=-0.15)
    assert s["n_pixels"] == 8
    assert s["scar_dndvi"] == -0.15
    assert s["scar_percentile_low_tail"] == 12.5       # only -0.2 is below
    assert 0 < s["pct_pixels_strong_loss"] <= 100


def test_d8_accumulation_valley():
    # A tilted plane with a central trench: flow must concentrate along the trench and grow
    # monotonically downstream; edges must not crash (the off-grid fix).
    h, w = 30, 21
    dem = np.tile(np.arange(h, 0, -1, dtype=float)[:, None], (1, w)) * 10.0
    dem[:, 10] -= 5.0                                   # trench down the middle
    acc = fr.d8_accumulation(dem)
    trench = acc[:, 10]
    assert trench[-1] == trench.max()                   # outlet has the whole catchment
    assert np.all(np.diff(trench) >= 0)                 # monotone growth downstream
    # Only the trench + its two flanking columns drain into it on a tilted plane (straight
    # descent beats the diagonal beyond one column), so ~3x a plain column's catchment.
    assert trench[-1] > 2 * acc[:, 3].max()
    # NaN (nodata) cells act as sinks, not crashes.
    dem2 = dem.copy()
    dem2[5:8, 5:8] = np.nan
    assert np.isfinite(fr.d8_accumulation(dem2)).all()


def test_routed_llof_flag_criterion():
    # The single shared LLOF criterion (§60 4c): 100 cells of 80 m pixels draining
    # through one channel cell = 0.64 km² >= the 0.5 km² threshold.
    acc = np.ones((20, 20))
    acc[10, 10] = 100.0
    flag, up = fr.routed_llof_flag(acc, 80.0, 8, 8)      # channel within the 3-px window
    assert flag and abs(up - 0.64) < 1e-9
    flag2, up2 = fr.routed_llof_flag(acc, 80.0, 2, 2)    # far from the channel
    assert not flag2 and up2 < 0.01
    fr.routed_llof_flag(acc, 80.0, 0, 19)                # corner: window clamps, no crash
    flag4, up4 = fr.routed_llof_flag(acc, 80.0, -10, -10)  # fully off-grid -> empty window
    assert not flag4 and up4 == 0.0


def test_orchestrator_d8_matches_probe_criterion():
    # llof_routing="d8" plumbing: the orchestrator's per-zone helper must reproduce
    # routed_llof_flag through the lonlat -> DEM-grid roundtrip (cache monkeypatched,
    # no rasters touched).
    import agentic_orchestrator as ao
    from pyproj import Transformer
    from rasterio.crs import CRS
    from rasterio.transform import from_origin

    acc = np.ones((20, 20))
    acc[10, 10] = 100.0
    tr = from_origin(500000.0, 3660000.0, 80.0, 80.0)
    ao._D8_ACC_CACHE["_FAKE_"] = (acc, tr, CRS.from_epsg(32643), 80.0)
    try:
        to_ll = Transformer.from_crs(32643, 4326, always_xy=True)
        lon, lat = to_ll.transform(500000.0 + 10.5 * 80, 3660000.0 - 10.5 * 80)
        flag, up = ao._llof_d8("_FAKE_", lon, lat)       # centred on the channel cell
        assert flag and abs(up - 0.64) < 1e-6
        lon2, lat2 = to_ll.transform(500000.0 + 2.5 * 80, 3660000.0 - 2.5 * 80)
        flag2, _ = ao._llof_d8("_FAKE_", lon2, lat2)     # far from the channel
        assert not flag2
    finally:
        del ao._D8_ACC_CACHE["_FAKE_"]


def test_temporal_skill_table_schema_and_consistency():
    f = PROJECT_ROOT / "data" / "inventory" / "temporal_skill_table.csv"
    rows = list(csv.DictReader(f.open(encoding="utf-8")))
    assert len(rows) >= 6
    from imerg_calibration import EVENTS
    ev_dates = {(s, d) for s, d, _, _ in EVENTS}
    for r in rows:
        assert (r["site"], r["date"]) in ev_dates, r["date"]
        assert r["burst_level"] in ("DORMANT", "WATCH", "ALERT")
        assert r["daily_level"] in ("DORMANT", "WATCH", "ALERT")
        assert r["caught_at_alert_by"] in ("both", "daily", "burst", "neither")
        if int(r["deaths"]) > 0:                        # every fatal event is caught
            assert r["caught_at_alert_by"] != "neither", r
        if r["caught_at_alert_by"] != "neither":
            assert r["delta_days"] == "0"


def test_report_artifacts_when_present():
    inv = PROJECT_ROOT / "data" / "inventory" / "susceptibility_crosscheck.json"
    if inv.exists():
        a = json.loads(inv.read_text(encoding="utf-8"))["auc"]
        for k in ("lr_terrain_cv", "lr_no_elevation_cv", "physics_fs_sat", "ensemble"):
            assert 0.0 <= a[k] <= 1.0, k
    opt = PROJECT_ROOT / "data" / "optical" / "optical_change_ardhkuwari.json"
    if opt.exists():
        o = json.loads(opt.read_text(encoding="utf-8"))
        assert o["detection_grade"] in ("DETECTED", "MARGINAL", "NOT DETECTED")
        assert o["n_images"]["pre"] > 0 and o["n_images"]["post"] > 0
    flow = PROJECT_ROOT / "data" / "hazard" / "flow_routing_probe.json"
    if flow.exists():
        fl = json.loads(flow.read_text(encoding="utf-8"))
        for s in fl["sites"].values():
            assert s["n_agree"] <= s["n_zones"]
            for z in s["zones"]:
                assert z["agree"] == (z["twi_llof"] == z["routed_llof"])


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

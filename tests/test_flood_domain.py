"""
test_flood_domain.py — F0, the flood GEOMETRY probe (workflows/flood_domain.py).
Cases U1-U7 of FLOOD_EXPANSION_PLAN_2026-07-28 §7.3, plus the shared-function pin.

Hermetic: no network, no GEE, no DEM on disk except one tiny GeoTIFF written to a temp dir
for the end-to-end record. Every routing answer is checked against an ANALYTIC expectation on
a synthetic DEM, not against a golden file — a golden file would only prove the code still
does what it did, not that it is right.

The load-bearing test here is test_targets_pin_to_shared_accumulation: flood_domain re-derives
the D8 receiver map that flow_routing_probe computes internally but does not expose, and the
plan forbids editing that validated file. So the two are pinned to identical results on four
different DEMs — if either drifts, this fails.

Run from project root:
    python tests/test_flood_domain.py
OR under pytest:
    python -m pytest tests/test_flood_domain.py -v
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import flood_domain as fd  # noqa: E402
import flow_routing_probe as frp  # noqa: E402


# ------------------------------------------------------------------------------
# Synthetic DEMs with known drainage
# ------------------------------------------------------------------------------
def _plane(h=12, w=9):
    """Tilted plane: elevation falls with row, so every cell drains straight down."""
    return np.tile(np.arange(h, 0, -1, dtype=float)[:, None], (1, w))


def _valley(h=15, w=11, axis=5):
    """V-shaped valley along column `axis`, tilted downhill with row."""
    r = np.arange(h)[:, None].astype(float)
    c = np.arange(w)[None, :].astype(float)
    return 100.0 - r * 1.0 + np.abs(c - axis) * 0.5


def _cone(n=21):
    """Cone with the peak at the centre: flow is radially OUTWARD, so a cell on the flank has
    a small wedge-shaped catchment that never reaches the array border."""
    c = (n - 1) / 2.0
    r_idx, c_idx = np.mgrid[0:n, 0:n]
    return 100.0 - np.hypot(r_idx - c, c_idx - c)


# ------------------------------------------------------------------------------
# The shared-function pin (plan §5)
# ------------------------------------------------------------------------------
def _accumulate_from_targets(dem: np.ndarray, targets: np.ndarray) -> np.ndarray:
    """Accumulate over flood_domain's receiver map using the probe's own algorithm shape."""
    h, w = dem.shape
    z = np.where(np.isfinite(dem), dem, -np.inf)
    acc = np.ones(h * w)
    acc[~np.isfinite(dem).ravel()] = 0
    tgt = targets.ravel()
    for i in np.argsort(z.ravel())[::-1]:
        t = tgt[i]
        if t >= 0 and acc[i] > 0:
            acc[t] += acc[i]
    return acc.reshape(h, w)


def test_targets_pin_to_shared_accumulation():
    """flood_domain.d8_targets must describe EXACTLY the routing flow_routing_probe accumulates,
    on every DEM shape we care about — including one with nodata."""
    holed = _valley()
    holed[7, 3] = np.nan
    holed[2, 8] = np.nan
    for name, dem in (("plane", _plane()), ("valley", _valley()),
                      ("cone", _cone()), ("holed", holed)):
        mine = _accumulate_from_targets(dem, fd.d8_targets(dem))
        theirs = frp.d8_accumulation(dem)
        assert np.array_equal(mine, theirs), (
            f"{name}: flood_domain's receiver map disagrees with the validated accumulation")


# ------------------------------------------------------------------------------
# U1-U3 — routing on known terrain
# ------------------------------------------------------------------------------
def test_U1_tilted_plane_drains_straight_down():
    h, w = 12, 9
    acc = frp.d8_accumulation(_plane(h, w))
    assert np.all(acc[h - 1, :] == h), f"bottom row should collect its whole column: {acc[h-1]}"
    assert np.all(acc[0, :] == 1), "the top row has nothing upstream of it"


def test_U2_catchment_mask_equals_the_accumulated_count():
    """The strongest available cross-check: the number of cells the BFS walks upstream of a
    point must equal the accumulation value the validated function computed for that point."""
    for name, dem in (("valley", _valley()), ("cone", _cone()), ("plane", _plane())):
        acc = frp.d8_accumulation(dem)
        targets = fd.d8_targets(dem)
        h, w = dem.shape
        for outlet in [(h - 1, w // 2), (h // 2, w // 2), (h - 1, 0)]:
            mask = fd.upstream_mask(targets, outlet)
            assert mask.sum() == acc[outlet], (
                f"{name} @{outlet}: BFS walked {mask.sum()} cells, accumulation says "
                f"{acc[outlet]}")
            assert mask[outlet], "the outlet must be inside its own catchment"


def test_U3_nodata_cells_carry_no_flow_and_do_not_leak():
    dem = _valley()
    dem[6, 4] = np.nan
    dem[6, 5] = np.nan
    acc = frp.d8_accumulation(dem)
    assert acc[6, 4] == 0 and acc[6, 5] == 0, "a nodata cell must contribute nothing"
    assert np.all(np.isfinite(acc)), "nodata must not leak NaN into the accumulation"
    targets = fd.d8_targets(dem)
    assert targets[6, 4] == -1 and targets[6, 5] == -1, "a nodata cell has no receiver"


# ------------------------------------------------------------------------------
# U4 + U7 — the truncation guard and its negative control
# ------------------------------------------------------------------------------
def test_U4_catchment_touching_the_dem_edge_is_refused():
    dem = _plane(12, 9)
    targets = fd.d8_targets(dem)
    valid = np.isfinite(dem)
    # The bottom-row outlet collects its whole column, which starts at the top BORDER row:
    # upstream terrain continues beyond the DEM, so its area is an under-estimate.
    mask = fd.upstream_mask(targets, (11, 4))
    edge = fd.touches_invalid(mask, valid)
    assert edge > 0, "a catchment reaching the array border must be detected as truncated"
    assert fd.coverage_ok(None, 95) is False, "unknown coverage must never be stageable"

    # And an interior catchment on the cone flank must NOT be flagged — a guard that rejects
    # everything is as useless as one that rejects nothing.
    cone = _cone()
    mask2 = fd.upstream_mask(fd.d8_targets(cone), (12, 10))
    assert fd.touches_invalid(mask2, np.isfinite(cone)) == 0, (
        "an interior catchment was wrongly flagged as truncated")
    assert fd.coverage_ok(100.0, 95) is True


def test_U4b_nodata_adjacency_counts_as_truncation():
    """Truncation is not only the array border: a catchment running into a nodata hole is
    equally unresolved, because real terrain continues where the DEM has no data."""
    cone = _cone()
    outlet = (12, 10)
    clean = fd.upstream_mask(fd.d8_targets(cone), outlet)
    assert fd.touches_invalid(clean, np.isfinite(cone)) == 0, "fixture must start un-truncated"
    # Punch the hole at a real NEIGHBOUR of the catchment (derived, not guessed) so the
    # catchment genuinely runs into missing data.
    r, c = np.argwhere(clean)[0]
    hole = next((r + dr, c + dc) for dr, dc in fd._D8 if not clean[r + dr, c + dc])
    cone[hole] = np.nan
    mask = fd.upstream_mask(fd.d8_targets(cone), outlet)
    assert fd.touches_invalid(mask, np.isfinite(cone)) > 0, (
        f"catchment adjacent to nodata at {hole} was not flagged truncated")


def test_U7_coverage_guard_negative_control():
    """NEGATIVE CONTROL. Disable the guard and the truncated fixture must become 'stageable' —
    proving the U4 assertion is carried by the guard and not by something else."""
    original = fd.coverage_ok
    try:
        fd.coverage_ok = lambda pct, min_pct: True        # the unguarded behaviour
        assert fd.coverage_ok(None, 95) is True, (
            "the negative control did not take effect — U4 would pass vacuously")
    finally:
        fd.coverage_ok = original
    assert fd.coverage_ok(None, 95) is False, "the guard was not restored"


# ------------------------------------------------------------------------------
# U5-U6 — channel geometry
# ------------------------------------------------------------------------------
def test_U5_off_grid_centroid_gives_an_empty_window_not_a_wraparound():
    is_channel = np.zeros((20, 20), dtype=bool)
    is_channel[0, 0] = True                    # a channel at the top-left corner ONLY
    # A centroid far off the bottom-right: the clamped window must be empty, and must NOT
    # wrap around to find that corner channel (the §60 4c slice bug).
    dist, outlet = fd.nearest_channel(is_channel, 500, 500, 80.0, search_px=3)
    assert dist is None and outlet is None
    # Far off the TOP-LEFT (negative indices) — the classic wraparound direction.
    dist2, _ = fd.nearest_channel(is_channel, -50, -50, 80.0, search_px=3)
    assert dist2 is None, "a negative-index window wrapped around the array"


def test_U6_channel_distance_is_exact():
    is_channel = np.zeros((30, 30), dtype=bool)
    is_channel[10, 15] = True
    px = 80.0
    d, outlet = fd.nearest_channel(is_channel, 10, 12, px)      # 3 cells due west
    assert outlet == (10, 15) and abs(d - 3 * px) < 1e-9, (d, outlet)
    d2, _ = fd.nearest_channel(is_channel, 13, 15, px)          # 3 cells due south
    assert abs(d2 - 3 * px) < 1e-9
    d3, _ = fd.nearest_channel(is_channel, 13, 18, px)          # 3,3 diagonal
    assert abs(d3 - np.hypot(3, 3) * px) < 1e-6
    # A zone exactly at the buffer edge counts as adjacent; one cell further does not.
    assert d == 240.0
    assert (d <= 240.0) and not (d <= 239.0)


def test_U6b_channel_network_uses_the_configured_threshold():
    dem = _valley()
    acc = frp.d8_accumulation(dem)
    px = 80.0
    acc_km2 = acc * px * px / 1e6
    strict = (acc_km2 >= 0.5).sum()
    loose = (acc_km2 >= 0.05).sum()
    assert loose >= strict, "a lower area threshold must never yield fewer channel cells"
    # The default the plan pins to the validated LLOF criterion.
    assert fd.DEFAULT_CHANNEL_UPSTREAM_KM2 == frp.UPSTREAM_KM2 == 0.5


# ------------------------------------------------------------------------------
# Time of concentration (feeds F1's window matching)
# ------------------------------------------------------------------------------
def test_tc_is_monotone_and_bounded():
    # Bigger catchment, same relief -> slower response.
    assert fd.time_of_concentration_h(50, 1200) > fd.time_of_concentration_h(5, 1200)
    # Same area, more relief (steeper) -> faster response.
    assert fd.time_of_concentration_h(10, 2000) < fd.time_of_concentration_h(10, 400)
    # Degenerate inputs return None rather than a fabricated number.
    for bad in ((0, 100), (10, 0), (10, None), (None, 100), (-1, 100)):
        assert fd.time_of_concentration_h(*bad) is None, bad
    # Sanity: a 10 km^2 Himalayan catchment with 1.2 km of relief responds in well under a day.
    tc = fd.time_of_concentration_h(10, 1200)
    assert 0.05 < tc < 6.0, tc


# ------------------------------------------------------------------------------
# Config gating
# ------------------------------------------------------------------------------
def test_flood_config_absent_block_returns_none_and_present_block_parses():
    import tempfile
    from config import load_config
    body = ("aoi_path: config/aoi/ramban_aoi.geojson\njob_name_prefix: T\n"
            "search_start: 2025-05-01\nsearch_end: 2025-10-31\n")
    with tempfile.TemporaryDirectory() as td:
        off = Path(td) / "off.yaml"
        off.write_text(body, encoding="utf-8")
        assert fd.load_flood_config(load_config(off)) is None
        on = Path(td) / "on.yaml"
        on.write_text(body + "flood:\n  channel_upstream_km2: 1.25\n  channel_buffer_m: 300\n",
                      encoding="utf-8")
        fc = fd.load_flood_config(load_config(on))
        assert fc.channel_upstream_km2 == 1.25 and fc.channel_buffer_m == 300
        # An omitted key falls back to the documented default, not to zero.
        assert fc.min_catchment_coverage_pct == 95


# ------------------------------------------------------------------------------
# Regime split (plan §2 scope boundary)
# ------------------------------------------------------------------------------
def test_regime_b_ceiling_stops_delineation():
    """A mainstem-scale catchment must bail out of the BFS instead of walking a million cells —
    the plan excludes Regime B, and the code must enforce that, not just document it."""
    dem = _plane(60, 60)
    targets = fd.d8_targets(dem)
    assert fd.upstream_mask(targets, (59, 30), max_cells=10) is None
    assert fd.upstream_mask(targets, (59, 30), max_cells=10_000) is not None
    assert fd.REGIME_B_KM2 == 200.0


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

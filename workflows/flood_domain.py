#!/usr/bin/env python
"""flood_domain.py — F0 of the Flash-Flood Expansion Plan (docs/references/
FLOOD_EXPANSION_PLAN_2026-07-28.md): the GEOMETRY probe. "Where would water go, and what of
ours is in the way?"

WHY THIS EXISTS: the validated product answers "which slopes are creeping, and is it raining
hard enough to trigger them". It has no notion of the CHANNEL below a slope — yet a documented
failure mechanism on these corridors is a flash flood undercutting the toe of a slope that was
already creeping. F0 supplies the missing geometry, and nothing else: no staging, no warning,
no change to any existing product.

WHAT IT COMPUTES (per registry AOI, from data already on disk — no new tasking, no new AOI):
  1. D8 flow accumulation on the stack's FULL-FRAME DEM (~290x230 km at 80 m — far larger than
     the InSAR AOI, which is exactly why upstream area from OUTSIDE the AOI is captured).
     The accumulation comes from flow_routing_probe.d8_accumulation — the SAME function whose
     criterion was validated and adopted for the routed-LLOF swap (§67), imported, never copied.
  2. The channel network: cells whose upstream area reaches `channel_upstream_km2`
     (default = the probe's validated 0.5 km^2 threshold).
  3. Per operational-footprint zone: distance to the nearest channel, the routed-LLOF flag
     (flow_routing_probe.routed_llof_flag — again shared), and the CATCHMENT draining to that
     nearest channel point: area, relief, bounding box, a time-of-concentration proxy, and a
     TRUNCATION check.
  4. An optional, NON-FATAL MERIT-Hydro cross-check of our upstream areas (needs GEE; skipped
     cleanly without it).

THE GUARD (the §65 lesson, applied before it can bite): a catchment whose cells touch the edge
of the DEM's valid data extends beyond what we can see, so its area is an UNDER-estimate of the
truth. Such a catchment is marked `truncated` and is NOT stageable — F1 refuses to grade it
rather than publishing a confident number computed from a partial catchment.

SCOPE (plan §2): this is a Regime-A tool — local tributary catchments. A "catchment" larger
than REGIME_B_KM2 is a mainstem river (the Chenab at Ramban drains ~10^4 km^2); it is recorded
with `regime: B` and deliberately NOT delineated or staged. Mainstem flood forecasting is
CWC's job with real gauges, and is excluded by the plan.

Outputs data/flood/flood_domain_{slug}.{json,md}. Reads the operational footprint; writes
nothing outside data/flood/.

  docker compose run --rm insar python workflows/flood_domain.py
  docker compose run --rm -e INSAR_CONFIG=config/vaishnodevi.yaml insar python workflows/flood_domain.py
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

from config import load_config  # noqa: E402
# The channel criterion and the accumulation are IMPORTED from the validated probe (plan §5
# shared-function rule) so the flood channels and the adopted LLOF flags can never diverge.
from flow_routing_probe import (  # noqa: E402
    UPSTREAM_KM2 as DEFAULT_CHANNEL_UPSTREAM_KM2,
    d8_accumulation,
    routed_llof_flag,
    stack_dem,
)

FLOOD_DIR = PROJECT_ROOT / "data" / "flood"
CACHE_DIR = FLOOD_DIR / "_cache"

# Scope boundary, not a tuning knob (plan §2): above this drainage area a "catchment" is a
# mainstem river, whose flood behaviour needs gauges and bathymetry we do not have.
REGIME_B_KM2 = 200.0
# How far from a zone centroid we look for a channel before calling it un-exposed (~4.8 km at
# 80 m). Generous on purpose: the answer is a measured DISTANCE, and the buffer decides.
CHANNEL_SEARCH_PX = 60

_D8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
_DIST = {(-1, -1): 1.414, (-1, 0): 1.0, (-1, 1): 1.414, (0, -1): 1.0,
         (0, 1): 1.0, (1, -1): 1.414, (1, 0): 1.0, (1, 1): 1.414}


# ── config (plan §5: an ABSENT `flood:` block disables the arm entirely) ─────────────
@dataclass(frozen=True)
class FloodConfig:
    channel_upstream_km2: float
    channel_buffer_m: float
    min_catchment_coverage_pct: float


def load_flood_config(cfg=None) -> FloodConfig | None:
    """The optional per-AOI `flood:` block, read from the registry YAML this Config came from.

    Returns None when the block is absent — the whole arm is then off. Deliberately read here
    rather than added to config.py: the plan sanctions exactly two touch-points in existing
    files, and the shared config loader is not one of them.
    """
    import yaml
    cfg = cfg or load_config()
    raw = yaml.safe_load(Path(cfg.source_path).read_text(encoding="utf-8")) or {}
    f = raw.get("flood")
    if not f:
        return None
    fc = FloodConfig(
        channel_upstream_km2=float(f.get("channel_upstream_km2",
                                         DEFAULT_CHANNEL_UPSTREAM_KM2)),
        channel_buffer_m=float(f.get("channel_buffer_m", 120)),
        min_catchment_coverage_pct=float(f.get("min_catchment_coverage_pct", 95)),
    )
    # VALIDATE, don't trust (house style — config._llof_routing does the same). Each of these
    # fails SILENTLY and produces a confident wrong answer rather than an error:
    #   * channel_upstream_km2 <= 0 makes EVERY cell a channel, so the "nearest channel" is the
    #     zone's own pixel and every catchment is meaningless;
    #   * channel_buffer_m < 0 makes nothing channel-adjacent, so the exposure layer is empty;
    #   * min_catchment_coverage_pct > 100 makes nothing stageable, so the arm publishes NO
    #     flood risk anywhere and looks calm rather than broken.
    where = Path(cfg.source_path).name
    if not fc.channel_upstream_km2 > 0:
        raise ValueError(f"Config {where}: flood.channel_upstream_km2 must be > 0, got "
                         f"{fc.channel_upstream_km2} (a non-positive threshold makes every "
                         f"cell a channel)")
    if fc.channel_buffer_m < 0:
        raise ValueError(f"Config {where}: flood.channel_buffer_m must be >= 0, got "
                         f"{fc.channel_buffer_m} (negative makes nothing channel-adjacent)")
    if not 0 < fc.min_catchment_coverage_pct <= 100:
        raise ValueError(f"Config {where}: flood.min_catchment_coverage_pct must be in (0, "
                         f"100], got {fc.min_catchment_coverage_pct} (>100 makes every "
                         f"catchment unstageable, which reads as 'no flood risk')")
    return fc


# ── D8 geometry ──────────────────────────────────────────────────────────────────────
def d8_targets(dem: np.ndarray) -> np.ndarray:
    """Steepest-descent receiver per cell as a FLAT index (-1 = pit/edge/nodata).

    flow_routing_probe computes this internally but does not expose it, and the plan forbids
    editing that file. Rather than trust two look-alike implementations, this one is PINNED to
    the shared function: tests/test_flood_domain.py asserts that accumulating over these
    targets reproduces flow_routing_probe.d8_accumulation EXACTLY on several DEMs, so the two
    cannot silently diverge.
    """
    h, w = dem.shape
    z = np.where(np.isfinite(dem), dem, -np.inf)
    best_drop = np.zeros((h, w))
    target = np.full((h, w), -1, dtype=np.int64)
    for dr, dc in _D8:
        zn = np.full((h, w), -np.inf)
        r0, r1 = max(0, dr), h + min(0, dr)
        c0, c1 = max(0, dc), w + min(0, dc)
        zn[r0 - dr:r1 - dr, c0 - dc:c1 - dc] = z[r0:r1, c0:c1]
        with np.errstate(invalid="ignore"):
            drop = np.where(np.isfinite(z) & np.isfinite(zn), (z - zn) / _DIST[(dr, dc)], -np.inf)
        upd = drop > best_drop
        best_drop = np.where(upd, drop, best_drop)
        tgt_flat = (np.arange(h)[:, None] + dr) * w + (np.arange(w)[None, :] + dc)
        target = np.where(upd, tgt_flat, target)
    return target


def upstream_mask(targets: np.ndarray, outlet: tuple[int, int],
                  max_cells: int | None = None) -> np.ndarray | None:
    """Boolean mask of every cell draining to `outlet`, by upstream breadth-first search.

    A neighbour n is a donor of c exactly when targets[n] == flat(c), so the catchment is walked
    in O(cells x 8) without ever building a full donor map of the 10.6 M-cell frame.
    Returns None when the catchment exceeds max_cells (the Regime-B bail-out).
    """
    h, w = targets.shape
    mask = np.zeros((h, w), dtype=bool)
    r0, c0 = outlet
    if not (0 <= r0 < h and 0 <= c0 < w):
        return mask
    mask[r0, c0] = True
    stack = [(r0, c0)]
    n = 1
    while stack:
        r, c = stack.pop()
        flat = r * w + c
        for dr, dc in _D8:
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w and not mask[rr, cc] and targets[rr, cc] == flat:
                mask[rr, cc] = True
                n += 1
                if max_cells is not None and n > max_cells:
                    return None
                stack.append((rr, cc))
    return mask


def touches_invalid(mask: np.ndarray, valid: np.ndarray) -> int:
    """Number of catchment cells adjacent to the DEM's invalid region or to the array border —
    i.e. cells where real upstream terrain may continue outside what we can see."""
    h, w = mask.shape
    rs, cs = np.nonzero(mask)
    n = 0
    for r, c in zip(rs, cs):
        if r == 0 or c == 0 or r == h - 1 or c == w - 1:
            n += 1
            continue
        for dr, dc in _D8:
            if not valid[r + dr, c + dc]:
                n += 1
                break
    return int(n)


def coverage_ok(coverage_pct, min_pct: float) -> bool:
    """A catchment is stageable only when its coverage is KNOWN and meets the bar.

    coverage_pct is None for a truncated catchment — its true area cannot be measured from this
    DEM, so it is refused rather than graded on a partial area (the §65 abort-don't-fabricate
    rule). None is never silently treated as 0 or 100.

    Anything non-numeric is treated as UNKNOWN coverage and refused too: a guard that raises
    mid-run would abort the whole site instead of declining one catchment, and "I could not
    tell" must always fail closed.
    """
    try:
        return coverage_pct is not None and float(coverage_pct) >= float(min_pct)
    except (TypeError, ValueError):
        return False


def time_of_concentration_h(area_km2: float, relief_m: float) -> float | None:
    """Kirpich (1940) time of concentration, with flow length from Hack's law (L = 1.4*A^0.6).

    A PROXY, and labelled as one everywhere it surfaces: Kirpich was fitted on small agricultural
    basins and is known to run short on steep mountain terrain. It is used only to pick which
    trailing rainfall window to grade (F1), never as a published hydrograph quantity.
    """
    if not (area_km2 and area_km2 > 0) or not (relief_m and relief_m > 0):
        return None
    l_km = 1.4 * (area_km2 ** 0.6)
    slope = relief_m / (l_km * 1000.0)
    if slope <= 0:
        return None
    t_min = 0.0195 * ((l_km * 1000.0) ** 0.77) * (slope ** -0.385)
    return round(t_min / 60.0, 3)


def nearest_channel(is_channel: np.ndarray, row: int, col: int, px_m: float,
                    search_px: int = CHANNEL_SEARCH_PX):
    """(distance_m, (row, col)) of the nearest channel cell, or (None, None) if none is within
    the search window. Slices are clamped at BOTH ends so an off-grid centroid yields an empty
    window instead of a negative index that wraps around the array (the §60 4c bug class)."""
    h, w = is_channel.shape
    r0, r1 = max(0, row - search_px), max(0, min(h, row + search_px + 1))
    c0, c1 = max(0, col - search_px), max(0, min(w, col + search_px + 1))
    win = is_channel[r0:r1, c0:c1]
    if win.size == 0 or not win.any():
        return None, None
    rr, cc = np.nonzero(win)
    d = np.hypot((rr + r0) - row, (cc + c0) - col)
    i = int(np.argmin(d))
    return float(d[i] * px_m), (int(rr[i] + r0), int(cc[i] + c0))


# ── per-stack geometry, cached ───────────────────────────────────────────────────────
def _stack_geometry(stack: str, cache: dict):
    """(acc, targets, dem, valid, transform, crs, px_m) for a stack's frame DEM.

    The accumulation is the expensive part (a topological pass over ~10.6 M cells), so it is
    memoised in-process and on disk under data/flood/_cache/ — a re-run is cheap, which keeps
    the workflow-idempotency rule in CLAUDE.md true for this script too.
    """
    if stack in cache:
        return cache[stack]
    import rasterio
    dem_path = stack_dem(stack)
    with rasterio.open(dem_path) as ds:
        dem = ds.read(1).astype(np.float64)
        dem[dem < -1000] = np.nan
        transform, crs, px_m = ds.transform, ds.crs, abs(ds.transform.a)
    valid = np.isfinite(dem)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    acc_npy = CACHE_DIR / f"{stack}_acc.npy"
    if acc_npy.exists():
        acc = np.load(acc_npy)
        if acc.shape != dem.shape:            # DEM changed under a stale cache — recompute
            acc = d8_accumulation(dem)
            np.save(acc_npy, acc)
    else:
        print(f"  [{stack}] computing D8 accumulation on {dem.shape[0]}x{dem.shape[1]} cells "
              f"(cached after this run)...")
        acc = d8_accumulation(dem)
        np.save(acc_npy, acc)
    targets = d8_targets(dem)
    out = (acc, targets, dem, valid, transform, crs, px_m)
    cache[stack] = out
    return out


def _catchment_record(acc, targets, dem, valid, px_m, outlet, fc: FloodConfig, transform, crs):
    """Everything F1 needs about the catchment draining to `outlet`, plus the truncation guard."""
    import pyproj
    import rasterio
    r, c = outlet
    area_km2 = round(float(acc[r, c]) * px_m * px_m / 1e6, 3)
    rec = {"outlet_rowcol": [int(r), int(c)], "area_km2": area_km2,
           "regime": "B" if area_km2 > REGIME_B_KM2 else "A"}
    if rec["regime"] == "B":
        # Plan §2: mainstem — recorded, never delineated or staged.
        rec.update(n_cells=None, truncated=None, coverage_pct=None, stageable=False,
                   relief_m=None, tc_hours=None, bbox_lonlat=None, centroid_lonlat=None,
                   refusal="regime B (mainstem river) — out of scope by plan §2")
        return rec
    max_cells = int(REGIME_B_KM2 * 1e6 / (px_m * px_m)) + 1
    mask = upstream_mask(targets, outlet, max_cells=max_cells)
    if mask is None:                                   # grew past the Regime-A ceiling mid-walk
        rec.update(regime="B", n_cells=None, truncated=None, coverage_pct=None, stageable=False,
                   relief_m=None, tc_hours=None, bbox_lonlat=None, centroid_lonlat=None,
                   refusal="catchment exceeded the Regime-A ceiling during delineation")
        return rec
    n_cells = int(mask.sum())
    edge = touches_invalid(mask, valid)
    truncated = edge > 0
    coverage_pct = None if truncated else 100.0
    z = dem[mask]
    relief = float(np.nanmax(z) - dem[r, c]) if np.isfinite(z).any() else None
    rows, cols = np.nonzero(mask)
    tr = pyproj.Transformer.from_crs(crs, 4326, always_xy=True)
    xs, ys = rasterio.transform.xy(transform, rows, cols)
    lons, lats = tr.transform(np.asarray(xs), np.asarray(ys))
    stageable = coverage_ok(coverage_pct, fc.min_catchment_coverage_pct)
    # The OUTLET's lon/lat — the only point where "upstream area" is comparable to another
    # routing product. (Sampling a reference grid at the catchment CENTROID instead compares
    # our outlet area against a mid-hillslope cell and manufactures a 10-300x "divergence";
    # measured and corrected 2026-07-28, §71.)
    ox, oy = rasterio.transform.xy(transform, r, c)
    olon, olat = pyproj.Transformer.from_crs(crs, 4326, always_xy=True).transform(ox, oy)
    rec.update(
        n_cells=n_cells,
        mask_area_km2=round(n_cells * px_m * px_m / 1e6, 3),
        truncated=bool(truncated), edge_contact_cells=edge, coverage_pct=coverage_pct,
        stageable=bool(stageable),
        relief_m=round(relief, 1) if relief is not None else None,
        tc_hours=time_of_concentration_h(area_km2, relief),
        bbox_lonlat=[round(float(np.min(lons)), 5), round(float(np.min(lats)), 5),
                     round(float(np.max(lons)), 5), round(float(np.max(lats)), 5)],
        centroid_lonlat=[round(float(np.mean(lons)), 5), round(float(np.mean(lats)), 5)],
        outlet_lonlat=[round(float(olon), 5), round(float(olat), 5)],
        refusal=None if stageable else (
            "catchment touches the edge of the DEM's valid data — its true upstream area is "
            "larger than measured here, so it is not graded (coverage unknown)"),
    )
    return rec


# ── optional MERIT-Hydro cross-check (NON-FATAL, needs GEE) ──────────────────────────
MERIT_SNAP_M = 150.0    # ~1.7 MERIT cells: enough to land on its channel, not another basin


def merit_crosscheck(points: list[dict], project: str | None = None,
                     snap_m: float = MERIT_SNAP_M):
    """Compare our D8 upstream areas against MERIT-Hydro's precomputed global flow accumulation
    AT THE OUTLET. Returns None when GEE is unavailable — this is corroboration, and its absence
    must never stop the probe (the radar_watch NISAR-block pattern).

    Two things this has to get right, both learned the hard way (§71):
      • sample at the OUTLET, not the catchment centroid — a centroid sits mid-hillslope, where
        any routing product reports a near-zero upstream area, which manufactured a bogus
        10-300x "divergence" on the first run;
      • take the MAX within a small snap radius rather than the value at the exact point. Our
        grid is 80 m and MERIT's is ~90 m, so the two channel rasters are offset by up to a
        cell; sampling a single point routinely lands one cell OFF MERIT's channel and reads
        hillslope instead. Snapping to the local maximum is the standard cross-resolution
        comparison for flow-accumulation grids.
    """
    if not points:
        return None
    try:
        from fetch_chirps import ee_init
        ee, proj = ee_init(project)
        img = ee.Image("MERIT/Hydro/v1_0_1").select("upa")     # upstream area, km^2
        # TWO samples per outlet: the value AT the point, and the max within the snap radius.
        # Comparing them is what makes the check honest — see the contamination rule below.
        pts = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"id": p["id"]})
            for p in points])
        buf = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]).buffer(snap_m), {"id": p["id"]})
            for p in points])
        at_pt = {f["properties"]["id"]: f["properties"].get("first")
                 for f in img.reduceRegions(pts, ee.Reducer.first(), 92).getInfo()["features"]}
        snapped = {f["properties"]["id"]: f["properties"].get("max")
                   for f in img.reduceRegions(buf, ee.Reducer.max(), 92).getInfo()["features"]}
        rows = []
        for p in points:
            mp, ms = at_pt.get(p["id"]), snapped.get(p["id"])
            # CONTAMINATED: the snap window also touches a channel an order of magnitude larger
            # than the one we are on (the Chenab mainstem runs within 150 m of several of our
            # outlets). Those points cannot be compared at this resolution — they are EXCLUDED
            # from the headline and counted, never quietly averaged in.
            contaminated = bool(mp and ms and ms > 10 * mp)
            rows.append({"id": p["id"], "ours_km2": p["area_km2"],
                         "merit_at_point_km2": round(float(mp), 3) if mp is not None else None,
                         "merit_snap_max_km2": round(float(ms), 3) if ms is not None else None,
                         "ratio_ours_over_merit": (round(p["area_km2"] / float(mp), 3)
                                                   if mp else None),
                         "excluded": contaminated,
                         "exclusion_reason": ("snap window straddles a channel >10x larger — "
                                              "not comparable at 80 m vs 90 m"
                                              if contaminated else None)})
        clean = [r["ratio_ours_over_merit"] for r in rows
                 if r["ratio_ours_over_merit"] and not r["excluded"]]
        spread = (max(clean) / min(clean)) if clean and min(clean) > 0 else None
        # A verdict on the CHECK ITSELF before any verdict on the routing (§65 rule: refuse to
        # publish a number the evidence cannot carry). At Regime-A scale an 80 m and a 90 m
        # channel raster simply do not align well enough for an outlet-point comparison: the
        # exact point usually lands on MERIT's hillslope, and widening the window jumps to a
        # mainstem. When most points are unusable or the survivors disagree wildly, this is
        # INCONCLUSIVE — not a measurement of our routing.
        conclusive = bool(clean and len(clean) >= max(3, len(rows) // 2)
                          and spread is not None and spread <= 3.0)
        return {"ee_project": proj, "snap_m": snap_m, "n_points": len(rows),
                "n_excluded": sum(1 for r in rows if r["excluded"]),
                "n_compared": len(clean), "points": rows,
                "conclusive": conclusive,
                "verdict": (
                    f"median ours/MERIT = {round(float(np.median(clean)), 3)} over "
                    f"{len(clean)} comparable outlets" if conclusive else
                    "INCONCLUSIVE at Regime-A scale — an 80 m vs 90 m channel raster does not "
                    "align well enough at headwater outlets (the exact point lands on MERIT's "
                    "hillslope; widening the window jumps to a mainstem). This says nothing "
                    "about our routing either way; its internal consistency is pinned instead "
                    "by tests (BFS catchment == accumulation) and by sharing the validated "
                    "§67 criterion."),
                "median_ratio_ours_over_merit": (round(float(np.median(clean)), 3)
                                                 if clean else None),
                "ratio_range": ([round(min(clean), 3), round(max(clean), 3)]
                                if clean else None)}
    except Exception as e:  # noqa: BLE001 — corroboration only
        return {"skipped": f"{type(e).__name__}: {e}"}


# ── main ─────────────────────────────────────────────────────────────────────────────
def _write_md(path: Path, rep: dict) -> None:
    fc = rep["config"]
    md = [f"# Flood domain (F0 geometry probe) — {rep['site_name']} (`{rep['slug']}`)", "",
          f"Generated {rep['generated_utc']} UTC. Channels = D8 upstream area >= "
          f"{fc['channel_upstream_km2']} km^2; a zone counts as channel-adjacent within "
          f"{fc['channel_buffer_m']} m.", "",
          "**This is geometry only** — no warning, no staging, no change to any existing "
          "product. Catchment areas come from the same D8 accumulation adopted for the routed "
          "LLOF flag (ledger §67).", "",
          f"- zones examined: **{rep['n_zones']}**",
          f"- channel-adjacent (within {fc['channel_buffer_m']} m): **{rep['n_channel_adjacent']}**",
          f"- catchments delineated: **{rep['n_catchments']}** "
          f"(Regime A {rep['n_regime_a']} · Regime B/mainstem {rep['n_regime_b']})",
          f"- stageable by F1 (coverage known and >= {fc['min_catchment_coverage_pct']}%): "
          f"**{rep['n_stageable']}**",
          f"- truncated at the DEM edge (refused): **{rep['n_truncated']}**", "",
          "| zone | severity | channel dist (m) | adjacent | upstream (km²) | regime | "
          "relief (m) | t_c (h) | stageable |", "|---|---|---|---|---|---|---|---|---|"]
    for z in rep["zones"]:
        cm = z.get("catchment") or {}
        md.append(f"| {z['zone']} | {z['severity']} | "
                  f"{'—' if z['channel_dist_m'] is None else round(z['channel_dist_m'])} | "
                  f"{'yes' if z['channel_adjacent'] else 'no'} | "
                  f"{cm.get('area_km2', '—')} | {cm.get('regime', '—')} | "
                  f"{cm.get('relief_m', '—')} | {cm.get('tc_hours', '—')} | "
                  f"{'YES' if cm.get('stageable') else 'no'} |")
    md += ["", "## How to read the catchment column", "",
           "The catchment shown is the one draining to the **nearest** channel cell to each "
           "zone — the watercourse that could actually undercut that slope. Because the nearest "
           "channel to a hillslope is usually a headwater tributary, these are small basins "
           "just above the "
           f"{fc['channel_upstream_km2']} km² channel threshold, not valley-floor rivers. That "
           "is the intended Regime-A scope (plan §2): a mainstem catchment is recorded as "
           "Regime B and never graded.", ""]
    mc = rep.get("merit_crosscheck")
    md += ["## MERIT-Hydro cross-check", ""]
    if mc is None:
        md.append("_not requested — re-run with `--merit` (needs GEE) to corroborate these "
                  "upstream areas against MERIT-Hydro._")
    elif not mc:
        md.append("_no catchment centroids were available to sample._")
    elif mc.get("skipped"):
        md.append(f"_skipped: {mc['skipped']}_ — corroboration only; the probe stands without it.")
    else:
        md.append(f"Sampled at each catchment **outlet** (not its centroid), snap "
                  f"{mc.get('snap_m')} m. {mc['n_compared']} of {mc['n_points']} points "
                  f"comparable; **{mc.get('n_excluded', 0)} excluded** where the snap window "
                  f"straddles a channel >10x larger (a mainstem passing close by — not "
                  f"comparable at 80 m vs 90 m).")
        md.append("")
        md.append(f"**{mc.get('verdict')}**")
    md += ["", f"**{rep['verdict']}**", ""]
    path.write_text("\n".join(md) + "\n", encoding="utf-8")


def carry_forward_merit(previous: dict | None, merit_points: list[dict]) -> dict | None:
    """Reuse a PREVIOUS MERIT cross-check when this run did not request one.

    Without this, a plain `flood_domain.py` re-run silently overwrites a computed corroboration
    with null — destroying a measurement as a side effect of an unrelated re-run, which is the
    same class of quiet data loss the rest of this project guards against.

    It is only carried when the sampled OUTLETS are unchanged; if the footprint moved, the old
    numbers describe different points and are dropped rather than shown against new geometry.
    Carried results are tagged so a reader can never mistake them for fresh ones.
    """
    if not previous or previous.get("skipped"):
        return None
    prev_ids = {p["id"] for p in previous.get("points", [])}
    if prev_ids != {p["id"] for p in merit_points}:
        return None
    return {**previous, "carried_forward": True,
            "carried_note": ("not recomputed this run — re-run with --merit to refresh "
                             "(outlets unchanged, so these still describe the same points)")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None, help="Registry YAML (default: the active AOI).")
    ap.add_argument("--merit", action="store_true",
                    help="Also run the MERIT-Hydro cross-check (needs GEE; non-fatal).")
    ap.add_argument("--project", default=None, help="GEE project id for --merit.")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    fc = load_flood_config(cfg)
    if fc is None:
        print(f"flood_domain: no `flood:` block in {Path(cfg.source_path).name} — "
              f"the flood arm is DISABLED for this AOI. Nothing written.")
        return 0

    slug, sfx = cfg.aoi_slug, cfg.data_suffix
    fp = PROJECT_ROOT / "data" / f"alerts{sfx}" / "mosaic_asc" / "alerts_operational.json"
    if not fp.exists():
        print(f"flood_domain: no operational footprint at {fp} — run the alert chain first.")
        return 0
    zones = json.loads(fp.read_text(encoding="utf-8"))["zones"]

    import pyproj
    import rasterio
    cache: dict = {}
    out_zones, merit_points = [], []
    for i, z in enumerate(zones, 1):
        stack = z["detected_by_looks"][0]
        acc, targets, dem, valid, transform, crs, px_m = _stack_geometry(stack, cache)
        acc_km2 = acc * px_m * px_m / 1e6
        is_channel = acc_km2 >= fc.channel_upstream_km2
        lon, lat = z["centroid_lonlat"]
        x, y = pyproj.Transformer.from_crs(4326, crs, always_xy=True).transform(lon, lat)
        r, c = rasterio.transform.rowcol(transform, x, y)
        dist_m, outlet = nearest_channel(is_channel, r, c, px_m)
        llof, up_km2 = routed_llof_flag(acc, px_m, r, c)     # the adopted §67 criterion
        rec = {"zone": i, "stack": stack, "severity": z["severity"],
               "centroid_lonlat": [lon, lat],
               "channel_dist_m": None if dist_m is None else round(dist_m, 1),
               "channel_adjacent": bool(dist_m is not None and dist_m <= fc.channel_buffer_m),
               "routed_llof": bool(llof), "zone_upstream_km2": round(up_km2, 3),
               "catchment": None}
        if outlet is not None:
            rec["catchment"] = _catchment_record(acc, targets, dem, valid, px_m, outlet, fc,
                                                 transform, crs)
            cm = rec["catchment"]
            if cm.get("outlet_lonlat") and cm.get("area_km2"):
                merit_points.append({"id": f"zone{i}", "lon": cm["outlet_lonlat"][0],
                                     "lat": cm["outlet_lonlat"][1],
                                     "area_km2": cm["area_km2"]})
        out_zones.append(rec)
        print(f"  zone {i:>2} ({z['severity']:>8}): channel "
              f"{'—' if dist_m is None else f'{dist_m:6.0f} m'}"
              f"{'  ADJACENT' if rec['channel_adjacent'] else ''}"
              + (f" | catchment {rec['catchment']['area_km2']} km^2 "
                 f"({rec['catchment']['regime']}"
                 f"{', TRUNCATED' if rec['catchment'].get('truncated') else ''}"
                 f"{', stageable' if rec['catchment'].get('stageable') else ''})"
                 if rec["catchment"] else ""))

    cats = [z["catchment"] for z in out_zones if z["catchment"]]
    n_a = sum(1 for c in cats if c["regime"] == "A")
    n_b = sum(1 for c in cats if c["regime"] == "B")
    n_stage = sum(1 for c in cats if c.get("stageable"))
    n_trunc = sum(1 for c in cats if c.get("truncated"))
    n_adj = sum(1 for z in out_zones if z["channel_adjacent"])
    rep = {
        "slug": slug, "site_name": cfg.site_name,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "footprint": str(fp.relative_to(PROJECT_ROOT).as_posix()),
        "config": {"channel_upstream_km2": fc.channel_upstream_km2,
                   "channel_buffer_m": fc.channel_buffer_m,
                   "min_catchment_coverage_pct": fc.min_catchment_coverage_pct,
                   "regime_b_km2": REGIME_B_KM2, "channel_search_px": CHANNEL_SEARCH_PX},
        "n_zones": len(out_zones), "n_channel_adjacent": n_adj,
        "n_catchments": len(cats), "n_regime_a": n_a, "n_regime_b": n_b,
        "n_stageable": n_stage, "n_truncated": n_trunc,
        "zones": out_zones,
        "merit_crosscheck": None,      # filled below
    }
    out_json = FLOOD_DIR / f"flood_domain_{slug}.json"
    if args.merit:
        rep["merit_crosscheck"] = merit_crosscheck(merit_points, args.project)
    elif out_json.exists():
        try:
            prev = json.loads(out_json.read_text(encoding="utf-8")).get("merit_crosscheck")
        except Exception:  # noqa: BLE001 — an unreadable previous run is simply no previous run
            prev = None
        rep["merit_crosscheck"] = carry_forward_merit(prev, merit_points)
        if rep["merit_crosscheck"]:
            print("  (MERIT cross-check carried forward from the previous run — "
                  "re-run with --merit to refresh)")
    rep["verdict"] = (
        f"{n_adj}/{len(out_zones)} operational zones sit within {fc.channel_buffer_m} m of a "
        f"channel draining >= {fc.channel_upstream_km2} km^2; {n_stage} catchment(s) are "
        f"complete enough to grade in F1"
        + (f", {n_trunc} refused as truncated" if n_trunc else "")
        + (f", {n_b} are mainstem (Regime B, out of scope)" if n_b else "") + ".")
    FLOOD_DIR.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    _write_md(FLOOD_DIR / f"flood_domain_{slug}.md", rep)
    print(f"VERDICT: {rep['verdict']}")
    print(f"  -> {out_json.name} , flood_domain_{slug}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

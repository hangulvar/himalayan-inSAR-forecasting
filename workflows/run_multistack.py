#!/usr/bin/env python
"""
run_multistack.py — drive Phases 2-4 across all connectable stacks and build the
AOI-wide product as a UNION across radar look geometries.

Part-4 design decisions:
  * Runs the stacks the connectivity gate marks "connected" (standard
    least-squares). Disconnected stacks (frame479 -> SVD, frame484 ->
    period-split) are detected from data/qa_masks/_rescue_recommendations.json
    and SKIPPED with a note — those inversions are a later pass.
  * Different looks (ASC path27 vs path100, DESC) image the ground with different
    LOS geometry, so velocities are NOT averaged. The AOI product is a UNION at
    the hazard/alert level: a slope is flagged if ANY look detects instability +
    measured creep. (FS itself is DEM-derived and geometry-independent.)

Stages (idempotent — a heavy stage is skipped when its output is newer than its
inputs; pass --force to recompute everything):
  2. Phase 2  custom_sbas_inverter.py  --stack S         -> data/velocity/
  3. Phase 3  geomechanical_engine.py  --stack S         -> data/hazard/
  4. Phase 4  agentic_orchestrator.py  --stack S --out-dir data/alerts/<S>/
  M. Mosaic   union hazard_class raster + union alert zones across the stacks
                                  -> data/mosaic/ , data/alerts/mosaic_asc/

Usage:
    python workflows/run_multistack.py            # connected stacks, all scenarios
    python workflows/run_multistack.py --force    # recompute every stage
    python workflows/run_multistack.py --stacks ASC_path27_frame106 ...  # explicit subset
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds

from config import load_config  # noqa: F401  (kept for AOI-config parity / future use)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = PROJECT_ROOT / "workflows"
QA_DIR = PROJECT_ROOT / "data" / "qa_masks"
RESCUE_RECOMMENDATIONS = QA_DIR / "_rescue_recommendations.json"
QUARANTINE_CSV = QA_DIR / "_quarantine_list.csv"
VEL_DIR = PROJECT_ROOT / "data" / "velocity"
HAZ_DIR = PROJECT_ROOT / "data" / "hazard"
ALERTS_DIR = PROJECT_ROOT / "data" / "alerts"
MOSAIC_DIR = PROJECT_ROOT / "data" / "mosaic"
MOSAIC_ALERTS_DIR = ALERTS_DIR / "mosaic_asc"
LOG_DIR = PROJECT_ROOT / "logs"

SCENARIOS = ["dry", "monsoon", "extreme"]
HAZARD_HIGH = 2.0
MERGE_DEG = 0.0015  # ~165 m: zones nearer than this (different looks) are one place

LOG_DIR.mkdir(exist_ok=True)
MOSAIC_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(LOG_DIR / "run_multistack.log", encoding="utf-8")],
)
logger = logging.getLogger("run_multistack")


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def _run(script: str, *args: str) -> None:
    cmd = [sys.executable, str(WORKFLOWS / script), *args]
    logger.info("  $ python workflows/%s %s", script, " ".join(args))
    if subprocess.run(cmd).returncode != 0:
        raise SystemExit(f"{script} failed for args {args}")


def _stale(output: Path, *inputs: Path) -> bool:
    """True if output is missing or older than any existing input."""
    if not output.exists():
        return True
    omt = output.stat().st_mtime
    return any(p.exists() and p.stat().st_mtime > omt for p in inputs)


def connected_stacks() -> list[str]:
    """Stacks the rescue gate marks 'connected' (eligible for least-squares)."""
    if not RESCUE_RECOMMENDATIONS.exists():
        raise SystemExit(
            f"Missing {RESCUE_RECOMMENDATIONS}. Run "
            "`python workflows/sbas_network_graph.py --recommend-only` first."
        )
    diag = json.loads(RESCUE_RECOMMENDATIONS.read_text(encoding="utf-8")).get("stacks", {})
    conn = sorted(s for s, d in diag.items() if d.get("status") == "connected")
    skipped = sorted(s for s, d in diag.items() if d.get("status") != "connected")
    if skipped:
        logger.info("Skipping non-connected stacks (need SVD/period-split): %s", skipped)
    return conn


# ------------------------------------------------------------------------------
# Per-stack Phases 2-4
# ------------------------------------------------------------------------------
def run_phases_per_stack(stack: str, force: bool) -> None:
    vel = VEL_DIR / f"{stack}_mean_velocity_los_highpass.tif"
    haz = HAZ_DIR / f"{stack}_hazard_class.tif"
    alerts_monsoon = ALERTS_DIR / stack / "alerts_monsoon.json"

    if force or _stale(vel, QUARANTINE_CSV):
        logger.info("[%s] Phase 2 — SBAS inversion", stack)
        _run("custom_sbas_inverter.py", "--stack", stack)
    else:
        logger.info("[%s] Phase 2 — up to date, skipping", stack)

    if force or _stale(haz, vel):
        logger.info("[%s] Phase 3 — geomechanical hazard", stack)
        _run("geomechanical_engine.py", "--stack", stack)
    else:
        logger.info("[%s] Phase 3 — up to date, skipping", stack)

    if force or _stale(alerts_monsoon, haz):
        logger.info("[%s] Phase 4 — per-stack alerts", stack)
        _run("agentic_orchestrator.py", "--stack", stack,
             "--out-dir", str(ALERTS_DIR / stack))
    else:
        logger.info("[%s] Phase 4 — up to date, skipping", stack)


# ------------------------------------------------------------------------------
# Mosaic: union hazard raster
# ------------------------------------------------------------------------------
def _common_grid(rasters: list[Path]):
    """(transform, width, height, crs) covering the union of all rasters, in the
    first raster's CRS at its pixel size. Bounds are reprojected to that CRS, so
    stacks in different UTM zones still union correctly."""
    with rasterio.open(rasters[0]) as r0:
        crs = r0.crs
        res = abs(r0.transform.a)
    lefts, bottoms, rights, tops = [], [], [], []
    for p in rasters:
        with rasterio.open(p) as r:
            l, b, rt, t = transform_bounds(r.crs, crs, *r.bounds)
            lefts.append(l); bottoms.append(b); rights.append(rt); tops.append(t)
    left, bottom, right, top = min(lefts), min(bottoms), max(rights), max(tops)
    width = int(round((right - left) / res))
    height = int(round((top - bottom) / res))
    return from_origin(left, top, res, res), width, height, crs


def _reproject_band(path: Path, transform, width, height, crs, resampling):
    dst = np.full((height, width), np.nan, dtype=np.float32)
    with rasterio.open(path) as src:
        reproject(
            source=rasterio.band(src, 1), destination=dst,
            src_transform=src.transform, src_crs=src.crs,
            dst_transform=transform, dst_crs=crs,
            resampling=resampling, src_nodata=src.nodata, dst_nodata=np.nan,
        )
    return dst


def mosaic_hazard(stacks: list[str]) -> dict:
    """Union each stack's hazard_class onto a common grid: a pixel takes the
    MAX class seen by any look (HIGH if any look says HIGH). Also writes a
    per-pixel 'how many looks flagged HIGH' coverage layer."""
    haz_paths = [HAZ_DIR / f"{s}_hazard_class.tif" for s in stacks
                 if (HAZ_DIR / f"{s}_hazard_class.tif").exists()]
    if not haz_paths:
        raise SystemExit("No per-stack hazard rasters found; run Phase 3 first.")
    transform, w, h, crs = _common_grid(haz_paths)

    union = np.full((h, w), -1.0, dtype=np.float32)
    n_high = np.zeros((h, w), dtype=np.int16)
    for p in haz_paths:
        hz = _reproject_band(p, transform, w, h, crs, Resampling.nearest)
        union = np.maximum(union, np.where(np.isfinite(hz), hz, -1.0))
        n_high += (hz == HAZARD_HIGH).astype(np.int16)
    union[union < 0] = np.nan

    prof = {"driver": "GTiff", "dtype": "float32", "count": 1, "crs": crs,
            "transform": transform, "width": w, "height": h,
            "nodata": np.nan, "compress": "lzw"}
    with rasterio.open(MOSAIC_DIR / "MOSAIC_ASC_hazard_class.tif", "w", **prof) as d:
        d.write(union, 1)
    with rasterio.open(MOSAIC_DIR / "MOSAIC_ASC_n_looks_high.tif", "w",
                       **dict(prof, dtype="int16", nodata=0)) as d:
        d.write(n_high.astype(np.int16), 1)

    counts = {
        "grid": f"{w}x{h} @ {abs(transform.a):.0f} m, {crs}",
        "low": int(np.sum(union == 0.0)),
        "watch": int(np.sum(union == 1.0)),
        "high": int(np.sum(union == HAZARD_HIGH)),
        "high_multi_look": int(np.sum(n_high >= 2)),
    }
    logger.info("Mosaic hazard: LOW=%(low)d WATCH=%(watch)d HIGH=%(high)d "
                "(HIGH confirmed by >=2 looks: %(high_multi_look)d)", counts)
    return counts


# ------------------------------------------------------------------------------
# Mosaic: union alert zones across looks
# ------------------------------------------------------------------------------
def _merge_group(group: list[dict]) -> dict:
    lons = [a["centroid_lonlat"][0] for a in group]
    lats = [a["centroid_lonlat"][1] for a in group]
    looks = sorted({a["_stack"] for a in group})
    severity = "CRITICAL" if any(a["severity"] == "CRITICAL" for a in group) else "HIGH"
    llof = any(a["downstream_risk"]["llof_potential"] for a in group)
    return {
        "severity": severity,
        "centroid_lonlat": [round(sum(lons) / len(lons), 5), round(sum(lats) / len(lats), 5)],
        "detected_by_looks": looks,
        "n_looks": len(looks),
        # Union semantics: strongest creep / worst FS that ANY look measured here.
        "min_fs_any_look": round(min(a["mean_fs"] for a in group), 3),
        "strongest_creep_mmyr": round(min(a["mean_velocity_mmyr"] for a in group), 1),
        "max_area_km2": round(max(a["area_km2"] for a in group), 4),
        "llof_potential": llof,
    }


def union_alerts(stacks: list[str], scenario: str) -> list[dict]:
    zones: list[dict] = []
    for s in stacks:
        f = ALERTS_DIR / s / f"alerts_{scenario}.json"
        if not f.exists():
            continue
        for a in json.loads(f.read_text(encoding="utf-8")).get("alerts", []):
            zones.append({**a, "_stack": s})

    merged: list[dict] = []
    used = [False] * len(zones)
    for i, z in enumerate(zones):
        if used[i]:
            continue
        group = [z]
        used[i] = True
        for j in range(i + 1, len(zones)):
            if used[j]:
                continue
            if (abs(zones[j]["centroid_lonlat"][1] - z["centroid_lonlat"][1]) < MERGE_DEG
                    and abs(zones[j]["centroid_lonlat"][0] - z["centroid_lonlat"][0]) < MERGE_DEG):
                group.append(zones[j])
                used[j] = True
        merged.append(_merge_group(group))
    merged.sort(key=lambda a: a["strongest_creep_mmyr"])
    return merged


def write_union_alerts(stacks: list[str]) -> dict:
    MOSAIC_ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}
    for sc in SCENARIOS:
        zones = union_alerts(stacks, sc)
        n_crit = sum(1 for z in zones if z["severity"] == "CRITICAL")
        n_multi = sum(1 for z in zones if z["n_looks"] >= 2)
        payload = {
            "scenario": sc,
            "method": "union across look geometries (a slope is flagged if ANY look "
                      "detects FS<1 AND measured creep)",
            "source_stacks": stacks,
            "summary": {"n_union_zones": len(zones), "n_critical": n_crit,
                        "n_confirmed_multi_look": n_multi},
            "zones": zones,
        }
        (MOSAIC_ALERTS_DIR / f"alerts_{sc}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8")
        _write_union_briefing(MOSAIC_ALERTS_DIR / f"alert_report_{sc}.md", sc, stacks, zones)
        summary[sc] = payload["summary"]
        logger.info("Union alerts [%s]: %d zones (%d critical, %d multi-look confirmed)",
                    sc, len(zones), n_crit, n_multi)
    return summary


def _write_union_briefing(path: Path, scenario: str, stacks: list[str], zones: list[dict]) -> None:
    lines = [
        f"# AOI-wide Union Alert Briefing — scenario: {scenario.upper()}",
        "",
        f"Union across {len(stacks)} ascending look(s): {', '.join(stacks)}.",
        "A zone is listed if **any** look found a slope both theoretically unstable "
        "(FS<1) and measurably creeping. Multi-look zones are corroborated by more "
        "than one geometry and are the most trustworthy.",
        "",
        f"**{len(zones)} union zone(s)** "
        f"({sum(1 for z in zones if z['severity']=='CRITICAL')} critical, "
        f"{sum(1 for z in zones if z['n_looks']>=2)} confirmed by >=2 looks).",
        "",
        "| # | severity | lon, lat | looks | min FS | strongest creep (mm/yr) | LLOF |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, z in enumerate(zones, 1):
        lon, lat = z["centroid_lonlat"]
        lines.append(
            f"| {i} | {z['severity']} | {lon:.4f}, {lat:.4f} | "
            f"{z['n_looks']} ({', '.join(s.replace('ASC_','') for s in z['detected_by_looks'])}) | "
            f"{z['min_fs_any_look']:.2f} | {z['strongest_creep_mmyr']:.0f} | "
            f"{'yes' if z['llof_potential'] else 'no'} |"
        )
    if not zones:
        lines.append("_No union zones — nothing flagged by any look in this scenario._")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------
# Driver
# ------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stacks", nargs="*", default=None,
                    help="Explicit stack list (default: all 'connected' stacks).")
    ap.add_argument("--force", action="store_true",
                    help="Recompute every stage even if outputs are up to date.")
    args = ap.parse_args()

    stacks = args.stacks if args.stacks else connected_stacks()
    if not stacks:
        raise SystemExit("No connected stacks to run.")
    logger.info("Multi-stack run over: %s", stacks)

    for stack in stacks:
        run_phases_per_stack(stack, args.force)

    logger.info("=== Building AOI-wide union mosaic ===")
    haz_counts = mosaic_hazard(stacks)
    alert_summary = write_union_alerts(stacks)

    logger.info("-" * 60)
    logger.info("Multi-stack complete. Stacks: %s", stacks)
    logger.info("Mosaic hazard grid %s — HIGH=%d (>=2 looks: %d)",
                haz_counts["grid"], haz_counts["high"], haz_counts["high_multi_look"])
    for sc, s in alert_summary.items():
        logger.info("  %-8s union zones=%d critical=%d multi-look=%d",
                    sc, s["n_union_zones"], s["n_critical"], s["n_confirmed_multi_look"])
    logger.info("Outputs: data/mosaic/MOSAIC_ASC_hazard_class.tif , "
                "data/alerts/mosaic_asc/alerts_<scenario>.json + briefings; "
                "per-stack alerts in data/alerts/<stack>/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

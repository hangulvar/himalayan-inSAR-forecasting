#!/usr/bin/env python
"""flow_routing_probe.py — Tier 4c of the Strengthening Plan (§56): would REAL flow routing
change the LLOF (landslide-lake outflow / debris-channel) flags, which today come from a TWI
PROXY? Measure-first, no product swap: the validated footprints stay untouched pre-merge; this
probe quantifies the divergence so the swap decision is evidence-based.

METHOD: D8 flow accumulation on each stack's full DEM (upstream drainage area per cell,
computed in elevation-descending topological order — real routing, including catchment area
from OUTSIDE the AOI, which the TWI proxy cannot see). For every operational-footprint zone:
is there a significant drainage path (upstream area >= 0.5 km^2) within ~240 m of the zone
centroid? Compare that ROUTED flag against the zone's existing TWI-proxy `llof_potential`.

Outputs data/hazard/flow_routing_probe.{json,md}; headline -> ledger (§60).
  docker compose run --rm insar python workflows/flow_routing_probe.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

MANIFEST = PROJECT_ROOT / "data" / "qa_masks" / "_stack_manifest.json"
TIFFS = PROJECT_ROOT / "data" / "processed_tiffs"
UPSTREAM_KM2 = 0.5
NEAR_PX = 3                       # ~240 m at 80 m pixels
AOI_SFX = {"ramban": "", "vaishnodevi": "_vaishnodevi"}

_D8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def d8_accumulation(dem: np.ndarray) -> np.ndarray:
    """Upstream cell count per cell (incl. itself), single-direction D8, NaN = sink/edge."""
    h, w = dem.shape
    z = np.where(np.isfinite(dem), dem, -np.inf)
    # Steepest-descent neighbour index per cell (flat index; -1 = pit/edge).
    best_drop = np.zeros((h, w))
    target = np.full((h, w), -1, dtype=np.int64)
    dist = {(-1, -1): 1.414, (-1, 0): 1.0, (-1, 1): 1.414, (0, -1): 1.0,
            (0, 1): 1.0, (1, -1): 1.414, (1, 0): 1.0, (1, 1): 1.414}
    for dr, dc in _D8:
        zn = np.full((h, w), -np.inf)
        r0, r1 = max(0, dr), h + min(0, dr)
        c0, c1 = max(0, dc), w + min(0, dc)
        zn[r0 - dr:r1 - dr, c0 - dc:c1 - dc] = z[r0:r1, c0:c1]
        with np.errstate(invalid="ignore"):
            drop = np.where(np.isfinite(z) & np.isfinite(zn),
                            (z - zn) / dist[(dr, dc)], -np.inf)
        upd = drop > best_drop
        best_drop = np.where(upd, drop, best_drop)
        tgt_flat = (np.arange(h)[:, None] + dr) * w + (np.arange(w)[None, :] + dc)
        target = np.where(upd, tgt_flat, target)
    acc = np.ones(h * w)
    acc[~np.isfinite(dem).ravel()] = 0
    order = np.argsort(z.ravel())[::-1]               # high -> low: donors before receivers
    tgt = target.ravel()
    for i in order:
        t = tgt[i]
        if t >= 0 and acc[i] > 0:
            acc[t] += acc[i]
    return acc.reshape(h, w)


def routed_llof_flag(acc: np.ndarray, px_m: float, row: int, col: int,
                     upstream_km2: float = UPSTREAM_KM2,
                     near_px: int = NEAR_PX) -> tuple[bool, float]:
    """The single LLOF criterion shared by this probe and the orchestrator's
    `llof_routing: d8` mode (§60 4c): max upstream drainage area within near_px
    of (row, col), flagged when it reaches upstream_km2."""
    # Clamp both ends to [0, shape] — a far-off-grid centroid must give an EMPTY
    # window, never a negative slice index that wraps around the array.
    r0, r1 = max(0, row - near_px), max(0, min(acc.shape[0], row + near_px + 1))
    c0, c1 = max(0, col - near_px), max(0, min(acc.shape[1], col + near_px + 1))
    window = acc[r0:r1, c0:c1]
    up_km2 = float(window.max()) * (px_m * px_m) / 1e6 if window.size else 0.0
    return up_km2 >= upstream_km2, up_km2


def stack_dem(stack: str) -> Path:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, meta in man.items():
        if meta.get("stack") == stack:
            p = TIFFS / name / f"{name}_dem.tif"
            if p.exists():
                return p
    raise SystemExit(f"No DEM tif found for stack {stack}")


def main() -> int:
    import pyproj
    report = {"upstream_threshold_km2": UPSTREAM_KM2, "near_px": NEAR_PX, "sites": {}}
    acc_cache: dict[str, tuple] = {}
    for slug, sfx in AOI_SFX.items():
        fp = PROJECT_ROOT / "data" / f"alerts{sfx}" / "mosaic_asc" / "alerts_operational.json"
        zones = json.loads(fp.read_text(encoding="utf-8"))["zones"]
        rows = []
        for i, zzz in enumerate(zones, 1):
            stack = zzz["detected_by_looks"][0]
            if stack not in acc_cache:
                dem_path = stack_dem(stack)
                with rasterio.open(dem_path) as ds:
                    dem = ds.read(1).astype(np.float64)
                    dem[dem < -1000] = np.nan
                    acc_cache[stack] = (d8_accumulation(dem), ds.transform, ds.crs,
                                        abs(ds.transform.a))
            acc, tr, crs, px = acc_cache[stack]
            lon, lat = zzz["centroid_lonlat"]
            x, y = pyproj.Transformer.from_crs(4326, crs, always_xy=True).transform(lon, lat)
            r, c = rasterio.transform.rowcol(tr, x, y)
            routed, up_km2 = routed_llof_flag(acc, px, r, c)
            rows.append({"zone": i, "stack": stack, "severity": zzz["severity"],
                         "twi_llof": bool(zzz["llof_potential"]),
                         "routed_llof": routed,
                         "max_upstream_km2": round(up_km2, 2),
                         "agree": routed == bool(zzz["llof_potential"])})
        n = len(rows)
        agree = sum(r["agree"] for r in rows)
        report["sites"][slug] = {
            "n_zones": n, "n_agree": agree,
            "flips_proxy_only": [r["zone"] for r in rows if r["twi_llof"] and not r["routed_llof"]],
            "flips_routed_only": [r["zone"] for r in rows if r["routed_llof"] and not r["twi_llof"]],
            "zones": rows}
        print(f"[{slug}] {agree}/{n} agree | proxy-only "
              f"{report['sites'][slug]['flips_proxy_only']} | routed-only "
              f"{report['sites'][slug]['flips_routed_only']}")
    tot = sum(s["n_zones"] for s in report["sites"].values())
    agr = sum(s["n_agree"] for s in report["sites"].values())
    flips = tot - agr
    report["verdict"] = (
        f"{agr}/{tot} zones agree between the TWI proxy and real D8 routing; {flips} flip. "
        + ("Divergence is material — schedule the validated swap to routed LLOF (a scored "
           "re-run, post-merge)." if flips / max(tot, 1) > 0.25 else
           "Divergence is small — the TWI proxy is an acceptable stand-in at zone scale; a "
           "swap is low priority (documented)."))
    out = PROJECT_ROOT / "data" / "hazard" / "flow_routing_probe.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [f"# Flow-routing probe vs TWI-proxy LLOF flags (Tier 4c)", "",
          f"D8 upstream area, threshold {UPSTREAM_KM2} km² within {NEAR_PX}px (~240 m).", ""]
    for slug, s in report["sites"].items():
        md.append(f"## {slug} — {s['n_agree']}/{s['n_zones']} agree "
                  f"(proxy-only flips {s['flips_proxy_only']}, routed-only "
                  f"{s['flips_routed_only']})")
        md += [f"- zone {r['zone']} ({r['stack']}, {r['severity']}): TWI {r['twi_llof']} vs "
               f"routed {r['routed_llof']} (upstream {r['max_upstream_km2']} km²)"
               for r in s["zones"]] + [""]
    md += [f"**{report['verdict']}**"]
    (PROJECT_ROOT / "data" / "hazard" / "flow_routing_probe.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")
    print("VERDICT:", report["verdict"])
    print(f"-> {out} , .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

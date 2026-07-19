#!/usr/bin/env python
"""polygon_stats.py — risk statistics for USER-DRAWN polygons (e.g. Google Earth Pro
KML of a suspect formation) against the current AOI product.

For each polygon: pixel coverage, hazard-class breakdown, ≥2-look confirmation,
per-track LOS velocity, slope, FS_dry/FS_sat, elevation range, distance to the
nearest alert zone per scenario, and a plain-language risk line. Report lands next
to the other operator artefacts (md + json).

  docker compose run --rm insar python workflows/polygon_stats.py \
      --polygons my_polygons.kml            # KML (Google Earth) or GeoJSON
"""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from pyproj import Transformer

from config import load_config
from stacks import product_stacks

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CFG = load_config()
_SFX = _CFG.data_suffix
MOSAIC_DIR = PROJECT_ROOT / "data" / f"mosaic{_SFX}"
VEL_DIR = PROJECT_ROOT / "data" / f"velocity{_SFX}"
HAZ_DIR = PROJECT_ROOT / "data" / f"hazard{_SFX}"
ALERTS_DIR = PROJECT_ROOT / "data" / f"alerts{_SFX}" / "mosaic_asc"
SCENARIOS = ["operational", "watch", "monsoon"]
HAZ_NAME = {0: "LOW", 1: "WATCH", 2: "HIGH"}


def read_polygons(path: Path) -> list[dict]:
    """[{name, rings_lonlat}] from a Google-Earth KML or a GeoJSON."""
    if path.suffix.lower() == ".kml":
        out = []
        root = ET.parse(path).getroot()
        for pm in root.iter():
            if not pm.tag.endswith("Placemark"):
                continue
            name = next((e.text for e in pm.iter() if e.tag.endswith("name")), "unnamed")
            for poly in (e for e in pm.iter() if e.tag.endswith("Polygon")):
                coords = next(e for e in poly.iter() if e.tag.endswith("coordinates"))
                ring = [[float(v) for v in c.split(",")[:2]]
                        for c in coords.text.split()]
                out.append({"name": name.strip(), "ring": ring})
        return out
    gj = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for i, f in enumerate(gj.get("features", [])):
        g = f["geometry"]
        if g["type"] not in ("Polygon", "MultiPolygon"):
            continue                       # lines/points aren't area targets
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for p in polys:
            out.append({"name": f.get("properties", {}).get("name", f"feature {i}"),
                        "ring": p[0]})
    return out


def stat(a, mask):
    v = a[mask]
    v = v[np.isfinite(v)]
    return (round(float(np.median(v)), 1), round(float(v.min()), 1),
            round(float(v.max()), 1)) if v.size else (None, None, None)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--polygons", required=True, help="KML or GeoJSON of polygons.")
    ap.add_argument("--out-name", default="polygon_stats")
    args = ap.parse_args()

    polys = read_polygons(Path(args.polygons))
    if not polys:
        raise SystemExit(f"No polygons found in {args.polygons}")
    stacks = product_stacks()

    with rasterio.open(MOSAIC_DIR / "MOSAIC_ASC_hazard_class.tif") as src:
        haz = src.read(1)
        tfm, crs, shape = src.transform, src.crs, src.shape
    with rasterio.open(MOSAIC_DIR / "MOSAIC_ASC_n_looks_high.tif") as src:
        looks = src.read(1)
    vels = {s: rasterio.open(VEL_DIR / f"{s}_mean_velocity_los_highpass.tif").read(1)
            for s in stacks}
    fs_sat = {s: rasterio.open(HAZ_DIR / f"{s}_FS_saturated.tif").read(1) for s in stacks}
    slope = rasterio.open(HAZ_DIR / f"{stacks[0]}_slope_deg.tif").read(1)
    zones = {}
    for sc in SCENARIOS:
        f = ALERTS_DIR / f"alerts_{sc}.json"
        zones[sc] = ([tuple(z["centroid_lonlat"]) for z in
                      json.loads(f.read_text(encoding="utf-8"))["zones"]]
                     if f.exists() else [])

    to_grid = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    results = []
    for p in polys:
        ring_xy = [to_grid.transform(lon, lat) for lon, lat in p["ring"]]
        geom = {"type": "Polygon", "coordinates": [ring_xy]}
        mask = ~geometry_mask([geom], out_shape=shape, transform=tfm, invert=False)
        n_px = int(mask.sum())
        clon = float(np.mean([c[0] for c in p["ring"]]))
        clat = float(np.mean([c[1] for c in p["ring"]]))
        r = {"name": p["name"], "centroid_lonlat": [round(clon, 6), round(clat, 6)],
             "n_pixels_80m": n_px, "area_km2": round(n_px * 0.0064, 3)}
        if n_px == 0:
            r["note"] = ("polygon smaller than one 80 m pixel or outside the grid — "
                         "sampling the centroid pixel instead")
            row, col = rasterio.transform.rowcol(tfm, *to_grid.transform(clon, clat))
            if 0 <= row < shape[0] and 0 <= col < shape[1]:
                mask = np.zeros(shape, bool)
                mask[row, col] = True
                n_px = 1
            else:
                results.append(r)
                continue
        counts = {HAZ_NAME.get(int(k), str(k)): int(v) for k, v in
                  zip(*np.unique(haz[mask & np.isfinite(haz)], return_counts=True))}
        r["hazard_px"] = counts
        r["px_2look_confirmed"] = int((looks[mask] >= 2).sum())
        r["slope_deg_median_min_max"] = stat(slope, mask)
        r["los_velocity_mmyr"] = {s: dict(zip(("median", "min", "max"),
                                              stat(vels[s], mask))) for s in stacks}
        r["fs_saturated_median"] = {s: stat(fs_sat[s], mask)[0] for s in stacks}
        r["dist_to_zone_m"] = {}
        for sc in SCENARIOS:
            if zones[sc]:
                d = min(math.hypot((clon - zx) * 93000, (clat - zy) * 111000)
                        for zx, zy in zones[sc])
                r["dist_to_zone_m"][sc] = round(d)
        # plain-language risk line
        creeping = any((v["median"] is not None and v["median"] <= -15)
                       for v in r["los_velocity_mmyr"].values())
        unstable = any(v is not None and v < 1.0 for v in r["fs_saturated_median"].values())
        near_op = r["dist_to_zone_m"].get("operational", 9e9) <= 250
        if r["px_2look_confirmed"] and creeping:
            risk = "HIGH INTEREST: measured creep confirmed by 2 tracks inside polygon"
        elif creeping and unstable:
            risk = "ELEVATED: single-track creep AND FS_sat<1 (would join alert zones when wet)"
        elif creeping:
            risk = "WATCH: single-track creep signal (could be noise — check confidence)"
        elif unstable:
            risk = "CONDITIONAL: physics-unstable when saturated, but no measured creep"
        else:
            risk = "LOW on current data: no creep signal, FS_sat >= 1"
        if near_op:
            risk += "; within 250 m of an operational alert zone"
        r["risk_line"] = risk
        results.append(r)
        print(f"[{p['name']}] {n_px}px  2look={r['px_2look_confirmed']}  "
              f"haz={counts}  -> {risk}")

    out = {"generated": date.today().isoformat(), "aoi": _CFG.aoi_slug,
           "source": Path(args.polygons).name, "stacks": stacks, "polygons": results,
           "caveats": "80 m pixels; LOS velocities (not 3-D); FS physics uses the "
                      "site config's soil parameters; [see RESULTS_AND_KPIS caveats]"}
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    jpath = ALERTS_DIR / f"{args.out_name}.json"
    jpath.write_text(json.dumps(out, indent=2), encoding="utf-8")
    lines = [f"# Polygon risk statistics — {_CFG.site_name} ({out['generated']})",
             f"", f"Source: `{out['source']}` | stacks: {', '.join(stacks)}", ""]
    for r in results:
        lines += [f"## {r['name']}  —  {r.get('risk_line', 'n/a')}", "",
                  "```json", json.dumps(r, indent=1), "```", ""]
    (ALERTS_DIR / f"{args.out_name}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"-> {jpath} , .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

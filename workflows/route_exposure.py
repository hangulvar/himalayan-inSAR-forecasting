#!/usr/bin/env python
"""route_exposure.py — WHICH PARTS OF THE ROUTE are exposed to the flagged hazard
(RESULTS_AND_KPIS.md §28). Overlays the curated route/infrastructure GeoJSON
(<slug>_route.geojson — OSM-derived walkable ways, ropeway, helipads, POIs) on the
union hazard mosaic + union alert zones, and emits a ranked per-segment read.

Method (honest about resolution):
  * The route is densified to ~40 m samples and each sample gets
      - distance to the nearest ≥2-look HIGH pixel (the multi-track CORE — trust first),
      - distance to the nearest HIGH pixel (any look),
      - distance to the nearest union alert-zone *edge* per scenario (zones are
        centroid+area circles — an 80 m-pixel-honest approximation).
  * A sample is exposed when within BUFFER_M = 250 m — the honest detection buffer the
    scored back-test supports (§16b); ≤ ON_M = 80 m (one pixel) counts as a direct hit.
  * Exposure class (highest wins): CORE (≥2-look px) > OPERATIONAL > WATCH > MONSOON
    (worst-case-only). Consecutive same-class samples merge into segments, ranked
    CORE-first — the "read first" list for the track.

Caveats inherited from §27: the underlying product is [UNVALIDATED] at this site
(borrowed φ, short chains, no local inventory) — treat as reconnaissance triage.

  docker compose run --rm insar python workflows/route_exposure.py
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from pyproj import Transformer  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402

from config import load_config  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CFG = load_config()
SLUG = _CFG.aoi_slug
MOSAIC_DIR = PROJECT_ROOT / "data" / f"mosaic{_CFG.data_suffix}"
OUT_DIR = PROJECT_ROOT / "data" / f"alerts{_CFG.data_suffix}" / "mosaic_asc"
INVENTORY = PROJECT_ROOT / "data" / "inventory" / f"{SLUG}_documented_landslides.geojson"

SCENARIOS = ["operational", "watch", "monsoon"]      # tier order after CORE
CLASS_ORDER = ["CORE", "OPERATIONAL", "WATCH", "MONSOON"]
CLASS_COLOR = {"CORE": "#7a0177", "OPERATIONAL": "#dc2828", "WATCH": "#f0b428",
               "MONSOON": "#fdae6b", "CLEAR": "#2ca25f"}
BUFFER_M = 250.0    # exposure buffer — the §16b honest detection buffer
ON_M = 80.0         # one mosaic pixel = a direct hit
STEP_M = 40.0       # route densification step


def densify(coords_xy: list[tuple[float, float]], step: float):
    """Yield points every `step` metres along a polyline (grid CRS)."""
    out = [coords_xy[0]]
    for (x0, y0), (x1, y1) in zip(coords_xy, coords_xy[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        n = max(int(seg // step), 1)
        for i in range(1, n + 1):
            out.append((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n))
    return out


def load_zones(scenario: str):
    """Union zones as (x, y, radius_m, attrs) in the mosaic CRS."""
    path = OUT_DIR / f"alerts_{scenario}.json"
    if not path.exists():
        return []
    zones = json.loads(path.read_text(encoding="utf-8")).get("zones", [])
    out = []
    for z in zones:
        lon, lat = z["centroid_lonlat"]
        x, y = TO_GRID.transform(lon, lat)
        r = math.sqrt(max(z.get("max_area_km2", 0.0), 1e-4) * 1e6 / math.pi)
        out.append((x, y, r, z))
    return out


def zone_distance(x: float, y: float, zones) -> tuple[float, dict | None]:
    """Distance (m) from a point to the nearest zone EDGE, and that zone."""
    best, best_z = float("inf"), None
    for zx, zy, zr, z in zones:
        d = max(math.hypot(x - zx, y - zy) - zr, 0.0)
        if d < best:
            best, best_z = d, z
    return best, best_z


def classify(d_core: float, dists: dict[str, float]) -> str:
    if d_core <= BUFFER_M:
        return "CORE"
    for sc, cls in (("operational", "OPERATIONAL"), ("watch", "WATCH"),
                    ("monsoon", "MONSOON")):
        if dists[sc] <= BUFFER_M:
            return cls
    return "CLEAR"


def main() -> int:
    global TO_GRID
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--route", default=str(PROJECT_ROOT / f"{SLUG}_route.geojson"))
    args = ap.parse_args()

    route_path = Path(args.route)
    if not route_path.exists():
        raise SystemExit(f"Missing route file {route_path} — curate it from OSM first.")
    haz_path = MOSAIC_DIR / "MOSAIC_ASC_hazard_class.tif"
    looks_path = MOSAIC_DIR / "MOSAIC_ASC_n_looks_high.tif"
    if not haz_path.exists():
        raise SystemExit(f"Missing {haz_path} — run run_multistack.py first.")

    with rasterio.open(haz_path) as src:
        haz = src.read(1)
        transform, crs = src.transform, src.crs
        px = abs(transform.a)
    with rasterio.open(looks_path) as src:
        looks = src.read(1)

    TO_GRID = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    high = haz == 2
    core = looks >= 2
    # Distance (m) to nearest True pixel; inf when the mask is empty.
    d_high_px = (distance_transform_edt(~high) * px if high.any()
                 else np.full(haz.shape, np.inf))
    d_core_px = (distance_transform_edt(~core) * px if core.any()
                 else np.full(haz.shape, np.inf))
    zones = {sc: load_zones(sc) for sc in SCENARIOS}

    def raster_dist(arr, x, y):
        row, col = rasterio.transform.rowcol(transform, x, y)
        if 0 <= row < arr.shape[0] and 0 <= col < arr.shape[1]:
            return float(arr[row, col])
        return float("inf")

    gj = json.loads(route_path.read_text(encoding="utf-8"))
    segments, points, lines_for_map = [], [], []
    for feat in gj["features"]:
        props, geom = feat["properties"], feat["geometry"]
        label = props.get("name") or f"unnamed {props.get('kind', 'way')}"
        if geom["type"] == "Point":
            x, y = TO_GRID.transform(*geom["coordinates"])
            dists = {sc: zone_distance(x, y, zones[sc])[0] for sc in SCENARIOS}
            cls = classify(raster_dist(d_core_px, x, y), dists)
            points.append({"name": label, "kind": props.get("kind"), "class": cls,
                           "lonlat": geom["coordinates"],
                           "dist_m": {k: (None if math.isinf(v) else round(v))
                                      for k, v in dists.items()}})
            continue

        xy = [TO_GRID.transform(lon, lat) for lon, lat in geom["coordinates"]]
        samples = densify(xy, STEP_M)
        lines_for_map.append((xy, label))
        cur = None
        for i, (x, y) in enumerate(samples):
            d_core = raster_dist(d_core_px, x, y)
            d_high = raster_dist(d_high_px, x, y)
            dists = {sc: zone_distance(x, y, zones[sc])[0] for sc in SCENARIOS}
            cls = classify(d_core, dists)
            if cls == "CLEAR":
                cur = None
                continue
            d_op, z_op = zone_distance(x, y, zones["operational"])
            if cur is None or cur["class"] != cls:
                lon0, lat0 = Transformer.from_crs(crs, "EPSG:4326",
                                                  always_xy=True).transform(x, y)
                cur = {"way": label, "kind": props.get("kind"),
                       "osm_id": props.get("osm_id"), "class": cls,
                       "start_lonlat": [round(lon0, 5), round(lat0, 5)],
                       "length_m": 0.0, "min_core_m": d_core, "min_high_m": d_high,
                       "min_zone_m": min(dists.values()), "direct_hit": False,
                       "nearest_op_zone": None}
                segments.append(cur)
            cur["length_m"] += STEP_M
            cur["min_core_m"] = min(cur["min_core_m"], d_core)
            cur["min_high_m"] = min(cur["min_high_m"], d_high)
            cur["min_zone_m"] = min(cur["min_zone_m"], min(dists.values()))
            cur["direct_hit"] |= (d_core <= ON_M or d_high <= ON_M
                                  or min(dists.values()) <= ON_M)
            if z_op is not None and d_op <= BUFFER_M and cur["nearest_op_zone"] is None:
                cur["nearest_op_zone"] = {
                    "severity": z_op.get("severity"), "n_looks": z_op.get("n_looks"),
                    "creep_mmyr": z_op.get("strongest_creep_mmyr"),
                    "llof": z_op.get("llof_potential")}

    for s in segments:                       # tidy for JSON
        for k in ("min_core_m", "min_high_m", "min_zone_m"):
            s[k] = None if math.isinf(s[k]) else round(s[k])
        s["length_m"] = round(s["length_m"])
    segments.sort(key=lambda s: (CLASS_ORDER.index(s["class"]),
                                 s["min_zone_m"] if s["min_zone_m"] is not None else 9e9,
                                 -s["length_m"]))

    # Ground truth overlay (§31): classify each documented/GSI location like the
    # infrastructure points, so the map carries the verification evidence too.
    truth = []
    if INVENTORY.exists():
        for feat in json.loads(INVENTORY.read_text(encoding="utf-8"))["features"]:
            if feat["geometry"]["type"] != "Point":
                continue
            p = feat["properties"]
            x, y = TO_GRID.transform(*feat["geometry"]["coordinates"])
            dists = {sc: zone_distance(x, y, zones[sc])[0] for sc in SCENARIOS}
            truth.append({"name": p.get("name"), "type": p.get("type"),
                          "date": p.get("date"),
                          "class": classify(raster_dist(d_core_px, x, y), dists),
                          "lonlat": feat["geometry"]["coordinates"],
                          "min_zone_m": (None if math.isinf(min(dists.values()))
                                         else round(min(dists.values())))})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {"generated": date.today().isoformat(), "aoi": SLUG,
              "route_file": route_path.name, "buffer_m": BUFFER_M, "on_m": ON_M,
              "validity": "UNVALIDATED at this site — reconnaissance triage (§27)",
              "class_order": CLASS_ORDER,
              "n_segments": len(segments), "segments": segments,
              "infrastructure_points": points,
              "ground_truth": truth}
    (OUT_DIR / "route_exposure.json").write_text(json.dumps(report, indent=2),
                                                 encoding="utf-8")
    write_md(OUT_DIR / "route_exposure.md", report)
    make_map(OUT_DIR / "route_exposure.png", haz, core, transform, crs,
             lines_for_map, segments, points, truth)

    n_by = {c: sum(1 for s in segments if s["class"] == c) for c in CLASS_ORDER}
    km_by = {c: sum(s["length_m"] for s in segments if s["class"] == c) / 1000
             for c in CLASS_ORDER}
    print(f"route exposure ({SLUG}): {len(segments)} exposed segment(s)")
    for c in CLASS_ORDER:
        if n_by[c]:
            print(f"  {c:<12s}: {n_by[c]:3d} segment(s), {km_by[c]:5.2f} km")
    for p in points:
        print(f"  [{p['class']:<12s}] {p['kind']}: {p['name']}")
    print(f"  -> {OUT_DIR / 'route_exposure.md'} , .json , .png")
    return 0


def write_md(path: Path, r: dict) -> None:
    lines = [f"# Route exposure — {r['aoi']} ({r['generated']})", "",
             f"_Exposure buffer {r['buffer_m']:.0f} m (§16b honest detection buffer); "
             f"direct hit ≤ {r['on_m']:.0f} m (one pixel). **{r['validity']}**_", "",
             "Read CORE first (≥2-look multi-track pixels), then OPERATIONAL "
             "(m=0.50 standing product), WATCH (m=0.70 recall net), MONSOON "
             "(worst-case-only).", "",
             "| # | class | way | length | min dist | direct hit | nearest op-zone |",
             "|---|---|---|---|---|---|---|"]
    for i, s in enumerate(r["segments"], 1):
        z = s["nearest_op_zone"]
        ztxt = (f"{z['severity']}, {z['n_looks']}-look, {z['creep_mmyr']} mm/yr"
                + (", LLOF" if z and z.get("llof") else "")) if z else "—"
        lines.append(f"| {i} | **{s['class']}** | {s['way']} ({s['kind']}) "
                     f"| {s['length_m']} m | {s['min_zone_m']} m "
                     f"| {'YES' if s['direct_hit'] else 'no'} | {ztxt} |")
    lines += ["", "## Infrastructure points", ""]
    for p in r["infrastructure_points"]:
        lines.append(f"- **{p['class']}** — {p['name']} ({p['kind']}); "
                     f"zone distances (m): {p['dist_m']}")
    truth = r.get("ground_truth", [])
    if truth:
        by = {}
        for t in truth:
            by[t["class"]] = by.get(t["class"], 0) + 1
        lines += ["", "## Ground truth (GSI inventory, §31) vs the flagged zones", "",
                  f"{len(truth)} documented locations; by exposure class: "
                  + ", ".join(f"{k} {v}" for k, v in sorted(by.items())) + ".", ""]
        for t in truth:
            if t.get("date"):
                lines.append(f"- ★ **{t['date']} — {t['name']}**: class **{t['class']}**, "
                             f"nearest zone {t['min_zone_m']} m.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_map(path: Path, haz, core, transform, crs, lines, segments, points,
             truth=()) -> None:
    from rasterio.plot import plotting_extent
    fig, ax = plt.subplots(figsize=(9, 10))
    ext = plotting_extent(haz, transform)
    shade = np.full(haz.shape + (4,), 0.0)
    shade[haz == 1] = (0.99, 0.85, 0.46, 0.5)          # WATCH class px
    shade[haz == 2] = (0.86, 0.16, 0.16, 0.7)          # HIGH px
    shade[core] = (0.48, 0.01, 0.47, 1.0)              # >=2-look core
    ax.imshow(shade, extent=ext)
    for xy, label in lines:
        xs, ys = zip(*xy)
        ax.plot(xs, ys, color="#1a6198", lw=1.2, alpha=0.8)
    to_grid = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    for s in segments[:25]:
        x, y = to_grid.transform(*s["start_lonlat"])
        ax.plot(x, y, "o", ms=6, mec="k", mfc=CLASS_COLOR[s["class"]])
    for p in points:
        x, y = to_grid.transform(*p["lonlat"])
        ax.plot(x, y, "^", ms=9, mec="k", mfc=CLASS_COLOR.get(p["class"], "#999"))
        ax.annotate(p["name"][:22], (x, y), fontsize=6, xytext=(3, 3),
                    textcoords="offset points")
    for t in truth:
        x, y = to_grid.transform(*t["lonlat"])
        if t.get("date"):                       # the dated disaster: unmissable star
            ax.plot(x, y, "*", ms=17, mec="k", mfc="#e31a1c", zorder=6)
            ax.annotate(f"{t['date']} {t['name'][:28]}", (x, y), fontsize=7,
                        fontweight="bold", xytext=(5, -9), textcoords="offset points")
        else:
            ax.plot(x, y, "x", ms=4, mew=1.2, color="#111", alpha=0.75)
    ax.set_title(f"Route exposure — hazard px (yellow/red), ≥2-look core (purple),\n"
                 f"route (blue), segment starts (dots), infrastructure (triangles),\n"
                 f"GSI ground truth (× = surveyed instability, ★ = 26 Aug 2025 disaster)")
    ax.set_xlabel(str(crs))
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

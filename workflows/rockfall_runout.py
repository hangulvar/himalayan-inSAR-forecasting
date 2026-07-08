#!/usr/bin/env python
"""rockfall_runout.py — energy-line rockfall RUNOUT cone from a source polygon:
"which structures below are in the fall path" (Watchlist README idea #6).

Empirical shadow-angle / Fahrboeschung method (Evans & Hungr 1993; Heim 1932):
a falling block usually stops before the line drawn from its detachment point
at the *reach angle* to the horizontal. For every DEM cell below the source
polygon we compute the STEEPEST energy line from any source cell,

    reach_angle(target) = max over sources of atan[(z_src - z_tgt) / dist],

and band it: >= 32 deg LIKELY (most fragmental rockfall stops inside this),
>= 27.5 deg POSSIBLE (median travel angles), >= 22 deg MAX-SHADOW (empirical
worst case for talus-slope shadows). The route/POIs (curated <slug>_route
.geojson) and cached OSM buildings are then sampled against the cone.

This is a first-order screen, not a trajectory simulation (no bounce, no
block size, no barriers/forest). It answers "could a rock physically get
there", not "will one".

  docker compose run --rm insar python workflows/rockfall_runout.py \
      --polygons "Research/Vaishno_Devi_Watchlist/Vaishno_Devi_Bhavan_Overhang.kml"
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
from matplotlib.colors import LightSource  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.features import geometry_mask  # noqa: E402
from rasterio.windows import from_bounds  # noqa: E402
from pyproj import Transformer  # noqa: E402

from config import load_config  # noqa: E402
from polygon_stats import read_polygons  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CFG = load_config()
SLUG = _CFG.aoi_slug
ALERTS_DIR = PROJECT_ROOT / "data" / f"alerts{_CFG.data_suffix}" / "mosaic_asc"
ROUTE_PATH = PROJECT_ROOT / f"{SLUG}_route.geojson"
BUILDINGS_PATH = PROJECT_ROOT / "data" / "osm" / f"{SLUG}_buildings_overpass.json"

# Band thresholds (deg) — empirical reach angles for fragmental rockfall.
BANDS = [("LIKELY", 32.0), ("POSSIBLE", 27.5), ("MAX_SHADOW", 22.0)]
BAND_COLOR = {"LIKELY": "#b30000", "POSSIBLE": "#e6550d", "MAX_SHADOW": "#fdae6b"}
SOURCE_CHUNK = 64          # sources broadcast per numpy chunk
MAX_SOURCES = 4000         # subsample beyond this (12.5 m cells)
POI_STEP_M = 20.0          # route densification step


def find_dem() -> Path:
    dem_dir = PROJECT_ROOT / "data" / f"dem_alos_12m{_CFG.data_suffix}"
    dems = sorted(dem_dir.glob("*.dem.tif"))
    if not dems:
        raise SystemExit(f"No ALOS DEM found in {dem_dir}")
    return dems[0]


def reach_angle_grid(dem: np.ndarray, transform, src_mask: np.ndarray) -> np.ndarray:
    """Max energy-line angle (deg) from any source cell to every cell, on the
    DEM window grid. Horizontal distance in metres (projected CRS assumed)."""
    res = abs(transform.a)
    rows, cols = np.nonzero(src_mask)
    if rows.size > MAX_SOURCES:
        step = int(np.ceil(rows.size / MAX_SOURCES))
        rows, cols = rows[::step], cols[::step]
    src_z = dem[rows, cols]
    h, w = dem.shape
    yy, xx = np.mgrid[0:h, 0:w]
    best_tan = np.full(dem.shape, -np.inf, dtype=np.float32)
    for i in range(0, rows.size, SOURCE_CHUNK):
        r, c = rows[i:i + SOURCE_CHUNK], cols[i:i + SOURCE_CHUNK]
        z = src_z[i:i + SOURCE_CHUNK]
        # (chunk, h, w) horizontal distance and height drop per source
        d = np.hypot(yy[None] - r[:, None, None],
                     xx[None] - c[:, None, None]).astype(np.float32) * res
        d = np.maximum(d, res)  # avoid /0 at the source cell itself
        tan = (z[:, None, None].astype(np.float32) - dem[None]) / d
        best_tan = np.maximum(best_tan, tan.max(axis=0))
    ang = np.degrees(np.arctan(best_tan)).astype(np.float32)
    ang[~np.isfinite(dem)] = np.nan
    return ang


def classify(angle_deg: float | None) -> str:
    if angle_deg is None or not np.isfinite(angle_deg):
        return "OUTSIDE"
    for name, thr in BANDS:
        if angle_deg >= thr:
            return name
    return "CLEAR"


def sample(grid: np.ndarray, transform, x: float, y: float) -> float | None:
    row, col = rasterio.transform.rowcol(transform, x, y)
    if 0 <= row < grid.shape[0] and 0 <= col < grid.shape[1]:
        v = grid[row, col]
        return float(v) if np.isfinite(v) else None
    return None


def densify_lonlat(coords, step_m: float):
    """~step_m-spaced lon/lat samples along a lon/lat polyline."""
    out = [tuple(coords[0])]
    for (lo0, la0), (lo1, la1) in zip(coords, coords[1:]):
        seg = math.hypot((lo1 - lo0) * 93000, (la1 - la0) * 111000)
        n = max(int(seg // step_m), 1)
        for i in range(1, n + 1):
            out.append((lo0 + (lo1 - lo0) * i / n, la0 + (la1 - la0) * i / n))
    return out


def load_buildings() -> list[dict]:
    """[{lonlat, name}] from the cached Overpass 'out center' JSON (see README
    of the watchlist for the fetch command); [] when the cache is absent."""
    if not BUILDINGS_PATH.exists():
        return []
    data = json.loads(BUILDINGS_PATH.read_text(encoding="utf-8-sig"))
    out = []
    for el in data.get("elements", []):
        ctr = el.get("center") or (
            {"lat": el.get("lat"), "lon": el.get("lon")} if el.get("lat") else None)
        if ctr:
            out.append({"lonlat": [ctr["lon"], ctr["lat"]],
                        "name": (el.get("tags") or {}).get("name", "")})
    return out


def band_polygons_kml(angle: np.ndarray, transform, crs, out_path: Path) -> None:
    """One KML polygon layer per band, for Google Earth field use."""
    from rasterio.features import shapes as rio_shapes
    to_ll = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    doc = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
           f"<name>rockfall runout bands — {_CFG.site_name}</name>"]
    kml_col = {"LIKELY": "600000b3", "POSSIBLE": "600d55e6", "MAX_SHADOW": "606baefd"}
    for name, thr in BANDS:
        m = (angle >= thr).astype(np.uint8)
        doc.append(f'<Folder><name>{name} (&gt;= {thr} deg)</name>')
        for geom, val in rio_shapes(m, mask=m.astype(bool), transform=transform):
            for ring in geom["coordinates"][:1]:      # outer ring only
                ll = [to_ll.transform(x, y) for x, y in ring]
                coords = " ".join(f"{lo:.6f},{la:.6f},0" for lo, la in ll)
                doc.append(
                    f'<Placemark><name>{name}</name><Style><PolyStyle>'
                    f'<color>{kml_col[name]}</color></PolyStyle><LineStyle>'
                    f'<color>ff{kml_col[name][2:]}</color></LineStyle></Style>'
                    f'<Polygon><outerBoundaryIs><LinearRing><coordinates>'
                    f'{coords}</coordinates></LinearRing></outerBoundaryIs>'
                    f'</Polygon></Placemark>')
        doc.append("</Folder>")
    doc.append("</Document></kml>")
    out_path.write_text("\n".join(doc), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--polygons", required=True,
                    help="KML/GeoJSON of the source formation (detachment zone).")
    ap.add_argument("--out-name", default="rockfall_runout")
    ap.add_argument("--buffer-km", type=float, default=3.0,
                    help="Analysis window beyond the polygon bbox (default 3 km).")
    args = ap.parse_args()

    polys = read_polygons(Path(args.polygons))
    if not polys:
        raise SystemExit(f"No polygons found in {args.polygons}")
    dem_path = find_dem()

    with rasterio.open(dem_path) as src:
        to_grid = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        # window: union bbox of all polygons + buffer, clipped to the DEM
        xs, ys = [], []
        for p in polys:
            for lon, lat in p["ring"]:
                x, y = to_grid.transform(lon, lat)
                xs.append(x); ys.append(y)
        buf = args.buffer_km * 1000
        win = from_bounds(min(xs) - buf, min(ys) - buf,
                          max(xs) + buf, max(ys) + buf, src.transform)
        win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        dem = src.read(1, window=win).astype(np.float32)
        if src.nodata is not None:
            dem[dem == src.nodata] = np.nan
        transform = src.window_transform(win)
        crs = src.crs

    src_mask = np.zeros(dem.shape, bool)
    for p in polys:
        ring_xy = [to_grid.transform(lon, lat) for lon, lat in p["ring"]]
        geom = {"type": "Polygon", "coordinates": [ring_xy]}
        src_mask |= ~geometry_mask([geom], out_shape=dem.shape,
                                   transform=transform, invert=False)
    if not src_mask.any():
        raise SystemExit("Source polygon rasterized to zero DEM cells.")

    print(f"DEM window {dem.shape} @ {abs(transform.a):.1f} m, "
          f"{int(src_mask.sum())} source cells — computing energy lines…")
    angle = reach_angle_grid(dem, transform, src_mask)
    angle_outside = np.where(src_mask, np.nan, angle)   # cone = outside the source

    # ---- exposure of the curated route/POIs --------------------------------
    route = json.loads(ROUTE_PATH.read_text(encoding="utf-8")) \
        if ROUTE_PATH.exists() else {"features": []}
    pois, segments = [], []
    for f in route["features"]:
        g, props = f["geometry"], f.get("properties", {})
        label = props.get("name") or props.get("kind") or "unnamed"
        if g["type"] == "Point":
            x, y = to_grid.transform(*g["coordinates"][:2])
            a = sample(angle_outside, transform, x, y)
            pois.append({"name": label, "kind": props.get("kind", ""),
                         "reach_angle_deg": None if a is None else round(a, 1),
                         "class": classify(a)})
        elif g["type"] == "LineString":
            pts = densify_lonlat([c[:2] for c in g["coordinates"]], POI_STEP_M)
            classes = []
            for lon, lat in pts:
                x, y = to_grid.transform(lon, lat)
                classes.append(classify(sample(angle_outside, transform, x, y)))
            n_in = {name: classes.count(name) for name, _ in BANDS}
            exposed_m = sum(n_in.values()) * POI_STEP_M
            if exposed_m:
                segments.append({
                    "name": label, "kind": props.get("kind", ""),
                    "exposed_m": int(exposed_m),
                    "m_per_band": {k: int(v * POI_STEP_M) for k, v in n_in.items() if v},
                })
    segments.sort(key=lambda s: -s["exposed_m"])

    # ---- buildings (cached OSM Overpass; coverage is HONESTLY sparse) ------
    buildings = load_buildings()
    b_rows = []
    for b in buildings:
        x, y = to_grid.transform(*b["lonlat"])
        a = sample(angle_outside, transform, x, y)
        cls = classify(a)
        if cls not in ("CLEAR", "OUTSIDE"):
            b_rows.append({**b, "reach_angle_deg": round(a, 1), "class": cls})

    # ---- rasters + map ------------------------------------------------------
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    prof = {"driver": "GTiff", "dtype": "float32", "count": 1, "crs": crs,
            "transform": transform, "width": dem.shape[1], "height": dem.shape[0],
            "nodata": np.nan, "compress": "lzw"}
    tif = ALERTS_DIR / f"{args.out_name}_reach_angle_deg.tif"
    with rasterio.open(tif, "w", **prof) as dst:
        dst.write(angle, 1)
    kml = ALERTS_DIR / f"{args.out_name}_bands.kml"
    band_polygons_kml(angle_outside, transform, crs, kml)

    fig, ax = plt.subplots(figsize=(10, 9))
    ls = LightSource(azdeg=315, altdeg=45)
    dem_f = np.where(np.isfinite(dem), dem, np.nanmedian(dem))
    ax.imshow(ls.hillshade(dem_f, vert_exag=1.5), cmap="gray", alpha=0.9)
    for name, thr in reversed(BANDS):
        band = (angle_outside >= thr)
        ax.contourf(band.astype(float), levels=[0.5, 1.5],
                    colors=[BAND_COLOR[name]], alpha=0.45)
        ax.plot([], [], color=BAND_COLOR[name], lw=6, alpha=0.6,
                label=f"{name} (energy line >= {thr} deg)")
    sy, sx = np.nonzero(src_mask)
    ax.scatter(sx, sy, s=1, c="#2b0057", alpha=0.5, label="source formation")
    for f in route["features"]:
        g = f["geometry"]
        if g["type"] == "LineString":
            pix = [rasterio.transform.rowcol(transform, *to_grid.transform(lo, la))
                   for lo, la in (c[:2] for c in g["coordinates"])]
            ax.plot([c for _, c in pix], [r for r, _ in pix],
                    color="#1f78b4", lw=1.1)
        elif g["type"] == "Point":
            r, c = rasterio.transform.rowcol(
                transform, *to_grid.transform(*g["coordinates"][:2]))
            if 0 <= r < dem.shape[0] and 0 <= c < dem.shape[1]:
                ax.plot(c, r, "^", color="k", ms=7)
                ax.annotate(f["properties"].get("name", ""), (c, r),
                            fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.plot([], [], color="#1f78b4", lw=1.1, label="route (curated OSM)")
    ax.set_title(f"Rockfall runout screen — {_CFG.site_name}\n"
                 f"energy-line cone from {Path(args.polygons).stem}")
    ax.set_axis_off()
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    png = ALERTS_DIR / f"{args.out_name}.png"
    fig.savefig(png, dpi=150)
    plt.close(fig)

    out = {
        "generated": date.today().isoformat(), "aoi": SLUG,
        "source_polygons": Path(args.polygons).name, "dem": dem_path.name,
        "method": "empirical energy line (Fahrboeschung/shadow angle), max over "
                  "all source cells; bands LIKELY>=32deg / POSSIBLE>=27.5deg / "
                  "MAX_SHADOW>=22deg (Evans & Hungr 1993)",
        "pois": pois,
        "route_segments_exposed": segments,
        "buildings_in_cone": b_rows,
        "n_buildings_checked": len(buildings),
        "caveats": "First-order screen: no trajectory/bounce/barrier physics "
                   "and NO terrain-blocking check (the energy line ignores "
                   "intervening ridges — treat any band that crosses one with "
                   "suspicion); the 22deg MAX_SHADOW band at multi-km range is "
                   "an extreme upper bound relevant only to very large "
                   "detachments; 12.5 m DEM smooths cliffs (crest reach angles "
                   "conservative); OSM building coverage at the shrine complex "
                   "is nearly empty so 'buildings_in_cone' UNDERCOUNTS — the "
                   "POI/route exposure is the trustworthy part.",
    }
    (ALERTS_DIR / f"{args.out_name}.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    lines = [f"# Rockfall runout screen — {_CFG.site_name} ({out['generated']})", "",
             f"Source: `{out['source_polygons']}` on `{out['dem']}` | {out['method']}",
             "", f"![map]({png.name})", "",
             "## POIs", "", "| POI | reach angle | class |", "|---|---|---|"]
    for p in pois:
        lines.append(f"| {p['name']} | {p['reach_angle_deg']} | {p['class']} |")
    lines += ["", "## Route segments inside the cone", "",
              "| way | exposed length | per band |", "|---|---|---|"]
    for s in segments:
        lines.append(f"| {s['name'] or s['kind']} | {s['exposed_m']} m | "
                     f"{s['m_per_band']} |")
    if not segments:
        lines.append("| _none_ | | |")
    lines += ["", f"## Buildings in cone ({len(b_rows)} of {len(buildings)} checked)",
              "", "```json", json.dumps(b_rows, indent=1), "```", "",
              "---", f"_{out['caveats']}_", ""]
    (ALERTS_DIR / f"{args.out_name}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"-> {png.name} , .md , .json , _bands.kml , _reach_angle_deg.tif "
          f"in {ALERTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

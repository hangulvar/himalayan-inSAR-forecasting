#!/usr/bin/env python
"""gacos_request.py — print exactly what to paste into the GACOS web form.

GACOS (http://www.gacos.net) has NO API: tropospheric-delay grids are requested
through a web form (bbox + time-of-day + date list) and delivered by email as a
tarball. This helper shrinks that manual step to copy/paste: it reads the radar
library's stack manifest and the active AOI, and prints — per stack — the form
values for every acquisition epoch we actually hold products for.

The companion `gacos_ingest.py` converts the delivered tarball into the
`<YYYYMMDD>.ztd.tif` GeoTIFFs that `_gacos_crosscheck.py` (§40) consumes.

Stdlib-only (no rasterio/geopandas/network) — runs natively without env setup:
    python workflows/gacos_request.py                     # all stacks, active AOI bbox
    python workflows/gacos_request.py --stacks ASC_path27_frame105,ASC_path100_frame103
    INSAR_CONFIG=config/ramban.yaml python workflows/gacos_request.py
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from config import load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STACK_MANIFEST = PROJECT_ROOT / "data" / "qa_masks" / "_stack_manifest.json"


def aoi_bounds_4326(aoi_path: Path) -> tuple[float, float, float, float]:
    """(min_lon, min_lat, max_lon, max_lat) from a GeoJSON in EPSG:4326, stdlib-only."""
    lons: list[float] = []
    lats: list[float] = []

    def walk(coords) -> None:
        if isinstance(coords[0], (int, float)):
            lons.append(float(coords[0]))
            lats.append(float(coords[1]))
        else:
            for c in coords:
                walk(c)

    gj = json.loads(aoi_path.read_text(encoding="utf-8"))
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    for f in feats:
        walk((f.get("geometry") or f)["coordinates"])
    return min(lons), min(lats), max(lons), max(lats)


def epochs_by_stack() -> dict[str, dict[str, str]]:
    """stack -> {YYYYMMDD: HH:MM:SS} from the products in the stack manifest.

    Product names are 'S1AA_<t1>_<t2>_...' where t = YYYYMMDDTHHMMSS; both scenes
    of every pair are epochs of the stack's track."""
    manifest = json.loads(STACK_MANIFEST.read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for product, meta in manifest.items():
        stack = meta["stack"]
        for ts in product.split("_")[1:3]:
            d, t = ts.split("T")
            out[stack][d] = f"{t[0:2]}:{t[2:4]}:{t[4:6]}"
    return out


def already_ingested_dates() -> set[str]:
    """Dates that already have an ingested ztd GeoTIFF anywhere under data/hazard*/."""
    return {p.name.split(".")[0]
            for p in PROJECT_ROOT.glob("data/hazard*/gacos*/*.ztd.tif")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stacks", default="",
                    help="Comma-separated stack labels to include (default: every "
                         "stack in the manifest).")
    ap.add_argument("--buffer-km", type=float, default=10.0,
                    help="Padding added around the AOI bbox for the form (km, default 10).")
    args = ap.parse_args()

    cfg = load_config()
    min_lon, min_lat, max_lon, max_lat = aoi_bounds_4326(PROJECT_ROOT / cfg.aoi_path)
    dlat = args.buffer_km / 111.32
    dlon = args.buffer_km / (111.32 * math.cos(math.radians((min_lat + max_lat) / 2)))
    n, s = max_lat + dlat, min_lat - dlat
    w, e = min_lon - dlon, max_lon + dlon

    wanted = {x.strip() for x in args.stacks.split(",") if x.strip()}
    stacks = epochs_by_stack()
    unknown = wanted - set(stacks)
    if unknown:
        raise SystemExit(f"Unknown stack(s) {sorted(unknown)}; manifest has {sorted(stacks)}")
    done = already_ingested_dates()

    print(f"GACOS request helper — site: {cfg.site_name}")
    print(f"Form: http://www.gacos.net  (results arrive by EMAIL as a tarball;")
    print(f"       feed that tarball to workflows/gacos_ingest.py)")
    print()
    print(f"Area of interest (AOI bbox + {args.buffer_km:g} km, EPSG:4326 degrees):")
    print(f"  North: {n:.4f}    South: {s:.4f}")
    print(f"  West:  {w:.4f}    East:  {e:.4f}")
    print()
    print("One request per stack (each track has its own time of day):")

    for stack in sorted(stacks):
        if wanted and stack not in wanted:
            continue
        epochs = stacks[stack]
        time_of_day = Counter(epochs.values()).most_common(1)[0][0]
        dates = sorted(epochs)
        new = [d for d in dates if d not in done]
        print()
        print(f"### {stack}  ({len(dates)} epochs; {len(dates) - len(new)} already ingested)")
        print(f"    Time of interest (UTC): {time_of_day[:5]}   (acquisitions at {time_of_day})")
        if new:
            print(f"    Dates to request ({len(new)}):")
            print("      " + "\n      ".join(", ".join(new[i:i + 6])
                                             for i in range(0, len(new), 6)))
        else:
            print("    Nothing to request — every epoch already has an ingested ztd.tif.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

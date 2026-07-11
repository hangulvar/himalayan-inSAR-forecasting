#!/usr/bin/env python
"""Ad-hoc: enumerate unique Sentinel-1 acquisition epochs (date + UTC time) over the
VD AOI, grouped by track, for a GACOS tropospheric-correction request. Throwaway helper
(not part of the pipeline) — reads the AOI + window from config.yaml."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime

import geopandas as gpd
import asf_search as asf
from shapely.geometry import mapping  # noqa
from config import load_config

cfg = load_config()
gdf = gpd.read_file(cfg.aoi_path).to_crs(4326)
wkt = gdf.union_all().wkt if hasattr(gdf, "union_all") else gdf.unary_union.wkt

res = asf.geo_search(
    intersectsWith=wkt, platform=[asf.PLATFORM.SENTINEL1A, asf.PLATFORM.SENTINEL1B],
    processingLevel=[asf.PRODUCT_TYPE.SLC], beamMode=[asf.BEAMMODE.IW],
    start=cfg.search_start, end=cfg.search_end,
)
print(f"AOI bounds (lon/lat): {gdf.total_bounds.tolist()}")
print(f"window: {cfg.search_start.date()} -> {cfg.search_end.date()}  |  {len(res)} scenes\n")

# group by (direction, path, frame); collect (date, HH:MM:SS UTC)
tracks = defaultdict(dict)   # key -> {date: time}
for s in res:
    p = s.properties
    st = datetime.fromisoformat(p["startTime"].replace("Z", "+00:00"))
    key = f"{p['flightDirection'][:3]} path{p['pathNumber']:>3} frame{p['frameNumber']}"
    tracks[key][st.strftime("%Y-%m-%d")] = st.strftime("%H:%M:%S")

for key in sorted(tracks):
    epochs = sorted(tracks[key].items())
    times = sorted({t for _, t in epochs})
    print(f"### {key}  ({len(epochs)} epochs; acq time UTC ~{times[0]}"
          + (f"..{times[-1]}" if len(times) > 1 else "") + ")")
    print("    dates: " + ", ".join(d for d, _ in epochs))
    print()

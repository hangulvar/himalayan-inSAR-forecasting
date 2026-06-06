#!/usr/bin/env python
"""ingest_gsi_inventory.py — extract the GSI field-validated landslide inventory PDF
(`Research/LandslideInventory/landslide_report.pdf`) into a readable CSV + a GeoJSON,
filtered to the AOI, for a SCORED spatial back-test (replaces the ~11 approximate
news-derived points; see RESULTS_AND_KPIS.md §12g).

The PDF is the all-India "LANDSLIDE INVENTORY (Field Validated)" table (582 pp, sorted
by latitude) with columns:
  S.No | Latitude | Longitude | Slide_Name | State | District | Subdivision Or Taluk |
  Material Involved | Movement Type | Initiation_Year | History_date
pdfplumber.extract_tables() parses these cleanly. We keep rows whose lat/lon fall in
the AOI bounding box (config.yaml) + a buffer, dedupe, and write:
  * data/inventory/gsi_inventory_aoi.csv      (all columns, human-readable)
  * data/inventory/gsi_inventory_aoi.geojson  (Point features -> backtest_inventory.py)
  * data/inventory/gsi_inventory_aoi.md        (count + breakdown summary)

Runs NATIVELY (insar_qa_env): needs only `pdfplumber` (`pip install pdfplumber`) + stdlib
— no numpy/GDAL, so the Windows BLAS/gRPC native-crash class does not apply. The PDF is a
static input, so this ingest is one-off + idempotent (re-running overwrites identically).

  python workflows/ingest_gsi_inventory.py            # AOI from config + 0.05 deg buffer
  python workflows/ingest_gsi_inventory.py --page-start 495 --page-end 582   # faster (J&K tail)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

PDF = PROJECT_ROOT / "Research" / "LandslideInventory" / "landslide_report.pdf"
OUT_DIR = PROJECT_ROOT / "data" / "inventory"
HEADER = ["S.No", "Latitude", "Longitude", "Slide_Name", "State", "District",
          "Subdivision Or Taluk", "Material Involved", "Movement Type",
          "Initiation_Year", "History_date"]


def aoi_bbox():
    """(w, s, e, n) lon/lat bounding box of the config AOI."""
    from config import load_config
    gj = json.loads(Path(load_config().aoi_path).read_text(encoding="utf-8"))
    xs, ys = [], []

    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for x in c:
                walk(x)
    for feat in gj.get("features", [gj]):
        walk(feat["geometry"]["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


def num(x):
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", default=str(PDF))
    ap.add_argument("--buffer-deg", type=float, default=0.05, help="bbox buffer (~5.5 km/0.05 deg).")
    ap.add_argument("--page-start", type=int, default=1, help="1-indexed first page to scan.")
    ap.add_argument("--page-end", type=int, default=0, help="1-indexed last page (0 = last).")
    ap.add_argument("--out-prefix", default="gsi_inventory_aoi")
    args = ap.parse_args()

    import pdfplumber
    w, s, e, n = aoi_bbox()
    b = args.buffer_deg
    latlim = (s - b, n + b)
    lonlim = (w - b, e + b)
    print(f"AOI bbox lon {w:.3f}..{e:.3f}  lat {s:.3f}..{n:.3f}  (+/-{b} deg buffer)")

    recs, seen = [], set()
    with pdfplumber.open(args.pdf) as pdf:
        last = args.page_end or len(pdf.pages)
        for pi in range(args.page_start - 1, last):
            for tbl in pdf.pages[pi].extract_tables() or []:
                for r in tbl:
                    if not r or str(r[0]).strip() in ("S.No", "", "None"):
                        continue
                    lat, lon = num(r[1]), num(r[2]) if len(r) > 2 else None
                    if lat is None or lon is None:
                        continue
                    if not (latlim[0] <= lat <= latlim[1] and lonlim[0] <= lon <= lonlim[1]):
                        continue
                    row = {HEADER[i]: (str(r[i]).strip() if i < len(r) and r[i] else "")
                           for i in range(len(HEADER))}
                    key = (round(lat, 5), round(lon, 5), row["Slide_Name"], row["District"])
                    if key in seen:
                        continue
                    seen.add(key)
                    row["Latitude"], row["Longitude"] = lat, lon
                    recs.append(row)

    if not recs:
        raise SystemExit("No inventory rows in the AOI bbox — widen --buffer-deg or the page range.")
    recs.sort(key=lambda x: (x["District"], x["Latitude"]))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / f"{args.out_prefix}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=HEADER)
        wtr.writeheader()
        wtr.writerows(recs)

    feats = []
    for r in recs:
        name = r["Slide_Name"] or f"{r['Subdivision Or Taluk'] or r['District']} slide {r['S.No']}"
        props = {"name": name, "type": "gsi_field_validated",
                 "district": r["District"], "subdivision": r["Subdivision Or Taluk"],
                 "material": r["Material Involved"], "movement_type": r["Movement Type"],
                 "year": r["Initiation_Year"], "history_date": r["History_date"],
                 "source": "GSI field-validated landslide inventory (landslide_report.pdf)"}
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [r["Longitude"], r["Latitude"]]},
                      "properties": props})
    gj = {"type": "FeatureCollection",
          "note": ("GSI field-validated landslide inventory clipped to the AOI bbox + "
                   f"{b} deg, from Research/LandslideInventory/landslide_report.pdf. "
                   "Authoritative georeferenced ground truth for backtest_inventory.py "
                   "(supersedes the news-derived approximate points)."),
          "features": feats}
    geojson_path = OUT_DIR / f"{args.out_prefix}.geojson"
    geojson_path.write_text(json.dumps(gj, indent=1), encoding="utf-8")

    # readable summary
    import collections
    byd = collections.Counter(r["District"] for r in recs)
    bym = collections.Counter(r["Movement Type"] for r in recs)
    lines = [f"# GSI field-validated landslide inventory — AOI subset", "",
             f"Extracted from `landslide_report.pdf` (GSI all-India field-validated inventory), "
             f"clipped to the AOI bbox (lon {w:.3f}..{e:.3f}, lat {s:.3f}..{n:.3f}) + {b} deg buffer.", "",
             f"- **{len(recs)} landslide records** in the AOI window.",
             "- By district: " + ", ".join(f"{k}={v}" for k, v in byd.most_common()),
             "- By movement type: " + ", ".join(f"{k or '(blank)'}={v}" for k, v in bym.most_common()), "",
             "| lat | lon | name | district | movement | year |", "|---|---|---|---|---|---|"]
    for r in recs[:40]:
        nm = (r["Slide_Name"] or "(unnamed)")[:34]
        lines.append(f"| {r['Latitude']:.4f} | {r['Longitude']:.4f} | {nm} | {r['District']} | "
                     f"{r['Movement Type']} | {r['Initiation_Year']} |")
    if len(recs) > 40:
        lines.append(f"| … | | _+{len(recs) - 40} more (see CSV)_ | | | |")
    (OUT_DIR / f"{args.out_prefix}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"wrote {len(recs)} AOI records ->")
    print(f"  {csv_path}")
    print(f"  {geojson_path}")
    print(f"  {OUT_DIR / f'{args.out_prefix}.md'}")
    print("by district:", dict(byd.most_common()))
    print("by movement:", dict(bym.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""backtest_inventory.py — validate the model's flagged alert zones (and the rainfall
trigger date) against a landslide INVENTORY. Turns a "rough hazard map" toward a
"validated forecast" by asking two questions:

  SPATIAL:  do documented landslide locations fall near a model-flagged alert zone?
  TEMPORAL: does the model's rainfall ID-threshold trigger date coincide with the
            dates of documented landslide events?

Inputs:
  --inventory  GeoJSON FeatureCollection of POINT features with properties
               {name, date (YYYY-MM-DD, optional), type, source}.
  --alerts     a model alerts JSON — either a per-stack `alerts_*.json` (key "alerts")
               or the union `mosaic_asc/alerts_*.json` (key "zones"); each item has
               "centroid_lonlat".
  --trigger-report  data/rainfall/id_threshold_report.json (for the trigger dates).

HONEST SCOPE: this computes a DETECTION/COINCIDENCE rate, not precision/recall — that
needs a COMPLETE inventory (e.g. GSI Bhukosh's 302 Ramban landslides) plus a specificity
test against where we did NOT flag. Treat the spatial number as indicative until the
authoritative inventory is ingested (this tool is built to ingest it unchanged).

  docker compose run --rm insar python workflows/backtest_inventory.py \
      --alerts data/alerts/mosaic_asc/alerts_monsoon.json
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INV_DIR = PROJECT_ROOT / "data" / "inventory"


def haversine_km(lon1, lat1, lon2, lat2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_inventory(path: Path):
    gj = json.loads(path.read_text(encoding="utf-8"))
    pts = []
    for f in gj["features"]:
        lon, lat = f["geometry"]["coordinates"][:2]
        p = dict(f.get("properties", {}))
        p["lon"], p["lat"] = float(lon), float(lat)
        pts.append(p)
    return pts


def load_zone_centroids(path: Path):
    d = json.loads(path.read_text(encoding="utf-8"))
    items = d.get("alerts") or d.get("zones") or []
    return [tuple(z["centroid_lonlat"]) for z in items if z.get("centroid_lonlat")]


def trigger_dates(path: Path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("trigger_days", [])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory", default=str(INV_DIR / "ramban_documented_landslides.geojson"))
    ap.add_argument("--alerts", default=str(PROJECT_ROOT / "data" / "alerts" / "mosaic_asc" / "alerts_monsoon.json"))
    ap.add_argument("--trigger-report", default=str(PROJECT_ROOT / "data" / "rainfall" / "id_threshold_report.json"))
    ap.add_argument("--buffer-km", type=float, default=2.0,
                    help="A documented location counts as 'detected' if a flagged zone is "
                         "within this distance (generous, to absorb approximate coords).")
    ap.add_argument("--temporal-window-days", type=int, default=10)
    args = ap.parse_args()

    inv = load_inventory(Path(args.inventory))
    zones = load_zone_centroids(Path(args.alerts))
    trig = trigger_dates(Path(args.trigger_report))
    if not zones:
        raise SystemExit(f"No zone centroids in {args.alerts}")

    # SPATIAL: nearest flagged zone to each documented location.
    spatial = []
    for p in inv:
        dmin = min(haversine_km(p["lon"], p["lat"], zlon, zlat) for zlon, zlat in zones)
        spatial.append({"name": p.get("name", "?"), "type": p.get("type"),
                        "date": p.get("date"), "source": p.get("source"),
                        "nearest_zone_km": round(dmin, 2),
                        "detected": bool(dmin <= args.buffer_km)})
    n_det = sum(s["detected"] for s in spatial)

    # TEMPORAL: documented EVENTS (those with a date) vs the trigger date(s).
    trig_d = [date.fromisoformat(t) for t in trig]
    temporal = []
    for s, p in zip(spatial, inv):
        if not p.get("date"):
            continue
        ev = date.fromisoformat(p["date"])
        if trig_d:
            ddays = min((abs((ev - td).days), td) for td in trig_d)[0]
            near = ddays <= args.temporal_window_days
        else:
            ddays, near = None, False
        temporal.append({"name": p.get("name"), "event_date": p["date"],
                         "nearest_trigger_delta_days": ddays,
                         "coincides": bool(near)})
    n_evt = len(temporal)
    n_evt_hit = sum(t["coincides"] for t in temporal)

    report = {
        "alerts_source": args.alerts, "n_flagged_zones": len(zones),
        "inventory_source": args.inventory, "n_documented": len(inv),
        "buffer_km": args.buffer_km, "trigger_days": trig,
        "spatial": {"n_detected": n_det, "n_total": len(inv),
                    "detection_rate": round(n_det / len(inv), 3) if inv else None,
                    "nearest_km_median": round(float(np.median([s["nearest_zone_km"] for s in spatial])), 2)},
        "temporal": {"n_events": n_evt, "n_coinciding": n_evt_hit,
                     "window_days": args.temporal_window_days},
        "per_location": spatial, "per_event": temporal,
    }
    INV_DIR.mkdir(parents=True, exist_ok=True)
    (INV_DIR / "backtest_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_md(INV_DIR / "backtest_report.md", report)
    make_map(INV_DIR / "backtest_map.png", inv, zones, spatial, args.buffer_km)

    print(f"flagged zones: {len(zones)}  |  documented locations: {len(inv)}")
    print(f"SPATIAL: {n_det}/{len(inv)} documented locations within {args.buffer_km} km of a "
          f"flagged zone (median nearest {report['spatial']['nearest_km_median']} km)")
    print(f"TEMPORAL: model trigger day(s) {trig or 'none'}; "
          f"{n_evt_hit}/{n_evt} dated events within ±{args.temporal_window_days} d of a trigger")
    for t in temporal:
        print(f"   {t['event_date']}  {t['name']}: nearest trigger Δ={t['nearest_trigger_delta_days']} d "
              f"-> {'COINCIDES' if t['coincides'] else 'MISS'}")
    print(f"  -> {INV_DIR/'backtest_report.json'} , .md , backtest_map.png")
    return 0


def write_md(path: Path, r: dict) -> None:
    s, t = r["spatial"], r["temporal"]
    lines = [
        "# Back-test against a landslide inventory", "",
        f"Model flagged zones: **{r['n_flagged_zones']}** (`{Path(r['alerts_source']).name}`). "
        f"Documented locations: **{r['n_documented']}** (`{Path(r['inventory_source']).name}`).",
        "", "## Spatial coincidence",
        f"- **{s['n_detected']}/{s['n_total']}** documented locations lie within **{r['buffer_km']} km** "
        f"of a flagged zone (detection rate **{s['detection_rate']}**; median nearest **{s['nearest_km_median']} km**).",
        "", "| documented location | type | nearest flagged zone (km) | within buffer |",
        "|---|---|---|---|",
    ]
    for p in r["per_location"]:
        lines.append(f"| {p['name']} | {p['type']} | {p['nearest_zone_km']} | "
                     f"{'✅' if p['detected'] else '—'} |")
    lines += ["", "## Temporal coincidence (rainfall trigger vs documented events)",
              f"- Model ID-threshold trigger day(s): **{', '.join(r['trigger_days']) or 'none'}**.",
              f"- **{t['n_coinciding']}/{t['n_events']}** dated events fall within ±{t['window_days']} days "
              f"of a trigger.", "",
              "| documented event | date | nearest trigger Δ (days) | coincides |",
              "|---|---|---|---|"]
    for e in r["per_event"]:
        lines.append(f"| {e['name']} | {e['event_date']} | {e['nearest_trigger_delta_days']} | "
                     f"{'✅' if e['coincides'] else '—'} |")
    lines += ["",
              "## Honest scope",
              "- This is a **coincidence/detection** check, not precision–recall: that needs a "
              "**complete** field inventory (GSI Bhukosh records ~302 landslides in the Ramban "
              "sub-basin) plus a specificity test where we did NOT flag.",
              "- Inventory coordinates here are **approximate place-centroids from public reporting**, "
              "not field-mapped scarps — replace with the GSI Bhukosh georeferenced inventory for a "
              "rigorous spatial back-test (this tool ingests it unchanged).",
              "- The analysis window now starts 2025-04-01 (extended from 2025-05-01 to cover the "
              "documented 27 Apr event), and the trigger runs on WATER = rain + snowmelt (ERA5-Land), "
              "which still under-counts orographic bursts — a gauge product (CHIRPS/GPM) is the cross-check."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_map(path: Path, inv, zones, spatial, buffer_km) -> None:
    zl = np.array(zones)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(zl[:, 0], zl[:, 1], s=8, c="#9ecae1", label="model flagged zones", alpha=0.6)
    for p, s in zip(inv, spatial):
        c = "#2ca02c" if s["detected"] else "#d62728"
        ax.scatter(p["lon"], p["lat"], s=70, marker="^", c=c, edgecolors="k", zorder=5)
        ax.annotate(p.get("name", ""), (p["lon"], p["lat"]), fontsize=7,
                    xytext=(4, 4), textcoords="offset points")
    ax.scatter([], [], marker="^", c="#2ca02c", edgecolors="k", label=f"documented (≤{buffer_km} km)")
    ax.scatter([], [], marker="^", c="#d62728", edgecolors="k", label=f"documented (>{buffer_km} km)")
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    ax.set_title("Back-test: documented landslides (▲) vs model flagged zones (·)")
    ax.legend(fontsize=8, loc="best"); ax.grid(alpha=0.3); ax.set_aspect("equal", "box")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

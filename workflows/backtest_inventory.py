#!/usr/bin/env python
"""backtest_inventory.py — validate the model's flagged alert zones (and the rainfall
trigger date) against a landslide INVENTORY. Turns a "rough hazard map" toward a
"validated forecast" by asking two questions:

  SPATIAL:  do documented landslide locations fall near a model-flagged alert zone?
  TEMPORAL: does the model's rainfall ID-threshold trigger date coincide with the
            dates of documented landslide events?
  SCORED:   precision/specificity vs a NULL-POINT control (random AOI locations) +
            distance-ROC (TPR vs FPR as buffer_km sweeps) -> AUC.

Inputs:
  --inventory  GeoJSON FeatureCollection of POINT features with properties
               {name, date (YYYY-MM-DD, optional), type, source}.
  --alerts     a model alerts JSON — either a per-stack `alerts_*.json` (key "alerts")
               or the union `mosaic_asc/alerts_*.json` (key "zones"); each item has
               "centroid_lonlat".
  --trigger-report  data/rainfall/id_threshold_report.json (for the trigger dates).
  --aoi-path   AOI GeoJSON polygon for the null-point sampling (default: config.aoi_path).

The scored arm treats GSI inventory points as the POSITIVE class and uniformly-drawn
random points inside the AOI as a NEGATIVE/NULL class. At a given buffer_km a point is
"detected" if any flagged-zone centroid is within buffer_km. We then report:
  TPR (= detection rate on real inventory)
  FPR (= detection rate on null points -- the chance level set by how much area we flag)
  specificity = 1 - FPR; precision = TPR / (TPR + FPR) at the default class-balanced prior;
  lift = TPR / FPR (how much better than chance)
  AUC of TPR(FPR) as buffer_km sweeps from small to large.

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

DEFAULT_ROC_BUFFERS_KM = [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]


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


def aoi_polygon_lonlat(path: Path):
    """Return the AOI as a list of (lon, lat) tuples and its bbox. Multi-ring
    polygons are unioned by bbox + a point-in-any-ring test."""
    gj = json.loads(path.read_text(encoding="utf-8"))
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    rings = []
    for f in feats:
        g = f["geometry"]
        if g["type"] == "Polygon":
            rings.append(g["coordinates"][0])
        elif g["type"] == "MultiPolygon":
            for poly in g["coordinates"]:
                rings.append(poly[0])
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return rings, (min(xs), min(ys), max(xs), max(ys))


def point_in_rings(lon, lat, rings):
    """True if (lon, lat) is inside ANY of the polygon outer rings (ray cast)."""
    for ring in rings:
        inside = False
        n = len(ring)
        for i in range(n):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % n]
            if (y1 > lat) != (y2 > lat):
                x_int = (x2 - x1) * (lat - y1) / (y2 - y1 + 1e-30) + x1
                if lon < x_int:
                    inside = not inside
        if inside:
            return True
    return False


def sample_null_points(rings, bbox, n: int, seed: int):
    """Uniform random points strictly inside the AOI polygon (rejection sampling
    against the polygon, not just its bbox)."""
    rng = np.random.default_rng(seed)
    w, s, e, n_ = bbox
    pts, attempts, cap = [], 0, n * 50
    while len(pts) < n and attempts < cap:
        lon = rng.uniform(w, e)
        lat = rng.uniform(s, n_)
        attempts += 1
        if point_in_rings(lon, lat, rings):
            pts.append((lon, lat))
    if len(pts) < n:
        raise SystemExit(f"Could not draw {n} null points in AOI after {cap} tries.")
    return pts


def nearest_zone_km(lon, lat, zones):
    return min(haversine_km(lon, lat, zlon, zlat) for zlon, zlat in zones)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory", default=str(INV_DIR / "ramban_documented_landslides.geojson"))
    ap.add_argument("--alerts", default=str(PROJECT_ROOT / "data" / "alerts" / "mosaic_asc" / "alerts_monsoon.json"))
    ap.add_argument("--trigger-report", default=str(PROJECT_ROOT / "data" / "rainfall" / "id_threshold_report.json"))
    ap.add_argument("--buffer-km", type=float, default=2.0,
                    help="A documented location counts as 'detected' if a flagged zone is "
                         "within this distance (generous, to absorb approximate coords).")
    ap.add_argument("--temporal-window-days", type=int, default=10)
    ap.add_argument("--aoi-path", default=None,
                    help="AOI polygon for null-point sampling (default: config.aoi_path).")
    ap.add_argument("--n-null", type=int, default=5000,
                    help="Number of null/random points inside the AOI for the specificity arm.")
    ap.add_argument("--null-seed", type=int, default=20260606,
                    help="RNG seed for reproducible null sampling.")
    ap.add_argument("--roc-buffers-km", type=str, default=None,
                    help=f"Comma-separated buffer-km list for the distance-ROC sweep "
                         f"(default: {','.join(str(x) for x in DEFAULT_ROC_BUFFERS_KM)}).")
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

    # SCORED ARM: null-point control + distance-ROC -----------------------------
    # AOI for null sampling: default to the one in config.yaml.
    aoi_path = Path(args.aoi_path) if args.aoi_path else None
    if aoi_path is None:
        import sys as _sys
        _sys.path.insert(0, str(PROJECT_ROOT / "workflows"))
        from config import load_config  # noqa: E402
        aoi_path = Path(load_config().aoi_path)
    rings, bbox = aoi_polygon_lonlat(aoi_path)
    null_pts = sample_null_points(rings, bbox, args.n_null, args.null_seed)
    null_dists = np.array([nearest_zone_km(lon, lat, zones) for lon, lat in null_pts])
    real_dists = np.array([s["nearest_zone_km"] for s in spatial])

    roc_buffers = (sorted(float(x) for x in args.roc_buffers_km.split(","))
                   if args.roc_buffers_km else DEFAULT_ROC_BUFFERS_KM)
    roc_rows = []
    for bkm in roc_buffers:
        tpr = float(np.mean(real_dists <= bkm))         # detection rate on real points
        fpr = float(np.mean(null_dists <= bkm))         # detection rate on null points
        # precision under the assumption of equal class priors (one real per null point):
        # TP/(TP+FP) = TPR / (TPR + FPR). Falls back to None when neither fires.
        prec = round(tpr / (tpr + fpr), 3) if (tpr + fpr) > 0 else None
        lift = round(tpr / fpr, 2) if fpr > 0 else None
        f1 = round(2 * prec * tpr / (prec + tpr), 3) if (prec and (prec + tpr) > 0) else None
        roc_rows.append({"buffer_km": bkm, "tpr": round(tpr, 3), "fpr": round(fpr, 3),
                         "specificity": round(1.0 - fpr, 3), "precision": prec,
                         "lift": lift, "f1": f1})

    # AUC via trapezoidal integration over (FPR, TPR), anchored at (0,0) and (1,1).
    fprs = np.array([0.0] + [r["fpr"] for r in roc_rows] + [1.0])
    tprs = np.array([0.0] + [r["tpr"] for r in roc_rows] + [1.0])
    order = np.argsort(fprs)
    auc = float(np.trapz(tprs[order], fprs[order]))

    # Headline metrics at the user-chosen --buffer-km (the same row as the spatial arm).
    at_buf = next((r for r in roc_rows if abs(r["buffer_km"] - args.buffer_km) < 1e-9), None)
    if at_buf is None:
        tpr_b = float(np.mean(real_dists <= args.buffer_km))
        fpr_b = float(np.mean(null_dists <= args.buffer_km))
        at_buf = {"buffer_km": args.buffer_km, "tpr": round(tpr_b, 3),
                  "fpr": round(fpr_b, 3), "specificity": round(1 - fpr_b, 3),
                  "precision": round(tpr_b / (tpr_b + fpr_b), 3) if (tpr_b + fpr_b) > 0 else None,
                  "lift": round(tpr_b / fpr_b, 2) if fpr_b > 0 else None,
                  "f1": None}

    scored = {
        "n_null_points": len(null_pts), "null_seed": args.null_seed,
        "aoi_path": str(aoi_path), "auc": round(auc, 3),
        "at_buffer_km": at_buf, "roc": roc_rows,
        "null_nearest_km_median": round(float(np.median(null_dists)), 2),
    }

    report = {
        "alerts_source": args.alerts, "n_flagged_zones": len(zones),
        "inventory_source": args.inventory, "n_documented": len(inv),
        "buffer_km": args.buffer_km, "trigger_days": trig,
        "spatial": {"n_detected": n_det, "n_total": len(inv),
                    "detection_rate": round(n_det / len(inv), 3) if inv else None,
                    "nearest_km_median": round(float(np.median([s["nearest_zone_km"] for s in spatial])), 2)},
        "temporal": {"n_events": n_evt, "n_coinciding": n_evt_hit,
                     "window_days": args.temporal_window_days},
        "scored": scored,
        "per_location": spatial, "per_event": temporal,
    }
    INV_DIR.mkdir(parents=True, exist_ok=True)
    (INV_DIR / "backtest_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_md(INV_DIR / "backtest_report.md", report)
    make_map(INV_DIR / "backtest_map.png", inv, zones, spatial, args.buffer_km, null_pts, null_dists)
    make_roc_plot(INV_DIR / "backtest_roc.png", roc_rows, auc)

    print(f"flagged zones: {len(zones)}  |  documented locations: {len(inv)}")
    print(f"SPATIAL: {n_det}/{len(inv)} documented locations within {args.buffer_km} km of a "
          f"flagged zone (median nearest {report['spatial']['nearest_km_median']} km)")
    print(f"TEMPORAL: model trigger day(s) {trig or 'none'}; "
          f"{n_evt_hit}/{n_evt} dated events within ±{args.temporal_window_days} d of a trigger")
    for t in temporal:
        print(f"   {t['event_date']}  {t['name']}: nearest trigger Δ={t['nearest_trigger_delta_days']} d "
              f"-> {'COINCIDES' if t['coincides'] else 'MISS'}")
    print(f"SCORED  (null n={len(null_pts)}, seed={args.null_seed}, AUC={auc:.3f}):")
    print(f"   at buffer {at_buf['buffer_km']} km: TPR={at_buf['tpr']}  FPR={at_buf['fpr']}  "
          f"specificity={at_buf['specificity']}  precision={at_buf['precision']}  "
          f"lift={at_buf['lift']}x  F1={at_buf['f1']}")
    print(f"   null-point median nearest-zone: {scored['null_nearest_km_median']} km "
          f"(vs real {report['spatial']['nearest_km_median']} km)")
    print(f"  -> {INV_DIR/'backtest_report.json'} , .md , backtest_map.png , backtest_roc.png")
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
    sc = r.get("scored")
    if sc:
        lines += ["",
                  f"## Scored arm — precision/specificity vs a null-point control "
                  f"(n={sc['n_null_points']}, seed={sc['null_seed']})",
                  f"- **AUC = {sc['auc']}** (TPR vs FPR across the buffer-km sweep).",
                  f"- At buffer **{sc['at_buffer_km']['buffer_km']} km**: "
                  f"TPR (recall) **{sc['at_buffer_km']['tpr']}**, FPR "
                  f"**{sc['at_buffer_km']['fpr']}**, specificity "
                  f"**{sc['at_buffer_km']['specificity']}**, precision "
                  f"**{sc['at_buffer_km']['precision']}**, lift "
                  f"**{sc['at_buffer_km']['lift']}x**, F1 **{sc['at_buffer_km']['f1']}**.",
                  f"- Null-point median nearest-zone distance: **{sc['null_nearest_km_median']} km** "
                  f"(real inventory: **{s['nearest_km_median']} km**) — closer = better than chance.",
                  "", "| buffer (km) | TPR (real) | FPR (null) | specificity | precision | lift | F1 |",
                  "|---|---|---|---|---|---|---|"]
        for row in sc["roc"]:
            lines.append(f"| {row['buffer_km']} | {row['tpr']} | {row['fpr']} | "
                         f"{row['specificity']} | {row['precision']} | {row['lift']} | {row['f1']} |")
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
              "- The SCORED arm draws random points uniformly inside the AOI polygon as a "
              "NEGATIVE class — TPR/FPR/AUC are computed as the buffer-km decision threshold "
              "sweeps. This converts the indicative 'coincidence rate' into a class-balanced "
              "score that calibrates against how much area we flag (a high TPR is only impressive "
              "if FPR stays low).",
              "- Window starts 2025-04-01; trigger runs on WATER = rain + snowmelt. KEY NOTE "
              "(RESULTS_AND_KPIS.md §12g): a DATE CORRECTION found the real major April event was the "
              "20 Apr 2025 Ramban cloudburst (3 deaths) — which WAS acute-rainfall-triggered and the model "
              "catches (regional curve Delta=0; IMERG E=2.25). An earlier 'rainfall ruled out' reading was a "
              "wrong-date artifact (news-derived 27 Apr). Caveat: daily AOI-mean products dilute the "
              "localized cloudburst cell, so sub-daily/point rain is what resolves it."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_map(path: Path, inv, zones, spatial, buffer_km, null_pts=None, null_dists=None) -> None:
    zl = np.array(zones)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(zl[:, 0], zl[:, 1], s=8, c="#9ecae1", label="model flagged zones", alpha=0.6)
    if null_pts is not None and null_dists is not None:
        nl = np.array(null_pts)
        hit = null_dists <= buffer_km
        ax.scatter(nl[hit, 0], nl[hit, 1], s=2, c="#bdbdbd", alpha=0.35,
                   label=f"null pts (FP, ≤{buffer_km} km)")
        ax.scatter(nl[~hit, 0], nl[~hit, 1], s=2, c="#f0f0f0", alpha=0.2,
                   label=f"null pts (TN, >{buffer_km} km)")
    for p, s in zip(inv, spatial):
        c = "#2ca02c" if s["detected"] else "#d62728"
        ax.scatter(p["lon"], p["lat"], s=70, marker="^", c=c, edgecolors="k", zorder=5)
    ax.scatter([], [], marker="^", c="#2ca02c", edgecolors="k", label=f"documented (≤{buffer_km} km)")
    ax.scatter([], [], marker="^", c="#d62728", edgecolors="k", label=f"documented (>{buffer_km} km)")
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    ax.set_title("Back-test: documented landslides (▲) vs model flagged zones (·) + null pts (.)")
    ax.legend(fontsize=8, loc="best"); ax.grid(alpha=0.3); ax.set_aspect("equal", "box")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def make_roc_plot(path: Path, roc_rows, auc: float) -> None:
    fprs = [0.0] + [r["fpr"] for r in roc_rows] + [1.0]
    tprs = [0.0] + [r["tpr"] for r in roc_rows] + [1.0]
    order = np.argsort(fprs)
    fprs = np.array(fprs)[order]
    tprs = np.array(tprs)[order]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot(fprs, tprs, "-o", color="#1f77b4", lw=2, ms=4, label=f"model (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], "--", color="#7f7f7f", lw=1, label="chance (AUC=0.5)")
    for r in roc_rows:
        ax.annotate(f"{r['buffer_km']} km", (r["fpr"], r["tpr"]),
                    fontsize=7, xytext=(4, -3), textcoords="offset points")
    ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("FPR = null-point detection rate")
    ax.set_ylabel("TPR = real-inventory detection rate")
    ax.set_title("Distance-ROC: buffer-km sweep")
    ax.legend(loc="lower right"); ax.grid(alpha=0.3); ax.set_aspect("equal", "box")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
"""coherence_watch.py — per-polygon COHERENCE-DROP watch: the pipeline's first
FAST-FAILURE detector (Watchlist README idea #4; closes part of the CV3 gap).

SBAS velocity only sees slow creep. A rockfall/collapse instead *destroys* the
radar echo: the failed face suddenly DECORRELATES between two consecutive
12-day pairs. The `*_corr.tif` coherence rasters already hold that signal —
this script turns them into a per-polygon timeline and flags sudden drops.

Method (honest about confounders):
  * Only same-stack shortest-baseline pairs (<= --max-pair-days, default 13) —
    coherence decays with temporal baseline, so mixing 24/36-day rescue pairs
    would fake a drop.
  * The discriminator is the AOI-RELATIVE coherence: rain wetting / vegetation
    flush / snow drop coherence across the WHOLE scene; a failure drops only
    the polygon. An epoch is flagged when the polygon fell vs its own history
    (abs drop) AND fell relative to the AOI mean (localized drop), both by
    >= --min-drop.
  * Verdict from the LATEST epoch per stack: DROP-CONFIRMED (>=2 stacks),
    DROP-SINGLE-TRACK (1), OK, or DATA-GAP.

A flagged drop is a *tell*, not a confirmation — follow with a Sentinel-2
before/after look (fresh scars are bright at 10 m) and the field protocol.

  docker compose run --rm insar python workflows/coherence_watch.py \
      --polygons "Research/Vaishno_Devi_Watchlist/Vaishno_Devi_Bhavan_Overhang.kml"
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.features import geometry_mask  # noqa: E402
from pyproj import Transformer  # noqa: E402

from config import load_config  # noqa: E402
from polygon_stats import read_polygons  # noqa: E402
from stacks import load_manifest, product_stacks  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CFG = load_config()
TIFF_DIR = PROJECT_ROOT / "data" / "processed_tiffs"
ALERTS_DIR = PROJECT_ROOT / "data" / f"alerts{_CFG.data_suffix}" / "mosaic_asc"

_DATE_RE = re.compile(r"S1AA_(\d{8})T\d{6}_(\d{8})T\d{6}_")


def pair_dates(product: str) -> tuple[date, date] | None:
    m = _DATE_RE.match(product)
    if not m:
        return None
    return (datetime.strptime(m.group(1), "%Y%m%d").date(),
            datetime.strptime(m.group(2), "%Y%m%d").date())


def stack_products(max_pair_days: int) -> dict[str, list[dict]]:
    """{stack: [{product, date1, date2}] date-sorted} for the connected stacks,
    keeping only shortest-baseline pairs whose corr.tif exists on disk."""
    manifest = load_manifest()
    out: dict[str, list[dict]] = {s: [] for s in product_stacks()}
    for product, entry in manifest.items():
        stack = entry.get("stack")
        if stack not in out:
            continue
        dates = pair_dates(product)
        if not dates or (dates[1] - dates[0]).days > max_pair_days:
            continue
        corr = TIFF_DIR / product / f"{product}_corr.tif"
        if corr.exists():
            out[stack].append({"product": product, "date1": dates[0],
                               "date2": dates[1], "corr": corr})
    for s in out:
        out[s].sort(key=lambda p: p["date2"])
    return {s: ps for s, ps in out.items() if ps}


def aoi_ring() -> list[list[float]]:
    gj = json.loads(_CFG.aoi_path.read_text(encoding="utf-8"))
    geom = gj["features"][0]["geometry"] if "features" in gj else gj["geometry"]
    coords = geom["coordinates"]
    return coords[0][0] if geom["type"] == "MultiPolygon" else coords[0]


def masks_for_grid(src, rings_lonlat: list[list[list[float]]],
                   cache: dict) -> list[np.ndarray]:
    """Pixel masks for each lon/lat ring on this raster's grid (cached per grid,
    since all products of a stack share one). Falls back to the centroid pixel
    for polygons smaller than one pixel (same pattern as polygon_stats)."""
    key = (str(src.crs), src.transform, src.shape)
    if key in cache:
        return cache[key]
    to_grid = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
    out = []
    for ring in rings_lonlat:
        ring_xy = [to_grid.transform(lon, lat) for lon, lat in ring]
        geom = {"type": "Polygon", "coordinates": [ring_xy]}
        m = ~geometry_mask([geom], out_shape=src.shape,
                           transform=src.transform, invert=False)
        if not m.any():
            clon = float(np.mean([c[0] for c in ring]))
            clat = float(np.mean([c[1] for c in ring]))
            row, col = rasterio.transform.rowcol(
                src.transform, *to_grid.transform(clon, clat))
            if 0 <= row < src.shape[0] and 0 <= col < src.shape[1]:
                m = np.zeros(src.shape, bool)
                m[row, col] = True
        out.append(m)
    cache[key] = out
    return out


def flag_epochs(series: list[dict], min_drop: float) -> None:
    """Mark each valid epoch whose coherence fell >= min_drop below the
    leave-one-out median of the others, both absolutely and AOI-relative."""
    valid = [e for e in series if e["coh"] is not None]
    for e in series:
        e["flag"] = False
        if e["coh"] is None or len(valid) < 3:
            continue
        others = [o for o in valid if o is not e]
        abs_drop = float(np.median([o["coh"] for o in others])) - e["coh"]
        rel_drop = (float(np.median([o["rel"] for o in others])) - e["rel"])
        e["abs_drop"] = round(abs_drop, 3)
        e["local_drop"] = round(rel_drop, 3)
        e["flag"] = abs_drop >= min_drop and rel_drop >= min_drop


def plot_polygon(name: str, per_stack: dict[str, list[dict]], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, (stack, series) in enumerate(sorted(per_stack.items())):
        dates = [e["date2"] for e in series]
        coh = [e["coh"] if e["coh"] is not None else np.nan for e in series]
        aoi = [e["aoi_coh"] for e in series]
        c = f"C{i}"
        ax.plot(dates, coh, "-o", color=c, label=f"{stack} — polygon")
        ax.plot(dates, aoi, "--", color=c, alpha=0.5, label=f"{stack} — AOI mean")
        fl = [(e["date2"], e["coh"]) for e in series if e["flag"]]
        if fl:
            ax.scatter(*zip(*fl), s=140, facecolors="none", edgecolors="red",
                       linewidths=2, zorder=5, label=f"{stack} — DROP")
    ax.set_ylim(0, 1)
    ax.set_ylabel("mean coherence (12-day pairs)")
    ax.set_title(f"Coherence-drop watch — {name} ({_CFG.site_name})")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--polygons", required=True, help="KML or GeoJSON of polygons.")
    ap.add_argument("--out-name", default="coherence_watch")
    ap.add_argument("--min-drop", type=float, default=0.12,
                    help="Coherence drop (absolute AND AOI-relative) that flags "
                         "an epoch (default 0.12 — ~2x the quiet epoch-to-epoch "
                         "scatter; re-tune when the timeline is longer).")
    ap.add_argument("--max-pair-days", type=int, default=13,
                    help="Keep only pairs at the standard revisit (default 13).")
    ap.add_argument("--min-valid-frac", type=float, default=0.3,
                    help="Min fraction of finite polygon pixels for a usable epoch.")
    args = ap.parse_args()

    polys = read_polygons(Path(args.polygons))
    if not polys:
        raise SystemExit(f"No polygons found in {args.polygons}")
    by_stack = stack_products(args.max_pair_days)
    if not by_stack:
        raise SystemExit("No <=%d-day pairs with corr.tif found for the connected "
                         "stacks." % args.max_pair_days)

    rings = [p["ring"] for p in polys] + [aoi_ring()]   # AOI ref rides along
    grid_cache: dict = {}
    results = {p["name"]: {} for p in polys}
    for stack, products in by_stack.items():
        for prod in products:
            with rasterio.open(prod["corr"]) as src:
                coh = src.read(1)
                masks = masks_for_grid(src, rings, grid_cache)
            aoi_v = coh[masks[-1]]
            aoi_v = aoi_v[np.isfinite(aoi_v)]
            aoi_mean = float(aoi_v.mean()) if aoi_v.size else None
            for p, m in zip(polys, masks):
                v = coh[m]
                n_px = int(m.sum())
                v = v[np.isfinite(v)]
                ok = (aoi_mean is not None and n_px > 0
                      and v.size / max(n_px, 1) >= args.min_valid_frac)
                entry = {
                    "pair": f"{prod['date1']}→{prod['date2']}",
                    "date2": prod["date2"],
                    "coh": round(float(v.mean()), 3) if ok else None,
                    "aoi_coh": round(aoi_mean, 3) if aoi_mean is not None else None,
                    "valid_frac": round(v.size / max(n_px, 1), 2) if n_px else 0.0,
                }
                entry["rel"] = (entry["coh"] - entry["aoi_coh"]
                                if entry["coh"] is not None else None)
                results[p["name"]].setdefault(stack, []).append(entry)

    reports = []
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    for p in polys:
        per_stack = results[p["name"]]
        latest_flags = []
        for stack, series in per_stack.items():
            flag_epochs(series, args.min_drop)
            last = series[-1]
            latest_flags.append(bool(last["flag"]) if last["coh"] is not None
                                else None)
        n_drop = sum(1 for f in latest_flags if f)
        n_gap = sum(1 for f in latest_flags if f is None)
        if n_drop >= 2:
            verdict = ("DROP-CONFIRMED: latest 12-day pair decorrelated on >=2 "
                       "tracks beyond the AOI-wide change — fast-failure tell; "
                       "check Sentinel-2 + field")
        elif n_drop == 1:
            verdict = ("DROP-SINGLE-TRACK: latest pair decorrelated on one track "
                       "only — could be geometry/noise; watch next pair")
        elif n_gap == len(latest_flags):
            verdict = "DATA-GAP: no usable coherence over the polygon in the latest pairs"
        else:
            verdict = "OK: latest pairs within the polygon's normal coherence range"
        slug = re.sub(r"\W+", "_", p["name"].strip()).strip("_").lower()
        png = ALERTS_DIR / f"{args.out_name}_{slug}.png"
        plot_polygon(p["name"], per_stack, png)
        n_epochs = min(len(s) for s in per_stack.values()) if per_stack else 0
        reports.append({
            "name": p["name"], "verdict": verdict, "n_epochs_min": n_epochs,
            "timeline_png": png.name,
            "stacks": {s: [dict(e, date2=str(e["date2"])) for e in series]
                       for s, series in per_stack.items()},
        })
        print(f"[{p['name']}] {verdict}")

    out = {
        "generated": date.today().isoformat(), "aoi": _CFG.aoi_slug,
        "source": Path(args.polygons).name,
        "params": {"min_drop": args.min_drop, "max_pair_days": args.max_pair_days,
                   "min_valid_frac": args.min_valid_frac},
        "stacks": {s: len(ps) for s, ps in by_stack.items()},
        "polygons": reports,
        "caveats": "Detector of sudden decorrelation, not of creep; needs >=3 "
                   "usable epochs per stack before it can flag at all. Scene-wide "
                   "drops (rain wetting, vegetation flush, snow) are subtracted "
                   "via the AOI-mean reference but a storm exactly coincident "
                   "with a failure can still mask it; steep-face layover pixels "
                   "carry little signal either way. A flag is a prompt to look "
                   "(Sentinel-2, field), never a confirmed failure.",
    }
    jpath = ALERTS_DIR / f"{args.out_name}.json"
    jpath.write_text(json.dumps(out, indent=2), encoding="utf-8")

    lines = [f"# Coherence-drop watch — {_CFG.site_name} ({out['generated']})", "",
             f"Source polygons: `{out['source']}` | pairs per stack: "
             + ", ".join(f"{s}={n}" for s, n in out["stacks"].items()),
             "", f"Flag threshold: drop >= {args.min_drop} vs the polygon's own "
                 "history, absolute AND AOI-relative (localized).", ""]
    for r in reports:
        lines += [f"## {r['name']} — {r['verdict']}", "",
                  f"![timeline]({r['timeline_png']})", "",
                  "| stack | pair | polygon coh | AOI coh | valid | drop (abs/local) | flag |",
                  "|---|---|---|---|---|---|---|"]
        for s, series in r["stacks"].items():
            for e in series:
                drops = (f"{e.get('abs_drop', '')}/{e.get('local_drop', '')}"
                         if "abs_drop" in e else "")
                lines.append(
                    f"| {s} | {e['pair']} | {e['coh']} | {e['aoi_coh']} | "
                    f"{e['valid_frac']} | {drops} | {'DROP' if e['flag'] else ''} |")
        lines.append("")
    lines += ["---", f"_{out['caveats']}_", ""]
    (ALERTS_DIR / f"{args.out_name}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"-> {jpath} , .md , per-polygon .png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

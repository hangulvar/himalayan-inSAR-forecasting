#!/usr/bin/env python
"""
build_3d_dashboard.py — Phase 4 Part B: interactive 3-D hazard explorer.

Produces a SINGLE self-contained HTML file (Plotly.js via CDN) that renders, in
interactive 3-D:

  • the Ramban terrain as a draped elevation surface (orbit / zoom / pan),
  • the measured InSAR creep (observation layer),
  • the agentic alert zones per rainfall scenario (dry / monsoon / extreme),
    each a marker you can hover for its plain-English reasoning,
  • scenario toggle buttons so you can watch the cascade light up with rainfall.

WHY NOT Streamlit/Pydeck (the literal Phase-4B spec): a static Plotly HTML needs
ZERO new Python dependencies (we only emit HTML + embedded JSON), so it never
touches the carefully-stabilised `insar_qa_env`, opens in any browser offline-ish
(only the Plotly CDN script needs the network), and is verifiable as a file. It
delivers the same WebGL 3-D experience. A hosted Streamlit version can be layered
on later in a separate env if a deployed web app is wanted.

Inputs (from Phases 2-4A): the velocity grid (master grid), a product DEM
(reprojected onto it), the Phase-3 hazard_class, and the Phase-4A alert JSONs.

Usage:
    python workflows/build_3d_dashboard.py
    python workflows/build_3d_dashboard.py --stride 2 --z-exaggeration 0.55
"""

from __future__ import annotations

import os
import sys

# BLAS DLL bootstrap (see error_history_log.md 2026-05-29).
if sys.platform == "win32":
    _dll = [os.path.join(sys.prefix, "Library", "bin"),
            os.path.join(sys.prefix, "Library", "mingw-w64", "bin"),
            os.path.join(sys.prefix, "Scripts")]
    os.environ["PATH"] = os.pathsep.join([d for d in _dll if os.path.isdir(d)]
                                         + [os.environ.get("PATH", "")])

import argparse
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

from config import load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QA_DIR = PROJECT_ROOT / "data" / "qa_masks"
QUARANTINE_CSV = QA_DIR / "_quarantine_list.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed_tiffs"
_CFG = load_config()
_SFX = _CFG.data_suffix            # '' for ramban; '_<slug>' so AOIs coexist
SITE = _CFG.site_name              # human-readable label for dashboard titles
VEL_DIR = PROJECT_ROOT / "data" / f"velocity{_SFX}"
HAZ_DIR = PROJECT_ROOT / "data" / f"hazard{_SFX}"
ALERTS_DIR = PROJECT_ROOT / "data" / f"alerts{_SFX}"
LOG_DIR = PROJECT_ROOT / "logs"

# Footer wording follows the config-gated LLOF source (§60 4c).
LLOF_NOTE = ("LLOF heuristic" if _CFG.llof_routing == "twi"
             else "LLOF via real D8 routing")

SCENARIOS = ["dry", "monsoon", "extreme"]
VEL_CREEP_THR = -15.0

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout),
                              logging.FileHandler(LOG_DIR / "build_3d_dashboard.log", encoding="utf-8")])
logger = logging.getLogger("dashboard3d")


def find_dem(stack: str) -> Path:
    rows = list(csv.DictReader(QUARANTINE_CSV.open(encoding="utf-8")))
    keep = sorted(r["product"] for r in rows
                  if r["stack"] == stack and r["decision"] == "KEEP")
    return PROCESSED_DIR / keep[0] / f"{keep[0]}_dem.tif"


def reproject_dem(dem_path: Path, transform, crs, w, h) -> np.ndarray:
    dst = np.full((h, w), np.nan, dtype=np.float32)
    with rasterio.open(dem_path) as src:
        reproject(rasterio.band(src, 1), dst,
                  src_transform=src.transform, src_crs=src.crs,
                  dst_transform=transform, dst_crs=crs,
                  resampling=Resampling.bilinear,
                  src_nodata=src.nodata, dst_nodata=np.nan)
    dst[(dst < -100) | (dst > 9000)] = np.nan
    return dst


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stack", default="ASC_path27_frame106")
    ap.add_argument("--stride", type=int, default=2,
                    help="Downsample factor for the terrain surface (2 = every 2nd pixel).")
    ap.add_argument("--z-exaggeration", type=float, default=0.5,
                    help="Vertical relief in the 3-D box (Plotly z aspectratio).")
    args = ap.parse_args()
    stack = args.stack
    logger.info(f"Building 3-D dashboard for {stack}")

    # Master grid + layers
    with rasterio.open(VEL_DIR / f"{stack}_mean_velocity_los_highpass.tif") as s:
        velocity = s.read(1)
        transform, crs, w, h = s.transform, s.crs, s.width, s.height
    dem = reproject_dem(find_dem(stack), transform, crs, w, h)
    elev_fill = float(np.nanmean(dem))

    # --- Terrain surface (downsampled) ---
    st = args.stride
    zr = dem[::st, ::st]
    rows = list(range(0, h, st))
    cols = list(range(0, w, st))
    z_surface = np.where(np.isfinite(zr), zr, None).tolist()  # None -> hole in Plotly

    surface = {
        "type": "surface", "name": "Terrain",
        "x": cols, "y": rows, "z": z_surface,
        "colorscale": "Earth", "reversescale": True, "showscale": False,
        "opacity": 1.0, "hoverinfo": "skip",
        "lighting": {"ambient": 0.6, "diffuse": 0.8, "specular": 0.1},
        "contours": {"z": {"show": True, "usecolormap": True,
                            "highlightcolor": "#fff", "project": {"z": False}}},
    }

    # --- Creep overlay (measured, scenario-independent) ---
    creep_yx = np.argwhere(np.isfinite(velocity) & (velocity < VEL_CREEP_THR))
    # thin for rendering if very dense
    if len(creep_yx) > 4000:
        idx = np.linspace(0, len(creep_yx) - 1, 4000).astype(int)
        creep_yx = creep_yx[idx]
    cx = [int(c) for _, c in creep_yx]
    cy = [int(r) for r, _ in creep_yx]
    cz = [float(dem[r, c]) if np.isfinite(dem[r, c]) else elev_fill for r, c in creep_yx]
    cvel = [round(float(velocity[r, c]), 1) for r, c in creep_yx]
    creep = {
        "type": "scatter3d", "name": "Measured creep", "mode": "markers",
        "x": cx, "y": cy, "z": cz, "visible": "legendonly",
        "marker": {"size": 1.6, "color": cvel, "colorscale": "YlOrRd",
                   "reversescale": True, "opacity": 0.6,
                   "colorbar": {"title": "LOS vel<br>mm/yr", "x": 1.02, "len": 0.4}},
        "text": [f"creep {v} mm/yr" for v in cvel], "hoverinfo": "text",
    }

    # --- Alert markers per scenario ---
    alert_traces = []
    counts = {}
    for i, sc in enumerate(SCENARIOS):
        jpath = ALERTS_DIR / f"alerts_{sc}.json"
        if not jpath.exists():
            logger.warning(f"missing {jpath.name}; run agentic_orchestrator.py first")
            continue
        data = json.loads(jpath.read_text(encoding="utf-8"))
        ax, ay, az, sizes, colors, texts = [], [], [], [], [], []
        for a in data["alerts"]:
            r, c = a["pixel_rowcol"]
            z = float(dem[r, c]) if (0 <= r < h and 0 <= c < w and np.isfinite(dem[r, c])) else elev_fill
            ax.append(c); ay.append(r); az.append(z + 60)  # lift above surface
            sizes.append(4 + min(a["area_km2"] * 120, 14))
            colors.append("#8b0000" if a["severity"] == "CRITICAL" else "#ff3b30")
            lon, lat = a["centroid_lonlat"]
            dr = a["downstream_risk"]
            texts.append(
                f"<b>Alert {a['id']} · {a['severity']}</b><br>"
                f"{lat:.4f}°N, {lon:.4f}°E<br>"
                f"FS {a['mean_fs']:.2f} · vel {a['mean_velocity_mmyr']:.0f} mm/yr "
                f"(peak {a['max_velocity_mmyr']:.0f})<br>"
                f"slope {a['mean_slope_deg']:.0f}° · {a['area_km2']:.3f} km²<br>"
                f"{'⚠️ LLOF downstream risk<br>' if dr['llof_potential'] else ''}"
                f"<i>{a['trigger_reason']}</i>")
        counts[sc] = len(ax)
        alert_traces.append({
            "type": "scatter3d", "name": f"Alerts ({sc})", "mode": "markers",
            "x": ax, "y": ay, "z": az,
            "visible": True if sc == "monsoon" else False,
            "marker": {"size": sizes, "color": colors, "symbol": "diamond",
                       "line": {"width": 0.5, "color": "#fff"}, "opacity": 0.95},
            "text": texts, "hoverinfo": "text",
        })
    logger.info(f"Alert counts: {counts}")

    traces = [surface, creep] + alert_traces

    # Scenario toggle buttons: keep surface(0)+creep(1) state, switch alert traces.
    n_fixed = 2
    buttons = []
    for i, sc in enumerate(SCENARIOS):
        vis = [True, "legendonly"] + [(j == i) for j in range(len(alert_traces))]
        buttons.append({"label": f"{sc.capitalize()}  ({counts.get(sc,0)})",
                        "method": "restyle", "args": [{"visible": vis}]})

    layout = {
        "title": {"text": f"{SITE} — 3-D Hazard Explorer ({stack})", "x": 0.5},
        "scene": {
            "xaxis": {"title": "pixel (E→)", "showspikes": False},
            "yaxis": {"title": "pixel (N→)", "showspikes": False},
            "zaxis": {"title": "elevation (m)"},
            "aspectmode": "manual",
            "aspectratio": {"x": 1, "y": round(h / w, 2), "z": args.z_exaggeration},
            "camera": {"eye": {"x": 1.5, "y": -1.5, "z": 1.1}},
            "bgcolor": "#0d1b2a",
        },
        "paper_bgcolor": "#0d1b2a", "font": {"color": "#eaeaea"},
        "margin": {"l": 0, "r": 0, "t": 44, "b": 0},
        "legend": {"x": 0, "y": 0.95, "bgcolor": "rgba(13,27,42,.6)"},
        "updatemenus": [{
            "type": "buttons", "direction": "right", "showactive": True,
            "x": 0.5, "xanchor": "center", "y": 1.08, "active": 1,
            "bgcolor": "#1b3a5b", "font": {"color": "#fff"},
            "buttons": buttons,
        }],
    }

    config = {"responsive": True, "displaylogo": False}
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>{SITE} — 3-D Hazard Explorer</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
<style>
 html,body{{margin:0;height:100%;background:#0d1b2a;font-family:Segoe UI,Arial,sans-serif}}
 #plot{{width:100vw;height:100vh}}
 #info{{position:fixed;left:12px;bottom:12px;max-width:360px;background:rgba(13,27,42,.82);
   color:#dfe7ef;border:1px solid #2b4a6b;border-radius:8px;padding:10px 12px;font-size:12px;z-index:9}}
 #info b{{color:#fff}} #info .k{{color:#ffd27f}}
</style></head><body>
<div id="plot"></div>
<div id="info">
 <b>🏔️ {SITE} — 3-D Hazard Explorer</b><br>
 Drag to orbit · scroll to zoom · hover an <span class="k">alert diamond</span> for its reasoning.<br>
 Use the top buttons to switch rainfall scenario — watch alerts grow from
 <span class="k">dry</span> to <span class="k">monsoon</span>. Toggle
 “Measured creep” in the legend to show observed motion.<br>
 <span style="color:#9fb3c8">Pathfinder stack · generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.
 Coverage ~14% of AOI (unmeasured ≠ safe); soil params assumed; {LLOF_NOTE}.</span>
</div>
<script>
 var traces = {json.dumps(traces)};
 var layout = {json.dumps(layout)};
 Plotly.newPlot("plot", traces, layout, {json.dumps(config)});
</script>
</body></html>"""

    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    out = ALERTS_DIR / "dashboard_3d.html"
    out.write_text(html, encoding="utf-8")
    size_mb = out.stat().st_size / 1e6
    logger.info(f"Wrote {out} ({size_mb:.1f} MB). Open it in a browser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

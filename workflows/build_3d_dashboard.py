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
from pyproj import Transformer
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


# Ramban's pathfinder stack — the historical default this dashboard was built on. It is a
# RAMBAN stack, and until 2026-08-14 it was the hardcoded default for EVERY AOI, so rebuilding
# the 3-D view for Vaishno Devi died on a rasterio "No such file" for a raster that site has
# never had (and deliberately will not: VD's registry file records that frame106 has too few
# usable pixels over that AOI to solve). Kept only as a PREFERENCE, and only when this AOI's
# own product actually contains it.
HISTORICAL_DEFAULT_STACK = "ASC_path27_frame106"


def has_velocity(stack: str) -> bool:
    return (VEL_DIR / f"{stack}_mean_velocity_los_highpass.tif").exists()


def available_stacks() -> list[str]:
    """Stacks this AOI actually has a velocity grid for (what the dashboard can be built on)."""
    return sorted(p.name[: -len("_mean_velocity_los_highpass.tif")]
                  for p in VEL_DIR.glob("*_mean_velocity_los_highpass.tif"))


def resolve_stack(requested: str | None) -> str:
    """Which stack to render, derived from the ACTIVE AOI rather than hardcoded.

    Order: an explicit --stack (validated); else this site's own product stacks, preferring
    the historical pathfinder stack when the site's product contains it so Ramban's view is
    unchanged; else any stack with a velocity grid. Raises with the real options listed —
    never a raw rasterio traceback about a path the reader has to decode.
    """
    have = available_stacks()
    if requested:
        if has_velocity(requested):
            return requested
        raise SystemExit(
            f"{_CFG.site_name}: no velocity grid for stack '{requested}' in {VEL_DIR}.\n"
            + (f"  This AOI has: {', '.join(have)}" if have else
               "  This AOI has NO velocity grids at all — run run_multistack.py first "
               "(a site at playbook step 2 has nothing to render yet)."))
    try:
        from stacks import product_stacks
        product = [s for s in product_stacks() if has_velocity(s)]
    except Exception:  # noqa: BLE001 — no standing product yet is a legitimate state
        product = []
    if HISTORICAL_DEFAULT_STACK in product:
        return HISTORICAL_DEFAULT_STACK
    if product:
        return product[0]
    if have:
        logger.warning(f"no standing product stacks for {_CFG.aoi_slug}; falling back to "
                       f"{have[0]} (the first stack with a velocity grid)")
        return have[0]
    raise SystemExit(
        f"{_CFG.site_name}: no velocity grids in {VEL_DIR} — there is nothing to render in 3-D "
        f"yet.\n  Run the Phase 2-4 driver first:\n"
        f"    docker compose run --rm -e INSAR_CONFIG=config/{_CFG.aoi_slug}.yaml "
        f"insar python workflows/run_multistack.py")


def exposure_traces(stack: str, footprint: str, transform, crs, dem, h: int, w: int,
                    elev_fill: float) -> tuple[list[dict], dict | None]:
    """The affected-area layer (exposure_footprint.py), draped on this stack's terrain.

    Two extra traces: the OUTLINE of each hazard zone (the ground the alert actually covers,
    instead of a single dot) and the POTENTIAL DOWNSTREAM PATH below it. Both are read from
    exposure_<footprint>.geojson and filtered to THIS radar look, so a zone another look saw
    is never drawn on a grid it was not measured on.

    Returns ([], None) when the layer has not been generated — the dashboard is unchanged in
    that case, which is what keeps this addition optional.
    """
    path = ALERTS_DIR / "mosaic_asc" / f"exposure_{footprint}.geojson"
    if not path.exists():
        logger.info(f"no {path.name} — affected-area layer omitted "
                    f"(run exposure_footprint.py to add it)")
        return [], None
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data.get("properties", {})
    to_grid = Transformer.from_crs("EPSG:4326", crs, always_xy=True)

    def ring_points(feat):
        """Ring vertices as (col, row, z, hover) on this grid; rings outside it are dropped."""
        pts = []
        for poly in feat["geometry"]["coordinates"]:
            for ring in poly:
                seg = []
                for lon, lat in ring:
                    x, y = to_grid.transform(lon, lat)
                    r, c = rasterio.transform.rowcol(transform, x, y)
                    if not (0 <= r < h and 0 <= c < w):
                        continue
                    z = float(dem[r, c]) if np.isfinite(dem[r, c]) else elev_fill
                    seg.append((int(c), int(r), z))
                if len(seg) >= 3:
                    pts.append(seg)
        return pts

    zone_x, zone_y, zone_z, zone_t = [], [], [], []
    path_x, path_y, path_z, path_t = [], [], [], []
    n_zones = n_paths = 0
    for f in data.get("features", []):
        p = f["properties"]
        if p.get("kind") == "hazard_zone" and p.get("stack") == stack:
            reach = p.get("downstream_reach_m") or {}
            hover = (f"<b>#{p.get('triage_rank')} · {p.get('severity')}</b><br>"
                     f"{p['lat']:.4f}°N, {p['lon']:.4f}°E<br>"
                     f"triage priority {p.get('triage_priority')} · fails at wetness "
                     f"m*={p.get('m_star')}<br>"
                     f"detection confidence {p.get('detection_confidence')} · "
                     f"{p.get('n_looks')} look(s)<br>"
                     + (f"debris could reach ~{max(reach.values())} m below" if reach else ""))
            for seg in ring_points(f):
                n_zones += 1
                for c, r, z in seg:
                    zone_x.append(c); zone_y.append(r); zone_z.append(z + 40); zone_t.append(hover)
                zone_x.append(None); zone_y.append(None); zone_z.append(None); zone_t.append("")
        elif p.get("kind") == "downstream_path" and p.get("of_zone_stack") == stack:
            hover = (f"<b>downstream of zone #{p.get('of_zone_rank')}</b><br>"
                     f"{p.get('reach_band')} (energy line ≥ {p.get('reach_angle_min_deg')}°)"
                     f"<br>{p.get('note', '')}")
            for seg in ring_points(f):
                n_paths += 1
                for c, r, z in seg:
                    path_x.append(c); path_y.append(r); path_z.append(z + 20); path_t.append(hover)
                path_x.append(None); path_y.append(None); path_z.append(None); path_t.append("")

    traces = []
    if zone_x:
        traces.append({"type": "scatter3d", "name": "Hazard zone footprint", "mode": "lines",
                       "x": zone_x, "y": zone_y, "z": zone_z, "visible": True,
                       "line": {"color": "#ff2d55", "width": 6},
                       "text": zone_t, "hoverinfo": "text"})
    if path_x:
        traces.append({"type": "scatter3d", "name": "Potential downstream path", "mode": "lines",
                       "x": path_x, "y": path_y, "z": path_z, "visible": True,
                       "line": {"color": "#ffa000", "width": 3},
                       "text": path_t, "hoverinfo": "text"})
    logger.info(f"affected-area layer: {n_zones} zone outline(s), {n_paths} downstream "
                f"outline(s) on {stack}")
    return traces, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stack", default=None,
                    help="Radar look to render. Default: derived from the ACTIVE AOI's own "
                         "products (never another site's stack — see resolve_stack).")
    ap.add_argument("--exposure-footprint", default="operational",
                    help="Which affected-area layer to drape (default: operational). "
                         "Omitted silently when that layer has not been generated.")
    ap.add_argument("--stride", type=int, default=2,
                    help="Downsample factor for the terrain surface (2 = every 2nd pixel).")
    ap.add_argument("--z-exaggeration", type=float, default=0.5,
                    help="Vertical relief in the 3-D box (Plotly z aspectratio).")
    args = ap.parse_args()
    stack = resolve_stack(args.stack)
    logger.info(f"Building 3-D dashboard for {stack} ({_CFG.aoi_slug})")

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

    exp_traces, exp_meta = exposure_traces(stack, args.exposure_footprint, transform, crs,
                                           dem, h, w, elev_fill)
    traces = [surface, creep] + alert_traces + exp_traces

    # Scenario toggle buttons: keep surface(0)+creep(1) state, switch alert traces.
    # The restyle is given EXPLICIT trace indices so it only ever touches those traces —
    # without them the visibility array would spill onto the affected-area traces appended
    # after the alerts and silently flip them every time a scenario button is pressed.
    n_fixed = 2
    scenario_idx = list(range(n_fixed + len(alert_traces)))
    buttons = []
    for i, sc in enumerate(SCENARIOS):
        vis = [True, "legendonly"] + [(j == i) for j in range(len(alert_traces))]
        buttons.append({"label": f"{sc.capitalize()}  ({counts.get(sc,0)})",
                        "method": "restyle", "args": [{"visible": vis}, scenario_idx]})

    # Affected-area ON/OFF — a dedicated control rather than a legend click, because this is
    # the layer an operator turns on to answer "what ground is this about?".
    exp_menu = []
    if exp_traces:
        exp_idx = list(range(n_fixed + len(alert_traces), len(traces)))
        exp_menu = [{
            "type": "buttons", "direction": "right", "showactive": True,
            "x": 0.5, "xanchor": "center", "y": 1.13, "active": 0,
            "bgcolor": "#5c2b1b", "font": {"color": "#fff"},
            "buttons": [
                {"label": "Affected area: ON", "method": "restyle",
                 "args": [{"visible": [True] * len(exp_idx)}, exp_idx]},
                {"label": "Affected area: OFF", "method": "restyle",
                 "args": [{"visible": [False] * len(exp_idx)}, exp_idx]},
            ]}]

    layout = {
        # Title on its own row above the control row (the affected-area toggle added a second
        # menu, and at a narrow window all three were landing on top of each other).
        "title": {"text": f"{SITE} — 3-D Hazard Explorer ({stack})", "x": 0.5, "y": 0.985},
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
        "margin": {"l": 0, "r": 0, "t": 120, "b": 0},
        "legend": {"x": 0, "y": 0.95, "bgcolor": "rgba(13,27,42,.6)"},
        "updatemenus": [{
            "type": "buttons", "direction": "right", "showactive": True,
            "x": 0.5, "xanchor": "center", "y": 1.03, "active": 1,
            "bgcolor": "#1b3a5b", "font": {"color": "#fff"},
            "buttons": buttons,
        }] + exp_menu,
    }

    # The affected-area note carries the layer's OWN standing (computed in exposure_footprint
    # from the back-test, not asserted here), so the shapes can never be read as endorsed by a
    # score they do not have.
    exp_note = ""
    if exp_meta:
        from html import escape as _esc
        # Only advertise the toggle when the toggle actually exists — a site whose layer is
        # empty gets no menu, and telling the reader to press a button that is not on the page
        # makes them doubt the page rather than the data.
        toggle = ("Switch it off with the “Affected area” button above the scenario row."
                  if exp_traces else "")
        exp_note = (
            f'<br><span class="k">Affected area</span> — outlines show the ground each zone '
            f'covers and the path debris could take below it. {toggle}'
            f'<br><span style="color:#ffb4b4">{_esc(str(exp_meta.get("headline", "")))}'
            f'</span><br><span style="color:#9fb3c8">'
            f'{_esc(str(exp_meta.get("scope_caveat", "")))}</span>')

    # Measured coverage of THIS look's grid, derived from the raster being rendered. It used to
    # read "Coverage ~14% of AOI" — a hardcoded RAMBAN measurement, printed unchanged on every
    # site's page the moment a second AOI could build one (§78's rule: a number must travel with
    # the identity of what it measured).
    cov_pct = 100.0 * float(np.isfinite(velocity).mean())

    # An empty explorer must SAY it is empty. Without this the page renders a serene, unmarked
    # mountain with "Dry (0) Monsoon (0) Extreme (0)" — which reads as "nothing wrong here"
    # rather than "this site has no hazard layers to show" (§79: empty map != safe slope).
    n_alert_markers = sum(counts.values())
    empty_note = ""
    if not n_alert_markers and not exp_traces:
        empty_note = (
            '<br><span style="color:#ffb4b4"><b>No hazard layers on this view.</b> The scenario '
            'products were never generated for this site, and its affected-area layer is empty. '
            'That is an <b>empty map, not a safe slope</b> — the terrain and the measured creep '
            'below are all this page is showing.</span>')

    # Interaction hints, only for layers this page actually has.
    hints = []
    if n_alert_markers:
        hints.append('hover an <span class="k">alert diamond</span> for its reasoning')
    hints.append('toggle “Measured creep” in the legend to show observed motion')
    scenario_hint = ("<br>Use the top buttons to switch rainfall scenario — watch alerts grow "
                     "from <span class=\"k\">dry</span> to <span class=\"k\">monsoon</span>."
                     if n_alert_markers else "")

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
 Drag to orbit · scroll to zoom · {' · '.join(hints)}.{scenario_hint}{empty_note}<br>
 <span style="color:#9fb3c8">Stack {stack} · generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.
 Measured velocity covers {cov_pct:.0f}% of this look's grid (unmeasured ≠ safe); soil params
 assumed; {LLOF_NOTE}.</span>{exp_note}
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

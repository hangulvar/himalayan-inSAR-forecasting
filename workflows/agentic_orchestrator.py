#!/usr/bin/env python
"""
agentic_orchestrator.py — Phase 4 Part A: the agentic warning system (MVP).

A *deterministic* orchestrator that embodies the project's three-agent vision as
a reproducible, offline Python pipeline (no LLM, no API keys). It ingests the
Phase 1-3 rasters, reasons about cascading hazard, and emits a fully demo-able
warning package.

The three agents (as classes, mirroring the project's "Agentic Multi-Modal
Hazard Forensics" concept):

  • InSARAuditor          — reads the LOS velocity + temporal-coherence rasters
                            (Phase 2) and identifies confidently *creeping*
                            ground.
  • MeteorologicalTrigger — given a rainfall scenario (dry / monsoon / extreme),
                            sets the assumed soil saturation and therefore which
                            Factor-of-Safety raster (Phase 3) applies.
  • CascadingReasoner     — fuses the two: a zone that is BOTH theoretically
                            unstable (FS < 1) AND measurably creeping fires an
                            alert. Clusters pixels into zones (dropping isolated
                            specks), geolocates them, and applies a heuristic
                            downstream-impact (LLOF) flag.

Outputs (per scenario, in data/alerts/):
  • alerts_<scenario>.json        — structured alerts (coords, reason, downstream risk)
  • alert_report_<scenario>.md    — human-readable briefing
  • dashboard_<scenario>.html     — self-contained, browser-openable hazard map + reasoning

Usage:
    python workflows/agentic_orchestrator.py                 # all 3 scenarios
    python workflows/agentic_orchestrator.py --scenario monsoon
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
import base64
import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from scipy import ndimage

from config import load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SFX = load_config().data_suffix   # '' for ramban; '_<slug>' so AOIs coexist
VEL_DIR = PROJECT_ROOT / "data" / f"velocity{_SFX}"
HAZ_DIR = PROJECT_ROOT / "data" / f"hazard{_SFX}"
OUT_DIR = PROJECT_ROOT / "data" / f"alerts{_SFX}"
RAIN_DIR = PROJECT_ROOT / "data" / "rainfall"
LOG_DIR = PROJECT_ROOT / "logs"

LOG_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(LOG_DIR / "agentic_orchestrator.log", encoding="utf-8")],
)
logger = logging.getLogger("orchestrator")

# Rainfall scenarios → assumed saturation → which Phase-3 FS raster to use.
# dry/monsoon/extreme are the MOCK what-if cascade (preserved baseline). 'operational' is
# the RAINFALL-REALISTIC standing product (RESULTS_AND_KPIS.md §16d/§20): the regional rainfall
# model only reaches m=1 on 11/214 days, so worst-case monsoon (m=1) over-flags (AUC 0.41,
# below chance). Drawing at a realistic wet-day saturation concentrates the alert on the
# steepest marginal slopes and BEATS CHANCE. The operating point is m=0.50 (~29 mm/72 h, a
# moderately-wet day) under MATRIC-SUCTION FS physics (§20) + the 12.5 m ALOS DEM (§21): AUC 0.64
# (the project best). History: m=0.40/0.535 (flat cohesion) -> m=0.55/0.614 (matric suction) ->
# m=0.50/0.64 (+12.5 m DEM). Each physics upgrade shifted the operating saturation + improved AUC.
# 'watch' is the higher-RECALL complement to 'operational' (§23): the m=0.50 ALERT map is sparse
# (12 zones, AUC-max but low recall), so 'watch' draws a wetter antecedent (m=0.70 ~ sustained
# monsoon) → a broader ~132-zone monitoring footprint. Two-tier hazard product: WATCH = monitor
# wider (more recall, lower precision), ALERT = act on the precise core. (Distinct from the
# operational_alarm.py TEMPORAL DORMANT/WATCH/ALERT states, which decide WHEN to consult a map.)
SCENARIOS = {
    "dry":         {"rainfall_mm_72h": 0,   "saturation": 0.0,  "fs_layer": "FS_dry"},
    "operational": {"rainfall_mm_72h": 29,  "saturation": 0.50, "fs_layer": "FS_real"},
    "watch":       {"rainfall_mm_72h": 50,  "saturation": 0.70, "fs_layer": "FS_real"},
    "monsoon":     {"rainfall_mm_72h": 120, "saturation": 1.0,  "fs_layer": "FS_saturated"},
    "extreme":     {"rainfall_mm_72h": 250, "saturation": 1.0,  "fs_layer": "FS_saturated"},
}

# Thresholds (consistent with Phase 3 / the project's Phase-4 rule).
VEL_CREEP_THR = -15.0     # mm/yr; more negative = moving away from sensor (downslope)
FS_FAIL = 1.0
MIN_CLUSTER_PX = 3        # drop isolated single/double-pixel specks (Phase 3 noise finding)
CRITICAL_VEL = -50.0      # mm/yr → escalate severity
CRITICAL_FS = 0.7


# ------------------------------------------------------------------------------
# Real-rainfall coupling — replaces the mock saturation with the MEASURED daily
# wetness (from fetch_rainfall.py + rainfall_id_threshold.py). FS is exactly linear
# in saturation m (infinite-slope model, constant unit weight), so for any real m we
# interpolate FS_real = (1-m)*FS_dry + m*FS_saturated from the two end-member rasters
# instead of re-running the geomechanical engine.
# ------------------------------------------------------------------------------
def load_wetness():
    """Ordered (dates, rain_mm{}, wetness_0_1{}) from the rainfall pipeline outputs."""
    path = RAIN_DIR / f"{load_config().aoi_slug}_wetness_daily.csv"
    if not path.exists():
        sys.exit(f"Missing {path} — run fetch_rainfall.py + rainfall_id_threshold.py first.")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    dates = [r["date"] for r in rows]
    return (dates,
            {r["date"]: float(r["rain_mm"]) for r in rows},
            {r["date"]: float(r["wetness_0_1"]) for r in rows})


def trigger_days() -> set:
    p = RAIN_DIR / "id_threshold_report.json"
    return set(json.loads(p.read_text(encoding="utf-8"))["trigger_days"]) if p.exists() else set()


def real_rainfall_cfg(date_str: str) -> dict:
    """Scenario cfg for a real date: saturation m from the daily wetness, 72h rainfall
    from the trailing 3-day total, and whether the day crossed the ID threshold."""
    dates, rain, mwet = load_wetness()
    if date_str not in mwet:
        sys.exit(f"{date_str} not in wetness series ({dates[0]}..{dates[-1]}).")
    i = dates.index(date_str)
    rain72 = sum(rain[d] for d in dates[max(0, i - 2):i + 1])
    return {"name": date_str, "rainfall_mm_72h": round(rain72),
            "saturation": round(mwet[date_str], 3), "fs_layer": "FS_real",
            "rain_day_mm": round(rain[date_str], 1),
            "is_trigger": date_str in trigger_days()}


# ------------------------------------------------------------------------------
# Agent 1 — InSAR Auditor
# ------------------------------------------------------------------------------
class InSARAuditor:
    """Reads Phase-2 velocity + temporal coherence; flags confident creep."""

    def __init__(self, stack: str, use_vslope: bool = False):
        self.stack = stack
        self.vel_kind = "downslope V_slope" if use_vslope else "LOS"
        name = "v_slope" if use_vslope else "mean_velocity_los_highpass"
        with rasterio.open(VEL_DIR / f"{stack}_{name}.tif") as s:
            v = s.read(1)
            self.transform = s.transform
            self.crs = s.crs
            self.width, self.height = s.width, s.height
        # V_slope is +ve downslope and already masks single-look blind pixels (|C|<0.3) to
        # NaN. Negate it so the failure direction stays NEGATIVE, matching the LOS sign
        # convention every downstream step (creep<thr, severity<=-50, sort, narrative) uses.
        self.velocity = -v if use_vslope else v
        tcoh = VEL_DIR / f"{stack}_temporal_coherence.tif"
        self.tcoh = rasterio.open(tcoh).read(1) if tcoh.exists() else None

    def creep_mask(self, vel_thr: float) -> np.ndarray:
        m = np.isfinite(self.velocity) & (self.velocity < vel_thr)
        logger.info(f"[Agent 1: InSAR Auditor] {int(m.sum()):,} pixels creeping "
                    f"({self.vel_kind} velocity < {vel_thr} mm/yr).")
        return m


# ------------------------------------------------------------------------------
# Agent 2 — Meteorological Trigger
# ------------------------------------------------------------------------------
class MeteorologicalTrigger:
    """Mock rainfall scenario → saturation → selects the applicable FS raster."""

    def __init__(self, stack: str, scenario: str, cfg=None):
        self.stack = stack
        self.scenario = scenario
        self.cfg = cfg if cfg is not None else SCENARIOS[scenario]
        if self.cfg["fs_layer"] == "FS_real":     # real-rainfall: interpolate end-members
            m = float(self.cfg["saturation"])
            with rasterio.open(HAZ_DIR / f"{stack}_FS_dry.tif") as s:
                fs_dry = s.read(1)
            with rasterio.open(HAZ_DIR / f"{stack}_FS_saturated.tif") as s:
                fs_sat = s.read(1)
            self.fs = (1.0 - m) * fs_dry + m * fs_sat    # FS is exactly linear in m
            logger.info(f"[Agent 2: Meteorological Trigger] REAL rainfall {scenario}: "
                        f"day {self.cfg.get('rain_day_mm')} mm, 72h {self.cfg['rainfall_mm_72h']} mm "
                        f"-> saturation m={m:.2f} -> FS_real=(1-m)*FS_dry+m*FS_saturated"
                        f"{'  [ID-THRESHOLD TRIGGER]' if self.cfg.get('is_trigger') else ''}.")
        else:
            with rasterio.open(HAZ_DIR / f"{stack}_{self.cfg['fs_layer']}.tif") as s:
                self.fs = s.read(1)
            logger.info(f"[Agent 2: Meteorological Trigger] scenario='{scenario}' "
                        f"rainfall={self.cfg['rainfall_mm_72h']} mm/72h -> "
                        f"saturation m={self.cfg['saturation']} -> uses {self.cfg['fs_layer']}.")

    def unstable_mask(self, fs_fail: float) -> np.ndarray:
        return np.isfinite(self.fs) & (self.fs < fs_fail)


# ------------------------------------------------------------------------------
# Agent 3 — Cascading Reasoner
# ------------------------------------------------------------------------------
class CascadingReasoner:
    """Fuses creep + instability into geolocated, clustered alert zones."""

    def __init__(self, stack: str, auditor: InSARAuditor):
        self.stack = stack
        self.auditor = auditor
        self.to_lonlat = Transformer.from_crs(auditor.crs, "EPSG:4326", always_xy=True)
        # Context layers for reasoning.
        self.slope = self._read(HAZ_DIR / f"{stack}_slope_deg.tif")
        self.dem_elev = None  # derived from slope grid only; elevation via TWI proxy
        twi_p = HAZ_DIR / f"{stack}_twi.tif"
        self.twi = self._read(twi_p) if twi_p.exists() else None
        # Valley-floor proxy: highest-TWI (most water-collecting) pixels.
        if self.twi is not None:
            finite = np.isfinite(self.twi)
            self.valley_twi = np.nanpercentile(self.twi[finite], 90) if finite.any() else None
        else:
            self.valley_twi = None

    @staticmethod
    def _read(p: Path):
        return rasterio.open(p).read(1) if p.exists() else None

    def build_alerts(self, creep: np.ndarray, fs: np.ndarray, unstable: np.ndarray,
                     scenario_cfg: dict) -> list[dict]:
        trigger = creep & unstable
        labels, n = ndimage.label(trigger)
        alerts: list[dict] = []
        for lab in range(1, n + 1):
            ys, xs = np.where(labels == lab)
            if ys.size < MIN_CLUSTER_PX:
                continue  # drop isolated specks (Phase 3 noise lesson)
            alerts.append(self._describe_zone(lab, ys, xs, fs, scenario_cfg))
        # Severity-sort: most negative velocity first.
        alerts.sort(key=lambda a: a["mean_velocity_mmyr"])
        for i, a in enumerate(alerts, start=1):
            a["id"] = i
        logger.info(f"[Agent 3: Cascading Reasoner] {len(alerts)} alert zone(s) "
                    f"(>= {MIN_CLUSTER_PX} px, FS<{FS_FAIL} AND creep).")
        return alerts

    def _describe_zone(self, lab, ys, xs, fs, cfg) -> dict:
        a = self.auditor
        n_px = int(ys.size)
        pixel_m = abs(a.transform.a)
        area_m2 = n_px * pixel_m * pixel_m
        # centroid pixel → UTM → lon/lat
        cy, cx = float(ys.mean()), float(xs.mean())
        ux, uy = a.transform * (cx + 0.5, cy + 0.5)
        lon, lat = self.to_lonlat.transform(ux, uy)
        vel_vals = a.velocity[ys, xs]
        fs_vals = fs[ys, xs]
        slope_vals = self.slope[ys, xs] if self.slope is not None else np.array([np.nan])
        mean_vel = float(np.nanmean(vel_vals))
        max_vel = float(np.nanmin(vel_vals))  # most negative = fastest downslope
        mean_fs = float(np.nanmean(fs_vals))
        mean_slope = float(np.nanmean(slope_vals))

        severity = "CRITICAL" if (mean_vel <= CRITICAL_VEL or mean_fs <= CRITICAL_FS) else "HIGH"

        # Downstream-impact (LLOF) heuristic — placeholder for a real flow-routing
        # / river-network analysis. We use the high-TWI valley proxy: a large,
        # steep failing zone with water-collecting (valley) terrain nearby is
        # flagged as a potential debris-delivery / Landslide-Lake-Outburst path.
        llof = False
        llof_reason = "No strong downstream-convergence signal near this zone."
        if self.twi is not None and self.valley_twi is not None:
            # look in a neighbourhood around the zone for valley pixels
            r0, r1 = max(int(ys.min()) - 5, 0), min(int(ys.max()) + 6, a.height)
            c0, c1 = max(int(xs.min()) - 5, 0), min(int(xs.max()) + 6, a.width)
            nbhd = self.twi[r0:r1, c0:c1]
            near_valley = np.isfinite(nbhd) & (nbhd >= self.valley_twi)
            if near_valley.any() and mean_slope > 25 and area_m2 > 4 * pixel_m * pixel_m:
                llof = True
                llof_reason = ("Failing steep zone drains toward a high-accumulation "
                               "channel (valley floor) within ~400 m — failure could "
                               "deliver debris to the downstream corridor (heuristic; "
                               "pending real hydrological flow routing).")

        reason = (
            f"{cfg['fs_layer']} = {mean_fs:.2f} (< {FS_FAIL}: theoretically unstable "
            f"under {cfg['rainfall_mm_72h']} mm/72h rainfall) coincides with measured "
            f"{a.vel_kind} creep of {mean_vel:.0f} mm/yr (peak {max_vel:.0f}) over "
            f"{area_m2/1e6:.3f} km² of {mean_slope:.0f}° slope."
        )
        return {
            "id": 0,
            "severity": severity,
            "centroid_lonlat": [round(lon, 5), round(lat, 5)],
            "pixel_rowcol": [int(round(cy)), int(round(cx))],
            "n_pixels": n_px,
            "area_km2": round(area_m2 / 1e6, 4),
            "mean_fs": round(mean_fs, 3),
            "mean_velocity_mmyr": round(mean_vel, 1),
            "max_velocity_mmyr": round(max_vel, 1),
            "mean_slope_deg": round(mean_slope, 1),
            "trigger_reason": reason,
            "downstream_risk": {"llof_potential": llof, "reason": llof_reason},
        }


# ------------------------------------------------------------------------------
# Dashboard rendering (self-contained HTML + embedded PNG)
# ------------------------------------------------------------------------------
def hazard_png_b64(fs: np.ndarray, creep: np.ndarray, fs_fail: float) -> str:
    """Colorise a hazard map to a base64 PNG: green=low, amber=watch, red=high."""
    from PIL import Image
    h, w = fs.shape
    rgb = np.full((h, w, 3), 235, dtype=np.uint8)  # nodata grey
    defined = np.isfinite(fs)
    unstable = defined & (fs < fs_fail)
    rgb[defined] = (70, 160, 70)                       # LOW (stable)
    rgb[unstable | (creep & defined)] = (240, 180, 40)  # WATCH
    rgb[unstable & creep] = (220, 40, 40)               # HIGH
    img = Image.fromarray(rgb, "RGB")
    # upscale for visibility while keeping it light
    scale = max(1, 700 // max(h, w))
    if scale > 1:
        img = img.resize((w * scale, h * scale), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii"), img.size


def write_dashboard(path: Path, stack: str, scenario: str, cfg: dict,
                    alerts: list[dict], fs: np.ndarray, creep: np.ndarray,
                    width: int, height: int) -> None:
    png_b64, (img_w, img_h) = hazard_png_b64(fs, creep, FS_FAIL)

    # marker overlays (percentage-positioned over the image)
    markers = []
    for a in alerts:
        r, c = a["pixel_rowcol"]
        left = 100.0 * (c + 0.5) / width
        top = 100.0 * (r + 0.5) / height
        color = "#b00020" if a["severity"] == "CRITICAL" else "#d62728"
        markers.append(
            f'<div class="mk" style="left:{left:.1f}%;top:{top:.1f}%;background:{color}" '
            f'title="Alert {a["id"]}: {a["severity"]}">{a["id"]}</div>'
        )

    cards = []
    for a in alerts:
        llof = a["downstream_risk"]
        llof_badge = ('<span class="badge llof">LLOF risk</span>'
                      if llof["llof_potential"] else "")
        cards.append(f"""
        <div class="card {a['severity'].lower()}">
          <div class="card-h"><span class="num">{a['id']}</span>
            <span class="sev {a['severity'].lower()}">{a['severity']}</span>{llof_badge}</div>
          <div class="coord">📍 {a['centroid_lonlat'][1]:.4f}°N, {a['centroid_lonlat'][0]:.4f}°E
            &nbsp;·&nbsp; {a['area_km2']:.3f} km² &nbsp;·&nbsp; {a['mean_slope_deg']:.0f}° slope</div>
          <div class="reason">{a['trigger_reason']}</div>
          <div class="downstream"><b>Downstream:</b> {llof['reason']}</div>
        </div>""")

    n_crit = sum(1 for a in alerts if a["severity"] == "CRITICAL")
    n_llof = sum(1 for a in alerts if a["downstream_risk"]["llof_potential"])
    cards_html = "\n".join(cards) if cards else (
        "<p class='none'>No alert zones fired for this scenario — "
        "no ground is both theoretically unstable AND measurably creeping.</p>")

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Ramban Hazard Dashboard — {scenario}</title>
<style>
 body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f5f7;color:#1c1c1e}}
 header{{background:#0d1b2a;color:#fff;padding:16px 24px}}
 header h1{{margin:0;font-size:19px}} header .sub{{opacity:.8;font-size:13px;margin-top:4px}}
 .wrap{{display:flex;gap:18px;padding:18px 24px;align-items:flex-start;flex-wrap:wrap}}
 .mapbox{{position:relative;flex:0 0 auto;border:1px solid #ccc;background:#fff;border-radius:6px;overflow:hidden}}
 .mapbox img{{display:block;width:{img_w}px;height:{img_h}px;max-width:60vw;height:auto}}
 .mk{{position:absolute;transform:translate(-50%,-50%);color:#fff;font-size:11px;font-weight:bold;
     width:18px;height:18px;border-radius:50%;text-align:center;line-height:18px;border:1.5px solid #fff;box-shadow:0 0 3px rgba(0,0,0,.5)}}
 .panel{{flex:1 1 360px;min-width:340px;max-height:78vh;overflow:auto}}
 .summary{{background:#fff;border:1px solid #ddd;border-radius:6px;padding:12px 14px;margin-bottom:12px}}
 .summary b{{font-size:22px}}
 .card{{background:#fff;border:1px solid #ddd;border-left:5px solid #d62728;border-radius:6px;padding:10px 12px;margin-bottom:10px}}
 .card.critical{{border-left-color:#b00020}}
 .card-h{{display:flex;align-items:center;gap:8px;margin-bottom:4px}}
 .num{{background:#333;color:#fff;width:20px;height:20px;border-radius:50%;text-align:center;line-height:20px;font-size:12px}}
 .sev{{font-weight:bold;font-size:12px;color:#d62728}} .sev.critical{{color:#b00020}}
 .badge.llof{{background:#1a73e8;color:#fff;font-size:10px;padding:2px 6px;border-radius:8px;margin-left:auto}}
 .coord{{font-size:12px;color:#444;margin:3px 0}}
 .reason{{font-size:13px;margin:4px 0}} .downstream{{font-size:12px;color:#555}}
 .legend{{font-size:12px;margin-top:8px}} .legend span{{display:inline-block;width:12px;height:12px;border-radius:2px;vertical-align:middle;margin:0 4px}}
 .none{{color:#666;font-style:italic}}
 footer{{padding:10px 24px;font-size:11px;color:#888}}
</style></head><body>
<header>
  <h1>🏔️ Ramban NH-44 — Landslide Hazard Dashboard</h1>
  <div class="sub">Agentic forecast · stack {stack} · scenario: <b>{scenario.upper()}</b>
   ({cfg['rainfall_mm_72h']} mm/72h rainfall, saturation m={cfg['saturation']}, {cfg['fs_layer']})
   · generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>
</header>
<div class="wrap">
  <div>
    <div class="mapbox">
      <img src="data:image/png;base64,{png_b64}" alt="hazard map"/>
      {''.join(markers)}
    </div>
    <div class="legend">
      <span style="background:#46a046"></span>Low / stable
      <span style="background:#f0b428"></span>Watch (unstable OR creeping)
      <span style="background:#dc2828"></span>High (unstable AND creeping)
      <span style="background:#ebebeb"></span>No data
    </div>
  </div>
  <div class="panel">
    <div class="summary">
      <b>{len(alerts)}</b> alert zone(s) &nbsp;|&nbsp; {n_crit} critical &nbsp;|&nbsp;
      {n_llof} with downstream (LLOF) risk<br>
      <span style="font-size:12px;color:#555">Rule: Factor of Safety &lt; {FS_FAIL}
      <b>AND</b> LOS creep &lt; {VEL_CREEP_THR} mm/yr, clustered to ≥ {MIN_CLUSTER_PX} px.</span>
    </div>
    {cards_html}
  </div>
</div>
<footer>MVP demo · deterministic orchestrator · velocity coverage is sparse (~14% of AOI);
absent pixels are unmeasured, not necessarily safe. Soil parameters are literature
assumptions; LLOF flag is a heuristic pending real flow routing.</footer>
</body></html>"""
    path.write_text(html, encoding="utf-8")


def write_report(path: Path, stack: str, scenario: str, cfg: dict, alerts: list[dict]):
    n_crit = sum(1 for a in alerts if a["severity"] == "CRITICAL")
    n_llof = sum(1 for a in alerts if a["downstream_risk"]["llof_potential"])
    lines = [
        f"# Hazard Briefing — {stack} — scenario: {scenario.upper()}",
        "",
        f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"by the deterministic agentic orchestrator (Phase 4 Part A)._",
        "",
        f"**Meteorological trigger:** {cfg['rainfall_mm_72h']} mm rainfall over 72 h "
        f"→ assumed saturation m={cfg['saturation']} → Factor-of-Safety layer "
        f"`{cfg['fs_layer']}`.",
        "",
        f"**Decision rule:** alert where `{cfg['fs_layer']} < {FS_FAIL}` **AND** "
        f"`LOS velocity < {VEL_CREEP_THR} mm/yr`, clustered to ≥ {MIN_CLUSTER_PX} pixels.",
        "",
        f"## Summary",
        f"- **{len(alerts)}** alert zone(s); **{n_crit}** critical; "
        f"**{n_llof}** with potential downstream (LLOF) impact.",
        "",
    ]
    if alerts:
        lines += ["## Alert zones (most active first)", "",
                  "| # | Severity | Location (lat, lon) | Area km² | Mean FS | "
                  "Mean vel (mm/yr) | Slope° | LLOF |",
                  "|---|---|---|---|---|---|---|---|"]
        for a in alerts:
            lines.append(
                f"| {a['id']} | {a['severity']} | "
                f"{a['centroid_lonlat'][1]:.4f}, {a['centroid_lonlat'][0]:.4f} | "
                f"{a['area_km2']:.3f} | {a['mean_fs']:.2f} | {a['mean_velocity_mmyr']:.0f} | "
                f"{a['mean_slope_deg']:.0f} | {'YES' if a['downstream_risk']['llof_potential'] else '–'} |")
        lines += ["", "## Reasoning (per zone)", ""]
        for a in alerts:
            lines.append(f"**Zone {a['id']} ({a['severity']}):** {a['trigger_reason']}")
            if a["downstream_risk"]["llof_potential"]:
                lines.append(f"  - ⚠️ Downstream: {a['downstream_risk']['reason']}")
            lines.append("")
    else:
        lines.append("_No alert zones — nothing is both unstable and creeping in this scenario._")
    lines += ["", "---",
              "_Caveats: velocity coverage ~14% of AOI (unmeasured ≠ safe); soil "
              "parameters are literature assumptions; LLOF is a heuristic pending "
              "real flow routing; single ascending stack._"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------
# Season hazard timeline — the time-resolved view the mock scenarios cannot give.
# ------------------------------------------------------------------------------
def hazard_timeline(stack: str, out_dir: Path, use_vslope: bool = False) -> None:
    """Alert-zone count per day, driven by the REAL daily saturation. Same FS<1 AND
    creep rule, but FS_real is re-interpolated for each day's measured wetness, so the
    hazard rises and falls with the actual rainfall (peaking on the trigger day)."""
    auditor = InSARAuditor(stack, use_vslope)
    creep = auditor.creep_mask(VEL_CREEP_THR)
    with rasterio.open(HAZ_DIR / f"{stack}_FS_dry.tif") as s:
        fs_dry = s.read(1)
    with rasterio.open(HAZ_DIR / f"{stack}_FS_saturated.tif") as s:
        fs_sat = s.read(1)
    dates, rain, mwet = load_wetness()
    trig = trigger_days()
    px_km2 = (abs(auditor.transform.a) / 1000.0) ** 2

    rows = []
    for d in dates:
        m = mwet[d]
        fs = (1.0 - m) * fs_dry + m * fs_sat
        labels, n = ndimage.label(creep & np.isfinite(fs) & (fs < FS_FAIL))
        if n:
            sizes = np.bincount(labels.ravel())[1:]
            keep = sizes[sizes >= MIN_CLUSTER_PX]
            nz, area = int(keep.size), float(keep.sum() * px_km2)
        else:
            nz, area = 0, 0.0
        rows.append((d, rain[d], m, nz, area))

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "hazard_timeline.csv"
    csv_path.write_text(
        "date,rain_mm,saturation_m,n_alert_zones,alert_area_km2\n"
        + "\n".join(f"{d},{r:.2f},{m:.3f},{nz},{a:.4f}" for d, r, m, nz, a in rows),
        encoding="utf-8")
    _timeline_figure(out_dir / "hazard_timeline.png", rows, trig, stack)
    peak = max(rows, key=lambda x: x[3])
    logger.info(f"[hazard timeline] {len(rows)} days -> {csv_path.name} + .png ; "
                f"peak {peak[3]} zones on {peak[0]} (m={peak[2]:.2f}, {peak[1]:.0f} mm); "
                f"trigger day(s): {sorted(trig) if trig else 'none'}")


def _timeline_figure(path: Path, rows, trig: set, stack: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dates = [r[0] for r in rows]
    x = np.arange(len(rows))
    rain = np.array([r[1] for r in rows])
    nz = np.array([r[3] for r in rows])
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x, rain, color="#9ecae1", width=1.0)
    ax.set_ylabel("daily rainfall (mm)", color="#3182bd")
    ax2 = ax.twinx()
    ax2.plot(x, nz, color="#cc3311", lw=1.6)
    ax2.set_ylabel("alert zones (FS<1 & creep)", color="#cc3311")
    for i, d in enumerate(dates):
        if d in trig:
            ax.axvline(i, color="k", ls="--", alpha=0.6)
    tick = np.linspace(0, len(rows) - 1, 7).astype(int)
    ax.set_xticks(tick)
    ax.set_xticklabels([dates[i] for i in tick], fontsize=8)
    ax.set_title(f"{stack}: hazard driven by REAL rainfall — alert zones (red) vs daily rain "
                 f"(blue); dashed = ID-threshold trigger")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ------------------------------------------------------------------------------
def run_scenario(stack: str, scenario: str, out_dir: Path = OUT_DIR, cfg=None,
                 use_vslope: bool = False) -> dict:
    logger.info(f"===== Orchestrating scenario '{scenario}' for {stack} =====")
    auditor = InSARAuditor(stack, use_vslope)
    met = MeteorologicalTrigger(stack, scenario, cfg)
    reasoner = CascadingReasoner(stack, auditor)

    creep = auditor.creep_mask(VEL_CREEP_THR)
    unstable = met.unstable_mask(FS_FAIL)
    alerts = reasoner.build_alerts(creep, met.fs, unstable, met.cfg)

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "stack": stack,
        "scenario": {"name": scenario, **met.cfg},
        "thresholds": {"fs_fail": FS_FAIL, "vel_creep_mmyr": VEL_CREEP_THR,
                       "min_cluster_px": MIN_CLUSTER_PX},
        "velocity_basis": auditor.vel_kind,
        "summary": {
            "n_alert_zones": len(alerts),
            "n_critical": sum(1 for a in alerts if a["severity"] == "CRITICAL"),
            "n_llof": sum(1 for a in alerts if a["downstream_risk"]["llof_potential"]),
            "total_alert_area_km2": round(sum(a["area_km2"] for a in alerts), 4),
        },
        "alerts": alerts,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"alerts_{scenario}.json").write_text(json.dumps(payload, indent=2),
                                                     encoding="utf-8")
    write_report(out_dir / f"alert_report_{scenario}.md", stack, scenario, met.cfg, alerts)
    write_dashboard(out_dir / f"dashboard_{scenario}.html", stack, scenario, met.cfg,
                    alerts, met.fs, creep, auditor.width, auditor.height)
    logger.info(f"Scenario '{scenario}': {len(alerts)} alerts -> "
                f"alerts_{scenario}.json / alert_report_{scenario}.md / "
                f"dashboard_{scenario}.html")
    return payload["summary"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stack", default="ASC_path27_frame106")
    ap.add_argument("--scenario", choices=list(SCENARIOS) + ["all"], default="all")
    ap.add_argument("--date", default=None,
                    help="Run a REAL-rainfall-driven scenario for this date (YYYY-MM-DD): the "
                         "saturation comes from the measured daily wetness, not a mock scenario.")
    ap.add_argument("--rainfall-timeline", action="store_true",
                    help="Write the season alert-zone timeline driven by real daily rainfall.")
    ap.add_argument("--use-vslope", action="store_true",
                    help="Detect creep from the slope-parallel velocity (*_v_slope.tif, "
                         "downslope-projected, single-look blind pixels excluded) instead of raw "
                         "LOS. Sharper/more physical; off by default to preserve the LOS baselines.")
    ap.add_argument("--out-dir", default=None,
                    help="Output directory for alerts/report/dashboard "
                         "(default: data/alerts/). Use per-stack dirs to avoid collisions.")
    args = ap.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else OUT_DIR
    if args.rainfall_timeline:
        hazard_timeline(args.stack, out_dir, args.use_vslope)
        return 0
    if args.date:
        run_scenario(args.stack, args.date, out_dir, real_rainfall_cfg(args.date), args.use_vslope)
        logger.info(f"Real-rainfall scenario {args.date} -> {out_dir}/dashboard_{args.date}.html")
        return 0
    scenarios = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    results = {sc: run_scenario(args.stack, sc, out_dir, use_vslope=args.use_vslope)
               for sc in scenarios}

    logger.info("-" * 60)
    logger.info("Scenario comparison (the cascade in action):")
    for sc, s in results.items():
        logger.info(f"  {sc:<8s}: {s['n_alert_zones']:>3d} zones, "
                    f"{s['n_critical']} critical, {s['n_llof']} LLOF, "
                    f"{s['total_alert_area_km2']:.2f} km²")
    logger.info(f"Open the dashboards in a browser: {out_dir}/dashboard_<scenario>.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())

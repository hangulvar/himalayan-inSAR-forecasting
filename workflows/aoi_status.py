#!/usr/bin/env python
"""aoi_status.py — the multi-AOI registry dashboard: where does every site stand?

Scans the per-AOI config registry (config/*.yaml), inspects each AOI's on-disk
artifacts, and answers three questions per site, deterministically:

  1. WHICH pipeline stages are done (polygon -> soil pass -> radar -> DEM ->
     multistack -> inventory -> validation -> operating points -> rainfall ->
     live alarm), including the MANUAL steps a new AOI needs (soil literature
     pass, ALOS DEM tile, verified landslide inventory);
  2. WHAT the current operational state is (alarm level / live zones / exceedance
     as-of the newest rainfall day, and how stale the rainfall is);
  3. WHAT to run next — the first incomplete stage's exact command.

Read-only over data/ (safe to run any time, any image — stdlib + yaml only, no
numpy/rasterio, so it also runs natively without the conda env's BLAS).

Outputs:
    console summary (ASCII)
    data/aoi_status.json    machine-readable
    data/aoi_status.html    self-contained browser dashboard

Usage:
    python workflows/aoi_status.py            # all AOIs in config/
    python workflows/aoi_status.py --aoi vaishnodevi   # just one slug
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml

from config import load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA = PROJECT_ROOT / "data"
RAIN_DIR = DATA / "rainfall"
INV_DIR = DATA / "inventory"

LEVEL_COLOR = {"DORMANT": "#9aa0a6", "WATCH": "#f0b428", "ALERT": "#dc2828",
               "NO LIVE SEASON": "#c7cdd6"}
# ERA5-Land publishes ~5 days behind real time; beyond this the live CSV is stale.
FRESH_DAYS = 7


@dataclass
class Stage:
    key: str
    label: str
    kind: str          # 'auto' | 'manual' | 'agent'
    done: bool
    detail: str = ""
    next_cmd: str = "" # what to run/do if not done


@dataclass
class AoiStatus:
    slug: str
    site_name: str
    config_path: str
    alarm_level: str = "NO LIVE SEASON"
    alarm_as_of: str = ""
    exceedance: str = ""
    live_zones: str = ""
    footprint_zones: str = ""
    rain_days_behind: str = ""
    last_multistack: str = ""
    next_step: str = ""
    stages: list = field(default_factory=list)


# ---------------------------------------------------------------------------
def discover_configs(only_slug: str | None) -> list[Path]:
    paths = sorted(p for p in CONFIG_DIR.glob("*.yaml"))
    if not paths:  # registry empty -> fall back to the root config (legacy layout)
        paths = [PROJECT_ROOT / "config.yaml"]
    if only_slug:
        paths = [p for p in paths if load_config(p).aoi_slug == only_slug]
        if not paths:
            raise SystemExit(f"No registry config with slug '{only_slug}' in {CONFIG_DIR}")
    return paths


def _mtime(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d") if p.exists() else ""


def _last_csv_row(p: Path) -> dict | None:
    if not p.exists():
        return None
    last = None
    with p.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            last = row
    return last


def _latest_season_file(pattern_prefix: str, slug: str) -> Path | None:
    """Newest-year live artifact: '<prefix>_<year>.csv' (ramban, grandfathered)
    or '<prefix>_<slug>_<year>.csv' (other AOIs)."""
    rx = (re.compile(rf"{re.escape(pattern_prefix)}_(\d{{4}})\.csv$") if slug == "ramban"
          else re.compile(rf"{re.escape(pattern_prefix)}_{re.escape(slug)}_(\d{{4}})\.csv$"))
    best, best_year = None, -1
    for p in RAIN_DIR.glob(f"{pattern_prefix}*.csv"):
        m = rx.match(p.name)
        if m and int(m.group(1)) > best_year:
            best, best_year = p, int(m.group(1))
    return best


# ---------------------------------------------------------------------------
def assess(cfg_path: Path) -> AoiStatus:
    cfg = load_config(cfg_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    slug, sfx = cfg.aoi_slug, cfg.data_suffix
    rel = cfg_path.relative_to(PROJECT_ROOT).as_posix()
    ccfg = f" --config {rel}"          # scripts exposing the flag (submitter etc.)
    denv = f"-e INSAR_CONFIG={rel} "   # every other script, via the env override
    st = AoiStatus(slug=slug, site_name=cfg.site_name,
                   config_path=cfg_path.relative_to(PROJECT_ROOT).as_posix())
    stages: list[Stage] = []

    # 1. AOI polygon (manual M1)
    stages.append(Stage(
        "polygon", "AOI polygon (GeoJSON, EPSG:4326)", "manual",
        cfg.aoi_path.exists(), detail=cfg.aoi_path.name,
        next_cmd="Draw the AOI (Google Earth Pro -> KML -> GeoJSON) and set aoi_path "
                 "in the registry file (docs/runbooks/NEW_AOI_PLAYBOOK.md M1)"))

    # 2. Soil pass (manual M2) — an explicit soil: block records the site's own pass;
    #    without it the engine runs on the Ramban-calibrated defaults.
    stages.append(Stage(
        "soil", "Site soil pass (soil: block in config)", "manual",
        bool(raw.get("soil")),
        detail="site-corroborated values in config" if raw.get("soil")
               else "RUNNING ON RAMBAN DEFAULTS",
        next_cmd="Do the site soil literature/field pass and add the soil: block "
                 "(docs/runbooks/NEW_AOI_PLAYBOOK.md M2) — do not silently inherit another site's soils"))

    # 3. Phase 1 radar+QA — the radar library is SHARED across AOIs on the same frames,
    #    so per-AOI completion is proxied by the first per-AOI compute product (velocity).
    vel = sorted((DATA / f"velocity{sfx}").glob("*_mean_velocity_los_highpass.tif"))
    stages.append(Stage(
        "radar", "Phase 1 - radar pull + QA (shared library)", "auto",
        bool(vel),
        detail="proxied by Phase-2 products (library is shared across AOIs)",
        next_cmd=f"python workflows/submit_hyp3_jobs.py{ccfg}   (dry-run preview; add "
                 f"--submit) -> download_hyp3_products.py -> the QA chain (README Phase 1)"))

    # 4. 12.5 m ALOS DEM tile (manual M3, recommended — 30 m HyP3 DEM is the fallback)
    dem_dir = DATA / f"dem_alos_12m{sfx}"
    dem = sorted(dem_dir.glob("*.tif"))
    stages.append(Stage(
        "dem", "12.5 m ALOS DEM tile (optional upgrade)", "manual",
        bool(dem), detail=dem[0].name if dem else "falls back to 30 m HyP3 DEM",
        next_cmd=f"Fetch the ALOS PALSAR RTC 12.5 m tile from ASF Vertex into "
                 f"data/dem_alos_12m{sfx}/ (docs/runbooks/NEW_AOI_PLAYBOOK.md M3)"))

    # 5. Phases 2-4 multistack (velocity -> hazard -> union alerts, one driver)
    haz = sorted((DATA / f"hazard{sfx}").glob("*_hazard_class.tif"))
    alerts_op = DATA / f"alerts{sfx}" / "mosaic_asc" / "alerts_operational.json"
    n_zones = ""
    if alerts_op.exists():
        try:
            n_zones = len(json.loads(alerts_op.read_text(encoding="utf-8")).get("zones", []))
        except Exception:  # noqa: BLE001 — a corrupt file just means "no zone count"
            n_zones = "?"
    stages.append(Stage(
        "multistack", "Phases 2-4 - velocity / hazard / union alerts", "auto",
        bool(vel) and bool(haz) and alerts_op.exists(),
        detail=f"{len(vel)} stack(s) inverted, {len(haz)} hazard map(s), "
               f"operational zones: {n_zones or 'none'}",
        next_cmd=f"docker compose run --rm {denv}insar python workflows/run_multistack.py"))
    st.footprint_zones = str(n_zones)
    st.last_multistack = _mtime(alerts_op)

    # 6. Verified landslide inventory (manual M4 — verified ground truth, see §12g)
    inv_candidates = ([INV_DIR / "gsi_inventory_aoi.geojson",
                       INV_DIR / "ramban_documented_landslides.geojson"] if slug == "ramban"
                      else [INV_DIR / f"{slug}_documented_landslides.geojson"])
    inv = next((p for p in inv_candidates if p.exists()), None)
    stages.append(Stage(
        "inventory", "Verified landslide inventory", "manual",
        inv is not None, detail=inv.name if inv else inv_candidates[-1].name + " missing",
        next_cmd="Build the verified inventory (GSI Bhukosh/NGDR + primary-source press "
                 "verification, docs/runbooks/NEW_AOI_PLAYBOOK.md M4) -> data/inventory/"))

    # 7. Scored validation back-test
    # A score describes the footprint it was computed on. This card sat one line under
    # "operational zones: none" and still read "AUC 0.76" — the §78 defect, in the multi-AOI
    # dashboard: the back-test scored a 14-zone map, a radar rebuild took that map to 0 zones,
    # and the old number kept describing a map it had never seen. Carry the scored zone count
    # with the score and say NOT MEASURED when the map has moved (§6 #3).
    bt = INV_DIR / f"backtest_operational{sfx}_report.json"
    bt_detail = ""
    if bt.exists():
        try:
            r = json.loads(bt.read_text(encoding="utf-8"))
            auc = (r.get("scored") or {}).get("auc")
            scored_zones = r.get("n_flagged_zones")
            if isinstance(scored_zones, int) and isinstance(n_zones, int) \
                    and scored_zones != n_zones:
                bt_detail = (f"NOT MEASURED for today's map — last scored a {scored_zones}-zone "
                             f"map (AUC {auc:.2f}), this map has {n_zones}"
                             if isinstance(auc, (int, float)) else "NOT MEASURED for today's map")
            else:
                bt_detail = f"AUC {auc:.2f}" if isinstance(auc, (int, float)) else "scored"
        except Exception:  # noqa: BLE001
            bt_detail = "scored"
    stages.append(Stage(
        "validation", "Scored back-test vs inventory", "auto",
        bt.exists(), detail=bt_detail,
        next_cmd=f"docker compose run --rm {denv}insar python workflows/backtest_inventory.py "
                 f"--alerts data/alerts{sfx}/mosaic_asc/alerts_operational.json "
                 f"--inventory data/inventory/<inventory>.geojson"))

    # 8. Site-tuned operating points (agent M5) — Ramban's calibration IS the default.
    tuned = ("operational_m" in raw and "watch_m" in raw) or slug == "ramban"
    stages.append(Stage(
        "oppoints", "Site-tuned operating points (m-sweep)", "agent",
        tuned,
        detail=(f"ALERT m={cfg.operational_m}, WATCH m={cfg.watch_m}"
                + ("" if "operational_m" in raw or slug != "ramban"
                   else " (calibrated defaults)")) if tuned
               else f"using defaults m={cfg.operational_m}/{cfg.watch_m} — unswept",
        next_cmd=f"docker compose run --rm {denv}insar python workflows/"
                 f"rainfall_selectivity_backtest.py  -> set operational_m/watch_m "
                 f"in the registry file"))

    # 9. Rainfall baseline (back-test season CSV)
    base_csv = RAIN_DIR / f"{slug}_era5land_daily.csv"
    stages.append(Stage(
        "rainfall", "Rainfall baseline season (ERA5-Land)", "auto",
        base_csv.exists(), detail=base_csv.name,
        next_cmd=f"docker compose run --rm {denv}mintpy python workflows/fetch_rainfall.py"))

    # 10. Live season + alarm state
    season_csv = _latest_season_file(f"{slug}_era5land_daily", slug)
    cal_csv = _latest_season_file("operational_alarm_calendar", slug)
    last_day = None
    if season_csv:
        rows_last = _last_csv_row(season_csv)
        if rows_last and rows_last.get("date"):
            last_day = date.fromisoformat(rows_last["date"])
    behind = (date.today() - last_day).days if last_day else None
    fresh = behind is not None and behind <= FRESH_DAYS
    st.rain_days_behind = "" if behind is None else str(behind)
    if cal_csv:
        row = _last_csv_row(cal_csv)
        if row:
            st.alarm_level = row.get("alarm_level", "?")
            st.alarm_as_of = row.get("date", "")
            st.exceedance = row.get("exceedance_E", "")
            st.live_zones = row.get("n_live_zones", "")
    stages.append(Stage(
        "live", "Live season rainfall + alarm (2-3 day cadence)", "auto",
        bool(season_csv) and bool(cal_csv) and fresh,
        detail=(f"as-of {last_day}, {behind}d behind today"
                if last_day else "no live-season CSV yet"),
        next_cmd=f"docker compose run --rm {denv}mintpy python workflows/live_alarm.py  && "
                 f"docker compose run --rm {denv}insar python workflows/live_alarm.py"))

    st.stages = [asdict(s) for s in stages]
    nxt = next((s for s in stages if not s.done), None)
    st.next_step = (f"[{nxt.kind}] {nxt.label} -> {nxt.next_cmd}" if nxt else
                    "All stages green - routine ops: live_alarm every 2-3 days + the "
                    "radar-cadence cycle when new S1 passes land (SESSION_REVIEW roadmap #1)")
    return st


# ---------------------------------------------------------------------------
def write_html(statuses: list[AoiStatus], out: Path) -> None:
    cards = []
    for s in statuses:
        color = LEVEL_COLOR.get(s.alarm_level, "#9aa0a6")
        rows = "".join(
            f"<tr><td class='st'>{'&#10003;' if g['done'] else '&#9675;'}</td>"
            f"<td>{g['label']}<span class='kind'>{g['kind']}</span></td>"
            f"<td class='dt'>{g['detail'] if g['done'] else g['next_cmd']}</td></tr>"
            for g in s.stages)
        stat = (f"as-of {s.alarm_as_of} &middot; E={s.exceedance} &middot; live zones "
                f"{s.live_zones}/{s.footprint_zones}" if s.alarm_as_of else
                "no live season yet")
        rain = f"{s.rain_days_behind}d behind" if s.rain_days_behind else "-"
        cards.append(f"""
  <div class="card">
    <div class="head">
      <div><h2>{s.site_name}</h2>
        <div class="sub">{s.slug} &middot; {s.config_path}</div></div>
      <div class="badge" style="background:{color}">{s.alarm_level}</div>
    </div>
    <div class="stat">{stat}</div>
    <div class="meta">rainfall: {rain} &middot; last multistack: {s.last_multistack or '-'}</div>
    <div class="next"><b>NEXT</b> {s.next_step}</div>
    <table>{rows}</table>
  </div>""")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>AOI status — multi-site registry</title><style>
 body{{font-family:system-ui,Segoe UI,sans-serif;margin:24px;background:#f5f6f8;color:#222}}
 h1{{margin:0 0 4px}} .gsub{{color:#666;font-size:13px;margin-bottom:18px}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:16px}}
 .card{{background:#fff;border-radius:10px;padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
 .head{{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}}
 h2{{margin:0;font-size:17px}} .sub{{color:#888;font-size:12px}}
 .badge{{color:#fff;font-weight:700;padding:4px 12px;border-radius:14px;font-size:13px;white-space:nowrap}}
 .stat{{margin:8px 0 2px;font-size:13px}} .meta{{color:#666;font-size:12px}}
 .next{{margin:10px 0;padding:8px 10px;background:#eef4ff;border-left:3px solid #3b6fd4;
        font-size:12.5px;border-radius:4px;word-break:break-word}}
 table{{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:4px}}
 td{{padding:4px 6px;border-top:1px solid #eee;vertical-align:top}}
 .st{{width:18px;text-align:center;color:#2e8b57;font-weight:700}}
 .kind{{color:#aaa;font-size:10.5px;margin-left:6px;text-transform:uppercase}}
 .dt{{color:#666;max-width:260px;word-break:break-word}}
 .foot{{color:#888;font-size:12px;margin-top:18px}}
</style></head><body>
<h1>Multi-AOI status</h1>
<div class="gsub">Generated {date.today().isoformat()} by workflows/aoi_status.py &middot;
registry: config/*.yaml &middot; switch the active AOI by editing the one-line
<code>active_config</code> pointer in config.yaml &middot; onboarding: docs/runbooks/NEW_AOI_PLAYBOOK.md
&middot; decision-support prioritization prototype — not a warning system; no safety decision should
rest on it</div>
<div class="grid">{''.join(cards)}</div>
<div class="foot">Stage semantics: AUTO = verified from on-disk artifacts &middot; MANUAL =
user-side step detected by its artifact/config footprint &middot; AGENT = scripted sweep whose
result is recorded in the registry file. "Phase 1" is proxied by Phase-2 products because the
radar library is shared across AOIs on the same Sentinel-1 frames.</div>
</body></html>"""
    out.write_text(html, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aoi", help="Only this AOI slug (default: every config/*.yaml)")
    args = ap.parse_args()

    statuses = [assess(p) for p in discover_configs(args.aoi)]

    for s in statuses:
        print(f"\n=== {s.site_name}  [{s.slug}]  ({s.config_path})")
        state = (f"{s.alarm_level} as-of {s.alarm_as_of}  E={s.exceedance}  "
                 f"live {s.live_zones}/{s.footprint_zones} zones"
                 if s.alarm_as_of else s.alarm_level)
        print(f"    state: {state}")
        for g in s.stages:
            mark = "x" if g["done"] else " "
            print(f"    [{mark}] {g['label']:<48} {g['detail'] if g['done'] else ''}")
        print(f"    NEXT: {s.next_step}")

    DATA.mkdir(exist_ok=True)
    (DATA / "aoi_status.json").write_text(
        json.dumps({"generated": date.today().isoformat(),
                    "aois": [asdict(s) for s in statuses]}, indent=2),
        encoding="utf-8")
    write_html(statuses, DATA / "aoi_status.html")
    print(f"\n-> data/aoi_status.json , data/aoi_status.html  "
          f"({len(statuses)} AOI(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())

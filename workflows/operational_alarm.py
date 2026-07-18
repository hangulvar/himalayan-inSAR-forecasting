#!/usr/bin/env python
"""operational_alarm.py — the regional I-D curve as a TEMPORAL GATE over the validated
operational hazard footprint. The two-factor operational warning (RESULTS_AND_KPIS.md §17):

    WHEN  — the regional NW-Himalaya I-D curve says today's rainfall crossed the danger line,
            graded by the peak exceedance E(t) = max_D [ cum_D(t) / threshold_cum(D) ]
            (reused from rainfall_specificity.py — the SAME signal, single source of truth).
    WHERE — the spatial footprint is the VALIDATED operational m=0.50 union product
            (alerts_operational.json, §16e/§20) — the validated map that BEATS CHANCE (AUC 0.64).

Why a gate and not the raw trigger: the regional curve is sensitive — it fires E>=1 on ~112/214
days (§12c), too often to be operational. An I-D curve is a LOWER BOUND; how far ABOVE matters.
So we GRADE the day by E and only raise the operational alarm when E is well above the line:

    DORMANT  E < watch_k          (default 1.0) — below the regional line; footprint not armed
    WATCH    watch_k <= E < alert_k             — line crossed; the operational footprint is ARMED
    ALERT    E >= alert_k          (default 2.0) — well above the line; raise the operational alarm

This is the honest separation the validation work demanded: the curve decides *when*; the alert is
*always drawn at the operational m* (we do NOT let the footprint balloon to the worst-case monsoon map
on wet days — that is exactly what over-flagged in §16b). AOI-mean rain gives ONE E per day, so the gate
is AOI-wide on/off; sub-daily/spatial rain (IMERG) would let it vary per zone (a documented limitation).

Differs from `agentic_orchestrator.py --rainfall-timeline`, which scales the footprint with each day's
saturation m (so it balloons on peak days). Here the footprint is FIXED at the validated operational map
and only the temporal STATE changes — the operationally correct framing.

  docker compose run --rm insar python workflows/operational_alarm.py \
      --csv data/rainfall/ramban_era5land_daily.csv --threshold nwhimalaya
"""

from __future__ import annotations

import argparse
import base64
import json
from datetime import date, datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from config import load_config  # noqa: E402
from rainfall_id_threshold import THRESHOLDS, SLUG, antecedent_index, load_daily  # noqa: E402
from rainfall_specificity import (  # noqa: E402
    peak_exceedance, documented_events, nearest_alert_delta,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAIN_DIR = PROJECT_ROOT / "data" / "rainfall"
_CFG = load_config()
_SFX = _CFG.data_suffix              # '' for ramban; '_<slug>' so AOIs coexist
SITE = _CFG.site_name
ALERTS_DIR = PROJECT_ROOT / "data" / f"alerts{_SFX}"
INV_DIR = PROJECT_ROOT / "data" / "inventory"
# Per-AOI inventory convention (ramban's name unchanged); events are skipped
# gracefully when the site has no inventory yet.
INVENTORY = INV_DIR / f"{SLUG}_documented_landslides.geojson"

LEVELS = ["DORMANT", "WATCH", "ALERT"]
LEVEL_COLOR = {"DORMANT": "#e8e8e8", "WATCH": "#f0b428", "ALERT": "#dc2828"}


def _lift_at(roc: list, km: float):
    """Lift (vs the null control) at a specific buffer width, or None."""
    for row in roc:
        if abs(row.get("buffer_km", -1) - km) < 1e-9:
            return row.get("lift")
    return None


def load_tier(path: Path, required: bool = False):
    """A hazard-tier card: zone counts from the union footprint JSON + scored metrics
    (AUC, recall@2 km, lift@250 m, and the >=2-look core AUC) auto-loaded from the matching
    back-test reports `data/inventory/backtest_<scenario>{,_2look}_report.json` if present.
    `m` (assumed saturation) comes from agentic_orchestrator.SCENARIOS — single source of
    truth, never hard-coded. Returns None if the footprint is absent (unless `required`)."""
    if not path.exists():
        if required:
            raise SystemExit(f"Missing footprint {path} — run run_multistack.py first.")
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    zones = payload.get("zones", [])
    scenario = payload.get("scenario", path.stem.replace("alerts_", ""))
    try:
        from agentic_orchestrator import SCENARIOS
        m = SCENARIOS.get(scenario, {}).get("saturation")
    except Exception:
        m = None
    tier = {
        "scenario": scenario, "m": m,
        "n_zones": len(zones),
        "n_crit": sum(1 for z in zones if z.get("severity") == "CRITICAL"),
        "n_multi": sum(1 for z in zones if z.get("n_looks", 1) >= 2),
        "auc": None, "recall": None, "spec": None, "lift250": None,
        "core_zones": None, "core_auc": None, "core_lift": None,
    }
    # Back-test reports are per-AOI: suffixed for non-ramban sites so another AOI's
    # dashboard can never wear ramban's validation scores (fields stay None -> omitted).
    rpt = INV_DIR / f"backtest_{scenario}{_SFX}_report.json"
    if rpt.exists():
        sc = json.loads(rpt.read_text(encoding="utf-8")).get("scored", {})
        ab = sc.get("at_buffer_km", {})
        tier.update(auc=sc.get("auc"), recall=ab.get("tpr"), spec=ab.get("specificity"),
                    lift250=_lift_at(sc.get("roc", []), 0.25))
    # Statistical-rigor overlay (§44, validation_stats.py): bootstrap CI + permutation p.
    # When present it also supplies the AUC/recall point values (same protocol, refreshed
    # inventory), so the displayed number and its interval always come from one run.
    vs = INV_DIR / f"validation_stats_{scenario}{_SFX}.json"
    if vs.exists():
        vm = json.loads(vs.read_text(encoding="utf-8")).get("model", {})
        tier.update(auc=vm.get("auc", tier["auc"]),
                    recall=vm.get("recall_at_buffer", tier["recall"]),
                    auc_ci=vm.get("auc_ci95"), p_perm=vm.get("p_perm_beats_chance"))
    core = INV_DIR / f"backtest_{scenario}{_SFX}_2look_report.json"
    if core.exists():
        c = json.loads(core.read_text(encoding="utf-8"))
        cs = c.get("scored", {})
        tier.update(core_zones=c.get("n_flagged_zones"), core_auc=cs.get("auc"),
                    core_lift=cs.get("at_buffer_km", {}).get("lift"))
    return tier


def per_zone_live(alerts_dir: Path, as_of: str):
    """The per-zone ranking (§19) for the as-of day, if per_zone_gate.py has produced it.
    Returns {n_active, total, zones[: top]} or None (panel is skipped if absent)."""
    import csv as _csv
    vf = alerts_dir / "per_zone_vulnerability.csv"
    tf = alerts_dir / "per_zone_active_timeline.csv"
    if not (vf.exists() and tf.exists()):
        return None
    zones = list(_csv.DictReader(vf.open(encoding="utf-8")))          # already ranked by m* asc
    n_active = next((int(r["n_active_zones"]) for r in _csv.DictReader(tf.open(encoding="utf-8"))
                     if r["date"] == as_of), None)
    if n_active is None:
        return None
    return {"n_active": n_active, "total": len(zones), "zones": zones[:max(n_active, 0)][:15]}


def load_watch_triage(scenario: str, n: int = 5):
    """Top-N ranked zones from watch_triage.py (§25, priority=(1−m*)×P), or None if absent."""
    f = ALERTS_DIR / "mosaic_asc" / f"per_zone_triage_{scenario}.json"
    if not f.exists():
        return None
    top = json.loads(f.read_text(encoding="utf-8")).get("top", [])[:n]
    return top or None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return float(2 * R * np.arcsin(np.sqrt(a)))


def load_historical_events(footprint_path: Path):
    """The curated per-AOI historical-damage record (data/inventory/<slug>_historical_events.json,
    source-verified per the CLAUDE.md date/provenance rules), ranked by damage (deaths desc, then
    injured, then the editorial damage_score tie-breaker for non-fatal events). Each event is
    annotated with its CURRENT standing in the alert system: distance to the nearest hazard zone
    and that zone's live parameters — from per_zone_vulnerability.csv (the same source as the
    WHICH ZONES table) when present, else the operational-footprint centroids. Returns None when
    the record is absent (the Past-events tab is simply skipped — never another site's history)."""
    import csv as _csv
    f = INV_DIR / f"{SLUG}_historical_events.json"
    if not f.exists():
        return None
    payload = json.loads(f.read_text(encoding="utf-8"))
    events = payload.get("events", [])
    if not events:
        return None
    events.sort(key=lambda e: (-(e.get("deaths") or 0), -(e.get("injured") or 0),
                               -(e.get("damage_score") or 0)))
    zones = []
    vf = ALERTS_DIR / "per_zone_vulnerability.csv"
    if vf.exists():
        for r in _csv.DictReader(vf.open(encoding="utf-8")):
            zones.append({"lat": float(r["lat"]), "lon": float(r["lon"]),
                          "severity": r.get("severity"), "m_star": r.get("m_star"),
                          "fs_0p40": r.get("fs_0p40"), "creep_mmyr": r.get("creep_mmyr"),
                          "confidence": r.get("detection_confidence")})
    elif footprint_path.exists():
        for z in json.loads(footprint_path.read_text(encoding="utf-8")).get("zones", []):
            lon, lat = z["centroid_lonlat"]
            zones.append({"lat": lat, "lon": lon, "severity": z.get("severity"),
                          "m_star": None, "fs_0p40": z.get("min_fs_any_look"),
                          "creep_mmyr": z.get("strongest_creep_mmyr"), "confidence": None})
    for e in events:
        best = None
        for z in zones:
            d = _haversine_km(e["lat"], e["lon"], z["lat"], z["lon"])
            if best is None or d < best[0]:
                best = (d, z)
        e["nearest_zone_km"] = round(best[0], 2) if best else None
        e["nearest_zone"] = best[1] if best else None
    return {"note": payload.get("note", ""), "updated": payload.get("updated", ""),
            "events": events}


def load_imerg_summary(sfx: str):
    """The sub-daily IMERG gate's season summary (imerg_gate.py), or None — the dashboard
    card is skipped when the check hasn't run for this season (never another season's)."""
    f = RAIN_DIR / f"imerg_gate_summary{sfx}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a corrupt summary must not break the dashboard
        return None


def _imerg_card(im: dict, as_of: str) -> str:
    """The 'sub-daily burst check' card: the same regional I-D curve applied to half-hourly
    GPM IMERG — sharper (30-min bursts) and fresher (~1-day latency) than the daily gate,
    framed honestly as an experimental second opinion with no back-tested operating points."""
    latest, top = im.get("latest") or {}, im.get("top_burst_day") or {}
    counts = im.get("level_counts", {})
    lvl = latest.get("level", "DORMANT")
    chip = (f'<span class="pill" style="background:{LEVEL_COLOR.get(lvl, "#999")}'
            f'{";color:#333" if lvl == "DORMANT" else ""}">{lvl}</span>')
    prov = (' <span style="color:#888">(provisional — the day is still arriving; '
            'E can only rise)</span>' if latest.get("provisional") else "")
    try:
        fresher = (date.fromisoformat(latest["date"]) - date.fromisoformat(as_of)).days
    except (KeyError, ValueError):
        fresher = 0
    fresh_txt = (f" — <b>{fresher} day(s) fresher</b> than the daily gate on this page"
                 if fresher > 0 else "")
    burst_txt = (f' · best burst {latest.get("burst_mm")} mm in {latest.get("duration_h")} h'
                 if latest.get("duration_h") else "")
    top_txt = (f'{top.get("date", "—")}: <b>{top.get("burst_mm")} mm in '
               f'{top.get("duration_h")} h</b> (E={top.get("max_E")})' if top else "—")
    return f"""  <div class="card">
    <h2>WHEN — sub-daily burst check <span style="font-weight:400;font-size:12px">(GPM IMERG ·
      experimental)</span></h2>
    <div class="sub2">A second, independent rain sensor: half-hourly satellite rainfall (GPM
      IMERG) screened against the SAME regional danger curve, but at short durations (30 min –
      24 h). It catches the short, localised cloudbursts that a daily average dilutes — and it
      runs only ~1 day behind real time. The two gates are complementary: long soaking wet
      spells register on the daily gate; sharp bursts register here.</div>
    <div class="big">E = {latest.get("max_E", "?")} {chip}</div>
    <div style="font-size:13px;color:#444">newest satellite day <b>{latest.get("date", "?")}</b>{fresh_txt}{prov}{burst_txt}</div>
    <p style="font-size:13px;margin:8px 0 2px"><b>Season by this lens:</b>
      {counts.get("ALERT", 0)} ALERT-grade · {counts.get("WATCH", 0)} WATCH-grade burst days
      (of {im.get("season", {}).get("days", "?")}). Biggest burst — {top_txt}.</p>
    <p style="font-size:12px;color:#888;margin:6px 0 0">Experimental second opinion: the
      validated alarm above remains the daily gate — this arm's thresholds are not yet
      back-tested. Satellite rain is a ~11 km pixel average (a slope-scale burst can still
      read low), it carries no snowmelt, and the newest day is provisional until complete.</p>
  </div>"""


def alarm_level(E: np.ndarray, watch_k: float, alert_k: float) -> list[str]:
    out = []
    for e in E:
        out.append("ALERT" if e >= alert_k else "WATCH" if e >= watch_k else "DORMANT")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(RAIN_DIR / f"{SLUG}_era5land_daily.csv"))
    ap.add_argument("--threshold", choices=sorted(THRESHOLDS), default="nwhimalaya",
                    help="Temporal I-D curve (default: nwhimalaya — the regional gate).")
    ap.add_argument("--footprint", default=str(ALERTS_DIR / "mosaic_asc" / "alerts_operational.json"),
                    help="The validated operational m=0.50 ALERT union product (§16e/§21).")
    ap.add_argument("--watch-footprint", default=str(ALERTS_DIR / "mosaic_asc" / "alerts_watch.json"),
                    help="The higher-recall m=0.70 WATCH union product (§23); shown as a 2nd tier "
                         "if present (pass a missing path to hide it).")
    ap.add_argument("--inventory", default=str(INVENTORY))
    ap.add_argument("--watch-k", type=float, default=1.0, help="E to ARM the footprint (WATCH).")
    ap.add_argument("--alert-k", type=float, default=2.0, help="E to RAISE the alarm (ALERT).")
    ap.add_argument("--window-days", type=int, default=10)
    ap.add_argument("--as-of", default=None,
                    help="Dashboard 'current state' date YYYY-MM-DD (default: the season peak-E day).")
    ap.add_argument("--out-suffix", default="")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"Missing rainfall CSV {csv_path} — run fetch_rainfall.py first.")
    thr = THRESHOLDS[args.threshold]
    a, b = thr["a"], thr["b"]
    rain_source = "CHIRPS (gauge)" if "chirps" in csv_path.name.lower() else "ERA5-Land"

    dates, rain, snowmelt, _tmin, _tmax = load_daily(csv_path)
    water = np.nan_to_num(rain) + np.nan_to_num(snowmelt)
    E, win_D = peak_exceedance(water, a, b)
    api = antecedent_index(water)
    levels = alarm_level(E, args.watch_k, args.alert_k)

    alert_tier = load_tier(Path(args.footprint), required=True)
    watch_tier = load_tier(Path(args.watch_footprint))   # 2nd tier (§23); None if absent
    if watch_tier:                                        # ranked "read first" top-N (§25), if present
        watch_tier["triage_top"] = load_watch_triage(watch_tier["scenario"], 5)
    n_zones, n_crit, n_multi = alert_tier["n_zones"], alert_tier["n_crit"], alert_tier["n_multi"]

    # Selectivity: raw regional trigger (E>=1) vs the gated WATCH/ALERT sets.
    n_raw = int((E >= 1.0).sum())
    counts = {lv: levels.count(lv) for lv in LEVELS}
    n_watch_plus = counts["WATCH"] + counts["ALERT"]
    alert_idx = [i for i, lv in enumerate(levels) if lv == "ALERT"]
    watch_plus_dates = [dates[i] for i, lv in enumerate(levels) if lv in ("WATCH", "ALERT")]
    alert_dates = [dates[i] for i in alert_idx]

    # Temporal coincidence: each documented dated event vs nearest ALERT / nearest WATCH+ day.
    # No inventory for this AOI yet -> no event panel (never score another site's events).
    inv_path = Path(args.inventory)
    events = documented_events(inv_path) if inv_path.exists() else []
    per_event = []
    for name, ev in events:
        d_alert = nearest_alert_delta(ev, alert_dates)
        d_watch = nearest_alert_delta(ev, watch_plus_dates)
        per_event.append({
            "name": name, "date": ev.isoformat(),
            "E_on_day": round(float(E[dates.index(ev)]), 2) if ev in dates else None,
            "nearest_alert_delta_days": d_alert,
            "nearest_watch_or_alert_delta_days": d_watch,
            "alarm_within_window": bool(d_watch is not None and d_watch <= args.window_days),
            "alert_within_window": bool(d_alert is not None and d_alert <= args.window_days),
        })
    n_caught_alarm = sum(e["alarm_within_window"] for e in per_event)
    n_caught_alert = sum(e["alert_within_window"] for e in per_event)

    report = {
        "footprint": str(Path(args.footprint).name),
        "footprint_zones": n_zones, "footprint_critical": n_crit, "footprint_multilook": n_multi,
        "rain_source": rain_source, "threshold_id": args.threshold,
        "threshold": f"{thr['label']} I={a}*D^-{b}",
        "watch_k": args.watch_k, "alert_k": args.alert_k,
        "season": {"start": dates[0].isoformat(), "end": dates[-1].isoformat(), "days": len(dates)},
        "raw_regional_trigger_days": n_raw,
        "raw_pct_season": round(100.0 * n_raw / len(dates), 1),
        "level_counts": counts,
        "watch_or_alert_days": n_watch_plus,
        "watch_or_alert_pct_season": round(100.0 * n_watch_plus / len(dates), 1),
        "alert_days": [dates[i].isoformat() for i in alert_idx],
        "alert_pct_season": round(100.0 * counts["ALERT"] / len(dates), 1),
        "selectivity_gain_raw_to_alert": f"{n_raw} -> {counts['ALERT']} days "
                                         f"({n_raw / max(counts['ALERT'], 1):.1f}x fewer)",
        "window_days": args.window_days,
        "events_caught_by_alarm": f"{n_caught_alarm}/{len(events)}",
        "events_caught_by_alert": f"{n_caught_alert}/{len(events)}",
        "per_event": per_event,
    }
    RAIN_DIR.mkdir(parents=True, exist_ok=True)
    sfx = args.out_suffix
    (RAIN_DIR / f"operational_alarm_report{sfx}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    write_calendar(RAIN_DIR / f"operational_alarm_calendar{sfx}.csv",
                   dates, water, E, win_D, levels, n_zones)
    write_md(RAIN_DIR / f"operational_alarm_report{sfx}.md", report)
    fig_path = RAIN_DIR / f"operational_alarm{sfx}.png"
    make_figure(fig_path, dates, E, levels, events, args.watch_k, args.alert_k)

    # "Current state" as-of a date: default to the season peak-E day (the strongest alarm).
    if args.as_of:
        as_of_i = dates.index(date.fromisoformat(args.as_of))
    else:
        as_of_i = int(np.argmax(E))
    # Per-zone ranking (§19) — render the live ranked zone list if per_zone_gate.py has run.
    per_zone = per_zone_live(ALERTS_DIR, dates[as_of_i].isoformat())
    # Curated historical-damage record — the Past-events tab (skipped when the site has none).
    hist = load_historical_events(Path(args.footprint))
    # Sub-daily IMERG second opinion (imerg_gate.py) — card skipped when absent.
    imerg = load_imerg_summary(sfx)
    write_dashboard(ALERTS_DIR / "mosaic_asc" / f"operational_alarm_dashboard{sfx}.html",
                    report, dates, E, levels, as_of_i, fig_path, alert_tier, watch_tier, per_zone,
                    hist, imerg)
    if imerg and imerg.get("latest"):
        il = imerg["latest"]
        print(f"IMERG sub-daily check: latest {il['date']} E={il['max_E']} ({il['level']}); "
              f"season ALERT-grade burst days: {imerg['level_counts'].get('ALERT', 0)}")
    if hist:
        n_rev = sum(1 for e in hist["events"] if e.get("review_needed"))
        print(f"PAST EVENTS tab: {len(hist['events'])} documented events "
              f"({n_rev} flagged pending review)")

    print(f"WHERE — ALERT ({alert_tier['scenario']} m={alert_tier['m']}): {n_zones} zones "
          f"({n_crit} critical, {n_multi} >=2-look, AUC {_auc_txt(alert_tier['auc'])})")
    if watch_tier:
        print(f"WHERE — WATCH ({watch_tier['scenario']} m={watch_tier['m']}): {watch_tier['n_zones']} zones "
              f"(recall {watch_tier['recall']}@2km, AUC {_auc_txt(watch_tier['auc'])}; "
              f">=2-look core AUC {_auc_txt(watch_tier['core_auc'])})")
    print(f"temporal gate: {thr['label']} on {rain_source}; watch_k={args.watch_k} alert_k={args.alert_k}")
    print(f"  raw regional trigger (E>=1): {n_raw}/{len(dates)} days ({report['raw_pct_season']}%)")
    print(f"  GATED: WATCH+={n_watch_plus} ({report['watch_or_alert_pct_season']}%)  "
          f"ALERT={counts['ALERT']} ({report['alert_pct_season']}%)  "
          f"-> {report['selectivity_gain_raw_to_alert']}")
    print(f"  ALERT day(s): {', '.join(report['alert_days']) or 'none'}")
    print(f"  documented events caught: by ALARM(WATCH+) {n_caught_alarm}/{len(events)}, "
          f"by ALERT {n_caught_alert}/{len(events)} (+/-{args.window_days} d)")
    for e in per_event:
        print(f"    {e['date']} {e['name'][:24]:24s} E={e['E_on_day']}  "
              f"nearest ALERT Δ={e['nearest_alert_delta_days']}  WATCH+ Δ="
              f"{e['nearest_watch_or_alert_delta_days']}")
    print(f"  -> {RAIN_DIR / f'operational_alarm_report{sfx}.json'} , .md , "
          f"operational_alarm_calendar{sfx}.csv , operational_alarm{sfx}.png")
    print(f"  -> dashboard (as-of {dates[as_of_i].isoformat()}, {levels[as_of_i]}): "
          f"{ALERTS_DIR / 'mosaic_asc' / f'operational_alarm_dashboard{sfx}.html'}")
    return 0


def write_calendar(path: Path, dates, water, E, win_D, levels, n_zones) -> None:
    lines = ["date,water_mm,exceedance_E,won_duration_d,alarm_level,n_live_zones"]
    for d, w, e, wd, lv in zip(dates, water, E, win_D, levels):
        live = n_zones if lv in ("WATCH", "ALERT") else 0
        lines.append(f"{d.isoformat()},{w:.2f},{e:.3f},{wd},{lv},{live}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_md(path: Path, r: dict) -> None:
    lines = [
        f"# Operational alarm — regional curve (WHEN) x validated footprint (WHERE)", "",
        f"**Footprint (WHERE):** the operational m=0.50 union product — **{r['footprint_zones']} zones** "
        f"({r['footprint_critical']} critical, {r['footprint_multilook']} >=2-look), the map that beats "
        f"chance (§16d/§16e).",
        f"**Temporal gate (WHEN):** {r['threshold']} on {r['rain_source']}, graded by the peak I-D "
        f"exceedance E(t); `watch_k={r['watch_k']}`, `alert_k={r['alert_k']}`.",
        "",
        "## Selectivity — the gate fixes the regional curve's over-firing",
        f"- Raw regional trigger (E>=1): **{r['raw_regional_trigger_days']}/{r['season']['days']} days** "
        f"({r['raw_pct_season']}% of season) — too sensitive to be operational.",
        f"- Gated **WATCH+** (footprint armed): **{r['watch_or_alert_days']} days** "
        f"({r['watch_or_alert_pct_season']}%).",
        f"- Gated **ALERT** (alarm raised): **{r['level_counts']['ALERT']} days** "
        f"({r['alert_pct_season']}%) — **{r['selectivity_gain_raw_to_alert']}**.",
        f"- ALERT day(s): {', '.join(r['alert_days']) or 'none'}.",
        "",
        "## Temporal validation — do ALERT days coincide with documented failures?",
        f"- Caught by ALARM (WATCH+): **{r['events_caught_by_alarm']}**; by ALERT: "
        f"**{r['events_caught_by_alert']}** (within +/-{r['window_days']} d).",
        "",
        "| documented event | date | E on day | nearest ALERT Δd | nearest WATCH+ Δd | caught |",
        "|---|---|---|---|---|---|",
    ]
    for e in r["per_event"]:
        lines.append(f"| {e['name']} | {e['date']} | {e['E_on_day']} | "
                     f"{e['nearest_alert_delta_days']} | {e['nearest_watch_or_alert_delta_days']} | "
                     f"{'ALERT' if e['alert_within_window'] else 'WATCH+' if e['alarm_within_window'] else '—'} |")
    lines += ["",
              "## Honest scope",
              "- AOI-mean rain gives ONE E per day, so the gate is AOI-wide on/off; sub-daily/point rain "
              "(IMERG) would let it vary per zone. The footprint is FIXED at the validated operational map "
              "— we do NOT balloon it to the worst-case monsoon map on wet days (that is what over-flagged, "
              "§16b).",
              "- The regional curve is a LOWER BOUND; the E grading converts 'is it raining enough?' into "
              "'how far above the line?', which is what restores selectivity (§12c).",
              "- 20 Apr 2025 is the verified deadly cloudburst (§12g); 27 Apr / 8 May sit only just above "
              "the regional line on reanalysis rain (low E), so they land in WATCH, not ALERT — the honest "
              "sensitivity/selectivity bind documented in §12c (gauge/sub-daily rain would raise their E)."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _auc_txt(v) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".") if isinstance(v, (int, float)) else "n/a"


def _conf_cell(v) -> str:
    """A color-coded detection-confidence (§24) table cell: green ≥0.9, amber ≥0.7, grey below."""
    try:
        p = float(v)
    except (TypeError, ValueError):
        return "<td>—</td>"
    color = "#1a8a4a" if p >= 0.9 else "#b8860b" if p >= 0.7 else "#999"
    return f"<td><b style='color:{color}'>{p:.2f}</b></td>"


def _gmaps(lat, lon, decimals: int = 4) -> str:
    """A lat, lon rendered as a click-to-open Google Maps link (satellite view of the spot)."""
    lat, lon = float(lat), float(lon)
    return (f'<a href="https://www.google.com/maps?q={lat:.5f},{lon:.5f}" target="_blank" '
            f'title="Open this location in Google Maps">{lat:.{decimals}f}, {lon:.{decimals}f}</a>')


def _aoi_tabs(dash_name: str) -> str:
    """Site-switcher tabs (one per registry AOI, sorted) with each site's latest alarm
    level collated from its season alarm calendar. The current site is highlighted;
    a sibling site gets a RELATIVE link (../../alerts<sfx>/mosaic_asc/…) only when its
    same-season dashboard actually exists — otherwise the tab renders greyed with a
    hint, so there are never dead links."""
    import csv as _csv
    import re as _re
    import yaml as _yaml
    sfx_now = dash_name[len("operational_alarm_dashboard"):-len(".html")]
    m = _re.search(r"_(\d{4})$", sfx_now)
    year = m.group(1) if m else None
    tabs = []
    for cfg_path in sorted((PROJECT_ROOT / "config").glob("*.yaml")):
        slug = cfg_path.stem
        sfx = "" if slug == "ramban" else f"_{slug}"
        try:
            site = str(_yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
                       .get("site_name") or slug.title())
        except Exception:  # noqa: BLE001 — a bad registry file must not break the dashboard
            site = slug.title()
        cal = RAIN_DIR / (f"operational_alarm_calendar{sfx}_{year}.csv" if year
                          else f"operational_alarm_calendar{sfx}.csv")
        level = None
        if cal.exists():
            rows = list(_csv.DictReader(cal.open(encoding="utf-8")))
            if rows:
                level = rows[-1].get("alarm_level")
        dot = (f'<span style="display:inline-block;width:9px;height:9px;border-radius:50%;'
               f'background:{LEVEL_COLOR.get(level, "#9aa0a6")};margin-right:6px" '
               f'title="latest alarm level: {level or "unknown"}"></span>')
        label = f"{dot}{site}" + (
            f' <span style="opacity:.75;font-size:11px">{level}</span>' if level else "")
        if slug == SLUG:
            tabs.append(f'<span class="tab active" style="cursor:default">{label}</span>')
            continue
        target_name = (f"operational_alarm_dashboard{sfx}_{year}.html" if year
                       else f"operational_alarm_dashboard{sfx}.html")
        target = PROJECT_ROOT / "data" / f"alerts{sfx}" / "mosaic_asc" / target_name
        if target.exists():
            tabs.append(f'<a class="tab" style="text-decoration:none" '
                        f'href="../../alerts{sfx}/mosaic_asc/{target_name}" '
                        f'title="Open the {site} dashboard for this season">{label}</a>')
        else:
            tabs.append(f'<span class="tab" style="opacity:.45;cursor:default" '
                        f'title="No {site} dashboard generated for this season yet">{label}</span>')
    return ('<span style="margin-left:auto;display:flex;gap:8px;align-items:center;flex-wrap:wrap">'
            '<span style="color:rgba(255,255,255,.7);font-size:12px">Sites:</span>'
            + "".join(tabs) + "</span>")


def _stack_links(scenario: str) -> str:
    """Per-stack map links for a tier's scenario (operational -> dashboard_operational.html, etc.).
    Links whichever per-stack dashboards actually exist for THIS site (the stack set differs
    per AOI — hardcoding ramban's trio put dead links on other sites' dashboards)."""
    stacks = sorted(p.parent.name for p in ALERTS_DIR.glob(f"*/dashboard_{scenario}.html")
                    if p.parent.name != "mosaic_asc" and not p.parent.name.endswith("_vslope"))
    return "\n".join(
        f'<li><a href="../{s}/dashboard_{scenario}.html">{s.replace("ASC_", "")}</a></li>'
        for s in stacks)


def _tier_card(tier: dict, role: str, compare_recall=None) -> str:
    """One WHERE tier card — ALERT (precise / act-now) or WATCH (wider / higher-recall, §23).
    Zone counts + scored metrics (AUC, recall, lift, >=2-look core) come from load_tier (read
    from the back-test reports), never hard-coded."""
    m = tier.get("m")
    m_txt = f"saturation m={m:.2f}" if isinstance(m, (int, float)) else "saturation n/a"
    rec = tier.get("recall")
    rec_txt = f"{rec:.2f}" if isinstance(rec, (int, float)) else "n/a"
    auc_txt = _auc_txt(tier.get("auc"))
    ci = tier.get("auc_ci")
    if isinstance(ci, (list, tuple)) and len(ci) == 2:
        auc_txt += f" [{ci[0]:.2f}–{ci[1]:.2f}]"  # 95% bootstrap CI (§44)
    triage = ""
    unscored = not isinstance(tier.get("auc"), (int, float))
    if role == "ALERT":
        title = ("WHERE — ALERT footprint (act now)" if unscored else
                 "WHERE — ALERT footprint (act now · the map that beats chance)")
        subtitle = ("The short, high-confidence list: slopes that are already creeping (measured "
                    "from satellite radar) AND are physically fragile. When the alarm is WATCH or "
                    "ALERT, these are the places to check first.")
        if unscored:
            # No back-test at this site yet — never borrow another AOI's validation claims.
            scored = ("<b>Not yet back-tested at this site</b> (no local landslide "
                      "inventory) — the footprint inherits the framework's validation, "
                      "not its own score. Held FIXED — the rainfall gate changes only "
                      "the alarm STATE, not the map.")
        else:
            lift250 = tier.get("lift250")
            lift_txt = (f", <b>{lift250:.0f}× better than luck @250 m</b>"
                        if isinstance(lift250, (int, float)) else "")
            p = tier.get("p_perm")
            p_txt = (f", p={p:.4f}" if isinstance(p, (int, float)) else "")
            scored = (f"Scored vs the GSI field-validated inventory (random-luck control): "
                      f"<b>AUC {auc_txt}</b> (beats chance{p_txt}), recall <b>{rec_txt}</b>@2 km{lift_txt}. "
                      f"Held FIXED — the rainfall gate changes only the alarm STATE, not the map.")
    else:
        title = "WHERE — WATCH footprint (monitor wider · higher recall)"
        subtitle = ("The wider monitoring net: catches more of the real failures at the cost of more "
                    "false positives. Use it to plan patrols and monitoring — act on the ALERT list.")
        ratio = (f" (≈{rec / compare_recall:.1f}× the ALERT recall)"
                 if isinstance(rec, (int, float)) and compare_recall else "")
        cz, ca, cl = tier.get("core_zones"), tier.get("core_auc"), tier.get("core_lift")
        core = ""
        if isinstance(ca, (int, float)):
            cl_txt = f", lift {cl:.2f}×@2 km" if isinstance(cl, (int, float)) else ""
            core = (f" Its <b>≥2-look core</b> ({cz} zones) still beats chance: "
                    f"<b>AUC {_auc_txt(ca)}</b>{cl_txt}.")
        if unscored:
            scored = ("<b>Not yet back-tested at this site</b> — a deliberately wider "
                      "monitoring net. Monitor these; act on the ALERT footprint.")
        else:
            scored = (f"Recall <b>{rec_txt}</b>@2 km{ratio}, at lower precision "
                      f"(AUC {auc_txt}, ≈chance overall).{core} Monitor these; act on the ALERT core.")
        top = tier.get("triage_top")
        if top:
            items = "\n".join(
                f"<li>{_gmaps(z['lat'], z['lon'], 3)} — <b>{z['priority']}</b> "
                f"<span style='color:#888'>(fragile m*{z['m_star']} · P{z['detection_confidence']}"
                f"{' · 2-look' if z.get('n_looks', 1) >= 2 else ''})</span></li>"
                for z in top)
            triage = (f"<div style='margin-top:8px;font-size:12px'><b>Read first — top {len(top)} by "
                      f"triage priority (§25, ranked not gated):</b>"
                      f"<ol style='margin:4px 0 0 18px;padding:0'>{items}</ol>"
                      f"<div style='color:#888;margin-top:3px'>priority = (1−m*)×P = fragility × "
                      f"detection confidence; full ranking in <code>per_zone_triage_watch.csv</code>.</div></div>")
    links = _stack_links(tier["scenario"])
    links_html = (f'<div style="font-size:13px;margin-top:6px"><b>Zoom in</b> — interactive '
                  f'per-stack maps (one per radar viewing geometry):</div>'
                  f'<ul style="font-size:13px;margin:4px 0 0 18px">{links}</ul>') if links else ""
    return f"""  <div class="card">
    <h2>{title}</h2>
    <div class="sub2">{subtitle}</div>
    <div class="big">{tier['n_zones']} zones</div>
    <div style="font-size:13px;color:#444">{tier['n_crit']} critical · {tier['n_multi']} multi-look-confirmed · {m_txt}</div>
    <p style="font-size:13px">{scored} <a href="#" onclick="showTab('guide');return false"
      style="font-size:12px;white-space:nowrap">what do these scores mean? →</a></p>
    {links_html}
    {triage}
  </div>"""


HIST_CONF_COLOR = {"VERIFIED": "#1a8a4a", "HIGH": "#1a5fb4", "MEDIUM": "#b8860b", "LOW": "#dc2828"}


def _hist_today_cell(e) -> str:
    """One event's CURRENT standing vs the alert system: distance to the nearest hazard zone and
    that zone's live parameters (m*, FS@0.40, creep, detection confidence — whichever exist)."""
    z, km = e.get("nearest_zone"), e.get("nearest_zone_km")
    if z is None:
        return "<td><span style='color:#888'>no zone data at this site yet</span></td>"
    d_txt = f"{km * 1000:.0f} m" if km < 1 else f"{km:.1f} km"
    parts = []
    if z.get("m_star"):
        parts.append(f"m* {z['m_star']}")
    if z.get("fs_0p40") not in (None, ""):
        try:
            parts.append(f"FS@0.40 {float(z['fs_0p40']):.2f}")
        except (TypeError, ValueError):
            pass
    if z.get("creep_mmyr") not in (None, ""):
        parts.append(f"creep {z['creep_mmyr']} mm/yr")
    if z.get("confidence"):
        parts.append(f"P {z['confidence']}")
    sev = z.get("severity") or "zone"
    sev_html = f"<b style='color:#aa0000'>CRITICAL</b>" if sev == "CRITICAL" else sev
    if km <= 2.0:
        return (f"<td><b>{d_txt}</b> to nearest hazard zone ({sev_html})"
                f"<br><span style='color:#666'>{' · '.join(parts)}</span></td>")
    return (f"<td><span style='color:#888'>outside today's mapped footprint "
            f"(nearest zone {d_txt} away)</span></td>")


def _hist_panel(hist, lvl, as_of) -> str:
    """The Past-events tab body: the site's documented landslide-damage history ranked by damage,
    each row source-cited with a confidence badge (LOW = pending review, never settled fact) and
    its current standing against the live alert system."""
    rows = []
    n_review = sum(1 for e in hist["events"] if e.get("review_needed"))
    for i, e in enumerate(hist["events"], 1):
        deaths, injured = e.get("deaths"), e.get("injured")
        if deaths is None and injured is None:
            cas = "<span style='color:#888' title='the source records casualties but not a count'>not stated</span>"
        else:
            bits = []
            if deaths is not None:
                bits.append(f"<b>{deaths}</b> dead" if deaths else "0 dead")
            if injured:
                bits.append(f"{injured} injured")
            cas = " · ".join(bits)
        date_txt = e.get("date") or f"<span style='color:#888'>{e.get('date_note', 'date unknown')}</span>"
        conf = e.get("confidence", "LOW")
        badge = (f"<span class='pill' style='background:{HIST_CONF_COLOR.get(conf, '#999')}' "
                 f"title=\"{e.get('confidence_reason', '')}\">{conf}</span>")
        if e.get("review_needed"):
            badge += "<br><span style='font-size:11px;color:#dc2828'>pending review</span>"
        srcs = []
        for j, s in enumerate(e.get("sources", []), 1):
            if s.get("url"):
                srcs.append(f"<a href=\"{s['url']}\" target=\"_blank\" title=\"{s['label']}\">[{j}]</a>")
            else:
                srcs.append(f"<span title=\"{s['label']}\" style='cursor:help;color:#666'>[{j}]</span>")
        rows.append(
            f"<tr><td>{i}</td><td><b>{e['name']}</b></td><td>{date_txt}</td>"
            f"<td>{_gmaps(e['lat'], e['lon'])}</td><td>{cas}</td>"
            f"<td style='max-width:340px'>{e['damage']}</td>"
            f"{_hist_today_cell(e)}<td>{badge}</td><td>{' '.join(srcs)}</td></tr>")
    review_note = (f" <b>{n_review} row(s) are LOW/flagged confidence and pending review</b> — "
                   f"treat them as leads, not settled fact." if n_review else "")
    return f"""
<div class="wrap">
  <div class="card" style="flex:1 1 100%">
    <h2>Past landslide events at this site — ranked by damage caused</h2>
    <div class="sub2">Documented history, worst first (deaths, then injuries, then infrastructure
      damage). Every row is source-verified — hover a confidence badge for how solid the record is,
      and the numbered brackets for the sources (linked where the source is online).{review_note}
      The <b>today at this location</b> column places each historical site against the CURRENT
      alert system (alarm <b>{lvl}</b> as of {as_of}): how far it sits from the nearest mapped
      hazard zone and that zone's live parameters. Click any coordinate to open the exact spot in
      Google Maps.</div>
    <table><tr><th>#</th><th>event</th><th>date</th>
      <th title='Click to open the exact spot in Google Maps'>location (lat, lon)</th>
      <th>casualties</th><th>damage</th>
      <th title='Distance from this historical location to the nearest zone in the CURRENT hazard footprint, with that zone&#39;s live parameters (m* = wetness at which it fails, FS = factor of safety, creep = measured motion, P = detection confidence)'>today at this location</th>
      <th title='How solid the historical record is: VERIFIED = primary source (GSI/peer-reviewed), HIGH = 2+ independent outlets or primary-corroborated, MEDIUM = single outlet or a flagged inconsistency, LOW = pending user review'>confidence</th>
      <th>sources</th></tr>
{chr(10).join(rows)}</table>
    <div style='font-size:12px;color:#666;margin-top:6px'>A historical location sitting
      <i>outside</i> today's footprint is NOT evidence it is safe — the footprint only covers
      slopes where radar kept coherence AND physics says fragile (an unmeasured slope is not a
      safe slope). Conversely, a nearby zone does not mean the old failure will repeat there.</div>
    <details style='font-size:12px;color:#666;margin-top:8px'>
      <summary style='cursor:pointer'>Provenance &amp; verification rules for this record
        (updated {hist['updated']})</summary>
      <p style='margin:6px 0 0'>{hist['note']}</p>
    </details>
  </div>
</div>"""


def write_dashboard(path: Path, r: dict, dates, E, levels, as_of_i: int, fig_path: Path,
                    alert_tier: dict, watch_tier=None, per_zone=None, hist=None,
                    imerg=None) -> None:
    """Self-contained operational warning dashboard: the WHERE (two-tier hazard footprint —
    ALERT + WATCH, §23) x WHEN (temporal alarm) x WHICH ZONES (per-zone ranking, §19) in one
    view, with a 'current state' banner as-of a chosen day."""
    lvl = levels[as_of_i]
    color = LEVEL_COLOR[lvl]
    as_of = dates[as_of_i].isoformat()
    e_now = float(E[as_of_i])
    n_zones = r["footprint_zones"]
    # Live-zone count: the per-zone-gated count (§19) if available, else the whole footprint on WATCH+.
    live = per_zone["n_active"] if per_zone else (n_zones if lvl in ("WATCH", "ALERT") else 0)
    blurb = {"ALERT": "Recent rainfall is WELL ABOVE the level that has historically triggered "
                      "landslides in this region — raise the alarm: restrict exposure below the "
                      "ALERT-footprint slopes and prioritise the live-zone list below.",
             "WATCH": "Recent rainfall has crossed the level that has historically triggered "
                      "landslides in this region — the hazard maps are armed: monitor the live-zone "
                      "list below and brief field teams, but this is not yet an act-now alarm.",
             "DORMANT": "Recent rainfall is below the regional landslide-triggering level — the "
                        "slopes still creep, but there is no active rainfall trigger today."}[lvl]
    # Site-specific honest caveats for the footer/guide (never wear another site's notes).
    if SLUG == "ramban":
        site_notes = ("20 Apr 2025 is the verified deadly cloudburst; 27 Apr / 8 May reach only WATCH "
                      "on reanalysis rain (their cells are sub-grid). Velocity coverage ~14% of AOI "
                      "(unmeasured ≠ safe); soil φ=36° site-calibrated, cohesion a matric-suction "
                      "dry/wet split (§20, lab-unconfirmed).")
    else:
        # Vaishno Devi (the only non-ramban site today): φ/c corroborated by site literature
        # (Kumar & Anbalagan 2013 + GSI overburden ranges, ledger §37) but not lab-confirmed.
        site_notes = ("Soil strength (φ, cohesion) sits within this site's published literature "
                      "ranges (project ledger §37) but is not yet confirmed by on-site lab testing; "
                      "radar velocity covers only part of the AOI (an unmeasured slope is NOT a "
                      "safe slope).")
    png_b64 = base64.b64encode(fig_path.read_bytes()).decode("ascii")

    ev_rows = "\n".join(
        f"<tr><td>{e['name']}</td><td>{e['date']}</td>"
        f"<td>{e['E_on_day'] if e['E_on_day'] is not None else '<span style=color:#888>before this season&#39;s data window</span>'}</td>"
        f"<td>{'<b style=color:#aa0000>ALERT</b>' if e['alert_within_window'] else ('WATCH+' if e['alarm_within_window'] else '—')}</td></tr>"
        for e in r["per_event"])

    where_cards = _tier_card(alert_tier, "ALERT")
    if watch_tier:
        where_cards += "\n" + _tier_card(watch_tier, "WATCH", compare_recall=alert_tier.get("recall"))

    hist_btn = ('<button id="btn-hist" class="tab" onclick="showTab(\'hist\')">'
                '🕰 Past events</button>' if hist else "")
    hist_div = (f'<div id="tab-hist" style="display:none">{_hist_panel(hist, lvl, as_of)}</div>'
                if hist else "")

    per_zone_html = ""
    if per_zone is not None:
        if per_zone["zones"]:
            tier_badge = {"fails-when-barely-wet": "#dc2828", "fails-on-a-wet-day": "#f0b428",
                          "fails-only-when-very-wet": "#8aa1b1"}
            zrows = "\n".join(
                f"<tr><td>{i}</td><td>{_gmaps(z['lat'], z['lon'])}</td>"
                f"<td>{z['m_star']}</td><td>{z['fs_0p40']}</td><td>{z['creep_mmyr']}</td>"
                f"{_conf_cell(z.get('detection_confidence'))}"
                f"<td>{'<b style=color:#aa0000>CRITICAL</b>' if z['severity']=='CRITICAL' else 'HIGH'}</td>"
                f"<td><span class='pill' style='background:{tier_badge.get(z['tier'],'#999')}'>{z['tier']}</span></td></tr>"
                for i, z in enumerate(per_zone["zones"], 1))
            body = (f"<table><tr><th>#</th>"
                    f"<th title='Click a coordinate to open the exact spot in Google Maps'>location (lat, lon)</th>"
                    f"<th title='Soil wetness at which THIS zone crosses its failure line (0 = bone dry, 1 = fully soaked). Lower = more fragile.'>m* (fails at)</th>"
                    f"<th title='Factor of Safety at moderate wetness (0.40): resisting forces ÷ driving forces. Below 1.0 = the physics says unstable.'>FS@0.40</th>"
                    f"<th title='Measured ground-motion speed from satellite radar (along its line of sight). These slopes are moving today, rain or not.'>creep mm/yr</th>"
                    f"<th title='Probability the measured creep is real motion rather than radar noise (green ≥ 0.9, amber ≥ 0.7).'>confidence</th>"
                    f"<th title='CRITICAL = worst physics combined with fastest creep.'>severity</th>"
                    f"<th title='How wet a day it takes to tip this zone (from its m*).'>vulnerability</th></tr>"
                    f"{zrows}</table>"
                    f"<div style='font-size:12px;color:#666;margin-top:6px'>m* = soil saturation at which the "
                    f"zone crosses failure (lower = fails when barely wet); <b>confidence</b> = P the creep is "
                    f"real vs the velocity noise floor (§24). Showing the {len(per_zone['zones'])} "
                    f"most vulnerable of {per_zone['n_active']} active; full ranking in "
                    f"<code>per_zone_vulnerability.csv</code> (§19).</div>")
        else:
            body = ("<p style='font-size:13px;color:#666'>No zones live — the regional gate is DORMANT "
                    "today (rainfall below the danger line), so no zone has been activated.</p>")
        per_zone_html = f"""
<div class="wrap">
  <div class="card" style="flex:1 1 100%">
    <h2>WHICH ZONES — live as of {as_of} &nbsp;<span style="font-weight:400;color:#666">
      ({per_zone['n_active']} of {per_zone['total']} operational zones active, ranked by vulnerability)</span></h2>
    <div class="sub2">Today's working checklist: a zone is "live" when the soil is estimated to be wet
      enough to reach ITS OWN tipping point (m* ≤ today's saturation). Most fragile first — click any
      coordinate to open the exact spot in Google Maps, and hover any column header for what it means.</div>
    {body}
  </div>
</div>"""

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<base target="_blank"><!-- every real link (maps, sources, per-stack, sibling sites) opens in a
 new tab so the dashboard is never navigated away; in-page tab switches use href="#" with
 onclick return-false and are unaffected -->
<title>{SITE} — Landslide Decision Support (research prototype)</title>
<meta property="og:type" content="website">
<meta property="og:title" content="{SITE} — InSAR Landslide Decision Support (research prototype)">
<meta property="og:description" content="Decision-support prioritization prototype: satellite-radar
 slope creep × slope physics × a rainfall gate rank WHERE slopes deserve inspection and WHEN
 vigilance should rise. Static snapshot as of {as_of}. Not a warning system — it does not predict
 individual landslides, and no safety decision should rest on it.">
<meta name="twitter:card" content="summary">
<!-- After hosting, add absolute URLs: <meta property="og:url" content="..."> and
     <meta property="og:image" content="..."> (og:image cannot be a data: URI). -->
<style>
 body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f5f7;color:#1c1c1e}}
 header{{background:#0d1b2a;color:#fff;padding:16px 24px}}
 header h1{{margin:0;font-size:20px}} header .sub{{opacity:.85;font-size:13px;margin-top:4px}}
 .tabs{{background:#13263a;padding:8px 24px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
 .tab{{background:transparent;border:1px solid rgba(255,255,255,.35);color:#fff;padding:6px 14px;
   border-radius:6px;font-size:13px;cursor:pointer}}
 .tab.active{{background:#fff;color:#0d1b2a;font-weight:600}}
 .banner{{margin:18px 24px;padding:18px 22px;border-radius:8px;color:#fff;background:{color};
   box-shadow:0 2px 6px rgba(0,0,0,.2)}}
 .banner .lvl{{font-size:30px;font-weight:800;letter-spacing:1px}}
 .banner .meta{{font-size:14px;margin-top:6px;opacity:.95}}
 .banner a{{color:#fff}}
 .fresh{{margin-top:10px;font-size:12px;padding:4px 10px;border-radius:4px;display:inline-block;
   background:rgba(255,255,255,.18)}}
 .disclaimer{{background:#fff3cd;color:#7a5b00;border-bottom:1px solid #e6cf8b;padding:8px 24px;
   font-size:12px;line-height:1.5}}
 .wrap{{display:flex;gap:18px;padding:0 24px 18px;flex-wrap:wrap}}
 .card{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:14px 16px;flex:1 1 340px;
   min-width:280px;overflow-x:auto}}
 .card h2{{margin:0 0 8px;font-size:15px}} .big{{font-size:26px;font-weight:700}}
 .sub2{{font-size:12px;color:#777;margin:-2px 0 8px;line-height:1.45}}
 table{{border-collapse:collapse;width:100%;font-size:13px;margin-top:6px}}
 th,td{{border:1px solid #e3e3e3;padding:5px 8px;text-align:left}} th{{background:#f0f2f5}}
 .calendar{{margin:0 24px 18px}} .calendar img{{width:100%;max-width:1100px;border:1px solid #ccc;border-radius:6px;background:#fff}}
 .pill{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;color:#fff;margin-right:4px}}
 footer{{padding:12px 24px;font-size:11px;color:#888}}
 a{{color:#1a5fb4}}
 .guide p, .guide li{{font-size:13px;line-height:1.55}}
 .guide h2{{font-size:15px}}
</style></head><body>
<header>
  <h1>🏔️ {SITE} — Landslide Decision Support <span style="font-size:13px;font-weight:400;
   opacity:.8">(prioritization prototype)</span></h1>
  <div class="sub"><b>WHERE</b> (two-tier hazard footprint: ALERT + WATCH) × <b>WHEN</b> (regional rainfall
   gate) × <b>WHICH ZONES</b> (per-zone vulnerability) · season {r['season']['start']} → {r['season']['end']} ·
   generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>
</header>
<nav class="tabs">
  <button id="btn-dash" class="tab active" onclick="showTab('dash')">Dashboard</button>
  {hist_btn}
  <button id="btn-guide" class="tab" onclick="showTab('guide')">📖 Guide — how to read this page</button>
  {_aoi_tabs(path.name)}
</nav>
<div class="disclaimer">⚠️ <b>RESEARCH PROTOTYPE — DECISION SUPPORT, NOT A WARNING SYSTEM.</b> This
 independent satellite-radar (InSAR) research product <b>ranks</b> WHERE slopes deserve inspection and
 WHEN vigilance should rise; it does <b>not predict individual landslides</b>. It is a <b>static
 snapshot</b> (rainfall data lags ~5 days) and is not affiliated with SMVDSB, GSI, NDMA or any
 authority. No safety, travel, or evacuation decision should rest on it — always follow official
 advisories.</div>

<div id="tab-dash">
<div class="banner">
  <div class="lvl">● ALARM: {lvl}</div>
  <div class="meta">as of <b>{as_of}</b> &nbsp;·&nbsp; rainfall exceedance E = <b>{e_now:.2f}×</b>
   the regional danger line &nbsp;·&nbsp; <b>{live}</b> hazard zones live.<br>{blurb}
   &nbsp;<a href="#" onclick="showTab('guide');return false">New here? Open the guide →</a></div>
  <div class="fresh" id="staleness" data-asof="{as_of}">Data current to {as_of}
   (enable JavaScript for a live staleness check).</div>
</div>

<div class="wrap">
{where_cards}
  <div class="card">
    <h2>WHEN — regional rainfall temporal gate</h2>
    <div class="sub2">The maps above say WHERE failures are plausible; this card says WHEN the danger is
      real. Each day's rainfall is compared against a published NW-Himalaya landslide-triggering
      threshold, and the alarm state is graded by how far above it we are (the exceedance E).</div>
    <div class="big">{r['level_counts']['ALERT']} ALERT days <span style="font-size:14px;color:#666">/ season</span></div>
    <div style="font-size:13px;color:#444">{r['alert_pct_season']}% of the season. The raw regional
      threshold alone would have fired on <b>{r['raw_regional_trigger_days']} days</b>; grading by E keeps
      only the {r['level_counts']['ALERT']} day(s) genuinely well above the line —
      <b>{r['selectivity_gain_raw_to_alert'].split('(')[-1].rstrip(')')}</b> alarm days, far less alarm fatigue.</div>
    <p style="font-size:13px;margin-bottom:4px">
      <span class="pill" style="background:#e8e8e8;color:#333">DORMANT E&lt;1</span>
      <span class="pill" style="background:#f0b428">WATCH 1≤E&lt;2</span>
      <span class="pill" style="background:#dc2828">ALERT E≥2</span></p>
    <p style="font-size:13px;margin:6px 0 2px"><b>Validation</b> — documented failures at this site vs the
      gate (caught by ALARM {r['events_caught_by_alarm']}, by ALERT {r['events_caught_by_alert']}):</p>
    <table><tr><th>event</th><th>date</th><th>E</th><th>gate state</th></tr>
{ev_rows}</table>
  </div>
{_imerg_card(imerg, as_of) if imerg else ""}
</div>
{per_zone_html}

<div class="calendar">
  <h2 style="margin:0 24px 6px 0;font-size:15px">Season at a glance — how dangerous was the rain,
    and what did the alarm say?</h2>
  <div class="sub2" style="margin:0 0 8px"><b>Top chart:</b> each blue bar is one day of the season.
    Its height is <b>E</b> — that day's recent rainfall compared with the amount of rain that has
    historically been enough to trigger landslides in this region (<b>E&nbsp;=&nbsp;1</b> means
    exactly at that historical danger line, <b>E&nbsp;=&nbsp;2</b> means twice it). Note this grades
    the <i>rain itself</i> against a proven danger threshold — it is not soil wetness/saturation
    (that is a separate quantity used for the hazard zones). The alarm simply follows E: below the
    line the system stays <b>quiet</b> (grey), above it the hazard maps are <b>armed — WATCH</b>
    (amber), and at E&nbsp;≥&nbsp;2 it raises the <b>ALERT</b> (red). Black vertical lines mark
    documented landslides at this site, so you can see whether they fell on flagged days.
    <b>Bottom strip:</b> the same season as a calendar — one coloured cell per day showing the alarm
    state that day; wide amber or red patches are the dangerous wet spells.</div>
  <img src="data:image/png;base64,{png_b64}" alt="season chart: daily rainfall danger level E and the alarm state calendar"/>
</div>
</div><!-- /tab-dash -->
{hist_div}
<div id="tab-guide" class="guide" style="display:none">
<div class="wrap">
  <div class="card" style="flex:1 1 100%">
    <h2>What is this dashboard?</h2>
    <p>It is a <b>decision-support prioritization view</b> for <b>{SITE}</b> — it ranks where to look
      and when to look harder; it does <b>not</b> predict individual landslides. It is built from two independent
      measurements: <b>satellite radar</b> (InSAR — millimetre-scale ground-motion mapping from orbit,
      which finds slopes that are <i>already creeping</i>) and <b>slope physics</b> (a Factor-of-Safety
      model on the terrain, which finds slopes that are <i>fragile when wet</i>). Where both agree, we
      draw a hazard zone. Rainfall then decides whether those zones are dangerous <i>today</i>.</p>
    <p>The page answers three questions, in order: <b>WHERE</b> could slopes fail (the two map cards) ·
      <b>WHEN</b> is the danger real (the rainfall gate card + the banner) · <b>WHICH ZONES</b> matter
      most right now (the ranked live-zone table).</p>
    <p>Monitoring more than one area? The <b>Sites</b> tabs in the top bar switch between the monitored
      areas — each tab's coloured dot shows that site's latest alarm level at a glance, so you can see
      the state of every site without leaving this page.</p>
  </div>
</div>
<div class="wrap">
  <div class="card">
    <h2>The three alarm states — and what to do</h2>
    <table>
      <tr><th>State</th><th>Meaning</th><th>Suggested action</th></tr>
      <tr><td><b style="color:#888">DORMANT</b></td>
        <td>Rainfall is below the regional landslide-triggering line (E &lt; 1). Slopes still creep,
          but there is no rainfall trigger.</td>
        <td>Routine monitoring only.</td></tr>
      <tr><td><b style="color:#b8860b">WATCH</b></td>
        <td>Rainfall has crossed the triggering line (1 ≤ E &lt; 2). The hazard maps are armed and
          zones start going live.</td>
        <td>Check the live-zone list; brief field teams; take extra care below listed slopes during
          and right after storms.</td></tr>
      <tr><td><b style="color:#dc2828">ALERT</b></td>
        <td>Rainfall is well above the triggering line (E ≥ 2) — the regime in which the region's
          documented failures have happened.</td>
        <td>Act on the ALERT footprint: restrict exposure below those slopes, inspect drainage and
          known cracks, prioritise by the table's ranking.</td></tr>
    </table>
  </div>
  <div class="card">
    <h2>The rainfall number E (exceedance)</h2>
    <p>Published research gives an <b>intensity–duration threshold</b> for the NW Himalaya: how much rain,
      sustained over how long, has historically been enough to trigger landslides. Each day we compare the
      accumulated rain over every window (1 day, 2 days, …) against that line and keep the worst ratio.</p>
    <p><b>E = 1.0</b> means exactly on the historical danger line. <b>E = 2.25</b> means the rain was
      2.25× that line. E grades the alarm: below 1 DORMANT, 1–2 WATCH, 2 and above ALERT. One honest
      limitation: E uses an <i>AOI-average</i> daily value, so a very localised cloudburst can read lower
      than what actually fell on one slope.</p>
  </div>
  <div class="card">
    <h2>Why two maps (ALERT vs WATCH)?</h2>
    <p>Any alert product trades misses against false alarms — so we publish both ends of the dial.
      The <b>ALERT footprint</b> is the precise, act-now list. The <b>WATCH footprint</b> is a wider net
      that catches more of the true failures at the cost of more false positives — right for planning
      patrols, wrong for sirens.</p>
    <p>Both maps are <b>held fixed</b>: rainfall changes only the alarm STATE, never the shapes. This
      stops the map "ballooning" on wet days, which is what over-flags in naive systems. A zone marked
      <b>multi-look-confirmed</b> (≥2-look) was detected independently from two different satellite
      viewing geometries — stronger evidence it is real motion.</p>
  </div>
  <div class="card">
    <h2>Reading the zone table</h2>
    <ul style="margin:4px 0 0 18px;padding:0">
      <li><b>location</b> — click any coordinate to open that exact spot in Google Maps (switch to
        satellite/terrain view to see the slope).</li>
      <li><b>m*</b> — the soil wetness at which THIS zone crosses its failure line (0 = bone dry,
        1 = fully saturated). Lower = more fragile: m* ≈ 0.22 fails on a barely-wet day.</li>
      <li><b>FS@0.40</b> — Factor of Safety at moderate wetness: resisting forces ÷ driving forces.
        Below 1.0 = the physics says unstable.</li>
      <li><b>creep mm/yr</b> — the measured ground motion speed from radar (along the satellite's line
        of sight). Larger magnitude = faster creep; these slopes are moving <i>today</i>, rain or not.</li>
      <li><b>confidence</b> — the probability the measured creep is real motion rather than radar noise
        (<b style="color:#1a8a4a">green ≥ 0.9</b>, <b style="color:#b8860b">amber ≥ 0.7</b>).</li>
      <li><b>severity / vulnerability</b> — CRITICAL combines the worst physics with the fastest creep;
        the vulnerability pill says how wet a day it takes to tip the zone.</li>
    </ul>
  </div>
  <div class="card">
    <h2>Terms at a glance</h2>
    <table>
      <tr><th>Term</th><th>Plain meaning</th></tr>
      <tr><td><b>InSAR</b></td><td>Measuring ground motion down to millimetres by comparing satellite
        radar images taken over the same spot at different times.</td></tr>
      <tr><td><b>creep</b></td><td>Slow, steady downhill movement of a slope (mm per year). A slope
        that creeps is telling you it is already unstable.</td></tr>
      <tr><td><b>hazard zone / footprint</b></td><td>A patch of slope flagged because radar says it is
        <i>already moving</i> AND physics says it is <i>fragile when wet</i>. The "footprint" is the
        full set of zones drawn on the map.</td></tr>
      <tr><td><b>saturation (m)</b></td><td>How wet the soil is assumed to be, from 0 (bone dry) to
        1 (fully soaked).</td></tr>
      <tr><td><b>m*</b></td><td>The wetness at which one specific zone crosses its failure line.
        Lower = touchier: an m* of 0.2 fails on a barely-wet day.</td></tr>
      <tr><td><b>exceedance (E)</b></td><td>Today's rain compared to the historical
        landslide-triggering line: 1 = exactly on the line, 2 = twice it.</td></tr>
      <tr><td><b>multi-look (≥2-look)</b></td><td>The same motion was seen independently from two
        different satellite viewing angles — much harder for noise to fake.</td></tr>
      <tr><td><b>AUC</b></td><td>How well the map separates real landslide locations from random
        spots: 0.5 = a coin flip, 1.0 = perfect.</td></tr>
      <tr><td><b>recall @2 km</b></td><td>Of the documented landslides, the share that had a flagged
        zone within 2 km.</td></tr>
      <tr><td><b>lift</b></td><td>How many times more often the map is near a real landslide than
        pure luck would be, at a given distance.</td></tr>
      <tr><td><b>p (permutation)</b></td><td>The chance a randomly-drawn map would score this well.
        The smaller it is, the harder the result is to explain away as luck.</td></tr>
      <tr><td><b>Factor of Safety (FS)</b></td><td>A slope's resisting forces ÷ driving forces.
        Above 1.0 the slope holds; below 1.0 the physics says it fails.</td></tr>
    </table>
  </div>
  <div class="card">
    <h2>Honest limitations</h2>
    <p>{site_notes}</p>
    <p>The rainfall gate uses ONE AOI-average value per day, so localised cloudbursts can under-read
      (sub-daily, per-zone rainfall is on the roadmap). Radar only measures where the ground stays
      coherent between passes — an unmeasured slope is NOT a safe slope. This dashboard is decision
      support for prioritising attention; it does not replace field judgment or official warnings.</p>
    <p style="color:#888">Full rankings and provenance: <code>per_zone_vulnerability.csv</code>,
      <code>per_zone_triage_watch.csv</code>, and the committed ledger <code>RESULTS_AND_KPIS.md</code>
      (§ references throughout this page point there).</p>
  </div>
  <div class="card">
    <h2>About this project &amp; data credits</h2>
    <p>An independent, end-to-end research prototype: free public satellite data → ground-motion
      measurement → physics-based hazard mapping → explainable, rainfall-gated <b>decision-support
      prioritization</b>. It is a
      <b>portfolio/research demonstration</b>, not an operational service: this page is a static
      snapshot generated on the date in the header, and it is not affiliated with or endorsed by any
      authority responsible for this site.</p>
    <p><b>Data:</b> Contains modified Copernicus Sentinel-1 radar data (2025–26), interferometry
      processed by ASF HyP3 (Alaska Satellite Facility) · rainfall from the Copernicus Climate Change
      Service ERA5-Land reanalysis · terrain from the ALOS PALSAR radiometrically-terrain-corrected
      DEM (© JAXA/METI, via ASF) · documented-landslide records from the Geological Survey of India ·
      route and building context © OpenStreetMap contributors (ODbL).</p>
  </div>
</div>
</div><!-- /tab-guide -->

<footer>Operational MVP · the WHEN gate uses one AOI rainfall value/day; per-zone differentiation is by each
 zone's critical saturation m* (§19), capped at the validated footprint. {site_notes}<br><br>
 <b>Decision-support prioritization prototype — not a warning system.</b> It ranks where to inspect
 and when vigilance should rise; it does not predict individual landslides. Static snapshot; always
 follow official advisories.<br>
 <b>Data &amp; credits:</b> Contains modified Copernicus Sentinel-1 data (2025–26), processed by
 ASF HyP3 (Alaska Satellite Facility) · rainfall: Copernicus Climate Change Service (C3S) ERA5-Land ·
 DEM: ALOS PALSAR RTC © JAXA/METI, via ASF · landslide records: Geological Survey of India (GSI) ·
 route &amp; buildings context: © OpenStreetMap contributors (ODbL) · map links: Google Maps.</footer>
<script>
function showTab(t){{
  for (const k of ['dash', 'hist', 'guide']) {{
    const tab = document.getElementById('tab-' + k), btn = document.getElementById('btn-' + k);
    if (tab) tab.style.display = (t === k) ? '' : 'none';
    if (btn) btn.classList.toggle('active', t === k);
  }}
  window.scrollTo(0, 0);
}}
// Live staleness guard: the page is a static snapshot, so its age is computed against the
// VIEWER's clock at open time. Healthy = the known ~5-day ERA5-Land lag + 2-3-day cycle
// cadence (<=8 d); beyond that the refresh cycle has been missed; beyond 14 d the shown alarm
// state must not be trusted at all.
(function () {{
  var el = document.getElementById('staleness');
  if (!el) return;
  var days = Math.floor((Date.now() - new Date(el.dataset.asof + 'T00:00:00')) / 864e5);
  var msg = 'Data current to ' + el.dataset.asof + ' — ' + days + ' day' +
            (days === 1 ? '' : 's') + ' behind the day you are reading this.';
  if (days > 14) {{
    el.style.background = '#7a0c0c';
    msg = '⚠ STALE SNAPSHOT — ' + msg + ' TREAT THE ALARM STATE AS UNKNOWN: run a refresh ' +
          'cycle (control panel / monsoon_cycle) and follow official advisories.';
  }} else if (days > 8) {{
    el.style.background = '#8a5a00';
    msg = '⚠ ' + msg + ' Beyond the normal data lag + refresh cadence — a refresh cycle has ' +
          'likely been missed; re-run it before acting on this state.';
  }} else {{
    el.style.background = '';
    msg = '🕐 ' + msg + ' Normal for this system (~5-day rainfall-data lag, 2–3-day refresh cadence).';
  }}
  el.textContent = msg;
}})();
</script>
</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def make_figure(path: Path, dates, E, levels, events, watch_k, alert_k) -> None:
    """The season-at-a-glance figure, written for a LAY reader (2026-07-18 readability pass —
    the jargon title/labels confused users into reading E as soil saturation). Panel 1: each
    day's rainfall graded against the region's historical landslide-triggering line; panel 2:
    the resulting alarm-state calendar strip with day counts."""
    x = np.arange(len(dates))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), height_ratios=[3, 1])
    box = dict(facecolor="white", alpha=0.75, edgecolor="none", pad=1.5)

    top = max(E.max() * 1.1, alert_k + 0.6)
    ax1.axhspan(watch_k, alert_k, color="#f0b428", alpha=0.15, lw=0)
    ax1.axhspan(alert_k, top, color="#dc2828", alpha=0.12, lw=0)
    ax1.fill_between(x, 0, E, color="#4477aa", step="mid", lw=0)
    ax1.axhline(watch_k, color="#b8860b", lw=1.2, ls="--")
    ax1.axhline(alert_k, color="#aa0000", lw=1.2, ls="--")
    ax1.set_ylim(0, top)
    # Plain-language band labels (y in data units, x as axes fraction).
    tf = ax1.get_yaxis_transform()
    ax1.text(0.99, (alert_k + top) / 2, "ALERT — rain well above the danger line (E ≥ 2)",
             transform=tf, ha="right", va="center", fontsize=8.5, color="#aa0000", bbox=box)
    ax1.text(0.99, (watch_k + alert_k) / 2, "WATCH — danger line crossed, hazard maps armed (1 ≤ E < 2)",
             transform=tf, ha="right", va="center", fontsize=8.5, color="#8a6500", bbox=box)
    ax1.text(0.99, watch_k * 0.45, "quiet — rain below the danger line",
             transform=tf, ha="right", va="center", fontsize=8.5, color="#666", bbox=box)
    ax1.text(0.01, watch_k, "historical danger line: rain that has triggered landslides in this region before (E = 1)",
             transform=tf, ha="left", va="bottom", fontsize=7.5, color="#8a6500", bbox=box)
    for name, ev in events:
        if ev in dates:
            i = dates.index(ev)
            ax1.axvline(i, color="#222", lw=1.0, alpha=0.7)
            short = name if len(name) <= 26 else name[:26].rsplit(" ", 1)[0] + "…"
            ax1.text(i, top * 0.97, f" {ev.isoformat()} — {short}", rotation=90,
                     fontsize=7, va="top", ha="left", color="#222")
    ax1.set_ylabel("rainfall danger level E\n(recent rain ÷ landslide-triggering rain)")
    ax1.set_title(f"Was the rain dangerous? Each day's rainfall vs the region's historical "
                  f"landslide-triggering threshold ({dates[0].year} season)")
    ax1.grid(alpha=0.3)

    # Panel 2: the season alarm calendar strip (one cell per day, coloured by level).
    rgb = np.array([[int(LEVEL_COLOR[lv][1:3], 16), int(LEVEL_COLOR[lv][3:5], 16),
                     int(LEVEL_COLOR[lv][5:7], 16)] for lv in levels], dtype=np.uint8)
    ax2.imshow(rgb[np.newaxis, :, :], aspect="auto", extent=[0, len(dates), 0, 1])
    ax2.set_yticks([])
    tick = np.linspace(0, len(dates) - 1, 8).astype(int)
    for ax in (ax1, ax2):
        ax.set_xticks(tick)
        ax.set_xlim(0, len(dates))
    ax1.set_xticklabels([])
    ax2.set_xticklabels([dates[i].strftime("%b %d") for i in tick])
    n_d, n_w, n_a = (levels.count(lv) for lv in LEVELS)
    ax2.set_xlabel(f"what the alarm showed each day — grey quiet ({n_d} days) · "
                   f"amber WATCH ({n_w} days) · red ALERT ({n_a} days)")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

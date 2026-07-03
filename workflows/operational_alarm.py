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

from rainfall_id_threshold import THRESHOLDS, SLUG, antecedent_index, load_daily  # noqa: E402
from rainfall_specificity import (  # noqa: E402
    peak_exceedance, documented_events, nearest_alert_delta,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAIN_DIR = PROJECT_ROOT / "data" / "rainfall"
ALERTS_DIR = PROJECT_ROOT / "data" / "alerts"
INV_DIR = PROJECT_ROOT / "data" / "inventory"
INVENTORY = INV_DIR / "ramban_documented_landslides.geojson"

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
    rpt = INV_DIR / f"backtest_{scenario}_report.json"
    if rpt.exists():
        sc = json.loads(rpt.read_text(encoding="utf-8")).get("scored", {})
        ab = sc.get("at_buffer_km", {})
        tier.update(auc=sc.get("auc"), recall=ab.get("tpr"), spec=ab.get("specificity"),
                    lift250=_lift_at(sc.get("roc", []), 0.25))
    core = INV_DIR / f"backtest_{scenario}_2look_report.json"
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
    events = documented_events(Path(args.inventory))
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
    make_figure(fig_path, dates, water, E, levels, events, args.watch_k, args.alert_k, n_zones)

    # "Current state" as-of a date: default to the season peak-E day (the strongest alarm).
    if args.as_of:
        as_of_i = dates.index(date.fromisoformat(args.as_of))
    else:
        as_of_i = int(np.argmax(E))
    # Per-zone ranking (§19) — render the live ranked zone list if per_zone_gate.py has run.
    per_zone = per_zone_live(ALERTS_DIR, dates[as_of_i].isoformat())
    write_dashboard(ALERTS_DIR / "mosaic_asc" / f"operational_alarm_dashboard{sfx}.html",
                    report, dates, E, levels, as_of_i, fig_path, alert_tier, watch_tier, per_zone)

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


def _stack_links(scenario: str) -> str:
    """Per-stack map links for a tier's scenario (operational -> dashboard_operational.html, etc.)."""
    return "\n".join(
        f'<li><a href="../{s}/dashboard_{scenario}.html">{s.replace("ASC_", "")}</a></li>'
        for s in ("ASC_path27_frame106", "ASC_path100_frame102", "ASC_path27_frame101"))


def _tier_card(tier: dict, role: str, compare_recall=None) -> str:
    """One WHERE tier card — ALERT (precise / act-now) or WATCH (wider / higher-recall, §23).
    Zone counts + scored metrics (AUC, recall, lift, >=2-look core) come from load_tier (read
    from the back-test reports), never hard-coded."""
    m = tier.get("m")
    m_txt = f"saturation m={m:.2f}" if isinstance(m, (int, float)) else "saturation n/a"
    rec = tier.get("recall")
    rec_txt = f"{rec:.2f}" if isinstance(rec, (int, float)) else "n/a"
    auc_txt = _auc_txt(tier.get("auc"))
    triage = ""
    if role == "ALERT":
        title = "WHERE — ALERT footprint (act now · the map that beats chance)"
        lift250 = tier.get("lift250")
        lift_txt = (f", <b>{lift250:.0f}× better than luck @250 m</b>"
                    if isinstance(lift250, (int, float)) else "")
        scored = (f"Scored vs the GSI field-validated inventory (random-luck control): "
                  f"<b>AUC {auc_txt}</b> (beats chance), recall <b>{rec_txt}</b>@2 km{lift_txt}. "
                  f"Held FIXED — the rainfall gate changes only the alarm STATE, not the map.")
    else:
        title = "WHERE — WATCH footprint (monitor wider · higher recall)"
        ratio = (f" (≈{rec / compare_recall:.1f}× the ALERT recall)"
                 if isinstance(rec, (int, float)) and compare_recall else "")
        cz, ca, cl = tier.get("core_zones"), tier.get("core_auc"), tier.get("core_lift")
        core = ""
        if isinstance(ca, (int, float)):
            cl_txt = f", lift {cl:.2f}×@2 km" if isinstance(cl, (int, float)) else ""
            core = (f" Its <b>≥2-look core</b> ({cz} zones) still beats chance: "
                    f"<b>AUC {_auc_txt(ca)}</b>{cl_txt}.")
        scored = (f"Recall <b>{rec_txt}</b>@2 km{ratio}, at lower precision "
                  f"(AUC {auc_txt}, ≈chance overall).{core} Monitor these; act on the ALERT core.")
        top = tier.get("triage_top")
        if top:
            items = "\n".join(
                f"<li>{float(z['lat']):.3f}, {float(z['lon']):.3f} — <b>{z['priority']}</b> "
                f"<span style='color:#888'>(fragile m*{z['m_star']} · P{z['detection_confidence']}"
                f"{' · 2-look' if z.get('n_looks', 1) >= 2 else ''})</span></li>"
                for z in top)
            triage = (f"<div style='margin-top:8px;font-size:12px'><b>Read first — top {len(top)} by "
                      f"triage priority (§25, ranked not gated):</b>"
                      f"<ol style='margin:4px 0 0 18px;padding:0'>{items}</ol>"
                      f"<div style='color:#888;margin-top:3px'>priority = (1−m*)×P = fragility × "
                      f"detection confidence; full ranking in <code>per_zone_triage_watch.csv</code>.</div></div>")
    return f"""  <div class="card">
    <h2>{title}</h2>
    <div class="big">{tier['n_zones']} zones</div>
    <div style="font-size:13px;color:#444">{tier['n_crit']} critical · {tier['n_multi']} multi-look-confirmed · {m_txt}</div>
    <p style="font-size:13px">{scored}</p>
    <ul style="font-size:13px;margin:4px 0 0 18px">{_stack_links(tier['scenario'])}</ul>
    {triage}
  </div>"""


def write_dashboard(path: Path, r: dict, dates, E, levels, as_of_i: int, fig_path: Path,
                    alert_tier: dict, watch_tier=None, per_zone=None) -> None:
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
    blurb = {"ALERT": "Rainfall is well above the regional danger line — raise the alarm on the "
                      "validated hazard footprint.",
             "WATCH": "Rainfall has crossed the regional danger line — the hazard footprint is armed; "
                      "monitor.",
             "DORMANT": "Rainfall is below the regional danger line — no active slope-failure alarm."}[lvl]
    png_b64 = base64.b64encode(fig_path.read_bytes()).decode("ascii")

    ev_rows = "\n".join(
        f"<tr><td>{e['name']}</td><td>{e['date']}</td><td>{e['E_on_day']}</td>"
        f"<td>{'<b style=color:#aa0000>ALERT</b>' if e['alert_within_window'] else ('WATCH+' if e['alarm_within_window'] else '—')}</td></tr>"
        for e in r["per_event"])

    where_cards = _tier_card(alert_tier, "ALERT")
    if watch_tier:
        where_cards += "\n" + _tier_card(watch_tier, "WATCH", compare_recall=alert_tier.get("recall"))

    per_zone_html = ""
    if per_zone is not None:
        if per_zone["zones"]:
            tier_badge = {"fails-when-barely-wet": "#dc2828", "fails-on-a-wet-day": "#f0b428",
                          "fails-only-when-very-wet": "#8aa1b1"}
            zrows = "\n".join(
                f"<tr><td>{i}</td><td>{float(z['lat']):.4f}, {float(z['lon']):.4f}</td>"
                f"<td>{z['m_star']}</td><td>{z['fs_0p40']}</td><td>{z['creep_mmyr']}</td>"
                f"{_conf_cell(z.get('detection_confidence'))}"
                f"<td>{'<b style=color:#aa0000>CRITICAL</b>' if z['severity']=='CRITICAL' else 'HIGH'}</td>"
                f"<td><span class='pill' style='background:{tier_badge.get(z['tier'],'#999')}'>{z['tier']}</span></td></tr>"
                for i, z in enumerate(per_zone["zones"], 1))
            body = (f"<table><tr><th>#</th><th>location (lat, lon)</th><th>m* (fails at)</th>"
                    f"<th>FS@0.40</th><th>creep mm/yr</th><th>confidence</th><th>severity</th>"
                    f"<th>vulnerability</th></tr>"
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
    {body}
  </div>
</div>"""

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Ramban NH-44 — Operational Landslide Alarm</title>
<style>
 body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f5f7;color:#1c1c1e}}
 header{{background:#0d1b2a;color:#fff;padding:16px 24px}}
 header h1{{margin:0;font-size:20px}} header .sub{{opacity:.85;font-size:13px;margin-top:4px}}
 .banner{{margin:18px 24px;padding:18px 22px;border-radius:8px;color:#fff;background:{color};
   box-shadow:0 2px 6px rgba(0,0,0,.2)}}
 .banner .lvl{{font-size:30px;font-weight:800;letter-spacing:1px}}
 .banner .meta{{font-size:14px;margin-top:6px;opacity:.95}}
 .wrap{{display:flex;gap:18px;padding:0 24px 18px;flex-wrap:wrap}}
 .card{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:14px 16px;flex:1 1 340px;min-width:320px}}
 .card h2{{margin:0 0 8px;font-size:15px}} .big{{font-size:26px;font-weight:700}}
 table{{border-collapse:collapse;width:100%;font-size:13px;margin-top:6px}}
 th,td{{border:1px solid #e3e3e3;padding:5px 8px;text-align:left}} th{{background:#f0f2f5}}
 .calendar{{margin:0 24px 18px}} .calendar img{{width:100%;max-width:1100px;border:1px solid #ccc;border-radius:6px;background:#fff}}
 .pill{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;color:#fff;margin-right:4px}}
 footer{{padding:12px 24px;font-size:11px;color:#888}}
 a{{color:#1a5fb4}}
</style></head><body>
<header>
  <h1>🏔️ Ramban NH-44 — Operational Landslide Alarm</h1>
  <div class="sub"><b>WHERE</b> (two-tier hazard footprint: ALERT + WATCH) × <b>WHEN</b> (regional rainfall
   gate) × <b>WHICH ZONES</b> (per-zone vulnerability) · season {r['season']['start']} → {r['season']['end']} ·
   generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>
</header>

<div class="banner">
  <div class="lvl">● ALARM: {lvl}</div>
  <div class="meta">as of <b>{as_of}</b> &nbsp;·&nbsp; rainfall exceedance E = <b>{e_now:.2f}×</b>
   the regional danger line &nbsp;·&nbsp; <b>{live}</b> hazard zones live. &nbsp; {blurb}</div>
</div>

<div class="wrap">
{where_cards}
  <div class="card">
    <h2>WHEN — regional rainfall temporal gate</h2>
    <div class="big">{r['level_counts']['ALERT']} ALERT days <span style="font-size:14px;color:#666">/ season</span></div>
    <div style="font-size:13px;color:#444">{r['alert_pct_season']}% of the season — a
      <b>{r['selectivity_gain_raw_to_alert'].split('(')[-1].rstrip(')')}</b> cut vs the raw regional
      trigger ({r['raw_regional_trigger_days']} days).</div>
    <p style="font-size:13px;margin-bottom:4px">
      <span class="pill" style="background:#e8e8e8;color:#333">DORMANT E&lt;1</span>
      <span class="pill" style="background:#f0b428">WATCH 1≤E&lt;2</span>
      <span class="pill" style="background:#dc2828">ALERT E≥2</span></p>
    <p style="font-size:13px;margin:6px 0 2px"><b>Validation</b> — documented failures vs the gate
      (caught by ALARM {r['events_caught_by_alarm']}, by ALERT {r['events_caught_by_alert']}):</p>
    <table><tr><th>event</th><th>date</th><th>E</th><th>gate state</th></tr>
{ev_rows}</table>
  </div>
</div>
{per_zone_html}

<div class="calendar">
  <h2 style="margin:0 24px 6px 0;font-size:15px">Season alarm calendar &amp; rainfall exceedance</h2>
  <img src="data:image/png;base64,{png_b64}" alt="season alarm calendar"/>
</div>

<footer>Operational MVP · the WHEN gate uses one AOI rainfall value/day; per-zone differentiation is by each
 zone's critical saturation m* (§19), capped at the validated footprint. 20 Apr 2025 is the verified deadly
 cloudburst; 27 Apr / 8 May reach only WATCH on reanalysis rain (their cells are sub-grid). Velocity coverage
 ~14% of AOI (unmeasured ≠ safe); soil φ=36° site-calibrated, cohesion a matric-suction dry/wet split (§20, lab-unconfirmed).</footer>
</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def make_figure(path: Path, dates, water, E, levels, events, watch_k, alert_k, n_zones) -> None:
    x = np.arange(len(dates))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), height_ratios=[3, 1])

    # Panel 1: exceedance E with WATCH/ALERT bands + documented events.
    ax1.axhspan(watch_k, alert_k, color="#f0b428", alpha=0.15, lw=0)
    ax1.axhspan(alert_k, max(E.max() * 1.05, alert_k + 0.5), color="#dc2828", alpha=0.12, lw=0)
    ax1.fill_between(x, 0, E, color="#4477aa", step="mid", lw=0)
    ax1.axhline(watch_k, color="#b8860b", lw=1.0, ls="--")
    ax1.axhline(alert_k, color="#aa0000", lw=1.0, ls="--")
    ax1.text(len(dates) - 1, watch_k, " WATCH", va="bottom", ha="right", fontsize=8, color="#8a6500")
    ax1.text(len(dates) - 1, alert_k, " ALERT", va="bottom", ha="right", fontsize=8, color="#aa0000")
    for name, ev in events:
        if ev in dates:
            i = dates.index(ev)
            ax1.axvline(i, color="#222", lw=1.0, alpha=0.7)
            ax1.text(i, ax1.get_ylim()[1] * 0.96, f" {ev.isoformat()}", rotation=90,
                     fontsize=7, va="top", ha="left", color="#222")
    ax1.set_ylabel("peak I-D exceedance E(t)")
    ax1.set_title(f"Operational alarm: regional curve gates the {n_zones}-zone validated footprint "
                  f"(WHEN x WHERE)")
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
    ax2.set_xlabel("season alarm calendar (grey=dormant, amber=watch, red=alert)")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

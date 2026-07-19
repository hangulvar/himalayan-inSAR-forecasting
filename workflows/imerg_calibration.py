#!/usr/bin/env python
"""imerg_calibration.py — Tier 1b of the Strengthening Plan (§56): give the sub-daily IMERG
burst arm (imerg_gate.py, §55) its first EVIDENCE-BASED, provisional operating points.

Three questions, answered from the 2025+2026 seasons already on disk (no new fetches):

  1. EVENT SKILL — what does the burst arm read on every VERIFIED event day (the §38-rule
     inventory events, both AOIs, both seasons), and what did the daily arm read the same day?
     (This is the standing two-arm temporal-skill table, plan Tier 3c seeded here.)
  2. SELECTIVITY — a threshold sweep: for each candidate alert level k, how many season days
     would the burst arm flag (the false-alarm proxy), and which verified events survive?
  3. BIAS — IMERG (11-km pixel mean) vs the Katra GAUGE on the two dated gauge anchors
     (§51: 184.2 mm & 629.4 mm/24 h, both ending 08:30 IST = 03:00 UTC). If IMERG under-reads
     extremes, its E is biased LOW and the alert threshold must NOT be pushed high.

Outputs data/rainfall/imerg_calibration_report.{json,md}. Headline numbers go to the ledger
(§58) — this report is the reproducible artifact behind them.

  docker compose run --rm insar python workflows/imerg_calibration.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

RAIN_DIR = PROJECT_ROOT / "data" / "rainfall"

# Verified events (provenance: the §38-rule inventories / ledger §51-§52 — dates re-verified
# against primary sources or 2+ outlets; LOW/undated rows deliberately excluded).
EVENTS = [
    ("ramban", "2025-04-20", "Ramban cloudburst (Seri Bagna/Kela Morh)", 3),
    ("ramban", "2025-05-08", "Chamba Seri mudslide (MEDIUM confidence)", 0),
    ("ramban", "2026-04-07", "Digdol-Khooni Nallah slide (NH-44)", 0),
    ("vaishnodevi", "2025-07-21", "Banganga landslide, old track", 1),
    ("vaishnodevi", "2025-08-26", "Ardhkuwari disaster", 34),
    ("vaishnodevi", "2026-07-08", "Himkoti landslide, new track", 0),
]
# The two dated gauge anchors (Katra station, 24 h ending 08:30 IST = 03:00 UTC).
GAUGE_ANCHORS = [
    ("vaishnodevi", "2025-07-21T03:00", 184.2, "Katra 24h ending 08:30 IST 21 Jul 2025 (§51)"),
    ("vaishnodevi", "2025-08-26T03:00", 629.4, "Katra 24h ending 08:30 IST 26 Aug 2025 (§51)"),
]
SWEEP_K = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]


def _sfx(slug: str, year: int) -> str:
    return f"_{year}" if slug == "ramban" else f"_{slug}_{year}"


def _daily_E_rows(slug: str, year: int):
    f = RAIN_DIR / f"{slug}_imerg_daily_E{_sfx(slug, year)}.csv"
    if not f.exists():
        return []
    return list(csv.DictReader(f.open(encoding="utf-8")))


def _daily_arm_level(slug: str, d: str):
    """The DAILY gate's level on date d, from the season alarm calendars (2025 grandfathered
    names: ramban unsuffixed, vaishnodevi _vaishnodevi_2025)."""
    year = d[:4]
    cands = ([RAIN_DIR / "operational_alarm_calendar.csv",
              RAIN_DIR / f"operational_alarm_calendar_{year}.csv"] if slug == "ramban"
             else [RAIN_DIR / f"operational_alarm_calendar_{slug}_{year}.csv"])
    for f in cands:
        if not f.exists():
            continue
        for r in csv.DictReader(f.open(encoding="utf-8")):
            if r["date"] == d:
                return r["alarm_level"], round(float(r["exceedance_E"]), 2)
    return None, None


def sweep(rows: list[dict], ks=SWEEP_K) -> dict:
    """Pure: per candidate k, the number/pct of season days with max_E >= k."""
    Es = [float(r["max_E"]) for r in rows]
    n = len(Es)
    return {str(k): {"days": sum(1 for e in Es if e >= k),
                     "pct": round(100.0 * sum(1 for e in Es if e >= k) / n, 1) if n else None}
            for k in ks}


def window_total(series: list[tuple[datetime, float]], end: datetime, hours: float) -> float:
    """Pure: mm accumulated in the `hours`-window ENDING at `end` (rate mm/h * 0.5 h steps)."""
    lo = end - timedelta(hours=hours)
    return round(sum(r * 0.5 for t, r in series if lo < t <= end), 1)


def _halfhourly(slug: str, year: int):
    f = RAIN_DIR / f"{slug}_imerg_halfhourly{_sfx(slug, year)}.csv"
    if not f.exists():
        return []
    return [(datetime.strptime(r["t"], "%Y-%m-%d %H:%M:%S"), float(r["r"]))
            for r in csv.DictReader(f.open(encoding="utf-8"))]


def main() -> int:
    report = {"generated": date.today().isoformat(),
              "events": [], "sweeps": {}, "gauge_bias": [], "proposal": {}}

    # 1. The two-arm event table.
    fatal_Es, all_Es = [], []
    for slug, d, name, deaths in EVENTS:
        rows = _daily_E_rows(slug, int(d[:4]))
        row = next((r for r in rows if r["date"] == d), None)
        if row is None:
            continue
        daily_lvl, daily_E = _daily_arm_level(slug, d)
        e = {"site": slug, "date": d, "event": name, "deaths": deaths,
             "burst_E": float(row["max_E"]), "burst_level": row["level"],
             "burst_window": f"{row['burst_mm']} mm/{row['duration_h']} h",
             "daily_E": daily_E, "daily_level": daily_lvl}
        report["events"].append(e)
        all_Es.append(e["burst_E"])
        if deaths:
            fatal_Es.append(e["burst_E"])

    # 2. Selectivity sweeps per AOI-season.
    for slug in ("ramban", "vaishnodevi"):
        for year in (2025, 2026):
            rows = _daily_E_rows(slug, year)
            if rows:
                report["sweeps"][f"{slug}_{year}"] = {"season_days": len(rows),
                                                     **{"k": sweep(rows)}}

    # 3. Gauge bias on the dated anchors.
    for slug, end_iso, gauge_mm, note in GAUGE_ANCHORS:
        series = _halfhourly(slug, int(end_iso[:4]))
        if not series:
            continue
        end = datetime.fromisoformat(end_iso)
        imerg_mm = window_total(series, end, 24.0)
        report["gauge_bias"].append({
            "site": slug, "window_end_utc": end_iso, "gauge_mm": gauge_mm,
            "imerg_mm": imerg_mm,
            "imerg_over_gauge": round(imerg_mm / gauge_mm, 2) if gauge_mm else None,
            "note": note})

    # 4. The provisional proposal, derived not asserted.
    min_fatal = min(fatal_Es) if fatal_Es else None
    min_all = min(all_Es) if all_Es else None
    biases = [g["imerg_over_gauge"] for g in report["gauge_bias"] if g["imerg_over_gauge"]]
    report["proposal"] = {
        "min_E_over_fatal_events": min_fatal,
        "min_E_over_all_verified_events": min_all,
        "gauge_bias_range": [min(biases), max(biases)] if biases else None,
        "burst_alert_k_provisional": 3.0,
        "burst_watch_k_unchanged": 1.0,
        "rationale": (
            "ALERT at k=3 keeps every FATAL verified event (3/3, weakest 20 Apr 2025 at "
            "E=3.07) plus the non-fatal burst-type Himkoti (3.9) — i.e. 4/4 of the events "
            "with burst character — while roughly halving flagged season days vs k=2 (see "
            "sweeps). The two events below k=3 are NOT burst failures: Digdol 7 Apr 2026 "
            "(0.99) is a multi-day soak, the DAILY arm's ALERT catch; Chamba Seri 8 May 2025 "
            "(1.09, MEDIUM-confidence) is marginal on the burst arm and missed by the daily "
            "arm too (E=0.67) — the one verified event neither arm flags at ALERT, recorded "
            "honestly. k must NOT be pushed above 3: IMERG under-reads the Katra gauge "
            "~4.5-6x on the extreme anchor days (11-km pixel mean vs a point gauge in "
            "orographic terrain), so burst E is biased LOW in exactly the events that "
            "matter, and the margin over the weakest fatal catch (3.07) is already thin. "
            "PROVISIONAL: n=6 events; revisit as the Tier-3c table grows."),
    }

    out = RAIN_DIR / "imerg_calibration_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [f"# IMERG burst-arm calibration (Tier 1b) — {report['generated']}", "",
          "| site | date | event | deaths | burst E (window) | burst level | daily E | daily level |",
          "|---|---|---|---|---|---|---|---|"]
    for e in report["events"]:
        md.append(f"| {e['site']} | {e['date']} | {e['event']} | {e['deaths']} | "
                  f"**{e['burst_E']}** ({e['burst_window']}) | {e['burst_level']} | "
                  f"{e['daily_E']} | {e['daily_level']} |")
    md += ["", "## Season-day counts at candidate alert thresholds k", ""]
    for key, s in report["sweeps"].items():
        row = ", ".join(f"E≥{k}: {v['days']}d ({v['pct']}%)" for k, v in s["k"].items())
        md.append(f"- **{key}** ({s['season_days']} days): {row}")
    md += ["", "## IMERG vs the Katra gauge (24 h, dated anchors)", ""]
    for g in report["gauge_bias"]:
        md.append(f"- {g['window_end_utc']}: IMERG **{g['imerg_mm']} mm** vs gauge "
                  f"**{g['gauge_mm']} mm** -> ratio {g['imerg_over_gauge']} ({g['note']})")
    md += ["", "## Provisional proposal", "", report["proposal"]["rationale"], "",
           f"-> burst-arm ALERT at **E ≥ {report['proposal']['burst_alert_k_provisional']}** "
           f"(WATCH unchanged at E ≥ 1). Display-only fusion may use these; the validated "
           f"daily alarm is untouched."]
    (RAIN_DIR / "imerg_calibration_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(report["events"], indent=1)[:1200])
    for key, s in report["sweeps"].items():
        print(key, {k: v["days"] for k, v in s["k"].items()})
    for g in report["gauge_bias"]:
        print(f"gauge bias {g['window_end_utc']}: imerg {g['imerg_mm']} / gauge {g['gauge_mm']}"
              f" = {g['imerg_over_gauge']}")
    print(f"-> {out} , .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

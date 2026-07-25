#!/usr/bin/env python
"""imerg_calibration.py — Tier 1b of the Strengthening Plan (§56): give the sub-daily IMERG
burst arm (imerg_gate.py, §55) its first EVIDENCE-BASED, provisional operating points.

Four questions, answered from the 2025+2026 seasons already on disk (no new fetches):

  1. EVENT SKILL — what does the burst arm read on every VERIFIED event day (the §38-rule
     inventory events, both AOIs, both seasons), and what did the daily arm read the same day?
     (This is the standing two-arm temporal-skill table, plan Tier 3c seeded here.)
  2. SELECTIVITY — a threshold sweep: for each candidate alert level k, how many season days
     would the burst arm flag (the false-alarm proxy), and which verified events survive?
  3. BIAS — IMERG (11-km pixel mean) vs the Katra GAUGE on the two dated gauge anchors
     (§51: 184.2 mm & 629.4 mm/24 h, both ending 08:30 IST = 03:00 UTC). If IMERG under-reads
     extremes, its E is biased LOW and the alert threshold must NOT be pushed high.
  4. FALSE ALARMS (§63) — the standing blocker to promoting this arm out of "experimental"
     (risk register: "burst arm cries wolf"). Question 2's day-count is only a PROXY: monsoon
     rain arrives in spells, so 11 flagged days can be 3 spells. Here the flagged days are
     clustered into EPISODES (the operational unit — one episode = one time the gate asks for
     a decision), each episode is marked explained/unexplained against the verified events,
     and the SAME measurement is run on the validated daily arm so the two are judged in one
     currency. Reported as a BOUND: the inventory records only fatal/newsworthy failures, so
     an "unexplained" episode is not a proven false alarm — hence a strict (±1 d) and a
     generous (±10 d) window bracket the truth.

Outputs data/rainfall/imerg_calibration_report.{json,md}. Headline numbers go to the ledger
(§58 for Q1-Q3, §63 for Q4) — this report is the reproducible artifact behind them.

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

from imerg_gate import BURST_ALERT_K, BURST_WATCH_K  # noqa: E402 — the shipped operating points

RAIN_DIR = PROJECT_ROOT / "data" / "rainfall"

# Verified events (provenance: the §38-rule inventories / ledger §51-§52 — dates re-verified
# against primary sources or 2+ outlets; LOW/undated rows deliberately excluded).
EVENTS = [
    ("ramban", "2025-04-20", "Ramban cloudburst (Seri Bagna/Kela Morh)", 3),
    ("ramban", "2025-05-08", "Chamba Seri mudslide (MEDIUM confidence)", 0),
    ("ramban", "2026-04-07", "Digdol-Khooni Nallah slide (NH-44 both directions)", 0),
    ("ramban", "2026-07-22", "Gangroo-Ramsu boulder strike (NH-44)", 2),   # §62, 3 outlets
    ("vaishnodevi", "2025-07-21", "Banganga landslide, old track", 1),
    ("vaishnodevi", "2025-08-26", "Ardhkuwari disaster", 34),
    ("vaishnodevi", "2026-07-08", "Himkoti landslide, new track", 0),
]
# Per-event provenance for the Tier-3c temporal-skill table (the one thing not derivable
# from the rainfall records). Keyed by (site, date) so EVENTS' shape stays stable.
PROVENANCE = {
    ("ramban", "2025-04-20"): ("peer-reviewed + multi-outlet (§12g)", "§58"),
    ("ramban", "2025-05-08"): ("single outlet (§51)", "§58"),
    ("ramban", "2026-04-07"): ("user review + 4 dated outlets (§52)", "§58"),
    ("ramban", "2026-07-22"): ("3 outlets, HIGH confidence (§62)", "§62"),
    ("vaishnodevi", "2025-07-21"): ("3+ outlets + gauge anchor (§51)", "§58"),
    ("vaishnodevi", "2025-08-26"): ("GSI primary + press (§51)", "§58"),
    ("vaishnodevi", "2026-07-08"): ("TOI + 5 outlets (§52)", "§58"),
}
# The two dated gauge anchors (Katra station, 24 h ending 08:30 IST = 03:00 UTC).
GAUGE_ANCHORS = [
    ("vaishnodevi", "2025-07-21T03:00", 184.2, "Katra 24h ending 08:30 IST 21 Jul 2025 (§51)"),
    ("vaishnodevi", "2025-08-26T03:00", 629.4, "Katra 24h ending 08:30 IST 26 Aug 2025 (§51)"),
]
# 2.4 is not a round number: it is the largest k that still reaches ALERT on the weakest FATAL
# event on record (Gangroo-Ramsu 22 Jul 2026, E=2.44) — the live candidate §63 has to price.
SWEEP_K = [1.0, 1.5, 2.0, 2.4, 3.0, 4.0, 5.0, 6.0, 8.0]

# --- Q4: false-alarm measurement (§63) ---------------------------------------
# An EPISODE is the operational unit: consecutive flagged days, merging spells separated by at
# most EPISODE_GAP_D quiet days (one monsoon spell with a one-day lull is one decision, not two).
EPISODE_GAP_D = 1
# The inventory records only fatal/newsworthy failures, so "unexplained" is not "false". A strict
# and a generous attribution window bracket the truth: the strict count is the UPPER bound on
# false alarms, the generous count the LOWER bound.
FA_WINDOWS_D = [1, 10]
SEASONS = [("ramban", 2025), ("ramban", 2026), ("vaishnodevi", 2025), ("vaishnodevi", 2026)]


def _sfx(slug: str, year: int) -> str:
    return f"_{year}" if slug == "ramban" else f"_{slug}_{year}"


def _daily_E_rows(slug: str, year: int):
    f = RAIN_DIR / f"{slug}_imerg_daily_E{_sfx(slug, year)}.csv"
    if not f.exists():
        return []
    return list(csv.DictReader(f.open(encoding="utf-8")))


def _daily_arm_rows(slug: str, year) -> list[dict]:
    """The DAILY gate's season calendar rows (2025 grandfathered names: ramban unsuffixed,
    vaishnodevi _vaishnodevi_2025)."""
    cands = ([RAIN_DIR / "operational_alarm_calendar.csv",
              RAIN_DIR / f"operational_alarm_calendar_{year}.csv"] if slug == "ramban"
             else [RAIN_DIR / f"operational_alarm_calendar_{slug}_{year}.csv"])
    rows = []
    for f in cands:
        if f.exists():
            # Ramban's 2025 calendar is the grandfathered unsuffixed name, so both candidates
            # are read — keep only the requested season's rows.
            rows += [r for r in csv.DictReader(f.open(encoding="utf-8"))
                     if r["date"].startswith(str(year))]
    return rows


def _daily_arm_level(slug: str, d: str):
    """The DAILY gate's level on date d; (None, None) when the season record does not reach
    that day (ERA5-Land publication latency — a pending verdict, not a miss)."""
    for r in _daily_arm_rows(slug, d[:4]):
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


# ---------------------------------------------------------------------------
# Q4 — episode-level false-alarm measurement (§63). All pure: unit-testable.
# ---------------------------------------------------------------------------
_LEVEL_RANK = {"DORMANT": 0, "WATCH": 1, "ALERT": 2}


def burst_level(E: float, alert_k: float = BURST_ALERT_K,
                watch_k: float = BURST_WATCH_K) -> str:
    """Pure: the burst arm's grade for a day's peak exceedance (mirrors imerg_gate)."""
    return "ALERT" if E >= alert_k else "WATCH" if E >= watch_k else "DORMANT"


def episodes(flag_dates: list[date], gap_d: int = EPISODE_GAP_D) -> list[tuple[date, date]]:
    """Pure: flagged days -> [(start, end)] maximal spells, merging runs separated by at most
    `gap_d` unflagged days."""
    spells: list[list[date]] = []
    for d in sorted(set(flag_dates)):
        if spells and (d - spells[-1][1]).days <= gap_d + 1:
            spells[-1][1] = d
        else:
            spells.append([d, d])
    return [(s, e) for s, e in spells]


def false_alarm_profile(day_levels: list[tuple[date, str]], event_dates: list[date],
                        min_level: str, window_d: int) -> dict:
    """Pure: how often does this arm ask for a decision, and how many of those asks are
    attributable to a verified event?

    `day_levels` is one season of (date, level); an episode is 'explained' when a verified
    event falls inside it or within `window_d` days of either end.

    Events OUTSIDE the record's span are excluded from the event tally: an arm whose season
    record stops before an event (ERA5-Land publication latency, §62) has a *pending* verdict
    on it, which is neither a catch nor a miss. They are counted separately.
    """
    rank = _LEVEL_RANK[min_level]
    flags = [d for d, lv in day_levels if _LEVEL_RANK.get(lv, 0) >= rank]
    eps = episodes(flags)
    w = timedelta(days=window_d)
    n_explained = sum(1 for s, e in eps if any(s - w <= ev <= e + w for ev in event_dates))

    span_lo, span_hi = day_levels[0][0], day_levels[-1][0]
    in_span = [ev for ev in event_dates if span_lo <= ev <= span_hi]
    n_caught = sum(1 for ev in in_span
                   if any(abs((ev - f).days) <= window_d for f in flags))
    lengths = sorted((e - s).days + 1 for s, e in eps)
    n = len(day_levels)
    return {
        "n_days": n,
        "n_flagged_days": len(flags),
        "pct_season": round(100.0 * len(flags) / n, 1) if n else None,
        "n_episodes": len(eps),
        "n_episodes_explained": n_explained,
        "n_episodes_unexplained": len(eps) - n_explained,
        "flagged_days_in_longest_episode": lengths[-1] if lengths else 0,
        "n_events": len(in_span),
        "n_events_caught": n_caught,
        "n_events_outside_record": len(event_dates) - len(in_span),
    }


def _burst_day_levels(slug: str, year: int, alert_k: float = BURST_ALERT_K):
    """(date, level) per season day. Provisional days (an incomplete half-hourly record biases
    E low) are dropped so they can neither manufacture nor mask an alarm."""
    return [(date.fromisoformat(r["date"]), burst_level(float(r["max_E"]), alert_k))
            for r in _daily_E_rows(slug, year) if r["provisional"] != "True"]


def _daily_day_levels(slug: str, year: int):
    return [(date.fromisoformat(r["date"]), r["alarm_level"])
            for r in _daily_arm_rows(slug, year)]


def _events_in(slug: str, year: int) -> list[date]:
    return [date.fromisoformat(d) for s, d, _n, _k in EVENTS
            if s == slug and d.startswith(str(year))]


def _pool(profiles: list[dict]) -> dict:
    """Sum per-season profiles into one pooled view + the per-100-day rate."""
    keys = ("n_days", "n_flagged_days", "n_episodes", "n_episodes_explained",
            "n_episodes_unexplained", "n_events", "n_events_caught",
            "n_events_outside_record")
    tot = {k: sum(p[k] for p in profiles) for k in keys}
    n = tot["n_days"]
    tot["pct_season"] = round(100.0 * tot["n_flagged_days"] / n, 1) if n else None
    tot["unexplained_episodes_per_100d"] = (
        round(100.0 * tot["n_episodes_unexplained"] / n, 2) if n else None)
    # How much of the alarm burden sits in one unbroken spell — the difference between an
    # acute gate (many short asks) and a chronic one (few asks, but months-long).
    tot["longest_episode_days"] = max((p["flagged_days_in_longest_episode"]
                                       for p in profiles), default=0)
    tot["mean_episode_days"] = (round(tot["n_flagged_days"] / tot["n_episodes"], 1)
                                if tot["n_episodes"] else None)
    return tot


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


def nearest_burst_alert_delta(slug: str, event_iso: str,
                              horizon_d: int = max(FA_WINDOWS_D)) -> int | None:
    """Signed days from the event to the nearest burst-arm ALERT day (negative = the ALERT came
    first) — the arm's LEAD TIME on that event. None when no ALERT falls within `horizon_d`;
    beyond that the nearest ALERT is an unrelated storm, not a lead time."""
    ev = date.fromisoformat(event_iso)
    deltas = [(d - ev).days for d, lv in _burst_day_levels(slug, ev.year) if lv == "ALERT"]
    near = [d for d in deltas if abs(d) <= horizon_d]
    return min(near, key=abs) if near else None


def temporal_skill_rows(events: list[dict]) -> list[dict]:
    """Tier-3c table (§60/3c) — DERIVED from the same records as the rest of this report so it
    can never drift from them (it was hand-maintained until §63, and the 22 Jul 2026 event
    silently never landed in it).

    `caught_at_alert_by` is the Δ=0 verdict. 'pending' means the daily arm's season record does
    not reach the event day (ERA5-Land latency) — an unknown verdict, not a miss.
    """
    rows = []
    for e in events:
        burst_alert = e["burst_level"] == "ALERT"
        daily_known = e["daily_level"] is not None
        daily_alert = e["daily_level"] == "ALERT"
        if not daily_known:
            caught = "burst" if burst_alert else "pending"
        elif burst_alert and daily_alert:
            caught = "both"
        else:
            caught = "burst" if burst_alert else "daily" if daily_alert else "neither"
        verified_by, ref = PROVENANCE.get((e["site"], e["date"]), ("", ""))
        delta = nearest_burst_alert_delta(e["site"], e["date"])
        rows.append({
            "site": e["site"], "date": e["date"], "event": e["event"], "deaths": e["deaths"],
            "verified_by": verified_by,
            "burst_E": f"{e['burst_E']:.2f}", "burst_level": e["burst_level"],
            "daily_E": "" if e["daily_E"] is None else f"{e['daily_E']:.2f}",
            "daily_level": "PENDING" if not daily_known else e["daily_level"],
            "caught_at_alert_by": caught,
            "delta_days": "0" if caught not in ("neither", "pending") else "",
            "burst_alert_lead_days": "" if delta is None else str(delta),
            "ledger_ref": ref,
        })
    return rows


def write_temporal_skill_table(rows: list[dict]) -> Path:
    out = PROJECT_ROOT / "data" / "inventory" / "temporal_skill_table.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return out


def false_alarm_section() -> dict:
    """Q4 (§63): both arms measured on the same yardstick, plus the burst arm's k-sweep.

    Per-arm numbers are pooled over the four AOI-seasons on disk. Each arm is scored on its
    OWN record length (the daily arm's 2026 season stops ~5 days short — ERA5-Land latency),
    so rates are reported per 100 days to stay comparable.
    """
    arms = {}
    for name, levels_fn in (("burst_imerg", _burst_day_levels),
                            ("daily_era5land", _daily_day_levels)):
        per_window = {}
        for w in FA_WINDOWS_D:
            per_level = {}
            for lvl in ("WATCH", "ALERT"):
                profiles, seasons = [], {}
                for slug, year in SEASONS:
                    dl = levels_fn(slug, year)
                    if not dl:
                        continue
                    p = false_alarm_profile(dl, _events_in(slug, year), lvl, w)
                    p["span"] = f"{dl[0][0].isoformat()}..{dl[-1][0].isoformat()}"
                    seasons[f"{slug}_{year}"] = p
                    profiles.append(p)
                per_level[lvl] = {**_pool(profiles), "by_season": seasons}
            per_window[f"pm{w}d"] = per_level
        arms[name] = per_window

    # The operating-point picker: unexplained-episode rate vs event recall, per candidate k.
    sweep_rows = []
    for k in SWEEP_K:
        for w in FA_WINDOWS_D:
            profiles = []
            for slug, year in SEASONS:
                dl = _burst_day_levels(slug, year, alert_k=k)
                if dl:
                    profiles.append(false_alarm_profile(dl, _events_in(slug, year), "ALERT", w))
            sweep_rows.append({"k": k, "window_d": w, **_pool(profiles)})

    return {
        "method": (
            "Flagged days are clustered into EPISODES (consecutive days, merging spells "
            f"separated by <= {EPISODE_GAP_D} quiet day) — one episode is one operational "
            "decision. An episode is EXPLAINED if a verified event falls in it or within the "
            "attribution window. Provisional IMERG days are dropped."),
        "honest_limit": (
            "The inventory records only fatal/newsworthy failures over two AOIs, so an "
            "unexplained episode is NOT a proven false alarm — many will be real rain that "
            "moved ground nobody reported. The strict (+/-1 d) count is therefore an UPPER "
            "bound on the false-alarm rate and the generous (+/-10 d) count a LOWER bound; "
            "the true rate lies between. Both arms carry the same bias, which is why the "
            "burst arm is only compared to the validated daily arm, never scored in absolute "
            "terms."),
        "episode_gap_days": EPISODE_GAP_D,
        "attribution_windows_d": FA_WINDOWS_D,
        "arms": arms,
        "burst_k_sweep": sweep_rows,
    }


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

    # 4. FALSE ALARMS (§63) — episodes, not days, and the same yardstick on both arms.
    report["false_alarms"] = false_alarm_section()
    skill_csv = write_temporal_skill_table(temporal_skill_rows(report["events"]))

    # 5. The provisional proposal, derived not asserted.
    min_fatal = min(fatal_Es) if fatal_Es else None
    min_all = min(all_Es) if all_Es else None
    n_fatal_at_k = sum(1 for e in report["events"]
                       if e["deaths"] and e["burst_E"] >= BURST_ALERT_K)
    n_fatal = sum(1 for e in report["events"] if e["deaths"])
    biases = [g["imerg_over_gauge"] for g in report["gauge_bias"] if g["imerg_over_gauge"]]
    report["proposal"] = {
        "min_E_over_fatal_events": min_fatal,
        "min_E_over_all_verified_events": min_all,
        "gauge_bias_range": [min(biases), max(biases)] if biases else None,
        "burst_alert_k_provisional": BURST_ALERT_K,
        "burst_watch_k_unchanged": BURST_WATCH_K,
        "fatal_events_at_alert_k_same_day": f"{n_fatal_at_k}/{n_fatal}",
        "rationale": (
            f"ALERT at k={BURST_ALERT_K:g} flags {n_fatal_at_k}/{n_fatal} FATAL verified "
            f"events ON THE DAY (weakest same-day catch 20 Apr 2025 at E=3.07) plus the "
            "non-fatal burst-type Himkoti (3.9), while roughly halving flagged season days "
            "vs k=2 (see sweeps). The events below k=3 are NOT all burst failures: Digdol "
            "7 Apr 2026 (0.99) is a multi-day soak, the DAILY arm's ALERT catch; Chamba Seri "
            "8 May 2025 (1.09, MEDIUM-confidence) is marginal on the burst arm and missed by "
            "the daily arm too (E=0.67) — the one verified event neither arm flags at ALERT, "
            "recorded honestly. NEW (§63) — Gangroo-Ramsu 22 Jul 2026 (2 deaths) reads only "
            "E=2.44 (WATCH) on the day, the first FATAL event this arm does not reach ALERT "
            "on at Δ=0: it was flagged ALERT four days earlier (18 Jul, E=3.05) and held "
            "WATCH continuously through the strike, so the arm was live but its same-day "
            "fatal floor is now 2.44, not 3.07. k must NOT be pushed above 3: IMERG "
            "under-reads the Katra gauge ~4.5-6x on the extreme anchor days (11-km pixel "
            "mean vs a point gauge in orographic terrain), so burst E is biased LOW in "
            "exactly the events that matter. Whether to LOWER k to ~2.4 is a live question — "
            "the false-alarm section prices that move. PROVISIONAL: n="
            f"{len(report['events'])} events; revisit as the Tier-3c table grows."),
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
    md += _false_alarm_md(report["false_alarms"])
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
    print("\n=== Q4 false alarms — episodes, both arms, same yardstick ===")
    for arm, per_window in report["false_alarms"]["arms"].items():
        for wkey, per_level in per_window.items():
            for lvl, p in per_level.items():
                print(f"  {arm:15s} {lvl:5s} {wkey:5s}  {p['n_flagged_days']:3d}d "
                      f"({p['pct_season']:4.1f}%) in {p['n_episodes']:2d} episodes "
                      f"(mean {p['mean_episode_days']}d, longest {p['longest_episode_days']}d) "
                      f"-> {p['n_episodes_unexplained']:2d} unexplained "
                      f"({p['unexplained_episodes_per_100d']}/100d), events "
                      f"{p['n_events_caught']}/{p['n_events']}"
                      + (f" (+{p['n_events_outside_record']} pending)"
                         if p["n_events_outside_record"] else ""))
    print(f"-> {out} , .md , {skill_csv}")
    return 0


def _false_alarm_md(fa: dict) -> list[str]:
    md = ["", "## Q4 — false alarms: episodes, not days (§63)", "", fa["method"], "",
          f"_{fa['honest_limit']}_", "",
          "| arm | level | window | flagged days | % season | episodes | mean / longest ep (d) "
          "| unexplained | per 100 d | events caught |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for arm, per_window in fa["arms"].items():
        for wkey, per_level in per_window.items():
            for lvl, p in per_level.items():
                pend = (f" (+{p['n_events_outside_record']} pending)"
                        if p["n_events_outside_record"] else "")
                md.append(f"| {arm} | {lvl} | ±{wkey[2:-1]} d | {p['n_flagged_days']} | "
                          f"{p['pct_season']} | {p['n_episodes']} | "
                          f"{p['mean_episode_days']} / {p['longest_episode_days']} | "
                          f"**{p['n_episodes_unexplained']}** | "
                          f"{p['unexplained_episodes_per_100d']} | "
                          f"{p['n_events_caught']}/{p['n_events']}{pend} |")
    md += ["", "### Burst-arm operating-point picker (ALERT at k)", "",
           "| k | window | ALERT days | episodes | unexplained | per 100 d | events caught |",
           "|---|---|---|---|---|---|---|"]
    for r in fa["burst_k_sweep"]:
        md.append(f"| {r['k']:g} | ±{r['window_d']} d | {r['n_flagged_days']} | "
                  f"{r['n_episodes']} | {r['n_episodes_unexplained']} | "
                  f"{r['unexplained_episodes_per_100d']} | "
                  f"{r['n_events_caught']}/{r['n_events']} |")
    return md


if __name__ == "__main__":
    raise SystemExit(main())

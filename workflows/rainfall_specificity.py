#!/usr/bin/env python
"""rainfall_specificity.py — restore SELECTIVITY to the (very sensitive) regional I-D trigger.

THE PROBLEM (RESULTS_AND_KPIS.md §12): the regional NW-Himalaya I-D curve catches both documented
spring 2025 events (back-test 0/2 -> 2/2) but fires on 112/214 days — sensitive, not selective. A
trigger that flags half the season cannot be operational.

THE FILTER: an I-D curve is a LOWER BOUND (below it, slides are rare); ABOVE it, how *far* above
matters. Rank each day by its peak I-D exceedance ratio
    E(t) = max over durations D of [ cum_D(t) / threshold_cum(D) ]
E>=1 == the binary regional trigger fires. A real cloudburst sits far above the line (26 Aug E~7x)
while routine monsoon rain barely crosses it (E~1.1x). Two INDEPENDENT specificity dials:
  * stringency k     : alert only if E >= k          (k=1 == the raw regional trigger)
  * antecedent floor : alert only if the antecedent wetness API is ALSO high — a second axis,
                       physically the "already-wet" condition (Shah et al. 2024 use ~53 mm/20 d on NH-44).

We SWEEP each dial and report the SENSITIVITY (are the documented 27 Apr / 8 May events still within
+/-W days of an alert day?) vs SELECTIVITY (how few days / % of season are flagged) trade-off — an
honest ROC-like view, scored against the inventory's dated events.

EXPECTED on ERA5-Land: you cannot be BOTH selective AND catch the spring bursts, because their
reanalysis rain is too small — which is the quantitative case for the CHIRPS gauge product. This is a
PROTOTYPE of the operating-point picker; re-run on data/rainfall/ramban_chirps_daily.csv once GEE auth
is done to see whether gauge rain opens a selective-and-sensitive window.

  docker compose run --rm insar python workflows/rainfall_specificity.py \
      --csv data/rainfall/ramban_era5land_daily.csv --threshold nwhimalaya
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from rainfall_id_threshold import (  # shared helpers — single source of truth
    THRESHOLDS, DEFAULT_THRESHOLD, DURATIONS_D, SLUG,
    load_daily, rolling_sum, antecedent_index, threshold_cumulative,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAIN_DIR = PROJECT_ROOT / "data" / "rainfall"
INVENTORY = PROJECT_ROOT / "data" / "inventory" / "ramban_documented_landslides.geojson"

K_SWEEP = [1.0, 1.5, 2.0, 3.0, 5.0]        # stringency multiples of the regional lower bound
API_Q_SWEEP = [0, 50, 75, 90]              # antecedent-wetness percentile floors (0 = off)
WINDOW_D = 10                              # +/- days for an event to count as "caught"


def peak_exceedance(water: np.ndarray, a: float, b: float):
    """E(t) = max_D cum_D(t)/threshold_cum(D), plus which duration won (for context)."""
    n = len(water)
    E = np.zeros(n)
    win_D = np.zeros(n, dtype=int)
    for D in DURATIONS_D:
        ratio = rolling_sum(water, D) / threshold_cumulative(D, a, b)
        ratio = np.nan_to_num(ratio, nan=0.0)
        better = ratio > E
        E[better] = ratio[better]
        win_D[better] = D
    return E, win_D


def documented_events(path: Path):
    """[(name, date)] for inventory features carrying a 'date'."""
    gj = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for f in gj["features"]:
        p = f.get("properties", {})
        if p.get("date"):
            out.append((p.get("name", "?"), date.fromisoformat(p["date"])))
    return out


def nearest_alert_delta(event: date, alert_dates: list[date]):
    return min((abs((event - d).days) for d in alert_dates), default=None)


def score(alert_mask, dates, events):
    """Selectivity (#/% season flagged) + sensitivity (per-event nearest-alert delta / caught)."""
    alert_dates = [dates[i] for i in np.where(alert_mask)[0]]
    per_event = []
    for name, ev in events:
        d = nearest_alert_delta(ev, alert_dates)
        per_event.append({"name": name, "date": ev.isoformat(),
                          "nearest_alert_delta_days": d,
                          "caught": bool(d is not None and d <= WINDOW_D)})
    return {
        "n_alert_days": int(alert_mask.sum()),
        "pct_season": round(100.0 * alert_mask.sum() / len(dates), 1),
        "n_events_caught": sum(e["caught"] for e in per_event),
        "n_events": len(events),
        "per_event": per_event,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(RAIN_DIR / f"{SLUG}_era5land_daily.csv"))
    ap.add_argument("--threshold", choices=sorted(THRESHOLDS), default="nwhimalaya",
                    help="Base I-D curve to make selective (default: nwhimalaya — the over-sensitive one).")
    ap.add_argument("--inventory", default=str(INVENTORY))
    ap.add_argument("--out-suffix", default="")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"Missing rainfall CSV: {csv_path} — run fetch_rainfall.py / fetch_chirps.py first.")
    thr = THRESHOLDS[args.threshold]
    a, b = thr["a"], thr["b"]
    rain_source = "CHIRPS (gauge)" if "chirps" in csv_path.name.lower() else "ERA5-Land"

    dates, rain, snowmelt, _tmin, _tmax = load_daily(csv_path)
    water = np.nan_to_num(rain) + np.nan_to_num(snowmelt)
    E, win_D = peak_exceedance(water, a, b)
    api = antecedent_index(water)
    events = documented_events(Path(args.inventory))

    # --- Dial 1: stringency k (antecedent off) ---
    k_rows = [{"k": k, "equiv_1day_mm": round(k * threshold_cumulative(1, a, b), 1),
               **score(E >= k, dates, events)} for k in K_SWEEP]
    # --- Dial 2: antecedent floor (at k=1, the raw regional trigger) ---
    base = E >= 1.0
    api_rows = []
    for q in API_Q_SWEEP:
        floor = float(np.percentile(api, q)) if q > 0 else -np.inf
        api_rows.append({"api_q": q, "api_floor_mm": round(floor, 1) if q > 0 else 0.0,
                         **score(base & (api >= floor), dates, events)})

    # "How rare" context: percentile rank of each event day's E, and the season peak.
    def pct_rank(x):
        return round(100.0 * float((E <= x).mean()), 1)
    ev_ctx = []
    for name, ev in events:
        if ev in dates:
            i = dates.index(ev)
            ev_ctx.append({"name": name, "date": ev.isoformat(), "E": round(float(E[i]), 2),
                           "E_percentile": pct_rank(E[i]), "won_duration_d": int(win_D[i])})
    peak_i = int(np.argmax(E))
    peak_ctx = {"date": dates[peak_i].isoformat(), "E": round(float(E[peak_i]), 2),
                "won_duration_d": int(win_D[peak_i])}

    # Headline: is there ANY selective (<20% season) setting that still catches both events?
    selective_both = [r for r in k_rows + api_rows
                      if r["pct_season"] < 20.0 and r["n_events_caught"] == len(events)]
    headline = (f"selective(<20% season)+both-events setting EXISTS: {selective_both[0]}"
                if selective_both else
                f"NO setting is both selective (<20% season) AND catches both events on {rain_source} "
                f"-> gauge precision (CHIRPS) needed.")

    report = {
        "source": csv_path.name, "rain_source": rain_source,
        "base_threshold": f"{thr['label']} I={a}*D^-{b}", "threshold_id": args.threshold,
        "window_days": WINDOW_D, "n_days": len(dates),
        "raw_regional_trigger_days": int(base.sum()),
        "stringency_sweep": k_rows, "antecedent_sweep": api_rows,
        "event_context": ev_ctx, "season_peak": peak_ctx, "headline": headline,
    }
    RAIN_DIR.mkdir(parents=True, exist_ok=True)
    sfx = args.out_suffix
    (RAIN_DIR / f"specificity_report{sfx}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_md(RAIN_DIR / f"specificity_report{sfx}.md", report)
    make_figure(RAIN_DIR / f"specificity{sfx}.png", dates, water, E, api, events, k_rows, base)

    print(f"base: {thr['label']} on {rain_source}  raw regional trigger days = {int(base.sum())}/{len(dates)}")
    print("stringency sweep (antecedent off):")
    for r in k_rows:
        evs = " ".join(f"{e['name'][:10]}Δ{e['nearest_alert_delta_days']}" for e in r["per_event"])
        print(f"  k={r['k']:>3}  (>= {r['equiv_1day_mm']:>5} mm/1d)  alerts={r['n_alert_days']:3d} "
              f"({r['pct_season']:4.1f}%)  events {r['n_events_caught']}/{r['n_events']}  [{evs}]")
    print("antecedent sweep (at k=1):")
    for r in api_rows:
        print(f"  API>=p{r['api_q']:<2} ({r['api_floor_mm']:>5} mm)  alerts={r['n_alert_days']:3d} "
              f"({r['pct_season']:4.1f}%)  events {r['n_events_caught']}/{r['n_events']}")
    print("event rarity (E = how far above the regional lower bound):")
    for e in ev_ctx:
        print(f"  {e['date']}  {e['name'][:22]:22s}  E={e['E']:.2f}  ({e['E_percentile']:.0f}th pct, "
              f"{e['won_duration_d']}d)")
    print(f"  season peak {peak_ctx['date']}  E={peak_ctx['E']:.2f}")
    print(f"HEADLINE: {headline}")
    print(f"  -> {RAIN_DIR / f'specificity_report{sfx}.json'} , .md , specificity{sfx}.png")
    return 0


def write_md(path: Path, r: dict) -> None:
    lines = [
        f"# Rainfall trigger specificity — {r['source']}", "",
        f"Making the **{r['base_threshold']}** regional I-D trigger SELECTIVE. Rain source: "
        f"**{r['rain_source']}**. Raw regional trigger fires **{r['raw_regional_trigger_days']}/"
        f"{r['n_days']}** days — sensitive, not selective. Two dials trade that down; scored vs the "
        f"documented 2025 events (±{r['window_days']} d).", "",
        "**Dial 1 — stringency k** (alert if peak I-D exceedance E ≥ k; antecedent off):", "",
        "| k | ≈1-day mm | alert days | % season | events caught | 27 Apr Δ | 8 May Δ |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in r["stringency_sweep"]:
        d = {e["date"]: e for e in row["per_event"]}
        d27 = d.get("2025-04-27", {}).get("nearest_alert_delta_days")
        d08 = d.get("2025-05-08", {}).get("nearest_alert_delta_days")
        lines.append(f"| {row['k']} | {row['equiv_1day_mm']} | {row['n_alert_days']} | "
                     f"{row['pct_season']} | {row['n_events_caught']}/{row['n_events']} | {d27} | {d08} |")
    lines += ["",
              "**Dial 2 — antecedent floor** (alert if E ≥ 1 AND antecedent wetness API ≥ percentile):", "",
              "| API floor | mm | alert days | % season | events caught |",
              "|---|---|---|---|---|"]
    for row in r["antecedent_sweep"]:
        lines.append(f"| p{row['api_q']} | {row['api_floor_mm']} | {row['n_alert_days']} | "
                     f"{row['pct_season']} | {row['n_events_caught']}/{row['n_events']} |")
    lines += ["", "**How rare were the documented events?** (E = how far above the regional lower bound; "
              "1.0 = just on the line)", ""]
    for e in r["event_context"]:
        lines.append(f"- {e['date']} {e['name']}: **E = {e['E']}** ({e['E_percentile']}th percentile of "
                     f"the season, via the {e['won_duration_d']}-day window)")
    lines += [f"- season peak {r['season_peak']['date']}: **E = {r['season_peak']['E']}** "
              f"({r['season_peak']['won_duration_d']}-day window)", "",
              f"## Headline", f"**{r['headline']}**", "",
              "_Interpretation: the documented spring events sit only just above the regional lower bound "
              "(E≈1) on this rain source, so any stringency that suppresses the routine monsoon also "
              "suppresses them — the classic sensitivity/selectivity bind. The genuinely independent lever "
              "is the rain MEASUREMENT: a gauge product (CHIRPS) that records the real spring bursts would "
              "raise their E, letting a selective k still catch them. Re-run on ramban_chirps_daily.csv._"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figure(path: Path, dates, water, E, api, events, k_rows, base) -> None:
    x = np.arange(len(dates))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8))

    # Panel 1: exceedance ratio E with the stringency levels + events.
    ax1.fill_between(x, 0, E, color="#9ecae1", step="mid", label="peak I-D exceedance E(t)")
    for k in (1.0, 2.0, 3.0):
        ax1.axhline(k, color="#888", lw=0.8, ls="--")
        ax1.text(len(dates) - 1, k, f" k={k}", va="bottom", ha="right", fontsize=7, color="#555")
    for name, ev_date in events:
        if ev_date in dates:
            i = dates.index(ev_date)
            ax1.axvline(i, color="#cc3311", lw=1.4)
            ax1.text(i, ax1.get_ylim()[1] * 0.95, f" {name[:14]}\n {ev_date}", color="#cc3311",
                     fontsize=7, va="top")
    ax1.set_ylabel("E = rain ÷ regional threshold")
    ax1.set_title("Specificity dial 1: how far each day rises above the regional I-D lower bound "
                  "(E≥1 = raw trigger)")
    tick = np.linspace(0, len(dates) - 1, 8).astype(int)
    ax1.set_xticks(tick); ax1.set_xticklabels([dates[i].strftime("%b %d") for i in tick])
    ax1.legend(fontsize=8, loc="upper left"); ax1.grid(alpha=0.3)

    # Panel 2: ROC-like trade-off — % season flagged vs events caught, per k.
    xs = [r["pct_season"] for r in k_rows]
    ys = [r["n_events_caught"] for r in k_rows]
    ax2.plot(xs, ys, "-o", color="#4477aa")
    for r in k_rows:
        ax2.annotate(f"k={r['k']}", (r["pct_season"], r["n_events_caught"]),
                     fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax2.set_xlabel("% of season flagged (lower = more selective)")
    ax2.set_ylabel("documented events caught (of 2)")
    ax2.set_ylim(-0.2, len(events) + 0.2); ax2.set_yticks(range(len(events) + 1))
    ax2.set_title("Sensitivity vs selectivity trade-off (each point = a stringency k)")
    ax2.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

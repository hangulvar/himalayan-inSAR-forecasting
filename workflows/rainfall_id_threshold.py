#!/usr/bin/env python
"""rainfall_id_threshold.py — intensity-duration (ID) landslide-trigger screen on the
real AOI daily rainfall (from fetch_rainfall.py), replacing the mock dry/monsoon/extreme.

THE METHOD: the field-standard landslide rainfall trigger is an intensity-duration
threshold — a curve I = a·D^(-b) (mean rainfall intensity I vs duration D). Rainfall
that plots ABOVE the curve has historically triggered slope failures. We use the
classic GLOBAL baseline of Caine (1980): I = 14.82·D^(-0.39) (I in mm/h, D in hours,
valid ~10 min–500 h). For each duration we form the rolling cumulative rainfall and
flag days whose mean intensity exceeds the threshold. (A regional Himalayan curve is
the refinement; global Caine is a conservative, well-known screen.)

Also emits a daily wetness/antecedent index (API) for the later FS-saturation coupling.

Runs in the lean `insar` image (numpy + matplotlib-base):
  docker compose run --rm insar python workflows/rainfall_id_threshold.py
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAIN_DIR = PROJECT_ROOT / "data" / "rainfall"

CAINE_A, CAINE_B = 14.82, 0.39          # I[mm/h] = A * D[h]^(-B), Caine (1980)
DURATIONS_D = [1, 2, 3, 5, 7, 10, 15]   # days


def caine_threshold_intensity(d_hours: np.ndarray) -> np.ndarray:
    return CAINE_A * d_hours ** (-CAINE_B)         # mm/h


def caine_threshold_cumulative(d_days: float) -> float:
    """Cumulative rainfall (mm) over d_days that just reaches the Caine threshold."""
    d_h = d_days * 24.0
    return float(caine_threshold_intensity(np.array([d_h]))[0] * d_h)


def load_daily(csv_path: Path):
    dates, rain = [], []
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dates.append(date.fromisoformat(row["date"]))
            rain.append(float(row["rain_mm"]))
    return dates, np.array(rain, dtype=np.float64)


def rolling_sum(x: np.ndarray, w: int) -> np.ndarray:
    """Trailing w-day sum at each index (NaN until enough history)."""
    out = np.full(x.shape, np.nan)
    c = np.cumsum(np.insert(x, 0, 0.0))
    out[w - 1:] = c[w:] - c[:-w]
    return out


def antecedent_index(rain: np.ndarray, k: float = 0.9, n: int = 14) -> np.ndarray:
    """API_t = sum_{j=0..n} rain_{t-j} * k^j — exponentially-decayed wetness memory (mm)."""
    api = np.zeros_like(rain)
    for j in range(n + 1):
        api[j:] += rain[:len(rain) - j] * (k ** j)
    return api


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default=str(RAIN_DIR / "ramban_era5land_daily.csv"))
    args = ap.parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"Missing rainfall CSV: {csv_path} — run fetch_rainfall.py first.")
    dates, rain = load_daily(csv_path)
    n = len(dates)

    per_dur, trigger = {}, np.zeros(n, dtype=bool)
    for D in DURATIONS_D:
        cum = rolling_sum(rain, D)
        thr_cum = caine_threshold_cumulative(D)
        exc = np.isfinite(cum) & (cum > thr_cum)
        trigger |= exc
        idx = np.where(exc)[0]
        per_dur[D] = {
            "threshold_cumulative_mm": round(thr_cum, 1),
            "n_exceedance_days": int(exc.sum()),
            "exceedance_dates": [dates[i].isoformat() for i in idx],
            "max_cumulative_mm": round(float(np.nanmax(cum)), 1),
            "max_cumulative_date": dates[int(np.nanargmax(cum))].isoformat(),
        }

    api = antecedent_index(rain)
    sat = np.clip(api / np.percentile(api, 95), 0.0, 1.0)   # relative 0..1 wetness proxy

    trig_idx = np.where(trigger)[0]
    report = {
        "source": csv_path.name, "threshold": "Caine (1980) I=14.82*D^-0.39 (global)",
        "season": {"start": dates[0].isoformat(), "end": dates[-1].isoformat(),
                   "days": n, "total_mm": round(float(rain.sum()), 1),
                   "max_day_mm": round(float(rain.max()), 1),
                   "max_day": dates[int(rain.argmax())].isoformat()},
        "durations_days": DURATIONS_D,
        "per_duration": {str(D): per_dur[D] for D in DURATIONS_D},
        "trigger_days": [dates[i].isoformat() for i in trig_idx],
        "n_trigger_days": int(trigger.sum()),
    }
    RAIN_DIR.mkdir(parents=True, exist_ok=True)
    (RAIN_DIR / "id_threshold_report.json").write_text(json.dumps(report, indent=2),
                                                       encoding="utf-8")
    write_md(RAIN_DIR / "id_threshold_report.md", report, per_dur)
    write_wetness(RAIN_DIR / "ramban_wetness_daily.csv", dates, rain, api, sat)
    make_figure(RAIN_DIR / "id_threshold.png", dates, rain, trigger, per_dur)

    print(f"rainfall {dates[0]}..{dates[-1]}  total={rain.sum():.0f} mm  "
          f"max-day={rain.max():.1f} mm")
    print(f"ID-threshold (Caine 1980) trigger days: {int(trigger.sum())}")
    for D in DURATIONS_D:
        pd = per_dur[D]
        print(f"  D={D:2d}d  thr={pd['threshold_cumulative_mm']:6.0f} mm  "
              f"exceed-days={pd['n_exceedance_days']:2d}  "
              f"(max {pd['max_cumulative_mm']:.0f} mm on {pd['max_cumulative_date']})")
    if trig_idx.size:
        print(f"  trigger window(s): {', '.join(report['trigger_days'])}")
    print(f"  -> {RAIN_DIR/'id_threshold_report.json'} , .md , id_threshold.png , "
          f"ramban_wetness_daily.csv")
    return 0


def write_wetness(path: Path, dates, rain, api, sat) -> None:
    lines = ["date,rain_mm,api_mm,wetness_0_1"]
    for d, r, a, s in zip(dates, rain, api, sat):
        lines.append(f"{d.isoformat()},{r:.3f},{a:.2f},{s:.3f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_md(path: Path, report: dict, per_dur: dict) -> None:
    s = report["season"]
    lines = [
        f"# Rainfall intensity–duration trigger — {report['source']}", "",
        f"Real ERA5-Land daily rainfall over the AOI, screened against the **Caine (1980)**",
        "global intensity–duration landslide threshold (I = 14.82·D⁻⁰·³⁹). Rainfall plotting",
        "above the curve has historically triggered failures. Replaces the mock dry/monsoon/",
        "extreme scenarios with what actually fell.", "",
        f"- season: **{s['start']} → {s['end']}** ({s['days']} days)",
        f"- total: **{s['total_mm']:.0f} mm**, peak day **{s['max_day_mm']:.1f} mm** ({s['max_day']})",
        f"- **ID-threshold trigger days: {report['n_trigger_days']}**", "",
        "| duration | Caine cumulative threshold | exceedance days | season max (date) |",
        "|---|---|---|---|",
    ]
    for D in report["durations_days"]:
        pd = per_dur[D]
        lines.append(f"| {D} d | {pd['threshold_cumulative_mm']:.0f} mm | "
                     f"{pd['n_exceedance_days']} | {pd['max_cumulative_mm']:.0f} mm "
                     f"({pd['max_cumulative_date']}) |")
    lines += ["",
              "**Trigger days (any duration exceeded):** "
              + (", ".join(report["trigger_days"]) if report["trigger_days"]
                 else "_none — no rainfall window crossed the global threshold this season._"),
              "",
              "_Note: Caine is a conservative GLOBAL baseline; a regional Himalayan I–D curve",
              "(typically lower) is the refinement. ERA5-Land underestimates orographic",
              "precipitation, so a gauge product (CHIRPS/GPM) is the planned cross-check._"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figure(path: Path, dates, rain, trigger, per_dur) -> None:
    x = np.arange(len(dates))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))
    ax1.bar(x, rain, color="#4477aa", width=1.0)
    for i in np.where(trigger)[0]:
        ax1.axvline(i, color="#cc3311", alpha=0.6, lw=1.2)
    ax1.set_ylabel("daily rainfall (mm)")
    ax1.set_title("AOI daily rainfall (ERA5-Land) — red = ID-threshold trigger day")
    tick = np.linspace(0, len(dates) - 1, 7).astype(int)
    ax1.set_xticks(tick); ax1.set_xticklabels([dates[i].strftime("%b %d") for i in tick])
    ax1.grid(alpha=0.3)

    # I-D scatter of the season's worst point per duration vs the Caine curve.
    d_h = np.array([D * 24.0 for D in per_dur])
    obs_I = np.array([per_dur[D]["max_cumulative_mm"] / (D * 24.0) for D in per_dur])
    dd = np.logspace(np.log10(12), np.log10(24 * 20), 100)
    ax2.loglog(dd, caine_threshold_intensity(dd), "k-", label="Caine (1980) threshold")
    above = obs_I > caine_threshold_intensity(d_h)
    ax2.scatter(d_h[~above], obs_I[~above], c="#4477aa", label="season max (below)")
    ax2.scatter(d_h[above], obs_I[above], c="#cc3311", label="season max (ABOVE → trigger)")
    for D, di, ii in zip(per_dur, d_h, obs_I):
        ax2.annotate(f"{D}d", (di, ii), fontsize=8, xytext=(3, 3), textcoords="offset points")
    ax2.set_xlabel("duration (hours)"); ax2.set_ylabel("mean intensity (mm/h)")
    ax2.set_title("Intensity–duration: season peaks vs threshold")
    ax2.grid(alpha=0.3, which="both"); ax2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

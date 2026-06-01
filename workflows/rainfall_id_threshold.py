#!/usr/bin/env python
"""rainfall_id_threshold.py — intensity-duration (ID) landslide-trigger screen on the
real AOI daily WATER INPUT (rain + snowmelt, from fetch_rainfall.py), replacing the
mock dry/monsoon/extreme.

THE METHOD: the field-standard landslide rainfall trigger is an intensity-duration
threshold — a curve I = a*D^(-b) (mean intensity I vs duration D). Rainfall that plots
ABOVE the curve has historically triggered slope failures. We use the classic GLOBAL
baseline of Caine (1980): I = 14.82*D^(-0.39) (I in mm/h, D in hours, valid ~10 min-500 h).

WHY WATER, NOT JUST RAIN: the back-test (backtest_inventory.py) showed a rainfall-only
trigger MISSED the documented Apr-May 2025 Ramban failures — the NW-Himalaya snowmelt /
freeze-thaw season. Snowmelt loads a slope just like rain, so we screen the ID curve on
the effective WATER INPUT = rain + snowmelt, and additionally flag freeze-thaw days
(Tmin<0<Tmax) as the spring slope-weakening conditioning that pairs with snowmelt.
(Treating snowmelt as ID-curve water input is a first-order coupling; a dedicated
snowmelt-driven threshold is the refinement.)

Also emits a daily wetness/antecedent index (API) for the FS-saturation coupling, now
built on the water input.

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


def _col(rows, name, default):
    out = []
    for r in rows:
        v = r.get(name)
        out.append(float(v) if v not in (None, "") else float(default))
    return np.array(out, dtype=np.float64)


def load_daily(csv_path: Path):
    """date[], rain_mm[], snowmelt_mm[], tmin_c[], tmax_c[]. Legacy CSVs (rain only)
    still load: missing snowmelt -> 0, missing temps -> NaN."""
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    dates = [date.fromisoformat(r["date"]) for r in rows]
    rain = _col(rows, "rain_mm", "nan")
    snowmelt = _col(rows, "snowmelt_mm", "0")
    tmin = _col(rows, "tmin_c", "nan")
    tmax = _col(rows, "tmax_c", "nan")
    return dates, rain, snowmelt, tmin, tmax


def rolling_sum(x: np.ndarray, w: int) -> np.ndarray:
    """Trailing w-day sum at each index (NaN until enough history)."""
    out = np.full(x.shape, np.nan)
    c = np.cumsum(np.insert(x, 0, 0.0))
    out[w - 1:] = c[w:] - c[:-w]
    return out


def antecedent_index(water: np.ndarray, k: float = 0.9, n: int = 14) -> np.ndarray:
    """API_t = sum_{j=0..n} water_{t-j} * k^j — exponentially-decayed wetness memory (mm)."""
    api = np.zeros_like(water)
    for j in range(n + 1):
        api[j:] += water[:len(water) - j] * (k ** j)
    return api


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default=str(RAIN_DIR / "ramban_era5land_daily.csv"))
    args = ap.parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"Missing rainfall CSV: {csv_path} — run fetch_rainfall.py first.")
    dates, rain, snowmelt, tmin, tmax = load_daily(csv_path)
    n = len(dates)
    water = np.nan_to_num(rain) + np.nan_to_num(snowmelt)     # effective input to the slope

    per_dur, trigger = {}, np.zeros(n, dtype=bool)
    for D in DURATIONS_D:
        cum = rolling_sum(water, D)
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

    freeze_thaw = np.isfinite(tmin) & np.isfinite(tmax) & (tmin < 0.0) & (tmax > 0.0)
    api = antecedent_index(water)
    sat = np.clip(api / np.percentile(api, 95), 0.0, 1.0)   # relative 0..1 wetness proxy

    trig_idx = np.where(trigger)[0]
    ft_idx = np.where(freeze_thaw)[0]
    report = {
        "source": csv_path.name,
        "threshold": "Caine (1980) I=14.82*D^-0.39 (global)",
        "trigger_basis": "water = rain + snowmelt (ERA5-Land)",
        "season": {"start": dates[0].isoformat(), "end": dates[-1].isoformat(),
                   "days": n,
                   "rain_total_mm": round(float(np.nansum(rain)), 1),
                   "snowmelt_total_mm": round(float(np.nansum(snowmelt)), 1),
                   "water_total_mm": round(float(water.sum()), 1),
                   "max_water_day_mm": round(float(water.max()), 1),
                   "max_water_day": dates[int(water.argmax())].isoformat()},
        "durations_days": DURATIONS_D,
        "per_duration": {str(D): per_dur[D] for D in DURATIONS_D},
        "trigger_days": [dates[i].isoformat() for i in trig_idx],
        "n_trigger_days": int(trigger.sum()),
        "freeze_thaw_days": [dates[i].isoformat() for i in ft_idx],
        "n_freeze_thaw_days": int(freeze_thaw.sum()),
    }
    RAIN_DIR.mkdir(parents=True, exist_ok=True)
    (RAIN_DIR / "id_threshold_report.json").write_text(json.dumps(report, indent=2),
                                                       encoding="utf-8")
    write_md(RAIN_DIR / "id_threshold_report.md", report, per_dur)
    write_wetness(RAIN_DIR / "ramban_wetness_daily.csv",
                  dates, rain, snowmelt, water, api, sat, freeze_thaw)
    make_figure(RAIN_DIR / "id_threshold.png", dates, rain, snowmelt, trigger, freeze_thaw, per_dur)

    s = report["season"]
    print(f"water {dates[0]}..{dates[-1]}  rain={s['rain_total_mm']:.0f} + "
          f"snowmelt={s['snowmelt_total_mm']:.0f} = {s['water_total_mm']:.0f} mm  "
          f"max-day={s['max_water_day_mm']:.1f} mm ({s['max_water_day']})")
    print(f"ID-threshold (Caine 1980, on water) trigger days: {int(trigger.sum())}")
    for D in DURATIONS_D:
        pd = per_dur[D]
        print(f"  D={D:2d}d  thr={pd['threshold_cumulative_mm']:6.0f} mm  "
              f"exceed-days={pd['n_exceedance_days']:2d}  "
              f"(max {pd['max_cumulative_mm']:.0f} mm on {pd['max_cumulative_date']})")
    if trig_idx.size:
        print(f"  trigger day(s): {', '.join(report['trigger_days'])}")
    print(f"  freeze-thaw days (Tmin<0<Tmax): {int(freeze_thaw.sum())}"
          + (f"  e.g. {report['freeze_thaw_days'][0]}..{report['freeze_thaw_days'][-1]}"
             if ft_idx.size else ""))
    print(f"  -> {RAIN_DIR/'id_threshold_report.json'} , .md , id_threshold.png , "
          f"ramban_wetness_daily.csv")
    return 0


def write_wetness(path: Path, dates, rain, snowmelt, water, api, sat, freeze_thaw) -> None:
    lines = ["date,rain_mm,snowmelt_mm,water_mm,api_mm,wetness_0_1,freeze_thaw"]
    for d, r, sm, w, a, s, ft in zip(dates, rain, snowmelt, water, api, sat, freeze_thaw):
        lines.append(f"{d.isoformat()},{r:.3f},{sm:.3f},{w:.3f},{a:.2f},{s:.3f},{int(ft)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_md(path: Path, report: dict, per_dur: dict) -> None:
    s = report["season"]
    lines = [
        f"# Rainfall + snowmelt intensity-duration trigger — {report['source']}", "",
        "Real ERA5-Land daily **water input (rain + snowmelt)** over the AOI, screened against",
        "the **Caine (1980)** global intensity-duration landslide threshold (I = 14.82*D^-0.39).",
        "Water plotting above the curve has historically triggered failures. Snowmelt is added to",
        "rain because the back-test showed rainfall alone missed the Apr-May 2025 (snowmelt-season)",
        "failures; freeze-thaw days are flagged as the paired spring weakening mechanism.", "",
        f"- season: **{s['start']} -> {s['end']}** ({s['days']} days)",
        f"- water: **{s['water_total_mm']:.0f} mm** = rain {s['rain_total_mm']:.0f} + "
        f"snowmelt {s['snowmelt_total_mm']:.0f}; peak water day **{s['max_water_day_mm']:.1f} mm** "
        f"({s['max_water_day']})",
        f"- **ID-threshold trigger days: {report['n_trigger_days']}** "
        f"({', '.join(report['trigger_days']) if report['trigger_days'] else 'none'})",
        f"- **freeze-thaw days (Tmin<0<Tmax): {report['n_freeze_thaw_days']}**", "",
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
                 else "_none — no water window crossed the global threshold this season._"),
              "",
              "_Note: Caine is a conservative GLOBAL baseline; a regional Himalayan I-D curve",
              "(typically lower) is the refinement. ERA5-Land underestimates orographic",
              "precipitation, so a gauge product (CHIRPS/GPM) is the planned cross-check. Snowmelt",
              "is treated as ID-curve water input (first-order); a dedicated snowmelt threshold is",
              "the refinement._"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figure(path: Path, dates, rain, snowmelt, trigger, freeze_thaw, per_dur) -> None:
    x = np.arange(len(dates))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))
    ax1.bar(x, rain, color="#4477aa", width=1.0, label="rain")
    ax1.bar(x, np.nan_to_num(snowmelt), bottom=np.nan_to_num(rain),
            color="#88ccee", width=1.0, label="snowmelt")
    for i in np.where(freeze_thaw)[0]:
        ax1.axvspan(i - 0.5, i + 0.5, color="#ddccff", alpha=0.35, lw=0)
    for i in np.where(trigger)[0]:
        ax1.axvline(i, color="#cc3311", alpha=0.7, lw=1.2)
    ax1.set_ylabel("daily water input (mm)")
    ax1.set_title("AOI daily water = rain + snowmelt (ERA5-Land); red = ID trigger, "
                  "shaded = freeze-thaw")
    tick = np.linspace(0, len(dates) - 1, 7).astype(int)
    ax1.set_xticks(tick); ax1.set_xticklabels([dates[i].strftime("%b %d") for i in tick])
    ax1.legend(fontsize=8, loc="upper left"); ax1.grid(alpha=0.3)

    # I-D scatter of the season's worst water point per duration vs the Caine curve.
    d_h = np.array([D * 24.0 for D in per_dur])
    obs_I = np.array([per_dur[D]["max_cumulative_mm"] / (D * 24.0) for D in per_dur])
    dd = np.logspace(np.log10(12), np.log10(24 * 20), 100)
    ax2.loglog(dd, caine_threshold_intensity(dd), "k-", label="Caine (1980) threshold")
    above = obs_I > caine_threshold_intensity(d_h)
    ax2.scatter(d_h[~above], obs_I[~above], c="#4477aa", label="season max (below)")
    ax2.scatter(d_h[above], obs_I[above], c="#cc3311", label="season max (ABOVE -> trigger)")
    for D, di, ii in zip(per_dur, d_h, obs_I):
        ax2.annotate(f"{D}d", (di, ii), fontsize=8, xytext=(3, 3), textcoords="offset points")
    ax2.set_xlabel("duration (hours)"); ax2.set_ylabel("mean intensity (mm/h)")
    ax2.set_title("Intensity-duration: season water peaks vs threshold")
    ax2.grid(alpha=0.3, which="both"); ax2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

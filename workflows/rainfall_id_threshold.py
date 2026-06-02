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

# Power-law intensity-duration landslide thresholds: I[mm/h] = A * D[h]^(-B).
# All in the frequentist convention (I in mm/h, D in hours) -> directly comparable.
# A regional Himalayan curve is much lower (more sensitive) than the conservative
# global Caine baseline: at D=1 day Caine ~ 100 mm vs NW-Himalaya ~ 19 mm.
#
# LITERATURE VERIFICATION (2026-06-02) -- coefficients + UNITS confirmed against sources:
#   * Caine (1980): I=14.82*D^-0.39, valid 10 min-10 days, 73 events. Geogr. Ann. A 62:23-27.
#     Self-check: I(D=1h)=14.82 mm/h (== A, exact); 1-day cumulative = 103 mm.
#   * NW Himalaya: I=2.9993*D^-0.4152 confirmed by the FULL self-consistent regional family in
#     the same paper -- NE Himalaya 5.8294*D^-0.4141, E Ghats 26.88*D^-0.6885, W Ghats
#     28.01*D^-0.641 (TRMM rainfall, 2007-2016, Brunetti-frequentist). UNITS stated in source:
#     "I in mm/h, D in hours" (ED threshold E in mm). Independent numeric cross-checks of OUR
#     curve: I(D=48h)=0.60 mm/h vs the Garhwal sub-zone anchor 0.45-0.50 mm/h; 1-day cumulative
#     19.2 mm vs Shah et al. (2024) NH-44 daily-intensity anchor ~14.35 mm/day. (Primary PDFs are
#     paywalled; values triangulated across multiple independent sources + the numeric checks
#     above. Tighten if you obtain the full JESS 2025 PDF.)
THRESHOLDS = {
    "caine1980": {
        "a": 14.82, "b": 0.39,
        "label": "Caine (1980) global",
        "cite": ("Caine N. (1980) Geogr. Ann. A 62:23-27. I=14.82*D^-0.39 (mm/h, h), valid "
                 "10 min-10 days. VERIFIED 2026-06-02 (I(1h)=14.82 reproduces A exactly)."),
    },
    "nwhimalaya": {
        "a": 2.9993, "b": 0.4152,
        "label": "NW Himalaya (frequentist, 2007-2016)",
        "cite": ("J. Earth Syst. Sci. (2025) 134:97 'The relation between rainfall and "
                 "landslides in India' -- frequentist I-D for the NW Himalaya: "
                 "I=2.9993*D^-0.4152 (mm/h, h; TRMM 2007-2016). VERIFIED 2026-06-02 against the "
                 "paper's full regional family (NE Himalaya 5.8294, E Ghats 26.88, W Ghats 28.01) "
                 "+ units, and cross-checked: I(48h)=0.60 mm/h vs Garhwal 0.45-0.50; 1-day 19.2 mm "
                 "vs Shah et al. (2024) Nat. Hazards 120:1319-1341 NH-44 (Udhampur-Banihal) ~14.35 "
                 "mm/day. PENDING: exact-coefficient confirm from the paywalled primary PDF."),
    },
}
DEFAULT_THRESHOLD = "caine1980"
DURATIONS_D = [1, 2, 3, 5, 7, 10, 15]   # days


def threshold_intensity(d_hours: np.ndarray, a: float, b: float) -> np.ndarray:
    return a * d_hours ** (-b)                      # mm/h


def threshold_cumulative(d_days: float, a: float, b: float) -> float:
    """Cumulative rainfall (mm) over d_days that just reaches the I-D threshold."""
    d_h = d_days * 24.0
    return float(threshold_intensity(np.array([d_h]), a, b)[0] * d_h)


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
    ap.add_argument("--threshold", choices=sorted(THRESHOLDS), default=DEFAULT_THRESHOLD,
                    help="I-D curve: 'caine1980' (global, conservative; default) or "
                         "'nwhimalaya' (regional, ~5x more sensitive). See THRESHOLDS.")
    ap.add_argument("--out-suffix", default="",
                    help="Append to the output filenames (e.g. '_nwhimalaya') so a "
                         "regional run does not overwrite the Caine baseline.")
    args = ap.parse_args()
    thr = THRESHOLDS[args.threshold]
    a, b = thr["a"], thr["b"]
    sfx = args.out_suffix
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"Missing rainfall CSV: {csv_path} — run fetch_rainfall.py first.")
    dates, rain, snowmelt, tmin, tmax = load_daily(csv_path)
    n = len(dates)
    water = np.nan_to_num(rain) + np.nan_to_num(snowmelt)     # effective input to the slope

    per_dur, trigger = {}, np.zeros(n, dtype=bool)
    for D in DURATIONS_D:
        cum = rolling_sum(water, D)
        thr_cum = threshold_cumulative(D, a, b)
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
    rain_source = "CHIRPS (gauge-blended)" if "chirps" in csv_path.name.lower() else "ERA5-Land"
    report = {
        "source": csv_path.name,
        "threshold_id": args.threshold,
        "threshold": f"{thr['label']} I={a}*D^-{b}",
        "threshold_citation": thr["cite"],
        "threshold_a_mmph": a, "threshold_b": b,
        "trigger_basis": f"water = rain + snowmelt ({rain_source})",
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
    (RAIN_DIR / f"id_threshold_report{sfx}.json").write_text(json.dumps(report, indent=2),
                                                             encoding="utf-8")
    write_md(RAIN_DIR / f"id_threshold_report{sfx}.md", report, per_dur)
    write_wetness(RAIN_DIR / f"ramban_wetness_daily{sfx}.csv",
                  dates, rain, snowmelt, water, api, sat, freeze_thaw)
    make_figure(RAIN_DIR / f"id_threshold{sfx}.png", dates, rain, snowmelt,
                trigger, freeze_thaw, per_dur, a, b, thr["label"])

    print(f"threshold: {thr['label']}  (I={a}*D^-{b}, mm/h vs h)")
    s = report["season"]
    print(f"water {dates[0]}..{dates[-1]}  rain={s['rain_total_mm']:.0f} + "
          f"snowmelt={s['snowmelt_total_mm']:.0f} = {s['water_total_mm']:.0f} mm  "
          f"max-day={s['max_water_day_mm']:.1f} mm ({s['max_water_day']})")
    print(f"ID-threshold ({args.threshold}, on water) trigger days: {int(trigger.sum())}")
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
    print(f"  -> {RAIN_DIR / f'id_threshold_report{sfx}.json'} , .md , "
          f"id_threshold{sfx}.png , ramban_wetness_daily{sfx}.csv")
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
        f"Daily **water input (rain + snowmelt)** over the AOI ({report['trigger_basis']}), screened",
        f"against the **{report['threshold']}** intensity-duration landslide threshold.",
        "Water plotting above the curve has historically triggered failures. Snowmelt is added to",
        "rain because the back-test showed rainfall alone missed the Apr-May 2025 (snowmelt-season)",
        "failures; freeze-thaw days are flagged as the paired spring weakening mechanism.", "",
        f"- threshold: **{report['threshold_id']}** — {report['threshold_citation']}",
        f"- season: **{s['start']} -> {s['end']}** ({s['days']} days)",
        f"- water: **{s['water_total_mm']:.0f} mm** = rain {s['rain_total_mm']:.0f} + "
        f"snowmelt {s['snowmelt_total_mm']:.0f}; peak water day **{s['max_water_day_mm']:.1f} mm** "
        f"({s['max_water_day']})",
        f"- **ID-threshold trigger days: {report['n_trigger_days']}** "
        f"({', '.join(report['trigger_days']) if report['trigger_days'] else 'none'})",
        f"- **freeze-thaw days (Tmin<0<Tmax): {report['n_freeze_thaw_days']}**", "",
        "| duration | cumulative threshold | exceedance days | season max (date) |",
        "|---|---|---|---|",
    ]
    for D in report["durations_days"]:
        pd = per_dur[D]
        lines.append(f"| {D} d | {pd['threshold_cumulative_mm']:.0f} mm | "
                     f"{pd['n_exceedance_days']} | {pd['max_cumulative_mm']:.0f} mm "
                     f"({pd['max_cumulative_date']}) |")
    is_regional = report["threshold_id"] != "caine1980"
    is_gauge = "chirps" in report["source"].lower()
    notes = []
    if is_regional:
        notes.append("This run uses a **regional** Himalayan I-D curve — far more sensitive than the "
                     "global Caine baseline (Caine ~100 mm/day vs this ~19 mm/day at D=1 d).")
    else:
        notes.append("Caine is a conservative GLOBAL baseline; the regional `nwhimalaya` curve "
                     "(~5x more sensitive) is the refinement (`--threshold nwhimalaya`).")
    notes.append("This run uses **CHIRPS** gauge-blended rain (resolves orographic bursts ERA5-Land "
                 "under-counts)." if is_gauge else
                 "ERA5-Land under-counts orographic precipitation, so the **CHIRPS** gauge product "
                 "(fetch_chirps.py) is the cross-check.")
    notes.append("Snowmelt is treated as ID-curve water input (first-order); a dedicated snowmelt "
                 "threshold is the refinement.")
    lines += ["",
              "**Trigger days (any duration exceeded):** "
              + (", ".join(report["trigger_days"]) if report["trigger_days"]
                 else "_none — no water window crossed the threshold this season._"),
              "", "_Note: " + " ".join(notes) + "_"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figure(path: Path, dates, rain, snowmelt, trigger, freeze_thaw, per_dur,
                a: float, b: float, label: str) -> None:
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
    ax2.loglog(dd, threshold_intensity(dd, a, b), "k-", label=f"{label} threshold")
    above = obs_I > threshold_intensity(d_h, a, b)
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

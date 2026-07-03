#!/usr/bin/env python
"""inverse_velocity_ttf.py — Fukuzono/Voight inverse-velocity time-to-failure (TTF)
screen for the alert zones of a stack.

THE METHOD (Fukuzono 1985): a slope in tertiary (accelerating) creep has an inverse
velocity 1/|v| that falls ~linearly toward zero; the time at which 1/|v| = 0 is the
projected failure time t_f. We use the per-pixel displacement time series we already
produce (`<stack>_displacement_timeseries.tif`, cumulative LOS mm, coh>=0.7-masked).

This is a property of the MEASURED motion, so it is INDEPENDENT of the rainfall
scenario; we read the operational (monsoon) alert zones only to know WHERE to look.

HONEST LIMITS (read before trusting any number): ~14 epochs over ~3.5 months at a
~30 mm/yr noise floor. Inverse velocity is noise-sensitive and clear accelerating
creep is rare, so most zones will (correctly) screen as STEADY. A zone is only called
ACCELERATING when its 1/|v| trend is significantly decreasing (R^2 >= --r2-min) and the
projected failure lands inside --horizon-days. Treat any TTF as a SCREENING flag to
watch, not a calibrated prediction.

Runs in the lean `insar` image (rasterio + numpy + matplotlib-base):
  docker compose run --rm insar python workflows/inverse_velocity_ttf.py --stack ASC_path27_frame106
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_timeseries(stack: str):
    """Return (t_days, dates, cube) — cube is (n_dates, H, W) cumulative LOS mm."""
    path = PROJECT_ROOT / "data" / "velocity" / f"{stack}_displacement_timeseries.tif"
    if not path.exists():
        raise SystemExit(f"Missing time series: {path} — run Phase 2 (custom inverter) first.")
    with rasterio.open(path) as src:
        cube = src.read().astype(np.float64)            # (n_dates, H, W)
        descs = src.descriptions
    dates = [datetime.strptime(d, "%Y-%m-%d") for d in descs]
    t0 = dates[0]
    t_days = np.array([(d - t0).days for d in dates], dtype=np.float64)
    return t_days, dates, cube


def smoothed_velocity(t: np.ndarray, d: np.ndarray):
    """Velocity (mm/day) at each epoch via a centered 3-point linear fit; returns
    (t_v, v) over epochs where a fit was possible and d is finite."""
    n = len(t)
    t_v, v = [], []
    for k in range(n):
        lo, hi = max(0, k - 1), min(n, k + 2)
        tt, dd = t[lo:hi], d[lo:hi]
        m = np.isfinite(dd)
        if m.sum() < 2:
            continue
        slope = np.polyfit(tt[m], dd[m], 1)[0]
        t_v.append(t[k]); v.append(slope)
    return np.array(t_v), np.array(v)


def fukuzono(t: np.ndarray, d: np.ndarray, r2_min: float, horizon: float,
             creep_thr_mmyr: float, min_v: int = 5, min_frac_creep: float = 0.7):
    """Classify a zone's cumulative-displacement series and estimate TTF.

    Returns a dict with class in {INSUFFICIENT, STEADY, ACCELERATING,
    ACCEL_BEYOND_HORIZON} plus diagnostics. Failure direction is negative LOS (motion
    away from sensor). HARD GATES against fitting noise: the zone must (1) have a net
    trend at least as fast as the creep threshold, and (2) move *consistently* in the
    creep direction (>= min_frac_creep of velocities negative) before we trust any
    inverse-velocity extrapolation. A steady creep gives ~flat 1/|v| (no TTF); only a
    genuinely accelerating one gives a significantly decreasing 1/|v|.
    """
    finite = np.isfinite(d)
    if finite.sum() < 6:
        return {"klass": "INSUFFICIENT", "n_obs": int(finite.sum())}
    t, d = t[finite], d[finite]
    t_v, v = smoothed_velocity(t, d)
    net = float(np.polyfit(t, d, 1)[0] * 365.25)            # net trend, mm/yr
    frac_creep = float(np.mean(v < 0)) if len(v) else 0.0
    out = {"n_obs": int(finite.sum()),
           "net_velocity_mmyr": round(net, 1),
           "latest_velocity_mmyr": round(float(v[-1] * 365.25), 1) if len(v) else None,
           "frac_creep_dir": round(frac_creep, 2)}

    # Gate 1: genuinely creeping (consistent with the alert's creep classification).
    # Gate 2: motion is consistently in the failure direction (not cherry-picked noise).
    creep_v = v < 0
    if net > creep_thr_mmyr or frac_creep < min_frac_creep or creep_v.sum() < min_v:
        out["klass"] = "STEADY"
        return out

    tv, iv = t_v[creep_v], 1.0 / np.abs(v[creep_v])         # inverse velocity (day/mm)
    b, a = np.polyfit(tv, iv, 1)                            # iv = a + b*t
    pred = a + b * tv
    ss_res = float(((iv - pred) ** 2).sum())
    ss_tot = float(((iv - iv.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    out["inv_vel_slope"] = b
    out["r2"] = round(r2, 3)

    if b < 0 and r2 >= r2_min:                              # accelerating + good fit
        t_f = -a / b
        ttf = t_f - t[-1]
        out["ttf_days"] = round(float(ttf), 1)
        if 0 < ttf <= horizon:
            out["klass"] = "ACCELERATING"
        else:
            out["klass"] = "ACCEL_BEYOND_HORIZON"
        out["_fit"] = (tv, iv, a, b, t[-1], t_f, t, d)      # for plotting
    else:
        out["klass"] = "STEADY"
    return out


def zone_series(cube: np.ndarray, vel: np.ndarray, row: int, col: int, radius: int,
                creep_thr_mmyr: float):
    """Mean cumulative-displacement series over the CREEP pixels of a (2r+1)^2 window
    (velocity <= creep threshold AND finite time series). Averaging only the failing
    pixels isolates the creep signal instead of diluting it with stable neighbours —
    the single biggest fix vs a plain window. Returns (series, n_creep_px)."""
    n, H, W = cube.shape
    r0, r1 = max(0, row - radius), min(H, row + radius + 1)
    c0, c1 = max(0, col - radius), min(W, col + radius + 1)
    block = cube[:, r0:r1, c0:c1].reshape(n, -1)
    vblock = vel[r0:r1, c0:c1].reshape(-1)                  # mm/yr
    creep = np.isfinite(vblock) & (vblock <= creep_thr_mmyr)
    if creep.sum() == 0:
        return np.full(n, np.nan), 0
    with np.errstate(invalid="ignore"):
        return np.nanmean(block[:, creep], axis=1), int(creep.sum())


def make_figure(zone, res, dates, out_png: Path):
    tv, iv, a, b, t_last, t_f, t, d = res["_fit"]
    t0 = dates[0]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 6), sharex=True)
    ax1.plot(t, d, "o-", color="#1f77b4")
    ax1.set_ylabel("cumulative LOS disp (mm)")
    ax1.set_title(f"Zone {zone['id']} ({zone['severity']}) — inverse-velocity TTF\n"
                  f"net {res['net_velocity_mmyr']:+.0f} mm/yr, "
                  f"TTF ~{res['ttf_days']:.0f} d, R²={res['r2']:.2f}")
    ax1.grid(alpha=0.3)
    ax2.plot(tv, iv, "o", color="#d62728", label="1/|v| (creep dir.)")
    xline = np.array([tv.min(), t_f])
    ax2.plot(xline, a + b * xline, "--", color="#d62728", label="Fukuzono fit → failure")
    ax2.axhline(0, color="k", lw=0.8)
    ax2.axvline(t_last, color="gray", ls=":", label="last obs")
    ax2.axvline(t_f, color="k", ls=":", label="projected failure")
    ax2.set_ylim(bottom=0)
    ax2.set_ylabel("inverse velocity (day/mm)")
    ax2.set_xlabel(f"days since {t0:%Y-%m-%d}")
    ax2.grid(alpha=0.3)
    ax2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stack", default="ASC_path27_frame106")
    ap.add_argument("--alerts", default=None,
                    help="Alerts JSON for zone locations (default: monsoon for the stack).")
    ap.add_argument("--window-radius", type=int, default=2, help="Zone window = (2r+1)^2.")
    ap.add_argument("--r2-min", type=float, default=0.5)
    ap.add_argument("--creep-vel", type=float, default=-15.0,
                    help="Creep threshold (mm/yr, negative = away from sensor). Matches the "
                         "orchestrator; gates which window pixels and zones are 'creeping'.")
    ap.add_argument("--horizon-days", type=float, default=365.0,
                    help="Report a TTF only if projected failure is within this horizon.")
    ap.add_argument("--use-vslope", action="store_true",
                    help="Select each zone's creep pixels from *_v_slope.tif (downslope-projected, "
                         "single-look blind pixels excluded) instead of raw LOS. The Fukuzono fit "
                         "still runs on the LOS time series (acceleration is scale-invariant), so "
                         "this refines WHICH pixels are analysed, not the accel test.")
    ap.add_argument("--max-figs", type=int, default=3)
    args = ap.parse_args()
    stack = args.stack

    alerts_path = Path(args.alerts) if args.alerts else \
        PROJECT_ROOT / "data" / "alerts" / stack / "alerts_monsoon.json"
    if not alerts_path.exists():
        raise SystemExit(f"Missing alerts JSON: {alerts_path}")
    alerts = json.loads(alerts_path.read_text(encoding="utf-8"))["alerts"]

    t_days, dates, cube = load_timeseries(stack)
    # High-pass velocity to match the orchestrator's creep definition (agentic_
    # orchestrator reads *_mean_velocity_los_highpass.tif); a raw-velocity mask would
    # miss the localized creep pixels the alert zones are actually built from. With
    # --use-vslope, select on the slope-parallel velocity instead (negated so +downslope
    # -> negative, matching the creep-threshold sign), which excludes blind-spot pixels.
    vel_name = "v_slope" if args.use_vslope else "mean_velocity_los_highpass"
    vel_path = PROJECT_ROOT / "data" / "velocity" / f"{stack}_{vel_name}.tif"
    with rasterio.open(vel_path) as vsrc:
        vel = vsrc.read(1).astype(np.float64)
    if args.use_vslope:
        vel = -vel
    out_dir = alerts_path.parent

    results, counts = [], {"ACCELERATING": 0, "ACCEL_BEYOND_HORIZON": 0,
                           "STEADY": 0, "INSUFFICIENT": 0}
    for z in alerts:
        row, col = z["pixel_rowcol"]
        d, n_creep = zone_series(cube, vel, row, col, args.window_radius, args.creep_vel)
        res = fukuzono(t_days, d, args.r2_min, args.horizon_days, args.creep_vel)
        counts[res["klass"]] += 1
        rec = {"id": z["id"], "severity": z["severity"],
               "centroid_lonlat": z["centroid_lonlat"], "klass": res["klass"],
               "n_creep_px": n_creep,
               "net_velocity_mmyr": res.get("net_velocity_mmyr"),
               "latest_velocity_mmyr": res.get("latest_velocity_mmyr"),
               "frac_creep_dir": res.get("frac_creep_dir"),
               "r2": res.get("r2"), "ttf_days": res.get("ttf_days")}
        if res["klass"] == "ACCELERATING":
            rec["failure_date_est"] = (dates[-1] + timedelta(
                days=res["ttf_days"])).strftime("%Y-%m-%d")
        results.append((rec, res))

    # Figures for the soonest-failing accelerating zones.
    accel = sorted([(rec, res) for rec, res in results if rec["klass"] == "ACCELERATING"],
                   key=lambda x: x[0]["ttf_days"])
    for rec, res in accel[:args.max_figs]:
        make_figure(rec, res, dates, out_dir / f"ttf_zone{rec['id']}.png")

    # Write report (drop the heavy _fit tuple).
    report = {"stack": stack,
              "method": "Fukuzono inverse-velocity (LOS series; "
                        + ("V_slope creep-pixel selection)" if args.use_vslope else "LOS selection)"),
              "alerts_source": alerts_path.name, "n_zones": len(alerts),
              "params": {"window_radius": args.window_radius, "r2_min": args.r2_min,
                         "horizon_days": args.horizon_days},
              "counts": counts, "zones": [rec for rec, _ in results]}
    (out_dir / "ttf_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(out_dir / "ttf_report.md", report, accel, dates)

    print(f"stack={stack}  zones={len(alerts)}  "
          f"ACCELERATING={counts['ACCELERATING']}  "
          f"beyond-horizon={counts['ACCEL_BEYOND_HORIZON']}  "
          f"STEADY={counts['STEADY']}  INSUFFICIENT={counts['INSUFFICIENT']}")
    if accel:
        for rec, _ in accel[:args.max_figs]:
            print(f"  zone {rec['id']} ({rec['severity']}): TTF ~{rec['ttf_days']:.0f} d "
                  f"-> ~{rec['failure_date_est']}  (R²={rec['r2']}, "
                  f"net {rec['net_velocity_mmyr']:+.0f} mm/yr)")
    else:
        print("  No zone shows statistically-significant acceleration in this window "
              "(expected for a short, noisy series — see HONEST LIMITS in the header).")
    print(f"  -> {out_dir/'ttf_report.json'} , ttf_report.md")
    return 0


def write_markdown(path: Path, report: dict, accel, dates) -> None:
    c = report["counts"]
    lines = [
        f"# Inverse-velocity time-to-failure — {report['stack']}", "",
        "Fukuzono/Voight inverse-velocity screen of the alert zones. **Scenario-independent**",
        "(a property of the measured motion). A zone is ACCELERATING only when its inverse-",
        f"velocity trend is significantly decreasing (R²≥{report['params']['r2_min']}) and the",
        f"projected failure lands within {report['params']['horizon_days']:.0f} days. Treat any",
        "TTF as a **screening flag to watch, not a calibrated prediction** (~14 epochs, ~3.5",
        "months, ~30 mm/yr noise).", "",
        f"- zones screened: **{report['n_zones']}**",
        f"- **ACCELERATING (within horizon): {c['ACCELERATING']}**",
        f"- accelerating but failure beyond horizon: {c['ACCEL_BEYOND_HORIZON']}",
        f"- steady / not consistently creeping: {c['STEADY']}",
        f"- insufficient data: {c['INSUFFICIENT']}", "",
    ]
    if accel:
        lines += ["## Accelerating zones (soonest first)", "",
                  "| zone | severity | net vel (mm/yr) | R² | TTF (days) | est. failure |",
                  "|---|---|---|---|---|---|"]
        for rec, _ in accel:
            lines.append(f"| {rec['id']} | {rec['severity']} | {rec['net_velocity_mmyr']:+.0f} "
                         f"| {rec['r2']} | {rec['ttf_days']:.0f} | {rec.get('failure_date_est','-')} |")
    else:
        lines += ["## Result", "",
                  "**No zone shows statistically-significant acceleration** in this observation",
                  "window. This is the expected, honest outcome for a short/noisy series and means",
                  "the flagged zones are creeping *steadily*, not visibly accelerating toward",
                  "failure — not that they are safe. Re-run as the time series lengthens."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

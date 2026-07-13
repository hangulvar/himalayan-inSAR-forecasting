#!/usr/bin/env python
"""per_zone_gate.py — make the operational alarm vary PER ZONE (RESULTS_AND_KPIS.md §19).

The §17 temporal gate is AOI-wide: one rainfall exceedance E(t) per day, so the whole footprint
is DORMANT/WATCH/ALERT together. The honest per-zone differentiator here is NOT per-zone rainfall
(rain is ~uniform at IMERG's ~10 km over a ~22 km AOI, and letting the footprint grow on wet days
re-introduces the §16b over-flag) — it is each zone's intrinsic VULNERABILITY.

Because FS is exactly linear in saturation m (infinite-slope), each zone has a CRITICAL SATURATION
    m* = (1 - FS_dry) / (FS_sat - FS_dry)
— the wetness at which THAT zone crosses FS = 1. A zone with low m* fails when barely wet (most
dangerous); one with m* near the operational 0.40 only fails when very wet. We sample FS_dry/FS_sat
at each operational zone's pixel, solve m*, and then:

  WHEN (regional)  : the §17 gate on E(t) decides IF an alarm is raised today (DORMANT/WATCH/ALERT).
  WHERE (per zone) : on a WATCH/ALERT day, the ACTIVE zones are those whose m* the day's saturation
                     m(t) has reached (m* <= m(t)) — capped at the validated footprint (never adds
                     zones from outside it, so no ballooning).

So on a drier day only the most marginal (low-m*) zones are active; on a very wet day more of the
88 escalate — a genuine per-zone alarm, ranked by vulnerability, that an operator can act on.

  docker compose run --rm insar python workflows/per_zone_gate.py
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
import rasterio  # noqa: E402

from config import load_config  # noqa: E402
from rainfall_id_threshold import THRESHOLDS, SLUG  # noqa: E402
from rainfall_specificity import peak_exceedance  # noqa: E402
from velocity_uncertainty import stack_noise, confidence  # noqa: E402  (§24 detection confidence)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAIN_DIR = PROJECT_ROOT / "data" / "rainfall"
_CFG = load_config()
_SFX = _CFG.data_suffix            # '' for ramban; '_<slug>' so AOIs coexist
_KAPPA = _CFG.kappa                # §45 TWI-distributed saturation slope (0 = uniform m)
HAZ_DIR = PROJECT_ROOT / "data" / f"hazard{_SFX}"
ALERTS_DIR = PROJECT_ROOT / "data" / f"alerts{_SFX}"

# Operational saturation baseline (m=0.50 under matric-suction §20 + the 12.5 m ALOS DEM §21;
# history m=0.40 flat -> 0.55 suction -> 0.50 +DEM) and the §17 temporal-gate thresholds.
M_OPERATIONAL = 0.50
WATCH_K, ALERT_K = 1.0, 2.0
# m* tiers (critical saturation): lower = fails at less wetness = more dangerous. Cuts sit
# below / around / above the operating saturation (matric-suction physics lifts m* into ~0.38-0.55).
TIERS = [(0.45, "fails-by-a-moderately-wet-day"), (0.52, "fails-on-a-wet-day"),
         (1.01, "fails-only-when-very-wet")]


def tier_of(mstar: float) -> str:
    for cut, name in TIERS:
        if mstar < cut:
            return name
    return TIERS[-1][1]


# Standing-product stack list (NOT the live connectivity snapshot — see the
# shared helper's docstring + error log 2026-07-13).
from stacks import product_stacks  # noqa: E402


def load_daily(csv_path: Path):
    """date[], water_mm[], saturation m[] from the wetness CSV (single source for both)."""
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    dates = [date.fromisoformat(r["date"]) for r in rows]
    water = np.array([float(r["water_mm"]) for r in rows])
    m = np.array([float(r["wetness_0_1"]) for r in rows])
    return dates, water, m


def critical_saturation(fs_dry: float, fs_sat: float) -> float | None:
    """m* solving FS_dry + m*(FS_sat - FS_dry) = 1, clipped to [0, 1]. None if degenerate."""
    denom = fs_sat - fs_dry
    if not np.isfinite(fs_dry) or not np.isfinite(fs_sat) or denom >= 0:
        return None              # saturation must REDUCE FS for a valid m*
    return float(np.clip((1.0 - fs_dry) / denom, 0.0, 1.0))


def collect_zones(stacks: list[str]) -> list[dict]:
    """Per-stack operational alert zones with their critical saturation m* (sampled at the
    zone's centroid pixel from that stack's FS_dry/FS_sat rasters)."""
    zones: list[dict] = []
    for s in stacks:
        af = ALERTS_DIR / s / "alerts_operational.json"
        if not af.exists():
            continue
        fd = HAZ_DIR / f"{s}_FS_dry.tif"
        fsat = HAZ_DIR / f"{s}_FS_saturated.tif"
        if not (fd.exists() and fsat.exists()):
            continue
        with rasterio.open(fd) as d:
            fs_dry = d.read(1)
        with rasterio.open(fsat) as d:
            fs_sat = d.read(1)
        # TWI-distributed saturation (§45): a zone in wet, convergent terrain (high TWI)
        # experiences an effective saturation m + kappa*(TWI - TWI_mean), so it crosses
        # FS=1 at a LOWER AOI-mean wetness. We fold that into an EFFECTIVE threshold
        # m*_eff = clip(m* - kappa*(TWI_zone - TWI_mean), 0, 1) and gate on m*_eff. kappa=0
        # -> m*_eff == m* exactly (outputs byte-identical to the uniform-m gate).
        twi = twi_mean = None
        twip = HAZ_DIR / f"{s}_twi.tif"
        if _KAPPA and twip.exists():
            with rasterio.open(twip) as d:
                twi = d.read(1)
            twi_mean = float(np.nanmean(twi))
        sigma_s = stack_noise(s)            # §24 per-stack velocity noise floor (mm/yr)
        for a in json.loads(af.read_text(encoding="utf-8")).get("alerts", []):
            r, c = a["pixel_rowcol"]
            if not (0 <= r < fs_dry.shape[0] and 0 <= c < fs_dry.shape[1]):
                continue
            mstar = critical_saturation(float(fs_dry[r, c]), float(fs_sat[r, c]))
            if mstar is None:
                continue
            twi_zone = (float(twi[r, c]) if twi is not None and np.isfinite(twi[r, c])
                        else None)
            mstar_eff = (float(np.clip(mstar - _KAPPA * (twi_zone - twi_mean), 0.0, 1.0))
                         if twi_zone is not None else mstar)
            lon, lat = a["centroid_lonlat"]
            creep = a.get("mean_velocity_mmyr")
            conf = (round(confidence(float(creep), sigma_s), 3)
                    if sigma_s and creep is not None else None)
            zones.append({
                "stack": s, "id": a["id"], "lon": round(lon, 5), "lat": round(lat, 5),
                "severity": a["severity"], "fs_dry": round(float(fs_dry[r, c]), 3),
                "fs_sat": round(float(fs_sat[r, c]), 3), "fs_0p40": a.get("mean_fs"),
                "m_star": round(mstar, 3), "m_star_eff": round(mstar_eff, 3),
                "twi": round(twi_zone, 2) if twi_zone is not None else None,
                "tier": tier_of(mstar_eff), "creep_mmyr": creep,
                "detection_confidence": conf, "n_pixels": a.get("n_pixels"),
            })
    zones.sort(key=lambda z: z["m_star_eff"])     # activation order (== m* when kappa=0)
    return zones


def regional_levels(E: np.ndarray) -> list[str]:
    return ["ALERT" if e >= ALERT_K else "WATCH" if e >= WATCH_K else "DORMANT" for e in E]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(RAIN_DIR / f"{SLUG}_wetness_daily.csv"))
    ap.add_argument("--threshold", choices=sorted(THRESHOLDS), default="nwhimalaya")
    ap.add_argument("--stacks", nargs="*", default=None)
    ap.add_argument("--as-of", default=None, help="Date YYYY-MM-DD for the active-zone snapshot "
                                                  "(default: the season peak-E day).")
    args = ap.parse_args()

    stacks = args.stacks or product_stacks()
    zones = collect_zones(stacks)
    if not zones:
        raise SystemExit("No operational zones found — run run_multistack.py first.")
    mstars = np.array([z["m_star"] for z in zones])          # intrinsic vulnerability spread
    mstars_eff = np.array([z["m_star_eff"] for z in zones])  # activation thresholds (§45 kappa)

    thr = THRESHOLDS[args.threshold]
    dates, water, m = load_daily(Path(args.csv))
    E, _ = peak_exceedance(water, thr["a"], thr["b"])
    levels = regional_levels(E)

    # Per-day active-zone count: regional gate ON (WATCH+) AND the zone's effective critical
    # saturation m*_eff reached by today's AOI-mean m(t) (m*_eff == m* when kappa=0).
    timeline = []
    for d, lv, mi, ei in zip(dates, levels, m, E):
        active = int(np.sum(mstars_eff <= mi)) if lv in ("WATCH", "ALERT") else 0
        timeline.append({"date": d.isoformat(), "saturation_m": round(float(mi), 3),
                         "exceedance_E": round(float(ei), 3), "regional_level": lv,
                         "n_active_zones": active})

    # As-of snapshot.
    as_of_i = (dates.index(date.fromisoformat(args.as_of)) if args.as_of
               else int(np.argmax(E)))
    as_of = dates[as_of_i]
    m_now, lv_now = float(m[as_of_i]), levels[as_of_i]
    active_now = ([z for z in zones if z["m_star_eff"] <= m_now]
                  if lv_now in ("WATCH", "ALERT") else [])

    from collections import Counter
    tier_counts = Counter(z["tier"] for z in zones)
    report = {
        "n_operational_zones": len(zones), "stacks": stacks,
        "m_operational_baseline": M_OPERATIONAL, "kappa": _KAPPA,
        "threshold_id": args.threshold,
        "m_star_min": round(float(mstars.min()), 3), "m_star_median": round(float(np.median(mstars)), 3),
        "m_star_max": round(float(mstars.max()), 3),
        "tier_counts": dict(tier_counts),
        "as_of": as_of.isoformat(), "as_of_saturation_m": round(m_now, 3),
        "as_of_regional_level": lv_now, "as_of_n_active": len(active_now),
        "peak_active_zones": max(t["n_active_zones"] for t in timeline),
        "top10_most_vulnerable": zones[:10],
    }
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    (ALERTS_DIR / "per_zone_vulnerability.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_zone_table(ALERTS_DIR / "per_zone_vulnerability.csv", zones)
    write_timeline(ALERTS_DIR / "per_zone_active_timeline.csv", timeline)
    write_md(ALERTS_DIR / "per_zone_vulnerability.md", report, zones)
    make_figure(ALERTS_DIR / "per_zone_gate.png", mstars, timeline, dates, m, as_of_i)

    print(f"operational zones: {len(zones)} across {stacks}  (kappa={_KAPPA:g})")
    print(f"critical saturation m*: min={mstars.min():.3f} median={np.median(mstars):.3f} "
          f"max={mstars.max():.3f}  (operational baseline m={M_OPERATIONAL})")
    if _KAPPA:
        print(f"m*_eff (kappa-shifted) : min={mstars_eff.min():.3f} "
              f"median={np.median(mstars_eff):.3f} max={mstars_eff.max():.3f}")
    print("vulnerability tiers:", dict(tier_counts))
    print(f"as-of {as_of} (m={m_now:.2f}, regional {lv_now}): {len(active_now)} zones ACTIVE "
          f"(m* <= today's saturation)")
    print(f"  season peak active zones: {report['peak_active_zones']}")
    print("  top-5 most vulnerable (lowest m* = fails when barely wet):")
    for z in zones[:5]:
        print(f"    {z['stack'].replace('ASC_','')} #{z['id']}  m*={z['m_star']:.3f}  "
              f"FS0.40={z['fs_0p40']}  creep={z['creep_mmyr']}  {z['severity']}")
    print(f"  -> {ALERTS_DIR/'per_zone_vulnerability.json'} , .csv , .md , "
          f"per_zone_active_timeline.csv , per_zone_gate.png")
    return 0


def write_zone_table(path: Path, zones: list[dict]) -> None:
    cols = ["stack", "id", "lon", "lat", "severity", "fs_dry", "fs_sat", "fs_0p40",
            "m_star", "m_star_eff", "twi", "tier", "creep_mmyr", "detection_confidence",
            "n_pixels"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(zones)


def write_timeline(path: Path, timeline: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "saturation_m", "exceedance_E",
                                          "regional_level", "n_active_zones"])
        w.writeheader()
        w.writerows(timeline)


def write_md(path: Path, r: dict, zones: list[dict]) -> None:
    lines = [
        "# Per-zone temporal gating — critical saturation m* of the operational footprint", "",
        f"The §17 alarm is AOI-wide; this makes it **per zone** via each zone's critical saturation "
        f"**m\\* = (1−FS_dry)/(FS_sat−FS_dry)** — the wetness at which that zone crosses FS=1. The regional "
        f"gate (E) decides IF an alarm is raised; on a WATCH/ALERT day the **active** zones are those whose "
        f"m\\* the day's saturation has reached (m\\* ≤ m(t)), capped at the validated **{r['n_operational_zones']} "
        f"zones** (no ballooning).", "",
        f"- m\\* spread across the footprint: **min {r['m_star_min']} / median {r['m_star_median']} / "
        f"max {r['m_star_max']}** (operational baseline m={r['m_operational_baseline']}).",
        f"- vulnerability tiers: " + ", ".join(f"**{k}** {v}" for k, v in r["tier_counts"].items()) + ".",
        f"- as of **{r['as_of']}** (saturation m={r['as_of_saturation_m']}, regional "
        f"**{r['as_of_regional_level']}**): **{r['as_of_n_active']} zones ACTIVE**; season peak "
        f"**{r['peak_active_zones']}** active.", "",
        "## Top-10 most vulnerable zones (lowest m*_eff = fire first)", "",
        "| rank | stack | zone | m* | m*_eff (§45) | FS@0.40 | creep mm/yr | conf (§24) | "
        "severity | tier |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, z in enumerate(zones[:10], 1):
        lines.append(f"| {i} | {z['stack'].replace('ASC_','')} | {z['id']} | {z['m_star']} | "
                     f"{z['m_star_eff']} | {z['fs_0p40']} | {z['creep_mmyr']} | "
                     f"{z.get('detection_confidence', '—')} | {z['severity']} | {z['tier']} |")
    lines += ["",
              "_Honest scope: per-zone differentiation is by intrinsic VULNERABILITY (m*), not per-zone "
              "rainfall — rain is ~uniform at ~10 km over the ~22 km AOI, so the WHEN gate stays regional. "
              "The active set never exceeds the validated footprint, so it cannot re-introduce the §16b "
              "over-flag. Acute cloudbursts are caught by the regional E gate (§17); m(t) is the antecedent "
              "saturation, which a daily product builds up slowly._"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figure(path: Path, mstars, timeline, dates, m, as_of_i) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8))
    # Panel 1: histogram of m* across zones (the per-zone vulnerability spread).
    ax1.hist(mstars, bins=np.linspace(0, M_OPERATIONAL, 21), color="#cc6677", edgecolor="#fff")
    ax1.axvline(float(np.median(mstars)), color="#222", ls="--", lw=1, label=f"median {np.median(mstars):.2f}")
    ax1.set_xlabel("critical saturation m* (lower = fails when barely wet)")
    ax1.set_ylabel("operational zones")
    ax1.set_title("Per-zone vulnerability spread (m* of the operational footprint)")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)
    # Panel 2: per-day active-zone count vs daily saturation, regional ALERT shaded.
    x = np.arange(len(timeline))
    nact = np.array([t["n_active_zones"] for t in timeline])
    ax2.fill_between(x, 0, nact, color="#dc2828", step="mid", alpha=0.7, label="active zones")
    ax2b = ax2.twinx()
    ax2b.plot(x, m, color="#4477aa", lw=1.2, label="AOI saturation m(t)")
    ax2b.set_ylabel("saturation m(t)", color="#4477aa")
    ax2.axvline(as_of_i, color="#222", lw=1.0, ls=":")
    ax2.set_ylabel("active operational zones", color="#aa0000")
    tick = np.linspace(0, len(timeline) - 1, 8).astype(int)
    ax2.set_xticks(tick); ax2.set_xticklabels([dates[i].strftime("%b %d") for i in tick])
    ax2.set_title("Per-day ACTIVE operational zones (regional gate ON & m* reached) vs saturation")
    ax2.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

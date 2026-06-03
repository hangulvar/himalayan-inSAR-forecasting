#!/usr/bin/env python
"""compare_tropo_methods.py — a Bekaert-style statistical comparison of MintPy
tropospheric-correction methods on frame106, the concrete attack on the ~30 mm/yr
atmospheric-noise floor.

Three velocity rasters (same 309x353 grid, same pixels), produced by re-running MintPy
with three `mintpy.troposphericDelay.method` settings:
  * none   = velocity_mintpy.tif        no correction (step 2 baseline)
  * era5   = velocity_mintpy_era5.tif    weather model (pyaps/ERA5)
  * height = velocity_mintpy_height.tif  empirical height-correlation (topo-correlated)

For each, over the COMMON coherence>=0.7 + custom-valid pixel set (identical across
methods, because temporal coherence is from the inversion BEFORE the tropo step), we
report two complementary noise metrics:
  (1) velocity STD (mm/yr) — the scatter / atmospheric-noise proxy; LOWER = quieter.
  (2) agreement with the independent custom SBAS inverter (Pearson r, raw + high-pass,
      and offset-removed RMS) — does the correction make the two engines AGREE more?

Method references (for the docs): Bekaert et al. (2015, RSE 170:40-47, "TRAIN") motivate
comparing methods; Doin et al. (2009, J.Appl.Geophys. 69:35-50) = the height-correlation/
power-law empirical correction; Jolivet et al. (2011, GRL 38:L17311) + ERA5 (Hersbach et
al. 2020) = the weather-model (pyaps) path; Yunjun et al. (2019, Comput.Geosci. 133) = MintPy.

  docker compose run --rm insar python workflows/compare_tropo_methods.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))
from crossval_mintpy import read, nan_gaussian_highpass, pearson   # shared helpers

OUT_DIR = PROJECT_ROOT / "data" / "mintpy"

METHODS = {
    "none":   ("velocity_mintpy.tif",        "no correction (baseline)"),
    "era5":   ("velocity_mintpy_era5.tif",   "ERA5 weather model (pyaps; Jolivet 2011)"),
    "height": ("velocity_mintpy_height.tif", "height-correlation empirical (Doin 2009)"),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stack", default="ASC_path27_frame106")
    ap.add_argument("--coh-thr", type=float, default=0.7)
    ap.add_argument("--hp-sigma-px", type=float, default=30.0)
    args = ap.parse_args()
    stack = args.stack

    vel = PROJECT_ROOT / "data" / "velocity"
    mp = OUT_DIR / stack / "mintpy_out"

    custom_raw = read(vel / f"{stack}_mean_velocity_los.tif")            # mm/yr, coh>=0.7
    custom_hp = read(vel / f"{stack}_mean_velocity_los_highpass.tif")
    coh = read(mp / "temporalCoherence_mintpy.tif")

    vels = {}
    for key, (fname, _label) in METHODS.items():
        p = mp / fname
        if not p.exists():
            raise SystemExit(f"Missing {p} — run the MintPy {key} pass first "
                             f"(run_mintpy_*_f106.sh / --troposphericDelay.method).")
        vels[key] = read(p) * 1000.0                                     # m/yr -> mm/yr

    # Common set: custom-valid AND coh>=0.7 AND every method finite -> identical pixels.
    common = np.isfinite(custom_raw) & np.isfinite(custom_hp) & (coh >= args.coh_thr)
    for v in vels.values():
        common &= np.isfinite(v)
    n = int(common.sum())
    if n < 100:
        raise SystemExit(f"Too few common pixels ({n}).")

    base_std = float(np.nanstd(vels["none"][common]))
    rows = {}
    for key, (fname, label) in METHODS.items():
        v = vels[key]
        # high-pass from the broad coh-masked support (not the sparse common set) so the
        # Gaussian low-pass has enough neighbours; then evaluate only where it is finite.
        v_cohmasked = np.where((coh >= args.coh_thr) & np.isfinite(v), v, np.nan).astype(np.float32)
        v_hp = nan_gaussian_highpass(v_cohmasked, args.hp_sigma_px)
        m_hp = common & np.isfinite(v_hp)
        d = (v[common] - custom_raw[common]).astype(np.float64)
        d -= d.mean()
        rows[key] = {
            "file": fname, "label": label,
            "std_mmyr": round(float(np.nanstd(v[common])), 1),
            "std_reduction_pct": round(100.0 * (base_std - float(np.nanstd(v[common]))) / base_std, 1),
            "r_vs_custom_raw": round(pearson(v, custom_raw, common), 3),
            "r_vs_custom_hp": round(pearson(v, custom_hp, common), 3),
            "rHP_vs_custom_hp": round(pearson(v_hp, custom_hp, m_hp), 3),
            "rms_offsetrm_mmyr": round(float(np.sqrt((d * d).mean())), 1),
        }

    best_std = min(rows, key=lambda k: rows[k]["std_mmyr"])
    best_r = max(rows, key=lambda k: rows[k]["r_vs_custom_raw"])
    report = {
        "stack": stack, "coh_thr": args.coh_thr, "common_px": n,
        "custom_std_mmyr": round(float(np.nanstd(custom_raw[common])), 1),
        "methods": rows,
        "lowest_scatter": best_std, "best_agreement_with_custom": best_r,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tropo_method_comparison.json").write_text(json.dumps(report, indent=2),
                                                          encoding="utf-8")
    write_md(OUT_DIR / "tropo_method_comparison.md", report)
    make_figure(OUT_DIR / "tropo_method_comparison.png", rows)

    print(f"stack={stack}  common coh>=0.7 px = {n:,}  (custom std {report['custom_std_mmyr']} mm/yr)")
    print(f"{'method':8s} {'std(mm/yr)':>11s} {'Δstd':>6s} {'r vs custom':>12s} {'rHP':>6s} {'RMS':>6s}")
    for key in METHODS:
        r = rows[key]
        print(f"{key:8s} {r['std_mmyr']:>11.1f} {r['std_reduction_pct']:>5.0f}% "
              f"{r['r_vs_custom_raw']:>+12.3f} {r['rHP_vs_custom_hp']:>+6.3f} {r['rms_offsetrm_mmyr']:>6.1f}")
    print(f"-> lowest scatter: {best_std}  |  best agreement with custom: {best_r}")
    print(f"-> {OUT_DIR/'tropo_method_comparison.json'} , .md , .png")
    return 0


def write_md(path: Path, r: dict) -> None:
    lines = [
        "# MintPy tropospheric-correction method comparison — frame106", "",
        f"Attack on the ~30 mm/yr atmospheric-noise floor: three MintPy tropo methods on the SAME "
        f"{r['common_px']:,} coherence>=0.7 pixels (custom inverter std {r['custom_std_mmyr']} mm/yr "
        f"for reference). A Bekaert et al. (2015, \"TRAIN\") style comparison.", "",
        "| method | velocity std (mm/yr) | std reduction | r vs custom (raw) | r (high-pass) | RMS off-rm |",
        "|---|---|---|---|---|---|",
    ]
    for key, m in r["methods"].items():
        lines.append(f"| **{key}** — {m['label']} | {m['std_mmyr']} | {m['std_reduction_pct']:+.0f}% | "
                     f"{m['r_vs_custom_raw']:+.3f} | {m['rHP_vs_custom_hp']:+.3f} | {m['rms_offsetrm_mmyr']} |")
    lines += ["",
              f"- **Lowest scatter (quietest):** `{r['lowest_scatter']}`.",
              f"- **Best agreement with the independent custom inverter:** `{r['best_agreement_with_custom']}`.",
              "",
              "**Reading it:** lower *std* = less atmospheric noise; higher *r vs custom* = the two "
              "independent SBAS engines agree more (the correction removed real atmosphere, not signal). "
              "`none` is the no-correction baseline; `era5` is the weather-model path already adopted; "
              "`height` is the empirical topo-correlated correction (no external data) — the Python-native "
              "analog of TRAIN's power-law method.", "",
              "**References:** Bekaert et al. (2015) *Remote Sens. Environ.* 170:40-47 (TRAIN; method "
              "comparison) · Doin et al. (2009) *J. Appl. Geophys.* 69:35-50 (height-correlation/power-law) "
              "· Jolivet et al. (2011) *Geophys. Res. Lett.* 38:L17311 + Hersbach et al. (2020) (ERA5/pyaps) "
              "· Yunjun et al. (2019) *Comput. Geosci.* 133:104331 (MintPy)."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figure(path: Path, rows: dict) -> None:
    keys = list(rows)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))
    colors = ["#bbbbbb", "#4477aa", "#ee7733"]
    ax1.bar(keys, [rows[k]["std_mmyr"] for k in keys], color=colors)
    ax1.set_ylabel("velocity std (mm/yr)"); ax1.set_title("Scatter (lower = quieter)")
    for i, k in enumerate(keys):
        ax1.text(i, rows[k]["std_mmyr"], f"{rows[k]['std_mmyr']:.0f}", ha="center", va="bottom", fontsize=9)
    ax1.grid(alpha=0.3, axis="y")
    ax2.bar(keys, [rows[k]["r_vs_custom_raw"] for k in keys], color=colors)
    ax2.set_ylabel("Pearson r vs custom inverter"); ax2.set_title("Agreement with the 2nd engine (higher = better)")
    for i, k in enumerate(keys):
        ax2.text(i, rows[k]["r_vs_custom_raw"], f"{rows[k]['r_vs_custom_raw']:+.2f}",
                 ha="center", va="bottom", fontsize=9)
    ax2.grid(alpha=0.3, axis="y")
    fig.suptitle("MintPy tropospheric-correction comparison (frame106) — attacking the ~30 mm/yr floor")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())

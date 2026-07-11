#!/usr/bin/env python
"""_gacos_crosscheck.py — Area 1 GACOS tropospheric cross-check for Vaishno Devi.

Independent-model test of the project's atmospheric quarantine (phase_elevation_audit.py):
for each operational 12-day pair on frame103/frame105, convert the GACOS zenith-delay
maps into a PREDICTED atmospheric phase signal and ask two questions:

  (1) Does GACOS's own delay field correlate with elevation the same way our observed
      phase does? (GACOS R^2 vs elevation, compared to our existing audit R^2)
  (2) Does GACOS's predicted delay pattern correlate SPATIALLY with our actual observed
      masked displacement for that pair? (direct GACOS-vs-observed correlation)

Physics: ZTD (zenith total delay, m) -> slant/LOS delay via the standard mapping function
LOS = ZTD / sin(theta), theta = look-vector elevation above horizon (HyP3 lv_theta,
radians). An interferometric pair's atmospheric phase screen is the delay DIFFERENCE
between its two epochs; convert to the same "apparent displacement" convention as
feature_engineering.py (disp = -phase*lambda/4pi) for direct comparability.

One-off analysis script (leading underscore, like _gacos_epochs.py) — not part of the
regular pipeline. Requires the GACOS ZTD grids already extracted to
data/hazard_vaishnodevi/gacos2_frame{103,105}/<YYYYMMDD>.ztd.tif (same shared grid).

  docker compose run --rm insar python workflows/_gacos_crosscheck.py
"""
from __future__ import annotations

import csv
import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.warp import Resampling, reproject  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GACOS_DIR = PROJECT_ROOT / "data" / "hazard_vaishnodevi"
TIFF_DIR = PROJECT_ROOT / "data" / "processed_tiffs"
QA_DIR = PROJECT_ROOT / "data" / "qa_masks"
AUDIT_CSV = QA_DIR / "_atmospheric_audit.csv"
OUT_DIR = GACOS_DIR

WAVELENGTH_M = 0.055465763  # Sentinel-1 C-band, same constant as feature_engineering.py

# (gacos subdir, epoch dates) per stack; consecutive pairs are built from these.
STACKS = {
    "ASC_path27_frame105": ("gacos2_frame105",
                             ["20260501", "20260513", "20260525", "20260606", "20260618"]),
    "ASC_path100_frame103": ("gacos2_frame103",
                              ["20260506", "20260518", "20260530", "20260611", "20260623"]),
}


def load_audit_r2() -> dict[str, float]:
    out = {}
    with AUDIT_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["product"]] = float(row["r_squared"])
    return out


def find_product(d1: str, d2: str) -> Path | None:
    hits = list(TIFF_DIR.glob(f"S1AA_{d1}T*_{d2}T*"))
    return hits[0] if hits else None


def reproject_to(src_path: Path, transform, crs, w, h, resampling) -> np.ndarray:
    dst = np.full((h, w), np.nan, dtype=np.float32)
    with rasterio.open(src_path) as src:
        reproject(source=rasterio.band(src, 1), destination=dst,
                  src_transform=src.transform, src_crs=src.crs,
                  dst_transform=transform, dst_crs=crs,
                  resampling=resampling, src_nodata=src.nodata, dst_nodata=np.nan)
    return dst


def pearson_r2(a: np.ndarray, b: np.ndarray, m: np.ndarray) -> tuple[float, float, int]:
    x = a[m].astype(np.float64) - a[m].astype(np.float64).mean()
    y = b[m].astype(np.float64) - b[m].astype(np.float64).mean()
    denom = np.sqrt((x * x).sum() * (y * y).sum())
    r = float((x * y).sum() / denom) if denom > 0 else float("nan")
    return r, r * r, int(m.sum())


def main() -> int:
    audit = load_audit_r2()
    rows = []

    for stack, (gacos_sub, dates) in STACKS.items():
        gdir = GACOS_DIR / gacos_sub
        for d1, d2 in zip(dates, dates[1:]):
            f1, f2 = gdir / f"{d1}.ztd.tif", gdir / f"{d2}.ztd.tif"
            if not (f1.exists() and f2.exists()):
                print(f"SKIP {stack} {d1}->{d2}: missing GACOS file(s)")
                continue
            prod_dir = find_product(d1, d2)
            if prod_dir is None:
                print(f"SKIP {stack} {d1}->{d2}: no matching product in processed_tiffs")
                continue
            prod = prod_dir.name

            with rasterio.open(f1) as ds:
                transform, crs, w, h = ds.transform, ds.crs, ds.width, ds.height
                ztd1 = ds.read(1).astype(np.float64)
            with rasterio.open(f2) as ds:
                ztd2 = ds.read(1).astype(np.float64)

            theta = reproject_to(prod_dir / f"{prod}_lv_theta.tif", transform, crs, w, h,
                                 Resampling.average).astype(np.float64)
            dem = reproject_to(prod_dir / f"{prod}_dem.tif", transform, crs, w, h,
                               Resampling.average)
            masked_disp_path = QA_DIR / prod / f"{prod}_masked_disp.tif"
            obs = reproject_to(masked_disp_path, transform, crs, w, h,
                               Resampling.average) if masked_disp_path.exists() else None

            with np.errstate(invalid="ignore", divide="ignore"):
                los_delay1 = ztd1 / np.sin(theta)
                los_delay2 = ztd2 / np.sin(theta)
            d_los = los_delay2 - los_delay1
            predicted_disp_mm = (-d_los * WAVELENGTH_M / (4.0 * np.pi)) * 1000.0

            valid_dem = np.isfinite(predicted_disp_mm) & np.isfinite(dem)
            r_elev, r2_elev, n_elev = pearson_r2(predicted_disp_mm, dem, valid_dem)

            if obs is not None:
                valid_obs = valid_dem & np.isfinite(obs)
                obs_mm = obs * 1000.0
                r_obs, r2_obs, n_obs = pearson_r2(predicted_disp_mm, obs_mm, valid_obs)
            else:
                r_obs = r2_obs = float("nan"); n_obs = 0

            row = {
                "stack": stack, "pair": f"{d1}-{d2}", "product": prod,
                "audit_r2": audit.get(prod),
                "gacos_r2_vs_elev": round(r2_elev, 4), "gacos_r_vs_elev": round(r_elev, 3),
                "n_elev": n_elev,
                "gacos_r2_vs_observed": round(r2_obs, 4) if np.isfinite(r2_obs) else None,
                "gacos_r_vs_observed": round(r_obs, 3) if np.isfinite(r_obs) else None,
                "n_observed": n_obs,
                "predicted_disp_mm_range": [round(float(np.nanmin(predicted_disp_mm)), 1),
                                             round(float(np.nanmax(predicted_disp_mm)), 1)],
            }
            rows.append(row)
            print(f"{stack:24s} {d1}-{d2}  audit_R2={row['audit_r2']:.3f}  "
                  f"GACOS_R2vsElev={r2_elev:.3f}  GACOS_R2vsObserved={row['gacos_r2_vs_observed']}"
                  f"  (n={n_elev}/{n_obs})")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {"rows": rows,
              "note": ("gacos_r2_vs_elev: does GACOS's own delay field correlate with "
                       "elevation on this pair (independent-model check on the SAME "
                       "physical hypothesis as the phase-elevation audit). "
                       "gacos_r2_vs_observed: does GACOS's predicted atmospheric-phase "
                       "PATTERN correlate with our actually-observed masked displacement "
                       "for that pair (the stronger, direct test).")}
    (OUT_DIR / "gacos_crosscheck.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_md(OUT_DIR / "gacos_crosscheck.md", rows)
    make_figure(OUT_DIR / "gacos_crosscheck.png", rows)
    print(f"\n-> {OUT_DIR / 'gacos_crosscheck.json'} , .md , .png")
    return 0


def write_md(path: Path, rows: list[dict]) -> None:
    lines = [
        "# GACOS tropospheric cross-check — Vaishno Devi operational stacks (Area 1)", "",
        "Independent-model test of the phase-elevation atmospheric audit: does an external "
        "weather-model tropospheric-delay product (GACOS) predict the same atmosphere we "
        "flag from the InSAR phase itself?", "",
        "| pair | our audit R² | GACOS R² vs elevation | GACOS R² vs OUR observed disp | n |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['stack'].replace('ASC_path','p')} {r['pair']} | "
                     f"{r['audit_r2']:.3f} | {r['gacos_r2_vs_elev']:.3f} | "
                     f"{r['gacos_r2_vs_observed'] if r['gacos_r2_vs_observed'] is not None else 'n/a'} | "
                     f"{r['n_elev']} |")
    lines += ["",
              "**Reading it:** `our audit R²` is the existing phase-vs-elevation atmospheric-",
              "quarantine metric (phase_elevation_audit.py) computed from OUR observed phase. "
              "`GACOS R² vs elevation` asks whether an INDEPENDENT physical model (ECMWF-based "
              "weather delay) predicts the same elevation-correlated pattern for that same pair "
              "— agreement is external validation of the audit; disagreement means either GACOS "
              "or the audit is picking up something the other misses. `GACOS R² vs OUR observed "
              "disp` is the direct, stronger test: does GACOS's predicted spatial delay pattern "
              "line up with what we actually measured for that pair (not just \"both correlate "
              "with elevation\", but \"they correlate with EACH OTHER\").", "",
              f"**Sample size caveat:** {len(rows)} pairs (the only epochs with GACOS coverage so "
              "far — the operational stacks' full spring-2026 chain). Small-n; a qualitative "
              "cross-check, not a statistically powered test.",
              "", "**Method:** ZTD -> slant delay via `LOS = ZTD / sin(lv_theta)` (lv_theta = "
              "HyP3 look-vector elevation above horizon, radians); pair delay difference -> "
              "predicted apparent displacement via the same `-phase*lambda/(4*pi)` convention as "
              "`feature_engineering.py`. All rasters resampled (area-average) onto the shared "
              "GACOS grid (~93 m) for comparison."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figure(path: Path, rows: list[dict]) -> None:
    labels = [r["pair"] for r in rows]
    audit = [r["audit_r2"] for r in rows]
    gacos_elev = [r["gacos_r2_vs_elev"] for r in rows]
    gacos_obs = [r["gacos_r2_vs_observed"] or 0 for r in rows]
    x = np.arange(len(labels)); width = 0.27
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(x - width, audit, width, label="our audit R² (phase vs elev)", color="#888888")
    ax.bar(x, gacos_elev, width, label="GACOS R² (predicted vs elev)", color="#4477aa")
    ax.bar(x + width, gacos_obs, width, label="GACOS R² (predicted vs OUR observed)", color="#ee7733")
    ax.axhline(0.5, color="red", ls="--", lw=0.8, label="quarantine line (0.5)")
    ax.axhline(0.3, color="orange", ls="--", lw=0.8, label="concern line (0.3)")
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("R²"); ax.set_title("GACOS tropospheric cross-check — VD operational stacks")
    ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

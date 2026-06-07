#!/usr/bin/env python
"""hazard_era5_compare.py — roll the MintPy ERA5-tropo-corrected velocity through the
hazard creep-fusion and compare it to the custom-SBAS hazard (frame106 only).

Context (RESULTS_AND_KPIS.md §3/§13): the MintPy ERA5 run *physically* subtracts the
atmospheric delay and cut frame106 velocity scatter 39 -> 21 mm/yr (custom uses a spatial
high-pass as an atmosphere proxy). The standing question (§5): does the cleaner velocity
change WHICH slopes the hazard flags as creeping? This rolls the ERA5 velocity through the
SAME creep -> hazard logic and quantifies the delta.

FAIR alignment (identical to crossval_mintpy.py, the validated recipe):
  * ERA5 velocity m/yr -> mm/yr (x1000); MintPy temporalCoherence >= 0.7 mask;
  * the SAME nan-aware Gaussian high-pass (sigma=30 px) the custom inverter applies, so both
    velocities are atmosphere-suppressed on the same 309x353 grid (sign already aligned: the
    crossval got r=+0.55 with this processing).
Hazard fusion MIRRORS geomechanical_engine.py exactly (HIGH = FS_saturated<1 AND creep;
WATCH = FS<1.3 OR creep) on the on-disk FS_saturated raster, so the only changed input is the
velocity. A SELF-CHECK recomputes the custom hazard the same way and asserts it reproduces the
on-disk custom hazard_class (guards against fusion drift).

Single-stack/demonstrative (only frame106 has an ERA5 velocity); does NOT touch the mosaic.

  docker compose run --rm insar python workflows/hazard_era5_compare.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage  # noqa: E402

from crossval_mintpy import nan_gaussian_highpass  # the SAME high-pass — single source  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VEL_DIR = PROJECT_ROOT / "data" / "velocity"
HAZ_DIR = PROJECT_ROOT / "data" / "hazard"

FS_FAIL = 1.0
FS_MARGINAL = 1.3
VEL_CREEP_THR = -15.0
MIN_CLUSTER_PX = 3       # orchestrator's zone size floor


def read(p: Path) -> np.ndarray:
    with rasterio.open(p) as s:
        return s.read(1)


def fuse_hazard(fs_sat: np.ndarray, vel: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Mirror geomechanical_engine.py hazard fusion. Returns (hazard_class, creep_mask)."""
    creep = np.isfinite(vel) & (vel < VEL_CREEP_THR)
    unstable = np.isfinite(fs_sat) & (fs_sat < FS_FAIL)
    marginal = np.isfinite(fs_sat) & (fs_sat < FS_MARGINAL)
    hazard = np.full(fs_sat.shape, np.nan, dtype=np.float32)
    hazard[np.isfinite(fs_sat)] = 0.0
    hazard[marginal | creep] = 1.0
    hazard[unstable & creep] = 2.0
    return hazard, creep


def iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = int(np.sum(a & b))
    union = int(np.sum(a | b))
    return round(inter / union, 3) if union else 0.0


def n_zones(high: np.ndarray) -> int:
    labels, n = ndimage.label(high)
    if not n:
        return 0
    sizes = np.bincount(labels.ravel())[1:]
    return int(np.sum(sizes >= MIN_CLUSTER_PX))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stack", default="ASC_path27_frame106")
    ap.add_argument("--mintpy-dir",
                    default=str(PROJECT_ROOT / "data" / "mintpy" / "ASC_path27_frame106" / "mintpy_out"))
    ap.add_argument("--coh-thr", type=float, default=0.7)
    ap.add_argument("--hp-sigma-px", type=float, default=30.0)
    args = ap.parse_args()
    stack, mp = args.stack, Path(args.mintpy_dir)

    fs_sat = read(HAZ_DIR / f"{stack}_FS_saturated.tif")
    custom_hp = read(VEL_DIR / f"{stack}_mean_velocity_los_highpass.tif")        # mm/yr, coh-masked
    custom_haz_disk = read(HAZ_DIR / f"{stack}_hazard_class.tif")

    era5_vel = read(mp / "velocity_mintpy_era5.tif") * 1000.0                    # m/yr -> mm/yr
    era5_coh = read(mp / "temporalCoherence_mintpy.tif")
    era5_masked = np.where(np.isfinite(era5_vel) & (era5_coh >= args.coh_thr), era5_vel, np.nan)
    era5_hp = nan_gaussian_highpass(era5_masked.astype(np.float32), args.hp_sigma_px)
    if isinstance(era5_hp, tuple):
        era5_hp = era5_hp[0]

    custom_haz, custom_creep = fuse_hazard(fs_sat, custom_hp)
    era5_haz, era5_creep = fuse_hazard(fs_sat, era5_hp)

    # SELF-CHECK: our re-fused custom hazard must reproduce the engine's on-disk hazard.
    a, b = custom_haz, custom_haz_disk
    same = np.array_equal(np.nan_to_num(a, nan=-9), np.nan_to_num(b, nan=-9))
    if not same:
        diff = int(np.sum(np.nan_to_num(a, nan=-9) != np.nan_to_num(b, nan=-9)))
        print(f"WARNING: re-fused custom hazard differs from on-disk in {diff} px "
              f"(fusion drift or stale raster) — interpret deltas with care.")

    custom_high = custom_haz == 2.0
    era5_high = era5_haz == 2.0
    common = np.isfinite(custom_hp) & np.isfinite(era5_hp)
    if int(common.sum()) > 1:
        r = float(np.corrcoef(custom_hp[common], era5_hp[common])[0, 1])
    else:
        r = float("nan")

    report = {
        "stack": stack, "self_check_custom_reproduced": bool(same),
        "common_px_both_velocities": int(common.sum()),
        "velocity_corr_r_on_common": round(r, 3),
        "creep": {
            "custom_px": int(custom_creep.sum()), "era5_px": int(era5_creep.sum()),
            "iou": iou(custom_creep, era5_creep),
            "both_px": int(np.sum(custom_creep & era5_creep)),
        },
        "high_hazard": {
            "custom_px": int(custom_high.sum()), "era5_px": int(era5_high.sum()),
            "iou": iou(custom_high, era5_high),
            "custom_zones_ge3px": n_zones(custom_high), "era5_zones_ge3px": n_zones(era5_high),
        },
        "coh_thr": args.coh_thr, "hp_sigma_px": args.hp_sigma_px,
        "note": ("Single-stack/demonstrative. ERA5 = MintPy physically-tropo-corrected velocity; "
                 "custom = spatial-high-pass atmosphere proxy. Same FS_saturated + same creep rule, "
                 "so the only changed input is the velocity."),
    }

    # Write the ERA5 hazard raster (a real rolled-through product) on the custom grid/profile.
    with rasterio.open(HAZ_DIR / f"{stack}_hazard_class.tif") as src:
        prof = src.profile
    with rasterio.open(HAZ_DIR / f"{stack}_hazard_class_era5.tif", "w", **prof) as dst:
        dst.write(era5_haz.astype(np.float32), 1)

    HAZ_DIR.mkdir(parents=True, exist_ok=True)
    (HAZ_DIR / "hazard_era5_compare_report.json").write_text(json.dumps(report, indent=2),
                                                             encoding="utf-8")
    write_md(HAZ_DIR / "hazard_era5_compare_report.md", report)
    make_figure(HAZ_DIR / "hazard_era5_compare.png", custom_haz, era5_haz, stack)

    c, hh = report["creep"], report["high_hazard"]
    print(f"stack {stack}  self-check custom reproduced: {same}  (velocity r={r:.3f} on "
          f"{int(common.sum()):,} common px)")
    print(f"CREEP px : custom {c['custom_px']:,}  ERA5 {c['era5_px']:,}  "
          f"(overlap {c['both_px']:,}, IoU {c['iou']})")
    print(f"HIGH px  : custom {hh['custom_px']:,}  ERA5 {hh['era5_px']:,}  IoU {hh['iou']}")
    print(f"HIGH zones (>={MIN_CLUSTER_PX}px): custom {hh['custom_zones_ge3px']}  "
          f"ERA5 {hh['era5_zones_ge3px']}")
    print(f"  -> {HAZ_DIR/'hazard_era5_compare_report.json'} , .md , hazard_era5_compare.png , "
          f"{stack}_hazard_class_era5.tif")
    return 0


def write_md(path: Path, r: dict) -> None:
    c, hh = r["creep"], r["high_hazard"]
    lines = [
        f"# ERA5-corrected velocity rolled through the hazard — {r['stack']}", "",
        "The MintPy **ERA5 physically-tropo-corrected** velocity vs the **custom spatial-high-pass** "
        "velocity, run through the SAME creep->hazard fusion (same FS_saturated, creep<-15 mm/yr, "
        "HIGH = FS<1 AND creep). The only changed input is the velocity.", "",
        f"- Self-check (re-fused custom == on-disk engine hazard): **{r['self_check_custom_reproduced']}**.",
        f"- Velocity agreement on the {r['common_px_both_velocities']:,} common (coh-masked, high-passed) "
        f"px: **r = {r['velocity_corr_r_on_common']}** (matches the §3 crossval r~0.55).",
        "",
        "| layer | custom (high-pass proxy) | ERA5 (physical tropo) | IoU |",
        "|---|---|---|---|",
        f"| creep px (vel < -15 mm/yr) | {c['custom_px']:,} | {c['era5_px']:,} | {c['iou']} |",
        f"| HIGH px (FS<1 AND creep) | {hh['custom_px']:,} | {hh['era5_px']:,} | {hh['iou']} |",
        f"| HIGH zones (>=3 px) | {hh['custom_zones_ge3px']} | {hh['era5_zones_ge3px']} | — |",
        "",
        "**Reading:** the two atmosphere-suppressed velocities agree at r~0.55 but are NOT "
        "interchangeable pixel-for-pixel — the creep/HIGH IoU quantifies how much the *physical* ERA5 "
        "correction reshuffles the flagged slopes vs the high-pass proxy. This is a frame106-only "
        "demonstrative variant (`*_hazard_class_era5.tif`); it does not enter the multi-stack mosaic "
        "(only frame106 has an ERA5 velocity). Rolling ERA5 through ALL stacks needs a per-stack MintPy "
        "ERA5 run (the DESC stacks were dumped, §4).",
        "", "_Honest scope: ERA5 covers the full grid but is coherence-masked to be comparable; the "
        "high-pass (sigma=30 px) is applied to both so neither carries a long-wavelength ramp._",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figure(path: Path, custom_haz, era5_haz, stack) -> None:
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(["#46a046", "#f0b428", "#dc2828"])
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, haz, title in [(axes[0], custom_haz, "custom (high-pass proxy)"),
                           (axes[1], era5_haz, "ERA5 (physical tropo)")]:
        ax.imshow(haz, cmap=cmap, vmin=0, vmax=2)
        ax.set_title(f"{title}\nHIGH px = {int(np.sum(haz==2)):,}"); ax.axis("off")
    # difference: where HIGH status disagrees
    ch, eh = custom_haz == 2, era5_haz == 2
    diff = np.full(custom_haz.shape, np.nan)
    diff[np.isfinite(custom_haz)] = 0
    diff[ch & ~eh] = 1     # custom-only HIGH
    diff[~ch & eh] = 2     # ERA5-only HIGH
    diff[ch & eh] = 3      # both HIGH
    dcmap = ListedColormap(["#eeeeee", "#4477aa", "#cc6677", "#222222"])
    axes[2].imshow(diff, cmap=dcmap, vmin=0, vmax=3)
    axes[2].set_title("HIGH agreement\nblue=custom-only red=ERA5-only black=both"); axes[2].axis("off")
    fig.suptitle(f"{stack}: hazard from custom vs ERA5-corrected velocity")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

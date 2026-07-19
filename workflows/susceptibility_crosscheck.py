#!/usr/bin/env python
"""susceptibility_crosscheck.py — Tier 3a of the Strengthening Plan (§56): would a plain
STATISTICAL susceptibility map beat our physics map on this ground? The reviewer question the
project has carried since Area 4 — answered on the same sample, same protocol, so the numbers
are comparable, whichever way they land.

METHOD (Ramban — the AOI with the 138-point GSI field-validated inventory):
  • Grid: the frame106 80 m stack grid (the AOI's widest-coverage stack).
  • Features (terrain only, nothing from radar or the physics engine): elevation, slope, TWI,
    curvature + roughness (both derived from the stack DEM).
  • Positives: GSI inventory points landing on valid pixels; negatives: seeded random valid
    pixels (the back-test's null-control philosophy — luck as the baseline).
  • Model: standardized logistic regression trained by IRLS (numpy only — the lean image has
    no sklearn; a linear model is the honest baseline anyway), scored by 5-fold CV AUC.
  • Comparators on the SAME points: the physics map (score = −FS_saturated: lower FS = more
    hazardous), and the rank-mean ENSEMBLE of the two.

Outputs data/inventory/susceptibility_crosscheck.{json,md}; headline -> ledger (§60).
  docker compose run --rm insar python workflows/susceptibility_crosscheck.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

HAZ = PROJECT_ROOT / "data" / "hazard"
STACK = "ASC_path27_frame106"
DEM_TIF = next((PROJECT_ROOT / "data" / "processed_tiffs").glob("*/*_dem.tif"))
INV = PROJECT_ROOT / "data" / "inventory" / "gsi_inventory_aoi.geojson"
SEED = 20260718
N_NEG = 2000
K_FOLD = 5


def _read(path: Path):
    with rasterio.open(path) as ds:
        return ds.read(1).astype(np.float64), ds.transform, ds.crs


def _sample(arr, transform, xs, ys):
    rows, cols = rasterio.transform.rowcol(transform, xs, ys)
    rows, cols = np.asarray(rows), np.asarray(cols)
    ok = (rows >= 0) & (rows < arr.shape[0]) & (cols >= 0) & (cols < arr.shape[1])
    out = np.full(len(xs), np.nan)
    out[ok] = arr[rows[ok], cols[ok]]
    return out


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank AUC (Mann-Whitney), NaN-safe."""
    ok = np.isfinite(scores)
    s, y = scores[ok], labels[ok]
    r = np.argsort(np.argsort(s)) + 1.0
    n1, n0 = int(y.sum()), int((1 - y).sum())
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def irls_logistic(X: np.ndarray, y: np.ndarray, iters: int = 30) -> np.ndarray:
    """Standardized-feature logistic regression via IRLS; returns weights (incl. intercept)."""
    Xb = np.column_stack([np.ones(len(X)), X])
    w = np.zeros(Xb.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xb @ w))
        W = p * (1 - p) + 1e-6
        try:
            w = np.linalg.solve(Xb.T @ (Xb * W[:, None]) + 1e-6 * np.eye(Xb.shape[1]),
                                Xb.T @ (W * (Xb @ w) + (y - p)))
        except np.linalg.LinAlgError:
            break
    return w


def kfold_auc(X: np.ndarray, y: np.ndarray, k: int = K_FOLD, seed: int = SEED):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(y))
    folds = np.array_split(idx, k)
    aucs = []
    for i in range(k):
        test = folds[i]
        train = np.concatenate([folds[j] for j in range(k) if j != i])
        w = irls_logistic(X[train], y[train])
        s = np.column_stack([np.ones(len(test)), X[test]]) @ w
        aucs.append(auc(s, y[test]))
    return float(np.mean(aucs)), float(np.std(aucs))


def terrain_features(dem: np.ndarray, px: float):
    gy, gx = np.gradient(dem, px)
    curv = np.gradient(gy, px, axis=0) + np.gradient(gx, px, axis=1)   # Laplacian curvature
    mean3 = (np.roll(dem, 1, 0) + np.roll(dem, -1, 0) + np.roll(dem, 1, 1)
             + np.roll(dem, -1, 1) + dem) / 5.0
    rough = np.abs(dem - mean3)                                        # local roughness
    return curv, rough


def main() -> int:
    slope, tr, crs = _read(HAZ / f"{STACK}_slope_deg.tif")
    twi, _, _ = _read(HAZ / f"{STACK}_twi.tif")
    fs_sat, _, _ = _read(HAZ / f"{STACK}_FS_saturated.tif")
    with rasterio.open(DEM_TIF) as ds:
        dem_native = ds.read(1).astype(np.float64)
        dem_tr = ds.transform
    px = abs(tr.a)
    curv_n, rough_n = terrain_features(dem_native, abs(dem_tr.a))

    # Inventory points -> raster CRS (rasters are projected; inventory is lon/lat).
    gj = json.loads(INV.read_text(encoding="utf-8"))
    lons = np.array([f["geometry"]["coordinates"][0] for f in gj["features"]])
    lats = np.array([f["geometry"]["coordinates"][1] for f in gj["features"]])
    import pyproj
    to_grid = pyproj.Transformer.from_crs(4326, crs, always_xy=True)
    pxs, pys = to_grid.transform(lons, lats)

    valid = np.isfinite(slope) & (slope > 0) & np.isfinite(twi)
    rng = np.random.default_rng(SEED)
    vr, vc = np.where(valid)
    pick = rng.choice(len(vr), size=N_NEG, replace=False)
    nxs, nys = rasterio.transform.xy(tr, vr[pick], vc[pick])
    nxs, nys = np.asarray(nxs), np.asarray(nys)

    xs = np.concatenate([pxs, nxs])
    ys = np.concatenate([pys, nys])
    y = np.concatenate([np.ones(len(pxs)), np.zeros(len(nxs))])

    feats = {
        "elevation": _sample(dem_native, dem_tr, xs, ys),
        "slope": _sample(slope, tr, xs, ys),
        "twi": _sample(twi, tr, xs, ys),
        "curvature": _sample(curv_n, dem_tr, xs, ys),
        "roughness": _sample(rough_n, dem_tr, xs, ys),
    }
    X = np.column_stack(list(feats.values()))
    ok = np.isfinite(X).all(axis=1)
    X, y2, xs2, ys2 = X[ok], y[ok], xs[ok], ys[ok]
    n_pos = int(y2.sum())
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)

    lr_auc, lr_std = kfold_auc(X, y2)
    w_full = irls_logistic(X, y2)
    lr_scores = np.column_stack([np.ones(len(X)), X]) @ w_full
    # Bias diagnostic: the corridor-hugging inventory makes ELEVATION a proxy for "near the
    # valley road" — refit without it to see how much skill is that proxy.
    keep = [i for i, k in enumerate(feats) if k != "elevation"]
    lr_noelev_auc, lr_noelev_std = kfold_auc(X[:, keep], y2, seed=SEED + 1)

    phys_scores = -_sample(fs_sat, tr, xs2, ys2)          # lower FS = more hazardous
    phys_auc = auc(phys_scores, y2)
    okp = np.isfinite(phys_scores)
    rank = lambda a: np.argsort(np.argsort(a)) / max(len(a) - 1, 1)   # noqa: E731
    ens = rank(lr_scores[okp]) + rank(phys_scores[okp])
    ens_auc = auc(ens, y2[okp])

    weights = {k: round(float(v), 3) for k, v in zip(feats, w_full[1:])}
    report = {
        "protocol": {"stack_grid": STACK, "n_pos_used": n_pos, "n_neg": N_NEG,
                     "kfold": K_FOLD, "seed": SEED,
                     "features": list(feats), "note":
                     "terrain-only LR (IRLS, standardized); physics = -FS_saturated on the "
                     "same points; ensemble = rank-mean; positives = GSI field-validated "
                     "inventory (corridor-biased, its documented caveat)"},
        "auc": {"lr_terrain_cv": round(lr_auc, 3), "lr_cv_std": round(lr_std, 3),
                "lr_no_elevation_cv": round(lr_noelev_auc, 3),
                "lr_no_elevation_std": round(lr_noelev_std, 3),
                "physics_fs_sat": round(phys_auc, 3), "ensemble": round(ens_auc, 3)},
        "lr_weights_standardized": weights,
    }
    out = PROJECT_ROOT / "data" / "inventory" / "susceptibility_crosscheck.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [f"# Susceptibility cross-check (Tier 3a) — terrain LR vs the physics map", "",
          f"Grid {STACK} · {n_pos} GSI positives vs {N_NEG} seeded random negatives · "
          f"{K_FOLD}-fold CV", "",
          f"| model | AUC |", "|---|---|",
          f"| terrain-only logistic regression (CV) | **{report['auc']['lr_terrain_cv']}** "
          f"± {report['auc']['lr_cv_std']} |",
          f"| physics map (−FS_saturated, same points) | **{report['auc']['physics_fs_sat']}** |",
          f"| rank-mean ensemble | **{report['auc']['ensemble']}** |", "",
          f"Standardized LR weights: {weights}", ""]
    (PROJECT_ROOT / "data" / "inventory" / "susceptibility_crosscheck.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")
    print(f"n_pos={n_pos}  LR(CV) AUC={lr_auc:.3f}±{lr_std:.3f}  "
          f"LR-no-elev={lr_noelev_auc:.3f}±{lr_noelev_std:.3f}  "
          f"physics(-FS_sat) AUC={phys_auc:.3f}  ensemble AUC={ens_auc:.3f}")
    print("weights:", weights)
    print(f"-> {out} , .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

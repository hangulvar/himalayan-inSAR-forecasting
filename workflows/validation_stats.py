#!/usr/bin/env python
"""validation_stats.py — statistical rigor for the inventory validation
(Science Upgrade Plan #1, 2026-07-13). Pure post-processing: no engine changes,
no new physics parameters.

Adds, on top of backtest_inventory.py's point estimates:

  BOOTSTRAP    percentile 95% CIs on the distance-ROC AUC and recall@buffer.
               The INVENTORY features are resampled with replacement (default
               B=10,000); the null set stays fixed — at n=5,000 its sampling
               error is negligible next to the n~40–140 inventory.
  PERMUTATION  one-sided p-value for "beats chance": pool inventory + null
               points, randomly reassign which n_inv of them are "inventory",
               recompute the AUC under H0 (default B=10,000).
  ABLATION     a dumb-baseline ladder scored with the IDENTICAL protocol the
               model product is scored with (per-stack mask -> cluster >=
               MIN_CLUSTER_PX -> centroid -> cross-stack MERGE_DEG union ->
               distance-ROC vs the same inventory + null set):
                 slope    slope_deg >= t                (terrain only)
                 logreg   logistic regression on slope+TWI, fit IN-SAMPLE on
                          inventory-vs-null (optimistic FOR the baseline —
                          if the pipeline still beats it, the claim is
                          conservative); flag the top fraction f of pixels
                 physics  FS_saturated < t (no InSAR); plus FS_real at the
                          site's operational m (physics at the same operating
                          point the model uses)
                 creep    LOS highpass velocity < t mm/yr (InSAR only)
               Each rung is swept over its threshold and the BEST AUC row is
               the rung's score — most favorable to the baseline, again
               conservative for the pipeline's incremental-skill claim.

The headline claim becomes "AUC x.xx [lo–hi], p=..., beats every ladder rung
by ΔAUC ..." instead of a bare point estimate.

Consumes the STANDING union product (stacks.product_stacks — never the live
connectivity snapshot, error log 2026-07-13). Run in Docker (plots):

  docker compose run --rm insar python workflows/validation_stats.py
  docker compose run --rm insar python workflows/validation_stats.py --scenario watch
  docker compose run --rm -e INSAR_CONFIG=config/vaishnodevi.yaml insar \
      python workflows/validation_stats.py
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
import rasterio  # noqa: E402
from pyproj import Transformer  # noqa: E402
from scipy import ndimage  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import backtest_inventory as bt               # noqa: E402
from agentic_orchestrator import MIN_CLUSTER_PX, VEL_CREEP_THR, FS_FAIL  # noqa: E402
from run_multistack import MERGE_DEG, HAZ_DIR, VEL_DIR, MOSAIC_ALERTS_DIR  # noqa: E402
from stacks import product_stacks             # noqa: E402
from config import load_config                # noqa: E402

_CFG = load_config()
_SFX = _CFG.data_suffix
INV_DIR = PROJECT_ROOT / "data" / "inventory"
DEFAULT_INVENTORY = (INV_DIR / "gsi_inventory_aoi.geojson" if _CFG.aoi_slug == "ramban"
                     else INV_DIR / f"{_CFG.aoi_slug}_documented_landslides.geojson")

# Rung threshold sweeps (each rung reports its BEST row — favors the baseline).
SLOPE_THRESHOLDS_DEG = [25.0, 30.0, 35.0, 40.0, 45.0]
FS_THRESHOLDS = [0.9, 1.0, 1.1, 1.3]
CREEP_THRESHOLDS = [-10.0, -15.0, -20.0, -25.0, -30.0]
LOGREG_FLAG_FRACTIONS = [0.005, 0.01, 0.02, 0.05, 0.10]


# ------------------------------------------------------------------------------
# Vectorized distance / AUC machinery (bootstrap + permutation need speed;
# point estimates still go through bt.roc_from_distances for ledger-exact values)
# ------------------------------------------------------------------------------
def nearest_km_vec(pts_lonlat: np.ndarray, zones_lonlat: np.ndarray,
                   chunk: int = 512) -> np.ndarray:
    """Nearest-zone haversine km for many points (numpy, chunked)."""
    pts = np.asarray(pts_lonlat, dtype=float)
    z = np.asarray(zones_lonlat, dtype=float)
    lat1, lon1 = np.radians(pts[:, 1]), np.radians(pts[:, 0])
    lat2, lon2 = np.radians(z[:, 1]), np.radians(z[:, 0])
    out = np.empty(len(pts))
    for i in range(0, len(pts), chunk):
        sl = slice(i, i + chunk)
        dphi = lat2[None, :] - lat1[sl, None]
        dlmb = lon2[None, :] - lon1[sl, None]
        a = (np.sin(dphi / 2) ** 2
             + np.cos(lat1[sl, None]) * np.cos(lat2[None, :]) * np.sin(dlmb / 2) ** 2)
        out[sl] = (2 * 6371.0 * np.arcsin(np.sqrt(a))).min(axis=1)
    return out


def _auc_rows(tpr: np.ndarray, fpr: np.ndarray) -> np.ndarray:
    """Trapezoidal AUC over (FPR, TPR) rows anchored at (0,0) and (1,1).
    tpr/fpr: (..., n_buf), monotone in the buffer sweep by construction."""
    ones = np.ones(tpr.shape[:-1] + (1,))
    zeros = np.zeros_like(ones)
    x = np.concatenate([zeros, fpr if fpr.ndim == tpr.ndim
                        else np.broadcast_to(fpr, tpr.shape), ones], axis=-1)
    y = np.concatenate([zeros, tpr, ones], axis=-1)
    return np.sum(0.5 * (y[..., 1:] + y[..., :-1]) * np.diff(x, axis=-1), axis=-1)


def score_with_stats(real_d: np.ndarray, null_d: np.ndarray, buffers: list[float],
                     buffer_km: float, n_boot: int, n_perm: int,
                     rng: np.random.Generator) -> dict:
    """Point estimates (via the shared bt.roc_from_distances) + bootstrap CIs
    + permutation p on one zone set's nearest-distance arrays."""
    roc_rows, auc, at_buf = bt.roc_from_distances(real_d, null_d, buffers, buffer_km)
    bufs = np.asarray(buffers)
    ib = int(np.argmin(np.abs(bufs - buffer_km)))
    real_det = real_d[:, None] <= bufs[None, :]          # (n_real, n_buf)
    null_det = null_d[:, None] <= bufs[None, :]
    n_real = len(real_d)
    fpr_fixed = null_det.mean(axis=0)

    # Bootstrap: resample inventory only (null fixed, see module docstring).
    idx = rng.integers(0, n_real, size=(n_boot, n_real))
    tpr_b = real_det[idx].mean(axis=1)                   # (B, n_buf)
    auc_b = _auc_rows(tpr_b, np.broadcast_to(fpr_fixed, tpr_b.shape))
    rec_b = tpr_b[:, ib]
    auc_ci = np.percentile(auc_b, [2.5, 97.5])
    rec_ci = np.percentile(rec_b, [2.5, 97.5])

    # Permutation: pooled labels reshuffled -> AUC distribution under H0.
    pooled = np.concatenate([real_det, null_det], axis=0)
    tot = pooled.sum(axis=0).astype(float)
    n_pool = pooled.shape[0]
    auc_p = np.empty(n_perm)
    for k in range(n_perm):
        pos = rng.choice(n_pool, size=n_real, replace=False)
        ps = pooled[pos].sum(axis=0).astype(float)
        tpr_k = ps / n_real
        fpr_k = (tot - ps) / (n_pool - n_real)
        auc_p[k] = _auc_rows(tpr_k[None, :], fpr_k[None, :])[0]
    p_perm = float((1 + np.sum(auc_p >= auc)) / (n_perm + 1))

    return {"auc": round(auc, 3),
            "auc_ci95": [round(float(auc_ci[0]), 3), round(float(auc_ci[1]), 3)],
            "recall_at_buffer": at_buf["tpr"],
            "recall_ci95": [round(float(rec_ci[0]), 3), round(float(rec_ci[1]), 3)],
            "p_perm_beats_chance": round(p_perm, 5),
            "at_buffer_km": at_buf, "roc": roc_rows}


# ------------------------------------------------------------------------------
# Ablation ladder — identical zone-building protocol on baseline layers
# ------------------------------------------------------------------------------
def load_stack_layers(stacks: list[str]) -> list[dict]:
    """Per-stack rasters the rungs need (grids differ per stack, like the model)."""
    layers = []
    for s in stacks:
        entry = {"stack": s}
        paths = {"slope": HAZ_DIR / f"{s}_slope_deg.tif",
                 "twi": HAZ_DIR / f"{s}_twi.tif",
                 "fs_sat": HAZ_DIR / f"{s}_FS_saturated.tif",
                 "fs_dry": HAZ_DIR / f"{s}_FS_dry.tif",
                 "vel": VEL_DIR / f"{s}_mean_velocity_los_highpass.tif"}
        with rasterio.open(paths["slope"]) as src:
            entry["transform"], entry["crs"] = src.transform, src.crs
            entry["slope"] = src.read(1)
        for k in ("twi", "fs_sat", "fs_dry", "vel"):
            with rasterio.open(paths[k]) as src:
                entry[k] = src.read(1)
        entry["to_lonlat"] = Transformer.from_crs(entry["crs"], "EPSG:4326",
                                                  always_xy=True)
        entry["from_lonlat"] = Transformer.from_crs("EPSG:4326", entry["crs"],
                                                    always_xy=True)
        layers.append(entry)
    return layers


def zones_from_mask(mask: np.ndarray, layer: dict) -> list[tuple[float, float]]:
    """Cluster a boolean mask exactly like the reasoner (>= MIN_CLUSTER_PX)
    and return cluster-centroid lon/lats."""
    labels, n = ndimage.label(mask)
    cents = []
    for lab in range(1, n + 1):
        ys, xs = np.where(labels == lab)
        if ys.size < MIN_CLUSTER_PX:
            continue
        cy, cx = float(ys.mean()), float(xs.mean())
        ux, uy = layer["transform"] * (cx + 0.5, cy + 0.5)
        lon, lat = layer["to_lonlat"].transform(ux, uy)
        cents.append((round(lon, 5), round(lat, 5)))
    return cents


def merge_union(cents: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Cross-stack union merge, same MERGE_DEG box rule as run_multistack."""
    merged, used = [], [False] * len(cents)
    for i, (lon, lat) in enumerate(cents):
        if used[i]:
            continue
        group = [(lon, lat)]
        used[i] = True
        for j in range(i + 1, len(cents)):
            if used[j]:
                continue
            if (abs(cents[j][1] - lat) < MERGE_DEG and abs(cents[j][0] - lon) < MERGE_DEG):
                group.append(cents[j])
                used[j] = True
        merged.append((sum(g[0] for g in group) / len(group),
                       sum(g[1] for g in group) / len(group)))
    return merged


def rung_zone_set(layers: list[dict], mask_fn) -> tuple[list[tuple[float, float]], int]:
    """Union zone centroids for a rung; mask_fn(layer) -> bool mask per stack."""
    cents, n_px = [], 0
    for layer in layers:
        m = mask_fn(layer)
        n_px += int(m.sum())
        cents.extend(zones_from_mask(m, layer))
    return merge_union(cents), n_px


def sample_covariates(pts_lonlat: list[tuple[float, float]],
                      layers: list[dict]) -> np.ndarray:
    """(n, 2) slope/TWI at each point — first stack with a finite value wins."""
    n = len(pts_lonlat)
    vals = np.full((n, 2), np.nan)
    lons = np.array([p[0] for p in pts_lonlat])
    lats = np.array([p[1] for p in pts_lonlat])
    for layer in layers:
        xs, ys = layer["from_lonlat"].transform(lons, lats)
        rows, cols = rasterio.transform.rowcol(layer["transform"], xs, ys)
        rows, cols = np.asarray(rows), np.asarray(cols)
        h, w = layer["slope"].shape
        ok = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w)
        need = np.isnan(vals[:, 0]) & ok
        r, c = rows[need], cols[need]
        sl, tw = layer["slope"][r, c], layer["twi"][r, c]
        fin = np.isfinite(sl) & np.isfinite(tw)
        tgt = np.where(need)[0][fin]
        vals[tgt, 0], vals[tgt, 1] = sl[fin], tw[fin]
    return vals


def fit_logreg(X: np.ndarray, y: np.ndarray, iters: int = 50) -> np.ndarray:
    """Plain-numpy IRLS logistic regression (2 covariates + intercept)."""
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-X @ beta))
        w = p * (1 - p) + 1e-9
        hess = X.T @ (X * w[:, None]) + 1e-6 * np.eye(X.shape[1])
        step = np.linalg.solve(hess, X.T @ (y - p))
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break
    return beta


def build_ladder(layers: list[dict], inv_lonlat, null_pts, operational_m: float):
    """Yield (rung, label, mask_fn) for every threshold of every rung."""
    rungs = []
    for t in SLOPE_THRESHOLDS_DEG:
        rungs.append(("slope", f"slope >= {t:.0f} deg",
                      lambda L, t=t: np.isfinite(L["slope"]) & (L["slope"] >= t)))
    for t in FS_THRESHOLDS:
        rungs.append(("physics", f"FS_saturated < {t}",
                      lambda L, t=t: np.isfinite(L["fs_sat"]) & (L["fs_sat"] < t)))
    m = operational_m
    rungs.append(("physics", f"FS_real(m={m}) < {FS_FAIL}",
                  lambda L, m=m: np.isfinite(L["fs_sat"]) & np.isfinite(L["fs_dry"])
                  & (((1 - m) * L["fs_dry"] + m * L["fs_sat"]) < FS_FAIL)))
    for t in CREEP_THRESHOLDS:
        rungs.append(("creep", f"velocity < {t:.0f} mm/yr",
                      lambda L, t=t: np.isfinite(L["vel"]) & (L["vel"] < t)))

    # Logistic regression slope+TWI: fit IN-SAMPLE on inventory-vs-null
    # (optimistic for the baseline; documented in the report).
    cov_inv = sample_covariates(inv_lonlat, layers)
    cov_null = sample_covariates(null_pts, layers)
    X = np.vstack([cov_inv, cov_null])
    y = np.concatenate([np.ones(len(cov_inv)), np.zeros(len(cov_null))])
    keep = np.isfinite(X).all(axis=1)
    mu, sd = X[keep].mean(axis=0), X[keep].std(axis=0) + 1e-9
    Xs = np.column_stack([np.ones(keep.sum()), (X[keep] - mu) / sd])
    beta = fit_logreg(Xs, y[keep])

    def prob(layer):
        s = (layer["slope"] - mu[0]) / sd[0]
        t = (layer["twi"] - mu[1]) / sd[1]
        with np.errstate(over="ignore", invalid="ignore"):
            p = 1.0 / (1.0 + np.exp(-(beta[0] + beta[1] * s + beta[2] * t)))
        p[~(np.isfinite(layer["slope"]) & np.isfinite(layer["twi"]))] = np.nan
        return p

    pooled = np.concatenate([prob(L)[np.isfinite(prob(L))] for L in layers])
    for f in LOGREG_FLAG_FRACTIONS:
        thr = float(np.quantile(pooled, 1.0 - f))
        rungs.append(("logreg", f"LR(slope,TWI) top {f*100:g}% (p>={thr:.3f})",
                      lambda L, thr=thr: np.nan_to_num(prob(L), nan=-1.0) >= thr))
    lr_info = {"beta": [round(float(b), 4) for b in beta],
               "covariates": ["intercept", "slope_deg (std)", "twi (std)"],
               "n_fit": int(keep.sum()),
               "note": "fit in-sample on inventory-vs-null -> optimistic for the baseline"}
    return rungs, lr_info


# ------------------------------------------------------------------------------
def forest_plot(path: Path, model_row: dict, best_rows: list[dict], title: str):
    rows = [model_row] + best_rows
    labels = [r["label"] for r in rows]
    aucs = [r["auc"] for r in rows]
    lo = [r["auc"] - r["auc_ci95"][0] for r in rows]
    hi = [r["auc_ci95"][1] - r["auc"] for r in rows]
    ypos = np.arange(len(rows))[::-1]
    fig, ax = plt.subplots(figsize=(8, 0.7 * len(rows) + 2))
    colors = ["#d62728"] + ["#1f77b4"] * len(best_rows)
    for yp, a, l, h, c in zip(ypos, aucs, lo, hi, colors):
        ax.errorbar(a, yp, xerr=[[l], [h]], fmt="o", color=c, capsize=4, lw=2)
    ax.axvline(0.5, color="#7f7f7f", ls="--", lw=1, label="chance (0.5)")
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("distance-ROC AUC (95% bootstrap CI)")
    ax.set_title(title, fontsize=10)
    ax.grid(alpha=0.3, axis="x")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def write_md(path: Path, rep: dict) -> None:
    m = rep["model"]
    lines = [
        f"# Validation statistics — {rep['site']} / {rep['scenario']}",
        "",
        f"Alerts: `{Path(rep['alerts_source']).name}` ({rep['n_zones']} zones) vs "
        f"inventory `{Path(rep['inventory_source']).name}` (n={rep['n_inventory']}), "
        f"null n={rep['n_null']} (seed {rep['null_seed']}), "
        f"B_boot={rep['n_boot']}, B_perm={rep['n_perm']} (seed {rep['stat_seed']}).",
        "",
        "## Headline (the model product, with uncertainty)",
        f"- **AUC = {m['auc']} [{m['auc_ci95'][0]}–{m['auc_ci95'][1]}]** (95% bootstrap CI, "
        f"inventory resampled)",
        f"- recall@{rep['buffer_km']} km = {m['recall_at_buffer']} "
        f"[{m['recall_ci95'][0]}–{m['recall_ci95'][1]}]",
        f"- permutation p (beats chance, one-sided) = **{m['p_perm_beats_chance']}**",
        "",
        "## Ablation ladder (best threshold per rung; identical scoring protocol)",
        "",
        "| rung | best variant | zones | flagged px | AUC [95% CI] | recall@"
        f"{rep['buffer_km']} km | precision | p_perm | ΔAUC (model − rung) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rep["ladder_best"]:
        lines.append(
            f"| {r['rung']} | {r['label']} | {r['n_zones']} | {r['n_px']} | "
            f"{r['auc']} [{r['auc_ci95'][0]}–{r['auc_ci95'][1]}] | "
            f"{r['recall_at_buffer']} | {r.get('precision_at_buffer')} | "
            f"{r['p_perm_beats_chance']} | "
            f"{round(m['auc'] - r['auc'], 3):+} |")
    lines += ["", "### All swept rows", "",
              "| rung | variant | zones | flagged px | AUC | recall |",
              "|---|---|---|---|---|---|"]
    for r in rep["ladder_all"]:
        lines.append(f"| {r['rung']} | {r['label']} | {r['n_zones']} | {r['n_px']} | "
                     f"{r['auc']} | {r['recall_at_buffer']} |")
    lines += [
        "", "## Honest scope",
        "- Bootstrap resamples the inventory only; the fixed null set (n=5,000) adds "
        "negligible extra variance. CIs at this inventory size are expected to be wide — "
        "that width IS the finding; cite intervals, not points.",
        "- The logistic-regression rung is fit and scored on the same inventory "
        "(in-sample): its AUC is optimistic. Beating an optimistic baseline is the "
        "conservative direction for the pipeline's incremental-skill claim.",
        "- Each rung reports its best threshold (best-case baseline), same direction.",
        "- The protocol is the standing distance-ROC (zone centroids, buffer sweep); "
        "it penalizes spatially vague products — exactly the operational question.",
    ]
    if rep.get("logreg"):
        lines.append(f"- Logistic regression fit: {rep['logreg']['beta']} on "
                     f"{rep['logreg']['covariates']} (n={rep['logreg']['n_fit']}).")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default="operational",
                    help="Standing product to score (sets default --alerts + output names).")
    ap.add_argument("--alerts", default=None,
                    help="Union alerts JSON (default: mosaic_asc/alerts_<scenario>.json).")
    ap.add_argument("--inventory", default=str(DEFAULT_INVENTORY))
    ap.add_argument("--aoi-path", default=None)
    ap.add_argument("--buffer-km", type=float, default=2.0)
    ap.add_argument("--n-null", type=int, default=5000)
    ap.add_argument("--null-seed", type=int, default=20260606)
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--n-perm", type=int, default=10000)
    ap.add_argument("--stat-seed", type=int, default=20260713,
                    help="RNG seed for bootstrap/permutation (reproducible).")
    ap.add_argument("--min-looks", type=int, default=1)
    ap.add_argument("--stacks", nargs="*", default=None,
                    help="Rung raster stacks (default: the standing product's source_stacks).")
    ap.add_argument("--skip-ablation", action="store_true",
                    help="Only the CI/p statistics on the model product (fast).")
    args = ap.parse_args()

    alerts_path = Path(args.alerts) if args.alerts else (
        MOSAIC_ALERTS_DIR / f"alerts_{args.scenario}.json")
    zones = bt.load_zone_centroids(alerts_path, args.min_looks)
    if not zones:
        raise SystemExit(f"No zone centroids in {alerts_path}")
    inv = bt.load_inventory(Path(args.inventory))
    inv_lonlat = [(p["lon"], p["lat"]) for p in inv]

    aoi_path = Path(args.aoi_path) if args.aoi_path else Path(_CFG.aoi_path)
    rings, bbox = bt.aoi_polygon_lonlat(aoi_path)
    null_pts = bt.sample_null_points(rings, bbox, args.n_null, args.null_seed)
    rng = np.random.default_rng(args.stat_seed)
    buffers = bt.DEFAULT_ROC_BUFFERS_KM

    print(f"site={_CFG.site_name} scenario={args.scenario} zones={len(zones)} "
          f"inventory={len(inv)} null={len(null_pts)}")

    def score_zone_set(cents):
        real_d = nearest_km_vec(inv_lonlat, cents)
        null_d = nearest_km_vec(null_pts, cents)
        return score_with_stats(real_d, null_d, buffers, args.buffer_km,
                                args.n_boot, args.n_perm, rng)

    model = {"label": f"model ({args.scenario})", **score_zone_set(zones)}
    print(f"MODEL  AUC {model['auc']} [{model['auc_ci95'][0]}-{model['auc_ci95'][1]}] "
          f"recall@{args.buffer_km}km {model['recall_at_buffer']} "
          f"[{model['recall_ci95'][0]}-{model['recall_ci95'][1]}] "
          f"p_perm {model['p_perm_beats_chance']}")

    ladder_all, ladder_best, lr_info = [], [], None
    if not args.skip_ablation:
        stacks = args.stacks or product_stacks(args.scenario)
        layers = load_stack_layers(stacks)
        print(f"ablation stacks: {stacks}")
        rungs, lr_info = build_ladder(layers, inv_lonlat, null_pts, _CFG.operational_m)
        for rung, label, mask_fn in rungs:
            cents, n_px = rung_zone_set(layers, mask_fn)
            if not cents:
                ladder_all.append({"rung": rung, "label": label, "n_zones": 0,
                                   "n_px": n_px, "auc": None, "recall_at_buffer": None})
                continue
            s = score_zone_set(cents)
            row = {"rung": rung, "label": label, "n_zones": len(cents), "n_px": n_px,
                   **{k: s[k] for k in ("auc", "auc_ci95", "recall_at_buffer",
                                        "recall_ci95", "p_perm_beats_chance")},
                   "precision_at_buffer": s["at_buffer_km"]["precision"],
                   "specificity_at_buffer": s["at_buffer_km"]["specificity"]}
            ladder_all.append(row)
            print(f"  {rung:<8} {label:<34} zones={len(cents):<5} "
                  f"AUC {row['auc']} [{row['auc_ci95'][0]}-{row['auc_ci95'][1]}]")
        for rung in ("slope", "logreg", "physics", "creep"):
            rows = [r for r in ladder_all if r["rung"] == rung and r["auc"] is not None]
            if rows:
                best = max(rows, key=lambda r: r["auc"])
                ladder_best.append({**best, "label": f"{best['label']} (best of rung)"})

    rep = {
        "site": _CFG.site_name, "scenario": args.scenario,
        "alerts_source": str(alerts_path), "n_zones": len(zones),
        "min_looks": args.min_looks,
        "inventory_source": args.inventory, "n_inventory": len(inv),
        "aoi_path": str(aoi_path), "n_null": len(null_pts),
        "null_seed": args.null_seed, "buffer_km": args.buffer_km,
        "n_boot": args.n_boot, "n_perm": args.n_perm, "stat_seed": args.stat_seed,
        "model": model, "ladder_best": ladder_best, "ladder_all": ladder_all,
        "logreg": lr_info,
    }
    INV_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"validation_stats_{args.scenario}{_SFX}"
    (INV_DIR / f"{stem}.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    write_md(INV_DIR / f"{stem}.md", rep)
    if ladder_best:
        forest_plot(INV_DIR / f"{stem}.png", model, ladder_best,
                    f"{_CFG.site_name} — {args.scenario}: model vs ablation ladder "
                    f"(95% bootstrap CIs)")
    print(f"-> {INV_DIR / (stem + '.json')} , .md" + (" , .png" if ladder_best else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

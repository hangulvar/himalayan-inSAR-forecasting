"""test_science_verification.py — pixel-exact physics + data-integrity regression suite.

Born from the 2026-07-17 full-product audit (RESULTS_AND_KPIS.md §49): every check
here recomputes an invariant INDEPENDENTLY (textbook formula, stdlib parse, raw
window sums) and compares it against the standing products — so a silent change to
the engine, the artifacts, or their wiring fails loudly. Only DURABLE invariants
live here (nothing tied to a session's as-of date or grown-inventory counts;
growth-prone counts are floors, following test_plumbing's MIN_PRODUCT_COUNT pattern).

Complements (does not duplicate): tests/test_fs_real.py (kappa/suction/m* module
invariants), tests/test_plumbing.py (Phase-1 inventory), tests/test_config_registry.py.

Run from project root (native env or the insar container):
    python tests/test_science_verification.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
import traceback
from datetime import date
from pathlib import Path

import numpy as np
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))
from config import load_config  # noqa: E402
import fs_real  # noqa: E402

# Site table: (config, hazard dir, velocity dir, sample stack, rainfall suffix).
# The sample stack pins the pixel-exact FS check to one operational stack per site.
SITES = {
    "ramban": ("config/ramban.yaml", "data/hazard", "data/velocity",
               "ASC_path27_frame106", ""),
    "vaishnodevi": ("config/vaishnodevi.yaml", "data/hazard_vaishnodevi",
                    "data/velocity_vaishnodevi", "ASC_path27_frame105", "_vaishnodevi"),
}
GAMMA_W = 9.81  # kN/m^3 — must match geomechanical_engine.GAMMA_W

# Growth floors (inventories only grow; shrinkage = data loss).
MIN_INVENTORY = {"vaishnodevi_documented_landslides.geojson": 46,
                 "gsi_inventory_aoi.geojson": 138}


# ------------------------------------------------------------------------------
# Physics: the standing FS rasters must match an INDEPENDENTLY written
# infinite-slope formula, pixel-exact (float32 epsilon).
#   FS = [c + (gamma - m*gw)*z*cos^2(b)*tan(phi)] / [gamma*z*sin(b)*cos(b)]
#   <2 deg -> 5.0 (flat override), clip [0,5], NaN where slope is NaN.
# ------------------------------------------------------------------------------
def _independent_fs(slope_deg: np.ndarray, c: float, phi: float, gamma: float,
                    z: float, m: float) -> np.ndarray:
    b = np.radians(slope_deg.astype(np.float64))
    num = c + (gamma - m * GAMMA_W) * z * np.cos(b) ** 2 * np.tan(np.radians(phi))
    den = gamma * z * np.sin(b) * np.cos(b)
    with np.errstate(invalid="ignore", divide="ignore"):
        fs = np.where(den > 1e-6, num / den, np.nan).astype(np.float32)
    fs[slope_deg < 2.0] = 5.0
    fs[~np.isfinite(slope_deg)] = np.nan
    return np.clip(fs, 0, 5)


def test_fs_rasters_match_independent_formula() -> None:
    for site, (cfgp, hdir, _, stack, _) in SITES.items():
        soil = load_config(str(PROJECT_ROOT / cfgp)).soil
        with rasterio.open(PROJECT_ROOT / hdir / f"{stack}_slope_deg.tif") as ds:
            slope = ds.read(1)
        for name, c, m in [("FS_dry", soil.cohesion_dry_kpa, 0.0),
                           ("FS_saturated", soil.cohesion_wet_kpa, 1.0)]:
            with rasterio.open(PROJECT_ROOT / hdir / f"{stack}_{name}.tif") as ds:
                std = ds.read(1)
            mine = _independent_fs(slope, c, soil.phi_deg, soil.gamma_kn_m3,
                                   soil.depth_m, m)
            both = np.isfinite(std) & np.isfinite(mine)
            assert np.array_equal(np.isfinite(std), np.isfinite(mine)), (
                f"{site}/{stack} {name}: NaN pattern differs from the formula's")
            maxdiff = float(np.max(np.abs(std[both] - mine[both])))
            assert maxdiff < 1e-4, (
                f"{site}/{stack} {name}: standing raster deviates from the "
                f"infinite-slope formula (max|diff|={maxdiff:.2e}) — engine or "
                f"soil config changed without a rebuild?")


def test_fs_saturated_never_exceeds_fs_dry() -> None:
    for site, (_, hdir, _, stack, _) in SITES.items():
        with rasterio.open(PROJECT_ROOT / hdir / f"{stack}_FS_dry.tif") as ds:
            d = ds.read(1)
        with rasterio.open(PROJECT_ROOT / hdir / f"{stack}_FS_saturated.tif") as ds:
            w = ds.read(1)
        both = np.isfinite(d) & np.isfinite(w)
        viol = int(np.sum(w[both] > d[both] + 1e-6))
        assert viol == 0, f"{site}/{stack}: {viol} px where FS_saturated > FS_dry"


def test_fs_linear_monotonic_and_root() -> None:
    """FS(m) non-increasing in m; the closed-form m* actually solves FS(m*)=1."""
    rng = np.random.default_rng(42)
    fsd = rng.uniform(0.8, 4.0, 500).astype(np.float32)
    fss = np.clip(fsd - rng.uniform(0.05, 1.5, 500), 0.05, None).astype(np.float32)
    fields = np.stack([fs_real.fs_field(fsd, fss, float(m))
                       for m in np.linspace(0, 1, 21)])
    assert np.all(np.diff(fields, axis=0) <= 1e-6), "FS increased with wetness"
    mstars = np.array([fs_real.critical_saturation(float(a), float(b))
                       for a, b in zip(fsd, fss)])
    interior = (mstars > 0) & (mstars < 1)
    fs_at = (1 - mstars[interior]) * fsd[interior] + mstars[interior] * fss[interior]
    assert np.allclose(fs_at, 1.0, atol=1e-5), "FS(m*) != 1 at the closed-form root"


def test_vg_suction_strictly_decreasing() -> None:
    psi = fs_real._psi_kpa(np.linspace(0.05, 0.95, 100), 0.05, 1.6)
    assert np.all(np.diff(psi) < 0), "van Genuchten psi(m) must fall as m rises"


# ------------------------------------------------------------------------------
# Rainfall: the ID-threshold trigger days recomputed from the raw season series
# (I = 2.9993*D^-0.4152 mm/h over D-day windows) must reproduce the standing report.
# ------------------------------------------------------------------------------
def test_id_threshold_reproduces_standing_report() -> None:
    checked = 0
    for site, (_, _, _, _, sfx) in SITES.items():
        for wet_csv in (PROJECT_ROOT / "data/rainfall").glob(
                f"{site}_wetness_daily{sfx}_*.csv"):
            year = wet_csv.stem.rsplit("_", 1)[-1]
            rep_p = PROJECT_ROOT / "data/rainfall" / f"id_threshold_report{sfx}_{year}.json"
            if not rep_p.exists():
                continue
            rows = list(csv.DictReader(wet_csv.open(encoding="utf-8")))
            col = next(c for c in rows[0] if "water" in c.lower()
                       or "wetness" in c.lower() or "total" in c.lower())
            water = np.array([float(r[col]) for r in rows])
            dates = [r["date"] for r in rows]
            trigger: set[str] = set()
            for D in (1, 2, 3, 5, 7, 10, 15):
                thr = 2.9993 * (24.0 * D) ** (1 - 0.4152)
                roll = np.convolve(water, np.ones(D), "valid")
                trigger.update(dates[i + D - 1] for i in np.nonzero(roll >= thr)[0])
            rep = json.loads(rep_p.read_text(encoding="utf-8"))
            n_rep = rep.get("n_trigger_days") or len(rep.get("trigger_days", []))
            assert len(trigger) == n_rep, (
                f"{site} {year}: recomputed {len(trigger)} trigger days, "
                f"report says {n_rep} — threshold wiring changed?")
            checked += 1
    assert checked >= 2, f"only {checked} site-season(s) had both CSV and report"


# ------------------------------------------------------------------------------
# Rasters: integrity, physical ranges, and grid identity with the velocity master.
# ------------------------------------------------------------------------------
RANGES = {"slope_deg": (0, 90), "twi": (-10, 40), "FS_dry": (0, 5),
          "FS_saturated": (0, 5), "hazard_class": (0, 2)}


def test_hazard_rasters_integrity() -> None:
    n = 0
    for _, (_, hdir, _, _, _) in SITES.items():
        for t in sorted((PROJECT_ROOT / hdir).glob("*.tif")):
            with rasterio.open(t) as ds:
                assert ds.crs is not None, f"{t.name}: no CRS"
                arr = ds.read(1)
            v = arr[np.isfinite(arr)]
            assert v.size > 0, f"{t.name}: all-NaN raster"
            for suf, (lo, hi) in RANGES.items():
                if t.stem.endswith(suf):
                    assert lo - 1e-6 <= v.min() and v.max() <= hi + 1e-6, (
                        f"{t.name}: values [{v.min():.2f},{v.max():.2f}] "
                        f"outside physical range [{lo},{hi}]")
            n += 1
    assert n >= 20, f"only {n} hazard rasters found — dirs moved?"


def test_hazard_layers_share_velocity_grid() -> None:
    for _, (_, hdir, vdir, _, _) in SITES.items():
        for sl in (PROJECT_ROOT / hdir).glob("*_slope_deg.tif"):
            stack = sl.name.replace("_slope_deg.tif", "")
            vel = PROJECT_ROOT / vdir / f"{stack}_mean_velocity_los_highpass.tif"
            if not vel.exists():
                continue
            with rasterio.open(vel) as dv:
                ref = (dv.width, dv.height, dv.transform)
            for suf in RANGES:
                p = PROJECT_ROOT / hdir / f"{stack}_{suf}.tif"
                if p.exists():
                    with rasterio.open(p) as ds:
                        assert (ds.width, ds.height, ds.transform) == ref, (
                            f"{stack}:{suf} grid differs from the velocity master")


def test_coherence_sample_in_unit_interval() -> None:
    import random
    random.seed(7)
    dirs = sorted(d for d in (PROJECT_ROOT / "data/processed_tiffs").iterdir()
                  if d.is_dir())
    for d in random.sample(dirs, min(3, len(dirs))):
        c = next(d.glob("*_corr.tif"), None)
        assert c is not None, f"{d.name}: no coherence tif"
        with rasterio.open(c) as ds:
            a = ds.read(1)
        v = a[np.isfinite(a)]
        assert v.size and -1e-6 <= v.min() and v.max() <= 1 + 1e-6, (
            f"{c.name}: coherence outside [0,1]")


# ------------------------------------------------------------------------------
# Inventories (stdlib json): parseable, growth-floor counts, inside the AOI bbox.
# ------------------------------------------------------------------------------
def _geojson_lonlat(path: Path) -> tuple[int, list[tuple[float, float]]]:
    lons, lats, n = [], [], 0

    def walk(c):
        if isinstance(c[0], (int, float)):
            lons.append(float(c[0])); lats.append(float(c[1]))
        else:
            for x in c:
                walk(x)

    gj = json.loads(path.read_text(encoding="utf-8"))
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    pts = []
    for f in feats:
        i0 = len(lons)
        walk((f.get("geometry") or f)["coordinates"])
        n += 1
        pts.append((float(np.mean(lons[i0:])), float(np.mean(lats[i0:]))))
    return n, pts


def test_inventories_valid_and_not_shrunk() -> None:
    aoi_of = {"vaishnodevi_documented_landslides.geojson": "config/aoi/vaishnodevi_aoi.geojson",
              "gsi_inventory_aoi.geojson": "config/aoi/ramban_aoi.geojson"}
    for inv_name, floor in MIN_INVENTORY.items():
        n, pts = _geojson_lonlat(PROJECT_ROOT / "data/inventory" / inv_name)
        assert n >= floor, (
            f"{inv_name}: {n} features < floor {floor} — inventory shrank (data loss?)")
        _, aoi_pts = _geojson_lonlat(PROJECT_ROOT / aoi_of[inv_name])
        ax = [p[0] for p in aoi_pts]; ay = [p[1] for p in aoi_pts]
        out = [p for p in pts if not (min(ax) - 0.2 <= p[0] <= max(ax) + 0.2
                                      and min(ay) - 0.2 <= p[1] <= max(ay) + 0.2)]
        assert not out, f"{inv_name}: {len(out)} feature(s) outside the AOI bbox+0.2deg"


# ------------------------------------------------------------------------------
# Season artifacts: continuity, valid levels, and cross-artifact consistency
# (calendar <-> alarm report <-> per-zone gate must describe the SAME state —
# a divergence means a partially-failed cycle).
# ------------------------------------------------------------------------------
VALID_LEVELS = {"DORMANT", "NORMAL", "WATCH", "WATCH+", "ALERT"}


def _latest_season(sfx: str, pattern: str) -> Path | None:
    hits = sorted((PROJECT_ROOT / "data/rainfall").glob(pattern.format(sfx=sfx)))
    return hits[-1] if hits else None


def test_season_series_and_calendar_wellformed() -> None:
    for site, (_, _, _, _, sfx) in SITES.items():
        cal = _latest_season(sfx, "operational_alarm_calendar{sfx}_2*.csv")
        assert cal is not None, f"{site}: no alarm calendar found"
        rows = list(csv.DictReader(cal.open(encoding="utf-8")))
        ds = [date.fromisoformat(r["date"]) for r in rows]
        assert all((b - a).days == 1 for a, b in zip(ds, ds[1:])), (
            f"{cal.name}: date gaps")
        lv = {r["alarm_level"] for r in rows}
        assert lv <= VALID_LEVELS, f"{cal.name}: unknown levels {lv - VALID_LEVELS}"


def test_alarm_artifacts_cross_consistent() -> None:
    for site, (cfgp, _, _, _, sfx) in SITES.items():
        cal = _latest_season(sfx, "operational_alarm_calendar{sfx}_2*.csv")
        year = cal.stem.rsplit("_", 1)[-1]
        rep = json.loads((PROJECT_ROOT / "data/rainfall" /
                          f"operational_alarm_report{sfx}_{year}.json").read_text(encoding="utf-8"))
        rows = list(csv.DictReader(cal.open(encoding="utf-8")))
        cal_alerts = [r["date"] for r in rows if r["alarm_level"] == "ALERT"]
        assert cal_alerts == rep["alert_days"], (
            f"{site} {year}: calendar ALERT days {cal_alerts} != report "
            f"{rep['alert_days']} — artifacts from different runs?")
        pz_dir = "data/alerts" + ("_vaishnodevi" if site == "vaishnodevi" else "")
        pz = json.loads((PROJECT_ROOT / pz_dir / "per_zone_vulnerability.json")
                        .read_text(encoding="utf-8"))
        assert pz["kappa"] == load_config(str(PROJECT_ROOT / cfgp)).kappa, (
            f"{site}: per-zone product kappa {pz['kappa']} != config — "
            f"stale product after a config change?")
        assert pz["as_of"] == rows[-1]["date"], (
            f"{site}: per-zone as_of {pz['as_of']} != calendar end {rows[-1]['date']} "
            f"— partially-failed cycle?")


# ------------------------------------------------------------------------------
# References: every § cited by the dashboard file must exist in the ledger.
# ------------------------------------------------------------------------------
def test_pair_date_parsers_accept_cross_unit_products() -> None:
    """The S1 constellation handover (§56/§61) ships cross-unit HyP3 products
    (S1AD, S1DD…). The date-parsing regexes were hardcoded to S1AA and silently
    dropped them — this pins the broadened S1[A-D][A-D] pattern in both parsers
    that feed the inversion/network, for both a same-unit and a cross-unit name."""
    import custom_sbas_inverter as csi
    import sbas_network_graph as sng

    s1aa = "S1AA_20260419T125645_20260501T125637_VVP012_INT80_G_weF_85CC"
    s1ad = "S1AD_20260618T125635_20260625T125553_VVP007_INT80_G_weF_05DD"
    for parse in (csi.parse_pair_dates, sng.parse_pair_dates):
        r1 = parse(s1aa)
        assert r1 is not None and (r1[0].date(), r1[1].date()) == (
            date(2026, 4, 19), date(2026, 5, 1)), (parse, "S1AA")
        r2 = parse(s1ad)                                   # the cross-unit seam
        assert r2 is not None and (r2[0].date(), r2[1].date()) == (
            date(2026, 6, 18), date(2026, 6, 25)), (parse, "S1AD")


def test_ledger_section_references_complete() -> None:
    ledger = (PROJECT_ROOT / "RESULTS_AND_KPIS.md").read_text(encoding="utf-8")
    have = set(re.findall(r"^## (\d+)[a-z]?\.", ledger, re.M))
    cited = set(re.findall(r"§(\d+)",
                           (PROJECT_ROOT / "SESSION_REVIEW.md").read_text(encoding="utf-8")))
    missing = sorted(int(c) for c in cited - have)
    assert not missing, f"SESSION_REVIEW cites missing ledger sections: {missing}"


# ------------------------------------------------------------------------------
# CLI runner (stdlib-only — works under pytest too).
# ------------------------------------------------------------------------------
def _all_tests() -> list:
    g = globals()
    return [(n, g[n]) for n in sorted(g) if n.startswith("test_") and callable(g[n])]


def main() -> int:
    tests = _all_tests()
    print(f"Running {len(tests)} science-verification tests...")
    print("-" * 70)
    n_pass = n_fail = 0
    for name, fn in tests:
        try:
            fn()
        except AssertionError as e:
            n_fail += 1
            print(f"FAIL  {name}\n      {e}")
        except Exception:
            n_fail += 1
            print(f"ERROR {name}")
            traceback.print_exc(limit=2)
        else:
            n_pass += 1
            print(f"PASS  {name}")
    print("-" * 70)
    print(f"Total: {n_pass} passed, {n_fail} failed.")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

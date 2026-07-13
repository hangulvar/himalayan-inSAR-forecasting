"""Regression tests for workflows/fs_real.py — the single source of truth for
"FS at wetness m" (§45 kappa TWI-distribution, §46 van Genuchten suction).

Pure numpy, no rasters/config needed: guards the physics invariants that §45's first
cut proved can silently break when consumers drift (error log 2026-07-13). Run natively
or in-container:  python tests/test_fs_real.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workflows"))
import fs_real
from config import SoilConfig, SuctionConfig

SOIL = SoilConfig(cohesion_dry_kpa=18.5, cohesion_wet_kpa=5.0, phi_deg=36.0,
                  gamma_kn_m3=19.0, depth_m=3.0)
VG = SuctionConfig(alpha_kpa_inv=0.204, n=1.41)   # Carsel & Parrish silt loam

rng = np.random.default_rng(20260713)
FS_DRY = rng.uniform(0.8, 3.0, (40, 40)).astype(np.float32)
# The engine clips its FS rasters to [0, 5]; the fixture must respect that domain or
# fs_field's suction-path clip legitimately diverges at the end-members.
FS_SAT = np.clip(FS_DRY - rng.uniform(0.2, 1.0, (40, 40)), 0.0, 5.0).astype(np.float32)
TWI = rng.uniform(3.5, 14.0, (40, 40)).astype(np.float32)
SLOPE = rng.uniform(5.0, 55.0, (40, 40)).astype(np.float32)


def test_kappa_zero_is_bitwise_identical():
    a = fs_real.fs_field(FS_DRY, FS_SAT, 0.4, TWI, 0.0)
    b = (1.0 - 0.4) * FS_DRY + 0.4 * FS_SAT
    assert np.array_equal(a, b), "kappa=0 must reproduce the scalar interpolation"


def test_kappa_preserves_spatial_mean_when_unclipped():
    mf = fs_real.m_field(0.4, TWI, 0.06)
    assert abs(float(np.mean(mf)) - 0.4) < 1e-6, "kappa must only redistribute wetness"


def test_effective_mstar_identity_at_kappa_zero():
    assert fs_real.effective_mstar(0.37, 9.1, 6.3, 0.0) == 0.37
    assert fs_real.effective_mstar(0.37, None, 6.3, 0.06) == 0.37


def test_effective_mstar_shift_direction():
    # wetter-than-average terrain (high TWI) activates at LOWER AOI-mean wetness
    assert fs_real.effective_mstar(0.5, 9.0, 6.0, 0.06) < 0.5
    assert fs_real.effective_mstar(0.5, 3.0, 6.0, 0.06) > 0.5


def test_suction_none_path_is_bitwise_identical():
    a = fs_real.fs_field(FS_DRY, FS_SAT, 0.4, TWI, 0.06, SLOPE, SOIL, None)
    b = fs_real.fs_field(FS_DRY, FS_SAT, 0.4, TWI, 0.06)
    assert np.array_equal(a, b), "suction=None must be the historical linear model"


def test_suction_cohesion_anchors_end_members():
    ms = np.linspace(0.0, 1.0, 1001)
    c = fs_real.cohesion_kpa(ms, SOIL, VG)
    assert c[0] == SOIL.cohesion_dry_kpa, "c(0) must equal c_dry exactly"
    assert c[-1] == SOIL.cohesion_wet_kpa, "c(1) must equal c_wet exactly"
    assert (c >= SOIL.cohesion_wet_kpa - 1e-9).all()
    assert (c <= SOIL.cohesion_dry_kpa + 1e-9).all()
    assert (np.diff(c) <= 1e-9).all(), "c(m) must be monotone non-increasing"


def test_suction_fs_reproduces_end_member_rasters():
    f0 = fs_real.fs_field(FS_DRY, FS_SAT, 0.0, None, 0.0, SLOPE, SOIL, VG)
    f1 = fs_real.fs_field(FS_DRY, FS_SAT, 1.0, None, 0.0, SLOPE, SOIL, VG)
    assert np.allclose(f0, FS_DRY, atol=1e-6), "FS(0) must reproduce FS_dry"
    assert np.allclose(f1, FS_SAT, atol=1e-6), "FS(1) must reproduce FS_sat"


def test_mstar_dispatch_linear_matches_closed_form():
    for fd, fs in [(1.5, 0.8), (1.05, 0.4), (2.5, 1.2), (0.9, 0.5)]:
        assert fs_real.mstar(fd, fs) == fs_real.critical_saturation(fd, fs)


def test_mstar_suction_root_solves_fs_equals_one():
    for fd, fs, sl in [(1.5, 0.8, 35.0), (1.3, 0.6, 45.0), (2.0, 0.9, 25.0)]:
        m = fs_real.mstar(fd, fs, SOIL, VG, sl)
        assert m is not None and 0.0 < m < 1.0
        k = fs_real.fs_cohesion_sensitivity(sl, SOIL)
        fs_at = (1 - m) * fd + m * fs + fs_real.cohesion_correction_kpa(m, SOIL, VG) * k
        assert abs(fs_at - 1.0) < 5e-3, f"grid root off: FS(m*)={fs_at}"


def test_mstar_suction_semantics_match_linear_edges():
    # never fails (FS_sat > 1) -> 1.0 ; already unstable dry (FS_dry < 1) -> 0.0
    assert fs_real.mstar(2.5, 1.2, SOIL, VG, 30.0) == 1.0
    assert fs_real.mstar(0.9, 0.5, SOIL, VG, 30.0) == 0.0
    # degenerate (saturation does not reduce FS) -> None, same as linear
    assert fs_real.mstar(1.0, 1.5, SOIL, VG, 30.0) is None
    assert fs_real.critical_saturation(1.0, 1.5) is None


def main() -> int:
    tests = [f for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    print(f"Running {len(tests)} fs_real physics tests...")
    print("-" * 70)
    failed = 0
    for f in tests:
        try:
            f()
            print(f"PASS  {f.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {f.__name__}: {e}")
    print("-" * 70)
    print(f"Total: {len(tests) - failed} passed, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

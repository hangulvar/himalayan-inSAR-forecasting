"""
test_nisar_ingest.py — the L-band ingestion contract (§83).

Covers the PURE half of nisar_ingest: granule parsing, the internal product naming that the
Phase-2 date parser has to read, and — the one that matters — the wavelength conversion.

Why the wavelength gets a negative control: `feature_engineering` hardcodes the Sentinel-1
wavelength, so pointing the existing C-band converter at L-band phase would under-report every
displacement by ~4.4x, silently and plausibly. This suite pins both the correct factor and the
size of the mistake that is being avoided.

Hermetic: no h5py, no network, no GDAL — the heavy readers/writers are imported lazily inside
nisar_ingest, so this runs in the lean image with the rest of the battery.

Run from project root:
    python tests/test_nisar_ingest.py
OR under pytest:
    python -m pytest tests/test_nisar_ingest.py -v
"""

from __future__ import annotations

import re
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import nisar_ingest as ni  # noqa: E402

WINTER = ("NISAR_L2_PR_GUNW_008_156_A_018_009_4000_SH_20251227T001346_20251227T001420_"
          "20260108T001346_20260108T001421_X05010_N_F_J_001")
MONSOON = ("NISAR_L2_PR_GUNW_024_156_A_018_025_4000_SH_20260707T001345_20260707T001420_"
           "20260719T001345_20260719T001420_P05023_N_F_J_001")
DESC = ("NISAR_L2_PR_GUNW_023_135_D_072_024_2000_SH_20260623T134704_20260623T134739_"
        "20260705T134704_20260705T134738_P05023_N_F_J_001")


def test_granule_parsing_reads_track_frame_direction_and_maturity() -> None:
    g = ni.parse_granule(WINTER)
    assert (g["track"], g["direction"], g["frame"]) == ("156", "A", "018"), g
    assert g["ref"] == "20251227T001346" and g["sec"] == "20260108T001346", g
    assert g["provisional"] is True, "all products over the AOI are _PR_ today (§82)"
    assert ni.parse_granule(DESC)["direction"] == "D"
    # A .h5 suffix must parse identically to the bare granule id.
    assert ni.parse_granule(WINTER + ".h5") == g


def test_non_nisar_names_are_rejected_not_guessed() -> None:
    for bad in ("S1AA_20260101T125624_20260113T125622_VVP012_INT80_G_weF_412F",
                "NISAR_L2_PR_GCOV_008_156_A_018_009_4000_SH_x", "", "nonsense"):
        try:
            ni.parse_granule(bad)
            raise AssertionError(f"accepted a non-GUNW name: {bad!r}")
        except ValueError:
            pass


def test_stack_id_is_distinct_from_every_s1_stack() -> None:
    """A NISAR stack must never collide with an S1 stack name — they share the manifest,
    and a collision would silently mix two bands into one inversion."""
    assert ni.stack_id(WINTER) == "NISAR_ASC_track156_frame018"
    assert ni.stack_id(DESC) == "NISAR_DESC_track135_frame072"
    assert ni.stack_id(WINTER).startswith("NISAR_")
    s1_like = re.compile(r"^(ASC|DESC)_path\d+_frame\d+$")
    assert not s1_like.match(ni.stack_id(WINTER))
    # Same track+frame, different dates -> SAME stack (that is what a stack means).
    assert ni.stack_id(WINTER) == ni.stack_id(MONSOON)


def test_product_name_is_readable_by_the_phase2_date_parser() -> None:
    """THE integration contract. custom_sbas_inverter.parse_pair_dates currently matches
    `S1[A-D][A-D]_<date>T<time>_<date>T<time>_`; the design doc's step 3 broadens that to
    accept NISAR too. This pins that our naming satisfies the broadened pattern EXACTLY, so
    the parser change is a one-line alternation and nothing else."""
    name = ni.product_name(WINTER)
    assert name == "NISAR_20251227T001346_20260108T001346_T156A_F018_GUNW", name
    broadened = re.compile(r"(?:S1[A-D][A-D]|NISAR)_(\d{8})T(\d{6})_(\d{8})T(\d{6})_")
    m = broadened.search(name)
    assert m, f"{name} would not parse after the documented parser broadening"
    assert (m.group(1), m.group(3)) == ("20251227", "20260108")
    # The CURRENT (unbroadened) parser must still reject it — proving the change is required
    # and has not been silently assumed.
    assert not re.search(r"S1[A-D][A-D]_(\d{8})T(\d{6})_(\d{8})T(\d{6})_", name)


def test_wavelength_is_derived_from_the_granule_not_hardcoded() -> None:
    lam = ni.wavelength_m(1_239_000_000.0)
    assert abs(lam - 0.241963) < 1e-5, lam
    for bad in (0, -1, None):
        try:
            ni.wavelength_m(bad)
            raise AssertionError(f"accepted implausible frequency {bad!r}")
        except (ValueError, TypeError):
            pass


def test_using_the_C_band_constant_on_L_band_would_underreport_4x() -> None:
    """NEGATIVE CONTROL for the §83 trap. Same phase, two wavelengths: the C-band constant
    shrinks L-band motion by ~4.4x. If someone ever routes NISAR through
    feature_engineering unchanged, this is the size of the silent error."""
    from feature_engineering import (COHERENCE_THRESHOLD as FE_THR,
                                     SENTINEL1_WAVELENGTH_M)
    lam_l = ni.wavelength_m(1_239_000_000.0)
    phase = 4.0 * 3.141592653589793          # exactly one wavelength of range change
    correct = ni.phase_to_los_displacement(phase, lam_l)
    wrong = ni.phase_to_los_displacement(phase, SENTINEL1_WAVELENGTH_M)
    assert abs(correct + lam_l) < 1e-9, "one cycle must map to one wavelength of LOS motion"
    assert correct < 0 and wrong < 0, "ASF sign convention: away from sensor is negative"
    ratio = correct / wrong
    assert 4.3 < ratio < 4.4, f"expected ~4.36x under-report, got {ratio:.3f}"

    # The mirrored masking threshold must equal the C-band chain's, or the two bands would be
    # quality-gated differently without anyone deciding that.
    assert ni.COHERENCE_THRESHOLD == FE_THR, (ni.COHERENCE_THRESHOLD, FE_THR)


def test_phase_to_displacement_matches_the_validated_formula() -> None:
    """With the S1 wavelength injected, this must reproduce feature_engineering exactly —
    the conversion is the same physics, only the constant is per-band."""
    import numpy as np

    from feature_engineering import (SENTINEL1_WAVELENGTH_M,
                                     phase_to_los_displacement as fe_convert)
    phase = np.array([-6.28318530718, -1.0, 0.0, 1.0, 6.28318530718], dtype="float32")
    mine = ni.phase_to_los_displacement(phase, SENTINEL1_WAVELENGTH_M)
    assert np.allclose(mine, fe_convert(phase), rtol=0, atol=1e-12)


# ------------------------------------------------------------------------------
# CLI runner (mirrors the rest of the battery).
# ------------------------------------------------------------------------------
def _all_tests() -> list:
    g = globals()
    return [(n, g[n]) for n in sorted(g) if n.startswith("test_") and callable(g[n])]


def main() -> int:
    tests = _all_tests()
    print(f"Running {len(tests)} NISAR-ingestion tests...")
    print("-" * 70)
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except Exception:
            failed += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
    print("-" * 70)
    print(f"Total: {len(tests) - failed} passed, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

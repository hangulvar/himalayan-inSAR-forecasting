"""
test_submit_pairs.py — the submitter's pair plumbing (2026-07-19): explicit --pair
parsing, the shared bucket-key definition, and the prefix-AGNOSTIC dedupe (the
cross-AOI blind spot that would have resubmitted 9 already-processed pairs for
the Ramban rebuild — the library is shared, so any prefix's job dedupes).

Hermetic: fake job/hyp3 objects only — no network, no credentials.

Run from project root (conda env active, or in the insar container):
    python -m pytest tests/test_submit_pairs.py -v
OR plain:
    python tests/test_submit_pairs.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import submit_hyp3_jobs as sub  # noqa: E402


def test_parse_pair_specs_valid():
    pairs = sub.parse_pair_specs(["A,B", "  C , D  "])
    assert pairs == [("A", "B"), ("C", "D")]


def test_parse_pair_specs_rejects_malformed():
    for bad in ["A", "A,B,C", "A,", ",B", "A,A"]:
        try:
            sub.parse_pair_specs([bad])
            raise AssertionError(f"{bad!r} did not raise ValueError")
        except ValueError:
            pass


def test_bucket_key_for():
    scene = SimpleNamespace(properties={"flightDirection": "ascending",
                                        "pathNumber": 27, "frameNumber": 106})
    assert sub.bucket_key_for(scene) == "ASCENDING_path27_frame106"
    bare = SimpleNamespace(properties={"pathNumber": 100, "frameNumber": 103})
    assert sub.bucket_key_for(bare) == "UNKNOWN_path100_frame103"


class _FakeJob:
    def __init__(self, name, granules, status="SUCCEEDED"):
        self.name = name
        self.job_parameters = {"granules": granules}
        self.status_code = status


class _FakeHyp3:
    def __init__(self, jobs):
        self._jobs = jobs

    def find_jobs(self):
        return self._jobs


def test_dedupe_is_prefix_agnostic():
    # The 2026-07-19 lesson: the VD backfill's jobs (other prefix) must dedupe a
    # Ramban submission of the same granule pair — the product library is shared.
    jobs = [
        _FakeJob("VD_Trikuta_ASCENDING_path27_frame105", ["A", "B"]),
        _FakeJob("Ramban_NH44_ASCENDING_path27_frame106", ["C", "D"]),
        _FakeJob("VD_Trikuta_ASCENDING_path27_frame105", ["E", "F"], "FAILED"),
        _FakeJob("VD_Trikuta_ASCENDING_path27_frame105", ["E", "F"], "FAILED"),
        _FakeJob("Ramban_NH44_ASCENDING_path27_frame106", ["G", "H"], "FAILED"),
    ]
    sigs = sub.fetch_existing_pair_signatures(_FakeHyp3(jobs), "Ramban_NH44")
    assert frozenset({"A", "B"}) in sigs          # other prefix still dedupes
    assert frozenset({"C", "D"}) in sigs          # own prefix as before
    assert frozenset({"E", "F"}) in sigs          # parked (2x FAILED), any prefix
    assert frozenset({"G", "H"}) not in sigs      # single failure -> retried


def test_dedupe_survives_find_jobs_error():
    class _Broken:
        def find_jobs(self):
            raise RuntimeError("api down")

    assert sub.fetch_existing_pair_signatures(_Broken(), "X") == set()


# ------------------------------------------------------------------------------
# Plain-python runner (mirrors the other suites)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)

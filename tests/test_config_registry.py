"""
test_config_registry.py — multi-AOI config registry plumbing assertions.

Verifies the per-AOI registry (config/*.yaml) and the root active_config
pointer stay coherent as AOIs are added: every file loads, slugs and HyP3
job-name prefixes are unique (the collision would silently mix two sites'
products), the pointer resolves into the registry, and the data-suffix
separation rules hold.

Stdlib + yaml only (no numpy/rasterio) — runs natively without the conda env.

Run from project root:
    python tests/test_config_registry.py
OR under pytest:
    python -m pytest tests/test_config_registry.py -v
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

from config import load_config  # noqa: E402

CONFIG_DIR = PROJECT_ROOT / "config"


def _registry_paths() -> list[Path]:
    return sorted(CONFIG_DIR.glob("*.yaml"))


def test_registry_is_nonempty() -> None:
    assert _registry_paths(), (
        f"No per-AOI configs in {CONFIG_DIR} — the registry should hold at "
        f"least ramban.yaml and vaishnodevi.yaml."
    )


def test_every_registry_config_loads() -> None:
    for p in _registry_paths():
        cfg = load_config(p)  # raises on missing keys / bad YAML
        assert cfg.aoi_path.exists(), (
            f"{p.name}: aoi_path {cfg.aoi_path.name} does not exist at the "
            f"project root."
        )


def test_slugs_and_prefixes_are_unique() -> None:
    cfgs = [load_config(p) for p in _registry_paths()]
    slugs = [c.aoi_slug for c in cfgs]
    prefixes = [c.job_name_prefix for c in cfgs]
    assert len(set(slugs)) == len(slugs), f"Duplicate AOI slugs: {slugs}"
    assert len(set(prefixes)) == len(prefixes), (
        f"Duplicate job_name_prefix values: {prefixes} — two AOIs would "
        f"claim each other's HyP3 jobs."
    )


def test_root_pointer_resolves_into_registry() -> None:
    root = load_config()  # follows active_config if present
    registry_slugs = {load_config(p).aoi_slug for p in _registry_paths()}
    assert root.aoi_slug in registry_slugs, (
        f"Root config resolves to slug '{root.aoi_slug}' which is not in the "
        f"registry ({sorted(registry_slugs)})."
    )


def test_data_suffix_separation_rules() -> None:
    """Ramban is grandfathered on the unsuffixed dirs; everyone else gets
    '_<slug>' — the invariant that lets AOIs coexist under data/."""
    for p in _registry_paths():
        cfg = load_config(p)
        expected = "" if cfg.aoi_slug == "ramban" else f"_{cfg.aoi_slug}"
        assert cfg.data_suffix == expected, (
            f"{p.name}: data_suffix {cfg.data_suffix!r} != {expected!r}"
        )


def test_product_stacks_follow_each_sites_standing_product() -> None:
    """stacks.product_stacks() must return the site's OWN product stacks — read
    from its union alerts file — never the live shared connectivity snapshot
    (the 2026-07-13 multi-AOI bug class: the snapshot follows whichever AOI's
    QA chain ran last)."""
    import json
    import os

    from stacks import product_stacks

    prev = os.environ.get("INSAR_CONFIG")
    try:
        for p in _registry_paths():
            cfg = load_config(p)
            union = (PROJECT_ROOT / "data" / f"alerts{cfg.data_suffix}"
                     / "mosaic_asc" / "alerts_operational.json")
            if not union.exists():
                continue  # brand-new AOI without a product yet: nothing to pin
            expected = json.loads(union.read_text(encoding="utf-8"))["source_stacks"]
            os.environ["INSAR_CONFIG"] = str(p)
            got = product_stacks()
            assert got == expected, (
                f"{p.name}: product_stacks() returned {got}, but the site's "
                f"standing product records {expected}"
            )
    finally:
        if prev is None:
            os.environ.pop("INSAR_CONFIG", None)
        else:
            os.environ["INSAR_CONFIG"] = prev


def test_soil_defaults_are_the_ramban_calibration() -> None:
    """A config WITHOUT a soil: block must land exactly on the Ramban-calibrated
    engine values (§20) — the guarantee that adding SoilConfig changed nothing
    numerically for existing sites."""
    import yaml

    minimal = {"aoi_path": "config/aoi/ramban_aoi.geojson", "job_name_prefix": "X",
               "search_start": "2025-01-01", "search_end": "2025-02-01"}
    tmp = PROJECT_ROOT / "data" / "_test_minimal_config.yaml"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(yaml.safe_dump(minimal), encoding="utf-8")
    try:
        s = load_config(tmp).soil
        assert (s.cohesion_dry_kpa, s.cohesion_wet_kpa, s.phi_deg,
                s.gamma_kn_m3, s.depth_m) == (18.5, 5.0, 36.0, 19.0, 3.0), (
            f"Soil defaults drifted from the §20 calibration: {s}"
        )
    finally:
        tmp.unlink(missing_ok=True)


def test_llof_routing_gate() -> None:
    """llof_routing (§60 4c): omitted -> 'twi' (the regression default that keeps the
    validated products byte-identical), 'd8' accepted, anything else fails loudly."""
    import yaml

    base = {"aoi_path": "config/aoi/ramban_aoi.geojson", "job_name_prefix": "X",
            "search_start": "2025-01-01", "search_end": "2025-02-01"}
    tmp = PROJECT_ROOT / "data" / "_test_llof_config.yaml"
    tmp.parent.mkdir(exist_ok=True)
    try:
        tmp.write_text(yaml.safe_dump(base), encoding="utf-8")
        assert load_config(tmp).llof_routing == "twi"
        tmp.write_text(yaml.safe_dump({**base, "llof_routing": "d8"}), encoding="utf-8")
        assert load_config(tmp).llof_routing == "d8"
        tmp.write_text(yaml.safe_dump({**base, "llof_routing": "dinf"}), encoding="utf-8")
        try:
            load_config(tmp)
            raise AssertionError("invalid llof_routing did not raise ValueError")
        except ValueError:
            pass
        for p in _registry_paths():
            assert load_config(p).llof_routing in ("twi", "d8"), p.name
    finally:
        tmp.unlink(missing_ok=True)


def test_llof_routing_adopted_state_is_d8_everywhere() -> None:
    """§67: the scheduled post-merge swap FIRED — every registry site now routes LLOF with
    real D8 flow accumulation, not the TWI proxy. Pinned so an accidental revert to the proxy
    is caught, and so flipping back is a deliberate, visible edit (the swap changes which
    zones carry the downstream-debris flag: Ramban 6/8 operational zones flipped, VD 3/14).

    If this test fails, decide which is true — a site was reverted on purpose (update this
    test AND the ledger), or the config drifted (fix the config).
    """
    for p in _registry_paths():
        assert load_config(p).llof_routing == "d8", (
            f"{p.name}: expected the adopted 'd8' routing (§67), got "
            f"'{load_config(p).llof_routing}'")


# ------------------------------------------------------------------------------
# CLI runner (mirrors tests/test_plumbing.py so both run the same way).
# ------------------------------------------------------------------------------
def _all_tests() -> list:
    g = globals()
    return [(n, g[n]) for n in sorted(g) if n.startswith("test_") and callable(g[n])]


def main() -> int:
    tests = _all_tests()
    print(f"Running {len(tests)} config-registry tests...")
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

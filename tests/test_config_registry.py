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


def test_period_split_parses_and_rejects_junk() -> None:
    """§79: `period_split: {stack: YYYY-MM-DD}` rescues a DISCONNECTED stack by inverting one
    period. Absent -> empty (the regression default). A malformed cutoff must fail AT LOAD,
    loudly — a silently-ignored typo puts the stack back on the skip list, which is how the
    ALERT footprint was emptied in the first place (§78)."""
    import yaml

    base = {"aoi_path": "config/aoi/ramban_aoi.geojson", "job_name_prefix": "X",
            "search_start": "2025-01-01", "search_end": "2025-02-01"}
    tmp = PROJECT_ROOT / "data" / "_test_period_split_config.yaml"
    tmp.parent.mkdir(exist_ok=True)
    try:
        tmp.write_text(yaml.safe_dump(base), encoding="utf-8")
        assert load_config(tmp).period_split == {}, "absent block must default to empty"

        # Quoted string AND bare YAML date (PyYAML turns the latter into datetime.date).
        for value in ("2026-07-07", __import__("datetime").date(2026, 7, 7)):
            tmp.write_text(yaml.safe_dump({**base, "period_split": {"ASC_p1_f1": value}}),
                           encoding="utf-8")
            assert load_config(tmp).period_split == {"ASC_p1_f1": "2026-07-07"}, repr(value)

        for bad in ("07-07-2026", "not-a-date", "2026-13-40"):
            tmp.write_text(yaml.safe_dump({**base, "period_split": {"ASC_p1_f1": bad}}),
                           encoding="utf-8")
            try:
                load_config(tmp)
                raise AssertionError(f"malformed period_split cutoff {bad!r} did not raise")
            except ValueError:
                pass

        tmp.write_text(yaml.safe_dump({**base, "period_split": ["ASC_p1_f1"]}), encoding="utf-8")
        try:
            load_config(tmp)
            raise AssertionError("period_split as a list did not raise")
        except ValueError:
            pass
    finally:
        tmp.unlink(missing_ok=True)


def test_period_split_stacks_are_RUN_not_skipped() -> None:
    """§79 REGRESSION GUARD — the whole point of the config entry.

    A stack the connectivity gate calls 'disconnected' must still be RUN when the registry
    names a period_split cutoff for it, and must be SKIPPED when it does not. Without this,
    a plain `run_multistack` (no --stacks) silently drops the stack from the run AND from the
    union mosaic — which took VD's ALERT footprint from 14 zones to 0 with nothing erroring.
    """
    import json
    import os

    import run_multistack as rm

    diag = {"stacks": {"ASC_good": {"status": "connected"},
                       "ASC_split": {"status": "disconnected"},
                       "ASC_hopeless": {"status": "disconnected"}}}
    tmp_diag = PROJECT_ROOT / "data" / "_test_rescue_recs.json"
    tmp_cfg = PROJECT_ROOT / "data" / "_test_period_split_run.yaml"
    saved_path, saved_env = rm.RESCUE_RECOMMENDATIONS, os.environ.get("INSAR_CONFIG")
    try:
        import yaml
        tmp_diag.write_text(json.dumps(diag), encoding="utf-8")
        tmp_cfg.write_text(yaml.safe_dump({
            "aoi_path": "config/aoi/ramban_aoi.geojson", "job_name_prefix": "X",
            "search_start": "2025-01-01", "search_end": "2025-02-01",
            "period_split": {"ASC_split": "2026-07-07"}}), encoding="utf-8")
        rm.RESCUE_RECOMMENDATIONS = tmp_diag
        os.environ["INSAR_CONFIG"] = str(tmp_cfg)

        got = rm.connected_stacks()
        assert got == ["ASC_good", "ASC_split"], got
        assert "ASC_hopeless" not in got, "a disconnected stack with NO cutoff must stay skipped"

        # NEGATIVE CONTROL: drop the cutoff and the rescued stack must fall back out.
        tmp_cfg.write_text(yaml.safe_dump({
            "aoi_path": "config/aoi/ramban_aoi.geojson", "job_name_prefix": "X",
            "search_start": "2025-01-01", "search_end": "2025-02-01"}), encoding="utf-8")
        assert rm.connected_stacks() == ["ASC_good"], "no cutoff -> no rescue"
    finally:
        rm.RESCUE_RECOMMENDATIONS = saved_path
        tmp_diag.unlink(missing_ok=True)
        tmp_cfg.unlink(missing_ok=True)
        if saved_env is None:
            os.environ.pop("INSAR_CONFIG", None)
        else:
            os.environ["INSAR_CONFIG"] = saved_env


def test_vaishnodevi_carries_the_load_bearing_period_split() -> None:
    """§79: VD's `ASC_path27_frame105` cutoff is load-bearing — it is the only thing keeping the
    stack (and therefore every alert zone it carries) in the union mosaic. If this fails, either
    path27's tail reconnected and the entry was deliberately removed (update the ledger too), or
    the config drifted and the map is about to silently empty."""
    cfg = load_config(CONFIG_DIR / "vaishnodevi.yaml")
    assert cfg.period_split.get("ASC_path27_frame105") == "2026-07-07", cfg.period_split


def test_status_card_never_shows_a_score_for_a_map_it_did_not_measure() -> None:
    """§78/§79 applied to the multi-AOI dashboard: this card printed "AUC 0.76" one line under
    "operational zones: none", because it read the back-test's AUC without checking WHICH map
    that back-test scored. A score must travel with the footprint it measured, and read
    NOT MEASURED once the map has moved.

    Asserted on the real cards (the artifact a user opens): for every registry site, whenever
    the scored zone count and today's zone count disagree, the validation row must not carry a
    bare AUC. Sites without products are skipped — they have no card to get wrong.
    """
    import json as _json
    import sys as _sys

    _sys.path.insert(0, str(PROJECT_ROOT / "workflows"))
    import aoi_status

    checked = 0
    for p in _registry_paths():
        st = aoi_status.assess(p)
        # assess() serialises its Stage dataclasses to dicts for the JSON/HTML surfaces.
        row = next((s for s in st.stages if s.get("key") == "validation"), None)
        if row is None or not row.get("done"):
            continue
        cfg = load_config(p)
        bt = (PROJECT_ROOT / "data" / "inventory"
              / f"backtest_operational{cfg.data_suffix}_report.json")
        if not bt.exists():
            continue
        scored = _json.loads(bt.read_text(encoding="utf-8")).get("n_flagged_zones")
        live = st.footprint_zones
        if not (isinstance(scored, int) and live.isdigit()):
            continue
        checked += 1
        if scored != int(live):
            assert "NOT MEASURED" in row["detail"], (
                f"{p.name}: the card shows {row['detail']!r} for a map with {live} zone(s) that "
                f"was scored at {scored} zone(s) — the score describes a different map")
        else:
            assert "NOT MEASURED" not in row["detail"], (
                f"{p.name}: the card withheld a score that DOES describe this map "
                f"({live} zones) — 'not measured' must not become the safe default")
    assert checked, "no site had both a scored back-test and a zone count — test was vacuous"


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

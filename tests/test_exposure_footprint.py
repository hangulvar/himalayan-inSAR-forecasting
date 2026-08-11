"""
test_exposure_footprint.py — the contract for the affected-area layer (zone shapes +
downstream corridors + ranked coordinates), and for its two surfaces (the dashboard card and
the 3-D explorer toggle).

What this suite is protecting, in order of how badly each would hurt:

  E1  the shapes are the PUBLISHED zones. exposure_footprint re-derives each zone's pixels from
      the rasters; if that ever stops reproducing alerts_<footprint>.json, the map would show
      confident outlines for a product nobody scored. The gate must REFUSE, not round off.
  E2  the runout physics is the shared, cited one — bands imported from rockfall_runout, routing
      imported from flood_domain (itself pinned to flow_routing_probe). Copies drift; imports
      cannot. Plus the properties a first-order energy line must have: never uphill, nested
      bands, a lower angle reaching further.
  E3  every claim about trust is COMPUTED. The headline over a below-chance map must say
      withdrawn, and the wording must come from operational_alarm._chance_verdict, not from a
      literal typed next to it (§79).
  E4  absence has a name. A watch footprint has no live gate — that must render as
      "not applicable", never as a plausible-looking `false`.
  E5  the KML/GeoJSON cannot be an injection vector, WITH a negative control that proves the
      audit can fail.
  E6  both surfaces are additive: the dashboard without the layer is byte-identical to the old
      page, and the 3-D scenario buttons cannot flip the new traces.

Hermetic: no network, no rasterio reads of data/, and NOTHING is written under data/ (§6 #10 —
a test that shells out to a workflow inherits production paths). Synthetic DEMs and fixtures
only; the two artifact checks skip cleanly when the git-ignored outputs are absent.

Run from project root:
    python tests/test_exposure_footprint.py
OR under pytest:
    python -m pytest tests/test_exposure_footprint.py -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import traceback
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import numpy as np  # noqa: E402

import exposure_footprint as ef  # noqa: E402


# ------------------------------------------------------------------------------
# Synthetic terrain: a constant slope that flattens onto a plain.
# ------------------------------------------------------------------------------
def _ramp_dem(h: int = 40, w: int = 12, drop_per_cell: float = 60.0,
              flat_at: int = 20) -> np.ndarray:
    """Elevation falling steeply down the rows, then flat — so an energy line MUST run out."""
    z = np.zeros((h, w), dtype=np.float64)
    for r in range(h):
        z[r, :] = max(0.0, (flat_at - r)) * drop_per_cell
    return z


def _targets(dem):
    from flood_domain import d8_targets
    return d8_targets(dem)


# ------------------------------------------------------------------------------
# E2 — the physics is SHARED, not re-implemented, and behaves like an energy line
# ------------------------------------------------------------------------------
def test_bands_and_routing_are_the_shared_validated_functions() -> None:
    import flood_domain as fd
    import flow_routing_probe as frp
    import rockfall_runout as rr

    assert ef.BANDS is rr.BANDS, (
        "the reach bands must be IMPORTED from rockfall_runout (Evans & Hungr 1993) so the "
        "citation and the numbers cannot drift apart")
    assert ef.d8_targets is fd.d8_targets, "routing must be the shared D8, never a copy"
    assert fd.d8_accumulation is frp.d8_accumulation, (
        "flood_domain's D8 must still be pinned to the validated probe")
    from run_multistack import MERGE_DEG
    assert ef.MERGE_DEG == MERGE_DEG, "the union-merge distance must be the product's own"


def test_trace_never_travels_uphill() -> None:
    dem = _ramp_dem()
    best, _ = ef.trace_downstream(dem, _targets(dem), 80.0, [(2, 6)], min_angle_deg=22.0)
    assert best, "the trace found nothing on a steep synthetic slope"
    z0 = dem[2, 6]
    for (r, c) in best:
        assert dem[r, c] <= z0, f"cell {(r, c)} is ABOVE the source — debris does not climb"


def test_energy_line_stops_on_the_flat_and_a_lower_angle_reaches_further() -> None:
    """The defining property of a Fahrboeschung screen: material stops when the line from the
    detachment point drops below the reach angle, and a SHALLOWER angle means a longer runout."""
    dem = _ramp_dem()
    tg = _targets(dem)
    steep, _ = ef.trace_downstream(dem, tg, 80.0, [(2, 6)], min_angle_deg=32.0)
    shallow, _ = ef.trace_downstream(dem, tg, 80.0, [(2, 6)], min_angle_deg=22.0)
    far_steep = max(r for r, _ in steep)
    far_shallow = max(r for r, _ in shallow)
    assert far_shallow >= far_steep, (
        f"a lower reach angle must reach at least as far: 22deg stopped at row {far_shallow}, "
        f"32deg at row {far_steep}")
    assert far_shallow < dem.shape[0] - 1, (
        "the trace ran to the DEM edge on terrain that flattens — the energy line is not "
        "stopping anything")


def test_reach_bands_are_nested() -> None:
    """LIKELY ⊆ POSSIBLE ⊆ MAX_SHADOW. If they ever cross, the map would show a 'likely' reach
    beyond its own outer bound."""
    dem = _ramp_dem()
    best, _ = ef.trace_downstream(dem, _targets(dem), 80.0, [(2, 6)], min_angle_deg=22.0)
    masks = ef.corridor_masks(best, dem.shape)
    order = [name for name, _ in ef.BANDS]          # steepest (smallest) first
    for inner, outer in zip(order, order[1:]):
        if inner in masks and outer in masks:
            assert (masks[inner] & ~masks[outer]).sum() == 0, (
                f"{inner} extends outside {outer} — the bands are not nested")


def test_reach_distance_is_measured_from_the_zone() -> None:
    dem = _ramp_dem()
    best, _ = ef.trace_downstream(dem, _targets(dem), 80.0, [(2, 6)], min_angle_deg=22.0)
    masks = ef.corridor_masks(best, dem.shape)
    reach = ef.band_reach_m(masks, (2, 6), 80.0)
    assert reach, "no reach distance reported for a corridor that exists"
    assert all(v > 0 for v in reach.values())
    widest = ef.BANDS[-1][0]
    if widest in reach:
        assert reach[widest] == max(reach.values()), (
            "the widest (lowest-angle) band must be the one that reaches furthest")


def test_trace_reports_why_it_stopped() -> None:
    """Silence is indistinguishable from success (§6 #5): a corridor cut off by the window edge
    must be recorded as truncated, not published as a runout that ended there."""
    dem = _ramp_dem(h=8, w=6, flat_at=99)            # never flattens -> must hit the edge
    _, stats = ef.trace_downstream(dem, _targets(dem), 80.0, [(1, 3)], min_angle_deg=22.0)
    assert sum(stats.values()) >= 1, "the trace ended without recording a reason"
    assert stats["hit_window_edge"] >= 1, (
        f"a slope that never flattens must end at the window edge, got {stats}")


# ------------------------------------------------------------------------------
# E1 — the shapes ARE the published zones, or nothing is written
# ------------------------------------------------------------------------------
def _cluster(rows, cols, vel=-30.0, zid=1):
    return {"ys": np.array(rows), "xs": np.array(cols), "mean_velocity_mmyr": vel, "id": zid}


def _published(rowcol, n_pixels, zid=1):
    return {"id": zid, "pixel_rowcol": list(rowcol), "n_pixels": n_pixels}


def test_identity_gate_accepts_the_matching_product() -> None:
    c = _cluster([10, 10, 11], [4, 5, 4])
    ef.verify_against_published([c], [_published([10, 4], 3)], "STACK")   # must not raise


def test_zone_order_uses_the_products_ROUNDED_velocity() -> None:
    """The published order is the order of the speeds ROUNDED to 1 dp — CascadingReasoner builds
    its zone dicts (which round) and only THEN sorts. Sorting full-precision means is invisible
    while every zone is distinct, and silently re-orders the moment two zones round together;
    11 of Ramban's 65 watch-tier zones do, and the identity gate caught it mid-session.

    Behavioural, not a source grep: two synthetic zones whose means round to the SAME value but
    differ at the second decimal, arranged so the rounded order (stable -> label order) and the
    unrounded order are OPPOSITE. Ordering by the raw means fails this test.
    """
    import agentic_orchestrator as ao
    from rasterio.transform import from_origin

    vel = np.full((10, 10), np.nan, dtype=np.float64)
    vel[1, 1:4] = [-20.00, -20.02, -20.04]          # label 1, mean -20.02
    vel[5, 1:4] = [-20.02, -20.04, -20.06]          # label 2, mean -20.04  (FASTER)
    fs = np.full((10, 10), 0.5)

    class _Auditor:
        def __init__(self, stack, use_vslope=False):
            self.velocity, self.transform = vel, from_origin(500000, 3700000, 80, 80)
            self.crs, self.width, self.height = "EPSG:32643", 10, 10

        def creep_mask(self, thr):
            return np.isfinite(self.velocity) & (self.velocity < thr)

    class _Trigger:
        def __init__(self, stack, scenario, cfg=None):
            self.fs = fs

        def unstable_mask(self, fail):
            return np.isfinite(self.fs) & (self.fs < fail)

    a_orig, t_orig = ao.InSARAuditor, ao.MeteorologicalTrigger
    try:
        ao.InSARAuditor, ao.MeteorologicalTrigger = _Auditor, _Trigger
        clusters, *_ = ef.zone_pixels("SYNTHETIC", "operational")
    finally:
        ao.InSARAuditor, ao.MeteorologicalTrigger = a_orig, t_orig

    assert len(clusters) == 2, clusters
    assert all(c["mean_velocity_mmyr"] == -20.0 for c in clusters), (
        [c["mean_velocity_mmyr"] for c in clusters])
    assert int(clusters[0]["ys"][0]) == 1, (
        "zone #1 is the row-5 cluster — the zones were ordered by the FULL-PRECISION mean, "
        "which is not the order the published product uses")


def test_identity_gate_refuses_a_moved_or_resized_zone() -> None:
    c = _cluster([10, 10, 11], [4, 5, 4])
    for bad, why in ((_published([12, 9], 3), "centroid moved"),
                     (_published([10, 4], 7), "pixel count changed")):
        try:
            ef.verify_against_published([c], [bad], "STACK")
        except SystemExit as e:
            assert "refusing to write" in str(e), str(e)
        else:
            raise AssertionError(f"the gate accepted a zone whose {why} — polygons would "
                                 f"describe a map that was never published")
    try:
        ef.verify_against_published([c, c], [_published([10, 4], 3)], "STACK")
    except SystemExit as e:
        assert "count mismatch" in str(e), str(e)
    else:
        raise AssertionError("the gate accepted a different NUMBER of zones")


# ------------------------------------------------------------------------------
# E3 — every trust claim is derived from the score
# ------------------------------------------------------------------------------
def test_headline_is_derived_and_withdraws_a_below_chance_map() -> None:
    import operational_alarm as oa

    below = {"state": "scored", "auc": 0.326, "n_zones": 30,
             "verdict": ef._plain(oa._chance_verdict(0.326))}
    near = {"state": "scored", "auc": 0.516, "n_zones": 106, "recall": 0.616,
            "verdict": ef._plain(oa._chance_verdict(0.516))}
    good = {"state": "scored", "auc": 0.676, "n_zones": 8,
            "verdict": ef._plain(oa._chance_verdict(0.676))}
    h_below, h_near, h_good = ef._headline(below), ef._headline(near), ef._headline(good)
    assert "WITHDRAWN" in h_below and "must NOT be used" in h_below, h_below
    assert "beats chance" not in h_below.lower(), (
        "a below-chance map was described as beating chance — the §79 defect, back")
    assert "PRIORITISE" in h_good and "WITHDRAWN" not in h_good, h_good
    # ~chance is its OWN state: no measured ranking skill, but a recall tier still has breadth.
    # Collapsing it into either neighbour would either overstate or understate it.
    assert "NO MEASURED SKILL" in h_near and "62%" in h_near, h_near
    assert "WITHDRAWN" not in h_near and "PRIORITISE" not in h_near, h_near
    for state, must in (("not_measured", "NOT MEASURED"),
                        ("never_scored", "UNVALIDATED"),
                        ("no_footprint", "No footprint")):
        assert must in ef._headline({"state": state}), state


def test_verdict_wording_comes_from_the_dashboards_own_function() -> None:
    """_plain must strip the MARKUP and nothing else — the words are operational_alarm's, so the
    KML an operator opens and the page they read can never disagree about the verdict."""
    import operational_alarm as oa
    for auc in (0.32, 0.50, 0.76, None):
        raw = oa._chance_verdict(auc)
        plain = ef._plain(raw)
        assert "<" not in plain and ">" not in plain, plain
        # every non-markup character survives, in order
        assert plain == raw.replace("<b>", "").replace("</b>", ""), (auc, raw, plain)


# ------------------------------------------------------------------------------
# E4 — absence has a name
# ------------------------------------------------------------------------------
def test_live_gate_is_not_applicable_outside_the_operational_footprint() -> None:
    keys, ctx = ef.active_zone_keys("watch", None)
    assert keys == set()
    assert ctx.get("state") == "not_applicable", ctx
    assert "operational footprint only" in ctx.get("reason", ""), ctx


def test_live_line_separates_never_measured_from_none_active() -> None:
    assert "not measured" in ef._live_line({"active": None}).lower()
    assert "not applicable" in ef._live_line(
        {"active": {"state": "not_applicable", "reason": "x"}}).lower()
    live = ef._live_line({"active": {"as_of": "2026-08-05", "n_active": 0, "n_total": 8,
                                     "regional_level": "DORMANT", "saturation_m": 0.1}})
    assert "0 of 8" in live and "2026-08-05" in live, live


# ------------------------------------------------------------------------------
# E5 — the exported layer cannot carry markup through, + a negative control
# ------------------------------------------------------------------------------
_PAYLOAD = "]]></name><Placemark><name>pwned</name><description>&<script>x</script>"


def _hostile_zone() -> dict:
    return {"stack": _PAYLOAD, "zone_id": 1, "severity": _PAYLOAD, "lon": 75.1, "lat": 33.2,
            "area_km2": 0.03, "n_pixels": 5, "creep_mmyr": -30.0, "m_star": 0.4,
            "vulnerability_tier": _PAYLOAD, "detection_confidence": 0.8,
            "triage_priority": 0.5, "triage_rank": 1, "n_looks": 1, "active_today": True,
            "rings": [[[75.1, 33.2], [75.11, 33.2], [75.11, 33.21], [75.1, 33.2]]],
            "downstream": {}, "downstream_reach_m": {}}


def _meta(zones) -> dict:
    return {"footprint": "operational", "n_union_zones": len(zones),
            "generated_utc": "2026-08-11 00:00 UTC", "headline": "h", "scope_caveat": "c",
            "verdict": {"state": "scored", "auc": 0.6, "text": "t"},
            "band_note": {n: f"note {n}" for n, _ in ef.BANDS},
            "top5": [{"rank": 1, "lat": 33.2, "lon": 75.1, "priority": 0.5, "m_star": 0.4,
                      "detection_confidence": 0.8, "n_looks": 1}]}


def _kml_placemark_names(path: Path) -> list[str]:
    import xml.etree.ElementTree as ET
    ns = "{http://www.opengis.net/kml/2.2}"
    return [(p.findtext(ns + "name") or "") for p in ET.parse(path).getroot().iter(ns + "Placemark")]


def test_kml_is_well_formed_and_hostile_text_stays_text() -> None:
    zones = [_hostile_zone()]
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "e.kml"
        ef.write_kml(out, zones, _meta(zones))
        names = _kml_placemark_names(out)          # raises on malformed XML
    assert names, "no placemarks parsed out of the KML"
    assert not any(n.strip() == "pwned" for n in names), (
        "an injected <Placemark> survived into the KML tree — the payload was not escaped")


def test_kml_escaping_audit_can_actually_fail() -> None:
    """NEGATIVE CONTROL: with the escaper disabled the check above MUST break. A guard that
    cannot fail is not a guard."""
    zones = [_hostile_zone()]
    original = ef.xml_escape
    try:
        ef.xml_escape = lambda v: v                      # the vulnerable behaviour
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "e.kml"
            ef.write_kml(out, zones, _meta(zones))
            try:
                names = _kml_placemark_names(out)
            except Exception:                            # malformed XML is also a detection
                return
    finally:
        ef.xml_escape = original
    assert any(n.strip() == "pwned" for n in names), (
        "the audit did not notice an UNESCAPED payload — the KML test above is vacuous")


def test_geojson_features_are_closed_rings_in_lonlat() -> None:
    zones = [dict(_hostile_zone(), stack="S", severity="HIGH", vulnerability_tier="t")]
    feats = ef.to_features(zones, _meta(zones))
    assert feats and feats[0]["properties"]["kind"] == "hazard_zone"
    assert "rings" not in feats[0]["properties"] and "downstream" not in feats[0]["properties"]
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "e.geojson"
        ef.write_geojson(out, feats, _meta(zones))
        gj = json.loads(out.read_text(encoding="utf-8"))
    assert gj["type"] == "FeatureCollection"
    for f in gj["features"]:
        for poly in f["geometry"]["coordinates"]:
            for ring in poly:
                assert ring[0] == ring[-1], "ring is not closed"
                for lon, lat in ring:
                    assert 60 < lon < 100 and 5 < lat < 40, (lon, lat)


# ------------------------------------------------------------------------------
# E6 — both surfaces are additive
# ------------------------------------------------------------------------------
_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c6360000002000100ffff03000006000557bfabd4"
    "0000000049454e44ae426082")


def _dashboard_args(tmp: Path):
    fig = tmp / "fig.png"
    fig.write_bytes(_TINY_PNG)
    r = {"season": {"start": "2026-06-01", "end": "2026-06-02", "days": 2},
         "level_counts": {"DORMANT": 1, "WATCH": 1, "ALERT": 0},
         "alert_pct_season": 0.0, "raw_regional_trigger_days": 1,
         "selectivity_gain_raw_to_alert": "1 -> 0 days (1.0x fewer)",
         "events_caught_by_alarm": "0/0", "events_caught_by_alert": "0/0",
         "per_event": [], "footprint_zones": 3}
    tier = {"scenario": "operational", "m": 0.5, "n_zones": 3, "n_crit": 1, "n_multi": 1,
            "auc": None, "recall": None, "spec": None, "lift250": None,
            "core_zones": None, "core_auc": None, "core_lift": None}
    return (r, [date(2026, 6, 1), date(2026, 6, 2)], np.array([0.5, 1.2]),
            ["DORMANT", "WATCH"], fig, tier)


def _exposure_report(n_zones: int = 2) -> dict:
    return {"footprint": "operational", "n_union_zones": n_zones, "n_shapes": n_zones,
            "headline": "This map scores better than chance at this site: use it to PRIORITISE "
                        "inspections, not to declare anywhere safe.",
            "scope_caveat": "First-order screen, not a runout simulation.",
            "verdict": {"state": "scored", "auc": 0.676, "verdict": "beats chance"},
            "active": {"as_of": "2026-08-05", "n_active": 1, "n_total": n_zones,
                       "regional_level": "WATCH", "saturation_m": 0.435},
            "top5_by_triage_priority": [
                {"rank": 1, "lat": 33.27, "lon": 75.14, "priority": 0.574, "m_star": 0.298,
                 "detection_confidence": 0.817, "n_looks": 1}]}


def _render(tmp: Path, exposure, other=None) -> str:
    import operational_alarm as oa
    r, dates, E, levels, fig, tier = _dashboard_args(tmp)
    out = tmp / f"dash_{'with' if exposure else 'without'}.html"
    oa.write_dashboard(out, r, dates, E, levels, 1, fig, tier,
                       exposure=exposure, exposure_other=other)
    return out.read_text(encoding="utf-8")


def test_dashboard_without_the_layer_is_the_old_page() -> None:
    import operational_alarm as oa
    exp = _exposure_report()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        without = _render(tmp, None)
        with_exp = _render(tmp, exp)
    assert "AFFECTED AREA" not in without, "the card rendered with NO layer present"
    card = oa._exposure_card(exp, None)
    assert card in with_exp, "the rendered card is not verbatim in the page"
    assert with_exp.replace(card, "") == without, (
        "the affected-area card changed the surrounding page — it must be a pure insertion")


def test_card_says_empty_map_not_safe_slope_and_points_at_the_wider_layer() -> None:
    import operational_alarm as oa
    card = oa._exposure_card(_exposure_report(n_zones=0), other="watch")
    assert "No shapes" in card and "not a safe slope" in card, card
    assert "exposure_watch.kml" in card, "an empty ALERT map must point at the wider layer"


def test_card_colours_the_headline_from_the_verdict() -> None:
    """§79 applied to CSS: a red warning over a map that beats chance is a caution it has not
    earned; a calm colour over a withdrawn map is an endorsement it must never get."""
    import operational_alarm as oa
    good = oa._exposure_card(_exposure_report())
    bad_rep = dict(_exposure_report(),
                   verdict={"state": "scored", "auc": 0.326, "verdict": "BELOW chance"},
                   headline="WITHDRAWN AS A RANKING: ...")
    bad = oa._exposure_card(bad_rep)
    assert "#1a8a4a" in good and "#a33" not in good.split("</h2>")[1][:400], good[:400]
    assert "#a33" in bad, bad[:400]


def test_live_alarm_hook_is_non_fatal_and_runs_before_the_dashboard() -> None:
    """Same contract the flood/imerg hooks are held to (R9): a failure here must not take the
    validated daily arm down, and the layer must refresh BEFORE the page that shows it."""
    src = (PROJECT_ROOT / "workflows" / "live_alarm.py").read_text(encoding="utf-8")
    assert 'run("exposure_footprint.py"' in src, "the layer is not wired into live_alarm.py"
    i = src.index('run("exposure_footprint.py"')
    try_at = src.rfind("try:", 0, i)
    assert try_at != -1 and src.count("run(", try_at, i) == 0, (
        "the exposure_footprint call is not the first statement of its own try block — a "
        "failure would break the validated daily alarm")
    assert "SKIPPED" in src[i:src.index("except", i) + 300], (
        "the hook's failure path must say it was skipped, not fail silently")
    assert i < src.index('run("operational_alarm.py"'), (
        "the layer must refresh BEFORE the dashboard render, or its card is a run behind")


def test_three_d_layer_is_omitted_when_it_has_not_been_generated() -> None:
    """The 3-D explorer must degrade to exactly the old dashboard when the layer is absent."""
    import build_3d_dashboard as b3
    traces, meta = b3.exposure_traces("ASC_pathX_frameY", "no_such_footprint_for_tests",
                                      None, None, None, 1, 1, 0.0)
    assert traces == [] and meta is None


def test_three_d_controls_target_disjoint_traces() -> None:
    """ARTIFACT check on the page a user actually opens (§6 #1): the scenario buttons and the
    affected-area buttons must restyle DISJOINT trace indices. Without explicit indices the
    scenario visibility array spills onto the new traces and silently flips them.
    Skips when the git-ignored dashboard has not been built."""
    import re
    pages = sorted(PROJECT_ROOT.glob("data/alerts*/dashboard_3d.html"))
    if not pages:
        print("      [3-D] no dashboard_3d.html on disk — skipped")
        return
    checked = 0
    for page in pages:
        m = re.search(r"var layout = (\{.*?\});\n", page.read_text(encoding="utf-8"), re.S)
        assert m, f"{page.name}: could not find the embedded layout"
        menus = json.loads(m.group(1)).get("updatemenus", [])
        if len(menus) < 2:
            continue                     # built before the layer existed for that AOI
        idx = []
        for menu in menus:
            for b in menu["buttons"]:
                assert len(b["args"]) == 2 and isinstance(b["args"][1], list), (
                    f"{page.name}: a control restyles WITHOUT explicit trace indices")
                assert len(b["args"][0]["visible"]) == len(b["args"][1]), (
                    f"{page.name}: visibility array and index list disagree in length")
            idx.append({i for b in menu["buttons"] for i in b["args"][1]})
        assert idx[0].isdisjoint(idx[1]), (
            f"{page.name}: the scenario buttons and the affected-area buttons touch the same "
            f"traces — pressing a scenario would flip the layer")
        checked += 1
    print(f"      [3-D] {checked} dashboard(s) audited for disjoint controls")


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

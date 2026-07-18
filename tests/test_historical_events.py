"""
test_historical_events.py — the curated Past-events record + dashboard tab
(operational_alarm.py: load_historical_events / _hist_panel / write_dashboard).

What is asserted:
  • both sites' historical-events JSONs are schema-valid, source-cited, inside
    their AOI, never future-dated (the §36 fabricated-event lesson), and every
    LOW-confidence row is explicitly flagged for user review;
  • the Vaishno Devi exclusion record (the fabricated "2 Sep 2025" event, §38)
    stays excluded — no event falls in the verified yatra-closure window;
  • ranking is deaths desc → injured → damage_score (worst damage first);
  • every event is annotated with its CURRENT alert standing (nearest hazard
    zone + live parameters) for BOTH sites, and distances are sane;
  • the rendered tab carries Google Maps links, confidence badges and the
    pending-review markers; the dashboard page keeps its existing tabs intact
    and degrades gracefully (no Past-events button) when the record is absent.

Run from project root (conda env active, or in the insar container):
    python -m pytest tests/test_historical_events.py -v
OR plain:
    python tests/test_historical_events.py
"""

from __future__ import annotations

import json
import base64
import sys
import tempfile
import traceback
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import operational_alarm as oa  # noqa: E402

INV_DIR = PROJECT_ROOT / "data" / "inventory"
SLUGS = ["ramban", "vaishnodevi"]
CONF_GRADES = {"VERIFIED", "HIGH", "MEDIUM", "LOW"}
# 1x1 transparent PNG for exercising write_dashboard without matplotlib savefig.
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def _load(slug: str) -> dict:
    f = INV_DIR / f"{slug}_historical_events.json"
    assert f.exists(), f"missing curated record {f}"
    return json.loads(f.read_text(encoding="utf-8"))


def _aoi_bbox(slug: str):
    g = json.loads((PROJECT_ROOT / "config" / "aoi" / f"{slug}_aoi.geojson")
                   .read_text(encoding="utf-8"))

    def flat(c):
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for x in c:
                yield from flat(x)
    pts = [p for f in g["features"] for p in flat(f["geometry"]["coordinates"])]
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    return min(lons), max(lons), min(lats), max(lats)


def test_schema_and_provenance_both_sites():
    for slug in SLUGS:
        payload = _load(slug)
        assert payload.get("site") == slug
        assert payload.get("note") and payload.get("updated")
        events = payload.get("events", [])
        assert events, f"{slug}: empty events list"
        for e in events:
            assert e.get("name") and e.get("damage"), e
            assert isinstance(e.get("lat"), (int, float)) and isinstance(e.get("lon"), (int, float))
            assert e.get("confidence") in CONF_GRADES, e["name"]
            assert 0 < e.get("confidence_score", 0) <= 1, e["name"]
            assert e.get("confidence_reason"), e["name"]
            assert e.get("sources") and all(s.get("label") for s in e["sources"]), e["name"]
            for s in e["sources"]:
                if s.get("url"):
                    assert s["url"].startswith("https://") and " " not in s["url"], s
            # Date rule: ISO date in the past, or null with an explicit date_note.
            if e.get("date") is None:
                assert e.get("date_note"), f"{e['name']}: undated without date_note"
            else:
                d = date.fromisoformat(e["date"])  # raises on malformed
                assert d <= date.today(), f"{e['name']}: future-dated (the §36 lesson)"
            # Every LOW row must be flagged for user review, and vice-versa noted.
            if e["confidence"] == "LOW":
                assert e.get("review_needed") is True, f"{e['name']}: LOW but not review-flagged"
            if e.get("review_needed"):
                assert "REVIEW" in e["confidence_reason"].upper(), e["name"]


def test_events_inside_aoi():
    for slug in SLUGS:
        lon_min, lon_max, lat_min, lat_max = _aoi_bbox(slug)
        for e in _load(slug)["events"]:
            assert lon_min - 0.02 <= e["lon"] <= lon_max + 0.02, (slug, e["name"])
            assert lat_min - 0.02 <= e["lat"] <= lat_max + 0.02, (slug, e["name"])


def test_vaishnodevi_exclusion_record_immunized():
    """The fabricated '2 Sep 2025' event (§38) must stay excluded: the note keeps the
    immunization record, and no event may fall inside the verified yatra-closure window
    (27 Aug - 14 Sep 2025) during which the route was demonstrably empty."""
    payload = _load("vaishnodevi")
    assert "2 Sep 2025" in payload["note"]
    for e in payload["events"]:
        if e.get("date"):
            d = date.fromisoformat(e["date"])
            assert not (date(2025, 8, 27) <= d <= date(2025, 9, 14)), \
                f"{e['name']}: dated inside the verified closure window"


def test_ranking_worst_damage_first():
    for slug, top_name, top_deaths in [("ramban", "Khooni Nallah", 10),
                                       ("vaishnodevi", "Ardhkuwari", 34)]:
        hist = _run_loader(slug)
        events = hist["events"]
        deaths = [(e.get("deaths") or 0) for e in events]
        assert deaths == sorted(deaths, reverse=True), f"{slug}: not deaths-desc"
        assert top_name in events[0]["name"] and events[0]["deaths"] == top_deaths


def test_haversine():
    assert oa._haversine_km(33.0, 75.0, 33.0, 75.0) == 0.0
    d = oa._haversine_km(33.0, 75.0, 34.0, 75.0)     # 1 deg latitude ~ 111.2 km
    assert 110.0 < d < 112.5, d


def _run_loader(slug: str):
    """Run load_historical_events as the given site (monkeypatching the module's
    per-AOI globals, restored afterwards) against that site's real footprint."""
    saved = (oa.SLUG, oa.ALERTS_DIR)
    sfx = "" if slug == "ramban" else f"_{slug}"
    try:
        oa.SLUG = slug
        oa.ALERTS_DIR = PROJECT_ROOT / "data" / f"alerts{sfx}"
        fp = oa.ALERTS_DIR / "mosaic_asc" / "alerts_operational.json"
        hist = oa.load_historical_events(fp)
        assert hist is not None, f"{slug}: loader returned None"
        return hist
    finally:
        oa.SLUG, oa.ALERTS_DIR = saved


def test_current_alert_annotation_both_sites():
    for slug in SLUGS:
        hist = _run_loader(slug)
        for e in hist["events"]:
            assert e.get("nearest_zone") is not None, (slug, e["name"])
            km = e["nearest_zone_km"]
            assert isinstance(km, float) and 0 <= km < 100, (slug, e["name"], km)
            z = e["nearest_zone"]
            assert z.get("severity") in ("CRITICAL", "HIGH"), (slug, e["name"], z)


def test_hist_panel_html():
    hist = _run_loader("vaishnodevi")
    html = oa._hist_panel(hist, "WATCH", "2026-07-11")
    assert "google.com/maps" in html                       # clickable location links
    assert "Past landslide events" in html
    assert html.count(">pending review</span>") == sum(       # the per-row badge marker
        1 for e in hist["events"] if e.get("review_needed"))
    for grade in ("VERIFIED", "HIGH", "MEDIUM", "LOW"):
        assert f">{grade}</span>" in html, grade           # confidence badges
    assert "alarm <b>WATCH</b> as of 2026-07-11" in html   # current gate state shown
    # Every event row landed, with its today-standing cell.
    for e in hist["events"]:
        assert e["name"] in html
    assert "to nearest hazard zone" in html or "outside today's mapped footprint" in html


def test_today_cell_inside_and_outside_footprint():
    z = {"severity": "HIGH", "m_star": "0.22", "fs_0p40": "0.947",
         "creep_mmyr": "-39.2", "confidence": "0.816"}
    near = oa._hist_today_cell({"nearest_zone": z, "nearest_zone_km": 0.5})
    assert "500 m" in near and "m* 0.22" in near and "creep -39.2 mm/yr" in near
    far = oa._hist_today_cell({"nearest_zone": z, "nearest_zone_km": 5.21})
    assert "outside today's mapped footprint" in far and "5.2 km" in far
    assert "no zone data" in oa._hist_today_cell({"nearest_zone": None, "nearest_zone_km": None})


def _minimal_dashboard_args(tmp: Path):
    fig = tmp / "fig.png"
    fig.write_bytes(_TINY_PNG)
    r = {"season": {"start": "2026-06-01", "end": "2026-06-02", "days": 2},
         "level_counts": {"DORMANT": 1, "WATCH": 1, "ALERT": 0},
         "alert_pct_season": 0.0, "raw_regional_trigger_days": 1,
         "selectivity_gain_raw_to_alert": "1 -> 0 days (1.0x fewer)",
         "events_caught_by_alarm": "0/0", "events_caught_by_alert": "0/0",
         "per_event": [], "footprint_zones": 3}
    dates = [date(2026, 6, 1), date(2026, 6, 2)]
    E = np.array([0.5, 1.2])
    levels = ["DORMANT", "WATCH"]
    tier = {"scenario": "operational", "m": 0.5, "n_zones": 3, "n_crit": 1, "n_multi": 1,
            "auc": None, "recall": None, "spec": None, "lift250": None,
            "core_zones": None, "core_auc": None, "core_lift": None}
    return r, dates, E, levels, fig, tier


def test_dashboard_page_with_and_without_hist():
    hist = _run_loader("vaishnodevi")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        r, dates, E, levels, fig, tier = _minimal_dashboard_args(tmp)
        out = tmp / "operational_alarm_dashboard_test.html"
        oa.write_dashboard(out, r, dates, E, levels, 1, fig, tier, hist=hist)
        page = out.read_text(encoding="utf-8")
        # New tab present, existing structure intact.
        for anchor in ("btn-hist", "tab-hist", "btn-dash", "tab-dash", "btn-guide",
                       "tab-guide", "ALARM: WATCH", "showTab"):
            assert anchor in page, anchor
        assert "Past events" in page
        # Every real link opens in a new tab (the dashboard is never navigated away).
        assert '<base target="_blank">' in page
        # Graceful degradation: no record -> no Past-events button, page still whole.
        out2 = tmp / "operational_alarm_dashboard_test2.html"
        oa.write_dashboard(out2, r, dates, E, levels, 1, fig, tier, hist=None)
        page2 = out2.read_text(encoding="utf-8")
        assert "btn-hist" not in page2 and "tab-hist" not in page2
        for anchor in ("btn-dash", "btn-guide", "ALARM: WATCH"):
            assert anchor in page2, anchor


def test_loader_footprint_fallback_without_per_zone_csv():
    """When per_zone_vulnerability.csv is absent (a site where per_zone_gate.py has not run),
    the annotation must fall back to the operational-footprint centroids (severity/FS/creep,
    no m*) instead of failing or silently skipping — and the today-cell must still render."""
    saved = (oa.SLUG, oa.ALERTS_DIR)
    real_fp = (PROJECT_ROOT / "data" / "alerts_vaishnodevi" / "mosaic_asc"
               / "alerts_operational.json")
    with tempfile.TemporaryDirectory() as td:
        try:
            oa.SLUG = "vaishnodevi"
            oa.ALERTS_DIR = Path(td)          # empty: no per_zone_vulnerability.csv here
            hist = oa.load_historical_events(real_fp)
        finally:
            oa.SLUG, oa.ALERTS_DIR = saved
    assert hist is not None
    for e in hist["events"]:
        z = e.get("nearest_zone")
        assert z is not None and z["m_star"] is None, e["name"]
        assert z.get("severity") in ("CRITICAL", "HIGH"), e["name"]
        assert isinstance(e["nearest_zone_km"], float)
        cell = oa._hist_today_cell(e)
        assert "<td>" in cell and "no zone data" not in cell, e["name"]


def test_loader_absent_record_returns_none():
    saved = oa.SLUG
    try:
        oa.SLUG = "no_such_site"
        assert oa.load_historical_events(Path("nonexistent.json")) is None
    finally:
        oa.SLUG = saved


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

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
    and degrades gracefully (no Past-events button) when the record is absent;
  • SECURITY: no field of the (untrusted, news/LLM-sourced) events record can
    inject an element, an event handler, or a non-http(s) URL into the rendered
    dashboard — asserted by PARSING the output, with a negative control proving
    the auditor detects the vulnerability it guards against.

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
    """Every event must get an HONEST current standing at every site — which means covering BOTH
    live states (§79). A site whose footprint holds zones must annotate each event with a real
    distance + severity; a site whose footprint is EMPTY (§78 — the noise-limited ALERT tier
    flags nothing at VD today) must say so explicitly, and must never invent a zone or imply the
    site is unprocessed."""
    for slug in SLUGS:
        hist = _run_loader(slug)
        for e in hist["events"]:
            z, km = e.get("nearest_zone"), e.get("nearest_zone_km")
            if z is None:
                assert e.get("mapped_but_empty") is True, (
                    slug, e["name"], "no zone AND not flagged as a mapped-but-empty footprint "
                                     "— the annotation would be silently missing")
                cell = oa._hist_today_cell(e)
                assert "mapped footprint is empty" in cell, (slug, e["name"], cell)
                assert "yet" not in cell, (slug, "must not imply the site is unprocessed")
                continue
            assert isinstance(km, float) and 0 <= km < 100, (slug, e["name"], km)
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
    # One of the three honest standings must appear: a real distance, outside-the-footprint, or
    # (§79) the mapped-but-empty case where the product currently flags nothing anywhere.
    assert ("to nearest hazard zone" in html
            or "outside today's mapped footprint" in html
            or "mapped footprint is empty" in html)


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
        # Staleness guard: banner element carries the as-of date; the view-time script with
        # both escalation thresholds is embedded (behavior itself is browser-verified).
        assert 'id="staleness" data-asof="2026-06-02"' in page
        for marker in ("TREAT THE ALARM STATE AS UNKNOWN", "days > 14", "days > 8"):
            assert marker in page, marker
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
    no m*) instead of failing or silently skipping — and the today-cell must still render.

    The footprint is a SYNTHETIC fixture, deliberately: this asserts the fallback LOGIC, and
    must not depend on the live map being non-empty. (§78 — it used to read the real
    alerts_operational.json and started failing when a radar rebuild legitimately took VD's
    ALERT footprint to 0 zones. That data-state question is now its own test, below.)"""
    saved = (oa.SLUG, oa.ALERTS_DIR)
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "alerts_operational.json"
        fp.write_text(json.dumps({"zones": [
            {"centroid_lonlat": [74.9490, 33.0320], "severity": "CRITICAL",
             "min_fs_any_look": 0.88},
            {"centroid_lonlat": [74.9310, 32.9905], "severity": "HIGH",
             "min_fs_any_look": 0.96},
        ]}), encoding="utf-8")
        try:
            oa.SLUG = "vaishnodevi"
            oa.ALERTS_DIR = Path(td)          # empty: no per_zone_vulnerability.csv here
            hist = oa.load_historical_events(fp)
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


def test_score_is_not_advertised_for_a_footprint_it_never_scored():
    """§78: a back-test score describes the footprint it was computed on. When a radar rebuild
    moves the map, the old AUC must render as NOT MEASURED — never as this map's validation.

    This is the guard for the real failure: VD's ALERT tier went 14 zones -> 0 in a cadence
    rebuild while the page still advertised 'AUC 0.757 · the map that beats chance' beside an
    EMPTY footprint. Carries its own negative control."""
    base = {"scenario": "operational", "m": 0.40, "n_crit": 0, "n_multi": 0,
            "auc": 0.757, "recall": 0.70, "lift250": None, "core_zones": None,
            "core_auc": None, "core_lift": None}

    # Footprint moved (scored 14, now 0) -> the score must be withdrawn, not displayed.
    moved = oa._tier_card({**base, "n_zones": 0, "scored_zones": 14}, "ALERT")
    assert "Not measured for this footprint" in moved
    assert "14-zone" in moved                      # says what WAS scored
    assert "beats chance" not in moved             # and drops the validation claim
    assert "0.757" not in moved.split("Not measured")[0]

    # NEGATIVE CONTROL: unchanged footprint -> the score is still legitimately advertised.
    same = oa._tier_card({**base, "n_zones": 14, "scored_zones": 14}, "ALERT")
    assert "Not measured for this footprint" not in same
    assert "beats chance" in same and "0.757" in same


def test_empty_footprint_does_not_take_down_the_daily_arm():
    """§79: an EMPTY operational footprint is a legitimate state (§78 — the ALERT tier is
    noise-limited and currently flags nothing at VD). `per_zone_gate.py` used to raise
    SystemExit, and `live_alarm.py` calls it with check=True — so a degraded WHERE map stopped
    the validated WHEN arm (rainfall calendar + dashboard) from updating at all.

    The gate must now publish the EMPTY state, stamped with the SAME as-of the rest of the
    cycle uses, and exit 0 — otherwise a stale ranking is left behind claiming zones that no
    longer exist (which is what `test_alarm_artifacts_cross_consistent` catches)."""
    import tempfile

    import per_zone_gate as pzg

    src = Path(pzg.__file__).read_text(encoding="utf-8")
    assert "raise SystemExit(\"No operational zones found" not in src, (
        "the empty footprint must not be a hard failure — it takes the daily arm down with it")

    # HERMETIC: ALERTS_DIR is redirected to a temp dir. per_zone_gate writes its artifacts
    # there, so this test can never touch the real data/alerts_<slug>/ tree — running it
    # against the live directory once overwrote the site's per-zone files with this synthetic
    # date and tripped the cross-consistency guard.
    saved_dir, saved_argv = pzg.ALERTS_DIR, sys.argv
    with tempfile.TemporaryDirectory() as td:
        out, wet = Path(td) / "alerts", Path(td) / "wet.csv"
        wet.write_text("date,rain_mm,snowmelt_mm,water_mm,api_mm,wetness_0_1,freeze_thaw\n"
                       "2026-07-01,0,0,0,0.0,0.100,0\n"
                       "2026-07-02,5,0,5,5.0,0.200,0\n"
                       "2026-07-03,9,0,9,9.0,0.300,0\n", encoding="utf-8")
        try:
            pzg.ALERTS_DIR = out
            sys.argv = ["per_zone_gate.py", "--csv", str(wet),
                        "--stacks", "NO_SUCH_STACK", "--as-of", "2026-07-03"]
            rc = pzg.main()
        finally:
            pzg.ALERTS_DIR, sys.argv = saved_dir, saved_argv

        assert rc == 0, f"empty footprint must exit 0 (not break the chain), got {rc}"
        rep = json.loads((out / "per_zone_vulnerability.json").read_text(encoding="utf-8"))
        assert rep["n_operational_zones"] == 0 and rep["as_of"] == "2026-07-03", rep
        assert "reason" in rep, "the empty state must say WHY, not just be empty"
        # The ranking table is present but empty — header only, no stale rows left behind.
        rows = (out / "per_zone_vulnerability.csv").read_text(encoding="utf-8").strip().split("\n")
        assert len(rows) == 1 and rows[0].startswith("stack,"), rows[:3]
    assert pzg.ALERTS_DIR == saved_dir, "the real alerts dir must be restored"


def test_chance_claim_is_derived_from_the_auc_not_asserted():
    """§79: the cards used to hard-code "beats chance" (ALERT) and "≈chance overall" (WATCH).
    Re-scoring VD's rebuilt map returned AUC 0.326 with 0/47 documented locations detected —
    random points landed CLOSER to the flagged zones than real landslides — so those phrases
    were false on a page read as a warning. The verdict must follow the number."""
    assert oa._chance_verdict(0.757) == "beats chance"
    assert oa._chance_verdict(0.50) == "≈chance"
    assert "BELOW chance" in oa._chance_verdict(0.326)
    assert oa._chance_verdict(None) == "not scored"

    base = {"scenario": "watch", "m": 0.75, "n_crit": 0, "n_multi": 0, "recall": 0.0,
            "lift250": None, "core_zones": None, "core_auc": None, "core_lift": None}
    bad = oa._tier_card({**base, "auc": 0.326, "n_zones": 30, "scored_zones": 30}, "WATCH")
    assert "BELOW chance" in bad
    assert "≈chance" not in bad and "beats chance" not in bad

    # An ALERT tier that no longer beats chance must also lose the headline claim.
    weak = oa._tier_card({**base, "scenario": "operational", "auc": 0.326,
                          "n_zones": 30, "scored_zones": 30}, "ALERT")
    assert "the map that beats chance" not in weak


def test_stale_validation_overlay_cannot_mask_a_fresher_worse_score(tmp_path=None):
    """§79: `validation_stats_<tier>_<slug>.json` is a SECOND score channel that goes stale
    independently of the back-test report. It records the footprint it measured (`n_zones`), so
    it may override only while that is still the live map — otherwise the page kept announcing
    "AUC 0.586 · beats chance" from a 102-zone overlay after the live 30-zone map had been
    re-scored at 0.326."""
    import tempfile

    saved = (oa.INV_DIR, oa._SFX)
    with tempfile.TemporaryDirectory() as td:
        inv = Path(td)
        try:
            oa.INV_DIR, oa._SFX = inv, "_testsite"
            fp = inv / "alerts_watch.json"
            fp.write_text(json.dumps({"scenario": "watch",
                                      "zones": [{"severity": "HIGH"} for _ in range(30)]}),
                          encoding="utf-8")
            (inv / "backtest_watch_testsite_report.json").write_text(
                json.dumps({"n_flagged_zones": 30,
                            "scored": {"auc": 0.326, "at_buffer_km": {"tpr": 0.0}}}),
                encoding="utf-8")
            overlay = {"n_zones": 102,
                       "model": {"auc": 0.586, "recall_at_buffer": 0.957,
                                 "auc_ci95": [0.52, 0.65], "p_perm_beats_chance": 0.02}}
            ov_path = inv / "validation_stats_watch_testsite.json"

            # STALE overlay (102 != 30 live zones) -> ignored, fresh back-test wins.
            ov_path.write_text(json.dumps(overlay), encoding="utf-8")
            tier = oa.load_tier(fp)
            assert tier["n_zones"] == 30, tier["n_zones"]
            assert tier["auc"] == 0.326, tier["auc"]

            # NEGATIVE CONTROL: overlay that matches the live map DOES override.
            ov_path.write_text(json.dumps({**overlay, "n_zones": 30}), encoding="utf-8")
            assert oa.load_tier(fp)["auc"] == 0.586
        finally:
            oa.INV_DIR, oa._SFX = saved


def test_loader_absent_record_returns_none():
    saved = oa.SLUG
    try:
        oa.SLUG = "no_such_site"
        assert oa.load_historical_events(Path("nonexistent.json")) is None
    finally:
        oa.SLUG = saved


# ------------------------------------------------------------------------------
# SECURITY — stored XSS via the (untrusted) historical-events record
# ------------------------------------------------------------------------------
# The events record is transcribed from news articles and LLM-synthesis leads, which CLAUDE.md
# and §36-§38 treat as UNTRUSTED. control_panel.py serves the generated dashboards from
# /file/... at the SAME ORIGIN as its control API, so an injected script would run with access
# to POST /run and to every file under data/. Substring checks are NOT enough here: escaped
# text legitimately still CONTAINS "onmouseover=" as inert characters. So parse the output and
# assert on the resulting DOM.

_XSS_EVENT = {
    "name": "X</b><img src=x onerror=alert(1)>",
    "date": "2026-01-01", "lat": 33.0, "lon": 75.0,
    "deaths": 0, "injured": 0,
    "damage": "<script>alert(4)</script>",
    "confidence": "HIGH", "confidence_reason": '" onload="alert(5)',
    "review_needed": False, "damage_score": 1, "confidence_score": 1,
    "sources": [{"label": '" onmouseover="alert(2)', "url": "javascript:alert(3)"},
                {"label": "legit", "url": "https://example.org/a?b=1&c=2"},
                {"label": "scheme-relative", "url": "//evil.example/x"},
                {"label": "data uri", "url": "data:text/html,<script>alert(9)</script>"}],
}


def _audit_html(markup: str) -> list:
    """Parse `markup`; return every injected element, on* handler and non-http(s) URL."""
    from html.parser import HTMLParser

    findings = []

    class Audit(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag in ("script", "iframe", "object", "embed", "svg"):
                findings.append(("element", tag))
            for k, v in attrs:
                if k.lower().startswith("on"):
                    findings.append(("handler", tag, k, v))
                if k.lower() in ("href", "src") and v:
                    head = v.split("?")[0]
                    scheme = head.split(":", 1)[0].lower() if ":" in head else ""
                    if scheme and scheme not in ("http", "https"):
                        findings.append(("scheme", tag, k, v[:40]))
                    if v.startswith("//"):
                        findings.append(("scheme-relative", tag, k, v[:40]))

    Audit().feed(markup)
    return findings


def test_hist_panel_is_not_injectable():
    hist = {"events": [dict(_XSS_EVENT)], "site": "t",
            "updated": "<img src=x onerror=alert(6)>", "note": "<b>note</b>"}
    html = oa._hist_panel(hist, "WATCH", date(2026, 7, 25))
    assert _audit_html(html) == [], _audit_html(html)
    # The payload must still be VISIBLE as text (escaped, not silently dropped) — a fix that
    # deletes the content would also pass an injection check while destroying the record.
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    # A legitimate https source keeps its link, with the query ampersand escaped.
    assert 'href="https://example.org/a?b=1&amp;c=2"' in html
    # javascript:, data: and scheme-relative sources are cited as plain text, never linked.
    assert html.count("<a href=") == 1 + html.count('href="https://www.google.com/maps')


def test_audit_helper_actually_detects_the_vulnerability():
    """NEGATIVE CONTROL. A guard that cannot fail is not a guard: disable the escaper and the
    same assertions must FAIL — proving the audit detects the bug it was written for."""
    original = oa._esc
    try:
        oa._esc = lambda v: "" if v is None else str(v)      # the pre-fix behaviour
        hist = {"events": [dict(_XSS_EVENT)], "site": "t", "updated": "u", "note": "n"}
        findings = _audit_html(oa._hist_panel(hist, "WATCH", date(2026, 7, 25)))
        kinds = {f[0] for f in findings}
        assert "element" in kinds, f"auditor missed the injected <script>/<img>: {findings}"
        assert "handler" in kinds, f"auditor missed the on* handler: {findings}"
    finally:
        oa._esc = original
    # …and with the escaper restored the very same input is clean again.
    hist = {"events": [dict(_XSS_EVENT)], "site": "t", "updated": "u", "note": "n"}
    assert _audit_html(oa._hist_panel(hist, "WATCH", date(2026, 7, 25))) == []


def test_safe_url_allow_list():
    assert oa._safe_url("https://a.example/x") == "https://a.example/x"
    assert oa._safe_url("http://a.example/x") == "http://a.example/x"
    for bad in ("javascript:alert(1)", "JavaScript:alert(1)", "data:text/html,<script>",
                "vbscript:msgbox", "//evil.example/x", "  javascript:alert(1)", "", None):
        assert oa._safe_url(bad) == "", bad
    # Quotes in an otherwise-valid URL are escaped, never allowed to close the attribute.
    assert '"' not in oa._safe_url('https://a.example/"onmouseover="alert(1)')


def test_full_dashboard_page_is_not_injectable():
    """End-to-end: the whole rendered page, not just the panel."""
    hist = {"events": [dict(_XSS_EVENT)], "site": "t",
            "updated": "<img src=x onerror=alert(7)>", "note": "<b>n</b>"}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        r, dates, E, levels, fig, tier = _minimal_dashboard_args(tmp)
        r["per_event"] = [{"name": "<script>alert(8)</script>", "date": "2026-01-01",
                           "E_on_day": 1.0, "alert_within_window": True,
                           "alarm_within_window": True}]
        out = tmp / "dash.html"
        oa.write_dashboard(out, r, dates, E, levels, 1, fig, tier, hist=hist,
                           radar={"through": "2026-05-06",
                                  "newer_at_asf": '"><img src=x onerror=alert(9)>',
                                  "new_scenes": 3, "new_units": "S1A/S1D"})
        page = out.read_text(encoding="utf-8")

    # The page legitimately contains FIRST-PARTY constructs written by our own code: its
    # <script> blocks, the tab buttons' onclick="showTab(...)", and the base64 figure. Allow
    # exactly those shapes and nothing else — so any NEW inline handler or URL scheme, whether
    # injected by data or added carelessly by us later, fails this test.
    import re
    ok_onclick = re.compile(r"^showTab\('[a-z]+'\)(;return false)?$")
    bad = []
    for f in _audit_html(page):
        if f[0] == "element" and f[1] == "script":
            continue
        if f[0] == "handler" and f[2] == "onclick" and ok_onclick.match(f[3] or ""):
            continue
        if f[0] == "scheme" and f[2] == "src" and (f[3] or "").startswith("data:image/png;base64"):
            continue
        bad.append(f)
    assert bad == [], bad

    # The injected payloads survive only as escaped text.
    assert "<script>alert(8)</script>" not in page
    assert "&lt;script&gt;alert(8)&lt;/script&gt;" in page
    assert 'onerror=alert(9)' not in page.replace("&quot;", '"').split("data-new=")[0]


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

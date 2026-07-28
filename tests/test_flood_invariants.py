"""
test_flood_invariants.py — the ADDITIVE contract for the flood arm
(docs/references/FLOOD_EXPANSION_PLAN_2026-07-28.md §7.2, cases R1-R8).

This suite exists to prove the claim "the flood arm changes nothing that already works".
It is deliberately written and run BEFORE any flood code touches disk: R1 snapshots every
protected artifact into data/flood/_baseline_freeze.json on its first run, and every run
after that re-hashes the same set and fails on any drift.

What is asserted:
  R1  every protected artifact is byte-identical to the frozen baseline;
  R2  a config with NO `flood:` block disables the arm — both entry points exit 0 and
      write nothing (the llof_routing / kappa "default reproduces the old world" pattern);
  R3  the dashboard built WITHOUT flood artifacts contains no flood card (DOM-parsed);
  R4  the dashboard built WITH a flood summary renders the card and leaves every other
      section byte-identical to the R3 render;
  R5  build_3d_dashboard.py carries no flood code yet (F0/F1 do not touch it) — this
      upgrades to a real with/without trace-parity test when F2 adds the layer;
  R6  the channel criterion IS flow_routing_probe's (function identity, not a copy) and
      the config default equals the probe's validated threshold;
  R8  a flood card fed hostile catchment metadata is escaped, with a NEGATIVE CONTROL
      that disables the escaper and requires this test to fail.
(R7 — "the full battery stays green" — is session bookkeeping, not a test.)

Hermetic: no network, no GEE, no rasterio. Run from project root:
    python tests/test_flood_invariants.py
OR under pytest:
    python -m pytest tests/test_flood_invariants.py -v
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

DATA = PROJECT_ROOT / "data"
FLOOD_DIR = DATA / "flood"
FREEZE = FLOOD_DIR / "_baseline_freeze.json"

# The protected set: the validated products the flood arm must never perturb.
# Globs are relative to data/. Kept explicit (not "everything") so the manifest stays
# meaningful — a sweep over all of data/ would drift on every unrelated run.
PROTECTED_GLOBS = [
    "alerts*/**/alerts_operational.json",      # the validated ALERT union + per-stack
    "alerts*/**/alerts_watch.json",            # the higher-recall WATCH tier (§23)
    "hazard*/**/*.tif",                        # hazard rasters (§67 untouched-check target)
    "velocity*/**/*.tif",                      # velocity rasters
    "rainfall/operational_alarm_report*.json",  # the daily arm, all four AOI-seasons
    "rainfall/operational_alarm_calendar*.csv",
    "inventory/backtest*report*.json",         # the scored back-tests (AUC/recall)
    "inventory/temporal_skill_table.csv",      # the generated Tier-3c skill table
]


# ------------------------------------------------------------------------------
# R1 — baseline freeze
# ------------------------------------------------------------------------------
def _protected_files() -> list[Path]:
    seen: set[Path] = set()
    for g in PROTECTED_GLOBS:
        seen.update(p for p in DATA.glob(g) if p.is_file())
    return sorted(seen)


def _digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest() -> dict:
    files = {}
    for p in _protected_files():
        st = p.stat()
        files[p.relative_to(PROJECT_ROOT).as_posix()] = {
            "sha256": _digest(p), "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }
    return {"created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "note": ("Baseline freeze for the flood expansion (plan §7.2 R1). CONTENT (sha256) "
                     "is the assertion; mtime is recorded for forensics only — a touched-but-"
                     "identical file is reported, not failed."),
            "globs": PROTECTED_GLOBS, "n_files": len(files), "files": files}


def test_R1_protected_artifacts_are_byte_identical():
    """First run SNAPSHOTS the validated products; every later run must reproduce them exactly."""
    FLOOD_DIR.mkdir(parents=True, exist_ok=True)
    current = build_manifest()
    assert current["n_files"] > 0, (
        "the protected set is EMPTY — the freeze would assert nothing. Run from a checkout "
        "that has data/ populated (the globs are in PROTECTED_GLOBS).")
    if not FREEZE.exists():
        FREEZE.write_text(json.dumps(current, indent=2), encoding="utf-8")
        print(f"      [R1] baseline CREATED: {current['n_files']} protected artifacts frozen")
        return
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))["files"]
    now = current["files"]
    missing = sorted(set(frozen) - set(now))
    changed = sorted(k for k in set(frozen) & set(now)
                     if frozen[k]["sha256"] != now[k]["sha256"])
    assert not missing, f"protected artifact(s) DISAPPEARED: {missing[:5]}"
    assert not changed, (
        f"protected artifact(s) CHANGED — the flood arm is not additive: {changed[:5]}\n"
        f"        Restore from backup, find what wrote them, and only then re-freeze.\n"
        f"        TWO legitimate causes, and nothing else:\n"
        f"        (1) a `live_alarm.py` run refreshes the CURRENT season's daily-arm files\n"
        f"            (operational_alarm_report_<year>.*, calendars) on purpose;\n"
        f"        (2) a DELIBERATE, additive schema extension of a generated artifact — e.g.\n"
        f"            temporal_skill_table.csv gaining the flood columns (§72). Additive means\n"
        f"            PROVEN additive: same row count, no column removed, ZERO existing cells\n"
        f"            changed. Verify that column-by-column before you accept it.\n"
        f"        In either case: confirm NOTHING ELSE moved (this message lists everything\n"
        f"        that did), then delete data/flood/_baseline_freeze.json to re-freeze.\n"
        f"        Any other cause: restore from backup and find what wrote it FIRST.")
    touched = [k for k in set(frozen) & set(now) if frozen[k]["mtime"] != now[k]["mtime"]]
    if touched:
        print(f"      [R1] note: {len(touched)} file(s) re-written with IDENTICAL content")
    added = sorted(set(now) - set(frozen))
    if added:
        print(f"      [R1] note: {len(added)} new file(s) matched the globs (not a violation)")


# ------------------------------------------------------------------------------
# R2 — absent config block = feature fully off
# ------------------------------------------------------------------------------
_NO_FLOOD_YAML = """\
aoi_path: config/aoi/ramban_aoi.geojson
site_name: Freeze Test Site
job_name_prefix: FreezeTest
search_start: 2025-05-01
search_end: 2025-10-31
"""


def test_R2_absent_flood_block_disables_the_arm():
    import flood_domain as fd
    import flood_gate as fg
    from config import load_config
    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "noflood.yaml"
        cfg_path.write_text(_NO_FLOOD_YAML, encoding="utf-8")
        cfg = load_config(cfg_path)
        assert fd.load_flood_config(cfg) is None, "a config without `flood:` must disable the arm"
        # Both entry points must no-op cleanly (exit 0) and write nothing.
        for mod in (fd, fg):
            out_before = sorted(p.name for p in FLOOD_DIR.glob("*")) if FLOOD_DIR.exists() else []
            rc = mod.main(["--config", str(cfg_path)])
            assert rc == 0, f"{mod.__name__}.main must exit 0 when disabled, got {rc}"
            out_after = sorted(p.name for p in FLOOD_DIR.glob("*")) if FLOOD_DIR.exists() else []
            assert out_before == out_after, (
                f"{mod.__name__} wrote artifacts while DISABLED: "
                f"{set(out_after) - set(out_before)}")


def test_R2b_present_flood_block_enables_it_with_documented_defaults():
    """The registry files ship a `flood:` block; its parsed values must match the plan's
    defaults so an unedited site behaves exactly as documented."""
    import flood_domain as fd
    from config import load_config
    for slug in ("ramban", "vaishnodevi"):
        cfg = load_config(PROJECT_ROOT / "config" / f"{slug}.yaml")
        fc = fd.load_flood_config(cfg)
        assert fc is not None, f"{slug}: expected a flood: block in the registry file"
        assert fc.channel_upstream_km2 == 0.5, slug
        assert fc.channel_buffer_m == 120, slug
        assert fc.min_catchment_coverage_pct == 95, slug


# ------------------------------------------------------------------------------
# R3 / R4 — the dashboard degrades to exactly the old page without flood artifacts
# ------------------------------------------------------------------------------
_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c6360000002000100ffff03000006000557bfabd4"
    "0000000049454e44ae426082")


def _minimal_dashboard_args(tmp: Path):
    import numpy as np
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


def _flood_summary(name: str = "Catchment 1") -> dict:
    return {"slug": "ramban", "experimental": True, "aborted": False,
            "generated_utc": "2026-07-28 10:00", "durations_h": [0.5, 1, 3, 6],
            "threshold": "NW Himalaya (frequentist, 2007-2016) I=2.9993*D^-0.4152",
            "flood_watch_k": 1.0, "flood_alert_k": 2.4,
            "season": {"start": "2026-06-01", "end": "2026-06-02", "days": 2},
            "n_catchments": 1, "n_staged": 1, "n_aborted": 0,
            "latest": {"catchment": name, "zone": 1, "level": "FLOOD-WATCH", "E_f": 1.4,
                       "date": "2026-06-02", "provisional": False},
            "latest_date": "2026-06-02",
            "season_peak": {"catchment": name, "zone": 1, "level": "FLOOD-ALERT", "E_f": 8.1,
                            "date": "2026-06-01", "duration_h": 1.0, "burst_mm": 12.3,
                            "area_km2": 8.4, "tc_hours": 0.9, "imerg_pixels": 1},
            "alert_days_per_catchment": {name: 1},
            "level_counts": {"FLOOD-DORMANT": 0, "FLOOD-WATCH": 1, "FLOOD-ALERT": 0},
            "catchments": [{"catchment": name, "zone": 1, "level": "FLOOD-WATCH", "E_f": 1.4,
                            "area_km2": 8.4, "tc_hours": 0.9, "duration_h": 1.0,
                            "date": "2026-06-02", "imerg_pixels": 1}]}


def _render(tmp: Path, flood):
    import operational_alarm as oa
    r, dates, E, levels, fig, tier = _minimal_dashboard_args(tmp)
    out = tmp / f"dash_{'with' if flood else 'without'}.html"
    oa.write_dashboard(out, r, dates, E, levels, 1, fig, tier, flood=flood)
    return out.read_text(encoding="utf-8")


def test_R3_dashboard_without_flood_artifacts_has_no_flood_card():
    from html.parser import HTMLParser
    with tempfile.TemporaryDirectory() as td:
        page = _render(Path(td), None)
    # Parse, don't substring-match (§66 lesson): look for the card's real anchor in the DOM.
    class Find(HTMLParser):
        hit = False

        def handle_data(self, data):
            if "catchment flood" in data.lower():
                self.hit = True
    p = Find()
    p.feed(page)
    assert not p.hit, "a flood card rendered with NO flood artifacts present"
    assert "flood-card" not in page
    for anchor in ("btn-dash", "ALARM: WATCH", "showTab"):
        assert anchor in page, anchor


def test_R4_flood_card_is_purely_additive():
    import operational_alarm as oa
    summary = _flood_summary()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        without = _render(tmp, None)
        with_flood = _render(tmp, summary)
    assert "flood-card" in with_flood and "flood-card" not in without
    # The ONLY difference is the inserted card: deleting exactly the card's own markup must
    # restore the old page byte-for-byte. Anything else (a shifted section, a changed count,
    # a re-ordered block) fails here.
    card = oa._flood_card(summary)
    assert card in with_flood, "the rendered card is not verbatim in the page"
    assert with_flood.replace(card, "") == without, (
        "the flood card changed the surrounding page — it must be a pure insertion")


def test_R5_three_d_dashboard_is_untouched_at_F1():
    """F0/F1 add no 3-D layer (that is F2's sanctioned touch-point). Pin that here so the
    'we did not touch it' claim is machine-checked rather than asserted in prose."""
    src = (PROJECT_ROOT / "workflows" / "build_3d_dashboard.py").read_text(encoding="utf-8")
    for token in ("flood", "catchment"):
        assert token not in src.lower(), (
            f"build_3d_dashboard.py now mentions {token!r} — if F2 has started, replace this "
            f"test with the real with/without trace-parity check from plan §7.2 R5")


# ------------------------------------------------------------------------------
# R6 — the channel criterion is the VALIDATED one, shared not copied
# ------------------------------------------------------------------------------
def test_R9_live_alarm_hook_is_non_fatal_and_cannot_reorder_the_daily_arm():
    """The flood arm is wired into live_alarm.py's regen (§70). Two properties must hold, and
    both are cheap to assert on the source (running the chain needs CDS + GEE credentials):

      1. the call is inside a try/except, like the imerg and radar hooks either side of it —
         a flood/GEE failure must never break the validated daily alarm;
      2. it runs BEFORE operational_alarm.py, so the card it feeds is current, and it is not
         placed after the dashboard render where it could only ever be stale.
    """
    src = (PROJECT_ROOT / "workflows" / "live_alarm.py").read_text(encoding="utf-8")
    assert 'run("flood_gate.py"' in src, "the flood hook is missing from live_alarm.py"
    i_flood = src.index('run("flood_gate.py"')
    # The nearest `try:` above the call must be closer than the nearest `run(` above it,
    # i.e. the call is the first statement of its own try block.
    try_at = src.rfind("try:", 0, i_flood)
    assert try_at != -1 and src.count("run(", try_at, i_flood) == 0, (
        "the flood_gate call is not wrapped in its own try/except — a GEE outage would take "
        "the validated daily alarm down with it")
    except_at = src.index("except", i_flood)
    assert "SKIPPED" in src[i_flood:except_at + 300], (
        "the flood hook's failure path must say it was skipped, not fail silently")
    assert i_flood < src.index('run("operational_alarm.py"'), (
        "flood_gate must run BEFORE the dashboard render, or its card is always a run behind")


def test_R6_channel_criterion_is_the_shared_validated_function():
    import flood_domain as fd
    import flow_routing_probe as frp
    assert fd.routed_llof_flag is frp.routed_llof_flag, (
        "flood_domain must IMPORT the probe's criterion, never re-implement it")
    assert fd.d8_accumulation is frp.d8_accumulation
    assert fd.DEFAULT_CHANNEL_UPSTREAM_KM2 == frp.UPSTREAM_KM2, (
        "the default channel threshold must equal the validated LLOF threshold (§60 4c)")


# ------------------------------------------------------------------------------
# R8 — the new card cannot be an injection vector (+ negative control)
# ------------------------------------------------------------------------------
def _audit_html(markup: str) -> list:
    """Return every <script> body and every on*= handler the parser actually sees."""
    from html.parser import HTMLParser

    class Audit(HTMLParser):
        def __init__(self):
            super().__init__()
            self.findings = []
            self._in_script = False

        def handle_starttag(self, tag, attrs):
            if tag == "script":
                self._in_script = True
            for k, v in attrs:
                if k.lower().startswith("on"):
                    self.findings.append(f"handler {k}={v}")
                if k.lower() in ("href", "src") and (v or "").lower().startswith("javascript:"):
                    self.findings.append(f"js-url {k}={v}")

        def handle_endtag(self, tag):
            if tag == "script":
                self._in_script = False

        def handle_data(self, data):
            if self._in_script and "INJECTED" in data:
                self.findings.append("script body: " + data.strip()[:60])
    a = Audit()
    a.feed(markup)
    return a.findings


_PAYLOADS = ['<script>alert("INJECTED")</script>',
             '" onmouseover="alert(\'INJECTED\')',
             "<img src=x onerror=alert('INJECTED')>"]


def _third_party(findings: list) -> list:
    """Drop the page's own FIRST-PARTY constructs (the tab buttons' onclick="showTab('x')"),
    exactly as tests/test_historical_events.py does. Anything else — including a NEW inline
    handler we add carelessly later — still fails."""
    import re
    ok = re.compile(r"^handler onclick=showTab\('[a-z]+'\)(;return false)?$")
    return [f for f in findings if not ok.match(f)]


def test_R8_flood_card_is_not_injectable():
    import operational_alarm as oa
    for payload in _PAYLOADS:
        summary = _flood_summary(name=payload)
        findings = _audit_html(oa._flood_card(summary))
        assert not findings, f"payload {payload!r} survived into the card DOM: {findings}"
        with tempfile.TemporaryDirectory() as td:
            page = _render(Path(td), summary)
        leaked = _third_party(_audit_html(page))
        assert not leaked, f"payload {payload!r} survived into the full page: {leaked}"


def test_R8b_audit_helper_actually_detects_the_vulnerability():
    """NEGATIVE CONTROL. A guard that cannot fail is not a guard: disable the escaper and
    the audit above MUST start reporting findings."""
    import operational_alarm as oa
    original = oa._esc
    try:
        oa._esc = lambda v: "" if v is None else str(v)      # the pre-fix behaviour
        findings = _audit_html(oa._flood_card(_flood_summary(name=_PAYLOADS[0])))
    finally:
        oa._esc = original
    assert findings, ("the DOM audit did not detect an UNESCAPED payload — the R8 test is "
                      "vacuous and would pass against a vulnerable card")


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

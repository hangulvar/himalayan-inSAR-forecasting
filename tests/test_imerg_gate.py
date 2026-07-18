"""
test_imerg_gate.py — the sub-daily IMERG gate (imerg_gate.py) + its dashboard card
(operational_alarm.py). Hermetic: NO network / GEE — the daily-E math runs on synthetic
half-hourly series, the cache round-trips through a temp dir, and the card renders from a
hand-built summary dict.

What is asserted:
  • a known synthetic burst produces the expected exceedance E at the expected duration
    (30 mm/h for 1 h vs the nwhimalaya curve -> E ~= 10 at D=1 h, ALERT);
  • trailing windows CROSS midnight — an overnight burst is credited to the day it ends in,
    never split to zero;
  • quiet days grade DORMANT; a day with an incomplete half-hourly record is provisional;
  • the half-hourly cache appends without duplicating and round-trips exactly;
  • write_outputs emits the daily CSV + summary JSON with consistent level counts;
  • the dashboard card renders (level chip, freshness, provisional note, honest-limits
    footer) and the page includes/omits it with/without a summary;
  • the suffix rule matches live_alarm's (ramban grandfathered).

Run from project root (conda env active, or in the insar container):
    python -m pytest tests/test_imerg_gate.py -v
OR plain:
    python tests/test_imerg_gate.py
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import traceback
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import imerg_gate as ig  # noqa: E402
import operational_alarm as oa  # noqa: E402
from rainfall_id_threshold import THRESHOLDS, threshold_intensity  # noqa: E402

A, B = THRESHOLDS["nwhimalaya"]["a"], THRESHOLDS["nwhimalaya"]["b"]


def _series(day0: datetime, n_days: int, rate_at: dict[int, float]):
    """A half-hourly series of n_days*48 steps; rate_at maps step-index -> mm/h rate."""
    return [(day0 + timedelta(minutes=30 * i), rate_at.get(i, 0.0))
            for i in range(n_days * 48)]


def test_synthetic_burst_E_and_duration():
    # 30 mm/h for exactly 1 hour (2 half-hourly steps) on day 1, rest dry.
    day0 = datetime(2026, 6, 1)
    series = _series(day0, 2, {20: 30.0, 21: 30.0})
    days = ig.daily_subdaily_E(series, A, B)
    assert len(days) == 2
    d1, d2 = days
    thr_1h = float(threshold_intensity(__import__("numpy").array([1.0]), A, B)[0])
    expect_E = 30.0 / thr_1h                       # ~10.0
    assert abs(d1["max_E"] - round(expect_E, 2)) < 0.01, d1
    assert d1["duration_h"] == 1 and d1["level"] == "ALERT"
    assert d1["burst_mm"] == 30.0 and d1["total_mm"] == 30.0
    # Day 2 is bone dry BUT trailing 24 h windows still see day-1 rain — its E must be the
    # 24 h-window value, not zero, and must grade below day 1.
    assert 0 < d2["max_E"] < d1["max_E"]


def test_overnight_burst_credited_to_the_day_it_ends_in():
    # Burst spanning midnight: 23:30 (step 47) and 00:00 (step 48), 30 mm/h each.
    day0 = datetime(2026, 6, 1)
    series = _series(day0, 2, {47: 30.0, 48: 30.0})
    days = ig.daily_subdaily_E(series, A, B)
    d2 = days[1]
    # The 1 h window ending 00:00 on day 2 holds the WHOLE 30 mm burst.
    assert d2["burst_mm"] == 30.0 and d2["duration_h"] == 1, d2
    assert d2["level"] == "ALERT"


def test_quiet_and_provisional_days():
    day0 = datetime(2026, 6, 1)
    series = _series(day0, 1, {})                  # full quiet day
    series += [(day0 + timedelta(days=1, minutes=30 * i), 0.1) for i in range(10)]  # partial
    days = ig.daily_subdaily_E(series, A, B)
    assert days[0]["level"] == "DORMANT" and days[0]["provisional"] is False
    assert days[1]["provisional"] is True and days[1]["n_steps"] == 10


def test_cache_roundtrip_appends_without_duplicates():
    day0 = datetime(2026, 6, 1)
    first = _series(day0, 1, {3: 5.0})
    more = [(day0 + timedelta(days=1, minutes=30 * i), 1.0) for i in range(4)]
    with tempfile.TemporaryDirectory() as td:
        cache = Path(td) / "hh.csv"
        ig.append_series(cache, first)
        ig.append_series(cache, more)
        back = ig.read_series(cache)
    assert len(back) == len(first) + len(more)
    assert back[0][0] == first[0][0] and back[-1][0] == more[-1][0]
    assert abs(back[3][1] - 5.0) < 1e-9


def test_write_outputs_schema_and_counts(tmp_path=None):
    day0 = datetime(2026, 6, 1)
    series = _series(day0, 3, {20: 30.0, 21: 30.0, 100: 3.0})   # 1 ALERT day, rest lower
    days = ig.daily_subdaily_E(series, A, B)
    saved = ig.RAIN_DIR
    with tempfile.TemporaryDirectory() as td:
        try:
            ig.RAIN_DIR = Path(td)
            ig.write_outputs(days, "_test", "nwhimalaya", A, B)
            rows = list(csv.DictReader((Path(td) / f"{ig.SLUG}_imerg_daily_E_test.csv")
                                       .open(encoding="utf-8")))
            summary = json.loads((Path(td) / "imerg_gate_summary_test.json")
                                 .read_text(encoding="utf-8"))
        finally:
            ig.RAIN_DIR = saved
    assert len(rows) == len(days) == summary["season"]["days"]
    assert sum(summary["level_counts"].values()) == len(days)
    assert summary["level_counts"]["ALERT"] >= 1
    assert summary["top_burst_day"]["date"] == days[0]["date"]  # the 30mm burst day
    assert summary["latest"]["date"] == days[-1]["date"]
    assert summary["threshold_id"] == "nwhimalaya"


def test_suffix_rule_matches_live_alarm():
    saved = ig.SLUG
    try:
        ig.SLUG = "ramban"
        assert ig.season_suffix(2026) == "_2026"
        ig.SLUG = "vaishnodevi"
        assert ig.season_suffix(2026) == "_vaishnodevi_2026"
    finally:
        ig.SLUG = saved


def _summary_fixture():
    return {"slug": "x", "threshold_id": "nwhimalaya",
            "season": {"start": "2026-04-01", "end": "2026-07-17", "days": 108},
            "level_counts": {"DORMANT": 80, "WATCH": 18, "ALERT": 10},
            "latest": {"date": "2026-07-17", "max_E": 3.43, "level": "ALERT",
                       "provisional": True, "duration_h": 3, "burst_mm": 19.5},
            "top_burst_day": {"date": "2026-07-01", "max_E": 6.4, "duration_h": 3,
                              "burst_mm": 36.5}}


def test_imerg_card_renders():
    html = oa._imerg_card(_summary_fixture(), "2026-07-12")
    assert "sub-daily burst check" in html and "experimental" in html
    assert "E = 3.43" in html and ">ALERT</span>" in html
    assert "5 day(s) fresher" in html                      # 07-17 vs the 07-12 as-of
    assert "provisional" in html
    assert "not yet" in html and "back-tested" in html     # honest-limits footer
    assert "36.5 mm in 3 h" in html


def test_dashboard_includes_and_omits_card():
    import base64
    import numpy as np
    from datetime import date as _date
    tiny = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
    r = {"season": {"start": "2026-06-01", "end": "2026-06-02", "days": 2},
         "level_counts": {"DORMANT": 1, "WATCH": 1, "ALERT": 0},
         "alert_pct_season": 0.0, "raw_regional_trigger_days": 1,
         "selectivity_gain_raw_to_alert": "1 -> 0 days (1.0x fewer)",
         "events_caught_by_alarm": "0/0", "events_caught_by_alert": "0/0",
         "per_event": [], "footprint_zones": 3}
    tier = {"scenario": "operational", "m": 0.5, "n_zones": 3, "n_crit": 1, "n_multi": 1,
            "auc": None, "recall": None, "spec": None, "lift250": None,
            "core_zones": None, "core_auc": None, "core_lift": None}
    dates = [_date(2026, 6, 1), _date(2026, 6, 2)]
    with tempfile.TemporaryDirectory() as td:
        fig = Path(td) / "f.png"
        fig.write_bytes(tiny)
        out = Path(td) / "operational_alarm_dashboard_t.html"
        oa.write_dashboard(out, r, dates, __import__("numpy").array([0.5, 1.2]),
                           ["DORMANT", "WATCH"], 1, fig, tier, imerg=_summary_fixture())
        page = out.read_text(encoding="utf-8")
        assert "sub-daily burst check" in page
        out2 = Path(td) / "operational_alarm_dashboard_t2.html"
        oa.write_dashboard(out2, r, dates, np.array([0.5, 1.2]),
                           ["DORMANT", "WATCH"], 1, fig, tier, imerg=None)
        assert "sub-daily burst check" not in out2.read_text(encoding="utf-8")


def test_load_imerg_summary_absent_and_corrupt():
    saved = oa.RAIN_DIR
    try:
        with tempfile.TemporaryDirectory() as td:
            oa.RAIN_DIR = Path(td)
            assert oa.load_imerg_summary("_nope") is None
            (Path(td) / "imerg_gate_summary_bad.json").write_text("{not json", encoding="utf-8")
            assert oa.load_imerg_summary("_bad") is None
    finally:
        oa.RAIN_DIR = saved


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

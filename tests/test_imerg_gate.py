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
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import imerg_calibration as ic  # noqa: E402
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


def test_calibrated_alert_threshold():
    """§64: burst-arm ALERT lowered to E>=2.4 (was 3.0 in §58); WATCH unchanged at 1.0.

    2.4 is chosen so the WEAKEST fatal event on record (Gangroo-Ramsu 22 Jul 2026, E=2.44)
    reaches ALERT on the day. Pin both sides of that boundary so a future re-tune is a
    deliberate act, not a silent drift.
    """
    assert ig.BURST_ALERT_K == 2.4 and ig.BURST_WATCH_K == 1.0
    assert ig.BURST_ALERT_K <= 2.44, "k must still reach the weakest fatal event (E=2.44)"
    day0 = datetime(2026, 6, 1)
    # E ~= 2.5 at D=1h (7.5 mm in 1 h): WATCH under §58's k=3, ALERT under §64's k=2.4.
    hot = ig.daily_subdaily_E(_series(day0, 1, {20: 7.5, 21: 7.5}), A, B)[0]
    assert 2.2 < hot["max_E"] < 2.8 and hot["level"] == "ALERT", hot
    # ~1.7x the line stays WATCH — the change lowers the bar, it does not remove it.
    mild = ig.daily_subdaily_E(_series(day0, 1, {20: 5.0, 21: 5.0}), A, B)[0]
    assert 1.0 < mild["max_E"] < 2.4 and mild["level"] == "WATCH", mild


def test_calibration_pure_functions():
    import imerg_calibration as ic
    rows = [{"max_E": "0.5"}, {"max_E": "1.2"}, {"max_E": "3.4"}, {"max_E": "9.0"}]
    s = ic.sweep(rows, ks=[1.0, 3.0, 8.0])
    assert s["1.0"]["days"] == 3 and s["3.0"]["days"] == 2 and s["8.0"]["days"] == 1
    assert s["1.0"]["pct"] == 75.0
    # window_total: 24h window ending 03:00 crosses midnight and sums rate*0.5.
    day0 = datetime(2025, 7, 20)
    series = [(day0 + timedelta(minutes=30 * i), 2.0) for i in range(96)]  # 2 mm/h for 2 days
    tot = ic.window_total(series, datetime(2025, 7, 21, 3, 0), 24.0)
    assert abs(tot - 48.0) < 0.01, tot                     # 24 h * 2 mm/h = 48 mm


def test_perzone_probe_pure_functions():
    import imerg_perzone_probe as pp
    rates = [0.0] * 20 + [30.0, 30.0] + [0.0] * 26        # the 1 h 30 mm burst
    e = pp.day_E(rates, A, B)
    assert abs(e - 10.0) < 0.1, e
    pts = [{"lon": 74.94, "lat": 33.01}, {"lon": 74.95, "lat": 33.02},
           {"lon": 75.01, "lat": 33.00}]
    assert pp.distinct_pixels(pts) == 2                    # 749/330 vs 750/330


def test_nisar_summarize():
    from datetime import date as _d
    import radar_watch as rw
    prods = [{"level": "GUNW", "acq": "2025-12-27"}, {"level": "GSLC", "acq": "2026-01-18"}]
    s = rw.summarize_nisar(prods, known_through=_d(2026, 1, 18))
    assert s["n_gunw"] == 1 and s["stream_started"] is False and s["newest_acq"] == "2026-01-18"
    s2 = rw.summarize_nisar(prods + [{"level": "GUNW", "acq": "2026-07-01"}],
                            known_through=_d(2026, 1, 18))
    assert s2["stream_started"] is True and s2["n_new_acq_dates"] == 1


def test_combined_two_arm_line():
    """Tier 1c: display-only combined read appears ONLY with a calibrated summary, and takes
    the max of the arms (daily WATCH + burst ALERT -> combined ALERT)."""
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
    im = _summary_fixture()
    im["burst_alert_k"] = 3.0
    im["latest"]["level"] = "ALERT"
    with tempfile.TemporaryDirectory() as td:
        fig = Path(td) / "f.png"
        fig.write_bytes(tiny)
        out = Path(td) / "d1.html"
        oa.write_dashboard(out, r, [_date(2026, 6, 1), _date(2026, 6, 2)],
                           np.array([0.5, 1.2]), ["DORMANT", "WATCH"], 1, fig, tier, imerg=im)
        page = out.read_text(encoding="utf-8")
        assert "Two-arm read" in page
        assert "§58-calibrated): <b>ALERT</b>" in page     # max(WATCH daily, ALERT burst)
        assert "remains the validated daily gate" in page
        # Without calibrated k (pre-§58 summary): no combined line, card still renders.
        im2 = _summary_fixture()
        out2 = Path(td) / "d2.html"
        oa.write_dashboard(out2, r, [_date(2026, 6, 1), _date(2026, 6, 2)],
                           np.array([0.5, 1.2]), ["DORMANT", "WATCH"], 1, fig, tier, imerg=im2)
        page2 = out2.read_text(encoding="utf-8")
        assert "Two-arm read" not in page2 and "sub-daily burst check" in page2


# ------------------------------------------------------------------------------
# §63 — the false-alarm measurement in imerg_calibration.py. Hermetic: every function
# under test is pure, so these run on hand-built day series with hand-counted answers.
# ------------------------------------------------------------------------------
def _d(iso: str) -> date:
    return date.fromisoformat(iso)


def test_episodes_merge_single_day_gaps_only():
    # 01,02 | gap of 1 (03) | 04  -> one episode; 07 is 2 quiet days later -> a second.
    got = ic.episodes([_d("2026-04-01"), _d("2026-04-02"), _d("2026-04-04"), _d("2026-04-07")])
    assert got == [(_d("2026-04-01"), _d("2026-04-04")), (_d("2026-04-07"), _d("2026-04-07"))]
    assert ic.episodes([]) == []
    # Unsorted input and duplicates must not change the answer.
    assert ic.episodes([_d("2026-04-04"), _d("2026-04-01"), _d("2026-04-01")]) == [
        (_d("2026-04-01"), _d("2026-04-01")), (_d("2026-04-04"), _d("2026-04-04"))]


def test_burst_level_reproduces_the_shipped_grades():
    # Boundary behaviour stated relative to the constants, so a re-tune (§58 k=3 -> §64 k=2.4)
    # does not silently invalidate the test — only test_calibrated_alert_threshold pins values.
    assert ic.burst_level(ic.BURST_WATCH_K - 0.01) == "DORMANT"
    assert ic.burst_level(ic.BURST_WATCH_K) == "WATCH"              # inclusive lower edge
    assert ic.burst_level(ic.BURST_ALERT_K - 0.01) == "WATCH"
    assert ic.burst_level(ic.BURST_ALERT_K) == "ALERT"              # inclusive lower edge
    # It must agree with the production gate's own grading on the same E.
    for E in (0.0, 0.5, 1.0, 2.39, 2.44, 3.0, 9.21):
        expected = ("ALERT" if E >= ig.BURST_ALERT_K else
                    "WATCH" if E >= ig.BURST_WATCH_K else "DORMANT")
        assert ic.burst_level(E) == expected, E


def test_false_alarm_profile_counts_episodes_and_attributes_them():
    # 10 days; ALERT on 02-03 (an event on the 3rd) and on 07-08 (nothing recorded).
    lv = {2: "ALERT", 3: "ALERT", 7: "ALERT", 8: "ALERT"}
    days = [(_d(f"2026-04-{i:02d}"), lv.get(i, "DORMANT")) for i in range(1, 11)]
    p = ic.false_alarm_profile(days, [_d("2026-04-03")], "ALERT", window_d=1)
    assert p["n_days"] == 10 and p["n_flagged_days"] == 4 and p["pct_season"] == 40.0
    assert p["n_episodes"] == 2
    assert p["n_episodes_explained"] == 1 and p["n_episodes_unexplained"] == 1
    assert p["n_events"] == 1 and p["n_events_caught"] == 1
    assert p["flagged_days_in_longest_episode"] == 2

    # A generous window pulls the second episode into the same event's orbit (07 is 4 d away).
    p10 = ic.false_alarm_profile(days, [_d("2026-04-03")], "ALERT", window_d=10)
    assert p10["n_episodes_unexplained"] == 0


def test_false_alarm_profile_watch_includes_alert_days():
    days = [(_d("2026-04-01"), "WATCH"), (_d("2026-04-02"), "ALERT"),
            (_d("2026-04-03"), "DORMANT")]
    assert ic.false_alarm_profile(days, [], "WATCH", 1)["n_flagged_days"] == 2
    assert ic.false_alarm_profile(days, [], "ALERT", 1)["n_flagged_days"] == 1


def test_events_outside_the_record_are_pending_not_missed():
    """The §62 case: an arm whose season stops before the event has no verdict on it —
    it must not be scored as a miss (nor as a catch)."""
    days = [(_d("2026-07-18"), "ALERT"), (_d("2026-07-19"), "DORMANT")]
    p = ic.false_alarm_profile(days, [_d("2026-07-22")], "ALERT", window_d=10)
    assert p["n_events"] == 0 and p["n_events_caught"] == 0
    assert p["n_events_outside_record"] == 1
    # Inside the record, the same ±10 d window does count it.
    days2 = days + [(_d(f"2026-07-{i}"), "DORMANT") for i in range(20, 26)]
    p2 = ic.false_alarm_profile(days2, [_d("2026-07-22")], "ALERT", window_d=10)
    assert p2["n_events"] == 1 and p2["n_events_caught"] == 1
    assert p2["n_events_outside_record"] == 0


def test_temporal_skill_rows_verdict_logic():
    def ev(**kw):
        base = {"site": "ramban", "date": "2026-07-22", "event": "x", "deaths": 2,
                "burst_E": 2.44, "burst_level": "WATCH", "daily_E": None, "daily_level": None}
        return {**base, **kw}

    by = {r["date"]: r for r in ic.temporal_skill_rows([
        ev(date="2025-04-20", burst_level="ALERT", daily_level="ALERT", daily_E=2.89),
        ev(date="2026-04-07", burst_level="DORMANT", daily_level="ALERT", daily_E=2.13),
        ev(date="2026-07-08", burst_level="ALERT", daily_level="WATCH", daily_E=1.06),
        ev(date="2025-05-08", burst_level="WATCH", daily_level="DORMANT", daily_E=0.67),
        ev(date="2026-07-22"),                                   # daily arm cannot see it yet
    ])}
    assert by["2025-04-20"]["caught_at_alert_by"] == "both"
    assert by["2026-04-07"]["caught_at_alert_by"] == "daily"
    assert by["2026-07-08"]["caught_at_alert_by"] == "burst"
    assert by["2025-05-08"]["caught_at_alert_by"] == "neither"
    assert by["2025-05-08"]["delta_days"] == ""
    pend = by["2026-07-22"]
    assert pend["caught_at_alert_by"] == "pending" and pend["daily_level"] == "PENDING"
    assert pend["daily_E"] == "" and pend["delta_days"] == ""
    # A burst ALERT settles the verdict even while the daily arm is blind.
    settled = ic.temporal_skill_rows([ev(burst_level="ALERT", burst_E=3.4)])[0]
    assert settled["caught_at_alert_by"] == "burst" and settled["delta_days"] == "0"


def test_pool_sums_and_rates():
    a = ic.false_alarm_profile([(_d("2026-04-01"), "ALERT")], [], "ALERT", 1)
    b = ic.false_alarm_profile([(_d("2026-05-01"), "DORMANT")], [], "ALERT", 1)
    tot = ic._pool([a, b])
    assert tot["n_days"] == 2 and tot["n_flagged_days"] == 1 and tot["n_episodes"] == 1
    assert tot["n_episodes_unexplained"] == 1
    assert tot["unexplained_episodes_per_100d"] == 50.0
    assert tot["mean_episode_days"] == 1.0 and tot["longest_episode_days"] == 1


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

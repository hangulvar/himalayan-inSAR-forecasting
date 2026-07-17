"""
test_control_panel.py — the local control panel + results hub (control_panel.py).

Covers the server contract WITHOUT Docker: the module is started in-process in
--dry-run mode (buttons echo the exact commands instead of running them), so
every test is fast, hermetic and safe to run any time.

What is asserted:
  • the composed docker commands MIRROR monsoon_cycle.ps1 exactly (per-site
    mintpy fetch + insar alarm + status board; INSAR_CONFIG per site);
  • action/AOI whitelisting, single-job-at-a-time (409), traversal guard on /file;
  • a dry-run job runs to completion and its log streams incrementally;
  • the results hub renders every registry AOI and reads the newest season
    alarm calendar (the same last-row fields monsoon_cycle.ps1 toasts about).

Run from project root:
    conda activate insar_qa_env   (any python 3.9+ works — stdlib only)
    python -m pytest tests/test_control_panel.py -v
OR plain:
    python tests/test_control_panel.py
"""

from __future__ import annotations

import json
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

import control_panel as cp  # noqa: E402

# ------------------------------------------------------------------------------
# In-process server on an ephemeral port, dry-run mode
# ------------------------------------------------------------------------------
cp.DRY_RUN = True
_server = ThreadingHTTPServer(("127.0.0.1", 0), cp.Handler)
_PORT = _server.server_address[1]
threading.Thread(target=_server.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{_PORT}"


def _get(path: str):
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def _post(path: str, body: str):
    req = urllib.request.Request(BASE + path, data=body.encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _wait_job_end(timeout: float = 30.0) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        _, body = _get("/status")
        job = json.loads(body)["job"]
        if job and job["state"] != "running":
            return job
        time.sleep(0.2)
    raise AssertionError("job did not finish in time")


# ------------------------------------------------------------------------------
# 1. Command composition mirrors monsoon_cycle.ps1
# ------------------------------------------------------------------------------

def test_refresh_cycle_steps_mirror_monsoon_cycle():
    aois = cp.list_aois()
    assert "ramban" in aois and "vaishnodevi" in aois
    steps = cp.steps_for("refresh_cycle", "all")
    # per site: fetch (mintpy) then alarm (insar); one status-board step at the end
    assert len(steps) == 2 * len(aois) + 1
    for i, slug in enumerate(aois):
        fetch_argv = steps[2 * i][1]
        alarm_argv = steps[2 * i + 1][1]
        assert fetch_argv == ["docker", "compose", "run", "--rm",
                              "-e", f"INSAR_CONFIG=config/{slug}.yaml",
                              "mintpy", "python", "workflows/live_alarm.py"]
        assert alarm_argv == ["docker", "compose", "run", "--rm",
                              "-e", f"INSAR_CONFIG=config/{slug}.yaml",
                              "insar", "python", "workflows/live_alarm.py"]
    assert steps[-1][1] == ["docker", "compose", "run", "--rm",
                            "insar", "python", "workflows/aoi_status.py"]


def test_single_aoi_and_other_actions():
    steps = cp.steps_for("refresh_cycle", "vaishnodevi")
    assert len(steps) == 3  # fetch + alarm + status board
    assert "INSAR_CONFIG=config/vaishnodevi.yaml" in steps[0][1]
    assert cp.steps_for("status_board", "all") == [
        ("status board (aoi_status.py)",
         ["docker", "compose", "run", "--rm", "insar", "python", "workflows/aoi_status.py"])]
    steps3d = cp.steps_for("rebuild_3d", "ramban")
    assert steps3d[0][1] == ["docker", "compose", "run", "--rm",
                             "-e", "INSAR_CONFIG=config/ramban.yaml",
                             "insar", "python", "workflows/build_3d_dashboard.py"]


def test_suffix_rule_matches_config_py():
    assert cp.data_suffix("ramban") == ""            # grandfathered
    assert cp.data_suffix("vaishnodevi") == "_vaishnodevi"


# ------------------------------------------------------------------------------
# 2. HTTP contract
# ------------------------------------------------------------------------------

def test_control_page_renders_buttons_and_aois():
    status, body = _get("/")
    assert status == 200
    for action in ("refresh_cycle", "status_board", "rebuild_3d"):
        assert f'data-action="{action}"' in body
    for slug in cp.list_aois():
        assert f'value="{slug}"' in body
    assert "DRY-RUN" in body  # the mode badge is visible


def test_run_rejects_unknown_action_and_aoi():
    status, res = _post("/run", "action=nuke_it&aoi=all")
    assert status == 400 and not res["ok"]
    status, res = _post("/run", "action=refresh_cycle&aoi=../../etc")
    assert status == 400 and not res["ok"]


def test_file_traversal_guard_and_serving():
    status, _ = _get("/file/../CLAUDE.md")
    assert status in (403, 404)          # never serve outside data/
    status, _ = _get("/file/..%2f..%2fCLAUDE.md")
    assert status in (403, 404)
    if (PROJECT_ROOT / "data" / "aoi_status.html").exists():
        status, body = _get("/file/aoi_status.html")
        assert status == 200 and "<html" in body.lower()


# ------------------------------------------------------------------------------
# 3. Job lifecycle (dry-run)
# ------------------------------------------------------------------------------

def test_dry_run_job_completes_and_streams_log():
    status, res = _post("/run", "action=status_board&aoi=all")
    assert status == 200 and res["ok"], res
    # busy rejection while running
    status, res2 = _post("/run", "action=status_board&aoi=all")
    assert status == 409 and "already running" in res2["msg"]
    job = _wait_job_end()
    assert job["state"] == "done"
    assert job["n_steps"] == 1
    _, body = _get("/status?log_from=0")
    log = "\n".join(json.loads(body)["log"])
    assert "DRY-RUN, would run: docker compose run --rm insar python workflows/aoi_status.py" in log
    assert "all steps done" in log
    # the job's log file exists and holds the same content
    log_file = cp.LOG_DIR / job["log_file"]
    assert log_file.exists()
    assert "DRY-RUN" in log_file.read_text(encoding="utf-8")


def test_incremental_log_offsets():
    _post("/run", "action=status_board&aoi=all")
    _wait_job_end()
    _, body = _get("/status?log_from=0")
    st = json.loads(body)
    n = st["log_next"]
    assert n == len(st["log"]) and n > 0
    _, body = _get(f"/status?log_from={n}")
    st2 = json.loads(body)
    assert st2["log"] == [] and st2["log_next"] == n


# ------------------------------------------------------------------------------
# 4. Results hub
# ------------------------------------------------------------------------------

def test_results_page_lists_every_aoi():
    status, body = _get("/results")
    assert status == 200
    for slug in cp.list_aois():
        assert f"<h2>{slug}</h2>" in body


def test_latest_alarm_reads_newest_calendar():
    for slug in cp.list_aois():
        found = cp.latest_calendar(slug)
        if not found:
            continue
        path, year = found
        assert path.exists()
        # Ramban's grandfathered names must never pick up another slug's file
        if slug == "ramban":
            assert "vaishnodevi" not in path.name
        row = cp.latest_alarm_row(slug)
        assert row is not None
        assert row["level"] in ("DORMANT", "WATCH", "ALERT"), row
        assert row["as_of"].count("-") == 2  # ISO date


def test_artifacts_exist_and_are_within_data():
    for slug in cp.list_aois():
        for _label, p in cp.aoi_artifacts(slug):
            assert p.exists(), p
            p.resolve().relative_to(cp.DATA.resolve())  # raises if outside data/


def test_live_operational_dashboard_listed_first_when_present():
    for slug in cp.list_aois():
        live_dir = cp.DATA / f"alerts{cp.data_suffix(slug)}" / "mosaic_asc"
        if not list(live_dir.glob("operational_alarm_dashboard*.html")):
            continue
        arts = cp.aoi_artifacts(slug)
        assert arts, slug
        label, p = arts[0]
        assert "Live operational alarm dashboard" in label
        assert p.parent == live_dir
        # per-AOI scoping: another slug's suffixed file must never leak in
        if slug == "ramban":
            assert "vaishnodevi" not in p.name


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

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
    board = cp.steps_for("status_board", "all")
    assert len(board) == 1
    assert board[0].label == "status board (aoi_status.py)"
    assert board[0].argv == ["docker", "compose", "run", "--rm", "insar", "python",
                             "workflows/aoi_status.py"]
    assert board[0].group is None, "the status board is cross-site, not owned by one AOI"
    steps3d = cp.steps_for("rebuild_3d", "ramban")
    assert steps3d[0][1] == ["docker", "compose", "run", "--rm",
                             "-e", "INSAR_CONFIG=config/ramban.yaml",
                             "insar", "python", "workflows/build_3d_dashboard.py"]


def test_suffix_rule_matches_config_py():
    assert cp.data_suffix("ramban") == ""            # grandfathered
    assert cp.data_suffix("vaishnodevi") == "_vaishnodevi"


def test_every_site_step_is_tagged_with_its_site() -> None:
    """The `group` tag is what makes per-site isolation possible; an untagged site step would
    silently go back to cancelling the whole job."""
    for step in cp.steps_for("refresh_cycle", "all"):
        if step.label.startswith("status board"):
            assert step.group is None, step
        else:
            assert step.group and step.label.startswith(step.group + ":"), step
    for step in cp.steps_for("rebuild_3d", "all"):
        assert step.group and f"INSAR_CONFIG=config/{step.group}.yaml" in step.argv, step


# ------------------------------------------------------------------------------
# 1b. Per-site isolation (2026-08-14 regression)
# ------------------------------------------------------------------------------
_OK = [sys.executable, "-c", "print('ok')"]
_FAIL = [sys.executable, "-c", "import sys; print('boom'); sys.exit(1)"]


def _run_steps(steps) -> cp.Job:
    """Drive the real runner over synthetic local steps (no Docker, no dry-run stubbing).

    `_run_job` probes Docker with force=True before doing anything, and this suite is meant to
    run anywhere (including inside a container with no docker CLI), so the probe is stubbed —
    the subject here is the step-sequencing logic, not the daemon check.
    """
    was_dry, was_probe = cp.DRY_RUN, cp.docker_status
    cp.DRY_RUN = False
    cp.docker_status = lambda *a, **k: "up"
    try:
        job = cp.Job("refresh_cycle", "all", steps)
        cp._run_job(job)
        return job
    finally:
        cp.DRY_RUN, cp.docker_status = was_dry, was_probe


def test_one_sites_failure_does_not_cancel_the_sites_behind_it() -> None:
    """THE 2026-08-14 REGRESSION. Tosh (a site with no WHERE map) exited 1 at step 4/7 and the
    runner returned, so Vaishno Devi's fetch, alarm and the status board never ran — the user
    read "step FAILED" as "the cycle failed" while VD's rainfall quietly went stale.

    A failure inside one site must skip only THAT site's remaining steps.
    """
    job = _run_steps([
        cp.Step("alpha: fetch", _OK, "alpha"),
        cp.Step("beta: fetch", _FAIL, "beta"),
        cp.Step("beta: alarm", _OK, "beta"),        # must be SKIPPED (its site failed)
        cp.Step("gamma: fetch", _OK, "gamma"),      # must still RUN
        cp.Step("status board", _OK, None),         # must still RUN
    ])
    log = "\n".join(job.lines)
    assert job.state == "failed", "a partial run must not be reported as a clean success"
    assert job.failed_groups == ["beta"], job.failed_groups
    assert "CONTINUING with the other sites" in log
    assert "SKIPPED (beta: alarm)" in log, "the failed site's later steps should be skipped"
    assert log.count("=== step 4/5 — gamma: fetch") == 1, (
        "gamma never ran — one site's failure is still cancelling the sites behind it")
    assert "=== step 5/5 — status board" in log, "the status board must still run"
    assert "these site(s) did not complete: beta" in log


def test_a_cross_site_step_failing_still_stops_the_job() -> None:
    """The mirror image: when the failing step is NOT owned by a site, there is no independent
    work left to protect, so stopping is correct. Without this the isolation rule would quietly
    become 'never stop', which is its own kind of dishonesty."""
    job = _run_steps([
        cp.Step("status board", _FAIL, None),
        cp.Step("alpha: fetch", _OK, "alpha"),
    ])
    log = "\n".join(job.lines)
    assert job.state == "failed"
    assert "job stopped" in log
    assert "alpha: fetch" not in log, "steps after a cross-site failure must not run"


def test_all_sites_healthy_still_reports_done() -> None:
    job = _run_steps([cp.Step("alpha: fetch", _OK, "alpha"),
                      cp.Step("status board", _OK, None)])
    assert job.state == "done" and job.failed_groups == []
    assert "all steps done" in "\n".join(job.lines)


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
# 3b. Browser-facing hardening (adversarial round, 2026-08-14)
# ------------------------------------------------------------------------------
def _raw(method: str, path: str, body: str | None = None, headers: dict | None = None):
    """A request with FULL control of the headers — urllib will not let us forge Host."""
    import http.client
    c = http.client.HTTPConnection("127.0.0.1", _PORT, timeout=10)
    c.request(method, path, body=body, headers=headers or {})
    r = c.getresponse()
    data = r.read()
    c.close()
    return r.status, dict(r.getheaders()), data


def test_host_header_allowlist_blocks_dns_rebinding() -> None:
    """Binding to 127.0.0.1 stops remote packets, NOT a page the user is browsing: an attacker
    domain with a short TTL can re-resolve to 127.0.0.1, and the request then arrives locally
    carrying the attacker's Host. A browser cannot forge Host, so checking it closes that."""
    for good in (f"127.0.0.1:{_PORT}", f"localhost:{_PORT}", "127.0.0.1"):
        st, _, _ = _raw("GET", "/", headers={"Host": good})
        assert st == 200, f"loopback Host {good} was refused ({st})"
    for bad in ("evil.example.com", "attacker.tld", f"evil.tld:{_PORT}", ""):
        st, _, _ = _raw("GET", "/", headers={"Host": bad})
        assert st == 403, f"Host {bad!r} was ACCEPTED ({st}) — DNS rebinding reaches this origin"


def test_cross_origin_post_cannot_start_a_job() -> None:
    """CSRF: /run launches Docker jobs, and an HTML form POST is a "simple request" — no
    preflight, CORS never consulted. Any page the user visits could have fired one."""
    import urllib.parse
    body = urllib.parse.urlencode({"action": "status_board", "aoi": "all"})
    hdrs = {"Content-Type": "application/x-www-form-urlencoded", "Host": f"127.0.0.1:{_PORT}"}
    st, _, data = _raw("POST", "/run", body, {**hdrs, "Origin": "https://evil.example.com"})
    assert st == 403 and b"cross-origin" in data, (
        f"a cross-origin POST started a job ({st}) — visiting a web page could run Docker here")
    # same-origin and origin-less (curl / the panel's own fetch) must still work
    st2, _, _ = _raw("POST", "/run", body, {**hdrs, "Origin": f"http://127.0.0.1:{_PORT}"})
    assert st2 in (200, 409), f"same-origin POST broken ({st2})"
    st3, _, _ = _raw("POST", "/run", body, hdrs)
    assert st3 in (200, 409), f"origin-less POST broken ({st3})"
    # HERMETICITY: those two accepted POSTs actually START a dry-run job, and `_current_job` is
    # module state shared with every other test in this file. Leave the panel idle or the next
    # test to post gets a 409 from OUR job (it did — that is how this was found).
    _wait_job_end()


def test_responses_carry_the_basic_browser_hardening_headers() -> None:
    """This server returns locally-generated HTML from the SAME origin as its control API, so
    a stray script in a dashboard would inherit that API."""
    st, hdrs, _ = _raw("GET", "/file/aoi_status.html", headers={"Host": f"127.0.0.1:{_PORT}"})
    if st == 404:
        print("      [hardening] aoi_status.html absent — headers checked on / instead")
        st, hdrs, _ = _raw("GET", "/", headers={"Host": f"127.0.0.1:{_PORT}"})
    low = {k.lower(): v for k, v in hdrs.items()}
    assert low.get("x-content-type-options") == "nosniff", low
    assert low.get("x-frame-options") == "DENY", low
    assert low.get("referrer-policy") == "no-referrer", low


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

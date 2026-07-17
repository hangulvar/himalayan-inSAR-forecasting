#!/usr/bin/env python
"""control_panel.py — local one-click control panel + results hub for the monsoon watch.

A SINGLE stdlib-only local web server (http.server — no Flask, no conda env needed:
nothing scientific is imported, so any Python 3.9+ runs it natively). It streamlines
the manual refresh loop without replacing it:

  CONTROL PAGE  (http://127.0.0.1:8765/)
    • Refresh cycle (per AOI or all sites) — the SAME chain monsoon_cycle.ps1 runs:
        docker compose run --rm -e INSAR_CONFIG=config/<slug>.yaml mintpy python workflows/live_alarm.py
        docker compose run --rm -e INSAR_CONFIG=config/<slug>.yaml insar  python workflows/live_alarm.py
      … then the multi-AOI status board (aoi_status.py, insar image).
    • Refresh status board only.
    • Rebuild the 3-D dashboard (build_3d_dashboard.py, insar image).
    One job at a time; live log streaming; every job also logged to logs/.

  RESULTS HUB   (http://127.0.0.1:8765/results)
    Latest alarm state per AOI (last row of the season alarm calendar) + freshness-
    stamped links that open the EXISTING artifacts (aoi_status.html, operational
    alarm PNG/report, the alerts-dir dashboards incl. dashboard_3d.html). No
    dashboard code is duplicated here — this page only finds and links.

Docker: the server NEVER starts or stops Docker (user decision 2026-07-16). It
checks `docker info` and, if the daemon is down, says so and asks you to start
Docker Desktop yourself.

Usage:
    python workflows/control_panel.py                # serve + open browser
    python workflows/control_panel.py --port 9000 --no-browser
    python workflows/control_panel.py --dry-run      # buttons echo commands (no Docker)

Idempotent/safe: read-only over data/ except through the underlying workflow
scripts, which are themselves idempotent.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA = PROJECT_ROOT / "data"
RAIN_DIR = DATA / "rainfall"
LOG_DIR = PROJECT_ROOT / "logs"

DEFAULT_PORT = 8765

# Same palette as aoi_status.py so the two surfaces read as one product.
LEVEL_COLOR = {"DORMANT": "#9aa0a6", "WATCH": "#f0b428", "ALERT": "#dc2828",
               "NO LIVE SEASON": "#c7cdd6"}


def list_aois() -> list[str]:
    """AOI slugs = the per-AOI config registry filenames (config/*.yaml)."""
    return sorted(p.stem for p in CONFIG_DIR.glob("*.yaml"))


def data_suffix(slug: str) -> str:
    """Mirror config.py's rule: '' for ramban (grandfathered), '_<slug>' otherwise."""
    return "" if slug == "ramban" else f"_{slug}"


# ── actions ──────────────────────────────────────────────────────────────────────────

def _compose(image: str, script: str, slug: str | None = None) -> list[str]:
    cmd = ["docker", "compose", "run", "--rm"]
    if slug:
        cmd += ["-e", f"INSAR_CONFIG=config/{slug}.yaml"]
    return cmd + [image, "python", f"workflows/{script}"]


def steps_for(action: str, aoi: str) -> list[tuple[str, list[str]]]:
    """(label, argv) steps for an action. `aoi` is a slug or 'all' where applicable."""
    slugs = list_aois() if aoi == "all" else [aoi]
    if action == "refresh_cycle":
        steps = []
        for s in slugs:
            steps.append((f"{s}: rainfall fetch (mintpy)", _compose("mintpy", "live_alarm.py", s)))
            steps.append((f"{s}: alarm regen (insar)", _compose("insar", "live_alarm.py", s)))
        steps.append(("status board (aoi_status.py)", _compose("insar", "aoi_status.py")))
        return steps
    if action == "status_board":
        return [("status board (aoi_status.py)", _compose("insar", "aoi_status.py"))]
    if action == "rebuild_3d":
        return [(f"{s}: 3-D dashboard (build_3d_dashboard.py)",
                 _compose("insar", "build_3d_dashboard.py", s)) for s in slugs]
    raise ValueError(f"unknown action: {action}")


ACTION_LABELS = {
    "refresh_cycle": "Refresh cycle (rain fetch → alarm → status board)",
    "status_board": "Refresh status board",
    "rebuild_3d": "Rebuild 3-D dashboard",
}


# ── docker check (cached; never starts/stops Docker) ─────────────────────────────────

_docker_lock = threading.Lock()
_docker_cache: tuple[float, str] = (0.0, "unknown")   # (checked_at, 'up'|'down')


def docker_status(force: bool = False, dry_run: bool = False) -> str:
    global _docker_cache
    if dry_run:
        return "up"
    with _docker_lock:
        ts, status = _docker_cache
        if not force and time.time() - ts < 15:
            return status
        try:
            rc = subprocess.run(["docker", "info"], capture_output=True,
                                timeout=20).returncode
            status = "up" if rc == 0 else "down"
        except Exception:  # noqa: BLE001 — CLI missing / timeout both mean "not usable"
            status = "down"
        _docker_cache = (time.time(), status)
        return status


# ── job runner (one at a time) ───────────────────────────────────────────────────────

class Job:
    def __init__(self, action: str, aoi: str, steps: list[tuple[str, list[str]]]):
        self.action = action
        self.aoi = aoi
        self.steps = steps
        self.state = "running"          # running | done | failed
        self.step_idx = 0
        self.lines: list[str] = []
        self.started = datetime.now()
        self.finished: datetime | None = None
        LOG_DIR.mkdir(exist_ok=True)
        self.log_path = LOG_DIR / f"control_panel_{self.started:%Y-%m-%d_%H%M%S}.log"

    def log(self, line: str) -> None:
        line = line.rstrip("\r\n")
        self.lines.append(line)
        if len(self.lines) > 8000:                    # cap memory; file keeps it all
            del self.lines[:2000]
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def as_dict(self) -> dict:
        return {"action": self.action, "label": ACTION_LABELS.get(self.action, self.action),
                "aoi": self.aoi, "state": self.state,
                "step": self.step_idx, "n_steps": len(self.steps),
                "step_labels": [s[0] for s in self.steps],
                "started": self.started.isoformat(timespec="seconds"),
                "log_file": self.log_path.name}


_job_lock = threading.Lock()
_current_job: Job | None = None
DRY_RUN = False


def _run_job(job: Job) -> None:
    if docker_status(force=True, dry_run=DRY_RUN) != "up":
        job.log("Docker is NOT running. Start Docker Desktop yourself (this panel never "
                "starts or stops it), wait for the whale, then hit the button again.")
        job.state = "failed"
        job.finished = datetime.now()
        return
    for i, (label, argv) in enumerate(job.steps):
        job.step_idx = i
        shown = " ".join(argv)
        job.log(f"=== step {i + 1}/{len(job.steps)} — {label}")
        job.log(f"$ {shown}")
        if DRY_RUN:
            argv = [sys.executable, "-c",
                    f"print('DRY-RUN, would run: ' + {shown!r}); import time; time.sleep(0.5)"]
        try:
            proc = subprocess.Popen(argv, cwd=PROJECT_ROOT, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    encoding="utf-8", errors="replace")
            for line in proc.stdout:
                job.log(line)
            rc = proc.wait()
        except Exception as e:  # noqa: BLE001 — surface, don't crash the server
            job.log(f"launch failed: {e}")
            rc = -1
        if rc != 0:
            job.log(f"=== step FAILED (exit {rc}) — job stopped")
            job.state = "failed"
            job.finished = datetime.now()
            return
    job.step_idx = len(job.steps)
    job.log("=== all steps done")
    job.state = "done"
    job.finished = datetime.now()


def start_job(action: str, aoi: str) -> tuple[bool, str]:
    global _current_job
    if action not in ACTION_LABELS:
        return False, f"unknown action '{action}'"
    valid_aois = set(list_aois()) | {"all"}
    if aoi not in valid_aois:
        return False, f"unknown AOI '{aoi}'"
    with _job_lock:
        if _current_job is not None and _current_job.state == "running":
            return False, "a job is already running — wait for it to finish"
        job = Job(action, aoi, steps_for(action, aoi))
        _current_job = job
    threading.Thread(target=_run_job, args=(job,), daemon=True).start()
    return True, "started"


# ── results-hub scanning (read-only) ─────────────────────────────────────────────────

def _ago(p: Path) -> str:
    secs = time.time() - p.stat().st_mtime
    if secs < 3600:
        return f"{secs / 60:.0f} min ago"
    if secs < 86400:
        return f"{secs / 3600:.1f} h ago"
    return f"{secs / 86400:.1f} d ago"


def latest_calendar(slug: str) -> tuple[Path, int] | None:
    """Newest-season alarm calendar for a slug (Ramban grandfathered on _<year>,
    others _<slug>_<year>; the unsuffixed file is the validated base season)."""
    sfx = data_suffix(slug)
    pat = re.compile(rf"^operational_alarm_calendar{re.escape(sfx)}_(\d{{4}})\.csv$")
    years = {}
    for p in RAIN_DIR.glob("operational_alarm_calendar*.csv"):
        m = pat.match(p.name)
        if m:
            years[int(m.group(1))] = p
    if years:
        y = max(years)
        return years[y], y
    base = RAIN_DIR / f"operational_alarm_calendar{sfx}.csv"
    return (base, 0) if base.exists() else None


def latest_alarm_row(slug: str) -> dict | None:
    found = latest_calendar(slug)
    if not found:
        return None
    path, _year = found
    last = None
    try:
        for last in csv.DictReader(path.open(encoding="utf-8")):
            pass
    except Exception:  # noqa: BLE001
        return None
    if not last:
        return None
    stale = ""
    try:
        behind = (date.today() - date.fromisoformat(last["date"])).days
        stale = f"{behind} d behind today"
    except Exception:  # noqa: BLE001
        pass
    return {"level": last.get("alarm_level", "?"), "as_of": last.get("date", "?"),
            "E": last.get("exceedance_E", "?"), "zones": last.get("n_live_zones", "?"),
            "stale": stale, "csv": path}


def aoi_artifacts(slug: str) -> list[tuple[str, Path]]:
    """(label, path) for this AOI's linkable artifacts, existing files only."""
    sfx = data_suffix(slug)
    out: list[tuple[str, Path]] = []
    year_pat = re.compile(rf"^operational_alarm{re.escape(sfx)}_(\d{{4}})\.png$")
    pngs = sorted((p for p in RAIN_DIR.glob("operational_alarm*.png")
                   if year_pat.match(p.name)), reverse=True)
    for p in pngs[:1]:
        out.append(("Operational alarm dashboard (PNG)", p))
    rep_pat = re.compile(rf"^operational_alarm_report{re.escape(sfx)}_(\d{{4}})\.md$")
    reps = sorted((p for p in RAIN_DIR.glob("operational_alarm_report*.md")
                   if rep_pat.match(p.name)), reverse=True)
    for p in reps[:1]:
        out.append(("Operational alarm report (MD)", p))
    alerts_dir = DATA / f"alerts{sfx}"
    if alerts_dir.is_dir():
        for p in sorted(alerts_dir.glob("*.html")):
            out.append((f"alerts: {p.name}", p))
        gate = alerts_dir / "per_zone_gate.png"
        if gate.exists():
            out.append(("Per-zone gate (PNG)", gate))
    cal = latest_calendar(slug)
    if cal:
        out.append(("Season alarm calendar (CSV)", cal[0]))
    return out


# ── HTML pages ───────────────────────────────────────────────────────────────────────

_CSS = """
body{font-family:'Segoe UI',system-ui,sans-serif;margin:0;background:#f4f6f8;color:#1f2733}
header{background:#1d3557;color:#fff;padding:14px 24px;display:flex;align-items:center;gap:16px}
header h1{font-size:18px;margin:0;font-weight:600}
header a{color:#a8dadc;text-decoration:none;font-size:14px}
main{max-width:980px;margin:20px auto;padding:0 16px}
.card{background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.12);padding:16px 20px;margin-bottom:16px}
.card h2{font-size:15px;margin:0 0 6px}
.card p.desc{margin:4px 0 12px;font-size:13px;color:#5a6472}
button{background:#1d3557;color:#fff;border:0;border-radius:6px;padding:8px 16px;font-size:14px;cursor:pointer}
button:disabled{background:#9aa0a6;cursor:not-allowed}
select{padding:6px 8px;border-radius:6px;border:1px solid #c7cdd6;font-size:14px;margin-right:10px}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;color:#fff}
#log{background:#10161d;color:#d7e0ea;font-family:Consolas,monospace;font-size:12px;
     padding:12px;border-radius:8px;max-height:420px;overflow-y:auto;white-space:pre-wrap;display:none}
table{border-collapse:collapse;width:100%;font-size:13px}
td,th{text-align:left;padding:6px 10px;border-bottom:1px solid #eef1f4}
a{color:#1d6fa5}
.muted{color:#8a93a0;font-size:12px}
"""


def control_page() -> str:
    aois = list_aois()
    opts_all = '<option value="all">All sites</option>' + "".join(
        f'<option value="{html.escape(a)}">{html.escape(a)}</option>' for a in aois)
    opts_one = "".join(
        f'<option value="{html.escape(a)}">{html.escape(a)}</option>' for a in aois)
    dry = ('<span class="pill" style="background:#7b3fb3">DRY-RUN</span>' if DRY_RUN else "")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Monsoon Watch — Control Panel</title><style>{_CSS}</style></head><body>
<header><h1>🏔️ Monsoon Watch — Control Panel</h1>{dry}
  <span id="docker" class="pill" style="background:#9aa0a6">Docker: checking…</span>
  <span style="flex:1"></span><a href="/results">Results hub →</a></header>
<main>
<div id="dockerhint" class="card" style="display:none;border-left:4px solid #dc2828">
  <b>Docker Desktop is not running.</b> Start it yourself (this panel never starts or
  stops Docker), wait for the whale icon, then retry. <span class="muted">Buttons stay
  enabled — a run started while Docker is down fails with a clear message.</span></div>

<div class="card"><h2>Refresh cycle</h2>
  <p class="desc">Rain fetch (ERA5-Land, mintpy image) → alarm regen (insar image) per
  site, then the multi-AOI status board — the same chain the scheduled cycle runs.</p>
  <select id="aoi_cycle">{opts_all}</select>
  <button class="run" data-action="refresh_cycle" data-sel="aoi_cycle">Run refresh cycle</button></div>

<div class="card"><h2>Status board</h2>
  <p class="desc">Regenerate the multi-AOI status dashboard only (aoi_status.py — fast).</p>
  <button class="run" data-action="status_board">Refresh status board</button></div>

<div class="card"><h2>3-D dashboard</h2>
  <p class="desc">Rebuild the interactive 3-D hazard explorer (build_3d_dashboard.py).
  Ramban has the full scenario inputs; other AOIs may fail if theirs don't exist yet.</p>
  <select id="aoi_3d">{opts_one}</select>
  <button class="run" data-action="rebuild_3d" data-sel="aoi_3d">Rebuild 3-D dashboard</button></div>

<div class="card"><h2>Job <span id="jobstate" class="pill" style="background:#9aa0a6">idle</span></h2>
  <div id="jobinfo" class="muted">No job run yet this session.</div>
  <div style="height:8px"></div><div id="log"></div></div>
</main>
<script>
let logFrom = 0, polling = null;
function setDocker(s) {{
  const el = document.getElementById('docker');
  el.textContent = 'Docker: ' + s;
  el.style.background = s === 'up' ? '#2e8b57' : (s === 'down' ? '#dc2828' : '#9aa0a6');
  document.getElementById('dockerhint').style.display = s === 'down' ? 'block' : 'none';
}}
async function poll(docker) {{
  const r = await fetch('/status?log_from=' + logFrom + (docker ? '&docker=1' : ''));
  const st = await r.json();
  if (st.docker) setDocker(st.docker);
  const j = st.job, badge = document.getElementById('jobstate');
  if (j) {{
    badge.textContent = j.state;
    badge.style.background = j.state === 'running' ? '#1d6fa5'
      : (j.state === 'done' ? '#2e8b57' : '#dc2828');
    document.getElementById('jobinfo').textContent =
      j.label + ' [' + j.aoi + '] — step ' + Math.min(j.step + 1, j.n_steps) + '/' + j.n_steps
      + ' — started ' + j.started + ' — log: logs/' + j.log_file;
    const lg = document.getElementById('log');
    if (st.log.length) {{
      lg.style.display = 'block';
      lg.textContent += st.log.join('\\n') + '\\n';
      lg.scrollTop = lg.scrollHeight;
      logFrom = st.log_next;
    }}
    document.querySelectorAll('button.run').forEach(b => b.disabled = j.state === 'running');
    if (j.state !== 'running' && polling) {{ clearInterval(polling); polling = null;
      if (j.state === 'done') document.getElementById('jobinfo').innerHTML +=
        ' — <a href="/results">open the results hub →</a>'; }}
  }}
}}
document.querySelectorAll('button.run').forEach(b => b.onclick = async () => {{
  const aoi = b.dataset.sel ? document.getElementById(b.dataset.sel).value : 'all';
  const r = await fetch('/run', {{method: 'POST',
    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
    body: 'action=' + b.dataset.action + '&aoi=' + encodeURIComponent(aoi)}});
  const res = await r.json();
  if (!res.ok) {{ alert(res.msg); return; }}
  logFrom = 0; document.getElementById('log').textContent = '';
  if (!polling) polling = setInterval(() => poll(false), 1500);
  poll(false);
}});
poll(true); setInterval(() => poll(true), 30000);
</script></body></html>"""


def _file_url(p: Path) -> str:
    return "/file/" + p.relative_to(DATA).as_posix()


def results_page() -> str:
    rows = []
    board = DATA / "aoi_status.html"
    board_link = (f'<a href="{_file_url(board)}" target="_blank">open</a> '
                  f'<span class="muted">updated {_ago(board)}</span>'
                  if board.exists() else '<span class="muted">not built yet</span>')
    for slug in list_aois():
        alarm = latest_alarm_row(slug)
        if alarm:
            color = LEVEL_COLOR.get(alarm["level"], "#9aa0a6")
            state = (f'<span class="pill" style="background:{color}">{html.escape(alarm["level"])}</span> '
                     f'as-of {html.escape(alarm["as_of"])} '
                     f'(E={html.escape(str(alarm["E"]))}, {html.escape(str(alarm["zones"]))} live zones)'
                     + (f' <span class="muted">— rainfall {html.escape(alarm["stale"])}</span>'
                        if alarm["stale"] else ""))
        else:
            state = '<span class="muted">no season alarm calendar found</span>'
        arts = "".join(
            f'<tr><td>{html.escape(label)}</td>'
            f'<td class="muted">updated {_ago(p)}</td>'
            f'<td><a href="{_file_url(p)}" target="_blank">open</a></td></tr>'
            for label, p in aoi_artifacts(slug))
        rows.append(f'<div class="card"><h2>{html.escape(slug)}</h2><p>{state}</p>'
                    f'<table>{arts or "<tr><td class=muted>no artifacts yet</td></tr>"}</table></div>')
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Monsoon Watch — Results Hub</title><style>{_CSS}</style></head><body>
<header><h1>📊 Monsoon Watch — Results Hub</h1><span style="flex:1"></span>
  <a href="/">← Control panel</a></header>
<main>
<div class="card"><h2>Multi-AOI status board</h2>
  <p class="desc">The cross-site stage/alarm dashboard (aoi_status.py).</p>{board_link}</div>
{''.join(rows)}
<p class="muted">Rendered {datetime.now():%Y-%m-%d %H:%M:%S} — reload after a run to
refresh timestamps. Files are served read-only from data/.</p>
</main></body></html>"""


# ── HTTP server ──────────────────────────────────────────────────────────────────────

MIME = {".html": "text/html; charset=utf-8", ".png": "image/png",
        ".json": "application/json", ".csv": "text/csv; charset=utf-8",
        ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8"}


class Handler(BaseHTTPRequestHandler):
    server_version = "MonsoonControlPanel/1.0"

    def log_message(self, fmt, *args):  # quiet console; job logs go to logs/
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, page: str, code: int = 200) -> None:
        self._send(code, page.encode("utf-8"), "text/html; charset=utf-8")

    def _json(self, obj: dict, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def do_GET(self):  # noqa: N802 — http.server API
        url = urlparse(self.path)
        if url.path == "/":
            return self._html(control_page())
        if url.path == "/results":
            return self._html(results_page())
        if url.path == "/status":
            q = parse_qs(url.query)
            log_from = int(q.get("log_from", ["0"])[0])
            out: dict = {"job": _current_job.as_dict() if _current_job else None,
                         "log": [], "log_next": log_from}
            if q.get("docker") == ["1"]:
                out["docker"] = docker_status(dry_run=DRY_RUN)
            if _current_job:
                lines = _current_job.lines
                out["log"] = lines[log_from:]
                out["log_next"] = len(lines)
            return self._json(out)
        if url.path.startswith("/file/"):
            return self._serve_file(unquote(url.path[len("/file/"):]))
        return self._html("<h1>404</h1>", 404)

    def do_POST(self):  # noqa: N802
        url = urlparse(self.path)
        if url.path != "/run":
            return self._json({"ok": False, "msg": "not found"}, 404)
        length = int(self.headers.get("Content-Length", 0))
        q = parse_qs(self.rfile.read(length).decode("utf-8"))
        action = q.get("action", [""])[0]
        aoi = q.get("aoi", ["all"])[0]
        ok, msg = start_job(action, aoi)
        return self._json({"ok": ok, "msg": msg}, 200 if ok else (409 if "already" in msg else 400))

    def _serve_file(self, rel: str) -> None:
        try:
            target = (DATA / rel).resolve()
            target.relative_to(DATA.resolve())     # traversal guard
        except (ValueError, OSError):
            return self._html("<h1>403</h1>", 403)
        if not target.is_file():
            return self._html("<h1>404</h1>", 404)
        ctype = MIME.get(target.suffix.lower(), "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)


def main(argv: list[str] | None = None) -> int:
    global DRY_RUN
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="buttons echo the commands instead of running Docker")
    args = ap.parse_args(argv)
    DRY_RUN = args.dry_run

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Monsoon Watch control panel: {url}" + ("  [DRY-RUN]" if DRY_RUN else ""))
    print("Ctrl+C to stop. Docker stays under your control — this panel only checks it.")
    if not args.no_browser:
        threading.Timer(0.7, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

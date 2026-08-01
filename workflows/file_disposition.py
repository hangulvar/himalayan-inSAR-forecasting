#!/usr/bin/env python
"""file_disposition.py — a READ-ONLY map of which local files are safe to delete, which must be
archived off-machine first, and which must never be touched.

WHY: `data/` is ~78 GB and mixes three very different kinds of file — validated products that
are load-bearing, raw inputs that cost HyP3 credits / CDS downloads to obtain (and whose ASF
copies have expired, §48), and cheap derived caches. Deleting the wrong one loses a validated
product or an irreplaceable download; never deleting anything wastes tens of GB. This tool
classifies every file so a cleanup is a decision, not a guess.

IT NEVER DELETES ANYTHING. It reads the tree and writes a report. Acting on the report is a
human step, done by hand.

FOUR CLASSES (a file's class answers "what happens if I delete it?"):
  PROTECTED      breaks the validated product or the repo. = in the flood baseline freeze
                 (the 116 hashed artifacts) OR git-tracked. NEVER delete as cleanup.
  ARCHIVE_FIRST  loses data that took credits / downloads / multi-session compute and cannot be
                 cheaply regenerated. Verify an off-machine copy (Google Drive / ASF / CDS)
                 exists, THEN delete. Each rule states how it would be re-created.
  REGENERABLE    a workflow rebuilds it cheaply, or it is pure cache/scratch. Delete freely to
                 reclaim space. (Assumes its ARCHIVE_FIRST *inputs* are still present — see the
                 dependency note in the report.)
  REVIEW         matched no rule. The tool refuses to guess "disposable"; a human decides.
                 (The conservative default — a new data dir lands here, not in REGENERABLE.)

Authority order: the freeze and git win over any path rule, so a validated raster living inside
an otherwise-regenerable directory is still correctly PROTECTED.

  docker compose run --rm insar python workflows/file_disposition.py
  python workflows/file_disposition.py            # native (needs the conda env for git)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FREEZE = PROJECT_ROOT / "data" / "flood" / "_baseline_freeze.json"
SCAN_ROOTS = ["data", "logs"]                       # where the disk actually lives
REPORT_STEM = "file_disposition_report"             # excluded from its own scan

# ── classification rules (DATA — project-specific, documented above) ─────────────────────
# ARCHIVE_FIRST: top-level dir under data/ (or a filename trait) -> how it is re-created.
ARCHIVE_FIRST_DIRS = {
    "raw_zips": "Google Drive archive (§48) — ASF copies expired; re-download costs HyP3 credits",
    "processed_tiffs": "re-extract from the Drive-archived raw zips, or re-process via HyP3 (credits)",
    "nisar": "re-fetch the GUNW granules from ASF (~4 min each, §65) — bandwidth, not credits",
    "dem_alos_12m": "re-download the ALOS 12 m DEM from ASF",
    "dem_alos_12m_vaishnodevi": "re-download the ALOS 12 m DEM from ASF",
    "mintpy": "re-run MintPy (multi-session compute; the §61-class rebuild)",
}
ARCHIVE_FIRST_SUFFIXES = {".grib"}                  # raw ERA5-Land pulls (CDS); also *.grib.idx etc.

# REGENERABLE: any path PART (dir at any depth) that means "cheap to rebuild / pure cache".
REGENERABLE_PARTS = {"_cache", "_rain", "__pycache__", ".ipynb_checkpoints"}
# REGENERABLE: top-level dir under data/ whose contents a workflow rebuilds (non-frozen files
# only — the freeze check above pulls the validated ones out into PROTECTED first).
REGENERABLE_DIRS = {
    "qa_masks": "re-run the QA masking over processed_tiffs (rebuilds the stack manifest too)",
    "alerts": "re-run operational_alarm.py / agentic_orchestrator.py",
    "alerts_vaishnodevi": "re-run operational_alarm.py / agentic_orchestrator.py",
    "velocity": "re-run the SBAS inversion (needs processed_tiffs)",
    "velocity_vaishnodevi": "re-run the SBAS inversion (needs processed_tiffs)",
    "hazard": "re-run the geomechanical engine",
    "hazard_vaishnodevi": "re-run the geomechanical engine",
    "mosaic": "re-run the union-mosaic step", "mosaic_asc": "re-run the union-mosaic step",
    "mosaic_vslope": "re-run the union-mosaic step",
    "mosaic_vaishnodevi": "re-run the union-mosaic step",
    "flood": "re-run flood_domain.py / flood_gate.py (the _cache/_rain here are caches)",
    "rainfall": "re-derive from the *.grib (archive-first) via the rainfall scripts",
    "optical": "re-run optical_change.py", "osm": "re-fetch from OpenStreetMap",
    "rebuild": "intermediate rebuild scratch — re-created by the rebuild workflow",
    "llof_swap": "the §67 pre-swap backup — safe to delete once the LLOF swap is accepted",
}
REGENERABLE_SUFFIXES = {".pyc", ".log", ".png", ".html"}
REGENERABLE_NAMES = {"radar_watch.json", "aoi_status.json"}
# A file whose name contains this is a generated report/figure, re-created by re-running its
# producing script (the frozen JSON back-tests are pulled into PROTECTED first; only their .md
# twins and un-frozen report variants reach this rule). Deliberately does NOT match the
# inventory's ground-truth DATA (gsi_inventory_aoi.geojson/csv) — that stays REVIEW so a human
# decides, per the "inventory is load-bearing ground truth" rule in CLAUDE.md.
REGENERABLE_NAME_SUBSTRINGS = {"report", "validation_stats", "susceptibility_crosscheck"}


def load_freeze_set() -> set[str]:
    """The POSIX rel-paths of the 116 hashed protected artifacts, or empty if the freeze is
    absent (a fresh checkout) — then PROTECTED rests on git alone, which is still correct."""
    if not FREEZE.exists():
        return set()
    return set(json.loads(FREEZE.read_text(encoding="utf-8")).get("files", {}))


def git_tracked_set() -> set[str]:
    """POSIX rel-paths git tracks under the scan roots. Empty (with a printed note) if git is
    unavailable — the freeze still covers the validated products."""
    try:
        out = subprocess.run(["git", "-C", str(PROJECT_ROOT), "ls-files", *SCAN_ROOTS],
                             capture_output=True, text=True, timeout=60, check=True)
        return {ln.strip() for ln in out.stdout.splitlines() if ln.strip()}
    except Exception as e:  # noqa: BLE001 — git missing must not break the report
        print(f"  (git unavailable: {type(e).__name__} — PROTECTED rests on the freeze only)")
        return set()


def classify(rel_posix: str, freeze: set[str], tracked: set[str]) -> tuple[str, str]:
    """(class, reason) for one file. Pure — the injected freeze/tracked sets make it testable
    without a real repo. Authority order is freeze/git first, then path rules, then REVIEW."""
    parts = rel_posix.split("/")
    name = parts[-1]
    # 1. Authoritative: hashed-protected or committed.
    if rel_posix in freeze:
        return "PROTECTED", "in the flood baseline freeze (a validated, hashed artifact)"
    if rel_posix in tracked:
        return "PROTECTED", "git-tracked (committed — deleting it is a repo change, not cleanup)"
    # 2. Regenerable caches take priority over the archive-first dir they may sit inside
    #    (data/flood/_cache is a cache even though flood/ is not archive-first, and a stray
    #    __pycache__ under processed_tiffs is still just bytecode).
    if REGENERABLE_PARTS & set(parts):
        hit = (REGENERABLE_PARTS & set(parts)).pop()
        return "REGENERABLE", f"cache/scratch directory '{hit}'"
    # 3. Archive-first raw/expensive layer (by top data-dir or raw-download suffix).
    top = parts[1] if parts[0] == "data" and len(parts) > 1 else None
    if top in ARCHIVE_FIRST_DIRS:
        return "ARCHIVE_FIRST", ARCHIVE_FIRST_DIRS[top]
    if any(name.endswith(s) or f"{s}." in name for s in ARCHIVE_FIRST_SUFFIXES):
        return "ARCHIVE_FIRST", "raw ERA5-Land GRIB — re-fetch from Copernicus CDS (fetch_rainfall.py)"
    # 4. Regenerable derived outputs.
    if top in REGENERABLE_DIRS:
        return "REGENERABLE", REGENERABLE_DIRS[top]
    if parts[0] == "logs":
        return "REGENERABLE", "log output"
    if any(name.endswith(s) for s in REGENERABLE_SUFFIXES) or name in REGENERABLE_NAMES:
        return "REGENERABLE", "derived report/figure/log"
    if any(sub in name for sub in REGENERABLE_NAME_SUBSTRINGS):
        return "REGENERABLE", "generated report — re-run its producing script"
    # 5. Unmatched — never guessed disposable.
    return "REVIEW", "matched no rule — classify by hand before deleting"


def scan(freeze: set[str], tracked: set[str]) -> dict:
    """Walk the scan roots, classify every file, aggregate by (class, top-dir)."""
    rows = []
    for root in SCAN_ROOTS:
        base = PROJECT_ROOT / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.name.startswith(REPORT_STEM):
                continue
            rel = p.relative_to(PROJECT_ROOT).as_posix()
            cls, reason = classify(rel, freeze, tracked)
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            top = rel.split("/")[1] if "/" in rel[len(root) + 1:] else root
            rows.append({"path": rel, "class": cls, "reason": reason, "bytes": size,
                         "group": f"{root}/{top}" if top != root else root})
    return {"rows": rows}


def _human(n: int) -> str:
    x = float(n)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if x < 1024 or u == "TB":
            return f"{x:.1f} {u}"
        x /= 1024


def build_report(scanned: dict, freeze: set[str]) -> dict:
    rows = scanned["rows"]
    classes = ["PROTECTED", "ARCHIVE_FIRST", "REGENERABLE", "REVIEW"]
    summary = {c: {"files": 0, "bytes": 0} for c in classes}
    groups: dict = {}
    for r in rows:
        summary[r["class"]]["files"] += 1
        summary[r["class"]]["bytes"] += r["bytes"]
        g = groups.setdefault((r["class"], r["group"]), {"files": 0, "bytes": 0, "reason": r["reason"]})
        g["files"] += 1
        g["bytes"] += r["bytes"]
    # Freeze integrity: a protected artifact that has vanished from disk.
    on_disk = {r["path"] for r in rows}
    missing = sorted(f for f in freeze if f not in on_disk)
    return {"summary": summary, "groups": groups, "rows": rows,
            "freeze_missing": missing,
            "review_files": sorted((r["path"], r["bytes"]) for r in rows if r["class"] == "REVIEW")}


def write_report(rep: dict) -> Path:
    out_md = PROJECT_ROOT / "data" / f"{REPORT_STEM}.md"
    s = rep["summary"]
    action = {
        "PROTECTED": "NEVER delete as cleanup — load-bearing or committed.",
        "ARCHIVE_FIRST": "verify an off-machine copy exists (Drive/ASF/CDS), THEN delete.",
        "REGENERABLE": "delete freely to reclaim space; a workflow rebuilds it.",
        "REVIEW": "classify by hand — the tool would not guess disposable.",
    }
    md = ["# Local file disposition map", "",
          "_Read-only classification of `data/` + `logs/`. This tool never deletes anything — "
          "acting on it is a manual step._", "",
          "## What each class means, and what to do", "",
          "| class | disk | files | action |", "|---|---:|---:|---|"]
    for c in ("PROTECTED", "ARCHIVE_FIRST", "REGENERABLE", "REVIEW"):
        md.append(f"| **{c}** | {_human(s[c]['bytes'])} | {s[c]['files']} | {action[c]} |")
    reclaim = s["REGENERABLE"]["bytes"]
    md += ["", f"**Reclaim now (REGENERABLE):** {_human(reclaim)}. "
           f"**Reclaim after archiving (ARCHIVE_FIRST):** {_human(s['ARCHIVE_FIRST']['bytes'])}.",
           "", "> Dependency note: REGENERABLE assumes its ARCHIVE_FIRST *inputs* are still "
           "present. e.g. `qa_masks/` and `velocity/` rebuild only if `processed_tiffs/` "
           "exists; `rainfall/` derived CSVs rebuild only from the `*.grib`. Delete the "
           "regenerable layer freely, but do not delete a REGENERABLE dir AND its ARCHIVE_FIRST "
           "input in the same breath unless you are done with that AOI-season."]
    for c in ("ARCHIVE_FIRST", "REGENERABLE", "PROTECTED", "REVIEW"):
        gs = sorted(((k[1], v) for k, v in rep["groups"].items() if k[0] == c),
                    key=lambda kv: -kv[1]["bytes"])
        if not gs:
            continue
        md += ["", f"## {c} — {action[c]}", "", "| location | disk | files | recreate / note |",
               "|---|---:|---:|---|"]
        for g, v in gs:
            md.append(f"| `{g}/` | {_human(v['bytes'])} | {v['files']} | {v['reason']} |")
    if rep["review_files"]:
        md += ["", "### REVIEW files (decide by hand)", ""]
        md += [f"- `{p}` ({_human(b)})" for p, b in rep["review_files"][:50]]
    if rep["freeze_missing"]:
        md += ["", "### ⚠ Freeze integrity — PROTECTED artifacts MISSING from disk", ""]
        md += [f"- `{f}`" for f in rep["freeze_missing"][:50]]
    else:
        md += ["", "_Freeze integrity: all baseline-frozen artifacts present on disk._"]
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    (PROJECT_ROOT / "data" / f"{REPORT_STEM}.json").write_text(
        json.dumps({"summary": rep["summary"],
                    "groups": {f"{k[0]}|{k[1]}": v for k, v in rep["groups"].items()},
                    "freeze_missing": rep["freeze_missing"],
                    "review_files": rep["review_files"]}, indent=2), encoding="utf-8")
    return out_md


def main() -> int:
    freeze, tracked = load_freeze_set(), git_tracked_set()
    print(f"file disposition: freeze={len(freeze)} artifacts, git-tracked={len(tracked)} paths")
    rep = build_report(scan(freeze, tracked), freeze)
    out = write_report(rep)
    s = rep["summary"]
    for c in ("PROTECTED", "ARCHIVE_FIRST", "REGENERABLE", "REVIEW"):
        print(f"  {c:<14} {_human(s[c]['bytes']):>10}  ({s[c]['files']} files)")
    if rep["freeze_missing"]:
        print(f"  ⚠ {len(rep['freeze_missing'])} baseline-frozen artifact(s) MISSING from disk")
    print(f"  -> {out.name} , {REPORT_STEM}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

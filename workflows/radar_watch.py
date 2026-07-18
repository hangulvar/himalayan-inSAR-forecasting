#!/usr/bin/env python
"""radar_watch.py — Tier 0c of the Strengthening Plan (§56): automate the DISCOVERY that new
radar data has landed, so the cadence rebuild is triggered by a signal instead of by someone
remembering to recheck (the S1 constellation handover went unnoticed for weeks exactly because
this loop was manual — error log 2026-07-18).

WHAT IT DOES (per registry AOI, one bounded all-units ASF query each):
  1. Reads the AOI's newest LIBRARY acquisition — the youngest scene date among the products
     of the stacks that feed its operational footprint (stack manifest × footprint
     source_stacks; the manifest is metadata-derived and updated by every download).
  2. Asks ASF for ALL Sentinel-1 units' SLC IW ASCENDING scenes over the AOI since then
     (ASC only: the library's stacks are ASC — a new DESC pass does not unblock a rebuild).
  3. Writes data/radar_watch.json — per-site: library_through, newest_asc_at_asf,
     new_asc_scenes, per-path newest — and prints a one-line verdict per site.

The operational dashboard's radar-freshness pill (operational_alarm.py) reads this file, so
"newer radar EXISTS at ASF — rebuild unblocked" appears on the dashboard automatically.
live_alarm.py's alarm stage runs this NON-FATALLY before each regen (ASF down => the pill just
shows the last known state); it also runs standalone:

  docker compose run --rm insar python workflows/radar_watch.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

MANIFEST = PROJECT_ROOT / "data" / "qa_masks" / "_stack_manifest.json"
WATCH_JSON = PROJECT_ROOT / "data" / "radar_watch.json"
_SCENE_DATE = re.compile(r"^S1[A-Z]{2}_\d{8}T\d{6}_(\d{8})T\d{6}_")


def library_newest(footprint_path: Path) -> date | None:
    """Newest acquisition date among the library products of the stacks feeding this
    footprint (None when the footprint/manifest is absent — new AOIs degrade gracefully)."""
    if not (footprint_path.exists() and MANIFEST.exists()):
        return None
    stacks = set(json.loads(footprint_path.read_text(encoding="utf-8"))
                 .get("source_stacks", []))
    newest = None
    for name, meta in json.loads(MANIFEST.read_text(encoding="utf-8")).items():
        if meta.get("stack") in stacks:
            m = _SCENE_DATE.match(name)
            if m:
                d = datetime.strptime(m.group(1), "%Y%m%d").date()
                newest = d if newest is None or d > newest else newest
    return newest


def summarize_new(scenes: list[dict], library_through: date | None) -> dict:
    """Pure summary of an ASF scene list vs the library edge (unit-tested without network).
    scenes: [{'date': 'YYYY-MM-DD', 'path': int, 'unit': 'S1D'}, ...] (ASC only)."""
    new = [s for s in scenes
           if library_through is None or date.fromisoformat(s["date"]) > library_through]
    per_path = {}
    for s in scenes:
        p = str(s["path"])
        per_path[p] = max(per_path.get(p, s["date"]), s["date"])
    return {
        "library_through": library_through.isoformat() if library_through else None,
        "newest_asc_at_asf": max((s["date"] for s in scenes), default=None),
        "new_asc_scenes": len(new),
        "new_units": sorted({s["unit"] for s in new}),
        "per_path_newest": per_path,
    }


def query_asf(wkt: str, since: date) -> list[dict]:
    """All-units S1 SLC IW ASCENDING scenes over the AOI since `since` (constellation-level —
    never a unit whitelist, per the 2026-07-18 lesson)."""
    import asf_search as asf
    res = asf.search(platform=[asf.PLATFORM.SENTINEL1], processingLevel=asf.PRODUCT_TYPE.SLC,
                     beamMode=asf.BEAMMODE.IW, intersectsWith=wkt,
                     start=f"{since.isoformat()}T00:00:00Z")
    out = []
    for r in res:
        p = r.properties
        if not (p.get("flightDirection") or "").upper().startswith("ASC"):
            continue
        when = (p.get("startTime") or "")[:10]
        if not when:  # rare metadata gaps — fall back to the scene name's date field
            m = re.search(r"_(\d{8})T\d{6}_", p.get("sceneName", ""))
            when = datetime.strptime(m.group(1), "%Y%m%d").date().isoformat() if m else None
        if when:
            out.append({"date": when, "path": p.get("pathNumber"),
                        "unit": (p.get("sceneName") or "???")[:3]})
    return out


def _aoi_wkt(aoi_path: Path) -> str:
    gj = json.loads(aoi_path.read_text(encoding="utf-8"))

    def flat(c):
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for x in c:
                yield from flat(x)
    pts = [p for f in gj.get("features", [gj]) for p in flat(f["geometry"]["coordinates"])]
    lons, lats = [p[0] for p in pts], [p[1] for p in pts]
    return (f"POLYGON(({min(lons)} {min(lats)},{max(lons)} {min(lats)},"
            f"{max(lons)} {max(lats)},{min(lons)} {max(lats)},{min(lons)} {min(lats)}))")


def main() -> int:
    import yaml
    from datetime import timedelta
    sites = {}
    for cfg_path in sorted((PROJECT_ROOT / "config").glob("*.yaml")):
        slug = cfg_path.stem
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        aoi_path = PROJECT_ROOT / cfg.get("aoi_path", "")
        sfx = "" if slug == "ramban" else f"_{slug}"
        fp = PROJECT_ROOT / "data" / f"alerts{sfx}" / "mosaic_asc" / "alerts_operational.json"
        if not (aoi_path.exists() and fp.exists()):
            continue
        lib = library_newest(fp)
        since = (lib - timedelta(days=1)) if lib else date(2026, 1, 1)
        scenes = query_asf(_aoi_wkt(aoi_path), since)
        s = summarize_new(scenes, lib)
        sites[slug] = s
        verdict = (f"NEW radar at ASF: {s['new_asc_scenes']} ASC scene(s) "
                   f"({'/'.join(s['new_units'])}) through {s['newest_asc_at_asf']} "
                   f"— the cadence rebuild is UNBLOCKED"
                   if s["new_asc_scenes"] else "no new ASC scenes — rebuild still waiting")
        print(f"radar watch [{slug}]: library through {s['library_through']} | {verdict}")
    if not sites:
        raise SystemExit("radar_watch: no site had an AOI + operational footprint to check")
    WATCH_JSON.write_text(json.dumps(
        {"checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
         "sites": sites}, indent=2), encoding="utf-8")
    print(f"  -> {WATCH_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

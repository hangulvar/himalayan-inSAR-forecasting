#!/usr/bin/env python
"""exposure_footprint.py — draw the ground each hazard zone occupies, and where its debris
would go: an "affected area" layer for the map products (GeoJSON + KML + the 3-D dashboard).

WHAT THIS ADDS. Until now a hazard zone was published as a single POINT (its centroid) plus a
row of numbers. An operator planning an inspection needs two more things:

  1. the SHAPE of the flagged ground — the actual pixels the zone occupies, not a dot;
  2. the ground BELOW it that the debris would cross if that slope let go.

Both are drawn from artifacts that already exist; this script invents no new science:

  • the zone shape is re-derived by re-running the SAME mask the published alert came from —
    agentic_orchestrator's `creep & unstable` fusion, its `MIN_CLUSTER_PX` speck filter, its
    severity sort — and is then CHECKED, zone by zone, against the published alerts JSON. If a
    single centroid or pixel count disagrees, this script REFUSES to write anything (a polygon
    that is not provably the published zone is worse than no polygon at all).

  • the downstream corridor is the real D8 flow path (flood_domain.d8_targets — the same routing
    the LLOF flag was switched to in §60 4c), truncated by the empirical energy line / reach
    angle imported from rockfall_runout.BANDS (Evans & Hungr 1993). Both halves are shared
    imports, not copies, so neither can silently drift from the version that was validated.

WHAT THE THREE "CONFIDENCE" NUMBERS MEAN — they answer different questions, keep them apart:

  • detection confidence P (§24) — is this slope really moving, or is it radar noise?
  • reach band (LIKELY / POSSIBLE / MAX_SHADOW) — how far down the path could material get?
  • the map verdict (AUC vs chance, §78/§79) — is this WHOLE map better than guessing? It is
    read from the same back-test artifacts the dashboard reads, through the same identity guard,
    and is stamped on EVERY output file. A withdrawn or below-chance map still renders (you
    asked for the shape), but it renders wearing that label, in every format.

HONEST SCOPE. The corridor is a first-order screen: 80 m cells, single-direction routing, no
volume, no entrainment, no barriers or forest, no channel bulking. The reach angles are the
ROCKFALL family, which are steeper (shorter) than the reach angles reported for channelized
debris flows — so the corridor is a LOWER BOUND on the ground at risk, never an upper one.
It answers "could material physically get there", not "will it".

  docker compose run --rm insar python workflows/exposure_footprint.py
  docker compose run --rm insar python workflows/exposure_footprint.py --footprint watch
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import shapes as rio_shapes

import agentic_orchestrator as ao
import flow_routing_probe
from config import load_config
from flood_domain import d8_targets
from rockfall_runout import BANDS          # empirical energy-line angles (Evans & Hungr 1993)
from run_multistack import MERGE_DEG       # union-merge distance (~165 m)
from stacks import product_stacks
from watch_triage import collect as triage_collect, merge_rank

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CFG = load_config()
_SFX = _CFG.data_suffix
SITE = _CFG.site_name
SLUG = _CFG.aoi_slug
ALERTS_DIR = PROJECT_ROOT / "data" / f"alerts{_SFX}"
MOSAIC_ALERTS_DIR = ALERTS_DIR / "mosaic_asc"

# Corridor width: the routed path is one cell wide, which at 80 m is a hairline on a map and
# implies a precision the routing does not have. Widen by one cell either side (3 cells ~ 240 m)
# and SAY SO — this is legibility, not a modelled inundation width.
CORRIDOR_DILATE_CELLS = 1
MAX_TRACE_STEPS = 400              # 400 x 80 m = 32 km — a stop, not an expectation
SEVERITY_COLOR = {"CRITICAL": "#8b0000", "HIGH": "#ff3b30"}
# KML colours are aabbggrr (alpha first, then BLUE-green-red — not rgb).
KML_FILL = {"CRITICAL": "8b00008b", "HIGH": "8b303bff"}
KML_BAND_FILL = {"LIKELY": "990000b3", "POSSIBLE": "990d55e6", "MAX_SHADOW": "996baefd"}


# ──────────────────────────────────────────────────────────────────────────────────────
# 1. Zone footprints — re-derived from the rasters, then PROVEN to be the published zones
# ──────────────────────────────────────────────────────────────────────────────────────
def zone_pixels(stack: str, scenario: str) -> tuple[list[dict], object, object, tuple]:
    """Re-run the orchestrator's own fusion for one stack and return, per zone, the pixels it
    occupies — in the same order and with the same ids the published alerts JSON uses.

    Every threshold comes from agentic_orchestrator (imported, never re-typed): the creep
    threshold, FS_FAIL, MIN_CLUSTER_PX, the severity sort. This function only remembers WHICH
    pixels each cluster held, which is the one thing the published JSON does not record.
    """
    from scipy import ndimage

    auditor = ao.InSARAuditor(stack)
    trigger_agent = ao.MeteorologicalTrigger(stack, scenario)
    creep = auditor.creep_mask(ao.VEL_CREEP_THR)
    unstable = trigger_agent.unstable_mask(ao.FS_FAIL)
    labels, n = ndimage.label(creep & unstable)

    clusters = []
    for lab in range(1, n + 1):
        ys, xs = np.where(labels == lab)
        if ys.size < ao.MIN_CLUSTER_PX:
            continue
        clusters.append({
            "ys": ys, "xs": xs,
            # ROUNDED to 1 dp on purpose. CascadingReasoner builds its zone dicts first (with
            # `round(mean_vel, 1)`) and only then sorts, so the published order is the order of
            # the ROUNDED speeds. Sorting the full-precision means instead is invisible while
            # every zone is distinct and silently re-orders the moment two zones round to the
            # same value — 11 of Ramban's 65 watch-tier zones do. The identity gate below
            # caught exactly that; this is the fix, not a loosened assertion.
            "mean_velocity_mmyr": round(float(np.nanmean(auditor.velocity[ys, xs])), 1)})
    # Same ordering rule as CascadingReasoner.build_alerts: most negative velocity first,
    # then ids assigned 1..N. Ids must line up with the published JSON or nothing is written.
    clusters.sort(key=lambda c: c["mean_velocity_mmyr"])
    for i, c in enumerate(clusters, start=1):
        c["id"] = i
    return clusters, auditor.transform, auditor.crs, (auditor.height, auditor.width)


def verify_against_published(clusters: list[dict], published: list[dict], stack: str) -> None:
    """The gate: every polygon must be provably the zone that was published, or we write nothing.

    Compared per zone: id, centroid pixel (the orchestrator's rounded mean row/col) and pixel
    count. A mismatch means the rasters on disk no longer produce the published product — the
    honest response is to stop and say so, never to publish shapes that describe a different map.
    """
    if len(clusters) != len(published):
        raise SystemExit(
            f"[{stack}] zone count mismatch: rasters now yield {len(clusters)} zone(s), the "
            f"published alerts JSON holds {len(published)}. The polygons would describe a "
            f"DIFFERENT map than the one that was scored — refusing to write. Re-run "
            f"run_multistack.py so the products and the rasters agree, then re-run this.")
    for c, p in zip(clusters, published):
        cy, cx = float(c["ys"].mean()), float(c["xs"].mean())
        got = [int(round(cy)), int(round(cx))]
        if got != list(p["pixel_rowcol"]) or int(c["ys"].size) != int(p["n_pixels"]):
            raise SystemExit(
                f"[{stack}] zone #{c['id']} does not match the published alert "
                f"(centroid {got} vs {p['pixel_rowcol']}, {c['ys'].size} px vs "
                f"{p['n_pixels']} px) — refusing to write polygons for a map this is not.")


def rings_from_mask(mask: np.ndarray, transform, to_lonlat) -> list[list[list[float]]]:
    """Outer rings of a boolean pixel mask, as lon/lat coordinate lists (GeoJSON winding)."""
    out = []
    m8 = mask.astype(np.uint8)
    for geom, _ in rio_shapes(m8, mask=mask, transform=transform):
        for ring in geom["coordinates"][:1]:            # exterior ring only
            out.append([[round(v, 6) for v in to_lonlat.transform(x, y)] for x, y in ring])
    return out


# ──────────────────────────────────────────────────────────────────────────────────────
# 2. Downstream corridor — real D8 routing, truncated by the empirical energy line
# ──────────────────────────────────────────────────────────────────────────────────────
def trace_downstream(dem: np.ndarray, targets: np.ndarray, px_m: float,
                     sources: list[tuple[int, int]], min_angle_deg: float,
                     ) -> tuple[dict, dict]:
    """Follow the D8 receiver chain from each source cell and record, per visited cell, the
    STEEPEST energy line reaching it from any source (Fahrboeschung / reach angle):

        angle(cell) = atan[(z_source - z_cell) / straight-line horizontal distance]

    The walk from a given source stops at the first cell whose angle falls below
    `min_angle_deg` — the empirical statement that material has run out of height to travel on
    (Evans & Hungr 1993, the same criterion rockfall_runout.py screens with). It also stops at a
    pit, the array edge, nodata, or a revisited cell.

    Returns ({(r, c): best_angle_deg}, stats) — stats records the reasons walks ended, so the
    caller can say "this corridor is cut off by the window edge" instead of implying it stopped.
    """
    h, w = dem.shape
    best: dict[tuple[int, int], float] = {}
    stats = {"hit_window_edge": 0, "hit_pit": 0, "ran_out_of_energy": 0, "hit_step_cap": 0}
    for sr, sc in sources:
        if not (0 <= sr < h and 0 <= sc < w) or not np.isfinite(dem[sr, sc]):
            continue
        z0 = float(dem[sr, sc])
        r, c = sr, sc
        seen = {(r, c)}
        for step in range(MAX_TRACE_STEPS):
            t = targets[r, c]
            if t < 0:
                stats["hit_pit"] += 1
                break
            nr, nc = int(t // w), int(t % w)
            if not (0 < nr < h - 1 and 0 < nc < w - 1):
                stats["hit_window_edge"] += 1
                break
            if (nr, nc) in seen or not np.isfinite(dem[nr, nc]):
                stats["hit_pit"] += 1
                break
            dist = float(np.hypot(nr - sr, nc - sc)) * px_m
            angle = float(np.degrees(np.arctan2(z0 - float(dem[nr, nc]), max(dist, px_m))))
            if angle < min_angle_deg:
                stats["ran_out_of_energy"] += 1
                break
            prev = best.get((nr, nc))
            if prev is None or angle > prev:
                best[(nr, nc)] = angle
            seen.add((nr, nc))
            r, c = nr, nc
        else:
            stats["hit_step_cap"] += 1
    return best, stats


def corridor_masks(best: dict, shape: tuple[int, int]) -> dict[str, np.ndarray]:
    """Nested reach bands as dilated boolean masks, widest band last."""
    from scipy import ndimage

    angle = np.full(shape, np.nan, dtype=np.float32)
    for (r, c), a in best.items():
        angle[r, c] = a
    out = {}
    for name, thr in BANDS:
        m = np.isfinite(angle) & (angle >= thr)
        if not m.any():
            continue
        if CORRIDOR_DILATE_CELLS:
            m = ndimage.binary_dilation(m, iterations=CORRIDOR_DILATE_CELLS)
        out[name] = m
    return out


def band_reach_m(masks: dict[str, np.ndarray], origin_rc: tuple[int, int],
                 px_m: float) -> dict[str, int]:
    """How far each band actually gets, in metres from the zone — the number an operator reads
    ("debris could reach ~600 m below this slope"). Straight-line distance to the furthest cell
    in the band, NOT the length of the winding path, so it matches what a map ruler shows."""
    r0, c0 = origin_rc
    out = {}
    for band, m in masks.items():
        rs, cs = np.nonzero(m)
        if rs.size:
            out[band] = int(round(float(np.hypot(rs - r0, cs - c0).max()) * px_m))
    return out


def dem_window(stack: str, bounds_utm: tuple[float, float, float, float], buffer_m: float):
    """The stack DEM cropped to the zones' bounding box + a buffer, so the D8 pass runs over a
    few hundred thousand cells instead of the full ~10 M-cell frame. Downstream tracing only
    ever moves away from the zones, and a walk that leaves this window is REPORTED as truncated
    (never silently ended) — see trace_downstream's stats."""
    with rasterio.open(flow_routing_probe.stack_dem(stack)) as src:
        win = rasterio.windows.from_bounds(bounds_utm[0] - buffer_m, bounds_utm[1] - buffer_m,
                                           bounds_utm[2] + buffer_m, bounds_utm[3] + buffer_m,
                                           src.transform)
        win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        dem = src.read(1, window=win).astype(np.float64)
        dem[dem < -1000] = np.nan
        if src.nodata is not None:
            dem[dem == src.nodata] = np.nan
        return dem, src.window_transform(win), src.crs, abs(src.transform.a)


# ──────────────────────────────────────────────────────────────────────────────────────
# 3. Ranking + provenance (all borrowed from the artifacts that already publish them)
# ──────────────────────────────────────────────────────────────────────────────────────
def ranked_union(stacks: list[str], scenario: str) -> list[dict]:
    """The union zones ranked worst-first by triage priority = (1-m*) x P — computed by
    watch_triage's own functions, so this layer and the dashboard's top-5 list can never
    disagree about the order."""
    rows = triage_collect(stacks, scenario)
    return merge_rank(rows, MERGE_DEG) if rows else []


def match_union(ranked: list[dict], lon: float, lat: float) -> tuple[int | None, dict | None]:
    """The union zone a per-look zone belongs to: nearest centroid inside the SAME merge
    distance the union itself used. Returns (1-based rank, zone) or (None, None)."""
    best = None
    for i, z in enumerate(ranked, 1):
        if abs(z["lat"] - lat) < MERGE_DEG and abs(z["lon"] - lon) < MERGE_DEG:
            d = abs(z["lat"] - lat) + abs(z["lon"] - lon)
            if best is None or d < best[0]:
                best = (d, i, z)
    return (best[1], best[2]) if best else (None, None)


def active_zone_keys(scenario: str, as_of: str | None) -> tuple[set, dict]:
    """Which operational zones are LIVE on the as-of day, as (stack, id) keys.

    The rule is not re-derived here: per_zone_gate.py sorts its zones by activation threshold
    m*_eff ascending and publishes how many are active; the active set is therefore that
    ranking's prefix — exactly the slice operational_alarm.per_zone_live takes for the
    dashboard's WHICH ZONES table. Returns (keys, context) with context empty when the gate
    has not run (absence is reported, never silently rendered as "none active").

    Only the OPERATIONAL footprint has a live gate. Zone ids are per-footprint, so joining a
    watch-footprint zone to this operational table on (stack, id) would silently attach the
    wrong zone's live state — the answer for any other footprint is "not applicable", said
    out loud, never a plausible-looking false.
    """
    if scenario != "operational":
        return set(), {"state": "not_applicable",
                       "reason": ("the per-zone live gate runs on the operational footprint "
                                  "only (§19); this is the '%s' footprint" % scenario)}
    vf = ALERTS_DIR / "per_zone_vulnerability.csv"
    jf = ALERTS_DIR / "per_zone_vulnerability.json"
    if not (vf.exists() and jf.exists()):
        return set(), {}
    rep = json.loads(jf.read_text(encoding="utf-8"))
    if as_of and rep.get("as_of") != as_of:
        return set(), {"as_of": rep.get("as_of"), "requested_as_of": as_of,
                       "state": "gate_not_run_for_this_day"}
    rows = list(csv.DictReader(vf.open(encoding="utf-8")))       # already m*_eff-ascending
    n_active = int(rep.get("as_of_n_active") or 0)
    keys = {(r["stack"], int(r["id"])) for r in rows[:n_active]}
    return keys, {"as_of": rep.get("as_of"), "saturation_m": rep.get("as_of_saturation_m"),
                  "regional_level": rep.get("as_of_regional_level"),
                  "n_active": n_active, "n_total": len(rows)}


def _plain(html: str) -> str:
    """Strip the markup out of a shared dashboard string so it can go into a KML balloon, a
    console line or a .md table. The VERDICT ITSELF is never re-derived here — it comes from
    operational_alarm._chance_verdict, which computes it from the AUC (§79); only its emphasis
    tags are removed, so the wording on the map can never drift from the wording on the page."""
    import re

    return re.sub(r"<[^>]+>", "", html)


def map_verdict(scenario: str) -> dict:
    """The whole map's standing, read through operational_alarm's own loader so this layer
    inherits its identity guard (§79: a stale overlay must not mask a fresher, worse score) and
    its DERIVED chance verdict (§79: 'beats chance' was once a string literal beside AUC 0.326).
    """
    import operational_alarm as oa

    tier = oa.load_tier(MOSAIC_ALERTS_DIR / f"alerts_{scenario}.json")
    if tier is None:
        return {"state": "no_footprint", "text": "no footprint file for this scenario"}
    sz, nz = tier.get("scored_zones"), tier.get("n_zones")
    if not isinstance(tier.get("auc"), (int, float)):
        return {"state": "never_scored", "auc": None, "n_zones": nz,
                "text": ("This site has no local back-test — the map has never been scored "
                         "here. Treat it as unvalidated, not as validated-and-fine.")}
    if isinstance(sz, int) and sz != nz:
        return {"state": "not_measured", "auc": tier["auc"], "n_zones": nz, "scored_zones": sz,
                "text": (f"NOT MEASURED for this footprint: the last back-test scored a "
                         f"{sz}-zone map (AUC {tier['auc']:.3f}); this map has {nz} zone(s), so "
                         f"that score does not describe what you are looking at.")}
    verdict = _plain(oa._chance_verdict(tier["auc"]))
    return {"state": "scored", "auc": tier["auc"], "n_zones": nz, "verdict": verdict,
            "recall": tier.get("recall"),
            "text": (f"Scored against this site's inventory: AUC {tier['auc']:.3f} "
                     f"({verdict}), recall {tier.get('recall')} @2 km.")}


# ──────────────────────────────────────────────────────────────────────────────────────
# 4. Writers
# ──────────────────────────────────────────────────────────────────────────────────────
def _headline(verdict: dict) -> str:
    """One plain sentence about whether this layer should be acted on — computed from the
    verdict, never typed as a literal beside a number that might contradict it."""
    if verdict["state"] == "scored" and verdict.get("verdict") == "beats chance":
        return ("This map scores better than chance at this site: use it to PRIORITISE "
                "inspections, not to declare anywhere safe.")
    if verdict["state"] == "scored" and verdict["auc"] > 0.45:
        # NOT the same failure as below-chance, and it must not wear the same words. A map at
        # ~chance has no MEASURED skill at placing zones, but a high-recall tier can still be
        # worth walking — its value is breadth, and the honest sentence says which is which.
        rec = verdict.get("recall")
        rec_txt = (f" It does catch {rec:.0%} of this site's documented failures within 2 km — "
                   f"breadth, not precision." if isinstance(rec, (int, float)) else "")
        return (f"NO MEASURED SKILL AT PLACING ZONES: this map scores {verdict['verdict']} at "
                f"this site (AUC {verdict['auc']:.3f}), so its ORDER carries no demonstrated "
                f"advantage over picking slopes at random.{rec_txt} Read it as a monitoring "
                f"net, not a ranking.")
    if verdict["state"] == "scored":
        return (f"WITHDRAWN AS A RANKING: this map scores {verdict['verdict']} at this site "
                f"(AUC {verdict['auc']:.3f}). The shapes show what the current inputs flag; "
                f"they must NOT be used to prioritise anything.")
    if verdict["state"] == "not_measured":
        return ("NOT MEASURED: the map moved since it was last scored, so no skill claim "
                "applies to these shapes.")
    if verdict["state"] == "never_scored":
        return ("UNVALIDATED at this site: no local inventory has ever scored this map. "
                "The shapes are a hypothesis, not a ranking.")
    return "No footprint exists for this scenario."


def write_geojson(path: Path, features: list[dict], meta: dict) -> None:
    path.write_text(json.dumps({"type": "FeatureCollection", "properties": meta,
                                "features": features}, indent=1), encoding="utf-8")


def _by_vulnerability(zones: list[dict]) -> list[dict]:
    """Most fragile first — the per-zone gate's own order (lowest critical saturation m*
    fires first). Distinct from triage priority; see the note in build()."""
    return sorted(zones, key=lambda z: (z.get("vulnerability_rank") or 1e9))


def _kml_poly(ring: list[list[float]], fill: str, line: str) -> str:
    coords = " ".join(f"{lo:.6f},{la:.6f},0" for lo, la in ring)
    return (f"<Style><PolyStyle><color>{fill}</color></PolyStyle>"
            f"<LineStyle><color>{line}</color><width>2</width></LineStyle></Style>"
            f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{coords}"
            f"</coordinates></LinearRing></outerBoundaryIs></Polygon>")


def write_kml(path: Path, zones: list[dict], meta: dict) -> None:
    """Google-Earth layer: zone shapes, downstream corridors, and the top-5 triage pins.

    Every text value is XML-escaped. The document description carries the map verdict, so the
    file cannot be opened without the reader seeing what the layer is and is not.
    """
    e = xml_escape
    doc = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
           f"<name>{e(SITE)} — affected-area layer ({e(meta['footprint'])})</name>",
           f"<description>{e(meta['headline'])} {e(meta['verdict']['text'])} "
           f"Generated {e(meta['generated_utc'])}. {e(meta['scope_caveat'])}</description>"]

    doc.append(f"<Folder><name>Hazard zones — {len(zones)} shape(s), ranked by vulnerability "
               f"(fails at the least rain first)</name>")
    for z in _by_vulnerability(zones):
        desc = ("vulnerability rank {vrank} · triage rank {rank} of {tot} · priority {pri} "
                "· {sev}\n"
                "{lat:.5f}N, {lon:.5f}E · {area} km²\n"
                "fails at wetness m*={ms} ({tier})\n"
                "measured creep {creep} mm/yr · detection confidence {conf} · seen by "
                "{looks} radar look(s)\nlive today: {live}\n"
                "debris could reach ~{reach} m below (outer bound of this screen)").format(
            vrank=z.get("vulnerability_rank"),
            rank=z["triage_rank"], tot=meta["n_union_zones"], pri=z["triage_priority"],
            sev=z["severity"], lat=z["lat"], lon=z["lon"], area=z["area_km2"],
            ms=z["m_star"], tier=z["vulnerability_tier"], creep=z["creep_mmyr"],
            conf=z["detection_confidence"], looks=z["n_looks"], live=z["active_today"],
            reach=max(z["downstream_reach_m"].values()) if z["downstream_reach_m"] else "—")
        name = "V{vrank} · T{rank} {sev} ({stack})".format(
            vrank=z.get("vulnerability_rank"), rank=z["triage_rank"], sev=z["severity"],
            stack=z["stack"])
        doc.append(f"<Placemark><name>{e(name)}</name>"
                   f"<description>{e(desc)}</description>")
        fill = KML_FILL.get(z["severity"], KML_FILL["HIGH"])
        doc.append(_kml_poly(z["rings"][0], fill, "ff" + fill[2:]) if z["rings"] else
                   "<Point><coordinates>"
                   f"{z['lon']:.6f},{z['lat']:.6f},0</coordinates></Point>")
        doc.append("</Placemark>")
    doc.append("</Folder>")

    doc.append("<Folder><name>Potential downstream path (first-order screen — a LOWER bound)"
               "</name>")
    for z in zones:
        for band, rings in z["downstream"].items():
            name = "zone #{rank} — {band}".format(rank=z["triage_rank"], band=band)
            for ring in rings:
                doc.append(f"<Placemark><name>{e(name)}</name>"
                           f"<description>{e(meta['band_note'][band])}</description>"
                           + _kml_poly(ring, KML_BAND_FILL[band],
                                       "ff" + KML_BAND_FILL[band][2:]) + "</Placemark>")
    doc.append("</Folder>")

    doc.append("<Folder><name>Top 5 by triage priority (read these first)</name>")
    for z in meta["top5"]:
        name = "{rank}. priority {pri}".format(rank=z["rank"], pri=z["priority"])
        desc = ("{lat:.5f}N, {lon:.5f}E — fragility m*={ms}, detection confidence {conf}, "
                "{looks} radar look(s)").format(lat=z["lat"], lon=z["lon"], ms=z["m_star"],
                                                conf=z["detection_confidence"],
                                                looks=z["n_looks"])
        doc.append(f"<Placemark><name>{e(name)}</name>"
                   f"<description>{e(desc)}</description>"
                   f"<Point><coordinates>{z['lon']:.6f},{z['lat']:.6f},0</coordinates></Point>"
                   f"</Placemark>")
    doc.append("</Folder></Document></kml>")
    path.write_text("\n".join(doc), encoding="utf-8")


def _live_line(meta: dict) -> str:
    """One sentence about the live/active state — with the three states kept apart: gated and
    counted, not gated yet, and not applicable to this footprint (§70/§79)."""
    a = meta["active"]
    if not a:
        return "- Live state: the per-zone gate has not run for this site — **not measured**."
    if "state" in a:
        return f"- Live state: **not applicable** — {a.get('reason', a['state'])}."
    return (f"- Live as of **{a['as_of']}**: **{a['n_active']} of {a['n_total']}** zones active "
            f"(regional gate {a['regional_level']}, soil wetness m={a['saturation_m']}).")


def write_md(path: Path, zones: list[dict], meta: dict) -> None:
    v = meta["verdict"]
    lines = [f"# Affected-area layer — {SITE} ({meta['footprint']} footprint)", "",
             f"**{meta['headline']}**", "",
             f"- Map standing: {v['text']}",
             f"- {meta['n_union_zones']} zone(s) on the map, drawn as {len(zones)} shape(s) "
             f"(one per radar look that sees them).",
             _live_line(meta), "",
             "## Zones ranked by VULNERABILITY (fails at the least rain first)", "",
             "_Vulnerability answers “which slope tips first as it gets wetter” (lowest m\\*). "
             "Triage priority (the next section) answers a different question — “which slope is "
             "BOTH fragile AND confidently moving”. A fragile zone whose motion is probably "
             "noise ranks high here and low there._", "",
             "| # | triage rank | location (lat, lon) | fails at m* | tier | creep mm/yr | "
             "confidence | priority | live today | debris could reach |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for z in _by_vulnerability(zones):
        # The OUTER bound of the screen (the widest band = the lowest reach angle present).
        r = z["downstream_reach_m"]
        reach = (f"~{max(r.values())} m below" if r else "—")
        lines.append(
            f"| {z.get('vulnerability_rank')} | {z['triage_rank']} | "
            f"{z['lat']:.5f}, {z['lon']:.5f} | **{z['m_star']}** | "
            f"{z['vulnerability_tier']} | {z['creep_mmyr']} | {z['detection_confidence']} | "
            f"{z['triage_priority']} | {z['active_today']} | {reach} |")
    lines += ["", "## Top 5 by triage priority", ""]
    for z in meta["top5"]:
        lines.append(f"{z['rank']}. **{z['lat']:.5f}, {z['lon']:.5f}** — priority "
                     f"{z['priority']} (fragility m*={z['m_star']}, detection "
                     f"confidence {z['detection_confidence']}, {z['n_looks']} look(s))")
    lines += ["", "---", "", f"_{meta['scope_caveat']}_", ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────────────────────
# 5. Driver
# ──────────────────────────────────────────────────────────────────────────────────────
def build(scenario: str, stacks: list[str], as_of: str | None, window_km: float,
          min_angle: float) -> dict:
    ranked = ranked_union(stacks, scenario)
    active_keys, active_ctx = active_zone_keys(scenario, as_of)
    verdict = map_verdict(scenario)

    zones: list[dict] = []
    skipped: dict[str, str] = {}
    for stack in stacks:
        af = ALERTS_DIR / stack / f"alerts_{scenario}.json"
        if not af.exists():
            skipped[stack] = "not_applicable: no per-look alerts file for this scenario"
            continue
        published = json.loads(af.read_text(encoding="utf-8")).get("alerts", [])
        clusters, transform, crs, _shape = zone_pixels(stack, scenario)
        verify_against_published(clusters, published, stack)
        if not clusters:
            skipped[stack] = "no zones in this look's footprint"
            continue
        to_lonlat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

        # One DEM window per stack, covering every zone in it.
        xs_all, ys_all = [], []
        for c in clusters:
            for yy, xx in ((c["ys"].min(), c["xs"].min()), (c["ys"].max(), c["xs"].max())):
                x, y = transform * (float(xx) + 0.5, float(yy) + 0.5)
                xs_all.append(x); ys_all.append(y)
        dem, dem_tf, dem_crs, px_m = dem_window(
            stack, (min(xs_all), min(ys_all), max(xs_all), max(ys_all)), window_km * 1000)
        targets = d8_targets(dem)

        for c, p in zip(clusters, published):
            mask = np.zeros(_shape, bool)
            mask[c["ys"], c["xs"]] = True
            rings = rings_from_mask(mask, transform, to_lonlat)
            lon, lat = p["centroid_lonlat"]

            # Zone pixels -> DEM-window cells (same CRS + 80 m grid; mapped through the
            # transforms rather than assumed, so a future regrid fails loudly instead of
            # silently tracing from the wrong place).
            srcs = []
            for yy, xx in zip(c["ys"], c["xs"]):
                x, y = transform * (float(xx) + 0.5, float(yy) + 0.5)
                rr, cc = rasterio.transform.rowcol(dem_tf, x, y)
                srcs.append((int(rr), int(cc)))
            best, trace_stats = trace_downstream(dem, targets, px_m, srcs, min_angle)
            to_ll_dem = Transformer.from_crs(dem_crs, "EPSG:4326", always_xy=True)
            masks = corridor_masks(best, dem.shape)
            downstream = {band: rings_from_mask(m, dem_tf, to_ll_dem)
                          for band, m in masks.items()}
            origin = (int(round(np.mean([s[0] for s in srcs]))),
                      int(round(np.mean([s[1] for s in srcs]))))
            reach_m = band_reach_m(masks, origin, px_m)

            rank, u = match_union(ranked, lon, lat)
            zones.append({
                "stack": stack, "zone_id": p["id"], "severity": p["severity"],
                "lon": lon, "lat": lat, "area_km2": p["area_km2"],
                "n_pixels": p["n_pixels"], "creep_mmyr": p["mean_velocity_mmyr"],
                "mean_slope_deg": p["mean_slope_deg"], "mean_fs": p["mean_fs"],
                "trigger_reason": p["trigger_reason"],
                "reaches_drainage": bool(p["downstream_risk"]["llof_potential"]),
                "drainage_reason": p["downstream_risk"]["reason"],
                "m_star": u["m_star"] if u else None,
                "vulnerability_tier": u["vulnerability_tier"] if u else None,
                "detection_confidence": u["detection_confidence"] if u else None,
                "triage_priority": u["priority"] if u else None,
                "triage_rank": rank, "n_looks": u["n_looks"] if u else 1,
                "active_today": ((stack, p["id"]) in active_keys
                                 if active_ctx and "state" not in active_ctx
                                 else (active_ctx.get("state") if active_ctx
                                       else "not gated (per-zone gate has not run for "
                                            "this day)")),
                "rings": rings, "downstream": downstream,
                "downstream_reach_m": reach_m, "downstream_trace": trace_stats,
            })
    # TWO different orders, both asked for and NOT the same question — keep them labelled:
    #   vulnerability = m* ascending  ("which slope tips at the least rain", the §19 gate order)
    #   triage priority = (1-m*)xP    ("which slope is BOTH fragile and confidently moving", §25)
    # A fragile zone whose motion is probably noise ranks high on the first and low on the
    # second; publishing one under the other's name would quietly change what is being claimed.
    for rank, z in enumerate(sorted(zones, key=lambda z: (z["m_star"] is None,
                                                          z["m_star"] or 0)), 1):
        z["vulnerability_rank"] = rank
    return {"zones": zones, "ranked": ranked, "active": active_ctx or None,
            "verdict": verdict, "skipped": skipped}


def to_features(zones: list[dict], meta: dict) -> list[dict]:
    feats = []
    for z in zones:
        props = {k: v for k, v in z.items() if k not in ("rings", "downstream")}
        props["kind"] = "hazard_zone"
        props["map_verdict"] = meta["verdict"]["state"]
        if z["rings"]:
            feats.append({"type": "Feature", "properties": props,
                          "geometry": {"type": "MultiPolygon",
                                       "coordinates": [[r] for r in z["rings"]]}})
        for band, rings in z["downstream"].items():
            if not rings:
                continue
            feats.append({"type": "Feature", "geometry": {
                "type": "MultiPolygon", "coordinates": [[r] for r in rings]},
                "properties": {"kind": "downstream_path", "reach_band": band,
                               "reach_angle_min_deg": dict(BANDS)[band],
                               "of_zone_rank": z["triage_rank"], "of_zone_stack": z["stack"],
                               "of_zone_id": z["zone_id"],
                               "note": meta["band_note"][band]}})
    return feats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--footprint", default="operational",
                    help="Which published footprint to draw (default: operational).")
    ap.add_argument("--stacks", nargs="*", default=None,
                    help="Radar looks to draw (default: the footprint's own source_stacks).")
    ap.add_argument("--as-of", default=None,
                    help="Day for the live/active flags (default: whatever per_zone_gate "
                         "last published).")
    ap.add_argument("--window-km", type=float, default=10.0,
                    help="DEM window around the zones for downstream routing (default 10 km).")
    ap.add_argument("--min-reach-angle-deg", type=float, default=min(t for _, t in BANDS),
                    help="Outer energy-line angle: LOWER = longer runout (default: the "
                         "rockfall screen's widest band).")
    args = ap.parse_args(argv)

    stacks = args.stacks or product_stacks(args.footprint)
    res = build(args.footprint, stacks, args.as_of, args.window_km, args.min_reach_angle_deg)
    zones, verdict = res["zones"], res["verdict"]

    # The top-5 comes from the UNION ranking (watch_triage's own order), not from the shape
    # list: one place seen by two radar looks is two shapes but ONE zone, and numbering the
    # shapes would print rank 2 twice and silently drop a real zone off the bottom of the five.
    top5 = [{"rank": i, "lat": z["lat"], "lon": z["lon"], "priority": z["priority"],
             "m_star": z["m_star"], "vulnerability_tier": z["vulnerability_tier"],
             "detection_confidence": z["detection_confidence"], "n_looks": z["n_looks"],
             "strongest_creep_mmyr": z["strongest_creep_mmyr"]}
            for i, z in enumerate(res["ranked"][:5], 1)]

    meta = {
        "site": SITE, "aoi": SLUG, "footprint": args.footprint, "stacks": stacks,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "n_union_zones": len(res["ranked"]), "n_shapes": len(zones), "top5": top5,
        "as_of": (res["active"] or {}).get("as_of"),
        "active": res["active"], "verdict": verdict, "headline": _headline(verdict),
        "skipped_looks": res["skipped"],
        "min_reach_angle_deg": args.min_reach_angle_deg,
        "corridor_width_cells": 1 + 2 * CORRIDOR_DILATE_CELLS,
        "method": ("zone shapes = the published alert clusters re-derived from the same rasters "
                   "and verified pixel-for-pixel against alerts_<footprint>.json; downstream = "
                   "D8 flow routing (flood_domain.d8_targets, the routing adopted in §60 4c) "
                   "truncated by the empirical energy line / reach angle "
                   "(rockfall_runout.BANDS, Evans & Hungr 1993)"),
        "band_note": {
            "LIKELY": "Material would very likely reach here if this slope failed "
                      "(energy line >= 32 deg).",
            "POSSIBLE": "Material could reach here (energy line >= 27.5 deg).",
            "MAX_SHADOW": "Outer bound of this screen (energy line >= 22 deg) — real "
                          "channelized debris flows travel further than this.",
        },
        "scope_caveat": (
            "First-order screen, not a runout simulation: 80 m cells, single-direction (D8) "
            "routing, no volume, entrainment, bulking, barriers or forest. The corridor is "
            "drawn 3 cells (~240 m) wide for legibility, which is NOT a modelled inundation "
            "width. The reach angles are the rockfall family and are steeper than reported "
            "debris-flow reach angles, so this corridor is a LOWER bound on the ground at "
            "risk. An unmapped slope is not a safe slope. Decision support, not a warning "
            "system."),
    }

    MOSAIC_ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    base = MOSAIC_ALERTS_DIR / f"exposure_{args.footprint}"
    write_geojson(base.with_suffix(".geojson"), to_features(zones, meta), meta)
    write_kml(base.with_suffix(".kml"), zones, meta)
    write_md(base.with_suffix(".md"), zones, meta)
    report = dict(meta)
    report["zones"] = [{k: v for k, v in z.items() if k != "rings"} for z in zones]
    report["top5_by_triage_priority"] = top5
    report["zones_ranked_by_triage_priority"] = res["ranked"]
    report["zones_ranked_by_vulnerability"] = sorted(
        res["ranked"], key=lambda z: z["m_star"])
    for z in report["zones"]:
        z["downstream"] = {b: len(r) for b, r in z["downstream"].items()}
    base.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"{SITE} · footprint '{args.footprint}': {len(zones)} zone shape(s) across "
          f"{len(stacks)} look(s); {meta['n_union_zones']} union zone(s) ranked.")
    print(f"  map standing: {verdict['text']}")
    if verdict["state"] != "scored" or verdict.get("verdict") != "beats chance":
        print(f"  !! {meta['headline']}")
    if res["skipped"]:
        for k, why in res["skipped"].items():
            print(f"  skipped {k}: {why}")
    for z in top5:
        print(f"    #{z['rank']}  {z['lat']:.5f}, {z['lon']:.5f}  "
              f"priority={z['priority']}  m*={z['m_star']}  "
              f"P={z['detection_confidence']}  looks={z['n_looks']}")
    print(f"  -> {base.with_suffix('.geojson')} , .kml , .json , .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

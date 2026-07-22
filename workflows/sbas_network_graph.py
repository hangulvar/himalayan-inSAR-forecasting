#!/usr/bin/env python
"""
sbas_network_graph.py — SBAS Design Matrix / Network Connectivity Check.

For each of the 5 stacks (direction/path/frame), this script:

  1. Reads the per-product KEEP / CONCERN / QUARANTINE label from
     data/qa_masks/_quarantine_list.csv.
  2. Parses the two acquisition dates from each HyP3 product name.
  3. Fetches the perpendicular baseline for every acquisition via
     asf_search.baseline_search (cached on disk so re-runs are instant).
  4. Builds a graph: nodes = unique acquisitions, edges = pairs.
  5. Runs union-find on the KEEP-only edge set to identify connected
     components.  If the graph is disconnected, the script flags which
     CONCERN edges would bridge it back together — those are the candidates
     to "rescue" before the velocity inversion.
  6. Renders the classic InSAR baseline diagram per stack into
     data/qa_masks/network_graphs/<stack>.svg.

NOTE: We deliberately do NOT use matplotlib. In this env (numpy 2.2 +
matplotlib 3.10 + Windows MKL), matplotlib's draw pipeline crashes with
Windows fatal exception 0xC06D007F inside patches.draw — even on a trivial
3-point plot. Rather than fight the binary stack, we emit standalone SVG
from the stdlib. SVG is the InSAR community's standard format anyway
(vector, scriptable, prints cleanly, opens in any browser).

The script answers the question: *can we run a standard least-squares SBAS
inversion on this graph, or do we need SVD pseudoinverse / pair rescue?*
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from config import load_config
from stacks import label_from_job_name

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QA_DIR = PROJECT_ROOT / "data" / "qa_masks"
QUARANTINE_CSV = QA_DIR / "_quarantine_list.csv"
# Auto-selected minimum-set bridging pairs consumed by apply_connectivity_rescues.py.
RESCUE_RECOMMENDATIONS = QA_DIR / "_rescue_recommendations.json"
# Note the leading underscore — keeps the directory from being treated as a
# masked-product folder by tests/test_plumbing.py and other walkers.
OUT_DIR = QA_DIR / "_network_graphs"
REPORT_MD = OUT_DIR / "_connectivity_report.md"
INDEX_HTML = OUT_DIR / "index.html"
BPERP_CACHE = OUT_DIR / "_bperp_cache.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("sbas_network_graph")


def parse_pair_dates(product_name: str) -> tuple[datetime, datetime] | None:
    """Extract (reference_date, secondary_date) from a HyP3 product name.
    S1[A-D][A-D]: accept cross-unit pairs (S1AD…) from the S1 handover (§56/§61)."""
    m = re.search(r"S1[A-D][A-D]_(\d{8})T(\d{6})_(\d{8})T(\d{6})_", product_name)
    if not m:
        return None
    fmt = "%Y%m%dT%H%M%S"
    return (
        datetime.strptime(m.group(1) + "T" + m.group(2), fmt),
        datetime.strptime(m.group(3) + "T" + m.group(4), fmt),
    )


# ------------------------------------------------------------------------------
# Perpendicular baseline lookup via asf_search (cached)
# ------------------------------------------------------------------------------
def fetch_bperp_per_stack(stack_acq_names: dict[str, list[str]]) -> dict[str, dict[str, float]]:
    """For each stack, fetch perpendicular baselines for all SLC acquisitions.

    Returns {stack_label: {scene_name: bperp_m}} — bperp relative to that
    stack's reference. One asf_search call per stack, then cached to disk.
    """
    if BPERP_CACHE.exists():
        cached = json.loads(BPERP_CACHE.read_text())
        if set(cached) == set(stack_acq_names):
            logger.info(f"Bperp cache hit: {BPERP_CACHE}")
            return cached
        logger.info("Bperp cache exists but stack set changed; refetching.")

    import asf_search as asf

    result: dict[str, dict[str, float]] = {}
    for stack, granules in stack_acq_names.items():
        if not granules:
            result[stack] = {}
            continue
        ref_name = sorted(granules)[0]
        logger.info(f"baseline_search reference for {stack}: {ref_name}")
        try:
            ref_results = asf.granule_search([ref_name])
            if len(ref_results) == 0:
                logger.warning(f"  reference {ref_name} not found in catalog")
                result[stack] = {}
                continue
            ref_product = ref_results[0]
            stack_results = asf.baseline_search.stack_from_product(ref_product)
        except Exception as e:
            logger.warning(f"  baseline lookup failed: {e}")
            result[stack] = {}
            continue

        bperp_map: dict[str, float] = {ref_name: 0.0}
        for product in stack_results:
            name = product.properties.get("sceneName")
            bperp = product.properties.get("perpendicularBaseline")
            if name and bperp is not None:
                bperp_map[name] = float(bperp)
        result[stack] = bperp_map
        logger.info(f"  {stack}: got Bperp for {len(bperp_map)} scenes")

    BPERP_CACHE.parent.mkdir(parents=True, exist_ok=True)
    BPERP_CACHE.write_text(json.dumps(result, indent=2))
    logger.info(f"Wrote Bperp cache: {BPERP_CACHE}")
    return result


def fetch_granule_names_per_stack(job_name_prefix: str) -> dict[str, list[str]]:
    """Pull SLC granule names from HyP3 job_parameters['granules']."""
    import hyp3_sdk as sdk

    hyp3 = sdk.HyP3()
    jobs = [j for j in hyp3.find_jobs() if j.name and j.name.startswith(job_name_prefix)]
    logger.info(f"Pulled {len(jobs)} HyP3 jobs to extract granule names.")

    stack_to_granules: dict[str, set[str]] = defaultdict(set)
    for job in jobs:
        if not job.files:
            continue
        stack = label_from_job_name(job.name, job_name_prefix)
        if stack == "unknown":
            continue
        granules = job.job_parameters.get("granules", []) if job.job_parameters else []
        for g in granules:
            stack_to_granules[stack].add(g)

    return {s: sorted(g) for s, g in stack_to_granules.items()}


# ------------------------------------------------------------------------------
# Union-find for connected components
# ------------------------------------------------------------------------------
class UnionFind:
    def __init__(self, items):
        self.parent: dict = {x: x for x in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[rx] = ry

    def components(self) -> list[list]:
        groups: dict = defaultdict(list)
        for x in self.parent:
            groups[self.find(x)].append(x)
        return sorted(groups.values(), key=lambda c: min(c))


# ------------------------------------------------------------------------------
# SVG rendering
# ------------------------------------------------------------------------------
COLOR = {"KEEP": "#2ca02c", "CONCERN": "#ff9f1c", "QUARANTINE": "#d62728"}
OPACITY = {"KEEP": 0.85, "CONCERN": 0.75, "QUARANTINE": 0.18}
EDGE_WIDTH = {"KEEP": 2.0, "CONCERN": 1.8, "QUARANTINE": 0.7}

SVG_W, SVG_H = 1100, 500
MARGIN = {"left": 70, "right": 30, "top": 70, "bottom": 60}
PLOT_W = SVG_W - MARGIN["left"] - MARGIN["right"]
PLOT_H = SVG_H - MARGIN["top"] - MARGIN["bottom"]


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_svg(
    stack: str,
    pair_rows: list[dict],
    nodes: list[datetime],
    bperp_by_date: dict[datetime, float],
    comps_keep: list[list[datetime]],
    n_keep: int,
    n_concern: int,
    n_quar: int,
) -> str:
    """Return a complete <svg>...</svg> string for one stack's network."""
    xs_dt = sorted(nodes)
    xs_ord = [d.toordinal() for d in xs_dt]
    x_min, x_max = min(xs_ord), max(xs_ord)
    x_span = max(x_max - x_min, 1)

    ys = [bperp_by_date.get(d, 0.0) for d in xs_dt] or [0.0]
    y_min, y_max = min(ys), max(ys)
    y_pad = max(10.0, (y_max - y_min) * 0.12)
    y_min, y_max = y_min - y_pad, y_max + y_pad
    y_span = max(y_max - y_min, 1.0)

    def x_to_px(d: datetime) -> float:
        return MARGIN["left"] + (d.toordinal() - x_min) / x_span * PLOT_W

    def y_to_px(b: float) -> float:
        return MARGIN["top"] + (1 - (b - y_min) / y_span) * PLOT_H

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {SVG_W} {SVG_H}" '
        f'style="background:#fafafa;font-family:Segoe UI,Arial,sans-serif;font-size:11px">'
    ]

    # Title block
    connected = len(comps_keep) == 1
    connectivity = (
        "CONNECTED via KEEP edges" if connected
        else f"DISCONNECTED — {len(comps_keep)} islands in KEEP-only graph"
    )
    parts.append(
        f'<text x="{SVG_W//2}" y="26" text-anchor="middle" '
        f'font-size="15" font-weight="bold">{_xml_escape(stack)}</text>'
    )
    parts.append(
        f'<text x="{SVG_W//2}" y="46" text-anchor="middle" font-size="11" fill="#444">'
        f'{len(nodes)} scenes · KEEP={n_keep} · CONCERN={n_concern} · '
        f'QUARANTINE={n_quar} · '
        f'<tspan font-weight="bold" fill="{"#1a8a1a" if connected else "#a00000"}">'
        f'{_xml_escape(connectivity)}</tspan></text>'
    )

    # Plot box
    parts.append(
        f'<rect x="{MARGIN["left"]}" y="{MARGIN["top"]}" '
        f'width="{PLOT_W}" height="{PLOT_H}" '
        f'fill="white" stroke="#888" stroke-width="1"/>'
    )

    # X-axis: monthly gridlines + labels
    cur = datetime(xs_dt[0].year, xs_dt[0].month, 1)
    last = xs_dt[-1]
    months: list[datetime] = []
    while cur <= last:
        months.append(cur)
        cur = (datetime(cur.year + 1, 1, 1) if cur.month == 12
               else datetime(cur.year, cur.month + 1, 1))
    for m in months:
        if m.toordinal() < x_min or m.toordinal() > x_max:
            continue
        px = x_to_px(m)
        parts.append(
            f'<line x1="{px:.1f}" y1="{MARGIN["top"]}" '
            f'x2="{px:.1f}" y2="{MARGIN["top"]+PLOT_H}" '
            f'stroke="#e0e0e0" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{px:.1f}" y="{MARGIN["top"]+PLOT_H+16}" '
            f'text-anchor="middle" font-size="10" fill="#555">'
            f'{m.strftime("%Y-%m")}</text>'
        )

    # Y-axis: 5 ticks
    for i in range(5):
        bp = y_min + (i / 4) * y_span
        py = y_to_px(bp)
        parts.append(
            f'<line x1="{MARGIN["left"]}" y1="{py:.1f}" '
            f'x2="{MARGIN["left"]+PLOT_W}" y2="{py:.1f}" '
            f'stroke="#e0e0e0" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{MARGIN["left"]-8}" y="{py:.1f}" '
            f'text-anchor="end" dy="3" font-size="10" fill="#555">'
            f'{bp:.0f}</text>'
        )

    # Axis titles
    parts.append(
        f'<text x="{MARGIN["left"]+PLOT_W//2}" y="{SVG_H-12}" '
        f'text-anchor="middle" font-size="11" fill="#333">Acquisition date</text>'
    )
    parts.append(
        f'<text transform="translate(20,{MARGIN["top"]+PLOT_H//2}) rotate(-90)" '
        f'text-anchor="middle" font-size="11" fill="#333">'
        f'Perpendicular baseline (m)</text>'
    )

    # Edges: paint QUARANTINE first (background), then CONCERN, then KEEP on top
    for decision in ("QUARANTINE", "CONCERN", "KEEP"):
        for r in pair_rows:
            if r["decision"] != decision:
                continue
            x1 = x_to_px(r["ref_date"])
            y1 = y_to_px(bperp_by_date.get(r["ref_date"], 0.0))
            x2 = x_to_px(r["sec_date"])
            y2 = y_to_px(bperp_by_date.get(r["sec_date"], 0.0))
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
                f'x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{COLOR[decision]}" '
                f'stroke-width="{EDGE_WIDTH[decision]}" '
                f'stroke-opacity="{OPACITY[decision]}"/>'
            )

    # Acquisition nodes
    for d in xs_dt:
        cx = x_to_px(d)
        cy = y_to_px(bperp_by_date.get(d, 0.0))
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" '
            f'fill="#202020" stroke="white" stroke-width="1.2">'
            f'<title>{d.strftime("%Y-%m-%d")} · Bperp={bperp_by_date.get(d,0.0):.1f} m</title>'
            f'</circle>'
        )

    # Island annotations (only if disconnected)
    if not connected:
        for ci, comp in enumerate(comps_keep):
            label_date = min(comp)
            cx = x_to_px(label_date)
            cy = y_to_px(bperp_by_date.get(label_date, 0.0))
            parts.append(
                f'<text x="{cx+10:.1f}" y="{cy-10:.1f}" '
                f'font-size="11" font-weight="bold" fill="#7a0000">'
                f'island #{ci+1} ({len(comp)} scenes)</text>'
            )

    # Inline legend (top-right of plot area)
    lx = MARGIN["left"] + PLOT_W - 240
    ly = MARGIN["top"] + 12
    parts.append(
        f'<rect x="{lx-8}" y="{ly-12}" width="220" height="58" '
        f'fill="white" stroke="#ccc" rx="3"/>'
    )
    for i, (label, color) in enumerate([
        ("KEEP (used in inversion)", COLOR["KEEP"]),
        ("CONCERN (atmos R² 0.3–0.5)", COLOR["CONCERN"]),
        ("QUARANTINE (excluded)", COLOR["QUARANTINE"]),
    ]):
        y = ly + i * 16
        parts.append(
            f'<line x1="{lx}" y1="{y}" x2="{lx+22}" y2="{y}" '
            f'stroke="{color}" stroke-width="2.5"/>'
        )
        parts.append(
            f'<text x="{lx+28}" y="{y+3}" font-size="10" fill="#333">'
            f'{label}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def build_and_plot(
    stack: str,
    pair_rows: list[dict],
    bperp_by_date: dict[datetime, float],
    out_path: Path,
) -> dict:
    """Build the graph, compute components, render SVG, return result dict."""
    node_set: set[datetime] = set()
    for r in pair_rows:
        node_set.add(r["ref_date"])
        node_set.add(r["sec_date"])
    nodes = sorted(node_set)

    uf_keep = UnionFind(nodes)
    uf_keep_concern = UnionFind(nodes)
    for r in pair_rows:
        if r["decision"] == "KEEP":
            uf_keep.union(r["ref_date"], r["sec_date"])
            uf_keep_concern.union(r["ref_date"], r["sec_date"])
        elif r["decision"] == "CONCERN":
            uf_keep_concern.union(r["ref_date"], r["sec_date"])

    comps_keep = uf_keep.components()
    comps_keep_concern = uf_keep_concern.components()

    node_to_keep_comp: dict[datetime, int] = {}
    for ci, comp in enumerate(comps_keep):
        for n in comp:
            node_to_keep_comp[n] = ci

    bridging_concerns: list[dict] = []
    for r in pair_rows:
        if r["decision"] != "CONCERN":
            continue
        c1 = node_to_keep_comp.get(r["ref_date"])
        c2 = node_to_keep_comp.get(r["sec_date"])
        if c1 is not None and c2 is not None and c1 != c2:
            bridging_concerns.append(r)

    n_keep = sum(1 for r in pair_rows if r["decision"] == "KEEP")
    n_concern = sum(1 for r in pair_rows if r["decision"] == "CONCERN")
    n_quar = sum(1 for r in pair_rows if r["decision"] == "QUARANTINE")

    svg = _render_svg(
        stack=stack,
        pair_rows=pair_rows,
        nodes=nodes,
        bperp_by_date=bperp_by_date,
        comps_keep=comps_keep,
        n_keep=n_keep,
        n_concern=n_concern,
        n_quar=n_quar,
    )
    out_path.write_text(svg, encoding="utf-8")
    logger.info(f"Wrote {out_path.name}")

    return {
        "stack": stack,
        "n_nodes": len(nodes),
        "n_keep": n_keep,
        "n_concern": n_concern,
        "n_quarantine": n_quar,
        "components_keep_only": len(comps_keep),
        "components_keep_concern": len(comps_keep_concern),
        "bridging_concerns": bridging_concerns,
        "comps_keep": [[d.strftime("%Y-%m-%d") for d in c] for c in comps_keep],
        "svg": svg,
    }


# ------------------------------------------------------------------------------
# Automated rescue recommendation
# ------------------------------------------------------------------------------
def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _gate_failure(it: dict, max_r2: float, min_coh: float, min_surv: float,
                  max_bperp: float | None = None) -> str | None:
    """Return None if the candidate clears every PRESENT quality metric, else a
    short string naming the first failing metric. Missing metrics are not failed
    (gate on available data) so a clean pair is never rejected for merely lacking
    a statistic — missing metrics are flagged on the selected entry instead."""
    if it["atmos_r2"] is not None and it["atmos_r2"] > max_r2:
        return f"atmos_r2={it['atmos_r2']:.3f}>{max_r2}"
    if it["coh"] is not None and it["coh"] < min_coh:
        return f"coherence={it['coh']:.3f}<{min_coh}"
    if it["surv"] is not None and it["surv"] < min_surv:
        return f"surviving_pct={it['surv']:.1f}<{min_surv}"
    # Perpendicular-baseline rule (config baseline.max_perp_baseline_m, roadmap 0b —
    # folded into the rescue gate 2026-07-13): a long-baseline bridge risks
    # geometric/volume decorrelation exactly where redundancy cannot average it out.
    if (max_bperp is not None and it.get("bperp") is not None
            and it["bperp"] > max_bperp):
        return f"bperp={it['bperp']:.0f}m>{max_bperp:.0f}m"
    return None


def bperp_date_maps_from_cache() -> dict[str, dict[datetime, float]]:
    """{stack: {acquisition datetime: bperp}} from the on-disk Bperp cache — OFFLINE.

    The cache is written by the full (ASF-online) run; the offline
    --recommend-only path reuses it so the Bperp gate works without network. On a
    brand-new dataset with no cache yet the gate simply has no Bperp data (pairs
    are then flagged missing_metrics:bperp, not rejected)."""
    if not BPERP_CACHE.exists():
        return {}
    out: dict[str, dict[datetime, float]] = {}
    for stack, bperp_map in json.loads(BPERP_CACHE.read_text()).items():
        date_map: dict[datetime, float] = {}
        for granule, bp in bperp_map.items():
            m = re.search(r"_(\d{8})T(\d{6})_", granule)
            if m:
                d = datetime.strptime(m.group(1) + "T" + m.group(2), "%Y%m%dT%H%M%S")
                date_map[d] = bp
        out[stack] = date_map
    return out


def recommend_rescues(
    rows: list[dict],
    max_atmos_r2: float = 0.45,
    min_coherence: float = 0.6,
    min_surviving_pct: float = 15.0,
    exclude_stacks: tuple[str, ...] = (),
    max_perp_baseline_m: float | None = None,
    bperp_maps: dict[str, dict[datetime, float]] | None = None,
) -> dict:
    """Auto-select the minimum set of CONCERN pairs that bridge each stack's
    KEEP-only islands — but only pairs that clear a quality GATE.

    A bridge is an unredundant single point of failure (its noise is not averaged
    out by SBAS redundancy), so a candidate is eligible only if it clears the
    gate: atmospheric ``R2 <= max_atmos_r2``, ``coherence >= min_coherence``,
    ``surviving_pct >= min_surviving_pct`` (each enforced only when present). Per
    stack we build islands from non-rescued KEEP edges, walk bridging candidates
    in DESCENDING coverage (highest surviving_pct first, R2 as a tiebreak), and
    select one only when it (a) merges two still-separate components AND (b) clears
    the gate. Coverage-first selection matters because a bridge gates network-wide
    solvability — once a candidate is below the R2 noise ceiling, the one that
    recovers the MOST usable ground is the better bridge (e.g. a shorter-baseline,
    higher-coherence pair beats a marginally-cleaner long-baseline one). A gap
    whose only bridges fail the gate is LEFT BROKEN — the stack stays disconnected
    (SVD / period-split downstream) rather than ingesting a noisy bridge.

    Determinism / idempotency: a previously-rescued pair (decision==KEEP with
    "RESCUED_FOR_CONNECTIVITY" in its reasons) is reverted to a CANDIDATE, so
    running on a pre- or post-rescue CSV yields the same result. Stacks in
    ``exclude_stacks`` are skipped (a manual override on top of the gate).

    Returns a payload dict: ``{gate, rescues: [...], stacks: {label: {...}}}``.
    """
    by_stack: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        dates = parse_pair_dates(r["product"])
        if dates is None:
            continue
        rescued = "RESCUED_FOR_CONNECTIVITY" in (r.get("reasons") or "")
        decision = r["decision"]
        if decision == "CONCERN" or (decision == "KEEP" and rescued):
            role = "candidate"
        elif decision == "KEEP":
            role = "base_keep"
        else:
            role = "ignore"
        by_stack[r["stack"]].append({
            "product": r["product"],
            "role": role,
            "ref_date": dates[0],
            "sec_date": dates[1],
            "atmos_r2": _safe_float(r.get("atmos_r_squared")),
            "coh": _safe_float(r.get("mean_coh_survivors")),
            "surv": _safe_float(r.get("surviving_pct")),
        })

    rescues: list[dict] = []
    diagnostics: dict[str, dict] = {}
    for stack in sorted(by_stack):
        items = by_stack[stack]
        # Pair Bperp = |bperp(secondary) - bperp(reference)| where both scenes are
        # in the (cache-derived) map; None otherwise — gate on available data.
        bmap = (bperp_maps or {}).get(stack) or {}
        for it in items:
            b1, b2 = bmap.get(it["ref_date"]), bmap.get(it["sec_date"])
            it["bperp"] = abs(b2 - b1) if (b1 is not None and b2 is not None) else None
        nodes: set[datetime] = set()
        for it in items:
            nodes.add(it["ref_date"])
            nodes.add(it["sec_date"])
        uf = UnionFind(sorted(nodes))
        for it in items:
            if it["role"] == "base_keep":
                uf.union(it["ref_date"], it["sec_date"])
        keep_islands = len(uf.components())

        if stack in exclude_stacks:
            diagnostics[stack] = {
                "keep_islands": keep_islands,
                "islands_after_rescue": keep_islands,
                "status": "excluded",
                "selected": [],
                "rejected_bridges": [],
            }
            continue

        # Highest coverage first (a bridge gates network-wide solvability), then
        # lowest R2, then date — among gate-passing candidates. The gate already
        # guarantees atmospheric purity, so we maximise recoverable ground. A
        # missing surviving_pct sorts last (treated as -1).
        candidates = sorted(
            (it for it in items if it["role"] == "candidate"),
            key=lambda it: (
                -(it["surv"] if it["surv"] is not None else -1.0),
                it["atmos_r2"] if it["atmos_r2"] is not None else 1.0,
                it["ref_date"], it["sec_date"],
            ),
        )
        selected: list[str] = []
        rejected: list[dict] = []
        for it in candidates:
            if uf.find(it["ref_date"]) == uf.find(it["sec_date"]):
                continue  # not (or no longer) a bridge — internal / redundant
            failure = _gate_failure(it, max_atmos_r2, min_coherence, min_surviving_pct,
                                    max_perp_baseline_m)
            if failure:
                rejected.append({
                    "product": it["product"],
                    "atmos_r2": it["atmos_r2"],
                    "coherence": it["coh"],
                    "surviving_pct": it["surv"],
                    "bperp_m": it["bperp"],
                    "reason": failure,
                })
                continue
            uf.union(it["ref_date"], it["sec_date"])
            missing = [m for m, v in (("coherence", it["coh"]), ("surviving_pct", it["surv"]),
                                      ("bperp", it["bperp"])) if v is None]
            rescues.append({
                "product": it["product"],
                "stack": stack,
                "bridges": (
                    f"{it['ref_date'].strftime('%Y-%m-%d')} <-> "
                    f"{it['sec_date'].strftime('%Y-%m-%d')} (merges two KEEP-only islands)"
                ),
                "atmos_r2": it["atmos_r2"],
                "coherence": it["coh"],
                "surviving_pct": it["surv"],
                "bperp_m": it["bperp"],
                "flags": [f"missing_metrics:{'+'.join(missing)}"] if missing else [],
            })
            selected.append(it["product"])

        islands_after = len(uf.components())
        diagnostics[stack] = {
            "keep_islands": keep_islands,
            "islands_after_rescue": islands_after,
            "status": "connected" if islands_after == 1 else "disconnected",
            "selected": selected,
            "rejected_bridges": rejected,
        }

    return {
        "gate": {
            "max_atmos_r2": max_atmos_r2,
            "min_coherence": min_coherence,
            "min_surviving_pct": min_surviving_pct,
            "max_perp_baseline_m": max_perp_baseline_m,
            "bperp_source": "cache" if bperp_maps else "unavailable (not gated)",
        },
        "rescues": rescues,
        "stacks": diagnostics,
    }


# ------------------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------------------
def write_index_html(results: list[dict]) -> None:
    """Embed all 5 SVGs into one self-contained HTML for easy browsing."""
    body_parts: list[str] = []
    for r in results:
        body_parts.append(f'<section style="margin:24px 0">{r["svg"]}</section>')
    html = (
        "<!doctype html>\n"
        "<html><head><meta charset='utf-8'>"
        "<title>SBAS Network Connectivity — Ramban</title>"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:1200px;"
        "margin:24px auto;padding:0 16px;color:#222}h1{margin-bottom:4px}"
        "p.meta{color:#666;margin-top:0}</style></head><body>"
        "<h1>SBAS Network Connectivity Report</h1>"
        "<p class='meta'>Auto-generated by <code>workflows/sbas_network_graph.py</code>. "
        "Each plot shows one stack's acquisition graph. Green edges = KEEP "
        "(used in inversion), orange = CONCERN, faint red = QUARANTINE.</p>"
        + "".join(body_parts) +
        "</body></html>"
    )
    INDEX_HTML.write_text(html, encoding="utf-8")
    logger.info(f"Wrote {INDEX_HTML}")


def write_report(results: list[dict]) -> None:
    lines: list[str] = [
        "# SBAS Network Connectivity Report",
        "",
        "Auto-generated by `workflows/sbas_network_graph.py`. The question this "
        "report answers: **does the KEEP-only edge set of each stack form a "
        "single connected component over the acquisition graph?** If yes, "
        "standard least-squares SBAS inversion is mathematically well-posed. "
        "If no, the network is fragmented and either (a) we rescue CONCERN "
        "edges to bridge, or (b) fall back to SVD pseudoinverse with rank-"
        "deficient handling.",
        "",
        "## Per-stack connectivity",
        "",
        "| Stack | scenes | KEEP | CONCERN | QUARANTINE | components (KEEP) | components (KEEP+CONCERN) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['stack']} | {r['n_nodes']} | {r['n_keep']} | "
            f"{r['n_concern']} | {r['n_quarantine']} | "
            f"**{r['components_keep_only']}** | {r['components_keep_concern']} |"
        )
    lines += ["", "## Bridging CONCERN pairs (rescue candidates)", ""]
    any_disconnected = False
    for r in results:
        if r["components_keep_only"] > 1:
            any_disconnected = True
            lines.append(f"### {r['stack']}")
            lines.append("")
            lines.append(
                f"KEEP-only graph has **{r['components_keep_only']} "
                f"disconnected components**. Without rescue, this stack cannot "
                f"be solved by standard least-squares.")
            lines.append("")
            lines.append("KEEP-only islands:")
            for ci, comp in enumerate(r["comps_keep"]):
                lines.append(
                    f"  - Island {ci+1} ({len(comp)} scenes): "
                    f"{comp[0]} … {comp[-1]}"
                )
            lines.append("")
            if r["bridging_concerns"]:
                lines.append("CONCERN pairs that would bridge components (rescue first):")
                lines.append("")
                lines.append("| product | ref date | sec date |")
                lines.append("|---|---|---|")
                for b in r["bridging_concerns"]:
                    lines.append(
                        f"| `{b['product']}` | "
                        f"{b['ref_date'].strftime('%Y-%m-%d')} | "
                        f"{b['sec_date'].strftime('%Y-%m-%d')} |"
                    )
            else:
                lines.append(
                    "No CONCERN pairs bridge the components — only QUARANTINE "
                    "pairs do. SVD fallback is required."
                )
            lines.append("")
    if not any_disconnected:
        lines.append("**All stacks are connected on KEEP edges alone. No rescue needed.**")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info(f"Wrote {REPORT_MD}")


# ------------------------------------------------------------------------------
# Driver
# ------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="SBAS network connectivity check + automated rescue recommendations."
    )
    ap.add_argument("--config", default=None,
                    help="Path to config.yaml (default: project-root config.yaml).")
    ap.add_argument("--recommend-only", action="store_true",
                    help="Only compute and write the rescue recommendations "
                         "(offline; skips the ASF baseline lookup and SVG plots).")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config(args.config)

    rows = list(csv.DictReader(QUARANTINE_CSV.open(encoding="utf-8")))
    logger.info(f"Loaded {len(rows)} products from {QUARANTINE_CSV.name}")

    # Rescue recommendations are computed offline (no ASF) and written first, so
    # they are available even if the ASF-dependent baseline plots below cannot run.
    # Bperp for the <max_perp_baseline_m gate comes from the on-disk cache (written
    # by previous full runs) — still offline; without a cache the gate is inactive
    # and candidates carry a missing_metrics:bperp flag instead.
    bperp_maps = bperp_date_maps_from_cache()
    if not bperp_maps:
        logger.warning("No Bperp cache — the perpendicular-baseline gate is "
                       "inactive this run (do a full ASF run to populate it).")
    payload = recommend_rescues(
        rows,
        max_atmos_r2=cfg.rescue_gate.max_atmos_r2,
        min_coherence=cfg.rescue_gate.min_coherence,
        min_surviving_pct=cfg.rescue_gate.min_surviving_pct,
        exclude_stacks=cfg.exclude_from_rescue,
        max_perp_baseline_m=cfg.baseline.max_perp_baseline_m,
        bperp_maps=bperp_maps,
    )
    RESCUE_RECOMMENDATIONS.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    logger.info(
        f"Wrote {len(payload['rescues'])} rescue recommendation(s) -> "
        f"{RESCUE_RECOMMENDATIONS.name} (gate: R2<={cfg.rescue_gate.max_atmos_r2}, "
        f"coh>={cfg.rescue_gate.min_coherence}, surv>={cfg.rescue_gate.min_surviving_pct}%, "
        f"Bperp<={cfg.baseline.max_perp_baseline_m}m"
        f"{'' if bperp_maps else ' [INACTIVE - no cache]'})"
    )
    for label, d in payload["stacks"].items():
        note = ""
        if d["status"] == "disconnected" and d["rejected_bridges"]:
            note = f"; {len(d['rejected_bridges'])} bridge(s) gated out as too noisy"
        logger.info(
            f"  {label}: islands {d['keep_islands']}->{d['islands_after_rescue']} "
            f"[{d['status']}], {len(d['selected'])} rescued{note}"
        )
    if args.recommend_only:
        return 0

    by_stack: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        dates = parse_pair_dates(r["product"])
        if dates is None:
            logger.warning(f"could not parse dates from {r['product']}; skipping")
            continue
        by_stack[r["stack"]].append({
            "product": r["product"],
            "decision": r["decision"],
            "ref_date": dates[0],
            "sec_date": dates[1],
        })

    stack_granules = fetch_granule_names_per_stack(cfg.job_name_prefix)
    bperp_per_stack = fetch_bperp_per_stack(stack_granules)

    stack_date_to_bperp: dict[str, dict[datetime, float]] = {}
    for stack, bperp_map in bperp_per_stack.items():
        date_map: dict[datetime, float] = {}
        for granule, bp in bperp_map.items():
            m = re.search(r"_(\d{8})T(\d{6})_", granule)
            if m:
                d = datetime.strptime(m.group(1) + "T" + m.group(2), "%Y%m%dT%H%M%S")
                date_map[d] = bp
        stack_date_to_bperp[stack] = date_map

    results: list[dict] = []
    for stack, pair_rows in sorted(by_stack.items()):
        if stack == "unknown":
            continue
        bperp_by_date = stack_date_to_bperp.get(stack, {})
        if not bperp_by_date:
            logger.warning(f"No Bperp data for {stack}; plotting with zeros")
        out_path = OUT_DIR / f"{stack}.svg"
        result = build_and_plot(stack, pair_rows, bperp_by_date, out_path)
        results.append(result)

    write_report(results)
    write_index_html(results)

    # Console summary
    print("-" * 78)
    print("Connectivity summary (KEEP-only graph):")
    all_connected = True
    for r in results:
        status = "OK" if r["components_keep_only"] == 1 else "BROKEN"
        if r["components_keep_only"] != 1:
            all_connected = False
        print(
            f"  {r['stack']:<24s} {status:<6s} "
            f"comps(KEEP)={r['components_keep_only']} "
            f"comps(KEEP+CONCERN)={r['components_keep_concern']} "
            f"bridging_concerns={len(r['bridging_concerns'])}"
        )
    print("-" * 78)
    if all_connected:
        print("ALL STACKS connected on KEEP edges only. "
              "Standard least-squares SBAS inversion is viable.")
    else:
        print("WARNING — at least one stack is fragmented. See "
              "_connectivity_report.md for which CONCERN pairs to rescue.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

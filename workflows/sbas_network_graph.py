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

import csv
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUARANTINE_CSV = PROJECT_ROOT / "data" / "qa_masks" / "_quarantine_list.csv"
# Note the leading underscore — keeps the directory from being treated as a
# masked-product folder by tests/test_plumbing.py and other walkers.
OUT_DIR = PROJECT_ROOT / "data" / "qa_masks" / "_network_graphs"
REPORT_MD = OUT_DIR / "_connectivity_report.md"
INDEX_HTML = OUT_DIR / "index.html"
BPERP_CACHE = OUT_DIR / "_bperp_cache.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("sbas_network_graph")


# ------------------------------------------------------------------------------
# Stack identification (mirrors _consolidate_quarantine.py)
# ------------------------------------------------------------------------------
def stack_key(product_name: str) -> str:
    """Map a HyP3 product folder name to its (direction, path, frame) stack."""
    m = re.search(r"S1AA_\d{8}T(\d{6})_", product_name)
    if not m:
        return "unknown"
    hms = m.group(1)
    if hms.startswith("1304"):
        return "ASC_path100_frame102"
    if hms.startswith("1256"):
        s = int(hms[4:6])
        return "ASC_path27_frame101" if s < 50 else "ASC_path27_frame106"
    if hms.startswith("0059"):
        s = int(hms[4:6])
        return "DESC_path34_frame479" if s < 25 else "DESC_path34_frame484"
    return "unknown"


def parse_pair_dates(product_name: str) -> tuple[datetime, datetime] | None:
    """Extract (reference_date, secondary_date) from a HyP3 product name."""
    m = re.search(r"S1AA_(\d{8})T(\d{6})_(\d{8})T(\d{6})_", product_name)
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


def fetch_granule_names_per_stack() -> dict[str, list[str]]:
    """Pull SLC granule names from HyP3 job_parameters['granules']."""
    import hyp3_sdk as sdk

    hyp3 = sdk.HyP3()
    jobs = [j for j in hyp3.find_jobs() if j.name and j.name.startswith("Ramban_NH44")]
    logger.info(f"Pulled {len(jobs)} HyP3 jobs to extract granule names.")

    stack_to_granules: dict[str, set[str]] = defaultdict(set)
    for job in jobs:
        if not job.files:
            continue
        product_name = job.files[0]["filename"].replace(".zip", "")
        stack = stack_key(product_name)
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(QUARANTINE_CSV.open(encoding="utf-8")))
    logger.info(f"Loaded {len(rows)} products from {QUARANTINE_CSV.name}")

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

    stack_granules = fetch_granule_names_per_stack()
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

"""Single source of truth for stack identity.

A *stack* is one (flightDirection, pathNumber, frameNumber) combination — the
only grouping over which Sentinel-1 interferograms may legitimately be paired.
The canonical label is e.g. ``ASC_path27_frame106`` (used by the QA scripts and
the velocity/hazard output filenames).

Stack identity is **metadata-derived**. ``download_hyp3_products.py`` records a
manifest (``data/qa_masks/_stack_manifest.json``) keyed by HyP3 product name,
deriving the stack from each job's name — which ``submit_hyp3_jobs.py`` built
from real ASF pathNumber/frameNumber metadata — so any AOI works.

For products downloaded *before* this manifest existed, :func:`seed_legacy_manifest`
reconstructs the entries from the Ramban acquisition time-of-day map, preserving
the proven labels. That time-of-day heuristic is Ramban-specific and is the one
piece a new AOI must NOT rely on — hence it lives only in the bootstrap path.

This module replaces the ``stack_key()`` function that was duplicated verbatim
across ``_consolidate_quarantine.py``, ``sbas_network_graph.py`` and
``_analyze_qa_stats.py``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "data" / "qa_masks" / "_stack_manifest.json"

# Map the two flight directions to the short prefix used in canonical labels.
_DIRECTION_ABBR = {
    "ASCENDING": "ASC", "ASC": "ASC",
    "DESCENDING": "DESC", "DESC": "DESC",
}


# ---------------------------------------------------------------------------
# Canonical labels
# ---------------------------------------------------------------------------
def canonical_label(direction: str, path, frame) -> str:
    """Build the canonical stack label, e.g. canonical_label('ASCENDING', 27, 106)
    -> 'ASC_path27_frame106'."""
    abbr = _DIRECTION_ABBR.get(str(direction).upper(), str(direction).upper())
    return f"{abbr}_path{path}_frame{frame}"


def label_from_job_name(job_name: str, job_name_prefix: str) -> str:
    """Derive the canonical stack label from a HyP3 job name.

    Job names are ``<prefix>_<DIRECTION>_path<P>_frame<F>`` (built by
    submit_hyp3_jobs.py from ASF metadata). Returns ``"unknown"`` if the name
    doesn't carry a direction/path/frame triple.
    """
    suffix = job_name
    if job_name.startswith(job_name_prefix):
        suffix = job_name[len(job_name_prefix):].lstrip("_")
    m = re.search(r"(ASCENDING|DESCENDING|ASC|DESC)_path(\d+)_frame(\d+)", suffix, re.I)
    if not m:
        return "unknown"
    return canonical_label(m.group(1), m.group(2), m.group(3))


def _parts_from_label(label: str) -> dict:
    """Decompose a canonical label back into direction/path/frame fields."""
    m = re.match(r"(ASC|DESC)_path(\d+)_frame(\d+)$", label)
    if not m:
        return {"direction": "unknown", "path": None, "frame": None}
    direction = "ASCENDING" if m.group(1) == "ASC" else "DESCENDING"
    return {"direction": direction, "path": int(m.group(2)), "frame": int(m.group(3))}


# ---------------------------------------------------------------------------
# Standing-product stack lookup
# ---------------------------------------------------------------------------
def product_stacks(scenario: str = "operational") -> list[str]:
    """Stacks behind a site's STANDING union product (its recorded source_stacks).

    The live connectivity snapshot (run_multistack.connected_stacks) is per-run
    scratch state: it is rewritten by whichever AOI's QA chain ran last, so under
    multi-AOI operation it can stop listing the stacks THIS site's validated
    product was built from (error log 2026-07-13: Ramban's per-zone gate found
    zero zones because the snapshot listed only the VD stacks). Consumers that
    operate on a standing product must take the stack list from the product
    itself; only builders of NEW products (run_multistack, the m/soil sweeps)
    should use the live snapshot. Falls back to the snapshot when no product
    exists yet (a brand-new AOI).
    """
    from config import load_config  # lazy — keep this module import-light

    union = (PROJECT_ROOT / "data" / f"alerts{load_config().data_suffix}"
             / "mosaic_asc" / f"alerts_{scenario}.json")
    if union.exists():
        src = json.loads(union.read_text(encoding="utf-8")).get("source_stacks") or []
        if src:
            return list(src)
    import run_multistack  # lazy — avoids a module-level import cycle

    return run_multistack.connected_stacks()


# ---------------------------------------------------------------------------
# Manifest I/O + lookup
# ---------------------------------------------------------------------------
def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, dict]:
    """Return {product_name: {stack, direction, path, frame, source}}; {} if absent."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(entries: dict[str, dict], path: Path = MANIFEST_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def stack_for_product(product_name: str, manifest: dict | None = None) -> str:
    """Canonical stack label for a HyP3 product (folder/zip stem).

    Looks up the manifest first; if the product isn't there, falls back to the
    Ramban time-of-day heuristic so existing Ramban data is never silently
    mislabelled even before the manifest is seeded. For a NEW AOI the heuristic
    returns ``"unknown"`` — the correct signal that the manifest must be built.
    """
    mani = manifest if manifest is not None else load_manifest()
    entry = mani.get(product_name)
    if entry and entry.get("stack"):
        return entry["stack"]
    return _legacy_stack_key(product_name)


def update_manifest_from_jobs(jobs, job_name_prefix: str, path: Path = MANIFEST_PATH) -> int:
    """Add/refresh manifest entries from HyP3 job objects (metadata-derived).

    Called by the downloader so every download run keeps the manifest current.
    Returns the number of entries written/updated.
    """
    mani = load_manifest(path)
    written = 0
    for job in jobs:
        if not (getattr(job, "name", None) and getattr(job, "files", None)):
            continue
        product = job.files[0]["filename"].replace(".zip", "")
        label = label_from_job_name(job.name, job_name_prefix)
        if label == "unknown":
            continue
        mani[product] = {"stack": label, "source": "metadata", **_parts_from_label(label)}
        written += 1
    write_manifest(mani, path)
    return written


# ---------------------------------------------------------------------------
# Legacy bootstrap (Ramban-specific; preserves the proven labels)
# ---------------------------------------------------------------------------
def _legacy_stack_key(product_name: str) -> str:
    """Ramban acquisition time-of-day -> stack label.

    Used ONLY to seed the manifest for data downloaded before metadata-based
    labelling existed. The Sentinel-1 acquisition time-of-day uniquely
    identifies each frame within each orbit *for the Ramban AOI*; it does not
    generalise, which is exactly why new AOIs use the metadata manifest instead.
    """
    m = re.search(r"S1[A-D][A-D]_\d{8}T(\d{6})_", product_name)  # incl. cross-unit S1AD (§61)
    if not m:
        return "unknown"
    hms = m.group(1)
    if hms.startswith("1304"):
        return "ASC_path100_frame102"
    if hms.startswith("1256"):
        return "ASC_path27_frame101" if int(hms[4:6]) < 50 else "ASC_path27_frame106"
    if hms.startswith("0059"):
        return "DESC_path34_frame479" if int(hms[4:6]) < 25 else "DESC_path34_frame484"
    return "unknown"


def seed_legacy_manifest(product_names, path: Path = MANIFEST_PATH) -> dict:
    """Build the manifest for EXISTING products from the legacy time-of-day map."""
    entries: dict[str, dict] = {}
    for product in product_names:
        label = _legacy_stack_key(product)
        entries[product] = {
            "stack": label, "source": "legacy_bootstrap", **_parts_from_label(label)
        }
    write_manifest(entries, path)
    return entries


def _product_names_from_coherence_csv() -> list[str]:
    """All product names recorded by feature_engineering.py (the earliest QA
    artifact that lists every product)."""
    import csv

    csv_path = PROJECT_ROOT / "data" / "qa_masks" / "_coherence_mask_stats.csv"
    if not csv_path.exists():
        return []
    with csv_path.open(encoding="utf-8") as f:
        return [r["product"] for r in csv.DictReader(f)]


if __name__ == "__main__":
    import argparse
    from collections import Counter

    ap = argparse.ArgumentParser(description="Stack manifest tools.")
    ap.add_argument(
        "--seed-legacy",
        action="store_true",
        help="Seed the manifest for existing products from the Ramban "
        "time-of-day map (auth-free bootstrap for already-downloaded data).",
    )
    args = ap.parse_args()

    if args.seed_legacy:
        products = _product_names_from_coherence_csv()
        if not products:
            raise SystemExit(
                "No products found in data/qa_masks/_coherence_mask_stats.csv. "
                "Run feature_engineering.py first."
            )
        seeded = seed_legacy_manifest(products)
        counts = Counter(e["stack"] for e in seeded.values())
        print(f"Seeded {len(seeded)} products into {MANIFEST_PATH}")
        for stack, n in sorted(counts.items()):
            print(f"  {stack:<24} {n}")
    else:
        ap.print_help()

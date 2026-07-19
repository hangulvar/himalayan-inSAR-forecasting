#!/usr/bin/env python
"""gacos_ingest.py — turn a GACOS email tarball into cross-check-ready GeoTIFFs.

Companion to gacos_request.py. Modern GACOS deliveries (verified on the
2026-07-11 frame103/105 tarballs) ship ready `<YYYYMMDD>.ztd.tif` GeoTIFFs —
those are extracted byte-identically. Older deliveries ship the classic ROI_PAC
pair `<YYYYMMDD>.ztd` (float32 LE) + `<YYYYMMDD>.ztd.rsc`; those are converted
(EPSG:4326, sea/void 0 -> NaN). Either way --out ends up with the exact
`<date>.ztd.tif` layout `_gacos_crosscheck.py` (§40) reads, one dir per track.

After ingesting it reports which interferometric pairs of the radar library are
now fully covered and prints the ready-to-paste STACKS snippet for the
cross-check. Idempotent: existing `<date>.ztd.tif` in --out are skipped.

Needs rasterio/numpy — run in the container (or the activated native env):
    docker compose run --rm insar python workflows/gacos_ingest.py \
        data/hazard_vaishnodevi/<delivery>.tar.gz --out data/hazard_vaishnodevi/gacos3_frame105
"""
from __future__ import annotations

import argparse
import json
import tarfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIFF_DIR = PROJECT_ROOT / "data" / "processed_tiffs"
STACK_MANIFEST = PROJECT_ROOT / "data" / "qa_masks" / "_stack_manifest.json"


def parse_rsc(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            out[parts[0]] = parts[1]
    return out


def collect_epochs(inputs: list[Path]) -> tuple[dict[str, bytes], dict[str, tuple[bytes, dict]]]:
    """(ready_tifs {date: tif_bytes}, classic {date: (ztd_bytes, rsc)}) from
    tarballs, directories, or bare files."""
    tifs: dict[str, bytes] = {}
    ztds: dict[str, bytes] = {}
    rscs: dict[str, dict] = {}

    def take(name: str, data: bytes) -> None:
        base = Path(name).name
        if base.endswith(".ztd.tif"):
            tifs[base[:-8]] = data
        elif base.endswith(".ztd.rsc"):
            rscs[base[:-8]] = parse_rsc(data.decode("utf-8", "replace"))
        elif base.endswith(".ztd"):
            ztds[base[:-4]] = data

    for inp in inputs:
        if inp.is_dir():
            for p in sorted(inp.iterdir()):
                if p.name.endswith((".ztd", ".ztd.rsc", ".ztd.tif")):
                    take(p.name, p.read_bytes())
        elif tarfile.is_tarfile(inp):
            with tarfile.open(inp) as tf:
                for m in tf.getmembers():
                    if m.isfile() and m.name.endswith((".ztd", ".ztd.rsc", ".ztd.tif")):
                        take(m.name, tf.extractfile(m).read())  # type: ignore[union-attr]
        else:
            take(inp.name, inp.read_bytes())

    classic = {d: (ztds[d], rscs[d]) for d in ztds if d in rscs and d not in tifs}
    for d in ztds:
        if d not in rscs and d not in tifs:
            print(f"SKIP {d}: .ztd present but no .ztd.rsc header")
    return tifs, classic


def convert_classic(out: Path, data: bytes, rsc: dict) -> None:
    w, h = int(rsc["WIDTH"]), int(rsc["FILE_LENGTH"])
    if len(data) != w * h * 4:
        raise SystemExit(f"{out.name}: byte count {len(data)} != WIDTH*FILE_LENGTH*4 "
                         f"({w}x{h}x4) — truncated download?")
    arr = np.frombuffer(data, dtype="<f4").reshape(h, w).copy()
    arr[arr == 0] = np.nan  # GACOS uses 0 for sea/void
    transform = Affine(float(rsc["X_STEP"]), 0.0, float(rsc["X_FIRST"]),
                       0.0, float(rsc["Y_STEP"]), float(rsc["Y_FIRST"]))
    with rasterio.open(out, "w", driver="GTiff", width=w, height=h, count=1,
                       dtype="float32", crs="EPSG:4326", transform=transform,
                       nodata=np.nan, compress="deflate") as dst:
        dst.write(arr, 1)


def check_shared_grid(out_dir: Path) -> None:
    """Every epoch in one dir must share a grid — pair differencing depends on it."""
    dims = {}
    for tif in sorted(out_dir.glob("*.ztd.tif")):
        with rasterio.open(tif) as ds:
            dims[tif.name] = (ds.width, ds.height, ds.transform)
    if len({(w, h) for w, h, _ in dims.values()}) > 1:
        detail = "\n  ".join(f"{n}: {w}x{h}" for n, (w, h, _) in dims.items())
        raise SystemExit(f"Mixed grids in {out_dir} — the cross-check differences "
                         f"epochs pixel-by-pixel. Use one --out per delivery/bbox.\n  {detail}")


def coverage_report(out_dir: Path) -> None:
    """Which library pairs both of whose epochs now have a ztd.tif in out_dir."""
    dates = sorted(p.name.split(".")[0] for p in out_dir.glob("*.ztd.tif"))
    have = set(dates)
    manifest = json.loads(STACK_MANIFEST.read_text(encoding="utf-8"))
    covered: dict[str, list[str]] = defaultdict(list)
    for product, meta in manifest.items():
        d1, d2 = (ts.split("T")[0] for ts in product.split("_")[1:3])
        if d1 in have and d2 in have and (TIFF_DIR / product).is_dir():
            covered[meta["stack"]].append(f"{d1}-{d2}")

    print(f"\nEpochs in {out_dir.name}: {len(dates)}  ({', '.join(dates)})")
    if not covered:
        print("No library pair has BOTH epochs covered yet — nothing the cross-check "
              "can score from this directory alone.")
        return
    print("Library pairs now fully covered:")
    for stack in sorted(covered):
        print(f"  {stack}: {len(covered[stack])} pair(s)  ({', '.join(sorted(covered[stack]))})")
    print("\nSTACKS snippet for workflows/_gacos_crosscheck.py (GACOS_DIR-relative subdir):")
    for stack in sorted(covered):
        stack_dates = sorted({d for pair in covered[stack] for d in pair.split("-")})
        print(f'    "{stack}": ("{out_dir.name}",\n'
              f'                 {json.dumps(stack_dates)}),')
    print("\nThen: docker compose run --rm insar python workflows/_gacos_crosscheck.py")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inputs", nargs="+", type=Path,
                    help="GACOS tarball(s), a directory of delivery files, or bare files")
    ap.add_argument("--out", type=Path, required=True,
                    help="Output dir for <date>.ztd.tif (e.g. "
                         "data/hazard_vaishnodevi/gacos3_frame105 — one dir per track)")
    args = ap.parse_args()

    tifs, classic = collect_epochs([p if p.is_absolute() else PROJECT_ROOT / p
                                    for p in args.inputs])
    if not (tifs or classic):
        raise SystemExit("No GACOS epochs (.ztd.tif, or .ztd + .ztd.rsc) found in the inputs.")

    out_dir = args.out if args.out.is_absolute() else PROJECT_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    n_new = n_skip = 0
    for date in sorted(set(tifs) | set(classic)):
        out = out_dir / f"{date}.ztd.tif"
        if out.exists():
            n_skip += 1
            continue
        if date in tifs:
            out.write_bytes(tifs[date])          # modern delivery: byte-identical extract
            print(f"  [extract] {out.name}")
        else:
            convert_classic(out, *classic[date])  # classic delivery: convert
            print(f"  [convert] {out.name}")
        n_new += 1
    print(f"ingested={n_new} already-present={n_skip}")

    check_shared_grid(out_dir)
    coverage_report(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

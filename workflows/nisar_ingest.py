#!/usr/bin/env python
"""nisar_ingest.py — the L-band ingestion path: NISAR GUNW -> this project's Phase-1 seam.

WHY THIS EXISTS (§81/§83). C-band cannot see 29.4% of VD's path-27 ground; L-band recovers
86.5% of it, so the sensor route is the way out of the §80 dead end (C-band flags nothing that
matches the inventory). This module is the plumbing that turns that finding into a product.

THE SEAM. A NISAR GUNW is already a GEOCODED interferogram, so it enters exactly where a HyP3
product does — as its own STACK:

    GUNW .h5 ──adapt──> data/processed_tiffs/<product>/<product>_corr.tif        (coherence)
                        data/qa_masks/<product>/<product>_masked_disp.tif        (LOS metres)
                        data/qa_masks/_stack_manifest.json                       (product->stack)
      then the EXISTING chain takes over unchanged:
        sbas_network_graph -> custom_sbas_inverter --stack NISAR_... -> geomechanical_engine
        -> agentic_orchestrator -> the union mosaic (which already merges stacks across CRSs)

Two facts make this cheap, both VERIFIED on the winter granule rather than assumed:
  * the GUNW grid is EPSG:32643 at 80 m — the SAME projection and posting our C-band products
    already use, so nothing has to be resampled;
  * the wavelength is carried IN the file (centerFrequency), so it can be derived per product.

THE TRAP THIS AVOIDS. `feature_engineering.phase_to_los_displacement` multiplies by a hardcoded
`SENTINEL1_WAVELENGTH_M` (0.0555 m). NISAR is ~0.242 m — running the C-band converter on L-band
phase would under-report every displacement by ~4.4x, silently and plausibly. So this module
does its own conversion with the wavelength READ FROM THE GRANULE, and
`tests/test_nisar_ingest.py` pins the factor.

STATUS: adapter + downloader are complete and tested; NISAR is NOT wired into any live product,
because a velocity series needs a connected network and only 8 GUNW acquisitions (all
provisional) exist over the AOI today. See docs/references/NISAR_INGESTION_DESIGN.md for the
remaining integration steps and their triggers.

Usage (h5py/rasterio -> the mintpy image; --list/--download need only asf_search):
    docker compose run --rm insar  python workflows/nisar_ingest.py --list
    docker compose run --rm insar  python workflows/nisar_ingest.py --download <granule>
    docker compose run --rm mintpy python workflows/nisar_ingest.py --adapt-all
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "workflows"))

NISAR_DIR = PROJECT_ROOT / "data" / "nisar"
TIFF_DIR = PROJECT_ROOT / "data" / "processed_tiffs"
QA_DIR = PROJECT_ROOT / "data" / "qa_masks"
MANIFEST = QA_DIR / "_stack_manifest.json"

# The C-band chain's masking threshold, MIRRORED not imported: feature_engineering imports
# rasterio at module level and the only image carrying h5py (mintpy) has no rasterio, so the
# two modules can never share a container. `tests/test_nisar_ingest.py` asserts this value
# still equals feature_engineering.COHERENCE_THRESHOLD, so the mirror cannot drift silently.
COHERENCE_THRESHOLD = 0.4

COH_GROUP = "science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram/HH"
FREQ_PATH = "science/LSAR/GUNW/grids/frequencyA/centerFrequency"
SPEED_OF_LIGHT_M_S = 299_792_458.0

# NISAR_L2_<PR|..>_GUNW_<cycle>_<track>_<A|D>_<frame>_<..>_<mode>_<pol>_<refStart>_<refEnd>_
# <secStart>_<secEnd>_<procTag>_...
_GRANULE = re.compile(
    r"^NISAR_L2_(?P<maturity>[A-Z]{2})_GUNW_(?P<cycle>\d+)_(?P<track>\d+)_(?P<direction>[AD])_"
    r"(?P<frame>\d+)_\d+_\d+_[A-Z]{2}_"
    r"(?P<ref>\d{8}T\d{6})_\d{8}T\d{6}_(?P<sec>\d{8}T\d{6})_\d{8}T\d{6}_")


def parse_granule(granule: str) -> dict:
    """Pull track/frame/direction/dates out of a NISAR granule name (pure)."""
    m = _GRANULE.match(Path(granule).stem)
    if not m:
        raise ValueError(f"not a recognisable NISAR GUNW granule: {granule}")
    d = m.groupdict()
    d["provisional"] = d["maturity"] == "PR"
    return d


def stack_id(granule: str) -> str:
    """The stack this granule belongs to. Prefixed NISAR_ so it can never collide with an
    S1 stack, and carries track/frame like the S1 convention does."""
    g = parse_granule(granule)
    look = "ASC" if g["direction"] == "A" else "DESC"
    return f"NISAR_{look}_track{int(g['track'])}_frame{g['frame']}"


def product_name(granule: str) -> str:
    """Internal product id. The two acquisition datetimes sit in the SAME positions as a
    HyP3 name, so one broadened regex reads both bands (see the design doc, step 3)."""
    g = parse_granule(granule)
    look = "ASC" if g["direction"] == "A" else "DESC"
    return (f"NISAR_{g['ref']}_{g['sec']}_T{int(g['track'])}{look[0]}"
            f"_F{g['frame']}_GUNW")


def wavelength_m(center_frequency_hz: float) -> float:
    """Radar wavelength from the granule's own centre frequency — NEVER hardcoded, because
    using the C-band constant on L-band phase under-reports displacement ~4.4x (§83)."""
    if not center_frequency_hz or center_frequency_hz <= 0:
        raise ValueError(f"implausible centre frequency: {center_frequency_hz!r}")
    return SPEED_OF_LIGHT_M_S / float(center_frequency_hz)


def phase_to_los_displacement(phase_rad, wavelength_m_: float):
    """Unwrapped phase (rad) -> LOS displacement (m), ASF/HyP3 sign convention (positive =
    motion toward the sensor). Same formula as feature_engineering, wavelength injected."""
    return -phase_rad * wavelength_m_ / (4.0 * 3.141592653589793)


def read_gunw(h5_path: Path) -> dict:
    """Coherence, unwrapped phase, grid and wavelength from a GUNW (lazy h5py import so the
    pure helpers above stay importable in the lean image)."""
    import h5py
    import numpy as np

    with h5py.File(h5_path, "r") as f:
        g = f[COH_GROUP]
        coh = np.asarray(g["coherenceMagnitude"][:], dtype="float32")
        phase = np.asarray(g["unwrappedPhase"][:], dtype="float32")
        x = np.asarray(g["xCoordinates"][:], dtype="float64")
        y = np.asarray(g["yCoordinates"][:], dtype="float64")
        dx = float(g["xCoordinateSpacing"][()])
        dy = float(g["yCoordinateSpacing"][()])
        epsg = int(g["projection"][()])
        freq = float(f[FREQ_PATH][()])
    return {"coh": coh, "phase": phase, "x0": float(x[0]), "y0": float(y[0]),
            "dx": dx, "dy": dy, "epsg": epsg, "wavelength_m": wavelength_m(freq)}


def adapt(h5_path: Path, coherence_threshold: float | None = None) -> dict:
    """GUNW -> the project's Phase-1 artifacts. Idempotent: existing outputs are left alone."""
    import numpy as np

    # GDAL, not rasterio: h5py lives only in the mintpy image and rasterio only in the lean
    # one, but BOTH carry gdal — so gdal is the only writer that lets read+write happen in a
    # single container (the same reason nisar_coherence_pilot.py uses it).
    from osgeo import gdal, osr

    thr = COHERENCE_THRESHOLD if coherence_threshold is None else coherence_threshold

    name = product_name(h5_path.name)
    stack = stack_id(h5_path.name)
    # BOTH artifacts live under qa_masks/, NOT processed_tiffs/. That directory is the HyP3
    # extraction library and carries a contract — 6 specific layers + the HyP3 metadata txt
    # (tests/test_plumbing.py). A GUNW has none of the look-vector/DEM layers, so putting it
    # there would either break that contract or force us to fabricate layers we do not have.
    disp_path = QA_DIR / name / f"{name}_masked_disp.tif"
    corr_path = QA_DIR / name / f"{name}_corr.tif"
    if disp_path.exists() and corr_path.exists():
        return {"product": name, "stack": stack, "status": "skipped_exists"}

    d = read_gunw(h5_path)
    disp = phase_to_los_displacement(d["phase"], d["wavelength_m"]).astype("float32")
    bad = (d["coh"] < thr) | ~np.isfinite(d["coh"])
    disp_masked = np.where(bad, np.nan, disp).astype("float32")

    # xCoordinates/yCoordinates are pixel CENTRES, so step back half a pixel to the corner.
    geotransform = (d["x0"] - d["dx"] / 2.0, d["dx"], 0.0,
                    d["y0"] - d["dy"] / 2.0, 0.0, d["dy"])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(int(d["epsg"]))
    wkt = srs.ExportToWkt()
    driver = gdal.GetDriverByName("GTiff")
    h, w = disp.shape
    for path, arr in ((disp_path, disp_masked), (corr_path, d["coh"])):
        path.parent.mkdir(parents=True, exist_ok=True)
        ds = driver.Create(str(path), w, h, 1, gdal.GDT_Float32, options=["COMPRESS=LZW"])
        ds.SetGeoTransform(geotransform)
        ds.SetProjection(wkt)
        band = ds.GetRasterBand(1)
        band.SetNoDataValue(float("nan"))
        band.WriteArray(arr)
        band.FlushCache()
        ds = None  # noqa: F841 — closing the dataset is what flushes it to disk

    finite = float(np.isfinite(disp_masked).mean() * 100.0)
    record_in_manifest(name, stack)
    return {"product": name, "stack": stack, "status": "ok",
            "wavelength_m": round(d["wavelength_m"], 6), "epsg": d["epsg"],
            "pixel_m": abs(d["dx"]), "survivor_pct": round(finite, 2),
            "coherence_threshold": thr}


def record_in_manifest(name: str, stack: str) -> None:
    """Add product->stack to the shared manifest. The HyP3 path derives this from job
    metadata (stacks.update_manifest_from_jobs); NISAR has no HyP3 job, so the granule name
    is the authority instead."""
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    man[name] = {**man.get(name, {}), "stack": stack, "source": "NISAR_GUNW"}
    MANIFEST.write_text(json.dumps(man, indent=2, sort_keys=True), encoding="utf-8")


def _aoi_wkt_for_active_config() -> str:
    from config import load_config
    from radar_watch import _aoi_wkt
    return _aoi_wkt(load_config().aoi_path)


def list_granules() -> list[str]:
    import asf_search as asf
    res = asf.search(dataset=asf.DATASET.NISAR,
                     intersectsWith=_aoi_wkt_for_active_config())
    return sorted(n for n in (r.properties.get("sceneName") or "" for r in res)
                  if "GUNW" in n)


def download(granule: str) -> Path:
    import asf_search as asf
    NISAR_DIR.mkdir(parents=True, exist_ok=True)
    hits = [r for r in asf.granule_search([granule])
            if r.properties.get("sceneName") == granule]
    if not hits:
        raise SystemExit(f"ASF has no granule named {granule!r}")
    hits[0].download(path=str(NISAR_DIR), session=asf.ASFSession())
    return NISAR_DIR / f"{granule}.h5"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="GUNWs at ASF over the active AOI.")
    ap.add_argument("--download", metavar="GRANULE", help="Fetch one granule into data/nisar/.")
    ap.add_argument("--adapt", metavar="H5", help="Adapt one on-disk granule.")
    ap.add_argument("--adapt-all", action="store_true", help="Adapt every .h5 in data/nisar/.")
    args = ap.parse_args()

    if args.list:
        for n in list_granules():
            print(f"  {'PROVISIONAL' if parse_granule(n)['provisional'] else 'FINAL      '}"
                  f"  {stack_id(n):32s}  {n}")
        return 0
    if args.download:
        print(f"  -> {download(args.download)}")
        return 0

    targets = ([Path(args.adapt)] if args.adapt else
               sorted(NISAR_DIR.glob("*.h5")) if args.adapt_all else [])
    if not targets:
        ap.error("nothing to do — pass --list, --download, --adapt or --adapt-all")
    for h5 in targets:
        r = adapt(h5)
        print(f"  [{r['status']}] {r['product']}  stack={r['stack']}" +
              (f"  lambda={r['wavelength_m']} m  {r['pixel_m']:.0f} m  EPSG:{r['epsg']}"
               f"  survivors={r['survivor_pct']}%" if r["status"] == "ok" else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
"""smoke_pyaps3.py — verify pyaps3 (MintPy's ERA5 downloader) works against the
NEW CDS endpoint (post-2024 migration) BEFORE enabling tropospheric correction.

Run inside the MintPy image (creds auto-mounted at ~/.cdsapirc):
  docker compose run --rm mintpy python workflows/smoke_pyaps3.py --inspect
  docker compose run --rm mintpy python workflows/smoke_pyaps3.py --download

--inspect : versions, pyaps3 download API, the ERA5 endpoint pyaps3 is configured
            to hit, and whether ~/.cdsapirc is readable. No network.
--download: actually fetch ONE ERA5 file for one frame106 date over the Ramban AOI
            bbox via pyaps3, to prove the new-CDS path end-to-end. Writes to /tmp.
"""

from __future__ import annotations

import argparse
import importlib.metadata as ilm
import os
import sys
from pathlib import Path


# Ramban AOI bounding box (deg). frame106 sits over the NH-44 corridor ~33.2N,75.2E.
# pyaps3/ERA5 snwe order = (South, North, West, East). Padded to whole ERA5 cells.
SNWE = (33.0, 33.6, 75.0, 75.7)


def inspect() -> int:
    import pyaps3 as pa

    print("=== versions ===")
    for p in ("pyaps3", "cdsapi", "mintpy"):
        try:
            print(f"  {p}: {ilm.version(p)}")
        except Exception as e:  # noqa: BLE001
            print(f"  {p}: version? {e}")

    print("=== pyaps3 download API ===")
    callables = [n for n in dir(pa) if not n.startswith("_")]
    print("  public names:", callables)
    dload = getattr(pa, "ECMWFdload", None)
    if dload is not None:
        import inspect as _i
        print("  ECMWFdload signature:", _i.signature(dload))

    print("=== ERA5 endpoint pyaps3 is configured to use ===")
    d = Path(pa.__file__).resolve().parent
    cfg = d / "model.cfg"
    print("  pyaps3 dir:", d)
    print("  model.cfg exists:", cfg.exists())
    if cfg.exists():
        import configparser
        c = configparser.ConfigParser()
        c.read(cfg)
        for sec in c.sections():
            url = c[sec].get("url", "")
            if "ERA5" in sec.upper() or "cds" in url.lower():
                print(f"  [{sec}] url = {url}")

    print("=== ~/.cdsapirc ===")
    rc = Path.home() / ".cdsapirc"
    print("  path:", rc, "exists:", rc.exists())
    if rc.exists():
        for line in rc.read_text().splitlines():
            if line.lower().startswith("url"):  # token line hidden
                print("  ", line)
    return 0


def download() -> int:
    import pyaps3 as pa

    workdir = Path("/tmp/pyaps3_smoke")
    workdir.mkdir(parents=True, exist_ok=True)
    # One acquisition date from the frame106 stack; ERA5 hour 12 (Sentinel-1 ~12:56 UTC).
    date_list = ["20250530"]
    hour = "12"
    print(f"pyaps3 ECMWFdload: date={date_list} hour={hour} snwe={SNWE} -> {workdir}")
    pa.ECMWFdload(date_list, hour, str(workdir), model="ERA5", snwe=SNWE)
    grbs = sorted(workdir.glob("ERA5*"))
    print("downloaded files:", [f"{g.name} ({g.stat().st_size} B)" for g in grbs])
    if not grbs or all(g.stat().st_size == 0 for g in grbs):
        print("FAIL: no non-empty ERA5 file downloaded")
        return 1
    print("PASS: pyaps3 fetched ERA5 from the configured CDS endpoint")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--download", action="store_true")
    args = ap.parse_args()
    if not (args.inspect or args.download):
        args.inspect = True
    rc = 0
    if args.inspect:
        rc |= inspect()
    if args.download:
        rc |= download()
    return rc


if __name__ == "__main__":
    sys.exit(main())

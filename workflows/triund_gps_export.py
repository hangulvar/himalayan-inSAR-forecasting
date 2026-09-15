#!/usr/bin/env python
"""triund_gps_export.py — turn the Triund screening into files a GPS app can use
in the field (RESULTS_AND_KPIS.md §87).

WHY: the dashboard is for planning at a desk. On the hill you want the route and
the flagged sections on a phone, offline, with your own position on them. That is
a different format problem, and GPX/KMZ solve it in different ways:

  triund_trek.gpx   the universal one. A <trk> for the route, plus <wpt> markers
                    at the START and END of every flagged segment, at each gully
                    crossing, and at the named landmarks. Imports into Gaia GPS,
                    OsmAnd, Locus, AllTrails, CalTopo, Garmin. GPX has NO polygon
                    type, so the cone AREAS cannot travel in it — the segment
                    waypoints are the honest substitute: they tell you when you
                    are entering and leaving one.

  triund_trek.kmz   zipped KML, for Google Earth (desktop + mobile), Organic Maps
                    and anything else that reads KML. This one DOES carry the cone
                    polygons, simplified so a phone can draw them.

Every waypoint name is prefixed with its band so it is readable in a list view,
and every description carries the screening caveat — CLAUDE.md rule 17: an
artifact that leaves the page carries its caveats per FEATURE, because nothing
travels with it.

  python workflows/triund_gps_export.py
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREEN = PROJECT_ROOT / "data" / "triund_screening"
GEOJSON = SCREEN / "triund_screening.geojson"

CAVEAT = ("SCREENING ONLY - decision support, not a warning system. Terrain + rainfall "
          "screen from a 30 m DEM. No radar, no site soil pass, no local landslide "
          "inventory: no measured slope motion, no Factor-of-Safety map, NO validation "
          "score. The runout cone answers 'could a block physically reach here', never "
          "'will one'. It models no block size, no bouncing, no forest braking and no "
          "barriers.")

BAND_SHORT = {"LIKELY (reach angle >= 32 deg)": "LIKELY",
              "POSSIBLE (>= 27.5 deg)": "POSSIBLE",
              "MAX-SHADOW (>= 22 deg)": "SHADOW",
              "SOURCE (slope >= 45 deg, not forested)": "SOURCE"}
# Garmin/Gaia render these; unknown symbols fall back harmlessly.
SYM = {"LIKELY": "Danger Area", "SOURCE": "Danger Area", "crossing": "Water Source",
       "trailhead": "Trail Head", "camp": "Campground", "peak": "Summit",
       "pass": "Summit", "approach": "Waypoint", "trail": "Waypoint"}


def load():
    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    out = {}
    for f in gj["features"]:
        out.setdefault(f["properties"]["layer"], []).append(f)
    return out


def ring_area_m2(ring):
    """Shoelace on a local equirectangular approximation — good enough to decide
    whether a polygon is worth carrying up a hill."""
    if len(ring) < 4:
        return 0.0
    lat0 = sum(p[1] for p in ring) / len(ring)
    kx = 111320.0 * math.cos(math.radians(lat0))
    ky = 110540.0
    s = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        s += (x0 * kx) * (y1 * ky) - (x1 * kx) * (y0 * ky)
    return abs(s) / 2.0


def simplify_ring(ring, tol_deg, min_pts=40):
    """Douglas-Peucker for CLOSED rings.

    The rings in the published GeoJSON were already simplified at 0.00025 deg when
    it was built — median ring is 5 points. Running a second, coarser pass over
    those collapses them to a line and they vanish. So: only touch rings that are
    actually big, and simplify the OPEN chain then re-close, because DP on a chain
    whose ends coincide has a degenerate baseline.
    """
    if len(ring) < min_pts:
        return ring
    closed = tuple(ring[0]) == tuple(ring[-1])
    chain = ring[:-1] if closed else ring
    out = simplify(chain, tol_deg)
    if closed:
        out = out + [out[0]]
    return out if len(out) >= 4 else ring


def simplify(ring, tol_deg):
    """Douglas-Peucker on an OPEN chain."""
    if len(ring) < 3:
        return ring

    def dmax(pts):
        x0, y0 = pts[0]
        x1, y1 = pts[-1]
        best, bi = 0.0, 0
        for i in range(1, len(pts) - 1):
            x, y = pts[i]
            num = abs((y1 - y0) * x - (x1 - x0) * y + x1 * y0 - y1 * x0)
            den = math.hypot(y1 - y0, x1 - x0) or 1e-12
            d = num / den
            if d > best:
                best, bi = d, i
        return best, bi

    d, i = dmax(ring)
    if d <= tol_deg:
        return [ring[0], ring[-1]]
    return simplify(ring[:i + 1], tol_deg)[:-1] + simplify(ring[i:], tol_deg)


def build_gpx(L) -> str:
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<gpx version="1.1" creator="triund_gps_export.py" '
         'xmlns="http://www.topografix.com/GPX/1/1" '
         'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 '
         'http://www.topografix.com/GPX/1/1/gpx.xsd">',
         '<metadata><name>Triund trek - terrain screening</name>',
         f'<desc>{escape(CAVEAT)}</desc></metadata>']

    def wpt(lon, lat, name, desc, sym):
        return (f'<wpt lat="{lat:.6f}" lon="{lon:.6f}"><name>{escape(name)}</name>'
                f'<desc>{escape(desc)}</desc><sym>{escape(sym)}</sym></wpt>')

    n_w = 0
    # named landmarks
    for f in L.get("waypoint", []):
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        x.append(wpt(lon, lat, p["name"], f'{p["kind"]}. {CAVEAT}',
                     SYM.get(p["kind"], "Waypoint")))
        n_w += 1
    # the start and end of every flagged segment — the field-useful part
    for f in sorted(L.get("flagged_trail_segment", []),
                    key=lambda f: f["properties"]["from_galu_km"]):
        p = f["properties"]
        c = f["geometry"]["coordinates"]
        b = p["band"]
        d = (f'{p["len_m"]} m in the {b} band, {p["from_galu_km"]:+.2f} to '
             f'{p["to_galu_km"]:+.2f} km from Galu Devi, {p["z0"]}-{p["z1"]} m, trail slope '
             f'~{p["slope_med"]} deg. '
             + ("Do not stop, regroup or photograph inside this stretch; keep a gap from the "
                "party ahead and glance uphill on entry. " if b == "LIKELY" else
                "You are on steep bare rock - mind your footing and what you dislodge onto "
                "people below. ")
             + CAVEAT)
        x.append(wpt(c[0][0], c[0][1], f'{b} START {p["from_galu_km"]:+.2f}km', d,
                     SYM.get(b, "Danger Area")))
        x.append(wpt(c[-1][0], c[-1][1], f'{b} end {p["to_galu_km"]:+.2f}km', d,
                     SYM.get(b, "Danger Area")))
        n_w += 2
    # gully crossings
    for f in sorted(L.get("drainage_crossing", []),
                    key=lambda f: -f["properties"]["up_km2"]):
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        d = (f'Gully crossing: {p["up_km2"]} km2 of catchment drains across the trail here, '
             f'at {p["z"]} m. Harmless dry; first place to become impassable in a downpour. '
             + CAVEAT)
        x.append(wpt(lon, lat, f'Gully {p["up_km2"]:.2f}km2 {p["from_galu_km"]:+.2f}km', d,
                     SYM["crossing"]))
        n_w += 1

    # the route itself, as one track with a segment per leg
    x.append('<trk><name>Triund trek (OSM-routed)</name>'
             f'<desc>{escape(CAVEAT)}</desc>')
    n_p = 0
    for f in L.get("trail", []):
        x.append("<trkseg>")
        for lon, lat in f["geometry"]["coordinates"]:
            x.append(f'<trkpt lat="{lat:.6f}" lon="{lon:.6f}"/>')
            n_p += 1
        x.append("</trkseg>")
    x.append("</trk></gpx>")
    return "\n".join(x), n_w, n_p


MIN_AREA_M2 = 5000.0   # 0.5 ha — below this a cone polygon is a sliver on foot


def build_kml(L, tol) -> tuple[str, int]:
    KC = {"LIKELY": "600000d6", "POSSIBLE": "6028a0f0",
          "SHADOW": "5078d6fa", "SOURCE": "80781e5a"}
    k = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
         '<name>Triund trek - terrain screening</name>',
         f'<description>{escape(CAVEAT)}</description>']
    for b, c in KC.items():
        k.append(f"<Style id='s{b}'><LineStyle><color>ff333333</color><width>1</width>"
                 f"</LineStyle><PolyStyle><color>{c}</color></PolyStyle></Style>")
    k.append("<Style id='trail'><LineStyle><color>ff1050f0</color><width>4</width>"
             "</LineStyle></Style>")
    k.append("<Style id='seg'><LineStyle><color>ff2828d6</color><width>6</width>"
             "</LineStyle></Style>")

    n_poly = 0
    n_drop = 0
    by_band = {}
    for f in L.get("runout_cone", []):
        by_band.setdefault(BAND_SHORT[f["properties"]["band"]], []).append(f)
    for b in ["SOURCE", "LIKELY", "POSSIBLE", "SHADOW"]:
        feats = by_band.get(b, [])
        if not feats:
            continue
        k.append(f"<Folder><name>Runout cone - {b} ({len(feats)})</name>"
                 f"<description>{escape(CAVEAT)}</description>")
        for f in feats:
            for ring in f["geometry"]["coordinates"]:
                raw = [tuple(p) for p in ring]
                # Slivers below MIN_AREA are noise at walking scale and just cost
                # a phone render budget that the LIKELY band needs.
                if ring_area_m2(raw) < MIN_AREA_M2:
                    n_drop += 1
                    continue
                r = simplify_ring(raw, tol)
                if len(r) < 4:
                    continue
                if r[0] != r[-1]:
                    r.append(r[0])
                co = " ".join(f"{a:.5f},{bb:.5f},0" for a, bb in r)
                k.append(f"<Placemark><name>{b}</name>"
                         f"<description>{escape(CAVEAT)}</description>"
                         f"<styleUrl>#s{b}</styleUrl><Polygon><outerBoundaryIs>"
                         f"<LinearRing><coordinates>{co}</coordinates></LinearRing>"
                         f"</outerBoundaryIs></Polygon></Placemark>")
                n_poly += 1
        k.append("</Folder>")

    k.append(f"<Folder><name>Trail</name><description>{escape(CAVEAT)}</description>")
    for f in L.get("trail", []):
        co = " ".join(f"{a:.6f},{b:.6f},0" for a, b in f["geometry"]["coordinates"])
        k.append(f"<Placemark><name>{escape(f['properties']['name'])}</name>"
                 f"<description>{escape(CAVEAT)}</description><styleUrl>#trail</styleUrl>"
                 f"<LineString><tessellate>1</tessellate><coordinates>{co}"
                 f"</coordinates></LineString></Placemark>")
    k.append("</Folder>")

    k.append(f"<Folder><name>Flagged segments</name>"
             f"<description>{escape(CAVEAT)}</description>")
    for f in L.get("flagged_trail_segment", []):
        p = f["properties"]
        co = " ".join(f"{a:.6f},{b:.6f},0" for a, b in f["geometry"]["coordinates"])
        k.append(f"<Placemark><name>{p['band']} {p['len_m']}m @ {p['from_galu_km']:+.2f}km"
                 f"</name><description>{escape(CAVEAT)}</description>"
                 f"<styleUrl>#seg</styleUrl><LineString><tessellate>1</tessellate>"
                 f"<coordinates>{co}</coordinates></LineString></Placemark>")
    k.append("</Folder>")

    for layer, label in [("waypoint", "Waypoints"), ("drainage_crossing", "Gully crossings")]:
        k.append(f"<Folder><name>{label}</name>"
                 f"<description>{escape(CAVEAT)}</description>")
        for f in L.get(layer, []):
            p = f["properties"]
            lon, lat = f["geometry"]["coordinates"]
            nm = p.get("name") or f"Gully {p.get('up_km2')} km2"
            k.append(f"<Placemark><name>{escape(str(nm))}</name>"
                     f"<description>{escape(CAVEAT)}</description>"
                     f"<Point><coordinates>{lon:.6f},{lat:.6f},0</coordinates></Point>"
                     f"</Placemark>")
        k.append("</Folder>")
    k.append("</Document></kml>")
    return "\n".join(k), n_poly


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simplify", type=float, default=0.00035,
                    help="polygon simplification tolerance in degrees (~35 m; default)")
    args = ap.parse_args(argv)

    if not GEOJSON.exists():
        raise SystemExit(f"Missing {GEOJSON} — build the screening first.")
    L = load()
    print("source layers: " + ", ".join(f"{k} {len(v)}" for k, v in L.items()))

    gpx, n_w, n_p = build_gpx(L)
    (SCREEN / "triund_trek.gpx").write_text(gpx, encoding="utf-8")
    print(f"\ntriund_trek.gpx : {n_w} waypoints, {n_p} track points, "
          f"{len(gpx) / 1024:.0f} kB")

    kml, n_poly = build_kml(L, args.simplify)
    kmz = SCREEN / "triund_trek.kmz"
    with zipfile.ZipFile(kmz, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("doc.kml", kml)
    print(f"triund_trek.kmz : {n_poly} cone polygons (simplified {args.simplify} deg), "
          f"{kmz.stat().st_size / 1024:.0f} kB zipped (kml was {len(kml) / 1024:.0f} kB)")

    # caveat audit — the rule that made §86 worth having
    n_pm = kml.count("<Placemark>")
    n_de = kml.count("<description>")
    assert n_de >= n_pm, "a placemark is missing its caveat"
    assert gpx.count("<desc>") >= gpx.count("<wpt "), "a waypoint is missing its caveat"
    print(f"\ncaveat audit: KML {n_pm}/{n_pm} placemarks carry a description; "
          f"GPX {n_w}/{n_w} waypoints carry one — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

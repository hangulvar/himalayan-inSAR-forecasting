#!/usr/bin/env python
"""triund_field_card.py — a one-page field card for the Triund trek (§87).

WHY PAPER: phones die, freeze, and lose signal. The card is the fallback that
still works at 2,800 m in the rain with a flat battery. It therefore carries only
what you would act on: distance from the Galu Devi check-post, what the ground
above you is doing there, and what to do about it.

Prints on one A5 side (or A4 at 2-up). Black-and-white legible — the band is
named in words as well as shaded, because a photocopy loses colour.

  python workflows/triund_field_card.py          # writes the HTML card
Open it and print to PDF (Ctrl+P). Page size is set to A5 in the stylesheet.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREEN = PROJECT_ROOT / "data" / "triund_screening"
GEOJSON = SCREEN / "triund_screening.geojson"
OUT = SCREEN / "triund_field_card.html"

CAVEAT = ("Screening only — terrain + rainfall, from a 30 m elevation model. No measured slope "
          "movement, no soil data, no local landslide record, no accuracy score. The bands say "
          "a block COULD reach a spot, never that one is coming.")


def load():
    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    out = {}
    for f in gj["features"]:
        out.setdefault(f["properties"]["layer"], []).append(f)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-len", type=int, default=100,
                    help="shortest flagged segment to print, metres (default 100)")
    args = ap.parse_args(argv)

    if not GEOJSON.exists():
        raise SystemExit(f"Missing {GEOJSON} — build the screening first.")
    L = load()

    segs = sorted((f["properties"] for f in L.get("flagged_trail_segment", [])
                   if f["properties"]["len_m"] >= args.min_len),
                  key=lambda p: p["from_galu_km"])
    cross = sorted((f["properties"] for f in L.get("drainage_crossing", [])),
                   key=lambda p: p["from_galu_km"])

    # Build one distance-ordered list of everything you pass, so the card reads
    # the way the walk happens rather than grouping by hazard type.
    rows = []
    for p in segs:
        rows.append({"km": p["from_galu_km"], "to": p["to_galu_km"],
                     "kind": p["band"], "len": p["len_m"],
                     "z": f'{p["z0"]}–{p["z1"]}', "slope": p["slope_med"]})
    for p in cross:
        rows.append({"km": p["from_galu_km"], "to": None, "kind": "GULLY",
                     "len": None, "z": str(p["z"]), "area": p["up_km2"]})
    rows.sort(key=lambda r: r["km"])

    # The action for each band is stated ONCE in the key. Repeating it on all 22
    # rows triples the page and makes the card slower to scan, which is the
    # opposite of what you want cold and wet.
    KEY = [
        ("LIKELY", "likely",
         "Steep bare rock above, close enough that even a short-running block arrives.",
         "<b>Don't stop.</b> No breaks or photos. Look up on entry, gap from the party "
         "ahead, cross steadily."),
        ("SOURCE", "source",
         "You are <i>on</i> the steep bare rock, not below it.",
         "<b>Watch your footing and what you kick</b> — it lands on people below. Call out."),
        ("GULLY", "gully",
         "A catchment drains across the trail.",
         "Dry: harmless. Raining: first place to become impassable — <b>don't cross a "
         "running gully</b>."),
    ]
    key_html = "".join(
        f'<div class="kr"><span class="tag t-{c}">{t}</span>'
        f'<span class="kd"><b>{m}</b> {a}</span></div>' for t, c, m, a in KEY)

    def fmt_km(v):
        return f"{v:+.2f}"

    tr = []
    for r in rows:
        k = r["kind"]
        where = (f'{fmt_km(r["km"])}&nbsp;&rarr;&nbsp;{fmt_km(r["to"])}'
                 if r["to"] is not None else f'{fmt_km(r["km"])}')
        detail = (f'{r["len"]}&thinsp;m &middot; {r["z"]}&thinsp;m &middot; ~{r["slope"]}&deg;'
                  if r["len"] else f'{r["area"]}&thinsp;km&sup2; &middot; {r["z"]}&thinsp;m')
        tr.append(
            f'<tr class="k-{k.lower()}"><td class="km">{where}</td>'
            f'<td class="band"><span class="tag t-{k.lower()}">{k}</span></td>'
            f'<td class="what">{detail}</td></tr>')

    # One column measured 240 mm against A5's 192 mm of usable height, so the
    # table runs in two columns: first half of the walk on the left, second on
    # the right. Splitting the TABLE (not the page) keeps each row on one line.
    half = (len(tr) + 1) // 2
    col_a, col_b = tr[:half], tr[half:]

    n_lik = sum(1 for r in rows if r["kind"] == "LIKELY")
    n_src = sum(1 for r in rows if r["kind"] == "SOURCE")
    n_gul = sum(1 for r in rows if r["kind"] == "GULLY")
    longest = max((r for r in rows if r["kind"] == "LIKELY"), key=lambda r: r["len"])

    doc = f"""<!doctype html>
<meta charset="utf-8">
<title>Triund field card</title>
<style>
@page {{ size: A5 portrait; margin: 9mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: "Helvetica Neue", Arial, sans-serif; font-size: 8.4pt;
  line-height: 1.32; color: #111; margin: 0; }}
h1 {{ font-size: 15pt; margin: 0; letter-spacing: -.01em; }}
.sub-h {{ font-size: 7.6pt; color: #444; margin: 2px 0 0; }}
header {{ border-bottom: 1.6pt solid #111; padding-bottom: 4px; margin-bottom: 7px;
  display: flex; justify-content: space-between; align-items: flex-end; gap: 10px; }}
.key {{ text-align: right; font-size: 7pt; color: #333; line-height: 1.5;
  white-space: nowrap; }}
.lede {{ margin: 0 0 5px; font-size: 8.2pt; }}
.lede b {{ background: #eee; padding: 0 2px; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ font-size: 6.4pt; text-transform: uppercase; letter-spacing: .09em; color: #555;
  text-align: left; border-bottom: .7pt solid #999; padding: 0 4px 2px; font-weight: 600; }}
td {{ padding: 3.5px 4px; border-bottom: .4pt solid #ccc; vertical-align: top; }}
td.km {{ font-variant-numeric: tabular-nums; white-space: nowrap; font-weight: 700;
  font-size: 7.4pt; padding-right: 2px; }}
td.band {{ width: 15mm; }}
td.what {{ font-variant-numeric: tabular-nums; color: #333; font-size: 7pt; }}
td {{ padding: 2.1px 3px; }}
.cols {{ display: flex; gap: 7px; align-items: flex-start; }}
.cols > table {{ flex: 1 1 0; min-width: 0; }}
.keybox {{ border: .7pt solid #111; padding: 4px 6px; margin: 5px 0; }}
.kr {{ display: flex; gap: 6px; align-items: baseline; margin-bottom: 3px; }}
.kr:last-child {{ margin-bottom: 0; }}
.kd {{ font-size: 7.4pt; line-height: 1.3; }}
.kd b {{ font-weight: 400; color: #555; }}
.sub {{ font-size: 6.6pt; color: #555; font-variant-numeric: tabular-nums; }}
.tag {{ display: inline-block; font-size: 6.4pt; font-weight: 700; letter-spacing: .05em;
  padding: .5px 3px; border: .7pt solid #111; }}
.t-likely {{ background: #111; color: #fff; }}
.t-source {{ background: #fff; color: #111; border-style: double; border-width: 2pt; }}
.t-gully  {{ background: #fff; color: #111; border-style: dashed; }}
tr.k-likely td {{ background: #f2f2f2; }}
.what b {{ font-weight: 700; }}
footer {{ margin-top: 7px; border-top: .7pt solid #999; padding-top: 5px;
  font-size: 6.6pt; color: #444; }}
.rule {{ margin: 5px 0; padding: 4px 6px; border: .7pt solid #111; font-size: 7.4pt; }}
.rule b {{ display: block; font-size: 8pt; margin-bottom: 1px; }}
@media screen {{ body {{ max-width: 148mm; margin: 12px auto; padding: 0 10px; }} }}
</style>

<header>
  <div>
    <h1>Triund &mdash; field card</h1>
    <p class="sub-h">Distances from the Galu Devi check-post &middot; negative = the
      McLeod&nbsp;Ganj / Dharamkot approach below it</p>
  </div>
  <div class="key">
    Galu Devi &rarr; Triund <b>5.01 km</b><br>
    McLeod Ganj &rarr; Triund <b>9.75 km</b><br>
    Triund ridge <b>2,833 m</b>
  </div>
</header>

<p class="lede">The whole climb from Galu Devi to Triund sits under steep ground &mdash;
<b>zero clear metres</b>. That is normal for this mountain and not a reason to turn back.
The list below is only the parts where it is worth changing what you are doing.</p>

<div class="rule"><b>If it is raining hard, or has been</b>
Gullies fill first and the scree sections turn to slurry. Turn around rather than cross a
running gully; they drop as fast as they rise. Late September is the good window, but roughly
half of past late-Septembers still crossed the rainfall line that has triggered slides here.</div>

<div class="keybox">{key_html}</div>

<div class="cols">
  <table>
    <thead><tr><th>km</th><th>What</th><th>Length &middot; height &middot; slope</th></tr></thead>
    <tbody>{chr(10).join(col_a)}</tbody>
  </table>
  <table>
    <thead><tr><th>km</th><th>What</th><th>Length &middot; height &middot; slope</th></tr></thead>
    <tbody>{chr(10).join(col_b)}</tbody>
  </table>
</div>

<footer>
<b>Summary:</b> {n_lik} exposed stretches, {n_src} on-source sections, {n_gul} gully crossings.
Longest exposed run <b>{longest['len']} m</b> at {fmt_km(longest['km'])}&ndash;{fmt_km(longest['to'])} km
({longest['z']} m) &mdash; the "22 Curves". Above Triund toward Snowline eases; the Dharamkot
approach below the check-post is clear.
<br><br>
<b>Check before you go:</b> the 6 Jan 2026 Kangra DDMA order requires prior permission from
SP Kangra for the Triund route and bans trekking above 3,000 m (Snowline ~3,100 m, Laka above
that; Triund ridge itself is below it). Permissions are void when IMD Shimla issues a warning.
Day-hike cut-off at the check-post 11:30, camping 14:00.
<br><br>
{html.escape(CAVEAT)}
</footer>
"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"  {len(rows)} rows: {n_lik} LIKELY, {n_src} SOURCE, {n_gul} gully")
    print(f"  distance span {fmt_km(rows[0]['km'])} to {fmt_km(rows[-1]['km'])} km from Galu Devi")
    print(f"  longest exposed run {longest['len']} m at {fmt_km(longest['km'])} km")
    print("  open it and print to PDF (A5 portrait is set in the stylesheet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

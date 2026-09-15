#!/usr/bin/env python
"""check_dashboard_render.py — EXECUTE the Triund dashboard's script and prove it
renders, before republishing it.

WHY THIS EXISTS (2026-09-15): a patch introduced a `const LAYERS`-style collision
— an injected top-level `const L` against the map function's own `const L = [...]`
legend array. The inner declaration shadows the outer for the whole function, so
a reference earlier in that function hit the temporal dead zone and threw
ReferenceError. The map and every block after it rendered BLANK, and it shipped.

`node --check` passed, because it parses; it cannot see a runtime scoping error.
The only check that catches this class is running the code. This does that
against a minimal DOM stub and asserts every render target was populated.

  python workflows/check_dashboard_render.py
  python workflows/check_dashboard_render.py --html some/other.html

Requires node on PATH. Exits non-zero on a thrown error or an empty target.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HTML = PROJECT_ROOT / "data" / "triund_screening" / "triund_dashboard.html"

# Every element the page is supposed to fill. A blank one means a silent failure.
TARGETS = ["map", "prof", "xsec", "verdict", "segs", "cross", "bands", "ledger",
           "needT", "needX", "rainv", "raintbl", "legend", "foot", "fresh",
           "raindate", "nowbox", "zlvl"]

HARNESS = r"""
const fs=require("fs"), vm=require("vm");
const code=fs.readFileSync(process.argv[2],"utf8");
const EXPECT=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
const made=[], nodes=new Map();
function mk(tag,id){return{tagName:tag,id:id||"",_attrs:{},_children:[],_html:"",_text:"",
 style:{},classList:{add(){},remove(){},contains:()=>false},
 setAttribute(k,v){this._attrs[k]=String(v);},getAttribute(k){return this._attrs[k];},
 removeAttribute(k){delete this._attrs[k];},
 appendChild(c){this._children.push(c);return c;},
 removeChild(c){const i=this._children.indexOf(c);if(i>=0)this._children.splice(i,1);},
 remove(){},addEventListener(){},setPointerCapture(){},releasePointerCapture(){},
 getBoundingClientRect(){return{left:0,top:0,width:846,height:782};},
 querySelector(){return null;},querySelectorAll(){return[];},
 get innerHTML(){return this._html;},set innerHTML(v){this._html=String(v);},
 get textContent(){return this._text;},set textContent(v){this._text=String(v);},
 get firstChild(){return this._children[0]||null;}};}
const document={getElementById(id){if(!nodes.has(id))nodes.set(id,mk("div",id));return nodes.get(id);},
 createElementNS(ns,t){const n=mk(t);made.push(n);return n;},
 createElement(t){const n=mk(t);made.push(n);return n;},
 documentElement:mk("html"),body:mk("body"),addEventListener(){}};
const sandbox={document,window:{addEventListener(){},matchMedia:()=>({matches:false,addEventListener(){}}),
 devicePixelRatio:1,getComputedStyle:()=>({})},console,Math,JSON,Date,Array,Object,String,
 Number,Boolean,Map,Set,parseInt,parseFloat,isNaN,isFinite,
 requestAnimationFrame:(f)=>f(0),setTimeout:(f)=>{try{f();}catch(e){}return 0;},
 localStorage:{getItem:()=>null,setItem(){},removeItem(){}}};
sandbox.globalThis=sandbox;
let err=null;
try{vm.createContext(sandbox);new vm.Script(code,{filename:"dashboard.js"})
 .runInContext(sandbox,{timeout:60000});}catch(e){err=e;}
const out={error:null,created:made.length,byTag:{},ids:{}};
if(err)out.error={name:err.name,message:err.message,
 stack:String(err.stack||"").split("\n").slice(0,4)};
for(const n of made)out.byTag[n.tagName]=(out.byTag[n.tagName]||0)+1;
for(const id of EXPECT){const n=nodes.get(id);
 out.ids[id]=n?{html:n._html.length,text:n._text.length,kids:n._children.length}:null;}
console.log(JSON.stringify(out));
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    html_path = Path(args.html)
    if not html_path.exists():
        raise SystemExit(f"Missing {html_path}")
    s = html_path.read_text(encoding="utf-8")
    i = s.find("<script>")
    j = s.rfind("</script>")
    if i < 0 or j < 0:
        raise SystemExit("No <script> block found in the page.")
    script = s[i + len("<script>"):j]

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "page.js").write_text(script, encoding="utf-8")
        (td / "harness.js").write_text(HARNESS, encoding="utf-8")
        (td / "ids.json").write_text(json.dumps(TARGETS), encoding="utf-8")
        try:
            p = subprocess.run(["node", str(td / "harness.js"), str(td / "page.js"),
                                str(td / "ids.json")],
                               capture_output=True, text=True, timeout=180)
        except FileNotFoundError:
            raise SystemExit("node is not on PATH — this check needs it.")
        if p.returncode != 0 and not p.stdout.strip():
            raise SystemExit(f"harness failed:\n{p.stderr[:2000]}")
        res = json.loads(p.stdout)

    print(f"script: {len(script) / 1024:.0f} kB   elements created: {res['created']}")
    if args.verbose:
        print("  by tag: " + ", ".join(f"{k} {v}" for k, v in sorted(res["byTag"].items())))

    ok = True
    if res["error"]:
        e = res["error"]
        print(f"\n  THROWN: {e['name']}: {e['message']}")
        for ln in e["stack"]:
            print(f"    {ln}")
        ok = False

    empty = [k for k, v in res["ids"].items()
             if v is None or (v["html"] == 0 and v["text"] == 0 and v["kids"] == 0)]
    for k, v in res["ids"].items():
        mark = "EMPTY" if k in empty else "ok"
        if args.verbose or k in empty:
            print(f"  {mark:5s} #{k}  " +
                  (f"html {v['html']}  text {v['text']}  kids {v['kids']}" if v else "MISSING"))
    if empty:
        print(f"\n  {len(empty)} render target(s) left blank: {', '.join(empty)}")
        ok = False

    # a page that renders nothing would otherwise pass an 'error is null' check
    if res["created"] < 300:
        print(f"\n  only {res['created']} elements created — the map/profile draw "
              f"hundreds; something stopped early")
        ok = False

    print("\n" + ("RENDER OK — safe to republish" if ok else "*** RENDER BROKEN ***"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

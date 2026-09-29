"""Frame check page (task 5.4v): one still at a time, three buttons.

Validates product detection (D-033). The frames were drawn at random, blind to every detector
score (`src/features/product_frame_sample.py`), and this page never shows a score, a label or a
detection box - so each answer is an independent look.

Keys: 1 = Coca-Cola product visible, 2 = other drink container, 3 = nothing;
left/right arrows move without answering. Every click is saved at once to
`docs/product_frame_check.csv`, so closing the page loses nothing.

Usage:
    python -m src.coding.frame_check_app
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.app import Handler as _CodingHandler  # noqa: E402

CHECK = config.DOCS / "product_frame_check.csv"
ANSWERS = {"coca_cola_product", "other_container", "none", ""}
_LOCK = threading.Lock()


def load() -> pd.DataFrame:
    if not CHECK.exists():
        raise SystemExit(f"{CHECK} not found - run: python -m src.features.product_frame_sample")
    df = pd.read_csv(CHECK, dtype=str).fillna("")
    for c in ("researcher_answer", "researcher_note", "answered_at"):
        if c not in df.columns:
            df[c] = ""
    return df


def save(order: str, field: str, value: str) -> dict:
    if field == "researcher_answer" and value not in ANSWERS:
        raise ValueError("invalid answer")
    if field not in ("researcher_answer", "researcher_note"):
        raise ValueError("invalid field")
    with _LOCK:
        df = load()
        i = df.index[df["order"] == str(order)]
        if len(i) != 1:
            raise ValueError("unknown frame")
        df.at[i[0], field] = value.replace("\r", " ").replace("\n", " ")[:1000]
        if field == "researcher_answer":
            df.at[i[0], "answered_at"] = (datetime.now(timezone.utc).isoformat(timespec="seconds")
                                          if value else "")
        tmp = CHECK.with_suffix(".tmp")
        df.to_csv(tmp, index=False, encoding="utf-8")
        tmp.replace(CHECK)
        return {"answered": int((df["researcher_answer"] != "").sum()), "total": len(df)}


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Frame check</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e3e1dc;--ok:#1f7a3a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
header{display:flex;align-items:center;gap:16px;padding:10px 20px;background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:2}
header h1{font-size:16px;margin:0}.bar{flex:1;height:8px;background:var(--line);border-radius:4px;overflow:hidden}.bar>i{display:block;height:100%;background:var(--ok);width:0}
#count{color:var(--muted);white-space:nowrap}
main{padding:14px 20px;max-width:1100px;margin:auto;display:grid;grid-template-columns:minmax(260px,420px) 1fr;gap:20px}
@media(max-width:820px){main{grid-template-columns:1fr}}
img{width:100%;border-radius:10px;background:#222;display:block}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.card h2{margin:0 0 6px;font-size:17px}.help{color:var(--muted);font-size:13px;margin:0 0 14px}
.opts{display:flex;flex-direction:column;gap:10px}
.opts button{font:inherit;font-size:16px;text-align:left;padding:12px 16px;border-radius:10px;border:1px solid var(--line);background:#fafaf8;cursor:pointer}
.opts button.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.meta{color:var(--muted);font-size:13px;margin:10px 0 0}
textarea{width:100%;min-height:44px;font:inherit;border:1px solid var(--line);border-radius:8px;padding:8px;margin-top:12px}
.nav{display:flex;gap:8px;margin-top:12px;align-items:center;flex-wrap:wrap}
.nav button{font:inherit;padding:8px 14px;border-radius:8px;border:1px solid var(--line);background:var(--card);cursor:pointer}
#saved{color:var(--ok);font-size:13px}kbd{background:#efece6;border-radius:4px;padding:0 5px;font-size:12px}
</style></head><body>
<header><h1>Frame check</h1><div class="bar"><i id="prog"></i></div><span id="count">-</span></header>
<main><div><img id="shot" alt="frame"><div class="meta" id="meta"></div></div>
<div class="card"><h2>What can you see in this still?</h2>
<p class="help">One frame from one video, chosen at random. Judge only this picture - not what you
remember of the video. A logo on a sign, a truck or a T-shirt is <b>not</b> a drink container.
A can, bottle, cup or glass holding a drink is.</p>
<div class="opts">
<button data-v="coca_cola_product"><kbd>1</kbd> &nbsp;A <b>Coca-Cola</b> product (any variant)</button>
<button data-v="other_container"><kbd>2</kbd> &nbsp;Another drink container (not Coca-Cola)</button>
<button data-v="none"><kbd>3</kbd> &nbsp;No drink container at all</button>
</div>
<textarea id="note" placeholder="Note (optional)"></textarea>
<div class="nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button>
<button id="nextopen">Next unanswered</button><span id="saved"></span></div></div></main>
<script>
let S=null,cur=0;const $=s=>document.querySelector(s);
async function load(){S=await (await fetch('/api/state')).json();const f=S.items.findIndex(it=>!it.researcher_answer);show(f<0?0:f);}
function progress(){const n=S.items.filter(it=>it.researcher_answer).length;$('#count').textContent=n+' / '+S.items.length+' answered';$('#prog').style.width=(100*n/S.items.length)+'%';}
function show(i){cur=Math.max(0,Math.min(i,S.items.length-1));const it=S.items[cur];
 $('#shot').src='/frame/'+it.order;
 $('#meta').textContent=(cur+1)+' of '+S.items.length+' \\u00b7 '+it.platform+' \\u00b7 '+it.t+' s into the video';
 document.querySelectorAll('.opts button').forEach(b=>b.classList.toggle('on',b.dataset.v===it.researcher_answer));
 $('#note').value=it.researcher_note||'';$('#saved').textContent='';progress();window.scrollTo(0,0);}
async function answer(v){const it=S.items[cur];it.researcher_answer=v;
 document.querySelectorAll('.opts button').forEach(b=>b.classList.toggle('on',b.dataset.v===v));
 if(await post(it.order,'researcher_answer',v))setTimeout(()=>{for(let k=1;k<=S.items.length;k++){const j=(cur+k)%S.items.length;if(!S.items[j].researcher_answer){show(j);return;}}$('#saved').textContent='All answered - saved.';},200);}
async function post(order,field,value){$('#saved').textContent='Saving...';try{const r=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({order:order,field:field,value:value})});
 if(!r.ok)throw new Error(await r.text());$('#saved').textContent='Saved';progress();return true;}catch(e){$('#saved').textContent='NOT saved - '+e.message;$('#saved').style.color='#b3261e';return false;}}
document.querySelectorAll('.opts button').forEach(b=>b.onclick=()=>answer(b.dataset.v));
$('#note').onchange=e=>{S.items[cur].researcher_note=e.target.value;post(S.items[cur].order,'researcher_note',e.target.value);};
$('#prev').onclick=()=>show(cur-1);$('#next').onclick=()=>show(cur+1);
$('#nextopen').onclick=()=>{for(let k=1;k<=S.items.length;k++){const j=(cur+k)%S.items.length;if(!S.items[j].researcher_answer){show(j);return;}}};
document.addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA')return;
 const m={'1':'coca_cola_product','2':'other_container','3':'none'};
 if(m[e.key])answer(m[e.key]);if(e.key==='ArrowRight')show(cur+1);if(e.key==='ArrowLeft')show(cur-1);});
load();
</script></body></html>"""


class Handler(_CodingHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/state":
            cols = ["order", "platform", "media_id", "t", "researcher_answer", "researcher_note"]
            items = load()[cols].to_dict("records")
            return self._send(200, json.dumps({"items": items}, ensure_ascii=False).encode("utf-8"),
                              "application/json; charset=utf-8")
        m = re.fullmatch(r"/frame/(\d+)", path)
        if m:
            row = load()
            row = row[row["order"] == m.group(1)]
            if row.empty:
                return self._send(404, b"not found", "text/plain")
            col = "image" if "image" in row.columns and row.iloc[0].get("image") else "frame"
            f = config.ROOT / str(row.iloc[0][col]).replace("\\", "/")
            if not f.exists():
                return self._send(404, b"not found", "text/plain")
            return self._send(200, f.read_bytes(), "image/jpeg")
        return self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path != "/api/save":
            return self._send(404, b"not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > 20000:
                raise ValueError("too large")
            d = json.loads(self.rfile.read(n) or b"{}")
            out = save(str(d["order"]), str(d["field"]), str(d.get("value", "")))
            return self._send(200, json.dumps(out).encode(), "application/json")
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            return self._send(400, str(exc).encode(), "text/plain")


def main() -> None:
    ap = argparse.ArgumentParser(description="Frame check page (5.4v).")
    ap.add_argument("--port", type=int, default=8776)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    df = load()
    missing = [r["order"] for _, r in df.iterrows()
               if not (config.ROOT / str(r.get("image") or r["frame"]).replace("\\", "/")).exists()]
    if missing:
        raise SystemExit(f"image missing for frames: {missing[:5]} - re-run product_frame_sample")
    server = None
    for port in range(args.port, args.port + 10):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit("no free port found")
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Frame check page: {url}")
    print(f"{int((df['researcher_answer'] != '').sum())} of {len(df)} answered so far. "
          f"Answers save to {CHECK.relative_to(config.ROOT)}. Ctrl+C here to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Every answer you clicked is saved.")


if __name__ == "__main__":
    main()

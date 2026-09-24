"""Visual Zero Sugar check page (D-029): one YouTube Short at a time, three buttons.

Shows the Short's frame sheet (one frame per shot, `src/screen/zero_sugar_check.py`) and the
video itself, and asks one question - the codebook's item 5: is Coca-Cola Zero Sugar packaging
shown anywhere? Every click is saved at once to `docs/zero_sugar_visual_check.csv` with the
time. Close it any time; it reopens at the first unanswered Short.

Like the coding page (`src/coding/app.py`): standard library only, bound to 127.0.0.1, videos
served by list position with byte ranges. It never shows an earlier blind code, a text label or
any automated score, so each answer is a fresh look.

Keys: 1 = Zero Sugar, 2 = Not Zero Sugar, 3 = Unsure (each saves and moves on);
left/right arrows move without answering.

Usage:
    python -m src.coding.zero_sugar_check_app
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
from src.coding.app import Handler as _CodingHandler  # noqa: E402  (reuses its video serving)

CHECK = config.DOCS / "zero_sugar_visual_check.csv"
ANSWERS = {"zero_sugar", "not_zero_sugar", "unsure", ""}
_LOCK = threading.Lock()


def load() -> pd.DataFrame:
    if not CHECK.exists():
        raise SystemExit(f"{CHECK} not found - run: python -m src.screen.zero_sugar_check")
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
            raise ValueError("unknown Short")
        df.at[i[0], field] = value.replace("\r", " ").replace("\n", " ")[:1000]
        if field == "researcher_answer":
            df.at[i[0], "answered_at"] = (datetime.now(timezone.utc).isoformat(timespec="seconds")
                                          if value else "")
        tmp = CHECK.with_suffix(".tmp")
        df.to_csv(tmp, index=False, encoding="utf-8")
        tmp.replace(CHECK)
        return {"answered": int((df["researcher_answer"] != "").sum()), "total": len(df)}


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Zero Sugar check</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e3e1dc;--ok:#1f7a3a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
header{display:flex;align-items:center;gap:16px;padding:10px 20px;background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:2}
header h1{font-size:16px;margin:0}.bar{flex:1;height:8px;background:var(--line);border-radius:4px;overflow:hidden}.bar>i{display:block;height:100%;background:var(--ok);width:0}
#count{color:var(--muted);white-space:nowrap}main{padding:14px 20px;max-width:1900px;margin:auto}
.sheet{width:100%;border-radius:8px;display:block;background:#222}
.row{display:grid;grid-template-columns:minmax(220px,340px) 1fr;gap:18px;margin-top:14px}@media(max-width:820px){.row{grid-template-columns:1fr}}
video{width:100%;max-height:60vh;background:#000;border-radius:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card h2{margin:0 0 6px;font-size:17px}.help{color:var(--muted);font-size:13px;margin:0 0 12px}
.opts{display:flex;gap:10px;flex-wrap:wrap}.opts button{font:inherit;font-size:16px;padding:10px 18px;border-radius:999px;border:1px solid var(--line);background:#fafaf8;cursor:pointer}
.opts button.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.meta{color:var(--muted);font-size:13px;margin:8px 0}textarea{width:100%;min-height:48px;font:inherit;border:1px solid var(--line);border-radius:8px;padding:8px;margin-top:12px}
.nav{display:flex;gap:8px;margin-top:12px;align-items:center;flex-wrap:wrap}.nav button{font:inherit;padding:8px 14px;border-radius:8px;border:1px solid var(--line);background:var(--card);cursor:pointer}
#saved{color:var(--ok);font-size:13px}kbd{background:#efece6;border-radius:4px;padding:0 5px;font-size:12px}
</style></head><body>
<header><h1>Zero Sugar check</h1><div class="bar"><i id="prog"></i></div><span id="count">-</span></header>
<main><img id="sheet" class="sheet" alt="frame sheet">
<div class="row"><div><video id="vid" controls playsinline preload="metadata"></video><div class="meta" id="meta"></div></div>
<div class="card"><h2>Is Coca-Cola Zero Sugar packaging shown anywhere in this Short?</h2>
<p class="help">Zero Sugar: a black can, a black label or cap, or the words "Zero Sugar" / "Coke Zero" on a pack or on screen.
Not Zero Sugar: only red Coca-Cola, silver Diet/Light, other variants, or no pack at all (a logo on a sign or truck does not count).
<b>A glass bottle looks dark because of the drink inside - judge the label, can or cap colour.</b>
The sheet shows one frame per shot; play the video whenever a shot is unclear.</p>
<div class="opts"><button data-v="zero_sugar">Zero Sugar <kbd>1</kbd></button><button data-v="not_zero_sugar">Not Zero Sugar <kbd>2</kbd></button><button data-v="unsure">Unsure <kbd>3</kbd></button></div>
<textarea id="note" placeholder="Note (optional), e.g. which second the can appears"></textarea>
<div class="nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button><button id="nextopen">Next unanswered</button><span id="saved"></span></div></div></div></main>
<script>
let S=null,cur=0;const $=s=>document.querySelector(s);
async function load(){S=await (await fetch('/api/state')).json();const f=S.items.findIndex(it=>!it.researcher_answer);show(f<0?0:f);}
function progress(){const n=S.items.filter(it=>it.researcher_answer).length;$('#count').textContent=n+' / '+S.items.length+' answered';$('#prog').style.width=(100*n/S.items.length)+'%';}
function show(i){cur=Math.max(0,Math.min(i,S.items.length-1));const it=S.items[cur];
 $('#sheet').src='/sheet/'+it.order;const v=$('#vid');v.src='/media/'+it.order;v.load();
 $('#meta').innerHTML=(cur+1)+' of '+S.items.length+' &middot; <b>'+esc(it.account)+'</b> &middot; <a href="'+it.url+'" target="_blank" rel="noopener">open on YouTube</a><br>'+esc(it.title||'');
 document.querySelectorAll('.opts button').forEach(b=>b.classList.toggle('on',b.dataset.v===it.researcher_answer));
 $('#note').value=it.researcher_note||'';$('#saved').textContent='';progress();window.scrollTo(0,0);}
async function answer(v){const it=S.items[cur];it.researcher_answer=v;document.querySelectorAll('.opts button').forEach(b=>b.classList.toggle('on',b.dataset.v===v));
 if(await post(it.order,'researcher_answer',v))setTimeout(()=>{for(let k=1;k<=S.items.length;k++){const j=(cur+k)%S.items.length;if(!S.items[j].researcher_answer){show(j);return;}}$('#saved').textContent='All answered - saved.';},250);}
async function post(order,field,value){$('#saved').textContent='Saving...';try{const r=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({order:order,field:field,value:value})});
 if(!r.ok)throw new Error(await r.text());$('#saved').textContent='Saved';progress();return true;}catch(e){$('#saved').textContent='NOT saved - '+e.message;$('#saved').style.color='#b3261e';return false;}}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
document.querySelectorAll('.opts button').forEach(b=>b.onclick=()=>answer(b.dataset.v));
$('#note').onchange=e=>{S.items[cur].researcher_note=e.target.value;post(S.items[cur].order,'researcher_note',e.target.value);};
$('#prev').onclick=()=>show(cur-1);$('#next').onclick=()=>show(cur+1);
$('#nextopen').onclick=()=>{for(let k=1;k<=S.items.length;k++){const j=(cur+k)%S.items.length;if(!S.items[j].researcher_answer){show(j);return;}}};
document.addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA')return;const m={'1':'zero_sugar','2':'not_zero_sugar','3':'unsure'};
 if(m[e.key])answer(m[e.key]);if(e.key==='ArrowRight')show(cur+1);if(e.key==='ArrowLeft')show(cur-1);});
load();
</script></body></html>"""


class Handler(_CodingHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/state":
            items = load()[["order", "media_id", "url", "account", "title", "researcher_answer",
                            "researcher_note"]].to_dict("records")
            return self._send(200, json.dumps({"items": items}, ensure_ascii=False).encode("utf-8"),
                              "application/json; charset=utf-8")
        m = re.fullmatch(r"/(media|sheet)/(\d+)", path)
        if m:
            row = load()
            row = row[row["order"] == m.group(2)]
            if row.empty:
                return self._send(404, b"not found", "text/plain")
            col = "video_path" if m.group(1) == "media" else "sheet"
            f = config.ROOT / row.iloc[0][col].replace("\\", "/")
            if not f.exists():
                return self._send(404, b"not found", "text/plain")
            if m.group(1) == "media":
                return self._video(f)
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
    ap = argparse.ArgumentParser(description="Visual Zero Sugar check page (D-029).")
    ap.add_argument("--port", type=int, default=8775)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    df = load()
    missing = [r["media_id"] for _, r in df.iterrows()
               if not (config.ROOT / r["video_path"].replace("\\", "/")).exists()
               or not (config.ROOT / r["sheet"].replace("\\", "/")).exists()]
    if missing:
        raise SystemExit(f"video or sheet missing for: {missing}")
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
    print(f"Zero Sugar check page: {url}")
    print(f"{int((df['researcher_answer'] != '').sum())} of {len(df)} answered so far. Answers save to "
          f"{CHECK.relative_to(config.ROOT)}. Press Ctrl+C here to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Every answer you clicked is saved.")


if __name__ == "__main__":
    main()

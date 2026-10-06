"""Coding page for the 192 focus videos (proposal gaps P1-P9, D-049).

Same design as the 15 September coding page (`src/coding/app.py`, whose video serving it reuses):
the video plays on the left, the 14 questions of `src/coding/codebook_focus.py` sit on the right in
five groups, and every click is saved at once to `data/coding/focus_codes.csv`. Close it any time;
it reopens at the first unfinished video. Standard library only, bound to 127.0.0.1.

Blind by design (D-049): the page shows the video, its account and its caption or title - what any
viewer sees - and never likes, comments, views, followers, the engagement measure, the 15 September
codes, a Zero Sugar label or any automated output. There is no link to the original post, because
the post would show its likes.

Usage:
    python -m src.coding.focus_app              # opens the page in your browser
    python -m src.coding.focus_app --no-browser
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
from src.coding.codebook_focus import FIELDS, QUESTIONS, SEED  # noqa: E402

CODING = config.DATA / "coding"
SAMPLE = CODING / "focus_sample.csv"
CODES = CODING / "focus_codes.csv"
COLS = ["order", "platform", "media_id", *FIELDS, "notes", "first_saved_at", "completed_at"]
_LOCK = threading.Lock()


# ------------------------------------------------------------------ sample
def draw_sample() -> pd.DataFrame:
    """The 192 focus videos (frozen table, docs/08 section 6) in one shuffled order, fixed by SEED."""
    dv = pd.read_parquet(config.PROCESSED / "dependent_variable.parquet")
    focus = dv[dv["in_focus"] & (dv["dv_status"] == "ok")][["platform", "media_id"]]

    yt = pd.read_parquet(config.PROCESSED / "youtube_corpus.parquet")
    yt = pd.DataFrame({
        "platform": "youtube", "media_id": yt["video_id"], "account": yt["channel_title"],
        "caption": (yt["title"].fillna("") + "\n\n" + yt["description"].fillna("").str.slice(0, 600)).str.strip(),
    })
    ig = pd.read_parquet(config.PROCESSED / "instagram_corpus.parquet")
    ig = pd.DataFrame({
        "platform": "instagram", "media_id": ig["shortcode"],
        "account": ig["owner_username"].fillna(ig["source_handle"]),
        "caption": ig["caption"].fillna("").str.slice(0, 1200),
    })
    s = focus.merge(pd.concat([yt, ig], ignore_index=True), on=["platform", "media_id"], how="left",
                    validate="1:1")
    if len(s) != 192 or s["account"].isna().any():
        raise SystemExit(f"expected the 192 focus videos with their account and caption, got {len(s)}")
    s = s.sort_values(["platform", "media_id"]).sample(frac=1, random_state=SEED).reset_index(drop=True)
    s.insert(0, "order", range(1, len(s) + 1))
    return s


def video_file(platform: str, media_id: str) -> Path:
    return (config.MEDIA_YT if platform == "youtube" else config.MEDIA_IG) / f"{media_id}.mp4"


def load_sample() -> pd.DataFrame:
    if not SAMPLE.exists():          # drawn once; never redrawn, so the order cannot change mid-way
        CODING.mkdir(parents=True, exist_ok=True)
        draw_sample().to_csv(SAMPLE, index=False, encoding="utf-8")
    return pd.read_csv(SAMPLE, dtype={"order": str, "media_id": str}, keep_default_na=False)


def load_codes(sample: pd.DataFrame) -> pd.DataFrame:
    if CODES.exists():
        c = pd.read_csv(CODES, dtype=str, keep_default_na=False)
        for col in COLS:
            if col not in c.columns:
                c[col] = ""
        return c[COLS]
    c = sample[["order", "platform", "media_id"]].astype(str).copy()
    for col in COLS[3:]:
        c[col] = ""
    return c


def save_answer(sample: pd.DataFrame, media_id: str, field: str, value: str) -> dict:
    allowed = {q[0]: {v for v, _ in q[3]} for q in QUESTIONS}
    if field != "notes" and (field not in allowed or value not in allowed[field] | {""}):
        raise ValueError("invalid field or value")
    with _LOCK:
        codes = load_codes(sample)
        idx = codes.index[codes["media_id"] == media_id]
        if len(idx) != 1:
            raise ValueError("unknown video")
        i = idx[0]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        codes.at[i, field] = value.replace("\r", " ")[:2000]
        if not codes.at[i, "first_saved_at"]:
            codes.at[i, "first_saved_at"] = now
        done = all(codes.at[i, f] for f in FIELDS)
        codes.at[i, "completed_at"] = (codes.at[i, "completed_at"] or now) if done else ""
        CODING.mkdir(parents=True, exist_ok=True)
        tmp = CODES.with_suffix(".tmp")
        codes.to_csv(tmp, index=False, encoding="utf-8")
        tmp.replace(CODES)
        return {"complete": int((codes["completed_at"] != "").sum()), "total": len(codes), "row_done": done}


# ------------------------------------------------------------------ page
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Video coding - 192 videos</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e3e1dc;--ok:#1f7a3a;--warn:#b3261e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
header{display:flex;align-items:center;gap:14px;padding:10px 20px;background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:3;flex-wrap:wrap}
header h1{font-size:16px;margin:0;font-weight:650}.bar{flex:1;min-width:120px;height:8px;background:var(--line);border-radius:4px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--ok);width:0}#count{font-variant-numeric:tabular-nums;color:var(--muted);white-space:nowrap}
header input,header label{font:inherit;font-size:13px}header input[type=number]{width:92px;padding:5px 8px;border:1px solid var(--line);border-radius:8px}
main{display:grid;grid-template-columns:minmax(260px,400px) 1fr;gap:20px;padding:16px 20px;max-width:1240px;margin:auto}
@media(max-width:860px){main{grid-template-columns:1fr}.left{position:static!important}}
.left{position:sticky;top:64px;align-self:start}
.left video{width:100%;max-height:68vh;background:#000;border-radius:10px;display:block}
.meta{margin:10px 2px 6px;color:var(--muted);font-size:13px}.meta b{color:var(--ink)}
.caption{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;max-height:20vh;overflow:auto;white-space:pre-wrap;font-size:13px}
.blind{color:var(--muted);font-size:12px;margin-top:8px}
.sec{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:14px 2px 6px;font-weight:650}
.sec:first-child{margin-top:0}
.q{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin-bottom:8px}
.q.done{border-color:#bfd9c6}.q h2{font-size:15px;margin:0 0 6px}.q p{margin:8px 0 0;color:var(--muted);font-size:12.5px}
body.nohelp .q p{display:none}
.num{color:var(--muted);font-weight:500;margin-right:4px}
.opts{display:flex;flex-wrap:wrap;gap:6px}.opts button{font:inherit;font-size:14px;padding:6px 13px;border-radius:999px;border:1px solid var(--line);background:#fafaf8;cursor:pointer}
.opts button:hover{border-color:#bbb}.opts button.on{background:var(--ink);border-color:var(--ink);color:#fff}
textarea{width:100%;min-height:50px;font:inherit;border:1px solid var(--line);border-radius:8px;padding:8px}
.nav{display:flex;gap:8px;align-items:center;margin:10px 0 30px;flex-wrap:wrap}.nav button{font:inherit;padding:8px 16px;border-radius:8px;border:1px solid var(--line);background:var(--card);cursor:pointer}
.nav .primary{background:var(--ink);color:#fff;border-color:var(--ink)}#saved{color:var(--ok);font-size:13px}
#answered{font-size:13px;color:var(--muted)}#answered.all{color:var(--ok);font-weight:600}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;background:#efece6;font-size:12px;margin-right:6px}
.finished{padding:40px;text-align:center}
</style></head><body>
<header><h1>Video coding &middot; 192 videos</h1><div class="bar"><i id="prog"></i></div><span id="count">-</span>
<label><input type="checkbox" id="help" checked> definitions</label>
<input id="jump" type="number" min="1" placeholder="Go to #" title="Type a video number and press Enter"></header>
<main><section class="left"><video id="vid" controls playsinline preload="metadata"></video>
<div class="meta" id="meta"></div><div class="caption" id="cap"></div>
<div class="blind">Watch with the sound on. This page never shows likes, comments, views, followers, earlier codes or any automatic label.</div></section>
<section id="right"></section></main>
<script>
let S=null,cur=0;
const $=s=>document.querySelector(s);
function store(k,v){try{if(v===undefined)return localStorage.getItem(k);localStorage.setItem(k,v);}catch(e){return null;}}
async function load(){S=await (await fetch('/api/state')).json();const f=S.items.findIndex(it=>!done(it.media_id));show(f<0?0:f);}
function done(id){const c=S.codes[id]||{};return S.questions.every(q=>c[q.field]);}
function nAnswered(id){const c=S.codes[id]||{};return S.questions.filter(q=>c[q.field]).length;}
function progress(){const n=S.items.filter(it=>done(it.media_id)).length;$('#count').textContent=n+' / '+S.items.length+' complete';$('#prog').style.width=(100*n/S.items.length)+'%';
 const it=S.items[cur];if(!it)return;const a=nAnswered(it.media_id),t=S.questions.length,el=$('#answered');if(el){el.textContent=a+' of '+t+' answered'+(a===t?' - complete':'');el.classList.toggle('all',a===t);}}
function show(i){cur=Math.max(0,Math.min(i,S.items.length-1));const it=S.items[cur],c=S.codes[it.media_id]||{};
 const v=$('#vid');v.src='/media/'+it.order;v.load();
 $('#meta').innerHTML='<span class="pill">#'+it.order+' of '+S.items.length+'</span><span class="pill">'+(it.platform==='youtube'?'YouTube Short':'Instagram Reel')+'</span> <b>'+esc(it.account||'')+'</b>';
 $('#cap').textContent=it.caption||'(no caption or title)';
 let h='',sec=null,k=0;for(const q of S.questions){k++;if(q.section!==sec){h+='<div class="sec">'+esc(q.section)+(q.section==='Sound'?' - sound on':'')+'</div>';sec=q.section;}
  h+='<div class="q'+(c[q.field]?' done':'')+'" id="q_'+q.field+'"><h2><span class="num">'+k+'.</span>'+esc(q.question)+'</h2><div class="opts">';
  for(const [val,lab] of q.options){h+='<button data-f="'+q.field+'" data-v="'+val+'" class="'+(c[q.field]===val?'on':'')+'">'+esc(lab)+'</button>';}
  h+='</div><p>'+esc(q.help)+'</p></div>';}
 h+='<div class="q"><h2>Notes (optional)</h2><textarea id="notes" placeholder="Anything unusual about this video">'+esc(c.notes||'')+'</textarea></div>';
 h+='<div class="nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button><button class="primary" id="nextopen">Next unfinished</button><span id="answered"></span><span id="saved"></span></div>';
 $('#right').innerHTML=h;progress();
 document.querySelectorAll('.opts button').forEach(b=>b.onclick=()=>pick(b.dataset.f,b.dataset.v));
 $('#notes').onchange=e=>save(it.media_id,'notes',e.target.value);
 $('#prev').onclick=()=>show(cur-1);$('#next').onclick=()=>show(cur+1);
 $('#nextopen').onclick=()=>{for(let j=1;j<=S.items.length;j++){const x=(cur+j)%S.items.length;if(!done(S.items[x].media_id)){show(x);return;}}finished();};
 window.scrollTo(0,0);}
function finished(){$('#right').innerHTML='<div class="q finished"><h2>All '+S.items.length+' videos are coded.</h2><p style="display:block">Your answers are saved. You can still go back and change any of them.</p><div class="nav" style="justify-content:center"><button id="back">Review from the start</button></div></div>';$('#back').onclick=()=>show(0);}
async function pick(field,val){const it=S.items[cur];S.codes[it.media_id]=S.codes[it.media_id]||{};S.codes[it.media_id][field]=val;
 document.querySelectorAll('button[data-f="'+field+'"]').forEach(b=>b.classList.toggle('on',b.dataset.v===val));$('#q_'+field).classList.add('done');await save(it.media_id,field,val);}
async function save(id,field,value){const el=$('#saved');el.style.color='';el.textContent='Saving...';
 try{const r=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media_id:id,field:field,value:value})});
  if(!r.ok)throw new Error(await r.text());el.textContent='Saved';progress();}catch(e){el.textContent='NOT saved - '+e.message;el.style.color='#b3261e';}}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
const hb=$('#help');hb.checked=store('focus_help')!=='off';document.body.classList.toggle('nohelp',!hb.checked);
hb.onchange=()=>{document.body.classList.toggle('nohelp',!hb.checked);store('focus_help',hb.checked?'on':'off');};
$('#jump').addEventListener('keydown',e=>{if(e.key==='Enter'){const n=parseInt(e.target.value,10);if(n>=1&&n<=S.items.length){show(n-1);e.target.value='';e.target.blur();}}});
document.addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA'||e.target.tagName==='INPUT')return;if(e.key==='ArrowRight')show(cur+1);if(e.key==='ArrowLeft')show(cur-1);});
load();
</script></body></html>"""


class Handler(_CodingHandler):
    sample: pd.DataFrame = None  # set in main()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/state":
            s = self.sample
            codes = load_codes(s).set_index("media_id")
            state = {
                "items": s[["order", "platform", "media_id", "account", "caption"]].to_dict("records"),
                "codes": {mid: {k: v for k, v in row.items() if k in FIELDS + ["notes"] and v}
                          for mid, row in codes.to_dict("index").items()},
                "questions": [{"field": f, "question": q, "help": h, "options": o, "section": sec}
                              for f, q, h, o, sec, _ in QUESTIONS],
            }
            return self._send(200, json.dumps(state, ensure_ascii=False).encode("utf-8"),
                              "application/json; charset=utf-8")
        m = re.fullmatch(r"/media/(\d+)", path)
        if m:
            row = self.sample[self.sample["order"] == m.group(1)]
            if row.empty:
                return self._send(404, b"not found", "text/plain")
            f = video_file(row.iloc[0]["platform"], row.iloc[0]["media_id"])
            return self._video(f) if f.exists() else self._send(404, b"not found", "text/plain")
        return self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path != "/api/save":
            return self._send(404, b"not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > 20000:
                raise ValueError("too large")
            data = json.loads(self.rfile.read(n) or b"{}")
            out = save_answer(self.sample, str(data["media_id"]), str(data["field"]), str(data.get("value", "")))
            return self._send(200, json.dumps(out).encode(), "application/json")
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            return self._send(400, str(exc).encode(), "text/plain")


def main() -> None:
    ap = argparse.ArgumentParser(description="Coding page for the 192 focus videos (D-049).")
    ap.add_argument("--port", type=int, default=8785)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    Handler.sample = load_sample()
    missing = [r.media_id for r in Handler.sample.itertuples() if not video_file(r.platform, r.media_id).exists()]
    if missing:
        raise SystemExit(f"video files missing for: {missing}")

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
    done = int((load_codes(Handler.sample)["completed_at"] != "").sum())
    print(f"Coding page (192 videos): {url}")
    print(f"{done} of {len(Handler.sample)} videos coded so far. Answers save to "
          f"{CODES.relative_to(config.ROOT)}. Press Ctrl+C here to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Everything you clicked is saved.")


if __name__ == "__main__":
    main()

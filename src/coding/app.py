"""Manual coding page (task 4.0/4.1, D-023).

A private page on this laptop for coding the fixed random subset: the video plays on the left,
five questions on the right, and every click is saved at once to
`data/coding/manual_codes.csv`. Close it any time; it reopens at the first unfinished video.

Standard library only (no Flask), bound to 127.0.0.1 so nothing is reachable from outside the
laptop. Video files are served by sample position, never by path, with byte-range support so
the player can seek.

The page is deliberately blind: it shows the video, its account and its caption or title -
the same things any viewer sees - and never the corpus group, a Zero Sugar label or any
automated output.

Usage:
    python -m src.coding.app              # opens the page in your browser
    python -m src.coding.app --no-browser
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.codebook import FIELDS, QUESTIONS, SAMPLE_SIZE, SEED  # noqa: E402

CODING = config.DATA / "coding"
SAMPLE = CODING / "sample.csv"
CODES = CODING / "manual_codes.csv"
_LOCK = threading.Lock()


# ------------------------------------------------------------------ sample
def draw_sample() -> pd.DataFrame:
    """Fixed random subset, stratified by platform, in a shuffled viewing order."""
    man = pd.read_csv(config.MEDIA / "download_manifest.csv", dtype={"media_id": str})
    man = man[man["status"] == "ok"].drop_duplicates(["platform", "media_id"], keep="last")
    parts = []

    yt = pd.read_parquet(config.PROCESSED / "youtube_corpus.parquet")
    yt = yt[yt["in_corpus"]]
    yt = yt[yt["video_id"].isin(man.loc[man["platform"] == "youtube", "media_id"])]
    yt = yt.sample(n=SAMPLE_SIZE["youtube"], random_state=SEED)
    parts.append(pd.DataFrame({
        "platform": "youtube", "media_id": yt["video_id"],
        "url": "https://www.youtube.com/shorts/" + yt["video_id"],
        "account": yt["channel_title"],
        "caption": (yt["title"].fillna("") + "\n\n" + yt["description"].fillna("").str.slice(0, 600)).str.strip(),
    }))

    ig = pd.read_parquet(config.PROCESSED / "instagram_corpus.parquet")
    ig = ig[ig["in_corpus"]]
    ig = ig[ig["shortcode"].isin(man.loc[man["platform"] == "instagram", "media_id"])]
    ig = ig.sample(n=SAMPLE_SIZE["instagram"], random_state=SEED)
    parts.append(pd.DataFrame({
        "platform": "instagram", "media_id": ig["shortcode"], "url": ig["permalink"],
        "account": ig["owner_username"].fillna(ig["source_handle"]),
        "caption": ig["caption"].fillna("").str.slice(0, 1200),
    }))

    s = pd.concat(parts, ignore_index=True).sample(frac=1, random_state=SEED).reset_index(drop=True)
    s.insert(0, "sample_order", range(1, len(s) + 1))
    s["video_file"] = [str((config.MEDIA_YT if p == "youtube" else config.MEDIA_IG) / f"{m}.mp4")
                       for p, m in zip(s["platform"], s["media_id"])]
    return s


def load_sample() -> pd.DataFrame:
    if not SAMPLE.exists():
        CODING.mkdir(parents=True, exist_ok=True)
        s = draw_sample()
        s.drop(columns=["video_file"]).to_csv(SAMPLE, index=False, encoding="utf-8")
    s = pd.read_csv(SAMPLE, dtype={"media_id": str}, keep_default_na=False)
    s["video_file"] = [str((config.MEDIA_YT if p == "youtube" else config.MEDIA_IG) / f"{m}.mp4")
                       for p, m in zip(s["platform"], s["media_id"])]
    return s


def load_codes(sample: pd.DataFrame) -> pd.DataFrame:
    cols = ["sample_order", "platform", "media_id", *FIELDS, "notes", "first_saved_at", "completed_at"]
    if CODES.exists():
        c = pd.read_csv(CODES, dtype=str, keep_default_na=False)
        for col in cols:
            if col not in c.columns:
                c[col] = ""
        return c[cols]
    c = sample[["sample_order", "platform", "media_id"]].astype(str).copy()
    for col in cols[3:]:
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
        return {"complete": int((codes["completed_at"] != "").sum()), "total": len(codes),
                "row_done": done}


# ------------------------------------------------------------------ page
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Video coding</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e3e1dc;--accent:#b3261e;--ok:#1f7a3a;--sel:#1d1d1f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
header{display:flex;align-items:center;gap:16px;padding:10px 20px;background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:2}
header h1{font-size:16px;margin:0;font-weight:650}.bar{flex:1;height:8px;background:var(--line);border-radius:4px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--ok);width:0}#count{font-variant-numeric:tabular-nums;color:var(--muted);white-space:nowrap}
main{display:grid;grid-template-columns:minmax(260px,420px) 1fr;gap:20px;padding:18px 20px;max-width:1200px;margin:auto}
@media(max-width:820px){main{grid-template-columns:1fr}}
.left video{width:100%;max-height:74vh;background:#000;border-radius:10px;display:block}
.meta{margin:10px 2px 6px;color:var(--muted);font-size:13px}.meta b{color:var(--ink)}
.caption{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;max-height:22vh;overflow:auto;white-space:pre-wrap;font-size:13px}
.q{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:10px}
.q.done{border-color:#bfd9c6}.q h2{font-size:15px;margin:0 0 4px}.q p{margin:0 0 9px;color:var(--muted);font-size:13px}
.opts{display:flex;flex-wrap:wrap;gap:8px}.opts button{font:inherit;padding:7px 14px;border-radius:999px;border:1px solid var(--line);background:#fafaf8;cursor:pointer}
.opts button:hover{border-color:#bbb}.opts button.on{background:var(--sel);border-color:var(--sel);color:#fff}
textarea{width:100%;min-height:54px;font:inherit;border:1px solid var(--line);border-radius:8px;padding:8px}
.nav{display:flex;gap:8px;align-items:center;margin-top:6px;flex-wrap:wrap}.nav button{font:inherit;padding:8px 16px;border-radius:8px;border:1px solid var(--line);background:var(--card);cursor:pointer}
.nav .primary{background:var(--ink);color:#fff;border-color:var(--ink)}#saved{color:var(--ok);font-size:13px;min-width:60px}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;background:#efece6;font-size:12px;margin-right:6px}
.finished{padding:40px;text-align:center}
</style></head><body>
<header><h1>Video coding</h1><div class="bar"><i id="prog"></i></div><span id="count">-</span><input id="jump" type="number" min="1" placeholder="Go to #" title="Type a video number and press Enter" style="width:92px;font:inherit;padding:5px 8px;border:1px solid var(--line);border-radius:8px"></header>
<main><section class="left"><video id="vid" controls playsinline preload="metadata"></video>
<div class="meta" id="meta"></div><div class="caption" id="cap"></div></section>
<section id="right"></section></main>
<script>
let S=null,cur=0;
const $=s=>document.querySelector(s);
async function load(){S=await (await fetch('/api/state')).json();const f=S.items.findIndex(it=>!done(it.media_id));show(f<0?0:f);}
function done(id){const c=S.codes[id]||{};return S.questions.every(q=>c[q.field]);}
function progress(){const n=S.items.filter(it=>done(it.media_id)).length;$('#count').textContent=n+' / '+S.items.length+' complete';$('#prog').style.width=(100*n/S.items.length)+'%';}
function show(i){cur=Math.max(0,Math.min(i,S.items.length-1));const it=S.items[cur],c=S.codes[it.media_id]||{};
 const v=$('#vid');v.src='/media/'+it.sample_order;v.load();
 $('#meta').innerHTML='<span class="pill">'+(cur+1)+' of '+S.items.length+'</span><span class="pill">'+(it.platform==='youtube'?'YouTube Short':'Instagram Reel')+'</span> <b>'+esc(it.account||'')+'</b> &middot; <a href="'+it.url+'" target="_blank" rel="noopener">open original</a>';
 $('#cap').textContent=it.caption||'(no caption available)';
 let h='';for(const q of S.questions){h+='<div class="q'+(c[q.field]?' done':'')+'" id="q_'+q.field+'"><h2>'+esc(q.question)+'</h2><p>'+esc(q.help)+'</p><div class="opts">';
  for(const [val,lab] of q.options){h+='<button data-f="'+q.field+'" data-v="'+val+'" class="'+(c[q.field]===val?'on':'')+'">'+esc(lab)+'</button>';}h+='</div></div>';}
 h+='<div class="q"><h2>Notes (optional)</h2><textarea id="notes" placeholder="Anything unusual about this video">'+esc(c.notes||'')+'</textarea></div>';
 h+='<div class="nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button><button class="primary" id="nextopen">Next unfinished</button><span id="saved"></span></div>';
 $('#right').innerHTML=h;progress();
 document.querySelectorAll('.opts button').forEach(b=>b.onclick=()=>pick(b.dataset.f,b.dataset.v));
 $('#notes').onchange=e=>save(it.media_id,'notes',e.target.value);
 $('#prev').onclick=()=>show(cur-1);$('#next').onclick=()=>show(cur+1);
 $('#nextopen').onclick=()=>{for(let k=1;k<=S.items.length;k++){const j=(cur+k)%S.items.length;if(!done(S.items[j].media_id)){show(j);return;}}finished();};
 window.scrollTo(0,0);}
function finished(){$('#right').innerHTML='<div class="q finished"><h2>All '+S.items.length+' videos are coded.</h2><p>Your answers are saved. You can still go back and change any of them.</p><div class="nav" style="justify-content:center"><button id="back">Review from the start</button></div></div>';$('#back').onclick=()=>show(0);}
async function pick(field,val){const it=S.items[cur];S.codes[it.media_id]=S.codes[it.media_id]||{};S.codes[it.media_id][field]=val;
 document.querySelectorAll('button[data-f="'+field+'"]').forEach(b=>b.classList.toggle('on',b.dataset.v===val));$('#q_'+field).classList.add('done');await save(it.media_id,field,val);}
async function save(id,field,value){$('#saved').textContent='Saving...';
 try{const r=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media_id:id,field:field,value:value})});
  if(!r.ok)throw new Error(await r.text());$('#saved').textContent='Saved';progress();}catch(e){$('#saved').textContent='Not saved - '+e.message;$('#saved').style.color='#b3261e';}}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
document.getElementById('jump').addEventListener('keydown',e=>{if(e.key==='Enter'){const n=parseInt(e.target.value,10);if(n>=1&&n<=S.items.length){show(n-1);e.target.value='';e.target.blur();}}});
document.addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA'||e.target.tagName==='INPUT')return;if(e.key==='ArrowRight')show(cur+1);if(e.key==='ArrowLeft')show(cur-1);});
load();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    sample: pd.DataFrame = None  # set in main()

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/state":
            s = self.sample
            codes = load_codes(s).set_index("media_id")
            state = {
                "items": s[["sample_order", "platform", "media_id", "url", "account", "caption"]]
                .to_dict("records"),
                "codes": {mid: {k: v for k, v in row.items() if k in FIELDS + ["notes"] and v}
                          for mid, row in codes.to_dict("index").items()},
                "questions": [{"field": f, "question": q, "help": h, "options": o}
                              for f, q, h, o in QUESTIONS],
            }
            return self._send(200, json.dumps(state, ensure_ascii=False).encode("utf-8"),
                              "application/json; charset=utf-8")
        m = re.fullmatch(r"/media/(\d+)", path)
        if m:
            row = self.sample[self.sample["sample_order"].astype(int) == int(m.group(1))]
            if row.empty or not Path(row.iloc[0]["video_file"]).exists():
                return self._send(404, b"not found", "text/plain")
            return self._video(Path(row.iloc[0]["video_file"]))
        return self._send(404, b"not found", "text/plain")

    def _video(self, f: Path) -> None:
        size = f.stat().st_size
        start, end, status = 0, size - 1, 200
        rng = self.headers.get("Range")
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng or "")
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
            else:
                start = max(size - int(m.group(2)), 0)
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            status = 206
        self.send_response(status)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            with open(f, "rb") as fh:
                fh.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = fh.read(min(1 << 16, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass  # the player cancelled a range request while seeking - normal

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
    ap = argparse.ArgumentParser(description="Manual video coding page.")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    Handler.sample = load_sample()
    missing = [r.media_id for r in Handler.sample.itertuples() if not Path(r.video_file).exists()]
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
    print(f"Video coding page: {url}")
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

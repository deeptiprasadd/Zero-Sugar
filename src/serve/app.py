"""Task 12.5 - the tool's web page (D-059): a form, a background job, a result screen and an about page.

    python -m src.serve.app            # http://127.0.0.1:5055 - this computer only
    python -m src.serve.app --check    # render every saved result and refuse words the wording rules forbid

One video is measured at a time (the graphics card); each job is saved under data/interim/serve/jobs/ so a
finished result survives a restart. The page shows only what D-046, D-054 and D-059 allow; every sentence comes
from `src/serve/wording.py`. The pages were redesigned with a box of example videos in D-065 (`src/serve/examples.py`).

With COKE_DEMO=1 (the online demo on Render, D-066) the site shows only the six examples' saved results, the About
page and /healthz: nothing is measured, so no video libraries or models for measuring are loaded.

With COKE_PUBLIC=1 (the free public server, D-069; started by gunicorn) the full tool runs for anyone: the queue starts
when the app loads, and the six examples open their saved results (their videos are not published).
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading
import traceback
import uuid
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.serve import examples as EX  # noqa: E402
from src.serve import wording as W  # noqa: E402
from src.serve.measure import SERVE, StepFailed  # noqa: E402

HOST, PORT = "127.0.0.1", 5055
DEMO = EX.DEMO
PUBLIC = os.environ.get("COKE_PUBLIC") == "1"     # D-069
SAVED = DEMO or PUBLIC                              # examples open saved results
CRLF, LF = chr(13) + chr(10), chr(10)
JOBS = SERVE / "jobs"
UPLOADS = SERVE / "uploads"

app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
app.config["MAX_CONTENT_LENGTH"] = 210 * 1024 ** 2
QUEUE: "queue.Queue[str]" = queue.Queue()
LOCK = threading.Lock()


# ------------------------------------------------------------------------------------------ jobs
def job_file(jid: str) -> Path:
    return JOBS / f"{jid}.json"


def load_job(jid: str) -> dict | None:
    if not jid.replace("-", "").isalnum():
        return None
    p = job_file(jid)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    from src.serve import drive_store                          # D-071: after a restart, read it back from Drive
    return drive_store.load(jid) if drive_store.enabled() else None


def save_job(job: dict) -> None:
    JOBS.mkdir(parents=True, exist_ok=True)
    with LOCK:
        job_file(job["id"]).write_text(json.dumps(job, ensure_ascii=False, indent=1, default=float), encoding="utf-8")


def hand_code_questions() -> list[tuple[str, str]]:
    from src.coding.focus_codes import H, LABEL
    return [(h, LABEL[h]) for h in H]


def run_job(jid: str) -> None:
    from src.serve import intake
    job = load_job(jid)
    job["status"], job["started"] = "running", datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_job(job)
    inp = job["inputs"]

    def progress(line: str) -> None:
        parts = line.split()
        name = W.GROUP_NAMES.get(parts[0], parts[0]) if parts else line
        job["progress"].append(f"{name} - done ({parts[1]} s)" if len(parts) > 1 else name)
        save_job(job)

    video = None
    try:
        if inp["link"]:
            video, d = intake.fetch_link(inp["link"])
            platform, title = d["platform"], d["title"]
            caption = "" if inp["no_caption"] else (inp["caption"] if inp["caption"] else d["caption"])
            followers = inp["followers"]
            if followers is None and d.get("followers_from_link"):
                followers, job["followers_from_link"] = float(d["followers_from_link"]), True
            job["link_details"] = {k: d.get(k) for k in ("platform", "video_id", "account", "duration_sec")}
        elif inp.get("example"):                                    # D-065: a video from the study's collection
            from src.serve import examples
            ex = examples.get(inp["example"])
            if ex is None:
                raise StepFailed("that example is no longer available")
            video = intake.store_upload(Path(ex["path"]))
            platform, title = ex["platform"], ex["title"]
            caption = "" if inp["no_caption"] else (inp["caption"] or None)
            followers = inp["followers"]
        else:
            video = intake.store_upload(Path(inp["upload_path"]))
            platform, title = inp["platform"], None
            caption = "" if inp["no_caption"] else (inp["caption"] or None)
            followers = inp["followers"]
        job["platform"], job["caption_used"] = platform, caption
        collab = inp["collab"] if platform == "instagram" else None
        r = intake.evaluate(video, platform, caption, title, followers, collab, inp["answers"] or None, log=progress)
        job["result"], job["status"] = r, "done"
    except StepFailed as exc:
        job["status"], job["message"] = "refused", str(exc)
    except Exception as exc:                                   # recorded for the person, then logged
        traceback.print_exc()
        job["status"], job["message"] = "error", f"Something went wrong while measuring ({type(exc).__name__})."
    job["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_job(job)
    from src.serve import drive_store                          # D-071: results only, never videos
    if drive_store.enabled():
        work = (job.get("result") or {}).get("video", {}).get("work")
        drive_store.delete_video_copies(job, inp.get("upload_path"), video, Path(work) if work else None)
        drive_store.save_in_background(job)


def worker() -> None:
    while True:
        jid = QUEUE.get()
        try:
            run_job(jid)
        finally:
            QUEUE.task_done()


# ------------------------------------------------------------------------------------------ views
def bar_pct(p: dict | None) -> float | None:
    """Where a value sits among the 192, 0-100, for the small position bar (D-065); beyond the range = the end."""
    if not p or p.get("pct") is None:
        return None
    return {"below": 0.0, "above": 100.0}.get(p.get("beyond"), max(0.0, min(100.0, float(p["pct"]))))


def result_view(job: dict) -> dict:
    """Everything the result page shows, as text, from the saved result (no measuring here)."""
    from src.serve.pipeline import artefacts
    art = artefacts()
    r, platform = job["result"], job["platform"]
    shares = art["schema"]["flag_shares"]
    caption = job.get("caption_used")
    rows = []
    for key, (name, kind) in W.FEATURES.items():
        dg = r["diagnostics"].get(key, {})
        v = dg.get("value")
        if kind == "yesno":
            low_all, low_plat = f"{shares[key]['all']:.0%} yes", f"{shares[key][platform]:.0%} yes"
        else:
            low_all, low_plat = W.pct_text(dg.get("among_192")), W.pct_text(dg.get(f"among_{platform}"))
        rows.append({"name": name, "value": W.value_text(key, v, len(caption) if caption is not None else None),
                     "all": low_all, "platform": low_plat,
                     "bar": None if kind == "yesno" else bar_pct(dg.get("among_192"))})
    hand = []
    for h, d in (r.get("hand_codes") or {}).items():
        hand.append({"label": d["label"][:1].upper() + d["label"][1:], "answer": "yes" if d["answer"] else "no",
                     "all": f"{d['share_among_192']:.0%}", "platform": f"{d[f'share_among_{platform}']:.0%}"})
    drivers, others = None, None
    if platform == "instagram":                                     # 12.6: model B only, three features (D-060)
        import numpy as np
        import pandas as pd
        from src.serve.explain_video import explain
        X = pd.DataFrame([{k: (np.nan if x is None else x) for k, x in r["model_inputs"].items()}])
        e = explain(X, art)
        drivers, others = W.driver_lines(e), W.others_line(e)
    if "speech_unclear" not in r:                                  # results saved before this flag existed
        import json as _json
        from src.serve.pipeline import speech_unclear
        recs = list(Path(r["video"]["work"]).glob("features/*.json"))
        r["speech_unclear"] = bool(recs) and speech_unclear(_json.loads(recs[0].read_text(encoding="utf-8")))
    b = r.get("base_rate")
    kpi = None
    if b:
        kpi = {"rate": W.rate_text(b["rate_typical"]), "lo": W.rate_text(b["rate_80"][0]),
               "hi": W.rate_text(b["rate_80"][1]), "clo": W.count_text(b["likes_comments_80"][0]),
               "chi": W.count_text(b["likes_comments_80"][1]), "followers": f"{b['followers']:,.0f}"}
    ig_pos = (r.get("instagram_score") or {}).get("higher_than_pct_of_120")
    return {"kpi": kpi, "ig_pos": ig_pos,"notices": W.top_notices(r, job["inputs"].get("zero_sugar"), art["schema"]),   # 12.7
            "certainty": W.certainty(b) if b else None,
            "youtube_range": W.youtube_range_note(b) if (b and platform == "youtube") else None,
            "drivers": drivers, "others": others, "no_drivers": W.NO_DRIVERS_YOUTUBE if platform == "youtube" else None,
            "cannot": W.CANNOT, "checks": W.checks_line(art["card"]["gates"], art["card"].get("gates_plain")),
            "platform": W.PLATFORM[platform], "platform_key": platform,
            "base": W.base_sentence(r["base_rate"], platform) if r.get("base_rate") else None,
            "followers_from_link": job.get("followers_from_link", False),
            "ig": W.ig_sentence(r["instagram_score"]) if r.get("instagram_score") else None,
            "rows": rows, "hand": hand, "missing": W.missing_lines(r["missing"], platform),
            "seconds": r["timing"]["total_sec"], "reused": r.get("reused_saved_measurement", False),
            "meaning": W.meaning(r, platform), "tips": W.worth_testing(r, platform),   # D-067
            "measured_on": W.measured_on_line(r)}                                           # D-069


def form_page(**kw):
    ex, ex_json = EX.for_page()
    return render_template("index.html", T=W.TEXT, questions=hand_code_questions(), examples=ex,
                           examples_json=ex_json, demo=DEMO, **kw)


@lru_cache(maxsize=None)
def demo_page(key: str) -> str | None:
    """D-066: the result page of one example, built from its saved result (no measuring)."""
    e = EX.get(key)
    if e is None:
        return None
    r = EX.saved_result(key)
    r["reused_saved_measurement"] = True
    job = {"id": key, "platform": e["platform"], "caption_used": e["caption"], "result": r,
           "inputs": {"upload_name": f"example: {e['label']}", "link": None, "zero_sugar": e["zero_sugar"]}}
    return render_template("result.html", T=W.TEXT, W=W, job=job, v=result_view(job), example=e, example_saved=True)


@app.context_processor
def mode():
    from src.serve import drive_store
    return {"demo": DEMO, "public": PUBLIC, "saved": SAVED, "drive": drive_store.enabled()}


# ------------------------------------------------------------------------------------------ quick check (D-072)
def quick_view(job: dict) -> dict:
    from src.serve.pipeline import artefacts
    from src.serve.quick import CAPTION_KEYS
    art = artefacts()
    r, platform = job["result"], job["platform"]
    shares = art["schema"]["flag_shares"]
    rows = []
    for key in CAPTION_KEYS:
        dg = r["diagnostics"].get(key)
        if dg is None:
            continue
        name, kind = W.FEATURES[key]
        if kind == "yesno":
            low_all, low_plat = f"{shares[key]['all']:.0%} yes", f"{shares[key][platform]:.0%} yes"
        else:
            low_all, low_plat = W.pct_text(dg.get("among_192")), W.pct_text(dg.get(f"among_{platform}"))
        rows.append({"name": name, "value": W.value_text(key, dg.get("value"), job.get("caption_chars")),
                     "all": low_all, "platform": low_plat, "bar": None if kind == "yesno" else bar_pct(dg.get("among_192"))})
    hand = [{"label": d["label"][:1].upper() + d["label"][1:], "answer": "yes" if d["answer"] else "no",
             "all": f"{d['share_among_192']:.0%}", "platform": f"{d[f'share_among_{platform}']:.0%}"}
            for d in (r.get("hand_codes") or {}).values()]
    b = r.get("base_rate")
    kpi = None
    if b:
        kpi = {"rate": W.rate_text(b["rate_typical"]), "lo": W.rate_text(b["rate_80"][0]),
               "hi": W.rate_text(b["rate_80"][1]), "followers": f"{b['followers']:,.0f}"}
    return {"kpi": kpi, "certainty": W.certainty(b) if b else None,
            "youtube_range": W.youtube_range_note(b) if (b and platform == "youtube") else None,
            "base": W.base_sentence(b, platform) if b else None, "platform": W.PLATFORM[platform],
            "rows": rows, "hand": hand, "caption_given": r.get("caption_given"),
            "meaning": W.meaning(r, platform), "tips": W.worth_testing(r, platform), "cannot": W.CANNOT,
            "checks": W.checks_line(art["card"]["gates"], art["card"].get("gates_plain"))}


@app.post("/quick")
def quick_submit():
    f = request.form
    errors = []
    platform = f.get("platform")
    if platform not in ("instagram", "youtube"):
        errors.append("Choose the platform.")
    followers = None
    try:
        followers = float((f.get("followers") or "").replace(",", "").strip())
        if followers <= 0:
            raise ValueError
    except ValueError:
        errors.append("Enter the account's follower count as a positive number.")
    if errors:
        return form_page(errors=errors, form=f), 400
    raw = (f.get("caption") or "").replace(CRLF, LF)
    caption = "" if f.get("no_caption") == "on" else (raw if raw.strip() else None)
    answers = {h: (1.0 if f.get(h) == "yes" else 0.0) for h, _ in hand_code_questions() if f.get(h) in ("yes", "no")}
    from src.serve import quick
    r = quick.check(platform, followers, caption, answers or None)
    job = {"id": "q" + uuid.uuid4().hex[:11], "kind": "quick", "status": "done", "platform": platform,
           "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "caption_chars": len(caption) if caption is not None else None,
           "inputs": {"platform": platform, "followers": followers, "caption_given": caption is not None,
                      "answers": answers}, "result": r}
    save_job(job)
    from src.serve import drive_store
    drive_store.save_in_background(job)
    return redirect(url_for("quick_page", qid=job["id"]))


@app.get("/quick/<qid>")
def quick_page(qid: str):
    job = load_job(qid)
    if job is None or job.get("kind") != "quick":
        abort(404)
    return render_template("quick.html", T=W.TEXT, W=W, job=job, v=quick_view(job))


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/example/<key>")
def example_page(key: str):
    html = demo_page(key) if SAVED else None
    if html is None:
        abort(404)
    return html


@app.get("/")
def index():
    return form_page()


@app.post("/submit")
def submit():
    f = request.form
    if SAVED and (f.get("example") or "").strip() and not (f.get("link") or "").strip():
        if EX.get(f["example"].strip()):                 # D-069: online, an example opens its saved result
            return redirect(url_for("example_page", key=f["example"].strip()))
    if DEMO:                                             # D-066: only the saved examples can be opened online
        key = (f.get("example") or "").strip()
        if EX.get(key) is None:
            return form_page(errors=["Choose one of the examples. This online demo cannot measure a new video."],
                             form=f), 400
        return redirect(url_for("example_page", key=key))
    link = (f.get("link") or "").strip()
    upload = request.files.get("video")
    errors = []
    example = None
    if (f.get("example") or "").strip():                                 # D-065
        from src.serve import examples
        example = examples.get(f["example"].strip())
        if example is None:
            errors.append("That example is not available.")
        elif link or (upload and upload.filename):
            errors.append("Choose an example, a video file or a link - only one of them.")
    elif not link and not (upload and upload.filename):
        errors.append("Choose a video file or paste a link, or use one of the examples.")
    if link and upload and upload.filename:
        errors.append("Choose a video file or a link, not both.")
    followers = None
    if (f.get("followers") or "").strip():
        try:
            followers = float(f["followers"].replace(",", "").strip())
            if followers <= 0:
                raise ValueError
        except ValueError:
            errors.append("The follower count must be a positive number.")
    if not link and not example and f.get("platform") not in ("instagram", "youtube"):
        errors.append("Choose the platform the video is for.")
    if link:
        from src.serve.intake import IntakeRefused, parse_link
        try:
            parse_link(link)
        except IntakeRefused as exc:
            errors.append(str(exc)[:1].upper() + str(exc)[1:] + ".")
    if errors:
        return form_page(errors=errors, form=f), 400
    jid = uuid.uuid4().hex[:12]
    upload_path = None
    # a browser sends a caption's line breaks as CR LF; the study's captions use LF (D-065)
    caption = (f.get("caption") or "").replace(CRLF, LF)
    if example and caption == (example["caption"] or "").replace(CRLF, LF):
        caption = example["caption"]                     # unchanged example caption: exactly the collection's text
    if not link and not example:
        d = UPLOADS / jid
        d.mkdir(parents=True, exist_ok=True)
        upload_path = d / (secure_filename(upload.filename) or "video.mp4")
        upload.save(upload_path)
    answers = {h: (1.0 if f.get(h) == "yes" else 0.0) for h, _ in hand_code_questions() if f.get(h) in ("yes", "no")}
    job = {"id": jid, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "queued",
           "progress": [], "inputs": {
               "link": link or None, "upload_path": str(upload_path) if upload_path else None,
               "upload_name": upload.filename if upload_path else (f"example: {example['label']}" if example else None),
               "example": example["key"] if example else None,
               "platform": example["platform"] if example else f.get("platform"),
               "followers": followers, "caption": caption, "no_caption": f.get("no_caption") == "on",
               "collab": {"yes": True, "no": False}.get(f.get("collab")), "zero_sugar": f.get("zero_sugar"),
               "answers": answers}}
    save_job(job)
    QUEUE.put(jid)
    return redirect(url_for("job_page", jid=jid))


@app.get("/job/<jid>")
def job_page(jid: str):
    job = load_job(jid) if not DEMO else None
    if job is None:
        abort(404)
    if job.get("kind") == "quick":                       # D-072
        return redirect(url_for("quick_page", qid=jid))
    if job["status"] == "done":
        return render_template("result.html", T=W.TEXT, W=W, job=job, v=result_view(job))
    others = [json.loads(p.read_text(encoding="utf-8")) for p in JOBS.glob("*.json")]
    ahead = sum(1 for j in others if j["id"] != jid and (j["status"] == "running" or
                                                         (j["status"] == "queued" and j["created"] < job["created"])))
    steps = [(name, any(line.startswith(name) for line in job["progress"])) for name in W.GROUP_NAMES.values()]
    return render_template("job.html", T=W.TEXT, job=job, ahead=ahead, steps=steps,
                           done=sum(1 for _, d in steps if d))


@app.get("/about")
def about():
    from src.serve.pipeline import artefacts, base_rate
    art = artefacts()
    sizes = [50_000, 500_000, 5_000_000]
    table = []
    for n in sizes:
        cells = []
        for p in ("instagram", "youtube"):
            b = base_rate(art, p, n)
            cells.append(f"{W.rate_text(b['rate_typical'])} ({W.rate_text(b['rate_80'][0])} to {W.rate_text(b['rate_80'][1])})")
        table.append({"followers": f"{n:,}", "instagram": cells[0], "youtube": cells[1]})
    return render_template("about.html", T=W.TEXT, card=art["card"], table=table, limits=W.ABOUT_LIMITS,
                           g4=W.g4_text(art["card"]["gates"], art["card"].get("gates_plain")))


# ------------------------------------------------------------------------------------------ checks
def check_pages() -> int:
    """Render the about page and every finished job; fail if a forbidden phrase appears."""
    bad = 0
    with app.test_client() as c:
        pages = [("/about", c.get("/about")), ("/", c.get("/")), ("/healthz", c.get("/healthz"))]
        q = c.post("/quick", data={"platform": "instagram", "followers": "250000",          # D-072
                                   "caption": "New Coca-Cola Zero Sugar for the match! #ZeroSugar #football"})
        pages.append(("/quick (form sent)", q))
        if q.status_code in (301, 302, 303):
            url = q.headers["Location"]
            pages.append((url, c.get(url)))
            job_file(url.rsplit("/", 1)[-1]).unlink(missing_ok=True)      # a check's own test result is not kept
        if SAVED:
            pages += [(f"/example/{e['key']}", c.get(f"/example/{e['key']}")) for e in EX.all_examples()]
        if not DEMO:
            for p in sorted(JOBS.glob("*.json")):
                j = json.loads(p.read_text(encoding="utf-8"))
                url = f"/quick/{j['id']}" if j.get("kind") == "quick" else f"/job/{j['id']}"
                pages.append((url, c.get(url)))
        for url, resp in pages:
            html = resp.get_data(as_text=True).lower()
            hits = [w for w in W.FORBIDDEN if w in html]
            print(f"{resp.status_code} {url}: {'forbidden words ' + str(hits) if hits else 'wording ok'}")
            bad += bool(hits) or resp.status_code >= 500
    return bad


def main() -> None:
    ap = argparse.ArgumentParser(description="12.5 - the tool's web page (D-059).")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        sys.exit(1 if check_pages() else 0)
    if DEMO:
        print(f"Open http://{HOST}:{PORT} - demo mode, saved examples only. Stop with Ctrl+C.")
        app.run(host=HOST, port=PORT, debug=False, threaded=True, load_dotenv=False)
        return
    start_worker()
    host, port = ("0.0.0.0", int(os.environ.get("PORT", 7860))) if PUBLIC else (HOST, PORT)
    print(f"Open http://{host}:{port} - {'public server' if PUBLIC else 'this computer only'}. Stop with Ctrl+C.")
    app.run(host=host, port=port, debug=False, threaded=True, load_dotenv=False)


def start_worker() -> None:
    """Queue again any job a restart interrupted, in order, and start the one measuring thread."""
    restart = sorted((json.loads(p.read_text(encoding="utf-8")) for p in JOBS.glob("*.json")), key=lambda j: j["created"])
    for j in restart:
        if j["status"] in ("queued", "running"):
            j["status"], j["progress"] = "queued", []
            save_job(j)
            QUEUE.put(j["id"])
    threading.Thread(target=worker, daemon=True).start()


if PUBLIC and "--check" not in sys.argv:               # D-069: under gunicorn main() does not run
    start_worker()


if __name__ == "__main__":
    main()

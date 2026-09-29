"""Task 5.12 - automated labels from a free local vision-language model (D-021, D-022, D-038).

Seven constructs (D-032). Four have a manual check in the researcher's 60 codes and go through
4.2's alpha rule; three do not and can only ever be reported as unvalidated:

    checked      has_celebrity, has_influencer, has_cta, humour_present
    unchecked    product_vs_lifestyle, ugc_vs_brand, promotional_language

**The four checked questions are the codebook's own wording** (`src/coding/codebook.py`), imported
rather than copied, so the model and the researcher answer the same question. The three unchecked
definitions are written below in the same style and were fixed before any model ran (D-038).

Input per video, as docs/05 section 3 specifies, with one change: six grid frames in time order,
the account name, the caption (YouTube: title + description) and the English translation of the
speech. **No OCR text** - 5.5 part B detects text but reads none (D-034) - so the model reads any
on-screen text from the frames itself. The researcher saw the whole video with sound; the model
sees six stills and a transcript. That gap is part of what alpha measures.

The model runs in Ollama on the laptop GPU: temperature 0, fixed seed, and the answer is forced
into a JSON schema whose values can only be the listed options. Every raw answer is kept.

Pilot (fixed before any model ran - D-038):
    10 of the 60 coded videos, 5 per platform, seed 20260929 (`pilot_sample.csv`). Each candidate
    labels them; the winner has the highest agreement with the researcher on the four checked
    constructs, where the model answering "unsure" counts as *not* agreeing (no winning by
    abstaining) and pairs the researcher marked "unsure" are left out. Ties: more valid answers,
    then faster. The pilot videos are then excluded from 4.2's primary alpha, so the chosen model
    is judged on 50 videos it was not chosen on.

Usage:
    python -m src.features.annotate --pilot --models qwen3-vl:4b,qwen2.5vl:3b
    python -m src.features.annotate --run --model <winner>        # all 300, cached per video
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.codebook import QUESTIONS  # noqa: E402
from src.features import common  # noqa: E402

OLLAMA = "http://127.0.0.1:11434"
OUT = config.INTERIM / "annotation"
PILOT_SAMPLE = OUT / "pilot_sample.csv"
SUMMARY = config.INTERIM / "annotation_summary.csv"
CODES = config.ROOT / "data" / "coding" / "manual_codes_FINAL.csv"

PILOT_SEED = 20260929
PILOT_PER_PLATFORM = 5
N_FRAMES = 6
MAX_SIDE = 768          # longest frame side sent to the model, pixels
MAX_TEXT = 1500         # characters of caption and of transcript sent
SEED = 20260929
# Qwen3-VL reasons before it answers. In the pilot one video ran out of room mid-reasoning at a
# 6,144-token window and returned nothing (D-038); a larger window changes no answer that fitted.
NUM_CTX = 10240
# ...and with reasoning on, some videos ran for 9 minutes and returned nothing. With reasoning off
# (D-038, decided by a re-run pilot) the answer is ~70 tokens and 6,144 fits on the GPU.
THINK = True
NUM_CTX_NO_THINK = 6144

CHECKED = ["has_celebrity", "has_influencer", "has_cta", "humour_present"]
_codebook = {q[0]: q for q in QUESTIONS}

# (question, help text, options) - the checked four straight from the codebook
CONSTRUCTS: dict[str, tuple[str, str, list[str]]] = {
    f: (_codebook[f][1], _codebook[f][2], [v for v, _ in _codebook[f][3]]) for f in CHECKED
}
CONSTRUCTS.update({
    "product_vs_lifestyle": (
        "Is the video mainly about the drink itself, or about a moment the drink is part of?",
        "Decide by what fills most of the video. "
        "PRODUCT: the can or bottle, its taste, ingredients, pack design, price or offer is the main "
        "subject - pack shots, pouring, taste close-ups, a new flavour announced. "
        "LIFESTYLE: people, music, sport, food, friends or an event are the main subject and the "
        "drink is one part of the scene.",
        ["product", "lifestyle", "unsure"]),
    "ugc_vs_brand": (
        "Does the video look made by an ordinary person or creator, or produced by or for the brand?",
        "This is about the look of the video, not who posted it. "
        "UGC: filmed on a phone, handheld, a person filming themselves or friends, informal edit, "
        "the creator's own voice. A creator video paid for by the brand but made in the creator's "
        "own style counts as UGC. "
        "BRAND: studio lighting, professional camera work, designed graphics and logos, polished "
        "edit, advertising voice-over.",
        ["ugc", "brand", "unsure"]),
    "promotional_language": (
        "Do the words in the video or caption use sales language?",
        "Words spoken, written on screen or in the caption that sell: offers, prices, discounts, "
        "'new', 'limited', 'win', 'free', 'buy now', contest or giveaway wording. "
        "A slogan (e.g. 'Real Magic') or a plain description of the scene is not sales language. "
        "YES: 'Now only 20 baht', 'New Zero Sugar Lemon', 'Win tickets'. "
        "NO: 'Enjoy the match', 'Real Magic', hashtags on their own.",
        ["yes", "no"]),
})
FIELDS = list(CONSTRUCTS)

SYSTEM = ("You label short marketing videos for a university research study. You are shown six "
          "still frames taken from one video in time order, the account that posted it, its "
          "caption, and an English translation of anything spoken. Read any text visible in the "
          "frames yourself. Answer every question from this evidence only, using exactly one of "
          "the allowed answers. Use 'unsure' only where it is allowed and the evidence really "
          "does not decide the question.")


def prompt_text(account: str, caption: str, transcript_en: str, speech_status: str) -> str:
    cap = (caption or "").strip()[:MAX_TEXT] or "(no caption)"
    if transcript_en.strip():
        tr = transcript_en.strip()[:MAX_TEXT]
    else:
        tr = {"no_speech": "(nobody speaks in this video)",
              "silent": "(the video has no sound)"}.get(speech_status, "(no usable speech)")
    qs = []
    for i, (f, (q, h, opts)) in enumerate(CONSTRUCTS.items(), 1):
        qs.append(f"{i}. {f} - {q}\n   {h}\n   Allowed answers: {', '.join(opts)}")
    return (f"Account: {account}\n\nCaption:\n{cap}\n\nSpeech (English translation):\n{tr}\n\n"
            "Questions:\n" + "\n\n".join(qs) +
            "\n\nReply with a JSON object with one key per question name.")


SCHEMA = {"type": "object", "properties": {f: {"type": "string", "enum": o}
                                           for f, (_, _, o) in CONSTRUCTS.items()},
          "required": FIELDS}
PROMPT_VERSION = hashlib.sha256((SYSTEM + prompt_text("A", "C", "T", "ok") +
                                 json.dumps(SCHEMA, sort_keys=True)).encode()).hexdigest()[:12]


def frames_b64(platform: str, media_id: str) -> tuple[list[str], list[float]]:
    grid = common.frame_list(platform, media_id, role="grid")
    idx = sorted(set(np.linspace(0, len(grid) - 1, min(N_FRAMES, len(grid))).round().astype(int)))
    out, ts = [], []
    for i in idx:
        img = cv2.imread(str(grid[i]["file"]))
        h, w = img.shape[:2]
        s = MAX_SIDE / max(h, w)
        if s < 1:
            img = cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        out.append(base64.b64encode(buf.tobytes()).decode())
        ts.append(round(float(grid[i]["t"]), 2))
    return out, ts


def _post(path: str, body: dict, timeout: int = 600) -> dict:
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


REQUEST_LIMIT = 180   # seconds, wall clock. One request once hung for 91 minutes (D-038).


def chat(body: dict) -> dict:
    """A chat request with a hard time limit; a hung server raises instead of stalling the run."""
    import concurrent.futures as cf
    ex = cf.ThreadPoolExecutor(max_workers=1)
    try:
        return ex.submit(_post, "/api/chat", body, REQUEST_LIMIT).result(timeout=REQUEST_LIMIT)
    except cf.TimeoutError:
        raise TimeoutError(f"no reply within {REQUEST_LIMIT} s") from None
    finally:
        ex.shutdown(wait=False, cancel_futures=True)


def model_digest(model: str) -> str:
    with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=30) as r:
        for m in json.loads(r.read())["models"]:
            if m["name"] == model:
                return m["digest"][:12]
    raise SystemExit(f"{model} is not in Ollama - it must be downloaded (with approval) first")


def gpu_share(model: str) -> float | None:
    with urllib.request.urlopen(OLLAMA + "/api/ps", timeout=30) as r:
        for m in json.loads(r.read()).get("models", []):
            if m["name"] == model and m.get("size"):
                return round(m.get("size_vram", 0) / m["size"], 3)
    return None


def unload(model: str) -> None:
    _post("/api/generate", {"model": model, "keep_alive": 0}, timeout=120)
    time.sleep(2)


def label_one(model: str, row: pd.Series) -> dict:
    doc = common.read_cache(row["platform"], row["media_id"])
    asr = doc.get("asr") or {}
    imgs, ts = frames_b64(row["platform"], row["media_id"])
    body = {"model": model, "stream": False, "format": SCHEMA, "keep_alive": "10m",
            "options": {"temperature": 0, "seed": SEED,
                        "num_ctx": ctx_for(model)},
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "images": imgs,
                          "content": prompt_text(str(row["account"]), row["caption"],
                                                 asr.get("transcript_en") or "",
                                                 asr.get("status") or "")}]}
    if not THINK:   # only ever sent to switch reasoning off; the pilot sent nothing (D-038)
        body["think"] = False
    t0 = time.time()
    out = {"platform": row["platform"], "media_id": row["media_id"], "model": model,
           "frames_t": ts, "raw": None, "valid": False}
    out["reloaded"] = False
    try:
        r = chat(body)
        if not r.get("done"):
            # A blank reply means the GPU arithmetic overflowed (the model emits only "@", token
            # 31) and Ollama's grammar check crashed on it. Ollama reuses cached state between
            # requests, so one such video poisons every later one until the model is reloaded.
            # Unload, reload, and ask again with the identical request (D-038). A video that still
            # fails on a clean model is recorded as missing - and the model is unloaded again so
            # it cannot poison the next video.
            out["reloaded"] = True
            unload(model)
            r = chat(body)
            if not r.get("done"):
                unload(model)
        out["raw"] = r["message"]["content"]
        out["thinking_chars"] = len(r["message"].get("thinking") or "")
        if not THINK and not (out["raw"] or "").strip():
            # Ollama 0.32.5 quirk: with reasoning off and a JSON schema, the model answers directly
            # (~70 tokens) but the answer is filed under "thinking". Same text, different field.
            out["raw"] = r["message"].get("thinking") or ""
            out["thinking_chars"] = 0
        out["prompt_tokens"] = r.get("prompt_eval_count")
        out["output_tokens"] = r.get("eval_count")
        out["done_reason"] = r.get("done_reason")
        # the model stopped because the window was full - its answer, if any, is incomplete
        out["ctx_tight"] = r.get("done_reason") == "length"
        ans = json.loads(out["raw"])
        bad = [f for f in FIELDS if ans.get(f) not in CONSTRUCTS[f][2]]
        out["valid"] = not bad
        for f in FIELDS:
            out[f] = ans.get(f) if ans.get(f) in CONSTRUCTS[f][2] else None
    except Exception as e:  # recorded, never silently retried into a different answer
        out["error"] = f"{type(e).__name__}: {e}"[:300]
        if isinstance(e, TimeoutError):
            try:
                unload(model)   # a hung model must not carry over to the next video
            except Exception:
                pass
    out["seconds"] = round(time.time() - t0, 1)
    return out


def pilot_sample() -> pd.DataFrame:
    """Drawn once, before any model runs, and never redrawn."""
    if PILOT_SAMPLE.exists():
        return pd.read_csv(PILOT_SAMPLE, dtype={"media_id": str})
    c = pd.read_csv(CODES, dtype={"media_id": str})
    s = pd.concat([c[c["platform"] == p].sample(PILOT_PER_PLATFORM, random_state=PILOT_SEED)
                   for p in ("instagram", "youtube")])[["platform", "media_id"]].reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    s.to_csv(PILOT_SAMPLE, index=False)
    return s


def agreement(auto: pd.DataFrame) -> tuple[float, int, int]:
    """Share of checked (video, construct) pairs where the model matches a definite human answer."""
    c = pd.read_csv(CODES, dtype={"media_id": str})
    m = auto.merge(c, on=["platform", "media_id"], suffixes=("_auto", ""))
    hits = n = 0
    for f in CHECKED:
        keep = m[f] != "unsure"
        hits += int((m.loc[keep, f + "_auto"] == m.loc[keep, f]).sum())
        n += int(keep.sum())
    return hits / n if n else float("nan"), hits, n


def ctx_for(model: str) -> int:
    """The larger window exists only for Qwen3-VL's reasoning; everything else runs as piloted."""
    return NUM_CTX if (THINK and model.startswith("qwen3")) else NUM_CTX_NO_THINK


def tag(model: str) -> str:
    return model.replace(":", "_") + ("" if THINK else "_nothink")


def pilot(models: list[str]) -> None:
    s = pilot_sample()
    idx = common.video_index().merge(s, on=["platform", "media_id"])
    assert len(idx) == len(s), "pilot videos missing from the corpus index"
    lines = ["# 5.12 pilot - which local model labels best (D-038)", "",
             f"10 of the researcher's 60 coded videos (5 per platform, seed {PILOT_SEED}), drawn "
             "before any model ran. Rule fixed in advance: highest agreement on the four checked "
             "constructs, a model 'unsure' counting as not agreeing; ties -> more valid answers, "
             f"then faster. Prompt version `{PROMPT_VERSION}`, temperature 0, seed {SEED}, "
             f"model reasoning {'on' if THINK else 'off'}.", "",
             "| Model | Digest | Agreement (checked 4) | Valid answers | Sec / video | Share on GPU |",
             "|---|---|---|---|---|---|"]
    results = []
    for model in models:
        dig = model_digest(model)
        rows, share = [], None
        for _, r in idx.iterrows():
            rows.append(label_one(model, r))
            share = share or gpu_share(model)
            print(f"  {model:14} {r['platform']:9} {r['media_id']:13} "
                  f"{rows[-1]['seconds']:6.1f}s valid={rows[-1]['valid']}")
        df = pd.DataFrame(rows)
        df.to_csv(OUT / f"pilot_{tag(model)}.csv", index=False)
        agr, hits, n = agreement(df)
        sec = df["seconds"].median()
        results.append((model, dig, agr, hits, n, int(df["valid"].sum()), sec, share))
        lines.append(f"| `{model}` | `{dig}` | **{agr:.0%}** ({hits}/{n}) | {int(df['valid'].sum())}/10 "
                     f"| {sec:.1f} | {share if share is not None else 'n/a'} |")
    best = sorted(results, key=lambda x: (-x[2], -x[5], x[6]))[0]
    lines += ["", f"**Chosen by the rule: `{best[0]}`.**", "",
              "Per construct, pilot videos only (model vs researcher, researcher-unsure left out):", "",
              "| Model | " + " | ".join(CHECKED) + " |", "|---|" + "---|" * len(CHECKED)]
    c = pd.read_csv(CODES, dtype={"media_id": str})
    for model, *_ in results:
        df = pd.read_csv(OUT / f"pilot_{tag(model)}.csv", dtype={"media_id": str})
        m = df.merge(c, on=["platform", "media_id"], suffixes=("_auto", ""))
        cells = []
        for f in CHECKED:
            k = m[f] != "unsure"
            cells.append(f"{int((m.loc[k, f + '_auto'] == m.loc[k, f]).sum())}/{int(k.sum())}")
        lines.append(f"| `{model}` | " + " | ".join(cells) + " |")
    lines += ["", "Ten videos cannot measure reliability - that is 4.2's job, on the 50 coded videos "
              "the pilot did not use. The pilot only picks the model."]
    text = "\n".join(lines) + "\n"
    (config.REPORTS / ("annotation_pilot.md" if THINK else "annotation_pilot_no_reasoning.md")
     ).write_text(text, encoding="utf-8")
    print(text)


def run(model: str, force: bool, only_coded: bool = False) -> None:
    dig = model_digest(model)
    params = {"model": model, "digest": dig, "prompt_version": PROMPT_VERSION, "seed": SEED,
              "n_frames": N_FRAMES, "think": THINK,
              "num_ctx": ctx_for(model), "max_side": MAX_SIDE, "max_text": MAX_TEXT, "version": 1}
    idx = common.video_index()
    if only_coded:   # the 60 coded videos first, so 4.2 can start before the long tail
        coded = pd.read_csv(CODES, dtype={"media_id": str})[["platform", "media_id"]]
        idx = idx.merge(coded, on=["platform", "media_id"])
    rows, t0, streak = [], time.time(), 0
    for i, (_, r) in enumerate(idx.iterrows(), 1):
        cached = common.read_cache(r["platform"], r["media_id"]).get("annotation") or {}
        # A finished attempt is kept whether it answered or failed on a clean model, so 4.2's
        # figures stay exactly as computed; only an attempt that hung is tried again.
        hung = (cached.get("seconds") or 0) > 2 * REQUEST_LIMIT or "TimeoutError" in str(cached.get("error"))
        if cached.get("params") == params and not hung and not force:
            p = cached
        else:
            p = label_one(model, r)
            p = {k: v for k, v in p.items() if k not in ("platform", "media_id")}
            p["params"] = params
            p["processed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            common.update_cache(r["platform"], r["media_id"], "annotation", p)
            streak = 0 if p.get("valid") else streak + 1
            if streak >= 8:
                raise SystemExit(f"8 new failures in a row at video {i} - stopping rather than churning; "
                                 "check the Ollama server. Everything so far is cached.")
        rows.append({"platform": r["platform"], "media_id": r["media_id"],
                     **{f"auto_{f}": p.get(f) for f in FIELDS},
                     "valid": p.get("valid"), "seconds": p.get("seconds"), "error": p.get("error")})
        if i % 25 == 0:
            print(f"  {i}/{len(idx)}  {(time.time() - t0) / 60:.1f} min", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(SUMMARY if not only_coded else OUT / "coded60_summary.csv", index=False)
    print(f"-> {SUMMARY.relative_to(config.ROOT)}  ({len(df)} rows, {int(df['valid'].sum())} valid, "
          f"{(time.time() - t0) / 60:.1f} min)")
    for f in FIELDS:
        print(f"  auto_{f:22} " + ", ".join(f"{k} {v}" for k, v in
                                            df[f"auto_{f}"].value_counts(dropna=False).items()))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="5.12 - automated labels, local model (D-038).")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--models", default="qwen3-vl:4b,qwen2.5vl:3b")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--model")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only-coded", action="store_true", help="just the 60 coded videos")
    ap.add_argument("--no-think", action="store_true", help="switch the model's reasoning off")
    a = ap.parse_args()
    global THINK
    THINK = not a.no_think
    if a.pilot:
        pilot([m.strip() for m in a.models.split(",")])
    if a.run:
        if not a.model:
            raise SystemExit("--run needs --model (the pilot's winner)")
        run(a.model, a.force, a.only_coded)


if __name__ == "__main__":
    main()

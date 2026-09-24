"""Task 5.9 - sentiment and emotion of the words in each video (docs/04 section 4).

Three texts per video, each scored separately and never mixed:

    speech_en       5.6's English translation of what is said   (task=translate)
    speech_native   5.6's transcript in the spoken language     (task=transcribe)
    caption         the Instagram caption, or the YouTube title + description

Sentiment: `cardiffnlp/twitter-xlm-roberta-base-sentiment` (XLM-T, social-media trained),
1.12 GB. Run on all three texts. It covers **8 languages** (ar, de, en, es, fr, hi, it, pt);
anything else is recorded with `*_lang_covered = False` so a Korean or Thai score is never
read as if it were as good as the English one. Score kept as
`compound = P(positive) - P(negative)` in [-1, 1], plus the label and all three probabilities.

Emotion: `j-hartmann/emotion-english-distilroberta-base` (7 emotions), 331 MB, **English only**.
It is run on the English translation, and on a caption only when the caption is detected as
English. docs/04 section 4 requires the methods chapter to say that emotion is measured
post-translation, because translation flattens emotional nuance - that weakens H3 and is
stated rather than hidden.

Cross-check required by docs/04 section 4: the correlation between native and translated
sentiment on the videos where both are available and the native language is covered. Printed
at the end of a run and recorded in docs/05 section 5.

Honest nulls, never zeros: a video with no speech (98), no intelligible speech (6) or silent
audio (2, D-025) gets **null** speech sentiment - zero would read as neutral, which is a
measurement that was not made. Where 5.6's translation failed (2 videos, `transcript_en_failed`)
the native score becomes the primary one and `speech_sentiment_source` says so. 5.6's
`transcript_low_confidence` flag (47 videos) is carried through untouched.

Caption language uses `langdetect` when it is installed. Without it, captions are still scored
and `caption_lang` is left unknown; task 5.7 establishes caption language properly, after which
this can be re-run with `--force` to fill the coverage flags.

Runs on **all 300 videos**: the Zero Sugar focus (D-030) applies when a model is fitted, not
when a feature is measured.

Usage:
    python -m src.features.sentiment --limit 3 --allow-download   # first run, fetches models
    python -m src.features.sentiment                              # all 300
    python -m src.features.sentiment --only youtube_dwrWSRpG77Q --force
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

SUMMARY = config.INTERIM / "sentiment_summary.csv"

SENT_REPO = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
EMO_REPO = "j-hartmann/emotion-english-distilroberta-base"
SENT_MB, EMO_MB = 1112, 331

# The 8 languages XLM-T was trained on (docs/04 section 4). Others are scored but flagged.
SENT_LANGS = {"ar", "de", "en", "es", "fr", "hi", "it", "pt"}
MAX_TOKENS = 512          # both models' limit, including special tokens; longer text is chunked
BATCH = 16
MIN_CHARS = 3             # below this there is nothing to score

PARAMS = {"sentiment_model": SENT_REPO, "emotion_model": EMO_REPO,
          "max_tokens": MAX_TOKENS, "covered_langs": sorted(SENT_LANGS),
          "score": "compound = P(pos) - P(neg)", "version": 1}

_URL = re.compile(r"https?://\S+|www\.\S+")
_MENTION = re.compile(r"@[A-Za-z0-9_.]+")
_HASH = re.compile(r"#(\w+)")
_WS = re.compile(r"\s+")


def clean(text: str) -> str:
    """Normalise text the way the Twitter-trained model expects, without dropping content."""
    t = str(text or "")
    t = _URL.sub("http", t)
    t = _MENTION.sub("@user", t)
    t = _HASH.sub(r"\1", t)           # keep the word, drop the hash
    return _WS.sub(" ", t).strip()


def detect_lang(text: str) -> str | None:
    if len(text) < 10:
        return None
    try:
        from langdetect import DetectorFactory, detect
    except ImportError:
        return None
    DetectorFactory.seed = 0          # langdetect is non-deterministic without this
    try:
        return detect(text)
    except Exception:
        return None


# ============================================================ models
def load_pair(allow_download: bool):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    def one(repo: str, mb: int):
        # transformers 5.11 warns that this tokenizer has "an incorrect regex pattern" and
        # suggests `fix_mistral_regex=True`. Checked 2026-09-23: the default tokenisation is
        # identical to the reference sentencepiece tokenizer (`use_fast=False`), while that flag
        # *changes* it ("!" -> "_!"), so the warning is wrong for this model. Do not set it.
        try:
            tok = AutoTokenizer.from_pretrained(repo, local_files_only=not allow_download)
            mdl = AutoModelForSequenceClassification.from_pretrained(
                repo, local_files_only=not allow_download)
        except OSError as exc:
            if not allow_download:
                raise SystemExit(
                    f"{repo} is not on disk. One-time download, about {mb} MB, free. "
                    f"Re-run with --allow-download once the researcher has approved it.") from exc
            raise
        return tok, mdl

    sent_tok, sent_mdl = one(SENT_REPO, SENT_MB)
    emo_tok, emo_mdl = one(EMO_REPO, EMO_MB)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return (sent_tok, sent_mdl.to(device).eval(), emo_tok, emo_mdl.to(device).eval(), device)


def _probs(tok, mdl, device, text: str) -> tuple[np.ndarray, int, int] | None:
    """Mean class probabilities over the text, chunked if it is longer than the model takes.

    Chunks are weighted by how many tokens they hold, so a long first chunk is not outvoted
    by a three-word tail.
    """
    import torch

    if len(text) < MIN_CHARS:
        return None
    # The tokenizer does the splitting: each chunk comes back complete with special tokens.
    enc = tok(text, truncation=True, max_length=MAX_TOKENS, return_overflowing_tokens=True)
    chunks = [c for c in enc["input_ids"] if c]
    if not chunks:
        return None
    weights, out = [], []
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]
        padded = tok.pad({"input_ids": batch}, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = mdl(**padded).logits
        out.append(torch.softmax(logits, dim=-1).cpu().numpy())
        weights.extend(len(c) for c in batch)
    p = np.vstack(out)
    w = np.asarray(weights, dtype=float)
    return (p * w[:, None]).sum(0) / w.sum(), len(chunks), int(w.sum())


def _sentiment(tok, mdl, device, text: str) -> dict | None:
    r = _probs(tok, mdl, device, text)
    if r is None:
        return None
    p, n_chunks, n_tokens = r
    order = [mdl.config.id2label[i].lower() for i in range(len(p))]
    by = dict(zip(order, (float(x) for x in p)))
    neg = by.get("negative", by.get("label_0", 0.0))
    neu = by.get("neutral", by.get("label_1", 0.0))
    pos = by.get("positive", by.get("label_2", 0.0))
    label = max((("negative", neg), ("neutral", neu), ("positive", pos)), key=lambda kv: kv[1])[0]
    return {"label": label, "compound": round(pos - neg, 4), "p_negative": round(neg, 4),
            "p_neutral": round(neu, 4), "p_positive": round(pos, 4),
            "n_chunks": n_chunks, "n_tokens": n_tokens, "n_chars": len(text)}


def _emotion(tok, mdl, device, text: str) -> dict | None:
    r = _probs(tok, mdl, device, text)
    if r is None:
        return None
    p, n_chunks, n_tokens = r
    probs = {mdl.config.id2label[i].lower(): round(float(x), 4) for i, x in enumerate(p)}
    label = max(probs, key=probs.get)
    return {"label": label, "score": probs[label], "probs": probs,
            "n_chunks": n_chunks, "n_tokens": n_tokens}


# ============================================================ one video
def one_video(models, platform: str, media_id: str, caption: str) -> dict:
    sent_tok, sent_mdl, emo_tok, emo_mdl, device = models
    asr = common.read_cache(platform, media_id).get("asr") or {}
    speech_status = asr.get("status", "missing")
    lang = asr.get("lang_audio")
    en_text = clean(asr.get("transcript_en") or "")
    native_text = clean(asr.get("transcript_native") or "")
    cap_text = clean(caption or "")
    cap_lang = detect_lang(cap_text)

    out: dict = {
        "status": "ok",
        "speech_status": speech_status,
        "lang_audio": lang,
        "lang_audio_covered": (lang in SENT_LANGS) if lang else None,
        "caption_lang": cap_lang,
        "caption_lang_covered": (cap_lang in SENT_LANGS) if cap_lang else None,
        "transcript_en_failed": bool(asr.get("transcript_en_failed")),
        "transcript_low_confidence": bool(asr.get("transcript_low_confidence")),
        "chars": {"speech_en": len(en_text), "speech_native": len(native_text),
                  "caption": len(cap_text)},
    }

    # --- sentiment. The native score is only trustworthy inside the model's 8 languages.
    out["sent_speech_en"] = _sentiment(sent_tok, sent_mdl, device, en_text)
    if native_text and lang in SENT_LANGS:
        out["sent_speech_native"] = _sentiment(sent_tok, sent_mdl, device, native_text)
        out["sent_speech_native_skipped"] = None
    else:
        out["sent_speech_native"] = None
        out["sent_speech_native_skipped"] = ("no_text" if not native_text
                                             else f"lang_not_covered:{lang}")
    out["sent_caption"] = _sentiment(sent_tok, sent_mdl, device, cap_text)

    # Which score stands as this video's speech sentiment, and why.
    if out["sent_speech_en"]:
        out["speech_sentiment_source"] = "transcript_en"
    elif out["sent_speech_native"]:
        out["speech_sentiment_source"] = "transcript_native (translation failed)"
    else:
        out["speech_sentiment_source"] = None

    # --- emotion, English text only (docs/04 section 4)
    out["emotion_speech_en"] = _emotion(emo_tok, emo_mdl, device, en_text)
    out["emotion_caption"] = (_emotion(emo_tok, emo_mdl, device, cap_text)
                              if cap_lang == "en" else None)
    out["emotion_caption_skipped"] = None if cap_lang == "en" else f"caption_lang:{cap_lang}"

    if not any((out["sent_speech_en"], out["sent_speech_native"], out["sent_caption"])):
        out["status"] = "no_text"
    out["params"] = PARAMS
    out["processed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return out


# ============================================================ run
def flat(platform: str, media_id: str, p: dict) -> dict:
    """One row per video for the summary CSV - the columns 5.10 will use."""
    se, sn, sc = p.get("sent_speech_en"), p.get("sent_speech_native"), p.get("sent_caption")
    em, ec = p.get("emotion_speech_en"), p.get("emotion_caption")
    primary = se or (sn if (p.get("speech_sentiment_source") or "").startswith("transcript_native")
                     else None)
    return {
        "platform": platform, "media_id": media_id, "status": p.get("status"),
        "speech_status": p.get("speech_status"),
        "lang_audio": p.get("lang_audio"), "lang_audio_covered": p.get("lang_audio_covered"),
        "caption_lang": p.get("caption_lang"),
        "caption_lang_covered": p.get("caption_lang_covered"),
        "sentiment_speech": primary["compound"] if primary else None,
        "sentiment_speech_label": primary["label"] if primary else None,
        "speech_sentiment_source": p.get("speech_sentiment_source"),
        "sentiment_speech_native": sn["compound"] if sn else None,
        "sentiment_speech_native_label": sn["label"] if sn else None,
        "sentiment_speech_native_skipped": p.get("sent_speech_native_skipped"),
        "sentiment_caption": sc["compound"] if sc else None,
        "sentiment_caption_label": sc["label"] if sc else None,
        "emotion_label": em["label"] if em else None,
        "emotion_score": em["score"] if em else None,
        "emotion_caption_label": ec["label"] if ec else None,
        "transcript_en_failed": p.get("transcript_en_failed"),
        "transcript_low_confidence": p.get("transcript_low_confidence"),
        "chars_speech_en": (p.get("chars") or {}).get("speech_en"),
        "chars_caption": (p.get("chars") or {}).get("caption"),
    }


def run(idx: pd.DataFrame, force: bool, allow_download: bool) -> pd.DataFrame:
    todo = [r for _, r in idx.iterrows()
            if force or (common.read_cache(r["platform"], r["media_id"]).get("sentiment") or {})
            .get("params") != PARAMS]
    print(f"5.9 sentiment and emotion: {len(idx)} selected, {len(todo)} to process")
    if todo:
        models = load_pair(allow_download)
        print(f"models loaded on {models[-1]}")
        if detect_lang("this is an english sentence for a detector check") is None:
            print("  note: langdetect is not installed - captions are still scored, but their "
                  "language is left unknown until task 5.7")
        t0 = time.time()
        for i, r in enumerate(todo, 1):
            p = one_video(models, r["platform"], r["media_id"], r["caption"])
            common.update_cache(r["platform"], r["media_id"], "sentiment", p)
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}  {(time.time() - t0) / 60:.1f} min")

    rows = []
    for _, r in idx.iterrows():
        p = common.read_cache(r["platform"], r["media_id"]).get("sentiment")
        if p:
            rows.append(flat(r["platform"], r["media_id"], p))
    df = pd.DataFrame(rows)
    df.to_csv(SUMMARY, index=False)
    print(f"-> {SUMMARY.relative_to(config.ROOT)}  ({len(df)} rows)")
    return df


def report(df: pd.DataFrame) -> None:
    print("\nstatus:", df["status"].value_counts(dropna=False).to_dict())
    for col, what in [("sentiment_speech", "speech sentiment"),
                      ("sentiment_caption", "caption sentiment"),
                      ("emotion_label", "emotion (English translation)")]:
        print(f"  {what:34} measured on {int(df[col].notna().sum()):3} of {len(df)} videos")
    print("\nspeech sentiment label, by platform (counts):")
    print(pd.crosstab(df["platform"], df["sentiment_speech_label"], dropna=False).to_string())
    print("\ncaption sentiment label, by platform (counts):")
    print(pd.crosstab(df["platform"], df["sentiment_caption_label"], dropna=False).to_string())
    print("\nemotion label, by platform (counts):")
    print(pd.crosstab(df["platform"], df["emotion_label"], dropna=False).to_string())
    skipped = df["sentiment_speech_native_skipped"].dropna()
    langs = sorted({s.split(":", 1)[1] for s in skipped if s.startswith("lang_not_covered")})
    print(f"\nnative sentiment: {int(df['sentiment_speech_native'].notna().sum())} scored; "
          f"{sum(s.startswith('lang_not_covered') for s in skipped)} skipped as outside the "
          f"model's 8 languages ({', '.join(langs) if langs else 'none'}); "
          f"{sum(s == 'no_text' for s in skipped)} had no transcript")
    print("caption language:",
          "unknown (langdetect not installed)" if df["caption_lang"].isna().all()
          else df["caption_lang"].value_counts(dropna=False).head(8).to_dict())

    # The cross-check docs/04 section 4 asks for.
    covered = df["caption_lang_covered"]
    print(f"caption sentiment: {int((covered == True).sum())} in the model's 8 languages, "  # noqa: E712
          f"{int((covered == False).sum())} outside them (scored, flagged, not used as "  # noqa: E712
          f"primary), {int(covered.isna().sum())} with no language detected")

    # The cross-check docs/04 section 4 asks for.
    both = df.dropna(subset=["sentiment_speech", "sentiment_speech_native"])
    if len(both) >= 10:
        pear = both["sentiment_speech"].corr(both["sentiment_speech_native"])
        spear = both["sentiment_speech"].corr(both["sentiment_speech_native"], method="spearman")
        agree = (both["sentiment_speech_label"] == both["sentiment_speech_native_label"]).mean()
        print(f"\nnative vs translated sentiment on {len(both)} videos: Pearson {pear:.3f}, "
              f"Spearman {spear:.3f} (docs/04 section 4 cross-check)")
        print(f"  same three-way label: {agree:.0%}")
        print(pd.crosstab(both["sentiment_speech_native_label"], both["sentiment_speech_label"],
                          rownames=["native"], colnames=["translated"]).to_string())
    else:
        print(f"\nnative vs translated cross-check: only {len(both)} videos have both - "
              f"reported as too few rather than correlated")
    print("\nNo engagement value is read here. Sentiment is a predictor; the outcome stays "
          "hidden until the pre-registered analysis (docs/08 section 7.9).")


def main() -> None:
    ap = argparse.ArgumentParser(description="5.9 - sentiment and emotion (docs/04 section 4).")
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", nargs="+", metavar="PLATFORM_MEDIAID")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--allow-download", action="store_true",
                    help=f"permit the one-time downloads: sentiment ~{SENT_MB} MB, "
                         f"emotion ~{EMO_MB} MB")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    idx = common.video_index(args.platform)
    if args.only:
        idx = idx[(idx["platform"] + "_" + idx["media_id"]).isin(args.only)]
    if args.limit:
        idx = idx.groupby("platform", group_keys=False).head(args.limit)
    df = run(idx, args.force, args.allow_download)
    if len(df):
        report(df)


if __name__ == "__main__":
    main()

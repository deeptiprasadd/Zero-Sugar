"""Task 5.6 - speech-to-text, spoken language, and speech timing, on the GPU.

For every corpus video, from the 16 kHz WAV written by 5.1, this produces (docs/04 sections
1-2, docs/05 Block B):

*   `lang_audio` - the spoken language, the project's source of truth for language. Detected
    from the *speech* regions only, over up to 90 s, so a music intro cannot decide it.
*   `transcript_native` - what is said, in the language it is said in. Speech rate and word
    counts come from this, because translation changes word counts.
*   `transcript_en` - an English translation, for sentiment and emotion (5.9), which are only
    comparable across languages in one language. For English audio the native transcript is
    used as-is rather than "translated" into English again.
*   `speech_dur_frac` - share of the video that is speech, from voice-activity detection.
*   `words_per_min` - words per minute *of speech* (speaking rate, not word density).

Model: faster-whisper `large-v3` (docs/04 section 2), float16 on the RTX 3050 (D-021). Every
video is processed with the same model, precision and settings, recorded in `PARAMS`; a run
never silently falls back to a different precision part-way.

**Defences against invented text**, which is the known failure of Whisper on brand video:
1.  The two digitally silent Reels are skipped outright (D-025).
2.  Voice-activity detection (Silero, bundled with faster-whisper) runs first. A video with no
    detected speech gets an empty transcript and `speech_dur_frac = 0`, and is never decoded -
    decoding music-only audio is exactly where Whisper produces phrases like "Thank you for
    watching".
3.  `condition_on_previous_text=False`, so one misheard line cannot seed a repeating loop.
4.  Every segment keeps Whisper's own confidence signals (average log-probability,
    no-speech probability, compression ratio), and known stock hallucination phrases are
    flagged, so suspect text can be found later rather than trusted now.

Sung lyrics are transcribed as speech; voice-activity detection does not separate singing
from talking. That is flagged for 5.8, whose music detector can tell them apart.

**No download happens unless asked.** The model (3.09 GB, Hugging Face,
Systran/faster-whisper-large-v3, MIT licence) is loaded from the local cache only; pass
`--allow-download` once to fetch it.

Usage:
    python -m src.features.asr --limit 2 --allow-download   # first run: fetch model, test
    python -m src.features.asr                               # all 300, resumable
    python -m src.features.asr --only instagram_C-Qrzffy557
    python -m src.features.asr --force
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

SUMMARY = config.INTERIM / "asr_summary.csv"

MODEL = "large-v3"
DEVICE = "cuda"
COMPUTE_TYPE = "float16"
BEAM_SIZE = 5
LANG_DETECT_SEGMENTS = 3          # up to 3 x 30 s of speech
MIN_SPEECH_SEC_FOR_RATE = 2.0     # below this, a words-per-minute figure is noise
LOW_LANG_PROB = 0.5               # below this the spoken language is uncertain (feeds 5.7)

# Video-level transcript confidence. Whisper's segment thresholds (below) are tuned for long
# recordings and did not fire on a 2-second misheard line under music (a German ad heard as
# "Fischen vor den Pricken" where its title cards read "MACHT ... BEREIT"). Per-word
# probability and language confidence did: 0.73 and 0.63 there, against 0.92+ and 0.85+ on
# transcripts checked against burned-in subtitles. A flag, never a deletion.
LOW_WORD_PROB = 0.80
LOW_LANG_PROB_FOR_TEXT = 0.70

# Segment-level suspicion rules: Whisper's documented failure thresholds.
SUSPECT_LOGPROB = -1.0
SUSPECT_NO_SPEECH = 0.6
SUSPECT_COMPRESSION = 2.4

# Stock phrases Whisper is known to produce on non-speech audio (subtitle-credit residue from
# its training data). Matched case-insensitively; a hit is flagged, never deleted.
HALLUCINATION_PATTERNS = [
    r"thank(s| you) for watching", r"subscribe to", r"subtitles? by", r"amara\.org",
    r"transcribed by", r"please like and subscribe", r"see you (in the )?next (video|time)",
    r"www\.[a-z0-9-]+\.(com|org)", r"copyright .{0,20}\d{4}",
]

STOCK_MAX_WORDS = 8               # a longer segment containing a stock phrase is real speech
POST_VERSION = "2026-09-21a"      # version of the clean-up rules in derive() (D-027)

VAD = {"threshold": 0.5, "min_speech_duration_ms": 250, "min_silence_duration_ms": 500,
       "speech_pad_ms": 200}

PARAMS = {"model": MODEL, "compute_type": COMPUTE_TYPE, "beam_size": BEAM_SIZE,
          "vad": VAD, "vad_model": "silero_v6 (bundled)",
          "condition_on_previous_text": False, "word_timestamps_native": True,
          "lang_detect_segments": LANG_DETECT_SEGMENTS, "english_translation": "reuse_native",
          "low_confidence_rule": {"word_prob_mean_below": LOW_WORD_PROB,
                                  "lang_prob_below": LOW_LANG_PROB_FOR_TEXT}}


def load_model(allow_download: bool):
    dirs = common.enable_cuda12_dlls()
    if not dirs:
        raise SystemExit("NVIDIA CUDA 12 libraries not found (nvidia-cublas-cu12, "
                         "nvidia-cudnn-cu12==9.10.2.21, nvidia-cuda-nvrtc-cu12). See "
                         "requirements.txt; without them the engine cannot use the GPU.")
    from faster_whisper import WhisperModel
    try:
        return WhisperModel(MODEL, device=DEVICE, compute_type=COMPUTE_TYPE,
                            local_files_only=not allow_download)
    except Exception as exc:
        if not allow_download and ("local" in str(exc).lower() or "not found" in str(exc).lower()
                                   or "snapshot" in str(exc).lower()):
            raise SystemExit(
                f"The {MODEL} model is not on disk. It is a one-time 3.09 GB download from "
                f"Hugging Face (Systran/faster-whisper-large-v3, MIT licence). Re-run with "
                f"--allow-download to fetch it.") from exc
        raise


def gpu_memory_used() -> str:
    """From the driver: the speech engine (CTranslate2) does not allocate through PyTorch."""
    import subprocess
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total",
                            "--format=csv,noheader"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "n/a"
    except Exception:
        return "n/a"


def load_audio(platform: str, media_id: str) -> np.ndarray:
    import soundfile as sf
    data, sr = sf.read(str(common.audio_file(platform, media_id)), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != common.AUDIO_SR:
        raise ValueError(f"expected {common.AUDIO_SR} Hz from 5.1, got {sr}")
    return data


def speech_regions(audio: np.ndarray) -> list[tuple[float, float]]:
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    ts = get_speech_timestamps(audio, VadOptions(**VAD))
    return [(round(t["start"] / common.AUDIO_SR, 3), round(t["end"] / common.AUDIO_SR, 3))
            for t in ts]


def segment_record(seg, with_words: bool) -> dict:
    rec = {"start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text.strip(),
           "avg_logprob": round(seg.avg_logprob, 4),
           "no_speech_prob": round(seg.no_speech_prob, 4),
           "compression_ratio": round(seg.compression_ratio, 4)}
    rec["suspect"] = bool(seg.avg_logprob < SUSPECT_LOGPROB
                          or seg.no_speech_prob > SUSPECT_NO_SPEECH
                          or seg.compression_ratio > SUSPECT_COMPRESSION)
    if with_words:
        rec["words"] = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2),
                         "p": round(w.probability, 3)} for w in (seg.words or [])]
    return rec


def hallucination_hits(text: str) -> list[str]:
    low = text.lower()
    return [p for p in HALLUCINATION_PATTERNS if re.search(p, low)]


def asr_one(model, row: pd.Series) -> dict:
    platform, media_id = row["platform"], row["media_id"]
    out = {"platform": platform, "media_id": media_id}
    doc = common.read_cache(platform, media_id)
    prep = doc.get("prep")
    if not prep:
        return {**out, "status": "failed", "error": "run 5.1 first"}
    duration = float(prep["video_duration_sec"])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    t0 = time.time()

    empty = {"lang_audio": None, "lang_audio_prob": None, "lang_audio_top": [],
             "lang_audio_detected": None, "lang_audio_prob_detected": None,
             "speech_sec_vad": 0.0, "transcript_en_failed": None,
             "transcript_native": "", "transcript_en": "", "segments_native": [],
             "segments_en": [], "word_count": 0, "words_per_min": None,
             "suspect_segment_frac": None, "hallucination_hits": []}

    if prep.get("audio_silent"):
        payload = {**empty, "status": "silent_audio", "speech_sec": 0.0,
                   "speech_dur_frac": 0.0, "speech_regions": [], "params": PARAMS,
                   "processed_at": now}
        common.update_cache(platform, media_id, "asr", payload)
        return {**out, **_summary(payload, duration), "sec": round(time.time() - t0, 1)}

    audio = load_audio(platform, media_id)
    regions = speech_regions(audio)
    speech_sec = round(sum(e - s for s, e in regions), 3)
    if speech_sec == 0:
        payload = {**empty, "status": "no_speech", "speech_sec": 0.0, "speech_dur_frac": 0.0,
                   "speech_regions": [], "params": PARAMS, "processed_at": now}
        common.update_cache(platform, media_id, "asr", payload)
        return {**out, **_summary(payload, duration), "sec": round(time.time() - t0, 1)}

    from faster_whisper.vad import VadOptions
    lang, prob, all_probs = model.detect_language(
        audio, vad_filter=True, vad_parameters=VadOptions(**VAD),
        language_detection_segments=LANG_DETECT_SEGMENTS)
    top = [[code, round(float(p), 4)] for code, p in sorted(all_probs, key=lambda x: -x[1])[:5]]

    common_kw = dict(language=lang, beam_size=BEAM_SIZE, vad_filter=True, vad_parameters=VAD,
                     condition_on_previous_text=False)
    segs, _ = model.transcribe(audio, task="transcribe", word_timestamps=True, **common_kw)
    native = [segment_record(s, with_words=True) for s in segs]

    if lang == "en":
        english, en_source = [dict(s, words=None) for s in native], "native_english"
    else:
        segs_en, _ = model.transcribe(audio, task="translate", **common_kw)
        english, en_source = [segment_record(s, with_words=False) for s in segs_en], "translated"
    for s in english:
        s.pop("words", None)

    payload = {
        "status": "ok",
        # Raw model output. `derive()` builds every reported field from these, so the
        # clean-up rules can be re-applied later without the GPU (--repost).
        "lang_audio_detected": lang, "lang_audio_prob_detected": round(float(prob), 4),
        "lang_audio_top": top, "transcript_en_source": en_source,
        "segments_native": native, "segments_en": english,
        "speech_regions": regions, "speech_sec_vad": speech_sec,
        "params": PARAMS, "processed_at": now,
    }
    payload = derive(payload, duration)
    payload["gpu_sec"] = round(time.time() - t0, 1)
    common.update_cache(platform, media_id, "asr", payload)
    return {**out, **_summary(payload, duration), "sec": payload["gpu_sec"]}


def is_stock_phrase(text: str) -> bool:
    """A short segment that is nothing but one of Whisper's stock non-speech outputs.

    Length-limited so a real sentence that happens to contain "subscribe to" is kept.
    """
    return bool(hallucination_hits(text)) and len(text.split()) <= STOCK_MAX_WORDS


def derive(p: dict, duration: float) -> dict:
    """Every reported field, from the raw model output. Idempotent; safe to re-run.

    Clean-up rules (D-027), applied to all videos alike:
    *   A stock-phrase segment is marked `stock_phrase` and left out of the transcript text.
        The segment itself stays in the record for audit.
    *   If no real native segment remains, the video has no intelligible speech: empty
        transcripts, no spoken language (the detection on such audio was a guess - 0.28 to
        0.44 on the cases seen), `speech_dur_frac = 0` as for the 98 no-speech videos. The
        voice-activity reading is kept as `speech_sec_vad`.
    *   If the English translation is left empty while the native transcript is not, the
        translation failed: `transcript_en_failed`, and 5.9 falls back to native-language
        sentiment for that video rather than scoring a stock phrase.
    """
    if p.get("status") in ("silent_audio", "no_speech"):
        return p
    # Caches written before this function existed hold the raw values under the plain names.
    p.setdefault("lang_audio_detected", p.get("lang_audio"))
    p.setdefault("lang_audio_prob_detected", p.get("lang_audio_prob"))
    p.setdefault("speech_sec_vad", p.get("speech_sec"))
    native, english = p["segments_native"], p["segments_en"]
    for s in native + english:
        s["stock_phrase"] = is_stock_phrase(s["text"])
    keep_n = [s for s in native if not s["stock_phrase"]]
    keep_e = [s for s in english if not s["stock_phrase"]]
    hits = sorted({h for s in native + english for h in hallucination_hits(s["text"])})

    if not keep_n:
        p.update({"status": "no_intelligible_speech", "lang_audio": None,
                  "lang_audio_prob": None, "lang_audio_uncertain": None,
                  "transcript_native": "", "transcript_en": "", "transcript_en_failed": None,
                  "word_count": 0, "words_per_min": None, "word_prob_mean": None,
                  "word_prob_min": None, "suspect_segment_frac": None,
                  "transcript_low_confidence": None, "speech_sec": 0.0,
                  "speech_dur_frac": 0.0, "hallucination_hits": hits,
                  "post_version": POST_VERSION})
        return p

    lang, prob = p["lang_audio_detected"], p["lang_audio_prob_detected"]
    text_native = " ".join(s["text"] for s in keep_n).strip()
    text_en = " ".join(s["text"] for s in keep_e).strip()
    words = sum(len(s.get("words") or []) for s in keep_n)
    probs = [w["p"] for s in keep_n for w in (s.get("words") or [])]
    wp_mean = round(float(np.mean(probs)), 4) if probs else None
    seg_sec = sum(s["end"] - s["start"] for s in keep_n) or 0.0
    suspect_sec = sum(s["end"] - s["start"] for s in keep_n if s["suspect"])
    speech_sec = p["speech_sec_vad"]
    p.update({
        "status": "ok", "lang_audio": lang, "lang_audio_prob": prob,
        "lang_audio_uncertain": bool(prob < LOW_LANG_PROB),
        "transcript_native": text_native, "transcript_en": text_en,
        "transcript_en_failed": bool(lang != "en" and text_native and not text_en),
        "speech_sec": speech_sec,
        "speech_dur_frac": round(min(1.0, speech_sec / duration), 4) if duration else None,
        "word_count": int(words),
        "words_per_min": (round(words / (speech_sec / 60.0), 1)
                          if speech_sec >= MIN_SPEECH_SEC_FOR_RATE else None),
        "suspect_segment_frac": round(suspect_sec / seg_sec, 4) if seg_sec else None,
        "word_prob_mean": wp_mean,
        "word_prob_min": round(float(np.min(probs)), 4) if probs else None,
        "transcript_low_confidence": bool((wp_mean is not None and wp_mean < LOW_WORD_PROB)
                                          or prob < LOW_LANG_PROB_FOR_TEXT),
        "hallucination_hits": hits, "post_version": POST_VERSION,
    })
    return p


def _summary(p: dict, duration: float) -> dict:
    return {"status": p["status"], "duration_sec": duration,
            "lang_audio": p["lang_audio"], "lang_audio_prob": p["lang_audio_prob"],
            "lang_audio_uncertain": p.get("lang_audio_uncertain"),
            "speech_sec": p["speech_sec"], "speech_dur_frac": p["speech_dur_frac"],
            "word_count": p["word_count"], "words_per_min": p["words_per_min"],
            "n_segments": len(p["segments_native"]),
            "suspect_segment_frac": p["suspect_segment_frac"],
            "word_prob_mean": p.get("word_prob_mean"),
            "transcript_low_confidence": p.get("transcript_low_confidence"),
            "hallucination_hits": "|".join(p["hallucination_hits"]),
            "transcript_en_source": p.get("transcript_en_source"),
            "transcript_en_failed": p.get("transcript_en_failed"),
            "lang_audio_detected": p.get("lang_audio_detected"),
            "speech_sec_vad": p.get("speech_sec_vad"),
            "native_preview": p["transcript_native"][:160],
            "en_preview": p["transcript_en"][:160]}


def repost(platform: str) -> None:
    """Re-derive every reported field from cached raw output under the current rules."""
    rows = []
    for _, r in common.video_index(platform).iterrows():
        doc = common.read_cache(r["platform"], r["media_id"])
        p = doc.get("asr")
        if not p or p.get("params") != PARAMS:
            continue
        duration = float(doc["prep"]["video_duration_sec"])
        before = (p.get("status"), p.get("transcript_native"), p.get("transcript_en"))
        p = derive(p, duration)
        common.update_cache(r["platform"], r["media_id"], "asr", p)
        after = (p["status"], p["transcript_native"], p["transcript_en"])
        rows.append({"platform": r["platform"], "media_id": r["media_id"],
                     **_summary(p, duration), "changed": before != after})
    df = pd.DataFrame(rows)
    df.drop(columns=["changed"]).to_csv(SUMMARY, index=False)
    print(f"repost: {len(df)} cached transcripts re-derived; {int(df['changed'].sum())} changed")
    print("status:", df["status"].value_counts().to_dict())
    ch = df[df["changed"]]
    if len(ch):
        print(ch[["platform", "media_id", "status", "lang_audio_detected", "native_preview",
                  "en_preview"]].to_string(index=False))


def main() -> None:
    ap = argparse.ArgumentParser(description="5.6 - speech-to-text, language, speech timing.")
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--limit", type=int, help="at most N videos per platform (quick test)")
    ap.add_argument("--only", nargs="+", metavar="PLATFORM_MEDIAID")
    ap.add_argument("--force", action="store_true", help="redo videos already transcribed")
    ap.add_argument("--allow-download", action="store_true",
                    help="permit the one-time 3.09 GB model download")
    ap.add_argument("--repost", action="store_true",
                    help="re-apply the clean-up rules to cached transcripts (no GPU)")
    args = ap.parse_args()

    if args.repost:
        repost(args.platform)
        return

    idx = common.video_index(args.platform)
    if args.only:
        idx = idx[(idx["platform"] + "_" + idx["media_id"]).isin(args.only)]
    if args.limit:
        idx = idx.groupby("platform", group_keys=False).head(args.limit)

    todo = []
    for _, r in idx.iterrows():
        cached = common.read_cache(r["platform"], r["media_id"]).get("asr")
        if cached and not args.force and cached.get("params") == PARAMS:
            continue
        todo.append(r)
    print(f"5.6 asr: {len(idx)} videos selected, {len(todo)} to process "
          f"({len(idx) - len(todo)} already done); model {MODEL} {COMPUTE_TYPE} on {DEVICE}")

    rows = []
    if todo:
        t_load = time.time()
        model = load_model(args.allow_download)
        print(f"model loaded in {time.time() - t_load:.0f}s")
        t0 = time.time()
        audio_done = 0.0
        for i, r in enumerate(todo, 1):
            try:
                res = asr_one(model, r)
            except Exception as exc:
                res = {"platform": r["platform"], "media_id": r["media_id"], "status": "failed",
                       "error": f"{type(exc).__name__}: {exc}"[:300]}
                if "out of memory" in str(exc).lower():
                    print(f"\nGPU ran out of memory on {r['media_id']}. Stopping rather than "
                          f"switching precision part-way, which would make videos incomparable.")
                    rows.append(res)
                    break
            rows.append(res)
            audio_done += float(r["duration_sec"] or 0)
            if i % 10 == 0 or i == len(todo):
                el = time.time() - t0
                print(f"  {i}/{len(todo)}  {el / 60:.1f} min, "
                      f"{audio_done / max(el, 1e-9):.1f}x real time, "
                      f"GPU memory in use {gpu_memory_used()}")

    for _, r in idx.iterrows():
        if not any(x["media_id"] == r["media_id"] and x["platform"] == r["platform"] for x in rows):
            cached = common.read_cache(r["platform"], r["media_id"]).get("asr")
            if cached:
                prep = common.read_cache(r["platform"], r["media_id"]).get("prep", {})
                rows.append({"platform": r["platform"], "media_id": r["media_id"],
                             **_summary(cached, float(prep.get("video_duration_sec") or 0))})

    df = pd.DataFrame(rows)
    if SUMMARY.exists() and len(df):
        old = pd.read_csv(SUMMARY, dtype={"media_id": str})
        df_out = pd.concat([old, df], ignore_index=True).drop_duplicates(
            subset=["platform", "media_id"], keep="last")
    else:
        df_out = df
    if len(df_out):
        df_out.to_csv(SUMMARY, index=False)
        print(f"\nWrote {SUMMARY.relative_to(config.ROOT)}")
    if not len(df):
        return

    print("status:", df["status"].value_counts().to_dict())
    ok = df[df["status"] == "ok"]
    if len(ok):
        print(f"languages: {ok['lang_audio'].value_counts().to_dict()}")
        print(f"uncertain language (prob < {LOW_LANG_PROB}): "
              f"{int(ok['lang_audio_uncertain'].fillna(False).astype(bool).sum())}")
        print(f"speech_dur_frac median {df['speech_dur_frac'].median():.2f}; "
              f"words_per_min median {ok['words_per_min'].median():.0f}")
        lc = ok[ok["transcript_low_confidence"].fillna(False).astype(bool)]
        print(f"low-confidence transcripts (word prob < {LOW_WORD_PROB} or language prob < "
              f"{LOW_LANG_PROB_FOR_TEXT}): {len(lc)} of {len(ok)}")
        hits = ok[ok["hallucination_hits"].fillna("") != ""]
        print(f"videos with a stock hallucination phrase: {len(hits)}")
        if len(hits):
            print(hits[["platform", "media_id", "hallucination_hits"]].to_string(index=False))
    failed = df[df["status"] == "failed"]
    if len(failed):
        print(f"\nFAILED: {len(failed)}")
        print(failed[["platform", "media_id", "error"]].to_string(index=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Task 5.7 - what language is this video in, and does it switch (docs/04 section 1).

Language is a variable here, not plumbing (D-003), and the three places it can differ are kept
apart because they genuinely do:

    lang_audio      what is spoken - Whisper's detection (5.6), the source of truth for speech
    lang_caption    the caption's language - langdetect, with a probability and a reliability flag
    lang_onscreen   burned-in text - **needs OCR (5.5 part B); not measured yet**

    is_code_switched   the fields that exist disagree, or the transcript is low-confidence
                       or its language was uncertain

**Why a flag and not a language count.** docs/04 section 1 defines code-switching as low Whisper
confidence *or* disagreement between the language fields; Hinglish captions in this corpus are
the obvious case. The flag records *which* of those fired (`code_switch_reason`), so a reader can
tell a genuine English caption over Hindi speech from a two-word transcript the model was unsure
about.

**Short text is not classified.** langdetect on a 15-character caption is a guess, so anything
under 20 characters is left unknown rather than given a language, and a detection below 0.90
probability is marked unreliable. The two silent Reels (D-025) and the 106 videos with no speech
have no `lang_audio` - those are nulls, not disagreements.

**Re-run when OCR lands.** `lang_onscreen` stays null and `PARAMS["onscreen"]` says
`not_measured`, so re-running after 5.5 part B fills it in and recomputes the flag.

Runs on all 300 videos (D-030: the focus applies at analysis, not at measurement).

Usage:
    python -m src.features.language
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

SUMMARY = config.INTERIM / "language_summary.csv"
MIN_CHARS = 20          # below this, a caption is not classified
MIN_PROB = 0.90         # below this, the detection is flagged unreliable
PARAMS = {"min_chars": MIN_CHARS, "min_prob": MIN_PROB, "detector": "langdetect 1.0.9",
          "onscreen": "not_measured (needs 5.5 part B OCR)", "version": 1}


def detect_caption(text: str) -> tuple[str | None, float | None, str | None]:
    """Language, probability, and why it was skipped (if it was)."""
    t = str(text or "").strip()
    if len(t) < MIN_CHARS:
        return None, None, f"caption under {MIN_CHARS} characters"
    try:
        from langdetect import DetectorFactory, detect_langs
    except ImportError:
        return None, None, "langdetect not installed"
    DetectorFactory.seed = 0            # langdetect is non-deterministic without this
    try:
        best = detect_langs(t)[0]
        return best.lang, round(float(best.prob), 4), None
    except Exception as exc:
        return None, None, f"detector failed: {type(exc).__name__}"


def one_video(platform: str, media_id: str, caption: str) -> dict:
    doc = common.read_cache(platform, media_id)
    asr = doc.get("asr") or {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lang_caption, prob, skipped = detect_caption(caption)
    lang_audio = asr.get("lang_audio")
    reliable = bool(lang_caption and prob is not None and prob >= MIN_PROB)

    reasons = []
    if lang_audio and lang_caption and reliable and lang_audio != lang_caption:
        reasons.append(f"audio {lang_audio} vs caption {lang_caption}")
    if asr.get("transcript_low_confidence"):
        reasons.append("low-confidence transcript")
    if asr.get("lang_audio_uncertain"):
        reasons.append("uncertain spoken language")

    return {"status": "ok",
            "lang_audio": lang_audio,
            "lang_audio_prob": asr.get("lang_audio_prob"),
            "lang_caption": lang_caption,
            "lang_caption_prob": prob,
            "lang_caption_reliable": reliable,
            "lang_caption_skipped": skipped,
            "lang_onscreen": None,
            "lang_onscreen_skipped": "not measured - needs 5.5 part B (OCR)",
            "langs_known": int(bool(lang_audio)) + int(bool(lang_caption)),
            "lang_match": (None if not (lang_audio and lang_caption and reliable)
                           else lang_audio == lang_caption),
            "is_code_switched": bool(reasons),
            "code_switch_reason": "; ".join(reasons) or None,
            "params": PARAMS, "processed_at": now}


def run(idx: pd.DataFrame, force: bool) -> pd.DataFrame:
    rows = []
    for _, r in idx.iterrows():
        cached = common.read_cache(r["platform"], r["media_id"]).get("language") or {}
        p = (cached if cached.get("params") == PARAMS and not force
             else one_video(r["platform"], r["media_id"], r["caption"]))
        if p is not cached:
            common.update_cache(r["platform"], r["media_id"], "language", p)
        rows.append({"platform": r["platform"], "media_id": r["media_id"],
                     **{k: v for k, v in p.items() if k != "params"}})
    df = pd.DataFrame(rows)
    df.to_csv(SUMMARY, index=False)
    print(f"-> {SUMMARY.relative_to(config.ROOT)}  ({len(df)} rows)")
    return df


def report(df: pd.DataFrame) -> None:
    print(f"\n{len(df)} videos")
    print(f"  spoken language known  : {int(df['lang_audio'].notna().sum())} "
          f"(the rest have no speech - 5.6)")
    print(f"  caption language known : {int(df['lang_caption'].notna().sum())}, of which "
          f"{int(df['lang_caption_reliable'].sum())} at >= {MIN_PROB:g} probability")
    print(f"  captions too short to classify: "
          f"{int((df['lang_caption_skipped'].fillna('').str.contains('under')).sum())}")
    print("\ncaption languages:", df["lang_caption"].value_counts().head(8).to_dict())
    print("spoken languages :", df["lang_audio"].value_counts().head(8).to_dict())

    both = df[df["lang_match"].notna()]
    print(f"\nboth languages known and reliable: {len(both)} videos; "
          f"they agree in {int(both['lang_match'].sum())}, differ in "
          f"{int((~both['lang_match'].astype(bool)).sum())}")
    diff = both[~both["lang_match"].astype(bool)]
    if len(diff):
        pairs = (diff["lang_audio"] + " speech / " + diff["lang_caption"] + " caption")
        print("  most common mismatches:", pairs.value_counts().head(6).to_dict())
        print(f"  English caption over non-English speech: "
              f"{int(((diff['lang_caption'] == 'en')).sum())} videos - the pattern docs/04 "
              f"section 1 predicted")
    print(f"\ncode-switching flag set on {int(df['is_code_switched'].sum())} videos:")
    reasons = df["code_switch_reason"].dropna().str.split("; ").explode()
    print("  reasons (a video can have more than one):",
          reasons.str.replace(r"audio \w+ vs caption \w+", "language mismatch", regex=True)
          .value_counts().to_dict())
    print("\nlang_onscreen is not measured yet - it needs the OCR half of 5.5. Re-running this "
          "step after that fills it in and recomputes the flag.")
    print("No engagement value is read here.")


def main() -> None:
    ap = argparse.ArgumentParser(description="5.7 - caption and spoken language, code-switching.")
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    idx = common.video_index(args.platform)
    df = run(idx, args.force)
    report(df)


if __name__ == "__main__":
    main()

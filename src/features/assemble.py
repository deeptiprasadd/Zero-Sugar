"""Task 5.10 - one row per video: `data/processed/features.parquet`.

Flattens the per-video JSON caches into a single table. The candidate features are **listed
explicitly** below rather than swept up from the caches, because the caches also hold working
material (transcripts, per-window scores, frame lists, file paths) that is not a feature and
must not drift into a model by accident.

**No outcome is read here.** The table carries identity, grouping and exposure columns plus
candidate features. Engagement lives in `dependent_variable.parquet` and is joined only when a
model is fitted, after the pre-registered analysis begins (docs/08 section 7.9).

Two Block E features are deliberately absent:
*   `account_prior_engagement` - it is built from *other videos' engagement*, so it can only be
    computed inside cross-validation folds (Phase 9), never here. Computing it now would leak the
    outcome into the feature table.
*   `posting_hour_local` - the local timezone of each market is not in the data. `posting_hour_utc`
    and `is_weekend_utc` are provided instead, and the limitation is stated: a 9 a.m. post in
    Bangkok and one in São Paulo are different local moments with the same UTC hour.

Excluded on evidence, not oversight:
*   `music_genre_*` - AudioSet's genre labels do not separate this corpus (D-033).
*   `container_*` / `product_*` (5.4) - the frame check failed gate B on 2026-09-29, so product
    visibility is reported as not measured (D-037).

The 5.12 automated labels enter as `auto_*` columns (D-038). Yes/no answers become True/False and
the model's "unsure" becomes null - it is not a "no". Whether a label may enter a model is decided
by 4.2's alpha in 5.11 rule 3, not here.

Usage:
    python -m src.features.assemble
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

OUT = config.PROCESSED / "features.parquet"
SUMMARY = config.INTERIM / "features_summary.csv"

# block -> {cache key: column name}. Anything not listed is working material, not a feature.
CANDIDATES: dict[str, dict[str, str]] = {
    "prep": {"video_duration_sec": "duration_sec", "native_fps": "fps",
             "aspect_ratio": "aspect_ratio", "audio_silent": "audio_silent"},
    "scenes": {"cuts_per_sec": "cuts_per_sec", "scene_count": "scene_count",
               "mean_shot_len_sec": "mean_shot_len_sec", "longest_shot_frac": "longest_shot_frac",
               "is_single_shot": "is_single_shot", "hidden_montage": "hidden_montage"},
    "asr": {"speech_dur_frac": "speech_dur_frac", "word_count": "word_count",
            "words_per_min": "words_per_min", "lang_audio": "lang_audio",
            "transcript_low_confidence": "transcript_low_confidence"},
    "audio_signal": {"loudness_db_mean": "loudness_db_mean",
                     "loudness_range_db": "loudness_range_db", "silence_frac": "silence_frac",
                     "spectral_centroid_hz": "spectral_centroid_hz", "tempo_bpm": "tempo_bpm",
                     "pitch_median_hz": "pitch_median_hz",
                     "pitch_std_semitones": "pitch_std_semitones", "voiced_frac": "voiced_frac"},
    "audio_events": {"music_frac": "music_frac", "music_present": "music_present",
                     "speech_frac_ast": "speech_frac_ast",
                     "speech_sung_frac": "speech_sung_frac", "talk_dur_frac": "talk_dur_frac",
                     "pitch_median_talk_hz": "pitch_median_talk_hz",
                     "pitch_std_talk_semitones": "pitch_std_talk_semitones"},
    "sentiment": {"speech_sentiment_source": "sentiment_speech_source"},
    "visual": {"brightness": "brightness", "contrast": "contrast", "saturation": "saturation",
               "colourfulness": "colourfulness", "red_ratio": "red_ratio",
               "edge_density": "edge_density", "brightness_sd": "brightness_sd",
               "saturation_sd": "saturation_sd", "red_ratio_sd": "red_ratio_sd",
               "red_frame_frac": "red_frame_frac"},
    "faces": {"face_present_frac": "face_present_frac", "mean_face_count": "mean_face_count",
              "max_face_count": "max_face_count", "mean_face_area": "mean_face_area"},
    "ocr": {"ocr_text_frame_frac": "ocr_text_frame_frac", "ocr_region_count": "ocr_region_count",
            "ocr_mean_text_area": "ocr_mean_text_area", "ocr_max_text_area": "ocr_max_text_area"},
    "meta": {"caption_char_len": "caption_char_len", "caption_word_count": "caption_word_count",
             "hashtag_count": "hashtag_count", "mention_count": "mention_count",
             "emoji_count": "emoji_count", "has_question_mark": "has_question_mark",
             "title_char_len": "title_char_len",
             "title_char_len_z_lang": "title_char_len_z_lang", "creator_collab": "creator_collab"},
    "language": {"lang_caption": "lang_caption", "is_code_switched": "is_code_switched",
                 "lang_match": "lang_match"},
    "keywords": {"kw_offer": "kw_offer", "kw_new": "kw_new", "kw_taste": "kw_taste",
                 "kw_zero_sugar": "kw_zero_sugar", "kw_event": "kw_event",
                 "kw_together": "kw_together"},
    "annotation": {"has_cta": "auto_has_cta", "has_celebrity": "auto_has_celebrity",
                   "has_influencer": "auto_has_influencer", "humour_present": "auto_humour_present",
                   "promotional_language": "auto_promotional_language",
                   "product_vs_lifestyle": "auto_product_vs_lifestyle",
                   "ugc_vs_brand": "auto_ugc_vs_brand"},
}
YES_NO = ["auto_has_cta", "auto_has_celebrity", "auto_has_influencer", "auto_humour_present",
          "auto_promotional_language"]
# Features that come from a nested part of a block.
NESTED = {
    "motion_px_per_sec": ("frames", ("summary", "motion_px_per_sec_median")),
    "sentiment_speech": ("sentiment", ("sent_speech_en", "compound")),
    "sentiment_caption": ("sentiment", ("sent_caption", "compound")),
    "emotion_label": ("sentiment", ("emotion_speech_en", "label")),
    "emotion_score": ("sentiment", ("emotion_speech_en", "score")),
}
# Grouping and identity columns: never features, always needed.
KEYS = ["platform", "media_id", "account", "in_focus", "is_zero_sugar", "selection", "market",
        "region", "account_size_tier", "followers", "video_age_days", "posted_at", "dv_status"]


def dig(doc: dict, block: str, path: tuple):
    node = doc.get(block) or {}
    for step in path:
        if not isinstance(node, dict):
            return None
        node = node.get(step)
        if node is None:
            return None
    return node


def build() -> pd.DataFrame:
    idx = common.video_index()
    rows = []
    for _, r in idx.iterrows():
        doc = common.read_cache(r["platform"], r["media_id"])
        row = {"platform": r["platform"], "media_id": r["media_id"]}
        for block, keys in CANDIDATES.items():
            src = doc.get(block) or {}
            for key, col in keys.items():
                row[col] = src.get(key)
        for col, (block, path) in NESTED.items():
            row[col] = dig(doc, block, path)
        row["blocks_present"] = sum(bool(doc.get(b)) for b in CANDIDATES)
        rows.append(row)
    feats = pd.DataFrame(rows)

    # Identity, grouping and exposure from the analysis table - **no engagement column**.
    dv = pd.read_parquet(config.PROCESSED / "dependent_variable.parquet")
    banned = [c for c in dv.columns if "engagement" in c or c in ("likes", "comments", "views")]
    keep = [c for c in KEYS if c in dv.columns]
    out = dv[keep].merge(feats, on=["platform", "media_id"], how="right", validate="1:1")
    leaked = [c for c in out.columns if c in banned]
    if leaked:
        raise SystemExit(f"outcome columns must not be here: {leaked}")

    # Posting time. Local time is not derivable (see the module docstring).
    ts = pd.to_datetime(out["posted_at"], utc=True, errors="coerce")
    out["posting_hour_utc"] = ts.dt.hour
    out["is_weekend_utc"] = ts.dt.dayofweek >= 5

    # Two keyword composites, so Block C's keywords fit the 18-20 budget without being cut
    # entirely (5.11, D-036). Null-safe: True if either group hit, False only if both were
    # searched and neither hit, null if neither was searched - a gap is never a "no".
    def any_of(a: str, b: str) -> pd.Series:
        va, vb = out[a], out[b]
        hit = (va == True) | (vb == True)                       # noqa: E712
        searched = va.notna() | vb.notna()
        return pd.Series(np.where(hit, True, np.where(searched, False, None)), index=out.index)

    out["kw_promotional"] = any_of("kw_offer", "kw_new")
    out["kw_experience"] = any_of("kw_taste", "kw_together")

    # Automated labels: yes/no -> True/False; "unsure" and failed answers -> null (D-038).
    for c in YES_NO:
        out[c] = out[c].map({"yes": True, "no": False}).astype(object)
        out[c] = out[c].where(out[c].notna(), None)
    for c in ["auto_product_vs_lifestyle", "auto_ugc_vs_brand"]:
        out[c] = out[c].where(out[c] != "unsure", None)
    return out.drop(columns=["posted_at"])


def report(df: pd.DataFrame) -> None:
    ident = [c for c in KEYS if c in df.columns] + ["blocks_present"]
    feats = [c for c in df.columns if c not in ident]
    print(f"\n{len(df)} videos, {len(feats)} candidate features "
          f"(budget after pruning: 18-20, D-030)")
    print(f"every block present for all videos: "
          f"{bool((df['blocks_present'] == len(CANDIDATES)).all())}")

    miss = df[feats].isna().mean().sort_values(ascending=False)
    print(f"\nmissing values - pruning rule 2 drops anything over 30% that cannot be flagged:")
    for c, v in miss[miss > 0].head(12).items():
        mark = "  <- over 30%" if v > 0.30 else ""
        print(f"  {c:28} {v:5.1%}{mark}")
    print(f"  ({int((miss == 0).sum())} features have no missing values)")

    num = df[feats].select_dtypes("number")
    near = {}
    for c in feats:
        s = df[c].dropna()
        if len(s):
            top = s.value_counts(normalize=True).iloc[0]
            if top > 0.95:
                near[c] = top
    print(f"\nnear-constant - pruning rule 1 drops anything above 95% one value:")
    for c, v in sorted(near.items(), key=lambda kv: -kv[1]):
        print(f"  {c:28} {v:5.1%} share the same value")
    if not near:
        print("  none")
    print(f"\nby type: {num.shape[1]} numeric, "
          f"{len([c for c in feats if df[c].dtype == bool])} boolean, "
          f"{len([c for c in feats if df[c].dtype == object])} text/categorical")
    print("\nNo engagement column is in this table (checked). It is joined only when a model is "
          "fitted, after docs/08 section 7.9's analysis begins.")


def main() -> None:
    ap = argparse.ArgumentParser(description="5.10 - assemble features.parquet.")
    ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    df = build()
    df.to_parquet(OUT, index=False)
    df.to_csv(SUMMARY, index=False)
    print(f"-> {OUT.relative_to(config.ROOT)}  ({len(df)} rows, {df.shape[1]} columns)")
    print(f"-> {SUMMARY.relative_to(config.ROOT)}")
    report(df)


if __name__ == "__main__":
    main()

"""Tasks 5.14, 5.15 and the language-safe text counts of docs/05 Block C.

Everything here comes from metadata already collected - no model, no GPU, no download.

    5.14  title_char_len, title_word_count          YouTube only (Reels have no title)
          title_char_len_z_lang                     length as a z-score within its language
    5.15  creator_collab                            Instagram: the post is a collaboration
                                                    (D-032 - replaces the dropped is_sponsored)
    Block C, language-safe counts (docs/04 section 5):
          caption_char_len, caption_word_count, hashtag_count, mention_count, emoji_count,
          has_question_mark                         (matches the Arabic mark as well)

**Two different texts, and they are not mixed.** A Reel has one caption. A Short has a title and
a description, and `common.video_index()` joins them - that joined text is what 5.9 scored and
what the caption counts use here, so the two steps agree. `title_*` is the Short's title alone,
and is null for every Reel: a feature that exists on one platform only enters platform-specific
models, never a pooled one (docs/05 section 4.0, rule 3).

**Normalising length within language.** Character counts mean different things in different
scripts (docs/04 section 5), so `title_char_len_z_lang` is the z-score within the language of the
video's own text. That language comes from 5.9's detection on the **joined title and
description**, not on the title alone - a 50-character title is too short to detect reliably, and
the two are written in the same language in this corpus. Task 5.7 replaces it with a properly
established caption language, after which this step can be re-run. A language with fewer than 5
titles is left null and flagged rather than standardised against itself (today: Arabic 4,
Turkish 1).

Runs on all 300 videos (the Zero Sugar focus applies at analysis, not at measurement - D-030).

Usage:
    python -m src.features.metadata
    python -m src.features.metadata --only youtube_dwrWSRpG77Q
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

SUMMARY = config.INTERIM / "metadata_summary.csv"
MIN_LANG_GROUP = 5          # below this, no within-language z-score
PARAMS = {"min_lang_group": MIN_LANG_GROUP, "version": 1}

_HASHTAG = re.compile(r"#\w+", re.UNICODE)
_MENTION = re.compile(r"@[A-Za-z0-9_.]+")
_QUESTION = re.compile(r"[?؟]")        # ASCII and Arabic question marks (docs/04 section 5)


def _emoji_count(text: str) -> int:
    import emoji
    return emoji.emoji_count(text)


def text_counts(text: str) -> dict:
    t = str(text or "")
    return {
        "caption_char_len": len(t),
        "caption_word_count": len(t.split()),
        "hashtag_count": len(_HASHTAG.findall(t)),
        "mention_count": len(_MENTION.findall(t)),
        "emoji_count": _emoji_count(t),
        "has_question_mark": bool(_QUESTION.search(t)),
    }


def build(idx: pd.DataFrame) -> pd.DataFrame:
    yt = pd.read_parquet(config.PROCESSED / "youtube_corpus.parquet")
    yt = yt[yt["in_corpus"].astype(bool)]
    titles = dict(zip(yt["video_id"].astype(str), yt["title"].fillna("")))
    ig = pd.read_parquet(config.PROCESSED / "instagram_corpus.parquet")
    ig = ig[ig["in_corpus"].astype(bool)]
    collab = dict(zip(ig["shortcode"].astype(str), ig["is_collab"]))

    rows = []
    for _, r in idx.iterrows():
        platform, mid = r["platform"], r["media_id"]
        row = {"platform": platform, "media_id": mid, **text_counts(r["caption"])}

        # 5.14 - title, YouTube only
        if platform == "youtube":
            title = str(titles.get(mid, ""))
            row["title_char_len"] = len(title)
            row["title_word_count"] = len(title.split())
        else:
            row["title_char_len"] = np.nan
            row["title_word_count"] = np.nan

        # 5.15 - collaboration post, Instagram only. YouTube Shorts are all brand-channel
        # posts, so the flag is False there by construction, not missing.
        row["creator_collab"] = bool(collab.get(mid, False)) if platform == "instagram" else False

        # language of the text, as detected by 5.9 on the same string
        sent = common.read_cache(platform, mid).get("sentiment") or {}
        row["text_lang"] = sent.get("caption_lang")
        rows.append(row)

    df = pd.DataFrame(rows)

    # 5.14 - length standardised inside its own language, where there are enough titles
    df["title_char_len_z_lang"] = np.nan
    df["title_z_lang_skipped"] = None
    yt_mask = df["platform"] == "youtube"
    for lang, n in df.loc[yt_mask, "text_lang"].value_counts().items():
        m = yt_mask & (df["text_lang"] == lang)
        if n >= MIN_LANG_GROUP:
            v = df.loc[m, "title_char_len"].astype(float)
            sd = v.std(ddof=0)
            df.loc[m, "title_char_len_z_lang"] = (v - v.mean()) / sd if sd > 0 else 0.0
        else:
            df.loc[m, "title_z_lang_skipped"] = f"only {int(n)} titles in {lang}"
    df.loc[yt_mask & df["text_lang"].isna(), "title_z_lang_skipped"] = "no language detected"
    return df


def report(df: pd.DataFrame) -> None:
    print(f"\n{len(df)} videos")
    yt, ig = df[df.platform == "youtube"], df[df.platform == "instagram"]
    print("\ntext counts (median, and share that are zero):")
    for c in ["caption_char_len", "caption_word_count", "hashtag_count", "mention_count",
              "emoji_count"]:
        print(f"  {c:20} YouTube {yt[c].median():7.1f}  ({(yt[c] == 0).mean():.0%} zero)   "
              f"Instagram {ig[c].median():7.1f}  ({(ig[c] == 0).mean():.0%} zero)")
    print(f"  {'has_question_mark':20} YouTube {int(yt['has_question_mark'].sum()):3} videos     "
          f"Instagram {int(ig['has_question_mark'].sum()):3} videos")
    print("\n5.14 title length (YouTube only):")
    t = yt["title_char_len"]
    print(f"  median {t.median():.0f} characters (10th-90th {t.quantile(.1):.0f}-{t.quantile(.9):.0f}), "
          f"max {t.max():.0f}; word count median {yt['title_word_count'].median():.0f}")
    print(f"  standardised within language for {int(yt['title_char_len_z_lang'].notna().sum())} "
          f"of {len(yt)} Shorts; skipped: "
          f"{yt['title_z_lang_skipped'].dropna().value_counts().to_dict()}")
    print(f"  languages used: {yt['text_lang'].value_counts(dropna=False).head(8).to_dict()}")
    print("\n5.15 creator collaboration:")
    print(f"  Instagram {int(ig['creator_collab'].sum())} of {len(ig)} Reels; "
          f"YouTube {int(yt['creator_collab'].sum())} of {len(yt)} (brand channels by construction)")
    print("\nNo engagement value is read here.")


def main() -> None:
    ap = argparse.ArgumentParser(description="5.14, 5.15 and Block C text counts.")
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--only", nargs="+", metavar="PLATFORM_MEDIAID")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    idx = common.video_index(args.platform)
    if args.only:
        idx = idx[(idx["platform"] + "_" + idx["media_id"]).isin(args.only)]
    df = build(idx)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for _, r in df.iterrows():
        payload = {k: (None if isinstance(v, float) and pd.isna(v) else v)
                   for k, v in r.items() if k not in ("platform", "media_id")}
        common.update_cache(r["platform"], r["media_id"], "meta",
                            {**payload, "params": PARAMS, "processed_at": now})
    df.to_csv(SUMMARY, index=False)
    print(f"-> {SUMMARY.relative_to(config.ROOT)}  ({len(df)} rows)")
    report(df)


if __name__ == "__main__":
    main()

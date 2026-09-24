"""Build the shareable data set in reports/shared/ (D-022).

Everything in `reports/shared/` is meant to be shown to a supervisor or examiner, so it holds
only data and a factual description of how the data was produced. Internal working material
- the decision log, the task tracker, review sheets, backups, raw scraper output - stays where
it is and is never copied here.

What "clean" means, and what it does not:
- **Removed:** internal workflow notes (who ran which step), personal file-system paths, and
  anything credential-shaped.
- **Kept, always:** how every value was obtained. Collection routes, manual records and
  automated steps are described in plain method terms. Clean means professional, not
  silent about method - D-010 and D-022 require the method to be stated.

`check()` scans the folder after every export and fails if a forbidden pattern appears, so a
careless edit cannot leak internal notes into a shared file.

Usage:
    python -m src.export.shared          # rebuild reports/shared/ and check it
    python -m src.export.shared --check  # check only
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.codebook import codebook_markdown  # noqa: E402

SHARED = config.REPORTS / "shared"

# Private screening list, kept outside this repository (internal/, gitignored) so the
# words it screens for are not published alongside the code. One regex per line, blank
# lines and # comments ignored. Missing or empty is treated as a failure, not as "clean":
# a silently weaker check is worse than none, because the export would look verified.
SCREEN_WORDS_FILE = config.ROOT / "internal" / "screen_words.txt"


def _assistant_note_pattern() -> re.Pattern:
    if not SCREEN_WORDS_FILE.exists():
        raise SystemExit(
            f"Missing {SCREEN_WORDS_FILE}.\n"
            "  The shared-export leak check needs its private word list.\n"
            "  Restore it before exporting - do not export without this check."
        )
    parts = [
        ln.strip()
        for ln in SCREEN_WORDS_FILE.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    if not parts:
        raise SystemExit(f"{SCREEN_WORDS_FILE} has no patterns; refusing to export.")
    return re.compile("|".join(parts), re.I)


# Patterns that must never appear in a shared file.
FORBIDDEN = {
    "internal assistant note": _assistant_note_pattern(),
    "personal file path": re.compile(r"[A-Za-z]:\\\\?Users|Deepti Prasad|AppData|scratchpad", re.I),
    "internal document reference": re.compile(r"TODO\.md|HANDOFF|00-decisions|progress-log|\bD-0\d\d\b|\bO-\d\d\b", re.I),
    "credential-like string": re.compile(r"AIza[0-9A-Za-z_\-]{20,}|apify_api_[0-9A-Za-z]{10,}|LOGIN_INFO|SAPISID"),
}

GROUP = {
    "curated_zero_sugar": "Zero Sugar - manually verified",
    "curated_relabelled_not_zero_sugar": "Regular - manually re-checked, not Zero Sugar",
    "screener_zero_sugar_comparison": "Zero Sugar - named in caption text",
    # A random draw is not "regular": on YouTube 49 of them show Zero Sugar on screen (D-029)
    "regular_fill": "Random draw",
    "stratified_fill": "Random draw",
    "replacement_fill": "Random draw (replacement)",
    "zero_sugar_census": "Zero Sugar - named in title, description or tags",
}


def _label_method(v: str) -> str:
    v = str(v or "")
    if v.startswith("researcher_visual (relabelled"):
        return "Manual visual check (re-checked)"
    if v.startswith("researcher_visual"):
        return "Manual visual check"
    if v.startswith("text_screener"):
        return "Caption text names Zero Sugar"
    return "Not identified as Zero Sugar"


def _yt_label_method(method: str, zero_sugar: bool) -> str:
    """How a Short's Zero Sugar label was decided, from `zs_label_method` (D-029).

    Fails on a method with no wording here, so a new route can never be shared under an old name.
    """
    if method == "text":
        return ("Title, description or tags name Zero Sugar (text screening)" if zero_sugar
                else "Not identified as Zero Sugar")
    if method == "researcher_visual_check":
        return "Manual visual check: Zero Sugar" if zero_sugar else "Manual visual check: not Zero Sugar"
    raise SystemExit(f"youtube: no shared wording for zs_label_method {method!r} - add it to "
                     "_yt_label_method() before exporting")


def _metrics_source(v: str) -> str:
    v = str(v or "")
    if v.startswith("researcher screenshot"):
        return "Recorded manually from the post (visible only when logged in); verified by the researcher"
    if v.startswith("yt-dlp"):
        return "Public post data via yt-dlp"
    if v == "Apify":
        return "Public post data via Apify Instagram scraper"
    return v or "unknown"


def _engagement_source(row: pd.Series) -> str:
    """How the likes and comments in this row were read - including a 7-day re-read."""
    first = _metrics_source(row["metadata_source"])
    refreshed = row.get("metrics_refreshed_at")
    if refreshed is None or pd.isna(refreshed):
        return first
    if first == "Public post data via yt-dlp":
        return "Public post data via yt-dlp, re-read at least 7 days after posting"
    return ("Public post data via yt-dlp, re-read at least 7 days after posting "
            f"(first read: {first[0].lower()}{first[1:]})")


def _followers_source(v: str) -> str:
    v = str(v or "")
    if v.startswith("apify"):
        return "Public profile data via Apify"
    if v.startswith("researcher_read") or v.startswith("researcher_transcribed"):
        return "Read from the Instagram profile by the researcher (as displayed, rounded)"
    return v or "unknown"


def _download_route(v: str) -> str:
    v = str(v or "")
    if "sssinstagram" in v:
        return "Downloaded manually via sssinstagram.com (post visible only when logged in)"
    if v.startswith("Apify video URL"):
        return "Apify direct video URL"
    if v.startswith("yt-dlp (logged in)"):
        return "yt-dlp, signed in to a YouTube account"
    if v.startswith("yt-dlp"):
        return "yt-dlp"
    return v or "unknown"


def _manifest(platform: str) -> pd.DataFrame:
    m = pd.read_csv(config.MEDIA / "download_manifest.csv", dtype={"media_id": str})
    m = m[m["platform"] == platform].drop_duplicates("media_id", keep="last").set_index("media_id")
    return m[["route", "width", "height", "fps", "duration_sec", "has_audio"]]


def instagram() -> pd.DataFrame:
    c = pd.read_parquet(config.PROCESSED / "instagram_corpus.parquet")
    c = c[c["in_corpus"]].copy()
    m = _manifest("instagram")
    c = c.join(m, on="shortcode", rsuffix="_file")
    out = pd.DataFrame({
        "reel_code": c["shortcode"],
        "url": c["permalink"],
        "corpus_group": c["corpus_reason"].map(GROUP),
        "zero_sugar": c["is_zero_sugar"],
        "in_analysis_set": c["in_focus"],
        "zero_sugar_label_method": c["zs_label_source"].map(_label_method),
        "coca_cola_account": c["source_handle"],
        "posted_by": c["owner_username"],
        "collaboration_post": c["is_collab"],
        "market": c["market"],
        "region": c["region"],
        "account_type": c["account_type"],
        "posted_at_utc": c["timestamp"],
        "likes": c["like_count"],
        "comments": c["comments_count"],
        "followers_of_poster": c["owner_followers"],
        "engagement_data_source": c.apply(_engagement_source, axis=1),
        "followers_source": c["followers_source"].map(_followers_source),
        "engagement_age_ok": c["metrics_maturity"].map(
            {"mature": "yes", "too_young_refresh": "no - refresh after 7 days"}),
        "video_width": c["width_file"], "video_height": c["height_file"],
        "video_fps": c["fps"], "video_seconds": c["duration_sec_file"],
        "has_audio": c["has_audio"],
        "video_source": c["route"].map(_download_route),
    })
    return out.sort_values(["corpus_group", "region", "reel_code"])


def youtube() -> pd.DataFrame:
    c = pd.read_parquet(config.PROCESSED / "youtube_corpus.parquet")
    c = c[c["in_corpus"]].copy()
    m = _manifest("youtube")
    c = c.join(m, on="video_id", rsuffix="_file")
    out = pd.DataFrame({
        "video_id": c["video_id"],
        "url": "https://www.youtube.com/shorts/" + c["video_id"],
        "title": c["title"],
        "channel": c["channel_title"],
        "market": c.get("market"),
        "corpus_group": c["corpus_reason"].map(GROUP),
        "zero_sugar": c["is_zero_sugar"],
        "in_analysis_set": c["in_focus"],
        "zero_sugar_label_method": [_yt_label_method(m, z) for m, z in
                                    zip(c["zs_label_method"], c["is_zero_sugar"].astype(bool))],
        "published_at_utc": c["published_at"],
        "views": c["view_count"], "likes": c["like_count"], "comments": c["comment_count"],
        "channel_subscribers": c["subscriber_count"],
        "metadata_source": "YouTube Data API v3",
        "video_width": c["width_file"],  # always the ffprobe measurement, never collection metadata
        "video_height": c["height_file"], "video_fps": c["fps"],
        "video_seconds": c["duration_sec_file"], "has_audio": c["has_audio"],
        "video_source": c["route"].map(_download_route),
    })
    return out.sort_values(["zero_sugar", "views"], ascending=[False, False])


DICTIONARY = [
    ("both", "corpus_group", "Why the video is in the 150: Zero Sugar (manually verified or named in text) or another Coca-Cola video drawn at random. On YouTube a random draw can still be Zero Sugar - see zero_sugar_label_method"),
    ("both", "zero_sugar", "True if the video features Coca-Cola Zero Sugar"),
    ("both", "in_analysis_set", "True if the video is in the analysed set (Zero Sugar videos only). The other videos are kept in these files and used only as a comparison check"),
    ("both", "zero_sugar_label_method", "How the Zero Sugar label was established: text screening, or a manual visual check of the video"),
    ("both", "likes / comments", "Engagement counts. Empty means hidden by the account, not zero"),
    ("both", "video_width / video_height / video_fps / video_seconds / has_audio", "Measured with ffprobe on the downloaded file"),
    ("both", "video_source", "How the video file was obtained"),
    ("instagram", "coca_cola_account", "The Coca-Cola account the Reel belongs to"),
    ("instagram", "posted_by", "Account shown as the poster; differs from coca_cola_account on collaboration posts"),
    ("instagram", "followers_of_poster", "Followers of posted_by; the exposure base for engagement rates"),
    ("instagram", "engagement_age_ok", "Engagement is used only if read at least 7 days after posting"),
    ("instagram", "region", "One of 8 regional groups used for analysis (market-level n is too small)"),
    ("youtube", "channel_subscribers", "Subscribers of the channel; the exposure base for engagement rates"),
]

README = """# Shared data - Coca-Cola short-form video study

Two corpora of 150 videos each, with the variables and sources below. Column definitions
are in `data_dictionary.csv`.

| File | Contents |
|---|---|
| `youtube_corpus.csv` | 150 YouTube Shorts from 5 official Coca-Cola channels (74 Zero Sugar) |
| `instagram_corpus.csv` | 150 Instagram Reels from official Coca-Cola accounts, incl. collaboration posts (112 Zero Sugar) |
| `codebook.md` | Definitions used for manual coding of a random 60-video subset |

## How the data was obtained

- **YouTube metadata:** YouTube Data API v3 (official API, public data).
- **YouTube video files:** yt-dlp, signed in to a YouTube account (public Shorts only).
- **Instagram metadata:** public post and profile data via the Apify Instagram scraper and
  yt-dlp. For posts visible only when logged in, likes and comments were recorded manually
  from the post and verified.
- **Instagram video files:** yt-dlp; posts visible only when logged in were downloaded
  manually via sssinstagram.com.
- **Zero Sugar labels:** Instagram - manual visual check of each Reel, plus Reels whose
  caption names Zero Sugar; YouTube - text screening of title, description and tags, then a
  manual visual check of every Short the text did not name (a sheet of 8 to 16 still frames
  spread through the Short - one per shot, evenly thinned when a Short has more than 16 shots -
  with the video to hand). 25 of those Shorts had been coded blind by the same coder a week
  earlier; the two looks gave the same Zero Sugar answer for 16 of the 25.
- **Video properties:** measured with ffprobe on each downloaded file.

## What is analysed

The study analyses **Coca-Cola Zero Sugar short videos only**: 186 of the 300 videos here, of
which **183 have a usable engagement figure** - 111 Instagram Reels from 16 accounts and 72
YouTube Shorts from 5 channels, 58 of those from the global Coca-Cola channel. The column
`in_analysis_set` marks them. The other 114 videos stay in these files and are used only as a
comparison check, so nothing is hidden and nothing is deleted.

Two things follow, and both are reported with every result:

- **The two platforms contribute unequal numbers**, from very different numbers of accounts.
- **The Zero Sugar label decides which videos are analysed**, and on YouTube that label is a
  judgement from watching the video rather than from text. Its repeat reliability is limited: on
  25 Shorts checked twice by the same person a week apart, the two answers agreed for 16. Results
  are reported with that figure, and the label is not described as validated.

Every feature is still measured on all 300 videos; the focus applies when results are produced.

## Selection

The two platforms were sampled differently. On YouTube, every Short whose title,
description or tags name Zero Sugar was kept and the rest drawn at random (fixed seed); the
random draws were then checked by eye, and those showing Zero Sugar packaging are labelled
Zero Sugar. On Instagram, most Zero Sugar Reels were hand-picked by manual review of account
pages (the Zero Sugar Reels readily visible on each page, not every one), plus Reels whose
caption names Zero Sugar, and the rest drawn at random (fixed seed). Zero Sugar is therefore
over-represented, most of all on Instagram, and corpus averages are not estimates for all
Coca-Cola posts. Engagement is used only when
read at least 7 days after posting; Reels first read sooner were re-read with yt-dlp once
they were, and their rows say so. Unusable videos (removed from the platform, or not
vertical) were replaced by random draws.
"""


def export() -> None:
    SHARED.mkdir(parents=True, exist_ok=True)
    ig, yt = instagram(), youtube()
    ig.to_csv(SHARED / "instagram_corpus.csv", index=False, encoding="utf-8-sig")
    yt.to_csv(SHARED / "youtube_corpus.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(DICTIONARY, columns=["platform", "column", "meaning"]).to_csv(
        SHARED / "data_dictionary.csv", index=False, encoding="utf-8-sig")
    (SHARED / "README.md").write_text(README, encoding="utf-8")
    (SHARED / "codebook.md").write_text(codebook_markdown(), encoding="utf-8")
    print(f"exported: instagram {len(ig)} rows, youtube {len(yt)} rows -> {SHARED.relative_to(config.ROOT)}")


def check() -> bool:
    problems = []
    for f in sorted(SHARED.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix.lower() not in (".csv", ".md", ".txt", ".json", ".html"):
            problems.append((f.name, "file type not checked - review by hand before sharing"))
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for what, pat in FORBIDDEN.items():
            hit = pat.search(text)
            if hit:
                problems.append((f.name, f"{what}: ...{text[max(0, hit.start()-25):hit.end()+25]!r}..."))
    if problems:
        print("NOT CLEAN:")
        for name, msg in problems:
            print(f"  {name}: {msg}")
        return False
    print(f"clean: {len(list(SHARED.glob('*')))} files in {SHARED.relative_to(config.ROOT)} passed every check")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="Build and check reports/shared/.")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not args.check:
        export()
    if not check():
        raise SystemExit(1)


if __name__ == "__main__":
    main()

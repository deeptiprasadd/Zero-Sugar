"""Every sentence the tool's page shows, in one place (D-059), so the wording rules can be checked.

Rules (D-042, D-046, D-047 rule 10, D-054, D-059): "typical" and "range", never a single predicted number or
"will get"; "associated with", never "causes" or "drives"; no platform recommendation; the Instagram score only
as a position, never a probability; nothing from the pooled models or the automated labels.
`FORBIDDEN` is checked against every rendered page by `src.serve.app --check`.
"""
from __future__ import annotations

import math

FORBIDDEN = ["will get", "causes", "drives", "we recommend", "better platform", "best platform", "guarantee"]

GROUP_NAMES = {"video": "Pictures: cuts, frames and movement", "speech": "Speech",
               "signal": "Loudness, faces and colour", "gpu": "Music and talking, caption tone, on-screen text",
               "text": "Language, keywords and caption counts"}

PLATFORM = {"instagram": "Instagram Reels", "youtube": "YouTube Shorts"}

# feature -> (plain name, how the value is shown)
FEATURES = {
    "duration_sec": ("Length", "seconds"),
    "cuts_log1p": ("Cutting pace", "cuts"),
    "motion_px_per_sec": ("Movement on screen", "motion"),
    "face_present_frac": ("Frames showing a face", "share"),
    "face_area0": ("Size of the largest face", "share_frame"),
    "edge_density": ("Visual detail (edges)", "plain3"),
    "colourfulness": ("Colourfulness", "plain3"),
    "red_ratio": ("Share of Coca-Cola red in the picture", "share_pixels"),
    "ocr_region_count": ("Blocks of on-screen text", "per_frame"),
    "ocr_mean_text_area": ("Screen covered by text", "share_frame"),
    "music_frac": ("Time with music", "share_time"),
    "talk_dur_frac": ("Time with talking", "share_time"),
    "loudness_db_mean": ("Loudness", "db"),
    "loudness_range_db": ("Loudness range", "db"),
    "sentiment_caption": ("Caption tone (-1 negative to +1 positive)", "signed"),
    "caplen_lang": ("Caption length", "caption"),
    "hashtag_count": ("Hashtags", "count"),
    "emoji_count": ("Emoji", "count"),
    "kw_event": ("Mentions an event (sport, music, festival)", "yesno"),
    "kw_promotional": ("Mentions an offer or something new", "yesno"),
}


def value_text(key: str, v: float | None, caption_chars: int | None = None) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "not measured"
    kind = FEATURES[key][1]
    if kind == "seconds":
        return f"{v:.0f} seconds"
    if kind == "cuts":
        return f"{math.expm1(v):.2f} cuts a second"
    if kind == "motion":
        return f"{v:.0f} (pixels a second)"
    if kind == "share":
        return f"{v:.0%} of frames"
    if kind == "share_frame":
        return f"{v:.1%} of the frame"
    if kind == "share_pixels":
        return f"{v:.1%} of pixels"
    if kind == "share_time":
        return f"{v:.0%} of the video"
    if kind == "per_frame":
        return f"{v:.1f} per frame"
    if kind == "db":
        return f"{v:.0f} dB"
    if kind == "signed":
        return f"{v:+.2f}"
    if kind == "caption":
        return f"{caption_chars} characters" if caption_chars is not None else "measured"
    if kind == "count":
        return f"{v:.0f}"
    if kind == "yesno":
        return "yes" if v >= 0.5 else "no"
    return f"{v:.3f}"


def pct_text(p: dict | None) -> str:
    if not p or p.get("pct") is None:
        return "-"
    if p.get("beyond") == "below":
        return "below every one"
    if p.get("beyond") == "above":
        return "above every one"
    return f"{p['pct']:.0f}%"


def rate_text(r: float) -> str:
    return f"{r:.3%}" if r < 0.001 else (f"{r:.2%}" if r < 0.1 else f"{r:.1%}")


def count_text(n: float) -> str:
    return f"{n:,.0f}" if n >= 1 else "fewer than 1"


TEXT = {
    "title": "Coca-Cola Zero Sugar short-video check",
    "intro": ("Upload a short video or paste an Instagram or YouTube link. The tool measures it the same way it "
              "measured 192 Coca-Cola Zero Sugar videos (Instagram 120, YouTube 72) and shows what a typical video "
              "from an account of your size gets, and how this video's measures compare."),
    "base_head": "What a typical video gets",
    "base_lead": ("For an account the models have not seen, they could not predict better than this. It is the "
                  "typical result for a Zero Sugar video from an account of this size, not a forecast for this video."),
    "base_no_followers": "Enter the account's follower count to see what a typical video gets.",
    "ig_head": "Instagram content score (exploratory)",
    "ig_lead": ("Found in a secondary analysis, not confirmed. On accounts it had not seen, the model ranked "
                "videos better than chance (0.70 on a scale where 0.5 is chance), but its scores barely move and "
                "cannot be read as a chance of high engagement, so no probability is shown."),
    "diag_head": "This video's measures beside the 192",
    "diag_lead": ("A description, not advice: none of these measures was shown to raise engagement. The two right "
                  "columns show where this video sits: the share of the 192 videos (and of this platform's videos) "
                  "with a lower value, videos with the same value counted half; for yes/no measures, the share "
                  "with 'yes'."),
    "hand_head": "Your descriptions beside the 192",
    "hand_lead": ("Your answers are shown next to how often the researcher found the same thing in the 192 videos. "
                  "They are not used in any number above."),
    "missing_head": "What the tool did not have",
    "about_link": "About this tool: what it learned from and how well it works",
}


def base_sentence(b: dict, platform: str) -> list[str]:
    lo, hi = b["rate_80"]
    clo, chi = b["likes_comments_80"]
    return [f"Typical engagement for {PLATFORM[platform]} from an account with {b['followers']:,.0f} followers: "
            f"{rate_text(b['rate_typical'])} of followers like or comment.",
            f"Eight in ten such videos fall between {rate_text(lo)} and {rate_text(hi)} - about "
            f"{count_text(clo)} to {count_text(chi)} likes and comments together.",
            "The range is wide because a large part of the difference between videos belongs to the account, "
            "which the tool cannot know for a new one."]


def ig_sentence(s: dict) -> str:
    return (f"This video scores higher than {s['higher_than_pct_of_120']:.0f}% of the 120 Instagram Zero Sugar "
            "videos, scored by the same model.")


ABOUT_LIMITS = [
    "Which videos count as Zero Sugar was decided partly by eye, and a repeat check of that decision agreed only "
    "weakly - so the 192 may include a few videos that are not Zero Sugar, or miss some that are.",
    "One brand and 22 accounts. On YouTube, 58 of the 72 videos come from one global channel.",
    "Likes and comments were read at least 7 days after posting; how old a video was is not part of these "
    "numbers.",
]

MISSING_NAMES ={**{k: v[0].lower() for k, v in FEATURES.items()}, "creator_collab_f": "collaboration with a creator"}


def missing_lines(m: dict, platform: str) -> list[str]:
    out = []
    if not m["caption_given"]:
        out.append("No caption was given, so the caption measures are missing (not counted as zero).")
    if platform == "youtube":
        gaps = [c for c in m["inputs_missing"] if c != "creator_collab_f"]
        if gaps:
            out.append("Measures that could not be taken: " + ", ".join(MISSING_NAMES.get(c, c) for c in gaps) + ".")
        out += {"no_speech": ["No speech was found in the video."], "silent_audio": ["The sound track is silent."],
                "no_intelligible_speech": ["No speech could be made out."]}.get(m["speech"], [])
        return out or ["Nothing was missing."]
    if not m["collaboration_given"]:
        out.append("Whether the post is a collaboration with a creator was not given.")
    if m["speech"] != "ok":
        out.append({"no_speech": "No speech was found in the video.",
                    "silent_audio": "The sound track is silent.",
                    "no_intelligible_speech": "No speech could be made out."}.get(m["speech"], "No usable speech."))
    if m["inputs_missing"]:
        names = ", ".join(MISSING_NAMES.get(c, c) for c in m["inputs_missing"])
        out.append(f"Missing inputs to the Instagram score: {names}. Each was filled with the typical value of the "
                   "120 training videos, exactly as during training.")
    return out or ["Nothing was missing."]

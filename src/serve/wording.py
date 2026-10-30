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
    return f"{n:,.0f}"


TEXT = {
    "title": "Coca-Cola Zero Sugar short-video check",
    "intro": ("Upload a short video or paste a link. In about 3 minutes you see a typical result for the account's "
              "size, how the video compares with 192 Zero Sugar videos, and ideas worth testing."),
    "base_head": "What a typical video gets",
    "base_lead": ("For an account the models have not seen, they could not predict better than this. It is the "
                  "typical result for a Zero Sugar video from an account of this size, not a forecast for this video."),
    "base_no_followers": "Enter the account's follower count to see what a typical video gets.",
    "ig_head": "Instagram content score (exploratory)",
    "ig_head_short": "Instagram content score",
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
    # D-065: the redesigned pages and the examples box
    "tagline": "Measures a short video the way the study measured 192 Coca-Cola Zero Sugar videos.",
    "footer": ("Runs on this computer only. Nothing is sent anywhere, except the request a link needs to reach "
               "Instagram or YouTube."),
    # D-066: the online demo (saved results of the six examples only) and the lighter pages
    "demo_lead": ("Pick a video to see what the tool says: a typical result for the account's size, how the video "
                  "compares with 192 Zero Sugar videos, and ideas worth testing."),
    "demo_note": ("This online demo shows saved results only and cannot measure a new video. Measuring needs the "
                  "researcher's computer and takes about 3 minutes a video."),
    "footer_demo": ("Online demo of saved results for six example videos. Measuring a new video runs on the "
                    "researcher's computer."),
    "examples_lead_demo": "Six real videos from the study's collection. None was used to train the tool.",
    "own_head": "Use your own video",
    "hero_tag": "Short-video check",
    "examples_head": "Try an example",
    "examples_lead": ("Six real videos from the study's collection. None was used to train the tool. Click one to "
                      "fill the form with its details."),
    "examples_ready": "ready",
    "examples_not_ready": "~3 min",
    "example_chosen": "Example from the study's collection",
    "example_clear": "Use my own video instead",
    "step_video": "The video",
    "step_account": "The account and the caption",
    "step_questions": "Two questions",
    "step_hand": "Optional: describe the video yourself",
    "drop_title": "Drop a video file here, or click to choose one",
    "drop_hint": "mp4, mov, m4v, webm or mkv - up to 3 minutes",
    "or_link": "or paste an Instagram Reel or YouTube Short link",
    "submit": "Measure the video",
    "submit_note": "Measuring takes about 3 minutes; a video measured before with the same details opens at once.",
    "progress_head": "Measuring the video",
    "progress_lead": "This takes about 3 minutes. The page updates by itself.",
    "kpi_rate_label": "of followers like or comment, typically",
    "kpi_range_label": "Eight in ten such videos fall between",
    "kpi_ig_label": "higher than this share of the 120 Instagram Zero Sugar videos, scored by the same model",
    "kpi_no_ig": "No content score for YouTube",
    # D-067: plain one-liners on the summary cards
    "kpi_range_plain": "Eight in ten videos from accounts this size land in this range.",
    "kpi_ig_plain": "of the 120 Instagram videos score lower on content. A rough guide, not a chance of success.",
    "no_ig_plain": "The study had too few YouTube channels to test a content score, so none is shown.",
    "bar_note": "The bar shows where this video sits among the 192: left = lower than all of them, right = higher.",
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


# ------------------------------------------------------------------------------------------ 12.6 explanations
DRIVER_TEXT = {
    "hashtag_count": {"name": "Hashtags", "more": "more hashtags", "unit": lambda v: f"{v:.0f}",
                      "caution": "In this study hashtags went with engagement only between accounts - accounts that use "
                                 "more hashtags - not as something shown to help a single video."},
    "talk_dur_frac": {"name": "Talking", "more": "more talking", "unit": lambda v: f"{v:.0%} of the video",
                      "caution": "Found on Instagram only. Among the 72 YouTube Shorts the pattern ran the other way "
                                 "(described, not tested)."},
    "face_present_frac": {"name": "Frames showing a face", "more": "more frames showing a face",
                          "unit": lambda v: f"{v:.0%} of frames",
                          "caution": "Found on Instagram only. Among the 72 YouTube Shorts the pattern ran the other "
                                     "way (described, not tested)."},
}
DRIVER_HEAD = "What the Instagram score leaned on"
DRIVER_LEAD = ("Only the three measures the model used consistently were explained (hashtags, talking, faces). These "
               "describe the model's score, not what will raise engagement.")
NO_DRIVERS_YOUTUBE = ("No explanation is given for YouTube videos: with 72 videos from 5 channels (58 from one), no "
                      "YouTube model could be tested.")


def where_text(p: float) -> str:
    return "above all" if p >= 100 else (f"higher than {p:.0f}%" if p > 0 else "below all")


def driver_lines(e: dict) -> list[dict]:
    out = []
    for d in e["drivers"]:
        t = DRIVER_TEXT[d["feature"]]
        if d["status"] == "not known":
            why = "no caption was given" if d["feature"] == "hashtag_count" else "it could not be measured"
            out.append({"name": t["name"], "line": f"Not known for this video ({why}), so not explained.",
                        "caution": ""})
            continue
        if d["status"] != "explained":
            out.append({"name": t["name"], "line": "Not explained: " + d["status"].split(": ", 1)[-1] + ".",
                        "caution": ""})
            continue
        v, avg = d["value"], d["average_of_120"]
        more_or_less = "more" if v > avg else ("less" if v < avg else "the same")
        line = (f"This video: {t['unit'](v)}; average of the 120: {t['unit'](avg)}. The model scores videos with "
                f"{t['more']} higher. ")
        if more_or_less == "the same":
            line += "This video sits at the average, so this measure does not move its position."
        elif round(d["position_at_average"]) == round(d["position_with"]):     # D-065: no "62%, not 62%"
            line += (f"With the average instead, its position would barely change "
                     f"({where_text(d['position_with'])} of the 120).")
        else:
            line += (f"With the average instead, it would score {where_text(d['position_at_average'])} of the 120, "
                     f"not {where_text(d['position_with'])}.")
        out.append({"name": t["name"], "line": line, "caution": t["caution"]})
    return out


def others_line(e: dict) -> str:
    three = sum(abs(d.get("shap_log_odds", 0.0)) for d in e["drivers"])
    rest = abs(e["other_18_log_odds"])
    comp = "more" if rest > three else "less"
    return (f"The model also uses 18 other measures, none consistent enough to explain. Together they moved this "
            f"video's score {comp} than these three did.")


# ------------------------------------------------------------------------------------------ D-067 plain summary
PATTERN_TAG = "a pattern, not proof"
NO_TIPS = "This video already follows the patterns the study saw."
TIPS_LEAD = ("The study found nothing proven to raise engagement. These are patterns it saw that this video does not "
             "already follow - worth trying, not promises.")


def _pos(r: dict, key: str, among: str) -> float | None:
    d = (r.get("diagnostics") or {}).get(key) or {}
    if d.get("value") is None:
        return None
    p = d.get(among) or {}
    return {"below": 0.0, "above": 100.0}.get(p.get("beyond"), p.get("pct"))


def meaning(r: dict, platform: str) -> list[str]:
    """Two or three plain sentences from values already on the page (D-067)."""
    out = []
    if r.get("base_rate"):
        out.append("The big number is what a typical video from an account this size gets. It is not a forecast for "
                   "this video: most of the difference between videos comes from the account itself.")
    s = r.get("instagram_score")
    if s:
        out.append(f"On content alone, this Reel scores higher than {s['higher_than_pct_of_120']:.0f}% of the 120 "
                   "Instagram videos the tool learned from - a rough guide, not a chance of success.")
    words = []
    for key, more, fewer in (("hashtag_count", "more hashtags", "fewer hashtags"),
                             ("talk_dur_frac", "more talking", "less talking"),
                             ("face_present_frac", "more faces on screen", "fewer faces on screen")):
        pos = _pos(r, key, "among_192")
        if pos is not None and pos != 50:
            words.append(more if pos > 50 else fewer)
    if words:
        out.append("Compared with the 192 study videos, it has " + ", ".join(words[:-1]) +
                   (" and " if len(words) > 1 else "") + words[-1] + " than most.")
    return out


def worth_testing(r: dict, platform: str) -> list[dict]:
    """At most three "ideas worth testing", by the rules fixed in D-067 before any page showed them."""
    tips = []
    pos = _pos(r, "hashtag_count", "among_192")
    if pos is not None and pos < 50:
        tips.append({"head": "Try a few more hashtags",
                     "line": "This video uses fewer hashtags than most of the 192. In the study, accounts that used "
                             "more hashtags had higher engagement - seen between accounts, not shown to help a single "
                             "video."})
    cta = ((r.get("hand_codes") or {}).get("hc_cta") or {}).get("answer")
    if cta != 1.0:
        tips.append({"head": "Ask viewers to do something",
                     "line": "A clear call to action (\"comment below\", \"tag a friend\") went with videos ranking "
                             "about 11 points higher out of 100 - the study's steadiest pattern, though judging it "
                             "by eye was only moderately repeatable."})
    if platform == "instagram":
        for key, head, what in (("talk_dur_frac", "Try more talking", "more talking"),
                                ("face_present_frac", "Show more faces", "more faces on screen")):
            pos = _pos(r, key, "among_instagram")
            if pos is not None and pos < 50:
                tips.append({"head": head,
                             "line": f"This Reel has less of this than most of the 120 Instagram videos. The Instagram "
                                     f"score leaned towards {what}; seen on Instagram only - YouTube Shorts ran the "
                                     "other way."})
    return tips[:3]


# ------------------------------------------------------------------------------------------ 12.7 warnings
CANNOT = ["The best time to post, or which hashtags to use - neither was modelled.",
          "Paid promotion, and how Instagram's or YouTube's own systems spread a video.",
          "Reach: Instagram does not publish reliable view counts, so no Instagram reach is shown.",
          "Sales, or anything beyond likes and comments.",
          "A forecast for this particular video: the range is for a typical video from an account of this size."]


def certainty(b: dict) -> dict:
    lo, hi = b["rate_80"]
    ratio = hi / lo if lo > 0 else float("inf")
    level = "high" if ratio <= 3 else ("moderate" if ratio <= 10 else "low")
    return {"level": level, "text": f"The top of the range is about {ratio:,.0f} times the bottom - that is how "
                                    "much typical videos from new accounts differ, and the tool cannot narrow it."}


def youtube_range_note(b: dict) -> str:
    return (f"On YouTube this range is too narrow: on accounts the model had not seen, it held "
            f"{b['interval_coverage_on_held_out_accounts']:.0%} of videos, not the 80% it should.")


def top_notices(r: dict, zero_sugar: str | None, schema: dict) -> list[str]:
    out = []
    if zero_sugar in ("no", "unsure"):
        said = "does not show Coca-Cola Zero Sugar" if zero_sugar == "no" else "may not show Coca-Cola Zero Sugar"
        out.append(f"You said the video {said}. The tool learned only from Zero Sugar videos, so this result "
                   "describes a kind of video it has not seen. (The tool cannot check this itself.)")
    b = r.get("base_rate")
    lo_f, hi_f = schema["ranges"]["followers"]
    if b and b["followers_outside_training"]:
        out.append(f"The follower count ({b['followers']:,.0f}) is outside the accounts the tool learned from "
                   f"({lo_f:,.0f} to {hi_f / 1e6:.1f} million), so the typical range reaches beyond what the data covers.")
    v = r["video"]
    if v.get("shorter_than_training"):
        out.append(f"The video is shorter than any of the 192 ({schema['ranges']['duration_sec'][0]:.1f} seconds).")
    if v.get("shape_outside_training"):
        lo_a, hi_a = schema["ranges"]["aspect_ratio"]
        out.append(f"The video's shape (width to height {v['aspect_ratio']:.2f}) is unlike the 192 ({lo_a:.2f} to {hi_a:.2f}).")
    beyond = [FEATURES[k][0].lower() for k, d in r["diagnostics"].items()
              if (d.get("among_192") or {}).get("beyond") and k in FEATURES]
    if beyond:
        out.append("On " + ", ".join(beyond) + ", this video is outside the range of the 192.")
    s = r.get("instagram_score")
    if s and s.get("outside_the_120"):
        out.append(f"Its Instagram score is {s['outside_the_120']} every one of the 120 training videos.")
    if r.get("speech_unclear"):
        out.append("The speech in this video is unclear (the speech engine was unsure of the words or the language). "
                   "Its reading of unclear speech can change from one run to the next - in the study too - so the share "
                   "of talking and the keyword measures are less certain.")
    return out


def g4_text(gates: dict, plain: dict | None = None) -> str:
    """The parity check (G4) in plain words, from the model card (its plain note when one was recorded)."""
    if plain and plain.get("G4"):
        return plain["G4"]
    g4 = gates.get("G4", "")
    if g4.startswith("pending"):
        return "the check that the tool measures exactly as the study did is still pending"
    if g4.startswith("pass within tolerance"):
        return ("on 10 of the 192 videos, measured twice, the tool's measurements matched the study's to within "
                "a millionth (not every last digit)")
    if g4.startswith("pass"):
        return "on 10 of the 192 videos, measured twice, the tool's measurements matched the study's exactly"
    return "on 10 of the 192 videos the tool's measurements did not all match the study's - see the About page"


def checks_line(gates: dict, plain: dict | None = None) -> str:
    g4_text_ = g4_text(gates, plain)
    return ("Release checks: the video's content did not beat follower count (so a typical result is shown); the "
            "Instagram score cannot be read as a chance (shown as a position); the ranges were too narrow and were "
            "widened (YouTube's still is). Does the tool measure exactly as the study did? "
            f"{g4_text_[:1].upper()}{g4_text_[1:]}.")


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

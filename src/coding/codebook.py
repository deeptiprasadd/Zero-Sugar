"""Manual coding scheme - the single source for the coding page and the shared codebook.

Five concrete constructs coded by the researcher on a fixed random subset of the corpus
(D-023). Definitions are written to be decidable from the video and its caption alone, so
two careful viewers would reach the same answer.
"""
from __future__ import annotations

SAMPLE_SIZE = {"youtube": 30, "instagram": 30}
SEED = 20260915

# (field, question, help text, options as (value, label))
QUESTIONS: list[tuple[str, str, str, list[tuple[str, str]]]] = [
    (
        "has_celebrity",
        "Does a celebrity appear?",
        "A widely famous person - film, TV, music or sports star, or a well-known public figure - "
        "is seen on screen or clearly heard. Famous mainly for their own work, not for social media. "
        "Fans or crowds at a celebrity's event do not count unless the celebrity is shown. "
        "YES: a famous singer or footballer drinking a Coke; a film star in an ad. "
        "NO: ordinary people at a picnic; a crowd at a concert where the singer is never shown.",
        [("yes", "Yes"), ("no", "No"), ("unsure", "Unsure")],
    ),
    (
        "has_influencer",
        "Does a social-media creator appear?",
        "A person known mainly from Instagram, YouTube or TikTok (food, lifestyle, comedy, travel "
        "creators) appears - typically talking to camera in their own style. A celebrity who also "
        "posts online counts as celebrity, not creator. "
        "YES: a food vlogger reviewing a restaurant with a Coke; a comedy creator doing a skit. "
        "NO: actors in a studio ad; staff or delivery workers; a famous singer (that is celebrity).",
        [("yes", "Yes"), ("no", "No"), ("unsure", "Unsure")],
    ),
    (
        "has_cta",
        "Is there a call to action?",
        "The video, its on-screen text, the voice-over or the caption asks the viewer to do "
        "something: buy, try, pre-book, follow, comment, share, tag, enter a contest, visit a place, "
        "scan a code, collect items. A slogan alone (e.g. 'Real Magic') is not a call to action. "
        "YES: 'Comment below to win', 'Pre-book now', 'Collect all the cans', 'Visit our stall'. "
        "NO: 'Enjoy an ice-cold Coke', 'Real Magic', a hashtag on its own.",
        [("yes", "Yes"), ("no", "No")],
    ),
    (
        "humour_present",
        "Is the video meant to be funny?",
        "The video clearly aims to amuse: jokes, comic acting, playful exaggeration, memes, "
        "funny situations or reactions. Merely cheerful or upbeat does not count. "
        "YES: a comic skit, a prank, a funny fail, a meme-style edit. "
        "NO: a happy concert montage, friends smiling at a picnic, a stylish product shot.",
        [("yes", "Yes"), ("no", "No"), ("unsure", "Unsure")],
    ),
    (
        "zero_sugar_visible",
        "Is Coca-Cola Zero Sugar shown?",
        "Look at the product at any point. Zero Sugar: black can, bottle or label, or the words "
        "'Zero Sugar' / 'Coke Zero' on pack or screen. Choose 'Other Coca-Cola' if only red "
        "Original Taste, Diet/Light or another variant appears, and 'No product' if no Coca-Cola "
        "pack is visible at all. "
        "ZERO SUGAR: a black can or bottle anywhere in the video. "
        "OTHER COCA-COLA: only red cans/bottles, a silver Diet Coke can. "
        "NO PRODUCT: only the logo on a sign or truck, or no Coca-Cola pack at all.",
        [("zero_sugar", "Zero Sugar"), ("other_coca_cola", "Other Coca-Cola"),
         ("no_product", "No product"), ("unsure", "Unsure")],
    ),
]

FIELDS = [q[0] for q in QUESTIONS]


def codebook_markdown() -> str:
    """Plain codebook for the shared folder - method only."""
    lines = [
        "# Manual coding codebook",
        "",
        f"A fixed random subset of {sum(SAMPLE_SIZE.values())} videos "
        f"({SAMPLE_SIZE['youtube']} YouTube Shorts, {SAMPLE_SIZE['instagram']} Instagram Reels; "
        f"seed {SEED}) was coded by the researcher, one video at a time in random order, "
        "watching the full video with sound and reading its caption or title. The coder did not "
        "see any automated labels or corpus grouping while coding.",
        "",
        "Agreement between manual and automated labels is reported per construct with "
        "Krippendorff's alpha; constructs below 0.67 are not used. 'Unsure' is treated as missing.",
        "",
    ]
    for i, (field, question, help_text, options) in enumerate(QUESTIONS, start=1):
        lines += [f"## {i}. {question}  (`{field}`)", "", help_text, "",
                  "Options: " + " / ".join(label for _, label in options), ""]
    return "\n".join(lines)

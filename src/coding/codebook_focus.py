"""Hand-coding of the 192 focus videos (proposal gaps P1-P9, D-049) - the single source for the coding
page (`src/coding/focus_app.py`) and the written codebook (docs/13).

Fixed before the first answer. Four questions repeat the 15 September codebook word for word
(`src/coding/codebook.py`) so the 40 videos coded both times give a repeat check, and two reuse the
wording of the unchecked automated labels (`src/features/annotate.py`, D-038) so those labels can be
compared with a human answer. Every question is decidable from the video (with sound) and its caption.
"""
from __future__ import annotations

from src.coding.codebook import QUESTIONS as _SEP15

SEED = 20261005                     # viewing order of the 192 videos
_sep15 = {q[0]: q for q in _SEP15}


def _same_as_sep15(field: str, section: str, gap: str) -> tuple:
    f, q, h, o = _sep15[field]
    return (f, q, h, o, section, gap)


# (field, question, help text, options as (value, label), section, proposal gap)
QUESTIONS: list[tuple[str, str, str, list[tuple[str, str]], str, str]] = [
    (
        "product_visibility",
        "How visible is a Coca-Cola can or bottle?",
        "Any Coca-Cola can or bottle, any variant (Zero Sugar, Original Taste, Diet/Light, flavours). "
        "Cups, glasses, fridges, signs and trucks do not count here - they belong to the next question. "
        "NONE: no can or bottle at any point. "
        "BRIEF: a can or bottle appears only in passing - a glimpse, small, in the background or partly "
        "out of shot. "
        "PROMINENT: a can or bottle is clearly a main subject at least once - large in frame and in focus, "
        "e.g. held up to camera, poured, a close-up, or an end pack shot.",
        [("none", "None"), ("brief", "Brief"), ("prominent", "Prominent"), ("unsure", "Unsure")],
        "On screen", "P1",
    ),
    (
        "logo_visibility",
        "How visible is the Coca-Cola logo or name?",
        "The Coca-Cola script logo, the red disc, or the words 'Coca-Cola' / 'Coke' anywhere - on packs, "
        "cups, signs, fridges, clothes, on-screen graphics or an end card. "
        "NONE: never visible. "
        "BRIEF: only in passing - small, in the background, or for a moment. "
        "PROMINENT: clearly a main subject at least once - large and in focus, e.g. a full-screen logo or "
        "end card, a close-up of the logo on a can, a big sign the camera dwells on.",
        [("none", "None"), ("brief", "Brief"), ("prominent", "Prominent"), ("unsure", "Unsure")],
        "On screen", "P2",
    ),
    (
        "people_present",
        "Does any person appear?",
        "A real person is seen on screen at any point - a face or a body. Hands alone (holding a can) do "
        "not count; cartoons and animated characters do not count. "
        "YES: friends at a table, a crowd, a presenter, a footballer, a creator talking to camera. "
        "NO: only pack shots, food, graphics or animation; only hands.",
        [("yes", "Yes"), ("no", "No"), ("unsure", "Unsure")],
        "People", "P4",
    ),
    _same_as_sep15("has_celebrity", "People", "P4"),
    _same_as_sep15("has_influencer", "People", "P4"),
    _same_as_sep15("humour_present", "Tone", "P5"),
    (
        "excitement_present",
        "Is the video meant to be exciting?",
        "The video clearly aims to thrill or pump up the viewer: sport action, goals and celebrations, "
        "cheering crowds, stunts, dramatic build-ups, a countdown or reveal, high-energy music with fast "
        "cutting. Merely cheerful, pleasant or upbeat does not count. "
        "YES: a goal-celebration montage, a concert crowd jumping, a fast-cut reveal of a new can. "
        "NO: friends chatting over lunch, a calm recipe video, a slow product shot with soft music.",
        [("yes", "Yes"), ("no", "No"), ("unsure", "Unsure")],
        "Tone", "P5",
    ),
    (
        "music_type",
        "What kind of music plays, mainly?",
        "Listen with the sound on and pick the style of the main music; if several pieces play, pick the "
        "one heard longest. NO MUSIC: only speech, natural sound or silence. "
        "POP: chart-style songs, including K-pop, Latin pop and film songs (e.g. Bollywood). "
        "HIP-HOP / RAP. ELECTRONIC / DANCE: EDM, house, club beats, mostly without singing. ROCK. "
        "TRADITIONAL / FOLK: a local traditional style from any country. "
        "CINEMATIC / ORCHESTRAL: film-score style, strings, epic build-ups. "
        "OTHER / CAN'T TELL: anything else, a short jingle only, or too faint to judge.",
        [("no_music", "No music"), ("pop", "Pop"), ("hiphop_rap", "Hip-hop / rap"),
         ("electronic_dance", "Electronic / dance"), ("rock", "Rock"), ("traditional_folk", "Traditional / folk"),
         ("cinematic_orchestral", "Cinematic / orchestral"), ("other_cant_tell", "Other / can't tell")],
        "Sound", "P6",
    ),
    (
        "voice_tone",
        "How does the speaking voice sound?",
        "Listen to people talking or a voice-over - not singing. If the tone changes, pick what most of "
        "the talking sounds like. "
        "EXCITED: energetic, loud, fast or enthusiastic - a sports commentator, a hyped presenter, "
        "shouting friends. "
        "CALM: relaxed, conversational or soft - a chat, a gentle voice-over. "
        "NO VOICE: nobody speaks - no voice at all, or the only voice is singing.",
        [("excited", "Excited"), ("calm", "Calm"), ("no_voice", "No voice"), ("unsure", "Unsure")],
        "Sound", "P7",
    ),
    _same_as_sep15("has_cta", "Message and campaign", "P3"),
    (
        "campaign_type",
        "What kind of campaign is this, mainly?",
        "If two fit, pick the one the video is mainly about. "
        "NEW PRODUCT: a new flavour, pack or limited edition is announced or shown as new. "
        "EVENT: a sport, music or entertainment event - a World Cup, a match, a concert, a festival, a "
        "film tie-in. "
        "SEASONAL: a festival or season - Ramadan, Christmas, Diwali, Lunar New Year, summer, holidays. "
        "PROMOTION: an offer, price, discount, contest, giveaway or collectable. "
        "FOOD: Coca-Cola with a meal - food pairing, a restaurant or delivery partner. "
        "GENERAL BRAND: none of these - the brand's mood or everyday moments.",
        [("new_product", "New product"), ("event", "Event"), ("seasonal", "Seasonal"),
         ("promotion", "Promotion"), ("food", "Food"), ("general_brand", "General brand"),
         ("unsure", "Unsure")],
        "Message and campaign", "P8",
    ),
    (
        "sponsored_disclosed",
        "Is the post disclosed as paid or sponsored?",
        "Judge from the caption and the video only. "
        "YES: #ad, #sponsored, #publi, #publicidad, 'paid partnership', 'sponsored by', 'in partnership "
        "with' (any language), written in the caption or shown on screen. "
        "NO: no such disclosure. A brand posting about its own product is 'No' unless it says so. "
        "The platform's own 'Paid partnership' tag is not on this page (the original post would show "
        "likes), so it cannot be used.",
        [("yes", "Yes"), ("no", "No")],
        "Message and campaign", "P8",
    ),
    (
        "product_vs_lifestyle",
        "Is the video mainly about the drink itself, or about a moment the drink is part of?",
        "Decide by what fills most of the video. "
        "PRODUCT: the can or bottle, its taste, ingredients, pack design, price or offer is the main "
        "subject - pack shots, pouring, taste close-ups, a new flavour announced. "
        "LIFESTYLE: people, music, sport, food, friends or an event are the main subject and the "
        "drink is one part of the scene.",
        [("product", "Product"), ("lifestyle", "Lifestyle"), ("unsure", "Unsure")],
        "Message and campaign", "P9",
    ),
    (
        "ugc_vs_brand",
        "Does the video look made by an ordinary person or creator, or produced by or for the brand?",
        "This is about the look of the video, not who posted it. "
        "UGC: filmed on a phone, handheld, a person filming themselves or friends, informal edit, "
        "the creator's own voice. A creator video paid for by the brand but made in the creator's "
        "own style counts as UGC. "
        "BRAND: studio lighting, professional camera work, designed graphics and logos, polished "
        "edit, advertising voice-over.",
        [("ugc", "UGC"), ("brand", "Brand"), ("unsure", "Unsure")],
        "Message and campaign", "P9",
    ),
]

FIELDS = [q[0] for q in QUESTIONS]
REPEATED_FROM_SEP15 = ["has_celebrity", "has_influencer", "humour_present", "has_cta"]


def people_type(row: dict) -> str:
    """P4's four groups, derived (D-049): celebrity > creator > ordinary people > none; unsure if undecidable.
    A question left unanswered counts like "unsure" (D-049 note, 9 Oct)."""
    if row.get("has_celebrity") == "yes":
        return "celebrity"
    if row.get("has_celebrity") != "no":
        return "unsure"
    if row.get("has_influencer") == "yes":
        return "influencer"
    if row.get("has_influencer") != "no":
        return "unsure"
    if row.get("people_present") == "yes":
        return "ordinary_people"
    if row.get("people_present") == "no":
        return "none"
    return "unsure"


def codebook_markdown() -> str:
    """The codebook as fixed before coding - method only, no internal notes."""
    lines = [
        "## The questions, exactly as shown on the coding page",
        "",
        "Generated from `src/coding/codebook_focus.py`. Questions marked *as 15 Sep* repeat the first "
        "codebook word for word.",
        "",
    ]
    section = None
    for i, (field, question, help_text, options, sec, gap) in enumerate(QUESTIONS, start=1):
        if sec != section:
            lines += [f"### {sec}", ""]
            section = sec
        tag = " - *as 15 Sep*" if field in REPEATED_FROM_SEP15 else ""
        lines += [f"**{i}. {question}** (`{field}`, {gap}{tag})", "", help_text, "",
                  "Options: " + " · ".join(label for _, label in options), ""]
    return "\n".join(lines)

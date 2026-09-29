"""Task 5.11 - cut the candidate features to the 18-20 budget (D-030, docs/05 section 4).

**What this can and cannot do today.** docs/05 section 4 fixes five rules, in order:

    1  drop near-constant features (>95% one value)            outcome-free  -> done here
    2  drop >30% missing that cannot be sensibly flagged        outcome-free  -> done here
    3  drop annotation constructs with alpha < 0.67             reads 4.2's result (D-038)
    4  within a block, drop one of any pair with |r| > 0.85     outcome-free  -> done here
    5  if still over budget, drop by lowest univariate          **needs the outcome** - training
       association, on training folds only                     folds only, in Phase 9

So this step applies **rules 1-4** and stops. Rule 3 reads 4.2's alpha table (researcher vs model,
never the outcome) and applies the placement fixed in D-038 before alpha was known. Rule 5 must
never run outside cross-validation folds - running it now would choose features by
looking at engagement, which is exactly what the pre-registration forbids (docs/08 section 7.9).

**Correlations are computed on the focus set** - the 183 usable Zero Sugar videos the analysis
uses (D-030) - because that is the sample the features will be modelled on. The 300-video figure
is printed beside it; where the two disagree the focus set decides, and the difference is reported.

**A pre-specified priority order** is fixed here, before any outcome is seen, so that if the
candidate set is still over budget after rules 1-4 the final cut is not made by looking at
results. Each keeper is tied to the hypothesis or control that needs it.

**Structural missingness is handled by routing, not imputation.** A video with no speech has no
sentiment, no words per minute and no voice pitch - that is not a missing measurement to fill in,
it is a video with nobody talking. Features undefined without speech go to a **speech-only
sub-analysis** (the 117 focus videos with speech); features where zero is the true measurement
(`talk_dur_frac`, `music_frac`, `speech_dur_frac`) stay in the main model. Platform-only features
(`title_char_len`, `creator_collab`) enter only that platform's models, as section 4.0 rule 3 says.

Writes the record docs/05 section 6 asks for: every drop with its reason.

Usage:
    python -m src.features.prune
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

FEATURES = config.PROCESSED / "features.parquet"
RECORD = config.REPORTS / "feature_pruning_record.md"
NEAR_CONSTANT = 0.95
MAX_MISSING = 0.30
CORR_LIMIT = 0.85
BUDGET = 20

BLOCKS = {
    "A_video": ["duration_sec", "fps", "aspect_ratio", "cuts_per_sec", "scene_count",
                "mean_shot_len_sec", "longest_shot_frac", "is_single_shot", "hidden_montage",
                "motion_px_per_sec", "brightness", "contrast", "saturation", "colourfulness",
                "red_ratio", "edge_density", "brightness_sd", "saturation_sd", "red_ratio_sd",
                "red_frame_frac", "face_present_frac", "mean_face_count", "max_face_count",
                "mean_face_area", "ocr_text_frame_frac", "ocr_region_count",
                "ocr_mean_text_area", "ocr_max_text_area"],
    "B_audio": ["audio_silent", "loudness_db_mean", "loudness_range_db", "silence_frac",
                "spectral_centroid_hz", "tempo_bpm", "pitch_median_hz", "pitch_std_semitones",
                "voiced_frac", "music_frac", "music_present", "speech_frac_ast",
                "speech_sung_frac", "talk_dur_frac", "pitch_median_talk_hz",
                "pitch_std_talk_semitones", "speech_dur_frac", "word_count", "words_per_min"],
    "C_text": ["caption_char_len", "caption_word_count", "hashtag_count", "mention_count",
               "emoji_count", "has_question_mark", "title_char_len", "title_char_len_z_lang",
               "sentiment_speech", "sentiment_caption", "emotion_label", "emotion_score",
               "kw_offer", "kw_new", "kw_taste", "kw_zero_sugar", "kw_event", "kw_together",
               "kw_promotional", "kw_experience",
               "lang_caption", "lang_audio", "is_code_switched", "lang_match",
               "sentiment_speech_source"],
    "D_creator": ["creator_collab", "auto_has_celebrity", "auto_has_influencer",
                  "auto_humour_present", "auto_product_vs_lifestyle", "auto_ugc_vs_brand"],
}
BLOCKS["C_text"] += ["auto_has_cta", "auto_promotional_language"]

# 5.12 automated labels and 4.2's verdict on them (D-038).
RELIABILITY = config.INTERIM / "annotation_reliability.csv"
CHECKED_AUTO = ["auto_has_cta", "auto_has_celebrity", "auto_has_influencer", "auto_humour_present"]
UNCHECKED_AUTO = ["auto_product_vs_lifestyle", "auto_ugc_vs_brand", "auto_promotional_language"]
TO_RESERVE_HEAD = ["auto_humour_present"]   # passes -> head of the reserve, not the pooled set
# Exposure controls are in every model by design and do not count against the budget
# (docs/05 section 4.0 rule 2).
EXPOSURE = ["followers", "video_age_days", "account_size_tier", "posting_hour_utc",
            "is_weekend_utc", "platform"]

# Features that cannot exist without speech: their absence is a property of the video, not a gap
# to impute. They go to the speech-only sub-analysis.
SPEECH_ONLY = ["sentiment_speech", "emotion_label", "emotion_score", "words_per_min",
               "word_count", "pitch_median_hz", "pitch_std_semitones", "pitch_median_talk_hz",
               "pitch_std_talk_semitones", "voiced_frac", "speech_sung_frac"]
PLATFORM_ONLY = {"title_char_len": "youtube", "title_char_len_z_lang": "youtube",
                 "creator_collab": "instagram"}

# Rule 0: decisions already taken elsewhere in the project. Applied first so they are not
# re-argued here, and each cites where it was decided. None of these looks at the outcome.
DOCUMENTED_DROPS: dict[str, str] = {
    "aspect_ratio": "rule 0: D-024 - near-constant by construction (279 of 300 at 0.562); "
                    "every video is vertical (D-001)",
    "fps": "rule 0: D-024 - a file property, not a creative choice; steps that compare frames "
           "sample at a fixed rate rather than trusting native fps",
    "scene_count": "rule 0: docs/05 section 4 / D-026 - collinear with duration (r = 0.76); "
                   "`cuts_per_sec` is the rate version and is kept",
    "is_single_shot": "rule 0: the extreme of `cuts_per_sec` (23 videos), already carried by it",
    "brightness": "rule 0: docs/05 Block A says pick 1-2 of brightness/contrast/saturation; "
                  "`colourfulness` and `red_ratio` are the two kept",
    "contrast": "rule 0: docs/05 Block A - pick 1-2; not kept",
    "saturation": "rule 0: docs/05 Block A - pick 1-2; `colourfulness` subsumes it "
                  "(Spearman 0.69) and is the documented measure",
    "brightness_sd": "rule 0: secondary spread version of a kept mean; means come first",
    "saturation_sd": "rule 0: secondary spread version of a kept mean",
    "red_ratio_sd": "rule 0: secondary spread version of a kept mean",
    "red_frame_frac": "rule 0: D-034 - near-constant (median 1.000 on both platforms); the "
                      "continuous `red_ratio` is kept instead",
    "ocr_text_frame_frac": "rule 0: D-034 - near-constant (123 of 300 videos exactly 1.000, "
                           "because logos and legal text appear in nearly every frame)",
    "ocr_max_text_area": "rule 0: extreme version of `ocr_mean_text_area`, which is kept",
    "max_face_count": "rule 0: extreme version of face presence; `mean_face_area` carries "
                      "close-up vs crowd more interpretably",
    "music_present": "rule 0: the boolean of `music_frac`, which is kept",
    "silence_frac": "rule 0: not in docs/05 Block B's list; loudness and talking share cover it",
    "has_question_mark": "rule 0: docs/04 section 5 rates it doubtful; 26 Shorts and 33 Reels "
                         "carry one, and no hypothesis rests on it",
    "kw_offer": "merged: half of `kw_promotional` (D-036) - kept, not discarded",
    "kw_new": "merged: half of `kw_promotional` (D-036) - kept, not discarded",
    "kw_taste": "merged: half of `kw_experience` (D-036) - kept, not discarded",
    "kw_together": "merged: half of `kw_experience` (D-036) - kept, not discarded",
}
# Language is a control, not a content feature (docs/05 Block E, docs/04 section 6).
AS_CONTROL = {"lang_caption": "language control (docs/05 Block E), not a content feature"}

# Pre-specified priority, fixed before any outcome was seen. Reason = the hypothesis or control
# that needs the feature. Highest priority first within each block.
PRIORITY: list[tuple[str, str]] = [
    ("duration_sec", "H1 - duration within short form"),
    ("cuts_per_sec", "pace; the montage decision of D-026 lives here"),
    ("motion_px_per_sec", "movement, measured in 5.3"),
    ("face_present_frac", "H4 - human presence, the validated half of it"),
    ("mean_face_area", "close-up vs crowd, which presence alone cannot separate"),
    ("edge_density", "visual busyness"),
    ("colourfulness", "colour, the least redundant of the colour measures"),
    ("red_ratio", "brand-meaningful colour (docs/05 Block A)"),
    ("ocr_region_count", "amount of on-screen text (D-034)"),
    ("ocr_mean_text_area", "how much of the frame that text covers"),
    ("music_frac", "H3/Block B - music presence, zero is a true measurement"),
    ("talk_dur_frac", "talking share, net of singing (D-028)"),
    ("loudness_db_mean", "loudness"),
    ("loudness_range_db", "dynamics"),
    ("sentiment_caption", "H3 - emotional tone of the text every video has"),
    # D-038, fixed before alpha was known: hypothesis instruments go here if they pass rule 3,
    # each one pushing the lowest of the 20 into the reserve.
    ("auto_has_cta", "H5 - call to action (automated label, passed alpha)"),
    ("auto_has_celebrity", "H4 - celebrity presence (automated label, passed alpha)"),
    ("auto_has_influencer", "H4 - creator presence (automated label, passed alpha)"),
    ("caption_char_len", "Block C - caption length, normalised within language later"),
    ("hashtag_count", "Block C - invariant across languages"),
    ("emoji_count", "Block C - invariant, and predictive in this literature"),
    # H6 asks about text characteristics and the proposal asks for keywords, so Block C keeps
    # three slots. The six flags become three features (D-036) rather than losing all six to
    # the budget, and they rank above Block B's own doubtful measures.
    ("kw_event", "H6 / Block C keywords - the largest group (104 videos, D-035)"),
    ("kw_promotional", "H6 / Block C - offer or new, merged (D-036)"),
    ("kw_experience", "H6 / Block C - taste or togetherness, merged (D-036)"),
    ("spectral_centroid_hz", "brightness of the sound - docs/05 Block B marks it doubtful, so it "
                             "ranks below Block C's keywords"),
    ("tempo_bpm", "tempo - Block B marks it doubtful, and D-028 found it unrelated to whether "
                  "music is present (Spearman -0.09)"),
    ("kw_zero_sugar", "Block C keywords - names the product in text"),
    ("is_code_switched", "D-003 - multilingual corpus property"),
    ("mention_count", "Block C - invariant, but 81% of Shorts and 67% of Reels have none, so it "
                      "ranks last of the text counts"),
    ("longest_shot_frac", "a second view of pace - how much of the video sits in one shot; kept "
                          "below `cuts_per_sec`, which it does not duplicate (|r| <= 0.85)"),
    ("creator_collab", "D-032 - replaces the dropped is_sponsored (Instagram only)"),
    ("title_char_len_z_lang", "5.14 - title length, within language (YouTube only)"),
    ("auto_humour_present", "Block D - humour (automated label, passed alpha); D-038 puts it at "
                            "the head of the reserve, since no hypothesis rests on it"),
]


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(FEATURES)
    focus = df[(df["in_focus"].astype(bool)) & (df["dv_status"] == "ok")]
    return df, focus


def near_constant(df: pd.DataFrame, cols: list[str]) -> dict[str, float]:
    out = {}
    for c in cols:
        s = df[c].dropna()
        if len(s):
            top = float(s.value_counts(normalize=True).iloc[0])
            if top > NEAR_CONSTANT:
                out[c] = top
    return out


def high_missing(df: pd.DataFrame, cols: list[str]) -> dict[str, float]:
    m = df[cols].isna().mean()
    return {c: float(v) for c, v in m.items() if v > MAX_MISSING}


def correlated_pairs(df: pd.DataFrame, cols: list[str]) -> list[tuple[str, str, float]]:
    num = df[cols].select_dtypes("number")
    if num.shape[1] < 2:
        return []
    c = num.corr(method="spearman", min_periods=30).abs()
    pairs = []
    for i, a in enumerate(c.columns):
        for b in c.columns[i + 1:]:
            v = c.loc[a, b]
            if pd.notna(v) and v > CORR_LIMIT:
                pairs.append((a, b, float(v)))
    return sorted(pairs, key=lambda x: -x[2])


def main() -> None:
    ap = argparse.ArgumentParser(description="5.11 - prune to the 18-20 budget (rules 1, 2, 4).")
    ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    all_df, focus = load()
    cols = [c for b in BLOCKS.values() for c in b]
    cols = [c for c in cols if c in all_df.columns]
    print(f"{len(cols)} candidate features; focus set {len(focus)} videos, all rows {len(all_df)}")

    dropped: dict[str, str] = {}

    # ---- rule 0: already decided elsewhere, cited
    for c, why in DOCUMENTED_DROPS.items():
        if c in cols:
            dropped[c] = why
    for c, why in AS_CONTROL.items():
        if c in cols:
            dropped[c] = f"routed: {why}"

    # ---- rule 3: automated labels, by 4.2's alpha (researcher vs model - never the outcome)
    rel = pd.read_csv(RELIABILITY) if RELIABILITY.exists() else None
    for c in UNCHECKED_AUTO:
        if c in cols:
            dropped[c] = ("rule 3: no manual check exists, so it can only be an unvalidated "
                          "automated label - kept as a column, never enters a model (D-023, D-038)")
    for c in CHECKED_AUTO:
        if c not in cols:
            continue
        if rel is None:
            dropped[c] = "rule 3 pending: 4.2 has not run"
            continue
        r = rel.set_index("construct").loc[c.removeprefix("auto_")]
        if not bool(r["passed"]):
            why = (f"alpha {r['alpha']:.3f} (95% CI {r['ci_lo']:.2f} to {r['ci_hi']:.2f}) on "
                   f"{int(r['n_pairs'])} held-out videos" if pd.notna(r["alpha"])
                   else "alpha not computable (only one answer occurred)")
            extra = (f"; model unsure on {r['model_unsure_share']:.0%}"
                     if r["model_unsure_share"] > 0.20 else "")
            dropped[c] = f"rule 3: {why}{extra} - below 0.67, dropped (4.2)"

    # ---- rule 1
    for c, v in near_constant(focus, cols).items():
        why = f"rule 1: near-constant - {v:.1%} of the focus set share one value"
        # an automated label already failed on alpha: keep that reason, add this one
        dropped[c] = f"{dropped[c]}; also {why}" if dropped.get(c, "").startswith("rule 3") else why

    # ---- rule 2, with the "sensibly flagged" exception spelled out
    for c, v in high_missing(focus, [c for c in cols if c not in dropped]).items():
        if c in SPEECH_ONLY:
            dropped[c] = (f"rule 2 exception: {v:.0%} missing **because the video has no speech** - "
                          f"not imputed, routed to the speech-only sub-analysis")
        elif c in PLATFORM_ONLY:
            dropped[c] = (f"rule 2 exception: {v:.0%} missing **by platform** - kept for "
                          f"{PLATFORM_ONLY[c]}-only models (section 4.0 rule 3)")
        else:
            dropped[c] = f"rule 2: {v:.0%} missing and no sensible flag"

    # ---- rule 4, within block, on the focus set
    corr_notes = []
    for block, members in BLOCKS.items():
        live = [c for c in members if c in all_df.columns and c not in dropped]
        for a, b, v in correlated_pairs(focus, live):
            if a in dropped or b in dropped:
                continue
            rank = {name: i for i, (name, _) in enumerate(PRIORITY)}
            loser = b if rank.get(a, 999) <= rank.get(b, 999) else a
            keeper = a if loser == b else b
            dropped[loser] = (f"rule 4: |Spearman| {v:.3f} with `{keeper}` inside {block} - "
                              f"kept the more interpretable of the pair")
            corr_notes.append((block, keeper, loser, v))

    survivors = [c for c in cols if c not in dropped]
    main_model = [c for c in survivors if c not in SPEECH_ONLY and c not in PLATFORM_ONLY]
    print(f"\nafter rules 0-4: {len(survivors)} features survive "
          f"({len(main_model)} of them usable in the pooled main model)")

    # ---- what the budget says. The cut is the top of the pre-specified order, so nothing is
    # chosen after a result is seen; rule 5 may only drop further inside folds, never add.
    ranked = [c for c, _ in PRIORITY if c in main_model]
    unranked = [c for c in main_model if c not in ranked]
    heads = [c for c in TO_RESERVE_HEAD if c in ranked]
    ranked = [c for c in ranked if c not in heads]
    final = ranked[:BUDGET]
    reserve = heads + ranked[BUDGET:]
    over = max(0, len(main_model) - BUDGET)

    lines = ["# 5.11 feature pruning record (D-030 budget 18-20; docs/05 section 4)", "",
             f"Candidates {len(cols)} -> **{len(survivors)} survive rules 0-4**, of which "
             f"**{len(main_model)}** can enter the pooled model. Correlations and constancy were "
             f"measured on the **focus set ({len(focus)} usable Zero Sugar videos)**, the sample "
             "the models will use. **No engagement value was read** - rule 3 reads only the "
             "researcher-vs-model alpha, and rule 5 is not applied here (see below).", "",
             "## Dropped, with the reason", "", "| Feature | Reason |", "|---|---|"]
    for c, why in sorted(dropped.items(), key=lambda kv: kv[1]):
        lines.append(f"| `{c}` | {why} |")

    lines += ["", f"## The pooled feature set: the top {BUDGET} of the pre-specified order", "",
              "Fixed here, before any engagement value was seen. Rule 5 may drop further inside "
              "training folds; it may never add, and nothing below the line can be promoted after "
              "a result is seen.", "",
              "| # | Feature | Why it is kept |", "|---|---|---|"]
    for i, c in enumerate(final, 1):
        lines.append(f"| {i} | `{c}` | {dict(PRIORITY)[c]} |")
    if reserve:
        lines += ["", f"**Reserve, in order ({len(reserve)}):** "
                  + ", ".join(f"`{c}`" for c in reserve)
                  + ". These enter only if a keeper above is removed by rule 3 (alpha) once the "
                    "automated labels exist - taken strictly in this order, not by preference."]
    if unranked:
        lines += ["", "**Survivors with no priority entry - a gap to close before modelling:** "
                  + ", ".join(f"`{c}`" for c in unranked)]

    lines += ["", "## Routed rather than dropped", "",
              "| Feature | Where it goes |", "|---|---|"]
    for c in survivors:
        if c in SPEECH_ONLY:
            lines.append(f"| `{c}` | speech-only sub-analysis (a video with no speech has no such "
                         "measurement; imputing one would invent it) |")
    for c, plat in PLATFORM_ONLY.items():
        if c in dropped and "by platform" in dropped[c]:
            lines.append(f"| `{c}` | {plat}-only models (section 4.0 rule 3) |")

    lines += ["", "## Exposure controls - outside the budget", "",
              "In every model by design (docs/05 section 4.0 rule 2): "
              + ", ".join(f"`{c}`" for c in EXPOSURE) + ".",
              "", "`account_prior_engagement` is **not** here: it is built from other videos' "
              "engagement, so it can only be computed inside cross-validation folds (Phase 9).",
              "", "## What is still outstanding", "",
              "| Rule | Status |", "|---|---|",
              "| 1 near-constant | applied |", "| 2 missingness | applied, with the exceptions above |",
              ("| 3 alpha < 0.67 | applied from 4.2 (`reports/annotation_reliability.md`); "
               "placement fixed in D-038 before alpha was known |" if rel is not None else
               "| 3 alpha < 0.67 | **waits for 4.2**, which waits for 5.12's automated labels |"),
              "| 4 within-block correlation | applied on the focus set |",
              f"| 5 lowest univariate association | **not applied and must not be yet** - it reads "
              f"the outcome, so it belongs inside training folds in Phase 9. "
              f"{'Needed: the pooled set is ' + str(len(main_model)) + ', over the budget of ' + str(BUDGET) if over else 'May not be needed: the pooled set is already within budget'} |",
              "", "5.4's `container_*` features are not in the table: the frame check failed gate B "
              "on 2026-09-29 and product visibility is reported as not measured (D-037)."]
    RECORD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\ndropped:")
    for c, why in sorted(dropped.items()):
        print(f"  {c:28} {why[:96]}")
    print(f"\nthe pooled feature set - top {BUDGET} of the fixed order:")
    for i, c in enumerate(final, 1):
        print(f"  {i:2}. {c:26} {dict(PRIORITY)[c][:58]}")
    if reserve:
        print(f"\nreserve, in order ({len(reserve)}): {', '.join(reserve)}")
    if unranked:
        print("\nNO PRIORITY ENTRY (gap to close):", ", ".join(unranked))
    print(f"\n-> {RECORD.relative_to(config.ROOT)}")
    print(f"\nBudget {BUDGET}: {len(main_model)} survived rules 0-4, so the set is the top "
          f"{len(final)} of the pre-specified order, with {len(reserve)} in reserve. Rule 5 may "
          f"trim further inside training folds; it may never add.")
    print("No engagement value was read here.")


if __name__ == "__main__":
    main()

# 5.11 feature pruning record (D-030 budget 18-20; docs/05 section 4)

Candidates 80 -> **28 survive rules 0-4**, of which **27** can enter the pooled model. Correlations and constancy were measured on the **focus set (192 usable Zero Sugar videos)**, the sample the models will use. **No engagement value was read** - rule 3 reads only the researcher-vs-model alpha, and rule 5 is not applied here (see below).

## Dropped, with the reason

| Feature | Reason |
|---|---|
| `kw_taste` | merged: half of `kw_experience` (D-036) - kept, not discarded |
| `kw_together` | merged: half of `kw_experience` (D-036) - kept, not discarded |
| `kw_offer` | merged: half of `kw_promotional` (D-036) - kept, not discarded |
| `kw_new` | merged: half of `kw_promotional` (D-036) - kept, not discarded |
| `lang_caption` | routed: language control (docs/05 Block E), not a content feature |
| `fps` | rule 0: D-024 - a file property, not a creative choice; steps that compare frames sample at a fixed rate rather than trusting native fps |
| `aspect_ratio` | rule 0: D-024 - near-constant by construction (279 of 300 at 0.562); every video is vertical (D-001) |
| `ocr_text_frame_frac` | rule 0: D-034 - near-constant (123 of 300 videos exactly 1.000, because logos and legal text appear in nearly every frame) |
| `red_frame_frac` | rule 0: D-034 - near-constant (median 1.000 on both platforms); the continuous `red_ratio` is kept instead |
| `has_question_mark` | rule 0: docs/04 section 5 rates it doubtful; 26 Shorts and 33 Reels carry one, and no hypothesis rests on it |
| `saturation` | rule 0: docs/05 Block A - pick 1-2; `colourfulness` subsumes it (Spearman 0.69) and is the documented measure |
| `contrast` | rule 0: docs/05 Block A - pick 1-2; not kept |
| `brightness` | rule 0: docs/05 Block A says pick 1-2 of brightness/contrast/saturation; `colourfulness` and `red_ratio` are the two kept |
| `scene_count` | rule 0: docs/05 section 4 / D-026 - collinear with duration (r = 0.76); `cuts_per_sec` is the rate version and is kept |
| `ocr_max_text_area` | rule 0: extreme version of `ocr_mean_text_area`, which is kept |
| `max_face_count` | rule 0: extreme version of face presence; `mean_face_area` carries close-up vs crowd more interpretably |
| `silence_frac` | rule 0: not in docs/05 Block B's list; loudness and talking share cover it |
| `saturation_sd` | rule 0: secondary spread version of a kept mean |
| `red_ratio_sd` | rule 0: secondary spread version of a kept mean |
| `brightness_sd` | rule 0: secondary spread version of a kept mean; means come first |
| `music_present` | rule 0: the boolean of `music_frac`, which is kept |
| `is_single_shot` | rule 0: the extreme of `cuts_per_sec` (23 videos), already carried by it |
| `sentiment_speech_source` | rule 1: near-constant - 98.3% of the focus set share one value |
| `audio_silent` | rule 1: near-constant - 99.0% of the focus set share one value |
| `hidden_montage` | rule 1: near-constant - 99.5% of the focus set share one value |
| `sentiment_speech` | rule 2 exception: 38% missing **because the video has no speech** - not imputed, routed to the speech-only sub-analysis |
| `emotion_label` | rule 2 exception: 38% missing **because the video has no speech** - not imputed, routed to the speech-only sub-analysis |
| `emotion_score` | rule 2 exception: 38% missing **because the video has no speech** - not imputed, routed to the speech-only sub-analysis |
| `speech_sung_frac` | rule 2 exception: 40% missing **because the video has no speech** - not imputed, routed to the speech-only sub-analysis |
| `words_per_min` | rule 2 exception: 42% missing **because the video has no speech** - not imputed, routed to the speech-only sub-analysis |
| `voiced_frac` | rule 2 exception: 46% missing **because the video has no speech** - not imputed, routed to the speech-only sub-analysis |
| `pitch_median_hz` | rule 2 exception: 47% missing **because the video has no speech** - not imputed, routed to the speech-only sub-analysis |
| `pitch_std_semitones` | rule 2 exception: 47% missing **because the video has no speech** - not imputed, routed to the speech-only sub-analysis |
| `pitch_median_talk_hz` | rule 2 exception: 51% missing **because the video has no speech** - not imputed, routed to the speech-only sub-analysis |
| `pitch_std_talk_semitones` | rule 2 exception: 51% missing **because the video has no speech** - not imputed, routed to the speech-only sub-analysis |
| `title_char_len` | rule 2 exception: 62% missing **by platform** - kept for youtube-only models (section 4.0 rule 3) |
| `title_char_len_z_lang` | rule 2 exception: 64% missing **by platform** - kept for youtube-only models (section 4.0 rule 3) |
| `lang_audio` | rule 2: 37% missing and no sensible flag |
| `lang_match` | rule 2: 44% missing and no sensible flag |
| `auto_has_cta` | rule 3: alpha -0.032 (95% CI -0.33 to 0.23) on 46 held-out videos - below 0.67, dropped (4.2) |
| `auto_has_celebrity` | rule 3: alpha 0.100 (95% CI -0.16 to 0.48) on 41 held-out videos - below 0.67, dropped (4.2); also rule 1: near-constant - 97.7% of the focus set share one value |
| `auto_humour_present` | rule 3: alpha 0.133 (95% CI -0.62 to 0.71) on 7 held-out videos; model unsure on 76% - below 0.67, dropped (4.2) |
| `auto_has_influencer` | rule 3: alpha 0.382 (95% CI 0.03 to 0.69) on 39 held-out videos - below 0.67, dropped (4.2) |
| `auto_product_vs_lifestyle` | rule 3: no manual check exists, so it can only be an unvalidated automated label - kept as a column, never enters a model (D-023, D-038) |
| `auto_ugc_vs_brand` | rule 3: no manual check exists, so it can only be an unvalidated automated label - kept as a column, never enters a model (D-023, D-038) |
| `auto_promotional_language` | rule 3: no manual check exists, so it can only be an unvalidated automated label - kept as a column, never enters a model (D-023, D-038) |
| `speech_dur_frac` | rule 4: |Spearman| 0.900 with `talk_dur_frac` inside B_audio - kept the more interpretable of the pair |
| `speech_frac_ast` | rule 4: |Spearman| 0.908 with `talk_dur_frac` inside B_audio - kept the more interpretable of the pair |
| `word_count` | rule 4: |Spearman| 0.941 with `speech_dur_frac` inside B_audio - kept the more interpretable of the pair |
| `caption_word_count` | rule 4: |Spearman| 0.945 with `caption_char_len` inside C_text - kept the more interpretable of the pair |
| `mean_face_count` | rule 4: |Spearman| 0.985 with `face_present_frac` inside A_video - kept the more interpretable of the pair |
| `mean_shot_len_sec` | rule 4: |Spearman| 0.986 with `cuts_per_sec` inside A_video - kept the more interpretable of the pair |

## The pooled feature set: the top 20 of the pre-specified order

Fixed here, before any engagement value was seen. Rule 5 may drop further inside training folds; it may never add, and nothing below the line can be promoted after a result is seen.

| # | Feature | Why it is kept |
|---|---|---|
| 1 | `duration_sec` | H1 - duration within short form |
| 2 | `cuts_per_sec` | pace; the montage decision of D-026 lives here |
| 3 | `motion_px_per_sec` | movement, measured in 5.3 |
| 4 | `face_present_frac` | H4 - human presence, the validated half of it |
| 5 | `mean_face_area` | close-up vs crowd, which presence alone cannot separate |
| 6 | `edge_density` | visual busyness |
| 7 | `colourfulness` | colour, the least redundant of the colour measures |
| 8 | `red_ratio` | brand-meaningful colour (docs/05 Block A) |
| 9 | `ocr_region_count` | amount of on-screen text (D-034) |
| 10 | `ocr_mean_text_area` | how much of the frame that text covers |
| 11 | `music_frac` | H3/Block B - music presence, zero is a true measurement |
| 12 | `talk_dur_frac` | talking share, net of singing (D-028) |
| 13 | `loudness_db_mean` | loudness |
| 14 | `loudness_range_db` | dynamics |
| 15 | `sentiment_caption` | H3 - emotional tone of the text every video has |
| 16 | `caption_char_len` | Block C - caption length, normalised within language later |
| 17 | `hashtag_count` | Block C - invariant across languages |
| 18 | `emoji_count` | Block C - invariant, and predictive in this literature |
| 19 | `kw_event` | H6 / Block C keywords - the largest group (104 videos, D-035) |
| 20 | `kw_promotional` | H6 / Block C - offer or new, merged (D-036) |

**Reserve, in order (7):** `kw_experience`, `spectral_centroid_hz`, `tempo_bpm`, `kw_zero_sugar`, `is_code_switched`, `mention_count`, `longest_shot_frac`. These enter only if a keeper above is removed by rule 3 (alpha) once the automated labels exist - taken strictly in this order, not by preference.

## Routed rather than dropped

| Feature | Where it goes |
|---|---|
| `title_char_len` | youtube-only models (section 4.0 rule 3) |
| `title_char_len_z_lang` | youtube-only models (section 4.0 rule 3) |

## Exposure controls - outside the budget

In every model by design (docs/05 section 4.0 rule 2): `followers`, `video_age_days`, `account_size_tier`, `posting_hour_utc`, `is_weekend_utc`, `platform`.

`account_prior_engagement` is **not** here: it is built from other videos' engagement, so it can only be computed inside cross-validation folds (Phase 9).

## What is still outstanding

| Rule | Status |
|---|---|
| 1 near-constant | applied |
| 2 missingness | applied, with the exceptions above |
| 3 alpha < 0.67 | applied from 4.2 (`reports/annotation_reliability.md`); placement fixed in D-038 before alpha was known |
| 4 within-block correlation | applied on the focus set |
| 5 lowest univariate association | **not applied and must not be yet** - it reads the outcome, so it belongs inside training folds in Phase 9. Needed: the pooled set is 27, over the budget of 20 |

5.4's `container_*` features are not in the table: the frame check failed gate B on 2026-09-29 and product visibility is reported as not measured (D-037).

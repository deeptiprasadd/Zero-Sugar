# 16 — The proposal, item by item: where each is answered

**Written 2026-10-17 (D-063, D-064).** Every item of `coco-cola-proposal.docx`, in the proposal's order, with
what the study did, where the answer is, and the decision behind it. Facts only, for the thesis and the
supervisor; nothing here is new analysis. Status: **done** - measured, tested or described as the proposal asks;
**changed** - done differently, with the reason in [15](15-changes-from-proposal.md); **not measurable** - tried,
and reported as a finding. "Addition" marks a declared addition, reported beside the pre-registered results,
never in place of them (D-050, D-056, D-063).

Analysis set throughout: 192 Coca-Cola Zero Sugar videos with a usable engagement figure (Instagram 120 from 17
accounts, YouTube 72 from 5 channels, 58 from one). The Zero Sugar label's repeat reliability goes with every
result: YouTube alpha 0.25, Instagram -0.10.

## 1. Framework

| Step | Status | Where |
|---|---|---|
| Zero Sugar marketing videos | changed - Shorts and Reels only; analysis narrowed to Zero Sugar on 23 Sep | D-001, D-030, D-039 |
| YouTube + Instagram data collection | done | [12](12-data-collection-record.md) |
| Video / audio / text / metadata extraction | done | [05](05-feature-extraction.md), [04](04-multilingual-pipeline.md) |
| Feature engineering | done - 76 candidates, 20 model features fixed before any outcome | D-036 |
| Marketing effectiveness measurement | changed - see section 3 | [06](06-dependent-variable.md), D-005 |
| EDA | done - section 7 | [07](07-eda.md) |
| Statistical analysis | done - section 8 | [08](08-statistical-analysis.md), D-042, D-043 |
| Machine learning prediction | done - section 9 | [09](09-modelling.md), D-044, D-045 |
| SHAP / explainable AI | done - section 10 | [10](10-explainability.md), D-047, D-048 |
| Characteristics of effective campaigns | done - the effective-video profile | D-052, `reports/effective_video_profile.md` |

## 2. Independent variables

| Block | Item | Status | Measure (where) |
|---|---|---|---|
| A Video | Video duration | done | `duration_sec` (5.2, ffprobe) |
| A | Aspect ratio | changed - dropped | every video vertical by design (D-024, D-036) |
| A | Visual complexity | done | `edge_density` (5.5A) |
| A | Number of scene changes | done | `cuts_per_sec`, log1p in models (5.2, D-026, D-040) |
| A | Product visibility | changed - hand-coded | automated detection failed (D-033, D-037); researcher's codes of all 192 (D-049) |
| A | Face / person presence | done | `face_present_frac`, face size (5.5C); "a person appears" hand-coded (D-049) |
| A | Text on screen | done | `ocr_region_count`, `ocr_mean_text_area` - detected, not read (D-034) |
| A | Brand / logo visibility | changed - hand-coded | D-049 |
| A | Colour / visual features | done | `colourfulness`, `red_ratio`, brightness, saturation (5.5A) |
| B Audio | Speech duration | done | `talk_dur_frac`, `speech_dur_frac` (5.6, 5.8) |
| B | Music presence | done | `music_present`, `music_frac` (5.8, D-028) |
| B | Music type | changed - hand-coded by ear | automated genre labels not measurable (D-033); codes D-049 |
| B | Speech rate | done - addition | `words_per_min`, 112 videos; not detected (D-057) |
| B | Audio intensity | done | `loudness_db_mean`, `loudness_range_db` (5.8) |
| B | Emotional tone | changed - hand-coded voice tone | voice emotion had no model (D-032); excited / calm / no voice coded (D-049) |
| B | Background music | done - addition | music behind talking, 106 videos; not detected (D-063, D-064) |
| C Text | Caption length | done | `caption_char_len`, standardised within language (D-055 section 4) |
| C | Title length | done - YouTube only | `title_char_len` (5.14) |
| C | Hashtags | done | `hashtag_count` - the one registered association, between accounts (D-043) |
| C | Keywords | changed - six groups merged into three | `kw_event`, `kw_promotional`, `kw_experience` (5.16, D-035, D-036) |
| C | Call to action | changed - hand-coded | automated label failed (D-038); codes D-049; H5 (D-051) |
| C | Sentiment | done | caption and speech sentiment (5.9, D-031) |
| C | Emotion | done - speech, English translation | 119 of the 121 videos with speech (D-031) |
| C | Promotional language | done | `kw_promotional` (D-036); the automated label failed (D-038) |
| C | Brand / product mentions | done - addition | Coca-Cola named, Zero Sugar named; not detected (D-057) |
| D Creator | Influencer / creator involvement | changed - hand-coded | automated label failed (D-038); codes D-049; collaboration posts from metadata (5.15) |
| D | Celebrity involvement | changed - hand-coded | automated label failed (D-038); codes D-049 |
| D | Campaign type | changed - hand-coded | dropped 24 Sep (D-032), then coded (D-049); described, not modelled (D-050) |
| D | Sponsored content | changed - hand-coded | judged from caption and video only (D-049) |
| D | Product- vs lifestyle-focused | changed - hand-coded | automated label disagrees with the codes, alpha 0.15 (D-051) |
| D | User- vs brand-generated | changed - hand-coded (the look) | automated label alpha 0.34 (D-051) |
| E Platform | YouTube vs Instagram | done | H7, EDA 8 (D-043, docs/07) |
| E | Posting time | done | UTC hour in models; local hour as a sensitivity (D-050, D-051) |
| E | Posting date | done | video age in every model; weekend flag; year in EDA 1 |
| E | Platform-specific engagement indicators | done - addition | YouTube per-view rate (D-057); Instagram publishes no reliable views (docs/06) |

## 3. Dependent variable

| Item | Status | Where |
|---|---|---|
| High vs low engagement | done - median split of the percentile, 100 / 92 | docs/06, D-041 |
| (Likes + comments + shares) / views | changed - (likes + comments) / followers | shares not public; Instagram views not reliable (docs/15 row 3) |
| Normalise within each platform | done - percentile within platform x follower tier | docs/06 section 3 |

## 4. Objectives

| # | Objective | Answer in one line | Where |
|---|---|---|---|
| Primary | Identify and predict characteristics of effective videos | associations found inside these accounts; nothing predicts a new account's video | D-043, D-045, D-051 |
| 1 | Collect the videos | 300 downloaded; 192 analysed | docs/12 |
| 2 | Distribution and characteristics | EDA 1-9 | docs/07 section 3 |
| 3 | Measure engagement | follower-based rate and percentile | docs/06 |
| 4 | Characteristics associated with effectiveness | hashtags (between accounts); call to action (addition, most robust) | D-043, D-051 |
| 5 | Duration and engagement | not detected | H1, D-043 |
| 6 | Emotional tone | not detected; full EDA 6 table described | H3, D-043; D-064 |
| 7 | Influencer / celebrity | detected, not robust to one AI-character series | H4, D-051 |
| 8 | Product visibility | detected, not robust to that series | H2, D-051 |
| 9 | Compare YouTube and Instagram | not detected; platform tied to selection and account size | H7, D-043; EDA 8; D-064 |
| 10 | Captions, hashtags, calls to action | hashtags between accounts; call to action within accounts | H6 (D-043), H5 (D-051) |
| 11 | Strongest predictors | no model beats reach for unseen accounts | D-045, D-048 |
| 12 | Machine-learning models | five models, three feature sets, grouped folds | D-044, D-045 |
| 13 | Statistics vs machine learning | fact sheet | docs/14 |
| 14 | SHAP | stable reliance pattern; Instagram: hashtags, talking, faces | D-047, D-048 |
| 15 | Profile of an effective video | Instagram: more talking, more faces; pooled: call to action | D-052 |

## 5. Research questions

| RQ | Answer | Where |
|---|---|---|
| RQ1 characteristics associated | as Objective 4 | docs/10 section 6 |
| RQ2 duration | not detected | H1 |
| RQ3 emotional tone | not detected | H3; D-064 Part B |
| RQ4 product presence | detected as an addition, not robust | H2 (D-051) |
| RQ5 influencer / celebrity | detected as an addition, not robust | H4 (D-051) |
| RQ6 captions, hashtags, calls to action | hashtags (between accounts), call to action | H6, H5 |
| RQ7 differences between platforms | no divergence meets the SHAP rule; H9 exploratory; described opposite directions for talking, faces, duration, humour | D-048, D-043, D-052, D-064 |
| RQ8 strongest predictors | none usable for a new account | D-045 |
| RQ9 (missing in the proposal's numbering; added) content beyond reach | no | D-045 |
| RQ10 what SHAP reveals | a consistent pattern that does not carry to new accounts; three Instagram correlates | D-048 |

## 6. Milestones 1-3

| Milestone | Item | Status |
|---|---|---|
| 1 YouTube | video ID, title, description, publication date, duration, views, likes, comments, channel information | done - `data/raw/youtube_shorts.parquet` (YouTube Data API) |
| 1 YouTube | thumbnail | done - collected (thumbnail link for all 2,094 videos); not analysed, as the proposal asks only to collect it |
| 1 YouTube | transcript where available | done - the study's own speech-to-text for every video (5.6, D-027); YouTube's own captions were not fetched |
| 1 Instagram | reel ID, caption, publication date, likes, comments, duration, hashtags, account information, reel content | done - `data/raw/instagram_reels.parquet`; 150 Reels downloaded (docs/12) |
| 2 | frames, audio, speech, on-screen text, faces, scene transitions, duration | done (5.1-5.6, 5.5) |
| 2 | product appearance, brand / logo appearance | changed - hand-coded after automated detection failed (D-037, D-049) |
| 3 | feature engineering | done (D-036) |

## 7. EDA

| EDA | Status | Where |
|---|---|---|
| 1 Distribution of videos | done | docs/07 row 1 |
| 2 Engagement distribution | done | docs/07 row 2 |
| 3 Video duration | done | docs/07 row 3 |
| 4 Product visibility | done (hand codes) | `reports/eda_codes.md` |
| 5 Human / influencer presence, four groups | done (hand codes) | `reports/eda_codes.md` |
| 6 Emotional content, seven kinds, against engagement | done - all seven side by side | `reports/statistical_results_p21.md` Part B (D-064) |
| 7 Caption and text | done | docs/07 row 7 |
| 8 YouTube vs Instagram, and the proposal's comparison table | done - table filled | docs/07 row 8; `reports/statistical_results_p21.md` Part C (D-064) |
| 9 Correlations (duration, product, emotion, creator, call to action, caption length) | done | docs/07 row 9; `reports/eda_codes.md` |

## 8. Hypotheses

| H | Verdict | Where |
|---|---|---|
| H1 duration | not detected | D-043 |
| H2 product visibility | detected as an addition; not robust | D-051 |
| H3 positive emotion | not detected | D-043 |
| H4 influencer or celebrity | detected as an addition; not robust, mainly between accounts | D-051 |
| H5 call to action | detected as an addition; the most robust; within accounts | D-051 |
| H6 caption length and hashtags | hashtags detected, between accounts only; caption length not | D-043 |
| H7 platform difference | not detected | D-043 |
| H8 joint predictive power | not detected | D-043, D-045 |
| H9 predictors differ by platform | exploratory; no SHAP divergence | D-043, D-048 |
| H10 duration x platform | exploratory; about zero | D-043, D-048 |

## 9-11. Models, evaluation, SHAP

| Item | Status | Where |
|---|---|---|
| Logistic regression, decision tree, random forest, XGBoost, MLP | done | D-045, docs/09 section 6 |
| Accuracy, precision, recall, F1, ROC-AUC, PR-AUC | done | docs/09 section 6 |
| Confusion matrix | done | `reports/confusion_matrices.md` (D-051) |
| Minority-class rule | not needed - 100 / 92 split | docs/07 row 2 |
| Stratified train/test split | changed - account-grouped cross-validation | D-006, D-044 |
| Cross-validation | done - 5 folds x 3 repeats, grouped by account | D-044 |
| Class weighting | done - `balanced` in the forest and XGBoost | docs/09 section 1 |
| Hyperparameter tuning | done - on grouped inner folds | D-044 |
| Threshold optimisation | done - F1 threshold, Youden's J beside it | D-044 |
| SHAP after XGBoost / random forest | done for XGBoost and two Instagram models; the random forest was at chance and not explained | D-047 |
| Importance of duration, product, emotional tone, influencer, call to action, caption, hashtags, audio, platform, posting | done - content features (D-048); hand codes in the SHAP of the addition models (D-051) | D-048, D-051 |
| Increase or decrease? | done - direction rule | D-047 rule 5 |
| Different on YouTube and Instagram? | done - no divergence meets the rule | D-048 |

## Beyond the proposal

The prediction tool (D-017, D-046, D-053-D-062), the declared additions (D-050/D-051, D-056/D-057, D-063/D-064),
and RQ9. Every change from the proposal, with its reason: [15](15-changes-from-proposal.md).

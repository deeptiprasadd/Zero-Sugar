# 07 — Exploratory Data Analysis

**Status:** **Run 2026-09-29** on the table frozen that day (docs/08 §6). Script: `src/eda/explore.py` (a script rather than the planned notebook, so every figure and number regenerates in one command). Figures: `reports/figures/eda*.png`, `diag*.png`; every number cited below: `reports/eda_numbers.md`.

Covers the proposal's EDA 1–9, plus five diagnostics the literature survey showed are
needed. Every figure gets a one-line finding recorded in §3 — a plot with no written
finding has not been analysed.

---

## 1. Proposal EDA 1–9

**Scope from 2026-09-23 (D-030): every analysis below runs on the focus set** — since 2c.R2 (D-039,
2026-09-29) **192 usable Zero Sugar videos, 22 accounts (Instagram 120 / 17, YouTube 72 / 5)**; at registration the 183 usable
Zero Sugar videos (`in_focus & dv_status == "ok"`; Instagram 111 from 16 accounts, YouTube 72
from 5). Every figure's title carries its n in videos and accounts. The 107 usable videos that
are not Zero Sugar stay in the data and are shown only in clearly labelled robustness panels,
never mixed in. EDA 1 (distribution of videos) is run on both sets, since knowing what the focus
left out is part of describing it.

| # | Analysis | Note under the short-form design |
|---|---|---|
| 1 | Distribution of videos | By platform, market, language, account, year, sampling tier |
| 2 | Engagement distribution | Both DV forms; expect heavy right skew — log for plotting |
| 3 | Video duration | **Range is now narrow** (both platforms ≤180s). H1 is a within-short-form test |
| 4 | Product visibility vs engagement | `product_visible_frac` split at median and as a continuous scatter. **2026-09-29: cannot be drawn** — product visibility is not measured (D-037) |
| 5 | Human / influencer presence | None / ordinary / influencer / celebrity — check cell sizes, may need collapsing |
| 6 | Emotional content | Remember emotion is measured post-translation ([04](04-multilingual-pipeline.md) §4) |
| 7 | Caption and text | Prefer invariant features; normalise caption length within language |
| 8 | YouTube vs Instagram | **Use the follower-normalised DV only** (D-005). **Pre-registered: §1a (2026-09-22), rewritten for the focused design in §1b (D-030)** |
| 9 | Correlation / association | Full matrix, then per-block |

### 1a. EDA 8 — pre-registered (D-029, 2026-09-22) — **superseded by §1b**

Left exactly as registered. It is now the plan for the wider 300-video robustness set; the
focused design (Zero Sugar only, D-030) is registered in §1b, and what changed is recorded in
[08](08-statistical-analysis.md) §7.8.

Written before any platform comparison was run; what had already been seen is disclosed in
[08](08-statistical-analysis.md) section 7.2. EDA 8 is descriptive: it makes no claim about
platform, it shows what the platform comparison is made of.

Runs on the frozen labels only ([08](08-statistical-analysis.md) section 7.4). In this order:

1. **Composition table first**, before any engagement value is shown: videos **and accounts** in
   every cell of platform x `is_zero_sugar` x `selection` (hand_picked | systematic), and
   platform x follower tier. Cells under 20 videos or 3 accounts are marked.
2. **How each Zero Sugar label was decided**, by platform: counts of `zs_label_method` (text /
   researcher_curated / clip_then_researcher).
3. **Figure:** distribution of `log10(engagement_rate_follower)` by platform, one panel per
   `is_zero_sugar` value, hand-picked Reels drawn in a distinct marker, the global YouTube
   channel in another. Per-panel n (videos, accounts) printed on the panel.
4. **Written finding (section 3, row 8):** states composition before any difference, and uses no
   word stronger than "differs descriptively". The inferential answer is model (a) of
   [08](08-statistical-analysis.md) section 7.5 and the verdict rules of section 7.6.

Not in EDA 8: any test, any p-value, any statement that one platform "performs better".

### 1b. EDA 8 — focused design, Zero Sugar only (registered 2026-09-23, D-030)

Written before any platform comparison was run. Replaces §1a for the analysis that is reported;
§1a still describes the robustness set. EDA 8 stays descriptive: it makes no claim about
platform, it shows what the comparison is made of. Runs on the frozen table only
([08](08-statistical-analysis.md) §6, row dated 2026-09-23). In this order:

1. **Composition table first**, before any engagement value is shown — the focus set
   (`in_focus & dv_status == "ok"`, **183 videos, 21 accounts**): videos **and accounts** in every
   cell of platform × `selection` and platform × follower tier. Cells under 20 videos or 3
   accounts are marked; on today's counts that marks Instagram systematic (6 videos, 5 accounts)
   and YouTube small+medium (14 videos, 4 accounts), and notes that YouTube large is 58 videos
   from **one** channel.
2. **How each Zero Sugar label was decided**, by platform: counts of `zs_label_method` (text /
   researcher_curated / researcher_visual_check), stated with the label's repeat agreement — 16
   of 25, alpha 0.25 (D-029). Under D-030 this label decides inclusion, so this table says who
   is in the study and on what evidence.
3. **Figure:** distribution of `log10(engagement_rate_follower)` by platform for the focus set,
   hand-picked Reels in a distinct marker, the global YouTube channel in another, per-panel n
   (videos, accounts) printed. One extra panel, clearly labelled as the robustness set, shows the
   107 usable rows that are not Zero Sugar — never mixed into the focus panel.
4. **Written finding (§3, row 8):** states composition before any difference, uses no word
   stronger than "differs descriptively", and states the selection caveat of
   [08](08-statistical-analysis.md) §7.9.3(c) — every hand-picked video is an Instagram Reel, so
   platform and selection cannot be separated in the focused design. The inferential answer is
   model (a) of §7.9.3 under the verdict rules of §7.9.4.

Not in EDA 8: any test, any p-value, any statement that one platform "performs better".

---

## 2. Added diagnostics

These are not optional — each one guards a decision made later.

| # | Diagnostic | Guards |
|---|---|---|
| A | **Videos per account**, bar chart | Justifies grouped CV (D-006). If one account holds 40% of the corpus, say so here. |
| B | **Engagement vs `video_age_days`**, scatter + LOESS | Shows how much age drives raw counts |
| C | **Correlation heatmap + VIF** | Drives the pruning in [05](05-feature-extraction.md) §4 |
| D | **Missingness matrix** | Hidden likes, absent views, failed extractions |
| E | **Sampling-tier balance by platform** | If YouTube is 90% brand and Instagram 60% creator, the platform comparison is partly a creator comparison |
| F | **Cross-posted pair count** | Determines whether the paired sub-analysis is viable (needs ≥20 pairs) |
| G | **Market × platform cell sizes** | Confirms quotas held; flags collinearity between market and account |

---

## 3. Findings log

_One line per figure. Fill as the analysis runs._

**Filled 2026-09-29.** Focus set, 192 videos / 22 accounts, unless stated. Every association
below is descriptive (Spearman or medians): no test was run and none may be read as an effect.

| # | Figure | Finding |
|---|---|---|
| 1 | `eda1_composition` | The focus set is recent (111 of 192 posted in 2026) and English-led (107 English captions, 12 languages in all); YouTube is concentrated in North America & Global (58 of 72) and the large-follower tier (58), Instagram spreads over 7 regions and all three tiers. |
| 2 | `eda2_engagement_distribution` | The raw rate is extremely skewed (skewness 9.5; median 0.0013); log10 removes it (0.15). The percentile DV is close to uniform, and the median split is **100 / 92 (52% / 48%) - the docs/06 §4 fallback (worse than 60/40) is not triggered**, so the existing percentile and label stand. |
| 3 | `eda3_duration` | Durations are short on both platforms (median 18.9 s Instagram, 20.5 s YouTube; 90th percentile 69 / 60 s). Duration and percentile are unrelated overall (Spearman -0.05); the upturn of the smoothed line above about 90 s rests on roughly 15 videos. |
| 4 | - | Not drawn: product visibility is not measured (D-037). |
| 5 | `eda5_human_presence` | Faces are almost universal (170 of 192 show one); median percentile 0.52 with no face, 0.48 face in up to half, 0.57 face in most frames - no steady pattern. On Instagram, creator-collaboration Reels sit higher (median 0.64, 31 videos / 8 accounts) than the rest (0.46, 89 / 16), but they come from half as many accounts. Celebrity and creator presence are not measured (D-038), so EDA 5's four categories cannot be built. |
| 6 | `eda6_emotion` | Caption sentiment is mostly positive and unrelated to percentile (Spearman 0.06, 185 videos); in this set it is also unrelated to caption length (-0.03), so the length check D-031 asked for finds no confound here. Speech emotion exists for 119 videos; only neutral (67), joy (25) and surprise (15) have 10+ videos - the other four labels have 12 between them. |
| 7 | `eda7_text` | Caption, hashtag, emoji and on-screen-text counts have similar medians on both platforms (hashtags 2, emoji 1). The smoothed rises with hashtags and emoji are carried by a handful of videos at 6+ hashtags or 6+ emoji. `kw_event` videos have a lower median percentile (0.43, 46 videos / 8 accounts) than the rest (0.57); 31 of the 46 are YouTube Shorts, mostly the FIFA campaign (D-035), so this is at least partly composition. |
| 8 | `eda8_platform_descriptive` | **Composition first:** every hand-picked video is an Instagram Reel (105 of 120); 58 of YouTube's 72 are one global channel (the only YouTube account in the large tier); labels rest on the researcher's curation or look for 161 of 192, with weak repeat agreement (YouTube alpha 0.25, Instagram -0.10). **Then:** the follower-normalised rate differs descriptively - median log10 -2.55 Instagram vs -4.32 YouTube - and a gap in the same direction appears in the robustness set. Platform, selection route and account size cannot be separated in these data (docs/08 §7.9.3(c)); this figure answers nothing about platform. |
| 9 | `eda9_feature_correlation` | Among the 20 features only five pairs reach Spearman 0.5 in size, the strongest colourfulness - red ratio 0.72; none reaches the 0.85 pruning line. |
| A | `diagA_videos_per_account` | 22 accounts; the global YouTube channel holds 58 videos (30% of the focus set) and three Instagram accounts another 60; 5 accounts contribute one video. Account-grouped CV (D-006) and the account random intercept are necessary, and account-grouped folds will be very unequal. |
| B | `diagB_age` | Older videos have higher raw rates (Spearman 0.44 with log10 rate; age 8-2,021 days, median 202) and, more weakly, higher percentiles (0.20). The YouTube Shorts are mostly 50-100 days old and low, so age and platform overlap. Age stays in every model as an exposure control. |
| C | `eda9_feature_correlation` (+ VIF in `eda_numbers.md`) | VIF is low for all 20 (maximum 3.6, colourfulness; none above 5). No collinearity drop is needed. |
| D | `diagD_missingness` | The 20 features are nearly complete: `mean_face_area` 11.5% missing (videos with no face - structural), `kw_event` / `kw_promotional` 4.7% ("not searched", D-035; 7 Reels, 2 Shorts), caption sentiment 3.6%, loudness 1% (the silent Reels, D-025). The view-based rate is missing for every Reel by design (YouTube only). |
| E | (tables in `eda_numbers.md`) | Every YouTube Short comes from a brand channel and 81% from the large tier; Instagram is 77% market brand accounts, 49% medium tier, with 31 creator collaborations. The platform comparison is also a comparison of account size and of curation. |
| F | (`reports/eda_crossposted_pairs.csv`) | **2 cross-posted pairs** by the rule fixed before looking (frame-embedding cosine >= 0.95, durations within 1 s); 6 YouTube Shorts have any Instagram match even at 0.90. **The paired sub-analysis (8.3, needs 20+) is not viable.** |
| G | (tables in `eda_numbers.md`) | 19 markets; only 3 (Global/US, Brazil, Thailand) appear on both platforms, and 16 markets have a single account - market and account are nearly the same variable, so market cannot enter a model beside account. |

---

## 4. Decisions coming out of EDA

_EDA should change the plan. Record what it changed._

**Filled 2026-09-29.** Each rule below uses counts or feature distributions only - none was chosen
by looking at which option gives a stronger engagement result.

| Decision | Driven by | Outcome |
|---|---|---|
| Features dropped for collinearity | Diagnostic C | **None.** Max VIF 3.6, max correlation 0.72; the 20 stand (D-036) |
| Categories collapsed for thin cells | EDA 5, EDA 6, Diagnostic G | **Emotion (H3):** labels with fewer than 10 focus videos merge into "other" - joy 25, neutral 67, surprise 15, other 12. **Human presence (H4):** only the face measures exist (D-038). **Market:** not a model term - it duplicates account in 16 of 19 markets |
| Normalisation scheme confirmed or revised | EDA 2, Diagnostic G | **Confirmed.** Median split 52 / 48, fallback not triggered; percentile within platform x size stays (docs/06 §3.1) |
| Paired sub-analysis viable? | Diagnostic F | **No** - 2 pairs against the 20 required. Task 8.3 is closed as not viable |
| Accounts excluded as outliers | Diagnostic A | **None.** The global channel (30%) stays; its influence is what docs/08 §7.9.3(d)'s pre-registered sensitivity analysis measures |
| Scale of `cuts_per_sec` (TODO 7.2) | Distribution only (D-026) | **log1p** in every model: one real montage at 9.68 against a next-highest 1.78; skewness 10.2 raw, 1.7 after log1p. The montage stays in (D-026) |

---

## 5. Plotting conventions

- Log scale for all raw engagement counts.
- Colour by platform consistently across every figure (fix the mapping once).
- Show n in every subplot title — with thin cells this matters constantly.
- Box plots must show individual points at this sample size; a box over 12 observations
  hides more than it shows.
- Every figure saved to `reports/figures/` at 300 dpi with a descriptive filename.

## 6. Addition, 2026-10-09 - exploration with the hand codes (D-050, D-051)

EDA 4 (product visibility), EDA 5 (four people groups) and EDA 6 (humour, excitement, voice tone), which
the automated measures could not support, re-run on the researcher's hand codes of the 192 videos;
descriptive only. Output `reports/eda_codes.md` and four figures (`eda4_product_visibility`,
`eda5_people_groups`, `eda6_tone`, `eda8_codes_by_platform`). Findings, as description:

- Celebrity videos (17, all Instagram, from 5 accounts) have a median percentile of 0.93; the other people
  groups 0.45-0.62. YouTube has no celebrity video.
- Videos with a call to action: median 0.66 against 0.44 without; lifestyle-focused 0.44 against
  product-focused 0.65; event campaigns 0.35, the lowest group.
- The 15 AI-character Shorts (one YouTube series) are coded no prominent product, no person and no call to
  action, and pull several group medians down; every table is also given without them.
- The codes are weakly reliable where checked (`reports/repeat_check.md`): read every difference as
  tentative.

## 7. Addition, 2026-10-17 - EDA 6 completed and the proposal's EDA 8 table (D-063, D-064)

Description only, on the 192; output `reports/statistical_results_p21.md` (Parts B and C).

- **EDA 6, the proposal's seven kinds side by side.** Median percentile: positive captions 0.545 (101), neutral
  0.546 (78), negative 0.478 (6, thin); positive speech 0.573 (45), neutral 0.565 (44), negative 0.461 (30);
  excitement 0.522 (84); humour 0.564 (56); surprise in speech 0.538 (15); happiness ("joy") in speech 0.683 (25,
  21 of them Reels). Nothing beyond H3 (not detected).
- **The proposal's table, Instagram / YouTube:** duration 18.9 / 20.5 s; likes + comments per follower 0.280% /
  0.0048% (YouTube per view 1.22%); caption 142.5 / 128.5 characters; product prominent 78% / 60%; creator or
  celebrity 45% / 12% of coded videos; positive captions 64% / 40%; joy in speech 31% / 8%; humour 34% / 26%;
  excitement 47% / 44%. Within each platform, product prominence and joy point the same way; duration, caption
  length, creator or celebrity, positive captions, humour and excitement point opposite ways (Spearman with the
  percentile, description). YouTube is 72 videos, 58 from one channel, including the 15 AI-character Shorts;
  platform, selection route and account size cannot be separated (docs/08 section 7.9.3(c)).

# P21 - the last proposal items: background music, EDA 6 completed, the proposal's platform table (D-063)

Focus set 192 videos, 22 accounts. A declared addition: the registered results (D-043, D-045, D-048) and the additions of D-051 and D-057 are unchanged. Engagement = percentile within platform x follower tier. Zero Sugar label: YouTube alpha 0.25, Instagram -0.10. Hand codes: one coder, 110 minutes for 100 minutes of video. Coverage of every proposal item: docs/16-proposal-coverage.md.

## Part A - background music behind talking (new measure, D-063)

Measured from the 5.8 records, nothing re-measured: **106 of 192 videos have talk** (Instagram 60, YouTube 46); the rest have no speech, silent audio, unintelligible or only sung speech, and are missing. Share of talking time with music behind it: median 0.76 (Instagram 0.66, YouTube 0.84); exactly 0 for 13, exactly 1 for 22; music behind at least half of the talking: 75 yes / 31 no. (D-063 recorded 106 / 13 / 22 / 75 from the counts before any test.)

### Description
| Kind | Measure | Group | Videos | Accounts | Instagram / YouTube | Median percentile | Rest: median (n) | Group without AI-character Shorts: median (n) |
|---|---|---|---|---|---|---|---|---|
| background music | music behind at least half of the talking | yes | 75 | 14 | 37 / 38 | 0.556 | 0.556 (31) | 0.593 (61) |
| background music | music behind at least half of the talking | no | 31 | 11 | 23 / 8 | 0.556 | 0.556 (75) | 0.565 (30) |

### The P21 family (two tests, its own Benjamini-Hochberg family, q = 0.05)
| # | Outcome | Measure | n, accounts | Test | Effect (95% CI) | Raw p | BH p | Verdict | Without AI-character Shorts: effect, raw p | Min. detectable |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | percentile (pooled) | background music (share of talking time with music behind it) | 106, 15 | LR test (mixed model), 1 df | -1.5 pct points per SD (-7.0 to +4.0) | 0.636 | 0.997 | **not detected at this sample size** | -0.5 pct points per SD, 0.900 (n 91) | r 0.27 |
| 2 | percentile (pooled) | background music (share of talking time with music behind it) | 106, 15 | Spearman | rho +0.000 | 0.997 | 0.997 | **not detected at this sample size** | rho +0.075, 0.477 (n 91) | r 0.27 |

Fits converged: #1 True, #2 True.

Stated with it: the music score is AudioSet's generic "Music" (genre is not measurable, D-033); talk comes from the speech-to-text segments, so videos with unclear speech carry run-to-run noise (D-062).

## Part B - EDA 6 completed: the proposal's seven kinds of emotional content (description only, no test)

In the proposal's order. Sentiment uses the sentiment model's own label (5.9; no threshold chosen here); surprise and happiness are the speech emotion labels "surprise" and "joy" (English translation of the speech, 5.9); excitement and humour are the researcher's hand codes (D-049; humour repeat alpha 0.69, excitement not repeat-checked). "Rest" = the other videos that have the same measure. Percentile = engagement ranked within platform and follower tier. Cells under 10 videos are marked thin.

| Kind (proposal) | Measure | Group | Videos | Accounts | Instagram / YouTube | Median percentile | Rest: median (n) | Group without AI-character Shorts: median (n) |
|---|---|---|---|---|---|---|---|---|
| Positive | caption sentiment | positive | 101 | 19 | 72 / 29 | 0.545 | 0.532 (84) | 0.546 (100) |
| Neutral | caption sentiment | neutral | 78 | 15 | 37 / 41 | 0.546 | 0.533 (107) | 0.581 (64) |
| Negative | caption sentiment | negative (thin) | 6 | 4 | 4 / 2 | 0.478 | 0.545 (179) | 0.478 (6) |
| Positive | speech sentiment | positive | 45 | 12 | 29 / 16 | 0.573 | 0.536 (74) | 0.649 (40) |
| Neutral | speech sentiment | neutral | 44 | 14 | 25 / 19 | 0.565 | 0.554 (75) | 0.574 (43) |
| Negative | speech sentiment | negative | 30 | 8 | 13 / 17 | 0.461 | 0.573 (89) | 0.593 (21) |
| Excitement | hand-coded: meant to be exciting | yes | 84 | 16 | 56 / 28 | 0.522 | 0.556 (98) | 0.538 (83) |
| Humour | hand-coded: meant to be funny | yes | 56 | 12 | 39 / 17 | 0.564 | 0.538 (125) | 0.584 (47) |
| Surprise | speech emotion | surprise | 15 | 5 | 6 / 9 | 0.538 | 0.556 (104) | 0.604 (12) |
| Happiness | speech emotion | joy | 25 | 9 | 21 / 4 | 0.683 | 0.542 (94) | 0.698 (24) |

Description only: the registered test of emotional content is H3 (D-043, not detected); no verdict is drawn from this table.

## Part C - the proposal's EDA 8 table: YouTube against Instagram (description only)

**Composition first** (docs/07 section 1b): Instagram 120 videos from 17 accounts, 105 of them hand-picked; YouTube 72 from 5 channels, 58 from one. Platform, selection route and account size cannot be separated (docs/08 section 7.9.3(c)); Zero Sugar label repeat reliability YouTube alpha 0.25, Instagram -0.10. The last two columns answer the proposal's question "does the same marketing strategy work equally well on both platforms?" only as description: the Spearman of the measure with the engagement percentile **within** each platform (n in brackets) - no test.

| Feature (proposal) | Measure | Instagram | YouTube | Spearman with percentile, Instagram | Spearman, YouTube | Same direction on both? |
|---|---|---|---|---|---|---|
| Duration | median seconds | 18.9 | 20.5 | +0.09 (120) | -0.35 (72) | opposite |
| Engagement | median (likes + comments) per follower | 0.280% | 0.0048% | - | - | - |
| Engagement | median (likes + comments) per view | not published (docs/06) | 1.22% | - | - | - |
| Caption length | median characters | 142.5 | 128.5 | -0.06 (120) | +0.17 (72) | opposite |
| Product visibility | can or bottle prominent (hand-coded) | 78% (120) | 60% (72) | +0.05 (120) | +0.28 (72) | same |
| Creator involvement | creator or celebrity (hand-coded, of coded) | 45% (77) | 12% (52) | +0.35 (77) | -0.10 (52) | opposite |
| Creator involvement | collaboration post (platform metadata) | 26% (120) | 0% (brand channels only) | - | - | - |
| Emotional content | caption sentiment positive | 64% (113) | 40% (72) | -0.04 (113) | +0.35 (72) | opposite |
| Emotional content | joy in speech (of videos with speech emotion) | 31% (67) | 8% (52) | +0.03 (67) | +0.08 (52) | same |
| Emotional content | humour (hand-coded) | 34% (116) | 26% (65) | +0.25 (116) | -0.35 (65) | opposite |
| Emotional content | excitement (hand-coded) | 47% (119) | 44% (63) | -0.03 (119) | +0.09 (63) | opposite |

Engagement is not compared through the percentile here: it is ranked within each platform, so its median is about the middle on both by construction (docs/06). The per-follower rate differs about as EDA 8 reported; the inferential answer is H7 (D-043, not detected). The within-platform Spearmans are descriptions of these 192 videos - the profile (D-052) holds the checked version for talking, faces, call to action and hashtags.

Wording (D-063): 'associated with', never 'causes'; a test not detected is 'not detected at this sample size' with its minimum detectable effect (a lower bound: account clustering makes it larger). Parts B and C are description. Nothing here changes the 20 model features, the models or the tool.

# P12 - exploration with the hand codes (D-050)

Focus set 192 videos, 22 accounts. Hand codes from `focus_codes_FINAL.csv` (one coder, 9 Oct; 110 minutes for 100 minutes of video; repeat reliability in `reports/repeat_check.md`). 'Unsure' and blank are missing. Descriptive only - no test, no p-value. The engagement percentile is ranked within platform and follower tier. Zero Sugar label reliability: YouTube alpha 0.25, Instagram -0.10.

## EDA 8 rows - make-up of every new measure by platform (counts, % of the platform's videos)
| Measure | Instagram (120) | YouTube (72) |
|---|---|---|
| product prominent | yes 93 (78%), no 27, missing 0 | yes 43 (60%), no 29, missing 0 |
| logo prominent | yes 89 (74%), no 30, missing 1 | yes 47 (65%), no 25, missing 0 |
| a person appears | yes 91 (76%), no 28, missing 1 | yes 37 (51%), no 35, missing 0 |
| creator or celebrity | yes 35 (29%), no 42, missing 43 | yes 6 (8%), no 46, missing 20 |
| humour | yes 39 (32%), no 77, missing 4 | yes 17 (24%), no 48, missing 7 |
| excitement | yes 56 (47%), no 63, missing 1 | yes 28 (39%), no 35, missing 9 |
| excited voice | yes 30 (25%), no 90, missing 0 | yes 20 (28%), no 51, missing 1 |
| call to action | yes 56 (47%), no 64, missing 0 | yes 32 (44%), no 40, missing 0 |
| sponsored disclosed | yes 25 (21%), no 95, missing 0 | yes 8 (11%), no 63, missing 1 |
| lifestyle focus | yes 71 (59%), no 46, missing 3 | yes 34 (47%), no 36, missing 2 |
| homemade (UGC) look | yes 34 (28%), no 84, missing 2 | yes 6 (8%), no 63, missing 3 |
| people group | missing 43, no person 28, creator 18, celebrity 17, ordinary people 14 | no person 33, missing 20, ordinary people 13, creator 6 |
| music | cinematic 57, no music 27, pop 25, other 9, missing 2 | cinematic 39, no music 18, pop 11, other 3, missing 1 |
| campaign | promotion 39, event 23, new product 20, food 18, general or seasonal 12, missing 8 | event 25, promotion 12, food 12, missing 11, new product 9, general or seasonal 3 |
| voice tone | no voice 63, excited 30, calm 27 | no voice 27, calm 24, excited 20, missing 1 |

Figure: `reports/figures/eda8_codes_by_platform.png`

## EDA 4 - product visibility (can or bottle)
| Group | Videos | Accounts | Instagram / YouTube | Median percentile | Median without AI-character Shorts |
|---|---|---|---|---|---|
| none or brief | 56 | 13 | 27 / 29 | 0.436 | 0.538 (41) |
| prominent | 136 | 21 | 93 / 43 | 0.564 | 0.564 (136) |
| missing (unsure or blank) | 0 | | | nan | |

Figure: `reports/figures/eda4_product_visibility.png`

## EDA 5 - people: none, ordinary people, creator, celebrity
| Group | Videos | Accounts | Instagram / YouTube | Median percentile | Median without AI-character Shorts |
|---|---|---|---|---|---|
| no person | 61 | 12 | 28 / 33 | 0.446 | 0.529 (46) |
| ordinary people | 27 | 9 | 14 / 13 | 0.620 | 0.620 (27) |
| creator | 24 | 5 | 18 / 6 | 0.510 | 0.510 (24) |
| celebrity | 17 | 5 | 17 / 0 | 0.931 | 0.931 (17) |
| missing (unsure or blank) | 63 | | | 0.533 | |

Figure: `reports/figures/eda5_people_groups.png`

## EDA 6 - humour, excitement, voice tone
| Group | Videos | Accounts | Instagram / YouTube | Median percentile | Median without AI-character Shorts |
|---|---|---|---|---|---|
| funny | 56 | 12 | 39 / 17 | 0.564 | 0.584 (47) |
| not funny | 125 | 22 | 77 / 48 | 0.538 | 0.551 (122) |
| missing (unsure or blank) | 11 | | | 0.416 | |

| Group | Videos | Accounts | Instagram / YouTube | Median percentile | Median without AI-character Shorts |
|---|---|---|---|---|---|
| exciting | 84 | 16 | 56 / 28 | 0.522 | 0.538 (83) |
| not exciting | 98 | 20 | 63 / 35 | 0.556 | 0.578 (91) |
| missing (unsure or blank) | 10 | | | 0.147 | |

| Group | Videos | Accounts | Instagram / YouTube | Median percentile | Median without AI-character Shorts |
|---|---|---|---|---|---|
| excited | 50 | 9 | 30 / 20 | 0.568 | 0.568 (50) |
| calm | 51 | 14 | 27 / 24 | 0.444 | 0.588 (36) |
| no voice | 90 | 17 | 63 / 27 | 0.491 | 0.491 (90) |
| missing (unsure or blank) | 1 | | | 0.385 | |

Figure: `reports/figures/eda6_tone.png`

## Music and campaign type (descriptive; not in the models, D-050)
| Group | Videos | Accounts | Instagram / YouTube | Median percentile | Median without AI-character Shorts |
|---|---|---|---|---|---|
| cinematic | 96 | 19 | 57 / 39 | 0.519 | 0.540 (94) |
| no music | 45 | 12 | 27 / 18 | 0.556 | 0.667 (33) |
| pop | 36 | 13 | 25 / 11 | 0.491 | 0.491 (36) |
| other | 12 | 8 | 9 / 3 | 0.588 | 0.588 (12) |
| missing (unsure or blank) | 3 | | | 0.545 | |

| Group | Videos | Accounts | Instagram / YouTube | Median percentile | Median without AI-character Shorts |
|---|---|---|---|---|---|
| promotion | 51 | 17 | 39 / 12 | 0.578 | 0.581 (50) |
| event | 48 | 10 | 23 / 25 | 0.353 | 0.391 (42) |
| food | 30 | 8 | 18 / 12 | 0.678 | 0.678 (30) |
| new product | 29 | 11 | 20 / 9 | 0.663 | 0.663 (29) |
| general or seasonal | 15 | 8 | 12 / 3 | 0.446 | 0.446 (15) |
| missing (unsure or blank) | 19 | | | 0.547 | |

## EDA 9 - each yes/no measure against the engagement percentile (description; no test)
Spearman rho; 'without AI' leaves out the 15 AI-character Shorts. Read as association in this sample only - the tests are P13 (`reports/statistical_results_added.md`).
| Measure | Videos coded | rho | rho without AI | Median pct, yes / no |
|---|---|---|---|---|
| product prominent | 192 | +0.137 | +0.006 | 0.564 / 0.436 |
| logo prominent | 191 | +0.086 | -0.024 | 0.551 / 0.479 |
| a person appears | 191 | +0.159 | +0.046 | 0.560 / 0.455 |
| creator or celebrity | 129 | +0.230 | +0.176 | 0.723 / 0.462 |
| humour | 181 | +0.050 | +0.109 | 0.564 / 0.538 |
| excitement | 182 | +0.011 | -0.012 | 0.522 / 0.556 |
| excited voice | 191 | +0.102 | +0.058 | 0.568 / 0.487 |
| call to action | 192 | +0.289 | +0.237 | 0.662 / 0.444 |
| sponsored disclosed | 191 | +0.051 | +0.018 | 0.556 / 0.503 |
| lifestyle focus | 187 | -0.201 | -0.153 | 0.444 / 0.649 |
| homemade (UGC) look | 187 | +0.065 | +0.034 | 0.555 / 0.495 |

## The two unchecked automated labels against the hand codes (D-038 labels; they stay out of every model)
| Label | Pairs | Raw agreement | Alpha | Hand: product or UGC / Model: product or UGC |
|---|---|---|---|---|
| product_vs_lifestyle | 172 | 59% | 0.15 | 73 / 130 |
| ugc_vs_brand | 173 | 79% | 0.34 | 38 / 30 |


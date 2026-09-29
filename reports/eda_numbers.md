# Exploration numbers (Phase 7)

Frozen analysis table: docs/08 section 6, row dated 2026-09-29. Focus set: n = 192 videos, 22 accounts. No test, p-value or model appears here.

## EDA 1 - distribution of videos
Focus set: n = 192 videos, 22 accounts. Robustness set (usable, not Zero Sugar): n = 98 videos, 11 accounts. All rows: 300.

**Year posted, focus set**
| year | instagram | youtube | total |
|---|---|---|---|
| 2021 | 1 | 3 | 4 |
| 2022 | 4 | 0 | 4 |
| 2023 | 6 | 0 | 6 |
| 2024 | 21 | 3 | 24 |
| 2025 | 32 | 11 | 43 |
| 2026 | 56 | 55 | 111 |
| total | 120 | 72 | 192 |

**How the video entered, focus set**
| selection | instagram | youtube | total |
|---|---|---|---|
| hand_picked | 105 | 0 | 105 |
| systematic | 15 | 72 | 87 |
| total | 120 | 72 | 192 |

**Follower tier, focus set**
| account_size_tier | instagram | youtube | total |
|---|---|---|---|
| large | 37 | 58 | 95 |
| medium | 59 | 10 | 69 |
| small | 24 | 4 | 28 |
| total | 120 | 72 | 192 |

**Region, focus set**
| region | instagram | youtube | total |
|---|---|---|---|
| Brazil | 8 | 4 | 12 |
| LatAm | 17 | 3 | 20 |
| MENA | 0 | 2 | 2 |
| North America & Global | 19 | 58 | 77 |
| Other | 27 | 0 | 27 |
| SE Asia | 16 | 5 | 21 |
| South Asia | 26 | 0 | 26 |
| Turkiye & Central Asia | 7 | 0 | 7 |
| total | 120 | 72 | 192 |

**Caption language, focus set**
| lang_caption | instagram | youtube |
|---|---|---|
| en | 63 | 44 |
| es | 16 | 3 |
| pt | 8 | 6 |
| ko | 14 | 0 |
| vi | 0 | 8 |
| unknown | 7 | 0 |
| tr | 7 | 0 |
| th | 1 | 5 |
| bn | 0 | 4 |
| id | 2 | 0 |
| ar | 0 | 2 |
| hr | 1 | 0 |
| it | 1 | 0 |

Figure: `reports/figures/eda1_composition.png`

## EDA 2 - engagement distribution
Follower-normalised engagement rate, focus set: median 0.0013, IQR 0.0001-0.0121, max 7.207, skewness raw 9.51 vs log10 0.15; zero rates: 0.
Percentile (the modelling DV): median 0.529, mean 0.521.
**Median split in the focus set (docs/06 section 4 fallback rule): 100 high / 92 low = 52% / 48%.** Rule: worse than 60/40 -> use the focus set's own median. Not triggered.

Figure: `reports/figures/eda2_engagement_distribution.png`

## EDA 3 - video duration
| platform | count | mean | std | min | 10% | 50% | 90% | max |
|---|---|---|---|---|---|---|---|---|
| instagram | 120.0 | 32.3 | 31.2 | 3.9 | 6.1 | 18.9 | 69.2 | 177.8 |
| youtube | 72.0 | 29.2 | 24.0 | 6.1 | 6.5 | 20.5 | 60.1 | 115.4 |

Spearman duration vs percentile, focus set (descriptive only): -0.05.

Figure: `reports/figures/eda3_duration.png`

## EDA 4 - product visibility: not drawn (D-037, not measured)

## EDA 5 - human presence
Celebrity and creator labels failed alpha (D-038), so presence is measured by faces only.
| faces | instagram | youtube | accounts | median percentile |
|---|---|---|---|---|
| no face | 16 | 6 | 12 | 0.522 |
| face in up to half | 47 | 32 | 16 | 0.475 |
| face in most frames | 57 | 34 | 17 | 0.573 |

**Instagram only - creator collaboration (from post metadata, 5.15)**
| creator_collab | size | median |
|---|---|---|
| False | 89 | 0.455 |
| True | 31 | 0.644 |

Figure: `reports/figures/eda5_human_presence.png`

## EDA 6 - emotional content
Emotion label exists only where there is speech, post-translation (D-031): n = 119 videos, 17 accounts.
| emotion_label | size | median | accounts |
|---|---|---|---|
| neutral | 67 | 0.515 | 16 |
| joy | 25 | 0.683 | 9 |
| surprise | 15 | 0.538 | 5 |
| disgust | 5 | 0.556 | 3 |
| fear | 3 | 0.795 | 1 |
| anger | 2 | 0.335 | 2 |
| sadness | 2 | 0.876 | 1 |

Caption sentiment available for 185 focus videos; Spearman with percentile 0.06 (descriptive). Reminder (D-031): sentiment shrinks with text length.
Spearman caption sentiment vs caption length, focus set: -0.03.

Figure: `reports/figures/eda6_emotion.png`

## EDA 7 - caption and text
| platform | caption_char_len | hashtag_count | emoji_count | ocr_region_count |
|---|---|---|---|---|
| instagram | 142.5 | 2.0 | 1.0 | 3.1 |
| youtube | 128.5 | 2.0 | 1.0 | 4.0 |

**kw_event**
| k | size | median |
|---|---|---|
| no | 137 | 0.573 |
| yes | 46 | 0.425 |

**kw_promotional**
| k | size | median |
|---|---|---|
| no | 153 | 0.545 |
| yes | 30 | 0.486 |

Figure: `reports/figures/eda7_text.png`

## EDA 8 - YouTube vs Instagram (docs/07 section 1b; descriptive, no test)
### 1. Composition - before any engagement value
| platform | selection | videos | accounts | thin (<20 videos or <3 accounts) |
|---|---|---|---|---|
| instagram | hand_picked | 105 | 13 | False |
| instagram | systematic | 15 | 9 | True |
| youtube | systematic | 72 | 5 | False |

| platform | account_size_tier | videos | accounts | thin (<20 videos or <3 accounts) |
|---|---|---|---|---|
| instagram | large | 37 | 4 | False |
| instagram | medium | 59 | 8 | False |
| instagram | small | 24 | 11 | False |
| youtube | large | 58 | 1 | True |
| youtube | medium | 10 | 3 | True |
| youtube | small | 4 | 1 | True |

YouTube: 58 of 72 videos come from one channel (Coca-Cola).

### 2. How each Zero Sugar label was decided
| zs_label_method | instagram | youtube | total |
|---|---|---|---|
| researcher_curated | 105 | 0 | 105 |
| researcher_visual_check | 9 | 47 | 56 |
| text | 6 | 25 | 31 |
| total | 120 | 72 | 192 |

By-eye label repeat reliability: YouTube 16 of 25, alpha 0.25 (D-029); Instagram 4 of 9, alpha -0.10 (D-039). The label decides inclusion (D-030).

### 3. Engagement by platform (descriptive)
| platform | count | mean | std | min | 25% | 50% | 75% | max |
|---|---|---|---|---|---|---|---|---|
| instagram | 120.0 | -2.329 | 1.123 | -4.973 | -2.993 | -2.554 | -1.649 | 0.858 |
| youtube | 72.0 | -4.036 | 1.218 | -5.984 | -4.751 | -4.318 | -3.577 | -0.594 |

| platform | selection | size | median |
|---|---|---|---|
| instagram | hand_picked | 105 | -2.447 |
| instagram | systematic | 15 | -2.847 |
| youtube | systematic | 72 | -4.318 |

Figure: `reports/figures/eda8_platform_descriptive.png`

## EDA 9 / Diagnostic C - correlation among the 20 features, and VIF
Pairs with |Spearman| >= 0.5: 5; max 0.72.
- `colourfulness` - `red_ratio`: 0.72
- `ocr_region_count` - `ocr_mean_text_area`: 0.68
- `cuts_per_sec` - `motion_px_per_sec`: 0.59
- `duration_sec` - `talk_dur_frac`: 0.55
- `loudness_db_mean` - `loudness_range_db`: -0.52

VIF (median-imputed for this diagnostic only): max 3.64 (`colourfulness`); above 5: 0; above 10: 0.
| index | VIF |
|---|---|
| colourfulness | 3.64 |
| red_ratio | 2.77 |
| ocr_mean_text_area | 2.07 |
| talk_dur_frac | 1.98 |
| loudness_range_db | 1.68 |
| loudness_db_mean | 1.68 |
| face_present_frac | 1.64 |
| ocr_region_count | 1.63 |
| duration_sec | 1.56 |
| music_frac | 1.54 |
| kw_event | 1.53 |
| caption_char_len | 1.44 |
| motion_px_per_sec | 1.41 |
| emoji_count | 1.37 |
| mean_face_area | 1.33 |
| edge_density | 1.27 |
| kw_promotional | 1.26 |
| sentiment_caption | 1.26 |
| hashtag_count | 1.17 |
| cuts_per_sec | 1.16 |

Figure: `reports/figures/eda9_feature_correlation.png`

## Diagnostic A - videos per account
22 accounts. Largest: Coca-Cola (youtube) with 58 videos = 30% of the focus set. Accounts with 1 video: 5.

| account | platform | videos |
|---|---|---|
| Coca-Cola | youtube | 58 |
| cocacola_india | instagram | 26 |
| cocacola | instagram | 19 |
| cocacola_korea | instagram | 15 |
| cocacolaeurope | instagram | 9 |
| cocacola_cl | instagram | 9 |
| cocacola_br | instagram | 8 |
| cocacola_tr | instagram | 7 |
| cocacolasg | instagram | 6 |
| Coca-Cola Thailand | youtube | 5 |
| cocacola_id | instagram | 5 |
| cocacola_costarica | instagram | 4 |
| Coca-Cola Brasil | youtube | 4 |
| cocacolamy | instagram | 4 |
| cocacola_kenya | instagram | 3 |
| Industria Mexicana de Coca-Cola | youtube | 3 |
| Coca-Cola Middle East | youtube | 2 |
| cocacola_elsalvador | instagram | 1 |
| cocacolabol | instagram | 1 |
| cocacola_th | instagram | 1 |
| cocacola_panama | instagram | 1 |
| cocacolacol | instagram | 1 |

Figure: `reports/figures/diagA_videos_per_account.png`

## Diagnostic B - engagement vs video age
Age range 8-2021 days (median 202). Spearman age vs log10 rate 0.44; vs percentile 0.20 (descriptive).

Figure: `reports/figures/diagB_age.png`

## Diagnostic D - missingness
Missing share in the focus set (non-zero only):
| index | missing |
|---|---|
| engagement_rate_view | 0.625 |
| mean_face_area | 0.115 |
| kw_event | 0.047 |
| kw_promotional | 0.047 |
| sentiment_caption | 0.036 |
| loudness_db_mean | 0.01 |
| loudness_range_db | 0.01 |
| motion_px_per_sec | 0.005 |

All rows: dv_status counts {'ok': 290, 'excluded_likes_hidden': 5, 'excluded_comments_disabled': 5}.

Figure: `reports/figures/diagD_missingness.png`

## Diagnostic E - sampling balance by platform
**selection, share of each platform's focus videos**
| selection | instagram | youtube |
|---|---|---|
| hand_picked | 0.875 | 0.0 |
| systematic | 0.125 | 1.0 |

**account_type, share of each platform's focus videos**
| account_type | instagram | youtube |
|---|---|---|
| brand channel (YouTube) | 0.0 | 1.0 |
| brand_global | 0.158 | 0.0 |
| brand_market | 0.767 | 0.0 |
| brand_region | 0.075 | 0.0 |

**account_size_tier, share of each platform's focus videos**
| account_size_tier | instagram | youtube |
|---|---|---|
| large | 0.308 | 0.806 |
| medium | 0.492 | 0.139 |
| small | 0.2 | 0.056 |

Every YouTube Short is posted by a brand channel; Instagram adds creator posts through collaborations (31 focus Reels flagged `creator_collab`).

## Diagnostic F - cross-posted pairs (the same video on both platforms)
Rule (fixed before looking): mean CLIP frame embedding cosine >= 0.95 and durations within 1 s; one-to-one. **2 candidate pairs in the focus set** (the paired sub-analysis needs >= 20, docs/08 section 2).
Sensitivity: with cosine >= 0.90, 6 YouTube Shorts have some Instagram match.

| youtube | instagram | similarity | yt_sec | ig_sec |
|---|---|---|---|---|
| IUf3c7Tgcr0 | DclLDcxk6Tq | 0.998 | 60.07 | 60.012 |
| ZLe_Dkhufro | DXotPv2iDtE | 0.988 | 32.369 | 32.32 |

## Diagnostic G - market x platform
| market | instagram | youtube | accounts |
|---|---|---|---|
| Global/US | 19 | 58 | 2 |
| Thailand | 1 | 5 | 2 |
| Brazil | 8 | 4 | 2 |
| LatAm/Mexico | 0 | 3 | 1 |
| MENA | 0 | 2 | 1 |
| India | 26 | 0 | 1 |
| South Korea | 15 | 0 | 1 |
| Chile | 9 | 0 | 1 |
| Europe | 9 | 0 | 1 |
| Turkiye | 7 | 0 | 1 |
| Singapore | 6 | 0 | 1 |
| Indonesia | 5 | 0 | 1 |
| Costa Rica | 4 | 0 | 1 |
| Malaysia | 4 | 0 | 1 |
| Kenya | 3 | 0 | 1 |
| Bolivia | 1 | 0 | 1 |
| Colombia | 1 | 0 | 1 |
| El Salvador | 1 | 0 | 1 |
| Panama | 1 | 0 | 1 |

Markets on both platforms: 3 of 19.

## Decision input (TODO 7.2) - the scale of `cuts_per_sec`
All 300: max 9.68, next 1.78, 99th pct 1.47; skewness raw 10.22, log1p 1.73. In the focus set the max is 9.68.


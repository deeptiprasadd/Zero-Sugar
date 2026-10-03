# Phase 8 - statistical results (D-042, docs/08 section 7.9)

Focus set: 192 videos, 22 accounts; complete cases for the H1-H6/H8 models: 179 videos, 19 accounts. Specification fixed before any test (D-042). Every result rests on the Zero Sugar inclusion label, whose repeat reliability is weak: YouTube 16 of 25, alpha 0.25; Instagram 4 of 9, alpha -0.10.

## H1 - duration
LR test, duration + duration^2 added to controls: chi2 = 2.15, df 2, p = 0.341 (n = 179, ML fits converged: True).
| Term | Coef (pct points per SD) | 95% CI | Std beta | p |
|---|---|---|---|---|
| `duration_z` | -0.011 | -0.075 to +0.053 | -0.04 | 0.736 |
| `duration2` | +0.015 | -0.009 to +0.038 | +0.05 | 0.219 |

Spearman, pooled: rho = -0.045 (95% CI -0.19 to 0.10), p = 0.533, n = 192.

Per platform (description, outside the family):
- youtube: rho = -0.353 (95% CI -0.54 to -0.13), n = 72, 5 accounts.
- instagram: rho = 0.091 (95% CI -0.09 to 0.27), n = 120, 17 accounts.

## H2 - product visibility: not tested (not measured, D-037)

## H3 - positive emotional content
MixedLM, caption sentiment (n = 179, converged: True):
| Term | Coef (pct points per SD) | 95% CI | Std beta | p |
|---|---|---|---|---|
| `sent_z` | +0.028 | -0.013 to +0.070 | +0.10 | 0.178 |

Kruskal-Wallis across collapsed speech emotion (n = 119, 17 accounts): H = 0.67, df 3, p = 0.881, epsilon^2 = 0.006.
| Emotion | Videos | Median percentile |
|---|---|---|
| joy | 25 | 0.683 |
| neutral | 67 | 0.515 |
| other | 12 | 0.600 |
| surprise | 15 | 0.538 |

## H4 - people on screen (faces only; celebrity / creator not measured, D-038)
LR test, face share + face size added to controls: chi2 = 2.31, df 2, p = 0.316 (n = 179, converged: True).
| Term | Coef (pct points per SD) | 95% CI | Std beta | p |
|---|---|---|---|---|
| `face_present_z` | -0.031 | -0.070 to +0.008 | -0.11 | 0.120 |
| `face_area_z` | +0.002 | -0.037 to +0.042 | +0.01 | 0.911 |

Mann-Whitney U, any face (170) vs none (22): U = 1936, p = 0.788, rank-biserial r = +0.036 (positive = higher with a face); medians 0.529 vs 0.522.

## H5 - call to action: not tested (no validated instrument, D-038)

## H6 - text characteristics
LR test, text block (caplen_z, hashtag_z, emoji_z, kw_event_i, kw_promo_i) added to controls: chi2 = 12.59, df 5, p = 0.028 (n = 179, converged: True).
| Term | Coef (pct points per SD, or yes vs no) | 95% CI | Std beta | p |
|---|---|---|---|---|
| `caplen_z` | -0.023 | -0.078 to +0.033 | -0.08 | 0.428 |
| `hashtag_z` | +0.052 | -0.000 to +0.103 | +0.18 | 0.050 |
| `emoji_z` | +0.021 | -0.028 to +0.070 | +0.07 | 0.400 |
| `kw_event_i` | -0.138 | -0.245 to -0.031 | -0.48 | 0.012 |
| `kw_promo_i` | -0.023 | -0.134 to +0.088 | -0.08 | 0.687 |

Spearman, caption length: rho = -0.001 (95% CI -0.14 to 0.14), p = 0.984, n = 192.

Spearman, hashtags: rho = 0.244 (95% CI 0.11 to 0.37), p = <0.001, n = 192.

## H7 - platform (docs/08 section 7.9, as registered)
Composition: instagram 120 videos / 17 accounts; youtube 72 videos / 5 accounts. Videos per account: Coca-Cola 58, cocacola_india 26, cocacola 19, cocacola_korea 15, cocacola_cl 9, cocacolaeurope 9, cocacola_br 8, cocacola_tr 7, cocacolasg 6, Coca-Cola Thailand 5, cocacola_id 5, Coca-Cola Brasil 4, cocacolamy 4, cocacola_costarica 4, Industria Mexicana de Coca-Cola 3, cocacola_kenya 3, Coca-Cola Middle East 2, cocacola_th 1, cocacolabol 1, cocacolacol 1, cocacola_elsalvador 1, cocacola_panama 1.

**(a) Main model** (`log10_er ~ C(platform, Treatment('youtube')) + C(tier2) + log_age + (1 | account)`, REML, n = 192, converged: True): platform coefficient (Instagram minus YouTube) **+0.470** log10 units, 95% CI -0.297 to +1.238, p = 0.230; ratio of engagement rates **10^beta = 3.0** (95% CI 0.5 to 17.3). Account variance 0.407, residual 0.670, **ICC 0.38**.
| Term | Coef | 95% CI | p |
|---|---|---|---|
| `Intercept` | -4.217 | -5.304 to -3.131 | <0.001 |
| `C(platform, Treatment('youtube'))[T.instagram]` | +0.470 | -0.297 to +1.238 | 0.230 |
| `C(tier2)[T.small_medium]` | +1.006 | +0.398 to +1.614 | 0.001 |
| `log_age` | +0.237 | -0.044 to +0.518 | 0.098 |

**(a2) Account medians** (17 Instagram vs 5 YouTube accounts): median of account medians -2.66 vs -3.05; Mann-Whitney U = 49, p = 0.649 (descriptive, weak by construction).

**(b) Follower tier - descriptive only** (median log10 rate, account-clustered bootstrap 95% CI):
| Platform | Tier | Videos | Accounts | Median | 95% CI |
|---|---|---|---|---|---|
| instagram | large | 37 | 4 | -2.88 | -4.17 to -2.62 |
| youtube | large | 58 | 1 | -4.48 | single account - no interval |
| difference (IG - YT) | large | | | +1.60 | +0.31 to +1.86 |
| instagram | small_medium | 83 | 15 | -2.22 | -2.78 to -1.65 |
| youtube | small_medium | 14 | 4 | -1.93 | -3.23 to -1.25 |
| difference (IG - YT) | small_medium | | | -0.29 | -1.29 to +1.34 |

**(c) Within Instagram, hand-picked vs systematic - descriptive, no test** (the selection re-run itself cannot be performed: 15 systematic videos < 20, D-039):
- hand_picked: 105 videos / 13 accounts, median -2.45 (95% CI -2.85 to -1.76)
- systematic: 15 videos / 9 accounts, median -2.85 (95% CI -3.51 to -2.74)
**The platform coefficient in (a) cannot be separated from the difference in how the two samples were built** - every hand-picked video is an Instagram Reel (7.9.3(c)).

**(d) Without the global channel (Coca-Cola)** - YouTube 14 videos / 4 accounts: coefficient -0.011 (95% CI -0.924 to +0.902), ratio 1.0, converged: True.

**Verdict by 7.9.4: Not detected.** (a) CI excludes 0: False; any sign reversal in (a2), (d) or the tier differences: True; an interval in (d) or the tier differences includes 0: True.

**Robustness, wider set (7.5(a), all 290 usable videos, 26 accounts, with `is_zero_sugar`):** platform coefficient +0.507 (95% CI -0.159 to +1.173), ratio 3.2, converged: True.

## H8 - do the content blocks jointly add to the controls?
LR test, all 20 content features added to controls: chi2 = 28.36, df 20, p = 0.101 (n = 179, converged: True).
- video block (10 features): chi2 = 11.06, df 10, p = 0.353
- audio block (4 features): chi2 = 6.58, df 4, p = 0.160
- text block (6 features): chi2 = 13.80, df 6, p = 0.032

Full model (REML, n = 179, converged: True, ICC 0.30):
| Term | Coef (pct points per SD, or yes vs no) | 95% CI | Std beta | p (unadjusted, descriptive) |
|---|---|---|---|---|
| `log_followers` | -0.018 | -0.118 to +0.082 | -0.06 | 0.721 |
| `log_age` | +0.033 | -0.072 to +0.138 | +0.11 | 0.542 |
| `C(platform, Treatment('youtube'))[T.instagram]` | -0.147 | -0.385 to +0.091 | -0.51 | 0.227 |
| `duration_z` | +0.039 | -0.018 to +0.095 | +0.13 | 0.182 |
| `cuts_z` | -0.003 | -0.054 to +0.048 | -0.01 | 0.907 |
| `motion_z` | -0.012 | -0.066 to +0.041 | -0.04 | 0.649 |
| `face_present_z` | -0.006 | -0.055 to +0.042 | -0.02 | 0.802 |
| `face_area_z` | +0.001 | -0.046 to +0.049 | +0.00 | 0.952 |
| `edge_z` | +0.005 | -0.040 to +0.049 | +0.02 | 0.840 |
| `colour_z` | +0.051 | -0.024 to +0.127 | +0.18 | 0.183 |
| `red_z` | -0.009 | -0.078 to +0.059 | -0.03 | 0.788 |
| `ocr_regions_z` | +0.008 | -0.044 to +0.060 | +0.03 | 0.762 |
| `ocr_area_z` | -0.055 | -0.116 to +0.006 | -0.19 | 0.078 |
| `music_z` | +0.003 | -0.045 to +0.051 | +0.01 | 0.903 |
| `talk_z` | -0.033 | -0.092 to +0.026 | -0.11 | 0.273 |
| `loud_z` | +0.043 | -0.008 to +0.095 | +0.15 | 0.097 |
| `loud_range_z` | +0.038 | -0.014 to +0.089 | +0.13 | 0.150 |
| `sent_z` | +0.016 | -0.027 to +0.060 | +0.06 | 0.464 |
| `caplen_z` | -0.049 | -0.112 to +0.014 | -0.17 | 0.130 |
| `hashtag_z` | +0.048 | -0.005 to +0.101 | +0.17 | 0.075 |
| `emoji_z` | +0.021 | -0.031 to +0.073 | +0.07 | 0.436 |
| `kw_event_i` | -0.124 | -0.251 to +0.003 | -0.43 | 0.056 |
| `kw_promo_i` | -0.024 | -0.144 to +0.096 | -0.08 | 0.699 |

## H9 and H10 - exploratory (estimates with 95% intervals; outside the family; never 'significant')
H9: each feature's slope difference, Instagram minus YouTube (one model per feature: controls + feature + feature x platform).
| Feature | Interaction coef (pct points per SD) | 95% CI | Interval excludes 0 |
|---|---|---|---|
| `duration_z` | +0.098 | -0.012 to +0.207 | no |
| `cuts_z` | -0.063 | -0.148 to +0.023 | no |
| `motion_z` | -0.150 | -0.250 to -0.050 | yes |
| `face_present_z` | +0.172 | +0.097 to +0.247 | yes |
| `face_area_z` | -0.061 | -0.143 to +0.021 | no |
| `edge_z` | +0.005 | -0.085 to +0.096 | no |
| `colour_z` | -0.161 | -0.252 to -0.071 | yes |
| `red_z` | -0.078 | -0.163 to +0.006 | no |
| `ocr_regions_z` | +0.051 | -0.037 to +0.139 | no |
| `ocr_area_z` | +0.165 | +0.041 to +0.289 | yes |
| `music_z` | -0.031 | -0.115 to +0.053 | no |
| `talk_z` | +0.141 | +0.055 to +0.228 | yes |
| `loud_z` | -0.076 | -0.159 to +0.007 | no |
| `loud_range_z` | +0.033 | -0.053 to +0.120 | no |
| `sent_z` | -0.087 | -0.172 to -0.002 | yes |
| `caplen_z` | -0.093 | -0.184 to -0.002 | yes |
| `hashtag_z` | -0.023 | -0.118 to +0.071 | no |
| `emoji_z` | -0.043 | -0.129 to +0.044 | no |
| `kw_event_i` | +0.231 | +0.039 to +0.423 | yes |
| `kw_promo_i` | +0.017 | -0.209 to +0.242 | no |

H10, duration x platform: +0.098 percentile points per SD (95% CI -0.012 to +0.207), converged: True. Exploratory; with 72 YouTube videos from 5 accounts the interval is the result.
The 'restricted to systematic selection' variant of 7.7 cannot be run (15 systematic Instagram videos); stated, not replaced.

## Assumption checks (docs/08 section 5)
- Full H8 model residuals: Shapiro-Wilk W = 0.990, p = 0.242; skew 0.03, kurtosis -0.15. The percentile is bounded 0-1, so departures are expected; each H1-H6 conclusion is read against its rank-based test (D-042).
- Account ICC (full H8 model): 0.299. Accounts differ; the random intercept stays.
- Spread of residuals vs fitted values: Spearman -0.06 (p = 0.407).
- Multicollinearity: VIF max 3.6 on the 20 features (D-040).

## Sensitivity - median imputation on all 192 videos (D-042)
- H1: chi2 = 3.17, df 2, p = 0.204 (n = 192)
- H4: chi2 = 1.35, df 2, p = 0.508 (n = 192)
- H6: chi2 = 11.73, df 5, p = 0.039 (n = 192)
- H8: chi2 = 32.16, df 20, p = 0.042 (n = 192)
- H3 caption sentiment: coef +0.028, p = 0.162 (n = 192)

## The confirmatory family - Benjamini-Hochberg, q = 0.05
| H | Test | n | Effect | Raw p | BH-adjusted p | Result |
|---|---|---|---|---|---|---|
| H1 | LR duration + duration^2 | 179 | chi2 2.15 (df 2) | 0.341 | 0.494 | not detected at this sample size |
| H1 | Spearman duration, pooled | 192 | rho -0.045 | 0.533 | 0.678 | not detected at this sample size |
| H3 | MixedLM caption sentiment | 179 | beta +0.10 | 0.178 | 0.415 | not detected at this sample size |
| H3 | Kruskal-Wallis speech emotion | 119 | eps2 0.006 | 0.881 | 0.949 | not detected at this sample size |
| H4 | LR face share + face size | 179 | chi2 2.31 (df 2) | 0.316 | 0.494 | not detected at this sample size |
| H4 | Mann-Whitney any face vs none | 192 | r_rb +0.036 | 0.788 | 0.919 | not detected at this sample size |
| H6 | LR text block | 179 | chi2 12.59 (df 5) | 0.028 | 0.149 | not detected at this sample size |
| H6 | Spearman caption length | 192 | rho -0.001 | 0.984 | 0.984 | not detected at this sample size |
| H6 | Spearman hashtags | 192 | rho 0.244 | <0.001 | 0.009 | detected |
| H7 | 7.9.3(a) platform coefficient | 192 | 10^b 3.0 | 0.230 | 0.459 | not detected at this sample size |
| H8 | LR all 20 features | 179 | chi2 28.36 (df 20) | 0.101 | 0.354 | not detected at this sample size |
| H8 | LR video block | 179 | chi2 11.06 (df 10) | 0.353 | 0.494 | not detected at this sample size |
| H8 | LR audio block | 179 | chi2 6.58 (df 4) | 0.160 | 0.415 | not detected at this sample size |
| H8 | LR text block | 179 | chi2 13.80 (df 6) | 0.032 | 0.149 | not detected at this sample size |

H7 verdict (7.9.4): **Not detected** - with the selection caveat stated every time.

### Reading the one detected result - hashtags (descriptive check, changes no verdict)
Account-clustered bootstrap 95% CI for the pooled rho: 0.05 to 0.44. **Within accounts** (each account's mean removed): rho = 0.022, p = 0.765. In the mixed model, which holds accounts apart, the hashtag coefficient is similar in size but its interval reaches 0 (H6 table). **So the association is between accounts - accounts that use more hashtags rank higher - not evidence that adding hashtags to a video raises its engagement.** 13 videos carry 6 or more hashtags.

## Notes
- Zero engagement rates replaced before the log: 0.
- Caption length standardised within language for: ['en', 'es', 'ko', 'pt', 'th', 'tr', 'vi']; other languages and unknown against the whole focus set.
- Complete cases cover 179 videos from 19 of the 22 accounts (accounts with a gap in every video drop out).
- Optimiser used per fit (highest finite likelihood among powell / lbfgs / bfgs / nm / cg): powell 52.

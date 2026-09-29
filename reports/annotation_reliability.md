# 4.2 annotation reliability - researcher vs model (D-038)

Researcher's 60 blind codes (`manual_codes_FINAL.csv`, read only) against the 5.12 automated labels. **Primary: the 50 coded videos the pilot did not use.** Nominal Krippendorff's alpha; 'unsure' on either side is missing; 95% interval from 2,000 bootstrap resamples. Rule fixed before any model ran: keep only if alpha >= 0.67 and the model said 'unsure' on at most 20% of videos.

## Primary (held-out videos)

| Construct | Pairs | Agreement | Alpha | 95% CI | Researcher yes | Model yes | Unsure (researcher / model) | Kept? |
|---|---|---|---|---|---|---|---|---|
| `has_celebrity` | 41 | 80% | **0.100** | -0.16 to 0.48 | 9 | 1 | 5 / 0 | no - dropped |
| `has_influencer` | 39 | 77% | **0.382** | 0.03 to 0.69 | 30 | 29 | 7 / 0 | no - dropped |
| `has_cta` | 46 | 48% | **-0.032** | -0.33 to 0.23 | 11 | 35 | 0 / 0 | no - dropped |
| `humour_present` | 7 | 57% | **0.133** | -0.62 to 0.71 | 3 | 6 | 15 / 38 | no - dropped |

## All 60 coded videos (including the 10 pilot videos)

| Construct | Pairs | Agreement | Alpha | 95% CI |
|---|---|---|---|---|
| `has_celebrity` | 49 | 84% | 0.118 | -0.13 to 0.49 |
| `has_influencer` | 46 | 74% | 0.364 | 0.04 to 0.64 |
| `has_cta` | 54 | 48% | -0.033 | -0.31 to 0.23 |
| `humour_present` | 10 | 50% | -0.044 | -0.58 to 0.42 |

Alpha corrects agreement for chance. When one answer dominates - most videos have no celebrity - high raw agreement can sit beside a low alpha, because agreeing on 'no' is what chance alone would produce.

The three constructs without a manual check (`product_vs_lifestyle`, `ugc_vs_brand`, `promotional_language`) have no alpha and are reported only as unvalidated automated labels (D-023, D-038). They do not enter any model.

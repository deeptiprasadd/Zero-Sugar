# P17 - the effective-video profile (D-052; proposal Objective 15)

An empirical profile, not a recommendation. Engagement is ranked within platform and follower tier, so the profile says nothing about reach; follower count matters for real reach and is not in it. Every measure with evidence is listed with the checks fixed before its result was known (D-047, D-050). Zero Sugar label reliability: YouTube alpha 0.25, Instagram -0.10. Hand codes: one coder, about one video per 30 seconds.

## The profile in one line

Among these Coca-Cola Zero Sugar short videos, **on Instagram** videos with more talking and more frames showing a face were associated with higher engagement (model-based, exploratory); **on both platforms pooled**, videos with a call to action were associated with higher engagement (statistics; measure weakly reliable). Only items that pass every check that applies to them are named here; the table shows the rest.

## Every item with evidence

| Measure | Evidence | Within accounts | Without the 15 AI-character Shorts | Measurement | In the one-line profile |
|---|---|---|---|---|---|
| hashtags | model (Instagram): stable in the Instagram logistic model (top 5 in 15/15); Instagram XGBoost agrees; statistics: H6, Spearman rho +0.244, BH p 0.009 (D-043) | rho +0.02 (p 0.765) - between accounts | rho +0.21 (p 0.005) - survives | automated count (exact) | no |
| share of the video with talking | model (Instagram): stable in the Instagram logistic model (top 5 in 14/15); Instagram XGBoost agrees | not tested (no detected test) | - | automated (speech model) | **yes** |
| share of frames with a face | model (Instagram): stable in the Instagram logistic model (top 5 in 12/15); Instagram XGBoost agrees | not tested (no detected test) | - | automated (face detector) | **yes** |
| a call to action | statistics: H5, +11.0 pct points, BH p 0.014 (LR) / <0.001 (rank) (D-051) | rho +0.19 (p 0.009) - holds | 0.154 / 0.002 (LR / rank) - survives | hand-coded; repeat alpha 0.50 (weakly reliable) | **yes** |
| a can or bottle shown prominently | statistics: H2, +10.4 pct points, BH p 0.021 (LR) / 0.059 (rank) (D-051) | rho +0.18 (p 0.012) - holds | 0.680 / 0.935 (LR / rank) - does not survive | hand-coded; repeat alpha 0.48 (weakly reliable) | no |
| a creator or celebrity | statistics: H4, +14.3 pct points, BH p 0.014 (LR) / 0.014 (rank) (D-051) | rho +0.09 (p 0.305) - between accounts | 0.081 / 0.062 (LR / rank) - does not survive | hand-coded; repeat alpha 0.38 / 0.52 (weakly reliable) | no |

Reading: hashtags pass the model checks but are associated with engagement only *between* accounts - they describe accounts that use more hashtags, not a lever for one video. Product prominence and creator or celebrity presence depend on one 15-video AI-character series.

## Instagram and YouTube side by side (description, no test)

High- vs low-engagement videos within each platform (shares for yes/no measures, means for hashtags, medians for shares of the video). YouTube: 72 videos from 5 channels, 58 from one - read its column as a description of mostly one channel.

| Measure | Instagram: high vs low | YouTube: high vs low | YouTube direction |
|---|---|---|---|
| hashtags | mean 3.0 vs 1.6 | mean 1.9 vs 1.5 | same |
| share of the video with talking | median 0.25 vs 0.00 | median 0.00 vs 0.65 | opposite |
| share of frames with a face | median 0.58 vs 0.33 | median 0.40 vs 0.73 | opposite |
| a call to action | 51% vs 42% | 62% vs 24% | same |
| a can or bottle shown prominently | 82% vs 73% | 67% vs 52% | same |
| a creator or celebrity | 60% vs 29% | 8% vs 15% | opposite |

## Where the Instagram model's contribution changes sign (the threshold column of docs/10 section 5)

The logistic model has no cut-off of its own; its contribution turns positive above the training average:

| Measure | Instagram average (120 videos) |
|---|---|
| hashtags | 2.29 |
| share of the video with talking | 0.292 |
| share of frames with a face | 0.467 |

No YouTube profile is model-based: no YouTube model can be tested fairly (D-041).

# Tasks 12.1-12.2 - the tool's models and their release checks (D-053)

Implements D-046: an honest base rate per platform and an exploratory Instagram content score. Gates fixed in D-053 before anything was fitted. G1 failed on 2 October (D-045) and is reported as such.

## 1. Base rate - engagement rate for a typical video from a new account
Mixed model `log10(rate) ~ platform + log10(followers)`, account intercept, 192 videos, 22 accounts (converged: True). Account variance 0.584, residual 0.677 (log10 units): 46% of the unexplained variation is between accounts.

**G3 - 80% interval coverage on account-grouped folds (576 test predictions, 5 x 3 folds):** overall 67%, Instagram 79%, YouTube 49% -> **FAIL** (rule: 70-90% overall and on each platform). Interval widened by x1.26, the factor that gives 80% overall on the same folds (D-053). After widening: overall 80%, Instagram 86%, YouTube 69% - **YouTube still under 70%: its interval is shown with a warning that it is too narrow for YouTube** (D-053).

What the tool would show (80% interval for a new account's typical video; rate = likes + comments per follower):
| Platform | Followers | Typical rate | 80% interval | Likes + comments, 80% range |
|---|---|---|---|---|
| instagram | 50,000 | 0.56% | 0.008% to 39.62% | 4 to 19,808 |
| instagram | 500,000 | 0.26% | 0.004% to 18.36% | 19 to 91,821 |
| instagram | 5,000,000 | 0.12% | 0.002% to 9.44% | 82 to 471,863 |
| youtube | 50,000 | 0.25% | 0.003% to 20.81% | 1 to 10,406 |
| youtube | 500,000 | 0.12% | 0.001% to 9.67% | 7 to 48,340 |
| youtube | 5,000,000 | 0.06% | 0.001% to 4.96% | 31 to 248,002 |

The interval is wide because 46% of the unexplained variation belongs to the account, which the tool cannot know for a new account. The engagement percentile is not modelled: it is ranked within platform and follower tier, so a typical video sits at the middle by construction (D-053).

## 2. Instagram content score (exploratory) - calibration, G2
Out-of-fold probabilities of the registered Instagram logistic M1, all 3 repeats (360 predictions; fold models rebuilt from the logged settings, ROC-AUCs reproduced exactly). Ten equal-count bins; G2 passes if every bin is within 0.10 of its mean predicted probability.

| Bin | Videos | (a) as fitted: predicted / observed | (b) Platt inside folds: predicted / observed |
|---|---|---|---|
| 1 | 36 | 0.43 / 0.44 | 0.32 / 0.22 |
| 2 | 36 | 0.46 / 0.47 | 0.43 / 0.50 |
| 3 | 36 | 0.47 / 0.50 | 0.46 / 0.72 |
| 4 | 36 | 0.48 / 0.64 | 0.47 / 0.67 |
| 5 | 36 | 0.49 / 0.58 | 0.48 / 0.64 |
| 6 | 36 | 0.49 / 0.64 | 0.50 / 0.47 |
| 7 | 36 | 0.51 / 0.19 | 0.51 / 0.47 |
| 8 | 36 | 0.53 / 0.39 | 0.53 / 0.42 |
| 9 | 36 | 0.55 / 0.53 | 0.55 / 0.28 |
| 10 | 36 | 0.62 / 0.69 | 0.66 / 0.69 |

(a) largest gap 0.32, Brier 0.247 -> **FAIL**; (b) largest gap 0.27, Brier 0.247 -> **FAIL**. Out-of-fold ROC-AUC 0.522 (pooled over repeats; per-fold mean 0.704). **The gap matters:** within one fold the score ranks videos better than chance, but its level shifts each time the model is refitted, so pooled across folds it ranks at chance and no probability can be attached to it. A position among videos scored by the same model is the most the score supports.

**How the tool shows the score (rule fixed in D-053): position among the 120 Instagram videos (no probability).**

Figure: `reports/figures/instagram_score_calibration.png`

## 3. Saved for the tool (12.1)
`models/base_rate.json`, `models/instagram_content_logreg.joblib` (C = 0.01), `models/reference_quantiles.json`, `models/model_card.json` (rewritten for D-046; the 2 October pooled models listed as comparison only). Follower range of the training data: 7,594 to 17,097,407 - outside it the tool warns.

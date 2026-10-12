# 14 — Statistical models and machine learning compared (P16, proposal Objective 13)

**Written 2026-10-09.** Source material for the thesis section that Objective 13 asks for ("to compare
statistical and machine-learning models"). Facts only, each tied to its result file and decision.

## 1. What each approach asks

| | Statistical models (docs/08) | Machine learning (docs/09) |
|---|---|---|
| Question | Is a feature associated with engagement in these 192 videos, with reach and account held fixed? | Can the engagement of a video from an account the model has never seen be predicted? |
| Outcome | Engagement percentile (continuous) | High vs low (median split of the same percentile) |
| How accounts are handled | Random intercept per account: the model uses both within- and between-account variation | Account-grouped folds: no account in both training and test data |
| Evidence | Coefficients, likelihood-ratio tests, Benjamini-Hochberg-adjusted p, 95% intervals | ROC-AUC on unseen accounts, corrected resampled t-test |
| Interpretation | Coefficient size and sign | SHAP, interpreted only where a stability rule was met (D-047) |
| Strength | Detects associations, including between accounts, at this sample size | Tests whether an association is usable for a new account |
| Weakness | An association can be account style rather than a video property | Small, account-heavy data leave little to learn for a new account |

## 2. What each found, side by side

| Topic | Statistics | Machine learning | Agree? |
|---|---|---|---|
| Account effect | ICC 0.30-0.38: a third of the variation is between accounts (D-043) | No pooled model above chance for unseen accounts (D-045) | Yes - both point to the account |
| All 20 content features together | Not detected (H8, BH p 0.354) | Content adds nothing to reach (XGBoost M2 - logistic M0 = -0.030, CI -0.234 to +0.174) | Yes |
| Hashtags | The only detected association, between accounts only (rho 0.244; within accounts 0.02) | The most-used stable feature in the pooled and Instagram models (D-048) | Yes - and both say "accounts that use more hashtags" |
| Platform | H7 not detected (ratio 3.0, CI 0.5-17.3) | Platform ranks near the bottom of the pooled model's SHAP | Yes |
| Instagram content | H9 exploratory: 8 of 20 feature x platform intervals exclude 0 | Instagram content-only models above chance (ROC-AUC 0.70 / 0.67, exploratory) | Consistent: content may matter more on Instagram |
| Hand codes (declared addition) | H2, H4, H5 detected; H2 and H4 not robust to one 15-video series; H5 holds within accounts (D-051) | No hand-code model above chance for unseen accounts; reach + hand codes vs reach: -0.085 (XGBoost) and +0.043 (logistic), intervals include 0 (D-051) | Yes - associations inside the sample, nothing a model can use for a new account |

## 3. The comparison in one paragraph of facts

The two approaches answer different questions and their results fit together. The statistics can detect
an association inside these 22 accounts; the machine learning shows whether it helps for a 23rd. Hashtag
use is associated with engagement, but between accounts, which is exactly the kind of association a model
cannot use for an account it has not seen. The proposal expected the machine-learning models to identify
the strongest predictors; on this data the statistical models were the more informative tool, and the
machine-learning result is the evidence that no measured content feature generalises to new accounts.

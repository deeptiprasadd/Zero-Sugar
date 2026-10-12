# P14 - hand codes in the models, and P10's local-time re-run - declared additions (D-050)

Focus set 192 videos, 22 accounts. Same pipeline, grids and folds as D-044 (5 x 3, account-grouped). **Fold check passed:** the re-computed logistic M0 equals the logged one in all 15 folds (largest difference 6e-17). H = 11 yes/no hand codes (product prominent, logo prominent, a person appears, creator or celebrity, humour, excitement, excited voice, call to action, sponsored disclosed, lifestyle focus, homemade (UGC) look); missing filled with the training fold's median. Hand codes: one coder, weakly reliable where checked (P11). The registered results (D-045) are unchanged.

## Pooled - does hand-coded content add to reach? (corrected resampled t)
| Comparison | ROC-AUC (mean +/- SD) | Logistic M0 | Difference | 95% CI | p |
|---|---|---|---|---|---|
| XGBoost Mh2 (reach + hand codes) - logistic M0 | 0.477 +/- 0.118 | 0.562 | -0.085 | -0.309 to +0.139 | 0.428 |
| LogReg Mh2 (reach + hand codes) - logistic M0 | 0.606 +/- 0.175 | 0.562 | +0.043 | -0.067 to +0.154 | 0.415 |

| Model | ROC-AUC (mean +/- SD) | Corrected 95% CI for AUC - 0.5 | Verdict |
|---|---|---|---|
| Pooled LogReg Mh1 | 0.601 +/- 0.098 | -0.016 to +0.219 | not above chance |
| Pooled LogReg Mh2 | 0.606 +/- 0.175 | -0.105 to +0.317 | not above chance |
| Pooled XGBoost Mh1 | 0.595 +/- 0.101 | -0.027 to +0.216 | not above chance |
| Pooled XGBoost Mh2 | 0.477 +/- 0.118 | -0.165 to +0.120 | not above chance |
| Instagram LogReg Mh1 (exploratory) | 0.588 +/- 0.113 | -0.049 to +0.225 | not above chance |
| Instagram XGBoost Mh1 (exploratory) | 0.613 +/- 0.113 | -0.023 to +0.250 | not above chance |

For comparison, the registered Instagram logistic M1 (20 measured content features): ROC-AUC 0.704.

## Sensitivity - without the 15 AI-character Shorts (177 videos; folds re-drawn)
| Comparison | ROC-AUC (mean +/- SD) | Logistic M0 | Difference | 95% CI | p |
|---|---|---|---|---|---|
| XGBoost Mh2 - logistic M0 | 0.487 +/- 0.129 | 0.631 | -0.144 | -0.334 to +0.046 | 0.127 |
| LogReg Mh2 - logistic M0 | 0.538 +/- 0.084 | 0.631 | -0.092 | -0.283 to +0.098 | 0.317 |

## P10 - local posting time in place of UTC (sensitivity; the registered numbers stay)
| Model | With local time | Registered (UTC) | Difference | 95% CI | p |
|---|---|---|---|---|---|
| LogReg M0 | 0.585 +/- 0.192 | 0.562 | +0.022 | -0.084 to +0.129 | 0.662 |
| XGBoost M2 | 0.488 +/- 0.155 | 0.533 | -0.045 | -0.137 to +0.047 | 0.312 |
Global/US (77 videos) keeps UTC (D-050).

## SHAP stability of two new models (D-047 rule 5; feeds the profile, P17)
- **Instagram logistic regression Mh1 (hand codes)** - rebuilt fold models match this run (max ROC-AUC difference 0e+00). Rank agreement median 0.45 (partly stable). Stable features: humour (higher -> higher), creator or celebrity (higher -> higher).
  Top five by out-of-fold mean |SHAP|: humour 0.069 (top 5 in 15/15); call to action 0.049 (top 5 in 6/15); homemade (UGC) look 0.048 (top 5 in 9/15); excitement 0.039 (top 5 in 2/15); sponsored disclosed 0.037 (top 5 in 9/15).
- **Pooled XGBoost Mh2 (reach + hand codes)** - rebuilt fold models match this run (max ROC-AUC difference 0e+00). Rank agreement median 0.63 (partly stable). Stable features: video age (log days) (higher -> higher), posting hour (UTC) (n/a), followers (log) (higher -> higher).
  Top five by out-of-fold mean |SHAP|: video age (log days) 0.450 (top 5 in 15/15); posting hour (UTC) 0.402 (top 5 in 15/15); followers (log) 0.361 (top 5 in 14/15); follower tier 0.194 (top 5 in 4/15); lifestyle focus 0.187 (top 5 in 10/15).

Run time 8.9 min.

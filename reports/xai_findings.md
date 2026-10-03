# Phase 10 - SHAP findings (D-047, docs/10)

Specification fixed before any SHAP value was computed: D-047. **SHAP says what a model relied on, not what causes engagement.** Model A (pooled XGBoost M2) did **not** predict above chance for unseen accounts (ROC-AUC 0.533, D-045), so its SHAP values describe what a model that failed relied on. Models B and C (Instagram only, content features) predicted above chance (ROC-AUC 0.704 and 0.670) and are **exploratory** - Instagram only, 17 accounts, not corrected for the many comparisons. The Zero Sugar inclusion label is weakly reliable (YouTube alpha 0.25, Instagram -0.10).

## 0. The fold models are the ones Phase 9 evaluated (D-047 rule 2)
| Model | Videos / accounts | Max ROC-AUC difference vs logged (15 folds) | Max prediction difference vs saved (repeat 1) | Max SHAP additivity error |
|---|---|---|---|---|
| A. Pooled XGBoost M2 | 192 / 22 | 5.6e-17 | 1.1e-16 | 4.8e-06 |
| B. Instagram logistic regression M1 | 120 / 17 | 0.0e+00 | 5.6e-17 | 4.4e-16 |
| C. Instagram XGBoost M1 | 120 / 17 | 0.0e+00 | 1.1e-16 | 2.4e-06 |

## 1. Stability first (10.1)
Rule (D-047 rule 5): a feature is **stable** if it is in the top 5 of at least 12 of the 15 fold models and its direction is the same in at least 12. Overall ranking verdict: median pairwise Spearman >= 0.7 stable, 0.4-0.7 partly stable, below 0.4 unstable. Each fold model is judged on all rows of its data set. Only stable features may be interpreted - at most 5 if the overall ranking is stable, at most 3 otherwise.

**A. Pooled XGBoost M2 - all rows.** Rank agreement between the 15 fold models (Spearman, 105 pairs): median **0.72** (10th-90th percentile 0.51 to 0.87) -> **stable**. Features in the top 10 of all 15 fold models: 2. Stable features (rule 5): hashtags, video age (log days).

| Rank (out-of-fold) | Feature | Mean abs SHAP | Top 5 in | Top 10 in | Direction (12 of 15) | Stable |
|---|---|---|---|---|---|---|
| 1 | hashtags | 0.350 | 13 / 15 | 15 / 15 | higher -> higher | **yes** |
| 2 | video age (log days) | 0.328 | 12 / 15 | 13 / 15 | higher -> higher | **yes** |
| 3 | cuts per second (log) | 0.313 | 11 / 15 | 15 / 15 | higher -> lower | no |
| 4 | posting hour (UTC) | 0.312 | 9 / 15 | 13 / 15 | n/a | no |
| 5 | share of frames with a face | 0.274 | 3 / 15 | 5 / 15 | higher -> higher | no |
| 6 | share of red | 0.265 | 5 / 15 | 14 / 15 | higher -> lower | no |
| 7 | share with music | 0.245 | 2 / 15 | 10 / 15 | higher -> higher | no |
| 8 | loudness | 0.238 | 6 / 15 | 12 / 15 | higher -> higher | no |
| 9 | visual detail (edges) | 0.231 | 3 / 15 | 12 / 15 | higher -> higher | no |
| 10 | share with talking | 0.222 | 3 / 15 | 7 / 15 | higher -> higher | no |
| 11 | followers (log) | 0.199 | 1 / 15 | 8 / 15 | higher -> higher | no |
| 12 | loudness range | 0.179 | 0 / 15 | 8 / 15 | higher -> higher | no |
| 13 | emoji | 0.152 | 1 / 15 | 4 / 15 | higher -> lower | no |
| 14 | caption sentiment | 0.146 | 2 / 15 | 2 / 15 | mixed (mostly -) | no |
| 15 | caption length (within language) | 0.137 | 1 / 15 | 3 / 15 | mixed (mostly -) | no |
| 16 | face size | 0.136 | 1 / 15 | 5 / 15 | mixed (mostly +) | no |
| 17 | motion | 0.112 | 1 / 15 | 2 / 15 | mixed (mostly -) | no |
| 18 | follower tier | 0.109 | 0 / 15 | 0 / 15 | n/a | no |
| 19 | on-screen text regions | 0.109 | 1 / 15 | 1 / 15 | mixed (mostly +) | no |
| 20 | colourfulness | 0.108 | 0 / 15 | 0 / 15 | mixed (mostly +) | no |
| 21 | on-screen text area | 0.074 | 0 / 15 | 0 / 15 | higher -> higher | no |
| 22 | platform (Instagram) | 0.057 | 0 / 15 | 1 / 15 | mixed (mostly -) | no |
| 23 | duration | 0.045 | 0 / 15 | 0 / 15 | mixed (mostly +) | no |
| 24 | event words | 0.003 | 0 / 15 | 0 / 15 | mixed (mostly -) | no |
| 25 | promotional words | 0.001 | 0 / 15 | 0 / 15 | mixed (mostly -) | no |
| 26 | weekend post (UTC) | 0.000 | 0 / 15 | 0 / 15 | mixed (mostly -) | no |

**B. Instagram logistic regression M1 - all rows.** Rank agreement between the 15 fold models (Spearman, 105 pairs): median **0.74** (10th-90th percentile 0.63 to 0.88) -> **stable**. Features in the top 10 of all 15 fold models: 5. Stable features (rule 5): hashtags, share with talking, share of frames with a face.

| Rank (out-of-fold) | Feature | Mean abs SHAP | Top 5 in | Top 10 in | Direction (12 of 15) | Stable |
|---|---|---|---|---|---|---|
| 1 | hashtags | 0.033 | 15 / 15 | 15 / 15 | higher -> higher | **yes** |
| 2 | share with talking | 0.030 | 14 / 15 | 15 / 15 | higher -> higher | **yes** |
| 3 | share of frames with a face | 0.029 | 12 / 15 | 15 / 15 | higher -> higher | **yes** |
| 4 | share of red | 0.023 | 10 / 15 | 15 / 15 | higher -> lower | no |
| 5 | on-screen text regions | 0.022 | 4 / 15 | 14 / 15 | higher -> higher | no |
| 6 | cuts per second (log) | 0.020 | 1 / 15 | 12 / 15 | higher -> lower | no |
| 7 | caption sentiment | 0.019 | 2 / 15 | 15 / 15 | higher -> lower | no |
| 8 | loudness range | 0.018 | 3 / 15 | 13 / 15 | higher -> higher | no |
| 9 | visual detail (edges) | 0.017 | 2 / 15 | 4 / 15 | higher -> higher | no |
| 10 | creator collaboration | 0.016 | 6 / 15 | 10 / 15 | higher -> higher | no |
| 11 | motion | 0.015 | 3 / 15 | 9 / 15 | higher -> lower | no |
| 12 | colourfulness | 0.015 | 3 / 15 | 6 / 15 | higher -> lower | no |
| 13 | caption length (within language) | 0.012 | 0 / 15 | 0 / 15 | higher -> higher | no |
| 14 | share with music | 0.008 | 0 / 15 | 0 / 15 | mixed (mostly +) | no |
| 15 | emoji | 0.007 | 0 / 15 | 1 / 15 | higher -> lower | no |
| 16 | duration | 0.007 | 0 / 15 | 3 / 15 | higher -> higher | no |
| 17 | event words | 0.006 | 0 / 15 | 3 / 15 | higher -> higher | no |
| 18 | promotional words | 0.006 | 0 / 15 | 0 / 15 | mixed (mostly +) | no |
| 19 | loudness | 0.005 | 0 / 15 | 0 / 15 | higher -> lower | no |
| 20 | on-screen text area | 0.004 | 0 / 15 | 0 / 15 | higher -> lower | no |
| 21 | face size | 0.003 | 0 / 15 | 0 / 15 | mixed (mostly +) | no |

**C. Instagram XGBoost M1 - all rows.** Rank agreement between the 15 fold models (Spearman, 105 pairs): median **0.63** (10th-90th percentile 0.24 to 0.82) -> **partly stable**. Features in the top 10 of all 15 fold models: 0. Stable features (rule 5): share of frames with a face.

| Rank (out-of-fold) | Feature | Mean abs SHAP | Top 5 in | Top 10 in | Direction (12 of 15) | Stable |
|---|---|---|---|---|---|---|
| 1 | share of frames with a face | 0.280 | 13 / 15 | 14 / 15 | higher -> higher | **yes** |
| 2 | share with talking | 0.204 | 9 / 15 | 12 / 15 | higher -> higher | no |
| 3 | caption sentiment | 0.178 | 11 / 15 | 14 / 15 | higher -> lower | no |
| 4 | visual detail (edges) | 0.145 | 6 / 15 | 9 / 15 | higher -> higher | no |
| 5 | motion | 0.144 | 8 / 15 | 14 / 15 | higher -> lower | no |
| 6 | cuts per second (log) | 0.125 | 7 / 15 | 13 / 15 | higher -> lower | no |
| 7 | share of red | 0.123 | 3 / 15 | 12 / 15 | higher -> lower | no |
| 8 | colourfulness | 0.112 | 4 / 15 | 7 / 15 | higher -> lower | no |
| 9 | on-screen text regions | 0.112 | 3 / 15 | 11 / 15 | higher -> higher | no |
| 10 | on-screen text area | 0.098 | 2 / 15 | 10 / 15 | higher -> higher | no |
| 11 | hashtags | 0.076 | 4 / 15 | 9 / 15 | higher -> higher | no |
| 12 | duration | 0.061 | 2 / 15 | 4 / 15 | mixed (mostly +) | no |
| 13 | share with music | 0.053 | 0 / 15 | 4 / 15 | mixed (mostly +) | no |
| 14 | loudness | 0.048 | 1 / 15 | 6 / 15 | mixed (mostly -) | no |
| 15 | loudness range | 0.048 | 1 / 15 | 8 / 15 | higher -> higher | no |
| 16 | face size | 0.046 | 0 / 15 | 3 / 15 | mixed (mostly -) | no |
| 17 | creator collaboration | 0.038 | 0 / 15 | 3 / 15 | mixed (mostly +) | no |
| 18 | caption length (within language) | 0.038 | 1 / 15 | 5 / 15 | mixed (mostly -) | no |
| 19 | emoji | 0.010 | 0 / 15 | 1 / 15 | mixed (mostly -) | no |
| 20 | promotional words | 0.002 | 0 / 15 | 1 / 15 | mixed (mostly +) | no |
| 21 | event words | 0.001 | 0 / 15 | 1 / 15 | mixed (mostly -) | no |

Figure: `reports/figures/shap/shap_stability.png`

### What may be interpreted
- **A. Pooled XGBoost M2:** hashtags (higher -> higher), video age (log days) (higher -> higher) - read as *what a model that did not predict above chance relied on*.
- **B. Instagram logistic regression M1:** hashtags (higher -> higher), share with talking (higher -> higher), share of frames with a face (higher -> higher).
- **C. Instagram XGBoost M1:** share of frames with a face (higher -> higher).

## 2. Global importance (10.2)
### Beeswarms (out-of-fold: each video explained only by fold models that did not see it, mean of 3)
Figure: `reports/figures/shap/shap_beeswarm_pooled.png`

Figure: `reports/figures/shap/shap_beeswarm_instagram.png`

Colour is the feature's value (blue low, red high); posting hour and follower tier are grey because each is two columns summed (D-047 rule 3) and has no single value.

### Importance by block
Figure: `reports/figures/shap/shap_blocks.png`

| Model | Block | Features | Sum of mean abs SHAP | Per feature |
|---|---|---|---|---|
| A | A video | 10 | 1.668 | 0.167 |
| A | B audio | 4 | 0.884 | 0.221 |
| A | C text | 6 | 0.789 | 0.132 |
| A | D creator | 0 | not measured | - |
| A | E platform and exposure | 6 | 1.005 | 0.168 |
| B | A video | 10 | 0.155 | 0.016 |
| B | B audio | 4 | 0.060 | 0.015 |
| B | C text | 6 | 0.082 | 0.014 |
| B | D creator | 1 | 0.016 | 0.016 |
| B | E platform and exposure | 0 | not in this model | - |

Block D (creator) is empty in the pooled model: no creator feature survived (automated labels failed, D-038; `creator_collab` exists only on Instagram).

### Dependence plots
Figure: `reports/figures/shap/shap_dependence_duration_pooled.png`

Figure: `reports/figures/shap/shap_dependence_instagram.png`

### Four waterfalls (model B only, D-047 rule 6)
Figure: `reports/figures/shap/shap_waterfalls_instagram.png`

Picked without a threshold, from repeat 1's saved out-of-fold probabilities; the bars are the mean out-of-fold SHAP over the 3 repeats.
| Case | Video | Account | Actually high? | Predicted probability | Sum of SHAP (log-odds) |
|---|---|---|---|---|---|
| True positive | DacfR8GMQOI | cocacola_kenya | yes | 0.676 | +0.516 |
| False positive | CqgEnkAtNAU | cocacola | no | 0.579 | +0.088 |
| True negative | DVRMTm8EflU | cocacola_cl | no | 0.400 | -0.284 |
| False negative | DZ557Q4jfxE | cocacola_cl | yes | 0.391 | -0.308 |

## 3. Per-platform view of the pooled model (10.3, RQ7 / H9 - exploratory)
**A. Pooled XGBoost M2 - YouTube Shorts rows.** Rank agreement between the 15 fold models (Spearman, 105 pairs): median **0.73** (10th-90th percentile 0.49 to 0.87) -> **stable**. Features in the top 10 of all 15 fold models: 2. Stable features (rule 5): hashtags, video age (log days).

**A. Pooled XGBoost M2 - Instagram Reels rows.** Rank agreement between the 15 fold models (Spearman, 105 pairs): median **0.72** (10th-90th percentile 0.53 to 0.85) -> **stable**. Features in the top 10 of all 15 fold models: 1. Stable features (rule 5): hashtags.

| Feature | YouTube rank | YouTube top 5 in | Instagram rank | Instagram top 5 in | Divergent? |
|---|---|---|---|---|---|
| hashtags | 5 | 13 / 15 | 2 | 13 / 15 | no |
| video age (log days) | 10 | 12 / 15 | 1 | 11 / 15 | no |
| cuts per second (log) | 2 | 10 / 15 | 4 | 11 / 15 | no |
| posting hour (UTC) | 4 | 8 / 15 | 3 | 10 / 15 | no |
| share of frames with a face | 1 | 3 / 15 | 12 | 4 / 15 | no |
| share of red | 3 | 3 / 15 | 7 | 6 / 15 | no |
| share with music | 6 | 3 / 15 | 8 | 3 / 15 | no |
| loudness | 12 | 9 / 15 | 5 | 3 / 15 | no |
| visual detail (edges) | 11 | 0 / 15 | 6 | 3 / 15 | no |
| share with talking | 9 | 4 / 15 | 9 | 4 / 15 | no |
| followers (log) | 7 | 3 / 15 | 11 | 2 / 15 | no |
| loudness range | 19 | 0 / 15 | 10 | 0 / 15 | no |
| emoji | 18 | 1 / 15 | 13 | 1 / 15 | no |
| caption sentiment | 8 | 2 / 15 | 17 | 1 / 15 | no |
| caption length (within language) | 17 | 1 / 15 | 14 | 1 / 15 | no |
| face size | 13 | 1 / 15 | 15 | 0 / 15 | no |
| motion | 15 | 0 / 15 | 19 | 1 / 15 | no |
| follower tier | 16 | 0 / 15 | 18 | 0 / 15 | no |
| on-screen text regions | 14 | 1 / 15 | 20 | 1 / 15 | no |
| colourfulness | 20 | 0 / 15 | 16 | 0 / 15 | no |
| on-screen text area | 21 | 0 / 15 | 22 | 0 / 15 | no |
| platform (Instagram) | 22 | 1 / 15 | 21 | 0 / 15 | no |
| duration | 23 | 0 / 15 | 23 | 0 / 15 | no |
| event words | 25 | 0 / 15 | 24 | 0 / 15 | no |
| promotional words | 24 | 0 / 15 | 25 | 0 / 15 | no |
| weekend post (UTC) | 26 | 0 / 15 | 26 | 0 / 15 | no |

Divergent (D-047 rule 7): top 5 in at least 12 of 15 fold models on one platform and outside the top 10 in at least 12 of 15 on the other. 58 of the 72 YouTube rows come from one channel; model A did not predict above chance.

Figure: `reports/figures/shap/shap_platform_comparison.png`

**Check on the Instagram view (docs/10 section 3):** Spearman between model A's importance on Instagram rows and model B's, over the 20 shared content features: **0.48**.

**H10 - duration x platform (SHAP interaction, model A, out-of-fold):** mean +0.0002 on YouTube rows, -0.0000 on Instagram rows (log-odds; mean absolute 0.0001, against a mean absolute duration SHAP of 0.0451). An estimate from a model at chance, never 'significant'.

## 4. B against C, and the effective-video profile (D-047 rule 8)
Spearman between B's and C's out-of-fold importance over their 21 features: **0.64**.

| Feature (stable in B) | B direction | C rank | C direction (fold models) | In the profile | Instagram mean (where B's contribution changes sign) |
|---|---|---|---|---|---|
| hashtags | higher -> higher | 11 | + in 14, - in 0 of 15 | **yes** | 2.29 |
| share with talking | higher -> higher | 2 | + in 15, - in 0 of 15 | **yes** | 0.292 |
| share of frames with a face | higher -> higher | 1 | + in 15, - in 0 of 15 | **yes** | 0.467 |

**Effective-video profile, Instagram only - exploratory association, not a recommendation:** hashtags: higher -> higher; share with talking: higher -> higher; share of frames with a face: higher -> higher. Follower count matters for real reach and is not in this content model; Instagram reach alone predicted below chance here (M0 0.46).

**For the tool (D-047 rule 9):** drivers may come only from model B and only from: hashtags, share with talking, share of frames with a face.

Run time 0.6 min.

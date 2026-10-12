# 10 — Explainability (SHAP)

**Status:** **Done 2026-10-02** - specification D-047 (written before any SHAP value was computed),
results D-048, `python -m src.models.explain`. Answers RQ10 and produces the interpretable core of the
contribution. Where this plan and D-047 differ, D-047 wins: three models are explained (pooled XGBoost
M2; Instagram logistic regression M1 and XGBoost M1), not Random Forest or the MLP.

---

## 1. Method

**TreeSHAP** on XGBoost and Random Forest — exact and fast for tree ensembles.
KernelSHAP only if the MLP needs explaining, and only if it performed well enough to be
worth explaining.

**Explain the M2 model** (content + exposure), not M1. The point is to see content
importance *alongside* exposure, not with exposure hidden.

**Stability check — do this first.** At n=192 (22 accounts), SHAP values can be unstable. Compute SHAP
on each of the 5 outer folds and report the rank correlation of feature importance across
folds. If rankings are unstable, say so and interpret only the top few features. An
unstable SHAP ranking presented as a finding would be the most likely serious error in
this project.

> **Amended 2026-10-02 (D-047):** the models ran on 5 folds x 3 repeats, so the check uses all **15**
> outer fold models, rebuilt from the settings Phase 9 logged and checked against its results first. The
> exact rule (top 5 in at least 12 of 15, same direction in at least 12; median rank agreement >= 0.70
> stable, 0.40-0.70 partly stable) was fixed in D-047 before any SHAP value existed.

---

## 2. Outputs

| Output | Purpose |
|---|---|
| Beeswarm summary plot | Global importance and direction, all features |
| Mean \|SHAP\| bar chart, **grouped by block A–E** | Answers "which modality matters most" — the grouping is what makes it an answer |
| Waterfall plots × 4 | One true positive, one true negative, one false positive, one false negative |
| Dependence plots | `duration`, emotion (collapsed, D-040) - recovers the shape, including non-linearity. `product_visible_frac` is not measured (D-037) |
| **Per-platform SHAP comparison** | The key figure. Answers RQ7 and H9 in a form a marketer can read |
| SHAP interaction values | `duration × platform` for H10 |

> **Amended 2026-10-02 (D-047):** no emotion dependence plot (emotion is not one of the 20 model
> features, D-040); Block D is empty in the pooled model (no creator measure survived, D-038); the four
> waterfalls come from the Instagram logistic model only, picked by predicted probability rather than a
> threshold.

**Block-grouped importance** is the figure that connects back to the proposal's structure:
sum mean |SHAP| within Blocks A (video), B (audio), C (text), D (creator), E (platform and
exposure). If Block E dominates, that is the honest headline — and it is exactly what the
exposure-aware literature predicts.

---

## 3. Per-platform comparison

**Rewritten 2026-10-01 (D-041).** No YouTube-only model is fitted (72 videos, 5 channels, 58 from
one; docs/09 section 5). The comparison uses **the pooled M2 model's SHAP values, summarised
separately for YouTube rows and Instagram rows** - one model, two views - plus the exploratory
Instagram-only model as a check on the Instagram view.

Exploratory throughout, with the fold-stability check applied to each platform's view. Where a
feature ranks high on one platform and low on the other, check whether it is stable, and remember
that on YouTube one channel supplies 58 of 72 rows, before making anything of it.

---

## 4. The caveat, stated up front

**SHAP attributes a model's predictions. It does not estimate causal effects.**

Every sentence in the results uses "associated with", not "causes" or "drives". This
belongs in the results chapter where the findings are presented — not buried in the
conclusion where nobody reads it.

Second caveat: SHAP explains the model, and the model may have learned a confound. If
`product_visible_frac` ranks high, it may be because product-heavy videos come from the
large official accounts. The M0/M1/M2 design and the account controls mitigate this but do
not eliminate it.

---

## 5. The effective-video profile (Specific Objective 15)

Build from the top-k stable SHAP features:

| Feature | Direction | Threshold from dependence plot | Platform |
|---|---|---|---|
| Share of the video with talking | more -> higher | none fitted; the linear model's contribution turns positive above the Instagram average (0.29) | Instagram (model-based, exploratory); **opposite on YouTube** (described) |
| Share of frames with a face | more -> higher | as above, average 0.47 | Instagram (model-based, exploratory); **opposite on YouTube** (described) |
| A call to action (hand-coded) | present -> higher | - (yes/no) | Both, pooled statistics (H5); same direction on YouTube (62% vs 24%) |
| Hashtags | more -> higher | Instagram average 2.3 | Listed, not in the profile: associated only between accounts |

**Filled 2026-10-09 (D-052), replacing the 2 October version.** Items pass every check fixed in advance:
stability with both Instagram models agreeing (D-047), and for tested items, within accounts and without
the 15 AI-character Shorts (D-050). Product prominence and creator or celebrity presence were detected in
the declared addition but do not survive without that series, so they are listed in
`reports/effective_video_profile.md`, not here. **YouTube is described, not modelled** (72 videos, 58 from
one channel): there, high-engagement Shorts had less talking and fewer faces than low ones. An empirical
association, not a recommendation; engagement is ranked within platform and follower tier, so the profile
says nothing about reach.

Rules to follow when writing it:

- Include only features stable across folds.
- State it as an empirical association, not a recommendation.
- Give separate profiles for YouTube and Instagram where they differ.
- Include the exposure caveat — a profile that ignores follower count would mislead a
  practitioner.

---

## 6. Results

**Filled 2026-10-02 (D-048).** Output `reports/xai_findings.md`, `reports/shap_importance.csv`,
`reports/shap_fold_importance.csv`, `reports/figures/shap/` (8 figures). Model A = pooled XGBoost M2 (did
not predict above chance for unseen accounts, D-045 - its SHAP values say what a failed model relied
on); B = Instagram logistic regression M1, C = Instagram XGBoost M1 (exploratory). Every result carries
the Zero Sugar label's repeat reliability (YouTube alpha 0.25, Instagram -0.10).

**Check first:** the 45 rebuilt fold models reproduce Phase 9 exactly (differences at most 1e-16).

### Stability check

| Metric | A pooled | B Instagram LogReg | C Instagram XGBoost |
|---|---|---|---|
| Spearman correlation of importance rankings across the 15 fold models (median, 10th-90th) | 0.72 (0.51-0.87) | 0.74 (0.63-0.88) | 0.63 (0.24-0.82) |
| Verdict (D-047) | stable | stable | partly stable |
| Features in the top 10 of all 15 fold models | 2 | 5 | 0 |
| Stable features (top 5 in >= 12 of 15, same direction in >= 12) | hashtags, video age | hashtags, talking share, face share | face share |
| Interpretation limited to | 2 features, as *what a failed model relied on* | 3 features | 1 feature |

### Global importance by block

Sum of mean \|SHAP\| (log-odds); B's values are on a much smaller scale, so compare within a model only.

| Block | A pooled | Rank | B Instagram | Rank |
|---|---|---|---|---|
| A — Video (10 features) | 1.668 | 1 | 0.155 | 1 |
| B — Audio (4) | 0.884 | 3 | 0.060 | 3 |
| C — Text (6) | 0.789 | 4 | 0.082 | 2 |
| D — Creator | not measured | - | 0.016 (`creator_collab`) | 4 |
| E — Platform / exposure (6) | 1.005 | 2 | not in this model | - |

Exposure does not dominate model A, but A is at chance, so this describes a failed model rather than
which kind of feature matters.

### Top features

| Rank | A pooled (mean \|SHAP\|, direction, stable?) | B Instagram (mean \|SHAP\|, direction, stable?) |
|---|---|---|
| 1 | hashtags - 0.350, more -> higher, **yes** | hashtags - 0.033, more -> higher, **yes** |
| 2 | video age - 0.328, older -> higher, **yes** | share with talking - 0.030, more -> higher, **yes** |
| 3 | cuts per second - 0.313, more -> lower, no (top 5 in 11 of 15) | share of frames with a face - 0.029, more -> higher, **yes** |
| 4 | posting hour - 0.312, n/a, no | share of red - 0.023, more -> lower, no (10 of 15) |
| 5 | share of frames with a face - 0.274, more -> higher, no | on-screen text regions - 0.022, more -> higher, no |

### Per-platform divergence

Model A, out-of-fold ranks on each platform's rows; both views stable (0.73 YouTube, 0.72 Instagram).

| Feature | YouTube rank | Instagram rank | Divergent? |
|---|---|---|---|
| hashtags | 5 (stable) | 2 (stable) | no |
| video age | 10 (stable) | 1 (top 5 in 11 of 15) | no |
| cuts per second | 2 | 4 | no |
| share of frames with a face | 1 (top 5 in only 3 of 15) | 12 | no - not stable on either |
| No feature meets the divergence rule (D-047 rule 7) | | | |

H10 (duration x platform, SHAP interaction): essentially zero on both platforms (+0.0002 / -0.0000).

### Answers to the research questions

| RQ | Answer |
|---|---|
| RQ1 — which characteristics associate with engagement | For a new account, none that a model could use above chance on the pooled set (D-045). On Instagram only (exploratory): more hashtags, more talking and more frames with a face go with a higher predicted chance of high engagement - hashtags as an account-level habit (D-043), and the model's scores barely move |
| RQ7 — do predictors differ across platforms | Not detected: no feature meets the divergence rule in the pooled model's per-platform SHAP; H9 stays exploratory (D-043) |
| RQ9 — does content predict beyond exposure | No (D-045). SHAP adds that the pooled model's reliance pattern was stable across folds yet did not carry to unseen accounts |
| RQ10 — what does SHAP reveal | A consistent but non-transferable pattern in the pooled model, and three consistent content correlates on Instagram that two different model types agree on - exploratory, with the account-level caveat |

# 09 — Machine Learning Models

**Status:** Planned. **Updated 2026-10-01 (D-041)** for the focus set - **192 usable Zero Sugar
videos from 22 accounts** (Instagram 120 / 17, YouTube 72 / 5; D-039) - and for the 1 October
modelling meeting. Where the researcher deferred to the proposal (target, per-platform models),
the proposal's text decides; what it says is quoted in D-041.

### 0. What is predicted, and from what (D-041)

- **Target: `engagement_high`** - high vs low engagement, the median split of the percentile within
  platform x size tier (100 high / 92 low in the focus set; the docs/06 fallback was not needed,
  D-040). This is the proposal's own dependent variable ("High-engagement vs Low-engagement",
  normalised within each platform) and fits its classification metrics. The **continuous
  percentile** stays the outcome of the mixed-effects statistics (docs/08); the tertile split stays a
  robustness check (docs/06).
- **Content features: the 20 fixed in D-036**, with `cuts_per_sec` as log1p (D-040). Speech-only
  features go to the speech-only sub-analysis (119 focus videos); `title_char_len*` enter only
  YouTube description, `creator_collab` only the Instagram model (section 5).
- **Exposure controls (M0):** `followers` (log), `video_age_days` (log), `account_size_tier`,
  `platform`, `posting_hour_utc`, `is_weekend_utc`; `account_prior_engagement` computed inside each
  training fold only.
- **Not available, reported as not measured** (researcher, 1 Oct): call to action and celebrity /
  creator presence (D-038), product visibility (D-037), music type (D-033). No automated label
  enters any model.

The design question is not "which model wins" — it is **"does content predict engagement
beyond reach?"** The nested feature sets in §2 answer that. Everything else is supporting
detail.

---

## 1. Models

| Model | Configuration | Expectation at n=192 |
|---|---|---|
| **Baseline 0** — majority class | — | Floor. Any model below this is broken |
| **Baseline 1** — exposure only | Logistic Regression on controls | **The number that matters.** Content must beat this |
| Logistic Regression | L2, scaled inputs | Competitive at this n; highly interpretable |
| Decision Tree | Depth-limited | Weak alone; included for interpretability |
| Random Forest | class_weight balanced | Strong |
| XGBoost | class_weight balanced | **Expected winner** — matches the literature at this scale |
| MLP | 1–2 hidden layers, early stopping | **Expected to lose.** **Kept (researcher, 1 Oct meeting)** and reported honestly: deep models need far more data, consistent with the survey. First to go if the schedule slips (SCHEDULE cut order) |

Baseline 1 is not optional. Without it there is no way to tell whether a 0.72 AUC means
"content predicts engagement" or "big accounts get more likes".

---

## 2. Nested feature sets — the core design

| Set | Features | Answers |
|---|---|---|
| **M0** | Exposure and account controls only | How much is explained by reach alone? |
| **M1** | Content features only (Blocks A–D) | Does content predict in isolation? |
| **M2** | Content + exposure | Full model |

**Headline result: M2 − M0.** That difference is the study's actual contribution. Reporting
only M2 would repeat exactly the error the exposure-aware Frontiers study exposes.

Report all three for every model, with confidence intervals on the difference.

---

## 3. Validation

```python
from sklearn.model_selection import StratifiedGroupKFold, RandomizedSearchCV
from sklearn.pipeline import Pipeline

# groups = account_id  — NEVER a plain random split (D-006)
outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
```

- **5 folds, repeated 3×** with different seeds. Report mean ± SD.
- **Everything inside a `Pipeline`** — scaling, encoding, imputation, and any
  data-dependent pruning — fitted within each training fold.
- **Nested CV** for tuning: `RandomizedSearchCV` inner, grouped outer folds give the
  honest estimate.
- **Threshold** chosen on the validation fold (maximise F1 or Youden's J). **Never** on
  test.

**Check fold balance.** With 22 accounts and 5 folds, the global YouTube channel (58 videos, 30% of
the focus set) fills most of one fold, and 5 accounts have a single video (D-040, diagnostic A). Log
videos, accounts, platform and class balance per fold, and report the fold holding the global
channel separately as well as in the average.

**`account_prior_engagement` is a leakage trap** — recompute it within each training fold
using only prior videos. Do not compute it once globally.

---

## 4. Metrics

| Metric | Why |
|---|---|
| Accuracy | Proposal requirement. Nearly meaningless on a balanced median split |
| Precision, Recall, F1 | Proposal requirement |
| ROC-AUC | Primary comparison metric |
| PR-AUC | More informative if the tertile split creates imbalance |
| Confusion matrix | Proposal requirement |
| **Brier score** | Added — are probabilities calibrated? |
| **Calibration curve** | Added — a confident wrong model is worse than an uncertain one |

**Report mean ± SD across folds, never a single split.** At n=192 in 22 accounts fold-to-fold
variance will be large, and a single number would be misleading.

**Learning curves** for the best model. They show whether more data would have helped —
which directly addresses the sample-size limitation and pre-empts the obvious examiner
question.

---

## 5. Per-platform comparison (rewritten 2026-10-01, D-041)

The proposal asks whether predictors differ between the platforms (RQ7, H9, H10; section 11: "Are
their effects different on YouTube and Instagram?"). It does not ask for a separate model per
platform, and with the focus set one cannot be tested fairly on YouTube. So:

- **Main answer - the pooled model, split by platform.** The M2 models include `platform`; their
  SHAP values are summarised separately for YouTube rows and Instagram rows ([10](10-explainability.md)
  section 3), and the mixed model carries feature x platform terms for H9/H10 (docs/08 section 7.9.7).
- **Instagram-only model - exploratory, labelled so before running:** 120 videos in 17 accounts,
  same 5x3 account-grouped folds, same metrics. Adds `creator_collab`.
- **No YouTube-only model.** 72 videos in 5 channels, 58 from one: account-grouped 5-fold CV would
  put almost all YouTube data in one fold, and the effective sample is a handful of independent
  units (minimum detectable r 0.33 even at ICC 0, `reports/power_analysis.md`). YouTube is described
  (EDA, the pooled model's YouTube rows) and the reason is stated in the thesis.

Their value is the comparison, not their accuracy; H9 and H10 stay exploratory (docs/08 7.9.7).

---

## 6. Results

**Filled 2026-10-02 (D-045).** Output `reports/model_comparison.md` (`python -m src.models.train`,
55 min); per-fold results `reports/model_fold_results.csv`, out-of-fold predictions
`reports/model_oof_predictions.csv`. Full tables are in the report; the key numbers are below.

### Main comparison — mean ± SD over 5×3 grouped folds

| Model | Set | Acc | Prec | Rec | F1 | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|---|---|---|---|---|
| Majority | — | 0.534 ± 0.089 | 0.534 ± 0.089 | 1.000 ± 0.000 | 0.692 ± 0.074 | 0.500 ± 0.000 | 0.534 ± 0.089 | 0.252 ± 0.003 |
| Exposure-only (LogReg) | M0 | 0.526 ± 0.124 | 0.516 ± 0.144 | 0.898 ± 0.229 | 0.649 ± 0.172 | 0.562 ± 0.204 | 0.617 ± 0.195 | 0.265 ± 0.028 |
| LogReg | M1 | 0.520 ± 0.074 | 0.529 ± 0.084 | 0.964 ± 0.058 | 0.678 ± 0.066 | 0.505 ± 0.145 | 0.596 ± 0.169 | 0.253 ± 0.024 |
| LogReg | M2 | 0.523 ± 0.088 | 0.527 ± 0.090 | 0.953 ± 0.081 | 0.675 ± 0.084 | 0.528 ± 0.187 | 0.581 ± 0.210 | 0.259 ± 0.033 |
| Decision Tree | M2 | 0.524 ± 0.092 | 0.529 ± 0.092 | 0.952 ± 0.094 | 0.676 ± 0.084 | 0.471 ± 0.085 | 0.528 ± 0.127 | 0.390 ± 0.102 |
| Random Forest | M2 | 0.531 ± 0.097 | 0.532 ± 0.094 | 0.959 ± 0.060 | 0.681 ± 0.087 | 0.511 ± 0.221 | 0.577 ± 0.213 | 0.260 ± 0.044 |
| XGBoost | M1 | 0.530 ± 0.104 | 0.529 ± 0.100 | 0.937 ± 0.108 | 0.673 ± 0.101 | 0.513 ± 0.134 | 0.599 ± 0.153 | 0.288 ± 0.048 |
| XGBoost | M2 | 0.536 ± 0.091 | 0.533 ± 0.091 | 0.933 ± 0.111 | 0.675 ± 0.093 | 0.533 ± 0.200 | 0.595 ± 0.207 | 0.313 ± 0.092 |
| MLP | M2 | 0.523 ± 0.098 | 0.527 ± 0.093 | 0.973 ± 0.089 | 0.680 ± 0.087 | 0.483 ± 0.132 | 0.562 ± 0.149 | 0.283 ± 0.044 |

Filled 2026-10-02 from `reports/model_comparison.md`. Accuracy, precision, recall and F1 use the
registered F1-maximising threshold, which labelled every test video "high" in many folds (D-044 note) -
hence recall near 1 and accuracy near the share of high videos. The same four metrics at the secondary
Youden threshold, and the M0/M1/M2 rows not shown here, are in the report. ROC-AUC is the headline.

### The headline number

| Quantity | Value |
|---|---|
| Reach-only baseline (LogReg M0) ROC-AUC | 0.562 +/- 0.204 |
| Best M0 ROC-AUC (reach alone) | 0.606 (MLP) |
| Best M2 ROC-AUC (reach + content) | 0.533 (XGBoost) |
| **M2 − M0 (primary: XGBoost M2 − LogReg M0)** | **−0.030** |
| 95% CI on the difference (corrected resampled t) | −0.234 to +0.174 (p 0.76) |
| **Does content add beyond reach?** | **Not detected - and neither content nor reach predicts above chance for accounts the model has not seen** (every pooled model's interval around 0.5 includes 0.5) |

### Per-platform (exploratory)

| Platform | n | Best model | ROC-AUC |
|---|---|---|---|
| Instagram (own model) | 120 / 17 accounts | LogReg M1 (content only) | **0.704 +/- 0.140**; above chance, corrected 95% CI for AUC - 0.5: +0.035 to +0.373 (exploratory) |
| YouTube | 72 / 5 accounts | not fitted (D-041) - see the pooled model's YouTube rows | - |

### Diagnostics

| Check | Result |
|---|---|
| Fold balance acceptable? | Test folds 25-72 videos, 2-6 accounts, share high 0.42-0.68; the global channel fills one fold per repeat - as expected (D-040) |
| Learning curve — would more data help? | Flat: XGBoost M2 0.52 with 40% of training accounts, 0.53 with 100% - more accounts of the same kind would not obviously help |
| Selected threshold | The registered F1 rule called every test video "high" in 6-13 of 15 folds per model; Youden's J reported beside it (D-044 note). Threshold metrics are therefore secondary |
| Calibration acceptable? | **No.** Brier 0.268 (LogReg M2) and 0.315 (XGBoost M2), worse than a constant 0.5 guess (0.25) |

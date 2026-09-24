# 09 — Machine Learning Models

**Status:** Planned.

The design question is not "which model wins" — it is **"does content predict engagement
beyond reach?"** The nested feature sets in §2 answer that. Everything else is supporting
detail.

---

## 1. Models

| Model | Configuration | Expectation at n=300 |
|---|---|---|
| **Baseline 0** — majority class | — | Floor. Any model below this is broken |
| **Baseline 1** — exposure only | Logistic Regression on controls | **The number that matters.** Content must beat this |
| Logistic Regression | L2, scaled inputs | Competitive at this n; highly interpretable |
| Decision Tree | Depth-limited | Weak alone; included for interpretability |
| Random Forest | class_weight balanced | Strong |
| XGBoost | class_weight balanced | **Expected winner** — matches the literature at this scale |
| MLP | 1–2 hidden layers, early stopping | **Expected to lose.** Report it: deep models need far more data, consistent with the survey |

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

**Check fold balance.** With ~20 accounts and 5 folds, a large account can dominate one
fold. Log accounts and class balance per fold.

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

**Report mean ± SD across folds, never a single split.** At n=300 fold-to-fold variance
will be large, and a single number would be misleading.

**Learning curves** for the best model. They show whether more data would have helped —
which directly addresses the sample-size limitation and pre-empts the obvious examiner
question.

---

## 5. Per-platform models

Fit YouTube-only and Instagram-only models (n≈150 each) for H9 and RQ7.

**These are underpowered.** Label them exploratory before running them, not after. Their
value is the SHAP comparison in [10](10-explainability.md), not their accuracy.

---

## 6. Results

_To be filled. Output: `reports/model_comparison.md`._

### Main comparison — mean ± SD over 5×3 grouped folds

| Model | Set | Acc | Prec | Rec | F1 | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|---|---|---|---|---|
| Majority | — | | | | | | | |
| Exposure-only | M0 | | | | | | | |
| LogReg | M1 | | | | | | | |
| LogReg | M2 | | | | | | | |
| Decision Tree | M2 | | | | | | | |
| Random Forest | M2 | | | | | | | |
| XGBoost | M1 | | | | | | | |
| XGBoost | M2 | | | | | | | |
| MLP | M2 | | | | | | | |

### The headline number

| Quantity | Value |
|---|---|
| Best M0 ROC-AUC (reach alone) | |
| Best M2 ROC-AUC (reach + content) | |
| **M2 − M0** | |
| 95% CI on the difference | |
| **Does content add beyond reach?** | |

### Per-platform (exploratory)

| Platform | n | Best model | ROC-AUC |
|---|---|---|---|
| YouTube | | | |
| Instagram | | | |

### Diagnostics

| Check | Result |
|---|---|
| Fold balance acceptable? | |
| Learning curve — would more data help? | |
| Selected threshold | |
| Calibration acceptable? | |

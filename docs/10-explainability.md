# 10 — Explainability (SHAP)

**Status:** Planned. Answers RQ10 and produces the interpretable core of the contribution.

---

## 1. Method

**TreeSHAP** on XGBoost and Random Forest — exact and fast for tree ensembles.
KernelSHAP only if the MLP needs explaining, and only if it performed well enough to be
worth explaining.

**Explain the M2 model** (content + exposure), not M1. The point is to see content
importance *alongside* exposure, not with exposure hidden.

**Stability check — do this first.** At n=300, SHAP values can be unstable. Compute SHAP
on each of the 5 outer folds and report the rank correlation of feature importance across
folds. If rankings are unstable, say so and interpret only the top few features. An
unstable SHAP ranking presented as a finding would be the most likely serious error in
this project.

---

## 2. Outputs

| Output | Purpose |
|---|---|
| Beeswarm summary plot | Global importance and direction, all features |
| Mean \|SHAP\| bar chart, **grouped by block A–E** | Answers "which modality matters most" — the grouping is what makes it an answer |
| Waterfall plots × 4 | One true positive, one true negative, one false positive, one false negative |
| Dependence plots | `duration`, `product_visible_frac`, emotion — recovers the shape, including non-linearity |
| **Per-platform SHAP comparison** | The key figure. Answers RQ7 and H9 in a form a marketer can read |
| SHAP interaction values | `duration × platform` for H10 |

**Block-grouped importance** is the figure that connects back to the proposal's structure:
sum mean |SHAP| within Blocks A (video), B (audio), C (text), D (creator), E (platform and
exposure). If Block E dominates, that is the honest headline — and it is exactly what the
exposure-aware literature predicts.

---

## 3. Per-platform comparison

Fit and explain YouTube and Instagram models separately, then compare feature rankings
side by side.

Underpowered at n≈150 each — present as exploratory, with the fold-stability check applied
per platform. Where a feature ranks high on one platform and low on the other, check
whether it is stable before making anything of it.

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
| | | | |

Rules to follow when writing it:

- Include only features stable across folds.
- State it as an empirical association, not a recommendation.
- Give separate profiles for YouTube and Instagram where they differ.
- Include the exposure caveat — a profile that ignores follower count would mislead a
  practitioner.

---

## 6. Results

_To be filled. Output: `reports/xai_findings.md`, `reports/figures/shap/`._

### Stability check

| Metric | Value |
|---|---|
| Spearman correlation of importance rankings across folds | |
| Features stable in the top 10 across all folds | |
| Interpretation limited to top ___ features | |

### Global importance by block

| Block | Sum mean \|SHAP\| | Rank |
|---|---|---|
| A — Video | | |
| B — Audio | | |
| C — Text | | |
| D — Creator | | |
| E — Platform / exposure | | |

### Top features

| Rank | Feature | Mean \|SHAP\| | Direction | Stable? |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

### Per-platform divergence

| Feature | YouTube rank | Instagram rank | Divergent? |
|---|---|---|---|

### Answers to the research questions

| RQ | Answer |
|---|---|
| RQ1 — which characteristics associate with engagement | |
| RQ7 — do predictors differ across platforms | |
| RQ9 — does content predict beyond exposure | |
| RQ10 — what does SHAP reveal | |

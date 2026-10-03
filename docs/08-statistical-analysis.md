# 08 — Statistical Analysis

**Status:** **Run 2026-10-01** (D-042 specification written first; results D-043; full output `reports/statistical_results.md` from `python -m src.stats.hypotheses`). This supplies the section missing from the proposal (which jumps from
EDA straight to Hypotheses). **The platform comparison (RQ7, H7, H9, H10) is pre-registered in
section 7 (2026-09-22, D-029); where section 7 and the rows below differ, section 7 wins.**

**Primary inferential model: linear mixed-effects with account random intercepts.**
Ordinary regression would treat 300 videos from ~20 accounts as 300 independent
observations. They are not, and OLS will overstate significance.

---

## 1. Test plan

| H | Claim | Test | Notes under the short-form design |
|---|---|---|---|
| H1 | Duration is associated with engagement | Spearman + regression **with quadratic term**, run separately per platform | Range now narrow (≤180s). Read as *within short form*. Munaro's medium/long finding is outside our range and cannot be confirmed or refuted here |
| H2 | Greater product visibility → higher effectiveness | Mann-Whitney U on median split, then MixedLM with controls | `product_visible_frac` is continuous — prefer the regression. **2026-09-29: not measured** — the detector failed its pre-set gate B, so H2 has no product-visibility instrument and rests on the Zero Sugar label alone (D-037) |
| H3 | Positive emotional content → higher engagement | Kruskal-Wallis across emotion labels, then MixedLM | Emotion measured post-translation — state it |
| H4 | Influencer/celebrity presence → higher engagement | Mann-Whitney U, then MixedLM | Check cell sizes first; may need to collapse to present/absent. **2026-09-29: the celebrity and creator labels failed α (0.10, 0.38; D-038)** - only human presence (`face_present_frac`, `mean_face_area`) remains |
| H5 | Clear CTA → higher effectiveness | Mann-Whitney U, then MixedLM | `has_cta` must have passed α ≥ 0.67. **2026-09-29: it did not** (α −0.03, D-038) - H5 has no validated instrument |
| H6 | Text characteristics associated with engagement | Multiple regression, MixedLM | Use invariant features; normalise caption length within language |
| H7 | Effectiveness differs between platforms | **Mixed model on log10 follower-normalised DV, section 7.5(a)**; Mann-Whitney U descriptive only | Never raw counts. Never mixed DV forms. Pre-registered in section 7 |
| H8 | Blocks jointly provide predictive power | Likelihood-ratio test, nested models | **This answers the new RQ9** |
| H9 | Predictors differ between platforms | Feature × platform interactions, or per-platform models compared | **Exploratory (section 7.7):** estimates and intervals only, outside the BH family |
| H10 | Platform moderates content effects | `duration × platform` interaction | **Exploratory (section 7.7)**, same treatment as H9 |

---

## 2. Model specification

**Primary:**

```
engagement_pct ~ content_features + exposure_controls + (1 | account)
```

`statsmodels.MixedLM`. Controls always included: `followers`, `video_age_days`,
`platform`, `language`/`region`, `sampling_tier`, and `brand` if tier-3 escalation was
used.

**Where cross-posted pairs exist**, cluster on `creative_id` as well, or add it as a
second random effect.

**The paired sub-analysis** (see [03](03-sampling-frame.md) §4): if ≥20 matched
cross-platform pairs exist, run a Wilcoxon signed-rank test on the pairs. Same creative,
two platforms — this is the cleanest available test of H7 and potentially the strongest
result in the thesis. Run it even if underpowered, and report the n.

---

## 3. Multiple comparisons

Ten hypotheses, many with several sub-tests. **Benjamini-Hochberg FDR correction across
the hypothesis family**, α = 0.05.

Report raw p, adjusted p, effect size and 95% CI for every test. A p-value without an
effect size is not a result at n=300.

Effect sizes: rank-biserial r for Mann-Whitney, ε² for Kruskal-Wallis, standardised β for
regression.

---

## 4. Power — read this before interpreting nulls

At n=300 (150/platform), the study is powered for medium effects and **not** for small
ones. Roughly, detecting d≈0.35 at 80% power needs ~130 per group; d≈0.2 needs ~390.

**Therefore: a null result is not evidence of no effect.** Every non-significant finding
must be reported as "not detected at this sample size", with the minimum detectable effect
stated. H9 and H10 are the most underpowered — split across platforms, each has ~150
observations for an interaction test. Label them exploratory in advance rather than
discovering the problem at the viva.

Run the power calculation before analysis and record it in §6.

---

## 5. Assumption checks

| Check | Action if violated |
|---|---|
| Normality of residuals | Log-transform DV, or rely on the non-parametric tests |
| Homoscedasticity | Robust standard errors |
| Multicollinearity (VIF > 5) | Already pruned in [05](05-feature-extraction.md); re-check post-pruning |
| Random-intercept variance ≈ 0 | If accounts genuinely do not differ, report it and fall back to OLS — it is a finding |
| Independence | Handled by the random effect; cross-posts by `creative_id` |

---

## 6. Results

**Filled 2026-10-01.** Output: `reports/statistical_results.md` (SHA-256 `ff50c35b...`), family table `reports/statistical_family.csv`. Focus set 192 videos / 22 accounts; the H1-H6/H8 models use the 179 complete cases (19 accounts), with a median-imputation sensitivity on all 192.

**Two computational notes, not specification changes:** (1) statsmodels' default optimiser stopped at a degenerate point on some fits (account variance 0, likelihood reported as infinite) or hit a singular Hessian; each model was therefore fitted with five optimisers and the highest finite likelihood kept (Powell in all 52 fits). (2) Three small accounts drop out of the complete cases.

### Label freeze for the platform comparison (section 7.4)

Recorded before any model was fitted and before any engagement value by platform was shown.

| Date | Frozen | SHA-256 |
|---|---|---|
| 2026-09-22 | Researcher's answers on all 125 text-unlabelled YouTube Shorts (`docs/zero_sugar_visual_check.csv`; read-only copy `docs/zero_sugar_visual_check_pass1_20260922.csv`): 49 Zero Sugar, 76 not, 0 unsure | `0d03a9e7c90fb7ec65bec9dd623e4f0433ac82c72c297353c64de9595a4505c7` |
| 2026-09-22 | Analysis table `data/processed/dependent_variable.parquet` with those answers applied: Zero Sugar YouTube 74 / 150 (72 / 144 usable), Instagram 112 / 150 (111 / 146 usable, unchanged) | `4d54d5a688a835c6562ee90cb3db9d964bc397963268fd7717729f5f1febcce6` |
| **2026-09-23** | **Re-freeze after D-030.** Same table plus the `in_focus` column (the focused scope, section 7.9): **183 usable rows in focus** - Instagram 111 / 16 accounts, YouTube 72 / 5 accounts - and 107 usable rows kept, flagged, as the robustness set. No engagement value, percentile or label changed: checked column by column against `dependent_variable_before_D030_20260923.parquet`, `in_focus` is the only addition. The percentile reference stays as computed over the whole corpus (researcher's decision, D-030) | `ceaead27d13075b4d5d594acee33d929c41b184ff8940a1a237ae7d6b2f30af1` |
| **2026-09-29** | **2c.R2 (D-039).** Researcher's by-eye answers on Instagram's 37 systematically drawn Reels that text does not name Zero Sugar, appended to the same answers file (orders 126-162; the 125 YouTube rows verified unchanged): **12 Zero Sugar, 25 not, 0 unsure**. Read-only copy `docs/zero_sugar_visual_check_pass2_20260929.csv` | `f2d3123fef552d1ba1e755432ed792dc5253323c38e6fb6af04302d3fb62fb2a` |
| **2026-09-29** | **Re-freeze after 2c.R2.** Labels re-applied with `src/screen/zero_sugar_labels.py`; table rebuilt by `src/process/dependent_variable.py`. **192 usable rows in focus - Instagram 120 / 17 accounts, YouTube 72 / 5** (was 183); 98 usable rows in the robustness set. Checked column by column against `dependent_variable_before_D039_20260929.parquet`: only `is_zero_sugar`, `zs_label_method` and `in_focus` changed, all on the 37 Reels; **no engagement value, percentile or engagement label changed** (compared without being displayed). Instagram's systematic Zero Sugar cell: **15 usable videos from 9 accounts - below the 20 the 7.9 contingency needs, so 7.5(c) is not run**. Repeat check on the 9 Reels also blind-coded on 15 Sep: **4 of 9 agree, alpha -0.10** | `ba6f0a2dceed49388de8a659e381adb0f74d650c67d6498dceba454d8ab97c23` |

If any label changes before the first model (for example the researcher's re-look at the *José vs
Mourinho* Shorts, or a check of Instagram's systematic Reels, D-029/D-030), the labels are
re-applied with `src/screen/zero_sugar_labels.py` and the table is re-frozen with a new dated row
here - never patched by hand. Label reliability to report with every result that uses the focus
set: 16 of 25 repeat answers agree, Krippendorff's alpha 0.25 (D-029, section 7.9.5). Under D-030
this label decides inclusion, not just a control. **Since 2026-09-29 also report the Instagram
by-eye label's repeat check: 4 of 9 agree, alpha -0.10 (D-039)** - it decides inclusion for 12
Reels.

### Power analysis

To be computed before any null is interpreted. The focused rows are the ones that matter now
(section 7.9.6); the 300-video rows belong to the robustness set.

**Computed 2026-10-01 for the focus set (192 / 22), before any test** - `python -m src.stats.power`,
full table and method in `reports/power_analysis.md`. Sample sizes and account spread only; no
engagement value was read. Each cell: minimum detectable effect at 80% power, two-sided alpha 0.05,
for ICC 0 / 0.1 / 0.3 (the fitted ICC from model (a) is reported with every null). `d` = yes/no
feature split in halves; `r` = continuous feature. The ICC columns are a cautious upper bound: most
features vary within an account, which the mixed model uses.

| Test family | n | Accounts | Minimum detectable effect (80% power) |
|---|---|---|---|
| **Focus set, pooled (D-030; 192 since D-039)** | **192** | 22 | d 0.41 / 0.77 / 1.25 · r 0.20 / 0.37 / 0.56 |
| **Focus set, Instagram** | **120** | 17 | d 0.52 / 0.79 / 1.17 · r 0.25 / 0.38 / 0.54 |
| **Focus set, YouTube** | **72** | 5 | d 0.67 / 1.73 / 4.01 · r 0.33 / 0.71 / 0.97 (one channel holds 58 - effectively very few independent units) |
| **Focus set, interactions (H9, H10)** | **192** | 22 | gap between the platforms' correlations (Fisher z) 0.43 / 0.98 / 2.16 - only very large differences detectable; exploratory (7.9.7) |
| Robustness set, pooled (290 usable) | 300 | 26 | |
| Robustness set, per platform (144 / 146 usable) | 150 | YouTube 5, Instagram 21 | |

### Hypothesis results

| H | Test | Statistic | Raw p | Adj. p | Effect size | 95% CI | Verdict |
|---|---|---|---|---|---|---|---|
| H1 | LR duration + duration^2 (MixedLM) · Spearman pooled | chi2 2.15 (df 2) · rho -0.045 | 0.341 · 0.533 | 0.494 · 0.678 | rho -0.045 | -0.19 to 0.10 | **Not detected** (min. detectable r 0.20 at ICC 0) |
| H2 | - | - | - | - | - | - | **Not tested** - product visibility not measured (D-037) |
| H3 | MixedLM caption sentiment · Kruskal-Wallis speech emotion | beta +0.10 · H 0.67 (df 3) | 0.178 · 0.881 | 0.415 · 0.949 | std beta +0.10 · eps2 0.006 | coef -0.013 to +0.070 | **Not detected** |
| H4 | LR face share + size · Mann-Whitney any face vs none | chi2 2.31 (df 2) · U 1936 | 0.316 · 0.788 | 0.494 · 0.919 | r_rb +0.036 | - | **Not detected** (celebrity / creator not measured, D-038) |
| H5 | - | - | - | - | - | - | **Not tested** - no validated instrument (D-038) |
| H6 | LR text block · Spearman caption length · Spearman hashtags | chi2 12.59 (df 5) · rho -0.001 · rho 0.244 | 0.028 · 0.984 · <0.001 | 0.149 · 0.984 · **0.009** | hashtags rho 0.244 | 0.11 to 0.37 (account-clustered 0.05 to 0.44) | **Hashtags detected - between accounts only** (within accounts rho 0.02); text block and caption length not detected |
| H7 | 7.9.3(a) platform coefficient | +0.470 log10 | 0.230 | 0.459 | ratio 10^b = 3.0 | 0.5 to 17.3 | **Not detected** by 7.9.4 (and (d), (a2), tier differences disagree in sign); selection caveat stands |
| H8 | LR all 20 features · video · audio · text blocks | chi2 28.36 (df 20) · 11.06 · 6.58 · 13.80 | 0.101 · 0.353 · 0.160 · 0.032 | 0.354 · 0.494 · 0.415 · 0.149 | - | - | **Not detected** (imputed sensitivity: all 20, p 0.042 unadjusted) |
| H9 | Feature x platform, 20 models (exploratory) | - | - | - | 8 of 20 intervals exclude 0 | see report | **Exploratory only**, not tested |
| H10 | Duration x platform (exploratory) | +0.098 per SD | - | - | - | -0.012 to +0.207 | **Exploratory only** - interval includes 0 |

### Mixed-effects model

Full H8 model (percentile ~ controls + 20 features + (1 | account), REML, n 179): every content
coefficient's interval includes 0 (table in `reports/statistical_results.md`); largest standardised
betas `kw_event` -0.43, `ocr_mean_text_area` -0.19, `colourfulness` +0.18, `hashtag_count` +0.17.

**Account random-intercept variance:** H7 model (log10 rate) 0.407 against residual 0.670.
**ICC:** **0.38** on the log10 rate (H7 model) and **0.30** on the percentile (full H8 model) -
roughly a third of the variation in engagement belongs to the account rather than the video. Residuals
pass the normality check (Shapiro-Wilk p 0.24) and show no spread pattern (Spearman -0.06).

### Paired sub-analysis

| Metric | Value |
|---|---|
| Matched pairs found | **2** (rule fixed before looking; D-040) |
| Wilcoxon statistic | not run - fewer than the 20 pairs required (task 8.3 closed) |
| p | - |
| Median difference | - |

---

## 7. Pre-registered platform comparison (D-029)

**Registered 2026-09-22, before any platform comparison was run.** Covers RQ7, H7, H9, H10 and
EDA 8. Any departure from this section when the analysis is run is reported as a deviation,
with its reason, next to the result it affects.

### 7.1 Why this section exists

The two platform samples were built differently, so a raw YouTube-vs-Instagram difference is
entangled with product and with how videos were chosen:

| | YouTube (150) | Instagram (150) |
|---|---|---|
| How videos entered | All 25 Shorts naming Zero Sugar in text + 125 random (seed 20260911) | **107 hand-picked** from the researcher's Zero Sugar list (106 kept as Zero Sugar, 1 relabelled Original) + 6 text-found Zero Sugar + 37 random |
| Zero Sugar, usable DV rows (2026-09-22) | 25 / 144 | 111 / 146 |
| Accounts with usable rows | **5** (one channel holds 117 of 144) | **21** |
| Follower tier "large" (>1M), usable rows | 117 / 144 | 45 / 146 |

Text screening undercounts Zero Sugar: it caught 29 of 98 researcher-verified Zero Sugar
Reels, and in the researcher's blind coding of 30 random Shorts, 13 showed Zero Sugar on
screen but only 5 were text-labelled. The YouTube Zero Sugar label is therefore being
re-checked visually (D-029, task 5.4) before this analysis runs.

### 7.2 What had already been seen - disclosure

Before this registration, two engagement descriptives by platform had been produced and seen,
because `src/process/dependent_variable.py` printed them on every run (2026-09-15, re-run
2026-09-21):

1. Per-platform distribution of `engagement_rate_follower` (docs/06 section 7): median 0.0048%
   YouTube, 0.27% Instagram. This was used to choose the within-platform percentile DV.
2. Median within-platform percentile by `is_zero_sugar`, per platform (Instagram 0.42 not Zero
   Sugar / 0.52 Zero Sugar; YouTube 0.48 / 0.64), under the pre-D-029 labels.

No model has been fitted and no test has been run. From 2026-09-22 the script hides engagement
values unless `--show-outcomes` is passed.

**Addendum 2026-09-29 - Phase 7 exploration (researcher's go-ahead).** Run on the table frozen that
day (192 focus videos), after the focus set was fixed, as docs/07 §1b registers: composition tables
first, then descriptive medians of log10 follower-normalised engagement by platform (Instagram
-2.55, YouTube -4.32) and by selection route, and descriptive feature-vs-percentile plots. **No test,
p-value or model.** Nothing in §7.9 was changed after these were seen.

### 7.3 Outcome for every platform comparison

`log10(engagement_rate_follower)`, where `engagement_rate_follower = (likes + comments) /
followers` (D-005). **Not** `engagement_pct`: the percentile is ranked within platform x
follower tier, so it has the same distribution on both platforms by construction and cannot
carry a platform difference. If any usable row has a rate of 0, a constant of half the
smallest positive rate is added before the log, and the number of rows affected is reported.

Rows: `dv_status == "ok"` in `data/processed/dependent_variable.parquet`.

### 7.4 When it runs

Only after the Zero Sugar labels are frozen: the researcher has answered every video on the
visual-check list (`docs/zero_sugar_visual_check.csv`), `is_zero_sugar` has been rebuilt from
text / researcher_curated / clip_then_researcher (D-029), and the SHA-256 of the analysis table
is recorded in section 6 before the first model is fitted.

### 7.5 Analyses

**(a) Main model.**

```
log10_er ~ platform + is_zero_sugar + follower_tier + log10(video_age_days) + (1 | account)
```

`statsmodels.MixedLM`, REML, random intercept per account (the D-006 grouping; `account` is
the channel on YouTube and the Coca-Cola account a Reel was collected from on Instagram).
`follower_tier` = large (>1M) vs small+medium (<=1M), the cells the DV uses (docs/06 section 7).
`log10(video_age_days)` is included because docs/08 section 2 lists age as a control that is
always in, and D-019 keeps it as a covariate; it is the only term beyond the platform,
Zero Sugar and follower-tier controls asked for. Region and language are left out: they vary
almost entirely between accounts, which the random intercept already absorbs.

- **Estimand:** the platform coefficient (Instagram minus YouTube), reported as
  `10^beta` - the ratio of engagement rates - with a 95% confidence interval.
- **Report with it:** accounts per platform, videos per account, the account variance and ICC.
- **Minimum-assumption check (a2):** one value per account (median `log10_er`), Instagram
  accounts vs YouTube accounts, Mann-Whitney U. With 5 YouTube accounts this is weak, and it is
  there to show how much of the video-level result rests on account differences.

**(b) Like with like.** Zero Sugar vs Zero Sugar and not-Zero-Sugar vs not-Zero-Sugar, across
platforms. First a table of **videos and accounts in every cell** (platform x `is_zero_sugar`,
and platform x `is_zero_sugar` x `selection`). Then, in each Zero Sugar stratum, model (a)
without the `is_zero_sugar` term. A stratum is tested only if **each platform has at least 20
videos and at least 3 accounts** in it; otherwise it is reported descriptively (median `log10_er`
with an account-clustered bootstrap 95% interval) and no test is run.

**(c) Sensitivity - without hand-picked Reels.** Re-run (a) and (b) on
`selection == "systematic"` only, i.e. dropping the 107 hand-picked Reels (106 Zero Sugar + 1
relabelled Original). `selection` exists only on Instagram, so it is perfectly tied to platform
among hand-picked rows and cannot be a control in a pooled model; that is why it is a separate
re-run rather than a term.

**(d) Sensitivity - without the dominant YouTube channel.** Re-run (a) without the global
Coca-Cola channel (117 of 144 usable Shorts), to show whether "YouTube" in (a) is mostly one
channel. Reported as a robustness check; YouTube then has about 27 videos from 4 accounts.

### 7.6 What counts as "the result holds" - decided now

| Verdict | Rule |
|---|---|
| **Holds** | (a) 95% CI for the platform coefficient excludes 0, **and** the sign is the same in (a2), in every testable stratum of (b), and in (c) |
| **Direction consistent, not robust** | (a) excludes 0 and no testable analysis reverses the sign, but one or more of (b)/(c) has a CI that includes 0 |
| **Not robust to sample composition** | The sign reverses in any testable stratum of (b) or in (c) |
| **Not detected** | (a) 95% CI includes 0 - reported as "not detected at this sample size", with the minimum detectable effect (section 4), never as "no difference" |

(d) is reported alongside and does not change the verdict; if it reverses the sign, the
result is described as driven by the global channel.

Only the platform coefficient from (a) enters the Benjamini-Hochberg family (section 3), as
H7. (a2), (b), (c) and (d) are robustness checks, not separate claims.

### 7.7 H9 and H10 are exploratory - decided now

H9 (predictors differ between platforms) and H10 (platform moderates content effects) are
**exploratory**. They are reported as effect estimates with 95% intervals, are **excluded from
the BH family**, and are not described as confirmed or significant, whatever their p-values.
Each is shown next to the same model restricted to `selection == "systematic"`, because the
hand-picked Reels are concentrated on one platform and one variant. H7's main test is model
(a); the Mann-Whitney U in section 1 is kept only as a descriptive comparison, since it ignores
accounts and composition.

### 7.8 Amendments

Dated; made before any engagement result by platform was produced. The text above is left as
registered.

| Date | Section | Amendment | Why |
|---|---|---|---|
| 2026-09-23 | 7.1-7.7 | **The design becomes Zero Sugar only** (D-030). `is_zero_sugar` stops being a control and becomes the inclusion criterion, so the like-with-like strata of 7.5(b) collapse; the "without hand-picked Reels" re-run of 7.5(c) is left with **6 Instagram videos from 5 accounts** and is no longer testable; the "without the global channel" re-run of 7.5(d) now leaves 14 YouTube videos, not 27. The focused plan is registered in full in **section 7.9**. 7.1-7.7 are left as registered and remain the plan for the wider 300-video set, which is kept as a robustness set - no row is deleted. | The supervisor answered the three questions in the week 3 report on 2026-09-23: analyse Coca-Cola Zero Sugar only; keep the YouTube vs Instagram comparison, with unequal counts per platform accepted. Registered before any model was fitted and before any engagement value by platform was produced. |
| 2026-09-22 | 7.4 | YouTube Zero Sugar labels come from the researcher's visual check of **every** Short that text does not label (125), recorded as `zs_label_method = researcher_visual_check`, instead of CLIP flags confirmed by the researcher (`clip_then_researcher`). The freeze condition is unchanged: all 125 answered, table rebuilt, SHA-256 recorded before the first model. | The pre-specified CLIP screen did not discriminate (AUC 0.58 on the 59 blind-coded videos; `reports/clip_zero_sugar_calibration.md`). A full check replaces a screen, so no CLIP threshold decides any label. |


### 7.9 Focused design - Zero Sugar only (registered 2026-09-23, D-030)

**Registered 2026-09-23**, before any model was fitted and before any engagement value by
platform was produced. Replaces 7.5 and 7.6 for the focused analysis; 7.1-7.4 and 7.7 still
apply as written. Sections 7.1-7.6 remain the plan for the wider 300-video robustness set.

**7.9.1 Sample.** `in_focus & dv_status == "ok"` in `data/processed/dependent_variable.parquet`:
**183 videos, 21 accounts** - Instagram 111 from 16 accounts, YouTube 72 from 5 accounts, 58 of
those 72 from the global Coca-Cola channel. Corpus rows in focus: 186 (3 Instagram Zero Sugar
Reels have hidden like counts and carry no outcome, D-005). Composition, videos (accounts):

| | Hand-picked | Systematic | Total |
|---|---|---|---|
| Instagram | 105 (13) | 6 (5) | 111 (16) |
| YouTube | - | 72 (5) | 72 (5) |

| | Large (>1M) | Small+medium (<=1M) | Total |
|---|---|---|---|
| Instagram | 32 (4) | 79 (13) | 111 (16) |
| YouTube | 58 (1) | 14 (4) | 72 (5) |

The 107 usable rows that are not Zero Sugar stay in the table, flagged `in_focus = False`, and
are never deleted (D-030). They are the robustness set of 7.1-7.6, not part of any result below.

**7.9.2 Outcome.** Unchanged from 7.3: `log10(engagement_rate_follower)`. The percentile
reference is also unchanged - ranks stay as computed against the whole 300-video corpus within
platform x follower tier (researcher's decision 2026-09-23, D-030; the alternative, ranking
within Zero Sugar only, would have left YouTube small+medium with 14 videos from 4 accounts).
The percentile is not the outcome of this comparison and cannot be: it is ranked within
platform (7.3).

**7.9.3 Analyses.**

**(a) Main model.** On the focus set:

```
log10_er ~ platform + follower_tier + log10(video_age_days) + (1 | account)
```

`is_zero_sugar` is dropped: it is constant by construction now, and product composition is
therefore held constant by design rather than controlled. Everything else is as 7.5(a) -
`statsmodels.MixedLM`, REML, random intercept per account; estimand the platform coefficient
(Instagram minus YouTube) reported as `10^beta` with a 95% confidence interval; reported with
accounts per platform, videos per account, account variance and ICC.

**(a2) Minimum-assumption check.** One value per account (median `log10_er`), 16 Instagram
accounts against 5 YouTube accounts, Mann-Whitney U. Weak by construction and descriptive only.

**(b) What replaces the like-with-like strata.** Nothing needs to replace the Zero Sugar strata:
with Zero Sugar only, the product composition that 7.5(b) existed to hold constant is constant.
Follower tier cannot take its place as a stratum - YouTube large is 58 videos from **one**
channel and YouTube small+medium is 14 videos, so neither meets the 20-videos-and-3-accounts
rule of 7.5(b). Follower tier therefore stays a covariate in (a) and is **reported descriptively
only**: per-cell n (videos and accounts) and median `log10_er` with an account-clustered
bootstrap 95% interval, with no test and no verdict resting on it.

**(c) The selection sensitivity can no longer be run, and this is a stated limitation.** Dropping
the hand-picked Reels leaves **6 Instagram videos from 5 accounts** against YouTube's 72, far
under the 7.5(b) rule, so the re-run registered in 7.5(c) is not performed. In the focused design
hand-picked selection is almost perfectly tied to platform - every hand-picked video is an
Instagram Reel, and 105 of Instagram's 111 focus videos are hand-picked - so **the platform
coefficient in (a) cannot be separated from the difference in how the two samples were built.**
That is reported next to the platform result, in those words, not buried in a limitations list.
What is still done:
- a descriptive comparison within Instagram only (105 hand-picked vs 6 systematic: medians with
  account-clustered bootstrap intervals, per-cell n, **no test**);
- **pre-specified contingency:** if the researcher's by-eye check of Instagram's 37 systematically
  drawn Reels (task 2c.R2) raises the systematic Zero Sugar cell to at least 20 videos from at
  least 3 accounts, the 7.5(c) re-run is performed exactly as first registered, and reported as a
  contingency that was specified in advance. Labels are re-applied and the table re-frozen first
  (7.9.5).

**(d) Sensitivity - without the dominant YouTube channel.** Kept, as 7.5(d), but the numbers have
changed: YouTube then has **14 videos from 4 accounts**, so the interval will be wide. Reported
as a robustness check that cannot overturn (a) on its own; if the model does not converge at that
size, the account-level medians are reported instead and that is stated.

**7.9.4 What counts as "the result holds" - decided now.** Replaces 7.6 for the focused design.

| Verdict | Rule |
|---|---|
| **Holds, with the selection caveat** | (a) 95% CI for the platform coefficient excludes 0, **and** the sign is the same in (a2) and in (d). The caveat of (c) is stated with it in every case |
| **Direction consistent, not robust** | (a) excludes 0, no analysis reverses the sign, but (d) or the follower-tier descriptives have intervals including 0 |
| **Not robust to sample composition** | The sign reverses in (a2), in (d), or in either follower-tier descriptive |
| **Not detected** | (a) 95% CI includes 0 - reported as "not detected at this sample size" with the minimum detectable effect from 7.9.6, never as "no difference" |

Only the platform coefficient from (a) enters the Benjamini-Hochberg family (section 3), as H7.
(a2), (b), (c) and (d) are robustness checks, not separate claims.

**7.9.5 The inclusion criterion is a weakly reliable label - report it with every result.** Under
D-029 the Zero Sugar label decided a control variable; under D-030 it decides **whether a video is
in the study at all**. Its reliability on YouTube is weak: the same coder's two looks agree for 16
of 25 Shorts (Krippendorff's alpha 0.25, bootstrap 95% CI -0.17 to 0.60), and 19 answers carry
notes suggesting some record repetition rather than packaging (D-029). Error is possible in both
directions - up to 15 Shorts of the repeated *José vs Mourinho* series may be excluded when they
should not be, and 6 of the 17 Shorts the blind codes called "other Coca-Cola" are included. So:
- every result that rests on the focus set is reported with this figure, and the label is never
  described as validated;
- if the researcher re-looks at the 36 *José vs Mourinho* Shorts (2c.R1) or checks Instagram's 37
  systematic Reels (2c.R2), the labels are re-applied with `src/screen/zero_sugar_labels.py`, the
  table is re-frozen with a new dated row in section 6, and every analysis is re-run from the new
  table. Numbers are never patched by hand.

**7.9.6 Power.** Section 4's minimum detectable effects were computed for n=300. They are
recomputed for **n=183 in 21 accounts** (and for YouTube's 5 accounts specifically) and recorded
in section 6 before any null result is interpreted. **Done 2026-10-01 for n=192 in 22 accounts**
(after D-039), before any test: section 6 and `reports/power_analysis.md`. A null at this size means "not detected",
and the ICC from (a) is reported with it, since 58 of 72 YouTube videos share one intercept.

**7.9.7 H9 and H10.** Still exploratory, exactly as 7.7: effect estimates with 95% intervals,
excluded from the BH family, never described as confirmed. The "restricted to
`selection == systematic`" variant that 7.7 asked for alongside them is unavailable for the same
reason as (c) (6 Instagram videos); the descriptive comparison in (c) is reported in its place,
and the absence of that check is stated.

**7.9.8 Freeze.** The analysis table carrying `in_focus` is recorded with its SHA-256 in section
6, dated 2026-09-23, before the first model.

# Power analysis - minimum detectable effects (docs/08 sections 4 and 7.9.6)

Computed from sample sizes and the spread of videos over accounts only; **no engagement value was read**. 80% power. `d` = standardised difference for a yes/no feature split in halves; `r` = correlation for a continuous feature. Columns give the effect at ICC 0 / 0.1 / 0.3 (share of engagement variance that belongs to the account; the fitted value comes from model (a) and is reported with every null).

| Test family | n | Accounts | m_eff | d, alpha 0.05 | r, alpha 0.05 | r, alpha 0.05/8 |
|---|---|---|---|---|---|---|
| Focus set, pooled | 192 | 22 | 26.4 | 0.41 / 0.77 / 1.25 | 0.20 / 0.37 / 0.56 | 0.25 / 0.46 / 0.67 |
| Focus set, Instagram | 120 | 17 | 13.7 | 0.52 / 0.79 / 1.17 | 0.25 / 0.38 / 0.54 | 0.32 / 0.47 / 0.64 |
| Focus set, YouTube | 72 | 5 | 47.5 | 0.67 / 1.73 / 4.01 | 0.33 / 0.71 / 0.97 | 0.41 / 0.82 / 0.99 |

**H9 / H10 (exploratory):** the smallest detectable difference between the two platforms' correlations, as a Fisher-z gap, is 0.43 / 0.98 / 2.16 at ICC 0 / 0.1 / 0.3 - roughly a correlation of 0.4 on one platform against none on the other at ICC 0. Platform differences in predictors of ordinary size cannot be detected; H9 and H10 stay estimates with intervals (7.9.7).

**YouTube:** 72 videos in 5 accounts, size-weighted cluster size 47.5 (one channel holds 58). At any realistic ICC its effective n is small, which is why no YouTube-only model is fitted (D-041).

**This is a cautious upper bound.** The design effect fully applies only to a feature that is constant within an account. Most of the 20 measures vary from video to video inside an account, and the mixed model uses that within-account variation, so the real minimum detectable effect lies between the ICC-0 column and the ICC columns.

Reading: Cohen's d 0.2 / 0.5 / 0.8 = small / medium / large; r 0.1 / 0.3 / 0.5 the same. **Only medium-to-large effects are detectable in the pooled focus set, and only large ones within a platform.** A null is reported as 'not detected at this sample size' with the value from this table, never as 'no effect'.

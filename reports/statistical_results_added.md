# P13 - H2, H4, H5 with the hand codes - a declared addition (D-050)

Focus set 192 videos, 22 accounts; complete cases per test. Outcome: engagement percentile (within platform x follower tier). Mixed model with an account intercept; controls platform, log followers, log video age (D-042). **The six tests below are their own Benjamini-Hochberg family (q = 0.05); the 14-test family of D-042 is unchanged.** Hand codes: one coder (9 Oct), 110 minutes for 100 minutes of video; repeat reliability (P11): call to action alpha 0.50, creator 0.38, celebrity 0.52, product none-vs-any 0.48 - all weakly reliable. Zero Sugar label: YouTube alpha 0.25, Instagram -0.10. Effects in percentile points (0-100).

## The addition family
| H | Measure | n (yes / no), accounts | Test | Effect (95% CI) | Raw p | BH p | Verdict | Without AI-character Shorts: raw p | Min. detectable d |
|---|---|---|---|---|---|---|---|---|---|
| H2 | product prominent vs none-or-brief | 192 (136 / 56), 22 | LR test (mixed model), 1 df | +10.4 pct points (+1.9 to +18.8) | 0.017 | 0.021 | **detected** | 0.680 (+1.9 pct points) | 0.45 |
| H2 | product prominent vs none-or-brief | 192 (136 / 56), 22 | Mann-Whitney U | r_rb +0.174; medians 0.564 vs 0.436 | 0.059 | 0.059 | **not detected at this sample size** | 0.935 (r_rb +0.009; medians 0.564 vs 0.538) | 0.45 |
| H4 | creator or celebrity vs neither | 129 (41 / 88), 17 | LR test (mixed model), 1 df | +14.3 pct points (+1.8 to +26.8) | 0.007 | 0.014 | **detected** | 0.081 (+9.0 pct points) | 0.53 |
| H4 | creator or celebrity vs neither | 129 (41 / 88), 17 | Mann-Whitney U | r_rb +0.285; medians 0.723 vs 0.462 | 0.009 | 0.014 | **detected** | 0.062 (r_rb +0.211; medians 0.723 vs 0.581) | 0.53 |
| H5 | call to action vs none | 192 (88 / 104), 22 | LR test (mixed model), 1 df | +11.0 pct points (+3.0 to +19.0) | 0.006 | 0.014 | **detected** | 0.154 (+5.4 pct points) | 0.41 |
| H5 | call to action vs none | 192 (88 / 104), 22 | Mann-Whitney U | r_rb +0.335; medians 0.662 vs 0.444 | <0.001 | <0.001 | **detected** | 0.002 (r_rb +0.274; medians 0.662 vs 0.485) | 0.41 |

Fits converged: H2 LR True, H2 Mann-Whitney True, H4 LR True, H4 Mann-Whitney True, H5 LR True, H5 Mann-Whitney True.

## Within-account check for each detected hypothesis (D-043 style; describes, changes no verdict)
- H2 (product prominent): with each account's mean removed, Spearman rho +0.181 (p 0.012, n 192) - the association holds within accounts.
- H4 (creator or celebrity): with each account's mean removed, Spearman rho +0.091 (p 0.305, n 129) - the association is mainly between accounts, not within them.
- H5 (call to action): with each account's mean removed, Spearman rho +0.187 (p 0.009, n 192) - the association holds within accounts.

## Outside the family - estimates only, never 'significant'
Four people groups (Kruskal-Wallis, n 129): epsilon^2 0.145; medians none 0.446 (61), ordinary_people 0.620 (27), influencer 0.510 (24), celebrity 0.931 (17). YouTube has no celebrity video, and the 17 celebrity videos come from 5 Instagram accounts.

Mixed-model coefficient of each other measure, added alone to the controls (percentile points, 95% CI):
| Measure | n | Coefficient | 95% CI | Without AI-character Shorts |
|---|---|---|---|---|
| logo prominent | 191 | +8.7 | +0.1 to +17.2 | +1.8 (-6.9 to +10.5) |
| excitement | 182 | +3.6 | -4.1 to +11.3 | +1.3 (-6.4 to +9.0) |
| excited voice | 191 | +1.5 | -7.6 to +10.6 | -4.3 (-12.9 to +4.4) |
| sponsored disclosed | 191 | +2.6 | -8.3 to +13.6 | -0.5 (-10.9 to +9.9) |
| lifestyle focus | 187 | -10.1 | -17.8 to -2.4 | -5.1 (-12.8 to +2.7) |
| homemade (UGC) look | 187 | +4.1 | -6.1 to +14.3 | +2.4 (-7.4 to +12.2) |
| music (reference: cinematic): no music | 189 | -3.5 | -13.0 to +6.1 | - |
| music (reference: cinematic): other | 189 | +15.8 | -0.3 to +31.9 | - |
| music (reference: cinematic): pop | 189 | +4.7 | -5.4 to +14.8 | - |
| campaign (reference: promotion): event | 173 | -14.8 | -25.8 to -3.7 | - |
| campaign (reference: promotion): food | 173 | +5.9 | -6.4 to +18.1 | - |
| campaign (reference: promotion): general or seasonal | 173 | -1.8 | -16.9 to +13.3 | - |
| campaign (reference: promotion): new product | 173 | +1.9 | -10.0 to +13.9 | - |

Wording (D-042): 'associated with', never 'causes'; a test not detected is 'not detected at this sample size' with its minimum detectable effect (a lower bound: account clustering makes it larger).

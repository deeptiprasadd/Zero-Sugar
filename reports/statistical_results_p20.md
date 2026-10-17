# P20 - speech rate, brand and product mentions, YouTube views - a declared addition (D-056)

Focus set 192 videos, 22 accounts; complete cases per test. Pooled tests: engagement percentile (within platform x follower tier), mixed model with an account intercept, controls platform, log followers, log video age (D-042). YouTube tests: log10 of (likes + comments) / views, controls log followers and log video age, 72 videos from 5 channels (58 from one). **The ten tests are their own Benjamini-Hochberg family (q = 0.05); the D-042 and D-050 families are unchanged.** Zero Sugar label: YouTube alpha 0.25, Instagram -0.10. Call to action: one coder, alpha 0.50. Zero view-based rates replaced before the log: 0.

Coverage: speech rate 112 videos; product named 53 yes / 120 no / 19 not searched; brand named 166 of 192 (every YouTube video: True; so its estimate rests on the 26 Reels that do not name it).

## The P20 family
| # | Outcome | Measure | n, accounts | Test | Effect (95% CI) | Raw p | BH p | Verdict | Without AI-character Shorts: effect, raw p | Min. detectable |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | percentile (pooled) | speech rate (words per minute) | 112, 16 | LR test (mixed model), 1 df | -1.4 pct points per SD (-8.6 to +5.8) | 0.925 | 0.925 | **not detected at this sample size** | +0.5 pct points per SD, 0.733 (n 97) | r 0.26 |
| 2 | percentile (pooled) | speech rate (words per minute) | 112, 16 | Spearman | rho -0.187 | 0.048 | 0.344 | **not detected at this sample size** | rho -0.127, 0.216 (n 97) | r 0.26 |
| 3 | percentile (pooled) | product named (Zero Sugar) | 173, 20 | LR test (mixed model), 1 df | +2.0 pct points yes vs no (-6.9 to +11.0) | 0.654 | 0.818 | **not detected at this sample size** | -2.4 pct points yes vs no, 0.584 (n 158) | d 0.46 (53 yes / 120 no) |
| 4 | percentile (pooled) | product named (Zero Sugar) | 173, 20 | Mann-Whitney U | r_rb +0.049; medians 0.578 vs 0.513 | 0.606 | 0.818 | **not detected at this sample size** | r_rb -0.033; medians 0.578 vs 0.554, 0.740 (n 158) | d 0.46 (53 yes / 120 no) |
| 5 | percentile (pooled) | brand named (Coca-Cola) | 192, 22 | LR test (mixed model), 1 df | -1.7 pct points yes vs no (-15.2 to +11.8) | 0.850 | 0.925 | **not detected at this sample size** | -1.5 pct points yes vs no, 0.853 (n 177) | d 0.59 (166 yes / 26 no) |
| 6 | percentile (pooled) | brand named (Coca-Cola) | 192, 22 | Mann-Whitney U | r_rb +0.181; medians 0.556 vs 0.403 | 0.138 | 0.344 | **not detected at this sample size** | r_rb +0.255; medians 0.581 vs 0.403, 0.038 (n 177) | d 0.59 (166 yes / 26 no) |
| 7 | view-based rate (YouTube) | hashtags | 72, 5 | LR test (mixed model), 1 df | x1.18 per-view rate per SD (0.97 to 1.44) | 0.096 | 0.344 | **not detected at this sample size** | x1.31 per-view rate per SD, 0.024 (n 57) | r 0.33 |
| 8 | view-based rate (YouTube) | hashtags | 72, 5 | Spearman | rho +0.125 | 0.297 | 0.594 | **not detected at this sample size** | rho +0.120, 0.373 (n 57) | r 0.33 |
| 9 | view-based rate (YouTube) | call to action (hand-coded) | 72, 5 | LR test (mixed model), 1 df | x0.71 per-view rate yes vs no (0.45 to 1.13) | 0.119 | 0.344 | **not detected at this sample size** | x0.70 per-view rate yes vs no, 0.160 (n 57) | d 0.67 (32 yes / 40 no) |
| 10 | view-based rate (YouTube) | call to action (hand-coded) | 72, 5 | Mann-Whitney U | r_rb -0.062; medians -1.942 vs -1.867 | 0.654 | 0.818 | **not detected at this sample size** | r_rb -0.175; medians -1.942 vs -1.825, 0.264 (n 57) | d 0.67 (32 yes / 40 no) |

Fits converged: #1 True, #2 True, #3 True, #4 True, #5 True, #6 True, #7 True, #8 True, #9 True, #10 True.

## Description only - the two YouTube engagement measures side by side
Spearman between the view-based rate and the follower-based percentile, 72 YouTube videos: rho -0.047 (without the AI-character Shorts -0.106, n 57). No test; per docs/06 the view-based measure is within-YouTube only and is never carried into a platform comparison.

Wording (D-042, D-056): 'associated with', never 'causes'; a test not detected is 'not detected at this sample size' with its minimum detectable effect (a lower bound: account clustering makes it larger).

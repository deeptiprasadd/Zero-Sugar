# 5.4 product on screen - validation (D-032 pending; gates fixed before scoring)

Truth: the researcher's blind codes, **54 videos with a Coca-Cola product visible vs 5 with none** ('unsure' dropped). The negative class is tiny, so every figure here is weak evidence and is reported as such.

| Check | Result | Gate | Pass |
|---|---|---|---|
| A. ROC AUC, `product_prob_mean` | **0.419** (95% CI 0.14-0.72) | >= 0.70 | NO |
| B. All no-product videos in the bottom half | ranks 0.72, 0.94, 0.72, 0.16, 0.51 | all <= 0.50 | NO |
| C. Not near-constant (10th-90th spread) | 0.720 | >= 0.10 | YES |

Sensitivity: AUC using the **best** square instead of the mean is 0.485 (the D-029 failure mode); AUC of the thresholded `product_visible_frac` is 0.406.

Median `product_prob_mean`: product visible 0.523, no product 0.630.

**Verdict: FAILED - product visibility is not measured this way; try YOLO before using anything.**
(Gate C, spread, passed - it guards against a constant feature, not against being wrong.)

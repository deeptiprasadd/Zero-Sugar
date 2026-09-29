# 5.4 product on screen - validation (D-033)

**120 of 120 sampled frames answered.** Frames drawn at random, one per video, 60 videos per platform, seed 20260928 - before any score was computed, and the answering page never showed a score or a box.

## Frame level - the check that matters

| Measure | Truth | ROC AUC | 95% CI | Frames |
|---|---|---|---|---|
| YOLO container confidence | container visible | **0.748** | 0.66-0.84 | 38 yes / 82 no |
| YOLO container confidence | Coca-Cola product | **0.741** | 0.65-0.83 | 37 yes / 83 no |
| CLIP prompt score (failed attempt) | container visible | **0.844** | 0.77-0.91 | 38 yes / 82 no |
| CLIP prompt score (failed attempt) | Coca-Cola product | **0.840** | 0.76-0.90 | 37 yes / 83 no |

At the pre-set threshold 0.25: **32 frames flagged**, of which 69% really hold a container (precision) and 66% hold a **Coca-Cola** product; recall 58% of the frames the researcher says have a container. Missed frames (16 of 88 unflagged) are where the object is small, blurred or partly out of shot.

Of every answered frame with a container, **97% are Coca-Cola's** - that ratio is why a brand-blind detector is a usable proxy here, and it is the number to quote when the feature is described.

## Gates

| Gate | Result | Required | Pass |
|---|---|---|---|
| A. Frame-level AUC, container | 0.748 (95% CI 0.66-0.84) | >= 0.70 | YES |
| B. No-product videos in the bottom half | ranks 0.60, 0.10, 0.36, 0.24, 0.10 | all <= 0.50 | NO |
| C. Not near-constant (10th-90th spread) | 0.745 | >= 0.10 | YES |

**Verdict: FAILED.** Product visibility is reported as not measured (D-033 option C); H2, RQ4 and 5.17 then rest on the Zero Sugar label alone.

### Sensitivity

| Threshold | Frames flagged | Precision | Recall |
|---|---|---|---|
| 0.15 | 35 | 66% | 61% |
| 0.25 | 32 | 69% | 58% |
| 0.4 | 29 | 72% | 55% |

The first attempt (whole-image CLIP) is kept in the table above so the two are comparable on identical frames; its failure is recorded in D-033.

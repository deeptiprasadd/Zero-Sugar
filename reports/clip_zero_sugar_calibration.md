# CLIP Zero Sugar screen - calibration (D-029)

> **Result of the first, pre-specified design: it does not discriminate. Not used.**
> The F2 rule chose the lowest possible threshold (0.105) and flagged every video - recall 1.00
> only because nothing was ruled out; 0 true negatives. Threshold-free check (ROC AUC, blind-coded
> videos, 2,000 bootstrap resamples): **all 0.58 (0.43-0.73), YouTube 0.76 (0.55-0.93), Instagram
> 0.45 (0.22-0.68)**. Cause: video score = best of ~150 squares per video saturates - 96% of all
> 300 videos have a square scoring >= 0.5 (median video score 0.98), because a dark scene or any
> black object wins the softmax against the other prompts. The F2 rule compounded it: tuning on
> 86 extra positives against 25 negatives made "flag everything" the cheapest choice.
> Outputs of this attempt were renamed `*_first_attempt*` so they cannot be mistaken for the list
> to answer. No label was changed.

Model ViT-L-14 (laion/CLIP-ViT-L-14-laion2B-s32B-b82K); frames scored as top/middle/bottom squares; video score = max frame score. Threshold rule: maximise F2 on the training videos.

Ground truth: 59 blind-coded videos (34 Zero Sugar); 87 further curated Reels used for tuning only (86 Zero Sugar, 1 relabelled Original).

| Evaluation | n | TP | FP | FN | TN | Precision (95% CI) | Recall (95% CI) |
|---|---|---|---|---|---|---|---|
| Leave-one-out, all blind-coded | 59 | 34 | 25 | 0 | 0 | 0.58 (0.45-0.69) | 1.00 (0.90-1.00) |
| Leave-one-out, YouTube only | 29 | 13 | 16 | 0 | 0 | 0.45 (0.28-0.62) | 1.00 (0.77-1.00) |
| Leave-one-out, Instagram only | 30 | 21 | 9 | 0 | 0 | 0.70 (0.52-0.83) | 1.00 (0.85-1.00) |
| Transfer: tuned on Instagram, tested on YouTube | 29 | 13 | 16 | 0 | 0 | 0.45 (0.28-0.62) | 1.00 (0.77-1.00) |

Leave-one-out thresholds ranged 0.105-0.105. Instagram-only threshold 0.105. **Final threshold for the list: 0.105.**

Listed for the researcher: 165 videos - ('instagram', 'clip_flag') 32, ('instagram', 'clip_flag+blind_code') 4, ('instagram', 'fyi_curated_vs_blind_code') 4, ('youtube', 'clip_flag') 117, ('youtube', 'clip_flag+blind_code') 8

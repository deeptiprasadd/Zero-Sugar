# P15 - confusion matrices (D-050)

Repeat 1 of the 5 x 3 account-grouped folds; each video predicted once by the fold model that did not see it. Check passed: every fold's ROC-AUC from the saved predictions equals the logged value (largest difference 8.3e-17). Cells: TP / FP / FN / TN (high = positive).

## Pooled (192 videos)

| Model | Set | F1 rule: TP / FP / FN / TN | Accuracy | Youden rule: TP / FP / FN / TN | Accuracy |
|---|---|---|---|---|---|
| Majority | M0 | 100 / 92 / 0 / 0 | 0.52 | 100 / 92 / 0 / 0 | 0.52 |
| Majority | M1 | 100 / 92 / 0 / 0 | 0.52 | 100 / 92 / 0 / 0 | 0.52 |
| Majority | M2 | 100 / 92 / 0 / 0 | 0.52 | 100 / 92 / 0 / 0 | 0.52 |
| LogReg | M0 | 97 / 89 / 3 / 3 | 0.52 | 66 / 63 / 34 / 29 | 0.49 |
| LogReg | M1 | 96 / 91 / 4 / 1 | 0.51 | 35 / 37 / 65 / 55 | 0.47 |
| LogReg | M2 | 93 / 89 / 7 / 3 | 0.50 | 44 / 49 / 56 / 43 | 0.45 |
| DecisionTree | M0 | 97 / 87 / 3 / 5 | 0.53 | 67 / 55 / 33 / 37 | 0.54 |
| DecisionTree | M1 | 97 / 91 / 3 / 1 | 0.51 | 49 / 49 / 51 / 43 | 0.48 |
| DecisionTree | M2 | 92 / 88 / 8 / 4 | 0.50 | 74 / 73 / 26 / 19 | 0.48 |
| RandomForest | M0 | 88 / 85 / 12 / 7 | 0.49 | 67 / 72 / 33 / 20 | 0.45 |
| RandomForest | M1 | 90 / 85 / 10 / 7 | 0.51 | 69 / 64 / 31 / 28 | 0.51 |
| RandomForest | M2 | 98 / 91 / 2 / 1 | 0.52 | 39 / 41 / 61 / 51 | 0.47 |
| XGBoost | M0 | 89 / 85 / 11 / 7 | 0.50 | 42 / 40 / 58 / 52 | 0.49 |
| XGBoost | M1 | 93 / 86 / 7 / 6 | 0.52 | 45 / 46 / 55 / 46 | 0.47 |
| XGBoost | M2 | 94 / 88 / 6 / 4 | 0.51 | 31 / 42 / 69 / 50 | 0.42 |
| MLP | M0 | 89 / 85 / 11 / 7 | 0.50 | 31 / 38 / 69 / 54 | 0.44 |
| MLP | M1 | 90 / 82 / 10 / 10 | 0.52 | 54 / 58 / 46 / 34 | 0.46 |
| MLP | M2 | 99 / 92 / 1 / 0 | 0.52 | 81 / 81 / 19 / 11 | 0.48 |

## Instagram only (120 videos, exploratory)

| Model | Set | F1 rule: TP / FP / FN / TN | Accuracy | Youden rule: TP / FP / FN / TN | Accuracy |
|---|---|---|---|---|---|
| LogReg | M0 | 59 / 59 / 2 / 0 | 0.49 | 51 / 54 / 10 / 5 | 0.47 |
| LogReg | M1 | 57 / 48 / 4 / 11 | 0.57 | 23 / 13 / 38 / 46 | 0.57 |
| LogReg | M2 | 58 / 54 / 3 / 5 | 0.53 | 16 / 18 / 45 / 41 | 0.47 |
| XGBoost | M0 | 39 / 50 / 22 / 9 | 0.40 | 23 / 36 / 38 / 23 | 0.38 |
| XGBoost | M1 | 47 / 31 / 14 / 28 | 0.62 | 31 / 16 / 30 / 43 | 0.62 |
| XGBoost | M2 | 46 / 34 / 15 / 25 | 0.59 | 32 / 14 / 29 / 45 | 0.64 |

The registered F1 rule often predicts nearly every video 'high' (D-044 note), which shows here as few predicted lows. Figure: `reports/figures/confusion_matrices.png`.

"""P15 - confusion matrices from the saved out-of-fold predictions, exactly as fixed in D-050.

Repeat 1 of the 5 x 3 account-grouped folds: each video is predicted once, by the fold model that did
not see it (`reports/model_oof_predictions.csv`). Each fold's thresholds - the registered F1 rule and the
Youden rule - come from `reports/model_fold_results.csv`. Fold membership is recomputed with the same
splitter and seed and checked: each fold's ROC-AUC from the saved predictions must equal the logged one.

Usage:
    python -m src.models.confusion
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from sklearn.model_selection import StratifiedGroupKFold  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.eda.explore import INK, INK2  # noqa: E402  (also sets the figure style)
from src.models.train import SEEDS, build  # noqa: E402

OUT = config.REPORTS / "confusion_matrices.md"
FIG = config.REPORTS / "figures" / "confusion_matrices.png"
ORDER = ["Majority", "LogReg", "DecisionTree", "RandomForest", "XGBoost", "MLP"]


def fold_of(df: pd.DataFrame) -> pd.Series:
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEEDS[0])
    fold = pd.Series(-1, index=df["media_id"])
    for k, (_, b) in enumerate(outer.split(df, df["y"], df["account"])):
        fold.iloc[b] = k
    return fold


def matrices() -> tuple[pd.DataFrame, float]:
    df = build()
    data = {"pooled": df, "instagram": df[df["platform"] == "instagram"].reset_index(drop=True)}
    oof = pd.read_csv(config.REPORTS / "model_oof_predictions.csv", dtype={"media_id": str})
    logged = pd.read_csv(config.REPORTS / "model_fold_results.csv")
    logged = logged[logged["repeat"] == 0]
    rows, worst = [], 0.0
    for tag, d in data.items():
        fold = fold_of(d)
        for (model, s), g in oof[oof["data"] == tag].groupby(["model", "set"]):
            g = g.assign(fold=g["media_id"].map(fold))
            lg = logged[(logged["data"] == tag) & (logged["model"] == model) & (logged["set"] == s)].set_index("fold")
            cells = {"f1": np.zeros(4, int), "j": np.zeros(4, int)}
            for k, gk in g.groupby("fold"):
                y, p = gk["y"].to_numpy(), gk["p"].to_numpy()
                if len(set(y)) > 1:
                    worst = max(worst, abs(roc_auc_score(y, p) - lg.loc[k, "roc_auc"]))
                for rule, col in (("f1", "threshold"), ("j", "threshold_j")):
                    yhat = (p >= lg.loc[k, col]).astype(int)
                    cells[rule] += [int(((yhat == 1) & (y == 1)).sum()), int(((yhat == 1) & (y == 0)).sum()),
                                    int(((yhat == 0) & (y == 1)).sum()), int(((yhat == 0) & (y == 0)).sum())]
            rows.append({"data": tag, "model": model, "set": s, "n": len(g),
                         **{f"{r}_{c}": v for r in cells for c, v in zip(("tp", "fp", "fn", "tn"), cells[r])}})
    return pd.DataFrame(rows), worst


def figure(t: pd.DataFrame) -> None:
    picks = [("pooled", "LogReg", "M0", "Pooled logistic regression, M0 (reach only)"),
             ("pooled", "XGBoost", "M2", "Pooled XGBoost, M2 (reach + content)"),
             ("instagram", "LogReg", "M1", "Instagram logistic regression, M1 (content only)")]
    fig, axes = plt.subplots(2, 3, figsize=(11.5, 7.2))
    for c, (tag, model, s, title) in enumerate(picks):
        r = t[(t["data"] == tag) & (t["model"] == model) & (t["set"] == s)].iloc[0]
        for k, (rule, name) in enumerate((("f1", "registered F1 threshold"), ("j", "Youden threshold"))):
            ax = axes[k, c]
            m = np.array([[r[f"{rule}_tn"], r[f"{rule}_fp"]], [r[f"{rule}_fn"], r[f"{rule}_tp"]]])
            ax.imshow(m, cmap="Blues", vmin=0, vmax=r["n"] * 0.7)
            for i in range(2):
                for j in range(2):
                    ax.text(j, i, str(m[i, j]), ha="center", va="center", fontsize=13,
                            color="white" if m[i, j] > r["n"] * 0.4 else INK)
            ax.set_xticks([0, 1], ["predicted low", "predicted high"])
            ax.set_yticks([0, 1], ["actually low", "actually high"])
            ax.grid(False)
            acc = (r[f"{rule}_tp"] + r[f"{rule}_tn"]) / r["n"]
            ax.set_title(f"{title}\n{name} - accuracy {acc:.2f}" if k == 0 else f"{name} - accuracy {acc:.2f}",
                         loc="left", fontsize=8.5)
    fig.suptitle("Confusion matrices, repeat 1 of the account-grouped folds (each video predicted once)",
                 x=0.01, ha="left", fontsize=10, fontweight="bold", color=INK)
    fig.text(0.01, -0.01, "Pooled: 192 videos, 22 accounts. Instagram: 120 videos, 17 accounts (exploratory).",
             fontsize=8, color=INK2)
    fig.tight_layout()
    fig.savefig(FIG, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t, worst = matrices()
    if worst > 1e-9:
        raise SystemExit(f"fold membership does not reproduce the logged ROC-AUCs (max difference {worst}) - stopped")
    figure(t)
    lines = ["# P15 - confusion matrices (D-050)", "",
             "Repeat 1 of the 5 x 3 account-grouped folds; each video predicted once by the fold model that did not "
             f"see it. Check passed: every fold's ROC-AUC from the saved predictions equals the logged value "
             f"(largest difference {worst:.1e}). Cells: TP / FP / FN / TN (high = positive).", ""]
    for tag in ("pooled", "instagram"):
        lines += [f"## {'Pooled (192 videos)' if tag == 'pooled' else 'Instagram only (120 videos, exploratory)'}", "",
                  "| Model | Set | F1 rule: TP / FP / FN / TN | Accuracy | Youden rule: TP / FP / FN / TN | Accuracy |",
                  "|---|---|---|---|---|---|"]
        s = t[t["data"] == tag].copy()
        s["o"] = s["model"].map(ORDER.index)
        for r in s.sort_values(["o", "set"]).itertuples():
            a1 = (r.f1_tp + r.f1_tn) / r.n
            a2 = (r.j_tp + r.j_tn) / r.n
            lines.append(f"| {r.model} | {r.set} | {r.f1_tp} / {r.f1_fp} / {r.f1_fn} / {r.f1_tn} | {a1:.2f} | "
                         f"{r.j_tp} / {r.j_fp} / {r.j_fn} / {r.j_tn} | {a2:.2f} |")
        lines.append("")
    lines += ["The registered F1 rule often predicts nearly every video 'high' (D-044 note), which shows here as few "
              "predicted lows. Figure: `reports/figures/confusion_matrices.png`."]
    t.to_csv(config.REPORTS / "confusion_matrices.csv", index=False)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

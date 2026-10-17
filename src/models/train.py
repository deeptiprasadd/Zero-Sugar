"""Phase 9 - does content predict engagement beyond reach? Exactly as fixed in D-044 (docs/09, D-041).

Target `engagement_high` on the focus set (192 videos, 22 accounts). Feature sets M0 (reach and
exposure), M1 (the 20 content features), M2 (both). Six models, account-grouped 5-fold CV repeated
3 times, tuning on account-grouped inner folds, threshold chosen on training out-of-fold predictions,
imputation and scaling inside every training fold. Headline: M2 - M0 ROC-AUC per model, and XGBoost
M2 against the reach-only logistic baseline, with the corrected resampled t-test.

Usage:
    python -m src.models.train            # everything (about an hour on 12 threads)
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402
from sklearn.base import clone  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.dummy import DummyClassifier  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,  # noqa: E402
                             f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import RandomizedSearchCV, StratifiedGroupKFold  # noqa: E402
from sklearn.neural_network import MLPClassifier  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from sklearn.tree import DecisionTreeClassifier  # noqa: E402
from xgboost import XGBClassifier  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import derived  # noqa: E402
from src.stats.hypotheses import RAW, load  # noqa: E402

OUT = config.REPORTS / "model_comparison.md"
PRED = config.REPORTS / "model_oof_predictions.csv"
FIG = config.REPORTS / "figures"
MODELS = config.ROOT / "models"
SEEDS = (42, 1042, 2042)
N_ITER = 20

M1 = list(RAW.values())          # the 20 content features, raw (scaled inside the pipeline)
M0 = ["log_followers", "log_age", "tier_large", "tier_medium", "platform_ig", "hour_sin", "hour_cos",
      "weekend"]
SETS = {"M0": M0, "M1": M1, "M2": M0 + M1}

GRIDS = {
    "Majority": (DummyClassifier(strategy="prior"), {}),
    "LogReg": (LogisticRegression(max_iter=5000),
               {"m__C": [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100]}),
    "DecisionTree": (DecisionTreeClassifier(random_state=0),
                     {"m__max_depth": [2, 3, 4, 5, 6, None], "m__min_samples_leaf": [2, 5, 10, 20],
                      "m__criterion": ["gini", "entropy"]}),
    "RandomForest": (RandomForestClassifier(n_estimators=500, class_weight="balanced", random_state=0, n_jobs=1),
                     {"m__max_depth": [2, 3, 5, 8, None], "m__min_samples_leaf": [1, 2, 5, 10],
                      "m__max_features": ["sqrt", 0.3, 0.5]}),
    "XGBoost": (XGBClassifier(tree_method="hist", eval_metric="logloss", random_state=0, n_jobs=1, verbosity=0),
                {"m__n_estimators": [100, 200, 400], "m__max_depth": [2, 3, 4],
                 "m__learning_rate": [0.01, 0.03, 0.1], "m__subsample": [0.7, 0.9, 1.0],
                 "m__colsample_bytree": [0.5, 0.7, 1.0], "m__min_child_weight": [1, 3, 5],
                 "m__reg_lambda": [1, 5, 10]}),
    "MLP": (MLPClassifier(early_stopping=True, max_iter=2000, random_state=0),
            {"m__hidden_layer_sizes": [(8,), (16,), (32,), (16, 8)],
             "m__alpha": [0.0001, 0.001, 0.01, 0.1, 1.0], "m__learning_rate_init": [0.001, 0.01]}),
}

LINES: list[str] = []


def out(s: str = "") -> None:
    LINES.append(s)


# ------------------------------------------------------------------------------------------ data
def build() -> pd.DataFrame:
    _, f = load()
    f = f.copy()
    f["tier_large"] = (f["account_size_tier"] == "large").astype(float)
    f["tier_medium"] = (f["account_size_tier"] == "medium").astype(float)
    f["platform_ig"] = (f["platform"] == "instagram").astype(float)
    h = f["posting_hour_utc"].astype(float)
    f["hour_sin"], f["hour_cos"] = np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24)
    f["weekend"] = f["is_weekend_utc"].astype(float)
    f["creator_collab_f"] = derived.flag01(f["creator_collab"])
    f["y"] = f["engagement_high"].astype(int)
    return f.reset_index(drop=True)


def pipe(model) -> Pipeline:
    return Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()), ("m", model)])


def best_threshold(y, p) -> float:
    cands = np.unique(p)
    scores = [f1_score(y, (p >= t).astype(int), zero_division=0) for t in cands]
    return float(cands[int(np.argmax(scores))])


def youden_threshold(y, p) -> float:
    """Secondary rule (added after the smoke test, D-044 note): maximise sensitivity + specificity - 1."""
    cands = np.unique(p)
    pos, neg = (y == 1).sum(), (y == 0).sum()
    j = [((p >= t) & (y == 1)).sum() / pos + ((p < t) & (y == 0)).sum() / neg - 1 for t in cands]
    return float(cands[int(np.argmax(j))])


def fit_one(name, cols, tr, te, seed):
    est, grid = GRIDS[name]
    Xtr, ytr, gtr = tr[cols], tr["y"], tr["account"]
    inner = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed)
    if grid:
        n = int(np.prod([len(v) for v in grid.values()]))
        search = RandomizedSearchCV(pipe(clone(est)), grid, n_iter=min(N_ITER, n), scoring="roc_auc",
                                    cv=inner, random_state=seed, n_jobs=-1, error_score=np.nan)
        search.fit(Xtr, ytr, groups=gtr)
        model, params = search.best_estimator_, search.best_params_
    else:
        model, params = pipe(clone(est)).fit(Xtr, ytr), {}
    # threshold from out-of-fold predictions inside the training fold
    oof = np.full(len(tr), np.nan)
    for a, b in inner.split(Xtr, ytr, gtr):
        m = clone(model).fit(Xtr.iloc[a], ytr.iloc[a])
        oof[b] = m.predict_proba(Xtr.iloc[b])[:, 1]
    thr = best_threshold(ytr.to_numpy(), oof)
    thr_j = youden_threshold(ytr.to_numpy(), oof)
    p = model.predict_proba(te[cols])[:, 1]
    yte = te["y"].to_numpy()
    yhat = (p >= thr).astype(int)
    met = {"roc_auc": roc_auc_score(yte, p) if len(set(yte)) > 1 else np.nan,
           "pr_auc": average_precision_score(yte, p), "brier": brier_score_loss(yte, p),
           "acc": accuracy_score(yte, yhat), "prec": precision_score(yte, yhat, zero_division=0),
           "rec": recall_score(yte, yhat, zero_division=0), "f1": f1_score(yte, yhat, zero_division=0),
           "threshold": thr}
    yj = (p >= thr_j).astype(int)
    met.update({"acc_j": accuracy_score(yte, yj), "prec_j": precision_score(yte, yj, zero_division=0),
                "rec_j": recall_score(yte, yj, zero_division=0), "f1_j": f1_score(yte, yj, zero_division=0),
                "threshold_j": thr_j, "all_high_f1rule": bool(yhat.all())})
    return met, p, params


def run_cv(df: pd.DataFrame, models: list[str], sets: dict, tag: str):
    rows, preds, folds = [], [], []
    for rep, seed in enumerate(SEEDS):
        outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
        for k, (a, b) in enumerate(outer.split(df, df["y"], df["account"])):
            tr, te = df.iloc[a], df.iloc[b]
            folds.append({"set": tag, "repeat": rep, "fold": k, "test_videos": len(te),
                          "test_accounts": te["account"].nunique(),
                          "test_youtube": int((te["platform"] == "youtube").sum()),
                          "test_high_share": round(te["y"].mean(), 2),
                          "global_channel_in_test": bool((te["account"] == "Coca-Cola").any())})
            for name in models:
                for s, cols in sets.items():
                    t0 = time.time()
                    met, p, params = fit_one(name, cols, tr, te, seed)
                    rows.append({"data": tag, "model": name, "set": s, "repeat": rep, "fold": k,
                                 **met, "params": json.dumps(params, default=str),
                                 "sec": round(time.time() - t0, 1)})
                    if rep == 0:
                        preds += [{"data": tag, "model": name, "set": s, "platform": pl, "media_id": mid,
                                   "account": acc, "y": yy, "p": pp}
                                  for pl, mid, acc, yy, pp in zip(te["platform"], te["media_id"],
                                                                   te["account"], te["y"], p)]
            print(f"  [{tag}] repeat {rep + 1}/3 fold {k + 1}/5 done", flush=True)
    return pd.DataFrame(rows), pd.DataFrame(preds), pd.DataFrame(folds)


def corrected_ci(diffs: np.ndarray, n_train: int, n_test: int):
    """Nadeau-Bengio corrected resampled t: variance inflated for overlapping training sets."""
    j = len(diffs)
    m, s2 = diffs.mean(), diffs.var(ddof=1)
    se = np.sqrt((1 / j + n_test / n_train) * s2)
    t = stats.t.ppf(0.975, j - 1)
    p = 2 * stats.t.sf(abs(m / se), j - 1) if se > 0 else np.nan
    return m, m - t * se, m + t * se, p


# ------------------------------------------------------------------------------------------ report
def summary_table(res: pd.DataFrame, title: str):
    out(f"### {title} - mean +/- SD over 15 account-grouped folds")
    out("| Model | Set | Acc | Prec | Rec | F1 | ROC-AUC | PR-AUC | Brier |")
    out("|---|---|---|---|---|---|---|---|---|")
    order = ["Majority", "LogReg", "DecisionTree", "RandomForest", "XGBoost", "MLP"]
    for name in [m for m in order if m in res["model"].unique()]:
        for s in ("M0", "M1", "M2"):
            r = res[(res["model"] == name) & (res["set"] == s)]
            if r.empty:
                continue
            cells = [f"{r[c].mean():.3f} +/- {r[c].std():.3f}" for c in
                     ("acc", "prec", "rec", "f1", "roc_auc", "pr_auc", "brier")]
            out(f"| {name} | {s} | " + " | ".join(cells) + " |")
    out("Threshold metrics at the secondary Youden cut-off (added after the smoke test showed the F1 rule "
        "often labels every video high; D-044 note):")
    out("| Model | Set | Acc | Prec | Rec | F1 | Folds where the F1 rule called every video high |")
    out("|---|---|---|---|---|---|---|")
    for name in [m for m in order if m in res["model"].unique()]:
        for s in ("M0", "M1", "M2"):
            r = res[(res["model"] == name) & (res["set"] == s)]
            if r.empty:
                continue
            cells = [f"{r[c].mean():.3f} +/- {r[c].std():.3f}" for c in ("acc_j", "prec_j", "rec_j", "f1_j")]
            out(f"| {name} | {s} | " + " | ".join(cells) + f" | {int(r['all_high_f1rule'].sum())} of {len(r)} |")
    out()


def diff_table(res: pd.DataFrame, n_train: int, n_test: int):
    out("| Model | M2 - M0 ROC-AUC | 95% CI (corrected) | p | M1 - M0 | 95% CI (corrected) |")
    out("|---|---|---|---|---|---|")
    for name in ["LogReg", "DecisionTree", "RandomForest", "XGBoost", "MLP"]:
        if name not in res["model"].unique():
            continue
        piv = res[res["model"] == name].pivot_table(index=["repeat", "fold"], columns="set", values="roc_auc")
        m2, lo2, hi2, p2 = corrected_ci((piv["M2"] - piv["M0"]).to_numpy(), n_train, n_test)
        m1, lo1, hi1, _ = corrected_ci((piv["M1"] - piv["M0"]).to_numpy(), n_train, n_test)
        out(f"| {name} | {m2:+.3f} | {lo2:+.3f} to {hi2:+.3f} | {p2:.3f} | {m1:+.3f} | {lo1:+.3f} to {hi1:+.3f} |")
    out()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    warnings.filterwarnings("ignore")
    t_start = time.time()
    df = build()
    n_train, n_test = int(len(df) * 0.8), int(len(df) * 0.2)
    out("# Phase 9 - model comparison (D-044, docs/09)")
    out()
    out(f"Focus set: {len(df)} videos, {df['account'].nunique()} accounts; target `engagement_high` "
        f"({int(df['y'].sum())} high / {int((1 - df['y']).sum())} low). Account-grouped 5-fold CV x 3 repeats; "
        "tuning on account-grouped inner folds; threshold from training out-of-fold predictions; "
        "imputation and scaling inside each training fold. Specification fixed before any fit (D-044). "
        "The Zero Sugar inclusion label is weakly reliable (YouTube alpha 0.25, Instagram -0.10).")
    out()

    res, preds, folds = run_cv(df, list(GRIDS), SETS, "pooled")
    out("## Fold make-up (pooled)")
    out(f"Test fold sizes {folds.loc[folds['set'] == 'pooled', 'test_videos'].min()}-"
        f"{folds.loc[folds['set'] == 'pooled', 'test_videos'].max()} videos, "
        f"{folds['test_accounts'].min()}-{folds['test_accounts'].max()} accounts; share high "
        f"{folds['test_high_share'].min()}-{folds['test_high_share'].max()}; the global channel's 58 "
        f"videos sit in one test fold per repeat ({int(folds['global_channel_in_test'].sum())} of 15 folds).")
    out()
    summary_table(res, "Main comparison")

    out("## The headline - does content add anything beyond reach? (D-044)")
    out("Paired over the 15 folds; intervals from the corrected resampled t-test (Nadeau-Bengio).")
    out()
    diff_table(res, n_train, n_test)
    x = res[(res["model"] == "XGBoost") & (res["set"] == "M2")].set_index(["repeat", "fold"])["roc_auc"]
    b = res[(res["model"] == "LogReg") & (res["set"] == "M0")].set_index(["repeat", "fold"])["roc_auc"]
    m, lo, hi, p = corrected_ci((x - b).to_numpy(), n_train, n_test)
    verdict = "content adds beyond reach" if lo > 0 else ("content does worse than reach alone" if hi < 0 else
                                                          "not detected - content adds nothing measurable beyond reach")
    best = res[res["set"] == "M2"].groupby("model")["roc_auc"].mean().drop("Majority").idxmax()
    bm0 = res[res["set"] == "M0"].groupby("model")["roc_auc"].mean().drop("Majority")
    out("| Quantity | Value |\n|---|---|")
    out(f"| Reach-only baseline (LogReg M0) ROC-AUC | {b.mean():.3f} +/- {b.std():.3f} |")
    out(f"| Best M0 ROC-AUC (reach alone) | {bm0.max():.3f} ({bm0.idxmax()}) |")
    out(f"| XGBoost M2 ROC-AUC (reach + content) | {x.mean():.3f} +/- {x.std():.3f} |")
    out(f"| Best M2 ROC-AUC | {res[res['set'] == 'M2'].groupby('model')['roc_auc'].mean()[best]:.3f} ({best}) - reported, not the basis of any conclusion |")
    out(f"| **Primary: XGBoost M2 - LogReg M0** | **{m:+.3f}** |")
    out(f"| 95% CI on the difference (corrected) | {lo:+.3f} to {hi:+.3f} (p = {p:.3f}) |")
    out(f"| **Does content add beyond reach?** | **{verdict}** |")
    out()

    # Instagram-only, exploratory
    ig = df[df["platform"] == "instagram"].reset_index(drop=True)
    ig_sets = {"M0": [c for c in M0 if c != "platform_ig"], "M1": M1 + ["creator_collab_f"],
               "M2": [c for c in M0 if c != "platform_ig"] + M1 + ["creator_collab_f"]}
    res_ig, preds_ig, folds_ig = run_cv(ig, ["LogReg", "XGBoost"], ig_sets, "instagram")
    out("## Instagram-only model - exploratory (D-041)")
    out(f"{len(ig)} videos, {ig['account'].nunique()} accounts; `creator_collab` added to M1/M2. No YouTube-only "
        "model (72 videos, 5 channels, 58 from one).")
    out()
    summary_table(res_ig, "Instagram only")
    diff_table(res_ig, int(len(ig) * 0.8), int(len(ig) * 0.2))

    # calibration, pooled out-of-fold predictions from repeat 1
    out("## Calibration (out-of-fold predictions, repeat 1)")
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    ax.plot([0, 1], [0, 1], color="#8a8984", lw=1, ls="--", label="perfect")
    for name, col in [("LogReg", "#2a78d6"), ("XGBoost", "#eb6834")]:
        pr = preds[(preds["model"] == name) & (preds["set"] == "M2")]
        fy, fx = calibration_curve(pr["y"], pr["p"], n_bins=6, strategy="quantile")
        ax.plot(fx, fy, marker="o" if name == "LogReg" else "^", color=col, lw=2, label=f"{name} M2")
        out(f"- {name} M2: Brier {brier_score_loss(pr['y'], pr['p']):.3f} on {len(pr)} out-of-fold predictions "
            f"(0.25 = a constant 0.5 guess).")
    ax.set_xlabel("predicted probability of high engagement"); ax.set_ylabel("observed share high")
    ax.set_title("Calibration, M2 models (out-of-fold)", loc="left", fontsize=10, fontweight="bold")
    ax.legend(frameon=False, fontsize=8); ax.grid(color="#e6e5e0", lw=0.6)
    fig.tight_layout(); fig.savefig(FIG / "model_calibration.png", dpi=300); plt.close(fig)
    out("Figure: `reports/figures/model_calibration.png`")
    out()

    # learning curve, XGBoost M2 with fixed moderate settings (stated)
    out("## Learning curve - XGBoost M2, fixed settings (depth 3, rate 0.05, 200 trees)")
    lc = []
    for frac in (0.4, 0.6, 0.8, 1.0):
        aucs = []
        for seed in SEEDS:
            outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
            rng = np.random.default_rng(seed)
            for a, b_ in outer.split(df, df["y"], df["account"]):
                tr, te = df.iloc[a], df.iloc[b_]
                accs = tr["account"].unique()
                keep = rng.choice(accs, max(2, int(round(frac * len(accs)))), replace=False)
                tr = tr[tr["account"].isin(keep)]
                if tr["y"].nunique() < 2 or te["y"].nunique() < 2:
                    continue
                m_ = pipe(XGBClassifier(max_depth=3, learning_rate=0.05, n_estimators=200, tree_method="hist",
                                        eval_metric="logloss", random_state=0, n_jobs=4, verbosity=0))
                m_.fit(tr[SETS["M2"]], tr["y"])
                aucs.append(roc_auc_score(te["y"], m_.predict_proba(te[SETS["M2"]])[:, 1]))
        lc.append((frac, np.mean(aucs), np.std(aucs)))
        out(f"- {int(frac * 100)}% of training accounts: ROC-AUC {np.mean(aucs):.3f} +/- {np.std(aucs):.3f}")
    slope = lc[-1][1] - lc[0][1]
    out(f"Change from 40% to 100% of training accounts: {slope:+.3f}.")
    out()

    # most frequent tuned settings
    out("## Tuned settings chosen most often (M2, pooled)")
    for name in ["LogReg", "DecisionTree", "RandomForest", "XGBoost", "MLP"]:
        top = res[(res["model"] == name) & (res["set"] == "M2")]["params"].value_counts()
        out(f"- {name}: {top.index[0]} ({top.iloc[0]} of 15 folds)")
    out()

    # artefacts for the tool (12.1): refit on all 192
    MODELS.mkdir(exist_ok=True)
    card = {"created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "decision": "D-044",
            "target": "engagement_high (median split of the percentile within platform x size tier)",
            "training_rows": len(df), "accounts": int(df["account"].nunique()),
            "feature_order": SETS["M2"], "models": {}}
    for name in ("XGBoost", "LogReg"):
        est, grid = GRIDS[name]
        search = RandomizedSearchCV(pipe(clone(est)), grid, n_iter=N_ITER, scoring="roc_auc",
                                    cv=StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42),
                                    random_state=42, n_jobs=-1)
        search.fit(df[SETS["M2"]], df["y"], groups=df["account"])
        path = MODELS / f"engagement_{name.lower()}_m2.joblib"
        joblib.dump(search.best_estimator_, path)
        r = res[(res["model"] == name) & (res["set"] == "M2")]
        card["models"][name] = {"file": path.name, "params": search.best_params_,
                                "cv_roc_auc_mean": round(r["roc_auc"].mean(), 3),
                                "cv_roc_auc_sd": round(r["roc_auc"].std(), 3),
                                "cv_brier_mean": round(r["brier"].mean(), 3)}
    card["not_calibrated_yet"] = "task 12.2"
    (MODELS / "model_card.json").write_text(json.dumps(card, indent=2, default=str), encoding="utf-8")
    out(f"Saved for the tool (12.1): `models/engagement_xgboost_m2.joblib`, `models/engagement_logreg_m2.joblib`, "
        "`models/model_card.json` (not yet calibrated - 12.2).")
    out()
    out(f"Run time {(time.time() - t_start) / 60:.1f} min.")

    allres = pd.concat([res, res_ig])
    allres.to_csv(config.REPORTS / "model_fold_results.csv", index=False)
    pd.concat([preds, preds_ig]).to_csv(PRED, index=False)
    pd.concat([folds, folds_ig]).to_csv(config.REPORTS / "model_folds.csv", index=False)
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print("\n".join(LINES))


if __name__ == "__main__":
    main()

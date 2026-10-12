"""Tasks 12.1-12.2 - the tool's two models and their release checks, exactly as fixed in D-053.

1. Base rate: log10(engagement rate) ~ platform + log10(followers), account random intercept; 80% prediction
   interval for a video from a NEW account; gate G3 = interval coverage on account-grouped folds.
2. Instagram content score (exploratory): the registered Instagram logistic M1, refitted on all 120; gate G2 =
   calibration of out-of-fold probabilities in ten equal-count bins (within 0.10), then Platt scaling inside
   the folds if needed, else no probability is shown (a position among the 120 instead).
3. Saved for the tool: models/base_rate.json, models/instagram_content_logreg.joblib (+ calibrator),
   models/reference_quantiles.json, models/model_card.json.

Usage:
    python -m src.serve.build_models
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.base import clone  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import brier_score_loss, roc_auc_score  # noqa: E402
from sklearn.model_selection import RandomizedSearchCV, StratifiedGroupKFold  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.focus_codes import H, LABEL as HLABEL, coded  # noqa: E402
from src.eda.explore import GREY, INK2  # noqa: E402  (also sets the figure style)
from src.models.train import GRIDS, M1, SEEDS, build, pipe  # noqa: E402
from src.stats.hypotheses import RAW, fit  # noqa: E402

MODELS = config.ROOT / "models"
OUT = config.REPORTS / "serving_models.md"
FIG = config.REPORTS / "figures" / "instagram_score_calibration.png"
Z80 = 1.2816
IG_COLS = M1 + ["creator_collab_f"]
FORMULA = "log10_er ~ C(platform, Treatment('youtube')) + log_followers"
LINES: list[str] = []


def out(s: str = "") -> None:
    LINES.append(s)


# ------------------------------------------------------------------------------------------ base rate
def base_fit(d: pd.DataFrame) -> dict:
    m, conv = fit(FORMULA, d)
    fe = m.fe_params
    cov = m.cov_params().loc[fe.index, fe.index]
    return {"names": list(fe.index), "beta": fe.to_numpy(), "cov": cov.to_numpy(),
            "var_account": float(m.cov_re.iloc[0, 0]), "var_resid": float(m.scale), "converged": conv}


def design(platform: pd.Series, log_f: pd.Series) -> np.ndarray:
    return np.column_stack([np.ones(len(platform)), (platform == "instagram").astype(float).to_numpy(),
                            log_f.to_numpy(float)])


def base_predict(b: dict, platform: pd.Series, log_f: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    x = design(platform, log_f)
    mean = x @ b["beta"]
    var_fixed = np.einsum("ij,jk,ik->i", x, b["cov"], x)
    sd = np.sqrt(var_fixed + b["var_account"] + b["var_resid"])
    return mean, sd


def g3(df: pd.DataFrame) -> dict:
    zs, plats = [], []
    for seed in SEEDS:
        outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
        for a, t in outer.split(df, df["y"], df["account"]):
            tr, te = df.iloc[a], df.iloc[t]
            b = base_fit(tr)
            mean, sd = base_predict(b, te["platform"], te["log_followers"])
            zs.append(np.abs(te["log10_er"].to_numpy() - mean) / sd)
            plats.append(te["platform"].to_numpy())
    z, pl = np.concatenate(zs), np.concatenate(plats)
    inside = z <= Z80
    cov = {"overall": float(inside.mean()), "instagram": float(inside[pl == "instagram"].mean()),
           "youtube": float(inside[pl == "youtube"].mean()), "n": int(len(z))}
    cov["passes"] = all(0.70 <= cov[k] <= 0.90 for k in ("overall", "instagram", "youtube"))
    cov["widen"] = float(np.quantile(z, 0.80) / Z80)          # used only if G3 fails (D-053)
    inside_w = z <= Z80 * cov["widen"]
    cov["after_widening"] = {"overall": float(inside_w.mean()), "instagram": float(inside_w[pl == "instagram"].mean()),
                             "youtube": float(inside_w[pl == "youtube"].mean())}
    return cov


# ------------------------------------------------------------------------------------------ Instagram score
def ig_oof(ig: pd.DataFrame, logged: pd.DataFrame) -> pd.DataFrame:
    """Out-of-fold probabilities, all 3 repeats, from fold models rebuilt with the logged settings; plus the
    Platt-scaled version (Platt fitted inside each training fold on its inner account-grouped out-of-fold
    predictions)."""
    rows = logged[(logged["data"] == "instagram") & (logged["model"] == "LogReg") & (logged["set"] == "M1")]
    rows = rows.set_index(["repeat", "fold"])
    est = GRIDS["LogReg"][0]
    recs, worst = [], 0.0
    for rep, seed in enumerate(SEEDS):
        outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
        for k, (a, t) in enumerate(outer.split(ig, ig["y"], ig["account"])):
            tr, te = ig.iloc[a], ig.iloc[t]
            params = json.loads(rows.loc[(rep, k), "params"])
            model = pipe(clone(est)).set_params(**params).fit(tr[IG_COLS], tr["y"])
            p = model.predict_proba(te[IG_COLS])[:, 1]
            worst = max(worst, abs(roc_auc_score(te["y"], p) - rows.loc[(rep, k), "roc_auc"]))
            inner = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed)
            oof = np.full(len(tr), np.nan)
            for ia, ib in inner.split(tr, tr["y"], tr["account"]):
                mi = pipe(clone(est)).set_params(**params).fit(tr.iloc[ia][IG_COLS], tr.iloc[ia]["y"])
                oof[ib] = mi.predict_proba(tr.iloc[ib][IG_COLS])[:, 1]
            platt = LogisticRegression(C=1e6).fit(logit(oof).reshape(-1, 1), tr["y"])
            p_cal = platt.predict_proba(logit(p).reshape(-1, 1))[:, 1]
            recs += [{"repeat": rep, "fold": k, "media_id": m, "y": int(y), "p": float(pp), "p_platt": float(pc)}
                     for m, y, pp, pc in zip(te["media_id"], te["y"], p, p_cal)]
    if worst > 1e-9:
        raise SystemExit(f"rebuilt Instagram fold models do not match Phase 9 ({worst}) - stopped (D-053)")
    return pd.DataFrame(recs)


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def calibration(y: np.ndarray, p: np.ndarray) -> tuple[pd.DataFrame, float]:
    bins = pd.qcut(pd.Series(p).rank(method="first"), 10, labels=False)
    t = pd.DataFrame({"y": y, "p": p, "bin": bins}).groupby("bin").agg(n=("y", "size"), predicted=("p", "mean"),
                                                                        observed=("y", "mean"))
    return t, float((t["observed"] - t["predicted"]).abs().max())


# ------------------------------------------------------------------------------------------ main
def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    warnings.filterwarnings("ignore")
    df = build()
    ig = df[df["platform"] == "instagram"].reset_index(drop=True)
    logged = pd.read_csv(config.REPORTS / "model_fold_results.csv")
    out("# Tasks 12.1-12.2 - the tool's models and their release checks (D-053)")
    out()
    out("Implements D-046: an honest base rate per platform and an exploratory Instagram content score. Gates "
        "fixed in D-053 before anything was fitted. G1 failed on 2 October (D-045) and is reported as such.")
    out()

    # 1. base rate
    cov = g3(df)
    b = base_fit(df)
    widen = 1.0 if cov["passes"] else cov["widen"]
    out("## 1. Base rate - engagement rate for a typical video from a new account")
    out(f"Mixed model `log10(rate) ~ platform + log10(followers)`, account intercept, 192 videos, 22 accounts "
        f"(converged: {b['converged']}). Account variance {b['var_account']:.3f}, residual {b['var_resid']:.3f} "
        f"(log10 units): {b['var_account'] / (b['var_account'] + b['var_resid']):.0%} of the unexplained variation "
        "is between accounts.")
    out()
    out(f"**G3 - 80% interval coverage on account-grouped folds ({cov['n']} test predictions, 5 x 3 folds):** "
        f"overall {cov['overall']:.0%}, Instagram {cov['instagram']:.0%}, YouTube {cov['youtube']:.0%} -> "
        f"**{'PASS' if cov['passes'] else 'FAIL'}** (rule: 70-90% overall and on each platform)."
        + ("" if cov["passes"] else f" Interval widened by x{widen:.2f}, the factor that gives 80% overall on the same folds (D-053). "
           f"After widening: overall {cov['after_widening']['overall']:.0%}, Instagram {cov['after_widening']['instagram']:.0%}, "
           f"YouTube {cov['after_widening']['youtube']:.0%}"
           + (" - **YouTube still under 70%: its interval is shown with a warning that it is too narrow for "
              "YouTube** (D-053)." if cov['after_widening']['youtube'] < 0.70 else ".")))
    out()
    out("What the tool would show (80% interval for a new account's typical video; rate = likes + comments per follower):")
    out("| Platform | Followers | Typical rate | 80% interval | Likes + comments, 80% range |")
    out("|---|---|---|---|---|")
    for plat in ("instagram", "youtube"):
        for f_ in (50_000, 500_000, 5_000_000):
            mean, sd = base_predict(b, pd.Series([plat]), pd.Series([np.log10(f_)]))
            lo, hi = 10 ** (mean - Z80 * sd * widen), 10 ** (mean + Z80 * sd * widen)
            out(f"| {plat} | {f_:,} | {10 ** mean[0]:.2%} | {lo[0]:.3%} to {hi[0]:.2%} | {lo[0] * f_:,.0f} to {hi[0] * f_:,.0f} |")
    out()
    out(f"The interval is wide because {b['var_account'] / (b['var_account'] + b['var_resid']):.0%} of the unexplained "
        "variation belongs to the account, which the tool cannot know for a new account. The engagement percentile is "
        "not modelled: it is ranked within platform and follower tier, so a typical video sits at the middle by "
        "construction (D-053).")
    out()

    # 2. Instagram score
    oof = ig_oof(ig, logged)
    t_a, gap_a = calibration(oof["y"].to_numpy(), oof["p"].to_numpy())
    t_b, gap_b = calibration(oof["y"].to_numpy(), oof["p_platt"].to_numpy())
    mode = "probability" if gap_a <= 0.10 else ("probability (Platt-calibrated)" if gap_b <= 0.10 else
                                                "position among the 120 Instagram videos (no probability)")
    out("## 2. Instagram content score (exploratory) - calibration, G2")
    out(f"Out-of-fold probabilities of the registered Instagram logistic M1, all 3 repeats ({len(oof)} predictions; "
        "fold models rebuilt from the logged settings, ROC-AUCs reproduced exactly). Ten equal-count bins; G2 passes if "
        "every bin is within 0.10 of its mean predicted probability.")
    out()
    out("| Bin | Videos | (a) as fitted: predicted / observed | (b) Platt inside folds: predicted / observed |")
    out("|---|---|---|---|")
    for i in range(10):
        out(f"| {i + 1} | {int(t_a.loc[i, 'n'])} | {t_a.loc[i, 'predicted']:.2f} / {t_a.loc[i, 'observed']:.2f} | "
            f"{t_b.loc[i, 'predicted']:.2f} / {t_b.loc[i, 'observed']:.2f} |")
    out()
    out(f"(a) largest gap {gap_a:.2f}, Brier {brier_score_loss(oof['y'], oof['p']):.3f} -> **{'PASS' if gap_a <= 0.10 else 'FAIL'}**; "
        f"(b) largest gap {gap_b:.2f}, Brier {brier_score_loss(oof['y'], oof['p_platt']):.3f} -> "
        f"**{'PASS' if gap_b <= 0.10 else 'FAIL'}**. Out-of-fold ROC-AUC {roc_auc_score(oof['y'], oof['p']):.3f} "
        "(pooled over repeats; per-fold mean 0.704). **The gap matters:** within one fold the score ranks videos "
        "better than chance, but its level shifts each time the model is refitted, so pooled across folds it ranks "
        "at chance and no probability can be attached to it. A position among videos scored by the same model is "
        "the most the score supports.")
    out()
    out(f"**How the tool shows the score (rule fixed in D-053): {mode}.**")
    out()
    fig, ax = plt.subplots(figsize=(5.4, 4.8))
    ax.plot([0, 1], [0, 1], color=GREY, lw=1, ls="--", label="perfect")
    ax.fill_between([0, 1], [-0.1, 0.9], [0.1, 1.1], color="#e6e5e0", alpha=0.6, label="G2 band (+/- 0.10)")
    ax.plot(t_a["predicted"], t_a["observed"], marker="o", color=INK2, lw=2, label="(a) as fitted")
    ax.plot(t_b["predicted"], t_b["observed"], marker="^", color="#1baf7a", lw=2, label="(b) Platt inside folds")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel("predicted probability of high engagement (bin mean)")
    ax.set_ylabel("observed share high")
    ax.set_title("Instagram content score - calibration (out-of-fold, 360)", loc="left", fontsize=9.5)
    ax.legend(fontsize=7.5, loc="upper left")
    fig.tight_layout(); fig.savefig(FIG, dpi=300); plt.close(fig)
    out("Figure: `reports/figures/instagram_score_calibration.png`")
    out()

    # 3. save the serving artefacts
    est, grid = GRIDS["LogReg"]
    search = RandomizedSearchCV(pipe(clone(est)), grid, n_iter=len(grid["m__C"]), scoring="roc_auc",
                                cv=StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEEDS[0]),
                                random_state=SEEDS[0], n_jobs=-1)
    search.fit(ig[IG_COLS], ig["y"], groups=ig["account"])
    final = search.best_estimator_
    joblib.dump(final, MODELS / "instagram_content_logreg.joblib")
    scores = np.sort(final.predict_proba(ig[IG_COLS])[:, 1])
    calib_file = None
    if mode.startswith("probability (Platt"):
        inner = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEEDS[0])
        oof_all = np.full(len(ig), np.nan)
        for ia, ib in inner.split(ig, ig["y"], ig["account"]):
            mi = clone(final).fit(ig.iloc[ia][IG_COLS], ig.iloc[ia]["y"])
            oof_all[ib] = mi.predict_proba(ig.iloc[ib][IG_COLS])[:, 1]
        joblib.dump(LogisticRegression(C=1e6).fit(logit(oof_all).reshape(-1, 1), ig["y"]),
                    MODELS / "instagram_content_platt.joblib")
        calib_file = "instagram_content_platt.joblib"
    flo, fhi = float(df["followers"].min()), float(df["followers"].max())
    (MODELS / "base_rate.json").write_text(json.dumps({
        "decision": "D-053", "formula": FORMULA, "fixed_effects": dict(zip(b["names"], b["beta"].tolist())),
        "fixed_effects_cov": b["cov"].tolist(), "var_account": b["var_account"], "var_resid": b["var_resid"],
        "interval": "80%", "z": Z80, "widen": widen, "followers_range": [flo, fhi],
        "g3_coverage": cov}, indent=2), encoding="utf-8")

    focus = df.merge(coded(), on=["platform", "media_id"], how="left", validate="1:1")
    qs = list(range(0, 101, 5))
    ref = {"decision": "D-053", "n_videos": len(df), "quantiles_at": qs, "features": {}, "hand_codes": {}}
    for raw in list(RAW.values()) + ["cuts_per_sec", "caption_char_len"]:
        if raw not in df:
            continue
        ref["features"][raw] = {p: np.nanpercentile(g[raw].astype(float), qs).round(6).tolist()
                                for p, g in [("all", df), *df.groupby("platform")]}
    for h in H:
        ref["hand_codes"][h] = {"label": HLABEL[h], **{p: round(float(g[h].mean()), 4)
                                                       for p, g in [("all", focus), *focus.groupby("platform")]}}
    (MODELS / "reference_quantiles.json").write_text(json.dumps(ref, indent=2), encoding="utf-8")

    old = json.loads((MODELS / "model_card.json").read_text(encoding="utf-8"))
    card = {
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "decisions": ["D-046", "D-053"],
        "training_set": "192 Coca-Cola Zero Sugar short videos, 22 accounts (Instagram 120 / 17, YouTube 72 / 5)",
        "outputs": {
            "base_rate": {"file": "base_rate.json", "what": "engagement rate (likes + comments per follower) of a "
                          "typical video from a new account of this platform and size, 80% interval",
                          "g3_interval_coverage": cov, "widened_by": widen},
            "instagram_content_score": {"file": "instagram_content_logreg.joblib", "calibrator": calib_file,
                                        "label": "exploratory: found in a secondary analysis, not confirmed",
                                        "cv_roc_auc": 0.704, "g2_largest_gap_as_fitted": gap_a,
                                        "g2_largest_gap_platt": gap_b, "display": mode,
                                        "training_scores_sorted": scores.round(6).tolist(),
                                        "chosen_C": search.best_params_["m__C"], "feature_order": IG_COLS},
            "diagnostics": {"file": "reference_quantiles.json",
                            "what": "the video's measures placed against the 192 videos; no claim that any raises engagement"},
            "youtube_score": None, "platform_recommendation": None},
        "gates": {"G1": "failed (D-045) - content did not beat reach for unseen accounts",
                  "G2": f"{'pass' if mode.startswith('probability') else 'fail'} - see instagram_content_score",
                  "G3": f"{'pass' if cov['passes'] else 'fail (interval widened)'} - see base_rate",
                  "G4": "pending (task 12.8: training/serving parity on 10 corpus videos)"},
        "not_served_comparison_only": old.get("models", old.get("not_served_comparison_only")),
        "followers_range": [flo, fhi],
        "limitations": ["Zero Sugar label weakly reliable (YouTube alpha 0.25, Instagram -0.10)",
                        "one brand, 22 accounts; YouTube 58 of 72 videos from one channel",
                        "engagement read at 7+ days; video age not modelled"],
    }
    (MODELS / "model_card.json").write_text(json.dumps(card, indent=2, default=float), encoding="utf-8")
    out("## 3. Saved for the tool (12.1)")
    out(f"`models/base_rate.json`, `models/instagram_content_logreg.joblib` (C = {search.best_params_['m__C']})"
        + (f", `models/{calib_file}`" if calib_file else "") + ", `models/reference_quantiles.json`, "
        "`models/model_card.json` (rewritten for D-046; the 2 October pooled models listed as comparison only). "
        f"Follower range of the training data: {flo:,.0f} to {fhi:,.0f} - outside it the tool warns.")
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print("\n".join(LINES))


if __name__ == "__main__":
    main()

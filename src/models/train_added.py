"""P14 (hand codes in the models) and P10's sensitivity re-run (local posting time), exactly as fixed in D-050.

Declared additions: the registered results of D-045 stay as reported. Same pipeline, grids, folds
(5 x 3, seeds 42 / 1042 / 2042), inner tuning and thresholds as `src/models/train.py`, which is reused
unchanged. The re-computed logistic M0 must equal the logged one fold by fold - the check that the folds
are the same.

Sets: Mh1 = the 11 hand-code columns H; Mh2 = M0 + H. P10: M0 and M2 with local hour and weekend.

Usage:
    python -m src.models.train_added          # about half an hour
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.focus_codes import H, LABEL as HLABEL, coded  # noqa: E402
from src.models import explain  # noqa: E402
from src.models.train import M0, M1, build, corrected_ci, run_cv  # noqa: E402

OUT = config.REPORTS / "model_comparison_added.md"
RES = config.REPORTS / "model_fold_results_added.csv"
PRED = config.REPORTS / "model_oof_predictions_added.csv"
M0_LOCAL = [c for c in M0 if c not in ("hour_sin", "hour_cos", "weekend")] + ["hour_sin_l", "hour_cos_l", "weekend_l"]
LINES: list[str] = []


def out(s: str = "") -> None:
    LINES.append(s)


def data() -> pd.DataFrame:
    df = build()
    n = len(df)
    df = df.merge(coded(), on=["platform", "media_id"], how="left", validate="1:1")
    lt = pd.read_csv(config.INTERIM / "local_time.csv", dtype={"media_id": str})
    df = df.merge(lt[["platform", "media_id", "posting_hour_local", "is_weekend_local"]],
                  on=["platform", "media_id"], how="left", validate="1:1")
    assert len(df) == n and df["ai_characters"].notna().all() and df["posting_hour_local"].notna().all()
    h = df["posting_hour_local"].astype(float)
    df["hour_sin_l"], df["hour_cos_l"] = np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24)
    df["weekend_l"] = df["is_weekend_local"].astype(float)
    df["ai_characters"] = df["ai_characters"].astype(bool)
    return df


def auc(res: pd.DataFrame, model: str, s: str) -> pd.Series:
    return res[(res["model"] == model) & (res["set"] == s)].set_index(["repeat", "fold"])["roc_auc"]


def diff_row(name: str, a: pd.Series, b: pd.Series, n: int) -> str:
    m, lo, hi, p = corrected_ci((a - b).to_numpy(), int(n * 0.8), int(n * 0.2))
    return f"| {name} | {a.mean():.3f} +/- {a.std():.3f} | {b.mean():.3f} | {m:+.3f} | {lo:+.3f} to {hi:+.3f} | {p:.3f} |"


def chance_row(name: str, a: pd.Series, n: int) -> str:
    m, lo, hi, _ = corrected_ci((a - 0.5).to_numpy(), int(n * 0.8), int(n * 0.2))
    return f"| {name} | {a.mean():.3f} +/- {a.std():.3f} | {lo:+.3f} to {hi:+.3f} | {'above chance' if lo > 0 else 'not above chance'} |"


def shap_stability(res: pd.DataFrame, preds: pd.DataFrame, df: pd.DataFrame) -> None:
    """D-047 rule 5 on two of the new models, reusing src/models/explain.py (rebuild, check, explain)."""
    explain.SPECS.update({
        "IH": {"label": "Instagram logistic regression Mh1 (hand codes)", "data": "instagram", "model": "LogReg",
               "set": "Mh1", "cols": H},
        "PH": {"label": "Pooled XGBoost Mh2 (reach + hand codes)", "data": "pooled_h", "model": "XGBoost",
               "set": "Mh2", "cols": M0 + H}})
    explain.LABEL.update(HLABEL)
    explain.BLOCK.update({h: "H" for h in H})
    out("## SHAP stability of two new models (D-047 rule 5; feeds the profile, P17)")
    for key in ("IH", "PH"):
        r = explain.run_model(key, df, res, preds)
        t = explain.stability(r, np.arange(len(r["df"])), "all")
        rho = t.attrs["rho"]
        stable = t[t["stable"]].sort_values("oof_rank")
        out(f"- **{explain.SPECS[key]['label']}** - rebuilt fold models match this run "
            f"(max ROC-AUC difference {r['check']['auc_max_diff']:.0e}). Rank agreement median {np.median(rho):.2f} "
            f"({explain.verdict(rho)}). Stable features: "
            + (", ".join(f"{x.label} ({x.direction})" for x in stable.itertuples()) or "none") + ".")
        out("  Top five by out-of-fold mean |SHAP|: "
            + "; ".join(f"{x.label} {x.oof_mean_abs_shap:.3f} (top 5 in {x.top5_folds}/15)"
                        for x in t.sort_values('oof_rank').head(5).itertuples()) + ".")
    out()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    warnings.filterwarnings("ignore")
    t0 = time.time()
    df = data()
    ig = df[df["platform"] == "instagram"].reset_index(drop=True)
    noai = df[~df["ai_characters"]].reset_index(drop=True)
    logged = pd.read_csv(config.REPORTS / "model_fold_results.csv")

    runs = []
    print("pooled: LogReg M0 (fold check)", flush=True)
    runs.append(run_cv(df, ["LogReg"], {"M0": M0}, "pooled_h"))
    print("pooled: hand-code sets", flush=True)
    runs.append(run_cv(df, ["LogReg", "XGBoost"], {"Mh1": H, "Mh2": M0 + H}, "pooled_h"))
    print("instagram: hand codes", flush=True)
    runs.append(run_cv(ig, ["LogReg", "XGBoost"], {"Mh1": H}, "instagram"))
    print("pooled without AI-character Shorts", flush=True)
    runs.append(run_cv(noai, ["LogReg"], {"M0": M0}, "pooled_noai"))
    runs.append(run_cv(noai, ["LogReg", "XGBoost"], {"Mh2": M0 + H}, "pooled_noai"))
    print("P10: local time", flush=True)
    runs.append(run_cv(df, ["LogReg"], {"M0_local": M0_LOCAL}, "pooled_local"))
    runs.append(run_cv(df, ["XGBoost"], {"M2_local": M0_LOCAL + M1}, "pooled_local"))
    res = pd.concat([r[0] for r in runs], ignore_index=True)
    preds = pd.concat([r[1] for r in runs], ignore_index=True)

    reg = logged[(logged["data"] == "pooled") & (logged["model"] == "LogReg") & (logged["set"] == "M0")]
    check = float((auc(res[res["data"] == "pooled_h"], "LogReg", "M0")
                   - reg.set_index(["repeat", "fold"])["roc_auc"]).abs().max())
    if check > 1e-9:
        raise SystemExit(f"re-computed logistic M0 differs from the logged one ({check}) - folds not the same; stopped")

    P = res[res["data"] == "pooled_h"]
    out("# P14 - hand codes in the models, and P10's local-time re-run - declared additions (D-050)")
    out()
    out(f"Focus set {len(df)} videos, {df['account'].nunique()} accounts. Same pipeline, grids and folds as D-044 "
        f"(5 x 3, account-grouped). **Fold check passed:** the re-computed logistic M0 equals the logged one in all "
        f"15 folds (largest difference {check:.0e}). H = 11 yes/no hand codes "
        f"({', '.join(HLABEL[h] for h in H)}); missing filled with the training fold's median. Hand codes: one coder, "
        "weakly reliable where checked (P11). The registered results (D-045) are unchanged.")
    out()
    out("## Pooled - does hand-coded content add to reach? (corrected resampled t)")
    out("| Comparison | ROC-AUC (mean +/- SD) | Logistic M0 | Difference | 95% CI | p |")
    out("|---|---|---|---|---|---|")
    m0 = auc(P, "LogReg", "M0")
    for model in ("XGBoost", "LogReg"):
        out(diff_row(f"{model} Mh2 (reach + hand codes) - logistic M0", auc(P, model, "Mh2"), m0, len(df)))
    out()
    out("| Model | ROC-AUC (mean +/- SD) | Corrected 95% CI for AUC - 0.5 | Verdict |")
    out("|---|---|---|---|")
    for model in ("LogReg", "XGBoost"):
        for s in ("Mh1", "Mh2"):
            out(chance_row(f"Pooled {model} {s}", auc(P, model, s), len(df)))
    I = res[res["data"] == "instagram"]
    for model in ("LogReg", "XGBoost"):
        out(chance_row(f"Instagram {model} Mh1 (exploratory)", auc(I, model, "Mh1"), len(ig)))
    reg_ig = logged[(logged["data"] == "instagram") & (logged["model"] == "LogReg") & (logged["set"] == "M1")]
    out()
    out(f"For comparison, the registered Instagram logistic M1 (20 measured content features): ROC-AUC "
        f"{reg_ig['roc_auc'].mean():.3f}.")
    out()
    N = res[res["data"] == "pooled_noai"]
    out(f"## Sensitivity - without the 15 AI-character Shorts ({len(noai)} videos; folds re-drawn)")
    out("| Comparison | ROC-AUC (mean +/- SD) | Logistic M0 | Difference | 95% CI | p |")
    out("|---|---|---|---|---|---|")
    for model in ("XGBoost", "LogReg"):
        out(diff_row(f"{model} Mh2 - logistic M0", auc(N, model, "Mh2"), auc(N, "LogReg", "M0"), len(noai)))
    out()
    L = res[res["data"] == "pooled_local"]
    regd = logged[logged["data"] == "pooled"]
    out("## P10 - local posting time in place of UTC (sensitivity; the registered numbers stay)")
    out("| Model | With local time | Registered (UTC) | Difference | 95% CI | p |")
    out("|---|---|---|---|---|---|")
    for model, s, rs in (("LogReg", "M0_local", "M0"), ("XGBoost", "M2_local", "M2")):
        a = auc(L, model, s)
        b = regd[(regd["model"] == model) & (regd["set"] == rs)].set_index(["repeat", "fold"])["roc_auc"]
        mm, lo, hi, p = corrected_ci((a - b).to_numpy(), int(len(df) * 0.8), int(len(df) * 0.2))
        out(f"| {model} {rs} | {a.mean():.3f} +/- {a.std():.3f} | {b.mean():.3f} | {mm:+.3f} | {lo:+.3f} to {hi:+.3f} | {p:.3f} |")
    out("Global/US (77 videos) keeps UTC (D-050).")
    out()
    shap_stability(res, preds, df)
    out(f"Run time {(time.time() - t0) / 60:.1f} min.")
    res.to_csv(RES, index=False)
    preds.to_csv(PRED, index=False)
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print("\n".join(LINES))


if __name__ == "__main__":
    main()

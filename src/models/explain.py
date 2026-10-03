"""Phase 10 - SHAP, exactly as fixed in D-047 (docs/10).

Three models, no others: A pooled XGBoost M2 (did not predict above chance, D-045 - SHAP says what a
model that failed relied on), B Instagram logistic regression M1 (the tool's exploratory score, D-046),
C Instagram XGBoost M1 (a cross-check of B). The 15 outer fold models of each are rebuilt from the
settings Phase 9 tuned and logged, and checked against Phase 9's logged results before any SHAP value
is computed. Stability first (10.1), then the figures (10.2) and the per-platform view (10.3).

Usage:
    python -m src.models.explain          # a few minutes
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import shap  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from scipy import stats  # noqa: E402
from sklearn.base import clone  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from sklearn.model_selection import StratifiedGroupKFold  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.eda.explore import COL, GREY, GRID, INK, INK2, MARK, NAME  # noqa: E402  (also sets the figure style)
from src.models.train import GRIDS, M1, SEEDS, SETS, build, pipe  # noqa: E402

OUT = config.REPORTS / "xai_findings.md"
FIG = config.REPORTS / "figures" / "shap"
IMPORTANCE = config.REPORTS / "shap_importance.csv"
FOLD_IMPORTANCE = config.REPORTS / "shap_fold_importance.csv"
FOLD_RESULTS = config.REPORTS / "model_fold_results.csv"
OOF = config.REPORTS / "model_oof_predictions.csv"

IG_M1 = M1 + ["creator_collab_f"]
SPECS = {
    "A": {"label": "Pooled XGBoost M2", "data": "pooled", "model": "XGBoost", "set": "M2", "cols": SETS["M2"]},
    "B": {"label": "Instagram logistic regression M1", "data": "instagram", "model": "LogReg", "set": "M1",
          "cols": IG_M1},
    "C": {"label": "Instagram XGBoost M1", "data": "instagram", "model": "XGBoost", "set": "M1", "cols": IG_M1},
}

# D-047 rule 3: two pairs of columns are one feature each (SHAP values add exactly)
MERGE = {"posting_hour": ["hour_sin", "hour_cos"], "follower_tier": ["tier_large", "tier_medium"]}
NO_DIRECTION = set(MERGE)

# D-047 rule 5, fixed before any SHAP value was computed
TOP, NEED, TOP10 = 5, 12, 10
STABLE_RHO, PARTLY_RHO = 0.70, 0.40

BLOCK = {
    "duration_sec": "A", "cuts_log1p": "A", "motion_px_per_sec": "A", "face_present_frac": "A",
    "face_area0": "A", "edge_density": "A", "colourfulness": "A", "red_ratio": "A",
    "ocr_region_count": "A", "ocr_mean_text_area": "A",
    "music_frac": "B", "talk_dur_frac": "B", "loudness_db_mean": "B", "loudness_range_db": "B",
    "sentiment_caption": "C", "caplen_lang": "C", "hashtag_count": "C", "emoji_count": "C",
    "kw_event": "C", "kw_promotional": "C",
    "creator_collab_f": "D",
    "log_followers": "E", "log_age": "E", "follower_tier": "E", "platform_ig": "E", "posting_hour": "E",
    "weekend": "E",
}
BLOCK_NAME = {"A": "A video", "B": "B audio", "C": "C text", "D": "D creator", "E": "E platform and exposure"}

LABEL = {
    "duration_sec": "duration", "cuts_log1p": "cuts per second (log)", "motion_px_per_sec": "motion",
    "face_present_frac": "share of frames with a face", "face_area0": "face size",
    "edge_density": "visual detail (edges)", "colourfulness": "colourfulness", "red_ratio": "share of red",
    "ocr_region_count": "on-screen text regions", "ocr_mean_text_area": "on-screen text area",
    "music_frac": "share with music", "talk_dur_frac": "share with talking", "loudness_db_mean": "loudness",
    "loudness_range_db": "loudness range", "sentiment_caption": "caption sentiment",
    "caplen_lang": "caption length (within language)", "hashtag_count": "hashtags", "emoji_count": "emoji",
    "kw_event": "event words", "kw_promotional": "promotional words",
    "creator_collab_f": "creator collaboration", "log_followers": "followers (log)",
    "log_age": "video age (log days)", "follower_tier": "follower tier", "platform_ig": "platform (Instagram)",
    "posting_hour": "posting hour (UTC)", "weekend": "weekend post (UTC)",
}

LINES: list[str] = []


def out(s: str = "") -> None:
    LINES.append(s)


def table(header: list[str], rows: list[list]) -> None:
    out("| " + " | ".join(header) + " |")
    out("|" + "---|" * len(header))
    for r in rows:
        out("| " + " | ".join(str(v) for v in r) + " |")
    out()


def merged_names(cols: list[str]) -> list[str]:
    names, seen = [], set()
    for c in cols:
        grp = next((g for g, members in MERGE.items() if c in members), None)
        name = grp or c
        if name not in seen:
            names.append(name)
            seen.add(name)
    return names


def merge_matrix(cols: list[str]) -> tuple[np.ndarray, list[str]]:
    names = merged_names(cols)
    m = np.zeros((len(cols), len(names)))
    for i, c in enumerate(cols):
        grp = next((g for g, members in MERGE.items() if c in members), None)
        m[i, names.index(grp or c)] = 1.0
    return m, names


# ------------------------------------------------------------------------------------------ fold models
def data_for(spec: dict, df: pd.DataFrame) -> pd.DataFrame:
    if spec["data"] == "instagram":
        return df[df["platform"] == "instagram"].reset_index(drop=True)
    return df


def run_model(key: str, df_all: pd.DataFrame, logged: pd.DataFrame, oof_saved: pd.DataFrame) -> dict:
    """Rebuild the 15 fold models, check them against Phase 9, and compute SHAP on every row."""
    spec = SPECS[key]
    df = data_for(spec, df_all)
    cols = spec["cols"]
    mm, names = merge_matrix(cols)
    n, q = len(df), len(names)
    est = GRIDS[spec["model"]][0]
    rows = logged[(logged["data"] == spec["data"]) & (logged["model"] == spec["model"])
                  & (logged["set"] == spec["set"])].set_index(["repeat", "fold"])
    saved = oof_saved[(oof_saved["data"] == spec["data"]) & (oof_saved["model"] == spec["model"])
                      & (oof_saved["set"] == spec["set"])].set_index("media_id")["p"]

    fold_sv = []                                  # per fold model: SHAP on all rows, merged, (n, q)
    fold_z = []                                   # the model's own (imputed, scaled) inputs, (n, p)
    oof_sv = np.full((len(SEEDS), n, q), np.nan)  # out-of-fold SHAP per repeat
    oof_int = np.full((len(SEEDS), n), np.nan)    # duration x platform interaction (model A only)
    test_of = []                                  # test-row indices per fold model
    auc_diff, pred_diff, add_err = [], [], []
    for rep, seed in enumerate(SEEDS):
        outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
        for k, (a, b) in enumerate(outer.split(df, df["y"], df["account"])):
            tr, te = df.iloc[a], df.iloc[b]
            params = json.loads(rows.loc[(rep, k), "params"])
            model = pipe(clone(est)).set_params(**params).fit(tr[cols], tr["y"])
            p = model.predict_proba(te[cols])[:, 1]
            auc_diff.append(abs(roc_auc_score(te["y"], p) - rows.loc[(rep, k), "roc_auc"]))
            if rep == 0:
                pred_diff.append(float(np.max(np.abs(p - saved.loc[te["media_id"]].to_numpy()))))

            prep, m = model[:-1], model.named_steps["m"]
            z_all = prep.transform(df[cols])
            assert z_all.shape[1] == len(cols), "imputer dropped a column"
            if spec["model"] == "LogReg":
                z_tr = prep.transform(tr[cols])
                ex = shap.LinearExplainer(m, shap.maskers.Independent(z_tr, max_samples=len(z_tr)))
                sv = ex.shap_values(z_all)
                margin = m.decision_function(z_all)
            else:
                ex = shap.TreeExplainer(m, feature_perturbation="tree_path_dependent")
                sv = ex.shap_values(z_all)
                margin = m.predict(z_all, output_margin=True)
                if key == "A":
                    iv = ex.shap_interaction_values(z_all[b])
                    i_d, i_p = cols.index("duration_sec"), cols.index("platform_ig")
                    oof_int[rep, b] = 2 * iv[:, i_d, i_p]
            add_err.append(float(np.max(np.abs(sv.sum(1) + ex.expected_value - margin))))
            svm = sv @ mm
            fold_sv.append(svm)
            fold_z.append(z_all)
            oof_sv[rep, b] = svm[b]
            test_of.append(b)

    check = {"auc_max_diff": max(auc_diff), "pred_max_diff": max(pred_diff), "additivity_max_err": max(add_err)}
    if check["auc_max_diff"] > 1e-6 or check["pred_max_diff"] > 1e-6:
        raise SystemExit(f"[{key}] rebuilt fold models do not match Phase 9: {check} - stopped (D-047 rule 2)")
    if check["additivity_max_err"] > 1e-4:
        raise SystemExit(f"[{key}] SHAP additivity check failed: {check} - stopped (D-047 rule 2)")
    return {"key": key, "spec": spec, "df": df, "cols": cols, "names": names, "fold_sv": fold_sv,
            "fold_z": fold_z, "oof": np.nanmean(oof_sv, axis=0), "oof_int": np.nanmean(oof_int, axis=0),
            "check": check}


# ------------------------------------------------------------------------------------------ stability
def directions(res: dict, rows: np.ndarray) -> np.ndarray:
    """Sign of Spearman(value, SHAP) per fold model and feature on the given rows; 0 if undefined."""
    cols, names = res["cols"], res["names"]
    d = np.zeros((len(res["fold_sv"]), len(names)))
    for f, (svm, z) in enumerate(zip(res["fold_sv"], res["fold_z"])):
        for j, nm in enumerate(names):
            if nm in NO_DIRECTION:
                continue
            x, s = z[rows, cols.index(nm)], svm[rows, j]
            if np.ptp(x) == 0 or np.ptp(s) == 0:
                continue
            r = stats.spearmanr(x, s).statistic
            d[f, j] = np.sign(r) if np.isfinite(r) else 0
    return d


def stability(res: dict, rows: np.ndarray, view: str) -> pd.DataFrame:
    names = res["names"]
    imp = np.array([np.abs(svm[rows]).mean(0) for svm in res["fold_sv"]])          # (15, q)
    ranks = np.array([stats.rankdata(-v, method="min") for v in imp])
    rho = [stats.spearmanr(imp[i], imp[j]).statistic for i in range(len(imp)) for j in range(i + 1, len(imp))]
    dirs = directions(res, rows)
    oof = np.abs(res["oof"][rows]).mean(0)
    oof_rank = stats.rankdata(-oof, method="min")
    t = pd.DataFrame({"model": res["key"], "view": view, "feature": names,
                      "label": [LABEL[nm] for nm in names], "block": [BLOCK[nm] for nm in names],
                      "oof_mean_abs_shap": oof, "oof_rank": oof_rank.astype(int),
                      "top5_folds": (ranks <= TOP).sum(0), "top10_folds": (ranks <= TOP10).sum(0),
                      "dir_pos_folds": (dirs > 0).sum(0), "dir_neg_folds": (dirs < 0).sum(0)})
    t["direction"] = np.select([t["feature"].isin(NO_DIRECTION), t["dir_pos_folds"] >= NEED,
                                t["dir_neg_folds"] >= NEED, t["dir_pos_folds"] > t["dir_neg_folds"],
                                t["dir_neg_folds"] > t["dir_pos_folds"]],
                               ["n/a", "higher -> higher", "higher -> lower", "mixed (mostly +)",
                                "mixed (mostly -)"], "mixed")
    t["stable"] = (t["top5_folds"] >= NEED) & (t["feature"].isin(NO_DIRECTION)
                                               | (t["dir_pos_folds"] >= NEED) | (t["dir_neg_folds"] >= NEED))
    t.attrs["rho"] = np.array(rho)
    t.attrs["imp"] = imp
    t.attrs["ranks"] = ranks
    return t.sort_values("oof_rank").reset_index(drop=True)


def verdict(rho: np.ndarray) -> str:
    med = float(np.median(rho))
    return "stable" if med >= STABLE_RHO else ("partly stable" if med >= PARTLY_RHO else "unstable")


def interpretable(t: pd.DataFrame) -> pd.DataFrame:
    cap = 5 if verdict(t.attrs["rho"]) == "stable" else 3
    return t[t["stable"]].sort_values("oof_rank").head(cap)


# ------------------------------------------------------------------------------------------ figures
CMAP = LinearSegmentedColormap.from_list("value", ["#2a78d6", "#d9d8d4", "#e34948"])  # low blue, high red


def save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    out(f"Figure: `reports/figures/shap/{name}.png`")
    out()


def value_matrix(res: dict) -> pd.DataFrame:
    """Raw feature values for colouring; merged features have no single value (shown grey)."""
    v = pd.DataFrame(index=res["df"].index)
    for nm in res["names"]:
        v[nm] = res["df"][nm].astype(float) if nm in res["df"] else np.nan
    return v


def fig_stability(tables: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 6.4), sharex=True)
    for ax, (key, t) in zip(axes, tables.items()):
        t = t.sort_values(["top5_folds", "oof_rank"], ascending=[True, False])
        colours = [INK2 if s else "#c9c8c3" for s in t["stable"]]
        ax.barh(t["label"], t["top5_folds"], color=colours, height=0.62)
        ax.axvline(NEED, color=INK, lw=1, ls="--")
        ax.set_xlim(0, 15)
        ax.set_xticks([0, 3, 6, 9, 12, 15])
        rho = t.attrs["rho"]
        ax.set_title(f"{key}. {SPECS[key]['label']}\nmedian rank agreement {np.median(rho):.2f} "
                     f"({verdict(rho)})", loc="left", fontsize=9.5)
        ax.set_xlabel("fold models (of 15) with the feature in its top 5")
        ax.tick_params(axis="y", labelsize=7.5)
        ax.grid(axis="y", visible=False)
    fig.text(0.01, -0.02, "Dark bars: stable under D-047 rule 5 (top 5 in at least 12 of 15 fold models, same "
             "direction in at least 12). Dashed line: 12 of 15.", fontsize=8, color=INK2)
    fig.tight_layout()
    save(fig, "shap_stability")


def fig_beeswarm(res: dict, t: pd.DataFrame, name: str, title: str) -> None:
    order = t.sort_values("oof_rank")["feature"].tolist()
    idx = [res["names"].index(f) for f in order]
    vals = value_matrix(res)[order]
    plt.figure()
    shap.summary_plot(res["oof"][:, idx], features=vals, feature_names=[LABEL[f] for f in order],
                      max_display=len(order), show=False, cmap=CMAP, plot_size=(8.2, 0.3 * len(order) + 1.6),
                      color_bar_label="feature value (low to high)")
    fig = plt.gcf()
    ax = fig.axes[0]
    ax.set_title(title, loc="left", fontsize=10)
    ax.set_xlabel("SHAP value (log-odds of high engagement), out-of-fold")
    save(fig, name)


def fig_blocks(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for key in ("A", "B"):
        t = tables[key]
        for blk in "ABCDE":
            s = t[t["block"] == blk]
            rows.append({"model": key, "block": blk, "features": len(s),
                         "sum": float(s["oof_mean_abs_shap"].sum()) if len(s) else np.nan,
                         "per_feature": float(s["oof_mean_abs_shap"].mean()) if len(s) else np.nan})
    b = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6), sharey=True)
    for ax, key in zip(axes, ("A", "B")):
        s = b[b["model"] == key].iloc[::-1]
        y = np.arange(len(s))
        top = s["sum"].max()
        ax.barh(y, s["sum"].fillna(0), color="#2a78d6", height=0.6)
        for yi, (_, r) in zip(y, s.iterrows()):
            empty = "not measured" if r["block"] == "D" else "not in this model"
            n_f = f"{r['features']} feature{'s' if r['features'] > 1 else ''}"
            txt = empty if not r["features"] else f"{r['sum']:.2f} ({n_f})"
            ax.text((0 if np.isnan(r["sum"]) else r["sum"]) + top * 0.02, yi, txt, va="center", fontsize=8,
                    color=INK2)
        ax.set_yticks(y, [BLOCK_NAME[x] for x in s["block"]])
        ax.set_title(f"{key}. {SPECS[key]['label']}", loc="left", fontsize=9.5)
        ax.set_xlabel("sum of mean |SHAP| over the block's features")
        ax.grid(axis="y", visible=False)
        ax.set_xlim(0, top * 1.55)       # own scale: the two models' SHAP sizes are not comparable
    fig.text(0.01, -0.03, "Each panel has its own scale: model B is strongly regularised, so its SHAP values are "
             "much smaller; compare blocks within a panel, not across.", fontsize=8, color=INK2)
    fig.tight_layout()
    save(fig, "shap_blocks")
    return b


def fig_platform(ta: dict[str, pd.DataFrame]) -> None:
    yt, ig = ta["youtube"].set_index("feature"), ta["instagram"].set_index("feature")
    order = ta["all"].sort_values("oof_rank")["feature"].tolist()[::-1]
    fig, ax = plt.subplots(figsize=(7.6, 0.3 * len(order) + 1.4))
    y = np.arange(len(order))
    for yi, f in zip(y, order):
        ax.plot([yt.loc[f, "oof_mean_abs_shap"], ig.loc[f, "oof_mean_abs_shap"]], [yi, yi], color=GRID, lw=2,
                zorder=1)
    for plat, t in (("youtube", yt), ("instagram", ig)):
        x = t.loc[order, "oof_mean_abs_shap"]
        st = t.loc[order, "stable"].to_numpy()
        ax.scatter(x[st], y[st], color=COL[plat], marker=MARK[plat], s=80, zorder=3, edgecolor="white",
                   linewidth=1, label=f"{NAME[plat]} ({'72' if plat == 'youtube' else '120'} videos) - stable")
        ax.scatter(x[~st], y[~st], facecolor="white", edgecolor=COL[plat], marker=MARK[plat], s=40, zorder=2,
                   linewidth=1.4, label=f"{NAME[plat]} - not stable")
    ax.set_yticks(y, [LABEL[f] for f in order], fontsize=8)
    ax.set_xlabel("mean |SHAP| on that platform's videos (out-of-fold)")
    ax.set_title("A. Pooled XGBoost M2 - what it relied on, YouTube vs Instagram rows\n"
                 "(the model did not predict above chance for unseen accounts; exploratory)", loc="left",
                 fontsize=9.5)
    ax.legend(loc="lower right", fontsize=7.5)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    save(fig, "shap_platform_comparison")


def fig_dependence(res: dict, features: list[str], name: str, title: str, by_platform: bool) -> None:
    n = len(features)
    fig, axes = plt.subplots(1, n, figsize=(4.0 * n, 3.4), squeeze=False)
    for ax, f in zip(axes[0], features):
        j = res["names"].index(f)
        x, s = res["df"][f].astype(float).to_numpy(), res["oof"][:, j]
        if by_platform:
            for plat in ("youtube", "instagram"):
                m = (res["df"]["platform"] == plat).to_numpy()
                ax.scatter(x[m], s[m], s=14, color=COL[plat], marker=MARK[plat], alpha=0.75, linewidth=0,
                           label=NAME[plat])
            ax.legend(fontsize=7.5)
        else:
            ax.scatter(x, s, s=14, color=COL["instagram"], marker=MARK["instagram"], alpha=0.75, linewidth=0)
        ax.axhline(0, color=GREY, lw=0.8)
        ax.set_xlabel(LABEL[f] + (" (s)" if f == "duration_sec" else ""))
        ax.set_ylabel("SHAP value (log-odds)")
    fig.suptitle(title, x=0.01, ha="left", fontsize=10, fontweight="bold")
    fig.tight_layout()
    save(fig, name)


def fig_waterfalls(res: dict, p_oof: pd.Series) -> list[dict]:
    df = res["df"]
    p = p_oof.loc[df["media_id"]].to_numpy()
    y = df["y"].to_numpy()
    picks = [("True positive: high video, highest predicted probability", np.where(y == 1)[0][np.argmax(p[y == 1])]),
             ("False positive: low video, highest predicted probability", np.where(y == 0)[0][np.argmax(p[y == 0])]),
             ("True negative: low video, lowest predicted probability", np.where(y == 0)[0][np.argmin(p[y == 0])]),
             ("False negative: high video, lowest predicted probability", np.where(y == 1)[0][np.argmin(p[y == 1])])]
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.2))
    info = []
    for ax, (title, i) in zip(axes.ravel(), picks):
        s = res["oof"][i]
        order = np.argsort(-np.abs(s))
        top, rest = order[:8], order[8:]
        labels = [LABEL[res["names"][j]] for j in top] + [f"{len(rest)} other features"]
        vals = list(s[top]) + [float(s[rest].sum())]
        yy = np.arange(len(vals))[::-1]
        ax.barh(yy, vals, color=["#e34948" if v > 0 else "#2a78d6" for v in vals], height=0.6)
        ax.set_yticks(yy, labels, fontsize=7.5)
        ax.axvline(0, color=GREY, lw=0.8)
        ax.set_title(f"{title}\n{df['media_id'].iloc[i]} - p = {p[i]:.3f}", loc="left", fontsize=8.5)
        ax.set_xlabel("contribution to log-odds of high (red raises, blue lowers)", fontsize=8)
        ax.grid(axis="y", visible=False)
        info.append({"case": title.split(":")[0], "media_id": df["media_id"].iloc[i], "account": df["account"].iloc[i],
                     "y": int(y[i]), "p": float(p[i]), "sum_shap": float(s.sum())})
    fig.suptitle("B. Instagram logistic regression M1 - four videos explained (out-of-fold, mean over 3 repeats)",
                 x=0.01, ha="left", fontsize=10, fontweight="bold")
    fig.tight_layout()
    save(fig, "shap_waterfalls_instagram")
    return info


# ------------------------------------------------------------------------------------------ report
def stability_rows(t: pd.DataFrame, n: int | None = None) -> list[list]:
    s = t.sort_values("oof_rank")
    if n:
        s = s.head(n)
    return [[r.oof_rank, r.label, f"{r.oof_mean_abs_shap:.3f}", f"{r.top5_folds} / 15", f"{r.top10_folds} / 15",
             r.direction, "**yes**" if r.stable else "no"] for r in s.itertuples()]


def describe_stability(key: str, t: pd.DataFrame, view: str) -> None:
    rho = t.attrs["rho"]
    v = verdict(rho)
    out(f"**{key}. {SPECS[key]['label']} - {view}.** Rank agreement between the 15 fold models (Spearman, 105 "
        f"pairs): median **{np.median(rho):.2f}** (10th-90th percentile {np.percentile(rho, 10):.2f} to "
        f"{np.percentile(rho, 90):.2f}) -> **{v}**. Features in the top 10 of all 15 fold models: "
        f"{int((t['top10_folds'] == 15).sum())}. Stable features (rule 5): "
        f"{', '.join(t[t['stable']].sort_values('oof_rank')['label']) or 'none'}.")
    out()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    warnings.filterwarnings("ignore")
    t0 = time.time()
    df = build()
    logged = pd.read_csv(FOLD_RESULTS)
    oof_saved = pd.read_csv(OOF)

    res = {}
    for key in SPECS:
        print(f"  rebuilding and explaining model {key} ...", flush=True)
        res[key] = run_model(key, df, logged, oof_saved)
        print(f"    checks: {res[key]['check']}", flush=True)

    # stability (10.1)
    tabs = {k: stability(r, np.arange(len(r["df"])), "all") for k, r in res.items()}
    plat = res["A"]["df"]["platform"].to_numpy()
    ta = {"all": tabs["A"],
          "youtube": stability(res["A"], np.where(plat == "youtube")[0], "youtube"),
          "instagram": stability(res["A"], np.where(plat == "instagram")[0], "instagram")}

    out("# Phase 10 - SHAP findings (D-047, docs/10)")
    out()
    out("Specification fixed before any SHAP value was computed: D-047. **SHAP says what a model relied on, not "
        "what causes engagement.** Model A (pooled XGBoost M2) did **not** predict above chance for unseen "
        "accounts (ROC-AUC 0.533, D-045), so its SHAP values describe what a model that failed relied on. "
        "Models B and C (Instagram only, content features) predicted above chance (ROC-AUC 0.704 and 0.670) "
        "and are **exploratory** - Instagram only, 17 accounts, not corrected for the many comparisons. "
        "The Zero Sugar inclusion label is weakly reliable (YouTube alpha 0.25, Instagram -0.10).")
    out()
    out("## 0. The fold models are the ones Phase 9 evaluated (D-047 rule 2)")
    table(["Model", "Videos / accounts", "Max ROC-AUC difference vs logged (15 folds)",
           "Max prediction difference vs saved (repeat 1)", "Max SHAP additivity error"],
          [[f"{k}. {r['spec']['label']}", f"{len(r['df'])} / {r['df']['account'].nunique()}",
            f"{r['check']['auc_max_diff']:.1e}", f"{r['check']['pred_max_diff']:.1e}",
            f"{r['check']['additivity_max_err']:.1e}"] for k, r in res.items()])

    out("## 1. Stability first (10.1)")
    out(f"Rule (D-047 rule 5): a feature is **stable** if it is in the top {TOP} of at least {NEED} of the 15 fold "
        f"models and its direction is the same in at least {NEED}. Overall ranking verdict: median pairwise "
        f"Spearman >= {STABLE_RHO} stable, {PARTLY_RHO}-{STABLE_RHO} partly stable, below {PARTLY_RHO} unstable. "
        "Each fold model is judged on all rows of its data set. Only stable features may be interpreted - at "
        "most 5 if the overall ranking is stable, at most 3 otherwise.")
    out()
    for k in SPECS:
        describe_stability(k, tabs[k], "all rows")
        table(["Rank (out-of-fold)", "Feature", "Mean abs SHAP", "Top 5 in", "Top 10 in", "Direction (12 of 15)",
               "Stable"], stability_rows(tabs[k]))
    fig_stability(tabs)

    out("### What may be interpreted")
    for k in SPECS:
        it = interpretable(tabs[k])
        names = ", ".join(f"{r.label} ({r.direction})" for r in it.itertuples()) or "nothing"
        out(f"- **{k}. {SPECS[k]['label']}:** {names}" + (" - read as *what a model that did not predict above "
            "chance relied on*" if k == "A" and len(it) else "") + ".")
    out()

    out("## 2. Global importance (10.2)")
    out("### Beeswarms (out-of-fold: each video explained only by fold models that did not see it, mean of 3)")
    fig_beeswarm(res["A"], tabs["A"], "shap_beeswarm_pooled",
                 "A. Pooled XGBoost M2 (did not predict above chance for unseen accounts)")
    fig_beeswarm(res["B"], tabs["B"], "shap_beeswarm_instagram",
                 "B. Instagram logistic regression M1 (exploratory)")
    out("Colour is the feature's value (blue low, red high); posting hour and follower tier are grey because each "
        "is two columns summed (D-047 rule 3) and has no single value.")
    out()
    out("### Importance by block")
    b = fig_blocks(tabs)
    table(["Model", "Block", "Features", "Sum of mean abs SHAP", "Per feature"],
          [[r.model, BLOCK_NAME[r.block], r.features,
            ("not measured" if r.block == "D" else "not in this model") if not r.features else f"{r['sum']:.3f}",
            "-" if not r.features else f"{r.per_feature:.3f}"] for _, r in b.iterrows()])
    out("Block D (creator) is empty in the pooled model: no creator feature survived (automated labels failed, "
        "D-038; `creator_collab` exists only on Instagram).")
    out()

    out("### Dependence plots")
    fig_dependence(res["A"], ["duration_sec"], "shap_dependence_duration_pooled",
                   "A. Duration (H1) - pooled XGBoost M2, by platform", by_platform=True)
    dep_b = ["duration_sec"] + [f for f in interpretable(tabs["B"])["feature"] if f != "duration_sec"]
    fig_dependence(res["B"], dep_b, "shap_dependence_instagram",
                   "B. Instagram logistic regression M1 - duration and the interpretable features",
                   by_platform=False)

    out("### Four waterfalls (model B only, D-047 rule 6)")
    pb = oof_saved[(oof_saved["data"] == "instagram") & (oof_saved["model"] == "LogReg")
                   & (oof_saved["set"] == "M1")].set_index("media_id")["p"]
    wf = fig_waterfalls(res["B"], pb)
    out("Picked without a threshold, from repeat 1's saved out-of-fold probabilities; the bars are the mean "
        "out-of-fold SHAP over the 3 repeats.")
    table(["Case", "Video", "Account", "Actually high?", "Predicted probability", "Sum of SHAP (log-odds)"],
          [[w["case"], w["media_id"], w["account"], "yes" if w["y"] else "no", f"{w['p']:.3f}",
            f"{w['sum_shap']:+.3f}"] for w in wf])

    out("## 3. Per-platform view of the pooled model (10.3, RQ7 / H9 - exploratory)")
    for view in ("youtube", "instagram"):
        describe_stability("A", ta[view], f"{NAME[view]} rows")
    yt, ig = ta["youtube"].set_index("feature"), ta["instagram"].set_index("feature")
    rows = []
    for f in ta["all"].sort_values("oof_rank")["feature"]:
        div = ""
        if yt.loc[f, "top5_folds"] >= NEED and (15 - ig.loc[f, "top10_folds"]) >= NEED:
            div = "**YouTube only**"
        elif ig.loc[f, "top5_folds"] >= NEED and (15 - yt.loc[f, "top10_folds"]) >= NEED:
            div = "**Instagram only**"
        rows.append([LABEL[f], int(yt.loc[f, "oof_rank"]), f"{yt.loc[f, 'top5_folds']} / 15",
                     int(ig.loc[f, "oof_rank"]), f"{ig.loc[f, 'top5_folds']} / 15", div or "no"])
    table(["Feature", "YouTube rank", "YouTube top 5 in", "Instagram rank", "Instagram top 5 in", "Divergent?"], rows)
    out("Divergent (D-047 rule 7): top 5 in at least 12 of 15 fold models on one platform and outside the top 10 in "
        "at least 12 of 15 on the other. 58 of the 72 YouTube rows come from one channel; model A did not predict "
        "above chance.")
    out()
    fig_platform(ta)

    shared = [f for f in M1]
    a_ig = ta["instagram"].set_index("feature").loc[shared, "oof_mean_abs_shap"]
    b_imp = tabs["B"].set_index("feature").loc[shared, "oof_mean_abs_shap"]
    r_ab = stats.spearmanr(a_ig, b_imp).statistic
    out(f"**Check on the Instagram view (docs/10 section 3):** Spearman between model A's importance on Instagram "
        f"rows and model B's, over the 20 shared content features: **{r_ab:.2f}**.")
    out()

    di = res["A"]["oof_int"]
    yi, ii = di[plat == "youtube"], di[plat == "instagram"]
    out(f"**H10 - duration x platform (SHAP interaction, model A, out-of-fold):** mean {yi.mean():+.4f} on YouTube "
        f"rows, {ii.mean():+.4f} on Instagram rows (log-odds; mean absolute {np.abs(di).mean():.4f}, against a mean "
        f"absolute duration SHAP of {np.abs(res['A']['oof'][:, res['A']['names'].index('duration_sec')]).mean():.4f}). "
        "An estimate from a model at chance, never 'significant'.")
    out()

    out("## 4. B against C, and the effective-video profile (D-047 rule 8)")
    tb, tc = tabs["B"].set_index("feature"), tabs["C"].set_index("feature")
    r_bc = stats.spearmanr(tb["oof_mean_abs_shap"], tc.loc[tb.index, "oof_mean_abs_shap"]).statistic
    out(f"Spearman between B's and C's out-of-fold importance over their 21 features: **{r_bc:.2f}**.")
    out()
    prof = []
    for f in interpretable(tabs["B"])["feature"]:
        db = tb.loc[f, "direction"]
        dc_sign = np.sign(tc.loc[f, "dir_pos_folds"] - tc.loc[f, "dir_neg_folds"])
        db_sign = 1 if db == "higher -> higher" else (-1 if db == "higher -> lower" else 0)
        agree = db_sign != 0 and dc_sign == db_sign
        prof.append([LABEL[f], db, int(tc.loc[f, "oof_rank"]),
                     f"+ in {tc.loc[f, 'dir_pos_folds']}, - in {tc.loc[f, 'dir_neg_folds']} of 15",
                     "**yes**" if agree else "no",
                     f"{res['B']['df'][f].astype(float).mean():.3g}" if agree else "-"])
    if prof:
        table(["Feature (stable in B)", "B direction", "C rank", "C direction (fold models)", "In the profile",
               "Instagram mean (where B's contribution changes sign)"], prof)
    in_profile = [p for p in prof if p[4] == "**yes**"]
    if in_profile:
        out("**Effective-video profile, Instagram only - exploratory association, not a recommendation:** "
            + "; ".join(f"{p[0]}: {p[1]}" for p in in_profile) + ". Follower count matters for real reach and is "
            "not in this content model; Instagram reach alone predicted below chance here (M0 0.46).")
    else:
        out("**Effective-video profile: not supported by this data** - no feature is stable in B with C agreeing "
            "on its direction.")
    out()
    out("**For the tool (D-047 rule 9):** drivers may come only from model B and only from: "
        + (", ".join(LABEL[f] for f in interpretable(tabs["B"])["feature"]) or "no feature") + ".")
    out()
    out(f"Run time {(time.time() - t0) / 60:.1f} min.")

    parts = []
    for t in (ta["all"], ta["youtube"], ta["instagram"], tabs["B"], tabs["C"]):
        u = t.copy()
        u.attrs = {}        # the per-fold arrays stay out of the combined table
        parts.append(u)
    pd.concat(parts).to_csv(IMPORTANCE, index=False)
    fold_rows = []
    for (key, view), t in [(("A", "all"), ta["all"]), (("A", "youtube"), ta["youtube"]),
                           (("A", "instagram"), ta["instagram"]), (("B", "all"), tabs["B"]), (("C", "all"), tabs["C"])]:
        names = res[key]["names"]
        for i, (imp, rk) in enumerate(zip(t.attrs["imp"], t.attrs["ranks"])):
            for nm, v, r in zip(names, imp, rk):
                fold_rows.append({"model": key, "view": view, "repeat": i // 5, "fold": i % 5, "feature": nm,
                                  "mean_abs_shap": v, "rank": int(r)})
    pd.DataFrame(fold_rows).to_csv(FOLD_IMPORTANCE, index=False)
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print("\n".join(LINES))


if __name__ == "__main__":
    main()

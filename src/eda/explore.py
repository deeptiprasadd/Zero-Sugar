"""Phase 7 - exploratory analysis (docs/07): proposal EDA 1-9 and diagnostics A-G.

Runs on the frozen analysis table (docs/08 section 6, row dated 2026-09-29) and the feature table.
**Focus set** = `in_focus & dv_status == "ok"` (192 usable Zero Sugar videos since D-039). The
non-Zero-Sugar usable rows appear only in panels labelled "robustness set", never mixed in.

What this does not do: no hypothesis test, no p-value, no model. EDA 8 follows docs/07 section 1b
exactly - composition tables before any engagement value, then a descriptive figure; the words
"differs descriptively" are the strongest it may use (researcher's go-ahead, 2026-09-29).

Outputs:
    reports/figures/eda_*.png        300 dpi, one per item, n (videos, accounts) in every title
    reports/eda_numbers.md           every number the findings log (docs/07 section 3) cites

Usage:
    python -m src.eda.explore
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from statsmodels.nonparametric.smoothers_lowess import lowess  # noqa: E402
from statsmodels.stats.outliers_influence import variance_inflation_factor  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

FIG = config.REPORTS / "figures"
NUMBERS = config.REPORTS / "eda_numbers.md"

# One fixed platform mapping for every figure (reference palette slots 1 and 2, which pass the
# all-pairs colour-vision checks in light mode); marker shape is the second cue.
COL = {"youtube": "#2a78d6", "instagram": "#eb6834"}
MARK = {"youtube": "o", "instagram": "^"}
NAME = {"youtube": "YouTube Shorts", "instagram": "Instagram Reels"}
GREY, INK, INK2, GRID, SURFACE = "#8a8984", "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"

FINAL20 = ["duration_sec", "cuts_per_sec", "motion_px_per_sec", "face_present_frac",
           "mean_face_area", "edge_density", "colourfulness", "red_ratio", "ocr_region_count",
           "ocr_mean_text_area", "music_frac", "talk_dur_frac", "loudness_db_mean",
           "loudness_range_db", "sentiment_caption", "caption_char_len", "hashtag_count",
           "emoji_count", "kw_event", "kw_promotional"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.titlesize": 10.5, "axes.titleweight": "bold", "axes.labelsize": 9,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "legend.fontsize": 8.5, "legend.frameon": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans",
})

LINES: list[str] = []


def out(s: str = "") -> None:
    LINES.append(s)


def table(df: pd.DataFrame, index: bool = True) -> None:
    """Markdown table without the optional `tabulate` package (not installed, not needed)."""
    t = df.reset_index() if index else df
    cols = [" / ".join(map(str, c)) if isinstance(c, tuple) else str(c) for c in t.columns]
    out("| " + " | ".join(cols) + " |")
    out("|" + "---|" * len(cols))
    for row in t.itertuples(index=False):
        out("| " + " | ".join(str(v) for v in row) + " |")
    out()


def nva(d: pd.DataFrame) -> str:
    return f"n = {len(d)} videos, {d['account'].nunique()} accounts"


def save(fig, name: str) -> None:
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    out(f"Figure: `reports/figures/{name}.png`")
    out()


def smooth(ax, x, y, color=INK2):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() >= 15:
        s = lowess(y[ok], x[ok], frac=0.6, return_sorted=True)
        ax.plot(s[:, 0], s[:, 1], color=color, lw=2)


def by_platform_scatter(ax, d, x, y, logx=False):
    for p in ("youtube", "instagram"):
        q = d[d["platform"] == p]
        ax.scatter(q[x], q[y], s=16, marker=MARK[p], color=COL[p], alpha=0.75,
                   edgecolor=SURFACE, linewidth=0.5, label=f"{NAME[p]} ({len(q)})")
    xs = np.log10(d[x].to_numpy(float)) if logx else d[x].to_numpy(float)
    ok = np.isfinite(xs)
    if logx:
        s = lowess(d[y].to_numpy(float)[ok], xs[ok], frac=0.6, return_sorted=True)
        ax.plot(10 ** s[:, 0], s[:, 1], color=INK2, lw=2, label="smoothed trend (both)")
        ax.set_xscale("log")
    else:
        smooth(ax, xs, d[y].to_numpy(float))
        ax.plot([], [], color=INK2, lw=2, label="smoothed trend (both)")


def strip_box(ax, groups: list[tuple[str, pd.DataFrame]], y: str):
    rng = np.random.default_rng(20260929)
    for i, (lab, g) in enumerate(groups):
        v = g[y].dropna().to_numpy(float)
        if len(v) >= 5:
            ax.boxplot(v, positions=[i], widths=0.5, showfliers=False, patch_artist=True,
                       boxprops=dict(facecolor="none", color=INK2, lw=1),
                       medianprops=dict(color=INK, lw=2), whiskerprops=dict(color=INK2),
                       capprops=dict(color=INK2))
        for p in ("youtube", "instagram"):
            w = g.loc[g["platform"] == p, y].dropna().to_numpy(float)
            ax.scatter(i + rng.uniform(-0.18, 0.18, len(w)), w, s=12, marker=MARK[p],
                       color=COL[p], alpha=0.7, edgecolor=SURFACE, linewidth=0.4)
    ax.set_xticks(range(len(groups)),
                  [f"{lab}\n(n={len(g)}, {g['account'].nunique()} acc.)" for lab, g in groups])


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dv = pd.read_parquet(config.PROCESSED / "dependent_variable.parquet")
    feats = pd.read_parquet(config.PROCESSED / "features.parquet")
    keep = [c for c in feats.columns if c not in dv.columns or c in ("platform", "media_id")]
    d = dv.merge(feats[keep], on=["platform", "media_id"], how="left", validate="1:1")
    d["log_er"] = np.log10(d["engagement_rate_follower"].where(d["engagement_rate_follower"] > 0))
    usable = d[d["dv_status"] == "ok"].copy()
    focus = usable[usable["in_focus"]].copy()
    robust = usable[~usable["in_focus"]].copy()
    return d, focus, robust


# ------------------------------------------------------------------------------------------ items
def eda1(d, focus, robust):
    out("## EDA 1 - distribution of videos")
    out(f"Focus set: {nva(focus)}. Robustness set (usable, not Zero Sugar): {nva(robust)}. "
        f"All rows: {len(d)}.")
    out()
    for col, title in [("year", "Year posted"), ("selection", "How the video entered"),
                       ("account_size_tier", "Follower tier"), ("region", "Region")]:
        t = pd.crosstab(focus[col], focus["platform"], margins=True, margins_name="total")
        out(f"**{title}, focus set**")
        table(t)
    lang = focus["lang_caption"].fillna("unknown")
    t = pd.crosstab(lang, focus["platform"])
    t = t.loc[t.sum(axis=1).sort_values(ascending=False).index]
    out("**Caption language, focus set**")
    table(t)

    fig, axs = plt.subplots(2, 2, figsize=(10, 7))
    for ax, col, title in [(axs[0, 0], "year", "Year posted"),
                           (axs[0, 1], "account_size_tier", "Follower tier"),
                           (axs[1, 0], "region", "Region"), (axs[1, 1], "lang_caption", "Caption language (top 8)")]:
        s = focus.assign(lang_caption=focus["lang_caption"].fillna("unknown"))
        t = pd.crosstab(s[col], s["platform"]).reindex(columns=["youtube", "instagram"], fill_value=0)
        t = t.loc[t.sum(axis=1).sort_values(ascending=False).index][:8] if col != "year" else t
        y = np.arange(len(t))
        ax.barh(y - 0.2, t["youtube"], 0.38, color=COL["youtube"], label=NAME["youtube"])
        ax.barh(y + 0.2, t["instagram"], 0.38, color=COL["instagram"], label=NAME["instagram"])
        ax.set_yticks(y, [str(i) for i in t.index]); ax.invert_yaxis(); ax.set_title(title, loc="left")
        ax.set_xlabel("videos"); ax.grid(axis="y", visible=False)
    fig.legend(*axs[0, 0].get_legend_handles_labels(), loc="lower center", ncols=2,
               bbox_to_anchor=(0.5, -0.03))
    fig.suptitle(f"EDA 1 - what is in the focus set ({nva(focus)})", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    save(fig, "eda1_composition")


def eda2(focus, robust):
    out("## EDA 2 - engagement distribution")
    er = focus["engagement_rate_follower"]
    out(f"Follower-normalised engagement rate, focus set: median {er.median():.4f}, "
        f"IQR {er.quantile(.25):.4f}-{er.quantile(.75):.4f}, max {er.max():.3f}, "
        f"skewness raw {er.skew():.2f} vs log10 {focus['log_er'].skew():.2f}; "
        f"zero rates: {int((er <= 0).sum())}.")
    pct = focus["engagement_pct"]
    out(f"Percentile (the modelling DV): median {pct.median():.3f}, mean {pct.mean():.3f}.")
    hi = focus["engagement_high"]
    share = float(hi.mean())
    out(f"**Median split in the focus set (docs/06 section 4 fallback rule): {int(hi.sum())} high / "
        f"{int((hi == 0).sum())} low = {share:.0%} / {1 - share:.0%}.** Rule: worse than 60/40 -> "
        f"use the focus set's own median. {'TRIGGERED' if max(share, 1 - share) > 0.60 else 'Not triggered'}.")
    out()
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.6))
    axs[0].hist(er, bins=40, color=GREY, edgecolor=SURFACE)
    axs[0].set_title("Raw rate - heavy right skew", loc="left"); axs[0].set_xlabel("(likes + comments) / followers")
    axs[1].hist(focus["log_er"].dropna(), bins=30, color=GREY, edgecolor=SURFACE, label=f"focus ({len(focus)})")
    axs[1].hist(robust["log_er"].dropna(), bins=30, histtype="step", color=INK, lw=1.2,
                label=f"robustness set ({len(robust)})")
    axs[1].set_title("log10 rate", loc="left"); axs[1].set_xlabel("log10 engagement rate"); axs[1].legend()
    axs[2].hist(pct, bins=20, color=GREY, edgecolor=SURFACE)
    axs[2].axvline(0.5, color=INK, lw=1, ls="--")
    axs[2].set_title("Percentile within platform x size", loc="left"); axs[2].set_xlabel("engagement percentile")
    for ax in axs:
        ax.set_ylabel("videos")
    fig.suptitle(f"EDA 2 - engagement, focus set ({nva(focus)})", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "eda2_engagement_distribution")


def eda3(focus):
    out("## EDA 3 - video duration")
    t = focus.groupby("platform")["duration_sec"].describe(percentiles=[.1, .5, .9]).round(1)
    table(t)
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
    bins = np.linspace(0, focus["duration_sec"].max() + 1, 30)
    for p in ("youtube", "instagram"):
        axs[0].hist(focus.loc[focus["platform"] == p, "duration_sec"], bins=bins, alpha=0.65,
                    color=COL[p], label=NAME[p])
    axs[0].set_xlabel("seconds"); axs[0].set_ylabel("videos"); axs[0].legend()
    axs[0].set_title("Duration by platform", loc="left")
    by_platform_scatter(axs[1], focus, "duration_sec", "engagement_pct")
    axs[1].set_xlabel("seconds"); axs[1].set_ylabel("engagement percentile")
    axs[1].set_title("Duration vs engagement (H1 preview, no test)", loc="left")
    fig.legend(*axs[1].get_legend_handles_labels(), loc="lower center", ncols=3, bbox_to_anchor=(0.5, -0.07))
    rho = focus[["duration_sec", "engagement_pct"]].corr(method="spearman").iloc[0, 1]
    out(f"Spearman duration vs percentile, focus set (descriptive only): {rho:.2f}.")
    out()
    fig.suptitle(f"EDA 3 - duration ({nva(focus)})", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "eda3_duration")


def eda5(focus):
    out("## EDA 5 - human presence")
    out("Celebrity and creator labels failed alpha (D-038), so presence is measured by faces only.")
    f = focus.copy()
    f["faces"] = pd.cut(f["face_present_frac"], [-0.01, 0, 0.5, 1.0],
                        labels=["no face", "face in up to half", "face in most frames"])
    t = f.groupby(["faces", "platform"], observed=False).size().unstack(fill_value=0)
    t["accounts"] = f.groupby("faces", observed=False)["account"].nunique()
    t["median percentile"] = f.groupby("faces", observed=False)["engagement_pct"].median().round(3)
    table(t)
    ig = f[f["platform"] == "instagram"]
    t2 = ig.groupby("creator_collab")["engagement_pct"].agg(["size", "median"]).round(3)
    out("**Instagram only - creator collaboration (from post metadata, 5.15)**")
    table(t2)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"width_ratios": [3, 2]})
    strip_box(axs[0], [(str(k), g) for k, g in f.groupby("faces", observed=False)], "engagement_pct")
    axs[0].set_ylabel("engagement percentile"); axs[0].set_title("Share of frames with a face", loc="left")
    strip_box(axs[1], [("no collab", ig[ig["creator_collab"] == False]),  # noqa: E712
                       ("creator collab", ig[ig["creator_collab"] == True])], "engagement_pct")  # noqa: E712
    axs[1].set_title("Instagram: creator collaboration", loc="left")
    for p in ("youtube", "instagram"):
        axs[0].scatter([], [], marker=MARK[p], color=COL[p], label=NAME[p])
    fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncols=2,
               bbox_to_anchor=(0.5, -0.06))
    fig.suptitle(f"EDA 5 - people on screen ({nva(focus)})", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "eda5_human_presence")


def eda6(focus):
    out("## EDA 6 - emotional content")
    sp = focus[focus["emotion_label"].notna()]
    out(f"Emotion label exists only where there is speech, post-translation (D-031): {nva(sp)}.")
    t = sp.groupby("emotion_label")["engagement_pct"].agg(["size", "median"]).round(3)
    t["accounts"] = sp.groupby("emotion_label")["account"].nunique()
    table(t.sort_values("size", ascending=False))
    rho = focus[["sentiment_caption", "engagement_pct"]].corr(method="spearman").iloc[0, 1]
    out(f"Caption sentiment available for {int(focus['sentiment_caption'].notna().sum())} focus videos; "
        f"Spearman with percentile {rho:.2f} (descriptive). Reminder (D-031): sentiment shrinks "
        f"with text length.")
    rl = focus[["sentiment_caption", "caption_char_len"]].corr(method="spearman").iloc[0, 1]
    out(f"Spearman caption sentiment vs caption length, focus set: {rl:.2f}.")
    out()
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    by_platform_scatter(axs[0], focus.dropna(subset=["sentiment_caption"]), "sentiment_caption", "engagement_pct")
    axs[0].set_xlabel("caption sentiment (-1 negative ... +1 positive)"); axs[0].set_ylabel("engagement percentile")
    axs[0].set_title("Caption sentiment", loc="left")
    fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncols=3, bbox_to_anchor=(0.5, -0.07))
    groups = [(k, g) for k, g in sp.groupby("emotion_label") if len(g) >= 5]
    strip_box(axs[1], groups, "engagement_pct")
    axs[1].set_title("Emotion of speech (labels with 5+ videos)", loc="left")
    axs[1].tick_params(axis="x", labelsize=7.5)
    fig.suptitle(f"EDA 6 - emotional tone ({nva(focus)}; speech {len(sp)})", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    save(fig, "eda6_emotion")


def eda7(focus):
    out("## EDA 7 - caption and text")
    cols = ["caption_char_len", "hashtag_count", "emoji_count", "ocr_region_count"]
    table(focus.groupby("platform")[cols].median().round(1))
    kw = focus[["kw_event", "kw_promotional"]].apply(lambda s: s.map({True: "yes", False: "no"}))
    for c in kw.columns:
        g = focus.assign(k=kw[c]).groupby("k")["engagement_pct"].agg(["size", "median"]).round(3)
        out(f"**{c}**")
        table(g)
    fig, axs = plt.subplots(2, 3, figsize=(13, 7.5))
    for ax, c, lab, logx in [(axs[0, 0], "caption_char_len", "caption length (characters)", True),
                             (axs[0, 1], "hashtag_count", "hashtags", False),
                             (axs[0, 2], "emoji_count", "emoji", False),
                             (axs[1, 0], "ocr_region_count", "on-screen text regions per frame", False)]:
        d = focus[focus[c].notna() & ((focus[c] > 0) if logx else True)]
        by_platform_scatter(ax, d, c, "engagement_pct", logx=logx)
        ax.set_xlabel(lab); ax.set_ylabel("engagement percentile"); ax.set_title(lab.capitalize(), loc="left")
    for ax, c in [(axs[1, 1], "kw_event"), (axs[1, 2], "kw_promotional")]:
        strip_box(ax, [("no", focus[focus[c] == False]), ("yes", focus[focus[c] == True])],  # noqa: E712
                  "engagement_pct")
        ax.set_title(c, loc="left")
    fig.legend(*axs[0, 0].get_legend_handles_labels(), loc="lower center", ncols=3,
               bbox_to_anchor=(0.5, -0.03))
    fig.suptitle(f"EDA 7 - caption and text ({nva(focus)})", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "eda7_text")


def eda8(focus, robust):
    out("## EDA 8 - YouTube vs Instagram (docs/07 section 1b; descriptive, no test)")
    out("### 1. Composition - before any engagement value")
    t = focus.groupby(["platform", "selection"]).agg(videos=("media_id", "size"),
                                                     accounts=("account", "nunique"))
    t["thin (<20 videos or <3 accounts)"] = (t["videos"] < 20) | (t["accounts"] < 3)
    table(t)
    t = focus.groupby(["platform", "account_size_tier"]).agg(videos=("media_id", "size"),
                                                             accounts=("account", "nunique"))
    t["thin (<20 videos or <3 accounts)"] = (t["videos"] < 20) | (t["accounts"] < 3)
    table(t)
    top = focus[focus["platform"] == "youtube"]["account"].value_counts()
    out(f"YouTube: {top.iloc[0]} of {top.sum()} videos come from one channel ({top.index[0]}).")
    out()
    out("### 2. How each Zero Sugar label was decided")
    table(pd.crosstab(focus["zs_label_method"], focus["platform"], margins=True, margins_name="total"))
    out("By-eye label repeat reliability: YouTube 16 of 25, alpha 0.25 (D-029); Instagram 4 of 9, "
        "alpha -0.10 (D-039). The label decides inclusion (D-030).")
    out()
    out("### 3. Engagement by platform (descriptive)")
    g = focus.groupby("platform")["log_er"].describe(percentiles=[.25, .5, .75]).round(3)
    table(g)
    g2 = focus.groupby(["platform", "selection"])["log_er"].agg(["size", "median"]).round(3)
    table(g2)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [2, 1]})
    rng = np.random.default_rng(20260929)
    glob = top.index[0]
    for i, p in enumerate(("youtube", "instagram")):
        q = focus[focus["platform"] == p]
        v = q["log_er"].to_numpy(float)
        axs[0].boxplot(v[np.isfinite(v)], positions=[i], widths=0.5, showfliers=False, patch_artist=True,
                       boxprops=dict(facecolor="none", color=INK2), medianprops=dict(color=INK, lw=2),
                       whiskerprops=dict(color=INK2), capprops=dict(color=INK2))
        for sub, face, lab in [(q[(q["selection"] == "hand_picked")], "none", "hand-picked Reel"),
                               (q[(q["account"] == glob)], COL[p], f"global channel ({glob})"),
                               (q[(q["selection"] != "hand_picked") & (q["account"] != glob)], COL[p], "other")]:
            if not len(sub):
                continue
            axs[0].scatter(i + rng.uniform(-0.2, 0.2, len(sub)), sub["log_er"], s=16,
                           marker="D" if "global" in lab else MARK[p],
                           facecolor=face, edgecolor=COL[p], linewidth=0.9, alpha=0.8,
                           label=f"{NAME[p]}: {lab} ({len(sub)})")
    axs[0].set_xticks([0, 1], [f"{NAME[p]}\n({nva(focus[focus['platform'] == p])})" for p in ("youtube", "instagram")])
    axs[0].set_ylabel("log10 engagement rate (follower-normalised)")
    axs[0].set_title("Focus set - Zero Sugar", loc="left")
    axs[0].legend(loc="lower center", fontsize=7, ncols=2, bbox_to_anchor=(0.5, -0.42))
    for i, p in enumerate(("youtube", "instagram")):
        q = robust[robust["platform"] == p]
        axs[1].scatter(i + rng.uniform(-0.2, 0.2, len(q)), q["log_er"], s=12, marker=MARK[p],
                       color=COL[p], alpha=0.6, edgecolor=SURFACE, linewidth=0.4)
    axs[1].set_xticks([0, 1], [f"{NAME[p]}\n({nva(robust[robust['platform'] == p])})" for p in ("youtube", "instagram")])
    axs[1].set_title("Robustness set - not Zero Sugar", loc="left")
    axs[1].set_ylim(axs[0].get_ylim())
    fig.suptitle("EDA 8 - engagement by platform, descriptive only (no test; composition differs, "
                 "see tables)", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "eda8_platform_descriptive")


def eda9_c(focus):
    out("## EDA 9 / Diagnostic C - correlation among the 20 features, and VIF")
    x = focus[FINAL20].astype(float)
    c = x.corr(method="spearman")
    pairs = [(a, b, c.loc[a, b]) for i, a in enumerate(FINAL20) for b in FINAL20[i + 1:]]
    strong = sorted([p for p in pairs if abs(p[2]) >= 0.5], key=lambda p: -abs(p[2]))
    out(f"Pairs with |Spearman| >= 0.5: {len(strong)}; max {max(abs(p[2]) for p in pairs):.2f}.")
    for a, b, v in strong:
        out(f"- `{a}` - `{b}`: {v:.2f}")
    out()
    z = x.fillna(x.median())
    z = (z - z.mean()) / z.std()
    vif = pd.Series([variance_inflation_factor(z.to_numpy(), i) for i in range(z.shape[1])],
                    index=FINAL20).sort_values(ascending=False).round(2)
    out(f"VIF (median-imputed for this diagnostic only): max {vif.max():.2f} (`{vif.index[0]}`); "
        f"above 5: {int((vif > 5).sum())}; above 10: {int((vif > 10).sum())}.")
    table(vif.to_frame("VIF"))
    fig, ax = plt.subplots(figsize=(9, 7.5))
    im = ax.imshow(c.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(20), FINAL20, rotation=90, fontsize=7.5)
    ax.set_yticks(range(20), FINAL20, fontsize=7.5)
    ax.grid(False)
    for i in range(20):
        for j in range(20):
            if i != j and abs(c.iloc[i, j]) >= 0.5:
                ax.text(j, i, f"{c.iloc[i, j]:.2f}", ha="center", va="center", fontsize=6,
                        color="white" if abs(c.iloc[i, j]) > 0.7 else INK)
    fig.colorbar(im, ax=ax, shrink=0.7, label="Spearman correlation")
    ax.set_title(f"EDA 9 / C - the 20 features ({nva(focus)}); values shown where |r| >= 0.5",
                 loc="left")
    fig.tight_layout()
    save(fig, "eda9_feature_correlation")


def diag_a(focus):
    out("## Diagnostic A - videos per account")
    t = focus.groupby(["account", "platform"]).size().sort_values(ascending=False)
    top = t.iloc[0]
    out(f"{len(t)} accounts. Largest: {t.index[0][0]} ({t.index[0][1]}) with {top} videos = "
        f"{top / len(focus):.0%} of the focus set. Accounts with 1 video: {int((t == 1).sum())}.")
    out()
    table(t.to_frame("videos").reset_index(), index=False)
    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(len(t))
    ax.barh(y, t.to_numpy(), color=[COL[p] for _, p in t.index], height=0.7)
    ax.set_yticks(y, [a for a, _ in t.index], fontsize=7.5); ax.invert_yaxis()
    ax.set_xlabel("videos"); ax.grid(axis="y", visible=False)
    for v, yy in zip(t.to_numpy(), y):
        ax.text(v + 0.5, yy, str(v), va="center", fontsize=7, color=INK2)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=COL[p], label=NAME[p]) for p in ("youtube", "instagram")],
              loc="lower right")
    ax.set_title(f"Diagnostic A - videos per account ({nva(focus)})", loc="left")
    fig.tight_layout()
    save(fig, "diagA_videos_per_account")


def diag_b(focus):
    out("## Diagnostic B - engagement vs video age")
    rho = focus[["video_age_days", "log_er"]].corr(method="spearman").iloc[0, 1]
    rho2 = focus[["video_age_days", "engagement_pct"]].corr(method="spearman").iloc[0, 1]
    out(f"Age range {focus['video_age_days'].min():.0f}-{focus['video_age_days'].max():.0f} days "
        f"(median {focus['video_age_days'].median():.0f}). Spearman age vs log10 rate {rho:.2f}; "
        f"vs percentile {rho2:.2f} (descriptive).")
    out()
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    by_platform_scatter(axs[0], focus, "video_age_days", "log_er", logx=True)
    axs[0].set_xlabel("video age at reading (days, log scale)"); axs[0].set_ylabel("log10 engagement rate")
    axs[0].set_title("Raw rate", loc="left")
    fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncols=3, bbox_to_anchor=(0.5, -0.07))
    by_platform_scatter(axs[1], focus, "video_age_days", "engagement_pct", logx=True)
    axs[1].set_xlabel("video age at reading (days, log scale)"); axs[1].set_ylabel("engagement percentile")
    axs[1].set_title("Percentile", loc="left")
    fig.suptitle(f"Diagnostic B - age ({nva(focus)})", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "diagB_age")


def diag_d(d, focus):
    out("## Diagnostic D - missingness")
    cols = FINAL20 + ["engagement_rate_follower", "engagement_rate_view"]
    m = focus[cols].isna()
    s = m.mean().sort_values(ascending=False)
    out("Missing share in the focus set (non-zero only):")
    table(s[s > 0].round(3).to_frame("missing"))
    out(f"All rows: dv_status counts {d['dv_status'].value_counts().to_dict()}.")
    out()
    fig, ax = plt.subplots(figsize=(10, 5))
    # YouTube first, so the divider and the axis labels sit over the right rows
    order = focus.assign(_p=(focus["platform"] != "youtube").astype(int)).sort_values(["_p", "account"]).index
    ax.imshow(m.loc[order].T.to_numpy(), aspect="auto", cmap="Greys", interpolation="nearest")
    ax.set_yticks(range(len(cols)), cols, fontsize=7); ax.grid(False)
    nyt = int((focus["platform"] == "youtube").sum())
    ax.axvline(nyt - 0.5, color=INK, lw=1)
    ax.set_xticks([nyt / 2, nyt + (len(focus) - nyt) / 2], ["YouTube", "Instagram"])
    ax.set_title(f"Diagnostic D - missing values, black = missing ({nva(focus)})", loc="left")
    fig.tight_layout()
    save(fig, "diagD_missingness")


def diag_e(focus):
    out("## Diagnostic E - sampling balance by platform")
    for col in ["selection", "account_type", "account_size_tier"]:
        t = pd.crosstab(focus[col].fillna("brand channel (YouTube)"), focus["platform"], normalize="columns").round(3)
        out(f"**{col}, share of each platform's focus videos**")
        table(t)
    out("Every YouTube Short is posted by a brand channel; Instagram adds creator posts through "
        f"collaborations ({int(focus.loc[focus['platform'] == 'instagram', 'creator_collab'].sum())} "
        "focus Reels flagged `creator_collab`).")
    out()


def diag_f(focus):
    out("## Diagnostic F - cross-posted pairs (the same video on both platforms)")
    meta = pd.read_parquet(config.INTERIM / "clip_vitl14_frames_meta.parquet")
    emb = np.load(config.INTERIM / "clip_vitl14_frames.npy").astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    meta["i"] = np.arange(len(meta))
    vec = {}
    for (p, m), g in meta.groupby(["platform", "media_id"]):
        v = emb[g["i"].to_numpy()].mean(axis=0)
        vec[(p, m)] = v / np.linalg.norm(v)
    yt = focus[focus["platform"] == "youtube"]
    ig = focus[focus["platform"] == "instagram"]
    Y = np.stack([vec[("youtube", m)] for m in yt["media_id"]])
    I = np.stack([vec[("instagram", m)] for m in ig["media_id"]])
    sim = Y @ I.T
    dur_ok = np.abs(yt["duration_sec"].to_numpy()[:, None] - ig["duration_sec"].to_numpy()[None, :]) <= 1.0
    cand = np.argwhere((sim >= 0.95) & dur_ok)
    rows = [(yt.iloc[a]["media_id"], ig.iloc[b]["media_id"], round(float(sim[a, b]), 3),
             yt.iloc[a]["duration_sec"], ig.iloc[b]["duration_sec"]) for a, b in cand]
    pairs = pd.DataFrame(rows, columns=["youtube", "instagram", "similarity", "yt_sec", "ig_sec"])
    # one-to-one: keep the best match for each video
    pairs = pairs.sort_values("similarity", ascending=False)
    pairs = pairs.drop_duplicates("youtube").drop_duplicates("instagram")
    out(f"Rule (fixed before looking): mean CLIP frame embedding cosine >= 0.95 and durations within "
        f"1 s; one-to-one. **{len(pairs)} candidate pairs in the focus set** (the paired "
        f"sub-analysis needs >= 20, docs/08 section 2).")
    loose = int(((sim >= 0.90) & dur_ok).any(axis=1).sum())
    out(f"Sensitivity: with cosine >= 0.90, {loose} YouTube Shorts have some Instagram match.")
    out()
    if len(pairs):
        table(pairs, index=False)
    pairs.to_csv(config.REPORTS / "eda_crossposted_pairs.csv", index=False)
    return pairs


def diag_g(focus):
    out("## Diagnostic G - market x platform")
    t = pd.crosstab(focus["market"], focus["platform"])
    t["accounts"] = focus.groupby("market")["account"].nunique()
    table(t.sort_values(["youtube", "instagram"], ascending=False))
    out(f"Markets on both platforms: {int(((t['youtube'] > 0) & (t['instagram'] > 0)).sum())} of {len(t)}.")
    out()


def cuts_scale(focus, d):
    out("## Decision input (TODO 7.2) - the scale of `cuts_per_sec`")
    c = d["cuts_per_sec"]
    out(f"All 300: max {c.max():.2f}, next {c.nlargest(2).iloc[1]:.2f}, 99th pct {c.quantile(.99):.2f}; "
        f"skewness raw {c.skew():.2f}, log1p {np.log1p(c).skew():.2f}. In the focus set the max is "
        f"{focus['cuts_per_sec'].max():.2f}.")
    out()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    FIG.mkdir(parents=True, exist_ok=True)
    d, focus, robust = load()
    out("# Exploration numbers (Phase 7)")
    out()
    out(f"Frozen analysis table: docs/08 section 6, row dated 2026-09-29. Focus set: {nva(focus)}. "
        "No test, p-value or model appears here.")
    out()
    eda1(d, focus, robust); eda2(focus, robust); eda3(focus)
    out("## EDA 4 - product visibility: not drawn (D-037, not measured)")
    out()
    eda5(focus); eda6(focus); eda7(focus); eda8(focus, robust); eda9_c(focus)
    diag_a(focus); diag_b(focus); diag_d(d, focus); diag_e(focus); diag_f(focus); diag_g(focus)
    cuts_scale(focus, d)
    NUMBERS.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print(f"-> {NUMBERS.relative_to(config.ROOT)} and {len(list(FIG.glob('eda*.png')) + list(FIG.glob('diag*.png')))} figures")


if __name__ == "__main__":
    main()

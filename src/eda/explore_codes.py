"""P12 - exploration with the hand codes, exactly as fixed in D-050 (descriptive only: no test, no p-value).

EDA 4 (product visibility), EDA 5 (four people groups), EDA 6 (humour, excitement, voice tone), EDA 8
rows (each new measure's make-up by platform, then a figure), EDA 9 (Spearman of each yes/no measure with
the engagement percentile, as description), and the two unchecked automated labels against the hand codes.
Every table is also given without the 15 AI-character Shorts.

Usage:
    python -m src.eda.explore_codes
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.focus_codes import H, LABEL, PEOPLE_ORDER, with_focus  # noqa: E402
from src.eda.explore import COL, GRID, INK2, MARK, NAME, strip_box  # noqa: E402  (also sets the figure style)
from src.features.reliability import alpha_nominal  # noqa: E402
from src.stats.hypotheses import load  # noqa: E402

OUT = config.REPORTS / "eda_codes.md"
FIG = config.REPORTS / "figures"
PEOPLE_NAME = {"none": "no person", "ordinary_people": "ordinary people", "influencer": "creator",
               "celebrity": "celebrity"}
LINES: list[str] = []


def out(s: str = "") -> None:
    LINES.append(s)


def save(fig, name: str) -> None:
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    out(f"Figure: `reports/figures/{name}.png`")
    out()


def group_table(d: pd.DataFrame, col: str, order: list[str], names: dict | None = None) -> None:
    out(f"| Group | Videos | Accounts | Instagram / YouTube | Median percentile | Median without AI-character Shorts |")
    out("|---|---|---|---|---|---|")
    for g in order:
        s = d[d[col] == g]
        s2 = s[~s["ai_characters"]]
        out(f"| {(names or {}).get(g, g)} | {len(s)} | {s['account'].nunique()} | "
            f"{int((s['platform'] == 'instagram').sum())} / {int((s['platform'] == 'youtube').sum())} | "
            f"{s['pct'].median():.3f} | {s2['pct'].median():.3f} ({len(s2)}) |")
    miss = d[col].isna().sum()
    out(f"| missing (unsure or blank) | {miss} | | | {d.loc[d[col].isna(), 'pct'].median():.3f} | |")
    out()


def composition(d: pd.DataFrame) -> None:
    out("## EDA 8 rows - make-up of every new measure by platform (counts, % of the platform's videos)")
    out("| Measure | Instagram (120) | YouTube (72) |")
    out("|---|---|---|")
    for h in H:
        cells = []
        for p in ("instagram", "youtube"):
            s = d.loc[d["platform"] == p, h]
            cells.append(f"yes {int((s == 1).sum())} ({(s == 1).mean():.0%}), no {int((s == 0).sum())}, "
                         f"missing {int(s.isna().sum())}")
        out(f"| {LABEL[h]} | {cells[0]} | {cells[1]} |")
    for col, name in (("people_group", "people group"), ("music_group", "music"), ("campaign_group", "campaign"),
                      ("voice_group", "voice tone")):
        cells = []
        for p in ("instagram", "youtube"):
            vc = d.loc[d["platform"] == p, col].value_counts(dropna=False)
            cells.append(", ".join(f"{('missing' if pd.isna(k) else PEOPLE_NAME.get(k, k))} {v}" for k, v in vc.items()))
        out(f"| {name} | {cells[0]} | {cells[1]} |")
    out()
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    y = np.arange(len(H))[::-1]
    for k, p in enumerate(("youtube", "instagram")):
        share = [d.loc[d["platform"] == p, h].mean() for h in H]
        ax.barh(y + (0.2 if p == "instagram" else -0.2), share, height=0.38, color=COL[p], label=NAME[p])
    ax.set_yticks(y, [LABEL[h] for h in H])
    ax.set_xlim(0, 1)
    ax.set_xlabel("share of the platform's coded videos with 'yes' (missing left out)")
    ax.set_title("EDA 8 - the hand-coded measures by platform (192 videos, 22 accounts; composition, not engagement)",
                 loc="left", fontsize=9.5)
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    save(fig, "eda8_codes_by_platform")


def figure_groups(d: pd.DataFrame, panels: list[tuple[str, list[str], dict, str]], name: str, title: str) -> None:
    fig, axes = plt.subplots(1, len(panels), figsize=(4.4 * len(panels), 4.2), squeeze=False)
    for ax, (col, order, names, sub) in zip(axes[0], panels):
        groups = [((names or {}).get(g, g), d[d[col] == g]) for g in order]
        strip_box(ax, groups, "pct")
        ax.set_ylabel("engagement percentile (within platform x follower tier)")
        ax.set_title(sub, loc="left", fontsize=9.5)
        ax.set_ylim(-0.02, 1.02)
    handles = [plt.Line2D([], [], marker=MARK[p], color=COL[p], ls="", label=NAME[p]) for p in ("youtube", "instagram")]
    fig.suptitle(title, x=0.01, ha="left", fontsize=10, fontweight="bold")
    fig.tight_layout()
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2, fontsize=8)
    save(fig, name)


def spearman_table(d: pd.DataFrame) -> None:
    out("## EDA 9 - each yes/no measure against the engagement percentile (description; no test)")
    out("Spearman rho; 'without AI' leaves out the 15 AI-character Shorts. Read as association in this sample "
        "only - the tests are P13 (`reports/statistical_results_added.md`).")
    out("| Measure | Videos coded | rho | rho without AI | Median pct, yes / no |")
    out("|---|---|---|---|---|")
    for h in H:
        s = d[d[h].notna()]
        s2 = s[~s["ai_characters"]]
        r = stats.spearmanr(s[h], s["pct"]).statistic
        r2 = stats.spearmanr(s2[h], s2["pct"]).statistic
        out(f"| {LABEL[h]} | {len(s)} | {r:+.3f} | {r2:+.3f} | {s.loc[s[h] == 1, 'pct'].median():.3f} / "
            f"{s.loc[s[h] == 0, 'pct'].median():.3f} |")
    out()


def automated_vs_hand(d: pd.DataFrame) -> None:
    out("## The two unchecked automated labels against the hand codes (D-038 labels; they stay out of every model)")
    out("| Label | Pairs | Raw agreement | Alpha | Hand: product or UGC / Model: product or UGC |")
    out("|---|---|---|---|---|")
    for col, pos in (("product_vs_lifestyle", "product"), ("ugc_vs_brand", "ugc")):
        a = d[col].where(d[col].isin(["product", "lifestyle"] if pos == "product" else ["ugc", "brand"]))
        b = d[f"auto_{col}"].where(d[f"auto_{col}"].isin(["product", "lifestyle"] if pos == "product" else ["ugc", "brand"]))
        keep = a.notna() & b.notna()
        x, y = a[keep].to_numpy(object), b[keep].to_numpy(object)
        out(f"| {col} | {int(keep.sum())} | {(x == y).mean():.0%} | {alpha_nominal(x, y):.2f} | "
            f"{int((x == pos).sum())} / {int((y == pos).sum())} |")
    out()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _, focus = load()
    d = with_focus(focus)
    out("# P12 - exploration with the hand codes (D-050)")
    out()
    out(f"Focus set {len(d)} videos, {d['account'].nunique()} accounts. Hand codes from `focus_codes_FINAL.csv` "
        "(one coder, 9 Oct; 110 minutes for 100 minutes of video; repeat reliability in `reports/repeat_check.md`). "
        "'Unsure' and blank are missing. Descriptive only - no test, no p-value. The engagement percentile is "
        "ranked within platform and follower tier. Zero Sugar label reliability: YouTube alpha 0.25, Instagram -0.10.")
    out()
    composition(d)
    out("## EDA 4 - product visibility (can or bottle)")
    group_table(d, "product_group", ["none or brief", "prominent"])
    figure_groups(d, [("product_group", ["none or brief", "prominent"], {}, "Can or bottle on screen")],
                  "eda4_product_visibility", "EDA 4 - engagement by product visibility (hand-coded)")
    out("## EDA 5 - people: none, ordinary people, creator, celebrity")
    group_table(d, "people_group", PEOPLE_ORDER, PEOPLE_NAME)
    figure_groups(d, [("people_group", PEOPLE_ORDER, PEOPLE_NAME, "Who appears (63 videos missing: unsure)")],
                  "eda5_people_groups", "EDA 5 - engagement by people group (hand-coded; YouTube has no celebrity)")
    out("## EDA 6 - humour, excitement, voice tone")
    d["humour_g"] = d["hc_humour"].map({1.0: "funny", 0.0: "not funny"})
    d["excite_g"] = d["hc_excitement"].map({1.0: "exciting", 0.0: "not exciting"})
    group_table(d, "humour_g", ["funny", "not funny"])
    group_table(d, "excite_g", ["exciting", "not exciting"])
    group_table(d, "voice_group", ["excited", "calm", "no voice"])
    figure_groups(d, [("humour_g", ["funny", "not funny"], {}, "Humour"),
                      ("excite_g", ["exciting", "not exciting"], {}, "Excitement"),
                      ("voice_group", ["excited", "calm", "no voice"], {}, "Voice tone")],
                  "eda6_tone", "EDA 6 - engagement by tone (hand-coded)")
    out("## Music and campaign type (descriptive; not in the models, D-050)")
    group_table(d, "music_group", ["cinematic", "no music", "pop", "other"])
    group_table(d, "campaign_group", ["promotion", "event", "food", "new product", "general or seasonal"])
    spearman_table(d)
    automated_vs_hand(d)            # load() already carries the auto_* columns from features.parquet
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print("\n".join(LINES))


if __name__ == "__main__":
    main()

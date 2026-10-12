"""P17 - the effective-video profile (proposal Objective 15), exactly as fixed in D-052.

Every measure with evidence is listed: the Instagram model-based items of D-047 rule 8 (from
`reports/shap_importance.csv`) and the statistically detected associations (H6 of D-043; H2, H4, H5 of
D-051). Each carries the checks fixed in advance - within accounts, without the 15 AI-character Shorts,
repeat reliability - and the one-line profile names only the items that pass every check that applies.
YouTube is described, not modelled: high- vs low-engagement videos side by side with Instagram, no test.

Usage:
    python -m src.eda.profile
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.focus_codes import with_focus  # noqa: E402
from src.stats.hypotheses import fmt_p, load  # noqa: E402
from src.stats.hypotheses_added import TESTS, run_tests, within_account  # noqa: E402

OUT = config.REPORTS / "effective_video_profile.md"
SHAP = config.REPORTS / "shap_importance.csv"

# item -> (column, plain name, kind of value, repeat reliability from P11 / measurement note)
ITEMS = {
    "hashtag_count": ("hashtags", "count", "automated count (exact)"),
    "talk_dur_frac": ("share of the video with talking", "share", "automated (speech model)"),
    "face_present_frac": ("share of frames with a face", "share", "automated (face detector)"),
    "hc_cta": ("a call to action", "yes/no", "hand-coded; repeat alpha 0.50 (weakly reliable)"),
    "hc_product_prominent": ("a can or bottle shown prominently", "yes/no", "hand-coded; repeat alpha 0.48 (weakly reliable)"),
    "hc_creator_or_celebrity": ("a creator or celebrity", "yes/no", "hand-coded; repeat alpha 0.38 / 0.52 (weakly reliable)"),
}


# wording of each item inside the one-line profile ("videos with ...")
ONE_LINE = {"hashtag_count": "more hashtags", "talk_dur_frac": "more talking", "face_present_frac": "more frames showing a face",
            "hc_cta": "a call to action", "hc_product_prominent": "a can or bottle shown prominently",
            "hc_creator_or_celebrity": "a creator or celebrity"}


def model_evidence() -> dict[str, dict]:
    """D-047 rule 8 on the saved SHAP tables: stable in model B and the same direction in model C."""
    t = pd.read_csv(SHAP)
    b = t[(t["model"] == "B") & (t["view"] == "all")].set_index("feature")
    c = t[(t["model"] == "C") & (t["view"] == "all")].set_index("feature")
    out = {}
    for f in b.index[b["stable"]]:
        sign_b = 1 if b.loc[f, "direction"] == "higher -> higher" else -1
        sign_c = np.sign(c.loc[f, "dir_pos_folds"] - c.loc[f, "dir_neg_folds"])
        out[f] = {"direction": "more -> higher" if sign_b > 0 else "more -> lower", "c_agrees": sign_c == sign_b,
                  "label": f"stable in the Instagram logistic model (top 5 in {b.loc[f, 'top5_folds']}/15); "
                           f"Instagram XGBoost {'agrees' if sign_c == sign_b else 'disagrees'}"}
    return out


def statistical_evidence(d: pd.DataFrame) -> dict[str, dict]:
    out = {}
    # H6 hashtags (registered family, D-043): Spearman; checks recomputed the same way
    s = d[d["hashtag_count"].notna()]
    r_all = stats.spearmanr(s["hashtag_count"], s["pct"])
    s2 = s[~s["ai_characters"]]
    r_noai = stats.spearmanr(s2["hashtag_count"], s2["pct"])
    rw, pw, _ = within_account(d, "hashtag_count")
    out["hashtag_count"] = {"test": f"H6, Spearman rho {r_all.statistic:+.3f}, BH p 0.009 (D-043)",
                            "within": (pw < 0.05 and rw > 0, f"rho {rw:+.2f} (p {fmt_p(pw)})"),
                            "noai": (r_noai.pvalue < 0.05, f"rho {r_noai.statistic:+.2f} (p {fmt_p(r_noai.pvalue)})")}
    # H2, H4, H5 (addition family, D-051)
    fam = pd.read_csv(config.REPORTS / "statistical_family_added.csv")
    noai = pd.DataFrame(run_tests(d[~d["ai_characters"]]))
    for h, col, _ in TESTS:
        f = fam[fam["H"] == h]
        n = noai[noai["H"] == h]
        rw, pw, _ = within_account(d, col)
        lr = f[f["test"].str.startswith("LR")].iloc[0]
        out[col] = {"test": f"{h}, {lr['effect'].split(' (')[0]}, BH p {fmt_p(lr['p_bh'])} (LR) / "
                            f"{fmt_p(f[f['test'] == 'Mann-Whitney U'].iloc[0]['p_bh'])} (rank) (D-051)",
                    "within": (pw < 0.05 and rw > 0, f"rho {rw:+.2f} (p {fmt_p(pw)})"),
                    "noai": (bool((n["p"] < 0.05).any()),
                             " / ".join(f"{fmt_p(p)}" for p in n["p"]) + " (LR / rank)")}
    return out


def side_by_side(d: pd.DataFrame, col: str, kind: str) -> tuple[str, str, str]:
    cells, signs = [], []
    for p in ("instagram", "youtube"):
        s = d[(d["platform"] == p) & d[col].notna()]
        hi, lo = s.loc[s["engagement_high"] == 1, col], s.loc[s["engagement_high"] == 0, col]
        if kind == "yes/no":
            a, b = hi.mean(), lo.mean()
            cells.append(f"{a:.0%} vs {b:.0%}")
        elif kind == "count":
            a, b = hi.mean(), lo.mean()
            cells.append(f"mean {a:.1f} vs {b:.1f}")
        else:
            a, b = hi.median(), lo.median()
            cells.append(f"median {a:.2f} vs {b:.2f}")
        signs.append(np.sign(a - b))
    same = "same" if signs[0] == signs[1] and signs[0] != 0 else ("no difference on YouTube" if signs[1] == 0 else "opposite")
    return cells[0], cells[1], same


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    warnings.filterwarnings("ignore")
    _, focus = load()
    d = with_focus(focus)
    d["engagement_high"] = d["engagement_high"].astype(int)
    ig = d[d["platform"] == "instagram"]
    model = model_evidence()
    stat = statistical_evidence(d)

    rows, passing = [], []
    for col, (name, kind, rel) in ITEMS.items():
        ev, checks = [], []
        if col in model:
            ev.append("model (Instagram): " + model[col]["label"])
            checks.append(model[col]["c_agrees"])
        if col in stat:
            ev.append("statistics: " + stat[col]["test"])
            checks += [stat[col]["within"][0], stat[col]["noai"][0]]
        ok = all(checks)
        if ok:
            passing.append((col, name, "Instagram (model-based, exploratory)" if col in model and col not in stat
                            else "both platforms pooled (statistics)"))
        rows.append([name, "; ".join(ev),
                     stat[col]["within"][1] + (" - holds" if stat[col]["within"][0] else " - between accounts")
                     if col in stat else "not tested (no detected test)",
                     stat[col]["noai"][1] + (" - survives" if stat[col]["noai"][0] else " - does not survive")
                     if col in stat else "-", rel, "**yes**" if ok else "no"])

    L = ["# P17 - the effective-video profile (D-052; proposal Objective 15)", "",
         "An empirical profile, not a recommendation. Engagement is ranked within platform and follower tier, so "
         "the profile says nothing about reach; follower count matters for real reach and is not in it. Every "
         "measure with evidence is listed with the checks fixed before its result was known (D-047, D-050). Zero "
         "Sugar label reliability: YouTube alpha 0.25, Instagram -0.10. Hand codes: one coder, about one video per "
         "30 seconds.", ""]
    L += ["## The profile in one line", ""]
    ig_items = [ONE_LINE[c] for c, n, w in passing if w.startswith("Instagram")]
    both = [ONE_LINE[c] for c, n, w in passing if w.startswith("both")]
    L.append("Among these Coca-Cola Zero Sugar short videos, **on Instagram** videos with "
             + (" and ".join(ig_items) if ig_items else "no measure")
             + " were associated with higher engagement (model-based, exploratory); **on both platforms pooled**, "
             "videos with " + (" and ".join(both) if both else "no measure")
             + " were associated with higher engagement (statistics; measure weakly reliable). Only items that "
             "pass every check that applies to them are named here; the table shows the rest.")
    L += ["", "## Every item with evidence", "",
          "| Measure | Evidence | Within accounts | Without the 15 AI-character Shorts | Measurement | In the one-line profile |",
          "|---|---|---|---|---|---|"]
    L += ["| " + " | ".join(r) + " |" for r in rows]
    L += ["", "Reading: hashtags pass the model checks but are associated with engagement only *between* accounts - "
          "they describe accounts that use more hashtags, not a lever for one video. Product prominence and creator "
          "or celebrity presence depend on one 15-video AI-character series.", ""]
    L += ["## Instagram and YouTube side by side (description, no test)", "",
          "High- vs low-engagement videos within each platform (shares for yes/no measures, means for hashtags, "
          "medians for shares of the video). YouTube: 72 videos from 5 channels, 58 from one - read its column as "
          "a description of mostly one channel.", "",
          "| Measure | Instagram: high vs low | YouTube: high vs low | YouTube direction |", "|---|---|---|---|"]
    for col, (name, kind, _) in ITEMS.items():
        a, b, same = side_by_side(d, col, kind)
        L.append(f"| {name} | {a} | {b} | {same} |")
    L += ["", "## Where the Instagram model's contribution changes sign (the threshold column of docs/10 section 5)", "",
          "The logistic model has no cut-off of its own; its contribution turns positive above the training average:",
          "", "| Measure | Instagram average (120 videos) |", "|---|---|"]
    for col in model:
        L.append(f"| {ITEMS[col][0]} | {ig[col].astype(float).mean():.3g} |")
    L += ["", "No YouTube profile is model-based: no YouTube model can be tested fairly (D-041)."]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()

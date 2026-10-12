"""P13 - H2, H4 and H5 with the hand codes, a declared addition exactly as fixed in D-050.

Same mixed model as D-042 (account random intercept; platform, log followers, log video age as
controls; five optimisers via `fit()`), percentile outcome, complete cases per test. The six tests are
their own Benjamini-Hochberg family; the 14-test family of D-042 is not re-opened. Everything is also run
without the 15 AI-character Shorts (beside, not in the family).

Usage:
    python -m src.stats.hypotheses_added
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import TTestIndPower

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.focus_codes import LABEL, PEOPLE_ORDER, with_focus  # noqa: E402
from src.stats.hypotheses import CONTROLS, fit, fmt_p, load, lr_test  # noqa: E402

OUT = config.REPORTS / "statistical_results_added.md"
FAMILY_CSV = config.REPORTS / "statistical_family_added.csv"
TESTS = [("H2", "hc_product_prominent", "product prominent vs none-or-brief"),
         ("H4", "hc_creator_or_celebrity", "creator or celebrity vs neither"),
         ("H5", "hc_cta", "call to action vs none")]
OTHER = ["hc_logo_prominent", "hc_excitement", "hc_voice_excited", "hc_sponsored", "hc_lifestyle", "hc_ugc"]
LINES: list[str] = []


def out(s: str = "") -> None:
    LINES.append(s)


def mde(n1: int, n0: int) -> float:
    """Smallest standardised difference detectable at 80% power, alpha 0.05 (no clustering: a lower bound)."""
    return float(TTestIndPower().solve_power(nobs1=n1, ratio=n0 / n1, alpha=0.05, power=0.8))


def run_tests(d: pd.DataFrame) -> list[dict]:
    rows = []
    for h, col, desc in TESTS:
        s = d[d[col].notna()].copy()
        r = lr_test(CONTROLS, [col], s)
        m, conv = fit(f"pct ~ {CONTROLS} + {col}", s)
        ci = m.conf_int().loc[col]
        a, b = s.loc[s[col] == 1, "pct"].to_numpy(float), s.loc[s[col] == 0, "pct"].to_numpy(float)
        U, p_mw = stats.mannwhitneyu(a, b, alternative="two-sided")
        rb = 2 * U / (len(a) * len(b)) - 1
        base = {"H": h, "measure": desc, "n": len(s), "accounts": s["account"].nunique(), "n_yes": len(a),
                "n_no": len(b), "mde_d": mde(len(a), len(b))}
        rows.append({**base, "test": "LR test (mixed model), 1 df", "p": r["p"], "conv": r["conv"] and conv,
                     "effect": f"{100 * m.params[col]:+.1f} pct points ({100 * ci[0]:+.1f} to {100 * ci[1]:+.1f})"})
        rows.append({**base, "test": "Mann-Whitney U", "p": float(p_mw), "conv": True,
                     "effect": f"r_rb {rb:+.3f}; medians {np.median(a):.3f} vs {np.median(b):.3f}"})
    return rows


def within_account(d: pd.DataFrame, col: str) -> tuple[float, float, int]:
    s = d[d[col].notna()]
    x = s[col] - s.groupby("account")[col].transform("mean")
    y = s["pct"] - s.groupby("account")["pct"].transform("mean")
    r, p = stats.spearmanr(x, y)
    return float(r), float(p), len(s)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    warnings.filterwarnings("ignore")
    _, focus = load()
    d = with_focus(focus)
    out("# P13 - H2, H4, H5 with the hand codes - a declared addition (D-050)")
    out()
    out(f"Focus set {len(d)} videos, {d['account'].nunique()} accounts; complete cases per test. Outcome: engagement "
        "percentile (within platform x follower tier). Mixed model with an account intercept; controls platform, log "
        "followers, log video age (D-042). **The six tests below are their own Benjamini-Hochberg family (q = 0.05); "
        "the 14-test family of D-042 is unchanged.** Hand codes: one coder (9 Oct), 110 minutes for 100 minutes of "
        "video; repeat reliability (P11): call to action alpha 0.50, creator 0.38, celebrity 0.52, product none-vs-any "
        "0.48 - all weakly reliable. Zero Sugar label: YouTube alpha 0.25, Instagram -0.10. Effects in percentile "
        "points (0-100).")
    out()
    fam = pd.DataFrame(run_tests(d))
    fam["p_bh"] = multipletests(fam["p"], method="fdr_bh")[1]
    fam["verdict"] = np.where(fam["p_bh"] < 0.05, "detected", "not detected at this sample size")
    sens = pd.DataFrame(run_tests(d[~d["ai_characters"]]))
    out("## The addition family")
    out("| H | Measure | n (yes / no), accounts | Test | Effect (95% CI) | Raw p | BH p | Verdict | Without AI-character Shorts: raw p | Min. detectable d |")
    out("|---|---|---|---|---|---|---|---|---|---|")
    for (_, r), (_, r2) in zip(fam.iterrows(), sens.iterrows()):
        out(f"| {r.H} | {r.measure} | {r.n} ({r.n_yes} / {r.n_no}), {r.accounts} | {r.test} | {r.effect} | "
            f"{fmt_p(r.p)} | {fmt_p(r.p_bh)} | **{r.verdict}** | {fmt_p(r2.p)} ({r2.effect.split(' (')[0]}) | "
            f"{r.mde_d:.2f} |")
    out()
    out("Fits converged: " + ", ".join(f"{r.H} {r.test.split(' ')[0]} {r.conv}" for r in fam.itertuples()) + ".")
    out()
    det = fam[fam["verdict"] == "detected"]
    if len(det):
        out("## Within-account check for each detected hypothesis (D-043 style; describes, changes no verdict)")
        for col_h in det["H"].unique():
            col = dict((h, c) for h, c, _ in TESTS)[col_h]
            r, p, n = within_account(d, col)
            out(f"- {col_h} ({LABEL[col]}): with each account's mean removed, Spearman rho {r:+.3f} (p {fmt_p(p)}, "
                f"n {n}) - " + ("the association holds within accounts." if p < 0.05 and r > 0 else
                                "the association is mainly between accounts, not within them."))
        out()
    out("## Outside the family - estimates only, never 'significant'")
    s = d[d["people_group"].notna()]
    groups = [s.loc[s["people_group"] == g, "pct"].to_numpy(float) for g in PEOPLE_ORDER]
    Hk, _ = stats.kruskal(*groups)
    out(f"Four people groups (Kruskal-Wallis, n {len(s)}): epsilon^2 {Hk / (len(s) - 1):.3f}; medians "
        + ", ".join(f"{g} {np.median(v):.3f} ({len(v)})" for g, v in zip(PEOPLE_ORDER, groups))
        + ". YouTube has no celebrity video, and the 17 celebrity videos come from 5 Instagram accounts.")
    out()
    out("Mixed-model coefficient of each other measure, added alone to the controls (percentile points, 95% CI):")
    out("| Measure | n | Coefficient | 95% CI | Without AI-character Shorts |")
    out("|---|---|---|---|---|")
    for col in OTHER:
        cells = []
        for frame in (d, d[~d["ai_characters"]]):
            t = frame[frame[col].notna()]
            m, _ = fit(f"pct ~ {CONTROLS} + {col}", t)
            ci = m.conf_int().loc[col]
            cells.append((len(t), 100 * m.params[col], 100 * ci[0], 100 * ci[1]))
        (n, b, lo, hi), (_, b2, lo2, hi2) = cells
        out(f"| {LABEL[col]} | {n} | {b:+.1f} | {lo:+.1f} to {hi:+.1f} | {b2:+.1f} ({lo2:+.1f} to {hi2:+.1f}) |")
    for col, name in (("music_group", "music (reference: cinematic)"),
                      ("campaign_group", "campaign (reference: promotion)")):
        ref = "cinematic" if col == "music_group" else "promotion"
        t = d[d[col].notna()]
        m, _ = fit(f"pct ~ {CONTROLS} + C({col}, Treatment('{ref}'))", t)
        ci = m.conf_int()
        for term in [x for x in m.params.index if x.startswith(f"C({col}")]:
            lvl = term.split("[T.")[1].rstrip("]")
            out(f"| {name}: {lvl} | {len(t)} | {100 * m.params[term]:+.1f} | {100 * ci.loc[term, 0]:+.1f} to "
                f"{100 * ci.loc[term, 1]:+.1f} | - |")
    out()
    out("Wording (D-042): 'associated with', never 'causes'; a test not detected is 'not detected at this sample size' "
        "with its minimum detectable effect (a lower bound: account clustering makes it larger).")
    fam.to_csv(FAMILY_CSV, index=False)
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print("\n".join(LINES))


if __name__ == "__main__":
    main()

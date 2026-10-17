"""P20 - speech rate, brand and product mentions, and YouTube views: a declared addition exactly as fixed in D-056.

Same mixed model as D-042 (account random intercept, five optimisers via `fit()`), complete cases per test.
Ten tests, their own Benjamini-Hochberg family; the D-042 and D-050 families are not re-opened. Every test is
also run without the 15 AI-character Shorts (beside the family, not in it).

    pooled, engagement percentile:  speech rate, product named (Zero Sugar), brand named (Coca-Cola)
    YouTube, view-based rate:       hashtags, call to action (hand-coded)

Usage:
    python -m src.stats.hypotheses_p20
"""
from __future__ import annotations

import sys
import unicodedata
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import TTestIndPower

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.focus_codes import with_focus  # noqa: E402
from src.features import common  # noqa: E402
from src.stats.hypotheses import CONTROLS, fit, fmt_p, load  # noqa: E402

OUT = config.REPORTS / "statistical_results_p20.md"
FAMILY_CSV = config.REPORTS / "statistical_family_p20.csv"
YT_CONTROLS = "log_followers + log_age"
# The Coca-Cola name, fixed in D-056 before any test: Latin forms and the corpus's other scripts.
BRAND_TERMS = ["coca-cola", "coca cola", "cocacola", "coke", "كوكاكولا", "كوكا كولا", "โค้ก", "코카콜라", "코크",
               "कोका-कोला", "कोका कोला"]
LINES: list[str] = []


def out(s: str = "") -> None:
    LINES.append(s)


def norm(text: object) -> str:
    return unicodedata.normalize("NFKC", str(text or "")).casefold()


def brand_named(caption: str, transcript_en: str) -> bool:
    """The Coca-Cola name in the caption or in the English translation of the speech (D-056)."""
    blob = norm(caption) + "\n" + norm(transcript_en)
    return any(norm(t) in blob for t in BRAND_TERMS)


# ------------------------------------------------------------------------------------------ data
def data() -> pd.DataFrame:
    _, focus = load()
    d = with_focus(focus)
    idx = common.video_index()
    caption = dict(zip(zip(idx["platform"], idx["media_id"]), idx["caption"]))
    asr = {(p, m): common.read_cache(p, m).get("asr") or {} for p, m in zip(d["platform"], d["media_id"])}
    d["speech_rate"] = pd.to_numeric(d["words_per_min"])
    d["product_named"] = d["kw_zero_sugar"].map({True: 1.0, False: 0.0})
    d["brand_named"] = [float(brand_named(caption[(p, m)], asr[(p, m)].get("transcript_en")))
                        for p, m in zip(d["platform"], d["media_id"])]
    vr = d["engagement_rate_view"].astype(float)
    pos = vr[vr > 0]
    d["vr_zeros"] = int((vr <= 0).sum())
    d["log10_vr"] = np.log10(vr.where(~(vr <= 0), pos.min() / 2))     # missing (Instagram) stays missing
    return d


# ------------------------------------------------------------------------------------------ tests
def lr_p(outcome: str, base: str, col: str, s: pd.DataFrame) -> tuple[float, bool]:
    m0, c0 = fit(f"{outcome} ~ {base}", s, reml=False)
    m1, c1 = fit(f"{outcome} ~ {base} + {col}", s, reml=False)
    return float(stats.chi2.sf(max(2 * (m1.llf - m0.llf), 0), 1)), c0 and c1


def mde_d(n1: int, n0: int) -> float:
    return float(TTestIndPower().solve_power(nobs1=n1, ratio=n0 / n1, alpha=0.05, power=0.8))


def mde_r(n: int) -> float:
    return float(np.tanh((stats.norm.ppf(0.975) + stats.norm.ppf(0.8)) / np.sqrt(n - 3)))


def effect_text(outcome: str, b: float, lo: float, hi: float, per: str) -> str:
    if outcome == "pct":
        return f"{100 * b:+.1f} pct points {per} ({100 * lo:+.1f} to {100 * hi:+.1f})"
    return f"x{10 ** b:.2f} per-view rate {per} ({10 ** lo:.2f} to {10 ** hi:.2f})"


def one(k: int, outcome: str, base: str, col: str, kind: str, label: str, d: pd.DataFrame) -> list[dict]:
    s = d[d[col].notna() & d[outcome].notna()].copy()
    term = col
    if kind == "continuous":
        s["x_z"] = (s[col] - s[col].mean()) / s[col].std()
        term = "x_z"
    p, conv = lr_p(outcome, base, term, s)
    m, conv2 = fit(f"{outcome} ~ {base} + {term}", s)
    b, (lo, hi) = float(m.params[term]), m.conf_int().loc[term].tolist()
    base_row = {"test_no": k, "outcome": "percentile (pooled)" if outcome == "pct" else "view-based rate (YouTube)",
                "measure": label, "n": len(s), "accounts": s["account"].nunique()}
    rows = [{**base_row, "test": "LR test (mixed model), 1 df", "p": p, "conv": conv and conv2,
             "effect": effect_text(outcome, b, lo, hi, "per SD" if kind == "continuous" else "yes vs no")}]
    if kind == "continuous":
        r, p2 = stats.spearmanr(s[col], s[outcome])
        rows.append({**base_row, "test_no": k + 1, "test": "Spearman", "p": float(p2), "conv": True,
                     "effect": f"rho {r:+.3f}", "mde": f"r {mde_r(len(s)):.2f}"})
        rows[0]["mde"] = f"r {mde_r(len(s)):.2f}"
    else:
        a, c = s.loc[s[col] == 1, outcome].to_numpy(float), s.loc[s[col] == 0, outcome].to_numpy(float)
        U, p2 = stats.mannwhitneyu(a, c, alternative="two-sided")
        rb = 2 * U / (len(a) * len(c)) - 1
        md = f"d {mde_d(len(a), len(c)):.2f} ({len(a)} yes / {len(c)} no)"
        rows[0]["mde"] = md
        rows.append({**base_row, "test_no": k + 1, "test": "Mann-Whitney U", "p": float(p2), "conv": True,
                     "effect": f"r_rb {rb:+.3f}; medians {np.median(a):.3f} vs {np.median(c):.3f}", "mde": md})
    return rows


TESTS = [  # (first test number, outcome, controls, column, kind, label, rows)
    (1, "pct", CONTROLS, "speech_rate", "continuous", "speech rate (words per minute)", "pooled"),
    (3, "pct", CONTROLS, "product_named", "binary", "product named (Zero Sugar)", "pooled"),
    (5, "pct", CONTROLS, "brand_named", "binary", "brand named (Coca-Cola)", "pooled"),
    (7, "log10_vr", YT_CONTROLS, "hashtag_count", "continuous", "hashtags", "youtube"),
    (9, "log10_vr", YT_CONTROLS, "hc_cta", "binary", "call to action (hand-coded)", "youtube"),
]


def run(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for k, outcome, base, col, kind, label, where in TESTS:
        s = d if where == "pooled" else d[d["platform"] == "youtube"]
        rows += one(k, outcome, base, col, kind, label, s)
    return pd.DataFrame(rows)


def within_account(d: pd.DataFrame, outcome: str, col: str) -> tuple[float, float, int]:
    s = d[d[col].notna() & d[outcome].notna()]
    x = s[col] - s.groupby("account")[col].transform("mean")
    y = s[outcome] - s.groupby("account")[outcome].transform("mean")
    r, p = stats.spearmanr(x, y)
    return float(r), float(p), len(s)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    warnings.filterwarnings("ignore")
    d = data()
    yt = d[d["platform"] == "youtube"]
    out("# P20 - speech rate, brand and product mentions, YouTube views - a declared addition (D-056)")
    out()
    out(f"Focus set {len(d)} videos, {d['account'].nunique()} accounts; complete cases per test. Pooled tests: "
        "engagement percentile (within platform x follower tier), mixed model with an account intercept, controls "
        "platform, log followers, log video age (D-042). YouTube tests: log10 of (likes + comments) / views, controls "
        f"log followers and log video age, {len(yt)} videos from {yt['account'].nunique()} channels "
        f"({int((yt['account'] == yt['account'].mode()[0]).sum())} from one). **The ten tests are their own "
        "Benjamini-Hochberg family (q = 0.05); the D-042 and D-050 families are unchanged.** Zero Sugar label: "
        "YouTube alpha 0.25, Instagram -0.10. Call to action: one coder, alpha 0.50. Zero view-based rates "
        f"replaced before the log: {int(d['vr_zeros'].iloc[0])}.")
    out()
    out(f"Coverage: speech rate {int(d['speech_rate'].notna().sum())} videos; product named "
        f"{int((d['product_named'] == 1).sum())} yes / {int((d['product_named'] == 0).sum())} no / "
        f"{int(d['product_named'].isna().sum())} not searched; brand named {int((d['brand_named'] == 1).sum())} of "
        f"{len(d)} (every YouTube video: {bool((yt['brand_named'] == 1).all())}; so its estimate rests on the "
        f"{int((d['brand_named'] == 0).sum())} Reels that do not name it).")
    out()
    fam = run(d)
    fam["p_bh"] = multipletests(fam["p"], method="fdr_bh")[1]
    fam["verdict"] = np.where(fam["p_bh"] < 0.05, "detected", "not detected at this sample size")
    sens = run(d[~d["ai_characters"]])
    out("## The P20 family")
    out("| # | Outcome | Measure | n, accounts | Test | Effect (95% CI) | Raw p | BH p | Verdict | Without AI-character Shorts: effect, raw p | Min. detectable |")
    out("|---|---|---|---|---|---|---|---|---|---|---|")
    for (_, r), (_, r2) in zip(fam.iterrows(), sens.iterrows()):
        out(f"| {r.test_no} | {r.outcome} | {r.measure} | {r.n}, {r.accounts} | {r.test} | {r.effect} | {fmt_p(r.p)} | "
            f"{fmt_p(r.p_bh)} | **{r.verdict}** | {r2.effect.split(' (')[0]}, {fmt_p(r2.p)} (n {r2.n}) | {r.mde} |")
    out()
    out("Fits converged: " + ", ".join(f"#{r.test_no} {r.conv}" for r in fam.itertuples()) + ".")
    out()
    det = fam[fam["verdict"] == "detected"]
    if len(det):
        out("## Within-account check for each detected test (D-043 style; describes, changes no verdict)")
        for no in sorted(det["test_no"].unique()):
            k, outcome, _, col, _, label, where = [t for t in TESTS if no in (t[0], t[0] + 1)][0]
            s = d if where == "pooled" else yt
            r, p, n = within_account(s, outcome, col)
            out(f"- #{no} {label}: with each account's mean removed, Spearman rho {r:+.3f} (p {fmt_p(p)}, n {n}).")
        out()
    out("## Description only - the two YouTube engagement measures side by side")
    r, p = stats.spearmanr(yt["log10_vr"], yt["pct"])
    r2, p2 = stats.spearmanr(yt.loc[~yt["ai_characters"], "log10_vr"], yt.loc[~yt["ai_characters"], "pct"])
    out(f"Spearman between the view-based rate and the follower-based percentile, {len(yt)} YouTube videos: rho {r:+.3f} "
        f"(without the AI-character Shorts {r2:+.3f}, n {int((~yt['ai_characters']).sum())}). No test; per docs/06 the "
        "view-based measure is within-YouTube only and is never carried into a platform comparison.")
    out()
    out("Wording (D-042, D-056): 'associated with', never 'causes'; a test not detected is 'not detected at this "
        "sample size' with its minimum detectable effect (a lower bound: account clustering makes it larger).")
    fam.to_csv(FAMILY_CSV, index=False)
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print("\n".join(LINES))


if __name__ == "__main__":
    main()

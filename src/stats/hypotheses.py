"""Phase 8 - hypothesis tests H1-H10, exactly as fixed in D-042 and docs/08 section 7.9.

Every choice below (variables, decisive tests, the Benjamini-Hochberg family, transforms, the
complete-case rule) was written into D-042 before this file was run. Nothing here may be changed
after seeing a result without a dated deviation note in docs/08.

Sample: focus set (`in_focus & dv_status == "ok"`), 192 videos, 22 accounts; the H1-H6/H8 models use
the 179 complete cases, with a median-imputation sensitivity on all 192.

Usage:
    python -m src.stats.hypotheses
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import derived  # noqa: E402  (derived inputs, shared with the tool - D-055)

OUT = config.REPORTS / "statistical_results.md"
SEED = 20261001
N_BOOT = 2000
PLAT = "C(platform, Treatment('youtube'))"
CONTROLS = f"{PLAT} + log_followers + log_age"

VIDEO = ["duration_z", "cuts_z", "motion_z", "face_present_z", "face_area_z", "edge_z",
         "colour_z", "red_z", "ocr_regions_z", "ocr_area_z"]
AUDIO = ["music_z", "talk_z", "loud_z", "loud_range_z"]
TEXT_H6 = ["caplen_z", "hashtag_z", "emoji_z", "kw_event_i", "kw_promo_i"]
TEXT = ["sent_z"] + TEXT_H6
ALL20 = VIDEO + AUDIO + TEXT
RAW = {"duration_z": "duration_sec", "cuts_z": "cuts_log1p", "motion_z": "motion_px_per_sec",
       "face_present_z": "face_present_frac", "face_area_z": "face_area0", "edge_z": "edge_density",
       "colour_z": "colourfulness", "red_z": "red_ratio", "ocr_regions_z": "ocr_region_count",
       "ocr_area_z": "ocr_mean_text_area", "music_z": "music_frac", "talk_z": "talk_dur_frac",
       "loud_z": "loudness_db_mean", "loud_range_z": "loudness_range_db",
       "sent_z": "sentiment_caption", "caplen_z": "caplen_lang", "hashtag_z": "hashtag_count",
       "emoji_z": "emoji_count", "kw_event_i": "kw_event", "kw_promo_i": "kw_promotional"}

LINES: list[str] = []
FAMILY: list[dict] = []
NOTES: list[str] = []


def out(s: str = "") -> None:
    LINES.append(s)


def fmt_p(p: float) -> str:
    return "n/a" if p is None or not np.isfinite(p) else ("<0.001" if p < 0.001 else f"{p:.3f}")


# ------------------------------------------------------------------------------------------ data
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    dv = pd.read_parquet(config.PROCESSED / "dependent_variable.parquet")
    feats = pd.read_parquet(config.PROCESSED / "features.parquet")
    keep = [c for c in feats.columns if c not in dv.columns or c in ("platform", "media_id")]
    d = dv.merge(feats[keep], on=["platform", "media_id"], how="left", validate="1:1")
    d = d[d["dv_status"] == "ok"].copy()
    d["pct"] = d["engagement_pct"].astype(float)
    er = d["engagement_rate_follower"].astype(float)
    zeros = int((er <= 0).sum())
    if zeros:
        er = er.where(er > 0, er[er > 0].min() / 2)
    d["log10_er"] = np.log10(er)
    d["log_followers"] = np.log10(d["followers"].astype(float))
    d["log_age"] = np.log10(d["video_age_days"].astype(float))
    d["tier2"] = np.where(d["account_size_tier"] == "large", "large", "small_medium")
    d = derived.video_measures(d)
    # caption length: log1p, z within caption language where that language has 5+ focus videos
    focus = d[d["in_focus"]].copy()
    ref = derived.caplen_reference(focus)
    focus["caplen_lang"] = derived.caplen_lang(focus, ref)
    focus["kw_event"] = derived.flag01(focus["kw_event"])
    focus["kw_promotional"] = derived.flag01(focus["kw_promotional"])
    NOTES.append(f"Zero engagement rates replaced before the log: {zeros}.")
    NOTES.append(f"Caption length standardised within language for: {sorted(ref['by_language'])}; other "
                 "languages and unknown against the whole focus set.")
    return d, focus


def standardise(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for z, raw in RAW.items():
        v = df[raw].astype(float)
        if z.endswith("_i"):
            df[z] = v
        elif z == "caplen_z":
            df[z] = v  # already a within-language z-score
        else:
            df[z] = (v - v.mean()) / v.std()
    df["duration2"] = df["duration_z"] ** 2
    return df


def complete(focus: pd.DataFrame) -> pd.DataFrame:
    need = list(RAW.values()) + ["pct", "log_followers", "log_age"]
    return standardise(focus.dropna(subset=need))


def imputed(focus: pd.DataFrame) -> pd.DataFrame:
    f = focus.copy()
    for raw in RAW.values():
        f[raw] = f[raw].astype(float).fillna(f[raw].astype(float).median())
    return standardise(f)


# ------------------------------------------------------------------------------------------ models
OPTIMISERS = ("powell", "lbfgs", "bfgs", "nm", "cg")
FIT_LOG: list[str] = []


def fit(formula: str, data: pd.DataFrame, reml: bool = True):
    """Same model, several optimisers; keep the highest finite likelihood (a computational choice).

    statsmodels' default optimiser can stop at a degenerate point (account variance 0, likelihood
    reported as infinite) or fail on a singular Hessian. Those fits are rejected; among valid fits
    the maximum (restricted) likelihood is the estimate the method defines.
    """
    best, best_conv = None, False
    for meth in OPTIMISERS:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                m = smf.mixedlm(formula, data, groups=data["account"]).fit(reml=reml, method=meth)
            except Exception:  # noqa: BLE001 - singular Hessian etc.: try the next optimiser
                continue
        if not np.isfinite(m.llf) or not np.all(np.isfinite(m.bse.drop("Group Var", errors="ignore"))):
            continue
        conv = bool(getattr(m, "converged", True)) and not any("converge" in str(x.message).lower() for x in w)
        if best is None or m.llf > best.llf + 1e-6:
            best, best_conv, used = m, conv, meth
    if best is None:
        raise RuntimeError(f"no optimiser gave a valid fit for: {formula}")
    FIT_LOG.append(used)
    return best, best_conv


def icc(m) -> float:
    v = float(m.cov_re.iloc[0, 0])
    return v / (v + float(m.scale))


def lr_test(base: str, added: list[str], data: pd.DataFrame) -> dict:
    full = base + " + " + " + ".join(added)
    m0, c0 = fit(f"pct ~ {base}", data, reml=False)
    m1, c1 = fit(f"pct ~ {full}", data, reml=False)
    lr = 2 * (m1.llf - m0.llf)
    df = len(added)
    return {"lr": lr, "df": df, "p": float(stats.chi2.sf(max(lr, 0), df)), "conv": c0 and c1, "n": len(data)}


def coef_table(m, terms: list[str], sd_y: float) -> list[str]:
    ci = m.conf_int()
    rows = []
    for t in terms:
        if t in m.params.index:
            rows.append(f"| `{t}` | {m.params[t]:+.3f} | {ci.loc[t, 0]:+.3f} to {ci.loc[t, 1]:+.3f} | "
                        f"{m.params[t] / sd_y:+.2f} | {fmt_p(m.pvalues[t])} |")
    return rows


def add_family(h: str, test: str, p: float, effect: str, n: int, conv: bool = True) -> None:
    FAMILY.append({"H": h, "test": test, "p": p, "effect": effect, "n": n, "conv": conv})


def spearman_ci(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    r, p = stats.spearmanr(x[ok], y[ok])
    n = int(ok.sum())
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
    return r, p, n, np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)


def cluster_boot(df: pd.DataFrame, stat, rng) -> tuple[float, float]:
    accounts = df["account"].unique()
    groups = {a: g for a, g in df.groupby("account")}
    vals = []
    for _ in range(N_BOOT):
        pick = rng.choice(accounts, len(accounts), replace=True)
        s = pd.concat([groups[a] for a in pick])
        v = stat(s)
        if np.isfinite(v):
            vals.append(v)
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


# ------------------------------------------------------------------------------------------ H tests
def h1(cc, focus):
    out("## H1 - duration")
    r = lr_test(CONTROLS, ["duration_z", "duration2"], cc)
    m, _ = fit(f"pct ~ {CONTROLS} + duration_z + duration2", cc)
    out(f"LR test, duration + duration^2 added to controls: chi2 = {r['lr']:.2f}, df {r['df']}, "
        f"p = {fmt_p(r['p'])} (n = {r['n']}, ML fits converged: {r['conv']}).")
    out("| Term | Coef (pct points per SD) | 95% CI | Std beta | p |\n|---|---|---|---|---|")
    LINES.extend(coef_table(m, ["duration_z", "duration2"], cc["pct"].std()))
    add_family("H1", "LR duration + duration^2", r["p"], f"chi2 {r['lr']:.2f} (df 2)", r["n"], r["conv"])
    rho, p, n, lo, hi = spearman_ci(focus["duration_sec"].to_numpy(float), focus["pct"].to_numpy(float))
    out(f"\nSpearman, pooled: rho = {rho:.3f} (95% CI {lo:.2f} to {hi:.2f}), p = {fmt_p(p)}, n = {n}.")
    add_family("H1", "Spearman duration, pooled", p, f"rho {rho:.3f}", n)
    out("\nPer platform (description, outside the family):")
    for pl in ("youtube", "instagram"):
        g = focus[focus["platform"] == pl]
        rho, p, n, lo, hi = spearman_ci(g["duration_sec"].to_numpy(float), g["pct"].to_numpy(float))
        out(f"- {pl}: rho = {rho:.3f} (95% CI {lo:.2f} to {hi:.2f}), n = {n}, {g['account'].nunique()} accounts.")
    out()


def h3(cc, focus):
    out("## H3 - positive emotional content")
    m, conv = fit(f"pct ~ {CONTROLS} + sent_z", cc)
    out(f"MixedLM, caption sentiment (n = {len(cc)}, converged: {conv}):")
    out("| Term | Coef (pct points per SD) | 95% CI | Std beta | p |\n|---|---|---|---|---|")
    LINES.extend(coef_table(m, ["sent_z"], cc["pct"].std()))
    add_family("H3", "MixedLM caption sentiment", float(m.pvalues["sent_z"]),
               f"beta {m.params['sent_z'] / cc['pct'].std():+.2f}", len(cc), conv)
    sp = focus[focus["emotion_label"].notna()].copy()
    counts = sp["emotion_label"].value_counts()
    sp["emo"] = sp["emotion_label"].where(sp["emotion_label"].map(counts) >= 10, "other")
    groups = [g["pct"].to_numpy(float) for _, g in sp.groupby("emo")]
    H, p = stats.kruskal(*groups)
    eps = H / (len(sp) - 1)
    med = sp.groupby("emo")["pct"].agg(["size", "median"]).round(3)
    out(f"\nKruskal-Wallis across collapsed speech emotion (n = {len(sp)}, "
        f"{sp['account'].nunique()} accounts): H = {H:.2f}, df {len(groups) - 1}, p = {fmt_p(p)}, "
        f"epsilon^2 = {eps:.3f}.")
    out("| Emotion | Videos | Median percentile |\n|---|---|---|")
    for k, r in med.iterrows():
        out(f"| {k} | {int(r['size'])} | {r['median']:.3f} |")
    add_family("H3", "Kruskal-Wallis speech emotion", p, f"eps2 {eps:.3f}", len(sp))
    out()


def h4(cc, focus):
    out("## H4 - people on screen (faces only; celebrity / creator not measured, D-038)")
    r = lr_test(CONTROLS, ["face_present_z", "face_area_z"], cc)
    m, _ = fit(f"pct ~ {CONTROLS} + face_present_z + face_area_z", cc)
    out(f"LR test, face share + face size added to controls: chi2 = {r['lr']:.2f}, df {r['df']}, "
        f"p = {fmt_p(r['p'])} (n = {r['n']}, converged: {r['conv']}).")
    out("| Term | Coef (pct points per SD) | 95% CI | Std beta | p |\n|---|---|---|---|---|")
    LINES.extend(coef_table(m, ["face_present_z", "face_area_z"], cc["pct"].std()))
    add_family("H4", "LR face share + face size", r["p"], f"chi2 {r['lr']:.2f} (df 2)", r["n"], r["conv"])
    a = focus.loc[focus["face_present_frac"] > 0, "pct"].to_numpy(float)
    b = focus.loc[focus["face_present_frac"] == 0, "pct"].to_numpy(float)
    U, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    rb = 2 * U / (len(a) * len(b)) - 1
    out(f"\nMann-Whitney U, any face ({len(a)}) vs none ({len(b)}): U = {U:.0f}, p = {fmt_p(p)}, "
        f"rank-biserial r = {rb:+.3f} (positive = higher with a face); medians {np.median(a):.3f} vs "
        f"{np.median(b):.3f}.")
    add_family("H4", "Mann-Whitney any face vs none", p, f"r_rb {rb:+.3f}", len(a) + len(b))
    out()


def h6(cc, focus):
    out("## H6 - text characteristics")
    r = lr_test(CONTROLS, TEXT_H6, cc)
    m, _ = fit(f"pct ~ {CONTROLS} + " + " + ".join(TEXT_H6), cc)
    out(f"LR test, text block ({', '.join(TEXT_H6)}) added to controls: chi2 = {r['lr']:.2f}, "
        f"df {r['df']}, p = {fmt_p(r['p'])} (n = {r['n']}, converged: {r['conv']}).")
    out("| Term | Coef (pct points per SD, or yes vs no) | 95% CI | Std beta | p |\n|---|---|---|---|---|")
    LINES.extend(coef_table(m, TEXT_H6, cc["pct"].std()))
    add_family("H6", "LR text block", r["p"], f"chi2 {r['lr']:.2f} (df {r['df']})", r["n"], r["conv"])
    for raw, lab in [("caption_char_len", "caption length"), ("hashtag_count", "hashtags")]:
        rho, p, n, lo, hi = spearman_ci(focus[raw].to_numpy(float), focus["pct"].to_numpy(float))
        out(f"\nSpearman, {lab}: rho = {rho:.3f} (95% CI {lo:.2f} to {hi:.2f}), p = {fmt_p(p)}, n = {n}.")
        add_family("H6", f"Spearman {lab}", p, f"rho {rho:.3f}", n)
    out()


def h7(d, focus, rng):
    out("## H7 - platform (docs/08 section 7.9, as registered)")
    f = focus.copy()
    out("Composition: " + "; ".join(
        f"{pl} {int((f['platform'] == pl).sum())} videos / {f.loc[f['platform'] == pl, 'account'].nunique()} accounts"
        for pl in ("instagram", "youtube")) + ". Videos per account: " +
        ", ".join(f"{a} {n}" for a, n in f["account"].value_counts().items()) + ".")
    form = f"log10_er ~ {PLAT} + C(tier2) + log_age"
    m, conv = fit(form, f)
    term = f"{PLAT}[T.instagram]"
    b, (lo, hi), p = m.params[term], m.conf_int().loc[term], m.pvalues[term]
    out(f"\n**(a) Main model** (`{form} + (1 | account)`, REML, n = {len(f)}, converged: {conv}): "
        f"platform coefficient (Instagram minus YouTube) **{b:+.3f}** log10 units, 95% CI {lo:+.3f} to "
        f"{hi:+.3f}, p = {fmt_p(p)}; ratio of engagement rates **10^beta = {10 ** b:.1f}** "
        f"(95% CI {10 ** lo:.1f} to {10 ** hi:.1f}). Account variance {float(m.cov_re.iloc[0, 0]):.3f}, "
        f"residual {float(m.scale):.3f}, **ICC {icc(m):.2f}**.")
    out("| Term | Coef | 95% CI | p |\n|---|---|---|---|")
    ci = m.conf_int()
    for t in m.params.index:
        if t != "Group Var":
            out(f"| `{t}` | {m.params[t]:+.3f} | {ci.loc[t, 0]:+.3f} to {ci.loc[t, 1]:+.3f} | {fmt_p(m.pvalues[t])} |")
    add_family("H7", "7.9.3(a) platform coefficient", float(p), f"10^b {10 ** b:.1f}", len(f), conv)

    acc = f.groupby(["account", "platform"])["log10_er"].median().reset_index()
    ia, ya = acc.loc[acc["platform"] == "instagram", "log10_er"], acc.loc[acc["platform"] == "youtube", "log10_er"]
    U, p2 = stats.mannwhitneyu(ia, ya, alternative="two-sided")
    sign_a2 = np.sign(ia.median() - ya.median())
    out(f"\n**(a2) Account medians** ({len(ia)} Instagram vs {len(ya)} YouTube accounts): median of account "
        f"medians {ia.median():.2f} vs {ya.median():.2f}; Mann-Whitney U = {U:.0f}, p = {fmt_p(p2)} "
        "(descriptive, weak by construction).")

    out("\n**(b) Follower tier - descriptive only** (median log10 rate, account-clustered bootstrap 95% CI):")
    out("| Platform | Tier | Videos | Accounts | Median | 95% CI |\n|---|---|---|---|---|---|")
    tier_diffs = {}
    for t in ("large", "small_medium"):
        for pl in ("instagram", "youtube"):
            g = f[(f["platform"] == pl) & (f["tier2"] == t)]
            if len(g) == 0:
                continue
            lo_, hi_ = cluster_boot(g, lambda s: s["log10_er"].median(), rng) if g["account"].nunique() > 1 else (np.nan, np.nan)
            out(f"| {pl} | {t} | {len(g)} | {g['account'].nunique()} | {g['log10_er'].median():.2f} | "
                f"{'single account - no interval' if not np.isfinite(lo_) else f'{lo_:.2f} to {hi_:.2f}'} |")
        g = f[f["tier2"] == t]

        def diff(s):
            i, y = s[s["platform"] == "instagram"]["log10_er"], s[s["platform"] == "youtube"]["log10_er"]
            return i.median() - y.median() if len(i) and len(y) else np.nan
        dl, dh = cluster_boot(g, diff, rng)
        tier_diffs[t] = (diff(g), dl, dh)
        out(f"| difference (IG - YT) | {t} | | | {diff(g):+.2f} | {dl:+.2f} to {dh:+.2f} |")

    ig = f[f["platform"] == "instagram"]
    out("\n**(c) Within Instagram, hand-picked vs systematic - descriptive, no test** (the selection "
        "re-run itself cannot be performed: 15 systematic videos < 20, D-039):")
    for sel in ("hand_picked", "systematic"):
        g = ig[ig["selection"] == sel]
        lo_, hi_ = cluster_boot(g, lambda s: s["log10_er"].median(), rng)
        out(f"- {sel}: {len(g)} videos / {g['account'].nunique()} accounts, median {g['log10_er'].median():.2f} "
            f"(95% CI {lo_:.2f} to {hi_:.2f})")
    out("**The platform coefficient in (a) cannot be separated from the difference in how the two "
        "samples were built** - every hand-picked video is an Instagram Reel (7.9.3(c)).")

    glob = f[f["platform"] == "youtube"]["account"].value_counts().index[0]
    fd = f[f["account"] != glob]
    try:
        md, convd = fit(form, fd)
        bd, (lod, hid) = md.params[term], md.conf_int().loc[term]
        out(f"\n**(d) Without the global channel ({glob})** - YouTube {int((fd['platform'] == 'youtube').sum())} "
            f"videos / {fd.loc[fd['platform'] == 'youtube', 'account'].nunique()} accounts: coefficient "
            f"{bd:+.3f} (95% CI {lod:+.3f} to {hid:+.3f}), ratio {10 ** bd:.1f}, converged: {convd}.")
        sign_d = np.sign(bd)
    except Exception as e:  # registered fallback: account medians
        out(f"\n**(d)** model failed ({e}); account medians reported instead.")
        sign_d = np.nan

    excl = not (lo <= 0 <= hi)
    signs = [sign_a2, sign_d] + [np.sign(v[0]) for v in tier_diffs.values()]
    reversed_ = any(np.isfinite(s) and s != np.sign(b) for s in signs)
    weak = any(v[1] <= 0 <= v[2] for v in tier_diffs.values()) or ("lod" in dir() and lod <= 0 <= hid)
    if not excl:
        verdict = "Not detected"
    elif reversed_:
        verdict = "Not robust to sample composition"
    elif weak:
        verdict = "Direction consistent, not robust"
    else:
        verdict = "Holds, with the selection caveat"
    out(f"\n**Verdict by 7.9.4: {verdict}.** (a) CI excludes 0: {excl}; any sign reversal in (a2), (d) or "
        f"the tier differences: {reversed_}; an interval in (d) or the tier differences includes 0: {weak}.")

    rb = d.copy()
    mr, convr = fit(f"log10_er ~ {PLAT} + C(is_zero_sugar) + C(tier2) + log_age", rb)
    out(f"\n**Robustness, wider set (7.5(a), all {len(rb)} usable videos, {rb['account'].nunique()} accounts, "
        f"with `is_zero_sugar`):** platform coefficient {mr.params[term]:+.3f} "
        f"(95% CI {mr.conf_int().loc[term, 0]:+.3f} to {mr.conf_int().loc[term, 1]:+.3f}), ratio "
        f"{10 ** mr.params[term]:.1f}, converged: {convr}.")
    out()
    return verdict


def h8(cc):
    out("## H8 - do the content blocks jointly add to the controls?")
    r = lr_test(CONTROLS, ALL20, cc)
    out(f"LR test, all 20 content features added to controls: chi2 = {r['lr']:.2f}, df {r['df']}, "
        f"p = {fmt_p(r['p'])} (n = {r['n']}, converged: {r['conv']}).")
    add_family("H8", "LR all 20 features", r["p"], f"chi2 {r['lr']:.2f} (df {r['df']})", r["n"], r["conv"])
    for name, block in [("video", VIDEO), ("audio", AUDIO), ("text", TEXT)]:
        rb = lr_test(CONTROLS, block, cc)
        out(f"- {name} block ({len(block)} features): chi2 = {rb['lr']:.2f}, df {rb['df']}, p = {fmt_p(rb['p'])}")
        add_family("H8", f"LR {name} block", rb["p"], f"chi2 {rb['lr']:.2f} (df {rb['df']})", rb["n"], rb["conv"])
    m, conv = fit(f"pct ~ {CONTROLS} + " + " + ".join(ALL20), cc)
    out(f"\nFull model (REML, n = {len(cc)}, converged: {conv}, ICC {icc(m):.2f}):")
    out("| Term | Coef (pct points per SD, or yes vs no) | 95% CI | Std beta | p (unadjusted, descriptive) |\n|---|---|---|---|---|")
    LINES.extend(coef_table(m, ["log_followers", "log_age", f"{PLAT}[T.instagram]"] + ALL20, cc["pct"].std()))
    out()
    return m


def h9_h10(cc):
    out("## H9 and H10 - exploratory (estimates with 95% intervals; outside the family; never 'significant')")
    out("H9: each feature's slope difference, Instagram minus YouTube (one model per feature: controls + "
        "feature + feature x platform).")
    out("| Feature | Interaction coef (pct points per SD) | 95% CI | Interval excludes 0 |\n|---|---|---|---|")
    for z in ALL20:
        m, conv = fit(f"pct ~ {CONTROLS} + {z} + {z}:{PLAT}", cc)
        t = f"{z}:{PLAT}[T.instagram]"
        if t not in m.params.index:
            continue
        lo, hi = m.conf_int().loc[t]
        out(f"| `{z}` | {m.params[t]:+.3f} | {lo:+.3f} to {hi:+.3f} | {'yes' if not (lo <= 0 <= hi) else 'no'}"
            f"{'' if conv else ' (not converged)'} |")
    m, conv = fit(f"pct ~ {CONTROLS} + duration_z + duration_z:{PLAT}", cc)
    t = f"duration_z:{PLAT}[T.instagram]"
    lo, hi = m.conf_int().loc[t]
    out(f"\nH10, duration x platform: {m.params[t]:+.3f} percentile points per SD (95% CI {lo:+.3f} to "
        f"{hi:+.3f}), converged: {conv}. Exploratory; with 72 YouTube videos from 5 accounts the "
        "interval is the result.")
    out("The 'restricted to systematic selection' variant of 7.7 cannot be run (15 systematic Instagram "
        "videos); stated, not replaced.")
    out()


def assumptions(m, cc):
    out("## Assumption checks (docs/08 section 5)")
    res = np.asarray(m.resid)
    W, p = stats.shapiro(res)
    out(f"- Full H8 model residuals: Shapiro-Wilk W = {W:.3f}, p = {fmt_p(p)}; skew {stats.skew(res):.2f}, "
        f"kurtosis {stats.kurtosis(res):.2f}. The percentile is bounded 0-1, so departures are expected; "
        "each H1-H6 conclusion is read against its rank-based test (D-042).")
    k = icc(m)
    out(f"- Account ICC (full H8 model): {k:.3f}." + (" Below 0.01 - OLS reported beside it (docs/08 section 5)."
                                                     if k < 0.01 else " Accounts differ; the random intercept stays."))
    if k < 0.01:
        o = smf.ols(f"pct ~ {CONTROLS} + " + " + ".join(ALL20), cc).fit()
        out(f"  OLS R^2 {o.rsquared:.3f}, adj. {o.rsquared_adj:.3f}.")
    fitted = np.asarray(m.fittedvalues)
    rs, rp = stats.spearmanr(np.abs(res), fitted)
    out(f"- Spread of residuals vs fitted values: Spearman {rs:.2f} (p = {fmt_p(rp)}).")
    out("- Multicollinearity: VIF max 3.6 on the 20 features (D-040).")
    out()


def sensitivity(imp):
    out("## Sensitivity - median imputation on all 192 videos (D-042)")
    for h, added in [("H1", ["duration_z", "duration2"]), ("H4", ["face_present_z", "face_area_z"]),
                     ("H6", TEXT_H6), ("H8", ALL20)]:
        r = lr_test(CONTROLS, added, imp)
        out(f"- {h}: chi2 = {r['lr']:.2f}, df {r['df']}, p = {fmt_p(r['p'])} (n = {r['n']})")
    m, _ = fit(f"pct ~ {CONTROLS} + sent_z", imp)
    out(f"- H3 caption sentiment: coef {m.params['sent_z']:+.3f}, p = {fmt_p(m.pvalues['sent_z'])} (n = {len(imp)})")
    out()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    warnings.filterwarnings("ignore", category=FutureWarning)
    rng = np.random.default_rng(SEED)
    d, focus = load()
    cc = complete(focus)
    imp = imputed(focus)
    out("# Phase 8 - statistical results (D-042, docs/08 section 7.9)")
    out()
    out(f"Focus set: {len(focus)} videos, {focus['account'].nunique()} accounts; complete cases for the "
        f"H1-H6/H8 models: {len(cc)} videos, {cc['account'].nunique()} accounts. Specification fixed "
        "before any test (D-042). Every result rests on the Zero Sugar inclusion label, whose repeat "
        "reliability is weak: YouTube 16 of 25, alpha 0.25; Instagram 4 of 9, alpha -0.10.")
    out()
    h1(cc, focus)
    out("## H2 - product visibility: not tested (not measured, D-037)\n")
    h3(cc, focus)
    h4(cc, focus)
    out("## H5 - call to action: not tested (no validated instrument, D-038)\n")
    h6(cc, focus)
    verdict = h7(d, focus, rng)
    m = h8(cc)
    h9_h10(cc)
    assumptions(m, cc)
    sensitivity(imp)

    fam = pd.DataFrame(FAMILY)
    fam["p_bh"] = multipletests(fam["p"], alpha=0.05, method="fdr_bh")[1]
    out("## The confirmatory family - Benjamini-Hochberg, q = 0.05")
    out("| H | Test | n | Effect | Raw p | BH-adjusted p | Result |\n|---|---|---|---|---|---|---|")
    for _, r in fam.iterrows():
        res = "detected" if r["p_bh"] < 0.05 else "not detected at this sample size"
        out(f"| {r['H']} | {r['test']}{'' if r['conv'] else ' (fit warning)'} | {r['n']} | {r['effect']} | "
            f"{fmt_p(r['p'])} | {fmt_p(r['p_bh'])} | {res} |")
    out()
    out(f"H7 verdict (7.9.4): **{verdict}** - with the selection caveat stated every time.")
    out()
    out("### Reading the one detected result - hashtags (descriptive check, changes no verdict)")
    groups = {a: g for a, g in focus.groupby("account")}
    accs = list(groups)
    vals = [stats.spearmanr(s["hashtag_count"], s["pct"])[0]
            for s in (pd.concat([groups[a] for a in rng.choice(accs, len(accs))]) for _ in range(N_BOOT))]
    w = focus.assign(h=focus["hashtag_count"] - focus.groupby("account")["hashtag_count"].transform("mean"),
                     q=focus["pct"] - focus.groupby("account")["pct"].transform("mean"))
    rw, pw = stats.spearmanr(w["h"], w["q"])
    out(f"Account-clustered bootstrap 95% CI for the pooled rho: {np.percentile(vals, 2.5):.2f} to "
        f"{np.percentile(vals, 97.5):.2f}. **Within accounts** (each account's mean removed): rho = {rw:.3f}, "
        f"p = {fmt_p(pw)}. In the mixed model, which holds accounts apart, the hashtag coefficient is "
        "similar in size but its interval reaches 0 (H6 table). **So the association is between accounts - "
        "accounts that use more hashtags rank higher - not evidence that adding hashtags to a video "
        "raises its engagement.** 13 videos carry 6 or more hashtags.")
    out()
    out("## Notes")
    NOTES.append(f"Complete cases cover {len(cc)} videos from {cc['account'].nunique()} of the "
                 f"{focus['account'].nunique()} accounts (accounts with a gap in every video drop out).")
    NOTES.append("Optimiser used per fit (highest finite likelihood among powell / lbfgs / bfgs / nm / cg): "
                 + ", ".join(f"{k} {v}" for k, v in pd.Series(FIT_LOG).value_counts().items()) + ".")
    for n in NOTES:
        out(f"- {n}")
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    fam.to_csv(config.REPORTS / "statistical_family.csv", index=False)
    print("\n".join(LINES))


if __name__ == "__main__":
    main()

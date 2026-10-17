"""P21 - the last proposal items, a declared addition exactly as fixed in D-063.

    Part A  background music behind talking: a new measure from the 5.8 records (nothing re-measured); two tests
            in their own Benjamini-Hochberg family, each also without the 15 AI-character Shorts
    Part B  EDA 6 completed: the proposal's seven kinds of emotional content side by side (description only)
    Part C  the proposal's EDA 8 table, Instagram against YouTube, with a Spearman within each platform
            (description only)

Same mixed model as D-042 (account random intercept, five optimisers via `fit()`), complete cases per test. The
D-042, D-050 and D-056 families are not re-opened.

Usage:
    python -m src.stats.hypotheses_p21
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.focus_codes import with_focus  # noqa: E402
from src.features import common  # noqa: E402
from src.stats.hypotheses import CONTROLS, fmt_p, load  # noqa: E402
from src.stats.hypotheses_p20 import one, within_account  # noqa: E402

OUT = config.REPORTS / "statistical_results_p21.md"
FAMILY_CSV = config.REPORTS / "statistical_family_p21.csv"
STEP = 0.1          # seconds of talk per music decision (D-063)
HALF = 0.5          # background music = music behind at least half of the talking (D-063, description only)
THIN = 10           # cells under 10 videos are marked thin, not merged (D-063)
LINES: list[str] = []


def out(s: str = "") -> None:
    LINES.append(s)


# ------------------------------------------------------------------------------------------ the new measure
def talk_music_frac(ev: dict) -> float | None:
    """Share of the talking time with music behind it (D-063). Each 0.1 s of talk (5.8's transcript segments marked
    "talk") takes the music decision of the 4 s window whose centre is nearest - "Music" at or above 5.8's own
    threshold. None when the video has no talk: not applicable, never 0."""
    wins = ev.get("windows") or []
    talk = [(s["start"], s["end"]) for s in (ev.get("segments") or []) if s.get("label") == "talk"]
    if not talk or not wins:
        return None
    centres = np.array([(w["start"] + w["end"]) / 2 for w in wins])
    music = np.array([w["music"] for w in wins]) >= ev["params"]["threshold"]
    hit = total = 0
    for a, b in talk:
        t = np.arange(a, b, STEP) + STEP / 2
        t = t[t < b]
        if len(t):
            near = np.abs(t[:, None] - centres[None, :]).argmin(1)
            hit += int(music[near].sum())
            total += len(t)
    return hit / total if total else None


# ------------------------------------------------------------------------------------------ data
def data() -> pd.DataFrame:
    _, focus = load()
    d = with_focus(focus)
    recs = {(p, m): common.read_cache(p, m) for p, m in zip(d["platform"], d["media_id"])}
    keys = list(zip(d["platform"], d["media_id"]))
    d["talk_music_frac"] = [talk_music_frac(recs[k].get("audio_events") or {}) for k in keys]
    d["talk_music_frac"] = pd.to_numeric(d["talk_music_frac"])
    d["background_music"] = np.where(d["talk_music_frac"].isna(), np.nan, (d["talk_music_frac"] >= HALF).astype(float))

    def label(k: tuple, field: str) -> str | None:
        return ((recs[k].get("sentiment") or {}).get(field) or {}).get("label")

    d["sent_caption_label"] = [label(k, "sent_caption") for k in keys]
    d["sent_speech_label"] = [label(k, "sent_speech_en") for k in keys]
    d["emotion_speech"] = d["emotion_label"]
    d["rate_follower_pct"] = 100 * d["engagement_rate_follower"].astype(float)
    d["rate_view_pct"] = 100 * d["engagement_rate_view"].astype(float)
    d["caption_chars"] = pd.to_numeric(d["caption_char_len"])
    d["collab01"] = d["creator_collab"].map({True: 1.0, False: 0.0})
    return d


def med(s: pd.Series) -> str:
    s = s.dropna()
    return f"{s.median():.3f}" if len(s) else "-"


def group_row(kind: str, measure: str, group: str, mask: pd.Series, base: pd.Series, d: pd.DataFrame) -> str:
    """One descriptive row: the group against the rest of the videos that have this measure."""
    g, rest = d[mask & base], d[~mask & base]
    thin = " (thin)" if len(g) < THIN else ""
    no_ai = g[~g["ai_characters"]]
    return (f"| {kind} | {measure} | {group}{thin} | {len(g)} | {g['account'].nunique()} | "
            f"{int((g['platform'] == 'instagram').sum())} / {int((g['platform'] == 'youtube').sum())} | "
            f"{med(g['pct'])} | {med(rest['pct'])} ({len(rest)}) | {med(no_ai['pct'])} ({len(no_ai)}) |")


# ------------------------------------------------------------------------------------------ Part A
def part_a(d: pd.DataFrame) -> pd.DataFrame:
    has = d["talk_music_frac"].notna()
    x = d.loc[has, "talk_music_frac"]
    out("## Part A - background music behind talking (new measure, D-063)")
    out()
    out(f"Measured from the 5.8 records, nothing re-measured: **{int(has.sum())} of {len(d)} videos have talk** "
        f"(Instagram {int((has & (d['platform'] == 'instagram')).sum())}, YouTube "
        f"{int((has & (d['platform'] == 'youtube')).sum())}); the rest have no speech, silent audio, unintelligible "
        f"or only sung speech, and are missing. Share of talking time with music behind it: median {x.median():.2f} "
        f"(Instagram {d.loc[has & (d['platform'] == 'instagram'), 'talk_music_frac'].median():.2f}, YouTube "
        f"{d.loc[has & (d['platform'] == 'youtube'), 'talk_music_frac'].median():.2f}); exactly 0 for "
        f"{int((x == 0).sum())}, exactly 1 for {int((x == 1).sum())}; music behind at least half of the talking: "
        f"{int((x >= HALF).sum())} yes / {int((x < HALF).sum())} no. (D-063 recorded 106 / 13 / 22 / 75 from the "
        "counts before any test.)")
    out()
    out("### Description")
    out("| Kind | Measure | Group | Videos | Accounts | Instagram / YouTube | Median percentile | Rest: median (n) | Group without AI-character Shorts: median (n) |")
    out("|---|---|---|---|---|---|---|---|---|")
    base = d["background_music"].notna()
    out(group_row("background music", "music behind at least half of the talking", "yes",
                  d["background_music"] == 1, base, d))
    out(group_row("background music", "music behind at least half of the talking", "no",
                  d["background_music"] == 0, base, d))
    out()
    fam = pd.DataFrame(one(1, "pct", CONTROLS, "talk_music_frac", "continuous",
                           "background music (share of talking time with music behind it)", d))
    fam["p_bh"] = multipletests(fam["p"], method="fdr_bh")[1]
    fam["verdict"] = np.where(fam["p_bh"] < 0.05, "detected", "not detected at this sample size")
    sens = pd.DataFrame(one(1, "pct", CONTROLS, "talk_music_frac", "continuous", "background music",
                            d[~d["ai_characters"]]))
    out("### The P21 family (two tests, its own Benjamini-Hochberg family, q = 0.05)")
    out("| # | Outcome | Measure | n, accounts | Test | Effect (95% CI) | Raw p | BH p | Verdict | Without AI-character Shorts: effect, raw p | Min. detectable |")
    out("|---|---|---|---|---|---|---|---|---|---|---|")
    for (_, r), (_, r2) in zip(fam.iterrows(), sens.iterrows()):
        out(f"| {r.test_no} | {r.outcome} | {r.measure} | {r.n}, {r.accounts} | {r.test} | {r.effect} | {fmt_p(r.p)} | "
            f"{fmt_p(r.p_bh)} | **{r.verdict}** | {r2.effect.split(' (')[0]}, {fmt_p(r2.p)} (n {r2.n}) | {r.mde} |")
    out()
    out("Fits converged: " + ", ".join(f"#{r.test_no} {r.conv}" for r in fam.itertuples()) + ".")
    if (fam["verdict"] == "detected").any():
        r, p, n = within_account(d, "pct", "talk_music_frac")
        out(f"Within-account check (D-043 style; describes, changes no verdict): Spearman rho {r:+.3f} "
            f"(p {fmt_p(p)}, n {n}).")
    out()
    out("Stated with it: the music score is AudioSet's generic \"Music\" (genre is not measurable, D-033); talk comes "
        "from the speech-to-text segments, so videos with unclear speech carry run-to-run noise (D-062).")
    out()
    return fam


# ------------------------------------------------------------------------------------------ Part B
def part_b(d: pd.DataFrame) -> None:
    out("## Part B - EDA 6 completed: the proposal's seven kinds of emotional content (description only, no test)")
    out()
    out("In the proposal's order. Sentiment uses the sentiment model's own label (5.9; no threshold chosen here); "
        "surprise and happiness are the speech emotion labels \"surprise\" and \"joy\" (English translation of the "
        "speech, 5.9); excitement and humour are the researcher's hand codes (D-049; humour repeat alpha 0.69, "
        "excitement not repeat-checked). \"Rest\" = the other videos that have the same measure. Percentile = "
        f"engagement ranked within platform and follower tier. Cells under {THIN} videos are marked thin.")
    out()
    out("| Kind (proposal) | Measure | Group | Videos | Accounts | Instagram / YouTube | Median percentile | Rest: median (n) | Group without AI-character Shorts: median (n) |")
    out("|---|---|---|---|---|---|---|---|---|")
    cap, spk = d["sent_caption_label"].notna(), d["sent_speech_label"].notna()
    for kind, lab in (("Positive", "positive"), ("Neutral", "neutral"), ("Negative", "negative")):
        out(group_row(kind, "caption sentiment", lab, d["sent_caption_label"] == lab, cap, d))
    for kind, lab in (("Positive", "positive"), ("Neutral", "neutral"), ("Negative", "negative")):
        out(group_row(kind, "speech sentiment", lab, d["sent_speech_label"] == lab, spk, d))
    out(group_row("Excitement", "hand-coded: meant to be exciting", "yes", d["hc_excitement"] == 1,
                  d["hc_excitement"].notna(), d))
    out(group_row("Humour", "hand-coded: meant to be funny", "yes", d["hc_humour"] == 1, d["hc_humour"].notna(), d))
    emo = d["emotion_speech"].notna()
    out(group_row("Surprise", "speech emotion", "surprise", d["emotion_speech"] == "surprise", emo, d))
    out(group_row("Happiness", "speech emotion", "joy", d["emotion_speech"] == "joy", emo, d))
    out()
    out("Description only: the registered test of emotional content is H3 (D-043, not detected); no verdict is drawn "
        "from this table.")
    out()


# ------------------------------------------------------------------------------------------ Part C
def spear(s: pd.DataFrame, col: str) -> tuple[str, float]:
    s = s[s[col].notna() & s["pct"].notna()]
    if len(s) < 3 or s[col].nunique() < 2:
        return "-", np.nan
    r = stats.spearmanr(s[col].astype(float), s["pct"])[0]
    return f"{r:+.2f} ({len(s)})", r


def part_c(d: pd.DataFrame) -> None:
    ig, yt = d[d["platform"] == "instagram"], d[d["platform"] == "youtube"]
    out("## Part C - the proposal's EDA 8 table: YouTube against Instagram (description only)")
    out()
    out(f"**Composition first** (docs/07 section 1b): Instagram {len(ig)} videos from {ig['account'].nunique()} accounts, "
        f"{int((ig['selection'] == 'hand_picked').sum())} of them hand-picked; YouTube {len(yt)} from "
        f"{yt['account'].nunique()} channels, {int((yt['account'] == yt['account'].mode()[0]).sum())} from one. "
        "Platform, selection route and account size cannot be separated (docs/08 section 7.9.3(c)); Zero Sugar label "
        "repeat reliability YouTube alpha 0.25, Instagram -0.10. The last two columns answer the proposal's question "
        "\"does the same marketing strategy work equally well on both platforms?\" only as description: the Spearman "
        "of the measure with the engagement percentile **within** each platform (n in brackets) - no test.")
    out()
    out("| Feature (proposal) | Measure | Instagram | YouTube | Spearman with percentile, Instagram | Spearman, YouTube | Same direction on both? |")
    out("|---|---|---|---|---|---|---|")

    def share(s: pd.DataFrame, col: str, val=1.0) -> str:
        v = s[col].dropna()
        return f"{100 * (v == val).mean():.0f}% ({len(v)})" if len(v) else "-"

    def row(feature: str, measure: str, a: str, b: str, col: str | None) -> None:
        if col is None:
            out(f"| {feature} | {measure} | {a} | {b} | - | - | - |")
            return
        (ti, ri), (ty, ry) = spear(ig, col), spear(yt, col)
        same = "-" if np.isnan(ri) or np.isnan(ry) else ("same" if np.sign(ri) == np.sign(ry) else "opposite")
        out(f"| {feature} | {measure} | {a} | {b} | {ti} | {ty} | {same} |")

    row("Duration", "median seconds", f"{ig['duration_sec'].median():.1f}", f"{yt['duration_sec'].median():.1f}",
        "duration_sec")
    row("Engagement", "median (likes + comments) per follower", f"{ig['rate_follower_pct'].median():.3f}%",
        f"{yt['rate_follower_pct'].median():.4f}%", None)
    row("Engagement", "median (likes + comments) per view", "not published (docs/06)",
        f"{yt['rate_view_pct'].median():.2f}%", None)
    row("Caption length", "median characters", f"{ig['caption_chars'].median():.1f}",
        f"{yt['caption_chars'].median():.1f}", "caption_chars")
    row("Product visibility", "can or bottle prominent (hand-coded)", share(ig, "hc_product_prominent"),
        share(yt, "hc_product_prominent"), "hc_product_prominent")
    row("Creator involvement", "creator or celebrity (hand-coded, of coded)", share(ig, "hc_creator_or_celebrity"),
        share(yt, "hc_creator_or_celebrity"), "hc_creator_or_celebrity")
    row("Creator involvement", "collaboration post (platform metadata)", share(ig, "collab01"),
        "0% (brand channels only)", None)
    d["_pos"] = np.where(d["sent_caption_label"].isna(), np.nan, (d["sent_caption_label"] == "positive").astype(float))
    d["_joy"] = np.where(d["emotion_speech"].isna(), np.nan, (d["emotion_speech"] == "joy").astype(float))
    ig, yt = d[d["platform"] == "instagram"], d[d["platform"] == "youtube"]
    row("Emotional content", "caption sentiment positive", share(ig, "_pos"), share(yt, "_pos"), "_pos")
    row("Emotional content", "joy in speech (of videos with speech emotion)", share(ig, "_joy"), share(yt, "_joy"), "_joy")
    row("Emotional content", "humour (hand-coded)", share(ig, "hc_humour"), share(yt, "hc_humour"), "hc_humour")
    row("Emotional content", "excitement (hand-coded)", share(ig, "hc_excitement"), share(yt, "hc_excitement"),
        "hc_excitement")
    d.drop(columns=["_pos", "_joy"], inplace=True)
    out()
    out("Engagement is not compared through the percentile here: it is ranked within each platform, so its median is "
        "about the middle on both by construction (docs/06). The per-follower rate differs about as EDA 8 reported; the "
        "inferential answer is H7 (D-043, not detected). The within-platform Spearmans are descriptions of these 192 "
        "videos - the profile (D-052) holds the checked version for talking, faces, call to action and hashtags.")
    out()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    warnings.filterwarnings("ignore")
    d = data()
    out("# P21 - the last proposal items: background music, EDA 6 completed, the proposal's platform table (D-063)")
    out()
    out(f"Focus set {len(d)} videos, {d['account'].nunique()} accounts. A declared addition: the registered results "
        "(D-043, D-045, D-048) and the additions of D-051 and D-057 are unchanged. Engagement = percentile within "
        "platform x follower tier. Zero Sugar label: YouTube alpha 0.25, Instagram -0.10. Hand codes: one coder, "
        "110 minutes for 100 minutes of video. Coverage of every proposal item: docs/16-proposal-coverage.md.")
    out()
    fam = part_a(d)
    part_b(d)
    part_c(d)
    out("Wording (D-063): 'associated with', never 'causes'; a test not detected is 'not detected at this sample size' "
        "with its minimum detectable effect (a lower bound: account clustering makes it larger). Parts B and C are "
        "description. Nothing here changes the 20 model features, the models or the tool.")
    fam.to_csv(FAMILY_CSV, index=False)
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print("\n".join(LINES))


if __name__ == "__main__":
    main()

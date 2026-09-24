"""Select the analysis corpus from screened collections.

Collection is exhaustive; the corpus is a subset of fixed size. How that subset is chosen
is a methodological decision, not a detail, because Zero Sugar content is scarce (D-013:
2.2% on Instagram, 4.0% on YouTube Shorts). Drawing 150 rows at random from ~1,000 Shorts
would leave roughly six Zero Sugar items — too few to say anything about the variant the
project is named after.

Two strategies, and the choice has consequences that must reach the methods chapter:

`random`
    A simple random sample of brand rows. Variant proportions match the population, so
    engagement figures generalise to "Coca-Cola short-form video as actually posted".
    Zero Sugar ends up too rare to model as a factor.

`stratified` (default)
    Keep every Zero Sugar row, then fill the remainder at random from the rest. Zero Sugar
    becomes analysable as a factor. **The sample is then deliberately unrepresentative:**
    Zero Sugar is over-represented relative to how often Coca-Cola actually posts it, so
    corpus-level averages are no longer population estimates, and any such figure needs
    reweighting or an explicit caveat.

Neither is "correct" — they answer different questions. The default is stratified because
the project's stated subject is Zero Sugar; the cost is recorded in `corpus_note` on every
row so the choice cannot be lost.

Usage:
    python -m src.screen.build_corpus --platform youtube --target 150
    python -m src.screen.build_corpus --platform youtube --strategy random
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

SEED = 20260911  # fixed so the corpus is reproducible from the raw collection


def build(df: pd.DataFrame, target: int, strategy: str = "stratified",
          seed: int = SEED) -> pd.DataFrame:
    """Return `df` with `in_corpus`, `corpus_reason` and `corpus_note` columns added."""
    out = df.copy()
    out["in_corpus"] = False
    out["corpus_reason"] = "not_selected"

    # off_brand rows are not Coca-Cola content and are never eligible.
    eligible = out[out["variant"] != "off_brand"]
    out.loc[out["variant"] == "off_brand", "corpus_reason"] = "excluded_off_brand"

    if eligible.empty:
        out["corpus_note"] = "no eligible rows"
        return out

    if strategy == "random":
        take = eligible.sample(n=min(target, len(eligible)), random_state=seed).index
        out.loc[take, "in_corpus"] = True
        out.loc[take, "corpus_reason"] = "random_sample"
        note = ("simple random sample of brand rows; variant proportions match the "
                "population, Zero Sugar left at its natural rate")
    else:
        zero = eligible[eligible["is_zero_sugar"]]
        rest = eligible[~eligible["is_zero_sugar"]]

        out.loc[zero.index, "in_corpus"] = True
        out.loc[zero.index, "corpus_reason"] = "zero_sugar_census"

        remaining = max(target - len(zero), 0)
        if remaining and not rest.empty:
            fill = rest.sample(n=min(remaining, len(rest)), random_state=seed).index
            out.loc[fill, "in_corpus"] = True
            out.loc[fill, "corpus_reason"] = "stratified_fill"

        pop_rate = len(zero) / len(eligible)
        got = int(out["in_corpus"].sum())
        corpus_rate = len(zero) / got if got else 0
        note = (f"stratified: every Zero Sugar row kept ({len(zero)}), remainder filled at "
                f"random. Zero Sugar is {corpus_rate:.1%} of the corpus vs {pop_rate:.1%} "
                f"of the population - OVER-REPRESENTED BY DESIGN, so corpus averages are "
                f"not population estimates without reweighting")

    out["corpus_note"] = note
    return out


def replace_unusable(platform: str = "youtube", seed: int = SEED) -> int:
    """Swap corpus videos that turned out unusable at download for new random fill rows.

    Unusable means the video is gone ("Video unavailable") or ffprobe shows it is not
    vertical (height <= width - the rule applied to Instagram too). Only the affected rows
    change; the rest of the corpus stays exactly as drawn, so no finished download is wasted.
    Replacements come from unselected brand rows that are not Zero Sugar and were read >=7
    days after posting (D-019). Returns the number of rows replaced; re-run after the
    replacements are downloaded, in case one of them is unusable too.
    """
    path = config.PROCESSED / f"{platform}_corpus.parquet"
    manifest = config.MEDIA / "download_manifest.csv"
    df = pd.read_parquet(path)
    id_col = "video_id" if platform == "youtube" else "shortcode"
    m = pd.read_csv(manifest, dtype={"media_id": str})
    m = m[m["platform"] == platform].set_index("media_id")

    for col in ("replaces", "exclusion_detail"):
        if col not in df.columns:
            df[col] = None

    bad = []
    for i, r in df[df["in_corpus"]].iterrows():
        vid = r[id_col]
        if vid not in m.index:
            continue
        rec = m.loc[vid]
        if rec["status"] == "failed" and "unavailable" in str(rec["error"]).lower():
            bad.append((i, "excluded_video_unavailable", "Video unavailable at download"))
        elif rec["status"] == "ok" and pd.notna(rec["width"]) and rec["height"] <= rec["width"]:
            bad.append((i, "excluded_not_vertical_after_download",
                        f"{int(rec['width'])}x{int(rec['height'])} by ffprobe"))
    if not bad:
        print(f"{platform}: nothing to replace")
        return 0

    age = (pd.to_datetime(df["collected_at"], utc=True, format="mixed")
           - pd.to_datetime(df.get("published_at", df.get("timestamp")), utc=True, format="mixed")
           ).dt.total_seconds() / 86400
    tried = df["corpus_reason"].astype(str).str.startswith(("excluded_", "replacement_fill"))
    pool = df[(~df["in_corpus"]) & (df["variant"] != "off_brand") & (~df["is_zero_sugar"])
              & (age >= 7) & ~tried]
    draw = pool.sample(n=min(len(bad), len(pool)), random_state=seed + int(tried.sum()))

    if not path.with_name(f"{platform}_corpus_before_replacement.parquet").exists():
        df.to_parquet(path.with_name(f"{platform}_corpus_before_replacement.parquet"), index=False)
    for (i, reason, detail), (j, _) in zip(bad, draw.iterrows()):
        df.loc[i, ["in_corpus", "corpus_reason", "exclusion_detail"]] = [False, reason, detail]
        df.loc[j, ["in_corpus", "corpus_reason", "replaces"]] = [True, "replacement_fill", df.at[i, id_col]]
        print(f"  {df.at[i, id_col]} ({reason}) -> {df.at[j, id_col]}")
    from src.screen.zero_sugar_labels import annotate  # D-029 provenance survives the rewrite
    df = annotate(df, platform)
    df.to_parquet(path, index=False)
    print(f"{platform}: replaced {len(draw)} | corpus now {int(df['in_corpus'].sum())} | "
          f"Zero Sugar {int((df['in_corpus'] & df['is_zero_sugar']).sum())}")
    return len(draw)


def main() -> None:
    if "--replace-unusable" in sys.argv:
        replace_unusable("youtube")
        return
    ap = argparse.ArgumentParser(description="Select the analysis corpus.")
    ap.add_argument("--platform", choices=["instagram", "youtube"], required=True)
    ap.add_argument("--target", type=int, default=150)
    ap.add_argument("--strategy", choices=["stratified", "random"], default="stratified")
    args = ap.parse_args()

    src = config.INTERIM / f"{args.platform}_screened.parquet"
    if not src.exists():
        raise SystemExit(f"{src} not found — run: python -m src.screen.zero_sugar --write")

    df = pd.read_parquet(src)
    if "variant" not in df.columns:
        raise SystemExit("screened file predates variant tagging — re-run the screener.")

    built = build(df, args.target, args.strategy)
    sel = built[built["in_corpus"]]

    print(f"\n{'=' * 62}")
    print(f"{args.platform.upper()}  strategy={args.strategy}  target={args.target}")
    print(f"  available (brand rows) : {int((built['variant'] != 'off_brand').sum())}")
    print(f"  selected               : {len(sel)}")
    if len(sel) < args.target:
        print(f"  ! SHORT OF TARGET by {args.target - len(sel)} — not enough eligible rows")
    print(f"\n  variant mix in corpus:")
    for v, c in sel["variant"].value_counts().items():
        print(f"    {v:<12}{c:>5}  {c / len(sel):6.1%}")
    print(f"\n  Zero Sugar in corpus   : {int(sel['is_zero_sugar'].sum())}")
    print(f"\n  {built['corpus_note'].iloc[0]}")

    out = config.PROCESSED / f"{args.platform}_corpus.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    from src.screen.zero_sugar_labels import annotate  # D-029 provenance survives a rebuild
    built = annotate(built, args.platform)
    built.to_parquet(out, index=False)
    print(f"\n  written -> {out}  (all rows kept; filter on in_corpus)")


if __name__ == "__main__":
    main()

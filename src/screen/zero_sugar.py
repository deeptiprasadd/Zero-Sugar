"""Zero Sugar screening — decide which collected videos actually feature the product.

The corpus target is Coca-Cola **Zero Sugar** specifically, but collection is by account,
and brand accounts post the whole portfolio. Something has to separate the two.

This module does the *text* half: caption, hashtags, title, description, alt text and
audio track name, across the corpus languages. It is cheap, runs offline, and needs no
video file.

**It is deliberately not the whole answer.** A Reel can show a black Zero Sugar can for
fifteen seconds and never name it in the caption, and text screening cannot see that.
So every row gets one of three verdicts, not a boolean:

    hit          an explicit Zero Sugar term is present            -> in the corpus
    unnamed      Coca-Cola is referenced, no variant named         -> needs a visual check
    off_brand    no Coca-Cola reference at all                     -> out

`unnamed` is the important one: it is not "no", it is "text cannot tell". Treating it as
"no" silently discards exactly the visually-branded content the study is about. The count
of `unnamed` rows *is* the size of the manual/visual screening job.

Usage:
    python -m src.screen.zero_sugar                      # screen both corpora
    python -m src.screen.zero_sugar --platform instagram
    python -m src.screen.zero_sugar --show-unnamed 20    # inspect the ambiguous ones
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

# --------------------------------------------------------------------- vocabularies
#
# Terms naming the Zero Sugar product. Curated per language rather than machine
# translated: a bare "zero" matches match scores, countdowns and "zero waste", and a bare
# Thai "ซีโร่" matches any transliterated "zero". Precision matters more than recall here
# because a false positive puts the wrong video in the corpus, where nothing downstream
# will catch it.
ZERO_TERMS: dict[str, list[str]] = {
    "en": ["zero sugar", "zero-sugar", "zerosugar", "coke zero", "cokezero",
           "coca-cola zero", "coca cola zero", "cocacola zero", "cokezerosugar",
           "no sugar", "sugar free", "sugar-free"],
    "es": ["coca-cola zero", "coca cola zero", "cocacola zero", "coca-cola sin azucar",
           "sin azucar", "sin azúcar", "cero azucar", "cero azúcar"],
    "pt": ["coca-cola zero", "coca cola zero", "coca zero", "zero acucar",
           "zero açúcar", "sem acucar", "sem açúcar"],
    "ar": ["كوكاكولا زيرو", "كوكا كولا زيرو", "زيرو شوجر", "بدون سكر", "خالي من السكر"],
    "th": ["โค้กซีโร่", "โค้ก ซีโร่", "ซีโร่ ชูการ์", "ไม่มีน้ำตาล", "สูตรไม่มีน้ำตาล",
           "น้ำตาล 0", "ปราศจากน้ำตาล"],
    "id": ["tanpa gula", "bebas gula", "coca-cola zero", "coke zero"],
    "hi": ["शुगर फ्री", "बिना चीनी", "zero sugar"],
}

# Any Coca-Cola reference at all. A row with none of these is not brand content and is
# out regardless of what the video shows.
BRAND_TERMS: list[str] = [
    "coca-cola", "coca cola", "cocacola", "coke", "#coke",
    "كوكاكولا", "كوكا كولا",          # ar
    "โค้ก", "โคคา-โคล่า",              # th
    "कोका-कोला", "कोक",                # hi
]

# Terms that mean a *different* variant. Their presence does not exclude a row on its own
# (a portfolio post can name several), but a row naming only these is not Zero Sugar.
OTHER_VARIANTS: list[str] = [
    "diet coke", "coca-cola light", "coke light", "coca-cola original taste",
    "cherry coke", "coca-cola cherry", "vanilla coke", "coca-cola vanilla",
]

# --------------------------------------------------------------------- variant tagging
#
# Under D-014 the corpus is the Coca-Cola brand family and the *variant* is a feature,
# not a filter. Zero Sugar reuses ZERO_TERMS so the two paths can never disagree.
VARIANT_TERMS: dict[str, list[str]] = {
    "zero_sugar": [t for terms in ZERO_TERMS.values() for t in terms],
    "diet_light": [
        "diet coke", "dietcoke", "coca-cola light", "coca cola light", "coke light",
        "كوكاكولا لايت", "โค้กไลท์", "coca-cola diet",
    ],
    "original": [
        "original taste", "coca-cola original", "coca cola original", "sabor original",
        "coca-cola classic", "coke classic", "clasica", "clásica", "cocacola original",
    ],
    "flavour": [
        "cherry coke", "coca-cola cherry", "vanilla coke", "coca-cola vanilla",
        "coca-cola lemon", "coca-cola orange", "coca-cola cereza", "coca-cola baunilha",
        "coca-cola spiced", "coca-cola move", "coca-cola starlight",
    ],
}


def classify_variant(blob: str) -> tuple[str, list[str]]:
    """Which Coca-Cola variant the text names.

    Returns (variant, all_named). Values:
        zero_sugar / diet_light / original / flavour   exactly one named
        multi                                          more than one named
        unnamed                                        brand present, variant not stated
        off_brand                                      no Coca-Cola reference at all

    `unnamed` is the honest majority verdict and must not be read as "original". Most
    brand posts simply show the product without naming the variant; a frame check on ten
    Reels (D-013) found them to be classic red, but ten is not evidence enough to relabel
    thousands of rows. Anything depending on the distinction needs the visual pass.
    """
    named = [v for v, terms in VARIANT_TERMS.items() if _found(blob, terms)]
    if len(named) > 1:
        return "multi", named
    if named:
        return named[0], named
    return ("unnamed", []) if _found(blob, BRAND_TERMS) else ("off_brand", [])


def _norm(text: object) -> str:
    """NFKC-fold and lowercase so Arabic/Thai forms and full-width variants compare."""
    return unicodedata.normalize("NFKC", str(text or "")).casefold()


def _found(blob: str, terms: list[str]) -> list[str]:
    return [t for t in terms if _norm(t) in blob]


def _blob_instagram(df: pd.DataFrame) -> pd.Series:
    """Every text surface a Reel offers, including hashtags parsed out of JSON."""
    def tags(val: object) -> str:
        try:
            return " ".join(json.loads(val) if val else [])
        except (json.JSONDecodeError, TypeError):
            return str(val or "")

    parts = [
        df.get("caption", pd.Series("", index=df.index)).fillna(""),
        df.get("hashtags", pd.Series("", index=df.index)).map(tags),
        df.get("mentions", pd.Series("", index=df.index)).map(tags),
        df.get("alt_text", pd.Series("", index=df.index)).fillna(""),
        df.get("audio_name", pd.Series("", index=df.index)).fillna(""),
    ]
    return sum((p.astype(str) + " " for p in parts), pd.Series("", index=df.index)).map(_norm)


def _blob_youtube(df: pd.DataFrame) -> pd.Series:
    parts = [
        df.get("title", pd.Series("", index=df.index)).fillna(""),
        df.get("description", pd.Series("", index=df.index)).fillna(""),
        df.get("tags", pd.Series("", index=df.index)).fillna(""),
        df.get("transcript", pd.Series("", index=df.index)).fillna(""),
    ]
    return sum((p.astype(str) + " " for p in parts), pd.Series("", index=df.index)).map(_norm)


def screen(df: pd.DataFrame, platform: str) -> pd.DataFrame:
    """Add zs_* screening columns. Does not filter — the caller decides what to keep."""
    if df.empty:
        return df
    out = df.copy()
    blob = _blob_instagram(out) if platform == "instagram" else _blob_youtube(out)

    all_zero = [t for terms in ZERO_TERMS.values() for t in terms]
    zero_hits = blob.map(lambda b: _found(b, all_zero))
    brand_hits = blob.map(lambda b: _found(b, BRAND_TERMS))
    other_hits = blob.map(lambda b: _found(b, OTHER_VARIANTS))

    langs = blob.map(lambda b: sorted({lang for lang, terms in ZERO_TERMS.items()
                                       if _found(b, terms)}))

    out["zs_terms"] = zero_hits.map(lambda x: json.dumps(x, ensure_ascii=False))
    out["zs_term_langs"] = langs.map(lambda x: ",".join(x))
    out["zs_brand_terms"] = brand_hits.map(lambda x: json.dumps(x, ensure_ascii=False))
    out["zs_other_variant"] = other_hits.map(lambda x: json.dumps(x, ensure_ascii=False))

    def verdict(z: list, b: list) -> str:
        if z:
            return "hit"
        if b:
            return "unnamed"   # brand present, variant not stated -> the video must decide
        return "off_brand"

    out["zs_verdict"] = [verdict(z, b) for z, b in zip(zero_hits, brand_hits)]
    # The visual-screening worklist. Not "no" — "text cannot tell".
    out["zs_needs_visual"] = out["zs_verdict"] == "unnamed"

    # Variant as a modelling feature (D-014), not a sampling filter.
    variants = blob.map(classify_variant)
    out["variant"] = [v for v, _ in variants]
    out["variant_named"] = [",".join(n) for _, n in variants]
    # True when Zero Sugar is named at all, including in a multi-variant post.
    # `variant_named` already lists every variant found, so a membership test over that
    # list covers both cases without relying on & / | precedence.
    out["is_zero_sugar"] = [
        "zero_sugar" in n.split(",") for n in out["variant_named"]
    ]
    return out


def report(df: pd.DataFrame, platform: str, label: str = "") -> dict:
    """Print the verdict breakdown and return it, so collection width can be planned."""
    n = len(df)
    counts = df["zs_verdict"].value_counts().to_dict()
    hit = counts.get("hit", 0)
    unnamed = counts.get("unnamed", 0)
    off = counts.get("off_brand", 0)

    print(f"\n{'=' * 62}")
    print(f"{platform.upper()}{'  ' + label if label else ''}   n = {n}")
    print(f"  hit       (explicit Zero Sugar text) : {hit:>4}  {hit / n:6.1%}")
    print(f"  unnamed   (brand, variant not named) : {unnamed:>4}  {unnamed / n:6.1%}   <- needs a visual check")
    print(f"  off_brand (no Coca-Cola reference)   : {off:>4}  {off / n:6.1%}")

    if hit:
        langs = [l for s in df.loc[df["zs_verdict"] == "hit", "zs_term_langs"] for l in s.split(",") if l]
        print(f"  languages triggering a hit           : {', '.join(sorted(set(langs)))}")

    if "variant" in df.columns:
        print(f"\n  variant tag (D-014 — a feature, not a filter):")
        for v, c in df["variant"].value_counts().items():
            note = "   <- text cannot tell; needs the visual pass" if v == "unnamed" else ""
            print(f"    {v:<12}{c:>5}  {c / n:6.1%}{note}")

    return {"n": n, "hit": hit, "unnamed": unnamed, "off_brand": off,
            "hit_rate": hit / n if n else 0.0}


def project(stats: dict, target: int, platform: str) -> None:
    """How wide the collection must go to reach `target` — on text evidence alone, and
    with an optimistic visual yield. Both bounds are printed because the truth sits
    between them and the gap is the argument for doing the visual pass."""
    rate = stats["hit_rate"]
    n = stats["n"]
    print(f"\n  to reach {target} on {platform}:")
    if rate > 0:
        need = int(round(target / rate))
        print(f"    text screening alone   : ~{need:,} videos to enumerate "
              f"(at the observed {rate:.1%})")
    else:
        print(f"    text screening alone   : UNREACHABLE — 0 of {n} matched")
    unnamed_rate = stats["unnamed"] / n if n else 0
    if unnamed_rate:
        # If a third of visually-branded posts turn out to be Zero Sugar, a deliberately
        # unverified placeholder, the effective rate becomes:
        eff = rate + unnamed_rate * 0.33
        if eff > 0:
            print(f"    + visual screening     : ~{int(round(target / eff)):,} videos, "
                  f"IF a third of the {stats['unnamed']} 'unnamed' rows show the product")
            print(f"      (0.33 is a placeholder, not a measurement — establish it by hand-checking a sample)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Zero Sugar text screening.")
    ap.add_argument("--platform", choices=["instagram", "youtube", "both"], default="both")
    ap.add_argument("--target", type=int, default=150, help="corpus target per platform")
    ap.add_argument("--show-unnamed", type=int, default=0,
                    help="print N ambiguous rows for eyeballing")
    ap.add_argument("--write", action="store_true",
                    help="write screened parquets back to data/interim/")
    args = ap.parse_args()

    jobs = []
    if args.platform in ("instagram", "both"):
        jobs.append(("instagram", config.RAW / "instagram_reels.parquet"))
    if args.platform in ("youtube", "both"):
        jobs.append(("youtube", config.RAW / "youtube_shorts.parquet"))

    for platform, path in jobs:
        if not path.exists():
            print(f"\n! {path.name} not found — collect first")
            continue
        df = pd.read_parquet(path)

        # On YouTube the corpus is Shorts only; screening the long-form uploads would
        # report a rate that does not apply to anything being collected.
        label = ""
        if platform == "youtube" and "is_short" in df.columns:
            df = df[df["is_short"] == True].copy()  # noqa: E712
            label = "(Shorts only)"

        if df.empty:
            print(f"\n! nothing to screen for {platform}")
            continue

        screened = screen(df, platform)
        stats = report(screened, platform, label)
        project(stats, args.target, platform)

        if args.show_unnamed:
            amb = screened[screened["zs_needs_visual"]]
            if not amb.empty:
                print(f"\n  --- {min(args.show_unnamed, len(amb))} 'unnamed' rows ---")
                text_col = "caption" if platform == "instagram" else "title"
                for _, r in amb.head(args.show_unnamed).iterrows():
                    txt = str(r.get(text_col) or "").replace("\n", " ")[:88]
                    print(f"    [{str(r.get('market'))[:9]:<10}] {txt}")

        if args.write:
            out = config.INTERIM / f"{platform}_screened.parquet"
            out.parent.mkdir(parents=True, exist_ok=True)
            screened.to_parquet(out, index=False)
            print(f"\n  written -> {out}")


if __name__ == "__main__":
    main()

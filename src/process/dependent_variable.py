"""Dependent variable: engagement rate, normalised percentile, binary labels (tasks 6.1-6.3).

Implements docs/06 exactly:

    engagement_rate_follower = (likes + comments) / followers      both platforms (primary)
    engagement_rate_view     = (likes + comments) / views          YouTube only (secondary)

then a percentile rank within `platform x account_size_tier x year`, collapsing thin cells in
the order docs/06 §3 prescribes (drop year, then merge size tiers, then platform only), and a
median split and a tertile split on that percentile.

Rules carried in from the decision log:
- **Hidden is not zero** (D-005): a hidden like count or disabled comments leaves the rate
  undefined. The row stays in the table with `dv_status` explaining why; it is never imputed.
- **7-day rule** (D-019): counts read less than 7 days after posting are held back
  (`pending_refresh`) until re-read.
- Followers are those of the account that posted (the creator, on a collaboration post) - the
  exposure base agreed in D-005.

Usage:
    python -m src.process.dependent_variable
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

OUT = config.PROCESSED / "dependent_variable.parquet"
MIN_CELL = 10
MIN_AGE_DAYS = 7
# One backup per decision that changed this table, copied once, before that decision's first write.
BACKUP_TAGS = ["before_D030_20260923"]


def _yt() -> pd.DataFrame:
    c = pd.read_parquet(config.PROCESSED / "youtube_corpus.parquet")
    c = c[c["in_corpus"]].copy()
    frame = pd.read_csv(config.ACCOUNTS_CSV, dtype=str).fillna("")
    region = dict(zip(frame["youtube_channel"], frame["region"]))
    return pd.DataFrame({
        "platform": "youtube", "media_id": c["video_id"], "account": c["channel_title"],
        "posted_by": c["channel_title"], "market": c["market"],
        "region": c["channel_id"].map(region).replace("", np.nan),
        "followers": pd.to_numeric(c["subscriber_count"], errors="coerce"),
        "likes": pd.to_numeric(c["like_count"], errors="coerce"),
        "comments": pd.to_numeric(c["comment_count"], errors="coerce"),
        "views": pd.to_numeric(c["view_count"], errors="coerce"),
        "likes_hidden": c["likes_hidden"].fillna(False).astype(bool) | c["like_count"].isna(),
        "comments_disabled": c["comments_disabled"].fillna(False).astype(bool) | c["comment_count"].isna(),
        "posted_at": pd.to_datetime(c["published_at"], utc=True, format="mixed"),
        "read_at": pd.to_datetime(c["collected_at"], utc=True, format="mixed"),
        "is_zero_sugar": c["is_zero_sugar"].astype(bool),
        # D-029: how the video entered the sample and how its Zero Sugar label was decided
        "is_zero_sugar_before_D029": c.get("is_zero_sugar_before_D029", c["is_zero_sugar"]).astype(bool),
        "zs_label_method": c.get("zs_label_method"),
        "zs_clip_screen": c.get("zs_clip_screen"),
        "selection": c.get("selection"),
        # D-030: analysis scope (Zero Sugar only). Non-focus rows stay in the table, flagged.
        "in_focus": c.get("in_focus", c["is_zero_sugar"]).astype(bool),
    })


def _ig() -> pd.DataFrame:
    c = pd.read_parquet(config.PROCESSED / "instagram_corpus.parquet")
    c = c[c["in_corpus"]].copy()
    return pd.DataFrame({
        "platform": "instagram", "media_id": c["shortcode"], "account": c["source_handle"],
        "posted_by": c["owner_username"], "market": c["market"], "region": c["region"],
        "followers": pd.to_numeric(c["owner_followers"], errors="coerce"),
        "likes": pd.to_numeric(c["like_count"], errors="coerce"),
        "comments": pd.to_numeric(c["comments_count"], errors="coerce"),
        "views": np.nan,  # Instagram views are unreliable (docs/06 §1) and never used
        "likes_hidden": c["like_count"].isna(),
        "comments_disabled": c["comments_disabled"].fillna(False).astype(bool) | c["comments_count"].isna(),
        "posted_at": pd.to_datetime(c["timestamp"], utc=True, format="mixed"),
        "read_at": pd.to_datetime(c["collected_at"], utc=True, format="mixed"),
        "is_zero_sugar": c["is_zero_sugar"].astype(bool),
        # D-029: how the video entered the sample and how its Zero Sugar label was decided
        "is_zero_sugar_before_D029": c.get("is_zero_sugar_before_D029", c["is_zero_sugar"]).astype(bool),
        "zs_label_method": c.get("zs_label_method"),
        "zs_clip_screen": c.get("zs_clip_screen"),
        "selection": c.get("selection"),
        "in_focus": c.get("in_focus", c["is_zero_sugar"]).astype(bool),
        "is_collab": c["is_collab"],
        "account_type": c["account_type"],
    })


def _tier(f: float) -> str | float:
    if pd.isna(f):
        return np.nan
    return "small" if f < 100_000 else ("medium" if f <= 1_000_000 else "large")


def build() -> tuple[pd.DataFrame, dict]:
    df = pd.concat([_yt(), _ig()], ignore_index=True)
    df["video_age_days"] = (df["read_at"] - df["posted_at"]).dt.total_seconds() / 86400
    df["year"] = df["posted_at"].dt.year
    df["account_size_tier"] = df["followers"].map(_tier)

    # ------------------------------------------------------------------ eligibility
    df["dv_status"] = "ok"
    df.loc[df["followers"].isna() | (df["followers"] <= 0), "dv_status"] = "excluded_no_followers"
    df.loc[df["comments_disabled"], "dv_status"] = "excluded_comments_disabled"
    df.loc[df["likes_hidden"], "dv_status"] = "excluded_likes_hidden"
    df.loc[(df["dv_status"] == "ok") & (df["video_age_days"] < MIN_AGE_DAYS), "dv_status"] = "pending_refresh"
    ok = df["dv_status"] == "ok"

    # ------------------------------------------------------------------ 6.1 / 6.2
    df["engagement_rate_follower"] = np.where(ok, (df["likes"] + df["comments"]) / df["followers"], np.nan)
    yt_ok = ok & (df["platform"] == "youtube") & (df["views"] > 0)
    df["engagement_rate_view"] = np.where(yt_ok, (df["likes"] + df["comments"]) / df["views"], np.nan)

    # ------------------------------------------------------------------ 6.3 cells
    schemes = [
        ("platform x size tier x year", ["platform", "account_size_tier", "year"]),
        ("platform x size tier", ["platform", "account_size_tier"]),
        ("platform x size (small+medium merged)", ["platform", "size_merged"]),
        ("platform only", ["platform"]),
    ]
    df["size_merged"] = df["account_size_tier"].replace({"small": "small_medium", "medium": "small_medium"})
    tried = []
    chosen = None
    for name, keys in schemes:
        sizes = df[ok].groupby(keys).size()
        tried.append((name, int(sizes.min()), int((sizes < MIN_CELL).sum()), len(sizes)))
        if sizes.min() >= MIN_CELL:
            chosen = (name, keys)
            break
    if chosen is None:
        chosen = schemes[-1]
    name, keys = chosen
    df["dv_cell"] = np.where(ok, df[keys].astype(str).agg(" | ".join, axis=1), None)
    df["engagement_pct"] = df[ok].groupby(keys)["engagement_rate_follower"].rank(pct=True, method="average")
    df["engagement_high"] = np.where(df["engagement_pct"].notna(), (df["engagement_pct"] > 0.5).astype(float), np.nan)
    df["engagement_tertile"] = pd.cut(df["engagement_pct"], [0, 1 / 3, 2 / 3, 1], labels=["low", "mid", "high"],
                                      include_lowest=True)
    df["engagement_tertile_binary"] = df["engagement_tertile"].map({"low": 0.0, "high": 1.0, "mid": np.nan}).astype(float)

    info = {"schemes_tried": tried, "scheme_used": name, "cell_keys": keys,
            "cells": df[ok].groupby(keys).size().to_dict()}
    return df.drop(columns=["size_merged"]), info


def report(df: pd.DataFrame, info: dict, show_outcomes: bool = False) -> None:
    """Counts and cell sizes always; engagement values only when asked (D-029).

    The platform comparison was pre-registered on 2026-09-22 (docs/08 section 7). Before that,
    this report printed engagement distributions by platform and median percentile by Zero
    Sugar within platform every time it ran; both had been seen, and that is disclosed in the
    pre-registration. From then on they stay hidden unless `--show-outcomes` is passed, so
    re-running the script to apply label changes does not show outcomes early.
    """
    print(f"{'=' * 66}\nDEPENDENT VARIABLE  (docs/06)")
    print("\nstatus by platform:")
    print(df.groupby(["platform", "dv_status"]).size().unstack(fill_value=0).to_string())
    print("\nnormalisation cells tried (min cell n, cells under 10, total cells):")
    for name, mn, under, total in info["schemes_tried"]:
        print(f"  {name:<40} min {mn:>3} | under {MIN_CELL}: {under:>2} of {total}")
    print(f"  -> USED: {info['scheme_used']}")
    for k, v in info["cells"].items():
        print(f"     {k}: {v}")
    ok = df[df["dv_status"] == "ok"]
    print(f"\nusable rows by platform: {ok.groupby('platform').size().to_dict()}")
    if "is_zero_sugar" in ok.columns:
        print("usable rows, platform x Zero Sugar (counts only):")
        print(pd.crosstab(ok["platform"], ok["is_zero_sugar"]).to_string())
    if "in_focus" in ok.columns:
        f = ok[ok["in_focus"]]
        print(f"\nD-030 focus set (Zero Sugar only), usable rows: {len(f)}")
        print(f"  videos per platform  : {f.groupby('platform').size().to_dict()}")
        print(f"  accounts per platform: {f.groupby('platform')['account'].nunique().to_dict()}")
        print(f"  kept as robustness set (not in focus): {int((~ok['in_focus']).sum())} usable, "
              f"{int((~df['in_focus']).sum())} rows in all")
    if not show_outcomes:
        print("\n(engagement values hidden - pre-registered comparison, D-029; "
              "--show-outcomes to display)")
        return
    print("\ndistributions (docs/06 §7):")
    rows = []
    for p, g in ok.groupby("platform"):
        r = g["engagement_rate_follower"]
        q1, q3 = r.quantile([.25, .75])
        rows.append({"platform": p, "n": len(g), "median ER_follower": f"{r.median():.4%}",
                     "IQR": f"{q1:.4%} - {q3:.4%}", "skew": round(r.skew(), 2),
                     "zero-comment videos": int((g["comments"] == 0).sum()),
                     "median followers": f"{g['followers'].median():,.0f}",
                     "median age (days)": round(g["video_age_days"].median(), 1)})
    print(pd.DataFrame(rows).to_string(index=False))
    hidden = df.groupby("platform")["likes_hidden"].sum().to_dict()
    print(f"\nhidden like counts: {hidden}")
    print(f"median split balance: {ok['engagement_high'].value_counts().to_dict()}")
    print(f"tertile split n (low+high): {int(ok['engagement_tertile_binary'].notna().sum())}")
    zs = ok.groupby(["platform", "is_zero_sugar"])["engagement_pct"].median().unstack()
    print("\nmedian percentile by Zero Sugar (descriptive only - no test yet):")
    print(zs.round(3).to_string())


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Build the dependent variable (docs/06).")
    ap.add_argument("--show-outcomes", action="store_true",
                    help="also print engagement values (hidden by default since D-029)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    df, info = build()
    report(df, info, show_outcomes=args.show_outcomes)
    if OUT.exists():
        for tag in BACKUP_TAGS:
            backup = OUT.with_name(f"{OUT.stem}_{tag}.parquet")
            if not backup.exists():
                shutil.copy2(OUT, backup)
                print(f"backup -> {backup.relative_to(config.ROOT)}")
    df.to_parquet(OUT, index=False)
    print(f"\nwritten -> {OUT.relative_to(config.ROOT)}  ({len(df)} rows)")


if __name__ == "__main__":
    main()

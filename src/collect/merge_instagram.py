"""Rebuild the canonical Instagram parquet from every raw actor response on disk.

**Why this exists.** `instagram.py` writes its output parquet with a plain
`df.to_parquet(...)` and never reads the existing file. There is no append and no
cross-run dedupe — `parse_items()` deduplicates within one run's items only. So each run
*replaces* the corpus rather than extending it, and a run's Reels are lost the moment the
next run finishes. That is not hypothetical: the 2026-09-09 run
`...jqOx3SUlWp6FvpVnf...` returned 180 Reels, 150 of them new, and every one was discarded
by a later run. The parquet held 60 rows while the raw directory held 319 unique Reels.

Raw JSON is written before anything is parsed (see `instagram.py` design note 1), so every
Reel ever returned is still on disk. This tool reads all of it back, merges, dedupes across
runs, and restores follower counts from saved profile runs.

**It makes no API call and costs nothing**, which is the point: on a free-tier account the
cheapest Reel is one already paid for. Re-running it is always safe and always idempotent.

**Collection discipline this implies.** Point new collection runs at a unique `--out`
(`data/raw/instagram_reels_<date>.parquet`), never at the canonical path, then fold them in
here. `--dry-run` is not a substitute: it takes exactly one file and overwrites too.

Usage:
    python -m src.collect.merge_instagram              # rebuild the canonical parquet
    python -m src.collect.merge_instagram --check      # report only, write nothing
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.collect.instagram import (  # noqa: E402
    RAW_RUNS,
    followers_from_saved_runs,
    parse_items,
)

# Both frames are needed, not just the Instagram one. Early runs used handles that live
# only in the cross-platform frame (`somoscocacola`), and a handle missing from the map
# yields a blank market — a row that silently drops out of any market-stratified analysis.
ACCOUNT_FRAMES = [config.DOCS / "accounts_instagram.csv", config.ACCOUNTS_CSV]

CANONICAL = config.RAW / "instagram_reels.parquet"


def account_lookup(paths: list[Path] = ACCOUNT_FRAMES) -> dict[str, dict[str, str]]:
    """handle -> {market, region, account_type} across every sampling frame.

    First frame wins on conflict, so the Instagram frame's labels take precedence over the
    older cross-platform one for handles present in both.
    """
    out: dict[str, dict[str, str]] = {}
    for path in paths:
        if not path.exists():
            print(f"  ! missing account frame: {path}")
            continue
        frame = pd.read_csv(path, dtype=str).fillna("")
        for _, row in frame.iterrows():
            handle = str(row.get("instagram_handle", "")).strip().lstrip("@")
            if handle and handle not in out:
                # The cross-platform frame calls this column `channel_type` (it describes
                # a YouTube channel there). Falling back keeps `somoscocacola` tagged
                # `industry_body` instead of blank — D-012 requires it stay controllable.
                kind = str(row.get("account_type", "") or row.get("channel_type", ""))
                out[handle] = {
                    "market": str(row.get("market", "")),
                    "region": str(row.get("region", "")),
                    "account_type": kind,
                }
    return out


def merge(runs_dir: Path = RAW_RUNS, verbose: bool = True) -> pd.DataFrame:
    """Parse every saved reel-actor run and merge into one deduplicated frame."""
    accounts = account_lookup()
    market_of = {h: v["market"] for h, v in accounts.items()}

    paths = sorted(runs_dir.glob("*reel*.json"))
    if not paths:
        raise SystemExit(f"No reel-actor runs in {runs_dir}. Nothing to merge.")

    frames: list[pd.DataFrame] = []
    seen: set[str] = set()
    for path in paths:
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  ! unreadable, skipped: {path.name} ({exc})")
            continue
        if not isinstance(items, list) or not items:
            continue
        frame = parse_items(items, market_of)
        if frame.empty:
            if verbose:
                print(f"  {path.name[:58]:60s} {len(items):>4} items -> 0 usable")
            continue
        codes = set(frame["shortcode"].dropna())
        if verbose:
            print(f"  {path.name[:58]:60s} {len(items):>4} items  "
                  f"{len(codes):>4} reels  {len(codes - seen):>4} new")
        seen |= codes
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    # The step that does not exist anywhere else: dedupe ACROSS runs, not within one.
    # Keep the last occurrence so a later re-pull refreshes like/comment counts.
    df = df.drop_duplicates(subset="shortcode", keep="last").reset_index(drop=True)

    # Followers come from saved profile runs rather than a fresh lookup. Map on
    # `owner_username`, never `source_handle`: a collaborator post reports the creator as
    # owner, and the exposure denominator must be the account that actually posted it.
    cached = followers_from_saved_runs(runs_dir)
    df["owner_followers"] = df["owner_followers"].fillna(
        df["owner_username"].map(cached))

    # Region and account_type ride in from the frame on the REQUESTED handle, so a
    # collaborator's Reel is attributed to the market that commissioned it (trap 4).
    for col in ("region", "account_type"):
        df[col] = df["source_handle"].map(
            {h: v[col] for h, v in accounts.items()}).fillna("")

    if verbose:
        print(f"  follower cache: {len(cached)} accounts from saved profile runs")
    return df


def report(df: pd.DataFrame) -> None:
    print("\n" + "=" * 62)
    print(f"merged Reels     : {len(df)}")
    print(f"source handles   : {df['source_handle'].nunique()}")
    print(f"owner accounts   : {df['owner_username'].nunique()}")
    print(f"markets          : {df['market'].replace('', pd.NA).nunique()}")
    print(f"regions          : {df['region'].replace('', pd.NA).nunique()}")
    unmapped = int((df["market"].fillna("") == "").sum())
    missing_f = int(df["owner_followers"].isna().sum())
    missing_l = int(df["like_count"].isna().sum())
    print(f"market unmapped  : {unmapped}{'   <-- INVESTIGATE' if unmapped else ''}")
    print(f"followers missing: {missing_f}{'   <-- INVESTIGATE' if missing_f else ''}")
    print(f"likes missing    : {missing_l}  (null means hidden, not zero)")
    if "sampling_tier" in df:
        tiers = df["sampling_tier"].value_counts().to_dict()
        print(f"tier 1 / tier 2  : {tiers.get(1, 0)} / {tiers.get(2, 0)}")
    if "timestamp" in df:
        ts = df["timestamp"].dropna().astype(str)
        if not ts.empty:
            print(f"date range       : {ts.min()[:10]} .. {ts.max()[:10]}")
    print("\nper region:")
    print(df["region"].replace("", "(unmapped)").value_counts().to_string())


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Merge every saved Instagram actor run into the canonical parquet.")
    ap.add_argument("--runs-dir", default=str(RAW_RUNS))
    ap.add_argument("--out", default=str(CANONICAL))
    ap.add_argument("--check", action="store_true",
                    help="report only; write nothing")
    args = ap.parse_args()

    print(f"merging raw actor runs from {args.runs_dir}")
    df = merge(Path(args.runs_dir))
    report(df)

    out = Path(args.out)
    if args.check:
        print(f"\n--check: nothing written. {out} left as-is.")
        return

    if out.exists():
        before = len(pd.read_parquet(out))
        kept = len(set(pd.read_parquet(out)["shortcode"]) & set(df["shortcode"]))
        print(f"\nexisting parquet : {before} rows, {kept} of them retained in the merge")
        if kept < before:
            print(f"  ! {before - kept} row(s) in the old file are NOT in the raw runs.")
            print("    Merging would lose them. Aborting - investigate first.")
            raise SystemExit(1)

    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"\nwritten          : {len(df)} rows -> {out}")
    print("cost             : $0.00 (no API call made)")


if __name__ == "__main__":
    main()

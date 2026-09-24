"""Task 2b.7 - re-read likes and comments for corpus Reels first read under 7 days old (D-019).

D-019: engagement counts enter the dependent variable only if read at least 7 days after
posting. Three corpus Reels were read sooner and carry `metrics_maturity =
too_young_refresh` with a `refresh_after` date. This module re-reads them once they are old
enough - free, logged-out `yt-dlp`, no video download - and folds the new reading in.

How it keeps the record honest:

1.  **The first reading is never overwritten.** New raw responses go to a dated folder,
    `data/raw/refresh_<YYYYMMDD>/<shortcode>.json`; the original fetch (or Apify run) stays
    where it was (D-016: raw responses are the record). Commenters' names and comment text
    are stripped before saving, as in `instagram_links` - only the counts are kept.
2.  **Every reading is logged** in `data/raw/metric_refreshes.csv`: when it was read, how old
    the post was, the counts, the source, the raw file.
3.  **Only the affected rows change.** `apply_refreshes()` takes, for each Reel, the latest
    logged reading made at least 7 days after posting and writes it into `like_count`,
    `comments_count` and `collected_at` (the read time the dependent variable uses). The
    values it replaces are kept in `*_first_read` columns. The corpus parquet is backed up
    before the first write. `build_instagram_corpus` calls the same function, so a future
    rebuild keeps the refresh instead of silently reverting it.
4.  **Hidden stays hidden** (D-005): a count that is now hidden is recorded as null, never 0.

Usage:
    python -m src.collect.refresh_metrics --check   # list what is due; no network, no writes
    python -m src.collect.refresh_metrics           # fetch what is due, apply, write
    python -m src.collect.refresh_metrics --apply-only
Then re-run `python -m src.process.dependent_variable` and `python -m src.export.shared`.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

CORPUS = config.PROCESSED / "instagram_corpus.parquet"
LEDGER = config.RAW / "metric_refreshes.csv"
MIN_AGE_DAYS = 7


def _posted(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df["timestamp"], utc=True, format="mixed")


def due(df: pd.DataFrame, now: datetime) -> pd.DataFrame:
    """In-corpus Reels read too young whose post is now at least 7 days old."""
    young = df[df["in_corpus"] & (df["metrics_maturity"] == "too_young_refresh")].copy()
    young["age_now_days"] = (pd.Timestamp(now) - _posted(young)).dt.total_seconds() / 86400
    return young[young["age_now_days"] >= MIN_AGE_DAYS]


def fetch(row: pd.Series, out_dir: Path) -> dict:
    """One fresh reading. Cached per run folder, so a re-run never fetches twice."""
    from src.collect.instagram_links import _pick_video, fetch_one
    code = row["shortcode"]
    path = out_dir / f"{code}.json"
    if path.exists():
        rec = json.loads(path.read_text(encoding="utf-8"))
    else:
        rec = fetch_one(row["permalink"])
        out_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    info = rec.get("info") or {}
    video = _pick_video(info)[0] if info else {}
    likes = info.get("like_count", video.get("like_count"))
    comments = info.get("comment_count", video.get("comment_count"))
    read_at = pd.Timestamp(rec["fetched_at"])
    posted = _posted(pd.DataFrame([row])).iloc[0]
    return {"shortcode": code, "status": rec.get("status"), "error": rec.get("error"),
            "read_at": read_at.isoformat(),
            "age_days": round((read_at - posted).total_seconds() / 86400, 3),
            "like_count": int(likes) if isinstance(likes, (int, float)) else None,
            "comments_count": int(comments) if isinstance(comments, (int, float)) else None,
            "source": f"yt-dlp {rec.get('yt_dlp_version')} (logged out)",
            "raw_file": str(path.relative_to(config.ROOT))}


def apply_refreshes(df: pd.DataFrame) -> pd.DataFrame:
    """Write the latest valid logged reading into each refreshed row. Idempotent."""
    if not LEDGER.exists():
        return df
    led = pd.read_csv(LEDGER, dtype={"shortcode": str})
    led = led[(led["status"] == "ok") & (led["age_days"] >= MIN_AGE_DAYS)]
    if led.empty:
        return df
    latest = led.sort_values("read_at").groupby("shortcode").tail(1).set_index("shortcode")
    df = df.copy()
    for col in ("like_count", "comments_count", "collected_at", "metrics_age_days"):
        if f"{col}_first_read" not in df.columns:
            df[f"{col}_first_read"] = pd.Series(pd.NA, index=df.index, dtype="object")
    for col in ("metrics_refreshed_at", "metrics_refresh_source"):
        if col not in df.columns:
            df[col] = pd.Series(pd.NA, index=df.index, dtype="object")
    for code, r in latest.iterrows():
        idx = df.index[df["shortcode"] == code]
        for i in idx:
            if pd.isna(df.at[i, "collected_at_first_read"]):   # keep the first reading once
                for col in ("like_count", "comments_count", "collected_at", "metrics_age_days"):
                    df.at[i, f"{col}_first_read"] = df.at[i, col]
            df.at[i, "like_count"] = r["like_count"] if pd.notna(r["like_count"]) else None
            df.at[i, "comments_count"] = (r["comments_count"] if pd.notna(r["comments_count"])
                                          else None)
            df.at[i, "collected_at"] = r["read_at"]
            df.at[i, "metrics_age_days"] = r["age_days"]
            df.at[i, "metrics_maturity"] = "mature"
            df.at[i, "refresh_after"] = None
            df.at[i, "metrics_refreshed_at"] = r["read_at"]
            df.at[i, "metrics_refresh_source"] = f"{r['source']}; raw {r['raw_file']}"
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description="2b.7 - refresh engagement counts read too young.")
    ap.add_argument("--check", action="store_true", help="list what is due; no network, no writes")
    ap.add_argument("--apply-only", action="store_true", help="no network; apply the ledger")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    df = pd.read_parquet(CORPUS)
    pending = df[df["in_corpus"] & (df["metrics_maturity"] == "too_young_refresh")]
    todo = due(df, now)
    print(f"pending refresh: {len(pending)}; due now (post >= {MIN_AGE_DAYS} days old): {len(todo)}")
    if len(todo):
        print(todo[["shortcode", "owner_username", "timestamp", "like_count", "comments_count",
                    "age_now_days"]].to_string(index=False))
    if args.check:
        return

    if not args.apply_only and len(todo):
        out_dir = config.RAW / f"refresh_{now:%Y%m%d}"
        rows = []
        for n, (_, r) in enumerate(todo.iterrows()):
            if n:
                time.sleep(random.uniform(3.0, 6.0))   # polite, as in instagram_links
            res = fetch(r, out_dir)
            print(f"  {res['shortcode']}: {res['status']}  likes {res['like_count']}  "
                  f"comments {res['comments_count']}  age {res['age_days']} d"
                  + (f"  ({res['error'][:80]})" if res["error"] else ""))
            rows.append(res)
        new = pd.DataFrame(rows)
        if LEDGER.exists():
            old = pd.read_csv(LEDGER, dtype={"shortcode": str})
            new = pd.concat([old, new], ignore_index=True).drop_duplicates(
                subset=["shortcode", "read_at"], keep="last")
        new.to_csv(LEDGER, index=False)
        print(f"ledger -> {LEDGER.relative_to(config.ROOT)}")

    backup = CORPUS.with_name(f"instagram_corpus_before_refresh_{now:%Y%m%d}.parquet")
    if not backup.exists():
        shutil.copy2(CORPUS, backup)
        print(f"backup -> {backup.relative_to(config.ROOT)}")
    after = apply_refreshes(df)
    changed = after[after["metrics_refreshed_at"].notna()] if "metrics_refreshed_at" in after else []
    after.to_parquet(CORPUS, index=False)
    print(f"corpus written: {len(changed)} row(s) carry a refreshed reading")
    if len(changed):
        print(changed[["shortcode", "like_count_first_read", "like_count",
                       "comments_count_first_read", "comments_count",
                       "metrics_age_days_first_read", "metrics_age_days",
                       "metrics_maturity"]].to_string(index=False))
    still = after[after["in_corpus"] & (after["metrics_maturity"] == "too_young_refresh")]
    print(f"still pending: {len(still)} {still['shortcode'].tolist()}")


if __name__ == "__main__":
    main()

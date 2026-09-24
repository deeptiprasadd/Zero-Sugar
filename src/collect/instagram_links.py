"""Fetch details for a researcher-curated list of Instagram Reel links (D-018).

The Apify collector (`instagram.py`) works account-by-account. The curated Zero Sugar list
is the opposite shape: individual links, each already checked by eye. This module fetches
metadata for those links with `yt-dlp` — free, no login, no video download — and writes it
in the same column names as the Apify parquet so the two can be merged later.

Design points:

1.  **One cached JSON per link**, in `data/raw/ytdlp_instagram/<shortcode>.json`, written
    before anything is parsed. Re-running skips links already fetched, so a run cut short
    by Instagram throttling resumes instead of starting again, and never re-fetches what is
    already on disk (the D-016 principle: raw responses are the record).
2.  **Polite pacing and a stop rule.** Logged-out Instagram answers throttling and "login
    required" with the same message. A run of consecutive failures is treated as
    throttling and the run stops rather than hammering — the remaining links are picked up
    by the next run.
3.  **Hidden ≠ zero.** A missing like or comment count stays null (D-005).
4.  **Output goes to a dated parquet**, never the canonical Instagram file (standing rule 1).
5.  Signed media URLs and request headers are stripped from the cache: they expire within
    hours and add nothing to the record.

Usage:
    python -m src.collect.instagram_links --limit 3          # small test
    python -m src.collect.instagram_links                    # all links, resumable
    python -m src.collect.instagram_links --retry-failed     # retry cached failures
    python -m src.collect.instagram_links --parse-only       # rebuild parquet from cache
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.collect.merge_instagram import account_lookup  # noqa: E402

CURATED_CSV = config.DOCS / "curated_zero_sugar_reels.csv"
CACHE = config.RAW / "ytdlp_instagram"

# Keys stripped from each format entry before caching — expiring or request-specific.
_VOLATILE = {"url", "manifest_url", "fragments", "http_headers", "fragment_base_url"}

# How many consecutive unavailable/login failures mean "we are being throttled".
STOP_AFTER = 6


def _classify(message: str) -> str:
    m = message.lower()
    if "rate-limit" in m or "login required" in m or "rate limit" in m or "429" in m:
        # Instagram gives one message for both; a single case cannot be told apart.
        return "unavailable_or_login"
    if "404" in m or "not found" in m or "isn't available" in m or "not available" in m \
            or "deleted" in m or "private" in m:
        return "not_available"
    if "empty media" in m:
        return "empty_media"
    return "error"


def _strip(info: dict) -> dict:
    """Drop expiring URLs and headers from a yt-dlp info dict, recursively for entries."""
    out = {k: v for k, v in info.items() if k not in _VOLATILE and k != "requested_formats"}
    if isinstance(out.get("formats"), list):
        out["formats"] = [{k: v for k, v in f.items() if k not in _VOLATILE}
                          for f in out["formats"]]
    if isinstance(out.get("entries"), list):
        out["entries"] = [_strip(e) for e in out["entries"] if isinstance(e, dict)]
    for k in ("thumbnail", "thumbnails"):
        out.pop(k, None)  # signed CDN URLs, expire
    # yt-dlp includes a sample of comments with each commenter's username, account id and
    # text. That is third-party personal data the project never uses and has committed not
    # to store; the comment *count* is kept separately in `comment_count`.
    out.pop("comments", None)
    return out


def fetch_one(permalink: str) -> dict:
    """Return a cache record for one link. Never raises for a per-link failure."""
    import yt_dlp  # imported here so --parse-only works without it
    from yt_dlp.version import __version__ as ytv

    rec = {"permalink": permalink,
           "fetched_at": datetime.now(timezone.utc).isoformat(),
           "yt_dlp_version": ytv, "status": None, "error": None, "info": None}
    opts = {"skip_download": True, "quiet": True, "no_warnings": True,
            "noprogress": True, "extract_flat": False}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(permalink, download=False)
            rec["info"] = _strip(ydl.sanitize_info(info))
            rec["status"] = "ok"
    except Exception as exc:  # yt-dlp raises DownloadError and friends
        msg = str(exc)
        rec["error"] = msg[-500:]
        rec["status"] = _classify(msg)
    return rec


def _tags(text: str, sigil: str) -> list[str]:
    return sorted(set(re.findall(rf"{re.escape(sigil)}([\w.]+)", text or "", flags=re.UNICODE)))


def _pick_video(info: dict) -> tuple[dict, bool]:
    """A /p/ link can be a carousel. Use its first video entry and flag it."""
    entries = info.get("entries")
    if isinstance(entries, list) and entries:
        vids = [e for e in entries if e.get("vcodec") not in (None, "none")
                or e.get("width")]
        return (vids[0] if vids else entries[0]), True
    return info, False


def _dims(info: dict) -> tuple[int | None, int | None]:
    w, h = info.get("width"), info.get("height")
    if w and h:
        return int(w), int(h)
    best = None
    for f in info.get("formats") or []:
        if f.get("width") and f.get("height") and f.get("vcodec") not in (None, "none"):
            if best is None or f["width"] * f["height"] > best[0] * best[1]:
                best = (f["width"], f["height"])
    return (int(best[0]), int(best[1])) if best else (None, None)


def to_row(code: str, curated: dict, rec: dict, accounts: dict) -> dict:
    """Map a cache record onto the Apify parquet's column names, plus curation fields."""
    info = rec.get("info") or {}
    video, carousel = _pick_video(info) if info else ({}, False)
    handle = info.get("channel") or video.get("channel")
    caption = info.get("description") or video.get("description") or ""
    w, h = _dims(video) if video else (None, None)
    ts = info.get("timestamp") or video.get("timestamp")
    acc = accounts.get(str(handle or ""), {})
    likes = info.get("like_count", video.get("like_count"))
    comments = info.get("comment_count", video.get("comment_count"))
    return {
        "platform": "instagram",
        "shortcode": code,
        "permalink": curated["permalink"],
        "url_type": curated.get("url_type"),
        "fetch_status": rec.get("status"),
        "fetch_error": rec.get("error"),
        "owner_username": handle,
        "owner_full_name": info.get("uploader") or video.get("uploader"),
        "owner_id": str(info.get("uploader_id") or video.get("uploader_id") or "") or None,
        "owner_followers": None,  # not in yt-dlp output; filled from frames/profile runs later
        "caption": caption or None,
        "hashtags": json.dumps(_tags(caption, "#"), ensure_ascii=False),
        "mentions": json.dumps(_tags(caption, "@"), ensure_ascii=False),
        "timestamp": (datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None),
        "like_count": int(likes) if isinstance(likes, (int, float)) else None,
        "comments_count": int(comments) if isinstance(comments, (int, float)) else None,
        "view_count": info.get("view_count", video.get("view_count")),
        "duration_sec": info.get("duration", video.get("duration")),
        "actor_width": w,
        "actor_height": h,
        "is_vertical": (h > w) if (w and h) else None,
        "is_carousel": carousel,
        "market": acc.get("market") or None,
        "region": acc.get("region") or None,
        "account_type": acc.get("account_type") or None,
        "in_account_frame": bool(acc),
        "researcher_label": curated.get("researcher_label"),
        "label_source": curated.get("label_source"),
        "curated_order": curated.get("curated_order"),
        "metadata_source": f"yt-dlp {rec.get('yt_dlp_version')}",
        "collected_at": rec.get("fetched_at"),
    }


def _looks_like_coca_cola(handle: str) -> bool:
    h = (handle or "").lower()
    return "cocacola" in h or "coca_cola" in h or h.startswith("coke")


def attribute_sources(df: pd.DataFrame, accounts: dict) -> pd.DataFrame:
    """Work out which Coca-Cola page each curated Reel belongs to.

    The chat export records links only, not the page each was saved from. On a
    collaboration post Instagram reports the *partner* (a creator, Crocs, Star Wars) as
    owner, so the owner alone cannot give market or region (trap 4). Evidence is used in
    strict order of strength, and `source_basis` records which one decided each row so a
    weak attribution can never pass for a strong one:

      owner_in_frame          owner is a frame account                        - certain
      caption_mention         caption @mentions exactly one frame account      - strong
      new_coca_cola_account   owner is a Coca-Cola handle outside the frame    - O-10, unverified
      neighbour_inferred      the links saved immediately before and after it
                              share one page; the researcher saved page by page - needs confirming
      unresolved              none of the above
    """
    out = df.copy()
    frame = set(accounts)
    src, basis = [], []
    for _, r in out.iterrows():
        owner = r.get("owner_username") or ""
        mentioned = [m for m in json.loads(r.get("mentions") or "[]") if m in frame]
        if r.get("fetch_status") != "ok":
            src.append(None); basis.append("not_fetched")
        elif owner in frame:
            src.append(owner); basis.append("owner_in_frame")
        elif len(set(mentioned)) == 1:
            src.append(mentioned[0]); basis.append("caption_mention")
        elif _looks_like_coca_cola(owner):
            src.append(owner); basis.append("new_coca_cola_account")
        elif len({m for m in json.loads(r.get("mentions") or "[]")
                  if _looks_like_coca_cola(m)}) == 1:
            # A collaboration tagging one Coca-Cola account that is not in the frame yet
            # (e.g. Kenya). Still unverified - it joins the O-10 list, it is not trusted.
            new = next(m for m in json.loads(r.get("mentions") or "[]")
                       if _looks_like_coca_cola(m))
            src.append(new); basis.append("caption_mention_new_account")
        else:
            src.append(None); basis.append("unresolved")
    out["source_handle"], out["source_basis"] = src, basis

    # Neighbour inference for what is still open, using only strong anchors.
    out = out.sort_values("curated_order", key=lambda s: pd.to_numeric(s, errors="coerce"))
    anchors = out["source_basis"].isin(["owner_in_frame", "caption_mention",
                                        "new_coca_cola_account",
                                        "caption_mention_new_account"])
    prev_src = out["source_handle"].where(anchors).ffill()
    next_src = out["source_handle"].where(anchors).bfill()
    fill = out["source_basis"].isin(["unresolved", "not_fetched"]) & \
        prev_src.notna() & (prev_src == next_src)
    out.loc[fill, "source_handle"] = prev_src[fill]
    out.loc[fill, "source_basis"] = out.loc[fill, "source_basis"].map(
        lambda b: "neighbour_inferred" if b == "unresolved" else "neighbour_inferred_unfetched")

    out["is_collab"] = out["owner_username"].notna() & out["source_handle"].notna() & \
        (out["owner_username"] != out["source_handle"])
    for col in ("market", "region", "account_type"):
        out[col] = out["source_handle"].map(lambda h: (accounts.get(h) or {}).get(col) or None)
    out["in_account_frame"] = out["source_handle"].isin(frame)
    return out.sort_index()


def agreement_report(curated_parquet: Path) -> pd.DataFrame:
    """Task 2b.2: do yt-dlp and Apify agree on the Reels both have fetched?

    The two were fetched days apart, so counts are expected to *grow*, not match exactly.
    Identity fields (account, posting time, dimensions) must match exactly — a mismatch
    there means the two sources are not describing the same post.
    """
    a = pd.read_parquet(config.RAW / "instagram_reels.parquet").drop_duplicates("shortcode")
    y = pd.read_parquet(curated_parquet)
    y = y[y["fetch_status"] == "ok"]
    m = y.merge(a, on="shortcode", suffixes=("_ytdlp", "_apify"))
    if m.empty:
        print("no overlap between the curated fetch and the Apify data")
        return m

    def ts(s):
        return pd.to_datetime(s, errors="coerce", utc=True)

    m["same_account"] = m["owner_username_ytdlp"] == m["owner_username_apify"]
    m["same_post_time"] = (ts(m["timestamp_ytdlp"]) - ts(m["timestamp_apify"])).abs() \
        <= pd.Timedelta(seconds=60)
    m["same_dims"] = (m["actor_width_ytdlp"] == m["actor_width_apify"]) & \
                     (m["actor_height_ytdlp"] == m["actor_height_apify"])
    for k in ("like_count", "comments_count"):
        m[f"{k}_ratio"] = m[f"{k}_ytdlp"] / m[f"{k}_apify"]

    print(f"\n{'=' * 62}\nAGREEMENT - yt-dlp vs Apify on {len(m)} shared Reels")
    print(f"  same account     : {int(m['same_account'].sum())}/{len(m)}")
    print(f"  same post time   : {int(m['same_post_time'].sum())}/{len(m)}")
    print(f"  same dimensions  : {int(m['same_dims'].sum())}/{len(m)}")
    for k in ("like_count", "comments_count"):
        r = m[f"{k}_ratio"].dropna()
        if len(r):
            print(f"  {k:<15}: ratio median {r.median():.3f}, range {r.min():.3f}-{r.max():.3f}, "
                  f"within +/-10%: {int(((r > 0.9) & (r < 1.1)).sum())}/{len(r)}")
    cols = ["shortcode", "owner_username_ytdlp", "like_count_apify", "like_count_ytdlp",
            "comments_count_apify", "comments_count_ytdlp", "same_post_time", "same_dims"]
    print(m[cols].to_string(index=False))
    return m


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch metadata for curated Instagram links.")
    ap.add_argument("--agreement", action="store_true",
                    help="task 2b.2: compare against the Apify data, then exit")
    ap.add_argument("--csv", default=str(CURATED_CSV))
    ap.add_argument("--limit", type=int, help="fetch at most N new links this run")
    ap.add_argument("--retry-failed", action="store_true", help="re-fetch cached failures")
    ap.add_argument("--parse-only", action="store_true", help="no network; rebuild parquet")
    ap.add_argument("--min-wait", type=float, default=3.0)
    ap.add_argument("--max-wait", type=float, default=6.0)
    ap.add_argument("--out", default=str(config.RAW /
                    f"instagram_curated_{datetime.now():%Y%m%d}.parquet"))
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    out_path = Path(args.out)
    if out_path.resolve() == (config.RAW / "instagram_reels.parquet").resolve():
        raise SystemExit("Refusing to write the canonical Instagram parquet (standing rule 1).")
    if args.agreement:
        agreement_report(out_path)
        return

    curated = pd.read_csv(args.csv, dtype=str).fillna("")
    curated = curated.drop_duplicates("shortcode")
    CACHE.mkdir(parents=True, exist_ok=True)

    if not args.parse_only:
        todo = []
        for _, r in curated.iterrows():
            p = CACHE / f"{r['shortcode']}.json"
            if p.exists():
                if not args.retry_failed:
                    continue
                if json.loads(p.read_text(encoding="utf-8")).get("status") == "ok":
                    continue
            todo.append(r)
        cached = len(curated) - len(todo)
        if args.limit:
            todo = todo[: args.limit]
        print(f"links in list: {len(curated)} | already cached: {cached} "
              f"| to fetch this run: {len(todo)}", flush=True)

        streak = 0
        for n, r in enumerate(todo, start=1):
            rec = fetch_one(r["permalink"])
            (CACHE / f"{r['shortcode']}.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            who = (rec.get("info") or {}).get("channel") or "-"
            print(f"  [{n:>3}/{len(todo)}] {r['shortcode']:<13} {rec['status']:<22} @{who}",
                  flush=True)
            streak = streak + 1 if rec["status"] == "unavailable_or_login" else 0
            if streak >= STOP_AFTER:
                print(f"\n! {STOP_AFTER} consecutive unavailable/login responses - treating "
                      f"as throttling and stopping. Re-run later with --retry-failed; "
                      f"everything fetched so far is cached.", flush=True)
                break
            if n < len(todo):
                time.sleep(random.uniform(args.min_wait, args.max_wait))

    accounts = account_lookup()
    rows = []
    for _, r in curated.iterrows():
        p = CACHE / f"{r['shortcode']}.json"
        if not p.exists():
            continue
        rows.append(to_row(r["shortcode"], r.to_dict(),
                           json.loads(p.read_text(encoding="utf-8")), accounts))
    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("Nothing cached yet.")
    df = attribute_sources(df, accounts)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)

    ok = df[df["fetch_status"] == "ok"]
    print(f"\n{'=' * 62}")
    print(f"cached records   : {len(df)} of {len(curated)} links  ->  {out_path.name}")
    print(f"fetch status     : {df['fetch_status'].value_counts().to_dict()}")
    if not ok.empty:
        print(f"vertical         : {int(ok['is_vertical'].fillna(False).sum())} of {len(ok)}")
        print(f"carousel posts   : {int(ok['is_carousel'].sum())}")
        print(f"likes hidden     : {int(ok['like_count'].isna().sum())}")
        print(f"collab posts     : {int(ok['is_collab'].sum())}")
    print(f"source basis     : {df['source_basis'].value_counts().to_dict()}")
    new = sorted(df.loc[df['source_basis'].isin(['new_coca_cola_account',
                                                 'caption_mention_new_account']),
                        'source_handle'].dropna().unique())
    print(f"new Coca-Cola accounts to verify (O-10): {new}")


if __name__ == "__main__":
    main()

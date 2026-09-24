"""Build the Instagram analysis corpus from the curated Zero Sugar list (D-018, D-019).

Replaces the stratified-from-screener Instagram corpus (8 Zero Sugar) with one built
around the researcher's visually verified Zero Sugar Reels, filled to n=150 with regular
Coca-Cola Reels already collected. YouTube keeps `build_corpus.py` unchanged.

Membership rules, in order:

1. **Curated Zero Sugar** - every Reel on `docs/curated_zero_sugar_reels.csv` that has a
   video and is vertical (height > width, the rule the YouTube classifier uses). Metadata
   from the yt-dlp fetch; for links only reachable logged-in, the researcher's manual
   download (`reports/curated_reels_to_check.csv`, `path` column).
2. **Screener-found Zero Sugar** - Reels in the 319 whose text names Zero Sugar but that
   are not on the curated list. Kept, labelled by source: they are the comparison group
   D-018 consequence 1 asks for.
3. **Regular fill** - random draw (fixed seed) from the 319: brand content, vertical, not
   Zero Sugar by text, not curated, and read at least 7 days after posting (D-019).

Every row carries where its label, date, shape and follower count came from. A value
that is missing stays null and is listed, never filled with a guess.

Usage:
    python -m src.screen.build_instagram_corpus            # build + write
    python -m src.screen.build_instagram_corpus --check    # report only
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.collect.instagram import followers_from_saved_runs  # noqa: E402
from src.collect.refresh_metrics import apply_refreshes  # noqa: E402
from src.screen.build_corpus import SEED  # noqa: E402
from src.screen.zero_sugar import screen  # noqa: E402

TARGET = 150
MIN_AGE_DAYS = 7  # D-019: engagement is only comparable once a post is a week old
CURATED_FETCH = config.RAW / "instagram_curated_20260915.parquet"
REVIEW = config.REPORTS / "curated_reels_to_check.csv"
MANUAL_METRICS = config.DOCS / "manual_reel_metrics.csv"
CURATED_LIST = config.DOCS / "curated_zero_sugar_reels.csv"
POOL = config.INTERIM / "instagram_screened.parquet"
FRAME = config.DOCS / "accounts_instagram.csv"
OUT = config.PROCESSED / "instagram_corpus.parquet"

# Page the researcher saved from -> the Coca-Cola account behind it (saving-order blocks,
# confirmed by the researcher on 2026-09-15 for every row asked about).
PAGE_HANDLE = {"India": "cocacola_india", "Coca-Cola main": "cocacola", "Turkiye": "cocacola_tr",
               "Malaysia": "cocacolamy", "Brazil": "cocacola_br", "Chile": "cocacola_cl",
               "Korea": "cocacola_korea", "Europe": "cocacolaeurope",
               "Costa Rica": "cocacola_costarica", "Indonesia": "cocacola_id",
               "Thailand": "cocacola_th", "Kenya": "cocacola_kenya", "Singapore": "cocacolasg"}

_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
_IG_EPOCH_MS = 1314220021721


def shortcode_time(code: str) -> pd.Timestamp:
    """Upload time encoded in an Instagram shortcode.

    Measured against 426 known post times (2026-09-15): median error ~1 minute, maximum
    2.7 days - scheduled posts are uploaded before they publish. Good enough for a 7-day
    rule on posts months old; not good enough to replace a real timestamp generally.
    """
    n = 0
    for ch in code:
        n = n * 64 + _ALPHA.index(ch)
    return pd.Timestamp((n >> 23) + _IG_EPOCH_MS, unit="ms", tz="UTC")


def _probe(path: Path) -> tuple[int | None, int | None, float | None]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    try:
        j = json.loads(r.stdout)
        s = j["streams"][0]
        return int(s["width"]), int(s["height"]), float(j["format"]["duration"])
    except (KeyError, IndexError, ValueError, json.JSONDecodeError):
        return None, None, None


def _age_days(post, read) -> pd.Series:
    return (pd.to_datetime(read, utc=True, format="mixed")
            - pd.to_datetime(post, utc=True, format="mixed")).dt.total_seconds() / 86400


def load_frame() -> dict[str, dict]:
    f = pd.read_csv(FRAME, dtype=str).fillna("")
    return {r["instagram_handle"]: r.to_dict() for _, r in f.iterrows()}


def curated_rows(frame: dict) -> pd.DataFrame:
    """Fetched curated Reels + the researcher's manual downloads, one row per shortcode."""
    fetched = pd.read_parquet(CURATED_FETCH)
    review = pd.read_csv(REVIEW, dtype=str, encoding="utf-8-sig").fillna("")
    review["shortcode"] = review["permalink"].str.extract(r"/(?:reel|p)/([^/]+)/")[0]
    confirmed = set(review.loc[review["your_answer"].str.strip().str.lower() == "yes", "shortcode"])

    ok = fetched[fetched["fetch_status"] == "ok"].copy()
    page_of = dict(zip(review["shortcode"], review["page_likely_saved_from"]))
    for i, r in ok[ok["shortcode"].isin(confirmed)].iterrows():
        handle = PAGE_HANDLE.get(page_of.get(r["shortcode"]))
        if handle and isinstance(r["source_handle"], str) and r["source_handle"] != handle:
            # Never silently overwrite evidence with a confirmation that disagrees with it.
            ok.at[i, "source_basis"] = f"{r['source_basis']}+CONFLICT_researcher_says_{handle}"
            continue
        ok.at[i, "source_handle"] = handle or r["source_handle"]
        ok.at[i, "source_basis"] = f"{r['source_basis']}+researcher_confirmed"
    # Market labels are re-read from the *current* frame: accounts verified after the fetch
    # (Chile, Kenya, Singapore) would otherwise stay blank.
    for col in ("market", "region", "account_type"):
        ok[col] = ok["source_handle"].map(lambda h: (frame.get(h) or {}).get(col) or None)
    ok["in_account_frame"] = ok["source_handle"].isin(frame)
    ok["is_collab"] = ok["owner_username"].notna() & ok["source_handle"].notna() & \
        (ok["owner_username"] != ok["source_handle"])
    ok["width"], ok["height"] = ok["actor_width"], ok["actor_height"]
    ok["shape_source"] = "yt-dlp metadata (ffprobe at download)"
    ok["timestamp_source"] = "yt-dlp"
    ok["download_route"] = "yt-dlp (pending)"
    ok["video_path"] = None

    manual = []
    for _, r in review[review["path"].str.lower().str.endswith(".mp4")].iterrows():
        path = Path(r["path"])
        w, h, dur = _probe(path) if path.exists() else (None, None, None)
        page = r["page_likely_saved_from"]
        src = PAGE_HANDLE.get(page)
        acc = frame.get(src, {})
        manual.append({
            "platform": "instagram", "shortcode": r["shortcode"], "permalink": r["permalink"],
            "fetch_status": "manual_download", "owner_username": None,
            "source_handle": src, "source_basis": "saving_order_block+researcher_confirmed",
            "is_collab": None, "market": acc.get("market") or None,
            "region": acc.get("region") or None, "account_type": acc.get("account_type") or None,
            "in_account_frame": bool(acc), "caption": None,
            "timestamp": shortcode_time(r["shortcode"]).isoformat(),
            "timestamp_source": "decoded from shortcode (median err ~1 min, max 2.7 d)",
            "like_count": None, "comments_count": None, "view_count": None,
            "duration_sec": dur, "width": w, "height": h,
            "is_vertical": (h > w) if (w and h) else None,
            "shape_source": "ffprobe on researcher download",
            "collected_at": None, "metadata_source": "researcher manual download",
            "download_route": "researcher manual download",
            "video_path": str(path) if path.exists() else None,
            "curated_order": r["saved_order"],
        })
    # Numbers for the manual downloads, transcribed from the researcher's screenshots
    # (`insta reels/screenshots/`, one file per shortcode; matching evidence in
    # `_rename_map.csv`). Instagram restricts these posts to logged-in users, so neither
    # yt-dlp nor Apify could read them ("restricted_page", 2026-09-15).
    metrics = pd.read_csv(MANUAL_METRICS, dtype=str).fillna("").set_index("shortcode")
    for row in manual:
        code = row["shortcode"]
        if code not in metrics.index:
            continue
        m = metrics.loc[code]
        flags = m["flags"]
        row["owner_username"] = m["owner_username"] or None
        row["owner_basis"] = m["owner_basis"]
        # Hidden is not zero (D-005): a like count the researcher flagged as implausible
        # is held null, with what was displayed kept alongside.
        row["like_count"] = None if ("LIKES SUSPECT" in flags or "LIKES HIDDEN" in flags) \
            else int(m["like_count"])
        row["likes_as_displayed"] = m["likes_as_displayed"]
        row["comments_count"] = int(m["comments_count"]) if m["comments_count"] else None
        row["collected_at"] = "2026-09-15T00:00:00+00:00"  # screenshot date
        row["metadata_source"] = "researcher screenshot, transcribed (docs/manual_reel_metrics.csv)"
        row["download_route"] = m["download_route"]
        row["label_flag"] = flags or None
        if row["owner_username"] and row["source_handle"]:
            row["is_collab"] = row["owner_username"] != row["source_handle"]

    cur = pd.concat([ok, pd.DataFrame(manual)], ignore_index=True)
    cur = cur.drop_duplicates("shortcode", keep="first")

    # What would the text screener have said about these verified Zero Sugar Reels?
    tagged = screen(cur.assign(alt_text=None, audio_name=None), "instagram")
    cur["text_variant"] = tagged["variant"].values
    cur["text_is_zero_sugar"] = tagged["is_zero_sugar"].values
    # The researcher's label per Reel, from the curated list. A Reel the researcher later
    # relabels (e.g. frames show Original Taste) stays in the corpus as a regular Reel.
    labels = pd.read_csv(CURATED_LIST, dtype=str, encoding="utf-8-sig").fillna("") \
        .set_index("shortcode")["researcher_label"].to_dict()
    cur["variant"] = cur["shortcode"].map(lambda c: labels.get(c) or "zero_sugar")
    cur["is_zero_sugar"] = cur["variant"] == "zero_sugar"
    cur["zs_label_source"] = "researcher_visual (each Reel checked, D-018)"
    cur.loc[~cur["is_zero_sugar"], "zs_label_source"] = \
        "researcher_visual (relabelled from zero_sugar after frame check)"
    return cur


def build(check: bool = False) -> pd.DataFrame:
    frame = load_frame()
    cur = curated_rows(frame)
    pool = pd.read_parquet(POOL)

    # ------------------------------------------------------------- 1. curated members
    cur["metrics_age_days"] = _age_days(cur["timestamp"], cur["collected_at"])
    cur["in_corpus"] = cur["is_vertical"].fillna(False).astype(bool)
    cur["corpus_reason"] = "excluded_not_vertical_or_shape_unknown"
    cur.loc[cur["in_corpus"] & cur["is_zero_sugar"], "corpus_reason"] = "curated_zero_sugar"
    cur.loc[cur["in_corpus"] & ~cur["is_zero_sugar"], "corpus_reason"] = \
        "curated_relabelled_not_zero_sugar"

    # ------------------------------------------------------------- pool preparation
    pool = pool[~pool["shortcode"].isin(cur["shortcode"])].copy()
    pool["width"], pool["height"] = pool["actor_width"], pool["actor_height"]
    pool["is_vertical"] = pool["height"] > pool["width"]
    pool["shape_source"] = "Apify metadata (ffprobe at download)"
    pool["timestamp_source"] = "Apify"
    pool["metadata_source"] = "Apify"
    pool["download_route"] = "yt-dlp (pending)"
    pool["source_basis"] = "requested_account"
    pool["metrics_age_days"] = _age_days(pool["timestamp"], pool["collected_at"])
    pool["in_corpus"] = False
    pool["corpus_reason"] = "not_selected"

    # ------------------------------------------------------------- 2. screener Zero Sugar
    zs = pool["is_zero_sugar"] & pool["is_vertical"]
    pool.loc[zs, ["in_corpus", "corpus_reason"]] = [True, "screener_zero_sugar_comparison"]
    pool.loc[pool["is_zero_sugar"], "zs_label_source"] = "text_screener (caption names Zero Sugar)"
    pool.loc[~pool["is_zero_sugar"], "zs_label_source"] = "none (text does not name a variant)"

    # ------------------------------------------------------------- 3. regular fill
    have = int(cur["in_corpus"].sum()) + int(zs.sum())
    need = max(TARGET - have, 0)
    eligible = pool[(~pool["is_zero_sugar"]) & (pool["variant"] != "off_brand")
                    & pool["is_vertical"] & (pool["metrics_age_days"] >= MIN_AGE_DAYS)]
    fill = eligible.sample(n=min(need, len(eligible)), random_state=SEED).index
    pool.loc[fill, ["in_corpus", "corpus_reason"]] = [True, "regular_fill"]

    for df in (cur, pool):
        # Three states, not two: a row with no engagement numbers yet is "pending", which
        # is a different problem from numbers read too soon.
        df["metrics_maturity"] = "mature"
        df.loc[df["metrics_age_days"] < MIN_AGE_DAYS, "metrics_maturity"] = "too_young_refresh"
        df.loc[df["like_count"].isna() & df["metrics_age_days"].isna(), "metrics_maturity"] = \
            "pending_manual_numbers"
        post = pd.to_datetime(df["timestamp"], utc=True, format="mixed")
        df["refresh_after"] = (post + pd.Timedelta(days=MIN_AGE_DAYS)).dt.strftime("%Y-%m-%d") \
            .where(df["metrics_maturity"] == "too_young_refresh")

    # ------------------------------------------------------------- followers (D-005)
    cached = followers_from_saved_runs()
    mm = pd.read_csv(MANUAL_METRICS, dtype=str).fillna("")
    manual_followers = {r["owner_username"]: float(r["owner_followers"]) for _, r in mm.iterrows()
                        if r["owner_username"] and r.get("owner_followers", "")}
    allrows = pd.concat([cur, pool], ignore_index=True)
    fsrc = pd.Series("apify_reel_run", index=allrows.index).where(allrows["owner_followers"].notna())
    for i, r in allrows[allrows["owner_followers"].isna()].iterrows():
        owner = r.get("owner_username")
        # Only the owner's own count is used. Falling back to the Coca-Cola page when the
        # owner is unknown would give a creator's #Ad post the brand's audience - an
        # exposure value for the wrong account, and invisible once written.
        who = owner if isinstance(owner, str) and owner else None
        if who is None:
            fsrc[i] = "pending_owner_unknown"
        elif who in cached:
            allrows.at[i, "owner_followers"], fsrc[i] = cached[who], "apify_profile_cache"
        elif who in manual_followers:
            # Restricted profiles: only a logged-in person can read the count.
            allrows.at[i, "owner_followers"] = manual_followers[who]
            fsrc[i] = "researcher_read_on_instagram_2026-09-15 (display-rounded)"
        elif who in frame and str(frame[who].get("followers_shown", "")).strip():
            allrows.at[i, "owner_followers"] = float(frame[who]["followers_shown"])
            fsrc[i] = "researcher_transcribed_frame"
    fsrc = fsrc.where(fsrc.notna() | allrows["owner_followers"].notna(),
                      "missing_profile_restricted_or_unlisted")
    allrows["followers_source"] = fsrc

    n_zs = int((allrows["in_corpus"] & allrows["is_zero_sugar"]).sum())
    allrows["corpus_note"] = (
        f"D-018/D-019 build {datetime.now():%Y-%m-%d}: curated Zero Sugar (researcher-verified, "
        f"most readily visible Zero Sugar Reels on 13 pages - not a census) + screener-found "
        f"Zero Sugar + random regular fill (seed {SEED}, vertical, read >=7 d after posting). "
        f"Zero Sugar is {n_zs}/{int(allrows['in_corpus'].sum())} of the corpus - "
        f"OVER-REPRESENTED BY DESIGN; corpus averages are not population estimates.")

    # Re-apply logged 7-day refreshes (2b.7, src/collect/refresh_metrics.py) so a rebuild
    # keeps the mature readings instead of reverting to the too-young first reads.
    allrows = apply_refreshes(allrows)

    sel = allrows[allrows["in_corpus"]]
    print(f"\n{'=' * 64}\nINSTAGRAM CORPUS  (target {TARGET})")
    print(f"  selected                      : {len(sel)}")
    print(f"  by reason                     : {sel['corpus_reason'].value_counts().to_dict()}")
    print(f"  Zero Sugar                    : {n_zs}")
    print(f"  metrics maturity              : {sel['metrics_maturity'].value_counts().to_dict()}")
    young = sel[sel["metrics_maturity"] == "too_young_refresh"]
    if len(young):
        print(f"  refresh these on/after        : {dict(zip(young['shortcode'], young['refresh_after']))}")
    conflicts = sel[sel["source_basis"].astype(str).str.contains("CONFLICT")]
    if len(conflicts):
        print(f"  ! page conflicts              : {conflicts['shortcode'].tolist()}")
    pend = sel[sel["like_count"].isna()]
    print(f"  likes missing (null)          : {len(pend)}  {sorted(pend['shortcode'])}")
    unknown_owner = sel[sel["owner_username"].isna()]
    print(f"  owner unknown                 : {len(unknown_owner)}  {sorted(unknown_owner['shortcode'])}")
    if "label_flag" in sel.columns:
        fl = sel[sel["label_flag"].notna()]
        print(f"  row notes (resolved flags)    : {dict(zip(fl['shortcode'], fl['label_flag'].str[:40]))}")
    print(f"  followers missing             : {int(sel['owner_followers'].isna().sum())}"
          f"  (owners: {sorted(sel.loc[sel['owner_followers'].isna(), 'owner_username'].dropna().unique())})")
    print(f"  regions                       : {sel['region'].value_counts(dropna=False).to_dict()}")
    cz = cur[cur["in_corpus"] & cur["text_variant"].notna() & (cur["fetch_status"] == "ok")]
    print(f"\n  text screener on researcher-verified Zero Sugar (n={len(cz)}): "
          f"caught {int(cz['text_is_zero_sugar'].sum())} "
          f"({cz['text_is_zero_sugar'].mean():.0%}) | tags {cz['text_variant'].value_counts().to_dict()}")
    if len(sel) < TARGET:
        print(f"  ! SHORT OF TARGET by {TARGET - len(sel)}")

    if not check:
        if OUT.exists():
            backup = OUT.with_name(f"instagram_corpus_before_D018_{datetime.now():%Y%m%d}.parquet")
            if not backup.exists():
                shutil.copy2(OUT, backup)
                print(f"\n  previous corpus kept -> {backup.name}")
        from src.screen.zero_sugar_labels import annotate  # D-029 provenance survives a rebuild
        allrows = annotate(allrows, "instagram")
        allrows.to_parquet(OUT, index=False)
        print(f"  written -> {OUT}  (all rows kept; filter on in_corpus)")
    return allrows


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the Instagram corpus (D-018, D-019).")
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    build(check=args.check)


if __name__ == "__main__":
    main()

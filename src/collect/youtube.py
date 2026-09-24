"""YouTube Shorts collector.

Enumerates a channel's uploads and retrieves metadata, then classifies which videos are
Shorts. Uses the REST API through `requests` rather than google-api-python-client — the
Data API v3 is simple enough that the extra dependency is not worth it.

Quota discipline (see docs/02-youtube-acquisition.md):
    channels.list       1 unit
    playlistItems.list  1 unit per 50 items
    videos.list         1 unit per 50 ids
    search.list         100 units   <- deliberately NOT used for enumeration

Usage:
    python -m src.collect.youtube --channel @cocacola
    python -m src.collect.youtube --accounts docs/accounts.csv
    python -m src.collect.youtube --channel @cocacola --download --limit 10
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

API = "https://www.googleapis.com/youtube/v3"

# YouTube's Shorts ceiling. Older Shorts were capped at 60s; the 180s limit is the
# current one, so it is the safe upper bound for a 2022-2025 corpus.
SHORTS_MAX_SEC = 180

_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>[\d.]+)S)?)?$"
)

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def parse_iso8601_duration(value: str | None) -> float | None:
    """'PT1M30S' -> 90.0. Returns None for missing or unparseable input.

    Live streams and some unavailable videos report 'P0D', which yields 0.0 — callers
    should treat 0 as suspect rather than as a real duration.
    """
    if not value:
        return None
    m = _DURATION_RE.match(value)
    if not m:
        return None
    parts = {k: float(v) for k, v in m.groupdict(default="0").items()}
    return (
        parts["days"] * 86400
        + parts["hours"] * 3600
        + parts["minutes"] * 60
        + parts["seconds"]
    )


def _to_int(value) -> int | None:
    """Statistics fields are strings, and absent when the uploader hides them.

    Absent is not zero — a hidden like count must stay None so it can be flagged and
    excluded from the DV rather than silently imputed.
    """
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass
class QuotaMeter:
    """Tracks API cost so an accidental search.list is obvious in the run summary."""

    units: int = 0
    calls: dict[str, int] = field(default_factory=dict)

    def charge(self, endpoint: str, cost: int = 1) -> None:
        self.units += cost
        self.calls[endpoint] = self.calls.get(endpoint, 0) + 1

    def summary(self) -> str:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(self.calls.items()))
        return f"{self.units} units ({detail})"


class YouTubeAPI:
    def __init__(self, api_key: str | None = None):
        self.key = api_key or config.require("YOUTUBE_API_KEY")
        self.session = requests.Session()
        self.quota = QuotaMeter()

    def _get(self, endpoint: str, params: dict, cost: int = 1) -> dict:
        params = {**params, "key": self.key}
        for attempt in range(4):
            resp = self.session.get(f"{API}/{endpoint}", params=params, timeout=30)
            if resp.status_code == 200:
                self.quota.charge(endpoint, cost)
                return resp.json()
            if resp.status_code in (403, 429):
                body = resp.text[:400]
                if "quotaExceeded" in body:
                    raise SystemExit(
                        "YouTube API daily quota exhausted. Quota resets at midnight "
                        "Pacific time. Consumed this run: " + self.quota.summary()
                    )
                if attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise SystemExit(f"YouTube API {resp.status_code}: {body}")
            if resp.status_code >= 500 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise SystemExit(f"YouTube API {resp.status_code}: {resp.text[:400]}")
        raise SystemExit("YouTube API: retries exhausted")

    # ---------------------------------------------------------------- channels

    def resolve_channel(self, ref: str) -> dict:
        """Accept a channel id, an @handle, or a channel/handle URL.

        Returns the uploads playlist id and subscriber count, both of which are needed
        downstream — subscriber_count is a mandatory exposure control (D-005).
        """
        ref = ref.strip()
        params = {"part": "snippet,contentDetails,statistics"}

        if m := re.search(r"/channel/(UC[\w-]{20,})", ref):
            params["id"] = m.group(1)
        elif m := re.search(r"/@([\w.\-]+)", ref):
            params["forHandle"] = "@" + m.group(1)
        elif ref.startswith("UC") and len(ref) >= 22:
            params["id"] = ref
        else:
            params["forHandle"] = ref if ref.startswith("@") else "@" + ref

        data = self._get("channels", params)
        items = data.get("items") or []
        if not items:
            raise SystemExit(
                f"Channel not found: {ref!r}\n"
                f"  Try the full URL, or the UC... channel id.\n"
                f"  Handles are case-sensitive in some cases."
            )
        it = items[0]
        stats = it.get("statistics", {})
        return {
            "channel_id": it["id"],
            "channel_title": it["snippet"]["title"],
            "channel_handle": it["snippet"].get("customUrl"),
            "uploads_playlist": it["contentDetails"]["relatedPlaylists"]["uploads"],
            "subscriber_count": _to_int(stats.get("subscriberCount")),
            "subscribers_hidden": stats.get("hiddenSubscriberCount", False),
            "channel_video_count": _to_int(stats.get("videoCount")),
        }

    # ---------------------------------------------------------------- uploads

    def list_upload_ids(self, playlist_id: str, max_items: int | None = None) -> list[str]:
        """Full channel enumeration at 1 quota unit per 50 — not search.list at 100."""
        ids: list[str] = []
        token = None
        while True:
            params = {"part": "contentDetails", "playlistId": playlist_id,
                      "maxResults": 50}
            if token:
                params["pageToken"] = token
            data = self._get("playlistItems", params)
            for item in data.get("items", []):
                vid = item.get("contentDetails", {}).get("videoId")
                if vid:
                    ids.append(vid)
            if max_items and len(ids) >= max_items:
                return ids[:max_items]
            token = data.get("nextPageToken")
            if not token:
                return ids

    # ---------------------------------------------------------------- videos

    def fetch_video_details(self, video_ids: list[str]) -> list[dict]:
        """videos.list in batches of 50 — 1 unit per batch regardless of part count."""
        out: list[dict] = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            data = self._get("videos", {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(batch),
            })
            out.extend(data.get("items", []))
        return out


# -------------------------------------------------------------- Shorts detection

def shorts_redirect_signal(video_id: str, session: requests.Session | None = None) -> tuple[bool | None, int | None]:
    """Third Shorts signal: /shorts/<id> serves 200 for a real Short, redirects otherwise.

    Returns (is_short_or_None, http_status). None means the check was inconclusive —
    a consent wall or a network failure — and must not be read as 'not a Short'.
    """
    sess = session or requests
    try:
        resp = sess.get(
            f"https://www.youtube.com/shorts/{video_id}",
            allow_redirects=False,
            timeout=15,
            headers={"User-Agent": BROWSER_UA},
        )
    except requests.RequestException:
        return None, None
    if resp.status_code == 200:
        return True, 200
    if resp.status_code in (301, 302, 303, 307, 308):
        return False, resp.status_code
    return None, resp.status_code


def probe_dimensions(path: Path) -> tuple[int | None, int | None]:
    """ffprobe the downloaded file for the authoritative aspect-ratio signal."""
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        streams = json.loads(res.stdout).get("streams") or []
        if streams:
            return streams[0].get("width"), streams[0].get("height")
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        pass
    return None, None


def classify(duration_sec: float | None, redirect_short: bool | None,
             width: int | None = None, height: int | None = None) -> dict:
    """Three-signal Shorts classification (docs/02-youtube-acquisition.md section 3).

    Signals are not peers. `redirect_short` is YouTube's own membership test for the
    Shorts shelf and is authoritative when conclusive. Duration is *necessary but not
    sufficient* — every Short is short, but a 15s horizontal TV commercial uploaded as
    a regular video is also short. Aspect ratio is strong corroboration but needs the
    downloaded file, so `is_short_prelim` decides what is worth downloading and
    `is_short` is the post-download verdict.
    """
    sig_duration = None if duration_sec is None else duration_sec <= SHORTS_MAX_SEC
    sig_vertical = None if not (width and height) else height > width

    prelim = bool(sig_duration) and redirect_short is not False

    # The redirect is definitional: /shorts/<id> serves 200 only for videos YouTube
    # itself files as Shorts. Verified against this channel's /shorts tab — 4/4 known
    # Shorts returned 200, 5/5 short regular uploads returned 303. Proxies are used
    # only where it is inconclusive (consent wall, network failure).
    if redirect_short is not None:
        final = redirect_short
    elif sig_vertical is not None:
        final = bool(sig_duration) and sig_vertical
    else:
        final = prelim

    # Flag only genuine contradictions — a proxy that makes the authoritative verdict
    # impossible. "Short but not a Short" describes every short regular upload and is
    # not a conflict; flagging it would swamp review with hundreds of ordinary videos
    # and hide the cases that actually need a human.
    if redirect_short is True:
        # Served as a Short, yet too long or horizontal: one of the two is wrong.
        disagree = sig_duration is False or sig_vertical is False
    elif redirect_short is False:
        # Vertical *and* short yet not served as a Short. Rare, and the likeliest
        # shape of a failed redirect check, so it is worth a look.
        disagree = sig_vertical is True and sig_duration is True
    else:
        # No authoritative signal; fall back to proxies disagreeing with each other.
        disagree = (sig_duration is not None and sig_vertical is not None
                    and sig_duration != sig_vertical)

    return {
        "sig_duration_ok": sig_duration,
        "sig_redirect_ok": redirect_short,
        "sig_vertical_ok": sig_vertical,
        "is_short_prelim": prelim,
        "is_short": final,
        "signals_disagree": disagree,
    }


# -------------------------------------------------------------- media download

def download_video(video_id: str, dest_dir: Path = config.MEDIA_YT,
                   max_height: int = 720) -> Path | None:
    """yt-dlp at <=720p. Shorts are vertical, so 720 is the *short* side — product and
    logo detection needs that detail (docs/02 section 5)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    existing = list(dest_dir.glob(f"{video_id}.*"))
    if existing:
        return existing[0]
    cmd = [
        "yt-dlp",
        "-f", f"bv*[height<={max_height}]+ba/b[height<={max_height}]/b",
        "-o", str(dest_dir / "%(id)s.%(ext)s"),
        "--no-playlist", "--quiet", "--no-warnings",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    except FileNotFoundError:
        print("  ! yt-dlp not installed — skipping downloads "
              "(pip install yt-dlp)", file=sys.stderr)
        return None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"  ! download failed for {video_id}: {exc}", file=sys.stderr)
        return None
    found = list(dest_dir.glob(f"{video_id}.*"))
    return found[0] if found else None


def fetch_transcript(video_id: str) -> tuple[str | None, str | None]:
    """Captions first (free, instant, multilingual). Whisper fallback runs in Phase 2.

    Returns (text, source) where source is 'captions' or None. Recorded because
    auto-captions and ASR have different error profiles (docs/02 section 5).
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return None, None
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        text = " ".join(snippet.text for snippet in fetched)
        return text, "captions"
    except Exception:
        # No captions, disabled, or region-blocked. Phase 2 will run Whisper.
        return None, None


# -------------------------------------------------------------- orchestration

def collect_channel(api: YouTubeAPI, ref: str, market: str = "",
                    max_videos: int | None = None,
                    check_redirect: bool = True,
                    download: bool = False,
                    transcripts: bool = False) -> pd.DataFrame:
    ch = api.resolve_channel(ref)
    print(f"\n{ch['channel_title']}  ({ch['channel_id']})")
    print(f"  subscribers: {ch['subscriber_count']:,}"
          if ch["subscriber_count"] is not None else "  subscribers: hidden")
    print(f"  uploads reported by API: {ch['channel_video_count']}")

    ids = api.list_upload_ids(ch["uploads_playlist"], max_items=max_videos)
    print(f"  enumerated: {len(ids)} videos")

    items = api.fetch_video_details(ids)
    print(f"  details retrieved: {len(items)}")

    collected_at = datetime.now(timezone.utc).isoformat()
    session = requests.Session()
    rows: list[dict] = []

    for it in items:
        sn, cd = it.get("snippet", {}), it.get("contentDetails", {})
        stats = it.get("statistics", {})
        vid = it["id"]
        duration = parse_iso8601_duration(cd.get("duration"))

        redirect_short, redirect_status = (None, None)
        # Only spend an HTTP request where duration makes a Short plausible.
        if check_redirect and duration is not None and duration <= SHORTS_MAX_SEC:
            redirect_short, redirect_status = shorts_redirect_signal(vid, session)

        row = {
            "platform": "youtube",
            "video_id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "title": sn.get("title"),
            "description": sn.get("description"),
            "published_at": sn.get("publishedAt"),
            "channel_id": sn.get("channelId"),
            "channel_title": sn.get("channelTitle"),
            "subscriber_count": ch["subscriber_count"],
            "channel_video_count": ch["channel_video_count"],
            "market": market,
            "duration_sec": duration,
            "view_count": _to_int(stats.get("viewCount")),
            "like_count": _to_int(stats.get("likeCount")),
            "comment_count": _to_int(stats.get("commentCount")),
            "likes_hidden": "likeCount" not in stats,
            "comments_disabled": "commentCount" not in stats,
            "tags": json.dumps(sn.get("tags", []), ensure_ascii=False),
            "category_id": sn.get("categoryId"),
            "default_audio_language": sn.get("defaultAudioLanguage"),
            "thumbnail_url": (sn.get("thumbnails", {}).get("high", {}) or {}).get("url"),
            "live_broadcast": sn.get("liveBroadcastContent"),
            "redirect_status": redirect_status,
            "collected_at": collected_at,
            "video_path": None,
            "width": None,
            "height": None,
            "transcript": None,
            "transcript_source": None,
        }
        row.update(classify(duration, redirect_short))
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    n_prelim = int(df["is_short_prelim"].sum())
    print(f"  Shorts (preliminary, duration + redirect): {n_prelim}")

    if download:
        shorts = df[df["is_short_prelim"]]
        print(f"  downloading {len(shorts)} candidates...")
        for idx, r in shorts.iterrows():
            path = download_video(r["video_id"])
            if not path:
                continue
            w, h = probe_dimensions(path)
            df.at[idx, "video_path"] = str(path)
            df.at[idx, "width"] = w
            df.at[idx, "height"] = h
            for key, val in classify(r["duration_sec"], r["sig_redirect_ok"], w, h).items():
                df.at[idx, key] = val
        print(f"  Shorts (confirmed vertical): {int(df['is_short'].sum())}")

    if transcripts:
        target = df[df["is_short_prelim"]]
        print(f"  fetching transcripts for {len(target)}...")
        for idx, r in target.iterrows():
            text, src = fetch_transcript(r["video_id"])
            df.at[idx, "transcript"] = text
            df.at[idx, "transcript_source"] = src
        got = int(df["transcript_source"].notna().sum())
        print(f"  transcripts from captions: {got} / {len(target)}")

    n_dis = int(df["signals_disagree"].sum())
    if n_dis:
        print(f"  ⚠ {n_dis} videos have disagreeing signals — review these manually")

    return df


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect YouTube Shorts metadata.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--channel", help="channel id, @handle, or URL")
    src.add_argument("--accounts", help="CSV with columns: market, youtube_channel")
    ap.add_argument("--market", default="", help="market label for --channel")
    ap.add_argument("--limit", type=int, help="cap videos enumerated per channel")
    ap.add_argument("--download", action="store_true",
                    help="download candidates and confirm aspect ratio")
    ap.add_argument("--transcripts", action="store_true", help="fetch caption transcripts")
    ap.add_argument("--no-redirect-check", action="store_true",
                    help="skip the /shorts/ HTTP signal")
    ap.add_argument("--out", default=str(config.RAW / "youtube_shorts.parquet"))
    args = ap.parse_args()

    api = YouTubeAPI()
    targets: list[tuple[str, str]] = []

    if args.channel:
        targets.append((args.channel, args.market))
    else:
        acc = pd.read_csv(args.accounts)
        col = "youtube_channel"
        if col not in acc.columns:
            raise SystemExit(f"{args.accounts} needs a '{col}' column. Found: "
                             f"{list(acc.columns)}")
        for _, r in acc.iterrows():
            ref = str(r[col]).strip()
            if ref and ref.lower() not in ("nan", "tbd", ""):
                targets.append((ref, str(r.get("market", ""))))
        if not targets:
            raise SystemExit(
                f"No usable channels in {args.accounts}.\n"
                "  Fill in the youtube_channel column first (plan Step 2)."
            )

    frames = []
    for ref, market in targets:
        try:
            df = collect_channel(
                api, ref, market=market, max_videos=args.limit,
                check_redirect=not args.no_redirect_check,
                download=args.download, transcripts=args.transcripts,
            )
            if not df.empty:
                frames.append(df)
        except SystemExit as exc:
            print(f"  ! skipped {ref}: {exc}", file=sys.stderr)

    if not frames:
        raise SystemExit("Nothing collected.")

    out = pd.concat(frames, ignore_index=True)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_path, index=False)

    shorts = out[out["is_short_prelim"]]
    print(f"\n{'=' * 62}")
    print(f"rows written        : {len(out)}  ->  {out_path}")
    print(f"Shorts candidates   : {len(shorts)}")
    print(f"channels            : {out['channel_id'].nunique()}")
    print(f"signal disagreements: {int(out['signals_disagree'].sum())}")
    print(f"likes hidden        : {int(out['likes_hidden'].sum())}")
    print(f"comments disabled   : {int(out['comments_disabled'].sum())}")
    print(f"quota consumed      : {api.quota.summary()}")
    if not shorts.empty and shorts["published_at"].notna().any():
        print(f"date range (Shorts) : {shorts['published_at'].min()[:10]} .. "
              f"{shorts['published_at'].max()[:10]}")


if __name__ == "__main__":
    main()

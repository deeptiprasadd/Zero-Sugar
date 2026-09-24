"""Instagram Reels collector (Apify route — docs/01-instagram-acquisition.md Route C).

Enumerates Reels for a list of public accounts, normalises the result into the field set
in docs/01 section 3, downloads the video files, and writes a parquet.

Talks to Apify's REST API through `requests` rather than `apify-client`, matching the
choice made in youtube.py: the two endpoints needed here are trivial, and one less
dependency is one less thing to pin.

Two design points that are not obvious:

1.  **Raw JSON is written before anything is parsed.** Actor schemas are author-specific
    and change without notice, and a deleted Reel is unrecoverable. The raw file is the
    record of what was actually returned; the parquet is an interpretation of it.

2.  **Field names are not standardised across actors**, so every field is resolved
    through a candidate list rather than a fixed key. `--dry-run` re-parses a saved raw
    file with no API call, which is how you adapt to a new actor's schema for free.

Usage:
    # what would run, without spending credits
    python -m src.collect.instagram --plan

    # 10-Reel pilot first, as docs/01 insists
    python -m src.collect.instagram --limit 10

    # full run + video download
    python -m src.collect.instagram --limit 60 --download

    # re-parse a saved raw file after switching actor (no API call, no cost)
    python -m src.collect.instagram --dry-run data/raw/apify_runs/<file>.json

    # cross-source agreement check (docs/01 section 4)
    python -m src.collect.instagram --limit 50 --compare-actor <author>/<actor>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

APIFY = "https://api.apify.com/v2"

# Default actor. Pin the build at run time with --actor-build (docs/01 section 6).
DEFAULT_ACTOR = "apify/instagram-reel-scraper"

RAW_RUNS = config.RAW / "apify_runs"

# Terminal states in the Apify run lifecycle.
_TERMINAL = {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}


# ------------------------------------------------------------------ field resolution

def _dig(item: dict, path: str):
    """Resolve a dotted path, tolerating missing links and list-valued nodes."""
    cur = item
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[0] if cur else None
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _first(item: dict, *paths, default=None):
    """First non-empty value among candidate paths.

    Zero is a legitimate like count, so only None and empty string/list are skipped.
    """
    for p in paths:
        val = _dig(item, p)
        if val is not None and val != "" and val != []:
            return val
    return default


def _to_int(val) -> int | None:
    """None-preserving int coercion. A hidden count must not become 0 (D-005)."""
    if val is None or isinstance(val, bool):
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _to_iso(val) -> str | None:
    """Actors return ISO strings or unix epochs; normalise to UTC ISO-8601."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(float(val), tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    return str(val)


def _as_list(val) -> list:
    if val is None:
        return []
    return val if isinstance(val, list) else [val]


# Path segments that are route markers, not usernames.
_NOT_A_HANDLE = {"reels", "reel", "p", "tv", "stories", "explore", "www.instagram.com"}


def _handle_from_url(url: str | None) -> str | None:
    """First real path segment of an Instagram URL.

    Handles `instagram.com/cocacola`, `.../cocacola/reels/`, and bare `cocacola`.
    Uses urlparse rather than splitting on "/" so the scheme cannot be mistaken for a
    path segment.
    """
    if not url:
        return None
    text = str(url).strip()
    parsed = urlparse(text if "//" in text else "//" + text)
    segments = [s for s in parsed.path.split("/") if s.strip()]

    if not segments:
        # A bare handle parses entirely into netloc, e.g. "cocacola".
        host = parsed.netloc.strip().lstrip("@")
        return host if host and "." not in host else None

    first = segments[0].strip().lstrip("@")
    # Only the first segment can be a handle. If it is a route marker the URL points at
    # a post, and what follows is a shortcode — returning that would silently invent an
    # account that does not exist.
    if not first or first.lower() in _NOT_A_HANDLE:
        return None
    return first


def normalize_reel(item: dict, market: str = "", sampling_tier: int | None = None) -> dict:
    """Map one actor record onto the docs/01 section 3 field set.

    Candidate keys cover apify/instagram-reel-scraper, apify/instagram-scraper and the
    common third-party variants. An unrecognised actor leaves fields null rather than
    crashing — parse_items() reports that, and the fix is to extend the lists here.
    """
    # `id` is a last resort: on this actor it holds the numeric *media* id, and on an
    # error record it holds the numeric *profile* id. An all-digit value is therefore
    # never a shortcode — accepting one would mint a phantom Reel from an error.
    shortcode = _first(item, "shortCode", "shortcode", "code")
    if not shortcode:
        candidate = _first(item, "id")
        if candidate is not None and not str(candidate).isdigit():
            shortcode = candidate
    permalink = _first(item, "url", "permalink", "postUrl")
    if not permalink and shortcode:
        permalink = f"https://www.instagram.com/reel/{shortcode}/"

    # Which requested account produced this row. On an Instagram collaborator post the
    # Reel appears on both profiles and the actor reports the *co-poster* as owner, so
    # owner_username alone cannot be mapped back to a market. `inputUrl` can.
    owner = _first(item, "ownerUsername", "username", "owner.username", "user.username")
    source_handle = _handle_from_url(_first(item, "inputUrl"))
    is_collab = bool(owner and source_handle and owner != source_handle)
    # Tier 1 = brand account, tier 2 = sponsored/collab creator (docs/01 section 5, D-009).
    tier = sampling_tier if sampling_tier is not None else (2 if is_collab else 1)

    caption = _first(item, "caption", "text", "title",
                     "edge_media_to_caption.edges.node.text")

    # Audio: original vs licensed is the strongest single predictor in the brand-TikTok
    # literature (docs/01 section 3), so it is captured even when nested awkwardly.
    audio_name = _first(item, "musicInfo.song_name", "musicInfo.title", "audio.title",
                        "musicCanonicalId", "audioName")
    audio_artist = _first(item, "musicInfo.artist_name", "audio.artist", "audioArtist")
    audio_original = _first(item, "musicInfo.uses_original_audio", "audio.isOriginal",
                            "isOriginalAudio")

    return {
        "platform": "instagram",
        "shortcode": shortcode,
        "permalink": permalink,
        "owner_username": owner,
        "source_handle": source_handle,
        "is_collab": is_collab,
        # Usernames can be changed by their owner; the numeric id cannot. Group by this.
        "owner_id": _first(item, "ownerId", "owner.id", "user.pk"),
        # Most Reel actors omit this entirely — it is filled by a separate profile
        # lookup in fetch_follower_counts(). Mandatory exposure control (D-005).
        "owner_followers": _to_int(_first(item, "ownerFollowersCount", "followersCount",
                                          "owner.followersCount", "user.followerCount")),
        "caption": caption,
        "hashtags": json.dumps(_as_list(_first(item, "hashtags")), ensure_ascii=False),
        "mentions": json.dumps(_as_list(_first(item, "mentions")), ensure_ascii=False),
        "timestamp": _to_iso(_first(item, "timestamp", "takenAt", "taken_at_timestamp",
                                    "takenAtTimestamp")),
        "like_count": _to_int(_first(item, "likesCount", "likeCount", "likes",
                                     "edge_liked_by.count")),
        "comments_count": _to_int(_first(item, "commentsCount", "commentCount",
                                         "comments", "edge_media_to_comment.count")),
        # Recorded but excluded from the cross-platform DV: Meta reports combined IG+FB
        # views for crossposted video, so it is not comparable (docs/01 section 1).
        "view_count": _to_int(_first(item, "videoViewCount", "viewsCount",
                                     "videoPlayCount", "playCount", "videoPlaysCount")),
        "duration_sec": _first(item, "videoDuration", "duration",
                               "videoDurationSeconds"),
        "audio_name": audio_name,
        "audio_artist": audio_artist,
        "audio_is_original": audio_original,
        "audio_url": _first(item, "audioUrl"),
        "is_sponsored": _first(item, "isSponsored", "sponsored", "paidPartnership",
                               default=False),
        # A pinned Reel sits at the top of the profile indefinitely and accumulates
        # engagement no ordinary post can reach. It is a confound for any engagement
        # model and must be available as a control, not silently averaged in.
        "is_pinned": _first(item, "isPinned", default=False),
        # Parallel to YouTube's comments_disabled: without it, a genuine 0 and a
        # switched-off comment section look identical (D-005).
        "comments_disabled": _first(item, "isCommentsDisabled", default=False),
        "media_product_type": _first(item, "productType", "mediaType", "type",
                                     "media_product_type"),
        "video_url": _first(item, "videoUrl", "video_url", "videoUrlBackup"),
        "alt_text": _first(item, "alt"),
        # Dimensions the actor reports, kept separate from the ffprobe columns so the
        # provenance of each is unambiguous. These arrive without a download, so aspect
        # ratio is available before deciding what to fetch.
        "actor_width": _to_int(_first(item, "dimensionsWidth", "originalWidth")),
        "actor_height": _to_int(_first(item, "dimensionsHeight", "originalHeight")),
        "market": market,
        "sampling_tier": tier,
        "video_path": None,
        "width": None,
        "height": None,
        "probed_duration_sec": None,
    }


# ------------------------------------------------------------------ apify transport

class Apify:
    """Minimal Apify REST client: start a run, wait for it, read its dataset."""

    def __init__(self, token: str | None = None, timeout: int = 30):
        self.token = token or config.require("APIFY_TOKEN")
        self.timeout = timeout
        self.session = requests.Session()

    def _url(self, path: str) -> str:
        return f"{APIFY}/{path}"

    def start_run(self, actor: str, run_input: dict, build: str | None = None) -> dict:
        """Actor ids carry a slash in the UI; the API wants it as a tilde."""
        actor_path = actor.replace("/", "~")
        params = {"token": self.token}
        if build:
            params["build"] = build
        resp = self.session.post(
            self._url(f"acts/{actor_path}/runs"),
            params=params, json=run_input, timeout=self.timeout,
        )
        if resp.status_code == 404:
            raise SystemExit(
                f"Actor '{actor}' not found.\n"
                "  Check the id on apify.com/store — it is '<author>/<name>'.\n"
                "  Some actors must be added to your account before first use."
            )
        if resp.status_code in (401, 403):
            raise SystemExit(
                "Apify rejected the token (401/403).\n"
                "  Check APIFY_TOKEN in .env — apify.com -> Settings -> Integrations."
            )
        resp.raise_for_status()
        return resp.json()["data"]

    def wait(self, run_id: str, poll: int = 5, max_wait: int = 1800) -> dict:
        """Poll to a terminal state. Actors queue before they start, so this is not
        instant even for tiny inputs."""
        waited = 0
        last = None
        while waited < max_wait:
            resp = self.session.get(self._url(f"actor-runs/{run_id}"),
                                    params={"token": self.token}, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()["data"]
            status = data.get("status")
            if status != last:
                print(f"    run {run_id}: {status}")
                last = status
            if status in _TERMINAL:
                return data
            time.sleep(poll)
            waited += poll
        raise SystemExit(
            f"Apify run {run_id} still running after {max_wait}s.\n"
            "  It is not lost — let it finish at console.apify.com/actors/runs, download\n"
            "  the dataset as JSON, then re-parse locally with --dry-run."
        )

    def dataset_items(self, dataset_id: str) -> list[dict]:
        resp = self.session.get(self._url(f"datasets/{dataset_id}/items"),
                                params={"token": self.token, "format": "json"},
                                timeout=120)
        resp.raise_for_status()
        return resp.json()


PROFILE_ACTOR = "apify/instagram-profile-scraper"


def fetch_follower_counts(api: "Apify", handles: list[str],
                          actor: str = PROFILE_ACTOR) -> dict[str, int]:
    """Follower count per account, from a profile actor.

    Reel actors generally return per-post data only — `apify/instagram-reel-scraper`
    carries `ownerUsername` and `ownerId` but no follower count. Since follower count is
    an account-level property, one profile lookup per handle is enough for the whole
    corpus, which is far cheaper than trying to source it per Reel.

    D-005 makes this a mandatory exposure control: engagement counts are meaningless
    without the audience size they were drawn from. A failure here is reported loudly
    rather than passed through as nulls.
    """
    if not handles:
        return {}
    print(f"  follower counts via {actor} ({len(handles)} accounts)...")
    try:
        run = api.start_run(actor, {"usernames": handles})
        run = api.wait(run["id"])
        if run.get("status") != "SUCCEEDED":
            print(f"  ! profile actor ended {run.get('status')} - followers left null")
            return {}
        items = api.dataset_items(run["defaultDatasetId"])
    except SystemExit as exc:
        print(f"  ! profile lookup failed: {exc}")
        return {}

    save_raw(items, actor, run["id"])
    out: dict[str, int] = {}
    for it in items:
        user = _first(it, "username", "ownerUsername", "user.username")
        n = _to_int(_first(it, "followersCount", "ownerFollowersCount",
                           "edge_followed_by.count", "follower_count"))
        if user and n is not None:
            out[str(user)] = n
    missing = [h for h in handles if h not in out]
    if missing:
        print(f"  ! no follower count for: {', '.join(missing)}")
    return out


def followers_from_saved_runs(runs_dir: Path = RAW_RUNS) -> dict[str, int]:
    """Rebuild the username -> followers map from previously saved profile-actor runs.

    Lets `--dry-run` restore the mandatory exposure control offline instead of paying to
    re-fetch numbers already on disk. Later runs win, so a re-pull refreshes the count.
    """
    out: dict[str, int] = {}
    if not runs_dir.exists():
        return out
    for path in sorted(runs_dir.glob("*profile*.json"), key=lambda p: p.stat().st_mtime):
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for it in items if isinstance(items, list) else []:
            user = _first(it, "username", "ownerUsername", "user.username")
            n = _to_int(_first(it, "followersCount", "ownerFollowersCount",
                               "edge_followed_by.count", "follower_count"))
            if user and n is not None:
                out[str(user)] = n
    return out


def save_raw(items: list[dict], actor: str, run_id: str) -> Path:
    """Write the actor output verbatim. This happens before parsing, always."""
    RAW_RUNS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = actor.replace("/", "_")
    path = RAW_RUNS / f"{safe}_{run_id}_{stamp}.json"
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ------------------------------------------------------------------ media

def download_reel(permalink: str, shortcode: str, video_url: str | None = None,
                  dest_dir: Path = config.MEDIA_IG) -> Path | None:
    """Direct CDN URL first, yt-dlp on the permalink as fallback.

    Actor-returned video URLs are signed and short-lived (docs/01 section 6), so the
    direct path only works in the same session as the metadata pull.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    existing = list(dest_dir.glob(f"{shortcode}.*"))
    if existing:
        return existing[0]

    if video_url:
        try:
            with requests.get(video_url, stream=True, timeout=120) as r:
                if r.ok and "video" in r.headers.get("Content-Type", ""):
                    out = dest_dir / f"{shortcode}.mp4"
                    with open(out, "wb") as fh:
                        for chunk in r.iter_content(1 << 16):
                            fh.write(chunk)
                    if out.stat().st_size > 1024:
                        return out
                    out.unlink(missing_ok=True)
        except requests.RequestException:
            pass  # expired signature or CDN refusal; fall through to yt-dlp

    try:
        subprocess.run(
            ["yt-dlp", "-o", str(dest_dir / f"{shortcode}.%(ext)s"),
             "--no-playlist", "--quiet", "--no-warnings", permalink],
            check=True, capture_output=True, timeout=600,
        )
    except FileNotFoundError:
        print("  ! yt-dlp not installed - pip install yt-dlp", file=sys.stderr)
        return None
    except (subprocess.SubprocessError, OSError):
        return None
    found = list(dest_dir.glob(f"{shortcode}.*"))
    return found[0] if found else None


def probe_media(path: Path) -> tuple[int | None, int | None, float | None]:
    """ffprobe for width, height and duration — authoritative over actor-reported values."""
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height:format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        data = json.loads(res.stdout)
        streams = data.get("streams") or []
        dur = data.get("format", {}).get("duration")
        w = streams[0].get("width") if streams else None
        h = streams[0].get("height") if streams else None
        return w, h, (float(dur) if dur else None)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError, ValueError):
        return None, None, None


# ------------------------------------------------------------------ orchestration

def read_accounts(path: str) -> list[tuple[str, str]]:
    """(handle, market) pairs from the sampling frame, skipping unfilled rows."""
    acc = pd.read_csv(path)
    col = "instagram_handle"
    if col not in acc.columns:
        raise SystemExit(f"{path} needs an '{col}' column. Found: {list(acc.columns)}")
    out = []
    for _, r in acc.iterrows():
        h = str(r.get(col, "")).strip().lstrip("@")
        if h and h.lower() not in ("nan", "tbd", ""):
            out.append((h, str(r.get("market", ""))))
    if not out:
        raise SystemExit(
            f"No Instagram handles in {path}.\n"
            "  Fill in the instagram_handle column first (plan Step 2)."
        )
    return out


def build_run_input(handles: list[str], limit: int) -> dict:
    """Input keys differ by actor; these cover the common Instagram actors.

    Extra keys are ignored by actors that do not declare them, so sending several is
    safer than guessing which one this actor reads.
    """
    return {
        "username": handles,
        "usernames": handles,
        "directUrls": [f"https://www.instagram.com/{h}/reels/" for h in handles],
        "resultsLimit": limit,
        "resultsType": "posts",
    }


def parse_items(items: list[dict],
                market_of: dict[str, str] | None = None) -> pd.DataFrame:
    """Normalise, stamp, and drop non-Reels.

    Separated from collect() so --dry-run can re-run exactly this step against a saved
    raw file, which is how a new actor's schema gets mapped without spending credits.
    """
    market_of = market_of or {}
    collected_at = datetime.now(timezone.utc).isoformat()

    # Actors report an unreadable account as a record with an `error` field rather than
    # by failing the run. These are not Reels and must never reach the corpus — but they
    # are the only signal that an account yielded nothing, so they are reported, not
    # silently discarded. A market can disappear this way without anything looking wrong.
    errors = [it for it in items if it.get("error") or it.get("isRestrictedProfile")]
    if errors:
        print(f"  ! {len(errors)} account(s) returned an error instead of Reels:")
        for it in errors:
            who = _first(it, "username", "ownerUsername") or _handle_from_url(
                _first(it, "inputUrl")) or "unknown"
            why = it.get("error") or "restricted profile"
            extra = it.get("restrictionReason")
            print(f"      @{who}: {why}" + (f" - {extra}" if extra else ""))
        items = [it for it in items if not (it.get("error") or it.get("isRestrictedProfile"))]

    rows = []
    for it in items:
        # Market comes from the requested account, not the owner: on a collaborator post
        # the owner is the creator, who has no market of their own in the frame.
        src = _handle_from_url(_first(it, "inputUrl")) or ""
        owner = _first(it, "ownerUsername", "username", "owner.username") or ""
        row = normalize_reel(it, market=market_of.get(src) or market_of.get(owner, ""))
        row["collected_at"] = collected_at
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    before = len(df)
    df = df[df["shortcode"].notna()].copy()
    if len(df) < before:
        print(f"  ! dropped {before - len(df)} records with no shortcode "
              f"(actor schema mismatch - inspect the raw JSON)")

    # Keep Reels/video; keep unknowns rather than guess them away.
    #
    # Nulls are tested before any string conversion. Stringifying first is version-
    # dependent — pandas 3.0 renders a missing value as "<NA>", older versions as
    # "None"/"nan" — so a keep-list of strings silently drops every row from any actor
    # that omits this field. Test the null mask directly and the behaviour is stable.
    if "media_product_type" in df.columns:
        kind = df["media_product_type"]
        allowed = {"reels", "reel", "clips", "video"}
        as_text = kind.astype("string").str.strip().str.lower()
        keep = kind.isna() | as_text.isin(allowed) | (as_text == "")
        keep = keep.fillna(True)
        dropped = int((~keep).sum())
        if dropped:
            print(f"  filtered out {dropped} non-Reel records")
        df = df[keep].copy()

    df = df.drop_duplicates(subset="shortcode").reset_index(drop=True)

    n_null = int(df["like_count"].isna().sum())
    if n_null:
        print(f"  ! {n_null}/{len(df)} records have no like_count - likely an unmapped "
              f"field name. Inspect the raw JSON and extend normalize_reel().")
    return df


def collect(actor: str, handles: list[tuple[str, str]], limit: int,
            build: str | None = None, download: bool = False,
            token: str | None = None,
            followers: bool = True) -> tuple[pd.DataFrame, Path | None]:
    api = Apify(token)
    names = [h for h, _ in handles]
    market_of = {h: m for h, m in handles}

    print(f"\nactor  : {actor}" + (f"  (build {build})" if build else ""))
    print(f"handles: {', '.join(names)}")
    print(f"limit  : {limit} per account")

    run = api.start_run(actor, build_run_input(names, limit), build=build)
    run = api.wait(run["id"])
    if run.get("status") != "SUCCEEDED":
        raise SystemExit(f"Apify run ended {run.get('status')} - see "
                         f"https://console.apify.com/actors/runs/{run['id']}")

    items = api.dataset_items(run["defaultDatasetId"])
    raw_path = save_raw(items, actor, run["id"])
    print(f"  raw JSON saved: {raw_path}")
    print(f"  records returned: {len(items)}")

    df = parse_items(items, market_of)
    if df.empty:
        return df, raw_path

    # Fill the exposure control if the Reel actor did not supply it (most do not).
    if followers and df["owner_followers"].isna().any():
        counts = fetch_follower_counts(api, sorted(df["owner_username"].dropna().unique()))
        if counts:
            filled = df["owner_username"].map(counts)
            df["owner_followers"] = df["owner_followers"].fillna(filled)
            got = int(df["owner_followers"].notna().sum())
            print(f"  followers resolved: {got} / {len(df)} rows")

    if download:
        print(f"  downloading {len(df)} videos...")
        for idx, r in df.iterrows():
            path = download_reel(r["permalink"], r["shortcode"], r["video_url"])
            if not path:
                continue
            w, h, dur = probe_media(path)
            df.at[idx, "video_path"] = str(path)
            df.at[idx, "width"] = w
            df.at[idx, "height"] = h
            df.at[idx, "probed_duration_sec"] = dur
        got = int(df["video_path"].notna().sum())
        print(f"  videos on disk: {got} / {len(df)}")

    return df, raw_path


# ------------------------------------------------------------------ validation (section 4)

def compare_sources(a: pd.DataFrame, b: pd.DataFrame,
                    name_a: str, name_b: str) -> pd.DataFrame:
    """Inter-source agreement on the same Reels (docs/01 section 4).

    Reports exact-match rate, MAD and MAPE for likes and comments. Systematic
    disagreement must be resolved before modelling, not explained away after.
    """
    j = a.merge(b, on="shortcode", suffixes=("_a", "_b"))
    print(f"\n{'=' * 62}")
    print(f"cross-source agreement: {name_a}  vs  {name_b}")
    print(f"  Reels matched on shortcode: {len(j)}")
    if j.empty:
        print("  ! no overlap - the two actors returned different Reels.")
        return pd.DataFrame()

    rows = []
    for field in ("like_count", "comments_count"):
        ca, cb = j[f"{field}_a"], j[f"{field}_b"]
        both = ca.notna() & cb.notna()
        n = int(both.sum())
        if not n:
            print(f"  {field}: no comparable pairs")
            continue
        diff = (ca[both] - cb[both]).abs()
        exact = int((diff == 0).sum())
        denom = ca[both].where(ca[both] != 0)
        mape = float((diff / denom).dropna().mean() * 100) if denom.notna().any() else float("nan")
        print(f"  {field}: n={n}  exact={exact} ({exact / n:.0%})  "
              f"MAD={diff.mean():.1f}  MAPE={mape:.2f}%")
        rows.append({"field": field, "n": n, "exact": exact,
                     "exact_rate": exact / n, "mad": float(diff.mean()), "mape": mape})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ cli

def main() -> None:
    ap = argparse.ArgumentParser(description="Collect Instagram Reels via Apify.")
    ap.add_argument("--accounts", default=str(config.ACCOUNTS_CSV),
                    help="CSV with columns: market, instagram_handle")
    ap.add_argument("--handle", action="append",
                    help="collect one handle (repeatable); overrides --accounts")
    ap.add_argument("--actor", default=DEFAULT_ACTOR, help="Apify actor id")
    ap.add_argument("--actor-build", help="pin the actor build (docs/01 section 6)")
    ap.add_argument("--compare-actor",
                    help="second actor, different author, for the section 4 agreement check")
    ap.add_argument("--limit", type=int, default=10,
                    help="Reels per account (default 10 - pilot first)")
    ap.add_argument("--download", action="store_true", help="download video files")
    ap.add_argument("--no-followers", action="store_true",
                    help="skip the profile lookup that fills owner_followers (D-005)")
    ap.add_argument("--plan", action="store_true",
                    help="show what would run, make no API call, spend nothing")
    ap.add_argument("--dry-run", metavar="RAW_JSON",
                    help="re-parse a saved raw file; no API call, no cost")
    ap.add_argument("--out", default=str(config.RAW / "instagram_reels.parquet"))
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- offline re-parse ------------------------------------------------
    if args.dry_run:
        raw = Path(args.dry_run)
        if not raw.exists():
            raise SystemExit(f"No such file: {raw}")
        items = json.loads(raw.read_text(encoding="utf-8"))
        print(f"re-parsing {len(items)} records from {raw.name}")

        # Market labels come from the frame, exactly as in a live run.
        market_of: dict[str, str] = {}
        try:
            acc = pd.read_csv(args.accounts)
            market_of = {str(r["instagram_handle"]).strip().lstrip("@"): str(r.get("market", ""))
                         for _, r in acc.iterrows()
                         if isinstance(r.get("instagram_handle"), str)}
        except (OSError, KeyError, ValueError):
            print("  ! could not read the accounts frame; markets left blank")

        df = parse_items(items, market_of)
        if df.empty:
            raise SystemExit("Nothing parsed - the actor schema is unmapped.")

        # Restore followers from saved profile runs rather than paying to re-fetch.
        saved = followers_from_saved_runs()
        if saved and df["owner_followers"].isna().any():
            df["owner_followers"] = df["owner_followers"].fillna(
                df["owner_username"].map(saved))
            print(f"  followers restored from saved runs: "
                  f"{int(df['owner_followers'].notna().sum())} / {len(df)} rows")

        df.to_parquet(out_path, index=False)
        print(f"\nrows written : {len(df)}  ->  {out_path}")
        missing_mkt = int((df["market"].fillna("") == "").sum())
        print(f"market unmapped : {missing_mkt}")
        print(f"tier 1 / tier 2 : {int((df['sampling_tier'] == 1).sum())}"
              f" / {int((df['sampling_tier'] == 2).sum())}")
        print(df[["shortcode", "owner_username", "market", "sampling_tier",
                  "like_count", "owner_followers"]].head(10).to_string(index=False))
        return

    handles = ([(h.lstrip("@"), "") for h in args.handle] if args.handle
               else read_accounts(args.accounts))

    # ---- plan only -------------------------------------------------------
    if args.plan:
        pinned = (f"  (build {args.actor_build})" if args.actor_build
                  else "  (build: LATEST - pin it with --actor-build, docs/01 section 6)")
        print("\nwould run, but --plan makes no API call and spends nothing:")
        print(f"  actor    : {args.actor}{pinned}")
        print(f"  accounts : {len(handles)}")
        for h, m in handles:
            print(f"      @{h:<22} {m}")
        print(f"  limit    : {args.limit} per account")
        print(f"  ceiling  : {len(handles) * args.limit} Reels")
        print(f"  download : {args.download}")
        print(f"  out      : {out_path}")
        have = "present" if config.get("APIFY_TOKEN") else "MISSING - add it to .env"
        print(f"  token    : {have}")
        return

    df, _ = collect(args.actor, handles, args.limit,
                    build=args.actor_build, download=args.download,
                    followers=not args.no_followers)
    if df.empty:
        raise SystemExit("Nothing collected.")

    df.to_parquet(out_path, index=False)

    print(f"\n{'=' * 62}")
    print(f"rows written     : {len(df)}  ->  {out_path}")
    print(f"accounts         : {df['owner_username'].nunique()}")
    print(f"likes missing    : {int(df['like_count'].isna().sum())}")
    print(f"followers missing: {int(df['owner_followers'].isna().sum())}")
    print(f"sponsored        : {int(df['is_sponsored'].astype(bool).sum())}")
    print(f"pinned (confound): {int(df['is_pinned'].astype(bool).sum())}")
    print(f"comments off     : {int(df['comments_disabled'].astype(bool).sum())}")
    n_collab = int(df["is_collab"].astype(bool).sum())
    print(f"tier 1 brand     : {int((df['sampling_tier'] == 1).sum())}")
    print(f"tier 2 collab    : {n_collab}  ({df.loc[df['is_collab'].astype(bool), 'owner_username'].nunique()} creators)")
    unmapped = int((df["market"].fillna("") == "").sum())
    if unmapped:
        print(f"! market unmapped: {unmapped} rows")
    if df["timestamp"].notna().any():
        ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True).dropna()
        if not ts.empty:
            print(f"date range       : {ts.min().date()} .. {ts.max().date()}")

    # ---- section 4 agreement check --------------------------------------
    if args.compare_actor:
        # followers=False: the counts are account-level and already resolved above,
        # so re-running the profile actor would spend credits for identical numbers.
        df_b, _ = collect(args.compare_actor, handles, args.limit,
                          download=False, followers=False)
        if df_b.empty:
            print("  ! comparison actor returned nothing")
        else:
            stats = compare_sources(df, df_b, args.actor, args.compare_actor)
            cmp_path = config.REPORTS / "instagram_source_agreement.csv"
            cmp_path.parent.mkdir(parents=True, exist_ok=True)
            stats.to_csv(cmp_path, index=False)
            b_path = out_path.with_name(out_path.stem + "_actor_b.parquet")
            df_b.to_parquet(b_path, index=False)
            print(f"\n  agreement stats  -> {cmp_path}")
            print(f"  second actor rows -> {b_path}")
            print("  Record these in docs/01-instagram-acquisition.md section 7.")


if __name__ == "__main__":
    main()

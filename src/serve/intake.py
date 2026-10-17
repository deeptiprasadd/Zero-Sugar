"""Task 12.4 - getting a video into the tool: an upload or a link, cached by file fingerprint (D-058).

    upload  -> stored once as data/interim/serve/media/<sha16>.<ext>
    link    -> details read first without downloading (comments stripped), refused if over 180 s, then the
               file downloaded with the corpus's own yt-dlp settings (src/collect/download_media.fetch),
               always logged out - no cookies, no login
    result  -> data/interim/serve/videos/<file sha16>/<inputs sha12>/result.json; the same video with the same
               platform, caption, title and collaboration answer is not measured again

    python -m src.serve.intake --file clip.mp4 --platform instagram --followers 500000
    python -m src.serve.intake --link https://www.instagram.com/reel/XXXX/ --followers 500000
    python -m src.serve.intake --parse https://youtu.be/XXXXXXXXXXX      # check a link, no network
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.serve.measure import SERVE, StepFailed  # noqa: E402

MEDIA = SERVE / "media"
LINKS = MEDIA / "links"
VIDEOS = SERVE / "videos"
UPLOAD_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
MAX_BYTES = 200 * 1024 ** 2
MAX_SEC = 180.0

LINK_RULES = [
    ("instagram", re.compile(r"^https?://(?:www\.)?instagram\.com/(?:[A-Za-z0-9_.]+/)?(reel|reels|p)/([A-Za-z0-9_-]+)")),
    ("youtube", re.compile(r"^https?://(?:www\.|m\.)?youtube\.com/shorts/([A-Za-z0-9_-]{11})")),
    ("youtube", re.compile(r"^https?://(?:www\.|m\.)?youtube\.com/watch\?(?:.*&)?v=([A-Za-z0-9_-]{11})")),
    ("youtube", re.compile(r"^https?://youtu\.be/([A-Za-z0-9_-]{11})")),
]


class IntakeRefused(StepFailed):
    """The video could not be taken in; the message is meant for the person using the tool."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------ uploads
def store_upload(src: Path) -> Path:
    """Keep one copy of an uploaded file, named by its fingerprint."""
    src = Path(src)
    if src.suffix.lower() not in UPLOAD_EXT:
        raise IntakeRefused(f"'{src.suffix}' files are not accepted; upload an mp4, mov, m4v, webm or mkv video")
    if src.stat().st_size > MAX_BYTES:
        raise IntakeRefused("this file is larger than 200 MB; short videos of up to 3 minutes are much smaller")
    from src.serve.pipeline import artefacts, probe
    probe(src, artefacts()["schema"]["ranges"])         # the pipeline's own checks, before anything is stored
    dest = MEDIA / f"{sha256(src)[:16]}{src.suffix.lower()}"
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    return dest


# ------------------------------------------------------------------------------------------ links
def parse_link(url: str) -> tuple[str, str, str]:
    """(platform, video id, canonical link). Anything that is not a Reel/post or a YouTube video is refused."""
    url = (url or "").strip()
    for platform, rule in LINK_RULES:
        m = rule.match(url)
        if m:
            if platform == "instagram":
                kind, vid = ("reel" if m.group(1) == "reels" else m.group(1)), m.group(2)
                return platform, vid, f"https://www.instagram.com/{kind}/{vid}/"
            vid = m.group(1)
            return platform, vid, f"https://www.youtube.com/watch?v={vid}"
    raise IntakeRefused("only Instagram Reel or post links and YouTube Shorts or video links are accepted")


def link_details(url: str) -> dict:
    """Read a link's public details without downloading the video (logged out, comments stripped)."""
    from src.collect.instagram_links import fetch_one
    platform, vid, canon = parse_link(url)
    rec = fetch_one(canon)
    if rec["status"] != "ok":
        msg = rec.get("error") or ""
        if platform == "youtube" and "confirm you" in msg.lower():
            raise IntakeRefused("YouTube asked for a sign-in before sharing this video; the tool never signs in. "
                                "Please download the Short and upload the file instead.")
        if rec["status"] in ("not_available", "unavailable_or_login"):
            raise IntakeRefused("this post could not be read without logging in (or no longer exists); the tool "
                                "never logs in. Please upload the video file instead.")
        raise IntakeRefused("the link could not be read; please upload the video file instead")
    info = rec["info"]
    title = info.get("title") if platform == "youtube" else None
    if platform == "youtube":
        caption = ((info.get("title") or "") + "\n" + (info.get("description") or "")).strip()
    else:
        caption = info.get("description") or ""
    d = {"platform": platform, "video_id": vid, "link": canon, "account": info.get("uploader_id") or info.get("channel"),
         "caption": caption, "title": title, "duration_sec": info.get("duration"),
         "followers_from_link": info.get("channel_follower_count"),
         "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "yt_dlp_version": rec.get("yt_dlp_version")}
    if d["duration_sec"] and float(d["duration_sec"]) > MAX_SEC:
        raise IntakeRefused(f"this video is {float(d['duration_sec']):.0f} seconds long; the tool covers short videos "
                            f"of up to {MAX_SEC:.0f} seconds")
    return d


def fetch_link(url: str) -> tuple[Path, dict]:
    """Details first, then the file - downloaded exactly as the corpus was, logged out. Reused if fetched before."""
    from src.collect.download_media import fetch
    platform, vid, _ = parse_link(url)
    LINKS.mkdir(parents=True, exist_ok=True)
    record = LINKS / f"{platform}_{vid}.json"
    if record.exists():
        d = json.loads(record.read_text(encoding="utf-8"))
        path = MEDIA / d["file"]
        if path.exists():
            return path, d
    d = link_details(url)
    tmp = MEDIA / "downloading"
    path, err = fetch(d["link"], tmp, f"{platform}_{vid}", cookiefile=None)
    if path is None:
        shutil.rmtree(tmp, ignore_errors=True)
        if platform == "youtube" and err and "confirm you" in err.lower():
            raise IntakeRefused("YouTube asked for a sign-in before sharing this video; the tool never signs in. "
                                "Please download the Short and upload the file instead.")
        raise IntakeRefused("the video could not be downloaded from the link; please upload the file instead")
    dest = MEDIA / f"{sha256(path)[:16]}{path.suffix.lower()}"
    if dest.exists():
        path.unlink()
    else:
        shutil.move(str(path), dest)
    shutil.rmtree(tmp, ignore_errors=True)
    d["file"] = dest.name
    record.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return dest, d


# ------------------------------------------------------------------------------------------ cached result
def inputs_key(platform: str, caption: str | None, title: str | None, creator_collab: bool | None) -> str:
    blob = json.dumps({"platform": platform, "caption": caption, "title": title, "collab": creator_collab},
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def evaluate(video: Path, platform: str, caption: str | None = None, title: str | None = None,
             followers: float | None = None, creator_collab: bool | None = None, answers: dict | None = None,
             log=print) -> dict:
    """Measure a stored video (or reuse its saved measurement) and return the outputs.

    The follower count and the hand-coded answers do not change any measurement, so they are applied to a saved
    result without measuring again."""
    from src.serve import pipeline
    video = Path(video)
    work = VIDEOS / sha256(video)[:16] / inputs_key(platform, caption, title, creator_collab)
    saved = work / "result.json"
    if saved.exists():
        art = pipeline.artefacts()
        r = json.loads(saved.read_text(encoding="utf-8"))
        r["base_rate"] = pipeline.base_rate(art, platform, followers)
        r["hand_codes"] = pipeline.hand_code_answers(art, answers, platform)
        r["reused_saved_measurement"] = True
        return r
    r = pipeline.predict(video, platform, caption=caption, followers=followers, creator_collab=creator_collab,
                         title=title, answers=answers, work=work, log=log)
    r["reused_saved_measurement"] = False
    return r


def main() -> None:
    ap = argparse.ArgumentParser(description="12.4 - take a video in by upload or link and evaluate it (D-058).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--link")
    g.add_argument("--parse", help="check that a link is accepted (no network)")
    ap.add_argument("--platform", choices=["instagram", "youtube"])
    ap.add_argument("--caption-file")
    ap.add_argument("--followers", type=float)
    ap.add_argument("--collab", choices=["yes", "no", "unknown"], default="unknown")
    args = ap.parse_args()
    collab = {"yes": True, "no": False, "unknown": None}[args.collab]
    try:
        if args.parse:
            print(parse_link(args.parse))
            return
        caption = Path(args.caption_file).read_text(encoding="utf-8") if args.caption_file else None
        if args.file:
            if not args.platform:
                ap.error("--platform is required with --file")
            video, platform, title = store_upload(Path(args.file)), args.platform, None
        else:
            video, d = fetch_link(args.link)
            platform, title = d["platform"], d["title"]
            caption = caption if caption is not None else d["caption"]
            print(f"from the link: {d['platform']} {d['video_id']}, account {d['account']}, "
                  f"followers {d['followers_from_link'] or 'not given'}")
        r = evaluate(video, platform, caption, title, args.followers, collab)
    except StepFailed as exc:
        raise SystemExit(f"Not taken in: {exc}")
    print(json.dumps({k: r[k] for k in ("video", "base_rate", "instagram_score", "missing", "reused_saved_measurement")},
                     indent=1, default=float))


if __name__ == "__main__":
    main()

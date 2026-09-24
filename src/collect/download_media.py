"""Phase 3: download and probe every corpus video (tasks 3.1, 3.2, 3.3).

Reads both processed corpora, fetches each `in_corpus` video into
`data/media/{youtube,instagram}/<id>.mp4`, probes it with ffprobe, and records the result in
`data/media/download_manifest.csv`.

Design points:

1.  **yt-dlp through its Python API**, not the `yt-dlp` command: the command is not on PATH
    in this environment, which silently disabled `download_video()` / `download_reel()`.
2.  **Short side capped at 720 px** (`-S res:720`, where "res" is the smaller dimension).
    This keeps the docs/02 §5 rule - 720 on the short side is enough for product and logo
    detection - and applies it the same way to vertical video on both platforms.
3.  **Resumable and idempotent.** A valid file already on disk is never re-downloaded; the
    manifest is merged, not overwritten, so a run cut short picks up where it stopped.
4.  **Researcher downloads are copied, not re-fetched.** Nine Instagram Reels are
    login-only; their `sssinstagram.com` files are copied in and marked as such.
5.  **Both platforms are paced and have a stop rule**: a run of consecutive failures
    (3 on YouTube, 6 on Instagram) is treated as throttling or a bot check, and that
    platform's loop stops rather than deepening the flag.
6.  Nothing but the video is written - no info JSON, no comments, no thumbnails.

Usage:
    python -m src.collect.download_media --limit 1          # one per platform, to test
    python -m src.collect.download_media                    # everything, resumable
    python -m src.collect.download_media --platform instagram
    python -m src.collect.download_media --probe-only       # re-probe files on disk
    python -m src.collect.download_media --check-cookies    # validate the YouTube login file

YouTube login: if downloads fail with "Sign in to confirm you're not a bot", put a cookies.txt
from a SPARE Google account at the path in .env `YOUTUBE_COOKIES_FILE` (default
secrets/youtube_cookies.txt, gitignored). It is used for YouTube only and never printed.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

MANIFEST = config.MEDIA / "download_manifest.csv"
STOP_AFTER = {"youtube": 3, "instagram": 6}
PACE = {"youtube": (1.0, 2.0), "instagram": (3.0, 6.0)}


def probe(path: Path) -> dict:
    """ffprobe: the authoritative shape, length, frame rate and audio presence."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration,size",
                        "-of", "json", str(path)], capture_output=True, text=True, timeout=120)
    try:
        j = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"probe_ok": False}
    streams = j.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = j.get("format") or {}
    fps = None
    if v and v.get("r_frame_rate") and "/" in v["r_frame_rate"]:
        num, den = v["r_frame_rate"].split("/")
        fps = round(float(num) / float(den), 3) if float(den) else None
    dur = float(fmt["duration"]) if fmt.get("duration") else None
    ok = bool(v) and bool(dur) and dur > 0
    return {"probe_ok": ok, "width": v.get("width") if v else None,
            "height": v.get("height") if v else None, "fps": fps,
            "duration_sec": round(dur, 3) if dur else None,
            "video_codec": v.get("codec_name") if v else None,
            "has_audio": a is not None, "bytes": int(fmt["size"]) if fmt.get("size") else None}


def items() -> pd.DataFrame:
    yt = pd.read_parquet(config.PROCESSED / "youtube_corpus.parquet")
    yt = yt[yt["in_corpus"]]
    ig = pd.read_parquet(config.PROCESSED / "instagram_corpus.parquet")
    ig = ig[ig["in_corpus"]]
    a = pd.DataFrame({"platform": "youtube", "media_id": yt["video_id"],
                      "url": "https://www.youtube.com/shorts/" + yt["video_id"],
                      "researcher_file": None})
    b = pd.DataFrame({"platform": "instagram", "media_id": ig["shortcode"],
                      "url": ig["permalink"], "researcher_file": ig["video_path"]})
    return pd.concat([a, b], ignore_index=True)


def cookies_path() -> Path | None:
    """The YouTube login file named in .env, if it exists. Never read or printed here."""
    val = config.get("YOUTUBE_COOKIES_FILE")
    if not val:
        return None
    p = Path(val)
    p = p if p.is_absolute() else config.ROOT / p
    return p if p.exists() else None


def check_cookies(path: Path) -> bool:
    """Is this a usable Netscape cookies.txt for YouTube? Reports names and dates only -
    cookie values are a live login and are never printed."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header_ok = bool(lines) and "Netscape HTTP Cookie File" in lines[0] or \
        (bool(lines) and lines[0].startswith("# HTTP Cookie File"))
    rows = [ln.split("\t") for ln in lines if ln and not ln.startswith("#") and ln.count("\t") >= 6]
    yt = [r for r in rows if r[0].lstrip(".").endswith(("youtube.com", "google.com"))]
    names = {r[5] for r in yt}
    login_names = {"LOGIN_INFO", "SAPISID", "__Secure-3PSID", "SID"}
    expiries = [int(r[4]) for r in yt if r[4].isdigit() and int(r[4]) > 0]
    print(f"  file              : {path.relative_to(config.ROOT) if path.is_relative_to(config.ROOT) else path.name}")
    print(f"  Netscape format   : {'yes' if header_ok else 'NO - export as cookies.txt (Netscape)'}")
    print(f"  youtube/google rows: {len(yt)} of {len(rows)}")
    print(f"  login cookies seen: {sorted(names & login_names) or 'NONE - not logged in when exported'}")
    if expiries:
        soonest = datetime.fromtimestamp(min(expiries), tz=timezone.utc)
        print(f"  earliest expiry   : {soonest:%Y-%m-%d}")
    ok = header_ok and bool(yt) and bool(names & login_names)
    print(f"  usable            : {'yes' if ok else 'no'}")
    return ok


def deno_path() -> Path | None:
    """Deno, the JavaScript runtime yt-dlp needs to answer YouTube's playback challenges.

    Installed with `pip install deno yt-dlp-ejs`, which puts deno.exe in Python's Scripts
    folder - not on PATH here, so yt-dlp would not find it on its own. Without it, logged-in
    YouTube requests fail with "The page needs to be reloaded" (2026-09-15).
    """
    import shutil
    import sysconfig
    found = shutil.which("deno")
    if found:
        return Path(found)
    p = Path(sysconfig.get_path("scripts")) / ("deno.exe" if sys.platform == "win32" else "deno")
    return p if p.exists() else None


def fetch(url: str, dest_dir: Path, media_id: str,
          cookiefile: Path | None = None) -> tuple[Path | None, str | None]:
    import yt_dlp

    dest_dir.mkdir(parents=True, exist_ok=True)
    opts = {"format": "bv*+ba/b", "format_sort": ["res:720", "ext:mp4:m4a"],
            "merge_output_format": "mp4", "outtmpl": str(dest_dir / f"{media_id}.%(ext)s"),
            "noplaylist": True, "quiet": True, "no_warnings": True, "noprogress": True,
            "retries": 3, "fragment_retries": 3, "overwrites": False}
    if cookiefile:
        opts["cookiefile"] = str(cookiefile)
    deno = deno_path()
    if deno:
        opts["js_runtimes"] = {"deno": {"path": str(deno)}}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as exc:  # DownloadError and friends; one failure must not end the run
        return None, str(exc)[-400:]
    found = sorted(dest_dir.glob(f"{media_id}.*"), key=lambda p: p.stat().st_size, reverse=True)
    found = [p for p in found if p.suffix.lower() in (".mp4", ".mkv", ".webm")]
    return (found[0], None) if found else (None, "yt-dlp finished but no video file found")


def load_manifest() -> pd.DataFrame:
    return pd.read_csv(MANIFEST, dtype={"media_id": str}) if MANIFEST.exists() else pd.DataFrame()


def save_manifest(rows: list[dict]) -> None:
    new = pd.DataFrame(rows)
    old = load_manifest()
    out = pd.concat([old, new], ignore_index=True) if not old.empty else new
    # A re-probe of a file already on disk must not erase how it was originally obtained -
    # that is provenance the methods chapter reports (it once relabelled 9 sssinstagram.com
    # downloads as "already_on_disk").
    if not old.empty and "route" in out.columns:
        first_route = (old[old["route"].astype(str) != "already_on_disk"]
                       .drop_duplicates(subset=["platform", "media_id"], keep="last")
                       .set_index(["platform", "media_id"])["route"])
        keys = pd.MultiIndex.from_frame(out[["platform", "media_id"]])
        known = pd.Series(keys.map(first_route.to_dict().get), index=out.index)
        mask = (out["route"].astype(str) == "already_on_disk") & known.notna()
        out.loc[mask, "route"] = known[mask]
    out = out.drop_duplicates(subset=["platform", "media_id"], keep="last")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(MANIFEST, index=False)


def main() -> None:
    ap = argparse.ArgumentParser(description="Download and probe corpus videos.")
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--limit", type=int, help="at most N new downloads per platform")
    ap.add_argument("--probe-only", action="store_true")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--check-cookies", action="store_true",
                    help="validate the YouTube cookies file (names/dates only) and exit")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from yt_dlp.version import __version__ as ytv

    yt_cookies = cookies_path()
    if args.check_cookies:
        if not yt_cookies:
            raise SystemExit(f"No cookies file at YOUTUBE_COOKIES_FILE={config.get('YOUTUBE_COOKIES_FILE')!r}")
        check_cookies(yt_cookies)
        return
    print(f"YouTube login: {'cookies file found (contents never shown)' if yt_cookies else 'none - logged out'}")

    todo = items()
    if args.platform != "both":
        todo = todo[todo["platform"] == args.platform]
    done = load_manifest()
    good = set()
    if not done.empty and not args.retry_failed:
        good = set(zip(done["platform"], done["media_id"]))

    for platform in ("youtube", "instagram"):
        part = todo[todo["platform"] == platform]
        if part.empty:
            continue
        dest = config.MEDIA_YT if platform == "youtube" else config.MEDIA_IG
        rows, streak, fetched, t0 = [], 0, 0, time.time()
        queue = [r for _, r in part.iterrows()]
        print(f"\n=== {platform}: {len(queue)} in corpus ===", flush=True)

        for n, r in enumerate(queue, start=1):
            mid = str(r["media_id"])
            existing = [p for p in dest.glob(f"{mid}.*") if p.suffix.lower() in (".mp4", ".mkv", ".webm")]
            rec = {"platform": platform, "media_id": mid, "url": r["url"],
                   "yt_dlp_version": ytv, "attempted_at": datetime.now(timezone.utc).isoformat()}
            path, err, route = None, None, None

            if existing:
                path, route = existing[0], "already_on_disk"
            elif args.probe_only:
                continue
            elif isinstance(r["researcher_file"], str) and Path(r["researcher_file"]).exists():
                path = dest / f"{mid}.mp4"
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(r["researcher_file"], path)
                route = "copied_researcher_download (sssinstagram.com)"
            elif (platform, mid) in good and not args.retry_failed:
                continue
            else:
                if args.limit and fetched >= args.limit:
                    continue
                # The login file goes to YouTube only - never to Instagram.
                path, err = fetch(r["url"], dest, mid,
                                  cookiefile=yt_cookies if platform == "youtube" else None)
                route = "yt-dlp (logged in)" if (platform == "youtube" and yt_cookies) else "yt-dlp"
                fetched += 1

            if path:
                rec.update(probe(path))
                rec.update({"status": "ok" if rec.get("probe_ok") else "bad_file",
                            "route": route, "path": str(path.relative_to(config.ROOT)), "error": None})
                streak = 0
            else:
                rec.update({"status": "failed", "route": route, "path": None, "error": err})
                streak += 1
            rows.append(rec)

            if n % 10 == 0 or rec["status"] != "ok" or (route or "").startswith("yt-dlp") and fetched <= 2:
                el = time.time() - t0
                rate = el / max(fetched, 1)
                left = sum(1 for q in queue[n:] if not any(dest.glob(f"{q['media_id']}.*")))
                print(f"  [{n:>3}/{len(queue)}] {mid:<13} {rec['status']:<8} {route or '':<14} "
                      f"{rec.get('width')}x{rec.get('height')} {rec.get('duration_sec')}s"
                      f"  | ~{left * (rate + sum(PACE[platform]) / 2) / 60:.0f} min left"
                      + (f"  ERR {err[:90]}" if err else ""), flush=True)
            if len(rows) >= 10:
                save_manifest(rows)
                rows = []
            if streak >= STOP_AFTER[platform]:
                # Both platforms: YouTube answers repeated requests from a flagged connection
                # with a bot check, and pressing on only deepens the flag.
                print(f"  ! {STOP_AFTER[platform]} consecutive failures - treating as throttling or a bot check, stopping "
                      f"{platform}. Re-run later; finished files are kept.", flush=True)
                break
            if route and route.startswith("yt-dlp"):
                time.sleep(random.uniform(*PACE[platform]))
        if rows:
            save_manifest(rows)

    m = load_manifest()
    if m.empty:
        print("nothing recorded")
        return
    print(f"\n{'=' * 64}\nMANIFEST  {MANIFEST.relative_to(config.ROOT)}")
    for platform, g in m.groupby("platform"):
        ok = g[g["status"] == "ok"]
        print(f"  {platform:<10} ok {len(ok):>3} | failed {int((g['status'] == 'failed').sum())} | "
              f"bad {int((g['status'] == 'bad_file').sum())} | {ok['bytes'].sum() / 1e9:.2f} GB | "
              f"no audio {int((~ok['has_audio'].astype(bool)).sum())} | "
              f"not vertical {int((ok['height'] <= ok['width']).sum())}")


if __name__ == "__main__":
    main()

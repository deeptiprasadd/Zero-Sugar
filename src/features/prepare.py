"""Task 5.1 - prepare every corpus video for measurement.

For each of the 300 in-corpus videos this writes:

*   **A 16 kHz mono WAV** into `data/interim/audio/`. This is the input for speech-to-text
    (5.6), prosody and energy (5.8) and music-vs-speech tagging. 16 kHz mono is what all
    three want; handing each of them an MP4 makes each one decode the file again.
*   **A normalisation profile** in the video's cache file: native shape, frame rate and
    length, plus the common working size every pixel measure resizes to (`common.WORK_WIDTH`).

**No normalised copy of the video is written.** docs/05 section 1 shows one in the pipeline
diagram; it would cost ~1.5 GB and ~30 min of re-encoding to buy comparability that resizing
at the moment of measurement gives for free - and it would blur the frames that on-screen
text recognition (5.5) needs sharp. Decided with the researcher, 2026-09-16.

**Silence is checked, not assumed.** All 300 files carry an audio *stream*, which is not the
same as audible sound. Speech-to-text on a silent track invents text rather than returning
nothing, so a silent file found here is worth more than a puzzling transcript found later.

Resumable: a video whose WAV already exists and probes correctly is skipped.

Usage:
    python -m src.features.prepare --limit 5     # try it on five videos per platform
    python -m src.features.prepare               # all 300, resumable
    python -m src.features.prepare --platform instagram
    python -m src.features.prepare --force       # redo work already done
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

AUDIO_MANIFEST = common.AUDIO / "audio_manifest.csv"

# Digital silence: nothing in the track rises above this sample amplitude (1.0 = full scale).
SILENT_PEAK = 1e-4
# Audible but effectively empty: below -60 dBFS on average.
NEAR_SILENT_RMS = 1e-3
# Audio and video length should agree; report anything further apart than this.
DURATION_TOLERANCE_SEC = 0.5


def extract_audio(src: Path, dest: Path) -> tuple[bool, str]:
    """ffmpeg: first audio stream -> 16 kHz mono 16-bit WAV. Returns (ok, error)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".wav.part")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src),
           "-vn", "-map", "0:a:0", "-ac", str(common.AUDIO_CHANNELS),
           "-ar", str(common.AUDIO_SR), "-c:a", "pcm_s16le", "-f", "wav", str(tmp)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return False, "ffmpeg timed out"
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        msg = (r.stderr or "ffmpeg failed").strip()
        return False, (msg.splitlines()[-1] if msg else "ffmpeg failed")[:200]
    tmp.replace(dest)
    return True, ""


def measure_audio(path: Path) -> dict:
    """Peak, loudness and silence, read straight from the samples."""
    import soundfile as sf
    try:
        data, sr = sf.read(str(path), dtype="float32", always_2d=False)
    except Exception as exc:  # an unreadable WAV is this step's failure, not 5.6's mystery
        return {"audio_readable": False, "audio_error": f"{type(exc).__name__}: {exc}"[:200]}
    if data.ndim > 1:
        data = data.mean(axis=1)
    if data.size == 0:
        return {"audio_readable": True, "audio_samples": 0, "audio_peak": 0.0,
                "audio_rms": 0.0, "audio_silent": True, "audio_near_silent": True}
    peak = float(np.abs(data).max())
    rms = float(np.sqrt(np.mean(np.square(data.astype(np.float64)))))
    return {"audio_readable": True, "audio_samples": int(data.size),
            "audio_sr_read": int(sr),
            "audio_peak": round(peak, 6), "audio_rms": round(rms, 6),
            "audio_silent": peak < SILENT_PEAK,
            "audio_near_silent": rms < NEAR_SILENT_RMS}


def prepare_one(row: pd.Series, force: bool) -> dict:
    platform, media_id = row["platform"], row["media_id"]
    src = Path(row["video_path"])
    wav = common.audio_file(platform, media_id)
    out = {"platform": platform, "media_id": media_id,
           "video_path": str(src.relative_to(config.ROOT)),
           "audio_path": str(wav.relative_to(config.ROOT)),
           "prepared_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    vprobe = common.ffprobe(src)
    if not vprobe.get("probe_ok"):
        return {**out, "status": "failed", "error": "source video did not probe"}

    w, h = vprobe.get("width"), vprobe.get("height")
    if not w or not h:
        return {**out, "status": "failed", "error": "source video has no video stream"}
    ww, wh = common.work_size(w, h)
    out.update({"native_width": w, "native_height": h, "native_fps": vprobe.get("fps"),
                "video_duration_sec": vprobe.get("duration_sec"),
                "aspect_ratio": round(w / h, 4),
                "work_width": ww, "work_height": wh, "work_scale": round(ww / w, 4)})

    reused = False
    if wav.exists() and not force:
        ap = common.ffprobe(wav)
        if (ap.get("probe_ok") and ap.get("sample_rate") == common.AUDIO_SR
                and ap.get("channels") == common.AUDIO_CHANNELS):
            reused = True
    if not reused:
        if not vprobe.get("has_audio"):
            return {**out, "status": "failed", "error": "source has no audio stream"}
        ok, err = extract_audio(src, wav)
        if not ok:
            return {**out, "status": "failed", "error": err}

    aprobe = common.ffprobe(wav)
    if not aprobe.get("probe_ok"):
        return {**out, "status": "failed", "error": "extracted WAV did not probe"}
    out.update({"audio_sr": aprobe.get("sample_rate"),
                "audio_channels": aprobe.get("channels"),
                "audio_duration_sec": aprobe.get("duration_sec"),
                "audio_bytes": aprobe.get("bytes")})
    out.update(measure_audio(wav))

    vd, ad = out.get("video_duration_sec"), out.get("audio_duration_sec")
    out["duration_gap_sec"] = round(abs(vd - ad), 3) if vd and ad else None
    out["duration_mismatch"] = bool(out["duration_gap_sec"] is not None
                                    and out["duration_gap_sec"] > DURATION_TOLERANCE_SEC)
    out["status"] = "reused" if reused else "ok"
    return out


def save_audio_manifest(rows: list[dict]) -> None:
    new = pd.DataFrame(rows)
    if AUDIO_MANIFEST.exists():
        old = pd.read_csv(AUDIO_MANIFEST, dtype={"media_id": str})
        new = pd.concat([old, new], ignore_index=True)
    new = new.drop_duplicates(subset=["platform", "media_id"], keep="last")
    AUDIO_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    new.to_csv(AUDIO_MANIFEST, index=False)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="5.1 - audio extraction plus normalisation profile.")
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--limit", type=int, help="at most N videos per platform (quick test)")
    ap.add_argument("--force", action="store_true", help="redo videos already prepared")
    ap.add_argument("--workers", type=int, default=4, help="parallel ffmpeg jobs (default 4)")
    args = ap.parse_args()

    idx = common.video_index(args.platform)
    if args.limit:
        idx = idx.groupby("platform", group_keys=False).head(args.limit)
    print(f"5.1 prepare: {len(idx)} videos "
          f"({idx['platform'].value_counts().to_dict()}), {args.workers} workers")

    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(prepare_one, row, args.force) for _, row in idx.iterrows()]
        for fut in as_completed(futures):
            res = fut.result()
            rows.append(res)
            if res["status"] != "failed":
                common.update_cache(res["platform"], res["media_id"], "prep",
                                    {k: v for k, v in res.items()
                                     if k not in ("platform", "media_id")})
            done += 1
            if done % 25 == 0 or done == len(idx):
                print(f"  {done}/{len(idx)}")

    save_audio_manifest(rows)
    df = pd.DataFrame(rows)

    print(f"\nWrote {AUDIO_MANIFEST.relative_to(config.ROOT)}")
    print("status:", df["status"].value_counts().to_dict())
    ok = df[df["status"] != "failed"]
    if len(ok):
        print(f"audio on disk: {ok['audio_bytes'].sum() / 1e6:.0f} MB, "
              f"{ok['audio_duration_sec'].sum() / 60:.1f} min")
        print(f"sample rates: {ok['audio_sr'].value_counts().to_dict()}  "
              f"channels: {ok['audio_channels'].value_counts().to_dict()}")
        print("aspect ratios: "
              f"{ok['aspect_ratio'].round(3).value_counts().head(6).to_dict()}")
        print(f"native fps: {ok['native_fps'].round(0).value_counts().head(6).to_dict()}")

    for flag, label in [("audio_silent", "SILENT audio"),
                        ("audio_near_silent", "near-silent audio"),
                        ("duration_mismatch", "audio/video length mismatch")]:
        if flag in df.columns:
            bad = df[df[flag].fillna(False).astype(bool)]
            if len(bad):
                print(f"\n{label}: {len(bad)}")
                cols = [c for c in ["platform", "media_id", "audio_rms", "audio_peak",
                                    "video_duration_sec", "duration_gap_sec"]
                        if c in bad.columns]
                print(bad[cols].to_string(index=False))

    failed = df[df["status"] == "failed"]
    if len(failed):
        print(f"\nFAILED: {len(failed)}")
        print(failed[["platform", "media_id", "error"]].to_string(index=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

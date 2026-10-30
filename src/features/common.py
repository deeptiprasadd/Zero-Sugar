"""Shared plumbing for Phase 5 feature extraction.

Three things every extraction step needs and none of them should re-invent:

1.  **Where the videos are.** The corpus parquets carry a `video_path` column, but it is
    empty - 0 of 150 YouTube rows and 9 of 150 Instagram rows have a value. The authoritative
    location of every file is `data/media/download_manifest.csv`. `video_index()` joins the
    two so a caller gets one row per corpus video with a path that exists on disk.
2.  **A per-video cache.** docs/05 §1: "Cache everything per video. A failed run must cost
    minutes, not days." Each step merges its own block into
    `data/interim/features/{platform}_{media_id}.json`; 5.10 flattens the lot into a parquet.
3.  **A common working resolution.** The corpus is not one shape: widths run 360-720 px and
    16 of 300 videos are 4:5 rather than 9:16. Pixel measures such as edge density and motion
    would otherwise partly measure file size rather than content. Every step that reads pixels
    resizes to `WORK_WIDTH` first, so the numbers are comparable. 360 is the *smallest* native
    width in the corpus, so nothing is ever upscaled and no detail is invented.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

# D-069: COKE_CPU=1 measures on the processor (the free public server has no graphics card).
CPU_ONLY = os.environ.get("COKE_CPU") == "1"

MANIFEST = config.MEDIA / "download_manifest.csv"
AUDIO = config.INTERIM / "audio"
CACHE = config.FEATURES_CACHE

# Common working width for every pixel-level measure (px). See docstring note 3.
WORK_WIDTH = 360

# Audio target for speech-to-text (5.6), prosody (5.8) and music tagging (5.9).
AUDIO_SR = 16_000
AUDIO_CHANNELS = 1


def video_index(platform: str = "both") -> pd.DataFrame:
    """One row per in-corpus video, with a file path that exists.

    Columns: platform, media_id, video_path, account, caption, posted_at,
    width, height, fps, duration_sec, has_audio, bytes.
    """
    yt = pd.read_parquet(config.PROCESSED / "youtube_corpus.parquet")
    yt = yt[yt["in_corpus"]]
    ig = pd.read_parquet(config.PROCESSED / "instagram_corpus.parquet")
    ig = ig[ig["in_corpus"]]

    # YouTube has no single caption field; title and description are the text a viewer sees.
    yt_caption = (yt["title"].fillna("") + "\n" + yt["description"].fillna("")).str.strip()
    a = pd.DataFrame({"platform": "youtube", "media_id": yt["video_id"].astype(str),
                      "account": yt["channel_title"], "caption": yt_caption,
                      "posted_at": yt["published_at"]})
    b = pd.DataFrame({"platform": "instagram", "media_id": ig["shortcode"].astype(str),
                      "account": ig["owner_username"], "caption": ig["caption"].fillna(""),
                      "posted_at": ig["timestamp"]})
    idx = pd.concat([a, b], ignore_index=True)

    if not MANIFEST.exists():
        raise SystemExit(f"Missing {MANIFEST}. Run src.collect.download_media first.")
    mf = pd.read_csv(MANIFEST, dtype={"media_id": str})
    mf = mf.drop_duplicates(subset=["platform", "media_id"], keep="last")
    keep = ["platform", "media_id", "path", "width", "height", "fps",
            "duration_sec", "has_audio", "bytes"]
    idx = idx.merge(mf[keep], on=["platform", "media_id"], how="left")

    # Paths in the manifest are relative to the project root and Windows-separated.
    idx["video_path"] = idx["path"].map(
        lambda p: str(config.ROOT / str(p).replace("\\", "/")) if pd.notna(p) else None)
    idx = idx.drop(columns=["path"])

    missing = idx[idx["video_path"].isna() | ~idx["video_path"].fillna("").map(
        lambda p: bool(p) and Path(p).exists())]
    if len(missing):
        raise SystemExit(
            f"{len(missing)} corpus videos have no file on disk, e.g. "
            f"{missing['media_id'].head(3).tolist()}. Re-run src.collect.download_media.")

    if platform != "both":
        idx = idx[idx["platform"] == platform]
    return idx.sort_values(["platform", "media_id"]).reset_index(drop=True)


def cache_file(platform: str, media_id: str) -> Path:
    return CACHE / f"{platform}_{media_id}.json"


def read_cache(platform: str, media_id: str) -> dict:
    p = cache_file(platform, media_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}  # a run killed mid-write; the step will simply redo its block


def update_cache(platform: str, media_id: str, block: str, payload: dict) -> None:
    """Merge one step's results into the video's cache. Written atomically.

    A half-written JSON file is indistinguishable from a missing one on the next run, which
    would silently drop a video from the feature table.
    """
    doc = read_cache(platform, media_id)
    doc.setdefault("platform", platform)
    doc.setdefault("media_id", media_id)
    doc[block] = payload
    p = cache_file(platform, media_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def audio_file(platform: str, media_id: str) -> Path:
    return AUDIO / f"{platform}_{media_id}.wav"


def ffprobe(path: Path) -> dict:
    """Shape, length, frame rate and stream presence. Same shape of answer as Phase 3."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels"
         ":format=duration,size",
         "-of", "json", str(path)],
        capture_output=True, text=True, timeout=120)
    try:
        j = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"probe_ok": False}
    streams = j.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = j.get("format") or {}
    fps = None
    if v and v.get("r_frame_rate") and "/" in str(v["r_frame_rate"]):
        num, den = str(v["r_frame_rate"]).split("/")
        fps = round(float(num) / float(den), 3) if float(den) else None
    dur = float(fmt["duration"]) if fmt.get("duration") else None
    return {"probe_ok": bool(dur) and dur > 0,
            "width": v.get("width") if v else None,
            "height": v.get("height") if v else None,
            "fps": fps,
            "duration_sec": round(dur, 3) if dur else None,
            "video_codec": v.get("codec_name") if v else None,
            "has_audio": a is not None,
            "audio_codec": a.get("codec_name") if a else None,
            "sample_rate": int(a["sample_rate"]) if a and a.get("sample_rate") else None,
            "channels": int(a["channels"]) if a and a.get("channels") else None,
            "bytes": int(fmt["size"]) if fmt.get("size") else None}


def work_size(width: int, height: int, work_width: int = WORK_WIDTH) -> tuple[int, int]:
    """Target size for pixel measures: fixed width, aspect preserved, even dimensions."""
    scale = work_width / float(width)
    h = int(round(height * scale))
    return work_width, h - (h % 2)


# --- Sampled frames (written by 5.3, read by 5.4, 5.5 and 5.12) --------------------------

FRAMES = config.INTERIM / "frames"


def frame_dir(platform: str, media_id: str) -> Path:
    return FRAMES / f"{platform}_{media_id}"


def frame_list(platform: str, media_id: str, role: str | None = None) -> list[dict]:
    """The frames 5.3 stored for one video, in time order.

    Each entry: `file` (absolute path), `t` (seconds from the first frame), `roles`
    ("grid" = the one-per-second sample, "scene" = the keyframe of a scene), `grid_second`,
    `scene`. Pass role="grid" for time-based fractions such as `face_present_frac`, so a
    video with many short scenes is not over-counted.
    """
    block = read_cache(platform, media_id).get("frames")
    if not block:
        raise FileNotFoundError(f"No frames for {platform}_{media_id}; run src.features.frames")
    base = config.ROOT / block["dir"]
    out = []
    for fr in block["frames"]:
        if role is None or role in fr["roles"]:
            out.append({**fr, "file": base / fr["file"]})
    return out


def load_frame(path: Path, work: bool = True):
    """Read a stored frame as a BGR array; `work=True` resizes to the common working width.

    Pixel measures (colour, edges, faces) use work=True so they are comparable across videos
    (D-024). On-screen text recognition uses work=False to keep the full-resolution frame.
    """
    import cv2
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    if work and img.shape[1] != WORK_WIDTH:
        w, h = work_size(img.shape[1], img.shape[0])
        img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
    return img


# --- Optical flow, shared by 5.2's montage check and 5.3's motion measure ----------------

# Farneback settings: OpenCV's documented defaults with one more pyramid level, so a fast
# pan at 360 px is still tracked.
FLOW = dict(pyr_scale=0.5, levels=4, winsize=15, iterations=3, poly_n=5, poly_sigma=1.2,
            flags=0)


def gray_work(img):
    """BGR frame -> greyscale at the common working width."""
    import cv2
    w, h = work_size(img.shape[1], img.shape[0])
    small = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)


def flow_and_residual(g0, g1):
    """Optical flow between two greyscale frames, and how much change the flow fails to explain.

    Returns (mean flow magnitude in px, residual in grey levels 0-255). The residual warps the
    second frame back onto the first along the measured flow and averages what is left.
    Movement - even shaky, handheld movement - is explained by flow and leaves little. A
    different picture cannot be warped into the first and leaves a lot. That is what separates
    a hidden cut from fast motion (docs/05 section 5, 5.3).
    """
    import cv2
    import numpy as np
    flow = cv2.calcOpticalFlowFarneback(g0, g1, None, **FLOW)
    mag = float(np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2).mean())
    h, w = g0.shape
    xx, yy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    warped = cv2.remap(g1, xx + flow[..., 0], yy + flow[..., 1], cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REPLICATE)
    m = 12  # the warp has no source pixels at the very edge
    res = float(np.abs(g0.astype(np.float32) - warped.astype(np.float32))[m:-m, m:-m].mean())
    return mag, res


def grab_gray(path: str, times: list[float]) -> dict[float, tuple[float, object]]:
    """Decode once and return {requested time: (actual time, greyscale working-width frame)}.

    Takes the decoded frame nearest each requested time (ties go to the earlier frame). Times
    are measured from the first decoded frame, the same convention 5.2 and 5.3 use.
    """
    import av
    wanted = sorted(set(times))
    out: dict[float, tuple[float, object]] = {}
    container = av.open(path)
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"
    rate = float(stream.average_rate) if stream.average_rate else 25.0
    prev, t0, i, n = None, None, 0, 0
    try:
        for frame in container.decode(stream):
            abs_t = float(frame.time) if frame.time is not None else n / rate
            n += 1
            t0 = abs_t if t0 is None else t0
            t = abs_t - t0
            while i < len(wanted) and t >= wanted[i]:
                if prev is not None and abs(prev[1] - wanted[i]) <= abs(t - wanted[i]):
                    out[wanted[i]] = (prev[1], gray_work(prev[0].to_ndarray(format="bgr24")))
                else:
                    out[wanted[i]] = (t, gray_work(frame.to_ndarray(format="bgr24")))
                i += 1
            prev = (frame, t)
        while i < len(wanted) and prev is not None and wanted[i] - prev[1] <= 0.5:
            out[wanted[i]] = (prev[1], gray_work(prev[0].to_ndarray(format="bgr24")))
            i += 1
    finally:
        container.close()
    return out


# --- CUDA 12 runtime for the speech engine ----------------------------------------------

def enable_cuda12_dlls() -> list[str]:
    """Let faster-whisper's engine (CTranslate2, built for CUDA 12) find its GPU libraries.

    PyTorch here is the CUDA 13 build and carries only CUDA 13 libraries, which CTranslate2
    cannot use: without this it sees the GPU but fails on its first computation
    ("cublas64_12.dll is not found") - and in a long run that failure surfaced as a silent
    hang. NVIDIA's own CUDA 12 wheels (nvidia-cublas-cu12, nvidia-cudnn-cu12 9.10.2.21 to
    match the cuDNN loader CTranslate2 bundles, nvidia-cuda-nvrtc-cu12) are installed in
    site-packages/nvidia/*/bin; this puts those folders first on the search path. Call it
    before faster_whisper is imported, and do not import torch in the same process first,
    or its CUDA 13 cuDNN pieces may be picked up instead.
    """
    import os
    import site
    added = []
    for sp in site.getsitepackages():
        for sub in ("cublas", "cudnn", "cuda_nvrtc"):
            d = Path(sp) / "nvidia" / sub / "bin"
            if d.is_dir() and str(d) not in added:
                added.append(str(d))
    for d in added:
        try:
            os.add_dll_directory(d)
        except (OSError, AttributeError):
            pass
    if added:
        os.environ["PATH"] = os.pathsep.join(added + [os.environ.get("PATH", "")])
    return added

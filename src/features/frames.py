"""Task 5.3 - sample the frames every visual step reads, and measure motion on the way.

One pass through each video writes two kinds of still frame to
`data/interim/frames/{platform}_{media_id}/`, as JPEG at native resolution:

*   **The one-per-second grid** - the frame nearest 0.5 s, 1.5 s, 2.5 s ... Each stands for
    its second of video. Time-based features (`product_visible_frac`, `face_present_frac`,
    `ocr_text_frame_frac`, `time_to_first_product`) are computed on the grid only, so a video
    is not counted more heavily for having more scenes.
*   **One keyframe per scene** - the frame at the middle of each scene from 5.2. The middle
    avoids the blur and fades at a cut. This is what stops a half-second product shot that
    falls between two grid samples from going unseen, and it gives 5.12 one frame per shot
    to choose from.

A frame that serves both roles is stored once.

**Motion is measured here, not in 5.5.** Motion cannot be read from stills a second apart;
it needs two frames close together, and the video is only open in this step. For each grid
frame, dense optical flow (Farneback) is measured against the frame nearest 0.1 s later, at
the common working width (D-024), and divided by the true time gap - so the unit is pixels
per second at 360 px wide whether the file is 10 fps or 60 fps. A pair that straddles a cut
from 5.2 is skipped: a cut is a change of shot, not movement, and would read as extreme
motion.

**Why the frames are kept on disk** when a normalised video copy was not (D-024): the copy
would have been an intermediate that nothing needed. These frames are the actual sample that
four later steps measure - product detection, faces, text and colour, and the automated
labels - so all of them see identical pixels at identical times, and any of them can be
checked by eye.

A video is re-sampled automatically if 5.2 changes its scene list (see
`scenes_fingerprint`), so the two steps cannot silently disagree.

Usage:
    python -m src.features.frames --limit 2     # a couple of videos per platform
    python -m src.features.frames               # all 300, resumable
    python -m src.features.frames --force       # redo work already done
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

SUMMARY = config.INTERIM / "frames_summary.csv"

GRID_OFFSET_SEC = 0.5      # sample the middle of each second
JPEG_QUALITY = 90
MOTION_GAP_SEC = 0.1       # partner frame for optical flow
CUT_MARGIN_SEC = 0.05      # a cut this close to either end of a pair also disqualifies it
FLOW = common.FLOW  # shared with 5.2's montage check

PARAMS = {"grid_offset_sec": GRID_OFFSET_SEC, "jpeg_quality": JPEG_QUALITY,
          "scene_keyframe": "midpoint_within_scene", "motion_gap_sec": MOTION_GAP_SEC,
          "cut_margin_sec": CUT_MARGIN_SEC, "work_width": common.WORK_WIDTH,
          "flow": "farneback", "flow_levels": FLOW["levels"], "decoder": "pyav"}


def scenes_fingerprint(scenes: list) -> str:
    """Identity of the scene list the frames were sampled from.

    If 5.2 changes a video's scenes (as the montage check did), its scene keyframes and the
    cut-skipping in the motion measure are stale and must be redone; parameters alone cannot
    tell.
    """
    import hashlib
    flat = ",".join(f"{s:.3f}-{e:.3f}" for s, e in scenes)
    return hashlib.sha1(flat.encode("ascii")).hexdigest()[:16]


def plan(duration: float, scenes: list[list[float]]) -> list[dict]:
    """Target times: the grid, each scene's midpoint, and each grid frame's motion partner."""
    targets = []
    k = 0
    while k + GRID_OFFSET_SEC < duration:
        t = k + GRID_OFFSET_SEC
        targets.append({"t": t, "kind": "grid", "grid_second": k})
        if t + MOTION_GAP_SEC < duration:
            targets.append({"t": t + MOTION_GAP_SEC, "kind": "partner", "grid_second": k})
        k += 1
    for i, (s, e) in enumerate(scenes):
        targets.append({"t": (s + e) / 2.0, "kind": "scene", "scene": i,
                        "start": s, "end": e})
    return sorted(targets, key=lambda x: x["t"])


def scene_of(t: float, starts: list[float]) -> int:
    # Scene boundaries are stored to the millisecond; a frame 0.4 ms before a rounded
    # boundary is the first frame of that scene, not the last of the one before.
    return max(0, bisect_right(starts, t + 5e-4) - 1)


def straddles_cut(t0: float, t1: float, cuts: list[float]) -> bool:
    return any(t0 - CUT_MARGIN_SEC < c <= t1 + CUT_MARGIN_SEC for c in cuts)


def frames_one(platform: str, media_id: str, video_path: str, force: bool) -> dict:
    """Sample one video. Safe to call in a worker process."""
    import av
    import cv2

    out = {"platform": platform, "media_id": media_id}
    doc = common.read_cache(platform, media_id)
    prep, scn = doc.get("prep"), doc.get("scenes")
    if not prep or not scn:
        return {**out, "status": "failed", "error": "run 5.1 and 5.2 first"}

    final = common.frame_dir(platform, media_id)
    duration = float(prep["video_duration_sec"])
    scenes = scn["scenes"] or [[0.0, duration]]
    fp = scenes_fingerprint(scenes)

    cached = doc.get("frames")
    if cached and not force and cached.get("params") == PARAMS and final.exists():
        same_scenes = (cached.get("scenes_fingerprint") == fp if "scenes_fingerprint" in cached
                       # written before fingerprints existed: fall back to the scene count
                       else cached["summary"].get("expected_scene") == len(scenes))
        if same_scenes and all((final / f["file"]).exists() for f in cached["frames"]):
            return {**out, "status": "reused", **cached["summary"]}

    starts = [s for s, _ in scenes]
    cuts = starts[1:]
    targets = plan(duration, scenes)

    tmp = final.with_name(final.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)

    stored: dict[int, dict] = {}       # decoded-frame pts -> stored-frame record
    grid_gray: dict[int, tuple] = {}   # grid_second -> (t, gray working-width frame)
    motion = []                        # per grid second
    skipped_cut = 0
    t_start = time.time()

    gray_work = common.gray_work

    def handle(target, frame, ft, key):
        nonlocal skipped_cut
        kind = target["kind"]
        if kind in ("grid", "scene"):
            img = None
            if key not in stored:
                img = frame.to_ndarray(format="bgr24")
                name = f"t{int(round(ft * 1000)):07d}.jpg"
                cv2.imwrite(str(tmp / name), img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                stored[key] = {"file": name, "t": round(ft, 3), "roles": [],
                               "grid_second": None, "scene": scene_of(ft, starts),
                               "width": img.shape[1], "height": img.shape[0]}
            rec = stored[key]
            if kind == "grid":
                if "grid" not in rec["roles"]:
                    rec["roles"].append("grid")
                rec["grid_second"] = target["grid_second"]
                if img is None:
                    img = frame.to_ndarray(format="bgr24")
                grid_gray[target["grid_second"]] = (ft, gray_work(img))
            else:
                if "scene" not in rec["roles"]:
                    rec["roles"].append("scene")
        elif kind == "partner":
            base = grid_gray.get(target["grid_second"])
            if base is None:
                return
            t0, g0 = base
            gap = ft - t0
            if gap <= 0:
                return
            if straddles_cut(t0, ft, cuts):
                skipped_cut += 1
                return
            g1 = gray_work(frame.to_ndarray(format="bgr24"))
            if g1.shape != g0.shape:
                return
            flow = cv2.calcOpticalFlowFarneback(g0, g1, None, **FLOW)
            mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
            motion.append({"grid_second": target["grid_second"], "t": round(t0, 3),
                           "gap_sec": round(gap, 4),
                           "px_per_sec": round(float(mag.mean()) / gap, 3)})

    try:
        container = av.open(video_path)
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        rate = float(stream.average_rate) if stream.average_rate else 25.0
        t0_abs, prev, prev_t, prev_key = None, None, None, None
        ti, n = 0, 0
        for frame in container.decode(stream):
            if frame.time is not None:
                abs_t = float(frame.time)
            else:
                abs_t = n / rate
            if t0_abs is None:
                t0_abs = abs_t
            ft = abs_t - t0_abs
            key = frame.pts if frame.pts is not None else n
            n += 1
            while ti < len(targets) and ft >= targets[ti]["t"]:
                tt = targets[ti]["t"]
                use_prev = prev is not None and abs(prev_t - tt) <= abs(ft - tt)
                # A scene's keyframe must come from that scene. In a one-frame-per-shot
                # montage the midpoint sits exactly between two frames, and rounding can
                # hand it the neighbouring shot's frame in either direction (seen on
                # Dax6ozkufSd). Prefer whichever candidate lies inside the scene.
                if targets[ti]["kind"] == "scene":
                    lo, hi = targets[ti]["start"] - 1e-3, targets[ti]["end"] - 1e-3
                    prev_in = prev is not None and lo <= prev_t < hi
                    cur_in = lo <= ft < hi
                    if use_prev and not prev_in and cur_in:
                        use_prev = False
                    elif not use_prev and not cur_in and prev_in:
                        use_prev = True
                if use_prev:
                    handle(targets[ti], prev, prev_t, prev_key)
                else:
                    handle(targets[ti], frame, ft, key)
                ti += 1
            prev, prev_t, prev_key = frame, ft, key
        # Targets past the last decoded frame: use the last frame if it is close enough.
        while ti < len(targets):
            if prev is not None and targets[ti]["t"] - prev_t <= 0.5:
                handle(targets[ti], prev, prev_t, prev_key)
            ti += 1
        container.close()
    except Exception as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        return {**out, "status": "failed", "error": f"{type(exc).__name__}: {exc}"[:200]}

    frames = sorted(stored.values(), key=lambda r: r["t"])
    n_grid = sum("grid" in f["roles"] for f in frames)
    n_scene = sum("scene" in f["roles"] for f in frames)
    vals = np.array([m["px_per_sec"] for m in motion], dtype=float)
    summary = {
        "n_files": len(frames), "n_grid": n_grid, "n_scene_keyframes": n_scene,
        "n_both": sum(len(f["roles"]) == 2 for f in frames),
        "expected_grid": sum(1 for x in targets if x["kind"] == "grid"),
        "expected_scene": len(scenes),
        "bytes": int(sum((tmp / f["file"]).stat().st_size for f in frames)),
        "motion_pairs": int(vals.size), "motion_skipped_cut": skipped_cut,
        "motion_px_per_sec_median": round(float(np.median(vals)), 3) if vals.size else None,
        "motion_px_per_sec_mean": round(float(vals.mean()), 3) if vals.size else None,
        "decode_sec": round(time.time() - t_start, 2),
    }

    shutil.rmtree(final, ignore_errors=True)
    tmp.rename(final)
    common.update_cache(platform, media_id, "frames", {
        "dir": str(final.relative_to(config.ROOT)), "params": PARAMS,
        "scenes_fingerprint": fp,
        "summary": summary, "frames": frames, "motion": motion,
        "sampled_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return {**out, "status": "ok", **summary}


def main() -> None:
    ap = argparse.ArgumentParser(description="5.3 - frame sampling plus motion.")
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--limit", type=int, help="at most N videos per platform (quick test)")
    ap.add_argument("--force", action="store_true", help="redo videos already sampled")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", nargs="+", metavar="PLATFORM_MEDIAID",
                    help="restrict to these videos, e.g. instagram_Dax6ozkufSd")
    args = ap.parse_args()

    idx = common.video_index(args.platform)
    if args.only:
        keys = idx["platform"] + "_" + idx["media_id"]
        idx = idx[keys.isin(args.only)]
    if args.limit:
        idx = idx.groupby("platform", group_keys=False).head(args.limit)
    print(f"5.3 frames: {len(idx)} videos, {args.workers} workers, JPEG q{JPEG_QUALITY}, "
          f"grid at k+{GRID_OFFSET_SEC}s + scene midpoints, motion gap {MOTION_GAP_SEC}s")

    from joblib import Parallel, delayed
    t0 = time.time()
    rows = Parallel(n_jobs=args.workers, backend="loky", verbose=0)(
        delayed(frames_one)(r["platform"], r["media_id"], r["video_path"], args.force)
        for _, r in idx.iterrows())
    wall = time.time() - t0

    df = pd.DataFrame(rows)
    if SUMMARY.exists():
        old = pd.read_csv(SUMMARY, dtype={"media_id": str})
        df_out = pd.concat([old, df], ignore_index=True).drop_duplicates(
            subset=["platform", "media_id"], keep="last")
    else:
        df_out = df
    df_out.to_csv(SUMMARY, index=False)

    print(f"\nWrote {SUMMARY.relative_to(config.ROOT)}  ({wall / 60:.1f} min wall clock)")
    print("status:", df["status"].value_counts().to_dict())
    ok = df[df["status"] != "failed"]
    if len(ok):
        print(f"frames stored: {int(ok['n_files'].sum())} "
              f"({int(ok['n_grid'].sum())} grid, {int(ok['n_scene_keyframes'].sum())} scene "
              f"keyframes, {int(ok['n_both'].sum())} serving both), "
              f"{ok['bytes'].sum() / 1e9:.2f} GB")
        short_g = ok[ok["n_grid"] < ok["expected_grid"]]
        short_s = ok[ok["n_scene_keyframes"] < ok["expected_scene"]]
        print(f"videos missing a grid frame: {len(short_g)}; "
              f"missing a scene keyframe: {len(short_s)}")
        print(f"motion pairs: {int(ok['motion_pairs'].sum())} measured, "
              f"{int(ok['motion_skipped_cut'].sum())} skipped for straddling a cut")
        m = ok["motion_px_per_sec_median"].dropna()
        print(f"motion (median px/sec at {common.WORK_WIDTH} px, per video): "
              f"min {m.min():.1f}  median {m.median():.1f}  max {m.max():.1f}")

    failed = df[df["status"] == "failed"]
    if len(failed):
        print(f"\nFAILED: {len(failed)}")
        print(failed[["platform", "media_id", "error"]].to_string(index=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

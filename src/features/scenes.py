"""Task 5.2 - scene boundaries and cut rate for every corpus video.

PySceneDetect's `ContentDetector` compares consecutive frames in HSV and calls a cut when the
average change crosses a threshold. From the boundaries this derives the Block A features in
docs/05 section 2A - `cuts_per_sec` above all, which is how fast-cut an edit is, and the one
the spec prefers over a raw scene count because a raw count is mostly a restatement of length.

The scene boundaries themselves are cached, because 5.3 samples one keyframe per scene.

Five choices worth knowing about:

1.  **The PyAV backend, not OpenCV.** 141 of the 150 YouTube files are AV1, which OpenCV
    decodes at about 1x real time - roughly 90 minutes for the corpus. PyAV decodes the same
    file about 4x faster. The two backends disagree slightly on where a cut falls, so the
    whole corpus is measured with one backend; mixing them would put the decoder into the
    feature.
2.  **`min_scene_len` is set in seconds, not frames.** PySceneDetect's default of 15 frames
    means 1.5 s on the corpus's 10 fps file and 0.25 s on its 60 fps files - the same setting
    would mean different things for different videos. A fixed 0.25 s means the same thing
    everywhere.
3.  **No cuts detected means one continuous shot, not zero shots.** `get_scene_list()` returns
    an empty list for a single-shot video; read literally that gives `scene_count = 0` and a
    negative cut count. Single-shot Reels are common and real, so they are recorded as
    `scene_count = 1`, `cut_count = 0`.
4.  **A second check catches photo-flash montages.** The 0.25 s minimum is what stops stage
    lights and camera shake from counting as cuts, and it is right for all but one of the 300
    videos (all screened by the check below; the extremes looked at frame by frame). It is
    wrong for a montage whose picture changes faster than that: one
    Reel swaps photo every frame at 10 fps and read as a single shot. So after detection,
    pairs of frames 0.1 s apart inside each scene are compared: optical flow is used to warp
    one onto the other and whatever the movement cannot explain is measured
    (`common.flow_and_residual`). Continuous footage leaves little; a new picture leaves a
    lot. If the typical leftover is above `MONTAGE_RESIDUAL`, the video is re-detected with a
    one-frame minimum and flagged `hidden_montage`. On the 41 fastest-moving videos the
    montage scored 90 and nothing else scored above 22 (docs/05 section 5, 5.3).
5.  **The 0.25 s minimum is applied to the last shot too.** PySceneDetect enforces it on
    every shot except the final one, so 37 videos ended with a "shot" of 1-6 frames - a
    black end frame, or the first frame of a shot the edit cut off - and gained a cut no
    viewer sees. A final fragment shorter than the minimum is merged into the shot before it
    (never in a hidden montage, where one-frame shots are the point).

Usage:
    python -m src.features.scenes --limit 3      # a few videos per platform
    python -m src.features.scenes                # all 300, resumable
    python -m src.features.scenes --workers 4
    python -m src.features.scenes --force        # redo work already done
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

SUMMARY = config.INTERIM / "scenes_summary.csv"

# Detector settings, recorded with every video so a later run can tell whether the cached
# result was produced under the same rules.
BACKEND = "pyav"
THRESHOLD = 27.0          # PySceneDetect's default; sensitivity checked, see docs/05 section 5
MIN_SCENE_LEN_SEC = 0.25  # in seconds on purpose - see note 2 in the module docstring
DETECTOR = "ContentDetector"

PARAMS = {"detector": DETECTOR, "threshold": THRESHOLD,
          "min_scene_len_sec": MIN_SCENE_LEN_SEC, "backend": BACKEND,
          "auto_downscale": True}

# Hidden-montage check (note 4). Threshold sits in the gap measured on the 41 fastest-moving
# videos: the one real montage 89.8, every other video 22.2 or lower.
MONTAGE_RESIDUAL = 50.0    # grey levels (0-255) left after motion compensation
MONTAGE_MIN_PAIRS = 3
MONTAGE_GAP_SEC = 0.1
MONTAGE_PARAMS = {"residual_threshold": MONTAGE_RESIDUAL, "min_pairs": MONTAGE_MIN_PAIRS,
                  "pair_gap_sec": MONTAGE_GAP_SEC, "work_width": common.WORK_WIDTH,
                  "flow_levels": common.FLOW["levels"]}

# Rules applied to the final scene list (note 5).
FINAL_PARAMS = {"merge_trailing_fragment_below_sec": MIN_SCENE_LEN_SEC}


def detect(path: str, min_scene_len: str | int = f"{MIN_SCENE_LEN_SEC}s"
           ) -> tuple[list[tuple[float, float]], float]:
    """Scene boundaries in seconds, plus how long detection took."""
    import scenedetect
    from scenedetect import ContentDetector, SceneManager, open_video

    scenedetect.logger.setLevel(logging.ERROR)
    video = open_video(path, backend=BACKEND)
    manager = SceneManager()
    manager.auto_downscale = True
    manager.add_detector(ContentDetector(threshold=THRESHOLD, min_scene_len=min_scene_len))
    t0 = time.time()
    manager.detect_scenes(video, show_progress=False)
    elapsed = time.time() - t0
    scenes = [(round(s.seconds, 3), round(e.seconds, 3))
              for s, e in manager.get_scene_list()]
    return scenes, round(elapsed, 2)


def derive(scenes: list[tuple[float, float]], duration: float) -> dict:
    """Boundaries -> the Block A cut features."""
    if not scenes:
        # No cut found anywhere: the video is one continuous shot (note 3).
        scenes = [(0.0, duration)]
    lengths = np.array([e - s for s, e in scenes], dtype=float)
    lengths = lengths[lengths > 0]
    if lengths.size == 0:
        lengths = np.array([duration], dtype=float)
    scene_count = int(len(scenes))
    cut_count = scene_count - 1
    return {
        "scene_count": scene_count,
        "cut_count": cut_count,
        "cuts_per_sec": round(cut_count / duration, 5) if duration else None,
        "mean_shot_len_sec": round(float(lengths.mean()), 3),
        "median_shot_len_sec": round(float(np.median(lengths)), 3),
        "std_shot_len_sec": round(float(lengths.std(ddof=0)), 3),
        "min_shot_len_sec": round(float(lengths.min()), 3),
        "max_shot_len_sec": round(float(lengths.max()), 3),
        "longest_shot_frac": round(float(lengths.max() / duration), 4) if duration else None,
        "is_single_shot": bool(scene_count == 1),
    }


def merge_trailing_fragment(scenes: list) -> tuple[list, float | None]:
    """Fold a final shot shorter than the minimum into the one before it (note 5)."""
    if len(scenes) < 2:
        return scenes, None
    s, e = scenes[-1]
    if e - s >= MIN_SCENE_LEN_SEC:
        return scenes, None
    merged = [list(x) for x in scenes[:-1]]
    merged[-1][1] = e
    return merged, round(e - s, 3)


def montage_check(video_path: str, scenes: list, duration: float) -> dict:
    """Is there a picture change inside detected scenes that movement cannot explain?"""
    cuts = [s for s, _ in scenes[1:]]
    times, pairs = [], []
    k = 0
    while k + 0.5 + MONTAGE_GAP_SEC < duration:
        a, b = k + 0.5, k + 0.5 + MONTAGE_GAP_SEC
        times += [a, b]
        pairs.append((a, b))
        k += 1
    frames = common.grab_gray(video_path, times) if times else {}
    residuals = []
    for a, b in pairs:
        if a not in frames or b not in frames:
            continue
        (ta, ga), (tb, gb) = frames[a], frames[b]
        if tb <= ta or any(ta - 0.05 < c <= tb + 0.05 for c in cuts):
            continue  # an already-detected cut is not evidence of a hidden one
        if ga.shape != gb.shape:
            continue
        residuals.append(common.flow_and_residual(ga, gb)[1])
    med = float(np.median(residuals)) if residuals else None
    return {"pairs": len(residuals),
            "residual_median": round(med, 2) if med is not None else None,
            "hidden_montage": bool(med is not None and len(residuals) >= MONTAGE_MIN_PAIRS
                                   and med > MONTAGE_RESIDUAL),
            "params": MONTAGE_PARAMS}


def scenes_one(platform: str, media_id: str, video_path: str,
               duration: float, force: bool) -> dict:
    """Detect (or reuse) one video's scenes. Safe to call in a worker process.

    Three stages, each reused from the cache when its own settings are unchanged, so adding
    the montage check did not mean re-running the 23-minute detection on all 300 videos.
    """
    out = {"platform": platform, "media_id": media_id}
    cached = common.read_cache(platform, media_id).get("scenes") or {}
    did = []

    # Stage 1 - standard detection (0.25 s minimum shot).
    base = None
    if cached and not force and cached.get("params") == PARAMS:
        # Caches written before the montage check stored the base result as `scenes`.
        base = cached.get("scenes_base", cached.get("scenes"))
        elapsed = cached.get("detect_sec")
    if base is None:
        try:
            base, elapsed = detect(video_path)
        except Exception as exc:
            return {**out, "status": "failed", "error": f"{type(exc).__name__}: {exc}"[:200]}
        did.append("detect")
    base = [list(s) for s in base]

    # Stage 2 - hidden-montage check.
    montage = cached.get("montage") if not did else None
    if not montage or montage.get("params") != MONTAGE_PARAMS:
        try:
            montage = montage_check(video_path, base, duration)
        except Exception as exc:
            return {**out, "status": "failed",
                    "error": f"montage check: {type(exc).__name__}: {exc}"[:200]}
        did.append("montage_check")

    # Stage 3 - a flagged montage is re-detected with a one-frame minimum.
    final = base
    if montage["hidden_montage"]:
        reuse = (not did and cached.get("scenes_base") is not None
                 and cached.get("scenes") is not None)
        if reuse:
            final = [list(s) for s in cached["scenes"]]
        else:
            try:
                final, _ = detect(video_path, min_scene_len=1)
            except Exception as exc:
                return {**out, "status": "failed",
                        "error": f"montage re-detect: {type(exc).__name__}: {exc}"[:200]}
            final = [list(s) for s in final]
            did.append("redetect_1frame")

    trailing = None
    if not montage["hidden_montage"]:
        final, trailing = merge_trailing_fragment(final)

    feats = derive([tuple(s) for s in final], duration)
    montage_cols = {"hidden_montage": montage["hidden_montage"],
                    "montage_residual_median": montage["residual_median"],
                    "montage_pairs": montage["pairs"],
                    "scene_count_base": derive([tuple(s) for s in base], duration)["scene_count"],
                    "trailing_fragment_merged_sec": trailing}
    unchanged = (cached.get("final_params") == FINAL_PARAMS
                 and [list(s) for s in (cached.get("scenes") or [])] == final)
    if not did and unchanged:
        return {**out, **feats, **montage_cols, "duration_sec": duration,
                "detect_sec": elapsed, "status": "reused"}

    payload = {**feats, **montage_cols, "duration_sec": duration, "detect_sec": elapsed,
               "params": PARAMS, "montage": montage, "final_params": FINAL_PARAMS,
               "scenes_base": base, "scenes": final,
               "detected_at": cached.get("detected_at") if "detect" not in did
               else datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    common.update_cache(platform, media_id, "scenes", payload)
    if not unchanged:
        did.append("final_rules")
    return {**out, **feats, **montage_cols, "duration_sec": duration,
            "detect_sec": elapsed, "status": "+".join(did)}


def main() -> None:
    ap = argparse.ArgumentParser(description="5.2 - scene boundaries and cut rate.")
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--limit", type=int, help="at most N videos per platform (quick test)")
    ap.add_argument("--force", action="store_true", help="redo videos already detected")
    ap.add_argument("--workers", type=int, default=4,
                    help="parallel decoders (default 4; AV1 decode is itself threaded)")
    args = ap.parse_args()

    idx = common.video_index(args.platform)
    if args.limit:
        idx = idx.groupby("platform", group_keys=False).head(args.limit)

    # Length comes from 5.1's profile so cuts_per_sec shares a denominator with every other
    # duration in the project; the index value is the fallback if 5.1 has not run.
    jobs = []
    for _, r in idx.iterrows():
        prep = common.read_cache(r["platform"], r["media_id"]).get("prep", {})
        dur = prep.get("video_duration_sec") or r["duration_sec"]
        jobs.append((r["platform"], r["media_id"], r["video_path"], float(dur)))

    total_min = sum(j[3] for j in jobs) / 60
    print(f"5.2 scenes: {len(jobs)} videos, {total_min:.0f} min of video, "
          f"{args.workers} workers, {DETECTOR}(threshold={THRESHOLD}, "
          f"min_scene_len={MIN_SCENE_LEN_SEC}s), backend={BACKEND}")

    from joblib import Parallel, delayed
    t0 = time.time()
    rows = Parallel(n_jobs=args.workers, backend="loky", verbose=5)(
        delayed(scenes_one)(p, m, v, d, args.force) for p, m, v, d in jobs)
    wall = time.time() - t0

    df = pd.DataFrame(rows)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
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
        print(f"\ncuts_per_sec: min {ok['cuts_per_sec'].min():.3f}  "
              f"median {ok['cuts_per_sec'].median():.3f}  "
              f"mean {ok['cuts_per_sec'].mean():.3f}  max {ok['cuts_per_sec'].max():.3f}")
        print(f"scene_count:  min {ok['scene_count'].min()}  "
              f"median {ok['scene_count'].median():.0f}  max {ok['scene_count'].max()}")
        print(f"single-shot videos: {int(ok['is_single_shot'].sum())} of {len(ok)}")
        if "montage_residual_median" in ok.columns:
            r = ok["montage_residual_median"].dropna()
            print(f"montage check: residual median across videos {r.median():.1f}, "
                  f"max {r.max():.1f}; threshold {MONTAGE_RESIDUAL}")
            hm = ok[ok["hidden_montage"].fillna(False).astype(bool)]
            print(f"hidden montages re-detected: {len(hm)}")
            if "trailing_fragment_merged_sec" in ok.columns:
                tf = ok["trailing_fragment_merged_sec"].dropna()
                print(f"trailing fragments merged: {len(tf)} "
                      f"(lengths {tf.min():.3f}-{tf.max():.3f}s)" if len(tf) else
                      "trailing fragments merged: 0")
            if len(hm):
                print(hm[["platform", "media_id", "duration_sec", "scene_count_base",
                          "scene_count", "cuts_per_sec", "montage_residual_median"]]
                      .to_string(index=False))
            near = ok[(ok["montage_residual_median"] > MONTAGE_RESIDUAL * 0.5)
                      & ~ok["hidden_montage"].fillna(False).astype(bool)]
            print(f"videos within half the threshold but not flagged: {len(near)}")
            if len(near):
                print(near[["platform", "media_id", "montage_residual_median",
                            "cuts_per_sec"]].to_string(index=False))
        by = ok.groupby("platform")[["cuts_per_sec", "scene_count", "duration_sec"]].median()
        print("\nmedian by platform:")
        print(by.round(3).to_string())
        fast = ok.nlargest(5, "cuts_per_sec")[
            ["platform", "media_id", "duration_sec", "scene_count", "cuts_per_sec"]]
        print("\nfastest-cut videos (check these look right):")
        print(fast.to_string(index=False))

    failed = df[df["status"] == "failed"]
    if len(failed):
        print(f"\nFAILED: {len(failed)}")
        print(failed[["platform", "media_id", "error"]].to_string(index=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

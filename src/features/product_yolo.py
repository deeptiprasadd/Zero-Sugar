"""Task 5.4, second attempt (D-033): find the drink container with an object detector.

Whole-image CLIP failed because it matches the *scene* rather than a small object: a can covering
a few percent of a frame cannot win a prompt comparison, so a Reel with no product scored 0.935
and podcast Shorts holding a can scored 0.06 (D-033, `reports/product_detection_validation.md`).
An object detector is the fix for exactly that failure - it looks for small objects and returns
boxes, which also makes `product_mean_area` possible for the first time.

**What this measures, named honestly: a drink container on screen, not a Coca-Cola product.**
The detector is COCO-trained and brand-blind: it knows `bottle`, `cup` and `wine glass`, and
cannot tell a Coca-Cola can from any other can or bottle. In a corpus of Coca-Cola brand videos
most containers will be Coca-Cola's, which is what makes it a usable proxy - but the feature is
called `container_*`, and any claim about "the product" carries that caveat.

Model: the COCO-trained YOLO already on the researcher's laptop (`models/yolo26n.pt`, 5.5 MB,
copied from an unrelated project on 2026-09-28) - **nothing was downloaded**.

Frames: the one-per-second grid frames (9,743), the same set 5.4's first attempt used, so the two
are comparable. Full-resolution frames, not the 360 px working width: a small can needs the pixels.

Stored per frame so thresholds can change without re-running: the highest container confidence and
the largest container box as a share of frame area. Video-level features are then derived:

    container_conf_mean        mean of the per-frame best confidence      (threshold-free)
    container_visible_frac     share of frames with confidence >= 0.25    (+ 0.15 / 0.40)
    container_mean_area        mean largest-box area share over frames where one is found
    time_to_first_container    seconds to the first frame >= 0.25; null if never
    container_frames_n         frames contributing

**Nothing enters the feature set until it is validated.** Truth comes from the researcher's
frame-level check (`docs/product_frame_check.csv`, task 5.4v): frames sampled at random, answered
yes/no by eye, never shown any detector output. The gates are the same as the first attempt's -
AUC >= 0.70 on the frame answers, plus the video-level check that the blind-coded no-product
videos sit low - and they are applied by `--validate` after the answers exist. A failed gate means
product visibility is reported as not measured (D-033 option C), not a quietly lowered threshold.

Usage:
    python -m src.features.product_yolo --detect            # run the detector, cache per frame
    python -m src.features.product_yolo --validate          # gates, once the frame answers exist
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

WEIGHTS = config.ROOT / "models" / "yolo26n.pt"
FRAME_SCORES = config.INTERIM / "container_frame_scores.parquet"
SUMMARY = config.INTERIM / "container_summary.csv"
CONTAINER_CLASSES = ("bottle", "cup", "wine glass")
CONF_FLOOR = 0.10           # keep everything above this; thresholds are applied later
THRESHOLDS = (0.15, 0.25, 0.40)
MAIN_THRESHOLD = 0.25
IMGSZ = 640
PARAMS = {"weights": WEIGHTS.name, "classes": list(CONTAINER_CLASSES), "imgsz": IMGSZ,
          "conf_floor": CONF_FLOOR, "threshold": MAIN_THRESHOLD, "grid_frames_only": True,
          "measures": "drink container, brand-blind", "version": 1}


def detect() -> pd.DataFrame:
    """Best container confidence and largest container box per grid frame."""
    import torch
    from ultralytics import YOLO

    if not WEIGHTS.exists():
        raise SystemExit(f"{WEIGHTS} not found. It was copied from the laptop's existing YOLO "
                         f"folder; nothing is downloaded by this module.")
    model = YOLO(str(WEIGHTS))
    names = model.names
    want = [k for k, v in names.items() if v in CONTAINER_CLASSES]
    if not want:
        raise SystemExit(f"this model has no container classes: {sorted(set(names.values()))[:20]}")
    device = 0 if torch.cuda.is_available() else "cpu"

    items = []
    for _, r in common.video_index().iterrows():
        for fr in common.frame_list(r["platform"], r["media_id"], role="grid"):
            items.append((r["platform"], r["media_id"], float(fr["t"]), str(fr["file"])))
    print(f"detecting on {len(items)} grid frames from "
          f"{len({(p, m) for p, m, _, _ in items})} videos, device={device}")

    rows, t0 = [], time.time()
    BATCH = 32
    for i in range(0, len(items), BATCH):
        chunk = items[i:i + BATCH]
        res = model.predict([c[3] for c in chunk], imgsz=IMGSZ, conf=CONF_FLOOR, classes=want,
                            device=device, verbose=False)
        for (platform, media_id, t, _), r in zip(chunk, res):
            conf = r.boxes.conf.cpu().numpy() if len(r.boxes) else np.zeros(0)
            area = np.zeros(0)
            if len(r.boxes):
                xyxy = r.boxes.xyxy.cpu().numpy()
                h, w = r.orig_shape
                area = ((xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])) / float(w * h)
            rows.append({"platform": platform, "media_id": media_id, "t": t,
                         "n_boxes": int(len(conf)),
                         "best_conf": float(conf.max()) if len(conf) else 0.0,
                         "max_area": float(area.max()) if len(area) else 0.0})
        if (i // BATCH) % 20 == 0:
            done = min(i + BATCH, len(items))
            print(f"  {done}/{len(items)}  {(time.time() - t0) / 60:.1f} min")
    df = pd.DataFrame(rows)
    df.to_parquet(FRAME_SCORES, index=False)
    print(f"-> {FRAME_SCORES.relative_to(config.ROOT)}  ({len(df)} frames, "
          f"{(time.time() - t0) / 60:.1f} min)")
    return df


def video_table(frames: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (platform, media_id), g in frames.groupby(["platform", "media_id"]):
        g = g.sort_values("t")
        conf, t = g["best_conf"].to_numpy(), g["t"].to_numpy()
        hit = t[conf >= MAIN_THRESHOLD]
        doc = common.read_cache(platform, media_id)
        duration = float((doc.get("prep") or {}).get("video_duration_sec") or np.nan)
        present = g.loc[conf >= MAIN_THRESHOLD, "max_area"]
        row = {"platform": platform, "media_id": media_id, "container_frames_n": len(g),
               "container_conf_mean": round(float(conf.mean()), 4),
               "container_conf_max": round(float(conf.max()), 4),
               "container_mean_area": round(float(present.mean()), 5) if len(present) else None,
               "time_to_first_container": round(float(hit[0]), 2) if len(hit) else None}
        for th in THRESHOLDS:
            row[f"container_visible_frac_{th:g}"] = round(float((conf >= th).mean()), 4)
        row["container_visible_frac"] = row[f"container_visible_frac_{MAIN_THRESHOLD:g}"]
        row["time_to_first_container_frac"] = (round(float(hit[0]) / duration, 4)
                                               if len(hit) and duration and duration > 0 else None)
        rows.append(row)
    return pd.DataFrame(rows)


def report(frames: pd.DataFrame, videos: pd.DataFrame) -> None:
    print(f"\nframes: {len(frames)}; with a container at "
          + ", ".join(f"{th:g}: {(frames['best_conf'] >= th).mean():.0%}" for th in THRESHOLDS))
    print("\nper video (counts and shares only - no engagement is read here):")
    for p, g in videos.groupby("platform"):
        v = g["container_visible_frac"]
        print(f"  {p:10} n={len(g):3}  container in some frame: "
              f"{int((g['container_conf_max'] >= MAIN_THRESHOLD).sum()):3}  "
              f"visible_frac median {v.median():.2f} (10th-90th {v.quantile(.1):.2f}-{v.quantile(.9):.2f})")
    a = videos["container_mean_area"].dropna()
    print(f"  box area share, where found: median {a.median():.3f} (90th {a.quantile(.9):.3f}) "
          f"- this is what CLIP could never give")
    tt = videos["time_to_first_container"].dropna()
    print(f"  time to first container: median {tt.median():.1f} s over {len(tt)} videos "
          f"({len(videos) - len(tt)} never)")
    print("\nNot validated yet: run the researcher's frame check (5.4v), then --validate.")


def main() -> None:
    ap = argparse.ArgumentParser(description="5.4 second attempt - container detection (D-033).")
    ap.add_argument("--detect", action="store_true", help="run the detector over the grid frames")
    ap.add_argument("--validate", action="store_true",
                    help="apply the gates against the researcher's frame answers")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.detect or not FRAME_SCORES.exists():
        frames = detect()
    else:
        frames = pd.read_parquet(FRAME_SCORES)
        print(f"reusing {len(frames)} frame scores from {FRAME_SCORES.relative_to(config.ROOT)}")
    videos = video_table(frames)
    videos.to_csv(SUMMARY, index=False)
    print(f"-> {SUMMARY.relative_to(config.ROOT)}  ({len(videos)} videos)")
    report(frames, videos)

    if args.validate:
        from src.features.product_validate import run_gates
        run_gates(frames, videos)
        return
    print("\nNothing written to the feature cache: the gates in D-033 must pass first.")


if __name__ == "__main__":
    main()

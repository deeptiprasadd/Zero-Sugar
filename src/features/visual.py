"""Task 5.5, part A - colour, brightness, contrast and visual busyness (docs/05 Block A).

No model and no download: OpenCV on the one-per-second grid frames (5.3), resized to the common
360 px working width so a 720 px video and a 360 px one are measured on the same footing (D-024).
Motion was already measured in 5.3 (D-026) and is not repeated here.

Per frame, then averaged over the video:

    brightness        mean V of HSV, 0-1
    contrast          standard deviation of greyscale, 0-1
    saturation        mean S of HSV, 0-1
    colourfulness     Hasler-Susstrunk: sqrt(sd_rg^2 + sd_yb^2) + 0.3 * sqrt(mean_rg^2 + mean_yb^2)
    red_ratio         share of pixels inside Coca-Cola's red hue band with decent saturation
                      and value - brand-meaningful, and the reason it is kept (docs/05 Block A)
    edge_density      share of pixels Canny calls an edge, at fixed thresholds

Also `*_sd` across frames for brightness, saturation and red_ratio: a video that cuts between a
dark street and a bright kitchen is not the same as one lit evenly, and the mean alone hides that.

**Red is not the same as a product.** `red_ratio` counts red pixels, which can be a can, a
backdrop, a shirt or a logo. It is a colour measure, named as one; product visibility is task 5.4.

Runs on all 300 videos (D-030: the focus applies at analysis, not at measurement).

Usage:
    python -m src.features.visual --limit 3
    python -m src.features.visual
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

SUMMARY = config.INTERIM / "visual_summary.csv"
# Coca-Cola red sits at the wrap-around of the OpenCV hue circle (0-179), so two bands.
RED_BANDS = ((0, 10), (170, 179))
RED_S_MIN, RED_V_MIN = 90, 60        # ignore pale pinks and near-black reds
CANNY_LO, CANNY_HI = 100, 200
PARAMS = {"work_width": common.WORK_WIDTH, "frames": "grid (one per second)",
          "red_bands": RED_BANDS, "red_s_min": RED_S_MIN, "red_v_min": RED_V_MIN,
          "canny": [CANNY_LO, CANNY_HI], "version": 1}


def frame_measures(img) -> dict:
    import cv2
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    b, g, r = (img[:, :, i].astype(np.float32) for i in range(3))
    rg = r - g
    yb = 0.5 * (r + g) - b
    colourful = float(np.sqrt(rg.std() ** 2 + yb.std() ** 2)
                      + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))

    red = np.zeros(h.shape, dtype=bool)
    for lo, hi in RED_BANDS:
        red |= (h >= lo) & (h <= hi)
    red &= (s >= RED_S_MIN) & (v >= RED_V_MIN)

    return {"brightness": float(v.mean()) / 255.0,
            "contrast": float(grey.std()) / 255.0,
            "saturation": float(s.mean()) / 255.0,
            "colourfulness": colourful / 255.0,
            "red_ratio": float(red.mean()),
            "edge_density": float((cv2.Canny(grey, CANNY_LO, CANNY_HI) > 0).mean())}


def one_video(platform: str, media_id: str) -> dict:
    frames = common.frame_list(platform, media_id, role="grid")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not frames:
        return {"status": "no_frames", "n_frames": 0, "params": PARAMS, "processed_at": now}
    rows = [frame_measures(common.load_frame(Path(f["file"]), work=True)) for f in frames]
    df = pd.DataFrame(rows)
    out: dict = {"status": "ok", "n_frames": len(df)}
    for c in df.columns:
        out[c] = round(float(df[c].mean()), 5)
    for c in ("brightness", "saturation", "red_ratio"):
        out[f"{c}_sd"] = round(float(df[c].std(ddof=0)), 5)
    out["red_frame_frac"] = round(float((df["red_ratio"] >= 0.02).mean()), 4)
    out["params"] = PARAMS
    out["processed_at"] = now
    return out


def run(idx: pd.DataFrame, force: bool, workers: int) -> pd.DataFrame:
    from concurrent.futures import ThreadPoolExecutor
    todo = [(r["platform"], r["media_id"]) for _, r in idx.iterrows()
            if force or (common.read_cache(r["platform"], r["media_id"]).get("visual") or {})
            .get("params") != PARAMS]
    print(f"5.5A colour and busyness: {len(idx)} selected, {len(todo)} to process")
    t0 = time.time()
    if todo:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for i, (pm, payload) in enumerate(
                    zip(todo, pool.map(lambda pm: one_video(*pm), todo)), 1):
                common.update_cache(pm[0], pm[1], "visual", payload)
                if i % 50 == 0 or i == len(todo):
                    print(f"  {i}/{len(todo)}  {(time.time() - t0) / 60:.1f} min")
    rows = []
    for _, r in idx.iterrows():
        p = common.read_cache(r["platform"], r["media_id"]).get("visual")
        if p:
            rows.append({"platform": r["platform"], "media_id": r["media_id"],
                         **{k: v for k, v in p.items() if k != "params"}})
    df = pd.DataFrame(rows)
    df.to_csv(SUMMARY, index=False)
    print(f"-> {SUMMARY.relative_to(config.ROOT)}  ({len(df)} rows)")
    return df


def report(df: pd.DataFrame) -> None:
    print("\nstatus:", df["status"].value_counts().to_dict())
    cols = ["brightness", "contrast", "saturation", "colourfulness", "red_ratio", "edge_density",
            "brightness_sd", "red_frame_frac"]
    print("\nmedian (10th-90th percentile), per platform:")
    for c in cols:
        yt, ig = [df[df.platform == p][c] for p in ("youtube", "instagram")]
        print(f"  {c:16} YouTube {yt.median():.3f} ({yt.quantile(.1):.3f}-{yt.quantile(.9):.3f})"
              f"   Instagram {ig.median():.3f} ({ig.quantile(.1):.3f}-{ig.quantile(.9):.3f})")
    print("\nfor 5.11's pruning (within-block correlation, |r| > 0.85 drops one):")
    sub = df[["brightness", "contrast", "saturation", "colourfulness", "red_ratio",
              "edge_density"]].corr(method="spearman").abs()
    pairs = [(a, b, sub.loc[a, b]) for i, a in enumerate(sub.columns) for b in sub.columns[i + 1:]]
    for a, b, v in sorted(pairs, key=lambda x: -x[2])[:4]:
        print(f"  {a} vs {b}: {v:.3f}{'   <- one of these goes' if v > 0.85 else ''}")
    print("\nNo engagement value is read here.")


def main() -> None:
    ap = argparse.ArgumentParser(description="5.5 part A - colour, contrast, busyness.")
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", nargs="+", metavar="PLATFORM_MEDIAID")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    idx = common.video_index(args.platform)
    if args.only:
        idx = idx[(idx["platform"] + "_" + idx["media_id"]).isin(args.only)]
    if args.limit:
        idx = idx.groupby("platform", group_keys=False).head(args.limit)
    df = run(idx, args.force, args.workers)
    if len(df):
        report(df)


if __name__ == "__main__":
    main()

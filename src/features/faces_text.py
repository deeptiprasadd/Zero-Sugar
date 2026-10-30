"""Task 5.5, parts B and C - faces on screen, and where on-screen text sits (docs/05 Block A).

Part C, faces: MediaPipe's BlazeFace short-range detector (`models/blaze_face_short_range.tflite`,
~230 KB, researcher-approved 2026-09-28). This build of mediapipe ships no models, so the file is
fetched once with `--allow-download` and then read from disk.

    face_present_frac   share of grid frames with at least one face
    mean_face_count     mean number of faces per grid frame
    max_face_count      the busiest frame
    mean_face_area      mean largest-face area as a share of the frame - a close-up and a crowd
                        shot both "have a face", and this is what separates them
    face_conf_mean      mean best detection confidence, so a weak run is visible

Part B, on-screen text: EasyOCR's CRAFT **detector only** (~80 MB, researcher-approved
2026-09-28). It finds where text is without reading it, which is deliberate:

*   docs/04 section 3 keeps these features coarse on purpose - "sentiment or keyword analysis on
    OCR output across six languages would not survive".
*   Detection is **language-free**, so Arabic, Korean and Thai frames are treated exactly like
    English ones. docs/04 warns Arabic recognition is where OCR fails most; this avoids it.
*   Text is detected on the **full-resolution** frame (D-024), not the 360 px working copy.

    ocr_text_frame_frac   share of grid frames containing any text
    ocr_region_count      mean number of text regions per frame. **Not `ocr_word_count`:** without
                          recognition a region is a text line or block, not a word. Named for what
                          it is (docs/04 section 3 deviation, recorded in D-034)
    ocr_mean_text_area    mean share of the frame covered by text boxes
    ocr_max_text_area     the busiest frame's coverage

`lang_onscreen` (task 5.7) stays **not measured**: it would need a reader per script, and docs/04
already rates Arabic recognition unreliable.

Runs on all 300 videos (D-030: the focus applies at analysis, not at measurement).

Usage:
    python -m src.features.faces_text --part faces --limit 3 --allow-download
    python -m src.features.faces_text --part faces
    python -m src.features.faces_text --part text --limit 3 --allow-download
    python -m src.features.faces_text --part text
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

SUMMARY_FACES = config.INTERIM / "faces_summary.csv"
SUMMARY_TEXT = config.INTERIM / "ocr_summary.csv"

FACE_MODEL = config.ROOT / "models" / "blaze_face_short_range.tflite"
FACE_URL = ("https://storage.googleapis.com/mediapipe-models/face_detector/"
            "blaze_face_short_range/float16/1/blaze_face_short_range.tflite")
FACE_MIN_CONF = 0.5
FACE_PARAMS = {"model": FACE_MODEL.name, "min_confidence": FACE_MIN_CONF,
               "frames": "grid (one per second)", "width": common.WORK_WIDTH, "version": 1}

OCR_MIN_CONF = 0.5          # CRAFT box score
OCR_PARAMS = {"detector": "easyocr CRAFT (detection only, no recognition)",
              "min_confidence": OCR_MIN_CONF, "frames": "grid (one per second)",
              "width": "full resolution (D-024)", "version": 1}


# ============================================================ part C - faces
def load_face_detector(allow_download: bool):
    import mediapipe as mp

    if not FACE_MODEL.exists():
        if not allow_download:
            raise SystemExit(f"{FACE_MODEL.name} is not on disk. One-time download, about 230 KB, "
                             f"free (Apache-2.0, Google). Re-run with --allow-download.")
        import urllib.request
        FACE_MODEL.parent.mkdir(parents=True, exist_ok=True)
        print(f"fetching {FACE_URL.rsplit('/', 1)[-1]} ...")
        urllib.request.urlretrieve(FACE_URL, FACE_MODEL)
        print(f"  saved {FACE_MODEL.stat().st_size / 1e3:.0f} KB -> "
              f"{FACE_MODEL.relative_to(config.ROOT)}")
    base = mp.tasks.BaseOptions(model_asset_path=str(FACE_MODEL))
    opts = mp.tasks.vision.FaceDetectorOptions(
        base_options=base, min_detection_confidence=FACE_MIN_CONF,
        running_mode=mp.tasks.vision.RunningMode.IMAGE)
    return mp.tasks.vision.FaceDetector.create_from_options(opts)


def faces_one(det, platform: str, media_id: str) -> dict:
    import cv2
    import mediapipe as mp

    frames = common.frame_list(platform, media_id, role="grid")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not frames:
        return {"status": "no_frames", "n_frames": 0, "params": FACE_PARAMS, "processed_at": now}
    counts, areas, confs = [], [], []
    for f in frames:
        img = common.load_frame(Path(f["file"]), work=True)
        h, w = img.shape[:2]
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        dets = res.detections or []
        counts.append(len(dets))
        if dets:
            boxes = [(d.bounding_box.width * d.bounding_box.height) / float(w * h) for d in dets]
            areas.append(max(boxes))
            confs.append(max(d.categories[0].score for d in dets))
    c = np.asarray(counts, dtype=float)
    return {"status": "ok", "n_frames": len(c),
            "face_present_frac": round(float((c > 0).mean()), 4),
            "mean_face_count": round(float(c.mean()), 4),
            "max_face_count": int(c.max()),
            "mean_face_area": round(float(np.mean(areas)), 5) if areas else None,
            "face_conf_mean": round(float(np.mean(confs)), 4) if confs else None,
            "params": FACE_PARAMS, "processed_at": now}


# ============================================================ part B - on-screen text
def load_text_detector(allow_download: bool):
    import easyocr

    model_dir = Path.home() / ".EasyOCR" / "model"
    have = (model_dir / "craft_mlt_25k.pth").exists()
    if not have and not allow_download:
        raise SystemExit("EasyOCR's CRAFT text detector is not on disk. One-time download, about "
                         "80 MB, free (Apache-2.0). Re-run with --allow-download.")
    # recognizer=False keeps this to detection: no language models, nothing read.
    return easyocr.Reader(["en"], gpu=not common.CPU_ONLY, verbose=False, recognizer=False,
                          download_enabled=allow_download or have)


def text_one(reader, platform: str, media_id: str) -> dict:
    frames = common.frame_list(platform, media_id, role="grid")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not frames:
        return {"status": "no_frames", "n_frames": 0, "params": OCR_PARAMS, "processed_at": now}
    regions, cover = [], []
    for f in frames:
        img = common.load_frame(Path(f["file"]), work=False)     # full resolution (D-024)
        h, w = img.shape[:2]
        boxes = reader.detect(img, text_threshold=OCR_MIN_CONF)[0]
        boxes = boxes[0] if boxes and isinstance(boxes[0], list) else (boxes or [])
        area = 0.0
        for b in boxes:
            x0, x1, y0, y1 = b[0], b[1], b[2], b[3]
            area += max(0, (x1 - x0)) * max(0, (y1 - y0)) / float(w * h)
        regions.append(len(boxes))
        cover.append(min(1.0, area))
    r = np.asarray(regions, dtype=float)
    cv = np.asarray(cover, dtype=float)
    return {"status": "ok", "n_frames": len(r),
            "ocr_text_frame_frac": round(float((r > 0).mean()), 4),
            "ocr_region_count": round(float(r.mean()), 3),
            "ocr_mean_text_area": round(float(cv.mean()), 5),
            "ocr_max_text_area": round(float(cv.max()), 5),
            "params": OCR_PARAMS, "processed_at": now}


# ============================================================ run
def run(part: str, idx: pd.DataFrame, force: bool, allow_download: bool) -> pd.DataFrame:
    block, params, summary = (("faces", FACE_PARAMS, SUMMARY_FACES) if part == "faces"
                              else ("ocr", OCR_PARAMS, SUMMARY_TEXT))
    todo = [(r["platform"], r["media_id"]) for _, r in idx.iterrows()
            if force or (common.read_cache(r["platform"], r["media_id"]).get(block) or {})
            .get("params") != params]
    print(f"5.5 {part}: {len(idx)} selected, {len(todo)} to process")
    if todo:
        model = (load_face_detector(allow_download) if part == "faces"
                 else load_text_detector(allow_download))
        fn = faces_one if part == "faces" else text_one
        t0 = time.time()
        for i, (p, m) in enumerate(todo, 1):
            common.update_cache(p, m, block, fn(model, p, m))
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}  {(time.time() - t0) / 60:.1f} min")
    rows = []
    for _, r in idx.iterrows():
        p = common.read_cache(r["platform"], r["media_id"]).get(block)
        if p:
            rows.append({"platform": r["platform"], "media_id": r["media_id"],
                         **{k: v for k, v in p.items() if k != "params"}})
    df = pd.DataFrame(rows)
    df.to_csv(summary, index=False)
    print(f"-> {summary.relative_to(config.ROOT)}  ({len(df)} rows)")
    return df


def report(part: str, df: pd.DataFrame) -> None:
    print("\nstatus:", df["status"].value_counts().to_dict())
    cols = (["face_present_frac", "mean_face_count", "mean_face_area", "face_conf_mean"]
            if part == "faces" else
            ["ocr_text_frame_frac", "ocr_region_count", "ocr_mean_text_area"])
    print("\nmedian (10th-90th percentile), per platform:")
    for c in cols:
        yt, ig = [df[df.platform == p][c].dropna() for p in ("youtube", "instagram")]
        if len(yt) and len(ig):
            print(f"  {c:20} YouTube {yt.median():.3f} ({yt.quantile(.1):.3f}-{yt.quantile(.9):.3f})"
                  f"   Instagram {ig.median():.3f} ({ig.quantile(.1):.3f}-{ig.quantile(.9):.3f})")
    if part == "faces":
        print(f"\nvideos with a face in at least one frame: "
              f"{int((df['face_present_frac'] > 0).sum())} of {len(df)}; "
              f"in most frames (>= 0.5): {int((df['face_present_frac'] >= 0.5).sum())}")
        print("Sanity: brand advertising is mostly people, so a very low share would be a red flag.")
    else:
        print(f"\nvideos with text in at least one frame: "
              f"{int((df['ocr_text_frame_frac'] > 0).sum())} of {len(df)}; "
              f"in most frames: {int((df['ocr_text_frame_frac'] >= 0.5).sum())}")
        print("`ocr_region_count` counts text regions, not words - nothing was read (D-034).")
    print("No engagement value is read here.")


def main() -> None:
    ap = argparse.ArgumentParser(description="5.5 parts B and C - faces and on-screen text.")
    ap.add_argument("--part", choices=["faces", "text"], required=True)
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", nargs="+", metavar="PLATFORM_MEDIAID")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--allow-download", action="store_true",
                    help="permit the one-time download: faces ~230 KB, text detector ~80 MB")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    idx = common.video_index(args.platform)
    if args.only:
        idx = idx[(idx["platform"] + "_" + idx["media_id"]).isin(args.only)]
    if args.limit:
        idx = idx.groupby("platform", group_keys=False).head(args.limit)
    df = run(args.part, idx, args.force, args.allow_download)
    if len(df):
        report(args.part, df)


if __name__ == "__main__":
    main()

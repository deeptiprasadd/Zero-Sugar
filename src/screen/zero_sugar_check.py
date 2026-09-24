"""D-029 - frame sheets and the answers file for the researcher's visual Zero Sugar check.

The CLIP screen did not discriminate (reports/clip_zero_sugar_calibration.md), so the
researcher checks every YouTube Short that text does not label Zero Sugar - 125 of the 150 -
by eye, the standard already used for Instagram (D-018).

For each Short this writes a sheet, `reports/zero_sugar_visual_check/youtube_<id>.jpg`: the
keyframe of every shot (from 5.3; evenly thinned to 16 if there are more), topped up with
one-per-second frames to at least 8, in time order. One frame per shot means a brief pack shot
is not skipped the way evenly spaced frames can skip it. Frames are chosen by position only -
nothing automated decides which frames are shown.

`docs/zero_sugar_visual_check.csv` lists the Shorts in checking order: the 100 not seen in the
blind coding first, then the 25 that were (random order within each group, seed 20260922). It
has 4 representative frame paths per Short, the sheet, the video file, and blank
`researcher_answer` / `researcher_note` / `answered_at` columns that the checking page
(`python -m src.coding.zero_sugar_check_app`) fills. Re-running never erases an answer.

Answers: zero_sugar | not_zero_sugar | unsure. Applied by `src/screen/zero_sugar_labels.py`.

Usage:
    python -m src.screen.zero_sugar_check
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

CHECK = config.DOCS / "zero_sugar_visual_check.csv"
SHEETS = config.REPORTS / "zero_sugar_visual_check"
CODES = config.DATA / "coding" / "manual_codes_FINAL.csv"
SEED = 20260922
MAX_FRAMES, MIN_FRAMES, THUMB_W, PER_ROW = 16, 8, 230, 8
ANSWER_COLS = ["researcher_answer", "researcher_note", "answered_at"]


def pick_frames(platform: str, media_id: str) -> list[dict]:
    frames = common.frame_list(platform, media_id)
    keys = [f for f in frames if "scene" in f["roles"]]
    if len(keys) > MAX_FRAMES:
        keys = [keys[i] for i in np.linspace(0, len(keys) - 1, MAX_FRAMES).round().astype(int)]
    if len(keys) < MIN_FRAMES:
        grid = [f for f in frames if "grid" in f["roles"] and f not in keys]
        need = min(MIN_FRAMES - len(keys), len(grid))
        if need:
            keys += [grid[i] for i in np.linspace(0, len(grid) - 1, need).round().astype(int)]
    seen, out = set(), []
    for f in sorted(keys, key=lambda f: f["t"]):
        if f["file"] not in seen:
            seen.add(f["file"]); out.append(f)
    return out


def make_sheet(path: Path, title: str, frames: list[dict]) -> None:
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    thumbs = []
    for f in frames:
        im = Image.open(f["file"]).convert("RGB")
        im = im.resize((THUMB_W, int(im.height * THUMB_W / im.width)))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 70, 22), fill=(0, 0, 0))
        d.text((5, 3), f"{f['t']:.1f}s", font=font, fill=(255, 255, 255))
        thumbs.append(im)
    th = max(t.height for t in thumbs)
    rows = (len(thumbs) + PER_ROW - 1) // PER_ROW
    cols = min(PER_ROW, len(thumbs))
    out = Image.new("RGB", (cols * (THUMB_W + 4) + 4, rows * (th + 4) + 34), (35, 35, 35))
    ImageDraw.Draw(out).text((8, 8), title, font=font, fill=(255, 230, 120))
    for n, t in enumerate(thumbs):
        out.paste(t, (4 + (n % PER_ROW) * (THUMB_W + 4), 34 + (n // PER_ROW) * (th + 4)))
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path, quality=90)


def main() -> None:
    yt = pd.read_parquet(config.PROCESSED / "youtube_corpus.parquet")
    yt = yt[yt["in_corpus"] & ~yt["is_zero_sugar_before_D029"].astype(bool)].copy()
    coded = set(pd.read_csv(CODES, dtype={"media_id": str})["media_id"])
    yt["blind_coded"] = yt["video_id"].isin(coded)
    rng = np.random.default_rng(SEED)
    order = []
    for grp in (False, True):                       # never-seen first, then blind-coded
        ids = sorted(yt.loc[yt["blind_coded"] == grp, "video_id"])
        order += list(rng.permutation(ids))
    idx = common.video_index("youtube").set_index("media_id")

    rows = []
    for n, vid in enumerate(order, 1):
        r = yt[yt["video_id"] == vid].iloc[0]
        fr = pick_frames("youtube", vid)
        sheet = SHEETS / f"youtube_{vid}.jpg"
        make_sheet(sheet, f"#{n}  YouTube {vid}  -  {len(fr)} frames, one per shot  -  "
                          f"is Coca-Cola Zero Sugar packaging shown?", fr)
        four = [fr[i] for i in np.linspace(0, len(fr) - 1, min(4, len(fr))).round().astype(int)]
        rows.append({"order": n, "platform": "youtube", "media_id": vid,
                     "url": f"https://www.youtube.com/shorts/{vid}",
                     "account": r["channel_title"], "title": r["title"],
                     "video_path": str(Path(idx.at[vid, "video_path"]).relative_to(config.ROOT)),
                     "why_listed": "not_text_labelled" + ("+blind_coded" if r["blind_coded"] else ""),
                     "sheet": str(sheet.relative_to(config.ROOT)), "n_frames_on_sheet": len(fr),
                     **{f"frame_{k + 1}": str(Path(four[k]["file"]).relative_to(config.ROOT))
                        if k < len(four) else "" for k in range(4)},
                     "researcher_answer": "", "researcher_note": "", "answered_at": ""})
        if n % 25 == 0:
            print(f"  {n}/{len(order)} sheets")
    out = pd.DataFrame(rows)
    if CHECK.exists():                               # never erase an answer
        old = pd.read_csv(CHECK, dtype=str).fillna("")
        if "answered_at" not in old.columns:
            old["answered_at"] = ""
        keep = old[old["researcher_answer"].str.strip() != ""][["platform", "media_id"] + ANSWER_COLS]
        out = out.drop(columns=ANSWER_COLS).merge(keep, on=["platform", "media_id"], how="left")
        out[ANSWER_COLS] = out[ANSWER_COLS].fillna("")
    out.to_csv(CHECK, index=False, encoding="utf-8")
    print(f"{len(out)} Shorts listed ({out['why_listed'].value_counts().to_dict()}); "
          f"frames per sheet {out['n_frames_on_sheet'].min()}-{out['n_frames_on_sheet'].max()}; "
          f"-> {CHECK.relative_to(config.ROOT)}, sheets in {SHEETS.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()

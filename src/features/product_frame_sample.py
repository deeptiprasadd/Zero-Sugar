"""Task 5.4v - draw the frames the researcher answers, to validate product detection (D-033).

Why a frame-level check is the only real validation: the blind codes say whether a product appears
*anywhere* in a video, and 54 of the 59 usable codes say yes, so at video level the construct is
near-constant. What H2 needs is the **share of the video** showing the product, and nothing on
disk is truth for that. docs/05 section 5 always reserved a frame check ("200 hand-coded frames")
for exactly this.

**The sample is drawn blind to every score.** One frame per video, chosen at random from that
video's one-per-second grid frames, 60 videos per platform, seed 20260928. No detector output
touches the choice, so the check cannot flatter either method. 120 frames, about a click each.

One question, three answers, which give both truths in one pass:

    1  a Coca-Cola product is visible      -> counts as a container AND as Coca-Cola
    2  another drink container is visible  -> counts as a container, not as Coca-Cola
    3  no drink container visible

That separation is what turns a brand-blind detector into a stated accuracy for the real
construct: it measures how often a detected container is in fact Coca-Cola's.

Writes `docs/product_frame_check.csv` (never overwrites answers already in it) and copies each
sampled frame to `reports/product_frame_check/` so the page has one folder to serve.

Usage:
    python -m src.features.product_frame_sample
    python -m src.coding.frame_check_app        # then answer them
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

CHECK = config.DOCS / "product_frame_check.csv"
FRAME_DIR = config.REPORTS / "product_frame_check"
PER_PLATFORM = 60
SEED = 20260928
ANSWER_COLS = ["researcher_answer", "researcher_note", "answered_at"]


def build(per_platform: int = PER_PLATFORM, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = common.video_index()
    rows = []
    for platform, g in idx.groupby("platform"):
        ids = sorted(g["media_id"].astype(str))
        pick = rng.choice(ids, size=min(per_platform, len(ids)), replace=False)
        for media_id in pick:
            frames = common.frame_list(platform, media_id, role="grid")
            if not frames:
                continue
            fr = frames[int(rng.integers(0, len(frames)))]
            rows.append({"platform": platform, "media_id": media_id, "t": round(float(fr["t"]), 2),
                         "frame": str(Path(fr["file"]).relative_to(config.ROOT))})
    df = pd.DataFrame(rows).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    df.insert(0, "order", range(1, len(df) + 1))
    for c in ANSWER_COLS:
        df[c] = ""

    if CHECK.exists():                      # never lose an answer already given
        old = pd.read_csv(CHECK, dtype=str).fillna("")
        keep = old.set_index(["platform", "media_id", "t"])[ANSWER_COLS]
        j = df.set_index(["platform", "media_id", "t"])
        for c in ANSWER_COLS:
            j[c] = keep[c].reindex(j.index).fillna("")
        df = j.reset_index()[["order", "platform", "media_id", "t", "frame", *ANSWER_COLS]]
        print(f"kept {int((df['researcher_answer'] != '').sum())} existing answers")

    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    for _, r in df.iterrows():
        dest = FRAME_DIR / f"{r['order']:03d}_{r['platform'][:2]}_{r['media_id']}.jpg"
        if not dest.exists():
            shutil.copy2(config.ROOT / str(r["frame"]).replace("\\", "/"), dest)
        df.loc[df["order"] == r["order"], "image"] = str(dest.relative_to(config.ROOT))
    df.to_csv(CHECK, index=False, encoding="utf-8")
    print(f"-> {CHECK.relative_to(config.ROOT)}  ({len(df)} frames, "
          f"{df['platform'].value_counts().to_dict()})")
    print(f"-> {FRAME_DIR.relative_to(config.ROOT)}  (one JPEG per sampled frame)")
    print("\nThe sample used no detector output: one random grid frame per video, "
          f"{per_platform} videos per platform, seed {seed}.")
    print("Next: python -m src.coding.frame_check_app")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description="5.4v - sample frames for the researcher to answer.")
    ap.add_argument("--per-platform", type=int, default=PER_PLATFORM)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    build(args.per_platform)


if __name__ == "__main__":
    main()

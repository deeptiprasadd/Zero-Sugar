"""D-029 - how each video entered the sample, and how its Zero Sugar label was decided.

Adds four columns to both corpus parquets (and, through `src.process.dependent_variable`, to the
analysis table):

    selection                  hand_picked | systematic   (corpus rows only)
                               hand_picked = entered from the researcher's curated Zero Sugar
                               list (D-018), including the one Reel relabelled Original on
                               inspection; systematic = text census, random draw or replacement.
    zs_label_method            text | researcher_curated | researcher_visual_check
                               (| clip_then_researcher, reserved: the CLIP screen did not
                               discriminate, so every YouTube Short text does not label was
                               checked by the researcher instead - D-029)
    zs_clip_screen             not_screened | flagged | not_flagged   (task 5.4, CLIP)
    is_zero_sugar_before_D029  the label as it stood before this step, kept for comparison
    in_focus                   True where the video is in the analysis scope: a corpus video
                               that features Zero Sugar (D-030, supervisor 2026-09-23 - analyse
                               Zero Sugar only). Rows outside the focus stay in every file as a
                               robustness set and are never deleted.

`is_zero_sugar` itself changes only where the researcher has answered on
`docs/zero_sugar_visual_check.csv` after looking at the frames. Nothing is relabelled
automatically, and a video that text does not name and CLIP does not flag keeps
`is_zero_sugar = False` with the meaning "not identified as Zero Sugar" - never "verified not
Zero Sugar" (D-014: `unnamed` is not `original`).

Idempotent: always rebuilds from `is_zero_sugar_before_D029`, so it can run after every change
to the answers file. Both corpus builders call `annotate()` before writing, so a rebuild keeps
the result. Each entry in `BACKUP_TAGS` is copied once, the first time this runs after that
decision, so the state before D-029 and before D-030 both stay on disk.

Usage:
    python -m src.screen.zero_sugar_labels            # apply, back up once, write
    python -m src.screen.zero_sugar_labels --check    # report only
Then: python -m src.process.dependent_variable
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

CONFIRM = config.DOCS / "zero_sugar_visual_check.csv"          # researcher's answers
CLIP_SCORES = config.INTERIM / "clip_zero_sugar_scores.csv"    # written by 5.4
# One backup per decision that changed these files, made once, before that decision's first write.
BACKUP_TAGS = ["before_D029_20260922", "before_D030_20260923"]
FILES = {"youtube": (config.PROCESSED / "youtube_corpus.parquet", "video_id"),
         "instagram": (config.PROCESSED / "instagram_corpus.parquet", "shortcode")}


def _answers(platform: str) -> pd.DataFrame:
    if not CONFIRM.exists():
        return pd.DataFrame(columns=["media_id", "researcher_answer"])
    a = pd.read_csv(CONFIRM, dtype=str).fillna("")
    a = a[(a["platform"] == platform) & (a["researcher_answer"].str.strip() != "")]
    return a


def _clip(platform: str) -> pd.DataFrame:
    if not CLIP_SCORES.exists():
        return pd.DataFrame(columns=["media_id", "clip_flagged"])
    c = pd.read_csv(CLIP_SCORES, dtype={"media_id": str})
    return c[c["platform"] == platform]


def annotate(df: pd.DataFrame, platform: str) -> pd.DataFrame:
    """Add D-029 columns to one platform's corpus table. Pure: returns a new frame."""
    id_col = FILES[platform][1]
    df = df.copy()
    if "is_zero_sugar_before_D029" not in df.columns:
        df["is_zero_sugar_before_D029"] = df["is_zero_sugar"].astype(bool)
    base = df["is_zero_sugar_before_D029"].astype(bool)
    reason = df["corpus_reason"].astype(str)
    curated = reason.str.startswith("curated") if platform == "instagram" else pd.Series(False, index=df.index)

    df["is_zero_sugar"] = base
    df["zs_label_method"] = np.where(curated, "researcher_curated", "text")
    df["selection"] = pd.Series(np.where(curated, "hand_picked", "systematic"), index=df.index) \
        .where(df["in_corpus"].astype(bool))

    df["zs_clip_screen"] = "not_screened"
    clip = _clip(platform)
    if len(clip):
        flag = dict(zip(clip["media_id"].astype(str), clip["clip_flagged"].astype(bool)))
        ids = df[id_col].astype(str)
        seen = ids.isin(flag)
        df.loc[seen, "zs_clip_screen"] = ids[seen].map(flag).map({True: "flagged", False: "not_flagged"})

    ans = _answers(platform)
    for _, a in ans.iterrows():
        i = df.index[df[id_col].astype(str) == a["media_id"]]
        if not len(i):
            raise SystemExit(f"{CONFIRM.name}: {platform} {a['media_id']} is not in the corpus table")
        v = a["researcher_answer"].strip().lower()
        # Say how the researcher came to look: listed by a CLIP flag, or checked because text did
        # not name the variant (the route taken after the CLIP screen failed - D-029).
        method = ("clip_then_researcher" if "clip" in str(a.get("why_listed", ""))
                  else "researcher_visual_check")
        if v == "zero_sugar":
            df.loc[i, "is_zero_sugar"] = True
            df.loc[i, "zs_label_method"] = method
        elif v == "not_zero_sugar":
            df.loc[i, "is_zero_sugar"] = False
            # the label now rests on the researcher's look, not on text alone
            df.loc[i, "zs_label_method"] = method
        elif v != "unsure":
            raise SystemExit(f"{CONFIRM.name}: unknown answer {v!r} for {a['media_id']} "
                             f"(use zero_sugar / not_zero_sugar / unsure)")

    # D-030: the analysis scope. Zero Sugar only, corpus rows only; everything else is kept and
    # flagged, so the wider 300-video analysis stays available as a robustness check.
    df["in_focus"] = df["is_zero_sugar"].astype(bool) & df["in_corpus"].astype(bool)
    return df


def report(df: pd.DataFrame, platform: str) -> None:
    c = df[df["in_corpus"].astype(bool)]
    print(f"\n{platform}: corpus {len(c)}")
    print(f"  selection        : {c['selection'].value_counts().to_dict()}")
    print(f"  zs_label_method  : {c['zs_label_method'].value_counts().to_dict()}")
    print(f"  zs_clip_screen   : {c['zs_clip_screen'].value_counts().to_dict()}")
    print(f"  Zero Sugar       : before {int(c['is_zero_sugar_before_D029'].sum())} -> now "
          f"{int(c['is_zero_sugar'].sum())}")
    print(f"  in_focus (D-030) : {int(c['in_focus'].sum())} in focus, "
          f"{int((~c['in_focus']).sum())} kept as robustness set")


def main() -> None:
    ap = argparse.ArgumentParser(description="D-029 selection and Zero Sugar label provenance.")
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    args = ap.parse_args()
    for platform, (path, _) in FILES.items():
        df = annotate(pd.read_parquet(path), platform)
        report(df, platform)
        if args.check:
            continue
        for tag in BACKUP_TAGS:
            backup = path.with_name(f"{path.stem}_{tag}.parquet")
            if not backup.exists():
                shutil.copy2(path, backup)
                print(f"  backup -> {backup.relative_to(config.ROOT)}")
        df.to_parquet(path, index=False)
        print(f"  written -> {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()

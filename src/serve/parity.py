"""Gate G4 - training/serving parity (docs/11 section 5; rules fixed in D-055 section 6).

The tool measures a new video with the training code (`src/serve/measure.py`). G4 checks that it really
gives the same model inputs: 10 of the 192 videos are measured again from their files, as if they were new,
in fresh folders, and their inputs are compared with the values the models were trained on.

    python -m src.serve.parity --draw      # draw the 10 (done once, before any pipeline run - D-055)
    python -m src.serve.parity --dev       # development check on 2 corpus videos outside the 192

G4 itself (task 12.8) measures the 10 twice, each time in a fresh folder, with `check(..., with_inputs=True)`;
its run mode and report (`reports/serving_parity.md`) are added in 12.8.

The sample is drawn once and never redrawn: per platform 3 videos with speech and 2 without (speech status
from 5.6), seed 20261017. These 10 are kept out of development; development checks use corpus videos
outside the 192 only (`dev_videos`).

**What is compared.** For the G4 videos: the model inputs the pipeline builds (21 for Instagram, the 20
content features for YouTube) against the values the models were trained on (`src.models.train.build()`),
and the Instagram score position. For every video, also the flattened candidate features against
`data/processed/features.parquet` (the automated-label columns excepted - not run by the tool, D-038).
Primary rule bit-for-bit (missing equals missing); secondary, reported beside it: counts and flags identical,
continuous values within 1e-6 absolute or relative (D-055 section 6). No engagement value is read out.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

SEED = 20261017
SAMPLE = config.REPORTS / "serving_parity_sample.csv"
REPORT = config.REPORTS / "serving_parity.md"
PER_PLATFORM = {"speech": 3, "no_speech": 2}
TOL = 1e-6
NOT_COMPARED = {"blocks_present", "title_char_len_z_lang"}   # the tool records 12 blocks, not 13 (no labels)


def speech_table() -> pd.DataFrame:
    """Every corpus video with its focus flag and 5.6 speech status - no engagement column."""
    f = pd.read_parquet(config.PROCESSED / "features.parquet", columns=["platform", "media_id", "in_focus",
                                                                         "dv_status"])
    f["speech"] = [(common.read_cache(p, m).get("asr") or {}).get("status") == "ok"
                   for p, m in zip(f["platform"], f["media_id"])]
    f["analysis_set"] = f["in_focus"].astype(bool) & (f["dv_status"] == "ok")
    return f.sort_values(["platform", "media_id"]).reset_index(drop=True)


def draw() -> pd.DataFrame:
    if SAMPLE.exists():
        raise SystemExit(f"{SAMPLE.relative_to(config.ROOT)} exists - the G4 sample is drawn once (D-055).")
    f = speech_table()
    rng = np.random.default_rng(SEED)
    rows = []
    for platform in ("instagram", "youtube"):
        pool = f[f["analysis_set"] & (f["platform"] == platform)]
        for kind, n in PER_PLATFORM.items():
            cand = pool[pool["speech"] == (kind == "speech")]["media_id"].tolist()
            for m in rng.choice(cand, size=n, replace=False):
                rows.append({"platform": platform, "media_id": m, "speech": kind == "speech"})
    out = pd.DataFrame(rows)
    out.to_csv(SAMPLE, index=False)
    return out


def g4_keys() -> set[tuple[str, str]]:
    s = pd.read_csv(SAMPLE, dtype={"media_id": str})
    return set(zip(s["platform"], s["media_id"]))


def dev_videos() -> list[tuple[str, str]]:
    """Two corpus videos outside the 192, both with speech (one per platform), for development checks."""
    f = speech_table()
    rng = np.random.default_rng(SEED + 1)
    out = []
    for platform in ("instagram", "youtube"):
        cand = f[~f["analysis_set"] & f["speech"] & (f["platform"] == platform)]["media_id"].tolist()
        out.append((platform, str(rng.choice(cand))))
    assert not set(out) & g4_keys()
    return out


# ------------------------------------------------------------------------------------------ comparing
# Counts and flags must match exactly even under the secondary rule (D-055 section 6).
DISCRETE = {"caption_char_len", "caption_word_count", "hashtag_count", "mention_count", "emoji_count",
            "scene_count", "max_face_count", "word_count", "title_char_len", "kw_event", "kw_promotional",
            "creator_collab_f", "instagram score position"}


def same(column: str, a, b) -> tuple[bool, bool]:
    """(identical, within the secondary tolerance). Missing equals missing."""
    na, nb = a is None, b is None
    if na or nb:
        return na and nb, na and nb
    if isinstance(a, (bool, str)) or isinstance(b, (bool, str)):
        return a == b, a == b
    fa, fb = float(a), float(b)
    exact = fa == fb
    if column in DISCRETE:
        return exact, exact
    return exact, abs(fa - fb) <= TOL or abs(fa - fb) <= TOL * max(abs(fa), abs(fb))


def py(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    if isinstance(v, np.bool_):
        return bool(v)
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def corpus_inputs(platform: str, media_id: str) -> dict:
    """What the corpus holds for a video and the tool would be given: the file, the caption text training
    measured, the YouTube title, the recorded collaboration flag."""
    idx = common.video_index(platform)
    r = idx[idx["media_id"] == media_id].iloc[0]
    feats = pd.read_parquet(config.PROCESSED / "features.parquet", columns=["platform", "media_id", "creator_collab"])
    collab = feats[(feats["platform"] == platform) & (feats["media_id"] == media_id)]["creator_collab"].iloc[0]
    title = None
    if platform == "youtube":
        yt = pd.read_parquet(config.PROCESSED / "youtube_corpus.parquet", columns=["video_id", "title"])
        title = str(yt[yt["video_id"].astype(str) == media_id]["title"].fillna("").iloc[0])
    return {"video_path": Path(r["video_path"]), "caption": r["caption"], "title": title,
            "creator_collab": py(collab)}


def compare_candidates(platform: str, media_id: str, served: pd.DataFrame) -> list[dict]:
    """The pipeline's flattened features against features.parquet (the automated labels excepted)."""
    feats = pd.read_parquet(config.PROCESSED / "features.parquet")
    t = feats[(feats["platform"] == platform) & (feats["media_id"] == media_id)].iloc[0]
    rows = []
    for c in served.columns:
        if c.startswith("auto_") or c in NOT_COMPARED or c not in t.index:
            continue
        a, b = py(served[c].iloc[0]), py(t[c])
        exact, close = same(c, a, b)
        rows.append({"level": "feature", "column": c, "served": a, "trained": b, "identical": exact,
                     "within_tolerance": close})
    return rows


def compare_inputs(platform: str, media_id: str, X: pd.DataFrame, art: dict) -> list[dict]:
    """The model inputs against the values the models were trained on (focus videos only)."""
    from src.models.train import build
    tr = build()
    t = tr[(tr["platform"] == platform) & (tr["media_id"] == media_id)].iloc[0]
    cols = art["schema"]["feature_order"] if platform == "instagram" else art["schema"]["content_features"]
    rows = []
    for c in cols:
        a, b = py(X[c].iloc[0]), py(float(t[c]) if pd.notna(t[c]) else None)
        exact, close = same(c, a, b)
        rows.append({"level": "model input", "column": c, "served": a, "trained": b, "identical": exact,
                     "within_tolerance": close})
    if platform == "instagram":
        from src.serve.pipeline import instagram_position
        tx = pd.DataFrame([{c: t[c] for c in art["schema"]["feature_order"]}]).astype(float)
        a, b = instagram_position(art, X)["higher_than_pct_of_120"], instagram_position(art, tx)["higher_than_pct_of_120"]
        rows.append({"level": "output", "column": "instagram score position", "served": a, "trained": b,
                     "identical": a == b, "within_tolerance": a == b})
    return rows


def check(videos: list[tuple[str, str]], folder: Path, with_inputs: bool) -> pd.DataFrame:
    from src.serve.pipeline import artefacts, feature_row, model_inputs, predict
    art = artefacts()
    if folder.exists():
        shutil.rmtree(folder)                     # always a fresh, empty folder (D-055 section 6)
    out = []
    for platform, media_id in videos:
        assert common.CACHE == config.FEATURES_CACHE   # training values are read from the training folders
        c = corpus_inputs(platform, media_id)
        print(f"{platform} {media_id}")
        r = predict(c["video_path"], platform, caption=c["caption"], creator_collab=c["creator_collab"],
                    title=c["title"], work=folder / f"{platform}_{media_id}", key=(platform, media_id))
        doc = json.loads((folder / f"{platform}_{media_id}" / "features" /
                          f"{platform}_{media_id}.json").read_text(encoding="utf-8"))
        served = feature_row(doc, caption_known=True)
        X = model_inputs(served, art["schema"])
        rows = compare_candidates(platform, media_id, served)
        if with_inputs:
            rows += compare_inputs(platform, media_id, X, art)
        for x in rows:
            x.update({"platform": platform, "media_id": media_id, "sec": r["timing"]["total_sec"]})
        out += rows
    return pd.DataFrame(out)


def summarise(df: pd.DataFrame) -> str:
    lines = []
    for (p, m), g in df.groupby(["platform", "media_id"], sort=False):
        n, ex, cl = len(g), int(g["identical"].sum()), int(g["within_tolerance"].sum())
        lines.append(f"{p} {m}: {ex}/{n} identical, {cl}/{n} within tolerance, {g['sec'].iloc[0]:.0f} s")
        for _, x in g[~g["identical"]].iterrows():
            lines.append(f"    {x['level']:11} {x['column']:24} served {x['served']!r}  trained {x['trained']!r}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="G4 - training/serving parity (D-055).")
    ap.add_argument("--draw", action="store_true", help="draw the 10 G4 videos (once)")
    ap.add_argument("--dev", action="store_true", help="development check on 2 videos outside the 192")
    args = ap.parse_args()
    if args.draw:
        s = draw()
        print(f"-> {SAMPLE.relative_to(config.ROOT)}")
        print(s.to_string(index=False))
    if args.dev:
        vids = dev_videos()
        df = check(vids, config.INTERIM / "serve" / "parity_dev", with_inputs=False)
        df.to_csv(config.INTERIM / "serve" / "parity_dev.csv", index=False)
        print(summarise(df))


if __name__ == "__main__":
    main()

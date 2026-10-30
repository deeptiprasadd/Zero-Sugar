"""Gate G4 - training/serving parity (docs/11 section 5; rules fixed in D-055 section 6).

The tool measures a new video with the training code (`src/serve/measure.py`). G4 checks that it really
gives the same model inputs: 10 of the 192 videos are measured again from their files, as if they were new,
in fresh folders, and their inputs are compared with the values the models were trained on.

    python -m src.serve.parity --draw      # draw the 10 (done once, before any pipeline run - D-055)
    python -m src.serve.parity --dev       # development check on 2 corpus videos outside the 192

    python -m src.serve.parity --run       # G4 itself (task 12.8): the 10, twice, each time in a fresh folder
    python -m src.serve.parity --record    # write the outcome on models/model_card.json (and rebuild the schema)
    COKE_CPU=1 python -m src.serve.parity --cpu-check   # D-069: 4 of the 10, measured on the processor only
    COKE_CPU=1 COKE_ASR_COMPUTE=int8 python -m src.serve.parity --int8-check   # D-070: the 2 with speech

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


_TRAINED: list[pd.DataFrame] = []


def trained() -> pd.DataFrame:
    """The model table the models were trained on (`src.models.train.build()`), built once per run."""
    if not _TRAINED:
        from src.models.train import build
        _TRAINED.append(build())
    return _TRAINED[0]


def compare_inputs(platform: str, media_id: str, X: pd.DataFrame, art: dict) -> list[dict]:
    """The model inputs against the values the models were trained on (focus videos only)."""
    tr = trained()
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


RESULT = config.INTERIM / "serve" / "g4_result.json"


def run_g4() -> dict:
    """G4 exactly as D-055 section 6 fixed it: the 10 drawn videos, twice, each time in a fresh folder."""
    import time
    s = pd.read_csv(SAMPLE, dtype={"media_id": str})
    vids = list(zip(s["platform"], s["media_id"]))
    speech = dict(zip(vids, s["speech"]))
    runs = []
    for k in (1, 2):
        t0 = time.time()
        df = check(vids, config.INTERIM / "serve" / f"g4_run{k}", with_inputs=True)
        df["run"] = k
        df.to_csv(config.INTERIM / "serve" / f"g4_run{k}.csv", index=False)
        runs.append(df)
        print(f"run {k}: {(time.time() - t0) / 60:.1f} min")
    both = pd.concat(runs, ignore_index=True)
    gate = both[both["level"].isin(["model input", "output"])]
    primary = bool(gate["identical"].all())
    secondary = bool(gate["within_tolerance"].all())
    key = ["platform", "media_id", "level", "column"]
    r1, r2 = (runs[0].set_index(key)["served"], runs[1].set_index(key)["served"])
    run_to_run = [i for i in r1.index if not same(i[3], py(r1[i]), py(r2[i]))[0]]
    res = {"decision": "D-055", "videos": len(vids), "primary_bit_for_bit": primary, "secondary_tolerance": secondary,
           "gate_rows": int(len(gate)), "gate_rows_identical": int(gate["identical"].sum()),
           "feature_rows": int((both["level"] == "feature").sum()),
           "feature_rows_identical": int(both.loc[both["level"] == "feature", "identical"].sum()),
           "run1_vs_run2_differences": [list(i) for i in run_to_run],
           "seconds_per_video": round(float(both.groupby(["run", "platform", "media_id"])["sec"].first().mean()), 1),
           "verdict": "pass" if primary else ("pass within tolerance" if secondary else "fail")}
    RESULT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    write_report(both, res, speech)
    return res


def write_report(both: pd.DataFrame, res: dict, speech: dict) -> None:
    L = ["# G4 - does the tool measure exactly as the study did? (task 12.8, rules fixed in D-055 section 6)", "",
         f"The 10 videos drawn on 17 October before any pipeline run ({SAMPLE.name}), each measured from its file with "
         "the caption the corpus holds and its recorded collaboration flag, in a fresh empty folder, **twice**. "
         "Compared: the inputs of the models (21 for Instagram, the 20 content features for YouTube) against the "
         "values the models were trained on, and for Instagram the score position. Primary rule: every input "
         "identical, missing equal to missing, in both runs. Secondary: counts and flags identical, continuous "
         "values within 1e-6. No engagement value is read out.", "",
         f"**Verdict: {res['verdict'].upper()}** - model inputs and outputs identical in {res['gate_rows_identical']} "
         f"of {res['gate_rows']} comparisons (both runs); the flattened features behind them identical in "
         f"{res['feature_rows_identical']} of {res['feature_rows']}; run 1 against run 2: "
         f"{len(res['run1_vs_run2_differences'])} differences. About {res['seconds_per_video']:.0f} s per video.", "",
         "| Video | Speech | Run | Model inputs identical | Features identical | Seconds |",
         "|---|---|---|---|---|---|"]
    for (run, p, m), g in both.groupby(["run", "platform", "media_id"], sort=False):
        gi = g[g["level"].isin(["model input", "output"])]
        gf = g[g["level"] == "feature"]
        L.append(f"| {p} {m} | {'yes' if speech[(p, m)] else 'no'} | {run} | {int(gi['identical'].sum())}/{len(gi)} | "
                 f"{int(gf['identical'].sum())}/{len(gf)} | {g['sec'].iloc[0]:.0f} |")
    diff = both[~both["identical"]]
    L += ["", "## Every difference" if len(diff) else "## Differences", ""]
    if len(diff):
        L += ["| Run | Video | Level | Measure | Tool | Study | Within 1e-6 |", "|---|---|---|---|---|---|---|"]
        for _, x in diff.iterrows():
            L.append(f"| {x['run']} | {x['platform']} {x['media_id']} | {x['level']} | {x['column']} | {x['served']!r} | "
                     f"{x['trained']!r} | {'yes' if x['within_tolerance'] else 'no'} |")
    else:
        L.append("None: every compared value is identical in both runs.")
    L += ["", "Code: `python -m src.serve.parity --run`. Automated-label columns are not compared (the tool does not "
          "run them, D-038)."]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


def record_on_card(note: str | None = None) -> None:
    """Write the G4 outcome into models/model_card.json, then rebuild the serving schema (it fingerprints the card).
    `note`: the outcome in plain words for the tool's pages (the cause of any difference, as recorded in the decision log)."""
    res = json.loads(RESULT.read_text(encoding="utf-8"))
    card_path = config.MODELS / "model_card.json"
    card = json.loads(card_path.read_text(encoding="utf-8"))
    card["gates"]["G4"] = (f"{res['verdict']} (D-055): on 10 of the 192 videos, measured twice, the tool's model "
                           f"inputs equal the study's in {res['gate_rows_identical']} of {res['gate_rows']} comparisons")
    if note:
        card.setdefault("gates_plain", {})["G4"] = note
    card_path.write_text(json.dumps(card, indent=2, default=float), encoding="utf-8")
    from src.serve.pipeline import build_schema
    build_schema()
    print("model card G4:", card["gates"]["G4"])


def _peak_memory(stop, out: dict) -> None:
    """Largest memory any measuring process of this run used, sampled each second (for the 2.7 GB limit, D-070)."""
    import psutil
    me = psutil.Process()
    while not stop.is_set():
        for ch in me.children(recursive=True):
            try:
                out["peak_mb"] = max(out.get("peak_mb", 0), ch.memory_info().rss / 2 ** 20)
            except psutil.Error:
                pass
        stop.wait(1.0)


def cpu_check(int8: bool = False) -> dict:
    """D-069: per platform the first G4 video with speech and the first without, once, on the processor, in a fresh
    folder. With int8 (D-070): only the two with speech, speech in int8."""
    import os
    import threading
    if not common.CPU_ONLY:
        raise SystemExit("set COKE_CPU=1 (and hide the graphics card, CUDA_VISIBLE_DEVICES=) before running this")
    if int8 != (os.environ.get("COKE_ASR_COMPUTE") == "int8"):
        raise SystemExit("--int8-check needs COKE_ASR_COMPUTE=int8, and --cpu-check needs it unset")
    s = pd.read_csv(SAMPLE, dtype={"media_id": str})
    s = pd.concat([s[(s["platform"] == p) & (s["speech"] == sp)].head(1)        # per platform: speech, no speech
                   for p in ("instagram", "youtube") for sp in ((True,) if int8 else (True, False))])
    vids = list(zip(s["platform"], s["media_id"]))
    tag = "g4_int8" if int8 else "g4_cpu"
    mem, stop = {}, threading.Event()
    threading.Thread(target=_peak_memory, args=(stop, mem), daemon=True).start()
    df = check(vids, config.INTERIM / "serve" / tag, with_inputs=True)
    stop.set()
    df.to_csv(config.INTERIM / "serve" / f"{tag}.csv", index=False)
    gate = df[df["level"].isin(["model input", "output"])]
    res = {"decision": "D-070" if int8 else "D-069", "videos": [list(v) for v in vids],
           "gate_rows": int(len(gate)), "gate_rows_identical": int(gate["identical"].sum()),
           "gate_rows_within_tolerance": int(gate["within_tolerance"].sum()),
           "feature_rows": int((df["level"] == "feature").sum()),
           "feature_rows_identical": int(df.loc[df["level"] == "feature", "identical"].sum()),
           "seconds_per_video": round(float(df.groupby(["platform", "media_id"])["sec"].first().mean()), 1),
           "peak_memory_mb_of_a_measuring_process": round(mem.get("peak_mb", 0.0)),
           "differences": [{k: str(x[k]) for k in ("platform", "media_id", "level", "column", "served", "trained")}
                           for _, x in df[~df["identical"]].iterrows()]}
    (config.INTERIM / "serve" / f"{tag}_result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(summarise(df))
    print(json.dumps({k: v for k, v in res.items() if k != "differences"}, indent=1))
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description="G4 - training/serving parity (D-055).")
    ap.add_argument("--draw", action="store_true", help="draw the 10 G4 videos (once)")
    ap.add_argument("--dev", action="store_true", help="development check on 2 videos outside the 192")
    ap.add_argument("--run", action="store_true", help="G4: the 10 drawn videos, twice, fresh folders (task 12.8)")
    ap.add_argument("--record", action="store_true", help="write the G4 outcome on the model card")
    ap.add_argument("--note", help="with --record: the outcome in plain words for the tool's pages")
    ap.add_argument("--cpu-check", action="store_true", help="D-069: 4 G4 videos measured without a graphics card")
    ap.add_argument("--int8-check", action="store_true", help="D-070: the 2 with speech, speech in int8")
    args = ap.parse_args()
    if args.run:
        print(json.dumps(run_g4(), indent=1))
    if args.record:
        record_on_card(args.note)
    if args.draw:
        s = draw()
        print(f"-> {SAMPLE.relative_to(config.ROOT)}")
        print(s.to_string(index=False))
    if args.cpu_check:
        cpu_check()
    if args.int8_check:
        cpu_check(int8=True)
    if args.dev:
        vids = dev_videos()
        df = check(vids, config.INTERIM / "serve" / "parity_dev", with_inputs=False)
        df.to_csv(config.INTERIM / "serve" / "parity_dev.csv", index=False)
        print(summarise(df))


if __name__ == "__main__":
    main()

"""Task 12.3 - the inference pipeline: a new video -> the training measurements -> the model inputs in the
trained order -> the tool's outputs (D-055; outputs as fixed in D-046, D-053, D-054).

    python -m src.serve.pipeline --build-schema         # once, after 12.1: models/serving_schema.json
    python -m src.serve.pipeline --video clip.mp4 --platform instagram --caption-file caption.txt \\
        --followers 500000 --collab no

1. **Checks before measuring** (D-055 section 2). Refused: a file that does not open as a video, no sound
   track, longer than 180 s. Measured but flagged: shorter than the corpus's shortest video, a shape outside
   its width-to-height range, followers outside the training range.
2. **Measurement** with the training code, in the video's own folder - `src.serve.measure`.
3. **Model inputs** with the training code: `assemble.flatten` and the shared `src/features/derived.py`
   functions, so caption length within language, the log cut rate, face size and the 0/1 flags are computed
   exactly as for the 192 videos. A caption or a collaboration answer that was not given is **missing, never
   zero or "no"**; with no caption, a keyword flag is "yes" only if the speech hit it (D-055 section 1).
4. **Outputs, as values** (the page and its wording are tasks 12.5-12.7): the base rate per platform with its
   80% interval (widened, YouTube marked under-covered); the exploratory Instagram content score as a
   position among the 120 training videos, no probability; each measure as a percentile among the 192; what
   was missing. Missing model inputs are filled by the saved model's own imputer (the training median). The
   hand-coded answers, if given, are passed through beside the shares among the 192 and never enter a model.

Nothing here reads engagement, except `--build-schema`, which needs the training table to compute the
caption-length reference exactly as the statistics did (no engagement value is used or written).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import assemble, common, derived  # noqa: E402
from src.serve.measure import SCHEMA, SERVE, StepFailed, as_stored, current_params, measure  # noqa: E402

MAX_SEC = 180.0                      # short-form scope (D-001); corpus maximum 177.8 s
FILES = ["base_rate.json", "instagram_content_logreg.joblib", "reference_quantiles.json", "model_card.json"]
KW_GROUPS = ["kw_offer", "kw_new", "kw_taste", "kw_zero_sugar", "kw_event", "kw_together"]
# Inputs built from the caption: missing when no caption was given (D-055 section 1).
CAPTION_FIELDS = ["caption_char_len", "caption_word_count", "hashtag_count", "mention_count", "emoji_count",
                  "has_question_mark", "sentiment_caption", "lang_caption"]
YES_NO = ["kw_event", "kw_promotional", "creator_collab"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------ schema
def build_schema() -> dict:
    """What the pipeline must match: the step settings of the 192 records, the caption-length reference,
    the trained input order, the ranges of the training data, and fingerprints of the saved models."""
    import joblib
    from src.stats.hypotheses import RAW, load

    feats = pd.read_parquet(config.PROCESSED / "features.parquet")
    focus_keys = feats[feats["in_focus"].astype(bool) & (feats["dv_status"] == "ok")]
    step_params = {"prep": None}
    for block, keys in current_params().items():
        stored = {}
        for key, now in keys.items():
            seen = {json.dumps((common.read_cache(p, m).get(block) or {}).get(key), sort_keys=True)
                    for p, m in zip(focus_keys["platform"], focus_keys["media_id"])}
            if len(seen) != 1 or json.loads(seen.pop()) != as_stored(now):
                raise SystemExit(f"step '{block}': the 192 records do not share one setting equal to the code")
            stored[key] = as_stored(now)
        step_params[block] = stored

    _, focus = load()                                  # the statistics table; engagement is not used here
    ref = derived.caplen_reference(focus)
    card = json.loads((config.MODELS / "model_card.json").read_text(encoding="utf-8"))
    order = card["outputs"]["instagram_content_score"]["feature_order"]
    model = joblib.load(config.MODELS / "instagram_content_logreg.joblib")
    if list(model.feature_names_in_) != order:
        raise SystemExit("the saved Instagram model's inputs differ from the model card's feature order")
    base = json.loads((config.MODELS / "base_rate.json").read_text(encoding="utf-8"))
    schema = {
        "decision": "D-055", "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "content_features": list(RAW.values()), "feature_order": order,
        "caplen_reference": ref, "step_params": step_params,
        "ranges": {"duration_sec": [float(feats["duration_sec"].min()), float(feats["duration_sec"].max())],
                   "aspect_ratio": [float(feats["aspect_ratio"].min()), float(feats["aspect_ratio"].max())],
                   "followers": base["followers_range"], "max_sec": MAX_SEC},
        "files": {f: sha256(config.MODELS / f) for f in FILES},
    }
    SCHEMA.write_text(json.dumps(schema, indent=1), encoding="utf-8")
    return schema


def artefacts() -> dict:
    """Load the schema and the saved models, refusing if a model file changed since the schema was built."""
    import joblib
    if not SCHEMA.exists():
        raise SystemExit("models/serving_schema.json is missing - run python -m src.serve.pipeline --build-schema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for f, h in schema["files"].items():
        if sha256(config.MODELS / f) != h:
            raise SystemExit(f"models/{f} changed after the schema was built - rebuild it (D-055)")
    model = joblib.load(config.MODELS / "instagram_content_logreg.joblib")
    if list(model.feature_names_in_) != schema["feature_order"]:
        raise SystemExit("the saved Instagram model's inputs are not in the trained order")
    read = lambda f: json.loads((config.MODELS / f).read_text(encoding="utf-8"))  # noqa: E731
    return {"schema": schema, "model": model, "card": read("model_card.json"), "base": read("base_rate.json"),
            "ref": read("reference_quantiles.json")}


# ------------------------------------------------------------------------------------------ inputs
def probe(video_path: Path, ranges: dict) -> dict:
    """D-055 section 2: refuse what the training data never contained; flag what it barely did."""
    pr = common.ffprobe(video_path)
    if not pr.get("probe_ok") or not pr.get("width") or not pr.get("height"):
        raise StepFailed("this file could not be opened as a video")
    if not pr.get("has_audio"):
        raise StepFailed("this video has no sound track; every video the tool learned from had one")
    if pr["duration_sec"] > MAX_SEC:
        raise StepFailed(f"this video is {pr['duration_sec']:.0f} seconds long; the tool covers short videos of "
                         f"up to {MAX_SEC:.0f} seconds")
    aspect = pr["width"] / pr["height"]
    lo_d, _ = ranges["duration_sec"]
    lo_a, hi_a = ranges["aspect_ratio"]
    return {"duration_sec": pr["duration_sec"], "aspect_ratio": round(aspect, 4),
            "shorter_than_training": pr["duration_sec"] < lo_d,
            "shape_outside_training": not (lo_a - 1e-3 <= aspect <= hi_a + 1e-3)}


def feature_row(doc: dict, caption_known: bool) -> pd.DataFrame:
    """The video's record -> one row of candidate features, flattened exactly as the corpus was."""
    df = pd.DataFrame([assemble.flatten(doc)])
    if not caption_known:
        for c in CAPTION_FIELDS:
            df[c] = None
        kw = doc.get("keywords") or {}
        for g in KW_GROUPS:                       # a hit in the speech is certain; a miss is not
            speech_hit = "transcript_en" in (kw.get(f"{g}_source") or "")
            df[g] = pd.Series([True if speech_hit else None], dtype=object)
    return derived.keyword_composites(df)


def model_inputs(row: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """Candidate features -> the model's inputs in the trained order, with the training derivations."""
    d = row.copy()
    for c in schema["content_features"] + ["cuts_per_sec", "mean_face_area", "caption_char_len"]:
        if c in d and c not in YES_NO:
            d[c] = pd.to_numeric(d[c])
    d = derived.video_measures(d)
    d["caplen_lang"] = derived.caplen_lang(d, schema["caplen_reference"])
    d["kw_event"] = derived.flag01(d["kw_event"])
    d["kw_promotional"] = derived.flag01(d["kw_promotional"])
    d["creator_collab_f"] = derived.flag01(d["creator_collab"])
    return d[schema["feature_order"]].astype(float)


# ------------------------------------------------------------------------------------------ outputs
def percentile(v: float, qv: list[float], qs: list[float]) -> dict:
    """Where a value sits among the reference videos, from their stored 5% steps: straight-line
    interpolation between steps; a value equal to several steps (many videos share it, e.g. 0) gets the
    middle of their range."""
    if v is None or not np.isfinite(v):
        return {"pct": None, "beyond": None}
    qv, qs = np.asarray(qv, float), np.asarray(qs, float)
    if v < qv[0]:
        return {"pct": 0.0, "beyond": "below"}
    if v > qv[-1]:
        return {"pct": 100.0, "beyond": "above"}
    lo, hi = np.searchsorted(qv, v, "left"), np.searchsorted(qv, v, "right")
    if hi > lo:
        return {"pct": float(qs[lo:hi].mean()), "beyond": None}
    x0, x1, y0, y1 = qv[lo - 1], qv[lo], qs[lo - 1], qs[lo]
    return {"pct": float(y0 + (y1 - y0) * (v - x0) / (x1 - x0)), "beyond": None}


def base_rate(art: dict, platform: str, followers: float | None) -> dict | None:
    """D-053/D-054: typical rate and 80% interval for a new account of this platform and size."""
    from src.serve.build_models import base_predict
    if not followers or followers <= 0:
        return None
    b = art["base"]
    expected = ["Intercept", "C(platform, Treatment('youtube'))[T.instagram]", "log_followers"]
    if list(b["fixed_effects"]) != expected:
        raise SystemExit("base_rate.json terms are not in the expected order")
    bb = {"beta": np.array(list(b["fixed_effects"].values())), "cov": np.array(b["fixed_effects_cov"]),
          "var_account": b["var_account"], "var_resid": b["var_resid"]}
    mean, sd = base_predict(bb, pd.Series([platform]), pd.Series([np.log10(float(followers))]))
    half = b["z"] * sd[0] * b["widen"]
    lo, mid, hi = 10 ** (mean[0] - half), 10 ** mean[0], 10 ** (mean[0] + half)
    flo, fhi = b["followers_range"]
    cov = b["g3_coverage"]["after_widening"][platform]
    return {"rate_typical": mid, "rate_80": [lo, hi], "likes_comments_80": [lo * followers, hi * followers],
            "followers": float(followers), "followers_outside_training": not (flo <= followers <= fhi),
            "interval_coverage_on_held_out_accounts": cov, "interval_under_covered": cov < 0.70,
            "widened_by": b["widen"]}


def instagram_position(art: dict, X: pd.DataFrame) -> dict:
    """D-054: the score only as a position - the share of the 120 training scores strictly below it."""
    s = float(art["model"].predict_proba(X[art["schema"]["feature_order"]])[:, 1][0])
    ref = np.asarray(art["card"]["outputs"]["instagram_content_score"]["training_scores_sorted"], float)
    s6 = round(s, 6)                                   # the stored scores are rounded to 6 places
    return {"higher_than_pct_of_120": round(100.0 * float((ref < s6).mean()), 1), "score": s6,
            "label": art["card"]["outputs"]["instagram_content_score"]["label"], "probability_shown": False}


def diagnostics(art: dict, row: pd.DataFrame, X: pd.DataFrame, platform: str) -> dict:
    ref = art["ref"]
    out = {}
    for c in art["schema"]["content_features"]:
        v = X[c].iloc[0] if c in X else pd.to_numeric(row[c]).iloc[0]
        q = ref["features"].get(c)
        if q is None:
            continue
        out[c] = {"value": None if pd.isna(v) else float(v),
                  "among_192": percentile(v, q["all"], ref["quantiles_at"]),
                  f"among_{platform}": percentile(v, q[platform], ref["quantiles_at"])}
    return out


def missing_inputs(X: pd.DataFrame, doc: dict, caption_known: bool, collab_known: bool) -> dict:
    asr_status = (doc.get("asr") or {}).get("status")
    return {"inputs_missing": [c for c in X.columns if pd.isna(X[c].iloc[0])],
            "caption_given": caption_known, "collaboration_given": collab_known,
            "speech": asr_status, "filled_by": "the saved model's training median (as in training)"}


def hand_code_answers(art: dict, answers: dict | None, platform: str) -> dict | None:
    """Passed through for the diagnostics page only - never a model input (D-051)."""
    if not answers:
        return None
    hc = art["ref"]["hand_codes"]
    return {h: {"answer": answers[h], "label": hc[h]["label"], "share_among_192": hc[h]["all"],
                f"share_among_{platform}": hc[h][platform]} for h in answers if h in hc}


# ------------------------------------------------------------------------------------------ one video
def predict(video_path: Path, platform: str, caption: str | None = None, followers: float | None = None,
            creator_collab: bool | None = None, title: str | None = None, answers: dict | None = None,
            work: Path | None = None, key: tuple[str, str] | None = None, log=print) -> dict:
    """Measure one video and return every output as values. `caption=None` means not given."""
    if platform not in ("instagram", "youtube"):
        raise ValueError("platform must be 'instagram' or 'youtube'")
    art = artefacts()
    video_path = Path(video_path).resolve()
    checks = probe(video_path, art["schema"]["ranges"])
    file_hash = sha256(video_path)[:16]
    if key is None:
        key = (platform, "v" + file_hash)
    if work is None:
        work = SERVE / "runs" / f"{file_hash}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    try:                                     # the training code records paths inside the project folder
        video_path.relative_to(config.ROOT)
    except ValueError:
        import shutil
        local = Path(work) / "media" / f"{file_hash}{video_path.suffix.lower()}"
        local.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(video_path, local)
        video_path = local
    job = {"work": str(work), "platform": key[0], "media_id": key[1], "video_path": str(video_path),
           "caption": caption, "title": title, "creator_collab": creator_collab, "file_sha256_16": file_hash}
    measured = measure(job, log=log)
    doc = measured["doc"]
    row = feature_row(doc, caption_known=caption is not None)
    X = model_inputs(row, art["schema"])
    result = {
        "video": {"file_sha256_16": file_hash, "platform": platform, **checks, "work": str(work)},
        "base_rate": base_rate(art, platform, followers),
        "instagram_score": instagram_position(art, X) if platform == "instagram" else None,
        "diagnostics": diagnostics(art, row, X, platform),
        "missing": missing_inputs(X, doc, caption is not None, creator_collab is not None),
        "hand_codes": hand_code_answers(art, answers, platform),
        "model_inputs": {c: (None if pd.isna(v) else float(v)) for c, v in X.iloc[0].items()},
        "timing": {"total_sec": measured["total_sec"], "steps": measured["steps"]},
        "gates": art["card"]["gates"],
    }
    (Path(work) / "result.json").write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="12.3 - measure one video and compute the tool's outputs.")
    ap.add_argument("--build-schema", action="store_true")
    ap.add_argument("--video")
    ap.add_argument("--platform", choices=["instagram", "youtube"])
    ap.add_argument("--caption-file", help="UTF-8 text file with the caption (YouTube: title, line break, "
                                           "description). Leave out if not known.")
    ap.add_argument("--title", help="YouTube title (optional; not a model input)")
    ap.add_argument("--followers", type=float)
    ap.add_argument("--collab", choices=["yes", "no", "unknown"], default="unknown")
    args = ap.parse_args()
    if args.build_schema:
        s = build_schema()
        print(f"-> {SCHEMA.relative_to(config.ROOT)}: {len(s['feature_order'])} inputs in the trained order, "
              f"settings of {len(s['step_params']) - 1} steps, caption-length reference for "
              f"{sorted(s['caplen_reference']['by_language'])}")
        return
    if not (args.video and args.platform):
        ap.error("--video and --platform are required")
    caption = Path(args.caption_file).read_text(encoding="utf-8") if args.caption_file else None
    collab = {"yes": True, "no": False, "unknown": None}[args.collab]
    try:
        r = predict(Path(args.video), args.platform, caption, args.followers, collab, args.title)
    except StepFailed as exc:
        raise SystemExit(f"Not measured: {exc}")
    print(json.dumps({k: r[k] for k in ("video", "base_rate", "instagram_score", "missing", "timing")},
                     indent=1, default=float))


if __name__ == "__main__":
    main()

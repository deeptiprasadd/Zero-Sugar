"""Task 5.4 - is a Coca-Cola product on screen, and from when (docs/05 Block A; H2, RQ4, 5.17).

Reuses the CLIP embeddings already on disk (`clip_vitl14_frames.npy`, 45,870 squares from 15,290
frames, made 2026-09-22) - **no model download and no re-encoding**, only a matrix multiply
against text prompts.

**Everything below is fixed before any score is looked at.** The D-029 Zero Sugar screen failed
because its rule was tuned after the fact and its video score was the *best of ~150 squares*,
which saturates: 96% of videos scored >= 0.5 because any dark object won the prompt comparison
(`reports/clip_zero_sugar_calibration.md`). Three changes follow from that:

1. **A frame's score is the mean of its three squares, not the best.** "Best square" is what
   saturated. The max is computed too, and reported only as a sensitivity check.
2. **The prompt list gives dark and logo-only frames somewhere to go** - "a dark scene" and "a
   logo on a sign" are non-product options, so a black object no longer has to be a can.
3. **The primary feature needs no threshold at all**: `product_prob_mean`, the mean product
   probability over the one-per-second frames. Thresholded features are reported beside it with
   their sensitivity at 0.4 / 0.5 / 0.6.

Features (one-per-second grid frames only, as docs/05 section 5.3 requires for time-based
measures, so a video with many shots is not weighted differently from one with few):

    product_prob_mean        mean product probability over the grid frames    (primary)
    product_prob_median      the same, median
    product_visible_frac     share of grid frames scoring >= 0.5             (+ 0.4 / 0.6)
    time_to_first_product    seconds to the first frame >= 0.5; null if never
    time_to_first_product_frac  the same as a share of the video's length
    product_frames_n         how many frames the video contributed

**Validation, and the gate, both decided now.** Truth is the researcher's 60 blind codes
(`zero_sugar_visible`, read-only): `zero_sugar` or `other_coca_cola` means a Coca-Cola product
was visible (54 videos), `no_product` means none (5), `unsure` is dropped (1). The negative class
is **tiny**, which is stated with every number below and is the honest limit of this check.

    Gate A  ROC AUC of product_prob_mean for product-visible vs no-product >= 0.70
    Gate B  all 5 no-product videos fall in the bottom half of the corpus by product_prob_mean
    Gate C  the measure is not near-constant: 10th-90th percentile range >= 0.10

If A and B pass, the features are used and the reliability figures are reported with them. If
either fails, **product visibility is reported as not measured** and the YOLO fallback
(`ultralytics`, already installed) is tried before anything is used - never a quiet threshold
change to make a gate pass. `product_mean_area` (docs/05 Block A) is **not measurable this way**:
CLIP scores a whole square and gives no box, so area would be invented. It waits for YOLO or is
dropped.

Usage:
    python -m src.features.product --validate      # scores + gates, writes nothing
    python -m src.features.product                 # validate, then write if the gates pass
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402
from src.features.clip_zero_sugar import ARCH, EMB, EMB_META, REPO, WEIGHTS  # noqa: E402

SUMMARY = config.INTERIM / "product_summary.csv"
# This attempt keeps its own report; the second attempt (YOLO) writes
# reports/product_detection_validation.md, so neither overwrites the other's record.
CALIB = config.REPORTS / "product_detection_attempt1_clip.md"
CODES = config.DATA / "coding" / "manual_codes_FINAL.csv"

PRODUCT_PROMPTS = [
    "a photo of a Coca-Cola can",
    "a photo of a red Coca-Cola can",
    "a photo of a black Coca-Cola Zero Sugar can",
    "a photo of a Coca-Cola glass bottle",
    "a photo of a Coca-Cola plastic bottle",
    "a person holding a Coca-Cola drink",
    "a Coca-Cola cup with a straw",
    "a Coca-Cola bottle on a table",
    "a glass of cola with ice",
]
OTHER_PROMPTS = [
    "a photo of people talking",
    "a photo of a crowd at an event",
    "a photo of food with no drink",
    "a photo of a sports stadium",
    "a photo of a city street",
    "a photo of nature",
    "text on a plain background",
    "a close-up of a person's face",
    "a photo of a room with no drink in it",
    "a dark scene",                     # dark frames need a home that is not a black can
    "a photo of a logo on a sign",      # a logo alone is not a product on screen
    "a photo of a football match",
]
THRESHOLDS = (0.4, 0.5, 0.6)
MAIN_THRESHOLD = 0.5
GATE_AUC, GATE_SPREAD = 0.70, 0.10
PARAMS = {"model": REPO, "square_reduce": "mean", "grid_frames_only": True,
          "threshold": MAIN_THRESHOLD, "n_product_prompts": len(PRODUCT_PROMPTS),
          "n_other_prompts": len(OTHER_PROMPTS), "version": 1}


# ------------------------------------------------------------------ scoring
def frame_table() -> pd.DataFrame:
    """One row per grid frame: platform, media_id, t, product probability (mean and max square)."""
    import open_clip
    import torch
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(REPO, WEIGHTS, local_files_only=True)
    model, _, _ = open_clip.create_model_and_transforms(ARCH, pretrained=path)
    tok = open_clip.get_tokenizer(ARCH)
    model = model.eval()
    with torch.no_grad():
        txt = model.encode_text(tok(PRODUCT_PROMPTS + OTHER_PROMPTS))
        txt = (txt / txt.norm(dim=-1, keepdim=True)).float().numpy()
        scale = float(model.logit_scale.exp().item())

    emb = np.load(EMB)
    sq = pd.read_parquet(EMB_META)
    if len(emb) != len(sq):
        raise SystemExit(f"embeddings and metadata disagree: {len(emb)} rows vs {len(sq)}")
    logits = scale * emb.astype(np.float32) @ txt.T
    logits -= logits.max(axis=1, keepdims=True)
    p = np.exp(logits)
    p /= p.sum(axis=1, keepdims=True)
    sq["prod"] = p[:, :len(PRODUCT_PROMPTS)].sum(axis=1)

    # Keep the one-per-second grid frames only (docs/05 section 5.3).
    grid = set()
    for _, r in common.video_index().iterrows():
        for fr in common.frame_list(r["platform"], r["media_id"], role="grid"):
            grid.add(str(Path(fr["file"]).relative_to(config.ROOT)))
    sq["is_grid"] = sq["file"].isin(grid)
    g = sq[sq["is_grid"]]
    if g.empty:
        raise SystemExit("no grid frames matched the embedding metadata - check frame roles")
    return (g.groupby(["platform", "media_id", "t"], as_index=False)
            .agg(prod_mean_sq=("prod", "mean"), prod_max_sq=("prod", "max")))


def video_table(frames: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (platform, media_id), g in frames.groupby(["platform", "media_id"]):
        g = g.sort_values("t")
        pr = g["prod_mean_sq"].to_numpy()
        t = g["t"].to_numpy()
        doc = common.read_cache(platform, media_id)
        duration = float((doc.get("prep") or {}).get("video_duration_sec") or np.nan)
        hit = t[pr >= MAIN_THRESHOLD]
        row = {"platform": platform, "media_id": media_id, "product_frames_n": len(g),
               "product_prob_mean": round(float(pr.mean()), 4),
               "product_prob_median": round(float(np.median(pr)), 4),
               "product_prob_max": round(float(pr.max()), 4),
               "product_prob_mean_maxsq": round(float(g["prod_max_sq"].mean()), 4),
               "time_to_first_product": round(float(hit[0]), 2) if len(hit) else None}
        for th in THRESHOLDS:
            row[f"product_visible_frac_{th:g}"] = round(float((pr >= th).mean()), 4)
        row["product_visible_frac"] = row[f"product_visible_frac_{MAIN_THRESHOLD:g}"]
        row["time_to_first_product_frac"] = (round(float(hit[0]) / duration, 4)
                                             if len(hit) and duration and duration > 0 else None)
        rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ validation
def truth() -> pd.DataFrame:
    """Blind codes only. Any Coca-Cola product visible (1) vs none (0); 'unsure' dropped."""
    c = pd.read_csv(CODES, dtype={"media_id": str})
    c = c[c["zero_sugar_visible"].isin(["zero_sugar", "other_coca_cola", "no_product"])]
    return pd.DataFrame({"platform": c["platform"], "media_id": c["media_id"],
                         "y": (c["zero_sugar_visible"] != "no_product").astype(int),
                         "code": c["zero_sugar_visible"]})


def auc_ci(score: np.ndarray, y: np.ndarray, n_boot: int = 2000, seed: int = 20260928):
    def auc(s, yy):
        pos, neg = s[yy == 1], s[yy == 0]
        if not len(pos) or not len(neg):
            return np.nan
        # rank-based AUC, ties counted as half
        return float((np.greater.outer(pos, neg).sum() + 0.5 * np.equal.outer(pos, neg).sum())
                     / (len(pos) * len(neg)))
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y))
        if len(set(y[i])) == 2:
            boots.append(auc(score[i], y[i]))
    lo, hi = (np.nanpercentile(boots, [2.5, 97.5]) if boots else (np.nan, np.nan))
    return auc(score, y), lo, hi


def validate(videos: pd.DataFrame) -> tuple[bool, str]:
    t = truth().merge(videos, on=["platform", "media_id"], how="left")
    missing = t["product_prob_mean"].isna().sum()
    s, y = t["product_prob_mean"].to_numpy(dtype=float), t["y"].to_numpy()
    a, lo, hi = auc_ci(s, y)
    a_max, _, _ = auc_ci(t["product_prob_mean_maxsq"].to_numpy(dtype=float), y)
    a_frac, _, _ = auc_ci(t["product_visible_frac"].to_numpy(dtype=float), y)

    videos = videos.copy()
    videos["pct"] = videos["product_prob_mean"].rank(pct=True)
    neg = t[t["y"] == 0].merge(videos[["platform", "media_id", "pct"]],
                              on=["platform", "media_id"], how="left")
    spread = (videos["product_prob_mean"].quantile(.9) - videos["product_prob_mean"].quantile(.1))

    gate_a = bool(a >= GATE_AUC)
    gate_b = bool((neg["pct"] <= 0.5).all())
    gate_c = bool(spread >= GATE_SPREAD)
    lines = [
        "# 5.4 product on screen - validation (D-032 pending; gates fixed before scoring)",
        "",
        f"Truth: the researcher's blind codes, **{int((y == 1).sum())} videos with a Coca-Cola "
        f"product visible vs {int((y == 0).sum())} with none** ('unsure' dropped). The negative "
        "class is tiny, so every figure here is weak evidence and is reported as such.",
        "",
        "| Check | Result | Gate | Pass |",
        "|---|---|---|---|",
        f"| A. ROC AUC, `product_prob_mean` | **{a:.3f}** (95% CI {lo:.2f}-{hi:.2f}) | >= {GATE_AUC:.2f} | {'YES' if gate_a else 'NO'} |",
        f"| B. All no-product videos in the bottom half | ranks {', '.join(f'{v:.2f}' for v in neg['pct'])} | all <= 0.50 | {'YES' if gate_b else 'NO'} |",
        f"| C. Not near-constant (10th-90th spread) | {spread:.3f} | >= {GATE_SPREAD:.2f} | {'YES' if gate_c else 'NO'} |",
        "",
        f"Sensitivity: AUC using the **best** square instead of the mean is {a_max:.3f} "
        f"(the D-029 failure mode); AUC of the thresholded `product_visible_frac` is {a_frac:.3f}.",
        "",
        f"Median `product_prob_mean`: product visible {np.median(s[y == 1]):.3f}, "
        f"no product {np.median(s[y == 0]):.3f}.",
    ]
    if missing:
        lines.append(f"\n**{missing} coded videos had no score** - investigate before trusting this.")
    verdict = gate_a and gate_b
    lines += ["", f"**Verdict: {'gates A and B pass - features used' if verdict else 'FAILED - product visibility is not measured this way; try YOLO before using anything'}.**",
              f"(Gate C, spread, {'passed' if gate_c else 'failed'} - it guards against a constant feature, not against being wrong.)"]
    return verdict, "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="5.4 - product on screen, from the CLIP embeddings.")
    ap.add_argument("--validate", action="store_true", help="score and check the gates, write nothing")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    frames = frame_table()
    videos = video_table(frames)
    print(f"scored {len(frames)} grid frames from {len(videos)} videos")
    ok, text = validate(videos)
    CALIB.write_text(text + "\n", encoding="utf-8")
    print(f"\n{text}\n\n-> {CALIB.relative_to(config.ROOT)}")

    if args.validate:
        print("\n--validate: nothing written to the feature cache")
        return
    if not ok:
        print("\nGates failed: no feature written. Next step is the YOLO fallback, or reporting "
              "product visibility as not measured (docs/05 section 2A).")
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for _, r in videos.iterrows():
        payload = {k: (None if isinstance(v, float) and pd.isna(v) else v)
                   for k, v in r.items() if k not in ("platform", "media_id")}
        common.update_cache(r["platform"], r["media_id"], "product",
                            {**payload, "params": PARAMS, "processed_at": now})
    videos.to_csv(SUMMARY, index=False)
    print(f"-> {SUMMARY.relative_to(config.ROOT)}  ({len(videos)} rows)")


if __name__ == "__main__":
    main()

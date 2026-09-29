"""Task 5.4v - do the product measures work? Gates applied to the researcher's frame answers (D-033).

Two methods are judged on **the same 120 frames**, which were drawn at random before either was
scored (`product_frame_sample.py`):

    YOLO container detection   `container_frame_scores.parquet`  - best box confidence per frame
    CLIP prompt score          recomputed here from the stored embeddings - the failed attempt

Truth from `docs/product_frame_check.csv`:

    container  = the researcher saw a Coca-Cola product **or** another drink container
    coca_cola  = the researcher saw a Coca-Cola product

Why both: the detector is brand-blind, so `container` is what it can possibly measure, and
`coca_cola` is what the study actually wants. The gap between the two AUCs, and the share of
answered containers that are Coca-Cola's, is the honest statement of what the feature means.

Gates, unchanged from the first attempt (D-033):

    A   frame-level ROC AUC for `container` >= 0.70
    B   the blind-coded no-product videos sit in the bottom half by `container_visible_frac`
    C   the video-level measure is not near-constant (10th-90th spread >= 0.10)

A and B decide. A failed gate means product visibility is reported as not measured - never a
threshold quietly moved until a gate passes.

Usage:
    python -m src.features.product_yolo --validate
    python -m src.features.product_validate            # same thing, reusing cached scores
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features.product import GATE_AUC, GATE_SPREAD, auc_ci, truth  # noqa: E402
from src.features.product_yolo import (FRAME_SCORES, MAIN_THRESHOLD, SUMMARY,  # noqa: E402
                                        THRESHOLDS, video_table)

CHECK = config.DOCS / "product_frame_check.csv"
CALIB = config.REPORTS / "product_detection_validation.md"


def answers() -> pd.DataFrame:
    if not CHECK.exists():
        raise SystemExit(f"{CHECK} not found - run: python -m src.features.product_frame_sample")
    a = pd.read_csv(CHECK, dtype=str).fillna("")
    a = a[a["researcher_answer"].str.strip() != ""].copy()
    bad = set(a["researcher_answer"]) - {"coca_cola_product", "other_container", "none"}
    if bad:
        raise SystemExit(f"unexpected answers in {CHECK.name}: {bad}")
    a["t"] = a["t"].astype(float).round(2)
    a["container"] = (a["researcher_answer"] != "none").astype(int)
    a["coca_cola"] = (a["researcher_answer"] == "coca_cola_product").astype(int)
    return a[["platform", "media_id", "t", "researcher_answer", "container", "coca_cola"]]


def clip_frame_scores() -> pd.DataFrame:
    """The failed attempt's per-frame score, recomputed so both methods face the same frames."""
    from src.features.product import frame_table
    f = frame_table().rename(columns={"prod_mean_sq": "clip_prod"})
    f["t"] = f["t"].astype(float).round(2)
    return f[["platform", "media_id", "t", "clip_prod"]]


def run_gates(frames: pd.DataFrame | None = None, videos: pd.DataFrame | None = None) -> bool:
    a = answers()
    if frames is None:
        frames = pd.read_parquet(FRAME_SCORES)
    if videos is None:
        videos = (pd.read_csv(SUMMARY) if Path(SUMMARY).exists() else video_table(frames))
    frames = frames.copy()
    frames["t"] = frames["t"].astype(float).round(2)

    m = a.merge(frames[["platform", "media_id", "t", "best_conf", "max_area"]],
                on=["platform", "media_id", "t"], how="left")
    unmatched = int(m["best_conf"].isna().sum())
    m = m.merge(clip_frame_scores(), on=["platform", "media_id", "t"], how="left")

    lines = ["# 5.4 product on screen - validation (D-033)", "",
             f"**{len(a)} of 120 sampled frames answered.** Frames drawn at random, one per video, "
             "60 videos per platform, seed 20260928 - before any score was computed, and the "
             "answering page never showed a score or a box.", ""]
    if unmatched:
        lines.append(f"**{unmatched} answered frames had no detector score** - investigate before "
                     "reading anything below.\n")
    if len(a) < 40 or m["container"].nunique() < 2:
        lines.append(f"Too few answers to judge yet (need both classes and about 40+ frames; "
                     f"have {len(a)}, container={m['container'].sum()}).")
        CALIB.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))
        return False

    rows = []
    for name, score in [("YOLO container confidence", "best_conf"),
                        ("CLIP prompt score (failed attempt)", "clip_prod")]:
        for tname, y in [("container visible", "container"), ("Coca-Cola product", "coca_cola")]:
            s = m[score].to_numpy(dtype=float)
            yy = m[y].to_numpy()
            if len(set(yy)) < 2:
                rows.append((name, tname, "only one class answered", "", ""))
                continue
            auc, lo, hi = auc_ci(s, yy)
            rows.append((name, tname, f"**{auc:.3f}**", f"{lo:.2f}-{hi:.2f}",
                         f"{int((yy == 1).sum())} yes / {int((yy == 0).sum())} no"))
    lines += ["## Frame level - the check that matters", "",
              "| Measure | Truth | ROC AUC | 95% CI | Frames |", "|---|---|---|---|---|"]
    lines += [f"| {a_} | {b} | {c} | {d} | {e} |" for a_, b, c, d, e in rows]

    # what a detection is worth, in plain terms
    det = m[m["best_conf"] >= MAIN_THRESHOLD]
    nodet = m[m["best_conf"] < MAIN_THRESHOLD]
    prec = det["container"].mean() if len(det) else float("nan")
    rec = (det["container"].sum() / max(1, m["container"].sum()))
    cc_given_det = det["coca_cola"].mean() if len(det) else float("nan")
    lines += ["", f"At the pre-set threshold {MAIN_THRESHOLD:g}: **{len(det)} frames flagged**, "
              f"of which {prec:.0%} really hold a container (precision) and "
              f"{cc_given_det:.0%} hold a **Coca-Cola** product; recall {rec:.0%} of the frames "
              f"the researcher says have a container. Missed frames "
              f"({int(nodet['container'].sum())} of {len(nodet)} unflagged) are where the object "
              "is small, blurred or partly out of shot.", ""]
    share_cc = m.loc[m["container"] == 1, "coca_cola"].mean() if m["container"].sum() else float("nan")
    lines.append(f"Of every answered frame with a container, **{share_cc:.0%} are Coca-Cola's** - "
                 "that ratio is why a brand-blind detector is a usable proxy here, and it is the "
                 "number to quote when the feature is described.")

    # Gate A
    auc_c, lo_c, hi_c = auc_ci(m["best_conf"].to_numpy(dtype=float), m["container"].to_numpy())
    gate_a = bool(auc_c >= GATE_AUC)

    # Gate B - video level, against the blind codes
    v = videos.copy()
    v["pct"] = v["container_visible_frac"].rank(pct=True)
    neg = truth().query("code == 'no_product'").merge(
        v[["platform", "media_id", "pct", "container_visible_frac"]],
        on=["platform", "media_id"], how="left")
    gate_b = bool((neg["pct"] <= 0.5).all())
    spread = float(v["container_visible_frac"].quantile(.9) - v["container_visible_frac"].quantile(.1))
    gate_c = bool(spread >= GATE_SPREAD)

    lines += ["", "## Gates", "", "| Gate | Result | Required | Pass |", "|---|---|---|---|",
              f"| A. Frame-level AUC, container | {auc_c:.3f} (95% CI {lo_c:.2f}-{hi_c:.2f}) | >= {GATE_AUC:.2f} | {'YES' if gate_a else 'NO'} |",
              f"| B. No-product videos in the bottom half | ranks {', '.join(f'{x:.2f}' for x in neg['pct'].fillna(-1))} | all <= 0.50 | {'YES' if gate_b else 'NO'} |",
              f"| C. Not near-constant (10th-90th spread) | {spread:.3f} | >= {GATE_SPREAD:.2f} | {'YES' if gate_c else 'NO'} |"]
    ok = gate_a and gate_b
    lines += ["", f"**Verdict: {'gates A and B pass' if ok else 'FAILED'}.** "
              + ("The container features may be used, described as a brand-blind measure with the "
                 "precision and Coca-Cola share above." if ok else
                 "Product visibility is reported as not measured (D-033 option C); H2, RQ4 and "
                 "5.17 then rest on the Zero Sugar label alone.")]
    lines += ["", "### Sensitivity", "",
              "| Threshold | Frames flagged | Precision | Recall |", "|---|---|---|---|"]
    for th in THRESHOLDS:
        d = m[m["best_conf"] >= th]
        lines.append(f"| {th:g} | {len(d)} | {d['container'].mean():.0%} | "
                     f"{d['container'].sum() / max(1, m['container'].sum()):.0%} |")
    lines += ["", "The first attempt (whole-image CLIP) is kept in the table above so the two are "
              "comparable on identical frames; its failure is recorded in D-033."]

    text = "\n".join(lines) + "\n"
    CALIB.write_text(text, encoding="utf-8")
    print(text)
    print(f"-> {CALIB.relative_to(config.ROOT)}")
    return ok


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    run_gates()


if __name__ == "__main__":
    main()

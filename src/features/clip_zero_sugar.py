"""Task 5.4, first use (D-029): visual Zero Sugar screen with CLIP, for the researcher to confirm.

The platform comparison is confounded with product because text finds only a fraction of the
Zero Sugar videos. This module scores every stored frame (5.3) with CLIP and produces a short
list of videos likely to show Zero Sugar packaging, with frames, for the researcher to confirm
by eye - the D-018 standard. **It never changes a label.** Confirmed answers go into
`docs/zero_sugar_visual_check.csv`; `src/screen/zero_sugar_labels.py` applies them.

Everything below was fixed before any score was looked at (2026-09-22):

*   **Model:** open_clip ViT-L-14, LAION-2B (`laion/CLIP-ViT-L-14-laion2B-s32B-b82K`, one
    1.71 GB safetensors file, MIT), float16 on the GPU.
*   **Frames:** every stored frame of every corpus video - the one-per-second grid and one per
    shot. Each frame is scored as **three overlapping squares, top / middle / bottom**, each the
    full frame width. CLIP's default centre crop would discard the top and bottom thirds of a
    vertical frame, where a hand-held can or an end-card pack often sits.
*   **Frame score:** softmax over a fixed prompt set (Zero Sugar packaging vs red Coca-Cola,
    Diet Coke, logo-only and non-product scenes); score = total probability of the Zero Sugar
    prompts; frame score = best of its three squares.
*   **Video score:** the maximum frame score - the codebook's definition is "a black can or
    bottle *anywhere* in the video" (reports/shared/codebook.md, item 5).
*   **Ground truth:** the researcher's blind codes (`zero_sugar_visible`, 60 videos, 59 once
    "unsure" is set aside; read only) and the researcher's D-018 labels: 106 curated Reels
    (Zero Sugar) and 1 curated Reel relabelled Original (not Zero Sugar). Where a curated Reel
    was also blind-coded, the blind code is its truth.
*   **Threshold rule:** the score that maximises F2 (recall weighted twice precision, because
    every flag is checked by eye, so a missed video costs more than an extra one to look at);
    ties go to the higher threshold.
*   **Never evaluated on the videos it was tuned on:**
    - *Leave-one-out:* each blind-coded video is judged with a threshold chosen on all the other
      labelled videos. Precision and recall are reported over the 59, and per platform.
    - *Transfer:* a threshold chosen on Instagram data only, tested on the 29 blind-coded Shorts.
    - The threshold used for the final list is chosen on all labelled videos; it produces the
      list the researcher checks, not a performance figure.

Outputs:
    data/interim/clip_vitl14_frames.npy (+ _meta.parquet)  image embeddings, reused by 5.4
    data/interim/clip_zero_sugar_scores.csv   one row per video: score, flag, top frames
    reports/clip_zero_sugar_calibration.md    precision, recall, thresholds (internal)
    docs/zero_sugar_visual_check.csv          the list the researcher answers
    reports/zero_sugar_visual_check/*.jpg     one 4-frame sheet per listed video

Usage:
    python -m src.features.clip_zero_sugar --embed      # encode frames (GPU, ~15 min)
    python -m src.features.clip_zero_sugar --score      # score, calibrate, write the list
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

REPO = "laion/CLIP-ViT-L-14-laion2B-s32B-b82K"
WEIGHTS = "open_clip_pytorch_model.safetensors"
ARCH = "ViT-L-14"
EMB = config.INTERIM / "clip_vitl14_frames.npy"               # one row per frame square
EMB_META = config.INTERIM / "clip_vitl14_frames_meta.parquet" # which frame/square each row is
SCORES = config.INTERIM / "clip_zero_sugar_scores.csv"
CALIB = config.REPORTS / "clip_zero_sugar_calibration.md"
CHECK = config.DOCS / "zero_sugar_visual_check.csv"
SHEETS = config.REPORTS / "zero_sugar_visual_check"
CODES = config.ROOT / "data" / "coding" / "manual_codes_FINAL.csv"

ZS_PROMPTS = [
    "a photo of a black Coca-Cola Zero Sugar can",
    "a photo of a Coca-Cola Zero Sugar bottle with a black label",
    "a black can of Coke Zero",
    "a person holding a black Coca-Cola Zero Sugar can",
    "Coca-Cola Zero Sugar packaging",
]
OTHER_PROMPTS = [
    "a photo of a red Coca-Cola can",
    "a photo of a red Coca-Cola bottle",
    "a person holding a red Coca-Cola can",
    "a silver Diet Coke can",
    "a Coca-Cola logo on a sign",
    "a photo of people",
    "a photo of food",
    "a photo of a sports stadium",
    "text on a plain background",
    "a photo with no drink in it",
]
FRAMES_TO_SHOW = 4


# ------------------------------------------------------------------------ model

def load_model():
    import open_clip
    import torch
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(REPO, WEIGHTS, local_files_only=True)
    model, _, preprocess = open_clip.create_model_and_transforms(ARCH, pretrained=path)
    tok = open_clip.get_tokenizer(ARCH)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device).eval()
    if device == "cuda":
        model = model.half()
    return model, preprocess, tok, device


def tiles(img):
    """Three overlapping full-width squares, top / middle / bottom (fewer if nearly square)."""
    w, h = img.size
    if h <= w * 1.15:
        return [img]
    offs = sorted({0, (h - w) // 2, h - w})
    return [img.crop((0, o, w, o + w)) for o in offs]


# ------------------------------------------------------------------------ embed

class _Frames:
    """Frames -> preprocessed squares, run in DataLoader workers so decoding keeps the GPU fed.

    (The first version decoded and cropped every 720x1280 JPEG on one CPU thread; the GPU sat at
    0% while it did.)
    """

    def __init__(self, items, preprocess):
        self.items, self.preprocess = items, preprocess

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        import torch
        from PIL import Image
        platform, media_id, t, rel = self.items[i]
        img = Image.open(config.ROOT / rel)
        if img.width >= 600:   # decode at half size: each square ends at 224 px either way
            img.draft("RGB", (img.width // 2, img.height // 2))
        sq = tiles(img.convert("RGB"))
        return torch.stack([self.preprocess(s) for s in sq]), [(platform, media_id, t, rel, k)
                                                               for k in range(len(sq))]


def _collate(batch):
    import torch
    return torch.cat([b[0] for b in batch]), [m for b in batch for m in b[1]]


def embed_all(workers: int = 6) -> None:
    import torch
    from torch.utils.data import DataLoader
    model, preprocess, _, device = load_model()
    items = []
    for _, r in common.video_index().iterrows():
        for fr in common.frame_list(r["platform"], r["media_id"]):
            items.append((r["platform"], r["media_id"], fr["t"],
                          str(Path(fr["file"]).relative_to(config.ROOT))))
    loader = DataLoader(_Frames(items, preprocess), batch_size=32, num_workers=workers,
                        collate_fn=_collate, persistent_workers=False)
    rows, embs = [], []
    t0 = time.time()
    log = config.INTERIM / "clip_embed_progress.log"
    with open(log, "w", encoding="utf-8") as lf:
        for n, (x, meta) in enumerate(loader, 1):
            x = x.to(device)
            if device == "cuda":
                x = x.half()
            with torch.no_grad():
                f = model.encode_image(x)
                f = f / f.norm(dim=-1, keepdim=True)
            embs.append(f.float().cpu().numpy().astype(np.float16))
            rows.extend(meta)
            if n % 50 == 0:
                lf.write(f"{n * 32}/{len(items)} frames, {len(rows)} squares, "
                         f"{(time.time() - t0) / 60:.1f} min\n")
                lf.flush()
    m = pd.DataFrame(rows, columns=["platform", "media_id", "t", "file", "tile"])
    # Two plain files: an array and a table. (A single .npz with a field named "file" failed on
    # save, after 20 minutes of encoding, because numpy reserves that name.)
    np.save(EMB, np.concatenate(embs))
    m.to_parquet(EMB_META, index=False)
    print(f"embedded {len(m)} squares from {m.groupby(['platform', 'media_id']).ngroups} videos "
          f"in {(time.time() - t0) / 60:.1f} min -> {EMB.relative_to(config.ROOT)}")


# ------------------------------------------------------------------------ score

def frame_scores() -> pd.DataFrame:
    import torch
    model, _, tok, device = load_model()
    with torch.no_grad():
        txt = model.encode_text(tok(ZS_PROMPTS + OTHER_PROMPTS).to(device))
        txt = (txt / txt.norm(dim=-1, keepdim=True)).float().cpu().numpy()
        scale = float(model.logit_scale.exp().item())
    emb = np.load(EMB)
    sq = pd.read_parquet(EMB_META)
    logits = scale * emb.astype(np.float32) @ txt.T
    logits -= logits.max(axis=1, keepdims=True)
    p = np.exp(logits); p /= p.sum(axis=1, keepdims=True)
    sq["zs"] = p[:, :len(ZS_PROMPTS)].sum(axis=1)
    # a frame's score is its best square
    return sq.groupby(["platform", "media_id", "t", "file"], as_index=False)["zs"].max()


def truth() -> pd.DataFrame:
    """Ground truth: blind codes first, then the researcher's D-018 curated labels."""
    codes = pd.read_csv(CODES, dtype={"media_id": str})
    codes = codes[codes["zero_sugar_visible"].isin(["zero_sugar", "other_coca_cola", "no_product"])]
    t = pd.DataFrame({"platform": codes["platform"], "media_id": codes["media_id"],
                      "y": (codes["zero_sugar_visible"] == "zero_sugar").astype(int),
                      "source": "blind_code"})
    ig = pd.read_parquet(config.PROCESSED / "instagram_corpus.parquet")
    ig = ig[ig["in_corpus"]]
    cur = pd.DataFrame({"platform": "instagram", "media_id": ig["shortcode"],
                        "y": (ig["corpus_reason"] == "curated_zero_sugar").astype(int),
                        "source": "curated_D018"})[ig["corpus_reason"].str.startswith("curated").values]
    cur = cur[~cur["media_id"].isin(t["media_id"])]           # blind code wins where both exist
    return pd.concat([t, cur], ignore_index=True)


def f2_threshold(scores: np.ndarray, y: np.ndarray) -> float:
    best, best_t = -1.0, 1.0
    for th in np.unique(scores)[::-1]:                        # high to low: ties keep the higher
        pred = scores >= th
        tp = int((pred & (y == 1)).sum()); fp = int((pred & (y == 0)).sum())
        fn = int((~pred & (y == 1)).sum())
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f2 = 5 * p * r / (4 * p + r) if p + r else 0.0
        if f2 > best + 1e-12:
            best, best_t = f2, float(th)
    return best_t


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    z = 1.96
    c = (k + z * z / 2) / (n + z * z)
    h = z * np.sqrt(k * (n - k) / n + z * z / 4) / (n + z * z)
    return (max(0.0, c - h), min(1.0, c + h))


def pr(pred: np.ndarray, y: np.ndarray) -> dict:
    tp = int((pred & (y == 1)).sum()); fp = int((pred & (y == 0)).sum())
    fn = int((~pred & (y == 1)).sum()); tn = int((~pred & (y == 0)).sum())
    return {"n": len(y), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": tp / (tp + fp) if tp + fp else float("nan"),
            "precision_ci": wilson(tp, tp + fp), "recall": tp / (tp + fn) if tp + fn else float("nan"),
            "recall_ci": wilson(tp, tp + fn)}


def corpus_labels() -> pd.DataFrame:
    yt = pd.read_parquet(config.PROCESSED / "youtube_corpus.parquet"); yt = yt[yt["in_corpus"]]
    ig = pd.read_parquet(config.PROCESSED / "instagram_corpus.parquet"); ig = ig[ig["in_corpus"]]
    a = pd.DataFrame({"platform": "youtube", "media_id": yt["video_id"].astype(str),
                      "url": "https://www.youtube.com/shorts/" + yt["video_id"].astype(str),
                      "label_now": yt["is_zero_sugar_before_D029"].astype(bool),
                      "selection": yt["selection"], "variant_text": yt["variant"]})
    b = pd.DataFrame({"platform": "instagram", "media_id": ig["shortcode"].astype(str),
                      "url": ig["permalink"], "label_now": ig["is_zero_sugar_before_D029"].astype(bool),
                      "selection": ig["selection"], "variant_text": ig["text_variant"]})
    return pd.concat([a, b], ignore_index=True)


def top_frames(fs: pd.DataFrame, k: int = FRAMES_TO_SHOW) -> list[tuple[float, str, float]]:
    """Best-scoring frames at least 1 s apart, shown in time order."""
    out: list[tuple[float, str, float]] = []
    for _, r in fs.sort_values("zs", ascending=False).iterrows():
        if all(abs(r["t"] - t) >= 1.0 for t, _, _ in out):
            out.append((float(r["t"]), r["file"], float(r["zs"])))
        if len(out) == k:
            break
    return sorted(out)


def sheet(path: Path, header: str, frames: list[tuple[float, str, float]]) -> None:
    """One image per listed video: its best frames side by side, for checking by eye."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    W = 300
    ims = []
    for t, f, s in frames:
        im = Image.open(config.ROOT / f).convert("RGB")
        im = im.resize((W, int(im.height * W / im.width)))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, 22), fill=(0, 0, 0))
        d.text((5, 3), f"{t:.1f}s   score {s:.2f}", font=font, fill=(255, 255, 255))
        ims.append(im)
    H = max(i.height for i in ims)
    out = Image.new("RGB", (max(1, len(ims)) * (W + 6), H + 30), (40, 40, 40))
    ImageDraw.Draw(out).text((6, 6), header, font=font, fill=(255, 230, 120))
    for n, im in enumerate(ims):
        out.paste(im, (n * (W + 6), 30))
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path, quality=88)


def score_and_list() -> None:
    fs = frame_scores()
    vid = fs.groupby(["platform", "media_id"], as_index=False)["zs"].max().rename(columns={"zs": "score"})
    lab = corpus_labels().merge(vid, on=["platform", "media_id"], how="left")
    tr = truth().merge(vid, on=["platform", "media_id"], how="inner")
    coded = tr[tr["source"] == "blind_code"].reset_index(drop=True)
    extra = tr[tr["source"] == "curated_D018"]

    # leave-one-out: each blind-coded video is judged by a threshold tuned without it
    loo_pred, loo_th = [], []
    for i in range(len(coded)):
        train = pd.concat([coded.drop(index=i), extra])
        th = f2_threshold(train["score"].values, train["y"].values)
        loo_th.append(th)
        loo_pred.append(bool(coded.at[i, "score"] >= th))
    coded["loo_pred"] = loo_pred
    res = {"all": pr(coded["loo_pred"].values, coded["y"].values)}
    for p in ("youtube", "instagram"):
        g = coded[coded["platform"] == p]
        res[p] = pr(g["loo_pred"].values, g["y"].values)
    # transfer: tuned on Instagram only, tested on the blind-coded Shorts
    ig_train = pd.concat([coded[coded["platform"] == "instagram"], extra])
    th_ig = f2_threshold(ig_train["score"].values, ig_train["y"].values)
    ytc = coded[coded["platform"] == "youtube"]
    res["transfer_ig_to_yt"] = pr((ytc["score"] >= th_ig).values, ytc["y"].values)
    # final threshold for the list the researcher checks - not an evaluation
    th_final = f2_threshold(tr["score"].values, tr["y"].values)

    # scores file, read by src/screen/zero_sugar_labels.annotate()
    lab["clip_flagged"] = lab["score"] >= th_final
    tops = {k: top_frames(g) for k, g in fs.groupby(["platform", "media_id"])}
    lab["top_frames"] = [" | ".join(f for _, f, _ in tops.get((p, m), []))
                         for p, m in zip(lab["platform"], lab["media_id"])]
    lab.assign(threshold=th_final)[["platform", "media_id", "score", "clip_flagged", "threshold",
                                    "top_frames"]].to_csv(SCORES, index=False)

    # the list the researcher answers
    codes = pd.read_csv(CODES, dtype={"media_id": str})[["platform", "media_id", "zero_sugar_visible"]]
    lab = lab.merge(codes.rename(columns={"zero_sugar_visible": "blind_code"}),
                    on=["platform", "media_id"], how="left")
    unlabelled = ~lab["label_now"] & (lab["selection"] == "systematic")
    flag = unlabelled & lab["clip_flagged"]
    coded_zs = unlabelled & (lab["blind_code"] == "zero_sugar")
    fyi = (lab["selection"] == "hand_picked") & lab["label_now"] & \
        lab["blind_code"].isin(["other_coca_cola", "no_product"])
    lab["why_listed"] = np.select(
        [flag & coded_zs, flag, coded_zs, fyi],
        ["clip_flag+blind_code", "clip_flag", "blind_code_only", "fyi_curated_vs_blind_code"], "")
    listed = lab[lab["why_listed"] != ""].sort_values(["platform", "why_listed", "score"],
                                                      ascending=[False, True, False])
    rows = []
    for _, r in listed.iterrows():
        fr = tops.get((r["platform"], r["media_id"]), [])
        sp = SHEETS / f"{r['platform']}_{r['media_id']}.jpg"
        sheet(sp, f"{r['platform']} {r['media_id']}  |  {r['why_listed']}  |  CLIP {r['score']:.2f} "
                  f"(threshold {th_final:.2f})  |  label now: "
                  f"{'Zero Sugar' if r['label_now'] else 'not identified'}", fr)
        rows.append({"platform": r["platform"], "media_id": r["media_id"], "url": r["url"],
                     "why_listed": r["why_listed"], "clip_score": round(float(r["score"]), 3),
                     "label_now": "zero_sugar" if r["label_now"] else "not_identified",
                     "text_variant": r["variant_text"], "blind_code": r["blind_code"],
                     **{f"frame_{k + 1}": (fr[k][1] if k < len(fr) else "")
                        for k in range(FRAMES_TO_SHOW)},
                     "sheet": str(sp.relative_to(config.ROOT)),
                     "researcher_answer": "", "researcher_note": ""})
    out = pd.DataFrame(rows)
    if CHECK.exists():   # never lose an answer already given
        old = pd.read_csv(CHECK, dtype=str).fillna("")
        keep = old[old["researcher_answer"].str.strip() != ""][
            ["platform", "media_id", "researcher_answer", "researcher_note"]]
        out = out.drop(columns=["researcher_answer", "researcher_note"]).merge(
            keep, on=["platform", "media_id"], how="left").fillna(
            {"researcher_answer": "", "researcher_note": ""})
    out.to_csv(CHECK, index=False, encoding="utf-8")

    def line(name: str, d: dict) -> str:
        return (f"| {name} | {d['n']} | {d['tp']} | {d['fp']} | {d['fn']} | {d['tn']} | "
                f"{d['precision']:.2f} ({d['precision_ci'][0]:.2f}-{d['precision_ci'][1]:.2f}) | "
                f"{d['recall']:.2f} ({d['recall_ci'][0]:.2f}-{d['recall_ci'][1]:.2f}) |")
    md = ["# CLIP Zero Sugar screen - calibration (D-029)\n",
          f"Model {ARCH} ({REPO}); frames scored as top/middle/bottom squares; video score = max "
          f"frame score. Threshold rule: maximise F2 on the training videos.\n",
          f"Ground truth: {len(coded)} blind-coded videos ({int(coded['y'].sum())} Zero Sugar); "
          f"{len(extra)} further curated Reels used for tuning only "
          f"({int(extra['y'].sum())} Zero Sugar, {int((extra['y'] == 0).sum())} relabelled Original).\n",
          "| Evaluation | n | TP | FP | FN | TN | Precision (95% CI) | Recall (95% CI) |",
          "|---|---|---|---|---|---|---|---|",
          line("Leave-one-out, all blind-coded", res["all"]),
          line("Leave-one-out, YouTube only", res["youtube"]),
          line("Leave-one-out, Instagram only", res["instagram"]),
          line("Transfer: tuned on Instagram, tested on YouTube", res["transfer_ig_to_yt"]),
          "",
          f"Leave-one-out thresholds ranged {min(loo_th):.3f}-{max(loo_th):.3f}. "
          f"Instagram-only threshold {th_ig:.3f}. **Final threshold for the list: {th_final:.3f}.**\n",
          f"Listed for the researcher: {len(out)} videos - " +
          ", ".join(f"{k} {v}" for k, v in out.groupby(["platform", "why_listed"]).size().items())]
    CALIB.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"\nwrote {SCORES.relative_to(config.ROOT)}, {CHECK.relative_to(config.ROOT)}, "
          f"{CALIB.relative_to(config.ROOT)}, {len(out)} sheets in {SHEETS.relative_to(config.ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="5.4 / D-029 - CLIP Zero Sugar screen.")
    ap.add_argument("--embed", action="store_true", help="encode all stored frames")
    ap.add_argument("--score", action="store_true", help="score, calibrate, write the check list")
    args = ap.parse_args()
    if args.embed:
        embed_all()
    if args.score:
        score_and_list()
    if not (args.embed or args.score):
        ap.print_help()


if __name__ == "__main__":
    main()

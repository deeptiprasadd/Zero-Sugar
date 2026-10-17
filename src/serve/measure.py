"""Task 12.3 - measure one video with the training feature code, in its own folder (D-055 section 3).

The tool must serve a new video the same inputs the models learned from, so it does not re-implement any
measurement: it calls the Phase 5 per-video functions in `src/features/` with their own settings, in the
order training ran them, and writes each result under the same block name of a per-video record.

**Its own folder.** Everything is written under `data/interim/serve/<run>/` (`features/`, `audio/`,
`frames/`), never into the training folders: the three folder locations in `src/features/common.py` are
pointed at the run folder inside this module's processes. A training measurement can therefore never be
overwritten, and a parity check (G4) cannot pass by reading a training value back.

**Separate processes, as in training.** Speech-to-text needs the CUDA 12 libraries loaded before
faster-whisper and no PyTorch in the same process (D-027), so the steps run in five groups, each in its own
Python process:

    video    5.1 preparation, 5.2 cuts, 5.3 frames + motion            (CPU)
    speech   5.6 speech-to-text                                        (graphics card, CUDA 12)
    signal   5.8 audio signal, 5.5 faces, 5.5 colour                   (CPU)
    gpu      5.8 sound events, 5.9 sentiment, 5.5 on-screen text       (graphics card, PyTorch)
    text     5.7 caption language, 5.16 keywords, caption counts       (CPU, no model)

Not run (D-055): the automated labels (5.12, D-038), music genre (D-033), product detection (D-037), CLIP.
Every model is read from disk; nothing is downloaded.

**Settings guard.** Before a step runs, its settings in the code are compared with the settings recorded for
the 192 training videos (`models/serving_schema.json`); a difference stops the run.

Used by `src.serve.pipeline`; one group is run as
    python -m src.serve.measure --job <run>/job.json --group video
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

SERVE = config.INTERIM / "serve"
SCHEMA = config.MODELS / "serving_schema.json"

GROUPS: dict[str, list[str]] = {
    "video": ["prep", "scenes", "frames"],
    "speech": ["asr"],
    "signal": ["audio_signal", "faces", "visual"],
    "gpu": ["audio_events", "sentiment", "ocr"],
    "text": ["language", "keywords", "meta"],
}


class StepFailed(RuntimeError):
    """A step could not measure this video; the message is meant for the person using the tool."""


# ------------------------------------------------------------------------------------------ settings
def current_params() -> dict[str, dict]:
    """The settings each step records in its block, as the code stands now (block -> {key: settings})."""
    from src.features import (asr, audio, faces_text, frames, keywords, language, metadata, scenes,
                              sentiment, visual)
    return {"scenes": {"params": scenes.PARAMS, "final_params": scenes.FINAL_PARAMS},
            "frames": {"params": frames.PARAMS}, "asr": {"params": asr.PARAMS},
            "audio_signal": {"params": audio.SIGNAL_PARAMS}, "audio_events": {"params": audio.EVENTS_PARAMS},
            "sentiment": {"params": sentiment.PARAMS}, "faces": {"params": faces_text.FACE_PARAMS},
            "ocr": {"params": faces_text.OCR_PARAMS}, "visual": {"params": visual.PARAMS},
            "language": {"params": language.PARAMS}, "keywords": {"params": keywords.PARAMS},
            "meta": {"params": metadata.PARAMS}}


def as_stored(x):
    return json.loads(json.dumps(x))     # tuples become lists, as in the JSON records


def guard(block: str) -> None:
    if not SCHEMA.exists():
        raise SystemExit(f"{SCHEMA.relative_to(config.ROOT)} is missing - run python -m src.serve.pipeline "
                         "--build-schema")
    stored = json.loads(SCHEMA.read_text(encoding="utf-8"))["step_params"].get(block)
    if stored is None:
        return                                           # preparation records no settings block
    now = as_stored(current_params()[block])
    if now != stored:
        raise SystemExit(f"step '{block}': the settings in the code differ from the ones the 192 training "
                         "videos were measured with - stopped (D-055 section 3)")


# ------------------------------------------------------------------------------------------ the steps
def point_at(work: Path) -> None:
    """Send every read and write of the feature code to this run's folder."""
    common.CACHE = work / "features"
    common.AUDIO = work / "audio"
    common.FRAMES = work / "frames"
    for d in (common.CACHE, common.AUDIO, common.FRAMES):
        d.mkdir(parents=True, exist_ok=True)


def run_group(job: dict, group: str) -> list[dict]:
    work = Path(job["work"])
    point_at(work)
    p, m = job["platform"], job["media_id"]
    caption = job["caption"] if job["caption"] is not None else ""   # missing is masked later (D-055 s.1)
    if group == "speech":
        common.enable_cuda12_dlls()       # before faster-whisper, and no PyTorch in this process (D-027)
    out = []
    for block in GROUPS[group]:
        guard(block)
        t0 = time.time()
        status = STEPS[block](p, m, job, caption)
        out.append({"step": block, "status": status, "sec": round(time.time() - t0, 1)})
    return out


def _prep(p, m, job, caption):
    from src.features import prepare
    res = prepare.prepare_one(pd.Series({"platform": p, "media_id": m, "video_path": job["video_path"]}),
                              force=False)
    if res["status"] == "failed":
        raise StepFailed(f"preparing the video failed: {res.get('error')}")
    # as prepare.main() writes it
    common.update_cache(p, m, "prep", {k: v for k, v in res.items() if k not in ("platform", "media_id")})
    return res["status"]


def _scenes(p, m, job, caption):
    from src.features import scenes
    prep = common.read_cache(p, m)["prep"]
    res = scenes.scenes_one(p, m, job["video_path"], float(prep["video_duration_sec"]), False)
    if res["status"] == "failed":
        raise StepFailed(f"cut detection failed: {res.get('error')}")
    return res["status"]


def _frames(p, m, job, caption):
    from src.features import frames
    res = frames.frames_one(p, m, job["video_path"], False)
    if res["status"] == "failed":
        raise StepFailed(f"frame sampling failed: {res.get('error')}")
    return res["status"]


def _asr(p, m, job, caption):
    from src.features import asr
    model = asr.load_model(allow_download=False)
    res = asr.asr_one(model, pd.Series({"platform": p, "media_id": m}))
    return res["status"]


def _audio_signal(p, m, job, caption):
    from src.features import audio
    return audio.signal_one(p, m, False)["status"]


def _faces(p, m, job, caption):
    from src.features import faces_text
    det = faces_text.load_face_detector(allow_download=False)
    payload = faces_text.faces_one(det, p, m)
    common.update_cache(p, m, "faces", payload)          # as faces_text.run() writes it
    return payload["status"]


def _visual(p, m, job, caption):
    from src.features import visual
    payload = visual.one_video(p, m)
    common.update_cache(p, m, "visual", payload)
    return payload["status"]


def _free_gpu():
    import gc
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass


def _audio_events(p, m, job, caption):
    from src.features import audio
    fe, model, device = audio.load_ast(allow_download=False)
    payload = audio.events_one(fe, model, device, p, m)
    common.update_cache(p, m, "audio_events", payload)   # as audio.run_events() writes it
    del fe, model
    _free_gpu()
    return payload["status"]


def _sentiment(p, m, job, caption):
    from src.features import sentiment
    models = sentiment.load_pair(allow_download=False)
    payload = sentiment.one_video(models, p, m, caption)
    common.update_cache(p, m, "sentiment", payload)      # as sentiment.run() writes it
    del models
    _free_gpu()
    return payload["status"]


def _ocr(p, m, job, caption):
    from src.features import faces_text
    reader = faces_text.load_text_detector(allow_download=False)
    payload = faces_text.text_one(reader, p, m)
    common.update_cache(p, m, "ocr", payload)
    del reader
    _free_gpu()
    return payload["status"]


def _language(p, m, job, caption):
    from src.features import language
    payload = language.one_video(p, m, caption)
    common.update_cache(p, m, "language", payload)       # as language.run() writes it
    return payload["status"]


def _keywords(p, m, job, caption):
    from src.features import keywords
    payload = keywords.one_video(p, m, caption)
    common.update_cache(p, m, "keywords", payload)
    return payload["status"]


def _meta(p, m, job, caption):
    """The caption counts of 5.15 (metadata.text_counts) plus the two inputs the corpus took from its
    collection records: the title (YouTube) and the collaboration flag, here given by the user."""
    from datetime import datetime, timezone
    from src.features import metadata
    title = job.get("title")
    sent = common.read_cache(p, m).get("sentiment") or {}
    payload = {**metadata.text_counts(caption),
               "title_char_len": len(title) if (p == "youtube" and title is not None) else None,
               "title_word_count": len(title.split()) if (p == "youtube" and title is not None) else None,
               "creator_collab": job.get("creator_collab"),
               "text_lang": sent.get("caption_lang"),
               "title_char_len_z_lang": None,
               "title_z_lang_skipped": "not computed by the tool - needs the corpus's titles; not a model input",
               "params": metadata.PARAMS,
               "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    common.update_cache(p, m, "meta", payload)
    return "ok"


STEPS = {"prep": _prep, "scenes": _scenes, "frames": _frames, "asr": _asr, "audio_signal": _audio_signal,
         "faces": _faces, "visual": _visual, "audio_events": _audio_events, "sentiment": _sentiment,
         "ocr": _ocr, "language": _language, "keywords": _keywords, "meta": _meta}


# ------------------------------------------------------------------------------------------ orchestration
def measure(job: dict, log=print) -> dict:
    """Run every group for one video, each in its own process. Returns the per-video record and timings.

    `job`: work (folder), platform, media_id (the record's key), video_path, caption (None = not given),
    title (YouTube, optional), creator_collab (True / False / None = not given).
    """
    work = Path(job["work"])
    work.mkdir(parents=True, exist_ok=True)
    job_file = work / "job.json"
    job_file.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    timings = []
    t_all = time.time()
    for group in GROUPS:
        t0 = time.time()
        logf = work / f"log_{group}.txt"
        with open(logf, "w", encoding="utf-8") as fh:
            r = subprocess.run([sys.executable, "-m", "src.serve.measure", "--job", str(job_file),
                                "--group", group], cwd=str(config.ROOT), env=env, stdout=fh,
                               stderr=subprocess.STDOUT)
        status_file = work / f"status_{group}.json"
        status = json.loads(status_file.read_text(encoding="utf-8")) if status_file.exists() else {}
        if r.returncode != 0 or not status.get("ok"):
            reason = status.get("error") or f"the '{group}' step stopped (see {logf.relative_to(config.ROOT)})"
            raise StepFailed(reason)
        timings += status["steps"]
        log(f"  {group:7} {time.time() - t0:5.1f} s  "
            + ", ".join(f"{s['step']} {s['status']}" for s in status["steps"]))
    # Read the record from the run folder directly. This process's `common` keeps pointing at the training
    # folders, so a caller can still read a training value and compare - never the run's own value back.
    record = work / "features" / f"{job['platform']}_{job['media_id']}.json"
    doc = json.loads(record.read_text(encoding="utf-8"))
    return {"doc": doc, "steps": timings, "total_sec": round(time.time() - t_all, 1)}


def main() -> None:
    ap = argparse.ArgumentParser(description="12.3 - run one group of feature steps on one video.")
    ap.add_argument("--job", required=True)
    ap.add_argument("--group", required=True, choices=list(GROUPS))
    args = ap.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    status_file = Path(job["work"]) / f"status_{args.group}.json"
    try:
        steps = run_group(job, args.group)
        status = {"ok": True, "steps": steps}
    except StepFailed as exc:
        status = {"ok": False, "error": str(exc)}
    except BaseException as exc:                      # recorded, then the process fails
        traceback.print_exc()
        status = {"ok": False, "error": f"{args.group}: {type(exc).__name__}: {exc}"[:300]}
    status_file.write_text(json.dumps(status, indent=1), encoding="utf-8")
    sys.exit(0 if status["ok"] else 1)


if __name__ == "__main__":
    main()

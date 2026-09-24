"""Task 5.8 - audio features: loudness, tone, tempo, voice pitch; music vs speech vs singing.

Two parts, cached separately in each video's cache so either can be re-run alone.

**Part A - signal measures (librosa, CPU, no model)** -> cache block `audio_signal`
    loudness_db_mean      mean frame loudness, dB relative to full scale (floor -80 dB)
    loudness_range_db     spread of loudness over non-silent frames (95th - 10th percentile)
    silence_frac          share of frames below -50 dB
    spectral_centroid_hz  "brightness" of the sound, over non-silent frames
    tempo_bpm             beats per minute from the onset envelope (meaningful for music)
    pitch_median_hz       voice pitch, measured only inside 5.6's speech regions
    pitch_std_semitones   pitch variability within each spoken segment, averaged (prosody)
    pitch_at_search_edge  median pitch pinned at the search limit: music or octave error
    voiced_frac           share of speech frames with a detectable pitch

**Part B - sound events (AST on the GPU)** -> cache block `audio_events`
    music_frac            share of 4-second windows where music is detected
    music_present         any window with music
    speech_sung_frac      share of 5.6's transcribed speech that is sung vocals, not talking
    talk_dur_frac         talking (not sung) as a share of the video
    pitch_*_talk          voice pitch measures from Part A, restricted to talking

Part B uses the Audio Spectrogram Transformer fine-tuned on AudioSet
(MIT/ast-finetuned-audioset-10-10-0.4593, BSD-3, 346 MB) - the same sound categories as
YAMNet, which docs/05 names but which needs TensorFlow, and TensorFlow has no build for this
Python (3.14). No download happens unless `--allow-download` is given.

The two digitally silent Reels (D-025) get null signal measures, and zero for music and speech,
which is the true measurement there.

Usage:
    python -m src.features.audio --part signal            # Part A, all 300, CPU
    python -m src.features.audio --part events --limit 3 --allow-download
    python -m src.features.audio --part events            # Part B, all 300, GPU
    python -m src.features.audio --only instagram_C-Qrzffy557 --force
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402

SUMMARY_SIGNAL = config.INTERIM / "audio_signal_summary.csv"
SUMMARY_EVENTS = config.INTERIM / "audio_events_summary.csv"

# ---- Part A settings
HOP = 512                   # 32 ms at 16 kHz
FRAME = 1024
DB_FLOOR = -80.0
SILENCE_DB = -50.0
PITCH_FMIN, PITCH_FMAX = 65.0, 500.0     # human speaking range
MIN_SPEECH_SEC_FOR_PITCH = 2.0
MIN_SEGMENT_SEC = 1.0
SIGNAL_PARAMS = {"hop": HOP, "frame": FRAME, "db_floor": DB_FLOOR, "silence_db": SILENCE_DB,
                 "pitch": "pyin", "pitch_range_hz": [PITCH_FMIN, PITCH_FMAX],
                 "pitch_scope": "within each 5.6 transcript segment >= 1 s, then averaged",
                 "min_speech_sec": MIN_SPEECH_SEC_FOR_PITCH}

# ---- Part B settings
AST_REPO = "MIT/ast-finetuned-audioset-10-10-0.4593"
WIN_SEC, HOP_SEC = 4.0, 2.0
EVENT_THRESHOLD = 0.5       # AudioSet outputs are independent per-label probabilities
# Talked vs sung, per transcript segment. Evidence (12 known videos, docs/05 section 5):
# speech score 0.57-0.77 on talking, 0.05-0.09 on songs, 0.30-0.59 on chanted slogans.
TALK_SPEECH_MIN = 0.30
SPEECH_LABELS = ["Speech", "Male speech, man speaking", "Female speech, woman speaking",
                 "Child speech, kid speaking", "Conversation", "Narration, monologue"]
VOCAL_LABELS = ["Singing", "Male singing", "Female singing", "Child singing", "Synthetic singing",
                "Choir", "Chant", "Mantra", "Rapping", "Humming", "Yodeling", "Vocal music",
                "A capella"]
EVENTS_PARAMS = {"model": AST_REPO, "window_sec": WIN_SEC, "hop_sec": HOP_SEC,
                 "threshold": EVENT_THRESHOLD, "talk_speech_min": TALK_SPEECH_MIN,
                 "talk_vs_sung_unit": "5.6 transcript segment"}


# ============================================================ Part A - signal measures

def signal_one(platform: str, media_id: str, force: bool) -> dict:
    """Loudness, brightness, tempo and voice pitch for one video. CPU; safe in a worker."""
    import librosa
    out = {"platform": platform, "media_id": media_id}
    doc = common.read_cache(platform, media_id)
    cached = doc.get("audio_signal")
    if cached and not force and cached.get("params") == SIGNAL_PARAMS:
        return {**out, **{k: v for k, v in cached.items() if k not in ("params", "pitch_per_segment")},
                "status": "reused"}
    prep, asr = doc.get("prep", {}), doc.get("asr", {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if prep.get("audio_silent"):
        payload = {"status": "silent_audio", "loudness_db_mean": None, "loudness_range_db": None,
                   "silence_frac": 1.0, "spectral_centroid_hz": None, "tempo_bpm": None,
                   "pitch_median_hz": None, "pitch_std_semitones": None, "voiced_frac": None,
                   "params": SIGNAL_PARAMS, "processed_at": now}
        common.update_cache(platform, media_id, "audio_signal", payload)
        return {**out, **{k: v for k, v in payload.items() if k != "params"}}

    import soundfile as sf
    y, sr = sf.read(str(common.audio_file(platform, media_id)), dtype="float32")
    rms = librosa.feature.rms(y=y, frame_length=FRAME, hop_length=HOP)[0]
    db = np.maximum(20 * np.log10(rms + 1e-10), DB_FLOOR)
    loud = db > SILENCE_DB
    cent = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=FRAME, hop_length=HOP)[0]
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    tempo = librosa.feature.tempo(onset_envelope=onset, sr=sr, hop_length=HOP)
    payload = {
        "status": "ok",
        "loudness_db_mean": round(float(db.mean()), 2),
        "loudness_range_db": (round(float(np.percentile(db[loud], 95) - np.percentile(db[loud], 10)), 2)
                              if loud.sum() >= 10 else None),
        "silence_frac": round(float(1 - loud.mean()), 4),
        "spectral_centroid_hz": round(float(cent[loud].mean()), 1) if loud.any() else None,
        "tempo_bpm": round(float(np.atleast_1d(tempo)[0]), 1) if loud.any() else None,
    }

    # Voice pitch, only inside 5.6's transcript segments - otherwise this would measure the
    # music. Variability is taken *within* each segment (usually one speaker's turn) and then
    # averaged: measured across the whole video it mostly measured how many voices, and of
    # which sexes, were in it (a man-woman dialogue read as a 13-semitone swing).
    segs = [s for s in (asr.get("segments_native") or [])
            if asr.get("status") == "ok" and not s.get("stock_phrase")
            and s["end"] - s["start"] >= MIN_SEGMENT_SEC]
    speech_sec = sum(s["end"] - s["start"] for s in segs)
    per_seg, all_f0, n_frames, n_voiced = [], [], 0, 0
    if speech_sec >= MIN_SPEECH_SEC_FOR_PITCH:
        for s in segs:
            seg = y[int(s["start"] * sr):int(s["end"] * sr)]
            f0, voiced, _ = librosa.pyin(seg, fmin=PITCH_FMIN, fmax=PITCH_FMAX, sr=sr,
                                         frame_length=FRAME * 2, hop_length=HOP)
            f0v = f0[voiced & np.isfinite(f0)]
            n_frames += len(f0)
            n_voiced += int(f0v.size)
            if f0v.size >= 10:
                med = float(np.median(f0v))
                per_seg.append({"start": s["start"], "end": s["end"], "median_hz": round(med, 1),
                                "std_st": round(float(np.std(12 * np.log2(f0v / med))), 3),
                                "n_voiced": int(f0v.size)})
                all_f0.append(f0v)
    f0_med = float(np.median(np.concatenate(all_f0))) if all_f0 else None
    f0_std = (float(np.average([p["std_st"] for p in per_seg],
                               weights=[p["n_voiced"] for p in per_seg])) if per_seg else None)
    edge = bool(f0_med is not None and (f0_med <= PITCH_FMIN * 1.08 or f0_med >= PITCH_FMAX * 0.9))
    payload.update({"pitch_median_hz": round(f0_med, 1) if f0_med else None,
                    "pitch_std_semitones": round(f0_std, 3) if f0_std is not None else None,
                    "voiced_frac": round(n_voiced / n_frames, 4) if n_frames else None,
                    "pitch_at_search_edge": edge, "pitch_segments": len(per_seg),
                    "pitch_speech_sec": round(speech_sec, 2), "pitch_per_segment": per_seg,
                    "params": SIGNAL_PARAMS, "processed_at": now})
    common.update_cache(platform, media_id, "audio_signal", payload)
    return {**out, **{k: v for k, v in payload.items() if k not in ("params", "pitch_per_segment")}}


def run_signal(idx: pd.DataFrame, force: bool, workers: int) -> pd.DataFrame:
    from joblib import Parallel, delayed
    t0 = time.time()
    rows = Parallel(n_jobs=workers, backend="loky")(
        delayed(signal_one)(r["platform"], r["media_id"], force) for _, r in idx.iterrows())
    df = pd.DataFrame(rows)
    df.to_csv(SUMMARY_SIGNAL, index=False)
    print(f"Part A: {len(df)} videos in {(time.time() - t0) / 60:.1f} min -> "
          f"{SUMMARY_SIGNAL.relative_to(config.ROOT)}")
    print("status:", df["status"].value_counts().to_dict())
    num = ["loudness_db_mean", "loudness_range_db", "silence_frac", "spectral_centroid_hz",
           "tempo_bpm", "pitch_median_hz", "pitch_std_semitones", "voiced_frac"]
    print(df[num].describe(percentiles=[.1, .5, .9]).T[["count", "min", "10%", "50%", "90%", "max"]]
          .round(2).to_string())
    return df


# ============================================================ Part B - sound events

def load_ast(allow_download: bool):
    import torch
    from transformers import ASTFeatureExtractor, ASTForAudioClassification
    try:
        fe = ASTFeatureExtractor.from_pretrained(AST_REPO, local_files_only=not allow_download)
        model = ASTForAudioClassification.from_pretrained(
            AST_REPO, local_files_only=not allow_download, use_safetensors=True)
    except OSError as exc:
        if not allow_download:
            raise SystemExit(f"{AST_REPO} is not on disk. It is a one-time 346 MB download "
                             f"(BSD-3). Re-run with --allow-download to fetch it.") from exc
        raise
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return fe, model.to(device).eval(), device


def events_one(fe, model, device, platform: str, media_id: str) -> dict:
    import soundfile as sf
    import torch
    doc = common.read_cache(platform, media_id)
    prep, asr = doc["prep"], doc.get("asr", {})
    duration = float(prep["video_duration_sec"])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if prep.get("audio_silent"):
        return {"status": "silent_audio", "n_windows": 0, "music_frac": 0.0, "music_present": False,
                "speech_frac_ast": 0.0, "speech_sung_frac": None, "talk_sec": 0.0,
                "talk_dur_frac": 0.0, "windows": [], "segments": [], "params": EVENTS_PARAMS,
                "processed_at": now}
    y, sr = sf.read(str(common.audio_file(platform, media_id)), dtype="float32")
    lab = model.config.label2id
    speech_ids = [lab[l] for l in SPEECH_LABELS if l in lab]
    vocal_ids = [lab[l] for l in VOCAL_LABELS if l in lab]
    music_id = lab["Music"]

    def score(clips):
        out = []
        for i in range(0, len(clips), 16):
            batch = fe(clips[i:i + 16], sampling_rate=sr, return_tensors="pt")
            with torch.no_grad():
                logits = model(batch["input_values"].to(device)).logits
            out.append(torch.sigmoid(logits).cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, len(lab)))

    # 1. Whole video in 4 s windows: how much of it carries music, how much speech.
    win, hop = int(WIN_SEC * sr), int(HOP_SEC * sr)
    starts = list(range(0, max(1, len(y) - win + 1), hop)) or [0]
    if starts[-1] + win < len(y):
        starts.append(max(0, len(y) - win))      # cover the tail
    P = score([y[s:s + win] for s in starts])
    windows = [{"start": round(s / sr, 2), "end": round(min(len(y), s + win) / sr, 2),
                "speech": round(float(p[speech_ids].max()), 3), "music": round(float(p[music_id]), 3),
                "vocal": round(float(p[vocal_ids].max()), 3),
                "top": [model.config.id2label[j] for j in np.argsort(-p)[:3]]}
               for s, p in zip(starts, P)]
    music = np.array([w["music"] for w in windows]) >= EVENT_THRESHOLD
    spk = np.array([w["speech"] for w in windows]) >= EVENT_THRESHOLD

    # 2. Each transcript segment on its own: talked or sung? AudioSet's singing labels barely
    #    fire on this corpus (a Christmas choir peaked at 0.06), but sung vocals score low as
    #    *speech* (0.05-0.09 on known songs) while talking scores high (0.57-0.77, even over
    #    music). Chanted slogans fall between (0.30-0.59) and count as talk.
    segs = [s for s in (asr.get("segments_native") or [])
            if asr.get("status") == "ok" and not s.get("stock_phrase") and s["end"] - s["start"] >= 0.5]
    seg_out = []
    for s in segs:
        a, b = int(s["start"] * sr), int(s["end"] * sr)
        chunks = [y[i:min(b, i + int(10 * sr))] for i in range(a, b, int(10 * sr))]   # AST takes <=10.24 s
        Q = score(chunks)
        sp = float(Q[:, speech_ids].max(1).mean())
        seg_out.append({"start": s["start"], "end": s["end"], "speech": round(sp, 3),
                        "vocal": round(float(Q[:, vocal_ids].max(1).mean()), 3),
                        "label": "talk" if sp >= TALK_SPEECH_MIN else "sung"})
    talk = sum(x["end"] - x["start"] for x in seg_out if x["label"] == "talk")
    sung = sum(x["end"] - x["start"] for x in seg_out if x["label"] == "sung")
    speech_sec = talk + sung

    # 3. Voice pitch on talking only, from 5.8 Part A's per-segment measures.
    talk_spans = [(x["start"], x["end"]) for x in seg_out if x["label"] == "talk"]
    per = [p for p in (doc.get("audio_signal", {}).get("pitch_per_segment") or [])
           if any(abs(p["start"] - s0) < 1e-3 and abs(p["end"] - e0) < 1e-3 for s0, e0 in talk_spans)]
    if per:
        w = np.array([p["n_voiced"] for p in per], dtype=float)
        pitch_std_talk = round(float(np.average([p["std_st"] for p in per], weights=w)), 3)
        pitch_med_talk = round(float(np.average([p["median_hz"] for p in per], weights=w)), 1)
    else:
        pitch_std_talk = pitch_med_talk = None
    return {"status": "ok", "n_windows": len(windows),
            "music_frac": round(float(music.mean()), 4), "music_present": bool(music.any()),
            "speech_frac_ast": round(float(spk.mean()), 4),
            "speech_sung_frac": round(sung / speech_sec, 4) if speech_sec else None,
            "talk_sec": round(talk, 2),
            "talk_dur_frac": round(min(1.0, talk / duration), 4) if duration else None,
            "pitch_median_talk_hz": pitch_med_talk, "pitch_std_talk_semitones": pitch_std_talk,
            "windows": windows, "segments": seg_out, "params": EVENTS_PARAMS, "processed_at": now}


def run_events(idx: pd.DataFrame, force: bool, allow_download: bool) -> pd.DataFrame:
    todo = [r for _, r in idx.iterrows()
            if force or (common.read_cache(r["platform"], r["media_id"]).get("audio_events") or {})
            .get("params") != EVENTS_PARAMS]
    print(f"Part B: {len(idx)} selected, {len(todo)} to process")
    if todo:
        fe, model, device = load_ast(allow_download)
        print(f"AST loaded on {device}")
        t0 = time.time()
        for i, r in enumerate(todo, 1):
            p = events_one(fe, model, device, r["platform"], r["media_id"])
            common.update_cache(r["platform"], r["media_id"], "audio_events", p)
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}  {(time.time() - t0) / 60:.1f} min")
    rows = []
    for _, r in idx.iterrows():
        p = common.read_cache(r["platform"], r["media_id"]).get("audio_events")
        if p:
            rows.append({"platform": r["platform"], "media_id": r["media_id"],
                         **{k: v for k, v in p.items() if k not in ("windows", "segments", "params")}})
    df = pd.DataFrame(rows)
    df.to_csv(SUMMARY_EVENTS, index=False)
    print(f"-> {SUMMARY_EVENTS.relative_to(config.ROOT)}")
    print("status:", df["status"].value_counts().to_dict())
    print(df[["music_frac", "speech_frac_ast", "speech_sung_frac", "talk_dur_frac",
              "pitch_std_talk_semitones"]]
          .describe(percentiles=[.1, .5, .9]).T[["count", "min", "10%", "50%", "90%", "max"]]
          .round(3).to_string())
    print("music present:", int(df["music_present"].sum()), "of", len(df))
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description="5.8 - audio signal measures and sound events.")
    ap.add_argument("--part", choices=["signal", "events"], required=True)
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", nargs="+", metavar="PLATFORM_MEDIAID")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--allow-download", action="store_true",
                    help="permit the one-time 346 MB AST download (Part B)")
    args = ap.parse_args()
    idx = common.video_index(args.platform)
    if args.only:
        idx = idx[(idx["platform"] + "_" + idx["media_id"]).isin(args.only)]
    if args.limit:
        idx = idx.groupby("platform", group_keys=False).head(args.limit)
    if args.part == "signal":
        run_signal(idx, args.force, args.workers)
    else:
        run_events(idx, args.force, args.allow_download)


if __name__ == "__main__":
    main()

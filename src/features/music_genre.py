"""Task 5.13 - what kind of music is playing (proposal Block B).

5.8 Part B already measured *whether* music is present, per 4-second window, with AST
(`MIT/ast-finetuned-audioset-10-10-0.4593`, already on disk - **no new download**). It kept only
the top-3 AudioSet labels per window, and those are mostly the generic "Music". This step re-runs
the same windows and keeps the **genre** labels, grouped.

    music_genre_top          the genre group with the highest mean probability over the music
                             windows; null where there is no music
    music_genre_top_score    that mean probability - how much the label is worth believing
    music_genre_<group>_frac share of music windows where that group is the strongest
    music_genre_margin       top group's mean probability minus the second group's

**Groups fixed here before any score was looked at** (AudioSet's own label names, grouped so
that no group is a single rare label):

    pop_rock, hip_hop_rnb, electronic_dance, latin, regional, classical_jazz_folk, functional

`functional` is jingles, theme and background music, soundtracks, Christmas and children's
music - the categories an advertisement actually uses, kept separate from the artist genres.

**Only where music plays.** A window counts if 5.8 scored music >= 0.5 there; a video with no
music window gets nulls (not zeros), and the two digitally silent Reels (D-025) stay null. Zero
would say "no genre", which is not what was measured.

**The check this step must pass.** 5.8 found AudioSet's *singing* labels barely fire on this
corpus (a Christmas choir peaked at 0.06), so its genre labels are not assumed to work either.
The run reports how high the genre probabilities actually get and how often the top group beats
the second. If they are as flat as the singing labels were, the honest report is that music type
could not be measured - that conclusion is stated, not papered over with an argmax.

Runs on all 300 videos (D-030: the focus applies at analysis, not at measurement).

Usage:
    python -m src.features.music_genre --limit 3
    python -m src.features.music_genre
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
from src.features.audio import AST_REPO, EVENT_THRESHOLD, HOP_SEC, WIN_SEC, load_ast  # noqa: E402

SUMMARY = config.INTERIM / "music_genre_summary.csv"

GROUPS: dict[str, list[str]] = {
    "pop_rock": ["Pop music", "Rock music", "Rock and roll", "Punk rock", "Heavy metal",
                 "Progressive rock", "Psychedelic rock", "Grunge", "Independent music",
                 "Beatboxing"],
    "hip_hop_rnb": ["Hip hop music", "Rapping", "Rhythm and blues", "Soul music", "Funk",
                    "Disco", "Grime music", "Trap music"],
    "electronic_dance": ["Electronic music", "Electronic dance music", "House music", "Techno",
                         "Trance music", "Dubstep", "Drum and bass", "Electronica",
                         "Dance music", "Ambient music", "New-age music", "Chiptune"],
    "latin": ["Music of Latin America", "Salsa music", "Cumbia", "Flamenco", "Reggae", "Ska",
              "Bossa nova", "Samba", "Mambo", "Merengue", "Bachata"],
    "regional": ["Music of Asia", "Music of Bollywood", "Carnatic music", "Middle Eastern music",
                 "Music of Africa", "Afrobeat", "Traditional music", "Gamelan", "Kwaito",
                 "Sitar", "Tabla"],
    "classical_jazz_folk": ["Classical music", "Opera", "Orchestra", "Jazz", "Blues", "Country",
                            "Folk music", "Bluegrass", "Gospel music", "Christian music",
                            "Choir", "A capella"],
    "functional": ["Jingle (music)", "Theme music", "Background music", "Soundtrack music",
                   "Video game music", "Christmas music", "Wedding music", "Lullaby",
                   "Music for children", "Song", "Vocal music"],
}
PARAMS = {"model": AST_REPO, "window_sec": WIN_SEC, "hop_sec": HOP_SEC,
          "music_window_threshold": EVENT_THRESHOLD, "groups": {k: len(v) for k, v in GROUPS.items()},
          "version": 1}


def group_ids(model) -> tuple[dict[str, list[int]], list[str]]:
    """AudioSet label ids per group, plus the names this model does not have."""
    lab = model.config.label2id
    ids, missing = {}, []
    for g, names in GROUPS.items():
        found = [lab[n] for n in names if n in lab]
        missing += [n for n in names if n not in lab]
        if found:
            ids[g] = found
    return ids, missing


def one_video(fe, model, device, ids: dict[str, list[int]], platform: str, media_id: str) -> dict:
    import soundfile as sf
    import torch

    doc = common.read_cache(platform, media_id)
    prep, ev = doc.get("prep", {}), doc.get("audio_events", {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    base = {k: None for k in ["music_genre_top", "music_genre_top_score", "music_genre_margin"]}
    base |= {f"music_genre_{g}_frac": None for g in GROUPS}

    if prep.get("audio_silent"):
        return {"status": "silent_audio", "n_music_windows": 0, **base,
                "params": PARAMS, "processed_at": now}
    if not ev or ev.get("status") != "ok":
        return {"status": "no_audio_events_yet", "n_music_windows": 0, **base,
                "params": PARAMS, "processed_at": now}
    # 5.8's windows say where music plays; re-score exactly those.
    music_windows = [w for w in ev.get("windows", []) if w["music"] >= EVENT_THRESHOLD]
    if not music_windows:
        return {"status": "no_music", "n_music_windows": 0, **base,
                "params": PARAMS, "processed_at": now}

    y, sr = sf.read(str(common.audio_file(platform, media_id)), dtype="float32")
    clips = [y[int(w["start"] * sr):int(w["start"] * sr) + int(WIN_SEC * sr)] for w in music_windows]
    probs = []
    for i in range(0, len(clips), 16):
        batch = fe(clips[i:i + 16], sampling_rate=sr, return_tensors="pt")
        with torch.no_grad():
            logits = model(batch["input_values"].to(device)).logits
        probs.append(torch.sigmoid(logits).cpu().numpy())
    P = np.concatenate(probs)

    # Per window, each group's score is the strongest of its labels.
    names = list(ids)
    G = np.stack([P[:, ids[g]].max(axis=1) for g in names], axis=1)     # windows x groups
    mean_by_group = G.mean(axis=0)
    order = np.argsort(-mean_by_group)
    argmax_per_window = G.argmax(axis=1)
    out = {
        "status": "ok",
        "n_music_windows": len(music_windows),
        "music_genre_top": names[int(order[0])],
        "music_genre_top_score": round(float(mean_by_group[order[0]]), 4),
        "music_genre_margin": round(float(mean_by_group[order[0]] - mean_by_group[order[1]]), 4),
        "genre_mean_scores": {g: round(float(v), 4) for g, v in zip(names, mean_by_group)},
        "max_label_score": round(float(P.max()), 4),
    }
    for j, g in enumerate(names):
        out[f"music_genre_{g}_frac"] = round(float((argmax_per_window == j).mean()), 4)
    out["params"] = PARAMS
    out["processed_at"] = now
    return out


def run(idx: pd.DataFrame, force: bool, allow_download: bool) -> pd.DataFrame:
    todo = [r for _, r in idx.iterrows()
            if force or (common.read_cache(r["platform"], r["media_id"]).get("music_genre") or {})
            .get("params") != PARAMS]
    print(f"5.13 music type: {len(idx)} selected, {len(todo)} to process")
    if todo:
        fe, model, device = load_ast(allow_download)
        ids, missing = group_ids(model)
        print(f"AST loaded on {device}; groups {list(ids)}")
        if missing:
            print(f"  label names not in this model, ignored: {sorted(set(missing))}")
        t0 = time.time()
        for i, r in enumerate(todo, 1):
            p = one_video(fe, model, device, ids, r["platform"], r["media_id"])
            common.update_cache(r["platform"], r["media_id"], "music_genre", p)
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}  {(time.time() - t0) / 60:.1f} min")
    rows = []
    for _, r in idx.iterrows():
        p = common.read_cache(r["platform"], r["media_id"]).get("music_genre")
        if p:
            rows.append({"platform": r["platform"], "media_id": r["media_id"],
                         **{k: v for k, v in p.items()
                            if k not in ("params", "genre_mean_scores")}})
    df = pd.DataFrame(rows)
    df.to_csv(SUMMARY, index=False)
    print(f"-> {SUMMARY.relative_to(config.ROOT)}  ({len(df)} rows)")
    return df


def report(df: pd.DataFrame) -> None:
    print("\nstatus:", df["status"].value_counts(dropna=False).to_dict())
    ok = df[df["status"] == "ok"]
    if ok.empty:
        print("no video produced a genre - nothing to report")
        return
    print(f"\ntop genre group over {len(ok)} videos with music:")
    print(pd.crosstab(ok["platform"], ok["music_genre_top"]).to_string())
    s, m = ok["music_genre_top_score"], ok["music_genre_margin"]
    print(f"\nhow strong the labels are (this decides whether the feature is usable):")
    print(f"  top group's mean probability : median {s.median():.3f}  "
          f"10th-90th {s.quantile(.1):.3f}-{s.quantile(.9):.3f}  max {s.max():.3f}")
    print(f"  margin over the second group : median {m.median():.3f}  max {m.max():.3f}")
    print(f"  strongest single AudioSet label in any music window: "
          f"median {ok['max_label_score'].median():.3f}")
    print(f"  videos whose top group reaches 0.20: {int((s >= 0.20).sum())} of {len(ok)}; "
          f"0.10: {int((s >= 0.10).sum())}; 0.05: {int((s >= 0.05).sum())}")
    print("\nJudge the run on those numbers: a median top score near 0.05 with a tiny margin "
          "means AudioSet's genre labels do not separate this corpus, the same way its singing "
          "labels did not (D-028) - in which case music type is reported as not measurable.")


def main() -> None:
    ap = argparse.ArgumentParser(description="5.13 - music type from AudioSet genre labels.")
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", nargs="+", metavar="PLATFORM_MEDIAID")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--allow-download", action="store_true",
                    help="not needed: the AST model is already on disk from 5.8")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    idx = common.video_index(args.platform)
    if args.only:
        idx = idx[(idx["platform"] + "_" + idx["media_id"]).isin(args.only)]
    if args.limit:
        idx = idx.groupby("platform", group_keys=False).head(args.limit)
    df = run(idx, args.force, args.allow_download)
    if len(df):
        report(df)


if __name__ == "__main__":
    main()

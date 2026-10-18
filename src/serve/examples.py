"""The examples box on the tool's form (D-065): six videos from the study's own collection that no model was fitted
on, offered with their real details and measured once in advance so each opens at once.

Five are Zero Sugar videos left out of the 192 only because their likes were hidden or their comments switched off
(their engagement was never read); one is a regular Coca-Cola Reel that shows the "not Zero Sugar" warning. None is
one of the 192 - a training video would score itself.

    python -m src.serve.examples              # list the examples and whether each saved measurement is ready
    python -m src.serve.examples --prepare    # measure every example not yet measured (3-4 minutes each)
"""
from __future__ import annotations

import argparse
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

# (platform, media_id) in the order the box shows them (D-065)
CHOSEN = [("instagram", "C4-MHHxqE2M"), ("youtube", "fkQUn9CHreE"), ("instagram", "DATm42ctA-V"),
          ("instagram", "DD9hPkAobol"), ("youtube", "fT1LhQTSawE"), ("instagram", "DaKsr6OzHqf")]
WHY = {"excluded_likes_hidden": "likes hidden", "excluded_comments_disabled": "comments off",
       "not_zero_sugar": "shows the warning"}


@lru_cache(maxsize=None)
def _fingerprint(path: str) -> str:
    from src.serve.intake import sha256
    return sha256(Path(path))[:16]


@lru_cache(maxsize=1)
def _examples() -> tuple[dict, ...]:
    from src.serve.parity import corpus_inputs
    dv = pd.read_parquet(config.PROCESSED / "dependent_variable.parquet")
    feats = pd.read_parquet(config.PROCESSED / "features.parquet",
                            columns=["platform", "media_id", "duration_sec", "talk_dur_frac"])
    out = []
    for platform, media_id in CHOSEN:
        row = dv[(dv["platform"] == platform) & (dv["media_id"] == media_id)].iloc[0]
        if bool(row["in_focus"]) and row["dv_status"] == "ok":
            raise SystemExit(f"{platform} {media_id} is one of the 192 - not allowed as an example (D-065)")
        f = feats[(feats["platform"] == platform) & (feats["media_id"] == media_id)].iloc[0]
        c = corpus_inputs(platform, media_id)
        zero_sugar = bool(row["is_zero_sugar"])
        notes = ["Zero Sugar" if zero_sugar else "not Zero Sugar",
                 "talking" if (f["talk_dur_frac"] or 0) > 0 else "no talking"]
        if c["creator_collab"]:
            notes.append("creator collab")
        if "mourinho" in (c["caption"] or "").lower():          # the series with AI-generated characters (D-049)
            notes.append("AI-character series")
        out.append({
            "key": f"{platform}_{media_id}", "platform": platform, "media_id": media_id,
            "account": str(row["account"]), "duration": float(f["duration_sec"]),
            "followers": float(row["followers"]), "caption": c["caption"], "title": c["title"],
            "collab": c["creator_collab"], "zero_sugar": "yes" if zero_sugar else "no",
            "why": WHY[row["dv_status"] if zero_sugar else "not_zero_sugar"], "notes": notes,
            "path": str(c["video_path"]),
            "label": (f"{row['account']} · {'Instagram Reel' if platform == 'instagram' else 'YouTube Short'} · "
                      f"{float(f['duration_sec']):.0f} s · {', '.join(notes)}"),
        })
    return tuple(out)


def all_examples() -> list[dict]:
    """The six examples, each with `ready` = its saved measurement exists for these exact details."""
    from src.serve.intake import VIDEOS, inputs_key
    out = []
    for e in _examples():
        key = inputs_key(e["platform"], e["caption"], e["title"], e["collab"] if e["platform"] == "instagram" else None)
        out.append({**e, "ready": (VIDEOS / _fingerprint(e["path"]) / key / "result.json").exists()})
    return out


def get(key: str) -> dict | None:
    return next((e for e in all_examples() if e["key"] == key), None)


def for_page() -> tuple[list[dict], str]:
    """The examples for the form, and the same as JSON for its script (no file paths, `</` escaped)."""
    import json
    ex = all_examples()
    public = [{k: e[k] for k in ("key", "platform", "account", "followers", "caption", "collab", "zero_sugar", "label")}
              for e in ex]
    return ex, json.dumps(public, ensure_ascii=False).replace("</", "<\\/")


def prepare() -> None:
    """Measure each example once with its real details, through the same checks and cache as an upload."""
    from src.serve import intake
    for e in all_examples():
        if e["ready"]:
            print(f"{e['key']}: ready")
            continue
        print(f"{e['key']}: measuring ...", flush=True)
        video = intake.store_upload(Path(e["path"]))
        collab = e["collab"] if e["platform"] == "instagram" else None
        r = intake.evaluate(video, e["platform"], e["caption"], e["title"], e["followers"], collab, None,
                            log=lambda line: print("   ", line, flush=True))
        print(f"{e['key']}: done in {r['timing']['total_sec']:.0f} s", flush=True)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="The examples box (D-065).")
    ap.add_argument("--prepare", action="store_true")
    if ap.parse_args().prepare:
        prepare()
    for e in all_examples():
        print(f"{e['key']:24} {e['account']:22} {e['duration']:5.0f} s  {e['followers']:>11,.0f}  "
              f"{', '.join(e['notes'])}  [{'ready' if e['ready'] else 'not measured yet'}]")


if __name__ == "__main__":
    main()

"""Download, once, every free model file the tool measures with (D-069), so the public server never waits on a
download while a visitor's video is being measured. Run at build time on the server:

    COKE_CPU=1 python -m src.serve.prefetch

faster-whisper large-v3 (MIT), the AST sound-event model, the two sentiment models, EasyOCR's text detector and
MediaPipe's face detector - the same ones the study used (docs/04, D-027, D-028, D-031). About 5 GB in all.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.features import asr, audio, faces_text, sentiment  # noqa: E402


def main() -> None:
    for name, load in (("speech (faster-whisper large-v3)", lambda: asr.load_model(True)),
                       ("sound events (AST)", lambda: audio.load_ast(True)),
                       ("sentiment and emotion", lambda: sentiment.load_pair(True)),
                       ("faces (MediaPipe)", lambda: faces_text.load_face_detector(True)),
                       ("on-screen text (EasyOCR)", lambda: faces_text.load_text_detector(True))):
        print(f"{name} ...", flush=True)
        load()
    print("all model files are on disk")


if __name__ == "__main__":
    main()

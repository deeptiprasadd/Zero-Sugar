"""The quick check of D-072: what can be computed exactly without the video - the typical result for the account's
size and the caption beside the 192 - for the public Render site, where no video can be measured.

The study's own steps run on the caption alone (`metadata.text_counts`, `language`, `keywords`) in a throw-away folder;
the numbers come from the same saved reference values and base-rate model as the full tool.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

CAPTION_KEYS = ["hashtag_count", "emoji_count", "caplen_lang", "kw_event", "kw_promotional"]


def check(platform: str, followers: float | None, caption: str | None, answers: dict | None) -> dict:
    from src.features import common, keywords, language, metadata
    from src.serve import pipeline as P
    from src.serve.measure import point_at
    art = P.artefacts()
    diagnostics = {}
    caption_known = caption is not None
    if caption_known:
        work = Path(tempfile.mkdtemp(prefix="quick_"))
        saved = (common.CACHE, common.AUDIO, common.FRAMES)
        try:
            point_at(work)
            p, m = platform, "quick"
            common.update_cache(p, m, "language", language.one_video(p, m, caption))
            common.update_cache(p, m, "keywords", keywords.one_video(p, m, caption))
            common.update_cache(p, m, "meta", {**metadata.text_counts(caption), "creator_collab": None,
                                               "params": metadata.PARAMS})
            row = P.feature_row(common.read_cache(p, m), caption_known=True)
            X = P.model_inputs(row, art["schema"])
            d = P.diagnostics(art, row, X, platform)
            diagnostics = {k: d[k] for k in CAPTION_KEYS if k in d}
        finally:
            common.CACHE, common.AUDIO, common.FRAMES = saved
            shutil.rmtree(work, ignore_errors=True)
    return {"base_rate": P.base_rate(art, platform, followers),
            "diagnostics": diagnostics,
            "caption_given": caption_known,
            "hand_codes": P.hand_code_answers(art, answers, platform),
            "measured_on": "quick check (caption and account size)",
            "gates": art["card"]["gates"]}

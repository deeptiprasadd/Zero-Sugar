"""The model inputs that are derived from measured features - one implementation (D-055 section 4).

Training builds these in three places - the feature table (`assemble.py`), the statistics table
(`src/stats/hypotheses.py`) and the model table (`src/models/train.py`) - and the prediction tool must build
them for a new video in exactly the same way, or it would be served inputs that differ from the ones the
model learned (docs/11 section 3). So all of them call these functions. Moved here on 2026-10-17 without
changing a value: the three training tables were compared before and after, value by value.

Nothing here reads engagement.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Caption length is standardised within a caption language only where that language has this many videos
# in the analysis set; otherwise against the whole set (D-040, docs/07).
CAPLEN_MIN_LANG = 5


def either(va: pd.Series, vb: pd.Series) -> pd.Series:
    """Null-safe "a or b" for two keyword groups (5.11, D-036).

    True if either group hit, False only if both were searched and neither hit, null if neither was
    searched - a gap is never a "no".
    """
    hit = (va == True) | (vb == True)                       # noqa: E712
    searched = va.notna() | vb.notna()
    return pd.Series(np.where(hit, True, np.where(searched, False, None)), index=va.index)


def keyword_composites(out: pd.DataFrame) -> pd.DataFrame:
    """The two merged keyword features, so Block C fits the 18-20 budget (5.11, D-036)."""
    out["kw_promotional"] = either(out["kw_offer"], out["kw_new"])
    out["kw_experience"] = either(out["kw_taste"], out["kw_together"])
    return out


def video_measures(d: pd.DataFrame) -> pd.DataFrame:
    """Per-video transforms that need no statistic of the data set (D-040)."""
    d["cuts_log1p"] = np.log1p(d["cuts_per_sec"].astype(float))
    d["face_area0"] = d["mean_face_area"].astype(float).where(d["face_present_frac"] > 0, 0.0)
    d["caplen_log"] = np.log1p(d["caption_char_len"].astype(float))
    return d


def caplen_reference(focus: pd.DataFrame) -> dict:
    """Means and standard deviations of log caption length in the analysis set: overall, and per caption
    language with at least CAPLEN_MIN_LANG videos. Training standardises against these; the tool stores
    them and standardises a new video against the same numbers."""
    counts = focus["lang_caption"].value_counts()
    big = sorted(counts[counts >= CAPLEN_MIN_LANG].index)
    v = focus["caplen_log"]
    ref = {"all": {"mean": float(v.mean()), "sd": float(v.std())}, "by_language": {}}
    for lang in big:
        s = v[focus["lang_caption"] == lang]
        ref["by_language"][lang] = {"mean": float(s.mean()), "sd": float(s.std())}
    return ref


def caplen_lang(df: pd.DataFrame, ref: dict) -> np.ndarray:
    """Log caption length as a z-score within its caption language (or against the whole set)."""
    by = ref["by_language"]
    lang = df["lang_caption"]
    mean = np.where(lang.isin(list(by)), lang.map(lambda x: by.get(x, {}).get("mean")), ref["all"]["mean"])
    sd = np.where(lang.isin(list(by)), lang.map(lambda x: by.get(x, {}).get("sd")), ref["all"]["sd"])
    return ((df["caplen_log"].to_numpy(float) - mean.astype(float)) / sd.astype(float))


def flag01(s: pd.Series) -> pd.Series:
    """A yes/no feature as 1.0 / 0.0, missing stays missing."""
    return s.map({True: 1.0, False: 0.0})

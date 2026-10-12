"""The locked hand codes of the 192 focus videos with the derived variables fixed in D-050.

One place for every later step (P12 exploration, P13 tests, P14 models), so each reads the codes the
same way: "unsure" and blank are missing; categories under 10 videos are merged as D-050 lists them; the
four people groups come from `people_type()` (D-049); the 15 AI-character Shorts are flagged.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.coding.codebook_focus import people_type  # noqa: E402

CODES = config.DATA / "coding" / "focus_codes_FINAL.csv"
SAMPLE = config.DATA / "coding" / "focus_sample.csv"
CODES_SHA256 = "ab52f980f6cd1cc3327624503e21921ac42bc0ee83021c860151eacc73435d3a"

# the 11 yes/no columns of feature set H (D-050, P14) - 1 / 0 / NaN (missing)
H = ["hc_product_prominent", "hc_logo_prominent", "hc_person", "hc_creator_or_celebrity", "hc_humour",
     "hc_excitement", "hc_voice_excited", "hc_cta", "hc_sponsored", "hc_lifestyle", "hc_ugc"]
LABEL = {"hc_product_prominent": "product prominent", "hc_logo_prominent": "logo prominent",
         "hc_person": "a person appears", "hc_creator_or_celebrity": "creator or celebrity",
         "hc_humour": "humour", "hc_excitement": "excitement", "hc_voice_excited": "excited voice",
         "hc_cta": "call to action", "hc_sponsored": "sponsored disclosed", "hc_lifestyle": "lifestyle focus",
         "hc_ugc": "homemade (UGC) look"}
PEOPLE_ORDER = ["none", "ordinary_people", "influencer", "celebrity"]


def _yn(s: pd.Series, yes: str = "yes", no: str = "no") -> pd.Series:
    return s.map({yes: 1.0, no: 0.0})


def coded() -> pd.DataFrame:
    """Codes + derived variables, one row per focus video. Refuses to run on a changed codes file."""
    import hashlib
    if hashlib.sha256(CODES.read_bytes()).hexdigest() != CODES_SHA256:
        raise SystemExit(f"{CODES.name} does not match its recorded SHA-256 (D-049) - stopped")
    c = pd.read_csv(CODES, dtype=str, keep_default_na=False)
    s = pd.read_csv(SAMPLE, dtype=str, keep_default_na=False)
    c["ai_characters"] = c["media_id"].isin(s.loc[s["caption"].str.contains("Mourinho", case=False), "media_id"])
    c["people_type"] = [people_type(r) for r in c.to_dict("records")]
    c["people_group"] = c["people_type"].where(c["people_type"].isin(PEOPLE_ORDER))
    vis = {"none": "none or brief", "brief": "none or brief", "prominent": "prominent"}
    c["product_group"] = c["product_visibility"].map(vis)
    c["logo_group"] = c["logo_visibility"].map(vis)
    music = {"cinematic_orchestral": "cinematic", "no_music": "no music", "pop": "pop", "hiphop_rap": "other",
             "electronic_dance": "other", "rock": "other", "other_cant_tell": "other", "traditional_folk": "other"}
    c["music_group"] = c["music_type"].map(music)
    camp = {"promotion": "promotion", "event": "event", "food": "food", "new_product": "new product",
            "general_brand": "general or seasonal", "seasonal": "general or seasonal"}
    c["campaign_group"] = c["campaign_type"].map(camp)
    c["voice_group"] = c["voice_tone"].map({"excited": "excited", "calm": "calm", "no_voice": "no voice"})

    c["hc_product_prominent"] = c["product_group"].map({"prominent": 1.0, "none or brief": 0.0})
    c["hc_logo_prominent"] = c["logo_group"].map({"prominent": 1.0, "none or brief": 0.0})
    c["hc_person"] = _yn(c["people_present"])
    c["hc_creator_or_celebrity"] = c["people_type"].map({"celebrity": 1.0, "influencer": 1.0,
                                                         "ordinary_people": 0.0, "none": 0.0})
    c["hc_humour"] = _yn(c["humour_present"])
    c["hc_excitement"] = _yn(c["excitement_present"])
    c["hc_voice_excited"] = c["voice_tone"].map({"excited": 1.0, "calm": 0.0, "no_voice": 0.0})
    c["hc_cta"] = _yn(c["has_cta"])
    c["hc_sponsored"] = _yn(c["sponsored_disclosed"])
    c["hc_lifestyle"] = c["product_vs_lifestyle"].map({"lifestyle": 1.0, "product": 0.0})
    c["hc_ugc"] = c["ugc_vs_brand"].map({"ugc": 1.0, "brand": 0.0})
    assert not set(c.loc[c["music_type"] != "", "music_type"]) - set(music), "unmapped music type"
    keep = ["platform", "media_id", "ai_characters", "people_type", "people_group", "product_group", "logo_group",
            "music_group", "campaign_group", "voice_group", "product_vs_lifestyle", "ugc_vs_brand", *H]
    return c[keep].astype({h: float for h in H})


def with_focus(focus: pd.DataFrame) -> pd.DataFrame:
    """Join the codes onto a focus-set frame (one row per video); every focus video must be coded."""
    out = focus.merge(coded(), on=["platform", "media_id"], how="left", validate="1:1")
    if out["ai_characters"].isna().any():
        raise SystemExit("a focus video has no hand codes - stopped")
    out["ai_characters"] = out["ai_characters"].astype(bool)
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = coded()
    print(len(c), "videos;", {h: int(c[h].notna().sum()) for h in H})
    print("people:", c["people_group"].value_counts(dropna=False).to_dict(), "| AI flagged:", int(c["ai_characters"].sum()))

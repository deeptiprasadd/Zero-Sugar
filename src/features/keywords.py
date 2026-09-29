"""Task 5.16 - the six keyword groups fixed in docs/04 section 5.1 (proposal Block C).

The list was approved by the researcher on 2026-09-24 and written down **before this ran and
before any engagement result was seen**. This module implements it and nothing more: no group is
added, no term is added after seeing a result. A change would be a dated amendment in docs/04
section 5.1 with its reason.

    kw_offer        offer or prize            win, prize, giveaway, discount, coupon...
    kw_new          new or limited            new, launch, limited edition, out now...
    kw_taste        taste or refreshment      taste, delicious, refreshing, thirst, ice cold...
    kw_zero_sugar   zero or no sugar          **reuses `src/screen/zero_sugar.ZERO_TERMS`**
    kw_event        sport or music event      world cup, FIFA, stadium, concert, festival...
    kw_together     togetherness or sharing   share, together, friends, family, celebrate...

**Where each group is searched.** Two texts per video, never merged:
*   `transcript_en` - 5.6's English translation, so every video with speech is searched with the
    English lists whatever language it was spoken in;
*   `caption` - in **its own language** (captions are not translated, D-031), using the
    per-language lists below.

**A language with no list is recorded as *not searched*, never as "no hit".** That distinction is
the whole point: a Korean caption with no Korean list would otherwise look like a caption that
mentions no prize. `kw_*_searched` says which texts were actually searched, and a video with
neither a transcript nor a supported caption gets **null**, not False.

**Precision over recall**, the same rule `zero_sugar.py` states: a bare "free" matches "sugar
free", a bare "back" matches "back to school", a bare "live" matches "live your life", and a bare
"goal" matches football talk in a video about a concert. Such words are therefore used only inside
longer phrases. Every hit records the term that caused it, so any surprising count can be traced
to the word behind it.

**Deviation from section 5.1, recorded 2026-09-28 (D-035):** matching is case-insensitive and
NFKC-normalised but **not** accent-folded. Section 5.1 said accent-insensitive; folding would break
Vietnamese, where the diacritics carry meaning (`mới` "new" folds to `moi`, which also collides
with `môi` "lips"). Accented and unaccented spellings are listed explicitly instead, which is what
`zero_sugar.py` already does for Spanish and Portuguese.

Word boundaries apply to Latin-script terms. Thai and Korean are written without spaces between
words, and Hindi and Arabic attach matras and clitics, so those terms match as substrings - the
same choice `zero_sugar.py` made.

Runs on all 300 videos (D-030: the focus applies at analysis, not at measurement).

Usage:
    python -m src.features.keywords --samples 3     # show matched snippets for spot-checking
    python -m src.features.keywords
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features import common  # noqa: E402
from src.screen.zero_sugar import ZERO_TERMS  # noqa: E402  (one vocabulary, one source of truth)

SUMMARY = config.INTERIM / "keywords_summary.csv"

# --------------------------------------------------------------------- the six groups
# Curated per language, not machine-translated, and deliberately narrow. Where a short word
# would over-match it appears only inside a phrase.
TERMS: dict[str, dict[str, list[str]]] = {
    "kw_offer": {
        "en": ["giveaway", "give away", "prize", "sweepstake", "contest", "win a", "win big",
               "chance to win", "enter to win", "winner of", "discount", "coupon", "promo code",
               "voucher", "special offer", "limited offer", "buy one", "cashback", "for free"],
        "es": ["sorteo", "premio", "gana un", "gana una", "ganá", "gratis", "descuento", "cupón",
               "cupon", "promoción", "promocion", "concurso"],
        "pt": ["sorteio", "prêmio", "premio", "ganhe", "grátis", "gratis", "desconto", "cupom",
               "promoção", "promocao", "concurso"],
        "tr": ["çekiliş", "cekilis", "ödül", "odul", "hediye", "kazan", "indirim", "kupon",
               "yarışma", "yarisma"],
        "vi": ["trúng thưởng", "quà tặng", "giải thưởng", "miễn phí", "giảm giá", "khuyến mãi",
               "bốc thăm"],
        "ko": ["경품", "추첨", "당첨", "이벤트", "할인", "쿠폰", "증정", "무료"],
        "th": ["ลุ้น", "ของรางวัล", "รางวัล", "แจก", "ฟรี", "ส่วนลด", "คูปอง", "ชิงโชค"],
        "hi": ["जीत", "इनाम", "मुफ्त", "छूट", "कूपन", "ऑफर", "प्रतियोगिता"],
    },
    "kw_new": {
        "en": ["new", "brand new", "launch", "launching", "introducing", "limited edition",
               "limited-edition", "now available", "out now", "coming soon", "is back",
               "are back", "back again", "returns"],
        "es": ["nuevo", "nueva", "lanzamiento", "edición limitada", "edicion limitada",
               "ya disponible", "estrena", "llegó", "llego"],
        "pt": ["novo", "nova", "lançamento", "lancamento", "edição limitada", "edicao limitada",
               "já disponível", "ja disponivel", "chegou"],
        "tr": ["yeni", "lansman", "sınırlı üretim", "sinirli uretim", "özel seri", "ozel seri",
               "satışta", "satista"],
        "vi": ["mới", "ra mắt", "phiên bản giới hạn", "đã có mặt", "sắp ra"],
        "ko": ["신제품", "출시", "새로운", "한정", "리뉴얼"],
        "th": ["ใหม่", "เปิดตัว", "ลิมิเต็ด", "วางจำหน่าย", "มาแล้ว"],
        "hi": ["नया", "नई", "लॉन्च", "लिमिटेड", "पेश", "अब उपलब्ध"],
    },
    "kw_taste": {
        "en": ["taste", "tasty", "delicious", "refreshing", "refreshment", "thirst", "crisp",
               "flavour", "flavor", "ice cold", "ice-cold", "chilled", "fizzy", "yummy"],
        "es": ["sabor", "delicioso", "deliciosa", "refrescante", "refrescar", "sed",
               "bien fría", "bien fria"],
        "pt": ["sabor", "delicioso", "deliciosa", "refrescante", "refrescar", "sede", "gelada",
               "geladinha", "gostoso"],
        "tr": ["lezzet", "lezzetli", "ferahlık", "ferahlik", "serinlik", "buz gibi", "tazele"],
        "vi": ["hương vị", "ngon", "mát lạnh", "giải khát", "sảng khoái"],
        "ko": ["맛있", "시원", "청량", "갈증"],
        "th": ["อร่อย", "สดชื่น", "รสชาติ", "ดับกระหาย", "ซ่า"],
        "hi": ["स्वाद", "स्वादिष्ट", "ताज़ा", "ताजा", "ठंडा", "प्यास"],
    },
    # Section 5.1: this group reuses the vocabulary already built and checked in zero_sugar.py,
    # so the two paths can never disagree. Its language coverage is that file's.
    "kw_zero_sugar": {lang: list(terms) for lang, terms in ZERO_TERMS.items()},
    "kw_event": {
        "en": ["world cup", "fifa", "uefa", "champions league", "stadium", "kick off", "kickoff",
               "match day", "matchday", "concert", "festival", "live show", "on stage", "lineup",
               "line-up", "playlist", "tickets"],
        "es": ["mundial", "fifa", "estadio", "partido", "concierto", "festival", "gira",
               "entradas", "escenario"],
        "pt": ["copa", "fifa", "estádio", "estadio", "jogo", "show", "festival", "turnê",
               "turne", "ingressos", "palco"],
        "tr": ["dünya kupası", "dunya kupasi", "fifa", "stadyum", "maç", "mac", "konser",
               "festival", "sahne", "bilet"],
        "vi": ["world cup", "fifa", "sân vận động", "trận đấu", "concert", "lễ hội", "sân khấu"],
        "ko": ["월드컵", "피파", "경기장", "콘서트", "페스티벌", "무대", "티켓"],
        "th": ["ฟุตบอลโลก", "ฟีฟ่า", "สนาม", "แมตช์", "คอนเสิร์ต", "เทศกาล", "เวที", "บัตร"],
        "hi": ["वर्ल्ड कप", "फीफा", "स्टेडियम", "मैच", "कॉन्सर्ट", "फेस्टिवल", "टिकट"],
    },
    "kw_together": {
        "en": ["share", "sharing", "together", "friends", "family", "celebrate", "celebration",
               "moment", "reunion", "gather", "party"],
        "es": ["comparte", "compartir", "juntos", "juntas", "amigos", "familia", "celebra",
               "celebración", "celebracion", "momento", "reunión", "reunion", "fiesta"],
        "pt": ["compartilhe", "compartilhar", "juntos", "juntas", "amigos", "família", "familia",
               "celebre", "comemorar", "momento", "reunião", "reuniao", "festa"],
        "tr": ["paylaş", "paylas", "birlikte", "arkadaşlar", "arkadaslar", "aile", "kutlama",
               "buluşma", "bulusma"],
        "vi": ["chia sẻ", "cùng nhau", "bạn bè", "gia đình", "ăn mừng", "khoảnh khắc", "tụ họp"],
        "ko": ["함께", "같이", "친구", "가족", "축하", "순간", "모임", "공유"],
        "th": ["แบ่งกัน", "ด้วยกัน", "เพื่อน", "ครอบครัว", "ฉลอง", "ช่วงเวลา", "รวมตัว", "แชร์"],
        "hi": ["शेयर", "साथ", "दोस्त", "परिवार", "जश्न", "पल", "मिलकर"],
    },
}
GROUPS = list(TERMS)
PARAMS = {"groups": GROUPS, "fixed_in": "docs/04 section 5.1 (approved 2026-09-24)",
          "accent_folding": False, "deviation": "D-035", "version": 1,
          "languages": {g: sorted(TERMS[g]) for g in GROUPS}}

_LATIN = re.compile(r"^[a-z0-9\s\-'’áàâãäéèêëíìîïóòôõöúùûüñçğışöüăđơưạảấầẩẫậắằẳẵặẹẻẽếềểễệ]+$")
_URL = re.compile(r"https?://\S+|www\.\S+")
_MENTION = re.compile(r"@[A-Za-z0-9_.]+")
_WS = re.compile(r"\s+")


def _norm(text: object) -> str:
    """NFKC-fold and casefold, as zero_sugar.py does. Accents are kept (see D-035)."""
    return unicodedata.normalize("NFKC", str(text or "")).casefold()


def clean(text: str) -> str:
    """Drop links and handles, keep hashtag words without the hash (docs/04 section 5.1)."""
    t = _URL.sub(" ", str(text or ""))
    t = _MENTION.sub(" ", t)
    t = t.replace("#", " ")
    return _WS.sub(" ", _norm(t)).strip()


def _hit(blob: str, term: str) -> bool:
    """Word-boundary match for Latin-script terms, substring for scripts without spaces."""
    t = _norm(term)
    if _LATIN.match(t):
        return re.search(rf"(?<!\w){re.escape(t)}(?!\w)", blob) is not None
    return t in blob


def search(blob: str, group: str, lang: str) -> list[str]:
    terms = TERMS[group].get(lang)
    if not terms:
        return []
    return [t for t in terms if _hit(blob, t)]


def one_video(platform: str, media_id: str, caption: str) -> dict:
    doc = common.read_cache(platform, media_id)
    asr, lang_block = doc.get("asr") or {}, doc.get("language") or {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    en_blob = clean(asr.get("transcript_en") or "")
    cap_blob = clean(caption)
    cap_lang = lang_block.get("lang_caption")

    out: dict = {"status": "ok", "caption_lang": cap_lang,
                 "searched_transcript_en": bool(en_blob),
                 "searched_caption": bool(cap_blob) and bool(cap_lang)}
    n_hit = 0
    for g in GROUPS:
        sources, terms = [], []
        # The English translation is searched with the English list for every video with speech.
        if en_blob and TERMS[g].get("en"):
            found = search(en_blob, g, "en")
            if found:
                sources.append("transcript_en")
                terms += found
        # The caption is searched in its own language, if that language has a list.
        cap_searchable = bool(cap_blob) and bool(cap_lang) and bool(TERMS[g].get(cap_lang))
        if cap_searchable:
            found = search(cap_blob, g, cap_lang)
            if found:
                sources.append("caption")
                terms += found
        searched = bool(en_blob and TERMS[g].get("en")) or cap_searchable
        out[g] = bool(terms) if searched else None
        out[f"{g}_source"] = "+".join(sources) or None
        out[f"{g}_terms"] = "; ".join(dict.fromkeys(terms)) or None
        out[f"{g}_searched"] = ("transcript_en+caption" if (en_blob and cap_searchable)
                                else "transcript_en" if en_blob
                                else "caption" if cap_searchable else "not_searched")
        n_hit += 1 if out[g] else 0
    out["n_groups_hit"] = n_hit
    out["any_group_searched"] = any(out[f"{g}_searched"] != "not_searched" for g in GROUPS)
    out["params"] = PARAMS
    out["processed_at"] = now
    return out


def run(idx: pd.DataFrame, force: bool) -> pd.DataFrame:
    rows = []
    for _, r in idx.iterrows():
        cached = common.read_cache(r["platform"], r["media_id"]).get("keywords") or {}
        p = (cached if cached.get("params") == PARAMS and not force
             else one_video(r["platform"], r["media_id"], r["caption"]))
        if p is not cached:
            common.update_cache(r["platform"], r["media_id"], "keywords", p)
        rows.append({"platform": r["platform"], "media_id": r["media_id"],
                     **{k: v for k, v in p.items() if k != "params"}})
    df = pd.DataFrame(rows)
    df.to_csv(SUMMARY, index=False)
    print(f"-> {SUMMARY.relative_to(config.ROOT)}  ({len(df)} rows)")
    return df


def report(df: pd.DataFrame, samples: int) -> None:
    print(f"\n{len(df)} videos; searched at all: {int(df['any_group_searched'].sum())}")
    print(f"  English transcript available: {int(df['searched_transcript_en'].sum())}   "
          f"caption with a known language: {int(df['searched_caption'].sum())}")
    print("\nhits per group (counts only - no engagement is read here):")
    print(f"  {'group':16} {'hit':>5} {'no hit':>7} {'not searched':>13}   platforms (hit)")
    for g in GROUPS:
        hit = df[g] == True          # noqa: E712  (None must stay distinct from False)
        no = df[g] == False          # noqa: E712
        ns = df[g].isna()
        by = df[hit].groupby("platform").size().to_dict()
        print(f"  {g:16} {int(hit.sum()):5} {int(no.sum()):7} {int(ns.sum()):13}   {by}")
    print(f"\ngroups hit per video: median {df['n_groups_hit'].median():.0f}, "
          f"none {int((df['n_groups_hit'] == 0).sum())}, "
          f"three or more {int((df['n_groups_hit'] >= 3).sum())}")
    print("\nwhich text produced the hits:")
    src = pd.Series([s for g in GROUPS for s in df[f"{g}_source"].dropna()])
    print(f"  {src.value_counts().to_dict()}")
    print("\ncaption languages with no list for some group (recorded as not searched):")
    unsearched = df[[f"{g}_searched" for g in GROUPS]].eq("not_searched").any(axis=1)
    print(f"  {df.loc[unsearched, 'caption_lang'].value_counts(dropna=False).head(8).to_dict()}")

    if samples:
        print(f"\n--- spot check: up to {samples} matched snippets per group, as docs/04 "
              f"section 5.1 requires ---")
        for g in GROUPS:
            got = df[(df[g] == True)].head(samples)      # noqa: E712
            print(f"\n{g}:")
            for _, r in got.iterrows():
                print(f"  {r['platform'][:2]} {r['media_id']:14} [{r[f'{g}_source']}] "
                      f"terms: {r[f'{g}_terms']}")
    print("\nNo engagement value is read here. The list was fixed before this ran (docs/04 §5.1).")


def main() -> None:
    ap = argparse.ArgumentParser(description="5.16 - the six approved keyword groups.")
    ap.add_argument("--platform", choices=["youtube", "instagram", "both"], default="both")
    ap.add_argument("--samples", type=int, default=0, help="print matched terms for spot-checking")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    idx = common.video_index(args.platform)
    df = run(idx, args.force)
    report(df, args.samples)


if __name__ == "__main__":
    main()

# 04 — Multilingual Pipeline

The corpus is deliberately multilingual (decision D-003). Every text-touching stage must
therefore handle Hindi, Spanish, Portuguese, Arabic, Indonesian and English — and Arabic
is right-to-left, which breaks naive OCR and tokenisation.

This document records how each stage handles language, and where quality degrades.

---

## 1. Language detection

Language is a **variable**, not just plumbing. Detect it once, early, and reuse.

**Source of truth: Whisper's detected language on the audio track.** Metadata fields lie —
YouTube's `defaultAudioLanguage` is frequently missing or wrong, and Instagram provides
nothing.

Record three separate fields, because they genuinely can differ:

| Field | Source | Why separate |
|---|---|---|
| `lang_audio` | Whisper detection | The spoken language |
| `lang_caption` | `langdetect` / `fasttext-langid` on caption | Captions are often English even when audio is not |
| `lang_onscreen` | OCR language detection | On-screen text may be a third language |

Code-switching is common in Indian marketing content (Hinglish especially). Add a
`is_code_switched` flag where Whisper confidence is low or the three fields disagree, and
report how many videos this affects — it is a genuine finding about the corpus, not just a
nuisance.

---

## 2. Speech recognition

**Model:** `faster-whisper` with `large-v3`. Multilingual, and by a wide margin the best
free option for Hindi, Arabic and Indonesian.

**Two outputs per video, both retained:**

1. `transcript_native` — `task=transcribe`, original language. Used for speech-rate,
   word-count and prosody-aligned features.
2. `transcript_en` — `task=translate`, English. Used for anything requiring cross-lingual
   comparability.

**Why both:** speech rate must be computed on the native transcript (translation changes
word counts, and words-per-minute is not comparable across a translation). But sentiment
and emotion are far more reliable in English, and comparing a Hindi sentiment score to a
Spanish one from different models is not defensible.

**Quality caveat to record:** Whisper's word error rate is meaningfully higher for Hindi,
Arabic and Indonesian than for English. Derived speech features are therefore noisier in
those markets. Since market is also a grouping variable, this noise is **not random with
respect to the design** — state it explicitly as a limitation.

**Validation:** hand-check 5 transcripts per language (30 total). Record a rough quality
rating in §6. If any language is badly served, consider dropping that market rather than
modelling noise.

---

## 3. On-screen text (OCR)

**Model:** EasyOCR (~80 languages, single interface) or PaddleOCR (better accuracy,
per-language model downloads).

**Recommendation: EasyOCR.** At n=300 the accuracy gap does not justify managing six model
sets, and the on-screen-text features being extracted are coarse.

**Arabic specifically** needs checking — RTL rendering and cursive script are where OCR
most often fails. Validate on 10 Arabic frames before trusting the output.

**Keep the features coarse.** Do not model OCR text semantically. Extract only:

- `ocr_text_frame_frac` — fraction of sampled frames containing any text
- `ocr_word_count` — total words detected
- `ocr_mean_text_area` — mean fraction of frame occupied by text

These survive OCR errors. Sentiment or keyword analysis on OCR output across six languages
would not.

---

## 4. Sentiment and emotion

This is where multilingual support is weakest, and the honest answer is to accept reduced
resolution rather than fake precision.

| Task | Model | Language coverage | Decision |
|---|---|---|---|
| Sentiment | `cardiffnlp/twitter-xlm-roberta-base-sentiment` | ~8 languages, social-media trained | **Primary** — run on native text |
| Sentiment (check) | Same model on `transcript_en` | English | Run both; report correlation |
| Emotion | `j-hartmann/emotion-english-distilroberta-base` | English only | Run on **translated** text only |
| VADER | English only | English | Skip — not multilingual |

**Decision on emotion:** run emotion classification on the English translation only, and
state clearly in the methods that emotion is measured post-translation. Translation
flattens emotional nuance, and this weakens H3. It is better to say so than to imply a
multilingual emotion measurement that was not made.

**Cross-check:** run sentiment natively *and* on the translation, then report the
correlation between the two. High correlation supports the translated-emotion approach.
Low correlation is itself a finding worth reporting.

---

## 5. Text features that are safe across languages

Some are language-invariant and should be preferred given the above:

| Feature | Cross-lingual? | Note |
|---|---|---|
| Caption character length | ✅ | Character counts differ in meaning across scripts — normalise within language |
| Hashtag count | ✅ | Fully invariant |
| Emoji count | ✅ | Fully invariant, and emoji are a genuine cross-cultural signal |
| Mention count | ✅ | Invariant |
| Question-mark presence | ⚠️ | Arabic uses `؟` — match both |
| Caption word count | ⚠️ | Not comparable for scripts without spaces |
| CTA presence | ⚠️ | Needs per-language patterns, or LLM annotation |
| Readability (Flesch) | ❌ | English-only formula. **Drop it** — it was in the plan, it does not survive multilingual scope |
| Sentiment | ⚠️ | See §4 |

**Given the ~30-feature budget (D-007), prefer the invariant features.** Emoji count and
hashtag count are cheap, robust, and genuinely predictive in the literature.

**CTA detection:** use LLM annotation rather than per-language regex. Maintaining
call-to-action patterns in six languages is not a good use of the time, and the LLM handles
it in one prompt.

### 5.1 Keyword groups for task 5.16 — fixed 2026-09-24, before the task runs

Approved by the researcher in advance (2026-09-24) and recorded here **before any engagement
result was looked at**, which is the condition the task carries. Six groups, chosen from the
proposal's Block C and from what this corpus actually contains; each is a yes/no flag per video,
not a count, because counts reward long text.

| Group | Flag | Matches (English stems; ✱ = also written per language, see below) |
|---|---|---|
| Offer or prize | `kw_offer` | win, winner, prize, giveaway, contest, sweepstake, free, discount, offer, coupon, code ✱ |
| New or limited | `kw_new` | new, launch, introducing, limited edition, now available, back, return ✱ |
| Taste or refreshment | `kw_taste` | taste, tasty, delicious, refreshing, refreshment, thirst, crisp, flavour/flavor, ice cold ✱ |
| Zero or no sugar | `kw_zero_sugar` | zero sugar, no sugar, sugar free, zero — **reuses the seven-language vocabulary already built and checked in `src/screen/zero_sugar.py`** |
| Sport or music event | `kw_event` | world cup, FIFA, match, final, stadium, goal, concert, festival, tour, live, playlist, artist ✱ |
| Togetherness or sharing | `kw_together` | share, sharing, together, friends, family, celebrate, moment, meal, reunion ✱ |

**Where they are matched.** The English translation of the speech (5.6) for every video with
speech, and the caption in its own language. Captions are **not** translated (D-031), so
non-English captions are matched with per-language term lists for the corpus's main caption
languages — Spanish, Portuguese, Korean, Vietnamese, Turkish, Thai, Hindi — built the way
`zero_sugar.py`'s vocabularies were, and spot-checked before use. A caption in a language with
no list is recorded as **not searched** (null), never as "no hit".

**Recorded per hit:** which group, which text it came from (`transcript_en` or `caption`), and
the matched term, so a surprising result can be traced to the word that caused it.

**Rules this task inherits:** word-boundary matching, accent- and case-insensitive; no stemming
beyond the listed variants (it misfires across languages); hashtags count as caption text with
the `#` removed (5.9's cleaning). The list is not extended after results are seen — an addition
would be a dated amendment here, with its reason.

#### Amendments to §5.1

| Date | Amendment | Why |
|---|---|---|
| 2026-09-28 | **Matching is case-insensitive and NFKC-normalised but *not* accent-folded** (D-035). Accented and unaccented spellings are listed explicitly instead, as `zero_sugar.py` already does for Spanish and Portuguese. | Folding accents breaks Vietnamese, where they carry meaning: `mới` ("new") folds to `moi`, which collides with `môi` ("lips"). Listing both spellings keeps Spanish and Portuguese recall without inventing Vietnamese matches. |
| 2026-09-28 | Word boundaries apply to Latin-script terms only; Thai, Korean, Hindi and Arabic terms match as substrings. | Thai and Korean are written without spaces between words, and Hindi and Arabic attach matras and clitics, so a boundary match would miss nearly everything. Same choice as `zero_sugar.py`. |
| 2026-09-28 | Short words that over-match are used only inside longer phrases: "free" (matches *sugar free*), "back" (*back to school*), "live" (*live your life*), "goal", "match", "final", "tour". | Precision over recall, the rule `zero_sugar.py` states: a false hit is invisible downstream, a miss is recorded as a miss. |

**Coverage as implemented** (`src/features/keywords.py`). Five groups carry lists for **English,
Spanish, Portuguese, Turkish, Vietnamese, Korean, Thai and Hindi** — the languages §5.1 named.
`kw_zero_sugar` reuses `zero_sugar.ZERO_TERMS`, whose languages are **en, es, pt, ar, th, id, hi**.
A caption in a language with no list for a group is recorded as **not searched** for that group,
never as "no hit", and the English translation of the speech is searched with the English lists
whatever the spoken language was.

---

## 6. Language as a control variable

`language` and `market` enter every model as controls — they are confounded with audience
size, platform norms and posting cadence.

With ~25 videos per market, a six-level categorical uses five degrees of freedom against a
30-feature budget. Two options:

- **Preferred:** collapse to `language_family` or `region` (3–4 levels) to save degrees of
  freedom.
- **Alternative:** treat market as a random effect in the mixed-effects models (Phase 6),
  which is more efficient and handles the small cells better.

Decide before modelling and record the choice here.

---

## 7. Validation log

### Spoken language found (5.6, 2026-09-21)

faster-whisper `large-v3` on all 300 videos: **194 with speech**, 98 with no detected voice,
6 with no intelligible speech (stock phrases only, D-027), 2 silent (D-025).

| Language | Videos | | Language | Videos |
|---|---|---|---|---|
| English | 102 | | Nepali | 6 |
| Portuguese | 24 | | Bengali | 5 |
| Spanish | 17 | | Turkish, German, Vietnamese | 3 each |
| Korean | 12 | | Malay, Swahili | 2 each |
| Hindi | 8 | | Chinese | 1 (a false reading - see below) |
| Thai | 6 | | Arabic, Indonesian | 0 |

The language plan above assumed Hindi, Spanish, Portuguese, Arabic, Indonesian and English.
The corpus as collected has **no Arabic or Indonesian speech** and adds Korean, Thai, Nepali,
Bengali and others.

**Language agrees with market wherever the account is regional:** Brazil -> Portuguese (16),
South Korea -> Korean (12), Thailand -> Thai (6), Turkiye -> Turkish (3), LatAm/Mexico ->
Spanish (8), Malaysia -> Malay, Kenya -> Swahili. **The global YouTube channel is the
exception: 28 of its 107 videos with speech are not in English** - a Kathmandu/Pokhara momo
series in Nepali, a Bengali jingle ("সাথে থাকলে সাথ বাড়ে"), Vietnamese Tet content,
Portuguese, German and Hindi. For that channel, `market = Global/US` describes the account,
not the audience of the video; `lang_audio` is the better control there (section 6).

**One false language:** `DTIKnsGjKlL` (a Crocs walking video) reads as Chinese from a sung
"la la la"; it carries the low-confidence flag. 9 videos have spoken-language probability
below 0.5, 47 carry the low-confidence flag (D-027).

### ASR quality spot-check

**Method, stated plainly:** transcripts cannot be checked by listening here. They were checked
against **subtitles burned into the picture**, read from the frame at each spoken segment's
midpoint (the frames of 5.3). Three videos per language were drawn **at random** (seed
20260921), three segments each. A line counts as checkable only where on-screen text
corresponds to the speech.

| Language | Videos drawn | Checkable lines | Matched | Notes |
|---|---|---|---|---|
| English | 3 | 3 | 3 | "from Vancouver" on screen -> "Came all the way from Vancouver for this". One video is a song, one has unreadably small text |
| Portuguese | 3 | 2 | 2 | "bora completar essa colecao?" exact. Two José Mourinho interviews have no subtitles; transcripts coherent |
| Spanish | 3 | 3 | 3 | "Me apasiona todo este negocio" exact. One song's English translation failed (flagged, D-027) |
| Hindi (mostly Hindi-English mixed) | 3 | 3 | 3 | By meaning: "Coca-Cola Foodmarks haina" -> "There's Coca-Cola Food Marks, right?" |
| Korean | 3 | 4 | 4 | "코카-콜라 맛있다!", "맛있는 걸 선택해!", "이거 역대급 코-크 인데요?" exact |
| **Total** | **15** | **15** | **15** | |

**What this does and does not show.** Every checkable line matched. But videos with subtitles
tend to have clear speech; songs and low-confidence fragments mostly have none, so this check
cannot put an error rate on the hard cases. That is what the low-confidence flag is for, and
the limitation is stated in the methods chapter. One transcript found wrong while testing - a
German ad heard as "Fischen vor den Pricken" under music - is what the per-word probability
rule catches (D-027).

### OCR spot-check

| Language | Frames checked | Usable? | Notes |
|---|---|---|---|
| Arabic (priority) | | | |
| Hindi | | | |
| Others | | | |

### Sentiment cross-check

| Metric | Value |
|---|---|
| Correlation, native vs translated sentiment | |
| Videos code-switched | |
| Videos where `lang_audio` ≠ `lang_caption` | |

# 13 — Hand-coding of the 192 focus videos (proposal measures P1–P9)

**Status:** Codebook fixed 2026-10-04 (D-049), before the first answer. **Coded by the researcher on
2026-10-09 and locked the same day** (`data/coding/focus_codes_FINAL.csv`, read-only, SHA-256 in
`focus_codes_FINAL.sha256`): 192 videos, 180 with every question answered, 14 answers left blank (missing).
The coding took 110 minutes for 100 minutes of video, so most videos were not watched in full with sound.
The 15 videos of an AI-generated-character series were set to "no person, no celebrity, no creator" by
the researcher's rule (D-049 note of 9 October; changes listed in `data/coding/focus_codes_changes.csv`).

---

## 1. Why

The proposal asks for measures that the automated routes could not deliver or that were dropped:
product visibility (D-037), brand/logo visibility, call to action, people (none / ordinary people /
creator / celebrity) and humour (D-038), excitement, music type (D-033), voice tone, campaign type and
sponsored content (D-032), product- vs lifestyle-focused and user- vs brand-generated. The researcher
decided on 4 October that none of them should be missing. They are measured here **by hand**, by the
researcher, on all 192 videos of the analysis set (D-030, D-039).

## 2. How

- **All 192 focus videos** (Instagram 120, YouTube 72), one at a time, in one random order (seed
  20261005), watching the whole video with sound and reading its caption or title.
- **Blind to engagement and to every earlier label.** The coding page shows the video, the account name
  and the caption or title only - no likes, comments, views, followers or engagement measure, no earlier
  code, no Zero Sugar label, no automated output, and no link to the original post (it would show likes).
- **Every click is saved at once** (`data/coding/focus_codes.csv`, with the time of the first and the
  last answer per video). When all 192 are coded, a read-only copy with a SHA-256 fingerprint is made
  before any analysis reads the codes.
- **The questions are fixed before the first answer** and are shown below exactly as on the page. Four
  repeat the 15 September codebook word for word, so the 40 videos coded both times give a repeat check;
  two reuse the wording of two automated labels that had no human check (D-038), so those labels can
  now be compared with a human answer (they still never enter a model).
- **"Unsure" counts as missing** in every analysis. The four people groups are derived: celebrity, else
  creator, else ordinary people (any person on screen), else none.
- **The new codes are a declared addition.** Every result already reported stays as reported; analyses
  that use the new codes are written down before they run.

Run the page with `python -m src.coding.focus_app` (opens in the browser; close any time, it resumes at
the first unfinished video).

## 3. Limitations stated in advance

- One coder. The repeat check covers four questions on 40 videos (and product "none vs any"); the other
  questions have no repeat check unless a subset is re-coded.
- No transcript is shown, as on 15 September, so speech in a language the coder does not know is judged
  from the pictures, caption and sound.
- "Sponsored" is judged from the caption and the video; the platform's own paid-partnership tag is not
  visible on the page.
- Music type is judged by ear from a short fixed list; it is a coder's judgement, not a measurement.

---

## The questions, exactly as shown on the coding page

Generated from `src/coding/codebook_focus.py`. Questions marked *as 15 Sep* repeat the first codebook word for word.

### On screen

**1. How visible is a Coca-Cola can or bottle?** (`product_visibility`, P1)

Any Coca-Cola can or bottle, any variant (Zero Sugar, Original Taste, Diet/Light, flavours). Cups, glasses, fridges, signs and trucks do not count here - they belong to the next question. NONE: no can or bottle at any point. BRIEF: a can or bottle appears only in passing - a glimpse, small, in the background or partly out of shot. PROMINENT: a can or bottle is clearly a main subject at least once - large in frame and in focus, e.g. held up to camera, poured, a close-up, or an end pack shot.

Options: None · Brief · Prominent · Unsure

**2. How visible is the Coca-Cola logo or name?** (`logo_visibility`, P2)

The Coca-Cola script logo, the red disc, or the words 'Coca-Cola' / 'Coke' anywhere - on packs, cups, signs, fridges, clothes, on-screen graphics or an end card. NONE: never visible. BRIEF: only in passing - small, in the background, or for a moment. PROMINENT: clearly a main subject at least once - large and in focus, e.g. a full-screen logo or end card, a close-up of the logo on a can, a big sign the camera dwells on.

Options: None · Brief · Prominent · Unsure

### People

**3. Does any person appear?** (`people_present`, P4)

A real person is seen on screen at any point - a face or a body. Hands alone (holding a can) do not count; cartoons and animated characters do not count. YES: friends at a table, a crowd, a presenter, a footballer, a creator talking to camera. NO: only pack shots, food, graphics or animation; only hands.

Options: Yes · No · Unsure

**4. Does a celebrity appear?** (`has_celebrity`, P4 - *as 15 Sep*)

A widely famous person - film, TV, music or sports star, or a well-known public figure - is seen on screen or clearly heard. Famous mainly for their own work, not for social media. Fans or crowds at a celebrity's event do not count unless the celebrity is shown. YES: a famous singer or footballer drinking a Coke; a film star in an ad. NO: ordinary people at a picnic; a crowd at a concert where the singer is never shown.

Options: Yes · No · Unsure

**5. Does a social-media creator appear?** (`has_influencer`, P4 - *as 15 Sep*)

A person known mainly from Instagram, YouTube or TikTok (food, lifestyle, comedy, travel creators) appears - typically talking to camera in their own style. A celebrity who also posts online counts as celebrity, not creator. YES: a food vlogger reviewing a restaurant with a Coke; a comedy creator doing a skit. NO: actors in a studio ad; staff or delivery workers; a famous singer (that is celebrity).

Options: Yes · No · Unsure

### Tone

**6. Is the video meant to be funny?** (`humour_present`, P5 - *as 15 Sep*)

The video clearly aims to amuse: jokes, comic acting, playful exaggeration, memes, funny situations or reactions. Merely cheerful or upbeat does not count. YES: a comic skit, a prank, a funny fail, a meme-style edit. NO: a happy concert montage, friends smiling at a picnic, a stylish product shot.

Options: Yes · No · Unsure

**7. Is the video meant to be exciting?** (`excitement_present`, P5)

The video clearly aims to thrill or pump up the viewer: sport action, goals and celebrations, cheering crowds, stunts, dramatic build-ups, a countdown or reveal, high-energy music with fast cutting. Merely cheerful, pleasant or upbeat does not count. YES: a goal-celebration montage, a concert crowd jumping, a fast-cut reveal of a new can. NO: friends chatting over lunch, a calm recipe video, a slow product shot with soft music.

Options: Yes · No · Unsure

### Sound

**8. What kind of music plays, mainly?** (`music_type`, P6)

Listen with the sound on and pick the style of the main music; if several pieces play, pick the one heard longest. NO MUSIC: only speech, natural sound or silence. POP: chart-style songs, including K-pop, Latin pop and film songs (e.g. Bollywood). HIP-HOP / RAP. ELECTRONIC / DANCE: EDM, house, club beats, mostly without singing. ROCK. TRADITIONAL / FOLK: a local traditional style from any country. CINEMATIC / ORCHESTRAL: film-score style, strings, epic build-ups. OTHER / CAN'T TELL: anything else, a short jingle only, or too faint to judge.

Options: No music · Pop · Hip-hop / rap · Electronic / dance · Rock · Traditional / folk · Cinematic / orchestral · Other / can't tell

**9. How does the speaking voice sound?** (`voice_tone`, P7)

Listen to people talking or a voice-over - not singing. If the tone changes, pick what most of the talking sounds like. EXCITED: energetic, loud, fast or enthusiastic - a sports commentator, a hyped presenter, shouting friends. CALM: relaxed, conversational or soft - a chat, a gentle voice-over. NO VOICE: nobody speaks - no voice at all, or the only voice is singing.

Options: Excited · Calm · No voice · Unsure

### Message and campaign

**10. Is there a call to action?** (`has_cta`, P3 - *as 15 Sep*)

The video, its on-screen text, the voice-over or the caption asks the viewer to do something: buy, try, pre-book, follow, comment, share, tag, enter a contest, visit a place, scan a code, collect items. A slogan alone (e.g. 'Real Magic') is not a call to action. YES: 'Comment below to win', 'Pre-book now', 'Collect all the cans', 'Visit our stall'. NO: 'Enjoy an ice-cold Coke', 'Real Magic', a hashtag on its own.

Options: Yes · No

**11. What kind of campaign is this, mainly?** (`campaign_type`, P8)

If two fit, pick the one the video is mainly about. NEW PRODUCT: a new flavour, pack or limited edition is announced or shown as new. EVENT: a sport, music or entertainment event - a World Cup, a match, a concert, a festival, a film tie-in. SEASONAL: a festival or season - Ramadan, Christmas, Diwali, Lunar New Year, summer, holidays. PROMOTION: an offer, price, discount, contest, giveaway or collectable. FOOD: Coca-Cola with a meal - food pairing, a restaurant or delivery partner. GENERAL BRAND: none of these - the brand's mood or everyday moments.

Options: New product · Event · Seasonal · Promotion · Food · General brand · Unsure

**12. Is the post disclosed as paid or sponsored?** (`sponsored_disclosed`, P8)

Judge from the caption and the video only. YES: #ad, #sponsored, #publi, #publicidad, 'paid partnership', 'sponsored by', 'in partnership with' (any language), written in the caption or shown on screen. NO: no such disclosure. A brand posting about its own product is 'No' unless it says so. The platform's own 'Paid partnership' tag is not on this page (the original post would show likes), so it cannot be used.

Options: Yes · No

**13. Is the video mainly about the drink itself, or about a moment the drink is part of?** (`product_vs_lifestyle`, P9)

Decide by what fills most of the video. PRODUCT: the can or bottle, its taste, ingredients, pack design, price or offer is the main subject - pack shots, pouring, taste close-ups, a new flavour announced. LIFESTYLE: people, music, sport, food, friends or an event are the main subject and the drink is one part of the scene.

Options: Product · Lifestyle · Unsure

**14. Does the video look made by an ordinary person or creator, or produced by or for the brand?** (`ugc_vs_brand`, P9)

This is about the look of the video, not who posted it. UGC: filmed on a phone, handheld, a person filming themselves or friends, informal edit, the creator's own voice. A creator video paid for by the brand but made in the creator's own style counts as UGC. BRAND: studio lighting, professional camera work, designed graphics and logos, polished edit, advertising voice-over.

Options: UGC · Brand · Unsure


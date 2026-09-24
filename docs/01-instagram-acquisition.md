# 01 — Instagram Reels Acquisition

**Target:** 150 Instagram Reels featuring Coca-Cola Zero Sugar, across multiple languages
and markets, with engagement metrics **and** downloadable video files.

The second half of that sentence is what rules most options out. Metadata alone is not
enough — the multimodal pipeline needs the actual video.

---

## 0. Do you need an Instagram account? No.

The researcher on this project does not use Instagram. That is fine — the chosen route
needs no Instagram account, no login, and no cookies.

| Route | Instagram account needed? |
|---|---|
| Apify (chosen — §Route C) | ❌ **No.** Actors advertised as cookieless read public profiles server-side |
| Business Discovery API | ✅ Yes — Business/Creator account + Facebook Page + Meta app |
| Hashtag Search | ✅ Yes, and ruled out anyway (§Route A) |
| Manual browsing | ⚠️ Effectively yes — see below |
| Meta Content Library | ✅ Institutional application |

**Why manual browsing is not a fallback for a non-user.** Instagram's logged-out web
experience is now heavily restricted: open a Reel link without an account and a sign-in
sheet slides over the video within seconds; scrolling triggers it sooner. Meta narrowed
this deliberately to drive account creation. So "just look at it in a browser" is not a
workable collection or verification method here.

**Do not use third-party "Reels viewer" sites.** Some solicit Instagram passwords, and none
are a defensible measurement source for a thesis. They are excluded.

**What Apify does instead.** Apify runs the scraper on *its own* managed servers. It fetches
the same public page a browser would, parses it, and hands back structured JSON. Your
credentials are never involved because no login happens at any point. You need one account:
an **Apify** account, created with an email address.

**Optional strengthening (O-05).** If you later want official-API validation, creating an
Instagram account, converting it to Business/Creator, making a Facebook Page, linking them,
and registering a Meta developer app takes roughly 40 minutes and costs nothing. That is
your call to make and to carry out — it is not required for the project to proceed, and
D-008 defines the validation approach that works without it.

---

## 1. The four routes, assessed

### Route A — Instagram Hashtag Search API ❌ RULED OUT

Endpoint: `GET /ig_hashtag_search` → `GET /{hashtag-id}/recent_media`

Superficially ideal: search `#cocacolazero`, get posts. It does not work for this project.

| Constraint | Effect |
|---|---|
| `recent_media` returns only media published **within 24 hours** of the query | Cannot build any historical corpus |
| ~50 posts maximum per response | Even the 24-hour window is truncated |
| 30 unique hashtags per rolling 7-day window | Cannot broaden by trying many tags |
| 200 requests/hour per user token | Slow even where usable |
| No PII, no Stories, no emoji in queries | Minor, but further narrows coverage |

**Verdict:** Only viable if you run it daily for months going forward. Not an option for a
retrospective corpus. Ruled out — recorded here so it is not rediscovered in Week 3.

---

### Route B — Business Discovery API ⚠️ OFFICIAL BUT OPTIONAL (needs an IG account)

Endpoint pattern:

```
GET /{your-ig-user-id}
  ?fields=business_discovery.username(cocacola){
      followers_count,
      media_count,
      media{
        id, caption, media_type, media_product_type,
        like_count, comments_count, timestamp, permalink,
        media_url, thumbnail_url
      }
    }
```

This is the official way to read **other** public Business/Creator accounts. Coca-Cola's
regional accounts are Business accounts, so this is legitimate, ToS-compliant access.

**What it gives:** follower count, media count, and recent posts with like and comment
counts, captions, timestamps, permalinks. `media_product_type` identifies `REELS`.

**What it does not give:**

- **Archive depth.** Returns *recent* media only. There is no documented way to page far
  back through years of a third-party account.
- **Reliable view counts.** Reel *insights* (reach, saves, plays) are own-account only.
  Where a view field does return, Meta now reports **combined Instagram + Facebook views**
  for crossposted video, so the number is not comparable across posts.
- **Follower lists** for third-party accounts — never available. Not needed here.

**Setup requirements:**

1. A Facebook Developer account and an App.
2. Your own Instagram **Business or Creator** account (convert a personal one — free).
3. That IG account linked to a Facebook Page.
4. Permissions: `instagram_basic`, `pages_show_list`, `pages_read_engagement`.
5. **Facebook App Review** for production use. Development mode works for your own linked
   assets and is usually sufficient for a student project — confirm before relying on it.

**Role in this project:** **optional.** Originally the validator (D-004), now superseded by
D-008 because the setup requires an Instagram Business account the researcher does not have.
Pursue only if open decision O-05 is taken; validation proceeds without it via §4.

---

### Route C — Apify Instagram Reel Scraper ✅ PRIMARY COLLECTOR

Actor: `apify/instagram-reel-scraper` (alternatives exist under other authors)

One call per Reel or per profile returns, in a single structured record:

- views and plays
- likes, comments
- caption, hashtags, mentions
- audio track information
- owner username and owner stats
- duration, thumbnail
- **the direct video URL** — downloadable
- in some actors, a transcript

No Instagram login, no OAuth, no daily quota. Reads the same public page a browser does.

**Cost:** free tier covers a 300-video pilot comfortably. Smallest useful run is roughly
$0.09; transcription actors charge about $0.05/video flat if used.

**Precedent:** this is what the published literature actually uses. The Message Sensation
Value study (arXiv:2604.19995) collected its TikTok corpus with Apify and 4KStogram.

**The catch — read this before running anything:**

Third-party scraping violates Instagram's Terms of Service. It is widely accepted in
academic work and the data is public, but it is not ToS-compliant. Therefore:

> **NOT BLOCKING — superseded by D-010.** The approval gate has been removed. Instead:
> (a) read the institutional data/ethics policy yourself and record the finding, and
> (b) state the collection method factually in the methods chapter. See
> [00-decisions.md](00-decisions.md) D-010. Route D remains the fallback if the policy
> turns out to require it.

Also record in the methods chapter: what was collected, that only public data was
accessed, that no commenter identities were stored, and that results are reported in
aggregate.

---

### Route D — Manual collection + yt-dlp ✅ VIABLE FALLBACK

At n=150 this is genuinely practical, roughly a few hours of work, and carries zero access
risk.

1. Browse the target accounts and hashtags by hand; record Reel permalinks in a CSV.
2. Record likes, comments and (where shown) views by hand at collection time.
3. Download the video files with `yt-dlp <permalink>`.
4. Stamp every row with `collected_at`.

**Trade-offs:** manual transcription of counts is error-prone — do a second pass on a 20%
sample and record the discrepancy rate. Slower, but fully defensible and immune to both
API changes and ToS objections.

---

### Route E — Meta Content Library ⚠️ BACKUP, LONG LEAD TIME

Academic access to public Facebook and Instagram content with engagement metrics, applied
for through ICPSR with institutional affiliation.

**Why it is not primary:** data is served inside a restricted virtual research
environment. Raw video files generally cannot be exported — which makes it unusable for a
multimodal pipeline that must process the video itself. Good for metadata validation,
useless for feature extraction.

**Lead time:** weeks to months. If it is wanted at all, apply in Week 1 (open decision
O-03).

---

## 2. How the scraping actually happens — step by step

```
account handles (from Coca-Cola corporate site)
        ↓
Apify Actor A  (profile → posts)      →  enumerate each account's Reels
        ↓
Apify Actor B  (reel detail)          →  metrics + direct video URL per Reel
        ↓
requests / yt-dlp                     →  download .mp4 files locally
        ↓
raw/instagram_reels.parquet + data/media/instagram/
```

### Step 1 — Get the account handles (no Instagram needed)

Apify needs to be *told* which accounts to read; it does not discover them. Take the handles
from Coca-Cola's corporate website and regional brand sites, which list official social
properties. This is also better methodology than search-based discovery, because the frame
becomes traceable to an authoritative source. Record them in
[03-sampling-frame.md](03-sampling-frame.md).

### Step 2 — Create an Apify account

Email signup, free tier. This is the only account required anywhere in the pipeline.

### Step 3 — Enumerate Reels per account

Run a profile-posts actor with the handle list as input. Choose one advertised as
**cookieless / no-login**. Filter the returned posts to `Reel` / video type. Output is a
list of Reel shortcodes and permalinks per account.

Save the **raw JSON exactly as returned**, before any parsing. If an actor's schema changes
or a Reel is later deleted, that file is the only record you will have.

### Step 4 — Pull metrics and video URLs

Run a Reel-detail actor over the shortcode list. Returns likes, comments, views, caption,
hashtags, audio-track info, owner follower count, duration, and the direct video URL.

Can be done from the Apify web console (point, click, download JSON) or via the Python
client:

```python
from apify_client import ApifyClient
client = ApifyClient(APIFY_TOKEN)
run = client.actor("<actor-id>").call(run_input={"usernames": handles})
items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
```

The web console is entirely adequate at n=150. Scripting only pays off if the collection
has to be repeated.

### Step 5 — Download the videos

The returned video URLs are short-lived — download promptly, in the same session:

```bash
yt-dlp -o "data/media/instagram/%(id)s.%(ext)s" "<permalink>"
```

`yt-dlp` also works directly on Instagram permalinks for public posts, so it is the fallback
if a video URL has already expired.

### Step 6 — Stamp and store

Add `collected_at` to every row before writing `raw/instagram_reels.parquet`. Engagement is a
snapshot and this field is not recoverable later.

### Practical notes

- **Run a 10-Reel pilot first.** Actor schemas differ between authors, and field names are
  not standardised. Discover that at n=10.
- **Pin the actor version.** Actors are updated by their authors without notice.
- **Cost at this scale is negligible** — the free tier covers a 300-video collection.
- **Private accounts cannot be scraped**, and Stories and the "For You" feed are out of
  reach regardless. Only public profile content is in scope, which is all this study needs.

---

## 3. Fields to capture

| Field | Source | Notes |
|---|---|---|
| `shortcode` | Apify | Primary key |
| `permalink` | Apify | For download and for manual re-check |
| `owner_username` | Apify | Grouping variable for CV |
| `owner_followers` | Apify / Business Discovery | **Exposure control — mandatory** |
| `caption` | Apify | Raw, original language |
| `hashtags`, `mentions` | Apify | Parsed lists |
| `timestamp` | Apify | Post publication time, with timezone |
| `like_count` | Apify + Business Discovery | Both recorded, for the agreement check |
| `comments_count` | Apify + Business Discovery | Both recorded |
| `view_count` | Apify | **Unreliable — do not use in the cross-platform DV** |
| `duration_sec` | Apify / ffprobe | Prefer ffprobe on the downloaded file |
| `audio_track` | Apify | Original audio vs licensed track — a strong predictor |
| `is_sponsored` | Apify / manual | Paid-partnership label |
| `media_product_type` | Business Discovery | Confirms `REELS` |
| `language` | Detected in Phase 2 | See [04](04-multilingual-pipeline.md) |
| `market` | Manual, from account | See [03](03-sampling-frame.md) |
| `collected_at` | Script | **Mandatory** — engagement is a snapshot |
| `video_path` | Script | Local file location |

**`audio_track` is worth highlighting.** The brand-TikTok study found original spoken
audio produced the largest single engagement effect of any variable it tested. On Reels,
original-vs-licensed audio is directly observable and cheap to capture. Do not skip it.

---

## 3a. What the actor actually returns — measured 2026-09-09

Pilot: `apify/instagram-reel-scraper`, 7 accounts, limit 10, 61 records, **$0.02**.
Four things differ from what section 3 assumed.

### It returns no follower count at all

`ownerUsername`, `ownerId` and `ownerFullName` are present; there is no follower field.
Since `owner_followers` is the mandatory exposure control (D-005), it is filled by a
second run of `apify/instagram-profile-scraper` and joined on username. Follower count is
an account-level property, so one lookup per account covers the whole corpus.

### 27% of returned Reels belong to other accounts — this is a feature

16 of 60 rows came from accounts that were never requested: `mumbaifoodie`,
`fukravarun`, `mistertikku`, `barkhasingh0308` (India), `ifoodbrasil`, `duhmarinho`
(Brazil), `costacoffee.mx`, `luismiguel`, `cocacolamx`, `fundacioncocacolamx` (Mexico),
`jaxdistrict` (MENA), `cocacolafutbol` (Global).

These are **Instagram collaborator posts**: a co-authored Reel appears on both profiles,
and the actor reports the co-poster as owner. This is exactly the sponsored-creator tier
that D-009 planned to derive manually — it arrives free with the brand pull.

Consequences, all handled in `normalize_reel()`:

- `market` is mapped from `inputUrl` (the requested account), **not** from
  `owner_username` — a creator has no market of their own in the frame. Mapping from the
  owner left 16 rows unlabelled.
- `source_handle` and `is_collab` are recorded.
- `sampling_tier` is set automatically: **1** for brand-owned, **2** for collaborator.
- `owner_followers` on a tier-2 row is the *creator's* follower count, which is the
  correct exposure base for that post but is not comparable to a brand row.

Note the outlier: a `luismiguel` collaboration drew 581,196 likes against a corpus median
in the low thousands. Tier-2 rows must be identifiable in the model for exactly this
reason.

### Coca-Cola Indonesia is age-restricted and returns nothing

`cocacola_id` yields no Reels at all. The actor returns an error record:

```
error               "Restricted profile"
isRestrictedProfile true
restrictionReason   "You must be 13 years old or over to see this profile"
latestPosts         []
```

An age gate needs an authenticated adult session, which the cookieless route by
definition does not have. **Indonesia therefore contributes zero rows on both platforms**
(no YouTube channel either). Recorded as O-08.

### Aspect ratio arrives without a download

`dimensionsWidth/Height` and `originalWidth/Height` are present, so vertical-format
screening is free and does not require fetching the file. Stored as `actor_width` /
`actor_height`, kept separate from the ffprobe columns so provenance stays unambiguous.

### Also captured, not in the original section 3 list

| Field | Why it matters |
|---|---|
| `is_pinned` | A pinned Reel sits atop the profile indefinitely and accrues engagement no ordinary post can reach. A confound; 1 found in 60. |
| `comments_disabled` | Without it, a genuine 0 and a disabled comment section are indistinguishable. |
| `owner_id` | Usernames are changeable, numeric ids are not. Group by this. |
| `audio_url`, `alt_text` | Free, and useful in Phase 2. |

### Two parsing bugs this pilot exposed

1. **Non-Reel filter dropped everything from schema-light actors.** The filter
   stringified the type column before testing for nulls, and pandas 3.0 renders a missing
   value as `<NA>` where older versions give `"None"`. Any actor omitting `productType`
   would have had **every row silently discarded**. Nulls are now tested before any
   string conversion.
2. **Error records became phantom Reels.** The restricted-profile record carries the
   numeric *profile* id in `id`, which the shortcode fallback accepted. An all-digit
   value is now rejected as a shortcode, and error records are reported and excluded
   before parsing — loudly, because an account yielding nothing is otherwise invisible.

---

## 4. Data-quality validation — cross-source agreement (D-008)

Since the official API route needs an Instagram account (see §0), validation is by
**inter-source reliability** instead. This is cheap, needs no account, and is reportable.

1. Pick two Apify actors by **different authors** using different scraping implementations.
2. Run both over the same 50 Reels.
3. Inner-join on shortcode and report: n matched, exact matches on `like_count`, mean
   absolute difference, and mean absolute percentage difference for both likes and comments.
4. High agreement supports the measurement. Systematic disagreement must be investigated
   before modelling — do not model on counts you have not checked.
5. Record results in §7.

**Snapshot drift.** Re-pull a random 30 Reels one week after the main collection and record
the change in like counts. This quantifies how much the snapshot problem matters for this
corpus and justifies the `video_age_days` control empirically rather than by assertion.

**If O-05 is taken** (Instagram Business account created), add the official Business
Discovery comparison as a third source. Agreement with an official source is stronger
evidence than agreement between two scrapers, so this is worth the 40 minutes if time
allows.

---

## 5. Reaching 150 across languages

Brand accounts alone may not yield 150 Zero Sugar Reels. Escalation order:

1. Coca-Cola Zero Sugar Reels from official regional brand accounts (see
   [03](03-sampling-frame.md)).
2. Sponsored creator/influencer Reels featuring Zero Sugar — pending open decision O-04.
3. Coca-Cola brand-family Reels (Original, Diet/Light) with `brand` as a feature —
   open decision O-02.

Log which escalation tier each video came from as `sampling_tier`. If tier 3 is used, the
brand variable must be controlled in every model.

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| Guide refuses scraping approval | Route D, but note it is weakened for a non-IG user — enumeration would need `yt-dlp` on permalinks obtained without browsing. Take O-05 and use Business Discovery instead. |
| Actor stops being cookieless / starts demanding login | Switch actor. Several independent cookieless actors exist; do not depend on one. |
| Video URL expires before download | Download in the same session as the metadata pull; `yt-dlp` on the permalink as fallback. |
| Apify actor breaks or changes schema | Pin the actor version. Save raw JSON responses unmodified before parsing. |
| Fewer than 150 Reels available | Escalation tiers in §5. Decide O-02/O-04 early. |
| Views unusable | Already handled — follower-normalised DV (D-005). |
| IP blocking mid-collection | Apify handles rotation. For Route D, collect in small batches over several days. |
| Account deletes a Reel after collection | Raw JSON and local video file are already saved. Never re-fetch as the source of truth. |

---

## 7. Execution log

> Append dated entries as collection runs. Record counts, failures, and anything surprising.

_Collector built and tested offline 2026-09-09; not yet run against the API (APIFY_TOKEN not set). No longer blocked — D-010 removed the approval gate._

| Date | Action | Result |
|---|---|---|
| 2026-09-09 | Built `src/collect/instagram.py` (Apify REST, no `apify-client` dep) | Offline tests pass: 3 differing actor schemas normalise correctly; zero-vs-missing preserved; duplicates and unmapped records dropped with warnings |
| 2026-09-09 | `--plan` against the drafted frame | 7 handles, ceiling 70 Reels at limit 10. Awaiting APIFY_TOKEN |
| 2026-09-09 | Token verified; 3-Reel pilot on `cocacola` | Worked. Exposed that the actor returns no follower count |
| 2026-09-09 | Added `fetch_follower_counts()` via profile actor | Followers resolved 60/60 |
| 2026-09-09 | 7-account pilot, limit 10 | 61 records -> **60 usable Reels**. 44 tier-1, 16 tier-2 collaborator. Markets 100% mapped. **$0.02 total** |
| 2026-09-09 | Diagnosed 18 owner accounts from 7 handles | Instagram collaborator posts, not a bug. Tiering and market mapping reworked around `inputUrl` |
| 2026-09-09 | Diagnosed the 61st record | `cocacola_id` age-restricted, 0 Reels. Two parsing bugs fixed (see 3a) |
| 2026-09-09 | Rebuilt corrected parquet via `--dry-run` | 60 rows, no further API spend |
| 2026-09-11 | D-015 frame built: `docs/accounts_instagram.csv`, 41 accounts | `--plan` clean. 39 from researcher screenshots, `cocacola_civ` dropped (unverified), `cocacola_br` + `cocacolamiddleeast` restored from site footers |
| 2026-09-11 | 41-account pilot, limit 3 | 120 records -> **118 usable Reels**, 40/41 accounts yielded data. 0 missing likes, 0 missing followers. 93 tier-1, 25 tier-2 from 22 creators. Dates 2024-02-19..2026-09-11 |
| 2026-09-11 | `cocacola_id` returned 0 again | Age gate reconfirmed (O-08). The only account yielding nothing |
| 2026-09-11 | `cocacolaeurope` flagged `restricted_page` | **Still returned 2 of 3 Reels.** Partially readable, not dead. Do not treat the warning as an empty account |
| 2026-09-11 | **Cost rate re-measured and corrected** | See below. Prior $0.02/61-record figure understated the true rate by ~8x |
| 2026-09-11 | **Found 319 unique Reels in saved raw JSON vs 60 in the parquet** | The collector overwrites rather than merges. The 2026-09-09 `jqOx3SUlWp6FvpVnf` run's 180 Reels (150 new) had been silently discarded. See D-016 |
| 2026-09-11 | Built `src/collect/merge_instagram.py` | Merges all raw runs, dedupes across runs, restores followers offline. **319 rows, 0 unmapped, 0 followers missing, $0.00** |
| 2026-09-11 | `region` added to both account frames | 38 markets -> 8 regions. Only 6 markets have n>=10; 29 have n<=3, so market-level analysis is not credible |
| 2026-09-11 | Screened + built the Instagram corpus | **150 selected, 8 Zero Sugar (5.3% of corpus vs 2.5% of population - over-represented by design)**. All 8 regions and all 8 account types present |
| 2026-09-11 | Exported `reports/instagram_corpus_150.csv` | 21 columns, sorted by region/market, for hand-coding |
| 2026-09-11 | **Video download route confirmed free** | Apify `video_url` values now return HTTP 403 (expired). `yt-dlp 2026.8.19` on permalinks succeeded **6 of 6** across six regions, logged out, no cookies |


### Cost — corrected 2026-09-11

The 2026-09-09 entry implied roughly $0.0003 per record. **That is wrong.** Measured against
`GET /v2/actor-runs/{id}` on the 41-account pilot, both actors bill at a near-identical
per-result rate:

| Run | Results | Cost | Per result |
|---|---|---|---|
| `apify/instagram-reel-scraper` | 120 Reels | $0.3130 | $0.002608 |
| `apify/instagram-profile-scraper` | 59 accounts | $0.1534 | $0.002600 |

**≈ $2.60 per 1,000 results, charged per result returned, not per compute-second.** The run
burned 0.067 compute units in 60s, so compute is negligible; results dominate. Two planning
consequences:

1. **A limit of 60 across 41 accounts is not affordable on the free tier.** Ceiling 2,460
   results ≈ $6.40 against $3.72 of allowance remaining. It would stop mid-collection.
2. **The ceiling is a worst case, not a bill.** Billing is per result *returned*, so accounts
   holding fewer Reels than the limit cost proportionally less. Smaller accounts
   (`cocacola_nicaragua`, 11.2K followers) will not return 30 Reels.

This is trap 1 again in a different costume: the old rate came from a 7-account run and did
not survive contact with a 41-account one. Re-measure rates when the scale changes.


### Validation results

_To be filled from §4._

| Metric | Value |
|---|---|
| Actor A used (author / version) | |
| Actor B used (author / version) | |
| Reels matched across the two actors | |
| Exact matches, `like_count` | |
| Mean absolute difference, `like_count` | |
| Mean absolute % difference, `like_count` | |
| Exact matches, `comments_count` | |
| Mean absolute difference, `comments_count` | |
| One-week drift in likes (30-Reel sample) | |
| Official Business Discovery comparison run? (O-05) | |

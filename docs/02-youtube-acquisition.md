# 02 — YouTube Shorts Acquisition

**Target:** 150 YouTube Shorts featuring Coca-Cola Zero Sugar, across multiple languages
and markets, with engagement metrics and downloadable video files.

Easier than Instagram in every respect: the API is official, free, generous, and exposes
view counts. The only real complication is that **YouTube has no "is this a Short?" flag**.

---

## 1. Access

YouTube Data API v3. Free, official, ToS-compliant. Requires only a Google Cloud project
with the API enabled and an API key — no OAuth needed for public read access, no review
process. Set up takes about ten minutes.

**Quota:** 10,000 units/day, and the cost model is what shapes the whole strategy:

| Call | Cost | Returns |
|---|---|---|
| `search.list` | **100 units** | 50 results |
| `playlistItems.list` | **1 unit** | 50 items |
| `videos.list` | **1 unit** | up to 50 videos, full detail |
| `channels.list` | **1 unit** | channel metadata |

`search.list` is 100× more expensive and returns incomplete, ranked results. Use it only
for discovery of unknown channels — never for enumerating a channel you already know.

---

## 2. Collection strategy

### Per known channel — the cheap path

```
channels.list(id=CHANNEL_ID, part=contentDetails,statistics)
    → uploads playlist ID  +  subscriberCount        [1 unit]
        ↓
playlistItems.list(playlistId=UPLOADS, maxResults=50, paged)
    → every video ID the channel has published        [1 unit per 50]
        ↓
videos.list(id=<50 comma-separated IDs>,
            part=snippet,contentDetails,statistics)
    → full metadata                                   [1 unit per 50]
```

A channel with 1,000 uploads costs about 41 units to enumerate completely. The full daily
quota would cover roughly 240 such channels. Quota is not a constraint at our scale.

### Discovery of unknown channels

Use `search.list` sparingly for finding creator/influencer content:
`q="coca cola zero sugar"`, `type=video`, `videoDuration=short`,
`regionCode` varied per target market. At 100 units per call, budget perhaps 20 calls
(2,000 units) and treat the output as a candidate list to filter by hand — not as the
sample itself. Search ranking is opaque and would bias the frame.

---

## 3. Identifying Shorts — the one real problem

The API does **not** expose a boolean for Shorts. Combine three signals:

1. **Duration** — `contentDetails.duration` is ISO-8601. Shorts are ≤ 3 minutes
   (previously ≤ 60s; older content in the corpus will follow the older cap).
   **Necessary but not sufficient** — see the measurement below.
2. **Aspect ratio** — read from the downloaded file with `ffprobe`. Shorts are vertical,
   height > width. Strong corroboration, but it costs a download.
3. **URL redirect** — `https://www.youtube.com/shorts/{video_id}` serves 200 for a genuine
   Short and redirects (303) otherwise. Cheap HTTP check, no quota, no download.

### The signals are not peers — measured 2026-09-09

Verified against the global channel (`UCosXctaTYxN4YPIvI5Fpcrw`), 60 most recent uploads:

| Check | Result |
|---|---|
| Known Shorts (taken from the channel's own `/shorts` tab) | 4/4 returned **200** |
| Short regular uploads | 5/5 returned **303** |
| Non-Shorts in the sample that are **under 180s** | **47 of 48** |
| Classified as Shorts | 12 of 60, matching the `/shorts` tab |

That third row is the point. Coca-Cola posts a great many 6–30 second horizontal TV
commercials as ordinary videos. **A duration-only rule would have misclassified 47 of 59
non-Shorts** — roughly an 80% false-positive rate. Duration alone is close to useless here.

**Rule (revised):** the redirect is YouTube's own membership test for the Shorts shelf and
is therefore **authoritative whenever it is conclusive**. Duration and aspect ratio are
proxies used only where it is not (consent wall, network failure).

**Flag a disagreement only for a genuine contradiction** — a proxy that makes the
authoritative verdict impossible (served as a Short yet horizontal, or longer than the
cap; or vertical *and* short yet not served as a Short, which is the likeliest shape of a
failed redirect check). "Short but not a Short" describes every short regular upload and
is **not** a conflict: flagging it buried 5 of 5 ordinary videos in review load on the
first run, and would have buried hundreds across the full channel.

---

## 4. Fields to capture

| Field | API path | Notes |
|---|---|---|
| `video_id` | `id` | Primary key |
| `title` | `snippet.title` | |
| `description` | `snippet.description` | |
| `published_at` | `snippet.publishedAt` | |
| `channel_id` | `snippet.channelId` | **Grouping variable for CV** |
| `channel_title` | `snippet.channelTitle` | |
| `subscriber_count` | `channels.list statistics` | **Exposure control — mandatory** |
| `duration_sec` | `contentDetails.duration` | Parse ISO-8601 (`isodate` or regex) |
| `view_count` | `statistics.viewCount` | YouTube-only secondary DV |
| `like_count` | `statistics.likeCount` | Can be hidden by the uploader — handle nulls |
| `comment_count` | `statistics.commentCount` | Can be disabled — handle nulls |
| `tags` | `snippet.tags` | Often absent |
| `category_id` | `snippet.categoryId` | |
| `default_audio_language` | `snippet.defaultAudioLanguage` | Often absent — verify with ASR |
| `thumbnail_url` | `snippet.thumbnails` | |
| `market` | Manual, from channel | See [03](03-sampling-frame.md) |
| `collected_at` | Script | **Mandatory** |
| `video_path` | Script | Local file |

**Dislikes are gone.** Removed from the API in 2021. Munaro et al. used dislikes as an
engagement signal; that is not reproducible here. Note it as a limitation.

**Nulls are meaningful.** A hidden like count is not zero. Keep it null, and record a
`likes_hidden` flag rather than imputing.

---

## 5. Media and transcripts

**Video:** `yt-dlp` at capped resolution.

```bash
yt-dlp -f "bv*[height<=720]+ba/b[height<=720]" \
       -o "data/media/youtube/%(id)s.%(ext)s" \
       "https://www.youtube.com/shorts/VIDEO_ID"
```

720p rather than 480p here — Shorts are vertical, so the *horizontal* resolution is the
short side, and product/logo detection needs the detail. Storage at n=150 is trivial.

**Transcripts:** try `youtube-transcript-api` first (free, instant, uses YouTube's own
captions, supports many languages). Fall back to Whisper on the extracted audio where no
captions exist. Record `transcript_source` as `captions` or `asr` — auto-captions and ASR
have different error profiles and that may matter in the text analysis.

---

## 6. Reaching 150 across languages

Escalation order mirrors Instagram (see [01](01-instagram-acquisition.md) §5):

1. Zero Sugar Shorts from official regional Coca-Cola channels.
2. Sponsored creator Shorts featuring Zero Sugar (open decision O-04).
3. Brand-family Shorts with `brand` as a feature (open decision O-02).

Log `sampling_tier` per video. Keep the tier distribution roughly comparable to
Instagram's — if YouTube is 90% brand-account and Instagram is 60% creator, the platform
comparison is partly a creator-type comparison.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Short/long misclassification | Three-signal rule in §3; manually review disagreements |
| Like or comment counts hidden | Keep null, flag it, exclude from DV rather than imputing |
| Regional channels have few Zero Sugar Shorts | Escalation tiers in §6 |
| `defaultAudioLanguage` missing | Detect language from Whisper output instead |
| Quota exhaustion | Only if `search.list` is overused — enumerate via uploads playlist |
| Tier imbalance vs Instagram | Track `sampling_tier` distribution per platform; report it |

---

## 8. Execution log

> Append dated entries as collection runs.

_Pilot runs done 2026-09-09 against the global channel. Full runs pending decisions O-06 and O-07._

| Date | Action | Channels | Videos | Notes |
|---|---|---|---|---|
| 2026-09-09 | API key verified, pilot on global channel | 1 | 5 | Crashed on Windows cp1252 console printing `⚠`; fixed centrally in `src/config.py` |
| 2026-09-09 | Diagnosed 5/5 "signal disagreement" | 1 | 5 | Not a data problem — `classify()` treated the signals as peers and discarded the redirect in the final verdict. Both bugs fixed |
| 2026-09-09 | Re-run after fix | 1 | 60 | 12 Shorts, **0** false flags. IDs cross-checked against the channel's `/shorts` tab |

### Collection summary

_To be filled._

| Metric | Value |
|---|---|
| Channels enumerated | |
| Videos retrieved | |
| Classified as Shorts | |
| Featuring Zero Sugar (after screening) | |
| Three-signal disagreements | |
| Transcripts from captions / from ASR | |
| Like counts hidden | |
| Quota consumed | |

---

## Full run — 2026-09-11

All five channels enumerated exhaustively. **95 quota units** of the 10,000/day allowance.

| Channel | Uploads | Shorts | Rate |
|---|---|---|---|
| Coca-Cola (global) | 1,089 | 217 | 19.9% |
| Industria Mexicana de Coca-Cola | 114 | 42 | 36.8% |
| Coca-Cola Brasil | 189 | 17 | 9.0% |
| Coca-Cola Thailand | 351 | 11 | 3.1% |
| Coca-Cola Middle East | 351 | 8 | 2.3% |
| **Total** | **2,094** | **295** | **14.1%** |

Signal disagreements between the duration and redirect checks: **0** across 2,094 videos.

### Screening and corpus

Of 295 Shorts: 25 name Zero Sugar (8.5%), 225 are `unnamed`, 45 are `off_brand`. The
stratified corpus keeps all 25 Zero Sugar rows and fills to 150 at random from the
remaining brand rows — **150 selected, 25 Zero Sugar (16.7%)**.

The 8.5% rate is materially higher than the 4.0% measured on the global channel alone
(D-013). Widening to five channels found more, so D-013's projection was pessimistic for
the multi-channel case. Its central conclusion is unchanged: at 8.5%, a Zero-Sugar-only
corpus of 150 would still need ~1,770 Shorts and only 295 exist.

### Two skews that belong in the methods chapter

1. **Channel concentration.** 119 of 150 corpus rows are from the global channel. The
   regional channels post few Shorts — MENA 8 and Thailand 11, from 351 uploads each.
   Cross-market comparison on YouTube is therefore weak by construction; the Instagram arm
   carries that comparison.
2. **Recency.** 110 of 150 rows are from 2026 and 133 from 2025-26. Shorts adoption is
   recent, so the corpus describes current practice rather than a decade of it. Any
   time-trend claim is confounded with format adoption.

### A note on pre-2020 "Shorts"

Four Shorts date from 2016-2017, before the format existed (launched 2020). These are
genuine: the `/shorts/<id>` URL serves them without redirect, so YouTube classifies them
as Shorts *today* by applying the format retroactively to short vertical videos. The
classifier is correct; the label is YouTube's, and it is a statement about present
treatment, not about how the video was published.

### Field completeness in the corpus

150/150 on views, duration, publish date, title, description, channel and subscribers.
`like_count` is null on 4 rows and `comment_count` on 2 — these are hidden/disabled, held
as null rather than 0 exactly as D-005 requires.

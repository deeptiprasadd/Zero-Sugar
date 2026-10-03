# 12 — Data collection: the factual record for the methods chapter

**Written 2026-10-01.** Source material for the methods chapter (task 11.1), not the chapter
itself. Every statement below is taken from the decision log and the data files, with the decision
named so it can be checked. D-010 makes one part of the chapter non-negotiable: **it must state how
the data was actually obtained, every route included.** Nothing here may be softened in the chapter.

---

## 1. Which accounts (the sampling frames)

| | YouTube | Instagram |
|---|---|---|
| How accounts were found | Social links in the footer of each `coca-cola.com/<market>` site, each YouTube link resolved to its permanent `UC...` channel id; no handle was guessed (D-011) | 39 accounts from the researcher's Instagram in-app search for "coca cola" (Accounts tab, 2026-09-11), every one carrying the blue verified badge; 2 more (`cocacola_br`, `cocacolamiddleeast`) restored from the official site footers; 1 unverified account dropped (D-015) |
| Accounts in the frame | 7 frame rows, **5 usable YouTube channels**; India and Indonesia have no channel of their own, and the Mexico channel is the bottlers' industry body (D-011, D-012) | 41, later **44**: Chile, Kenya and Singapore surfaced from the researcher's curated links and were verified by the researcher (blue tick, follower count) (D-018) |
| Non-market accounts | Mexico industry body, kept and flagged | Global, regional, event, venue, sponsorship and bottler accounts kept and flagged by `account_type` (D-015) |

Why the guessing rule matters, for the chapter: `youtube.com/@CocaColaIndia` - the handle anyone
would try - belongs to an unrelated channel (D-011).

## 2. YouTube

- **Metadata:** YouTube Data API v3 (official, free tier, API key, logged out). Every upload of the
  5 channels was enumerated: **2,094 videos**.
- **Which are Shorts:** the API has no Shorts flag. Three signals were combined - duration (Shorts
  are at most 3 minutes), the `/shorts/<id>` URL (200 for a real Short, redirect otherwise; the
  decisive signal) and, after download, vertical shape (docs/02 section 3). Result: **295 Shorts**.
- **Corpus of 150:** every Short whose title, description or tags name Zero Sugar (**25**), plus a
  random draw of the rest (seed 20260911). After download, 2 Shorts had been removed from YouTube and
  4 were square; each was replaced by a random eligible brand Short (seeded, at least 7 days old)
  and the replacement recorded on the row (D-020).
- **Video files:** downloaded with **yt-dlp while signed in to a spare Google account** (not the
  researcher's own). Logged-out downloads were refused with YouTube's "confirm you're not a bot"
  check, which was **not** bypassed. The cookie file was exported by the researcher from a private
  browser window following yt-dlp's documented method, kept out of the repository, used only for
  YouTube, and **deleted and the session signed out** after the downloads. A JavaScript runtime
  (deno 2.9.6, yt-dlp-ejs 0.8.0) was installed because signed-in requests need it (D-020).
  Signing in changed access, not content: these are public Shorts, and nothing account-specific was
  collected.

## 3. Instagram

- **Regular Reels - metadata and links:** the **Apify Instagram Reel Scraper**, on Apify's free
  plan (no card; $1.37 of the $5 monthly allowance used by 2026-09-15): **319 Reels** from the 41
  accounts. **Apify scraping is against Instagram's terms of service and must be disclosed in the
  methods chapter** (D-004). No Instagram account was used for it (D-008).
- **Hand-picked Zero Sugar Reels:** **118 links** the researcher saved on 2026-09-13 from 13 account
  pages after checking each Reel by eye - **the Zero Sugar Reels readily visible on each page, most
  but not all of them** (researcher, 2026-09-15). This is purposive selection, a verified subset,
  not a census, and it may lean toward the Reels Instagram shows most (D-018).
  - Fetched with **yt-dlp, logged out**: 107 of 118; 98 vertical and usable.
  - **10 login-only Reels downloaded by the researcher by hand with sssinstagram.com**
    (`sssinstagram.com/reels-downloader`); 9 usable. Recorded per row in `download_route`.
  - For those 9 login-only posts, **likes and comments were transcribed by the researcher from
    screenshots** and confirmed; no logged-out source could cross-check them. Their post dates were
    decoded from the shortcode (checked on 426 known dates: median error about 1 minute) (D-018).
  - Follower counts of 24 of 25 creator accounts (collaboration posts) came from an Apify profile
    lookup; 4 restricted accounts' follower counts were read on Instagram by the researcher and are
    display-rounded (D-018).
- **Agreement between sources:** on 11 Reels read by both yt-dlp and Apify - same account, post
  time and aspect ratio 11/11, likes + comments within 0.4% (D-018).
- **Corpus of 150:** 107 hand-picked Zero Sugar Reels (one later relabelled Original Taste on
  inspection) + 6 Reels whose caption names Zero Sugar + **37 regular Reels drawn at random** (seed
  20260911) from the 319, vertical and read at least 7 days after posting (D-018, D-019).
- **Video files:** yt-dlp logged out; the 9 login-only Reels via sssinstagram.com (above).
- **Personal data:** commenters' usernames and ids that yt-dlp caches were stripped at fetch time;
  the WhatsApp export the links came from is kept out of the repository (D-018).

## 4. Engagement readings

- **Outcome:** (likes + comments) / followers on both platforms (D-005); views exist only on YouTube.
- **7-day rule:** counts enter only if read at least 7 days after posting. Three Reels first read
  sooner were re-read with yt-dlp at 7.5-16.6 days; first readings kept on the row (D-019, 2b.7).
- Usable rows: 290 of 300 (5 hidden like counts, 5 comments disabled).

## 5. Zero Sugar labels (they decide which videos are analysed, D-030)

| Route | Videos in the analysis set (192) | How |
|---|---|---|
| Text names Zero Sugar | 31 | multilingual keyword screen of titles, descriptions, tags or captions |
| Researcher's hand-picked list | 105 | each Reel checked by eye before saving (D-018) |
| Researcher's check by eye | 56 | every YouTube Short and every randomly drawn Instagram Reel the text did not name, judged from one frame per shot with the video at hand (D-029, D-039) |

**Repeat reliability, to be stated with every result:** the same person's two looks agreed for 16 of
25 Shorts (alpha 0.25) and 4 of 9 Reels (alpha -0.10). An automatic image screen was tried first and
failed (AUC 0.58), so no automated score decides any label (D-029).

## 6. What it cost, and what was never done

- **Cost: nothing.** Free API quota, Apify's free allowance, free tools; no paid service.
- **Not done:** no login wall or bot check was bypassed; no private account was accessed; no
  personal data about commenters is kept; the spare account's session was signed out and its cookie
  file deleted.

## 7. Limitations the chapter must carry

- **The two platforms were sampled differently:** YouTube by rule (text + random); Instagram mostly
  by hand (105 of 120 analysed Reels). Platform and selection cannot be separated (docs/08 7.9.3(c)).
- **YouTube is concentrated:** 5 channels, 58 of 72 analysed Shorts from the global channel.
- **Market coverage differs by platform** because of how Coca-Cola organises its channels (D-011).
- **9 Reels carry hand-transcribed engagement**; all others are machine-read.
- **The Zero Sugar label is weakly reliable** (section 5).

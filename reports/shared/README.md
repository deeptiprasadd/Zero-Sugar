# Shared data - Coca-Cola short-form video study

Two corpora of 150 videos each, with the variables and sources below. Column definitions
are in `data_dictionary.csv`.

| File | Contents |
|---|---|
| `youtube_corpus.csv` | 150 YouTube Shorts from 5 official Coca-Cola channels (74 Zero Sugar) |
| `instagram_corpus.csv` | 150 Instagram Reels from official Coca-Cola accounts, incl. collaboration posts (112 Zero Sugar) |
| `codebook.md` | Definitions used for manual coding of a random 60-video subset |

## How the data was obtained

- **YouTube metadata:** YouTube Data API v3 (official API, public data).
- **YouTube video files:** yt-dlp, signed in to a YouTube account (public Shorts only).
- **Instagram metadata:** public post and profile data via the Apify Instagram scraper and
  yt-dlp. For posts visible only when logged in, likes and comments were recorded manually
  from the post and verified.
- **Instagram video files:** yt-dlp; posts visible only when logged in were downloaded
  manually via sssinstagram.com.
- **Zero Sugar labels:** Instagram - manual visual check of each hand-picked Reel, plus Reels
  whose caption names Zero Sugar; the 37 randomly drawn Reels the caption did not name were then
  checked by eye in the same way as YouTube (12 showed Zero Sugar). 9 of those Reels had been
  coded blind by the same coder two weeks earlier; the two looks agreed for 4 of the 9. YouTube - text screening of title, description and tags, then a
  manual visual check of every Short the text did not name (a sheet of 8 to 16 still frames
  spread through the Short - one per shot, evenly thinned when a Short has more than 16 shots -
  with the video to hand). 25 of those Shorts had been coded blind by the same coder a week
  earlier; the two looks gave the same Zero Sugar answer for 16 of the 25.
- **Video properties:** measured with ffprobe on each downloaded file.

## What is analysed

The study analyses **Coca-Cola Zero Sugar short videos only**: 198 of the 300 videos here, of
which **192 have a usable engagement figure** - 120 Instagram Reels from 17 accounts and 72
YouTube Shorts from 5 channels, 58 of those from the global Coca-Cola channel. The column
`in_analysis_set` marks them. The other 102 videos stay in these files and are used only as a
comparison check, so nothing is hidden and nothing is deleted.

Two things follow, and both are reported with every result:

- **The two platforms contribute unequal numbers**, from very different numbers of accounts.
- **The Zero Sugar label decides which videos are analysed**, and for every YouTube Short and
  Instagram's randomly drawn Reels that the text does not name, it is a judgement from looking at
  the video rather than from text. Its repeat reliability is limited: the same person's two looks
  agreed for 16 of 25 Shorts and 4 of 9 Reels. Results are reported with those figures, and the
  label is not described as validated.

Every feature is still measured on all 300 videos; the focus applies when results are produced.

## Selection

The two platforms were sampled differently. On YouTube, every Short whose title,
description or tags name Zero Sugar was kept and the rest drawn at random (fixed seed); the
random draws were then checked by eye, and those showing Zero Sugar packaging are labelled
Zero Sugar. On Instagram, most Zero Sugar Reels were hand-picked by manual review of account
pages (the Zero Sugar Reels readily visible on each page, not every one), plus Reels whose
caption names Zero Sugar, and the rest drawn at random (fixed seed); those random draws were
then checked by eye as on YouTube. Zero Sugar is therefore
over-represented, most of all on Instagram, and corpus averages are not estimates for all
Coca-Cola posts. Engagement is used only when
read at least 7 days after posting; Reels first read sooner were re-read with yt-dlp once
they were, and their rows say so. Unusable videos (removed from the platform, or not
vertical) were replaced by random draws.

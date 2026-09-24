# reports/ — which file to open

**For the current lists of videos, use `shared/`.** It is rebuilt from the data each time labels
change and is checked before it is published. Everything else in this folder is a working file
or a dated snapshot, kept as a record of how the corpus was built.

*Note added 2026-09-24.*

## Current

| File | What it is |
|---|---|
| `shared/youtube_corpus.csv` | The 150 YouTube Shorts. **74 Zero Sugar**, all 74 in the analysis set (`in_analysis_set`) |
| `shared/instagram_corpus.csv` | The 150 Instagram Reels. **112 Zero Sugar**, all 112 in the analysis set |
| `shared/README.md` | How the data was obtained and what is analysed |
| `shared/data_dictionary.csv`, `shared/codebook.md` | Column definitions; the manual coding definitions |

The analysis set is the Zero Sugar videos with a usable engagement figure: **183** (Instagram 111,
YouTube 72). The YouTube Zero Sugar label is weakly reliable: the same coder's two looks at 25
Shorts agreed on 16 (Krippendorff's alpha 0.25). See `shared/README.md`.

## Out of date — do not use for counts

| File | Snapshot of | Why it is out of date |
|---|---|---|
| `youtube_corpus_150.csv` | 2026-09-15, when the YouTube corpus was first built | Shows **25** Zero Sugar Shorts — those named in the text only. The visual check of every other Short (22 Sep) raised this to **74** |
| `instagram_corpus_150.csv` | 2026-09-15, when the Instagram corpus was first built | Zero Sugar count (112) still matches, but it has no analysis-set column, and 3 Reels that were under 7 days old show their first reading, not the 7-day re-read of 21 Sep |
| `instagram_corpus_150_before_D018.csv` | 2026-09-11, before the hand-picked Zero Sugar Reels were added | The Instagram corpus as it stood before that change (see `docs/00-decisions.md`) |

These files are left exactly as they were written, so the record of each stage is intact.

## Working files from earlier steps

| File | What it is |
|---|---|
| `curated_reels_to_check.csv` | 26 hand-picked Reels that needed a logged-in check, with the answers recorded (15 Sep) |
| `researcher_inputs_needed.csv` | 10 Reels whose likes, comments and account were read from screenshots and checked (15 Sep) |
| `clip_zero_sugar_calibration.md`, `clip_zero_sugar_first_attempt_list.csv` | The automatic Zero Sugar screen tried on 22 Sep. **It failed (ROC AUC 0.58) and labelled nothing**; kept as the record of that attempt |
| `figures/` | Charts, once the analysis produces them (empty so far) |

The frame sheets used for the visual Zero Sugar checks are not in the repository (63 MB of
video frames); they can be regenerated from the videos.

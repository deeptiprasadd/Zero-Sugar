# 05 — Feature Extraction

**Status:** Planned. Method specified below; fill results as extraction runs.

Constraint that governs everything here: **~30 features reach the models** (D-007). Extract
generously, prune deliberately, and record the pruning.

---

## 1. Pipeline

```
media/*.mp4
   ├─ ffmpeg          → normalised video + mono 16 kHz WAV
   ├─ PySceneDetect   → scene boundaries
   ├─ frame sampling  → 1 fps + one keyframe per scene
   │    ├─ CLIP       → product / logo presence
   │    ├─ MediaPipe  → faces
   │    ├─ EasyOCR    → on-screen text
   │    └─ OpenCV     → colour, complexity, motion
   ├─ faster-whisper  → transcript (native + English)
   ├─ librosa/openSMILE → prosody, energy
   └─ YAMNet          → music vs speech tagging
        ↓
interim/features/{video_id}.json      ← per-video cache, always
        ↓
processed/features.parquet
```

**Cache everything per video.** A failed run must cost minutes, not days. Parallelise with
`joblib`.

---

## 2. Features by block

### Block A — Video

| Feature | Method | Keep? |
|---|---|---|
| `duration_sec` | ffprobe | ✅ Core — H1 |
| `scene_count` | PySceneDetect | ⚠️ Collinear with duration — use rate instead |
| `cuts_per_sec` | scene_count / duration | ✅ Preferred over raw count |
| `mean_shot_len` | duration / scene_count | ⚠️ Inverse of above — pick one |
| `product_visible_frac` | CLIP zero-shot | ✅ Core — H2 |
| `product_mean_area` | CLIP + box area | ✅ |
| `time_to_first_product` | first detection | ✅ Interesting, cheap |
| `face_present_frac` | MediaPipe | ✅ |
| `mean_face_count` | MediaPipe | ⚠️ Likely collinear with above |
| `ocr_text_frame_frac` | EasyOCR | ✅ |
| `mean_saturation`, `brightness`, `contrast` | OpenCV | ⚠️ Pick 1–2 |
| `colourfulness` | Hasler-Süsstrunk | ✅ |
| `red_ratio` | OpenCV hue mask | ✅ Brand-meaningful |
| `edge_density` | Canny | ✅ Visual-complexity proxy |
| `motion_intensity` | Farnebäck optical flow | ✅ |

Aspect ratio is dropped — every video is vertical by construction (D-001). A constant
feature carries no information.

### Block B — Audio

| Feature | Method | Keep? |
|---|---|---|
| `speech_dur_frac` | Whisper timestamps | ✅ |
| `words_per_min` | native transcript | ✅ Compute on native, not translated |
| `music_present` | YAMNet | ✅ |
| `is_original_audio` | Instagram metadata | ✅ **High priority** — strongest single effect in the brand-TikTok study |
| `rms_energy_mean` | librosa | ✅ |
| `spectral_centroid_mean` | librosa | ⚠️ |
| `tempo` | librosa | ⚠️ |
| `pitch_std` | librosa/openSMILE | ⚠️ |

`is_original_audio` is only directly available on Instagram. For YouTube, approximate it
or leave null and flag — do not silently impute.

### Block C — Text

Prefer language-invariant features (see [04](04-multilingual-pipeline.md) §5).

| Feature | Keep? |
|---|---|
| `caption_char_len` | ✅ Normalise within language |
| `hashtag_count` | ✅ Invariant |
| `emoji_count` | ✅ Invariant |
| `mention_count` | ✅ |
| `has_cta` | ✅ Via LLM annotation |
| `sentiment_score` | ✅ See [04](04-multilingual-pipeline.md) §4 |
| `emotion_label` | ⚠️ English-translation only |
| `readability` | ❌ **Dropped** — English-only formula |

### Block D — Creator / campaign

All via LLM annotation (§3), all requiring reliability validation.

`has_influencer`, `has_celebrity`, `is_sponsored`, `product_vs_lifestyle`, `ugc_vs_brand`,
`campaign_type`, `humour_present`.

### Block E — Platform and exposure

| Feature | Keep? |
|---|---|
| `platform` | ✅ Core |
| `followers` / `subscribers` | ✅ **Mandatory exposure control** |
| `account_prior_engagement` | ✅ Leave-one-out, past videos only |
| `video_age_days` | ✅ **Mandatory** |
| `posting_hour_local` | ✅ |
| `is_weekend` | ✅ |
| `market` / `language` | ✅ Control — see [04](04-multilingual-pipeline.md) §6 |
| `sampling_tier` | ✅ Control |
| `brand` | ✅ Only if tier-3 escalation used |

**`account_prior_engagement` leaks if done carelessly.** Compute it only from videos
published *before* the focal video, and only from the training fold.

---

## 3. LLM annotation

Input per video: native transcript + English translation + OCR text + caption + six
sampled frames. Output: strict JSON against a fixed schema.

> **Amended by D-023 (2026-09-15):** 60 random videos (30 per platform), 5 concrete
> constructs, coded in `src/coding/app.py`. The text below is the original plan.

**Validation is mandatory.** Hand-code a random 150-video subset (50% of the corpus at
this n — high, but affordable and it makes the annotation defensible). Report
Krippendorff's α per construct. **Drop any construct below 0.67.**

Expect a reliability gradient: concrete perceptual constructs (`has_celebrity`,
`has_cta`) will code well; abstract ones (`campaign_type`) will not.

---

## 4. Pruning rules — pre-register before looking at the outcome

### 4.0 Budget: ~18–20 features at n=183 (D-030, recorded 2026-09-23 — before any pruning)

D-007 capped the feature set at ~30 for n=300. The analysis set is now the 183 usable Zero Sugar
videos (D-030), in **21 accounts**, so the cap comes down with it. **The budget is 18–20 features
entering any model, 20 absolute maximum.**

Why that number: with a median split the focus set gives roughly 90 videos per class, and the
working rule of about 10 observations per class per predictor puts the ceiling near 9 — which is
below what the study needs to answer its questions. 18–20 is the compromise the design can
defend: it keeps one or two features per proposal block, and the grouped cross-validation by
account (D-006, 21 groups) plus the nested feature sets M0–M4 ([09](09-modelling.md) §2) are what
stop that from being read as a well-powered model. Anything beyond 20 would make SHAP unstable at
this size, which defeats the purpose of the study.

How it is reached, in this order, so the cap never decides which features matter:
1. Rules 1–5 below run exactly as written (the outcome is not consulted except in rule 5, and
   there only on training folds).
2. **Exposure controls do not count against the budget** (`followers`, `follower_tier`,
   `video_age_days`, `platform`) — they are in every model by design ([08](08-statistical-analysis.md) §2).
3. `title_char_len` (5.14, YouTube only) and `creator_collab` (5.15, Instagram only) count only
   against the budget of the platform-specific models they can enter, never the pooled one.
4. If the count is still over 20, the lowest-ranked features by rule 5 are dropped until it is 20,
   and every drop is recorded in §6 with its reason.

If either researcher re-look (2c.R1, 2c.R2) changes the focus set size materially, this budget is
recomputed from the same reasoning and the change is recorded here with its date.

### 4.1 The rules

Applied in order:

1. Drop near-constant features (>95% one value).
2. Drop features with >30% missing that cannot be sensibly flagged.
3. Drop annotation constructs with α < 0.67.
4. Within each block, drop one of any pair with |r| > 0.85 — keep the more interpretable.
5. If still over the budget in §4.0 (**18–20**, was ~30 before D-030), drop by lowest univariate
   association **computed on training folds only**.

Record every drop and its reason in §6. Pruning decided after seeing test performance is
not pruning, it is overfitting.

**Extraction is not narrowed by the focus.** Every feature is still measured on all 300 videos
(D-030): the 114 non-Zero-Sugar videos carry features so the robustness analysis can run, and the
prediction tool (D-017) must extract features from any video it is given. The focus applies when
a model is fitted, not when a feature is measured.

---

## 5. Execution log

| Date | Stage | Videos processed | Failures | Notes |
|---|---|---|---|---|
| 2026-09-16 | **5.1 prepare** (`src/features/prepare.py`) | 300 / 300 | 0 | 16 kHz mono WAV per video, 312 MB, 162.5 min. Normalisation profile cached per video. **No normalised video copy written (D-024).** 2 Reels found digitally silent (D-025). |

### 5.1 — what preparation found

- **Audio:** 300 / 300 extracted, every one 16 kHz mono. Audio and video length agree to
  within 0.5 s on all 300.
- **Silent audio, 2 videos:** `Cd5oWJNsfI0`, `DUC5hF6E7Lj` (Instagram). Both carry an AAC
  stream that is silent end to end (ffmpeg `volumedetect`: −91.0 dB mean *and* max, against
  −18 dB mean / −0.3 dB max on a normal file). Confirmed on the source MP4s, so this is the
  material, not the extraction. Flagged `audio_silent`; **5.6 must skip them** — speech-to-text
  invents words on silence rather than returning none (D-025).
- **Frame rate is not uniform:** 25 fps (n=101), 24 fps (n=98), 30 fps (n=97), 60 fps (n=2),
  29 fps (n=1), 10 fps (n=1). Any measure comparing frames over time samples at a fixed rate
  rather than trusting native fps.
- **Aspect ratio is near-constant, not constant.** 279 of 300 are 9:16 (0.562); 16 are 4:5
  (0.800); the rest are odd ratios (0.45–0.566). §2 Block A drops it correctly, but under
  pruning rule 1 (>95% one value), not "constant by construction".
- **Corpus file paths come from `data/media/download_manifest.csv`, not from the corpora.**
  The `video_path` column in both corpus parquets is empty (0/150 YouTube, 9/150 Instagram).
  `src/features/common.video_index()` does the join and refuses to run if any file is missing.


| 2026-09-16 | **5.2 scenes** (`src/features/scenes.py`) | 300 / 300 | 0 | `ContentDetector`, threshold 27.0, `min_scene_len` 0.25 s, PyAV backend. 22.9 min wall clock on 5 workers (113.7 min of CPU). |
| 2026-09-16 | **5.2 amended (D-026)** | 300 / 300 | 0 | Hidden-montage check added (1 video re-detected); final fragments under 0.25 s merged (37 videos). Detection itself reused from the first run. 4.4 min. |
| 2026-09-16 | **5.3 frames** (`src/features/frames.py`) | 300 / 300 | 0 | 15,290 JPEG frames (9,743 one-per-second, 5,815 one-per-shot, 268 both), 1.86 GB, quality 90, native resolution. Motion measured on 8,517 frame pairs. 7.9 min for the first full run. |

### 5.2 - cut detection, and what was checked before trusting it

> **Corrected later the same day (D-026).** The figures in this subsection are from the first
> run. Checking 5.3's output by eye found one photo montage read as a single shot, and 37
> videos credited with a one-to-six-frame "shot" at their very end. **Current figures:**
> `cuts_per_sec` median **0.466**, mean 0.543, max **9.679** (the montage; next 1.781);
> **23** single-shot videos (17 Instagram, 6 YouTube); 5,815 shots in total. Correlations:
> `scene_count` vs duration r = 0.76; `cuts_per_sec` vs duration r = 0.05 (Spearman 0.19);
> `mean_shot_len_sec` vs `cuts_per_sec` Spearman -0.988. The fastest-cut video is now the
> montage, `Dax6ozkufSd`; `DYFHnCeuLKB` is the fastest conventional edit. See the 5.3
> subsection below for how each problem was found.

**Result.** `cuts_per_sec` median **0.467**, mean 0.516, range 0.000-1.781 (10th percentile
0.086, 90th 0.994). `scene_count` 1-128, median 12. **21 videos are a single continuous
shot** (16 Instagram, 5 YouTube); all are 15.5 s or shorter, which is what a genuine
single-shot video looks like.

**Two settings were checked rather than assumed.**

*Working resolution - no effect.* Five videos spanning 6-178 s, 360-720 px wide and both
aspect ratios were detected at PySceneDetect's automatic downscale, at no downscale, and at
half scale. **All three gave identical scene counts on all five videos.** Cut detection is a
whole-frame average, so it does not depend on the working resolution the way `edge_density`
and `motion_intensity` will (D-024). The fast automatic setting is therefore safe, and is
what the corpus was run with.

*Threshold - real effect, kept at the default anyway.* On the same five videos, counts fall
by roughly 20-35% going from threshold 24 to 35, and `cuts_per_sec` rank correlation against
the default of 27 is 0.70-0.80. Short videos move most (a 6 s clip went from 0.82 to 0.16
cuts/sec across that range) because each cut is a larger share of the total. There is no
ground truth for cut locations and none will be hand-made, so the threshold stays at
PySceneDetect's untuned default of **27.0**. *This is a stated limitation: `cuts_per_sec` is
measured consistently across the corpus, but its absolute level is a function of the
threshold, and short videos are the least stable.*

**Detection was inspected, not just summarised.** Frames 0.2 s before and 0.1 s after
detected cuts were compared on four videos chosen from the extremes:

- a YouTube Bundesliga ad (1.11 cuts/sec) - every pair is a different shot (match footage,
  title cards, a product close-up). No false positives from camera motion.
- an Instagram street-interview Reel (0.82 cuts/sec, 75 scenes) - genuine rapid cuts between
  speakers at one table, not one long take misread.
- the fastest-cut video in the corpus (`DYFHnCeuLKB`, 1.78 cuts/sec) - a montage with a new
  clip roughly every half second. The number is real.
- a single-shot video (`FPMSu_mNu-M`, 15.5 s) - ten frames across its length show one
  unbroken take. `is_single_shot` is not a detection failure.

**Evidence for the Block A pruning decisions in section 2A** (feature-to-feature only; the
outcome was not consulted, so section 4 rule 4 can be applied at 5.11 as pre-registered):

| Pair | Correlation | What it means |
|---|---|---|
| `scene_count` vs `duration_sec` | r = 0.76 (Spearman 0.77) | Confirmed: a raw count is largely a restatement of length. Use the rate. |
| `cuts_per_sec` vs `duration_sec` | r = 0.18 (Spearman 0.21) | Nearly independent of length - the feature carries its own information. |
| `mean_shot_len_sec` vs `cuts_per_sec` | Spearman **-0.988** | Near-perfect inverse. Rule 4 applies at 5.11; keep `cuts_per_sec`, drop `mean_shot_len_sec`. |
| `motion_px_per_sec` vs `cuts_per_sec` | Spearman 0.57 (measured at 5.3) | Related but distinct; below the 0.85 line, both stay. |

**An early observation, not a finding.** Instagram Reels cut faster at the median
(0.519/sec vs 0.413/sec) and are shorter (19.6 s vs 29.1 s). This is a raw difference with no
controls; whether it survives account-level and exposure controls is Phase 8's question, not
this one's.

**Performance note.** 141 of the 150 YouTube files are AV1, which OpenCV decodes at about
1x real time. The PyAV backend decodes the same file ~4x faster and was used throughout. The
two backends place a few cuts differently (75 vs 77 scenes on one test file), so the corpus
was measured with one backend only - mixing them would put the decoder into the feature.

### 5.3 - frame sampling, motion, and the two problems it exposed in 5.2

**What is stored.** For every video, the frame nearest the middle of each second (the
*grid*: 9,743 frames) and the frame at the middle of each shot (5,815), as JPEG quality 90
at native resolution in `data/interim/frames/`. 268 frames serve both roles and are stored
once. 1.86 GB. Time-based features (`product_visible_frac`, `face_present_frac`,
`ocr_text_frame_frac`, `time_to_first_product`) use the grid only, so a video is not
weighted by its number of shots. `common.frame_list()` and `common.load_frame()` are how
later steps read them.

*Why keep 1.86 GB of frames when a 1.5 GB normalised video copy was rejected (D-024)?* The
copy would have been an intermediate that nothing needed. These frames are the sample four
later steps measure - product detection (5.4), faces, text and colour (5.5), and the
automated labels (5.12) - so they all see identical pixels at identical moments, and any
result can be checked by eye against the exact frame that produced it. With 67 GB free, that
is worth the space.

**Checked before the full run.**
- *Right pixels:* stored frames compared against an independent decoder (ffmpeg) at the same
  moments on 4 videos. Average colour per channel agreed within 0.4 (0-255 scale) - no
  colour-channel swap, no brightness-range error. Per-pixel difference 0.6-1.6, which is JPEG
  compression. One 23.976 fps file first read 6.3; comparing one frame earlier gave 1.1 - the
  comparison script's own millisecond rounding had picked the next frame, not the pipeline.
- *Right way up:* no file in the corpus carries a rotation flag.
- *By eye:* Coca-Cola red renders red; burned-in subtitles are sharp enough to read.

**Motion.** Dense optical flow (Farneback) between each grid frame and the frame nearest
0.1 s later, at the 360 px working width, divided by the true time gap: pixels per second,
comparable across 10 fps and 60 fps files. Pairs crossing a cut are skipped (1,205 of 9,722).
Per-video median over 299 videos: **17.9 px/s** (10th percentile 4.5, 90th 54.6, max 144.6).
Instagram 20.9, YouTube 16.4 at the median - raw, uncontrolled. Spearman 0.57 with
`cuts_per_sec` (related, below the 0.85 pruning line) and 0.02 with duration.
Extremes checked by eye: the stillest (0.03) is a static title card after a fade-in; the most
moving (144.6) is handheld first-person walking footage.

**Problem 1 - a photo montage read as one shot.** The third extreme checked, the corpus's
only 10 fps file (`Dax6ozkufSd`, motion 102), shows a different photo in every frame pair.
5.2 had called it a single shot because its 0.25 s minimum merges shots shorter than that.
Loosening the minimum is not the fix: at one frame, counts on the 44 most at-risk videos rose
up to 11x, and consecutive frames showed the additions were stage-light flicker and camera
shake. Instead, a motion-compensated residual (how much change optical flow cannot explain)
separates the cases cleanly:

| Video (truth established by eye) | Typical leftover change |
|---|---|
| Photo montage, new picture every frame | **89.8** |
| Ad with animated title cards | 28.8 |
| Handheld walking, shaky | 22.2 |
| Concert, flickering stage lights | 21.0 |
| Single take, people gesturing | 2.1 |
| Static title card | 0.1 |
| *All 300 videos, median* | *3.3* |

Threshold 50: one video above it. Built into 5.2 (D-026).

**Problem 2 - a phantom cut at the end of 37 videos.** A strict check - every shot has a
keyframe taken from inside itself - failed on 5 videos, all ending in a one-frame "shot".
PySceneDetect enforces the minimum shot length on every shot except the last; 37 videos had
a final segment of 1-6 frames, while no first or middle shot in the corpus was under 0.25 s.
Viewed frame by frame, one ends on a black frame and another on the first frame of a shot
the edit cut off. Such fragments are now merged into the preceding shot (D-026); 3 of the
37 turn out to be single-shot videos.

The same check exposed a keyframe tie in the montage: one-frame shots put each midpoint
exactly between two frames, and rounding gave 12 of its 39 shots a neighbour's frame.
Keyframes are now always taken from inside their own shot.

**Final integrity check, all 300 videos:** every shot has its own keyframe and it lies inside
that shot; no grid second missing; no frame file missing; every frame cache matches 5.2's
current scene list; no shot under 0.25 s outside the montage; motion missing only for the
montage, where every frame pair crosses a cut.

### 5.6 - speech-to-text (2026-09-21)

| Date | Stage | Videos | Failures | Notes |
|---|---|---|---|---|
| 2026-09-21 | **5.6 asr** (`src/features/asr.py`) | 300 / 300 | 0 | faster-whisper large-v3, float16, RTX 3050: 32.8 min, ~5x real time, 4.0 of 6.1 GB. Needed NVIDIA's CUDA 12 runtime (D-027). |

- **Block B features now measured:** `speech_dur_frac` (voice-activity share of the video) and
  `words_per_min` (words per minute *of speech*, native transcript). Median `speech_dur_frac`
  0.41 over all 300 and 0.78 among the 194 videos with speech; median `words_per_min` 172
  (183 videos with at least 2 s of speech).
- **An early observation, not a finding:** Instagram Reels are mostly without speech - median
  speech share **0.06**, against **0.75** for YouTube Shorts; 79 of 150 Reels have speech
  against 115 of 150 Shorts. Raw and uncontrolled.
- Transcripts, English translations and spoken language are in each video's cache (`asr`
  block); `data/interim/asr_summary.csv` is the one-row-per-video view. Validation and the
  language findings are in docs/04 section 7; clean-up rules in D-027.
- **For 5.9:** use `transcript_en` for emotion except where `transcript_en_failed` (2 videos);
  carry `transcript_low_confidence` through. **For 5.8:** sung jingles are transcribed as
  speech; the music detector decides singing versus talking.

### 5.8 - audio: loudness, tone, pitch; music, talk and singing (2026-09-22)

| Date | Stage | Videos | Failures | Notes |
|---|---|---|---|---|
| 2026-09-22 | **5.8 Part A** signal (`src/features/audio.py`, librosa, CPU) | 300 / 300 | 0 | 1.7 min. Pitch re-measured within segments after the first version confused speaker mix with prosody |
| 2026-09-22 | **5.8 Part B** events (AST on GPU) | 300 / 300 | 0 | ~17 min of work (wall clock 2.4 h: the machine paused ~2 h between videos 75 and 100) |

| Feature | Median (10th-90th pct) | n | Note |
|---|---|---|---|
| `loudness_db_mean` | -21.4 dB (-30.1 to -17.1) | 298 | 2 silent Reels null (D-025) |
| `loudness_range_db` | 17.0 dB (9.3 to 25.2) | 298 | |
| `spectral_centroid_hz` | 1,731 Hz (1,245 to 2,211) | 298 | "brightness" |
| `tempo_bpm` | 125 (104 to 144) | 298 | Meaningful only with music; unrelated to `music_frac` (Spearman -0.09) |
| `music_frac` | 0.81 (0.08 to 1.00) | 300 | Music in 272 videos |
| `talk_dur_frac` | 0.32 (0.00 to 0.88) | 300 | Talking, net of singing. Instagram median 0.00, YouTube 0.66 |
| `speech_sung_frac` | 0.00 (0.00 to 0.18) | 187 | 37 videos with some singing, 14 mostly sung |
| `pitch_std_talk_semitones` | 3.46 (2.14 to 6.03) | 166 | Within-segment, talk only; 20 rest on one segment |

**Checked against known videos** (truth from content, not by listening): 3 songs -> 100% sung;
6 talking videos -> 0-1% sung; 2 of 3 chanted Korean slogans -> talk, the third on the line.
Every one of the 14 "mostly sung" videos reads as lyrics, humming or a jingle from its
transcript. Details and the reasoning for each choice: D-028.

**Not measurable:** `is_original_audio` - 71% missing on Instagram, absent on YouTube (D-028).

### 5.9 - sentiment and emotion (2026-09-23)

| Date | Stage | Videos | Failures | Notes |
|---|---|---|---|---|
| 2026-09-23 | **5.9 sentiment + emotion** (`src/features/sentiment.py`, both models on the GPU) | 300 / 300 | 0 | 0.5 min. XLM-T sentiment (1.12 GB) on three texts each; DistilRoBERTa emotion (331 MB) on English text only. Downloads approved by the researcher; `sentencepiece` 0.2.2 (1.4 MB) and `langdetect` 1.0.9 (1 MB) added |

Three texts are scored separately and never mixed: **speech in English** (5.6's translation),
**speech in its own language**, and the **caption** (Instagram caption; on YouTube the title plus
description).

| Feature | Median (10th-90th pct) | n | Note |
|---|---|---|---|
| `sentiment_speech` | +0.03 (-0.43 to +0.71) | 194 | `P(pos) - P(neg)` on the English translation. Labels: 73 positive, 66 neutral, 55 negative |
| `sentiment_speech_native` | +0.01 (-0.59 to +0.58) | 154 | Same model on the spoken language, **only inside its 8 languages** |
| `sentiment_caption` | +0.39 (+0.01 to +0.79) | 291 | Labels: 137 positive, 147 neutral, 7 negative - captions are marketing copy, and it shows |
| `emotion_label` | - | 192 | neutral 105, joy 39, surprise 23, fear 9, disgust 6, anger 6, sadness 4 |
| `emotion_score` | 0.72 (0.45 to 0.94) | 192 | Confidence in the winning emotion |

**Coverage, and what is deliberately left null.** 106 videos have no transcript to score (98 no
speech, 6 no intelligible speech, 2 silent - D-025) and 9 have no caption; 6 videos have neither
and are `status = no_text`. Those are **null, not zero**: zero would read as neutral, a
measurement that was not made. Native sentiment is skipped for 40 videos whose spoken language is
outside XLM-T's 8 (bn, ko, ms, ne, sw, th, tr, vi, zh) and the reason is recorded per video.
Captions: 238 in covered languages, 53 outside them (scored and flagged, never used as the
primary measure), 9 with no language detected. 5.6's `transcript_low_confidence` (47) and
`transcript_en_failed` (2) are carried through; for those 2, the native score becomes the primary
one and `speech_sentiment_source` says so.

**Cross-check required by [04](04-multilingual-pipeline.md) section 4.** Native against
translated sentiment on the 154 videos with both: **Pearson 0.946, Spearman 0.929, same
three-way label on 86%**. Disagreements are almost all native-neutral read as translated-negative
(11 of 21). High agreement is what docs/04 said would support measuring emotion on the
translation, so that route stands - and emotion is still reported as post-translation.

**Checked before trusting the output** (the CLIP lesson):
- transformers 5.11 warns this tokenizer has "an incorrect regex pattern" and advises
  `fix_mistral_regex=True`. **The warning is wrong here:** the default tokenisation is identical
  to the reference sentencepiece tokenizer, while that flag changes it ("!" becomes "_!"). Do not
  set it. Text round-trips correctly in en, es, pt, hi, ar and ko.
- On 11 sentences with obvious sentiment across 6 languages the model scored **11 of 11** right,
  with confident probabilities (0.90-0.96).

**A measurement property to carry into analysis.** The score is a length-weighted average over
512-token chunks, so **longer speech reads as more neutral**: median |score| is 0.45 under 200
characters, 0.29 at 200-600, and 0.15 at 600-2,000 (Spearman -0.31 between length and |score|).
Consequences: H3 uses the continuous score with text length available as a covariate; 7.2's
diagnostics check `sentiment_speech` against `caption_char_len` and word count before either
enters a model; and speech and caption sentiment are only weakly related (Spearman 0.25), so they
are two features, not one.

**Stated in methods:** emotion is measured on translated text (docs/04 section 4), it is
English-only, it has no manual check in the 60 codes, and it is therefore reported as an
unvalidated automated measure under the 4.2 rule.

### CLIP product-detection validation

| Metric | Value |
|---|---|
| Frames hand-coded | 200 |
| Precision | |
| Recall | |
| Threshold chosen | |
| Escalated to YOLO? | |

### Annotation reliability (Krippendorff's α)

| Construct | α | Kept? |
|---|---|---|
| `has_celebrity` | | |
| `has_influencer` | | |
| `has_cta` | | |
| `product_vs_lifestyle` | | |
| `ugc_vs_brand` | | |
| `campaign_type` | | |
| `humour_present` | | |

---

## 6. Pruning record

_To be filled._

| Feature | Dropped at rule | Reason |
|---|---|---|

**Final feature count:** ___ / 30

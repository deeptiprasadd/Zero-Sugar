# 05 — Feature Extraction

**Status:** Planned. Method specified below; fill results as extraction runs.

Constraint that governs everything here: **18-20 features reach the models** (D-030; it was ~30
under D-007, when the analysis set was 300 videos rather than 183 — see §4.0). Extract
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
| `talk_music_frac` | 5.8's sound windows over its talk segments | ➕ **Added 2026-10-17 (D-063):** background music behind talking - analysis only, not a model feature; not detected (D-064) |
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

`has_influencer`, `has_celebrity`, `product_vs_lifestyle`, `ugc_vs_brand`, `humour_present`.

> **Amended by D-032 (2026-09-24):** `is_sponsored` and `campaign_type` are **dropped** - the
> first is missing for 107 of 150 Reels and near-constant on YouTube, the second is abstract with
> no manual check. `creator_collab` (task 5.15, from collection metadata) replaces `is_sponsored`.
> **Voice emotion is dropped too** (Block B): it needs a model the project does not have, and a
> typical Reel carries speech ~6% of the time. 5.12 therefore annotates **7 constructs**.

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

> **Amended by D-038 (2026-09-29) - how 5.12 actually runs.** Seven constructs (D-032). Model:
> **Qwen2.5-VL 3B** (`qwen2.5vl:3b`, Q4_K_M, 3.2 GB) in Ollama on the laptop GPU. A 10-video pilot
> on a rule fixed before it ran first chose Qwen3-VL 4B (agreement on the four checked constructs
> 70% vs 62%), but Qwen3-VL's built-in reasoning ran away on some videos (one took 520 s and
> answered nothing). With reasoning switched off it was re-piloted on the same videos under a rule
> written first, reached 57%, and so lost to Qwen2.5-VL (`reports/annotation_pilot.md`,
> `reports/annotation_pilot_no_reasoning.md`). Input: six evenly spaced grid
> frames (longest side 768 px), account name, caption, English speech translation - **no OCR
> text**, because 5.5 part B reads none (D-034); the model reads on-screen text from the frames.
> The four checked questions are the codebook's own wording (`src/coding/codebook.py`); the
> three unchecked ones are defined in `src/features/annotate.py`. Temperature 0, fixed seed,
> answers forced into a JSON schema of the allowed options, every raw answer kept. Validation is
> 4.2 on the 50 coded videos the pilot did not use (D-038).

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

### 5.13 - music type: measured, and found not measurable (2026-09-28)

| Date | Stage | Videos | Failures | Notes |
|---|---|---|---|---|
| 2026-09-28 | **5.13 music genre** (`src/features/music_genre.py`, AST already on disk, GPU) | 300 / 300 | 0 | 9.1 min. 272 videos with music, 26 without, 2 silent (D-025). Seven genre groups fixed before scoring |

**The finding: AudioSet's genre labels do not separate this corpus, so music *type* is not
measured.** The numbers that decide it, on the 272 videos with music:

| | |
|---|---|
| Top genre group's mean probability | median **0.019** (10th-90th 0.004-0.069), max 0.189 |
| Margin over the second group | median 0.010 |
| Videos whose top group reaches 0.20 / 0.10 | **0** / 10 of 272 |
| Strongest single AudioSet label in a music window | median **0.790** - the generic "Music" |

Looking at what the model actually says settles it. On eight inspected videos the confident labels
are `Music` 0.55-0.73, `Speech`, `Television`; every genre label sits at 0.01-0.03 - the same
level as `Fart` 0.04, `Ice cream truck` 0.05 and `Animal` 0.01 in the same windows. A genre chosen
at 0.02 is competing with nonsense at 0.02. Instrument labels occasionally do better (an accordion
at 0.11), which is a hint that AudioSet's instrument heads work better than its genre heads, not
evidence that the genre is right.

The choice *is* internally consistent - a video's top group wins a median 85% of its own music
windows - but consistency without magnitude is not validity: the same small bias repeats across
windows of the same track. This is the same failure as D-028's singing labels, found the same way.

**Kept, not deleted:** the scores stay in each video's cache and in
`data/interim/music_genre_summary.csv` with `status`, so the finding is checkable. They do **not**
enter the feature set (`music_genre_top` is not a feature), and the write-up reports music type as
not measurable alongside `is_original_audio` and voice emotion. `music_present` and `music_frac`
from 5.8 are unaffected and remain the audio features for H-tests.

### 5.14 title length and 5.15 creator collaboration (2026-09-28)

| Date | Stage | Videos | Failures | Notes |
|---|---|---|---|---|
| 2026-09-28 | **5.14 + 5.15 + Block C text counts** (`src/features/metadata.py`; metadata only, no model) | 300 / 300 | 0 | Instant. Nothing downloaded |

| Feature | Value | Note |
|---|---|---|
| `title_char_len` | median **51** characters (10th-90th 29-84), 9 words | YouTube only; null for every Reel |
| `title_char_len_z_lang` | computed for **145 of 150** Shorts | Arabic (4 titles) and Turkish (1) are too few to standardise - left null and flagged |
| `creator_collab` | **41 of 150 Reels**; YouTube 0 of 150 | False by construction on YouTube (all brand channels), not missing |
| `caption_char_len` | median 163 (YouTube), 147 (Instagram) | YouTube = title + description, the same text 5.9 scored |
| `hashtag_count` | median 2 both platforms | 47% of Shorts and 33% of Reels have none |
| `mention_count` | median 0 | 81% of Shorts and 67% of Reels have none |
| `emoji_count` | median 1 both platforms | |
| `has_question_mark` | 26 Shorts, 33 Reels | Matches the Arabic `؟` as well (docs/04 section 5) |

The caption counts had no task number of their own - they are docs/05 Block C's language-safe
features, computed here because they come from the same text. Title language is taken from 5.9's
detection on title + description, not on the 50-character title alone; 5.7 will replace it.

### 5.4 product on screen - first attempt with CLIP: failed its gates (2026-09-28)

| Date | Stage | Videos | Failures | Notes |
|---|---|---|---|---|
| 2026-09-28 | **5.4 first attempt** (`src/features/product.py`, reused the existing CLIP embeddings - no download, no re-encoding) | 9,743 grid frames from 300 videos scored | - | **Failed the gates fixed before scoring; nothing was written to the feature cache** |

Gates and results (`reports/product_detection_attempt1_clip.md`), against the researcher's blind
codes - 54 videos with a Coca-Cola product visible, **5 with none**:

| Check | Gate | Result | Pass |
|---|---|---|---|
| A. ROC AUC of `product_prob_mean` | >= 0.70 | **0.419** (95% CI 0.14-0.72) | no |
| B. All no-product videos in the bottom half | all <= 0.50 | ranks 0.72, 0.94, 0.72, 0.16, 0.51 | no |
| C. Not near-constant (10th-90th spread) | >= 0.10 | 0.720 | yes |

Median score is **higher** for the no-product videos (0.630) than for the product-visible ones
(0.523) - the measure points the wrong way. Using the best square instead of the mean gives 0.485,
so the change made after D-029 was not the problem.

**Why it fails, from looking at the frames' winning prompts.** A Reel coded *no product* scores
0.935 because "a person holding a Coca-Cola drink" wins 94% of its squares: CLIP matches the
**scene** - a person holding something - not the brand. The podcast Shorts that genuinely show a
can on the table score 0.06-0.10, because "a close-up of a person's face" wins: a can covering a
few percent of the frame cannot win a whole-square comparison. **Whole-image CLIP cannot see a
small product**, which is the same reason the D-029 Zero Sugar screen failed. No prompt wording
fixes it.

**Two further limits to state whatever comes next:**
1. **At video level the construct barely varies** - 54 of the 59 usable codes say a product is
   visible - so "is a product visible at all" is nearly constant in a brand corpus, and an AUC
   computed against 5 negatives is weak whatever it says (CI 0.14-0.72).
2. **What H2 needs is `product_visible_frac`, how much of the video shows the product, and the 60
   codes contain no ground truth for that at all.** The frame-level check this section was always
   meant to hold (200 hand-coded frames, above) is the only way to validate it.

**Next, for the researcher to choose:** the YOLO fallback (object detection finds small objects,
gives boxes, and would make `product_mean_area` possible, but is brand-blind - it would measure
"a drink container on screen"), a short frame-level check by eye to validate either measure, or
reporting product visibility as not measured and letting H2 / RQ4 / 5.17 rest on the Zero Sugar
label alone. Recorded in D-033; nothing is used until that is decided.

### 5.4 second attempt - container detection, and the frame check that will judge it (2026-09-28)

| Date | Stage | Frames | Failures | Notes |
|---|---|---|---|---|
| 2026-09-28 | **5.4 second attempt** (`src/features/product_yolo.py`, COCO-trained YOLO) | 9,743 grid frames | 0 | 4.6 min on the GPU. **Nothing downloaded** - a 5.5 MB COCO YOLO already on the laptop was copied to `models/yolo26n.pt` |
| 2026-09-28 | **5.4v frame sample** (`src/features/product_frame_sample.py`) | 120 frames drawn | - | One random grid frame per video, 60 videos per platform, seed 20260928, **drawn before any score was computed** |

**An object detector is the right tool for the failure CLIP had**: it looks for small objects and
returns boxes, so `product_mean_area` - which docs/05 Block A asks for and CLIP could never give -
becomes possible.

**What it measures, named honestly: a drink container, not a Coca-Cola product.** The model is
COCO-trained and brand-blind (`bottle`, `cup`, `wine glass`); it cannot tell a Coca-Cola can from
any other. The features are therefore called `container_*`, and the frame check below measures how
often a detected container really is Coca-Cola's - the number to quote whenever the feature is
described.

First run, unvalidated and not yet in the feature set:

| | |
|---|---|
| Frames with a container | 27% at 0.15, **23% at 0.25**, 19% at 0.40 |
| Videos with one somewhere | 242 of 300 (Instagram 116, YouTube 126) |
| `container_visible_frac` | median 0.14 Instagram, 0.13 YouTube (10th-90th 0.00-0.75) |
| `container_mean_area` | median **7%** of the frame where found (90th 30%) |
| `time_to_first_container` | median 4.5 s over 242 videos; 58 never |

Per-frame confidence and box area are cached (`data/interim/container_frame_scores.parquet`), so a
threshold can change without re-running the detector.

**The frame check (5.4v) decides whether any of this is used.** 120 frames, one click each, three
answers - *a Coca-Cola product* / *another drink container* / *nothing* - which give both the truth
the brand-blind detector can be judged against and the truth the study actually wants. The page
(`python -m src.coding.frame_check_app`) never shows a score, a label or a box. Gates are unchanged
and applied by `src/features/product_validate.py`: frame-level AUC >= 0.70 for *container*, the
blind-coded no-product videos in the bottom half, and a measure that is not near-constant. Both
methods are scored on the **same** frames, so the comparison is fair. A failed gate means product
visibility is reported as not measured (D-033 option C) - not a threshold moved until it passes.

**Result, 2026-09-29: failed gate B - product visibility is not measured (D-037).** All 120
frames answered (37 Coca-Cola product, 1 other container, 82 nothing).

| Gate | Result | Required | Pass |
|---|---|---|---|
| A. Frame-level AUC, container visible | 0.748 (95% CI 0.66-0.84) | >= 0.70 | yes |
| B. Blind-coded no-product videos in the bottom half | ranks 0.60, 0.10, 0.36, 0.24, 0.10 | all <= 0.50 | **no** |
| C. Not near-constant (10th-90th spread) | 0.745 | >= 0.10 | yes |

The one video that fails gate B shows a Coca-Cola-branded fountain cup, which the detector counts
as a container and the codebook's *no product* ("no Coca-Cola pack") does not - the detector and the
blind code measure different things, and the gate exists to catch that. Neither the code nor the
gate was changed after the result. At the pre-set 0.25 threshold the detector's precision was 69%
and recall 58%; 37 of the 38 frames with a container showed a Coca-Cola product. Whole-image CLIP
ranked the same frames better (AUC 0.844) but failed gate B far worse in the first attempt, so it is
not reinstated. **The `container_*` features do not enter the feature table**; the cached scores are
kept for checking. 5.17 is cancelled as specified.

### 5.5 part A - colour, contrast and visual busyness (2026-09-28)

| Date | Stage | Videos | Failures | Notes |
|---|---|---|---|---|
| 2026-09-28 | **5.5A colour and busyness** (`src/features/visual.py`, OpenCV, CPU) | 300 / 300 | 0 | 0.6 min, 6 threads. No model, no download. Grid frames at the 360 px working width (D-024) |

| Feature | YouTube median (10th-90th) | Instagram median (10th-90th) |
|---|---|---|
| `brightness` | 0.463 (0.345-0.604) | 0.527 (0.306-0.709) |
| `contrast` | 0.215 (0.167-0.278) | 0.209 (0.154-0.275) |
| `saturation` | 0.408 (0.238-0.690) | 0.417 (0.278-0.682) |
| `colourfulness` | 0.196 (0.115-0.322) | 0.231 (0.141-0.381) |
| `red_ratio` | 0.176 (0.102-0.599) | 0.223 (0.076-0.550) |
| `edge_density` | 0.049 (0.033-0.073) | 0.046 (0.026-0.078) |
| `brightness_sd` (across frames) | 0.114 (0.046-0.182) | 0.074 (0.016-0.158) |

**No pair correlates above 0.85**, so all six survive pruning rule 4 for now; the strongest are
`colourfulness` vs `red_ratio` (Spearman 0.72) and `saturation` vs `colourfulness` (0.69). Re-check
at 7.2C with every feature present.

**One feature is already a pruning candidate:** `red_frame_frac` (share of frames at least 2% red)
has a median of **1.000** on both platforms - nearly every frame of nearly every video carries some
Coca-Cola red, which is unsurprising and nearly constant. The continuous `red_ratio` is the version
to keep. Recorded here rather than dropped silently.

**`red_ratio` is a colour measure, not a product measure.** Red pixels can be a can, a backdrop, a
shirt or a logo; product visibility is task 5.4.

### 5.5 part C - faces (2026-09-28)

| Date | Stage | Videos | Failures | Notes |
|---|---|---|---|---|
| 2026-09-28 | **5.5C faces** (`src/features/faces_text.py`, MediaPipe BlazeFace short-range) | 300 / 300 | 0 | 3.3 min. Model **230 KB, researcher-approved**; this mediapipe build (0.10.35) ships no models, so it is fetched once to `models/` |

| Feature | YouTube median (10th-90th) | Instagram median (10th-90th) |
|---|---|---|
| `face_present_frac` | 0.578 (0.067-0.970) | 0.467 (0.000-0.926) |
| `mean_face_count` | 0.616 (0.067-1.112) | 0.467 (0.000-0.970) |
| `mean_face_area` | 0.099 (0.053-0.206) | 0.078 (0.042-0.178) |
| `face_conf_mean` | 0.865 (0.604-0.919) | 0.810 (0.603-0.913) |

**262 of 300 videos show a face in at least one frame**, 155 in most frames - which is what brand
advertising should look like, and the sanity check this step needed. `mean_face_area` is kept
because it separates a close-up from a crowd shot, which `face_present_frac` alone cannot.

### 5.5 part B - on-screen text: detector only, nothing read (2026-09-28)

EasyOCR's CRAFT detector (**83 MB, researcher-approved**), **detection only, no recognition**:

- docs/04 section 3 keeps these features coarse on purpose;
- detection is **language-free**, so Arabic, Korean and Thai frames are treated like English ones -
  and docs/04 warns Arabic recognition is where OCR fails worst;
- text is found on the **full-resolution** frame, not the 360 px working copy (D-024).

`ocr_region_count` replaces docs/04's `ocr_word_count`: without recognition a region is a text line
or block, not a word, so it is named for what it measures (D-034). **`lang_onscreen` (5.7) is
therefore not measured** - it would need a reader per script.

| Date | Stage | Videos | Failures | Notes |
|---|---|---|---|---|
| 2026-09-28 | **5.5B on-screen text** (EasyOCR CRAFT, detection only, GPU) | 300 / 300 | 0 | 42.1 min, full-resolution frames |

| Feature | YouTube median (10th-90th) | Instagram median (10th-90th) |
|---|---|---|
| `ocr_text_frame_frac` | 0.970 (0.500-1.000) | 0.927 (0.372-1.000) |
| `ocr_region_count` | 4.54 (1.20-12.65) | 3.13 (0.89-10.15) |
| `ocr_mean_text_area` | 0.063 (0.027-0.101) | 0.040 (0.010-0.113) |

**Checked by drawing the boxes on frames and looking** (the habit that caught 5.2's montage and
5.8's singing labels). Three videos - busiest, typical and quietest by region count - were
inspected: **every box was real text**, and the busiest frame is a mock phone-chat screen that
genuinely is full of writing. No false positives on textures or patterns.

**What the inspection changed, though, is how the feature must be read.** The detector finds the
**Coca-Cola logo and the legal small print** as readily as a subtitle, and those sit in almost every
frame of an advert. That is why `ocr_text_frame_frac` is near-saturated: **123 of 300 videos are
exactly 1.000** and 124 are at 0.99 or above. So:
- **`ocr_text_frame_frac` is a pruning candidate** for the same reason as `red_frame_frac` - a
  near-constant feature carries no information.
- **`ocr_region_count` and `ocr_mean_text_area` carry the variation** (region count median 4.0,
  10th-90th 1.1-11.4, max 36.7) and are the two to keep into 5.11.
- Any finding about "on-screen text" means *any* text, including brand marks and disclaimers, not
  only captions the viewer is meant to read. State it that way in the results.

### 5.7 caption and spoken language, code-switching (2026-09-28)

| Date | Stage | Videos | Failures | Notes |
|---|---|---|---|---|
| 2026-09-28 | **5.7 language** (`src/features/language.py`, langdetect) | 300 / 300 | 0 | Instant. `lang_onscreen` left null pending 5.5B recognition, which is not planned |

| | |
|---|---|
| Spoken language known | **194** (the rest have no speech, 5.6) |
| Caption language known | **291**, of which **267** at >= 0.90 probability |
| Captions too short to classify (< 20 characters) | 9 - left unknown rather than guessed |
| Both known and reliable | 174 videos: **agree 144, differ 30** |
| **English caption over non-English speech** | **21 videos** - exactly the pattern docs/04 section 1 predicted |
| `is_code_switched` | **60 videos**: low-confidence transcript 47, language mismatch 30, uncertain spoken language 9 (a video can have more than one) |

Most common mismatches: Hindi speech with an English caption (8), Nepali speech with an English
caption (5), English speech with a Spanish caption (4). Captions are written for a wider audience
than the audio, which is why docs/04 keeps the fields separate instead of collapsing them into one
"language" variable.

### 5.16 keyword groups (2026-09-28)

| Date | Stage | Videos | Failures | Notes |
|---|---|---|---|---|
| 2026-09-28 | **5.16 keywords** (`src/features/keywords.py`, no model, no download) | 300 / 300 | 0 | Instant. List fixed and approved 2026-09-24 in [04](04-multilingual-pipeline.md) §5.1, before this ran and before any engagement result was seen |

Two texts per video, never merged: 5.6's **English translation** (192 videos have one, searched
with the English lists whatever was spoken) and the **caption in its own language** (291 have a
detected language). 288 of 300 videos were searched for at least one group.

| Group | Hit | No hit | Not searched | Instagram / YouTube (hits) |
|---|---|---|---|---|
| `kw_event` (sport or music event) | **104** | 179 | 17 | 26 / 78 |
| `kw_together` (togetherness, sharing) | **86** | 197 | 17 | 44 / 42 |
| `kw_taste` (taste, refreshment) | **53** | 230 | 17 | 32 / 21 |
| `kw_zero_sugar` | **53** | 220 | 27 | 32 / 21 |
| `kw_new` (new or limited) | **37** | 246 | 17 | 19 / 18 |
| `kw_offer` (offer or prize) | **18** | 265 | 17 | 9 / 9 |

Median one group per video; 69 videos hit none; 20 hit three or more. Hits came from the caption
alone 196 times, the transcript alone 87, and both 68.

**`kw_event` is much more common on YouTube (78 vs 26)** — the FIFA World Cup content in the
YouTube corpus, which the 2026 campaign is built around. That is a composition fact about the
corpus, not a platform effect, and it belongs beside any result that uses this feature.

**Not searched is not a zero.** 17 videos have neither an English transcript nor a caption in a
covered language; `kw_zero_sugar` adds 10 more because its vocabulary covers a different language
set (it reuses `zero_sugar.ZERO_TERMS`: en, es, pt, ar, th, id, hi, so Turkish, Vietnamese and
Korean captions are not searched for it). Those rows are **null**, and `kw_*_searched` records
which text was searched for every video.

**Spot-checked before use, as §5.1 requires.** Matched terms were printed per group: Korean
경품 (prize), 당첨 (win), 한정 (limited edition), 맛있 (tasty), 함께 (together) all landed in the
right groups, as did the English hits. Every hit stores the term that caused it, so a surprising
count can be traced to the word behind it.

Three amendments to the instrument, all recorded in [04](04-multilingual-pipeline.md) §5.1 with
reasons: no accent folding (it would break Vietnamese), substring matching for Thai/Korean/Hindi/
Arabic, and short over-matching words used only inside phrases.

### CLIP product-detection validation

| Metric | Value |
|---|---|
| Frames hand-coded | **0** - not done; the video-level check above was used instead |
| Precision | not computed: the gates failed first (AUC 0.419) |
| Recall | not computed |
| Threshold chosen | none - no threshold is honest on a measure that points the wrong way |
| Escalated to YOLO? | **Yes, 2026-09-28** - with a model already on disk, no download (D-033). Judged on 120 hand-answered frames on 2026-09-29: precision 69%, recall 58% at 0.25, frame AUC 0.748, **failed gate B** - not used (D-037) |

### Annotation reliability (Krippendorff's α)

**Filled 2026-09-29 (D-038).** Qwen2.5-VL 3B vs the researcher's blind codes, on the 50 coded
videos the pilot did not use (46 answered). Rule: keep if α >= 0.67. Report:
`reports/annotation_reliability.md`.

| Construct | α (95% CI) | Kept? |
|---|---|---|
| `has_celebrity` | 0.100 (-0.16 to 0.48) | no |
| `has_influencer` | 0.382 (0.03 to 0.69) | no |
| `has_cta` | -0.032 (-0.33 to 0.23) | no |
| `humour_present` | 0.133 (-0.62 to 0.71), model unsure on 38 of 46 | no |
| `product_vs_lifestyle` | no manual check | unvalidated column, never modelled |
| `ugc_vs_brand` | no manual check | unvalidated column, never modelled |
| `promotional_language` | no manual check | unvalidated column, never modelled |
| ~~`campaign_type`~~ | dropped by D-032 | - |

---

## 6. Pruning record

**Filled 2026-09-28 (D-036).** Full table, every drop with its reason:
`reports/feature_pruning_record.md`, written by `python -m src.features.prune`.

| | |
|---|---|
| Candidates assembled (5.10) | **76** in `data/processed/features.parquet`, 300 rows, no engagement column |
| Survived rules 0, 1, 2 and 4 | **27** |
| **The pooled set** | **20** - the top of a priority order fixed before any outcome was seen |
| Ordered reserve | 7, enter only if a keeper fails rule 3, strictly in order |
| Rules not yet applied | ~~3~~ applied 2026-09-29 (D-038); **5** (reads the outcome - training folds only, Phase 9) |
| Re-run 2026-09-29, after 5.4's verdict | `features.parquet` byte-identical (SHA-256 `0f545806...`), same 20 and same reserve. 5.4's `container_*` features do not enter - gate B failed (D-037). Next re-run: after 5.12 |
| Re-run 2026-09-29, after 5.12 and 4.2 - **rule 3 applied** | 7 `auto_*` columns added (80 candidates in the pruning blocks; SHA-256 `25186e50...`). All four checked labels fail alpha and are dropped under rule 3 (`auto_has_celebrity` is also near-constant); the three unchecked labels are kept as columns and never modelled (D-038). **Same 20 and same 7 in reserve.** Rules left: **5 only** (training folds, Phase 9) |
| Re-run 2026-09-29, after 2c.R2 (D-039) | Focus set **183 -> 192** (Instagram 111 -> 120). Constancy and correlations re-measured on the 192: only percentages moved (e.g. speech-only features 37% -> 38% missing); **same 20, same 7 in reserve**. The speech-only sub-analysis now has 119 focus videos. SHA-256 `83fab00b...`. The 18-20 budget is kept: the focus set grew, and section 4.0's reasoning only tightens as n falls |

The 20: `duration_sec`, `cuts_per_sec`, `motion_px_per_sec`, `face_present_frac`,
`mean_face_area`, `edge_density`, `colourfulness`, `red_ratio`, `ocr_region_count`,
`ocr_mean_text_area`, `music_frac`, `talk_dur_frac`, `loudness_db_mean`, `loudness_range_db`,
`sentiment_caption`, `caption_char_len`, `hashtag_count`, `emoji_count`, `kw_event`,
`kw_promotional`.

Exposure controls sit outside the budget and are in every model by design: `followers`,
`video_age_days`, `account_size_tier`, `platform`, `posting_hour_utc`, `is_weekend_utc`.

Routed rather than dropped: 11 speech-dependent features to a **speech-only sub-analysis** (117
focus videos have speech); `title_char_len*` to YouTube-only models; `creator_collab` to
Instagram-only models.



_To be filled._

| Feature | Dropped at rule | Reason |
|---|---|---|

**Final feature count:** ___ / 30

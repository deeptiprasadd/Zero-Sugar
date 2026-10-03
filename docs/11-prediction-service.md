# 11 — Prediction Service (Flask UI)

**Status:** Planned; **re-scoped 2026-10-02 by D-046** - gate G1 failed (D-045), so the tool follows section 5's pre-registered fallback: an honest base-rate prediction, video diagnostics, and an Instagram content score labelled exploratory; no platform recommendation. Where this document and D-046 differ, D-046 wins. This is the project's final deliverable and its stated purpose: a tool
where someone supplies a video (file or link), and gets back a prediction of how it would
perform **on YouTube Shorts and on Instagram Reels**, so they can decide what to post and
where.

Everything in `docs/05`–`10` feeds this. The models are not the end of the project; this is.

---

## 1. What the tool can honestly predict — read this before designing the UI

The goal is an *accurate* predictor. Accuracy here has hard limits set by the data, and a
tool that overstates its confidence is worse than useless — it would send people in the
wrong direction with a number that looks authoritative. Four constraints shape the design.

### 1.1 The dependent variable is a percentile, not a like count

`docs/06` §3 defines engagement as a **percentile rank within `platform × account_size_tier
× year`**. The model therefore predicts *relative* performance — "this creative would land
around the 70th percentile for accounts your size" — not "you will get 12,438 likes."

An absolute count can be *derived* (`predicted_rate × follower_count`), and the UI should
show it because it is what people actually want, but it must be shown as a **range**, and
it must be labelled as derived. A point estimate would be false precision.

### 1.2 Exposure dominates content

This is the single most important finding in the literature behind this project (Frontiers
in AI 2026, see the survey): **exposure features dominate SHAP, and removing them costs
more than removing content features.** `docs/09` §1 makes Baseline 1 — exposure only —
mandatory for exactly this reason.

**Consequence for the UI: a video alone is not enough input.** The tool must ask for the
account's follower count and platform. Without them it is predicting with the weakest half
of the model. If a user genuinely has no account context, the tool should return a
content-only prediction and say plainly that it is the less reliable mode.

### 1.3 Reach/views are YouTube-only

`docs/06` §1: Instagram does not expose Reel views reliably — Meta returns combined IG+FB
counts for crossposted video and insights are own-account only. So:

| Output | YouTube Shorts | Instagram Reels |
|---|---|---|
| Engagement percentile | ✅ | ✅ |
| Likes + comments range | ✅ | ✅ |
| Views / reach | ✅ (secondary DV) | ❌ **Not predictable** — say so in the UI |

Do not invent an Instagram reach number. The honest answer is "Instagram does not publish
this".

### 1.4 The training data is one brand — and now one product line

The corpus is Coca-Cola's own accounts and their collaborating creators (D-014), 8.8K–3.3M
followers, 38 markets. A prediction for a food blogger with 400 followers, or for a
non-brand personal video, is **out of distribution**. The tool must detect this and warn —
see §4.3. This is a genuine limitation of a single-brand study design, not a bug to hide.

**Narrower since D-030 (2026-09-23).** The models are fitted on the **183 usable Coca-Cola Zero
Sugar videos** (Instagram 111 from 16 accounts, YouTube 72 from 5, 58 of those from one channel).
Three consequences the UI and the model card must carry:

1. **What the tool is for:** how a *Zero Sugar* short video would perform on each platform. A
   video featuring another Coca-Cola variant, or no product at all, is out of distribution for
   the same reason a 400-follower account is — the warning in §4.3 covers both, and the reason
   string says which applies.
2. **Instagram's side is mostly hand-picked creative** (105 of 111), so its training data is
   tilted towards the Zero Sugar posts that were easiest to find on each account's page, not a
   random sample of them ([08](08-statistical-analysis.md) §7.9.3(c)).
3. **YouTube's side is thin and concentrated:** 72 videos, 5 channels, 58 from the global
   channel. Per-platform confidence must reflect that, not be averaged away.

The non-Zero-Sugar videos remain in the data as a robustness set (D-030), so a wider model can be
fitted and compared; if it is shipped instead, the model card says which set it came from.

### 1.5 What "accurate" therefore means here

**At n=183 since D-030** (21 accounts), everything below applies with less room than it had at
n=300: the same gates, wider intervals, and a feature budget of 18–20
([05](05-feature-extraction.md) §4.0). If the focused models cannot pass G1, the honest options
are to ship the exposure baseline plus content diagnostics (as §5 already says) or to ship the
wider-set model and label it as such — never to quietly widen the training set to make a gate
pass.

At n=300, with grouped CV by account (D-006), the realistic target is the one `docs/09`
already sets: **beat Baseline 1 (exposure only) by a meaningful margin**, and be
*calibrated* — when the tool says 70th percentile, outcomes should actually land near the
70th percentile. A well-calibrated model with honest intervals is far more useful to a real
person than a confident wrong number. **Calibration is the accuracy claim this project can
defend**, and §5 makes it a release gate.

---

## 2. Prediction contract

```
POST /predict
  video      : file upload (mp4/mov) OR url (YouTube, Instagram, or direct)
  platform   : "youtube" | "instagram" | "both"   (default "both")
  followers  : int, optional but strongly recommended
  market     : optional, one of the 8 regions; defaults to Global
→
  per platform:
    engagement_percentile      : int 0-100
    percentile_interval        : [lo, hi]        80% prediction interval
    engagement_rate_range      : [lo, hi]        (likes+comments)/followers
    est_likes_comments_range   : [lo, hi]        derived; only if followers given
    est_views_range            : [lo, hi] | null  YouTube only
    confidence                 : "high" | "moderate" | "low"
    out_of_distribution        : bool + reason
    top_drivers                : [{feature, direction, shap_value}] x5
  recommendation               : which platform suits this creative better, and why
```

The `recommendation` field is the project's actual contribution reaching a user: the
per-platform SHAP comparison from `docs/10` §2, expressed as a sentence.

---

## 3. Architecture

```
Flask app  (src/serve/app.py)
   │
   ├─ upload / URL  ──►  yt-dlp (if URL)  ──►  local mp4
   │
   ├─ feature extraction  ──►  REUSES src/features/ from Phase 5, unchanged
   │        (ffmpeg, PySceneDetect, CLIP, MediaPipe, EasyOCR,
   │         faster-whisper, librosa, transformers)
   │
   ├─ align to the trained feature schema  ──►  the ~30 pruned features (D-007)
   │
   ├─ models/  ──►  M2 (content + exposure), per platform, + calibrator
   │
   └─ TreeSHAP  ──►  top drivers + per-platform comparison
```

**Reuse, do not rewrite.** The inference path must call the *same* extraction code as
training. A second implementation would drift from the first, and the model would be
served features that differ subtly from the ones it learned — the classic
training/serving skew, and it fails silently. `src/features/` is written once, in Phase 5,
and imported here.

**Artefacts loaded at startup** (all written by Phase 9): the fitted model per platform,
the fitted scaler/encoder, the feature name list in training order, the calibrator, and a
`model_card.json` recording test performance, training date, and corpus composition.

**Latency.** Full multimodal extraction on one video takes roughly 30–90s on CPU, most of
it CLIP and Whisper. That is too slow for a blocking HTTP request: run extraction as a
background job and poll, with a progress indicator. Cache by file hash — the same video
re-submitted must not be re-extracted.

---

## 4. UI

Three screens. Keep it plain; the audience is a marketer, not a data scientist.

### 4.1 Input
Drag-and-drop or paste a link. Platform toggle (YouTube / Instagram / both). Follower count
field, with a visible note that the prediction is substantially weaker without it.

### 4.2 Result
- The headline: predicted percentile per platform, **shown as a band, never a bare number**.
- Derived likes+comments range, clearly labelled as derived from the rate.
- Views for YouTube; for Instagram, an explicit "Instagram does not publish this".
- **Which platform suits this creative better**, with the reason in one sentence.
- Top 5 drivers from SHAP, in plain words ("product appears in the first 2 seconds",
  "fast cutting", "no on-screen text"), each with direction.
- A model card link: how accurate this is, measured how, on what.

### 4.3 Honesty surfaces — not optional
- **Out-of-distribution banner** when follower count is far outside 8.8K–3.3M, when the
  video has no detectable brand/product content, or when it shows a Coca-Cola variant other
  than Zero Sugar (D-030 — the models were fitted on Zero Sugar videos only). Wording: what the
  model was trained on, and that this input is unlike it.
- **Confidence badge** driven by the prediction interval width, not by vibes.
- **"What this can't tell you"** — posting time, hashtags, paid promotion, and the
  algorithm's own state are not modelled and often dominate real outcomes.

---

## 5. Release gates — do not ship until all four pass

| Gate | Requirement | Why |
|---|---|---|
| **G1** | M2 beats Baseline 1 (exposure only) on held-out grouped CV | If content adds nothing, the tool is a follower-count calculator with extra steps |
| **G2** | Calibration curve within ±10 percentile points across deciles | The accuracy claim this project can actually defend (§1.5) |
| **G3** | Prediction intervals achieve their nominal coverage on held-out data | An interval that lies is worse than no interval |
| **G4** | Training/serving parity: features extracted by the service match the training pipeline bit-for-bit on 10 corpus videos | Silent skew is the most likely way this ships broken |

If G1 fails, **say so in the write-up and ship the tool as an exposure baseline plus content
diagnostics.** That is still a real result — it would corroborate the Frontiers finding —
and it is far better than shipping a content model that does not work.

**Outcome, 2026-10-02: G1 failed** on the pooled focus set - XGBoost M2 minus the reach-only baseline
-0.030 ROC-AUC (corrected 95% CI -0.234 to +0.174), and no pooled model above chance for unseen accounts
(D-045). The fallback above applies, as specified in D-046: base rate with honest intervals, video
diagnostics against the 192 Zero Sugar videos, and an Instagram-only content score (ROC-AUC 0.70,
exploratory) shown with its accuracy. G2-G4 still gate whatever the tool displays.

---

## 6. Scope boundary

In scope: prediction and explanation for a single video, both platforms, from public
signals available at post time.

Out of scope, and should be stated in the UI: posting-time optimisation, hashtag
recommendation, paid-promotion modelling, audience targeting, and any claim about revenue
or sales. None of these are measurable from this corpus.

---

## 7. Execution log

_Append dated entries as the service is built._

| Date | Action | Result |
|---|---|---|
| 2026-09-12 | Deliverable added to scope (D-017); this document written | Method specified; build begins after Phase 10 |
| 2026-10-02 | G1 failed (D-045); tool re-scoped to the pre-registered fallback (D-046) | Base rate + diagnostics + exploratory Instagram content score; no platform recommendation. Pooled models saved in `models/` stay for comparison, not for serving |
| 2026-10-02 | SHAP done (D-047 spec, D-048 results) | The tool's "drivers" may name only three features, from the Instagram logistic model: hashtags, share with talking, share of frames with a face. That model's probabilities barely move (80% of videos 0.45-0.56), so G2 (task 12.2) decides whether the Instagram score is shown as a probability at all |

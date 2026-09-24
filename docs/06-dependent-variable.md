# 06 — Dependent Variable

**Status:** Planned. Method specified; fill distributions once data exists.

This is the single most consequential file in the project. A defensible DV rescues an
imperfect model; an indefensible DV invalidates a perfect one.

---

## 1. The constraint that decides everything

| | YouTube Shorts | Instagram Reels |
|---|---|---|
| Views | ✅ Available via API | ⚠️ Unreliable — combined IG+FB for crossposts, insights own-account only |
| Likes | ✅ (can be hidden) | ✅ |
| Comments | ✅ (can be disabled) | ✅ |
| Shares | ❌ | ❌ Not public |
| Saves | ❌ | ❌ Own-account only |
| Followers/subs | ✅ | ✅ |

**Only likes, comments and follower count are reliably available on both platforms.** The
DV must be built from those three.

---

## 2. Definitions

### Primary — cross-platform comparable (D-005)

```
engagement_rate_follower = (like_count + comment_count) / followers
```

Used for **every** cross-platform test: H7, H9, RQ7, and all pooled models.

### Secondary — YouTube only

```
engagement_rate_view = (like_count + comment_count) / view_count
```

Higher-quality when available. Use for within-YouTube robustness checks. **Never** carry a
finding from this measure into a cross-platform claim.

### Why shares were dropped

The proposal specified `(Likes + Comments + Shares) / Views`. Shares are not public on
either platform. Retaining the term would mean either imputing zero (wrong) or dropping
Instagram (defeats the study). Documented in the methods as a data-availability
constraint.

---

## 3. Normalisation

Raw rates are not comparable across platforms, account sizes or years. Convert to
percentile rank within cells:

```
cell = platform × account_size_tier × year
```

with `account_size_tier` in {small <100k, medium 100k–1M, large >1M} followers.

With n=300 across ~36 possible cells, many cells will be thin. **Check cell sizes before
committing.** If cells fall below ~10, collapse — drop `year` first, then merge size
tiers. Record what was collapsed.

**Fallback if cells are too thin:** rank within platform only, and enter
`account_size_tier` and `year` as model covariates instead of as normalisation strata.
This is the more likely outcome at n=300 and is perfectly defensible.

### 3.1 The reference set under the Zero Sugar focus (D-030, decided 2026-09-23)

The analysis is now Zero Sugar only (183 usable videos), but **the percentile keeps its existing
reference**: each video is still ranked against every usable video of the same platform and
follower tier in the 300-video corpus, Zero Sugar or not. So `engagement_pct` reads "this video
outperformed x% of the brand's short-form output on that platform at that account size".

Decided by the researcher on 2026-09-23, after both options were laid out. The alternative -
ranking within Zero Sugar only - was rejected because it would leave **YouTube small+medium with
14 videos from 4 accounts**, where a rank moves in steps of about 7 percentile points; it would
change every percentile value, and it would take the 107 non-Zero-Sugar usable videos off a
comparable scale, which is what makes the robustness check in
[08](08-statistical-analysis.md) §7.1-7.6 comparable with the focused result. Keeping the
reference also means nothing had to be recomputed: the table was re-frozen for the new column
only ([08](08-statistical-analysis.md) §6, row dated 2026-09-23).

**Consequence to state in the thesis:** the yardstick includes videos that are not in the
analysis. That is a normalisation choice, not leakage — no outcome of an analysed video informs
its own features — but the percentile must be described in those words, never as "rank among
Zero Sugar videos".

---

## 4. Binary label

**Main:** median split on the normalised percentile within each cell. Retains all 300
observations, ~150 per class, no imbalance problem.

**Under the Zero Sugar focus (D-030, rule fixed 2026-09-23 before any outcome was looked at).**
The split stays at the 0.5 mark of the existing percentile (§3.1), so "high" keeps its meaning:
better than half of the brand's short-form output in that platform and size cell. Because the
focus set is a subset of what that percentile was computed over, **its own balance is not
guaranteed** — it could come out lopsided. That balance has deliberately not been looked at yet;
it is an engagement result, and it is reported at EDA ([07](07-eda.md) §1b, task 7.2).
**Pre-specified rule:** if the focus set's split is worse than 60/40, the modelling label is
taken at the focus set's own median percentile instead, that choice is reported as the
pre-specified fallback it is, and both versions are run so the difference is visible. The
continuous percentile is unaffected either way.

**Robustness:** top vs bottom tertile, middle discarded. Sharper contrast, n drops to
~200. Report both. If they disagree, that is a finding about the fragility of the
threshold — report it rather than picking the flattering one.

**Continuous form retained** for the regression and mixed-effects models in Phase 6.

---

## 5. Class imbalance

A median split gives balanced classes by construction, so imbalance handling is largely
moot for the main model. Where it does arise (tertile split, per-platform models):

- Use `class_weight='balanced'`.
- **Do not use SMOTE.** Interpolating between CLIP scores, optical-flow magnitudes and
  one-hot campaign types manufactures videos that could not exist, and it corrupts the
  SHAP analysis that is the point of the study.

---

## 6. Threats to validity — state these in the thesis

| Threat | Handling |
|---|---|
| **Age** — older videos accumulated more engagement | `video_age_days` as a control; 2016–2026 included, and likes/comments count only if read **≥7 days after posting** — younger posts are re-read, not dropped (D-019) |
| **Exposure** — engagement is algorithm-allocated, not purely earned | M0/M1/M2 nested design in [09](09-modelling.md) |
| **Snapshot** — counts are one moment in time | `collected_at` recorded; one-week drift measured on a 30-video sample |
| **Hidden counts** — YouTube uploaders can hide likes | Kept null and flagged; excluded from DV, not imputed |
| **Follower ≠ reach** — followers is a proxy for exposure, not a measure of it | Acknowledged as a limitation; the best available given API constraints |
| **Cross-posted duplicates** | `creative_id` clustering; paired sub-analysis (see [03](03-sampling-frame.md) §4) |

---

## 7. Distributions

**Filled 2026-09-15, re-run 2026-09-21** after the 7-day refresh of three Reels (2b.7) by
`python -m src.process.dependent_variable` →
`data/processed/dependent_variable.parquet` (300 rows, every row kept with a `dv_status`).

| Metric | YouTube | Instagram |
|---|---|---|
| n with a usable DV | 144 | **146** |
| Excluded: likes hidden | 4 | 1 |
| Excluded: comments disabled | 2 | 3 |
| Held back: read <7 days after posting | 0 | 0 (3 re-read 2026-09-21) |
| Median engagement_rate_follower | 0.0048% | 0.2699% |
| IQR | 0.0014% – 0.0296% | 0.1094% – 2.0302% |
| Skew | 9.13 | 8.29 |
| Zero-comment videos | 28 | 5 |
| Median followers | 4,820,000 | 369,198 |
| Median video_age_days (at read) | 86.3 | 254.2 |

The two platforms' raw rates differ by ~55x, driven by exposure base: 117 of 144 usable
YouTube Shorts come from one 4.82M-subscriber channel. This is why raw rates are never
compared across platforms and the percentile is used instead. Both distributions are heavily
right-skewed (skew 8–9), which the rank transform absorbs.

### Cell sizes after normalisation

| Scheme tried | Smallest cell | Cells under 10 |
|---|---|---|
| platform × size tier × year | 1 | 16 of 24 |
| platform × size tier | 9 | 1 of 6 |
| **platform × size tier, small+medium merged — used** | **27** | **0 of 4** |

| Cell | n | of which in the Zero Sugar focus (D-030) | Accounts in focus |
|---|---|---|---|
| instagram · large (>1M) | 45 | 32 | 4 |
| instagram · small+medium (≤1M) | 101 | 79 | 13 |
| youtube · large (>1M) | 117 | 58 | **1 channel** |
| youtube · small+medium (≤1M) | 27 | 14 | 4 |
| **Total usable** | **290** | **183** | **21** |

The focus column is counts only, added 2026-09-23; the ranks themselves are unchanged (§3.1).
The focus set's Zero Sugar label rests on a weakly reliable judgement on YouTube (16 of 25 repeat
answers agree, alpha 0.25; D-029), and it now decides inclusion — state that wherever these
counts appear.

**Cells collapsed:** `year` dropped from the strata (16 of 24 cells under 10); small and
medium tiers merged (YouTube medium alone had 9).
**Final normalisation scheme used:** percentile rank within platform × {large, small+medium};
`year` and `video_age_days` enter the models as covariates, per the §3 fallback.
**Binary labels:** median split 147 high / 143 low; tertile split keeps 193 (low + high).

**Refresh, 2026-09-21 (2b.7).** Three Reels first read at 1.5, 3.7 and 6.9 days old were
re-read with yt-dlp at 7.5, 9.7 and 16.6 days: likes 115->148, 1,758->1,864, 364->410;
comments 1->3, 3->3, 16->24. First readings are kept (`*_first_read` columns; raw responses
in `data/raw/refresh_20260921/`, log in `data/raw/metric_refreshes.csv`). Adding three rows
to the Instagram cells moved 100 other Instagram percentiles by at most 0.011 (median
0.004) - expected, since percentiles are ranks within the cell.

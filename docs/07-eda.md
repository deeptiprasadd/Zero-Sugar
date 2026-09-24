# 07 — Exploratory Data Analysis

**Status:** Planned. Notebook: `notebooks/eda.ipynb`. Figures: `reports/figures/`.

Covers the proposal's EDA 1–9, plus five diagnostics the literature survey showed are
needed. Every figure gets a one-line finding recorded in §3 — a plot with no written
finding has not been analysed.

---

## 1. Proposal EDA 1–9

**Scope from 2026-09-23 (D-030): every analysis below runs on the focus set** — the 183 usable
Zero Sugar videos (`in_focus & dv_status == "ok"`; Instagram 111 from 16 accounts, YouTube 72
from 5). Every figure's title carries its n in videos and accounts. The 107 usable videos that
are not Zero Sugar stay in the data and are shown only in clearly labelled robustness panels,
never mixed in. EDA 1 (distribution of videos) is run on both sets, since knowing what the focus
left out is part of describing it.

| # | Analysis | Note under the short-form design |
|---|---|---|
| 1 | Distribution of videos | By platform, market, language, account, year, sampling tier |
| 2 | Engagement distribution | Both DV forms; expect heavy right skew — log for plotting |
| 3 | Video duration | **Range is now narrow** (both platforms ≤180s). H1 is a within-short-form test |
| 4 | Product visibility vs engagement | `product_visible_frac` split at median and as a continuous scatter |
| 5 | Human / influencer presence | None / ordinary / influencer / celebrity — check cell sizes, may need collapsing |
| 6 | Emotional content | Remember emotion is measured post-translation ([04](04-multilingual-pipeline.md) §4) |
| 7 | Caption and text | Prefer invariant features; normalise caption length within language |
| 8 | YouTube vs Instagram | **Use the follower-normalised DV only** (D-005). **Pre-registered: §1a (2026-09-22), rewritten for the focused design in §1b (D-030)** |
| 9 | Correlation / association | Full matrix, then per-block |

### 1a. EDA 8 — pre-registered (D-029, 2026-09-22) — **superseded by §1b**

Left exactly as registered. It is now the plan for the wider 300-video robustness set; the
focused design (Zero Sugar only, D-030) is registered in §1b, and what changed is recorded in
[08](08-statistical-analysis.md) §7.8.

Written before any platform comparison was run; what had already been seen is disclosed in
[08](08-statistical-analysis.md) section 7.2. EDA 8 is descriptive: it makes no claim about
platform, it shows what the platform comparison is made of.

Runs on the frozen labels only ([08](08-statistical-analysis.md) section 7.4). In this order:

1. **Composition table first**, before any engagement value is shown: videos **and accounts** in
   every cell of platform x `is_zero_sugar` x `selection` (hand_picked | systematic), and
   platform x follower tier. Cells under 20 videos or 3 accounts are marked.
2. **How each Zero Sugar label was decided**, by platform: counts of `zs_label_method` (text /
   researcher_curated / clip_then_researcher).
3. **Figure:** distribution of `log10(engagement_rate_follower)` by platform, one panel per
   `is_zero_sugar` value, hand-picked Reels drawn in a distinct marker, the global YouTube
   channel in another. Per-panel n (videos, accounts) printed on the panel.
4. **Written finding (section 3, row 8):** states composition before any difference, and uses no
   word stronger than "differs descriptively". The inferential answer is model (a) of
   [08](08-statistical-analysis.md) section 7.5 and the verdict rules of section 7.6.

Not in EDA 8: any test, any p-value, any statement that one platform "performs better".

### 1b. EDA 8 — focused design, Zero Sugar only (registered 2026-09-23, D-030)

Written before any platform comparison was run. Replaces §1a for the analysis that is reported;
§1a still describes the robustness set. EDA 8 stays descriptive: it makes no claim about
platform, it shows what the comparison is made of. Runs on the frozen table only
([08](08-statistical-analysis.md) §6, row dated 2026-09-23). In this order:

1. **Composition table first**, before any engagement value is shown — the focus set
   (`in_focus & dv_status == "ok"`, **183 videos, 21 accounts**): videos **and accounts** in every
   cell of platform × `selection` and platform × follower tier. Cells under 20 videos or 3
   accounts are marked; on today's counts that marks Instagram systematic (6 videos, 5 accounts)
   and YouTube small+medium (14 videos, 4 accounts), and notes that YouTube large is 58 videos
   from **one** channel.
2. **How each Zero Sugar label was decided**, by platform: counts of `zs_label_method` (text /
   researcher_curated / researcher_visual_check), stated with the label's repeat agreement — 16
   of 25, alpha 0.25 (D-029). Under D-030 this label decides inclusion, so this table says who
   is in the study and on what evidence.
3. **Figure:** distribution of `log10(engagement_rate_follower)` by platform for the focus set,
   hand-picked Reels in a distinct marker, the global YouTube channel in another, per-panel n
   (videos, accounts) printed. One extra panel, clearly labelled as the robustness set, shows the
   107 usable rows that are not Zero Sugar — never mixed into the focus panel.
4. **Written finding (§3, row 8):** states composition before any difference, uses no word
   stronger than "differs descriptively", and states the selection caveat of
   [08](08-statistical-analysis.md) §7.9.3(c) — every hand-picked video is an Instagram Reel, so
   platform and selection cannot be separated in the focused design. The inferential answer is
   model (a) of §7.9.3 under the verdict rules of §7.9.4.

Not in EDA 8: any test, any p-value, any statement that one platform "performs better".

---

## 2. Added diagnostics

These are not optional — each one guards a decision made later.

| # | Diagnostic | Guards |
|---|---|---|
| A | **Videos per account**, bar chart | Justifies grouped CV (D-006). If one account holds 40% of the corpus, say so here. |
| B | **Engagement vs `video_age_days`**, scatter + LOESS | Shows how much age drives raw counts |
| C | **Correlation heatmap + VIF** | Drives the pruning in [05](05-feature-extraction.md) §4 |
| D | **Missingness matrix** | Hidden likes, absent views, failed extractions |
| E | **Sampling-tier balance by platform** | If YouTube is 90% brand and Instagram 60% creator, the platform comparison is partly a creator comparison |
| F | **Cross-posted pair count** | Determines whether the paired sub-analysis is viable (needs ≥20 pairs) |
| G | **Market × platform cell sizes** | Confirms quotas held; flags collinearity between market and account |

---

## 3. Findings log

_One line per figure. Fill as the analysis runs._

| # | Figure | Finding |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
| 6 | | |
| 7 | | |
| 8 | | |
| 9 | | |
| A | | |
| B | | |
| C | | |
| D | | |
| E | | |
| F | | |
| G | | |

---

## 4. Decisions coming out of EDA

_EDA should change the plan. Record what it changed._

| Decision | Driven by | Outcome |
|---|---|---|
| Features dropped for collinearity | Diagnostic C | |
| Categories collapsed for thin cells | EDA 5, Diagnostic G | |
| Normalisation scheme confirmed or revised | Diagnostic G | |
| Paired sub-analysis viable? | Diagnostic F | |
| Accounts excluded as outliers | Diagnostic A | |

---

## 5. Plotting conventions

- Log scale for all raw engagement counts.
- Colour by platform consistently across every figure (fix the mapping once).
- Show n in every subplot title — with thin cells this matters constantly.
- Box plots must show individual points at this sample size; a box over 12 observations
  hides more than it shows.
- Every figure saved to `reports/figures/` at 300 dpi with a descriptive filename.

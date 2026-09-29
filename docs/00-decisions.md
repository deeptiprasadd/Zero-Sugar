# Decision Log

Append-only. Each entry records what was decided, why, and what it rules out. When a
decision is reversed, add a new entry that supersedes it — do not edit history.

Format: `D-nnn` · date · decision · rationale · consequences.

---

## D-001 — Short-form only: YouTube Shorts vs Instagram Reels

**Date:** 2026-09-09
**Decision:** The corpus is restricted to vertical short-form video. Long-form YouTube
content is excluded.

**Rationale:** Two reasons, and the second is the stronger one.

1. Short-form is where brand video reach currently concentrates.
2. It fixes a real methodological flaw in the original proposal. Comparing long-form
   YouTube against Reels confounds platform with format — any "platform difference" would
   partly be a format difference. Matched format, matched duration ceiling, and matched
   consumption context make RQ7, H7 and H9 answerable instead of confounded.

**Consequences:**
- RQ7 / H7 / H9 become clean tests of platform, not of format.
- Duration variance narrows (both platforms cap near 3 minutes), which weakens the
  test of H1. H1 must now be read as "duration *within short form*", stated explicitly.
- Rules out the EnTube-style long-form comparison and the Munaro finding as a direct
  prior — Munaro's medium/long videos are outside our range.

---

## D-002 — Corpus target: 150 per platform

**Date:** 2026-09-09
**Decision:** Minimum 150 YouTube Shorts and 150 Instagram Reels. 300 total.

**Rationale:** User-set target. Balanced across platforms so platform comparisons are not
driven by unequal cell sizes.

**Consequences:**
- Small relative to comparable studies (9,600–23,700 videos). Modelling must be
  correspondingly conservative — see D-007.
- Balanced design means no reweighting needed for the platform comparison.
- 300 with a median split gives ~150 per class, which is enough for a tree ensemble with
  a capped feature set but not for a deep fusion model.

---

## D-003 — Deliberately multilingual and multi-market

**Date:** 2026-09-09
**Decision:** Videos may be in any language. Language and market are recorded as
features, and quotas are set per market rather than letting one market dominate.

**Rationale:** User requirement, and it is analytically useful — multilingual sampling
buys predictor variance, which is exactly what a 300-row dataset most lacks. Coca-Cola
also runs genuinely different creative per market, so this widens the range of the
independent variables.

**Consequences:**
- ASR, OCR and sentiment must all be multilingual. See
  [04-multilingual-pipeline.md](04-multilingual-pipeline.md).
- `language` and `market` become control variables, not just descriptors.
- Emotion classification is weaker outside English. Recorded as a limitation.
- Adds a confound: market correlates with audience size and platform norms. Must be
  controlled alongside account.

---

## D-004 — Instagram acquisition: Apify primary, Business Discovery as validator

**Date:** 2026-09-09
**Decision:** Collect Reels via the Apify Instagram Reel Scraper. Independently query the
official Business Discovery API on the overlapping subset and report agreement on like
and comment counts.

**Rationale:** Hashtag Search is unusable (24-hour window — see
[01](01-instagram-acquisition.md)). Business Discovery alone gives no archive depth and no
video files. Apify gives metadata plus the direct video URL in one call. The official
cross-check converts "I scraped Instagram" into a measurement-validation exercise.

**Consequences:**
- Apify use violates Instagram ToS. Must be disclosed in methods and cleared with the
  guide before collection starts. **Blocking item.**
- ~~Requires a small paid budget (free tier covers the pilot).~~ **Corrected 2026-09-11:**
  no budget is required. The Apify account is on the FREE plan (`isPaying: false`, no card
  attached) with a $5.00 monthly usage allowance, verified against `GET /v2/users/me/limits`.
  $0.81 of it was consumed by all work to date, and the cycle resets 2026-10-08. Hitting the
  ceiling stops runs until reset; it never bills. Cost is a rate limit here, not an expense.
- Produces a reportable data-quality statistic instead of an unexamined assumption.

---

## D-005 — Cross-platform DV is follower-normalised on both sides

**Date:** 2026-09-09
**Decision:** For any test that compares platforms, engagement is
`(likes + comments) / followers`. View-normalised engagement is retained as a
**YouTube-only** secondary measure.

**Rationale:** YouTube exposes Shorts view counts; Instagram does not expose Reel views
reliably (Meta now returns combined IG+Facebook views for crossposted video, and Reel
insights are own-account only). Using views on one side and followers on the other would
make H7 and H9 measure the metric difference rather than the platform difference.

**Consequences:**
- Shares are dropped from the formula entirely — not public on Instagram.
- H7 and H9 rest on a like-for-like measure.
- Any YouTube-only finding using view-normalised engagement must be labelled as such and
  not carried into cross-platform claims.

---

## D-006 — Grouped cross-validation by account

**Date:** 2026-09-09
**Decision:** `StratifiedGroupKFold` grouped by account/channel. Never a plain random
split.

**Rationale:** 300 videos come from roughly 20 accounts. A random split puts videos from
the same account in both train and test, leaking account identity and inflating every
metric.

**Consequences:**
- Reported accuracy will be lower than a naive split would suggest. This is correct, not
  a regression.
- Accounts with very few videos may fall entirely into one fold. Check fold balance.

---

## D-007 — Feature budget capped at ~30

**Date:** 2026-09-09
**Decision:** At most 25–30 features enter the models. Blocks A–E are pruned before
modelling, not after.

**Rationale:** n≈300. The full Block A–E specification implies 60–80 features. That ratio
overfits regardless of regularisation, and it makes SHAP unstable — which defeats the
purpose of the study.

**Consequences:**
- Pruning rules must be pre-registered in [05](05-feature-extraction.md) so selection is
  not driven by the outcome: drop by within-block correlation (|r| > 0.85), drop
  near-constant features, drop annotation constructs failing reliability (α < 0.67).
- Pruning happens on training folds only where it is data-dependent.
- MLP is expected to underperform XGBoost at this size. That is a finding to report, not
  a failure to hide.

---

## D-008 — Validation by cross-source agreement, not by official API

**Date:** 2026-09-09
**Supersedes:** the validation half of D-004. The Apify-as-primary-collector half stands.

**Decision:** Validate scraped engagement counts by running **two independent Apify actors**
(different authors, different scraping implementations) over the same Reels and reporting
agreement. The official Business Discovery cross-check becomes optional.

**Rationale:** Business Discovery requires an Instagram Business/Creator account linked to a
Facebook Page, plus a Meta developer app. The researcher does not have an Instagram account.
Creating that chain is free and takes 30–45 minutes, but it is friction on the critical path
and it is not the only way to get a reliability estimate.

Manual browser spot-checking — the obvious alternative — is **not viable**: Instagram's
logged-out web experience now walls Reels behind a sign-in prompt almost immediately.

**Consequences:**
- No Instagram account is needed anywhere in the pipeline. Confirmed: Apify actors
  advertised as cookieless return follower counts, captions, likes, comments and video URLs
  for public profiles without login.
- The validation statistic becomes inter-source reliability rather than
  agreement-with-official-source. Weaker, but honest and reportable.
- If the researcher later chooses to create the Business account chain, official validation
  can be added as a strengthening step. Recorded as open decision O-05.
- **Third-party "Reels viewer" websites are not an acceptable measurement source** and some
  solicit Instagram passwords. Not to be used.

---

## D-009 — Creator content in scope; brand accounts plus sponsored creators

**Date:** 2026-09-09
**Resolves:** O-04.

**Decision:** The frame covers official Coca-Cola regional brand accounts **and** sponsored
creator/influencer content featuring Zero Sugar.

**Rationale:** Two reasons. It makes 150 per platform realistically reachable, and it is
required for H4 (influencer/celebrity effect) to be testable at all — a brand-account-only
corpus has almost no variance on that predictor.

**Consequences:**
- `sampling_tier` must be logged per video and controlled in every model.
- Tier distribution must be kept comparable across platforms. If YouTube ends up 90%
  brand-account and Instagram 60% creator, the platform comparison becomes partly a
  creator-type comparison. Tracked as an EDA diagnostic.
- Creator handles are derived **after** the brand pull, by extracting tagged accounts and
  paid-partnership mentions from brand content, then confirming manually. Not hunted for by
  hand up front.

---

## D-010 — Ethics handled by policy check and disclosure, not by permission request

**Date:** 2026-09-09
**Supersedes:** O-01 as an approval gate.

**Decision:** No permission request is made. Instead: (a) read the institution's own research
data / ethics policy to establish whether public social-media collection requires review, and
(b) describe the collection method factually in the methods chapter. The Instagram official
API chain (O-05) is additionally recommended as a hedge, since it requires nobody's approval.

**Rationale:** The researcher does not wish to involve the supervisor, and on inspection the
framing was wrong anyway — most institutions exempt already-public data from human-subjects
review, and that can be established by reading the policy rather than by asking. Published
work in this area routinely states the collection tool with no ethics statement.

**Consequences:**
- Instagram collection is no longer gated on an approval conversation.
- **The methods chapter must state how data was actually obtained.** Not seeking permission is
  acceptable; misrepresenting the method is not, and it is the kind of thing that surfaces
  badly at a viva. This is the one non-negotiable part of this decision.
- If the institutional policy *does* mandate review, that obligation stands regardless of
  preference and must be followed. Establishing this early is the point of the check.
- O-05 is upgraded from optional to recommended: an official-API route removes the ToS
  question from the critical path entirely.

---

## D-011 — Sampling frame traced from Coca-Cola's own regional sites, not guessed

**Date:** 2026-09-09
**Status:** Accepted
**Resolves:** the verification half of plan Step 2.

**Decision:** Every account in the frame is established by following the social links published
in the footer of the corresponding `coca-cola.com/<market>` site, then resolving each YouTube
URL to its permanent `UC...` channel id. Handles are never guessed from the brand name.

**Rationale:** Guessing fails, and fails silently. `youtube.com/@CocaColaIndia` — the handle any
reasonable person would try first — belongs to an unrelated channel named "Play Boy"
(`UCm8oDUKg1PeoFUZl0LA4UAA`). Collecting from it would have produced a full market's worth of
plausible-looking, entirely invalid data, most likely undetected until the analysis stage.

Channel ids rather than handles are stored because handles are user-changeable and `/user/` and
`/c/` URLs are legacy forms; the `UC...` id is immutable.

**Findings that change the design:**
- **India and Indonesia have no separate YouTube channel.** The India site's YouTube link is a
  *playlist* (`PLCIVZWq1FAwfcgL6q4drjQJaLoEL3mSIK`) owned by the global channel; the Indonesia
  site's YouTube icon points at the global channel outright, and `@cocacolaindonesia` 404s.
  Both markets do run separate Instagram accounts. The "one channel per market" assumption in
  `03-sampling-frame.md` is therefore false for 2 of 6 markets. Recorded as O-06.
- **The Mexico channel is an industry body**, "Industria Mexicana de Coca-Cola"
  (`UCO02nrsyRS6bzxkxDbVhehQ`) — the bottlers' association, not consumer marketing. Its
  Instagram counterpart `somoscocacola` is likely corporate/employer branding. Flagged
  `verified=check`; needs a human look before inclusion. Recorded as O-07.

**Consequences:**
- 5 of 7 rows carry a usable YouTube channel id; YouTube collection can begin on those.
- Market coverage on YouTube is structurally narrower than on Instagram. This is a property of
  how Coca-Cola organises its channels, not a collection failure, and belongs in the methods
  chapter as a stated limitation.

---

## D-012 - Collect what exists; do not prune the frame for symmetry

**Date:** 2026-09-09
**Status:** Accepted
**Resolves:** O-06, O-07.

**Decision:** Every verified account stays in the frame. India and Indonesia contribute
Instagram only, because they genuinely have no YouTube channel. The Mexico channel stays
in despite being an industry body rather than a consumer brand channel.

**Rationale (researcher's, 2026-09-09):** the object of study is what drives engagement on
short-form video, not a comparison between regions. Market is a covariate here, not the
treatment. Discarding real, verified data to make the panel look balanced would shrink the
corpus toward the 150-per-platform floor for no analytical gain.

**Consequences:**
- YouTube covers 5 of 7 markets, Instagram 7 of 7. Coverage is unbalanced **by
  construction, not by attrition** - it reflects how Coca-Cola actually organises its
  channels. State it in the methods chapter as such.
- **Market cannot be treated as a clean experimental factor** and must not be read as one.
  Use it as a control/nuisance term. Any market-level claim needs a caveat about coverage.
- `channel_type` is added to `docs/accounts.csv` (`brand` | `industry_body`) so the Mexico
  channel's different content mix can be controlled for, or checked as a robustness split,
  rather than silently averaged in. Keeping the data and marking it preserves the option;
  dropping it would not.
- If Zero Sugar Reels fall short of 150, the escalation tiers in `01` section 5 apply as
  before - this decision widens the frame rather than narrowing it.

---

**Update 2026-09-09, after the Instagram pilot:** Indonesia turns out to contribute
nothing on *either* platform — `cocacola_id` is age-restricted and returns zero Reels to a
cookieless scraper. D-012's reasoning is unaffected (keep what exists, do not prune for
symmetry), but Indonesia is now an empty row rather than an Instagram-only one. Recorded
as O-08. India, by contrast, is the pilot's richest market: 5 brand Reels plus 5
collaborator Reels from four creators.

---

## D-013 - Zero Sugar screening measured: the n=150-per-platform target is not reachable on that variant

**Date:** 2026-09-09
**Status:** Evidence recorded. **Forces a decision on O-02.**

**What was measured.** `src/screen/zero_sugar.py` screens caption, hashtags, alt text,
audio name (Instagram) and title, description, tags, transcript (YouTube) against curated
per-language Zero Sugar vocabularies (en, es, pt, ar, th, id, hi). Every row gets one of
three verdicts: `hit`, `unnamed` (Coca-Cola present, variant not stated - the video must
decide), `off_brand`.

| Corpus | n | hit | rate |
|---|---|---|---|
| Instagram, 7 accounts, most recent 10 each | 60 | 0 | 0.0% |
| Instagram, 3 accounts, 3 years (2023-2026) | 180 | 4 | **2.2%** |
| YouTube Shorts, global channel, 60 enumerated | 12 | 6 | 50.0% *(artefact - see below)* |
| YouTube Shorts, global channel, 300 enumerated | 149 | 6 | **4.0%** |

**The 50% figure was a small-sample artefact and is withdrawn.** The same six videos (a
Bundesliga tie-in and the "Scream" football ads, several of them multi-language cuts of
one another) sat in the first 60 uploads. Widening to 300 uploads found no further hits:
6 remained 6 while the denominator grew twelvefold. An earlier projection of ~207
reachable Zero Sugar Shorts was derived from that artefact and is wrong by roughly an
order of magnitude; the honest figure is ~21 on the global channel, perhaps ~40 across all
five.

**Visual check.** Ten Reels were downloaded and frames inspected directly (three frames
each, spread across markets and both tiers). Every identifiable product was **classic red**
Coca-Cola - red cans, red bottles, red FIFA cans, red delivery trucks. Zero Sugar: 0 of 10.
The visual channel does not rescue the text rate in this sample.

**Temporal finding.** Instagram Zero Sugar content is a **2024 campaign that stopped**:
all 4 hits fall in 2024, on the global account only. 2023: 0. 2025: 0. 2026: 0 of 139.

**What this implies arithmetically.** At the measured rates, 150 Zero Sugar items would
require enumerating roughly **6,800 Reels** and **3,750 Shorts**. The five YouTube channels
hold 2,079 uploads in total; the Instagram accounts hold far fewer Reels than 6,800. The
target is therefore not reachable on Zero Sugar alone from Coca-Cola's own accounts - not
by text screening, and on present evidence not by visual screening either.

**This is not a collection failure.** The collectors work; the pilots were clean. Coca-Cola
simply does not post Zero Sugar at that volume. Better established now, at a cost of $0.15,
than in Week 6.

**Consequences:** O-02 moves from "decide after pilot counts" to **decide now** - it gates
how wide collection goes and therefore everything downstream.

---

## D-014 - Corpus is the Coca-Cola brand family; variant becomes a feature

**Date:** 2026-09-11
**Status:** Accepted
**Resolves:** O-02.

**Decision:** Collect Coca-Cola short-form video across the brand family and record which
**variant** each item names (`zero_sugar` | `diet_light` | `original` | `flavour` |
`multi` | `unnamed` | `off_brand`) as a column. Zero Sugar stays fully in scope - it is
measured rather than used to filter the sample.

**Rationale:** D-013 measured Zero Sugar at 2.2% on Instagram and 4.0% on YouTube Shorts,
which puts n=150 on that variant out of reach from Coca-Cola's own accounts. The research
question is what drives engagement on short-form brand video; variant is a predictor
within that question, not the sampling criterion. This is the same reasoning the
researcher applied to market in D-012.

**What this preserves:** the n=150-per-platform target, the cross-platform comparison, and
Zero Sugar itself - which becomes a testable effect (does naming Zero Sugar change
engagement?) instead of a constraint that shrinks the corpus to ~20-40 rows.

**Consequences:**
- `src/screen/zero_sugar.py` gains `variant`, `variant_named` and `is_zero_sugar`
  columns alongside the original `zs_*` screening columns.
- **`unnamed` will be the majority tag and must not be silently read as `original`.** Most
  brand posts show the product without naming the variant. A ten-Reel frame check (D-013)
  found those to be classic red, but ten frames cannot justify relabelling thousands of
  rows. Any analysis that turns on original-vs-zero needs the visual pass first; any that
  does not can use `is_zero_sugar` as-is.
- The methods chapter must state that variant was established from text where stated and
  left unresolved otherwise. Reporting `unnamed` as `original` would be a fabricated
  measurement.
- Collection order set by the researcher: **YouTube Shorts first**, all five channels.
  Instagram waits for an account list the researcher will supply.

---

## D-015 - Instagram sampling frame: 41 researcher-supplied accounts

**Date:** 2026-09-11
**Status:** Accepted
**Resolves:** O-09. Supersedes the drafted 7-handle Instagram frame in `docs/accounts.csv`
for the Instagram arm. `docs/accounts.csv` remains the authority for the YouTube arm.

**Decision:** The Instagram arm collects from the 41 accounts listed in
`docs/accounts_instagram.csv`.

**Provenance, and how it differs from D-011.** 39 of the 41 came from the researcher's own
Instagram in-app search for "coca cola" under the Accounts tab, captured 2026-09-11. That is
a weaker provenance standard than D-011's "traced from Coca-Cola's own regional site
footers" - but it is not guessing, which is what D-011 actually forbids. Every retained
handle carried Instagram's blue verified badge. The two exceptions strengthen rather than
weaken the frame: `cocacola_br` and `cocacolamiddleeast` were *not* in the search results
and were restored from the official site footers, i.e. at full D-011 provenance.

**`cocacola_civ` dropped.** Coca-Cola Cote d'Ivoire was the one account in the search
results with no verified badge and no follower count displayed. That is the exact profile
that made `youtube.com/@CocaColaIndia` a trap. Researcher decision: drop it. Cote d'Ivoire
is now an empty row, like Indonesia may be (O-08).

**Brazil and MENA restored.** Neither appeared in the search results, but both have YouTube
channels already in the corpus (17 and 8 Shorts). Dropping them would have left those two
markets on one platform only, making the D-005 cross-platform comparison impossible for
them. Researcher decision: add both.

**Six accounts are not market accounts.** Kept and marked in an `account_type` column
rather than pruned, following D-012's reasoning exactly:

| Handle | `account_type` | What it actually is |
|---|---|---|
| `cocacola` | `brand_global` | Global master account |
| `cocacolaeurope` | `brand_region` | Region, not a country |
| `cocacola_flow` | `event` | Flow Fest music festival, Mexico |
| `cocacolamusicexperience` | `event` | Music festival, Spain |
| `cocacolaarena` | `venue` | Coca-Cola Arena, Dubai |
| `cocacola_coliseum` | `venue` | Coca-Cola Coliseum, Toronto |
| `cocacolafutbol` | `sponsorship` | Football sponsorship property |
| `cocacolafemsa_panama` | `bottler` | FEMSA the bottler, not the brand |

Venue and event accounts post crowd and lineup content rather than product advertising, so
`account_type` is expected to matter in modelling. It must be available as a covariate.
This is the same call as `channel_type=industry_body` for `somoscocacola` under D-012.

**Consequences:**
- Frame goes from 7 handles to 41; ceiling at `--limit 60` is 2,460 Reels, against the 60
  Reels of the pilot. Trap 1 - small samples lie about rates - is materially reduced.
- **The variant screener does not cover 6 of the 41 markets' languages.** `ZERO_TERMS` in
  `src/screen/zero_sugar.py` covers en/es/pt/ar/th/id/hi. Korea, Turkiye, Uzbekistan,
  Kyrgyzstan, Azerbaijan and Israel post in languages with no term list. Their Reels will
  tag `unnamed` whether or not they show Zero Sugar - a *systematic* miss by market, not
  random noise. Either extend `ZERO_TERMS` or report variant coverage per market and
  exclude those markets from any original-vs-zero test. Do not read their `unnamed` as
  evidence of anything (trap 5).
- `cocacola_id` stays in the frame despite O-08. It cost nothing to retry and the run
  reports the age-gate loudly as an error record rather than silently.

---

## D-016 - Collection is incremental and zero-spend; raw JSON is the corpus of record

**Date:** 2026-09-11
**Status:** Accepted

**Decision:** The canonical Instagram parquet is *rebuilt* from every saved raw actor
response by `src/collect/merge_instagram.py`, never written directly by a collection run.
Collection runs write to a dated `--out`; the merge tool folds them in. The project is to
be completed without spending money, and without depending on the free allowance.

**What forced this.** `src/collect/instagram.py:744` writes the parquet with a plain
`df.to_parquet(...)` and never reads the existing file. There is no append and no
cross-run dedupe - `drop_duplicates(subset="shortcode")` at `:553` operates within one
run's items only. Each run therefore *replaced* the corpus. The 2026-09-09 run
`...jqOx3SUlWp6FvpVnf...` returned 180 Reels, 150 of them new, and all were discarded by
the next run. **The parquet held 60 rows while the raw directory held 319 unique Reels.**
The data had been collected and then thrown away.

**Why raw JSON is the corpus of record.** Design note 1 in `instagram.py` already writes
raw responses before parsing, for provenance. That habit turned out to be worth 259 Reels:
because the JSON survived, nothing had to be re-fetched. On a free-tier account the
cheapest Reel is one already paid for.

**Result - the entire Instagram arm, for $0.00:**

| | |
|---|---|
| Merged Reels | **319** (was 60 in the parquet) |
| Markets / regions | 38 / 8, **0 unmapped** |
| Followers resolved offline | **319 / 319** from 99 cached profile records |
| Instagram corpus | **150 selected, 8 Zero Sugar** |
| Apify spend for all of it | **$0.00**, allowance untouched at $3.72 |

**Consequences:**
- Never point a collection run at `data/raw/instagram_reels.parquet`. Use a dated `--out`
  then `python -m src.collect.merge_instagram`. `--dry-run` is not a substitute: it takes
  one file and also overwrites (`:708`).
- The merge tool refuses to write if the existing parquet holds rows absent from the raw
  runs, so it cannot itself cause the loss it was built to repair.
- `region` added to both account frames. **Market-level analysis is not credible here** -
  of 38 markets only 6 have n>=10 and 29 have n<=3. Analyse and stratify on `region`, and
  report per-cell n.
- `account_lookup()` falls back from `account_type` to `channel_type`, keeping
  `somoscocacola` tagged `industry_body` as D-012 requires rather than blank.
- **Video download is free.** Apify's `video_url` values expire (verified: HTTP 403), but
  `yt-dlp` fetches Instagram permalinks logged-out - 6 of 6 tested across six regions.
  The docs/01 section 0 warning about logged-out browsing does not extend to `yt-dlp`.

**Accepted limitation:** Zero Sugar is n=8 (2.5%) on Instagram. This *confirms* D-013's
2.2% on a 5x wider denominator, but cannot support a Zero-Sugar-effect test on this arm.
Spending would not fix it - at 2.5%, n=30 needs ~1,200 more Reels. Test variant on the
YouTube arm (n=25) and pooled (n=33); let Instagram carry market, format and tier
variation. This is D-014 working as intended, not a failure of it.

---

## D-017 - The deliverable is a prediction service, not a report

**Date:** 2026-09-12
**Status:** Accepted
**Specified in:** [11-prediction-service.md](11-prediction-service.md)

**Decision:** The project ends in a **Flask web tool**: submit a video file or link, get a
prediction of how it would perform on YouTube Shorts and on Instagram Reels, with an
explanation of what drove the prediction and which platform suits the creative better.
Phases 5-10 are now means to that end rather than the end itself.

**Rationale (researcher's, 2026-09-12):** the work should help people decide what to post
and where. A thesis chapter does not do that; a working tool does. This also gives the
per-platform SHAP comparison (`docs/10` §2) a concrete consumer - it becomes a sentence a
marketer can act on rather than a figure in an appendix.

**What this does not change:** the corpus, the DV, the models, or the analysis. The tool
serves the same M2 model the thesis reports. If the tool and the chapter ever disagree,
the chapter is wrong - they must be the same artefact.

**Four constraints the tool must respect.** These come from decisions already made and are
not negotiable without revisiting them:

1. **The DV is a percentile rank (D-005, `docs/06` §3), not a like count.** Absolute
   figures are *derived* (`rate x followers`) and must be shown as ranges, labelled as
   derived. A point estimate would be false precision.
2. **Exposure dominates content.** Baseline 1 is mandatory in `docs/09` §1 for this reason.
   **So the UI must ask for follower count** - a video on its own is missing the strongest
   predictor, and a content-only prediction has to be labelled the weaker mode.
3. **Reach is YouTube-only.** Instagram does not publish reliable Reel views (`docs/06`
   §1). The UI says so rather than inventing a number.
4. **Training data is one brand**, 8.8K-3.3M followers (D-014). Predictions for small or
   non-brand accounts are out of distribution and must be flagged in the interface.

**On "very accurate".** At n=300 with grouped CV (D-006), the defensible accuracy claim is
**calibration**, not precision: when the tool says 70th percentile, outcomes should land
near the 70th percentile, with prediction intervals that achieve their nominal coverage.
`docs/11` §5 turns this into four release gates. **If content fails to beat the exposure
baseline (gate G1), ship the tool as an exposure baseline plus content diagnostics and
report that** - it would corroborate the Frontiers 2026 finding and is a real result. A
confident wrong number sent to someone making a decision is the worst outcome available
here.

**Consequences:**
- New Phase 12 in the project to-do list; `flask` added to `requirements.txt`.
- **Inference must import the Phase 5 extraction code, never reimplement it.** A second
  implementation drifts and produces training/serving skew, which fails silently. Gate G4
  tests for it.
- Phase 9 must now persist artefacts for serving: fitted model per platform, scaler and
  encoders, feature order, calibrator, and a `model_card.json`.
- Extraction takes ~30-90s per video, so the service needs background jobs and a cache
  keyed on file hash, not a blocking request.

---

## D-018 - Researcher-curated Zero Sugar Reels enter the Instagram corpus

**Date:** 2026-09-15
**Status:** Accepted (researcher's decision); corpus rebuild pending
**Supersedes:** D-016's accepted limitation "Zero Sugar is n=8 on Instagram", and TODO
standing rule 5.

**Decision:** The Instagram corpus becomes every usable Reel from the researcher's
hand-curated Zero Sugar list, filled to n=150 with regular Coca-Cola Reels from the 319
already collected. The list is `docs/curated_zero_sugar_reels.csv`: 118 unique links
(119 pasted, one twice) saved on 2026-09-13 from 13 pages - India, global `cocacola`,
Turkiye, Malaysia, Brazil, Chile, Korea, Europe, Costa Rica, Indonesia, Thailand, Kenya,
Singapore. Content spans ads, concert campaigns, product close-ups, influencer brand
deals and co-branded cans (FIFA, Star Wars, celebrity concerts), across languages.

**Why this is better evidence than the screener.** Text cannot see a can. Six curated
Reels were already in the corpus; the screener tagged 2 `zero_sugar` and 4 `unnamed`. The
researcher's label is a *visual* judgement, which is the pass D-014 said `unnamed` needs.
n=6 is too small to quote as a recall rate (trap 1) - but it shows the direction.

**Consequences:**
1. **Deliberate, verified selection - not random, by design.** The researcher states
   (2026-09-15) that every Reel on the list was checked individually and each one shows
   Coke Zero Sugar. So the *label* is a confirmed visual judgement, not an estimate. The
   methods chapter should describe it as purposive selection by manual review of each
   page's Reels. The one thing still to state precisely there is coverage: whether every
   Zero Sugar Reel on each page was saved, or a subset. **Answered 2026-09-15: most, not
   all - the Zero Sugar Reels readily visible on each page.** So the list is a
   researcher-verified *subset*, not a census, and plausibly tilted toward the Reels
   Instagram surfaces most (recent, pinned, popular). State it that way in the methods,
   and do not generalise a Zero Sugar engagement effect beyond visible content without
   the comparison below. As a check either way, compare curated
   Zero Sugar against the screener-found Zero Sugar Reels already collected.
2. **The platforms no longer match in make-up.** Instagram will be mostly Zero Sugar;
   YouTube is 16.7%. Variant must be controlled in any cross-platform comparison, and the
   D-017 tool's Instagram model will have learned mainly from Zero Sugar content.
3. **Two metadata sources.** Curated links are fetched with `yt-dlp` (free; verified
   2026-09-15 on 3 links: account, likes, comments, date, dimensions - no views, no
   duration, no follower count). The 319 came from Apify. Check agreement on the overlap
   before merging.
4. **Three markets are outside the 41-account frame:** Singapore (`cocacolasg`, from
   metadata), Chile and Kenya (handles unknown until fetched). Handles come from the data,
   never guessed; the researcher confirms verified badge and follower count (O-10).
5. **Content type and collaboration partner become hand-coding constructs** in task 4.1,
   held to the same alpha >= 0.67 rule as every other construct.
6. **Download route:** `yt-dlp` first - it fetches from Instagram directly, is scriptable,
   and has a version to cite. The supervisor's `sssinstagram.com` is a manual fallback for
   any link `yt-dlp` cannot fetch, done by the researcher by hand, and recorded per row in
   a `download_route` column so the methods chapter can state it.
7. **The researcher's label is not exempt from checking.** It is re-checked in hand-coding
   like everything else.
8. The raw WhatsApp export (`Cocacolaaaa/`) is gitignored: it holds a contact's name and
   share tokens tied to the researcher's account. The CSV is the record.
9. `CjsWsVlNPH7` is a 2022 horizontal video post, not a vertical Reel. Five links are `/p/`
   posts; each needs an in-scope check.

**Result, 2026-09-15 (tasks 2b.1, 2b.2).** `yt-dlp` fetched 107 of 118 links free; 98 are
vertical and usable. Saving order matches the researcher's page list block for block, which
placed the two failing clusters: 6 links between Costa Rica and Thailand are Indonesia
(age-gated, as O-08 predicts) and the Kenya block sits between Thailand and Singapore. Three
Coca-Cola accounts outside the frame surfaced from the data: `cocacola_cl`,
`cocacola_kenya` (from a caption tag), `cocacolasg` - all O-10. 27 of 107 are
collaboration posts; their page is recorded in `source_basis` by strength of evidence.
Agreement with Apify on the 11 shared Reels: same account, post time and aspect ratio
11/11; likes+comments within 0.4%. Two apparent disagreements were not: dimensions were
different-resolution copies of one video, and a Thai Reel read by Apify 1.5 h after posting
(242 likes) had 1,758 at 89 h - growth, which raised O-11. yt-dlp's cached comment samples
held commenters' usernames and ids; they are stripped at fetch time and were scrubbed from
the files already written.

**Corpus built, 2026-09-15 (tasks 2b.3-2b.5; `src/screen/build_instagram_corpus.py`).**
150 Reels: **107 curated Zero Sugar** (98 fetched + 9 of the researcher's 10 manual downloads)
+ **6 screener-found Zero Sugar** not on the list (kept as the comparison group) + **37
regular** Reels drawn at random (seed 20260911) from the 319, vertical and read >=7 days
after posting. **113 Zero Sugar**, against 8 in the corpus it replaces (backed up as
`instagram_corpus_before_D018_20260915.parquet`). All 8 regions populated.

- **O-10 closed.** Researcher verified all three: `cocacola_cl` 443k, `cocacola_kenya`
  89.9k, `cocacolasg` 30.5k, blue tick on each. Added to `accounts_instagram.csv` (44).
- **All 15 inferred collaboration pages confirmed** by the researcher; no conflicts.
- **Manual downloads.** 10 of the 11 login-only links were downloaded by the researcher
  (`insta reels/`); `DThmhSbkx6n` could not be and is dropped. `C6NePO-Blbh` is square
  (720x720) and excluded by the vertical rule. Their post dates are decoded from the
  shortcode (validated on 426 known times: median error ~1 min, max 2.7 days - all ten
  are months old, so the 7-day rule is unaffected). Their likes/comments are **pending**:
  the researcher's screenshots were pasted into the CSV and Excel drops images on CSV save.
- **Text screening misses most real Zero Sugar.** On the 98 researcher-verified Reels with
  captions, the screener named Zero Sugar in **29 (30%)**; 48 were `unnamed` and 21
  `off_brand` (creator captions that never mention Coca-Cola). This is the measured case
  for the visual label, and it means screener-based Zero Sugar counts elsewhere in the
  project (YouTube: 25) are lower bounds.
- **Still open:** likes/comments for 9 manual Reels; follower counts for 24 creator
  accounts that own collaboration posts; 3 refreshes due by 2026-09-20; the tool used for
  the manual downloads, for the methods chapter.

**Manual Reels and followers, 2026-09-15 (tasks 2b.6, 2b.8).**
- **Download tool:** the researcher's 10 manual downloads used `sssinstagram.com/reels-downloader`
  (researcher-confirmed). Recorded per row in `download_route`; the methods chapter should
  name it alongside `yt-dlp`.
- **Screenshots:** 12 files in `insta reels/screenshots/`, matched to shortcodes and renamed
  automatically at the researcher's request. Each match's evidence is in `_rename_map.csv`
  (caption text, shortcode date, capture time, and for `DTYRCT0jN7L` a frame comparison).
  Numbers transcribed into `docs/manual_reel_metrics.csv`, not yet checked by the researcher.
  `DSEsIQHksTP` is matched by elimination and date only - its screenshot shows no caption.
- **These posts are restricted to logged-in users.** An Apify post lookup returned
  `restricted_page` for all 9, as yt-dlp had failed on them - so the screenshot numbers
  cannot be cross-checked by any logged-out source. `trophytour`'s profile is likewise
  restricted. That is a property of the posts, and it should be stated: these 9 rows carry
  researcher-transcribed engagement, every other row carries machine-read engagement.
- **Hidden is not zero:** `C4-MHHxqE2M` displayed 3 likes against 23 comments; held null
  pending the researcher, displayed value kept in `likes_as_displayed`.
- **Label query:** 16 frames across `DTYRCT0jN7L` (FIFA Trophy Tour, India) show only red
  Coca-Cola Original Taste packaging. Label kept as the researcher's; flagged in `label_flag`
  for re-check.
- **Followers:** Apify profile lookup (~$0.09 for both lookups, free allowance, researcher chose it)
  resolved 24 of 25 creator accounts. A bug that filled an unknown owner's followers with the
  Coca-Cola page's count was caught before it reached the corpus - a creator's #Ad post
  would have been given the brand's audience. Unknown owners now stay null.
- **Still open:** owner handle for 8 manual Reels; `trophytour` follower count; whether
  `C4-MHHxqE2M` likes are hidden; the `DTYRCT0jN7L` label; 3 refreshes by 2026-09-20.

**Researcher answers applied, 2026-09-15 (task 2b.6 closed).** From
`reports/researcher_inputs_needed.csv`: all 9 transcribed like/comment pairs confirmed; all
8 owners supplied (5 x `cocacola_id`, `cocacola`, and two Kenyan creators in collaboration
with `@cocacola_kenya`: `ivvanoh_festo`, `shely_sophisticatedrhythm` - both handles confirmed to
exist by Apify, profiles restricted); follower counts read on Instagram for the restricted
accounts (`trophytour` 305K, `cocacola_id` 96.4K, the two creators 242K and 61.3K -
display-rounded, recorded as such). `C4-MHHxqE2M` likes confirmed hidden and held null.
**`DTYRCT0jN7L` relabelled `original`** (researcher: "original I think"; frames show only
Original Taste) - it stays in the corpus as `curated_relabelled_not_zero_sugar`.
**Final Instagram corpus: 150 Reels, 112 Zero Sugar; 0 unknown owners; 0 missing follower
counts.** One of 107 curated labels overturned on inspection - the hand-coding pass (4.1)
should still re-check every label, since only this one Reel was frame-checked.

---

## D-019 - Include 2026; engagement counts only once a post is 7 days old

**Date:** 2026-09-15
**Status:** Accepted (researcher's decision)
**Resolves:** O-11.

**Decision:** (1) The analysis window includes 2026. The "2022-2025" restriction in
`06-dependent-variable.md` is lifted. (2) Likes and comments enter the dependent variable
only if they were read **at least 7 days after the post went up**. A post read sooner is
not dropped; its numbers are refreshed once it is a week old (free, `yt-dlp`).

**Why.** Applied as written, the 2022-2025 window would have kept 32 of 150 YouTube Shorts
and 54 of 98 curated Zero Sugar Reels - the corpus is mostly 2026 because Shorts and Reels
adoption is recent. The 7-day rule exists because early counts are not comparable: a Thai
Reel read 1.5 h after posting showed 242 likes, and 1,758 at 89 h.

**Consequences:**
- `video_age_days` stays as a control; the 7-day floor removes the steepest part of the
  growth curve, which a linear age term cannot model.
- **YouTube corpus unaffected:** 0 of 150 were read under 7 days old.
- **Instagram:** regular fill Reels must be at least 7 days old when read - 79 of the 319
  were not, and are ineligible. Three corpus Reels are flagged `too_young_refresh` with a
  `refresh_after` date (latest 2026-09-20).
- Time-trend findings remain entangled with format adoption (docs/02), now across 2016-2026.

---

## D-020 - YouTube video files are downloaded logged in, with a spare account

**Date:** 2026-09-15
**Status:** Accepted (researcher's decision)

**Context.** Instagram's 150 Reels downloaded logged-out without trouble. YouTube refused
every logged-out download from this connection with "Sign in to confirm you're not a bot",
most likely because of the 2,094-video enumeration and 295 redirect checks run on
2026-09-11. The bot check was not bypassed.

**Decision.** Download the 150 YouTube Shorts signed in to a **spare** Google account (not
the researcher's own), using a `cookies.txt` exported by the researcher from a private
browser window, following yt-dlp's documented method. No script extracted cookies from
the browser, and the file is never printed. It lives at `secrets/youtube_cookies.txt`,
gitignored (`secrets/`, `*cookies*.txt`), is passed to yt-dlp for YouTube only, and is to be
deleted and the session signed out once downloads finish.

**A second requirement surfaced.** Signed in, YouTube answered "The page needs to be
reloaded". That message comes from YouTube, not yt-dlp: logged-in requests use web clients
that must solve JavaScript playback challenges, and no JavaScript runtime was installed.
With the researcher's approval, `deno 2.9.6` (Deno authors, PyPI) and `yt-dlp-ejs 0.8.0`
(yt-dlp project, PyPI) were installed; the next test downloaded at 720x1280.

**Consequences:**
- **Methods chapter:** YouTube *metadata* came from the official Data API v3 (logged-out,
  API key); YouTube *video files* were downloaded with yt-dlp while signed in to a spare
  account. Instagram metadata came from Apify and yt-dlp logged-out, 9 video files from
  `sssinstagram.com` by the researcher. All four routes should be named.
- Signing in changes access, not content: these are public Shorts, and nothing account-
  specific (recommendations, history) is collected.
- `.env.example` had held the real YouTube API key; blanked before any commit (0 commits
  existed, so it never left the machine).

**Result, 2026-09-15.** All 150 YouTube Shorts downloaded logged in (0.63 GB, 86 min of
video). Two corpus Shorts had been removed from YouTube since 2026-09-11 ("Video
unavailable") and four downloaded as square 720x720 - including one replacement - so fail the
height > width rule already applied to Instagram. None was Zero Sugar. Each was swapped
for a random unselected brand Short (`build_corpus.py --replace-unusable`, seeded, >=7 days
old, not Zero Sugar), with `replaces` and `exclusion_detail` recorded on the rows; the rest
of the corpus is unchanged. **Both corpora now: 150 videos each, every file on disk,
vertical, with audio** - YouTube 25 Zero Sugar, Instagram 112.

---

## D-021 - AI annotation runs on a free local model on the researcher's GPU

**Date:** 2026-09-15
**Status:** Accepted (researcher's decision); model chosen by pilot
**Resolves:** O-12.

**Decision:** The 8 annotation constructs in docs/05 §3 are produced by a free, open vision-
language model running locally on the researcher's laptop GPU (NVIDIA GeForce RTX 3050
Laptop, 6 GB). No paid AI API is used.

**Why this is sufficient.** The project already has the safeguard that makes a smaller model
acceptable: every construct is checked against the researcher's hand-coding with
Krippendorff's alpha and **dropped if alpha < 0.67** (docs/05 §3-4). A weaker model costs
constructs, visibly and measurably - it cannot quietly degrade the results. Running locally
also keeps the corpus on the machine and makes the Flask tool (D-017) free to run.

**Correction recorded.** An earlier check (2026-09-15) reported "no GPU". That was wrong: it
queried PyTorch, and the installed build is CPU-only (`torch 2.12.0+cpu`), which cannot see
a GPU. `nvidia-smi` shows the RTX 3050, 6144 MiB, driver 596.21, CUDA 13.2.

**Consequences:**
- PyTorch must be swapped for its CUDA build (`torch 2.12.0+cu130`, `torchvision 0.27.0+cu130`,
  official download.pytorch.org index; cp314 Windows wheels confirmed to exist). Same version
  number as the installed CPU build, to avoid disturbing other libraries. Needs the
  researcher's approval to download (~3 GB).
- **6 GB of video memory limits model size** to small or quantized models (roughly 3-7B
  parameters). Expect concrete constructs (`has_celebrity`, `has_cta`) to pass alpha and
  abstract ones (`campaign_type`) to be at risk - exactly the gradient docs/05 §3 predicts.
- Model selection by pilot: run candidates on ~10 videos, compare to the researcher's codes,
  keep the best that fits in memory. Record the model name, version and prompt in the
  methods chapter.
- The GPU also shortens Phase 5 (Whisper transcription, CLIP, EasyOCR).
- Standing rule 10 ("no money spent") continues to hold.

---

## D-022 - Automated annotation is kept and stated openly; shared files hold data and method only

**Date:** 2026-09-15
**Status:** Accepted (researcher's decision)

**Decision:** (1) The 8 annotation constructs stay automated (D-021) and are described
openly in the methods chapter as automated annotation validated against manual coding, with
the model named and alpha reported per construct. (2) Anything shown to a supervisor or
examiner comes only from `reports/shared/`, built by `src/export/shared.py`.

**Why.** The researcher was concerned that "AI labels" would look careless. The concern is
addressed by presentation, not concealment: automated annotation validated by Krippendorff's
alpha against a human-coded subset is an established method and reads as rigorous when
reported that way. An undisclosed automated step is what would do real damage at a viva, so
hiding it was ruled out.

**What "clean" means - and its limits:**
- **Removed from shared files:** internal workflow notes (which step the researcher or the
  assistant ran), personal file-system paths, internal document references, credential-like
  strings. `check()` scans every shared file for these and fails the export if one appears;
  a planted test leak was caught (2026-09-15).
- **Never removed:** how each value was obtained. Collection routes, manual records, the
  sssinstagram.com downloads, the logged-in YouTube downloads and automated steps are all
  stated in `reports/shared/README.md` and per row.
- **Records are not rewritten to misattribute work.** Internal files keep full provenance.
- **Disclosure of AI assistance** in the thesis follows the institution's policy (O-01),
  which the researcher is to read. Keeping shared data tables free of workflow notes does not
  replace whatever that policy requires.
- **Only `reports/shared/` is clean.** `docs/`, the rest of `reports/`, `data/` and the code
  contain internal notes. If the whole project folder or repository is ever shared, those go
  with it.

**Found while building it.** The download manifest had overwritten the true source of 9
sssinstagram.com Reels, 1 pilot Reel and 149 YouTube Shorts with "already_on_disk" when files
were re-probed. Repaired from the corpus records and the run history (every YouTube file
came from a logged-in run; no logged-out attempt succeeded), and `save_manifest()` now keeps
the original route on re-probe.

**Consequences for later phases:** automated labels appear in shared tables under clearly
named columns (e.g. `auto_has_cta` beside `manual_has_cta` on the hand-coded subset), with
the model and prompt described in the README.

---

## D-023 - Manual coding: 60 random videos, 5 concrete constructs, coded by the researcher

**Date:** 2026-09-15
**Status:** Accepted (researcher's decision)
**Amends:** docs/05 §3 ("hand-code a random 150-video subset").

**Decision:** The researcher codes a fixed random subset of **60 videos** (30 YouTube, 30
Instagram; seed 20260915; `data/coding/sample.csv`) on **5 concrete constructs**:
`has_celebrity`, `has_influencer`, `has_cta`, `humour_present`, `zero_sugar_visible`.
Coding happens in a local page (`python -m src.coding.app`) that shows only the video, its
account and caption, never automated labels or corpus grouping, and saves each answer to
`data/coding/manual_codes.csv`.

**Why.** 150 videos on 8+ constructs (6-8 h) was more than the researcher could take on.
A 20% random subset is a common, defensible share for reliability checks, and concrete
perceptual constructs are the ones a single coder can judge consistently. Estimated time:
~2 h, in sittings of about 20 videos.

**What was ruled out.** The assistant coding the videos and presenting the result as the
researcher's manual coding. Manual coding is the human check on the automated labels; coded
by the same kind of system it checks, alpha would measure agreement with itself while being
reported as human validation. The researcher also declined a second coder.

**Consequences:**
- Alpha is computed per construct on the 60 (manual vs automated); below 0.67 the construct
  is not used. With n=60 the alpha confidence intervals are wider than at 150 - report them.
- `product_vs_lifestyle`, `ugc_vs_brand`, `campaign_type` and `is_sponsored` have **no manual
  check**. They are either dropped or reported explicitly as unvalidated automated labels;
  they must not be presented as validated. (`is_sponsored` also has platform metadata -
  Instagram's paid-partnership flag - which is a better source than annotation.)
- `zero_sugar_visible` also re-checks the Instagram Zero Sugar labels (D-018 consequence 7)
  on the 30 Instagram Reels in the subset.
- Codebook published to `reports/shared/codebook.md` (clean).
- A test click made while verifying the page was deleted before handover; the codes file
  starts empty, so every answer in it is the researcher's.

---

## D-024 - No normalised copy of each video; frames are normalised at the moment of measurement

**Date:** 2026-09-16
**Status:** Accepted (researcher's decision)
**Amends:** docs/05 section 1 (the pipeline diagram shows "ffmpeg -> normalised video + mono
16 kHz WAV"). The WAV stands; the normalised video does not.

**Decision:** Task 5.1 extracts a 16 kHz mono WAV per video and records a normalisation
profile, but writes **no re-encoded copy of the video**. Every step that reads pixels
resizes frames to a common working width (`src/features/common.WORK_WIDTH = 360 px`,
aspect preserved) at the moment it measures them.

**Why.** The reason to normalise is that the corpus is not one shape: native widths run
360-720 px and 16 of the 300 videos are 4:5 rather than 9:16. Left alone, `edge_density`
and `motion_intensity` would partly measure file size rather than content. Resizing at
measurement time removes exactly that confound, and:

- costs ~1.5 GB less disk and ~30 min less re-encoding than a second copy of the corpus;
- leaves on-screen text recognition (5.5) the full-resolution frame, which a 360 px copy
  would have blurred;
- 360 px is the *smallest* native width in the corpus, so no frame is ever upscaled and no
  detail is invented.

**Consequences:**
- Pixel measures are reported at a stated common working width; the methods chapter says so
  rather than implying the files were transcoded.
- Frame rate is *not* normalised on disk either. Native fps is recorded per video (25 fps
  n=101, 24 fps n=98, 30 fps n=97, 60 fps n=2, 29 fps n=1, 10 fps n=1). Steps that compare
  frames over time (motion, 5.5) sample at a fixed rate rather than trusting native fps.
- `aspect_ratio` remains a dropped feature, but for the correct reason: it is
  **near-constant** (279 of 300 at 0.562), not constant by construction as docs/05 states.

---

## D-025 - Two corpus Reels have digitally silent audio; they are flagged, not dropped or imputed

**Date:** 2026-09-16
**Status:** Accepted

**Decision:** `Cd5oWJNsfI0` and `DUC5hF6E7Lj` (both Instagram) carry an AAC audio stream that
is silent end to end. They stay in the corpus, flagged `audio_silent` in the 5.1 cache. Audio
features for them are left **null**, never zero-by-default, except where zero is the true
measurement (`speech_dur_frac`, `music_present`).

**Evidence.** ffmpeg `volumedetect` on the original MP4s reports mean and max volume of
-91.0 dB across every sample - digital silence, not quiet audio. A normal corpus video reads
-18 dB mean / -0.3 dB max. Confirmed on the source files, so this is not an extraction fault.
Corpus-wide the audio RMS median is 0.135; these two are the only zeros.

**Why it matters.** Speech-to-text does not return nothing on a silent track - it invents
text. Transcribing these two would have put fabricated words into `transcript`,
`words_per_min`, sentiment (5.9) and the automated labels (5.12), where they would have been
indistinguishable from real content. 5.6 must skip any video flagged `audio_silent`.

**Consequences:**
- 5.6, 5.8 and 5.9 read the `audio_silent` flag and skip rather than transcribe or measure.
- Two videos with null audio features is well inside the 30%-missing pruning rule
  (docs/05 section 4, rule 2); no feature is dropped because of this.
- The methods chapter reports 300 videos measured, 298 with usable audio.

---

## D-026 - Cut detection: a hidden-montage check, and the minimum shot applies to the last shot too

**Date:** 2026-09-16
**Status:** Accepted
**Amends:** 5.2 as first run the same day (docs/05 section 5); task 5.5 (motion moves to 5.3).

**Decision:**
1. **Hidden-montage check.** After standard cut detection (0.25 s minimum shot), 5.2 compares
   pairs of frames 0.1 s apart inside each detected scene. Optical flow warps one onto the
   other and the change it cannot explain is measured. If the typical leftover exceeds 50 grey
   levels (of 255) over at least 3 pairs, the video is re-detected with a one-frame minimum
   and flagged `hidden_montage`.
2. **The 0.25 s minimum applies to the final shot.** PySceneDetect enforces it on every shot
   except the last. A final fragment shorter than 0.25 s is merged into the shot before it
   (not in a hidden montage).
3. **Motion is measured in 5.3**, while the video is being decoded, not in 5.5, which only
   sees stills a second apart.
4. **A scene keyframe always comes from inside its own scene**, and frames are assigned to
   scenes with a 0.5 ms tolerance for the millisecond rounding of stored boundaries.

**How these were found.** All four came out of checking 5.3's output by eye, not from the
numbers looking wrong.
- The motion extremes included a Reel (`Dax6ozkufSd`, 10 fps, 3.9 s) that is a photo montage
  with a new picture on every frame. 5.2 had called it one continuous shot and 5.3 read the
  picture changes as motion.
- A strict integrity check (every shot has a keyframe from inside itself) then failed on 5
  videos. All 5 ended in a one-frame "shot". Counting across the corpus found **37 videos**
  whose last shot was 1-6 frames long, while no first or middle shot anywhere was under
  0.25 s. Two were viewed frame by frame: one ends on a single black frame, the other on the
  first frame of a shot the edit cut off. Neither is a cut a viewer sees.

**Why a residual check and not a looser minimum.** Loosening the minimum to one frame on the
44 most at-risk videos multiplied their counts by up to 11x. One second of consecutive frames
from two of them showed the extra "cuts" were stage-light flicker and handheld camera shake.
The minimum is right; what needed deciding was the exception, and whether movement explains a
change is evidence the cut detector does not have.

**Evidence the check separates the cases.** Leftover change after motion compensation, typical
value per video, on videos whose truth was established by eye: photo montage **89.8**;
handheld walking video 22.2; concert with flickering stage lights 21.0; ad with animated title
cards 28.8; single take with people gesturing 2.1; static title card 0.1. Across all 300 the
median is 3.3; one video exceeds 50 (the montage) and one other exceeds 25 (the ad, whose cuts
were inspected frame by frame). The threshold sits in a gap, not on a slope.

**Effect on the features:**

| | First 5.2 run | After D-026 |
|---|---|---|
| `cuts_per_sec` median / mean | 0.467 / 0.516 | **0.466 / 0.543** |
| `cuts_per_sec` max | 1.781 | **9.679** (the montage; next 1.781) |
| Single-shot videos | 21 | **23** (17 Instagram, 6 YouTube) |
| Total shots | 5,814 | **5,815** (+38 montage, -37 end fragments) |
| Videos whose count changed | - | **38** |
| `motion_px_per_sec` | - | 299 values; null for the montage (every pair crosses a cut) |

**Consequences:**
- `cuts_per_sec` has one extreme value. It is real - the video changes picture ten times a
  second - but it will dominate any linear model. How to treat it (log scale, rank, or cap) is
  a Phase 7 diagnostics decision, made before the outcome is consulted.
- The checks live in the pipeline, not as hand corrections, so the Flask tool (D-017), which
  imports this code, treats a submitted video the same way.
- 5.3 records a fingerprint of the scene list it sampled from and re-samples automatically when
  5.2 changes it. After the end-fragment merge, exactly the 37 changed videos were re-sampled.
- Known limits, stated in methods: a montage *section* inside an otherwise normal video lowers
  `cuts_per_sec` slightly without tripping the check; within-shot flicker nudges motion up.
  Both are small against the per-video medians used.

---

## D-027 - Speech-to-text: CUDA 12 runtime for the GPU, and rules for text that is not speech

**Date:** 2026-09-21
**Status:** Accepted (download and install approved by the researcher)

**Decision:**
1. **CUDA 12 runtime.** faster-whisper's engine (CTranslate2 4.8.2) is built for CUDA 12; the
   installed PyTorch is the CUDA 13 build and carries only CUDA 13 libraries. NVIDIA's own
   CUDA 12 wheels are installed alongside: `nvidia-cublas-cu12==12.9.2.10`,
   `nvidia-cuda-nvrtc-cu12==12.9.86`, `nvidia-cudnn-cu12==9.10.2.21` (1.32 GB, free). cuDNN is
   pinned to **9.10.2.21** because CTranslate2 bundles that exact cuDNN loader and cuDNN
   refuses to mix versions. `common.enable_cuda12_dlls()` points only the speech engine at
   them; PyTorch keeps its own CUDA 13 copies (verified: still on the GPU afterwards).
2. **Stock phrases are not transcript.** A segment of 8 words or fewer that is one of
   Whisper's stock non-speech outputs ("Thank you for watching", "Subtitles by the
   Amara.org community", ...) is marked `stock_phrase` and left out of the transcript text.
   The raw segment stays in the record.
3. **No intelligible speech.** If nothing real remains, the video is `no_intelligible_speech`:
   empty transcripts, no spoken language, `speech_dur_frac = 0` - the same as the 98 videos
   with no detected voice. The voice-activity reading is kept as `speech_sec_vad`.
4. **Failed translation.** If the English translation is empty while the native transcript is
   not, `transcript_en_failed` is set and 5.9 uses native-language sentiment for that video.
5. **Low-confidence flag.** `transcript_low_confidence` when mean word probability < 0.80 or
   spoken-language probability < 0.70. A flag, never a deletion.

**Correction recorded.** The handoff (2026-09-16) said faster-whisper's engine "sees" the GPU.
It did - `get_cuda_device_count()` returned 1 - but it could not compute on it: the first
real run failed with `cublas64_12.dll is not found`, and inside the long run that failure
surfaced as a silent hang (0% GPU, no CPU, no error) rather than an error. Seeing a device is
not the same as using it; the check now is a real transcription.

**Why rules 2-5.** On the full run, 6 transcripts contained stock phrases. In 5 the whole
transcript was one such phrase, produced from music (language probability 0.28-0.44, word
probability 0.54-0.77, no-speech probability 0.68-0.88): left in, "Thank you for watching!"
would have been scored as positive sentiment and offered to the automated labels as a call to
action. In the sixth, the Spanish transcript was real lyrics but the English "translation" was
only "Subtitles by the Amara.org community". Rule 5 exists because Whisper's own segment
thresholds, built for long recordings, did not fire on a 2-second misheard line under music;
per-word probability did (0.73 there, 0.92+ on transcripts checked against subtitles).

**Consequences:**
- 300 videos: **194 with speech**, 98 no speech, 6 no intelligible speech, 2 silent (D-025).
- Rules live in `asr.derive()` and re-apply without the GPU (`--repost`), and the Flask tool
  (D-017) inherits them by importing the same code.
- 47 of 194 transcripts are low-confidence: mostly 2-5 word lyric fragments and the
  code-switched Nepali-English series. Whether transcript-based features exclude them is a
  5.11 / 7.2 decision, made before the outcome is consulted.
- Transcripts of sung jingles count as speech here; 5.8's music detector is what separates
  singing from talking.

---

## D-028 - Audio features: AST instead of YAMNet; talk vs sung from the speech score; pitch within segments

**Date:** 2026-09-22
**Status:** Accepted (model download approved by the researcher)
**Amends:** docs/05 section 2B (YAMNet named as the music-vs-speech model).

**Decision:**
1. **Sound events come from AST**, the Audio Spectrogram Transformer fine-tuned on AudioSet
   (`MIT/ast-finetuned-audioset-10-10-0.4593`, BSD-3, 346 MB), on the GPU through the existing
   PyTorch. YAMNet uses the same AudioSet categories but needs TensorFlow, which has no build
   for this project's Python 3.14 (latest TensorFlow 2.21 stops at 3.13); a second Python for
   one model was not worth it.
2. **Talked vs sung is decided per transcript segment from AST's *speech* score**, not its
   singing labels: a segment is talk if its speech score is at least 0.30, otherwise sung
   vocals. On 12 videos whose truth was known from their content, AudioSet's singing labels
   barely fired (a Christmas choir peaked at 0.06), while the speech score split cleanly:
   0.57-0.77 on talking (even over music), 0.05-0.09 on songs. Chanted slogans (the Korean
   "코카콜라 맛있다") fall between, 0.30-0.59, and count as talk; one sits on the line.
3. **Voice pitch variability is measured within each transcript segment and averaged**, and a
   talk-only version excludes sung segments. Measured across a whole video it mostly measured
   how many voices, and of which sexes, were present: five man-woman or group conversations
   read 10-13 semitones and fell to 2-5 when measured within segments.

**Consequences:**
- Music is in 272 of 300 videos (Instagram 86%, YouTube 95%). Talking share: median 0.0 on
  Instagram, 0.66 on YouTube - the same platform gap 5.6 found, now net of singing.
- 37 videos contain some sung vocals in their transcribed speech; 14 are mostly sung.
- For 5.11 (pre-registered rule 4, |r| > 0.85): keep `talk_dur_frac` over `speech_dur_frac`
  (Spearman 0.91), drop `speech_frac_ast` (0.88 with `speech_dur_frac`; it was a cross-check),
  keep `pitch_std_talk_semitones` over `pitch_std_semitones` (0.996).
- **`is_original_audio` cannot be measured.** Only Apify reported it: 43 of 150 Reels (38
  original, 5 not); yt-dlp does not, and YouTube has no equivalent. At 71% missing on
  Instagram and 100% on YouTube it fails pruning rule 2 (>30% missing). docs/05 called it high
  priority after the brand-TikTok study; its absence is a stated limitation, and it is not
  guessed from other fields.
- 20 of the 166 talk-only pitch values rest on a single segment and are the least reliable.

---

## D-029 - Platform comparison pre-registered; YouTube Zero Sugar decided by eye for every Short text does not name

**Date:** 2026-09-22
**Status:** Accepted (researcher's decisions: check all 125 by eye after the CLIP screen failed;
keep the answers as given after seeing how they compare with the blind codes)
**Amends:** D-014 for YouTube (text-`unnamed` Shorts are now resolved by eye, not left open);
D-018 consequence 2 and TODO standing rule 5 (YouTube Zero Sugar is no longer 25); docs/08
section 7.4 (amended in 7.8, before any analysis).

**The problem.** The two platform samples were built differently. Instagram: 107 Reels
hand-picked from the researcher's Zero Sugar list, 43 systematic. YouTube: all systematic,
with only the 25 Shorts that name Zero Sugar in title, description or tags labelled Zero Sugar.
The researcher's blind codes (D-023) showed 13 of 30 random Shorts with Zero Sugar on screen,
only 5 of them text-labelled, so the YouTube label was badly undercounted and a raw platform
difference would be tangled up with product and with how videos were chosen.

**Decision:**
1. **The platform comparison is pre-registered** before any comparison was run: docs/08 section
   7 (main mixed model, like-with-like strata, sensitivity without the hand-picked Reels and
   without the global channel, verdict rules, H9/H10 exploratory) and docs/07 section 1a (EDA 8).
   The two engagement descriptives already seen are disclosed there (7.2).
   `src/process/dependent_variable.py` hides engagement values unless `--show-outcomes` is given.
2. **Every corpus row says how it entered and how its label was decided**
   (`src/screen/zero_sugar_labels.py`): `selection` (hand_picked | systematic), `zs_label_method`
   (text | researcher_curated | researcher_visual_check), `zs_clip_screen`,
   `is_zero_sugar_before_D029`. Backups `*_before_D029_20260922.parquet`. Both corpus builders
   re-apply it on rebuild.
3. **The CLIP ViT-L-14 screen failed and decides no label** (AUC 0.58, 95% CI 0.43-0.73, on 59
   blind-coded videos; `reports/clip_zero_sugar_calibration.md`). Its embeddings are kept for
   5.4 product features; its screen outputs are renamed `*_first_attempt*`.
4. **The researcher checked all 125 text-unlabelled YouTube Shorts by eye** on a local page
   (`src/coding/zero_sugar_check_app.py`): a sheet of 8-16 frames (one per shot; evenly thinned
   to 16 on the 46 Shorts with more shots, median 29; topped up to 8 on the 27 with fewer) plus
   the video, three answers, never shown blind codes, text labels or scores. The first pass did
   not save; the second was answered on the page on 2026-09-22 between 18:49 and 18:57 (local
   time), 125 of 125:
   **49 Zero Sugar, 76 Not Zero Sugar, 0 Unsure**. Applied as `zs_label_method =
   researcher_visual_check` (both answers; a "not" answer now also rests on a look, not on text).
5. **Answers kept exactly as given.** After the agreement and the note pattern below were shown,
   the researcher was offered a re-look at the 19 noted Shorts or a full second pass, and chose
   to keep the answers (2026-09-22). No answer was entered or changed by anyone else.

**Result.**

| | Before | After |
|---|---|---|
| YouTube Zero Sugar, corpus | 25 / 150 | **74 / 150** (25 text + 49 visual check) |
| YouTube Zero Sugar, usable DV rows | 25 / 144 | **72 / 144** |
| Instagram Zero Sugar, corpus / usable | 112 / 111 | unchanged |

Checked, not assumed: every engagement column (rates, percentile, high/low splits, followers,
likes, comments, views, status, cell, age) is identical to the backup in all 300 rows; exactly 49 rows
changed `is_zero_sugar`, all False to True, and they are exactly the 49 answered Zero Sugar.

Usable rows, videos (accounts), by platform x `is_zero_sugar` x `selection`:

| | Hand-picked | Systematic | Total |
|---|---|---|---|
| Instagram, Zero Sugar | 105 (13) | 6 (5) - thin | 111 (16) |
| Instagram, not Zero Sugar | 1 (1) - thin | 34 (9) | 35 (9) |
| YouTube, Zero Sugar | - | 72 (5) | 72 (5) |
| YouTube, not Zero Sugar | - | 72 (4) | 72 (4) |

("Thin" = under 20 videos or 3 accounts, docs/07 section 1a.) Of the 72 usable YouTube Zero
Sugar Shorts, 58 come from the global channel, which also holds 59 of the 72 not-Zero-Sugar.

**Reliability of the new label - weak, and stated.**
- **Repeat agreement.** 25 of the 125 had also been coded blind on 2026-09-15 (full video with
  sound). The two looks by the same coder give the same Zero Sugar answer for **16 of 25**;
  Krippendorff's alpha **0.25** (bootstrap 95% CI -0.17 to 0.60). Both Zero Sugar 5, both not
  11; blind "other Coca-Cola" but now Zero Sugar 6; blind Zero Sugar but now not 3. Across all
  30 blind-coded Shorts, 10 of the 13 coded Zero Sugar are now labelled Zero Sugar, and 6 of the
  17 coded otherwise are too. This is below the 0.67 bar the project sets for automated labels.
- **Answers that may record something else.** 19 answers carry a note, and all 19 are Not Zero
  Sugar: 14 "again the same video" and 1 "too many time this video is coming and its usless",
  all in the *José vs Mourinho* podcast series (36 of the 125), plus 4 "not related to our work".
  In positions 1-74, 12 of 16 episodes of the series were answered Zero Sugar; from position 75,
  where the "usless" note appears, 5 of 20 were (none of the 5 with a note). Two of the 3
  blind-Zero-Sugar-now-not disagreements are "again the same video" rows. So some of these
  answers may say the video is repetitive or off-topic rather than that no Zero Sugar pack is
  shown. If the 15 series answers are of that kind, YouTube Zero Sugar is undercounted by up to 15.
- **Pace:** median 3 seconds per Short (quartiles 2.75-4), 8.4 minutes for 125. On the 46
  thinned sheets a brief pack shot can be visible only in the video, not on the sheet.

**Consequences:**
- **Both like-with-like strata are testable** under docs/08 section 7.5(b) (at least 20 videos
  and 3 accounts per platform). In the systematic-only re-run (c), Instagram Zero Sugar has 6
  videos from 5 accounts, so that stratum is descriptive only.
- **Report the label's reliability next to every result that uses `is_zero_sugar`**, above all
  H7 (b): 16 of 25, alpha 0.25, and the note pattern. Do not describe the YouTube label as
  validated.
- **Labels frozen** for the pre-registered analysis (docs/08 section 6): answers SHA-256
  `0d03a9e7...a4505c7`, read-only copy `docs/zero_sugar_visual_check_pass1_20260922.csv`;
  analysis table `4d54d5a6...f1febcce6`. Any later label change is a dated re-freeze there.
- **The platforms are still not treated the same way on Instagram's side.** YouTube's random
  draws were all checked by eye; Instagram's 37 random Reels were not (the blind codes found 4
  unlabelled Zero Sugar Reels among Instagram's systematic Reels, and 4 hand-picked Reels coded
  otherwise). An Instagram check is offered to the researcher, not done.
- **No new collection** (D-012, D-016): YouTube Zero Sugar at 72 usable is below Instagram's 111
  but no longer too few for the registered strata.
- **Shared export** (`src/export/shared.py`) now states per row how each YouTube label was decided
  (text screening / manual visual check: Zero Sugar / manual visual check: not Zero Sugar) and
  fails on any method it has no wording for; random draws are "Random draw", not "Regular"; the
  README describes the check and the 16-of-25 agreement.
- **Methods chapter:** describe the check as it was done (single coder, frame sheet plus video,
  three answers, the repeat agreement and the note pattern), and the failed CLIP screen with the
  docs/08 7.8 amendment. Neither CLIP nor any automated step decided a label.

---

## D-030 - Analysis narrowed to Coca-Cola Zero Sugar; the platform comparison stays

**Date:** 2026-09-23
**Status:** Accepted (supervisor's answers to the week 3 report, relayed by the researcher; the
engagement reference below is the researcher's own decision, made the same day)
**Amends:** D-014 - the brand-family corpus stands, but **analysis** is Zero Sugar only; D-002's
balanced-design rationale (unequal counts per platform are now accepted); D-007 (feature budget
~30 -> 18-20); docs/08 section 7.1-7.7 (amendment row in 7.8, focused plan in 7.9); docs/07
section 1a (superseded by 1b); docs/03 section 1 criterion 2 (in force again, for analysis).

**Decision.** The supervisor answered the three questions in `progressreport-week 3.docx`:
1. **Analyse Coca-Cola Zero Sugar only.**
2. **Keep the YouTube vs Instagram comparison.** Unequal counts per platform are accepted.
3. **Make a private GitHub repository** and add the supervisor as a collaborator (the
   researcher's task, G-01; nothing in this entry depends on it).

**The focus set, verified on disk 2026-09-23** (every figure below was checked against
`data/processed/dependent_variable.parquet`, not taken from the brief):

| | Instagram | YouTube | Total |
|---|---|---|---|
| Zero Sugar corpus videos | 112 | 74 | **186** |
| With a usable engagement figure (`dv_status == "ok"`) | 111 | 72 | **183** |
| Accounts holding those videos | 16 | 5 | **21** |
| Of which one account | - | **58 of 72 from the global channel** | |
| Hand-picked / systematic (usable) | 105 / 6 | 0 / 72 | |
| Follower tier: large / small+medium (usable) | 32 / 79 | 58 / 14 | |

The 3 Zero Sugar corpus videos without an outcome are Instagram Reels with hidden like counts
(D-005). 114 corpus videos are not Zero Sugar (107 of them usable); **they stay in every file**,
flagged `in_focus = False`, as the robustness set.

**What was applied.**
1. **2c.1 focus flag.** `in_focus = is_zero_sugar & in_corpus`, added in
   `src/screen/zero_sugar_labels.py` (so both corpus builders re-apply it) and carried into the
   analysis table by `src/process/dependent_variable.py`. Backups
   `*_before_D030_20260923.parquet` for both corpora and the analysis table. Nothing was deleted.
   Checked column by column: `in_focus` is the **only** change to the analysis table - no
   engagement value, percentile, label or status differs from the backup in any of the 300 rows.
2. **2c.2 engagement reference - kept as it was** (researcher's decision, 2026-09-23, after both
   options were laid out). A video's percentile still ranks it against every usable video of the
   same platform and follower tier in the whole corpus, Zero Sugar or not, so cells stay 27-117
   videos and the robustness set stays on a comparable scale. Ranking within Zero Sugar only was
   rejected: it would have left **YouTube small+medium with 14 videos from 4 accounts** (ranks
   moving in ~7-percentile steps), changed every percentile value, and required a full re-freeze.
   Recorded in docs/06 section 3.1, with the consequence stated plainly - the yardstick includes
   videos that are not analysed, and the percentile must never be described as a rank among Zero
   Sugar videos. A **fallback rule is fixed in advance** in docs/06 section 4: if the focus set's
   median split turns out worse than 60/40 at EDA, the modelling label is taken at the focus
   set's own median, and both versions are reported. That balance has deliberately not been
   looked at - it is an engagement result.
3. **2c.3 pre-registration rewritten** for the focused design: docs/08 **section 7.9** (registered
   2026-09-23) and docs/07 **section 1b**. Sections 7.1-7.7 and 1a are left exactly as registered
   and now describe the robustness set; the change and its reason are in the 7.8 amendment table.
4. **2c.4 feature budget 18-20**, recorded in docs/05 section 4.0 **before any pruning**, with the
   reasoning (about 90 videos per class after a median split; 21 grouped-CV accounts), the
   exemption for exposure controls, and the platform-specific exceptions.
5. **2c.5 docs and shared export.** docs 03, 05, 06, 07, 08, 11 updated; `reports/shared/` carries
   a new `in_analysis_set` column per row, a "What is analysed" section, and the label's repeat
   reliability. Rebuilt, leak check passed.

**What the focus costs, stated rather than glossed.**
- **The selection sensitivity is gone.** Dropping the hand-picked Reels leaves **6 Instagram
  videos from 5 accounts**, so docs/08 7.5(c) cannot run. Every hand-picked video is an Instagram
  Reel and 105 of Instagram's 111 focus videos are hand-picked, so **the platform coefficient
  cannot be separated from how the two samples were built.** That sentence is now required next to
  the platform result (docs/08 7.9.3(c)). What replaces it: a descriptive within-Instagram
  comparison (no test), and a pre-specified contingency to run the original re-run if the
  researcher's check of Instagram's 37 systematic Reels (2c.R2) lifts that cell to 20 videos from
  3 accounts.
- **The like-with-like strata collapse** - which is the one gain: product composition is now held
  constant by design rather than controlled. Follower tier cannot replace them as a stratum
  (YouTube large is one channel; YouTube small+medium is 14 videos), so it stays a covariate and
  is reported descriptively only.
- **"Without the global channel" (7.5(d)) survives but is thinner:** YouTube then has 14 videos
  from 4 accounts.
- **Power drops.** docs/08 section 4's minimum detectable effects were for n=300; they are
  recomputed for n=183 / 21 accounts before any null is interpreted (7.9.6).
- **The Zero Sugar label now decides inclusion, not just a control.** On YouTube it is weakly
  reliable - the same coder's two looks agree for 16 of 25, Krippendorff's alpha 0.25 (D-029) -
  and error runs both ways: up to 15 *José vs Mourinho* Shorts may be excluded when they should
  not be, and 6 of the 17 Shorts the blind codes called "other Coca-Cola" are included. Report it
  with every result; never call the label validated (7.9.5).
- **Two researcher re-looks are recommended** (TODO 2c.R1, 2c.R2, ~15 min each). If either
  happens, labels are re-applied with `src/screen/zero_sugar_labels.py` and the table re-frozen
  with a new dated row in docs/08 section 6 - numbers are never patched by hand.

**What does not change.**
- **Feature extraction still runs on all 300 videos.** The focus applies when a model is fitted,
  not when a feature is measured - the robustness set needs features, and the prediction tool must
  extract them from whatever video it is given (docs/05 section 4).
- The corpus, the collection routes, the dependent variable's values and the 60 manual codes are
  untouched. Nothing new was collected and nothing cost money (D-012, D-016).
- **The tool (D-017) narrows with the study:** it predicts for Zero Sugar creative, and a video
  showing another variant is out of distribution and must be flagged as such (docs/11 sections
  1.4, 4.3).

---

## D-031 - Sentiment where the model can be trusted; emotion only after translation

**Date:** 2026-09-23
**Status:** Accepted (both model downloads approved by the researcher)
**Implements:** docs/04 section 4 (task 5.9), with the coverage rules below added.

**Decision:**
1. **Three texts, scored separately, never averaged into one:** the English translation of the
   speech (5.6), the speech in its own language, and the caption (on YouTube, title plus
   description). Speech and caption sentiment are only weakly related (Spearman 0.25), so
   collapsing them would hide a difference rather than summarise it.
2. **Sentiment:** `cardiffnlp/twitter-xlm-roberta-base-sentiment` (XLM-T, 1.12 GB), kept as
   `compound = P(positive) - P(negative)` in [-1, 1] plus the label and all three probabilities.
3. **Native-language sentiment is produced only inside the model's 8 languages**
   (ar, de, en, es, fr, hi, it, pt). For the other 40 videos (bn, ko, ms, ne, sw, th, tr, vi, zh)
   it is left null with the reason recorded, rather than published as if it were as good. The
   English translation carries the comparable measure for every video that has speech.
4. **Captions outside those 8 languages are scored but flagged** (`caption_lang_covered = False`,
   53 of 291) and are not used as a primary measure. They are kept rather than dropped because
   caption language comes from `langdetect` today and 5.7 will establish it properly; the flag is
   what stops a Korean caption score being read like an English one.
5. **Emotion** (`j-hartmann/emotion-english-distilroberta-base`, 331 MB, 7 emotions) runs **only
   on English text**: the translated speech, and a caption only when it is detected as English.
   It has no manual check among the 60 codes, so it is reported as an unvalidated automated
   measure (D-023's rule), and the methods chapter states that it is measured post-translation.
6. **No text means null, not zero.** 106 videos have no transcript (98 no speech, 6 no
   intelligible speech, 2 silent - D-025), 9 have no caption, 6 have neither. Zero would read as
   neutral, which is a measurement that was not made (the same rule as D-005 for engagement).

**Evidence gathered before trusting any score.**
- **Cross-check (docs/04 section 4):** native vs translated sentiment on the 154 videos with
  both - Pearson 0.946, Spearman 0.929, same three-way label on 86%. docs/04 said high agreement
  would support measuring emotion on the translation; it does, and the caveat stays.
- **The tokenizer warning is a false alarm.** transformers 5.11 warns of "an incorrect regex
  pattern" and advises `fix_mistral_regex=True`. Checked: the default tokenisation matches the
  reference sentencepiece tokenizer exactly, while that flag *changes* it. The flag is not set,
  and the code says why so it is not "fixed" later.
- **Sanity check:** 11 of 11 sentences with obvious sentiment, across 6 languages, scored
  correctly (0.90-0.96 confidence).

**Consequence for analysis - the score shrinks as text grows.** It is a length-weighted average
over 512-token chunks, so a long transcript reads as more neutral: median |score| 0.45 under 200
characters, 0.29 at 200-600, 0.15 at 600-2,000 (Spearman -0.31). So H3 uses the continuous score
with text length available as a covariate; 7.2 checks sentiment against caption length and word
count before either enters a model; and 5.11 treats speech and caption sentiment as two features.

**Environment.** `sentencepiece` 0.2.2 and `langdetect` 1.0.9 installed from prebuilt cp314
wheels (~2.4 MB together, free); torch, numpy, pandas and OpenCV verified unchanged. Without
sentencepiece, transformers 5 picks the wrong tokenizer converter and fails asking for
`tiktoken` - recorded because the error message points in the wrong direction.

**Not done here, and why:** captions are not translated, so caption emotion exists only for the
178 English captions. A translation model would be a new ~2.5 GB download; task 5.16 (keywords)
may need one, and the alternative is per-language keyword lists like the variant screener's.
That is a decision for the researcher when 5.16 runs, not something assumed now.

---

## D-032 - Three proposal features dropped; disclosure settled by the researcher

**Date:** 2026-09-24
**Status:** Accepted (researcher's decisions)
**Resolves:** O-13 and O-01. **Amends:** docs/05 section 3 (the annotation set drops from 9
constructs to 7) and the proposal's Block B and D feature lists.

**1. Three features are dropped** (researcher, 2026-09-24, accepting the recommendation of
2026-09-22). Each was proposed in the original plan; each is dropped for a measured reason, and
the reason belongs in the limitations section rather than in silence:

| Dropped | Why |
|---|---|
| **Voice emotion** | Needs a speech-emotion model this project does not have, and the available ones are trained mostly on English acted speech. A typical Reel carries speech about 6% of the time (5.8), so for most of the corpus there is nothing to measure. Text sentiment and emotion (5.9, D-031) already cover emotional tone for every video with words |
| **`is_sponsored`** | Instagram's paid-partnership flag is missing for 107 of the 150 corpus Reels, and every YouTube Short is posted by a brand channel, so the variable is near-constant where it exists at all. It fails the missing-data rule (docs/05 section 4, rule 2) before any model sees it. **`creator_collab` (5.15) replaces it** - the same idea from collection metadata rather than from an unvalidated label |
| **`campaign_type`** | Abstract, automated-only, and with no manual check among the 60 codes it could never be reported as validated (D-023). The reliability gradient in D-021 predicted it would be the weakest construct. Dropping it before it runs is cheaper than dropping it after |

**Consequences:** 5.12 annotates **7 constructs**, not 9: `has_cta`, `has_influencer`,
`has_celebrity`, `humour_present`, `product_vs_lifestyle`, `ugc_vs_brand`,
`promotional_language`. Four of those have a manual check in the 60 codes and go through the
alpha rule; `product_vs_lifestyle`, `ugc_vs_brand` and `promotional_language` do not and are
reported as unvalidated automated labels (D-023). Three fewer features also helps the 18-20
budget (D-030).

**2. Disclosure (O-01 closed).** The researcher reports there is **no institutional data-ethics
or AI-assistance policy to read** - recorded as the researcher's statement, not as a verified
fact about the institution - and has decided that assistant involvement is not to be mentioned
throughout the project's files.

What that does and does not change:
- **Unchanged and not negotiable (D-010, D-022):** the methods chapter states how the data was
  actually obtained (YouTube Data API, Apify, yt-dlp logged out and logged in, sssinstagram.com,
  the researcher's screenshots) and describes every **automated measurement step** factually -
  speech-to-text, sound events, CLIP embeddings, sentiment and emotion, and the vision-language
  annotation of 5.12, each named with its model and its reliability figure. Those are parts of
  the method, not workflow notes, and they stay.
- **Applied:** writing-assistant involvement is kept out of the published files. The researcher
  moved the planning and diary files to `internal/` (gitignored) on 2026-09-24 and the leak
  check now reads its word list from `internal/screen_words.txt`, so the words are not published
  either. Verified 2026-09-24: no tracked file in the repository mentions the assistant.
- **If the institution does ask** for a statement on assistance, it is a one-line addition at
  submission; nothing in the record needs rewriting, because nothing in the record is false.

---

## D-033 - Music type is not measurable here; whole-image CLIP cannot see the product

**Date:** 2026-09-28
**Status:** Two findings accepted; **one choice open for the researcher** (below)
**Amends:** the proposal's Block B (music type) and docs/05 Block A (`product_visible_frac`,
`time_to_first_product`, `product_mean_area`).

**1. Music type (5.13) is measured and reported as not measurable.** AST's AudioSet genre labels
were run on the 4-second windows 5.8 had already found music in (272 videos; the model was already
on disk, so nothing was downloaded). Seven genre groups were fixed before scoring. The top group's
mean probability has a median of **0.019** and never reaches 0.20 on any video, while the strongest
single label in those windows is the generic "Music" at a median 0.790. On inspection every genre
label sits at 0.01-0.03 - alongside `Fart` 0.04 and `Ice cream truck` 0.05 in the same windows.
A video's top group does win a median 85% of its own windows, but that is consistency, not
validity: the same small bias repeats across windows of one track.
**This is D-028's singing-label finding again**, and the same rule applies - the scores are kept
in the cache and the summary for checking, `music_genre_top` does **not** become a feature, and
music type joins `is_original_audio` and voice emotion (D-032) as a stated limitation.
`music_present` and `music_frac` from 5.8 are unaffected.

**2. Whole-image CLIP cannot measure product visibility (5.4, first attempt).** The existing
embeddings were scored against a product-vs-scene prompt set with the three fixes D-029's failure
implied (mean of the three squares rather than the best; "a dark scene" and "a logo on a sign"
given as non-product options; a threshold-free primary measure). Gates were fixed in the module
before scoring, and **it failed them: AUC 0.419** (95% CI 0.14-0.72), with the five no-product
videos ranking 0.72, 0.94, 0.72, 0.16 and 0.51. Nothing was written to the feature cache.

The cause is visible in the winning prompts: a Reel coded *no product* scores 0.935 because "a
person holding a Coca-Cola drink" wins 94% of its squares - CLIP matches the **scene**, not the
brand - while podcast Shorts that do show a can on the table score 0.06-0.10 because "a close-up
of a person's face" wins. **A product covering a few percent of the frame cannot win a whole-image
comparison.** Prompt wording does not fix that, and the best-square variant is no better (0.485).

**Two limits that hold whatever is chosen next:**
- **The video-level construct barely varies:** 54 of the 59 usable blind codes say a product is
  visible. In a brand corpus "is a product visible at all" is near-constant, so any AUC against
  5 negatives is weak evidence in either direction.
- **H2 needs `product_visible_frac` - how much of the video shows the product - and the 60 codes
  contain no ground truth for it.** Only a frame-level check can validate that, which is what
  docs/05 section 5's "200 hand-coded frames" placeholder always intended.

**Open choice, for the researcher (nothing is used until it is made):**

| Option | What it gives | What it costs |
|---|---|---|
| **A. YOLO fallback** (recommended, with B) | An object detector finds small objects and returns boxes, so `product_visible_frac`, `time_to_first_product` **and** `product_mean_area` become possible. **Brand-blind:** it measures "a drink container on screen", not "a Coca-Cola product", and must be named that way | ~6 MB weights download, free, needs approval; ~1 h |
| **B. Frame-level check by eye** | ~100-200 sampled frames answered yes/no gives the only real validation for a *fraction* measure, and would validate A or any successor | ~15 min of the researcher's time; a labelling pass, like the 125-Short check, not new construct coding |
| **C. Report product visibility as not measured** | Honest and free | H2, RQ4 and 5.17 then rest on the Zero Sugar label alone - itself weakly reliable on YouTube (alpha 0.25, D-029). A real loss for a proposal hypothesis |

Recorded so the decision is visible: option C is defensible and costs nothing, but it removes a
hypothesis the proposal asks about, so it should be chosen deliberately rather than by default.

**Chosen by the researcher, 2026-09-28: A + B - the detector, validated by a frame check.**
What was done the same day:
- **No download was needed.** A COCO-trained YOLO (5.5 MB) already existed on the laptop from an
  unrelated project; it was copied to `models/yolo26n.pt` (gitignored). Nothing was fetched and
  nothing cost money.
- **Detection run on all 9,743 grid frames** in 4.6 minutes (`src/features/product_yolo.py`):
  a container in 23% of frames at the pre-set 0.25, in 242 of 300 videos; `container_mean_area`
  median 7% of the frame; `time_to_first_container` median 4.5 s. Per-frame confidence and area are
  cached so a threshold can change without re-running.
- **The features are named `container_*`, not `product_*`.** The detector is brand-blind: it
  measures a drink container on screen. The frame check quantifies how often that container is
  Coca-Cola's, and that ratio is quoted wherever the feature appears.
- **120 frames drawn for the researcher to answer** (`src/features/product_frame_sample.py`): one
  random grid frame per video, 60 videos per platform, seed 20260928, **drawn before any score was
  computed**; the page (`src/coding/frame_check_app.py`) shows no score, label or box. Three
  answers - Coca-Cola product / other container / nothing - give both the truth the detector can be
  judged on and the truth the study wants.
- **Nothing has entered the feature set.** `src/features/product_validate.py` applies the same
  gates to the frame answers and scores **both** methods on the same frames; it refuses to judge on
  fewer than 40 answers. If the gates fail, option C stands.

**Outcome, 2026-09-29: the gates failed (gate B), so option C stands - see D-037.**

---

## D-034 - On-screen text is found, not read; faces need a model this build does not ship

**Date:** 2026-09-28
**Status:** Accepted (both downloads approved by the researcher, with their sizes, the same day)
**Amends:** docs/04 section 3 (`ocr_word_count`) and docs/04 section 1 (`lang_onscreen`).

**1. OCR runs as a detector only - it finds where text is and never reads it** (EasyOCR's CRAFT,
83 MB). Three reasons, in order of weight:
- docs/04 section 3 already required these features to stay coarse: "sentiment or keyword analysis
  on OCR output across six languages would not survive".
- **Detection is language-free.** Arabic, Korean, Thai and English frames are treated identically,
  which removes exactly the failure docs/04 section 3 warns about - Arabic recognition, RTL and
  cursive script being where OCR breaks.
- Reading the words would need a separate recogniser per script (Latin, Arabic, Korean, Thai,
  Devanagari, Bengali) at 10-30 MB each, and the resulting data would be **unevenly reliable across
  markets** - and market is a grouping variable here, so that noise would not be random (docs/04
  section 2's standing warning).

**Consequences:**
- `ocr_word_count` (docs/04 section 3) becomes **`ocr_region_count`**: a detected region is a line
  or block of text, not a word. Named for what it measures. `ocr_text_frame_frac` and
  `ocr_mean_text_area` are unaffected - neither ever needed the words.
- **`lang_onscreen` (docs/04 section 1, task 5.7) is not measured.** The code-switching flag runs on
  the two fields that exist - spoken language versus caption language, plus 5.6's confidence flags -
  and `src/features/language.py` records `lang_onscreen_skipped` per video so the gap is visible
  rather than implied. If recognisers are ever added, re-running 5.7 fills the field and recomputes
  the flag.
- Text is detected on the **full-resolution** frame, which is what D-024 reserved full resolution
  for.

**2. Faces come from a 230 KB model, fetched once.** mediapipe 0.10.35 is the tasks-only build: it
ships **no** bundled models, so BlazeFace short-range was downloaded to `models/`. The alternative
needing no download was OpenCV's 2001-era Haar cascade, which misses profiles and small faces; the
researcher chose the model, and `face_conf_mean` is kept per video so a weak run would be visible
rather than silent. Result: 262 of 300 videos show a face somewhere, 155 in most frames - which is
what brand advertising should look like.

**3. What the boxes showed when inspected, and what it changes.** The detector was checked by
drawing its boxes on frames: every box was real text, including on the busiest frame (a mock
phone-chat screen). But it finds the **Coca-Cola logo and the legal small print** as readily as a
subtitle, and those are present in almost every frame of an advert - so `ocr_text_frame_frac` is
near-constant (**123 of 300 videos exactly 1.000**). Consequences: `ocr_text_frame_frac` is a
pruning candidate, `ocr_region_count` and `ocr_mean_text_area` carry the real variation and go
forward, and any statement about "on-screen text" in the results must say it includes brand marks
and disclaimers, not only viewer-facing captions.

**4. Also recorded from the same session:** `red_frame_frac` has a median of 1.000 on both platforms
(nearly every frame carries some Coca-Cola red) and is a pruning candidate before modelling starts;
the continuous `red_ratio` is the version to keep. No colour or busyness pair correlates above 0.85,
so none is dropped yet - 7.2C re-checks with every feature present. **Two near-constant features
found the same day** (`red_frame_frac`, `ocr_text_frame_frac`) is a reminder that "share of frames
with X" saturates in brand advertising, where X is usually always there; the continuous and count
versions are the informative ones.

---

## D-035 - Keyword matching: no accent folding, and "not searched" is not a zero

**Date:** 2026-09-28
**Status:** Accepted
**Amends:** docs/04 section 5.1, the keyword list the researcher approved on 2026-09-24 (the list
itself is unchanged; these are matching rules).

Task 5.16 ran on all 300 videos with the six approved groups. Three rules had to be settled while
implementing it, and each is recorded in docs/04 section 5.1's amendment table:

1. **Matching is case-insensitive and NFKC-normalised but not accent-folded.** Section 5.1 said
   accent-insensitive. Folding would break Vietnamese, where accents carry meaning - `mới` ("new")
   folds to `moi`, which collides with `môi` ("lips"). Accented and unaccented spellings are listed
   explicitly instead, which is what `zero_sugar.py` already does for Spanish and Portuguese.
2. **Word boundaries for Latin-script terms; substring for Thai, Korean, Hindi and Arabic.** Thai
   and Korean have no spaces between words and Hindi and Arabic attach matras and clitics, so a
   boundary match would find almost nothing. Same choice as the variant screener.
3. **Short words that over-match are used only inside phrases** - "free" would match *sugar free*,
   "back" *back to school*, "live" *live your life*, and "goal", "match" and "final" would fire on
   football talk in a video about a concert. Precision over recall, as `zero_sugar.py` states: a
   false hit is invisible downstream, a miss is recorded as a miss.

**Result:** `kw_event` 104 videos, `kw_together` 86, `kw_taste` 53, `kw_zero_sugar` 53, `kw_new` 37,
`kw_offer` 18. Median one group per video; 69 videos hit none.

**Two things to carry into the analysis:**
- **`kw_event` is three times more common on YouTube than Instagram (78 vs 26)** because the
  YouTube corpus is built around the 2026 FIFA World Cup campaign. That is corpus composition, not
  a platform effect, and it is stated wherever the feature is used.
- **"Not searched" is null, never False.** 17 videos have neither an English transcript nor a
  caption in a covered language, and `kw_zero_sugar` has 10 more because its vocabulary covers a
  different language set (it reuses `ZERO_TERMS`: en, es, pt, ar, th, id, hi - so Turkish,
  Vietnamese and Korean captions are not searched for it). `kw_*_searched` records which text was
  searched for every video, so a missing measurement can never be read as an absent keyword.

**Spot-checked before use**, as section 5.1 requires: matched terms printed per group, and the
Korean, Thai and English hits land where they should. Every hit stores the term behind it.

---

## D-036 - The feature set: 20 features, fixed in order before any outcome was seen

**Date:** 2026-09-28
**Status:** Accepted
**Implements:** tasks 5.10 and 5.11 against the 18-20 budget of D-030 and the five rules of
docs/05 section 4. **Amends** docs/04 section 5.1 (six keyword flags become three features).

**1. One feature table (5.10).** `data/processed/features.parquet`, 300 rows, 76 candidate
features, assembled from the per-video caches by `src/features/assemble.py`. The candidates are
**listed explicitly in the code** rather than swept from the caches, because the caches also hold
transcripts, per-window scores and file paths that are working material, not features.
**No engagement column is in the table** - the script fails if one appears - and it is joined only
when a model is fitted, after docs/08 section 7.9's analysis begins.

Two Block E features are deliberately absent, and the reasons matter:
- **`account_prior_engagement`** is built from *other videos' engagement*, so it can only be
  computed inside cross-validation folds (Phase 9). Computing it here would put the outcome in the
  feature table.
- **`posting_hour_local`** needs each market's timezone, which the data does not carry.
  `posting_hour_utc` and `is_weekend_utc` stand in, and the limitation is stated: 9 a.m. in Bangkok
  and 9 a.m. in Sao Paulo are the same UTC hour and different local moments.

**2. Pruning (5.11) applied rules 1, 2 and 4 only - and stopped there on purpose.**
Rule 3 (alpha < 0.67) needs task 4.2, which needs 5.12's automated labels. **Rule 5 reads the
outcome**, so it belongs inside training folds in Phase 9 and must not run now. Correlations and
constancy were measured on the **focus set (183 usable Zero Sugar videos)**, the sample the models
will use. Full record with every drop and its reason: `reports/feature_pruning_record.md`.

A **rule 0** was added ahead of the others: 17 features whose fate was already decided elsewhere
(D-024's `aspect_ratio` and `fps`, D-026's `scene_count`, D-034's `red_frame_frac` and
`ocr_text_frame_frac`, docs/05 Block A's "pick 1-2" for brightness/contrast/saturation, and the
spread and extreme variants of kept means). Each drop cites where it was decided, so none is
re-argued here.

**3. Structural missingness is routed, not imputed.** A video with nobody talking has no sentiment,
no words per minute and no voice pitch. That is not a gap to fill - it is a property of the video.
So 11 speech-dependent features go to a **speech-only sub-analysis** (the 117 focus videos with
speech), features where zero is the true measurement (`talk_dur_frac`, `music_frac`) stay in the
main model, and platform-only features (`title_char_len*`, `creator_collab`) enter only that
platform's models, as section 4.0 rule 3 requires.

**4. The keyword flags become three features, and two of them make the cut.** Applied strictly by
correlation and constancy, all six keyword flags fell outside the budget - which would have meant
the proposal's Block C keywords, and part of H6, had no instrument at all. Rather than let a
budget silently delete a research question, `kw_offer`+`kw_new` merge into **`kw_promotional`** and
`kw_taste`+`kw_together` into **`kw_experience`** (null-safe: True if either hit, False only if both
were searched and neither hit, null if neither was searched). `kw_event` stays separate as the
largest group. They rank above `spectral_centroid_hz` and `tempo_bpm`, which **docs/05 Block B
itself marks doubtful** and which D-028 found unrelated to whether music is present.

**5. The final set is the top 20 of a priority order fixed now**, each entry tied to the hypothesis
or control that needs it:

duration, cuts per second, motion, face presence, face area, edge density, colourfulness, red
ratio, on-screen text regions, text area, music share, talking share, loudness, loudness range,
caption sentiment, caption length, hashtags, emoji, `kw_event`, `kw_promotional`.

**Seven sit in an ordered reserve** (`kw_experience`, `spectral_centroid_hz`, `tempo_bpm`,
`kw_zero_sugar`, `is_code_switched`, `mention_count`, `longest_shot_frac`). They enter **only** if
a keeper is removed by rule 3 once the automated labels exist, strictly in that order. Nothing
below the line can be promoted after a result is seen, and rule 5 may only drop further inside
folds - never add. That is what stops the feature set being chosen by what happens to work.

**Still to come into this record:** 5.12's automated labels (week 4) and 5.4's `container_*`
features, if the frame check's gates pass (D-033). Both require 5.10 and 5.11 to be re-run, and
the record to be rewritten with a new date.

---

## D-037 - Product visibility is not measured: the container detector failed gate B

**Date:** 2026-09-29
**Status:** Accepted - the outcome D-033 fixed in advance for a failed gate (option C)
**Closes:** task 5.4 and its validation 5.4v. **Cancels** task 5.17 as specified (it needed 5.4).

**What was run.** The researcher answered all 120 sampled frames on 2026-09-29 (37 Coca-Cola
product, 1 other drink container, 82 nothing; Instagram 20/0/40, YouTube 17/1/42).
`python -m src.features.product_yolo --validate` then applied the three gates fixed before either
method was scored. Report: `reports/product_detection_validation.md`.

| Gate | Result | Required | Pass |
|---|---|---|---|
| A. Frame-level AUC, container visible | **0.748** (95% CI 0.66-0.84) | >= 0.70 | yes |
| B. The five blind-coded no-product videos in the bottom half | ranks 0.60, 0.10, 0.36, 0.24, 0.10 | all <= 0.50 | **no** |
| C. Not near-constant (10th-90th spread) | 0.745 | >= 0.10 | yes |

**Gates A and B both decide, so the verdict is a fail.** Following D-033, product visibility is
reported as **not measured**; the `container_*` features do not enter the feature table; H2, RQ4
and 5.17 rest on the Zero Sugar label alone, which is itself weakly reliable on YouTube (alpha 0.25,
D-029). No threshold was moved and no gate was re-run.

**Why gate B failed, recorded so the limitation is described accurately.** One video fails it:
YouTube `eKBjm4_DiQA`, container in 19% of its frames (rank 0.60, just above the median of 0.13).
Its frames were inspected after the verdict: from about 17 s it shows a **Coca-Cola-branded
fountain cup** - small in a meal offer, then filling the frame. The detector is not wrong about what
is on screen. The blind code (`no_product`) is not wrong either: the codebook defined *no product*
as "no Coca-Cola **pack**" (a can or bottle). The two measure different things - the detector any
drink container, the codebook a pack - and gate B was written to catch exactly that kind of
mismatch. Re-coding the video, or re-defining the gate after seeing which way it went, would be
choosing the truth to fit the result, so neither was done. Gate B rests on only five negatives,
which D-033 already said is weak evidence in either direction; that weakness cuts both ways and is
not a reason to set the gate aside.

**What the frame check showed anyway, for the limitations section:**
- At the pre-set threshold 0.25 the detector flagged 32 of 120 frames: **precision 69%**, recall
  58%. Missed frames are small, blurred or partly out of shot.
- Of the 38 frames the researcher saw a drink container in, **37 (97%) were Coca-Cola's** - in this
  corpus a container on screen is almost always the brand's.
- **Whole-image CLIP ranked frames better (frame AUC 0.844) than the detector (0.748)** on the same
  120 frames. That does not reopen the first attempt: CLIP failed gate B far worse (no-product
  videos at 0.72 and 0.94, D-033), and a method that orders single frames well but puts product-free
  videos near the top cannot give a trustworthy share-of-video measure. Recorded because it is true
  and a reader of the report will see it.

**What stays.** The per-frame scores and `data/interim/container_summary.csv` are kept for
checking, as with music type (D-033). The 120 answers stay in `docs/product_frame_check.csv`.
**5.17 is cancelled as specified** (a `product_focus` threshold on a validated 5.4 measure). The
only remaining route to product-vs-lifestyle is 5.12's automated `product_vs_lifestyle` label,
which has no manual code to check it against and so, under 4.2's rule, can only be reported as
unvalidated. **5.10 and 5.11 need no re-run for 5.4** - no feature was added - and are re-run after
5.12 as D-036 already requires.

---

## D-038 - Automated labels: pilot rule, reliability rule and where passing labels enter, fixed before any model ran

**Date:** 2026-09-29
**Status:** Rules accepted and written **before any model produced a label**; results appended below
**Implements:** 5.12 (seven constructs, D-032), 4.2, and 5.11 rule 3.

**Models.** The researcher approved downloading two free vision-language models on 2026-09-29 and
declined a third (Gemma 3 4B, which carries Google's own terms): **Qwen3-VL 4B** (`qwen3-vl:4b`,
3.3 GB) and **Qwen2.5-VL 3B** (`qwen2.5vl:3b`, 3.2 GB), run locally in Ollama (already installed;
nothing paid). Code: `src/features/annotate.py`.

**Questions.** The four constructs with a manual check use **the codebook's own wording**, imported
from `src/coding/codebook.py`, so the model and the researcher answer the same question. The three
without one (`product_vs_lifestyle`, `ugc_vs_brand`, `promotional_language`) have definitions
written in the same style, in the module, before any model ran. `ugc_vs_brand` is defined as the
**look** of the video (phone-shot vs produced), not who posted it - every YouTube Short and most
Reels are posted by brand accounts, so "who posted it" would be near-constant.

**Input.** Six grid frames evenly spaced in time (longest side 768 px), the account name, the
caption (YouTube: title + description, up to 1,500 characters) and the English speech translation
(up to 1,500 characters). **No OCR text**, amending docs/05 section 3: 5.5 part B detects text and
reads none (D-034), so the model reads on-screen text from the frames. Temperature 0, seed
20260929, answers forced into a JSON schema that allows only the listed options; every raw answer
is kept.

**Pilot rule.** 10 of the researcher's 60 coded videos, 5 per platform, seed 20260929
(`data/interim/annotation/pilot_sample.csv`, drawn before any model ran). The winner has the
highest agreement with the researcher on the four checked constructs; a model answering "unsure"
counts as not agreeing (no winning by abstaining); pairs the researcher marked "unsure" are left
out. Ties: more valid answers, then faster. The prompt is not tuned on the pilot's results.

**Reliability rule (4.2).**
- Krippendorff's alpha, nominal, researcher vs model, per checked construct.
- **Primary: the 50 coded videos the pilot did not use**, so the chosen model is judged on videos
  it was not chosen on. All 60 are reported as well.
- "Unsure" on either side is treated as missing, and the count is reported. If the model says
  "unsure" on more than 20% of a construct's videos, the construct fails, so it cannot pass by
  abstaining.
- 95% interval from 2,000 bootstrap resamples of videos.
- **The construct is dropped if the point alpha is below 0.67.** If alpha cannot be computed
  (only one answer occurs), it is not validated and is dropped.

**Where passing labels enter the feature order (5.11 rule 3)** - fixed now, before alpha is known:
- `auto_has_cta` (H5), then `auto_has_celebrity` and `auto_has_influencer` (H4) are inserted
  **directly after `sentiment_caption`**, in that order, if they pass. They are the instruments
  of two proposal hypotheses, and D-036's order ranks hypothesis instruments above generic counts.
  Each one inserted pushes the lowest of the 20 to the head of the reserve.
- `auto_humour_present` (Block D, no hypothesis) goes **to the head of the reserve** if it passes.
- **The three unchecked labels never enter a model.** They are kept as columns, described as
  unvalidated automated labels (D-023), and may be tabulated descriptively.
- A construct that fails is recorded under rule 3 in the pruning record, with its alpha.

**Pilot result, 2026-09-29** (`reports/annotation_pilot.md`): **Qwen3-VL 4B chosen by the rule** -
agreement with the researcher on the four checked constructs 70% (26 of 37 pairs) against 62%
(23 of 37) for Qwen2.5-VL 3B, and about four times faster (median 23 s vs 100 s a video). Per
construct the picture is mixed and ten videos decide nothing about reliability: Qwen2.5-VL matched
all 10 celebrity answers but only 1 of 8 humour answers; Qwen3-VL 8/10 and 7/8. That is 4.2's job.

**Three things found while setting up, recorded because they affect how the labels are described:**
- **Qwen3-VL reasons before it answers**, and on one pilot video (`Qd_mTNyMYiM`) the reasoning
  filled the 6,144-token window, so it returned nothing - counted against it in the pilot. The
  window was raised to **10,240** before the main run. With temperature 0 this changes no answer
  that already fitted; it costs speed (about 20% of the model now sits in main memory). Answers
  that still hit the limit are recorded as missing, flagged `done_reason = length`, and counted.
- **The labels are close to, not exactly, repeatable.** Three uncoded or pilot videos asked three
  times each: identical seven answers in 8 of 9 runs; the exception (a first run with a different
  reasoning length) differed on 2 of 7 labels. Reported as a limitation; the cache keeps the answer
  actually used.
- **One smoke test was run on a coded, non-pilot video** (`C4Meop_AIdj`) by mistake, before the
  pilot. Its answer was not compared with the researcher's code, nothing was changed because of it,
  and the main run labels it afresh. Recorded so the held-out claim is exact.

**Change of set-up, 2026-09-29 - reasoning switched off, and the pilot re-run under a rule written
first.** The main run was stopped after 7 of the 60 coded videos: Qwen3-VL's reasoning ran away on
some videos (one took 520 s and still returned nothing), which put 300 videos at a day or more with
failures. The fix is to switch the model's reasoning step off (Ollama `think: false`). **That is not
the set-up the pilot chose**, so it was not swapped in silently. Rule, written before the re-run:
Qwen3-VL with reasoning off labels the **same 10 pilot videos** with the same prompt; it is used
only if its agreement on the four checked constructs is **at least Qwen2.5-VL's 62% (23 of 37)**,
ties going to the faster model as before; otherwise Qwen2.5-VL 3B is used. The 7 labels from the
stopped run are discarded. 4.2's held-out alpha remains the real check whichever model is used.

**Re-run result:** with reasoning off, Qwen3-VL answered in 2.9 s a video but agreed with the
researcher on **57% (21 of 37)**, below 62%. **By the rule, Qwen2.5-VL 3B labels the corpus**
(`reports/annotation_pilot_no_reasoning.md`). One more Ollama 0.32.5 quirk was found on the way: with
reasoning off and a JSON schema, the model's answer is filed under the "thinking" field rather than
the answer field; the code reads it from there (same text, only the field differs).

**A GPU fault found in the first Qwen2.5-VL run, and how it is contained.** The first run over the
60 coded videos returned **no valid answer at all** and was stopped. Cause, from Ollama's server log:
on some videos the GPU arithmetic overflows, the model emits only "@" (the classic sign of invalid
numbers), and Ollama's answer-format check crashes on it. Worse, Ollama reuses cached state between
requests, so **one such video poisons every later request** until the model is reloaded - which is
why a pilot video that answered normally on its own failed when it came after a bad one. A fresh
server did not help; a reload between requests did. The fix: when a reply comes back blank, the
model is unloaded and the identical request is sent once more to a clean model; if it still fails,
the video is recorded as missing (never guessed) and the model is unloaded again so it cannot
poison the next one. Each video records whether it needed the reload. Checked: after the fix a pilot
video gave the same answer as in the pilot. Two approaches that did not work are recorded for
completeness: plain JSON mode (crashes the same way) and no format at all (the model writes only
"@@@@").

**4.2 result, 2026-09-29: all four checked labels fail and are dropped** (`reports/annotation_reliability.md`).
Qwen2.5-VL answered 54 of the 60 coded videos (6 blank even on a clean model - including 2 pilot
videos that had answered in the morning, so the fault is not tied to particular videos alone).
Primary sample, the 50 coded videos the pilot did not use (46 answered):

| Construct | Pairs | Raw agreement | Alpha | 95% CI | Researcher yes / model yes | Kept? |
|---|---|---|---|---|---|---|
| `has_celebrity` | 41 | 80% | 0.100 | -0.16 to 0.48 | 9 / 1 | no |
| `has_influencer` | 39 | 77% | 0.382 | 0.03 to 0.69 | 30 / 29 | no |
| `has_cta` | 46 | 48% | -0.032 | -0.33 to 0.23 | 11 / 35 | no |
| `humour_present` | 7 | 57% | 0.133 | -0.62 to 0.71 | 3 / 6 | no (model "unsure" on 38 of 46) |

All 60 give the same picture (0.118, 0.364, -0.033, -0.044). The failures are not narrow: the model
calls almost every video a call to action (it agrees with the researcher less often than chance),
misses 8 of the 9 celebrities, and declines to judge humour. The counts were re-checked directly
against the codes file before being reported.

**Consequences, as fixed above before alpha was known:** no automated label enters any model; the
20-feature set is unchanged; the three unchecked labels stay as unvalidated columns. **H5 has no
validated instrument** (docs/08 required `has_cta` to pass). **H4 keeps only `face_present_frac` /
`mean_face_area`** - human presence, not celebrity or creator presence. Humour is not measured.
These join music type and product visibility as stated limitations.

**Not done, and why:** Qwen3-VL with reasoning on won the pilot and was set aside for speed, not
quality. Trying it now on the same 50 held-out videos would be choosing a model after seeing the
test result, and its alpha would no longer be a fair check. That would need new, unseen coded
videos. The researcher can decide whether that is worth it; the default is to accept the result.

**Full run, 2026-09-29: 280 of 300 videos answered, 20 recorded as missing** (blank even on a clean
model; never guessed). The first attempt at the long tail stalled when one request hung for 91
minutes; requests now have a hard 3-minute limit, a hung attempt is the only kind re-tried (that
video then failed normally), and a run stops itself after 8 failures in a row. Finished attempts
are never re-run, so the labels 4.2 was computed on are exactly the stored ones (checked: 0
differences). Answer shares across the 280 show the same leaning as on the coded videos - call to
action "yes" 226, sales language "yes" 259, humour "unsure" 222, celebrity "yes" 7.
**5.10 and 5.11 re-run:** 7 `auto_*` columns in `features.parquet`, all dropped from modelling by
rule 3 as fixed above; **the 20 features and the 7 in reserve are unchanged.** Only rule 5 (inside
training folds, Phase 9) remains.


---

## D-039 - The Instagram check (2c.R2) is done before exploration; the José vs Mourinho answers stand

**Date:** 2026-09-29
**Status:** Accepted (researcher's answers in chat, 2026-09-29); 2c.R2 answers pending

**2c.R1 - the 36 *José vs Mourinho* Shorts: the 22 September answers stand, and the task stays
open.** Asked in chat whether a re-look had been done, the researcher first wrote "there is no zero
sugar". Because that would have reversed 17 of the researcher's own 22 September answers and taken
15 usable Shorts out of the study (analysis set 183 -> 168, YouTube 72 -> 57, the global channel
58 -> 43), the consequence was put back to the researcher before anything was changed. The
researcher chose **"No, keep 22 Sep answers"** - there was no video-by-video re-look. Nothing was
changed. Recorded as given in chat, 2026-09-29. The weak repeat reliability of the YouTube label
(alpha 0.25, D-029) is unaffected and is still reported with every Zero Sugar result.

**2c.R2 - Instagram's 37 regular Reels: the researcher chose to check them now.** The 37 are the
systematically drawn Reels that text does not name Zero Sugar (`corpus_reason = regular_fill`).
They were appended to `docs/zero_sugar_visual_check.csv` as orders 126-162 (`python -m
src.screen.zero_sugar_check --instagram`): never-seen first, the 9 blind-coded last, random within
each group (seed 20260929), one frame per shot, the same question and page as the YouTube check
(`python -m src.coding.zero_sugar_check_app`, now wording "this video"). **The 125 YouTube rows and
their answers were verified unchanged**, and the frozen copy
`docs/zero_sugar_visual_check_pass1_20260922.csv` was not touched. The page shows no score,
label or earlier code.

What happens with the answers is already registered (docs/08 section 7.9, 7.9.5): labels re-applied
with `src/screen/zero_sugar_labels.py`, the analysis table re-frozen with a dated row in section 6,
and, **if Instagram's systematic Zero Sugar cell reaches at least 20 videos from at least 3
accounts, the 7.5(c) "without hand-picked Reels" comparison is run as first registered**. The 9
blind-coded Reels give a small repeat check against the researcher's earlier codes.

**Order of work - the focus set is frozen before exploration looks at engagement.** The researcher
said "go" for Phase 7 the same day. Exploration waits for the 37 answers and the re-freeze: if the
list of analysed videos could still change after engagement had been charted, any change would
look like - and could be - inclusion chosen by the results.

**Result, 2026-09-29.** The researcher answered all 37 (12 Zero Sugar, 25 not, 0 unsure; all 37
within two minutes, about 3 seconds each - the same pace as the 125-Short check). Read-only copy
`docs/zero_sugar_visual_check_pass2_20260929.csv`. Labels re-applied, table rebuilt and re-frozen
(docs/08 section 6, `ba6f0a2d...`), backups `*_before_D039_20260929.parquet`:
- **Focus set 183 -> 192 usable** (Instagram 111 -> 120 from 17 accounts; YouTube 72 unchanged).
  Only `is_zero_sugar`, `zs_label_method` and `in_focus` changed, all on the 37 Reels; **no
  engagement value changed**, checked without display.
- **Contingency not met:** Instagram's systematic Zero Sugar cell is **15 usable videos from 9
  accounts**, short of 20, so 7.5(c) stays unrun and the within-Instagram comparison stays
  descriptive (105 hand-picked vs 15 systematic, no test).
- **Repeat check is poor: 4 of the 9 blind-coded Reels agree with the 15 September codes, alpha
  -0.10** (3 blind "Zero Sugar" now "not", 2 blind "other Coca-Cola" now "Zero Sugar"). Nine
  videos is a small check, but it points the same way as YouTube's 0.25: **the by-eye Zero Sugar
  label is weakly reliable on both platforms**, and it decides inclusion for 12 of these Reels.
  The answers stand as given (as in D-029); the figure is reported with every Zero Sugar result.
- 5.10 and 5.11 re-run on the 192: same 20 features and 7 in reserve; only percentages moved.

---

## D-040 - What exploration decided: emotion collapsed, log cuts, no paired analysis, market not a term

**Date:** 2026-09-29
**Status:** Accepted
**Implements:** Phase 7 (tasks 7.1-7.3) and docs/07 section 4. Run on the table frozen that day
(192 focus videos, 22 accounts) by `src/eda/explore.py`; findings in docs/07 section 3, numbers in
`reports/eda_numbers.md`, figures in `reports/figures/`.

**Every rule below was set from counts or feature distributions, not from which option gives a
stronger engagement result.** No test, p-value or model was run.

1. **Emotion (H3) is collapsed by count:** labels with fewer than 10 focus videos merge into
   "other" - joy 25, neutral 67, surprise 15, other 12 (disgust 5, fear 3, anger 2, sadness 2).
   Emotion exists only for the 119 focus videos with speech and stays in the speech-only analysis.
2. **`cuts_per_sec` enters every model as log1p(cuts_per_sec)** (TODO 7.2): one real montage at
   9.68 cuts a second against a next-highest 1.78; skewness 10.2 raw, 1.7 after the transform. The
   montage stays in (D-026).
3. **The paired cross-platform analysis (task 8.3) is not viable and is closed:** 2 cross-posted
   pairs by a rule fixed before looking (frame-embedding cosine >= 0.95, durations within 1 s)
   against the 20 required.
4. **Market is not a model term:** 16 of 19 markets have one account, so market duplicates the
   account random intercept.
5. **Confirmed, unchanged:** no collinearity drop (max VIF 3.6); the percentile DV and its median
   split (100 / 92, the docs/06 section 4 fallback not triggered); no account excluded (the global
   channel's 30% is what the pre-registered sensitivity analysis 7.9.3(d) is for).

**What exploration showed that the write-up must carry** (descriptive only):
- the platform gap in follower-normalised engagement (median log10 -2.55 Instagram vs -4.32
  YouTube) comes with a complete overlap of platform, selection route (all hand-picked videos are
  Reels) and account size (YouTube's large tier is one channel) - it answers nothing about platform;
- age overlaps platform too (YouTube Shorts mostly 50-100 days old);
- `kw_event` is lower-ranked, and 31 of its 46 videos are YouTube Shorts from the FIFA campaign.

---

## Open decisions

| ID | Question | Blocking | Needed by |
|---|---|---|---|
| O-01 | ~~Guide approval for scraping~~ — ~~read the institutional data/ethics policy and record the finding~~ — **closed 2026-09-24 by D-032:** the researcher reports no such policy applies, and decided how assistance is handled. The factual methods description (D-010) stands unchanged. | — | Closed |
| O-02 | ~~Zero Sugar only, or brand family?~~ - **resolved by D-014: brand family, variant as a feature, Zero Sugar retained and measured.** | - | Closed |
| O-03 | Apply to Meta Content Library as a backup route? Lead time is weeks. | No | Week 1 if at all |
| O-04 | ~~Creator content in scope?~~ — **resolved by D-009: yes, brand + sponsored creators.** | — | Closed |
| O-05 | Create the IG Business + FB Page + Meta app chain? **Now recommended** (D-010) — ~40 min, free, removes the ToS question from the critical path. | No | Before IG collection |
| O-06 | ~~India + Indonesia have no market YouTube channel~~ - **resolved by D-012: keep both, Instagram-only.** | - | Closed |
| O-07 | ~~Mexico industry-body channel in scope?~~ - **resolved by D-012: kept, marked `channel_type=industry_body`.** | - | Closed |
| O-08 | ~~Indonesia is age-gated and yields nothing cookieless~~ - **resolved 2026-09-15 without O-05:** 5 Indonesian Zero Sugar Reels entered via the researcher's logged-in view, sssinstagram.com downloads and transcribed screenshots (D-018). | - | Closed |
| O-09 | ~~Instagram account list~~ - **resolved by D-015: 41 accounts in `docs/accounts_instagram.csv`.** | - | Closed |
| O-10 | ~~New IG accounts from the curated list~~ - **closed 2026-09-15: all three verified (D-018).** | - | Closed |
| O-11 | ~~DV window vs a mostly-2026 corpus~~ - **resolved by D-019: include 2026, 7-day rule.** | - | Closed |
| O-12 | ~~Which model makes the 8 annotation labels?~~ - **resolved by D-021: free local model on the researcher's RTX 3050 GPU, validated by alpha.** | - | Closed |

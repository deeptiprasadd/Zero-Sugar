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

## D-041 - The modelling plan after the 1 October meeting: high/low target, one pooled model split by platform, MLP kept

**Date:** 2026-10-01
**Status:** Accepted
**Source:** the researcher's answers in chat on 2026-10-01 to the four questions of the meeting
handout (`modelling-meeting-handout.docx`, 30 Sep). For two of them the researcher's answer was to
follow the proposal (`coco-cola-proposal.docx`, read only); what the proposal says is quoted so the
reading can be checked. Recorded as the researcher's answers, not as the supervisor's words.

| Question | Answer | Basis |
|---|---|---|
| 1. High vs low as the main target, continuous score for the regression? | **Yes.** `engagement_high` is the machine-learning target; the continuous percentile is the outcome of the mixed-effects statistics | Researcher: "according to the proposal". The proposal's dependent variable is "High-engagement vs Low-engagement", with engagement normalised "within each platform", and its evaluation section is a classification one (F1, PR-AUC, ROC-AUC, confusion matrix, threshold optimisation) |
| 2. Instagram-only model, YouTube described without one? | **One pooled model, explained separately for each platform; an exploratory Instagram-only model; no YouTube-only model** | Researcher: "according to the proposal". The proposal asks whether predictors differ between platforms (RQ7, H9, H10; SHAP section: "Are their effects different on YouTube and Instagram?") but never asks for a model per platform. A YouTube-only model cannot be tested fairly: 72 videos in 5 channels, 58 from one, so account-grouped folds collapse and the minimum detectable correlation is 0.33 even with no account clustering |
| 3. Call to action and celebrity - not measured, or hand-code more? | **Reported as not measured** | Researcher. H5 has no instrument; H4 rests on face presence only (D-038) |
| 4. Keep the neural network (MLP)? | **Kept**, reported honestly if it loses; still first in the cut order if the schedule slips | Researcher |

**Applied the same day:** docs/09 (section 0 added, section 5 rewritten, n=192 / 22 accounts, fold
balance around the global channel), docs/10 (per-platform section rewritten; dependence plots
without product visibility), docs/08 section 6 power table filled.

**Power, computed before any test** (`python -m src.stats.power`, `reports/power_analysis.md`): at
80% power the pooled focus set detects a yes/no difference of d 0.41 and a correlation of r 0.20 if
accounts did not matter (ICC 0), rising to d 0.77 / r 0.37 at ICC 0.1 - a cautious upper bound,
since most features vary within accounts. Instagram alone: d 0.52 / r 0.25 at ICC 0. YouTube alone:
r 0.33 at ICC 0, unusable at any realistic ICC. **Only medium-to-large effects are detectable;
platform differences in predictors only if very large** - so H9 and H10 stay estimates with
intervals, and every null is reported as "not detected at this sample size" with these values.


---

## D-042 - Phase 8 specification: exactly which test decides each hypothesis, fixed before any test

**Date:** 2026-10-01
**Status:** Accepted - **written before any hypothesis test or model was run** (researcher's go for
Phase 8, 2026-10-01). docs/08 sections 1-3 name the kind of test for each hypothesis; this entry
pins the variables, the decisive test and the family, so no choice can follow a result. The
platform comparison (H7) is run exactly as docs/08 section 7.9 registers it and is not re-specified
here. Code: `src/stats/hypotheses.py`; output `reports/statistical_results.md`.

**Sample.** Focus set, `in_focus & dv_status == "ok"`: 192 videos, 22 accounts (table frozen
2026-09-29, docs/08 section 6). Every result carries the Zero Sugar label's repeat reliability
(YouTube alpha 0.25, Instagram -0.10).

**Outcome.** H1-H6 and H8: `engagement_pct`, the continuous percentile (docs/08 section 2; D-041).
H7, H9, H10: as registered - H7 on `log10(engagement_rate_follower)` (7.9.2); H9/H10 on the
percentile, exploratory.

**Model.** `statsmodels.MixedLM`, random intercept per account. Coefficients from REML fits;
likelihood-ratio tests from ML fits of nested models on the same rows. **Controls in every
H1-H6/H8 model:** `platform`, `log10(followers)`, `log10(video_age_days)`. Region and language are
left out: they vary between accounts, which the random intercept absorbs (as 7.5(a) argues), and
market duplicates account (D-040). Continuous predictors are z-scored; coefficients are reported in
percentile points per SD, with the standardised beta (coefficient / SD of the outcome).

**Feature handling, fixed now.** `mean_face_area` = 0 where no face appears (all 22 missing values
are exactly the 22 no-face videos, so 0 is the true area, not a guess). `cuts_per_sec` as log1p
(D-040). Caption length as log1p(characters), z-scored **within caption language** where the
language has 5+ focus videos, otherwise against the whole set (docs/05 Block C). Remaining gaps
(keywords not searched 9, caption sentiment 7, loudness 2, motion 1) -> complete cases, **179
videos**; a sensitivity re-run with median imputation is reported beside every model that drops rows.

**Decisive tests (the confirmatory family, Benjamini-Hochberg at q = 0.05, docs/08 section 3):**

| H | Test 1 | Test 2 |
|---|---|---|
| H1 duration | LR test of duration + duration^2 (both z) added to the controls model | Spearman, duration vs percentile, pooled |
| H2 product visibility | **not tested** - not measured (D-037) | - |
| H3 positive emotion | MixedLM coefficient of caption sentiment (the text every video has; D-036 priority) | Kruskal-Wallis, percentile across the collapsed speech-emotion groups joy / neutral / surprise / other (D-040), 119 speech videos, epsilon^2 |
| H4 people on screen | LR test of `face_present_frac` + `mean_face_area` added to the controls model | Mann-Whitney U, any face vs none (170 vs 22), rank-biserial r. Celebrity / creator presence not measured (D-038) |
| H5 call to action | **not tested** - no validated instrument (D-038) | - |
| H6 text | LR test of the text block - caption length (within-language z), hashtags, emoji, `kw_event`, `kw_promotional` - added to the controls model | Spearman, caption length and hashtags vs percentile (two tests) |
| H7 platform | 7.9.3(a) platform coefficient, verdict by 7.9.4 | (a2), (b), (c), (d) as registered - robustness, not in the family |
| H8 joint predictive power | LR test: controls model vs controls + all 20 content features | Per-block LR tests (video, audio, text) - reported, in the family |

Per-platform Spearman for H1 (docs/08 section 1 asks for it) is reported with intervals as a
description, outside the family. **H9** (feature x platform, one model per feature, each of the 20)
and **H10** (duration x platform) are exploratory: estimates with 95% intervals, outside the family,
never called significant (7.7, 7.9.7).

**Assumption checks (docs/08 section 5), run and reported, decisions fixed now:** residual
normality (Q-Q, Shapiro-Wilk) - the percentile is bounded, so non-normal residuals are expected; if
present, each H1-H6 conclusion is confirmed against its rank-based test 2, and disagreement is
reported, not resolved by choice. Account variance near 0 (ICC < 0.01) -> the OLS fit is reported
beside it. VIF already max 3.6 (D-040). The platform comparison's registered robustness on the
wider 290-video set (7.5(a) with `is_zero_sugar`) is run and reported as robustness only.

**Wording of results, fixed now:** "associated with", never "causes"; a BH-adjusted p >= 0.05 is
"not detected at this sample size" with the minimum detectable effect from `reports/power_analysis.md`.


---

## D-043 - Phase 8 results: one association, between accounts; no other hypothesis detected

**Date:** 2026-10-01
**Status:** Accepted - results of the tests fixed in D-042 and docs/08 section 7.9
**Output:** `reports/statistical_results.md`, `reports/statistical_family.csv` (`python -m src.stats.hypotheses`)

**Confirmatory family (14 tests, Benjamini-Hochberg q = 0.05): one detected.**
- **H6, hashtags:** Spearman rho 0.244 (95% CI 0.11 to 0.37), BH-adjusted p 0.009. **The association
  is between accounts, not within them:** with each account's mean removed rho is 0.02 (p 0.77), and
  in the mixed model the hashtag coefficient (std beta +0.17) has an interval reaching 0. It is
  described as "accounts that use more hashtags rank higher", never as hashtags raising a video's
  engagement. 13 videos carry 6+ hashtags.
- **Not detected at this sample size:** H1 duration (rho -0.045), H3 caption sentiment (std beta +0.10)
  and speech emotion (eps2 0.006), H4 faces (r_rb +0.036), the H6 text block and caption length, H7
  platform, H8 all features and each block. Each null is reported with the minimum detectable effect
  from `reports/power_analysis.md` (pooled r 0.20 at ICC 0).
- **Not tested:** H2 (product visibility not measured, D-037), H5 (no call-to-action measure, D-038).

**H7 - platform (7.9.3):** platform coefficient +0.470 log10 units, Instagram/YouTube rate ratio 3.0
(95% CI 0.5 to 17.3), p 0.23 -> **"Not detected"** under 7.9.4. The raw gap seen in exploration (about
1.8 log10 units) shrinks to 0.47 once follower tier and account are in the model: in the large tier
Instagram is higher (+1.60, interval +0.31 to +1.86), in the small/medium tier slightly lower (-0.29,
-1.29 to +1.34); without the global YouTube channel the coefficient is -0.01. The wider 290-video set
gives the same picture (ratio 3.2, CI including 1). The selection caveat (every hand-picked video is a
Reel) stands beside it.

**What the models say about accounts:** ICC 0.38 (log10 rate) and 0.30 (percentile) - about a third
of the variation in engagement belongs to the account, not the video. That, together with the
reach-only baseline of Phase 9, is the honest headline so far.

**Exploratory (H9, H10; never "significant"):** 8 of the 20 feature x platform intervals exclude 0
(e.g. face share, talking share, on-screen text area, event words steeper on Instagram; motion,
colourfulness, sentiment, caption length steeper on YouTube). With 20 intervals, YouTube's 72 videos
from 5 channels (58 from one) and no correction, these are leads for the SHAP comparison, not
findings. H10 duration x platform +0.098 per SD, interval -0.012 to +0.207.

**Robustness and checks:** median-imputation sensitivity agrees on every test except H8 overall
(p 0.042 unadjusted with imputation vs 0.101; still not detected after adjustment). Residuals normal
(Shapiro-Wilk p 0.24), no spread pattern; VIF max 3.6. Computational note: five optimisers per fit,
highest finite likelihood kept (Powell in all 52), because the default stopped at degenerate points.


---

## D-044 - Phase 9 specification: models, folds, tuning, threshold and the headline test, fixed before any model ran

**Date:** 2026-10-02
**Status:** Accepted - **written before any model was fitted** (researcher's go, 2026-10-02).
Implements docs/09 under D-041. Code: `src/models/train.py`; output `reports/model_comparison.md`.

**Data and target.** Focus set, 192 videos / 22 accounts. Target `engagement_high` (100 high / 92
low). All 192 rows are used: missing values are imputed **inside each training fold** (median),
never from test rows.

**Feature sets.**
- **M0 - reach and exposure only:** log10 followers, log10 video age, follower tier (large /
  medium / small, one-hot), platform, posting hour in UTC (as sine and cosine), weekend flag.
- **M1 - content only:** the 20 features of D-036 with the D-040/D-042 transforms (log1p cuts, face
  area 0 where no face, caption length z-scored within language - a transform that reads no outcome).
- **M2 - M0 + M1.**
- **Deviation, recorded now: `account_prior_engagement` is not used.** docs/09 asked for it computed
  within training folds from prior videos. Under account-grouped folds a test account has no videos
  in training, so the value could only come from that account's own other videos - their outcomes -
  which is leakage. It is dropped; M0 carries follower count and tier instead.

**Models (docs/09 section 1).** Majority class; logistic regression (L2, scaled); decision tree;
random forest (class-balanced); XGBoost; MLP (1-2 hidden layers, early stopping; kept, D-041).
Tuning: randomised search, 20 settings, inside each training fold on **account-grouped inner folds**
(3), scored by ROC-AUC. Grids are fixed in the code before the first run.

**Validation.** `StratifiedGroupKFold` by account, 5 outer folds, **repeated 3 times** (seeds 42,
1042, 2042) = 15 fits per model and feature set. Fold make-up (videos, accounts, platform, class
balance, which fold holds the global channel) is logged.

**Threshold.** For F1 / precision / recall / accuracy, the threshold that maximises F1 on
**out-of-fold predictions within the training fold**; never chosen on test rows. ROC-AUC, PR-AUC and
Brier need no threshold.

**Headline (docs/09 section 2), fixed now.** For every model, **M2 minus M0 ROC-AUC**, paired over the
15 outer folds, with a 95% interval from the **corrected resampled t-test** (Nadeau-Bengio), because
repeated-CV folds overlap and an ordinary t-interval would be too narrow. **Primary comparison:
XGBoost M2 against the reach-only logistic baseline (logistic regression M0)** - docs/09's "content
must beat this" - with the same correction. "Content adds beyond reach" only if that interval
excludes 0. The best model is reported, but no conclusion rests on picking it after the fact.

**Instagram-only model (exploratory, D-041):** same pipeline and folds on 120 videos / 17 accounts,
logistic regression and XGBoost, M0 / M1 / M2, plus `creator_collab`. No YouTube-only model.

**Also reported:** calibration (Brier, calibration curve on pooled out-of-fold predictions), a
learning curve for XGBoost M2 (share of training accounts), mean +/- SD over folds for every metric.

**Note added 2026-10-02, after a one-fold smoke test and before the full run:** the F1-maximising
threshold often labels every test video "high" (with a near-even split that is a cheap way to a
fair F1), which makes accuracy, precision, recall and F1 uninformative. The registered F1 rule is
kept and reported as is; a **secondary Youden's J threshold** (the other rule docs/09 names), chosen
the same way on training out-of-fold predictions, is reported beside it, with the number of folds in
which the F1 rule called every video high. ROC-AUC - the headline - uses no threshold and is
unaffected.
**Saved for the tool (task 12.1):** the XGBoost and logistic M2 pipelines refitted on all 192, the
feature order, and a model card with the cross-validated numbers. Calibration for the tool (12.2)
comes later.


---

## D-045 - Phase 9 results: no model predicts engagement for unseen accounts; an Instagram-only lead

**Date:** 2026-10-02
**Status:** Accepted - results of D-044
**Output:** `reports/model_comparison.md` (`python -m src.models.train`, 55 min)

**Headline (primary, registered in D-044): content does not add measurably beyond reach.** XGBoost
M2 against the reach-only logistic baseline: ROC-AUC difference **-0.030** (corrected 95% CI -0.234
to +0.174, p 0.76). No model's M2 - M0 interval excludes 0.

**The stronger, plainer finding: in the pooled set nothing predicts above chance for an account the
model has not seen.** Every pooled model sits near ROC-AUC 0.5 (best M0 0.61, best M2 0.53), and each
one's corrected interval around 0.5 includes 0.5. Two reasons, both structural, belong next to it:
(1) the target is a percentile ranked **within platform and follower tier**, so reach has been
normalised out of it by design - a reach-only model *should* sit near chance; (2) about a third of the
variation in engagement belongs to the account (ICC 0.30-0.38, D-043), and account-grouped testing
correctly gives the model no access to a new account's level. Together with D-043, the evidence says
engagement here is mostly an account property this design cannot learn for a new account.

**Exploratory lead - Instagram only (120 videos, 17 accounts; not corrected for the many comparisons):**
content-only models predict above chance for unseen Instagram accounts - logistic regression M1
ROC-AUC **0.704 +/- 0.140** (corrected 95% CI for AUC - 0.5: +0.035 to +0.373), XGBoost M1 0.670 (+0.039
to +0.300). The M2 - M0 gains (+0.23 to +0.25) are flattered by Instagram M0 sitting below chance, so
they are not quoted as the effect; the comparison with chance is. One plausible reason the pooled
models fail where Instagram alone does not: the fold that holds the global YouTube channel asks a
mostly-Instagram model to rank 58 YouTube videos, and the H9 estimates (D-043) suggest content relates
to engagement differently on the two platforms. That is a hypothesis for the SHAP step, not a finding.

**Also:** calibration is poor (Brier 0.268 / 0.315, worse than a constant guess); the learning curve is
flat; the F1 threshold rule labelled every video "high" in many folds, so threshold metrics are
secondary (D-044 note); tuned logistic regression chose the strongest regularisation (C = 0.001) in 9 of
15 folds - itself a sign there is little signal to fit.

**Consequences for the prediction tool (D-017, docs/11).** The saved pooled models
(`models/engagement_*_m2.joblib`, task 12.1) predict at about chance for a new account, so docs/11's
release gates cannot be passed by them as they stand. The researcher decides how the tool proceeds;
options are recorded in docs/11 when that decision is made. Nothing is changed in the tool's plan here.


---

## D-046 - The tool follows its pre-registered fallback: honest base rate, video diagnostics, and an Instagram content score labelled exploratory

**Date:** 2026-10-02
**Status:** Accepted. The researcher was asked how the tool should proceed after D-045 and answered
"do whatever is best for the project" (chat, 2026-10-02); this is that choice, and it follows the rule
docs/11 section 5 wrote before any model ran.

**Why a decision was needed.** Gate G1 (M2 beats the exposure-only baseline on grouped CV) **failed** on
the pooled focus set (D-045), and no pooled model predicts above chance for a new account. docs/11
section 5 fixed in advance what then happens: "say so in the write-up and ship the tool as an exposure
baseline plus content diagnostics". Section 1.5 also fixed what may not happen: quietly changing the
training set until a gate passes.

**What the tool becomes (both platforms, Zero Sugar creative):**
1. **An honest base-rate prediction per platform** - the expected engagement percentile for a typical
   video from an account of that size, with an interval that reflects what the data actually supports
   (wide), labelled "the models could not predict better than this for a new account".
2. **Video diagnostics** - the 20 measured features of the submitted video placed against the 192 Zero
   Sugar videos (for example "faster cutting than 80% of them"), with no claim that any of them raises
   engagement (H1-H8 not detected except an account-level hashtag association, D-043).
3. **An Instagram content score, labelled exploratory** - the Instagram-only content model (ROC-AUC
   0.70 on unseen accounts, D-045) shown with its measured accuracy and the words "exploratory: found
   in a secondary analysis, not confirmed". It is not offered for YouTube (no YouTube model, D-041).
4. **No "which platform suits this video better" verdict.** H7 was not detected and H9 is exploratory;
   the tool shows how Zero Sugar videos fared on each platform descriptively, with the selection
   caveat, instead of a recommendation.

**Gates.** G1 is reported as failed, in the tool's "about this model" page and in the thesis. G2
(calibration) and G3 (interval coverage) apply to whatever probabilities and intervals the tool shows -
the base-rate intervals and the Instagram score must pass them on grouped CV before release, or the
score is shown without a probability. G4 (training/serving parity) applies unchanged.

**Not chosen, and why:** rebuilding the tool around the Instagram model alone (it would turn an
exploratory, uncorrected finding into the deliverable's centre); hiding the failed gate; widening the
training set to the 290-video robustness set to look for a passing model (forbidden by docs/11 section
1.5).

---

## D-047 - Phase 10 specification: which models SHAP explains, the stability rule, and what may be said, fixed before any SHAP value was computed

**Date:** 2026-10-02
**Status:** Accepted - **written before any SHAP value was computed** (researcher's go, 2026-10-02).
Implements docs/10 under D-041, D-045 and D-046. Code: `src/models/explain.py`; output
`reports/xai_findings.md`, `reports/shap_importance.csv`, `reports/shap_fold_importance.csv`,
`reports/figures/shap/`.

**Starting point, fixed now whatever SHAP shows.** SHAP divides a model's prediction among its
inputs. It says what a model relied on, not what causes engagement. D-045 found that **no pooled model
predicts above chance for an account it has not seen**, so SHAP of the pooled model describes **what a
model that did not work relied on** - it is reported that way and never as what is associated with
engagement. Only the Instagram-only content models predicted above chance (exploratory, uncorrected).

**1. Which models are explained - these three and no others.**

| | Model | Why | Explainer |
|---|---|---|---|
| **A** | Pooled XGBoost M2 (192 videos, 28 inputs) | The primary model of D-044; docs/10 explains M2 so content is seen beside reach. Gives the per-platform view (RQ7/H9) and the duration x platform interaction (H10) | TreeSHAP (`tree_path_dependent`), log-odds |
| **B** | Instagram logistic regression M1 (120 videos, 20 content features + `creator_collab`) | The model D-046 made the tool's exploratory Instagram score (ROC-AUC 0.704) - its explanation is what the tool would show | Linear SHAP, log-odds, background = the whole training fold (no subsampling) |
| **C** | Instagram XGBoost M1 (same inputs) | A cross-check of B with a different kind of model (ROC-AUC 0.670) | TreeSHAP, log-odds |

**Not explained, and why:** Random Forest (docs/10 section 1 named it; pooled M2 0.511, the same
failure, and XGBoost is the registered primary model); the MLP (docs/10: only "if it performed well
enough to be worth explaining" - 0.483); the decision tree; the pooled M0/M1 variants; the Instagram M2
variants (B and C are the content models D-046 put in the tool; Instagram reach alone predicts below
chance, M0 0.46 / 0.38, and that is reported beside B so exposure is not hidden).

**2. The fold models are rebuilt, not re-tuned, and checked first.** Phase 9 did not save its fold
models. Each of the **15 outer fold models** (5 folds x 3 repeats, seeds 42 / 1042 / 2042 - docs/10
section 1 and TODO 10.1 said "5 outer folds"; corrected here to the 15 that D-044 ran) is rebuilt on the
same training rows with the settings tuned for that fold, read from `reports/model_fold_results.csv`.
**Check before any SHAP value:** every rebuilt fold's test ROC-AUC must equal the logged value (to
1e-6), and repeat 1's test predictions must equal the saved out-of-fold predictions
(`reports/model_oof_predictions.csv`, to 1e-6). If either fails, the run stops and the failure is
recorded; no SHAP is computed on models that are not the ones evaluated. A SHAP additivity check
(values + base = model output, to 1e-4) runs on every fold model.

**3. Inputs counted as one feature.** The two posting-hour columns (sine, cosine) and the two
follower-tier columns are each summed into one feature (SHAP values add exactly), so model A ranks 26
features, B and C rank 21. Direction is not defined for these two.

**4. Two uses of each fold model.**
- **Stability (10.1):** each fold model is explained on **all rows** of its data set (192, or 120), so
  every fold model is judged on the same videos and differences in ranking come from the models, not
  from which videos fell in the test fold.
- **Findings (10.2, 10.3):** **out-of-fold SHAP** - each video is explained only by the fold model that
  did not see it, one value per repeat, averaged over the 3 repeats. Beeswarms, block totals, the
  per-platform view, dependence plots and waterfalls use these.

**5. The stability rule (10.1) - decides what may be interpreted.**
- Importance of a feature in a fold model = mean |SHAP| over the reference rows; ranks 1 = highest.
- **Overall ranking:** Spearman correlation between the importance vectors of every pair of the 15 fold
  models (105 pairs); reported as the median with the 10th-90th percentile range. Verdict word fixed
  now: **stable** if the median is >= 0.70, **partly stable** if 0.40-0.70, **unstable** below 0.40.
- **A feature is stable** if it ranks **in the top 5 in at least 12 of the 15 fold models** *and* its
  **direction** - the sign of the Spearman correlation between its (imputed, scaled) value and its SHAP
  value - is the same in at least 12 of 15 (direction not required for the two merged features). Also
  reported: features in the top 10 of all 15 (the docs/10 table row).
- **What may be interpreted:** only stable features, in order of out-of-fold mean |SHAP| - **at most 5**
  if the overall verdict is "stable", **at most 3** otherwise. If no feature is stable, the result is
  "no feature is used consistently enough to interpret", and the figures are shown as description only.
- For model A the same rule is applied **separately to its YouTube rows (72) and its Instagram rows
  (120)** for the per-platform view.

**6. Outputs (10.2), per docs/10 section 2, with three amendments.**
- Beeswarm (out-of-fold) for A and B; ranking table for C.
- **Block-grouped importance**, the docs/10 measure (sum of mean |SHAP| over the block's features), with
  the per-feature average beside it because blocks differ in size. Blocks: A video (10 features), B
  audio (4), C text (6), D creator, E platform and exposure (6 after merging). **Amendment: Block D is
  empty in the pooled model** - no creator feature survived (automated labels failed, D-038;
  `creator_collab` exists only on Instagram) - shown as "not measured"; in B and C it holds
  `creator_collab`.
- **Dependence plots:** duration (H1) for A and B, and every feature interpreted under rule 5 for B.
  **Amendment: no emotion plot** - emotion is not one of the 20 model features (speech-only, D-040).
  Product visibility is not measured (D-037).
- **Four waterfalls, from model B only** (the model the tool would explain; waterfalls of a model at
  chance would be anecdotes). **Amendment: chosen without a threshold** (the F1 rule labels nearly
  every video high, D-044 note): the high video with the highest out-of-fold probability (true positive),
  the low video with the highest (false positive), the low video with the lowest (true negative), the
  high video with the lowest (false negative).

**7. Per-platform comparison (10.3, RQ7/H9) - exploratory throughout.**
- Model A's out-of-fold mean |SHAP| per feature on YouTube rows against Instagram rows - the key figure.
- A feature is **divergent** if it is in the top 5 in at least 12 of 15 fold models on one platform and
  outside the top 10 in at least 12 of 15 on the other. Stated beside every divergence: 58 of the 72
  YouTube rows come from one channel, and model A did not predict above chance.
- **Check on the Instagram view (docs/10 section 3):** Spearman between model A's Instagram-row
  importance and model B's, over the 20 shared content features.
- **H10:** SHAP interaction value duration x platform from model A (both halves, so 2 x the off-diagonal
  value), out-of-fold, mean on YouTube rows vs Instagram rows. An estimate, never "significant".

**8. B against C, and the effective-video profile (docs/10 section 5).** Reported: Spearman between B's
and C's out-of-fold importance over their 21 features, and for each stable B feature, C's rank and
direction. **The profile is built only from features stable in B whose direction C shares**, Instagram
only, worded as an exploratory association with the exposure caveat. If none qualify, the profile is
reported as not supported by this data. **No YouTube profile** (no model predicted above chance there),
and **nothing from model A enters a profile**.

**9. For the tool (task 12.6).** The tool's "drivers" may come **only from model B, and only from
features that pass rule 5** here. Nothing from model A is shown to a user.

**10. Wording, fixed now.** "The model relied on", "associated with" - never "drives", "causes" or
"raises". Every result carries: the Zero Sugar label's repeat reliability (YouTube alpha 0.25,
Instagram -0.10); that model A did not predict above chance; that B and C are exploratory (Instagram
only, 17 accounts, not corrected for the many comparisons).

---

## D-048 - Phase 10 results: on Instagram the model leans on hashtags, talking and faces; the pooled model learned a stable pattern that does not carry to new accounts

**Date:** 2026-10-02
**Status:** Accepted - results of D-047
**Output:** `reports/xai_findings.md`, `reports/shap_importance.csv`, `reports/shap_fold_importance.csv`,
8 figures in `reports/figures/shap/` (`python -m src.models.explain`, 0.6 min)

**Check first (rule 2): passed.** All 45 fold models (15 for each of A, B, C), rebuilt from the logged
settings, reproduce Phase 9 exactly - ROC-AUC and predictions differ by at most 1e-16; SHAP values add
up to the model output within 5e-6. The models explained are the models evaluated.

**Stability (10.1, rule 5):**

| Model | Rank agreement across 15 fold models (median, 10th-90th) | Verdict | Stable features (direction) |
|---|---|---|---|
| A. Pooled XGBoost M2 | 0.72 (0.51-0.87) | stable | hashtags (more -> higher), video age (older -> higher) |
| B. Instagram logistic regression M1 | 0.74 (0.63-0.88) | stable | hashtags, share with talking, share of frames with a face (all more -> higher) |
| C. Instagram XGBoost M1 | 0.63 (0.24-0.82) | partly stable | share of frames with a face (more -> higher) |

**What this says, in the wording D-047 fixed:**
- **Model A is consistent and still useless for a new account.** Its fold models rely on much the same
  inputs every time (0.72), yet none predicts above chance for unseen accounts (D-045): it learns the
  same pattern repeatedly, and the pattern does not carry to accounts it has not seen. Its two stable
  features are reported only as *what a model that failed relied on*.
- **Model B (exploratory):** Instagram Reels with **more hashtags, more talking and more frames with a
  face** are scored as more likely to be high-engagement. **Model C agrees on the direction of all three**
  (positive in 14, 15 and 15 of its 15 fold models), and B and C rank their 21 features similarly
  (Spearman 0.64). By rule 8 these three form the **effective-video profile - Instagram only,
  exploratory, an association and not a recommendation.** No YouTube profile; nothing from model A.
- **Two cautions that go wherever the profile goes.** (1) A model tested on accounts it has not seen
  can only learn what tells accounts apart. D-043 found hashtags associated with engagement **between
  accounts only** (within-account rho 0.02), so this reads as "accounts that use more hashtags", not as
  something that lifts a single video. Whether face share and talking share are account style or a
  per-video matter was not tested (it is not in D-047's specification); the pooled face test (H4) was
  not detected. (2) **B's score barely moves:** strongly regularised (C = 0.001 in 9 of 15 folds), its
  out-of-fold probabilities run from 0.39 to 0.68, and 80% of videos sit between **0.45 and 0.56**. It is
  a weak lean, not a confident prediction.

**Per-platform view (10.3, RQ7 / H9, exploratory):** model A's rankings on YouTube rows and on
Instagram rows are each stable (0.73 and 0.72), and **no feature is divergent** under rule 7. Hashtags
are stable on both platforms' rows. The largest visible gap - face share, 1st on YouTube rows and 12th
on Instagram rows - is in the top 5 of only 3 and 4 fold models, so it is not a finding. A's Instagram
view and model B agree moderately (Spearman 0.48 over the 20 content features). **RQ7 from SHAP: no
platform difference in what the pooled model relied on meets the rule** - with the standing caveats
(58 of 72 YouTube rows from one channel; model A at chance).

**H10:** the duration x platform interaction is essentially zero (mean +0.0002 log-odds on YouTube
rows, -0.0000 on Instagram rows), and duration is among the least-used inputs (23rd of 26 in A, 16th of
21 in B). Agrees with D-043 (H1, H10 not detected).

**Importance by block (docs/10):** model A - video 1.67 (10 features), platform and exposure 1.01 (6),
audio 0.88 (4), text 0.79 (6); per feature, audio is highest (0.22). Exposure does not dominate, but for
a model at chance this describes a failed model, not which kind of feature matters. Model B - video
0.16, text 0.08, audio 0.06, creator 0.02 (B's values are on a much smaller scale; compare within a
model only). Block D is empty in the pooled model (no creator measure survived).

**Waterfalls (model B):** the most confident correct "high" (p 0.676) is driven mostly by face share and
talking share; the most confident wrong "high" (p 0.579) by caption sentiment.

**Consequences for the tool (rule 9, D-046):** the tool's "drivers" may name only hashtags, share with
talking and share of frames with a face, from model B. Because B's probabilities barely move, gate G2
(calibration, task 12.2) decides whether the Instagram score is shown as a probability at all, as D-046
already requires.

---

## D-049 - Hand-coding of the 192 focus videos for the proposal's missing measures: questions, blinding and rules, fixed before the first answer

**Date:** 2026-10-04
**Status:** Accepted - **written before any answer exists** (`data/coding/focus_codes.csv` did not exist).
**Source:** the researcher's request of 4 October that nothing in the proposal be left missing (proposal
gaps P1-P9 in the plan). This **reverses three drops of D-032** - campaign type, sponsored content and
voice tone - by measuring them by hand instead of by model, and gives a human measure for what the
automated routes failed to measure: product visibility (D-037), music type (D-033), call to action,
celebrity, creator and humour (D-038). Code: `src/coding/codebook_focus.py` (questions, SHA-256
`98cc36a5...` at the time of writing), `src/coding/focus_app.py` (page); codebook in
`docs/13-focus-coding.md`.

**Who and what.** The researcher codes **all 192 focus videos** (Instagram 120, YouTube 72), one at a
time, in one random order fixed by seed 20261005 (`data/coding/focus_sample.csv`, drawn once and never
redrawn), watching the whole video with sound and reading its caption or title.

**Blind.** The page shows the video, the account name and the caption or title, and nothing else: no
likes, comments, views, followers or engagement measure, no earlier code, no Zero Sugar label, no
automated output. **Unlike the earlier pages, it has no link to the original post**, because the post
shows its like count. No transcript or translation is shown, so the conditions match the 15 September
coding (D-023) and the repeat check below compares like with like; the cost is that speech in a language
the researcher does not know is judged from the pictures, the caption and the sound alone.

**The 14 questions** (exact wording in the codebook; options in brackets):

| # | Field | Measures | Gap |
|---|---|---|---|
| 1 | `product_visibility` | Coca-Cola can or bottle (none / brief / prominent / unsure) | P1 |
| 2 | `logo_visibility` | Coca-Cola logo or name anywhere (none / brief / prominent / unsure) | P2 |
| 3 | `people_present` | any real person on screen (yes / no / unsure) | P4 |
| 4 | `has_celebrity` | **as 15 Sep** | P4 |
| 5 | `has_influencer` | **as 15 Sep** (social-media creator) | P4 |
| 6 | `humour_present` | **as 15 Sep** | P5 |
| 7 | `excitement_present` | meant to be exciting (yes / no / unsure) | P5 |
| 8 | `music_type` | no music / pop / hip-hop-rap / electronic-dance / rock / traditional-folk / cinematic-orchestral / other-can't tell | P6 |
| 9 | `voice_tone` | speaking voice (excited / calm / no voice / unsure) | P7 |
| 10 | `has_cta` | **as 15 Sep** (call to action) | P3 |
| 11 | `campaign_type` | new product / event / seasonal / promotion / food / general brand / unsure | P8 |
| 12 | `sponsored_disclosed` | paid or sponsored disclosed in caption or video (yes / no) | P8 |
| 13 | `product_vs_lifestyle` | **wording of the unchecked automated label** (D-038) | P9 |
| 14 | `ugc_vs_brand` | **wording of the unchecked automated label** (D-038) - the look, not who posted | P9 |

**Rules fixed now:**
- **"Can or bottle" means the same as on 15 September.** Product visibility counts cans and bottles
  only; cups, glasses, signs and trucks go to the logo question. So a "none" here is the 15 September
  "no product", and the definitional question behind D-037's gate B failure (does a fountain cup count?)
  is settled in advance: it does not.
- **P4's four groups are derived, not asked:** celebrity if `has_celebrity` is yes; otherwise creator if
  `has_influencer` is yes; otherwise ordinary people if `people_present` is yes; otherwise none; "unsure"
  wherever the deciding answer is unsure (`people_type()` in the codebook module).
- **Sponsored is judged from the caption and the video only.** The platform's own "Paid partnership" tag
  is not visible on the page (showing the post would show its likes); this is a stated limitation.
- **"Unsure" is missing**, never a category, in every analysis.
- **The questions are frozen from the first answer.** The researcher may ask for changes before coding
  starts; after that, any change is a dated note here, never a silent edit, and answers already given
  are not re-asked.
- **When all 192 are coded**, a read-only copy `data/coding/focus_codes_FINAL.csv` and its SHA-256 are
  made before any analysis reads the codes - as on 15 September (D-023). `manual_codes_FINAL.csv` is not
  touched.

**Repeat check (P11) - what it can and cannot cover.** **40 of the 60 videos coded on 15 September are in
the focus set** (Instagram 24, YouTube 16), not 60 as the 4 October plan assumed. On those 40, four
questions repeat word for word (celebrity, creator, humour, call to action), and product visibility's
"none vs any" matches 15 September's "no product vs a pack". **The other nine questions have no repeat
check** unless the researcher re-codes a subset later; that is the researcher's choice, and the gap is
stated either way. The exact repeat-check rules (statistic, what follows from a low value) are written
as their own entry **before P11 runs**, as are the analyses that use the new codes (P12-P14).

**What does not change:** the 20-feature set of D-036 and every result already reported (D-043, D-045,
D-048). The new codes enter later only as a **declared addition**, reported beside the pre-registered
results, never in place of them. The automated labels stay out of every model (D-038), whatever the
comparison with these hand codes shows.

**Note 2026-10-09 - state of the coding** (the researcher coded on 9 October, 16:55-18:45 IST; checked
without reading engagement and without comparing with the 15 September codes). **No answer was changed.**
- **180 of 192 complete;** 12 videos carry 14 blank answers (page numbers 7, 22, 27, 50, 59, 80, 81, 84,
  94, 122, 171, 185). The FINAL copy is not made until they are filled.
- **Pace, for the methods:** 110 minutes for 192 videos whose running time totals 100 minutes. Had every
  video been played once in full, about 3 seconds per video would remain for 14 answers and the caption,
  so **most videos were not watched in full with sound**, as this entry assumed (about 2 minutes a video
  was planned). Stated as a limitation, as D-039 recorded the pace of the by-eye check. It bears most on
  the sound questions (music type, voice tone) and on humour and excitement.
- **Celebrity and creator "unsure" on 71 videos each** (70 the same videos). Under the rules above these
  are missing, so the four people groups will rest on about 120 videos.
- **AI-generated characters.** The researcher noted (in the codes, and in chat on 9 October: "José vs
  Mourinho - these are AI generated characters") that the *José vs Mourinho* Shorts show AI-generated
  characters. 15 of them are in the focus set (all from the global YouTube channel). They were coded "a
  person appears: yes" (15 of 15) and celebrity / creator "unsure" (10) or "no" (5). The codebook did not
  foresee AI-generated people (it excludes cartoons and animated characters). How they are coded is the
  researcher's rule to set, applied to all 15 alike, before the FINAL copy. This does not touch the Zero
  Sugar labels or which videos are in the study.

**Note 2026-10-09, later - rule for AI-generated characters applied; codes locked.**
- **The researcher chose rule A in chat (9 October): AI-generated characters are not real people**, so
  for all 15 *José vs Mourinho* Shorts "a person appears", "celebrity" and "creator" are all "no". This
  changed **35 answers** (person 15 yes -> no; celebrity 10 and creator 10 unsure -> no), exactly as shown
  to the researcher before choosing. Every change is listed with its old value and source in
  `data/coding/focus_codes_changes.csv`; no other answer changed (checked row by row). The 15 are flagged
  for every analysis of the new codes, which is run with and without them.
- **The 14 blank answers stay blank.** The researcher asked for them to be filled for her; they were
  not, because an answer not given by the researcher is not a hand code and could not be described as
  one. They count as missing, like "unsure" (0.5% of 2,688 answers). `people_type()` now treats an
  unanswered question like "unsure" (the questions' wording is unchanged; module SHA-256 now
  `e52c4d80...`).
- **FINAL copy made:** `data/coding/focus_codes_FINAL.csv` (read-only), SHA-256 `ab52f980f6cd1cc3...`
  (full value in `focus_codes_FINAL.sha256`): 192 videos, 180 with every question answered.
  `manual_codes_FINAL.csv` is unchanged (`82c4afec...`).

---

## D-050 - Specification for the proposal-gap analyses (P10-P15), fixed before any of them ran

**Date:** 2026-10-09
**Status:** Accepted - **written before any new code was set against engagement and before the new
codes were compared with the 15 September codes** (researcher's go, 9 October). Only the locked codes
(`focus_codes_FINAL.csv`, `ab52f980...`) and their answer counts had been looked at. Every result here is
a **declared addition**: the registered results (D-043, D-045, D-048) stay exactly as reported.

**Rules for all of P11-P14.**
- Codes come from `focus_codes_FINAL.csv` only; "unsure" and blank are missing.
- **Small categories are merged, fixed now from the answer counts (fewer than 10 videos merges):**
  product visibility "none" (3) joins "brief" -> none-or-brief 56 vs prominent 136; logo "none" (1) the
  same; music hip-hop/rap 6, electronic 3, other 2 and rock 1 -> "other" (12), beside cinematic/orchestral
  96, no music 45, pop 36; campaign "seasonal" (3) joins "general brand" (12). People groups: none 61,
  ordinary people 27, creator 24, celebrity 17, missing 63; YouTube has no celebrity (stated).
- **AI-character sensitivity:** every P12-P14 result is also given without the 15 *José vs Mourinho*
  Shorts (D-049), beside the main result, never instead of it.
- Every result carries the coding caveats: one coder, 110 minutes for 100 minutes of video, and each
  measure's repeat reliability from P11 (or "not measured").

**P11 - repeat check.** The 40 videos coded on 15 September and 9 October (Instagram 24, YouTube 16; 4
are AI-character Shorts). Constructs: celebrity, creator, humour and call to action (same wording), and
product visibility as "none" vs "brief or prominent" against 15 September's "no product" vs a pack.
Krippendorff's alpha, nominal (`alpha_nominal` in `src/features/reliability.py`, already checked against
the reference package), 2,000 bootstrap resamples of videos (seed 20261009), with raw agreement and the
number of pairs. Main result on the FINAL codes; sensitivity without the 4 AI-character Shorts, whose
answers rule A changed. **Bands fixed now:** alpha >= 0.80 reliable; 0.667-0.80 tentative; below 0.667
weakly reliable; one value only on both sides = not estimable. **No construct is dropped for a low
value** - it is the only measure, as with the Zero Sugar label (D-029); its band goes with every result.

**P10 - local posting time.** Each market mapped to a time zone (IANA, daylight saving handled):
single-zone countries their own zone; Brazil `America/Sao_Paulo`, Indonesia `Asia/Jakarta`,
LatAm/Mexico `America/Mexico_City`, Chile `America/Santiago`; regional accounts approximate - Europe
`Europe/Paris`, MENA `Asia/Dubai`; **Global/US (77 videos) keeps UTC** (no single audience), flagged.
Each video gets `posting_hour_local`, `is_weekend_local` and the quality of its zone. Used in (a) a
description of how many videos change day or hour band, and (b) **one sensitivity re-run** of the
pooled logistic M0 and XGBoost M2 with local hour and weekend in place of UTC (same folds and grids),
reported beside the registered numbers.

**P12 - exploration with the new codes (descriptive only: no test, no p-value).** EDA 4 (percentile by
product visibility), EDA 5 (by the four people groups), EDA 6 (by humour, excitement, voice tone), EDA 8
rows (every new measure's composition by platform, then a descriptive figure), EDA 9 (Spearman of each
new yes/no or ordinal measure with the percentile, as description). Also: the two unchecked automated
labels (`product_vs_lifestyle`, `ugc_vs_brand`) against the hand codes - agreement and alpha - which
keeps them out of every model whatever it shows (D-038).

**P13 - H2, H4, H5 as a declared addition.** Focus set; complete cases per test; percentile outcome;
mixed model with an account intercept and the D-042 controls (platform, log followers, log video age),
fitted with `fit()` from `src/stats/hypotheses.py`.

| H | Measure (1 vs 0) | Test 1 | Test 2 |
|---|---|---|---|
| H2 | product prominent vs none-or-brief | LR test, 1 df, added to the controls | Mann-Whitney U, rank-biserial r |
| H4 | creator or celebrity vs neither (ordinary people or no person) | LR test, 1 df | Mann-Whitney U |
| H5 | call to action yes vs no | LR test, 1 df | Mann-Whitney U |

- **These six tests are their own Benjamini-Hochberg family (q = 0.05).** The 14-test family of D-042
  is not re-opened.
- For any test detected after correction, the within-account check of D-043 (Spearman with each
  account's mean removed) is reported; it describes, and changes no verdict.
- Each null carries the minimum detectable effect for its own group sizes (two-sample, 80% power,
  alpha 0.05, no account clustering - a lower bound).
- Outside the family, estimates with 95% intervals only, never "significant": the four people groups
  (Kruskal-Wallis), and a mixed-model coefficient for each other new measure (logo prominent,
  excitement, excited voice, music groups, campaign groups, sponsored, lifestyle, homemade look).

**P14 - the hand codes in the models (declared addition).** One feature set **H** of 11 yes/no columns:
product prominent, logo prominent, person present, creator or celebrity, humour, excitement, excited
voice (calm or no voice = 0), call to action, sponsored, lifestyle, homemade (UGC) look. Missing ->
median inside each training fold. Music and campaign type stay out of the models (several categories;
P12 describes them), which keeps every set within the 18-20 budget (D-030). Sets: **Mh1 = H**, **Mh2 =
M0 + H** (M1 + H would be 31 features and is not fitted). Logistic regression and XGBoost only, the
D-044 grids, folds (5 x 3, seeds 42 / 1042 / 2042), inner tuning and thresholds. **Pooled headline of
the addition:** XGBoost Mh2 and logistic Mh2, each minus the logistic M0 from the same folds, corrected
resampled t-test. Instagram (exploratory): Mh1 against chance and beside the registered Instagram
logistic M1 (0.704). Sensitivity: the pooled headline without the 15 AI-character Shorts. SHAP
stability by D-047 rule 5 for the Instagram logistic Mh1 and the pooled XGBoost Mh2, reported
descriptively; it feeds the effective-video profile (P17), whose own rules are written before it runs.

**P15 - confusion matrices.** For each pooled model x set and each Instagram model x set: one matrix
summed over the five test folds of repeat 1 (each video once, from the saved out-of-fold predictions),
at each fold's registered F1 threshold and at its Youden threshold (both logged in
`reports/model_fold_results.csv`). Fold membership is recomputed with the same splitter and seed and
checked: each fold's ROC-AUC from the saved predictions must equal the logged value.

**Code:** `src/features/local_time.py` (P10), `src/coding/repeat_check.py` (P11),
`src/eda/explore_codes.py` (P12), `src/stats/hypotheses_added.py` (P13), `src/models/train_added.py` (P14
and P10's re-run), `src/models/confusion.py` (P15). P16 (statistics vs machine learning compared), P17
(profile for both platforms) and P18 (changes from the proposal) follow from these results.

---

## D-051 - Results of the proposal-gap analyses: three hand-coded associations, two of which rest on one AI-character series

**Date:** 2026-10-09
**Status:** Accepted - results of D-050, a declared addition; the registered results are unchanged.
**Outputs:** `reports/repeat_check.md`, `reports/local_time.md`, `reports/confusion_matrices.md`,
`reports/eda_codes.md`, `reports/statistical_results_added.md`, `reports/model_comparison_added.md`.

**P11 - the hand codes are weakly reliable where they can be checked** (40 videos coded twice, about three
weeks apart): humour alpha 0.69 (tentative); celebrity 0.52, call to action 0.50, product none-vs-any 0.48
and creator 0.38 (all weakly reliable; most intervals wide). Without the 4 AI-character Shorts: celebrity
0.78 and humour 0.75 (tentative), creator 0.49, call to action 0.45. The other nine questions have no
repeat check. With the coding pace (110 minutes for 100 minutes of video), every result below rests on
noisy measures.

**P10 - local time.** 115 of the 192 videos got a local zone (77 Global/US stay UTC). In UTC, 28 videos
looked like night posts (0-6 h); in local time 2 are. The hour band changes for 93 of the 115, the
weekend flag for 1. [Model re-run with local time: see P14 below.]

**P15 - confusion matrices** (repeat 1, each video once; check passed, fold ROC-AUCs reproduced to 1e-16).
The registered F1 threshold predicts nearly every video "high" (pooled XGBoost M2: 94 / 88 / 6 / 4 for TP /
FP / FN / TN, accuracy 0.51); at the Youden threshold accuracy is 0.42-0.54 pooled. Instagram XGBoost M1
reaches 0.62 and logistic M1 0.57 at both thresholds.

**P12 - exploration (description only).** Celebrity videos (17, all Instagram, 5 accounts) have a median
percentile of 0.93 against 0.45-0.62 for the other people groups; videos with a call to action 0.66 against
0.44; lifestyle-focused 0.44 against product-focused 0.65; event campaigns 0.35, the lowest. Spearman with
the percentile: call to action +0.29, creator or celebrity +0.23, lifestyle -0.20; the others within 0.16.
The two unchecked automated labels disagree with the hand codes (product vs lifestyle alpha 0.15, UGC vs
brand 0.34): they stay out of every model (D-038).

**P13 - H2, H4, H5 (own BH family of six tests).**

| H | Measure | Mixed-model effect (95% CI) | BH p (LR; Mann-Whitney) | Verdict | Without the 15 AI-character Shorts | Within accounts |
|---|---|---|---|---|---|---|
| H2 | product prominent | +10.4 points (+1.9 to +18.8) | 0.021; 0.059 | LR detected, rank test not | +1.9 points, p 0.68 - **gone** | rho +0.18 (p 0.012) |
| H4 | creator or celebrity (n 129) | +14.3 points (+1.8 to +26.8) | 0.014; 0.014 | detected | +9.0 points, p 0.08; rank p 0.06 - **not detected** | rho +0.09 (p 0.31) - between accounts |
| H5 | call to action | +11.0 points (+3.0 to +19.0) | 0.014; <0.001 | detected | +5.4 points, p 0.15; **rank test p 0.002** | rho +0.19 (p 0.009) - within accounts |

**How to read it.** All 15 AI-character Shorts are coded the same way - no prominent product, no call to
action, no person - and they come from one channel. The H2 association disappears without them, and H4
weakens below detection; both are therefore **not robust**, and H4 is mainly between accounts (5 accounts
supply the 17 celebrity videos). **H5 (call to action) is the most robust**: detected by both tests, its
rank test holds without the series, and it holds within accounts - but the call-to-action code is weakly
reliable (alpha 0.50) and its mixed-model effect without the series is not detected. Outside the family,
estimates only: lifestyle focus -10.1 points (-17.8 to -2.4; without the series -5.1, interval crossing 0);
event campaigns -14.8 points against promotions (-25.8 to -3.7).

**P14 - the hand codes do not help prediction for unseen accounts** (`python -m src.models.train_added`;
fold check passed - the re-computed logistic M0 equals the logged one in all 15 folds). Reach + hand codes
against the reach-only logistic baseline: XGBoost Mh2 -0.085 (corrected 95% CI -0.309 to +0.139),
logistic Mh2 +0.043 (-0.067 to +0.154) - not detected. No hand-code model is above chance: pooled logistic
Mh1 0.601 (CI for AUC - 0.5: -0.016 to +0.219), XGBoost Mh1 0.595; Instagram logistic Mh1 0.588 and XGBoost
Mh1 0.613 (exploratory), below the registered Instagram logistic M1 (0.704). Without the 15 AI-character
Shorts the differences are -0.144 and -0.092 (intervals include 0). SHAP stability: Instagram logistic Mh1
partly stable (0.45; stable: humour and creator or celebrity, both positive); pooled XGBoost Mh2 partly
stable (0.63; stable features are reach: video age, posting hour, followers).

**P10's model re-run - local time changes nothing measurable:** logistic M0 0.585 against 0.562 registered
(+0.022, CI -0.084 to +0.129); XGBoost M2 0.488 against 0.533 (-0.045, -0.137 to +0.047).

**Together.** The hand codes reproduce the pattern of D-043/D-045: some associations inside these 22
accounts (call to action the most robust), none that a model can use to predict a new account's video. For
the tool (D-046): the hand-coded questions may be shown to a user as diagnostics against the 192 videos,
but no score is built from them.

---

## D-052 - Specification of the effective-video profile (P17, Objective 15), written before it was built

**Date:** 2026-10-09
**Status:** Accepted - written before the profile tables were computed. **Stated plainly:** the results it
draws on (D-043, D-048, D-051) were already known, so this entry does not choose items by result; it
lists every item that has evidence and attaches the checks that were fixed before those results existed.

**What the profile is.** Proposal Objective 15: "an empirical profile of an effective Coca-Cola Zero Sugar
marketing video". docs/10 section 5 sets its rules: stable features only, an association not a
recommendation, separate profiles where the platforms differ, and the exposure caveat.

**Items - every measure with evidence, none left out:**
1. **Model-based, Instagram (pre-registered in D-047 rule 8):** hashtags, share with talking, share of
   frames with a face - stable in the Instagram logistic model, with the Instagram XGBoost agreeing (D-048).
2. **Statistical associations detected:** hashtags (H6, registered family, D-043); product prominent (H2),
   creator or celebrity (H4) and call to action (H5) (addition family, D-051).

**Labels attached to each item, all from checks fixed in advance:** whether the association holds within
accounts (D-043 / D-050 check); whether it survives without the 15 AI-character Shorts in at least one of
its two tests (D-050); the measure's repeat reliability (P11). **The one-line profile names only the items
that pass every check that applies to them**; the rest stay in the table with their labels, so the reader
sees the full picture.

**Two platforms (docs/10 section 5).** Instagram: the model-based items plus the statistical ones. YouTube:
**descriptive only** - no YouTube model can be tested (D-041). For every item, the median (or share) among
the platform's high- vs low-engagement videos is shown side by side for Instagram and YouTube, no test;
a YouTube direction is "same" or "opposite" by the sign of that difference. Stated beside YouTube: 72
videos, 58 from one channel.

**Threshold column.** The Instagram logistic model has no threshold of its own: its contribution changes
sign at the training average, which is reported (D-048). Otherwise medians, no fitted cut-off.

**Wording, fixed now:** "videos with ... were associated with higher engagement in this sample"; never
"do ...", "should" or "increases". The exposure caveat goes with every line: engagement here is ranked
within platform and follower tier, so the profile says nothing about reach.

Code: `src/eda/profile.py`; output `reports/effective_video_profile.md`; docs/10 section 5 filled.

**Result, 2026-10-09.** One-line profile - items that pass every check that applies to them: **on
Instagram, more talking and more frames showing a face** (model-based, exploratory); **pooled, a call to
action** (within accounts and in the rank test without the AI-character series; the code is weakly
reliable, alpha 0.50). Listed but not in the line: hashtags (between accounts only), product prominent and
creator or celebrity (do not survive without the series). **YouTube, described:** high-engagement Shorts
had *less* talking (median 0.00 vs 0.65) and fewer face frames (0.40 vs 0.73) than low ones - the opposite
of Instagram, matching the exploratory H9 signs of D-043 - while call to action (62% vs 24%), hashtags and
product prominence point the same way on both. YouTube's column is mostly one channel (58 of 72).

---

## D-053 - Specification of the tool's two models and their checks (tasks 12.1-12.2), written before they were fitted

**Date:** 2026-10-09
**Status:** Accepted - written before either model below was fitted or checked (researcher: "complete the
half work of week 6"). Implements D-046 items 1 and 3 and docs/11 gates G2 and G3. Code
`src/serve/build_models.py`; outputs in `models/` and `reports/serving_models.md`.

**1. Base rate per platform (D-046 item 1).**
- **What it predicts:** the engagement **rate** (likes + comments per follower) of a typical Zero Sugar video
  from a new account of a given platform and follower count, with an **80% prediction interval**; the
  tool derives a likes + comments range from it when the user gives a follower count. **Not a percentile:**
  the percentile is ranked within platform and follower tier, so by construction every cell's typical value
  is the middle (about the 50th, with an 80% range of roughly the 10th to 90th) - the tool says so instead
  of showing a model for it.
- **Model:** mixed model, `log10(rate) ~ platform + log10(followers)` with a random intercept per account,
  fitted with `fit()` of `src/stats/hypotheses.py` (REML) on the 192 videos. For a new account the
  prediction variance is account variance + residual variance + the fixed-effect uncertainty; the interval
  is mean +/- 1.2816 x its square root (80%). Video age is not a term (the tool predicts a mature video;
  stated as a limitation: engagement was read at 7 days or later, ages vary).
- **G3, fixed now:** account-grouped cross-validation with the D-044 folds (5 x 3, seeds 42 / 1042 / 2042):
  fit on the training accounts, interval for each test video as for a new account, coverage = share of test
  videos inside it. **G3 passes if coverage is within 70-90% overall and on each platform.** If it fails,
  the interval is widened by the factor that brings overall coverage to 80% on the same folds, reported,
  and the tool says so; if YouTube alone fails, YouTube's interval is shown with that warning.
- G2 does not apply (no probability is shown for the base rate).

**2. Instagram content score (D-046 item 3, exploratory).**
- **Model:** the registered Instagram logistic regression M1 (the 20 content features + `creator_collab`;
  imputation and scaling in the pipeline), tuned as D-044 on account-grouped inner folds, refitted on all
  120 Instagram videos.
- **G2, fixed now - calibration on out-of-fold probabilities** (all 3 repeats, 360 predictions; fold models
  rebuilt from the logged settings and checked against the logged ROC-AUCs): ten equal-count bins of the
  predicted probability; **G2 passes if every bin's observed share of high-engagement videos is within 0.10
  of its mean predicted probability.** Brier score reported beside it.
- **Order fixed now:** (a) the model as fitted; if (a) fails, (b) Platt scaling fitted inside each training
  fold on its own account-grouped inner out-of-fold predictions and checked the same way; if (b) passes, the
  tool ships the calibrator with the model. **If both fail, the tool shows no probability:** the score is
  shown as a position - "higher than X% of the 120 Instagram Zero Sugar videos" - labelled exploratory.
- No YouTube score (D-041, D-046).

**3. Saved for the tool (12.1).** `models/base_rate.json` (coefficients, covariance of the fixed effects,
variance components, training ranges), `models/instagram_content_logreg.joblib` (+ calibrator if G2 passes
with it), `models/reference_quantiles.json` (the 20 features' 0-100% quantiles per platform from the 192
videos, and the hand-coded measures' shares, for the diagnostics of D-046 item 2), and `models/model_card.json`
rewritten for D-046 (what each output is, its measured accuracy, gates G1-G4 and their status). The pooled
models of 2 October stay in `models/` for comparison and are not served.

**Out of range:** follower counts outside the training range (7,594 to 17.1 million) are flagged by the
tool, never extrapolated silently (docs/11 section 4.3).

---

## D-054 - Results for 12.1-12.2: both release checks fail, and the tool takes the fallbacks D-053 fixed

**Date:** 2026-10-09
**Status:** Accepted - results of D-053. Output `reports/serving_models.md`,
`reports/figures/instagram_score_calibration.png`, `models/` (`python -m src.serve.build_models`).

**Base rate - G3 fails, interval widened, YouTube still warned.** The 80% interval for a new account's
typical video held 67% of test videos on account-grouped folds (Instagram 79%, YouTube 49%; rule 70-90%).
Widened by x1.26 as fixed in advance: overall 80% (by construction - the factor was chosen on these folds),
Instagram 86%, **YouTube 69%, still under 70%**, so the tool shows YouTube's interval with a warning that
it is too narrow. The intervals are very wide - for an Instagram account of 500,000 followers, a typical
rate of 0.26% with an 80% range of 0.004% to 18% - because 46% of the unexplained variation lies between
accounts, which the tool cannot know for a new one. That width is the honest finding, not a defect.

**Instagram content score - G2 fails both ways; no probability is shown.** Out-of-fold calibration (360
predictions, ten bins): largest gap 0.32 as fitted and 0.27 after Platt scaling inside the folds (rule
0.10). The reason: within each fold the score ranks videos above chance (mean ROC-AUC 0.704), but its level
shifts from one refit to the next, so pooled across folds it ranks at chance (0.522). Following D-053, the
tool shows the score only as a position - "higher than X% of the 120 Instagram Zero Sugar videos", scored
by the same model - labelled exploratory. Stated limitation: the 120 reference scores are in-sample for the
final model (C = 0.01).

**Gates now:** G1 failed (D-045); G2 failed -> no probability; G3 failed -> widened interval + YouTube
warning; G4 (training/serving parity) pending, task 12.8. The model card says each in plain words.

**Saved (12.1):** `models/base_rate.json`, `models/instagram_content_logreg.joblib`,
`models/reference_quantiles.json`, `models/model_card.json` (the 2 October card was replaced; its pooled-model entries are kept inside it as comparison only).
No calibrator is saved (G2 failed with it).

---

## D-055 - Specification of the inference pipeline (task 12.3) and of the parity check G4 (task 12.8), written before either was built or run

**Date:** 2026-10-17
**Status:** Accepted - **written before any pipeline code existed and before any video was measured by it**
(researcher, 17 October: "complete the 6th week work"). Three choices put to the researcher on 11 October
are taken as recommended then - how strict G4 is (section 6), how a missing caption or collaboration answer
is treated (section 1), and moving the derived inputs into shared functions (section 4); stated plainly, the
researcher did not answer them one by one, and may change any of them before G4 runs. Implements docs/11
section 3 under D-046, D-053 and D-054. Code: `src/serve/measure.py` (runs the feature steps on one video),
`src/serve/pipeline.py` (model inputs and outputs), `src/serve/parity.py` (G4); artefact
`models/serving_schema.json`.

**Superseded wording, recorded so it is not followed by mistake:** the docs/11 section 3 diagram (CLIP,
"~30 pruned features", M2 per platform, TreeSHAP) predates D-030, D-036 and D-046; the original task wording
for 12.3 ("incl. the annotation step") predates D-038. Neither applies.

**1. What goes in.** A video file on this computer (task 12.4 adds links and uploads); the platform it is
meant for (Instagram or YouTube); its caption (for YouTube the title and description, joined as in training:
title, a line break, description); the account's follower count; and, for Instagram, whether the post is a
collaboration with a creator. **Caption and collaboration are optional and, when not given, are missing -
never zero and never "no"** (hidden is not zero, D-005). A caption given as empty is a real empty caption and
is measured as one, as in training. When the caption is missing, every input built from it (caption length,
hashtags, emoji, caption sentiment) is missing, and each keyword flag is "yes" only if the speech hits a
keyword and otherwise missing - a hit is certain, a miss is not. The hand-coded questions (D-049) may be
answered by the user; the answers are passed through to the diagnostics and **never enter a model** (D-051).

**2. Refused, with the reason in plain words:** a file that does not open as a video; a video with no sound
track (all 300 training videos had one); a video longer than 180 seconds (short-form scope, D-001; the corpus
maximum is 177.8 s). **Measured but flagged as unlike the training data** (wording in task 12.7): shorter than
3.9 s, a shape outside the corpus's width-to-height range 0.45-0.80, followers outside 7,594 to 17.1 million.

**3. How the video is measured - the training code, unchanged.** The video goes through the Phase 5 steps in
training order, calling the same per-video functions with the same settings: preparation (5.1), cuts (5.2),
frames and motion (5.3), speech-to-text (5.6), audio signal and sound events (5.8), sentiment (5.9), faces,
on-screen text and colour (5.5), caption language (5.7), keywords (5.16) and the caption counts of 5.15.
**Not run:** the automated labels (5.12; none passed its check, D-038), music genre (D-033), product
detection (D-037) and CLIP (D-029).
- **Its own folder.** Everything the pipeline writes - audio, frames, the per-video record - goes under
  `data/interim/serve/<run>/`, never into the training folders (`data/interim/features/`, `audio/`,
  `frames/`). So it can never overwrite a training measurement, and a check cannot pass by reading a training
  value back. The three folder locations in `src/features/common.py` are pointed at the run folder inside the
  pipeline's own processes; the feature modules are not edited.
- **Separate processes, as in training.** Speech-to-text runs in its own process with the CUDA 12 libraries
  loaded first (D-027: no PyTorch in that process); the other graphics-card steps run in a second process.
  Every model is read from disk; nothing is downloaded.
- **Settings guard.** `models/serving_schema.json` stores the settings each step recorded for the 192
  training videos. Checked on 17 October before anything was built: each step has one setting across all 192,
  equal to today's code (13 blocks). The pipeline refuses to run if a step's settings in the code differ from
  the stored ones.
- **Glue only.** Where a training script wrote a step's result into the record from its main loop
  (preparation, sound events, sentiment, faces, text, colour, language, keywords, caption counts), the
  pipeline writes the same result under the same block name. The measuring functions are called, not copied.

**4. From measurements to model inputs - one implementation.** The derived inputs - the log cut rate, face
size (0 when no face), caption length within its language, the keyword groups and collaboration as 0/1 - are
computed today inside `src/features/assemble.py`, `src/stats/hypotheses.py` and `src/models/train.py`. They
are moved into one shared module (`src/features/derived.py`) that those scripts call, and the pipeline calls
the same functions. **Before and after the move, the feature table (built in memory from the records), the
statistics table and the model table are compared value by value; they must be identical, or the move is
undone.** `data/processed/features.parquet` is not rewritten. For a new video, caption length within language
uses the means and standard deviations of the 192 (per caption language with at least 5 of the 192, otherwise
the whole 192), computed by the same function training uses and stored in the schema. The result is the 20
content features plus collaboration in the trained order (`feature_order` in `models/model_card.json`),
checked against the saved model's own column names when it is loaded.

**5. What comes out** (values only; the page and its wording are tasks 12.5-12.7):
- **Base rate** per platform (D-053, D-054): the typical engagement rate and its 80% interval for a new
  account of that size, widened x1.257, YouTube marked as under-covered (69%); a likes + comments range from
  the follower count. No follower count, no base rate.
- **Instagram content score**, Instagram only: the saved model's score shown only as a **position - the
  share of the 120 training scores strictly below it** (D-054), labelled exploratory; no probability.
- **Diagnostics:** each of the 20 measures as a percentile among the 192 and among that platform's videos,
  by straight-line interpolation between the 5% steps in `models/reference_quantiles.json`; no claim about
  engagement (D-046 item 2).
- **What was missing and why** (no caption, no speech, collaboration unknown), so task 12.7 can say which
  inputs the score lacked. A missing model input is filled by the saved model's own imputer (the training
  median), exactly as in training - nothing is chosen here.
- No YouTube score and no platform verdict (D-046).

**6. G4 - training/serving parity** (registered in docs/11 section 5; run in task 12.8). Fixed now:
- **Sample, drawn now, before any pipeline run:** 10 of the 192 - per platform 3 with speech and 2 without
  (speech status from 5.6, which does not involve engagement), seed 20261017, written to
  `reports/serving_parity_sample.csv`. **These 10 are not used while the pipeline is built**; development
  checks use corpus videos outside the 192 only.
- **Run:** each video is measured from its file, with the caption the corpus holds for it and its recorded
  collaboration flag, in a fresh empty folder - **twice**, in two folders.
- **Compared:** the model inputs (21 for the Instagram videos, the 20 content features for YouTube videos)
  against the values the models were trained on (`build()` in `src/models/train.py`), and for the 5 Instagram
  videos the score position. No engagement value is read out or shown.
- **Primary rule (docs/11 wording, "bit-for-bit"):** every input identical, missing equal to missing, in both
  runs -> G4 passes.
- **Secondary, reported beside it:** counts and flags identical, continuous inputs within 1e-6 (absolute or
  relative). Run 1 against run 2 shows whether a difference is run-to-run variation on the graphics card or a
  lasting difference from training.
- **If G4 fails:** the cause is found and recorded. A pipeline fault is fixed and the same 10 are re-run,
  every run kept. A difference that cannot be removed by 1 November is shipped as a failed gate - named on the
  model card and the tool's about page with the input and the size of the difference - as G1-G3 were.
  **Never:** re-measuring or editing training values to match, or drawing a new sample.
- Time per video is reported.

**What does not change:** the 20 features, the saved models, every reported result, the hand codes, and the
rule that no automated label is used.

**Note 2026-10-17 - built; first checks (not G4).**
- **Section 4's move:** the feature table built in memory (300 x 96), the statistics tables (290 x 125 and
  192 x 126) and the model table (192 x 134) are identical value by value before and after;
  `features.parquet` was not rewritten (SHA-256 unchanged, `83fab00b...`).
- **Schema:** the 21 inputs in the model card's order equal the saved model's own column names; 12 steps'
  settings (preparation records none) shared by all 192 records and equal to the code; caption-length
  reference for en, es, ko, pt, th, tr and vi.
- **G4 sample** (drawn before any run): Instagram Da4ZFCUssvp, DTAgD-IExL-, Da8In57ug3r (speech in Swahili,
  Hindi, Turkish), DcGF4VEIxbT (no speech), Cd5oWJNsfI0 (silent audio); YouTube Uf__4_hjwoM, YEo8ShllJ1g,
  vFrcDKzucBI (English), 7P6P4bSZr5g, Fi3fytTXkoA (no speech). Not yet run.
- **Development check** on two corpus videos outside the 192, both with English speech (Instagram
  DaKsr6OzHqf, YouTube nUsWSsbWwYg): all **73 flattened features identical** to `features.parquet` on both
  (automated-label columns not compared). 258 s and 193 s a video, most of it starting the processes and
  loading the models. This is not G4: the videos are outside the 192, and model inputs were not compared.
- **Refusals** checked on test files: not a video, no sound track, 181 s - each refused before anything was
  written.
- **A guard added during the build:** the process that compares keeps reading training values from the
  training folders (asserted), and reads the run's record from its own file - otherwise a check could
  compare the run with itself.
- **Display detail, in code:** a value equal to several of the stored 5% steps (many videos share it, e.g.
  0) is placed at the middle of their range.
- **End to end as a new video** (a copy of the development Instagram clip from outside the project folder, no
  caption, collaboration not given, 500,000 followers): measured in 163 s; seven inputs reported missing
  (the four caption inputs, both keyword flags - the speech hit neither - and collaboration); base rate 0.26%
  with an 80% range of 0.004% to 18%, as D-054 reported; Instagram score shown as a position only. A test on
  a record measured *with* its caption showed that the keyword rule of section 1 should not depend on how the
  record was made: each flag is now "yes" only if that group's recorded source includes the speech. The run
  above is unchanged by this.

---

## D-056 - Specification of P20: speech rate, brand and product mentions, and YouTube views, a declared addition written before any test

**Date:** 2026-10-17
**Status:** Accepted - **written before any of these measures was set against engagement.** Source: the
13 October check against the proposal (measured but not tested: Block B speech rate, Block C brand/product
mentions, Block E platform-specific engagement indicators); the researcher approved testing them on 13 October.
Only counts were looked at to write this (no engagement value): speech rate exists for 112 of the 192 (121 have
speech; the rate is left empty under 2 seconds of speech, docs/05), Zero Sugar named 53 / not named 120 / not
searched 19, the brand named in 166 (all 72 YouTube videos and 94 of 120 Reels), a view-based rate for all 72
YouTube videos. Like D-050, everything here is a **declared addition**: the registered results (D-043, D-045,
D-048) and the 9 October addition (D-051) stay exactly as reported. Code `src/stats/hypotheses_p20.py`; output
`reports/statistical_results_p20.md`, `reports/statistical_family_p20.csv`.

**The measures.**
- **Speech rate** - `words_per_min` from speech-to-text (5.6): words per minute of speech, counted on the
  native-language transcript; empty when a video has under 2 s of speech. Sung lyrics are transcribed as
  speech (stated limitation, D-028). z-scored on the rows used.
- **Product named** - `kw_zero_sugar` (5.16, vocabulary fixed 24 September, docs/04 section 5.1: zero sugar,
  no sugar, sugar free, zero, in seven languages) in the caption (in its own language) or in the English
  translation of the speech. "Not searched" is missing, never "no".
- **Brand named** - **measured here for the first time, fixed now:** the Coca-Cola name in the caption or in
  the English translation of the speech. Terms: `coca-cola`, `coca cola`, `cocacola`, `coke`, and in the
  corpus's other scripts `كوكاكولا`, `كوكا كولا`, `โค้ก`, `코카콜라`, `코크`, `कोका-कोला`, `कोका कोला`.
  Matched as text after Unicode normalisation and case folding (so hashtags and account tags count: a
  caption tagging the brand names it). Every YouTube video names the brand, so its estimate rests on the 26
  Reels that do not.
- **View-based engagement (YouTube only)** - `engagement_rate_view` = (likes + comments) / views (docs/06
  section 2), as `log10`; a zero rate would be replaced by half the smallest positive one before the log, as
  in D-042. Instagram publishes no reliable views (docs/06), so it has no counterpart. Per docs/06 it is a
  within-YouTube robustness measure: **no finding from it is carried into a platform comparison.**

**The tests - one Benjamini-Hochberg family of ten (q = 0.05), separate from the D-042 and D-050 families.**

| # | Outcome | Measure | Test 1 | Test 2 |
|---|---|---|---|---|
| 1-2 | percentile (pooled, 192) | speech rate (n 112) | LR test, 1 df, added to the D-042 controls | Spearman |
| 3-4 | percentile (pooled) | product named (n 173) | LR test, 1 df | Mann-Whitney U, rank-biserial r |
| 5-6 | percentile (pooled) | brand named (n 192) | LR test, 1 df | Mann-Whitney U |
| 7-8 | view-based rate (YouTube, 72) | hashtags (the one registered association, D-043) | LR test, 1 df, controls log followers + log video age | Spearman |
| 9-10 | view-based rate (YouTube) | call to action, hand-coded (the most robust addition, D-051; alpha 0.50) | LR test, 1 df | Mann-Whitney U |

- Mixed model with an account intercept, fitted with `fit()` of `src/stats/hypotheses.py` (five
  optimisers); LR tests from ML fits on the same rows; complete cases per test. Pooled controls as D-042
  (platform, log followers, log video age). On YouTube the account intercept rests on 5 channels, 58 videos
  from one - stated with every YouTube result.
- **Beside the family, never in it:** each test without the 15 AI-character Shorts (D-049; all 15 are YouTube);
  for any detected test, the within-account Spearman of D-043 (describes, changes no verdict); each null with
  its minimum detectable effect (two-sample or correlation, 80% power, alpha 0.05, no clustering - a lower bound).
- **Description only, no test:** Spearman between the view-based rate and the follower-based percentile on the 72
  YouTube videos - do the two measures rank YouTube videos alike?
- Every result carries: the Zero Sugar label's repeat reliability (YouTube alpha 0.25, Instagram -0.10); for call
  to action, the hand-coding caveats (one coder, 110 minutes for 100 minutes of video, alpha 0.50).

**Wording, fixed now:** "associated with", never "causes"; a test not detected is "not detected at this sample
size" with its minimum detectable effect. P20 does not change the 20 model features, the models or the tool.

---

## D-057 - Results of P20: no association detected for speech rate, brand or product mentions, or with YouTube views

**Date:** 2026-10-17
**Status:** Accepted - results of D-056, a declared addition; every earlier result is unchanged.
**Output:** `reports/statistical_results_p20.md`, `reports/statistical_family_p20.csv`
(`python -m src.stats.hypotheses_p20`; all 20 fits converged).

| # | Outcome | Measure (n, accounts) | Effect (95% CI) | BH p (test 1; test 2) | Without the 15 AI-character Shorts |
|---|---|---|---|---|---|
| 1-2 | percentile | speech rate (112, 16) | -1.4 points per SD (-8.6 to +5.8); Spearman rho -0.19 | 0.925; 0.344 | +0.5 points; rho -0.13 |
| 3-4 | percentile | product named - Zero Sugar (173, 20) | +2.0 points (-6.9 to +11.0); medians 0.58 vs 0.51 | 0.818; 0.818 | -2.4 points |
| 5-6 | percentile | brand named - Coca-Cola (192, 22; 26 not naming it, all Reels) | -1.7 points (-15.2 to +11.8); medians 0.56 vs 0.40 | 0.925; 0.344 | -1.5 points; rank test raw p 0.038 |
| 7-8 | YouTube per-view rate | hashtags (72, 5) | x1.18 per SD (0.97 to 1.44); rho +0.13 | 0.344; 0.594 | x1.31, raw p 0.024 |
| 9-10 | YouTube per-view rate | call to action (72, 5) | x0.71 (0.45 to 1.13); medians 1.1% vs 1.4% per view | 0.344; 0.818 | x0.70 |

**All ten not detected at this sample size** (minimum detectable effects: speech rate r 0.26; product named
d 0.46; brand named d 0.59; YouTube r 0.33 and d 0.67 - lower bounds). The without-series values are reported
beside the family and change no verdict.

**Description (no test): the two YouTube engagement measures do not rank videos alike** - Spearman between
the per-view rate and the follower-based percentile -0.05 over the 72 Shorts (-0.11 without the AI-character
series). Engagement per view and engagement per follower measure different things here, so the YouTube
results of this study are specific to the follower-based measure that D-005 chose for the platform
comparison. The call-to-action association of D-051 (follower-based) does not carry to the per-view rate,
where its estimate points the other way (not detected).

**Together with D-043 and D-051:** no further content measure is associated with engagement in this sample;
every proposal item is now measured or tested (P20 closes the last three).

---

## D-058 - Specification of the tool's video intake (task 12.4): uploads and links, cached by file fingerprint

**Date:** 2026-10-17
**Status:** Accepted - written before the intake code. Code `src/serve/intake.py`; it hands a file and its
details to the pipeline of D-055.

**Uploads.** A video file (mp4, mov, m4v, webm, mkv; at most 200 MB). It is stored once under
`data/interim/serve/media/<first 16 characters of its SHA-256>.<ext>`; the same file uploaded again is not
stored twice. Whether it is usable (opens as a video, has sound, at most 180 s) is decided by the pipeline's
checks (D-055 section 2), not by the file name.

**Links.** Only Instagram Reel or post links (`instagram.com/reel/...`, `/p/...`) and YouTube Shorts or video
links (`youtube.com/shorts/...`, `youtube.com/watch?v=...`, `youtu.be/...`); anything else is refused before
any request. The details are read first without downloading (yt-dlp, as `src/collect/instagram_links.py` does,
comments stripped - third-party personal data is not kept, D-018); a video longer than 180 s is refused
there, before the download. The file is then downloaded with **the same yt-dlp settings as the corpus**
(`fetch()` of `src/collect/download_media.py`: best video and audio up to 720p, merged to mp4), so a linked
video reaches the measurements in the same form the 300 did. **Always logged out: no cookies, no login, no
account** (D-020's spare-account cookies were deleted and are not used again). YouTube refused logged-out
downloads during collection (D-020); if it does so here, the tool says so in plain words and asks for the
file to be uploaded instead - it does not work around the check.
- **Taken from the link, shown to the user and editable:** the caption (Instagram: the post's text; YouTube:
  title, a line break, description - as in training) and the title. A follower count is taken only if the
  platform's public data gives one (YouTube channels usually do; logged-out Instagram usually does not), and
  is shown as "from the link" for the user to confirm; the tool still asks for it (TODO rule 7).
- Kept per link: platform, video id, account handle, caption, title, duration, follower count if given, and
  when it was fetched - nothing else.

**Cache.** A result is kept under `data/interim/serve/videos/<file fingerprint>/<inputs fingerprint>/`, where
the inputs fingerprint covers the platform, caption, title and collaboration answer. The same video with the
same inputs returns the saved result without measuring again; any changed input measures again. Every
folder is under `data/interim/` (never published, gitignored).

**Not done:** no batch or playlist downloads (one video per request), no private or login-only posts, no
storage of anything about the people who commented.

**Note 2026-10-17 - built and tested without network.** Nine link forms checked (Instagram reel, reels, p,
with an account path or tracking text; YouTube shorts, watch, youtu.be): the accepted ones resolve to the
video id and keep their kind; other sites and profile pages are refused. Uploads: a non-video, a video without
sound and a text file are refused, now *before* anything is stored (a first version stored a non-video before
the pipeline refused it; fixed, the file removed). The same clip uploaded twice: measured once (170 s, the
same score position as the 12.3 run), then reused in 15 s with the base rate recomputed for a new follower
count. **Not yet tested: a live link** - that downloads a video, and waits for the researcher's approval.

**Note 2026-10-17, later - live links tested (researcher's approval, chat 17 Oct: "yes test the links").** One
Instagram Reel (DaKsr6OzHqf, 1.8 MB, 10 s) and one YouTube Short (nUsWSsbWwYg, 5.3 MB, 7 s), both corpus videos
outside the 192, fetched logged out: **each downloaded file is byte-for-byte identical to the corpus file**
(same SHA-256), and each caption equals the corpus caption, so the measurements are those already checked
(73/73, D-055 note). YouTube did not ask for a sign-in this time and gave the channel's follower count (4.82
million); Instagram gave none. The Instagram handle was read from the wrong field (a number); fixed to the field
the collection code uses, and the one stored record corrected from the corpus.

---

## D-059 - Specification of the tool's web page (task 12.5), written before it was built

**Date:** 2026-10-17
**Status:** Accepted - written before the page code. Code `src/serve/app.py` (Flask), `src/serve/wording.py`
(every sentence the page shows), `src/serve/templates/`. Drivers (12.6) and warnings (12.7) are added to the same
page in their own tasks; this entry fixes the page and what it may say.

**Where it runs.** On this computer only: `python -m src.serve.app` serves `http://127.0.0.1:5055`, bound to
127.0.0.1 so no other machine can reach it. No accounts, no sign-in. Uploaded files, link downloads and results
stay under `data/interim/serve/` (gitignored). Nothing is sent anywhere except the platform request a link needs
(D-058).

**What it asks** (one screen):
- a video file **or** a link (D-058);
- the platform (Instagram or YouTube; with a link, the link decides);
- the account's follower count - asked every time (rule 7 of the task list); with a YouTube link that gives one,
  an empty field uses it and the page says "from the link";
- the caption: empty means **not known** (missing), unless the box "this post has no caption" is ticked (then a
  real empty caption); with a link, an empty field uses the link's caption;
- Instagram: "Is this post a collaboration with a creator?" yes / no / don't know (don't know = missing);
- "Does the video show Coca-Cola Zero Sugar?" yes / no / not sure - the models were fitted on Zero Sugar
  videos only (D-030); the answer feeds task 12.7's notice and changes no number;
- optional, folded away: the 11 hand-coded yes/no measures of D-050 (product prominent, logo prominent, a person,
  creator or celebrity, humour, excitement, excited voice, call to action, sponsored, lifestyle, homemade look),
  each "yes / no / skip" - shown beside the share among the 192, **never used in any number** (D-051).

**While it works.** One video at a time (the graphics card); the page shows the queue position and each of the
five measuring groups as it finishes, refreshing every few seconds; a refusal (D-055 section 2, D-058) is shown in
its plain words.

**What it shows**, in this order, worded as fixed in `wording.py`:
1. **What a typical video gets** (D-053/D-054): the typical engagement rate for a new account of that size and
   its 80% range, with the likes + comments range those give - labelled "the models could not predict better than
   this for an account they have not seen". Never a single predicted number, never "this video will get".
2. **Instagram only - the exploratory score** (D-054): "higher than X% of the 120 Instagram Zero Sugar videos,
   scored by the same model", labelled exploratory, with its measured accuracy (0.70 on unseen accounts) and that
   its scores barely move; **no probability**.
3. **The video's measures beside the 192**: each of the 20 in plain units, and the share of the 192 (and of that
   platform's videos) with a lower value; yes/no measures as "yes / no" beside the share of the 192 with "yes".
   Headed "a description, not advice: none of these was shown to raise engagement" (D-043, D-046 item 2).
4. **Your descriptions beside the 192** (if answered).
5. **What the tool did not have** - the missing inputs and how they were filled (D-055 section 5).
6. A link to **"About this tool"**: what it was trained on, the four checks and how each came out (G1 failed, G2
   failed, G3 failed and widened, G4 pending - in plain words), and how Zero Sugar videos fared on each platform
   described only, with the selection caveat (D-046 item 4).

**Never on the page:** a platform recommendation (D-046), a probability, "causes", "drives", "will get", or any
number from the pooled models or from the automated labels.

**Note 2026-10-17 - built and tested.** Four submissions to the running page: an upload with two optional
answers (the saved measurement reused; the page says so), a YouTube link (from the cached link record - no new
download; follower count 4.82 million taken from the link and marked so; caption from the link), a file that is
not a video (refused: "This file could not be opened as a video"), and an invalid form (two plain errors, nothing
queued). `python -m src.serve.app --check` rendered the form, the About page and the three jobs: no forbidden
wording. Changed after the first look: the waiting page now counts the video being measured; on a reused result
the page says the saved measurement was used instead of an old timing; the table heading says that videos with
the same value count half; the About page shows the limitations in plain words rather than the model card's
technical lines. Not on the page yet, by design: the three Instagram drivers (12.6) and the warnings, including
YouTube's too-narrow range and the Zero Sugar answer (12.7).

---

## D-060 - Specification of the tool's explanations (task 12.6) and warnings (task 12.7), written before either was built

**Date:** 2026-10-17
**Status:** Accepted - written before any explanation was computed for a new video and before the warning code
(researcher: "continue 12.6 and 12.7"). Code: `src/serve/explain_video.py` (12.6), `src/serve/wording.py`
(12.7 text), shown on the result page of D-059.

### Part 1 - explanations ("drivers", 12.6)

**Which, fixed by D-047 rule 9 and D-048:** only the Instagram content model (model B), and only its three
stable features - hashtags, share of the video with talking, share of frames with a face. **Instagram results
only.** The other 18 inputs also move the score but none was used consistently enough to be explained; the page
says so. YouTube results show no explanation and say why (no YouTube model could be tested, D-041).

**How, the same method as D-047:** `shap.LinearExplainer` on the served model, with the model's own imputed and
scaled inputs and **the 120 Instagram training videos as the background, all of them** (`max_samples` set - the
subsampling trap of D-047). The background is stored in `models/serving_schema.json`. Before anything is shown,
an additivity check (SHAP values + base value = the model's log-odds, to 1e-6) runs on every call, and at schema
build the served model's SHAP values for the 120 are checked against the plain linear formula (coefficient x
(scaled value - background mean)).

**Direction rule, fixed now:** a feature is explained only if the served model's coefficient has the sign D-048
found stable (more -> higher for all three). If a sign differs, that feature is listed as "not explained: the
served model does not agree with the stable direction" - never shown the other way round.

**What is shown per feature:** this video's value beside the average of the 120 Instagram videos (the SHAP
reference point), and the model's position with and without that difference - "with the average amount of
talking, the model would place it higher than X% of the 120 instead of Y%". A feature the tool could not measure
(missing, filled by the imputer) is shown as "not known" and not explained. **Wording:** "the model scores ...
higher", "associated with in this sample", never "drives", "causes", "add more ... to"; the hashtag line carries
D-043's caution (between accounts only: accounts that use more hashtags, not something shown to help one video);
the talking and face lines carry D-052's YouTube description (on YouTube the 72 Shorts showed the opposite -
described, not tested).

### Part 2 - warnings (12.7; docs/11 section 4.3, D-046, D-053, D-055 section 2)

A notice at the top of the result when any of these holds (each with its reason in plain words):
1. **Not Zero Sugar:** the user answered "no" or "not sure" to "Does the video show Coca-Cola Zero Sugar?" - the
   models learned from Zero Sugar videos only (D-030); the result is shown, marked as unlike the training data.
   The tool cannot check this itself (automatic product detection failed, D-033, D-037).
2. **Followers outside 7,594 to 17.1 million** - the typical-rate range is then an extrapolation (D-053).
3. **Shorter than 3.9 s, or a shape outside the width-to-height range 0.45-0.80** (D-055 section 2).
4. **Measures outside the range of the 192** (any of the 20 above or below every one), naming them.
5. **Instagram score outside the range of the 120** (above or below every training score).

Always shown, in their sections:
6. **How sure (docs/11 "confidence badge", driven by the interval width):** high if the top of the 80% range is
   at most 3 times the bottom, moderate up to 10 times, low above that - with the ratio in words. (With the
   intervals of D-054 every result is "low", and the page says why.)
7. **YouTube's range is too narrow** - on every YouTube base rate: on accounts the model had not seen it held 69%
   of videos, not 80% (D-054).
8. **Exploratory** on the Instagram score (already in D-059) and **no probability**.
9. **What this cannot tell you** (docs/11 section 4.3, section 6): posting time, hashtag or posting advice, paid
   promotion, the platform's own distribution, Instagram reach (no reliable views, docs/06), sales; a typical
   result for an account, not a forecast for this video.
10. **The release checks** in one line under the result, from the model card: G1-G3 failed with the fallbacks
    named, G4 pending until task 12.8 changes it.
11. Missing caption, collaboration or speech - already in "what the tool did not have" (D-059).

**Never:** hiding a warning when it applies, or softening one because the result looks good.

---

## D-061 - Writing is kept off the repository: a separate `writing/` folder

**Date:** 2026-10-17
**Status:** Accepted - the researcher's decision (chat, 17 October: only the coding and data part should be on the
repository, not the reports or papers; then, of the options put to her, "only papers/reports" and "move them all").

**What changes.** A new folder `writing/`, listed in `.gitignore`, holds everything written for people rather than
produced by the code: `writing/paper/` (the journal template, the paper's facts sheet and template, and exports of the
paper draft), `writing/progress-reports/` (the weekly reports) and `writing/project/` (proposal, literature survey,
meeting handout, reference guide). The 14 Word files that sat at the project root were moved there unchanged.

**What does not change.** The repository keeps the code (`src/`), the locked hand codes (`data/coding/`), the method
notes and this decision log (`docs/`) and the analysis results (`reports/`, including `reports/shared/`), so nothing
the supervisor can read today disappears. The root `/*.docx` rule stays as a second guard.

---

## D-062 - Results of G4 (task 12.8): nine of ten videos match exactly; the tenth shows that unclear speech is re-read at random

**Date:** 2026-10-17
**Status:** Accepted - results of D-055 section 6, run as fixed there (researcher: "go, run 12.8"). Output
`reports/serving_parity.md` (`python -m src.serve.parity --run`, run 1 47.5 min, run 2 37.8 min, about 4 minutes a
video).

**Result - the gate fails as registered.** Of 420 comparisons of model inputs and outputs (10 videos, both runs), 417
are identical; of 1,460 comparisons of the measures behind them, 1,439. **Nine of the ten videos match the study
exactly in both runs** - every model input, the Instagram score position and all 73 measures - including Hindi and
Turkish speech that is translated, a Reel with silent audio and four videos without speech. The tenth, Instagram
`Da4ZFCUssvp` (132 s, Swahili speech the engine read with low confidence), differs in its speech-derived measures: the
share of talking (a model input) was 0.382 in the study, 0.420 in run 1 and 0.372 in run 2; its Instagram score
position 92.5% in the study, 93.3% in run 1 and 92.5% in run 2. Primary (bit for bit) and secondary (within 1e-6) rules
both fail on this video.

**Cause, found before anything was changed.** The two records agree in everything before the words: the audio (same
samples, peak and loudness), the speech regions found, the detected language (Swahili, probability 0.5596) and every
recorded setting. Only the decoded text differs, and its confidence is very low (average log-probability -2.67 in
the study, -0.72 and -2.83 in the tool's runs). faster-whisper 1.2.1, used unchanged with its default settings,
re-decodes a passage at rising temperatures (0.2 to 1.0, with random sampling) whenever its log-probability falls
below -1.0 or its compression ratio above 2.4; no random seed was set in the study. **So the transcript of unclear
speech is a random draw - in the study as in the tool - and the tool's two runs differ from each other as much as
from the study.** It is not a fault of the pipeline (D-055 section 3 holds: the same code, the same settings), and it
cannot be removed without re-measuring the study's videos, which is not allowed after the results; fixing a seed in
the tool would make the tool repeatable but still could not reproduce the study's draw.

**How far it reaches in the study:** at least 5 of the 124 analysis-set videos with transcribed speech have a passage
below those limits (3 Instagram, 2 YouTube) - a lower bound, because a passage that passed after a retry is not
recorded as such. For them, the speech-derived measures (share of talking, words per minute, voice pitch, speech
sentiment and emotion, the keyword flags from speech) carry run-to-run noise. Share of talking is one of the three
features the Instagram model relies on (D-048); the analysis results are not re-run (no rule allows it), and the
noise is stated as a limitation.

**What follows, as D-055 fixed it:** the tool is released with G4 marked failed - on its model card and About page,
naming the measure and the size of the difference. **Added after the result, as a warning, not a rule change:** the
tool now tells the user when a video's speech is unclear, that its transcript and the talking and keyword measures
can change from run to run (`speech_unclear` in `src/serve/pipeline.py`). Trigger: the study's own low-confidence
flag of 5.6 (D-027), or a passage below the engine's retry limits (the study's `SUSPECT_LOGPROB` and
`SUSPECT_COMPRESSION`). The limits alone missed the Swahili video in run 1, whose random retry happened to succeed and
left no trace; the low-confidence flag caught it in both runs. Cautious by design: it fires on 3 of the 10 G4 videos
(one changed) and on 30 of the 121 analysis-set videos with speech, so the page says "can change", not "will".

**Note 2026-10-17 - built and checked.** At schema build: the served model's coefficients for hashtags, talking
and faces all have the stable sign (all three explained); SHAP values of the served model equal the linear formula
on the 120 (largest gap 0.0); the 120 x 21 background is stored. On the Instagram test clip (no caption): talking
89% of the video against an average of 29% - with the average, the score would sit higher than 78% of the 120
instead of 89%; faces 0% of frames against 47% - with the average, 96%; hashtags not known (no caption). The
other 18 inputs together moved its score more than these three, and the page says so. **Warnings seen on the
running page:** "not Zero Sugar" and "not sure" answers, followers below the training range (1,000), a measure
above every one of the 192 (on-screen text blocks); certainty "low" on every result (ratio of the range's top to
bottom about 8,000); YouTube's too-narrow range; no YouTube explanation and why; "what this cannot tell you"; the
release-check line. Changed after reading the pages: "about 0" instead of "fewer than 1" likes; the certainty level
no longer printed twice; the with-average sentence shortened; hashtags "not known (no caption was given)"; tables
kept inside their boxes on a narrow window. `python -m src.serve.app --check`: 6 pages, no forbidden wording.

---

## Open decisions

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

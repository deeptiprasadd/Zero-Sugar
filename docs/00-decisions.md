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

## Open decisions

| ID | Question | Blocking | Needed by |
|---|---|---|---|
| O-01 | ~~Guide approval for scraping~~ — **superseded by D-010.** Now: read the institutional data/ethics policy yourself and record the finding. | No | Before IG collection |
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

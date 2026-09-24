# 03 — Sampling Frame

The sampling frame is part of the method, not a convenience. It is versioned here and any
change gets a dated entry in §6.

**Target:** 150 YouTube Shorts + 150 Instagram Reels, spread across markets and languages
so that no single market dominates.

---

## 1. Inclusion criteria

A video enters the corpus only if **all** of the following hold:

1. **Format** — vertical short-form. YouTube Short (≤180s, vertical) or Instagram Reel.
2. **Product** — Coca-Cola Zero Sugar is visible or explicitly named. Tier-3 escalation
   (brand family) is permitted only under open decision O-02, and is flagged.
3. **Window** — published between **1 January 2022 and 31 December 2025**. Short-form
   before 2022 is sparse and formats were still settling; 2026 posts are too young for
   engagement to have stabilised.
4. **Public** — publicly accessible at collection time.
5. **Duration** — at least 5 seconds. Below that, most extracted features are degenerate.
6. **Audio present** — a video with no audio track cannot support Block B. Silent videos
   are excluded and the exclusion count is reported.

### Exclusion criteria

- Duplicate content cross-posted to both platforms (see §4 — this needs a decision per
  pair, not a blanket rule).
- Videos where the product appears only as incidental background in user-generated content
  with no brand association.
- Non-marketing content (news coverage, unboxing by unaffiliated users) unless deliberately
  sampled as a comparison tier.

---

## 2. Market and language quotas

Target ~25 videos per market per platform, six markets, 150 per platform. Quotas are
targets, not hard constraints — record actuals and report shortfalls.

| Market | Primary language | YT target | IG target | YT actual | IG actual |
|---|---|---|---|---|---|
| Global / US | English | 25 | 25 | | |
| India | Hindi / English | 25 | 25 | | |
| Latin America | Spanish | 25 | 25 | | |
| Brazil | Portuguese | 25 | 25 | | |
| MENA | Arabic | 25 | 25 | | |
| Southeast Asia | Indonesian / Thai | 25 | 25 | | |
| **Total** | | **150** | **150** | | |

Markets can be substituted if a target market yields too little content — Japan, Western
Europe (French, German, Spanish) and Nigeria/South Africa are reasonable alternates. Log
any substitution in §6.

**Why quotas matter here.** Without them, the global English account will dominate simply
because it posts most, and `market` will collinear with `account`, making both
uninterpretable. Balanced cells keep the language and market effects estimable.

---

## 3. Candidate accounts

> ⚠️ **Every handle below is a candidate and must be verified before the frame is locked.**
> Confirm each account exists, is official, is a Business/Creator account (Instagram), and
> actually posts short-form. Replace anything that fails. Do not collect against an
> unverified frame.

### YouTube channels — to verify

| Market | Candidate channel | Verified? | Channel ID | Subs | Shorts found |
|---|---|---|---|---|---|
| Global | Coca-Cola | ☐ | | | |
| India | Coca-Cola India | ☐ | | | |
| LatAm | Coca-Cola (regional) | ☐ | | | |
| Brazil | Coca-Cola Brasil | ☐ | | | |
| MENA | Coca-Cola (regional) | ☐ | | | |
| SEA | Coca-Cola Indonesia | ☐ | | | |

### Instagram accounts — to verify

| Market | Candidate handle | Verified? | Business acct? | Followers | Reels found |
|---|---|---|---|---|---|
| Global | @cocacola | ☐ | ☐ | | |
| India | @cocacola_in | ☐ | ☐ | | |
| LatAm | regional handle | ☐ | ☐ | | |
| Brazil | @cocacola_br | ☐ | ☐ | | |
| MENA | regional handle | ☐ | ☐ | | |
| SEA | regional handle | ☐ | ☐ | | |

**How to verify:** Coca-Cola's own corporate site lists regional social properties; work
from there rather than from search results, so the frame is traceable to an authoritative
source. Record where each handle was confirmed.

### Creator and influencer accounts

Pending open decision **O-04**. If in scope, build this list from paid-partnership labels
and branded-content disclosures on the brand accounts' tagged content rather than from
hashtag search.

---

## 4. Cross-posted duplicates

Coca-Cola frequently posts the same creative to both YouTube Shorts and Instagram Reels.
This is a genuine problem for H7 and H9, and it cuts both ways:

- **Keeping duplicates** is arguably *ideal* — the same creative on two platforms is a
  natural experiment isolating platform effect from content effect.
- **Keeping duplicates unflagged** violates independence and inflates the platform
  comparison.

**Decision:** keep them, but detect and flag them. Add a `creative_id` that is shared
across platforms for matched pairs, detected by perceptual hash of sampled frames plus
manual confirmation. Then:

- Main models treat videos independently but cluster standard errors on `creative_id` as
  well as account.
- Run a **paired sub-analysis** on the matched pairs alone. If there are enough pairs
  (≥20), this is the cleanest possible test of H7 and potentially the strongest result in
  the thesis.

Record the pair count in §5.

---

## 5. Frame status

| Metric | Target | Actual |
|---|---|---|
| YouTube channels verified | 6+ | |
| Instagram accounts verified | 6+ | |
| YouTube Shorts collected | 150 | |
| Instagram Reels collected | 150 | |
| Markets represented | 6 | |
| Languages represented | 6+ | |
| Cross-posted pairs identified | — | |
| Excluded: silent | — | |
| Excluded: too short | — | |
| Excluded: product not present | — | |
| Tier 1 / 2 / 3 split | — | |

---

## 6. Frame change log

> Any change to accounts, quotas, markets or criteria after the frame is locked goes here
> with a date and reason.

| Date | Change | Reason |
|---|---|---|
| 2026-09-09 | Frame drafted, unverified | Initial |
| 2026-09-22 | **Realised samples differ by platform in how videos were chosen; now recorded per row (D-029).** Every corpus row carries `selection`: Instagram 107 `hand_picked` (researcher's Zero Sugar list, D-018) + 43 `systematic`; YouTube 150 `systematic`. YouTube Zero Sugar is now decided by eye for every Short text does not name: **25 → 74** (72 of 144 usable). Instagram's 37 random Reels have not had the same check. Frame, accounts and quotas unchanged; nothing new collected | A raw platform difference would otherwise be tangled with product and selection. The platform comparison is pre-registered in [08](08-statistical-analysis.md) §7 |
| 2026-09-23 | **Analysis narrowed to Coca-Cola Zero Sugar (D-030, supervisor's decision).** Collection and feature extraction stay on all 300 videos; the corpus is unchanged. An `in_focus` flag marks the **186 Zero Sugar corpus videos (183 usable: Instagram 111 / 16 accounts, YouTube 72 / 5, 58 of those from the global channel)**, and the 114 others stay in every file, flagged, as a robustness set. Unequal counts per platform are accepted by the supervisor | §1 criterion 2 of this document — "Coca-Cola Zero Sugar is visible or explicitly named" — is in force again, but as an *analysis* filter rather than a collection filter. D-014's brand-family collection is what made a Zero Sugar set of this size reachable at all |

> **Note (2026-09-22, updated 2026-09-23).** The 2022-2025 window above is superseded (D-019) and
> §2-3's six-market quota plan was replaced by the verified frames (D-011, D-015). §1 criterion 2
> (Zero Sugar visible or named) was superseded **for collection** by D-014 and applies again
> **for analysis** under D-030: everything is collected and measured, and the 183 usable Zero
> Sugar videos are what the results rest on. For the sample as built, see the per-row `selection`,
> `zs_label_method` and `in_focus` columns, D-029's composition table and D-030's focus counts.

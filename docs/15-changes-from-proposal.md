# 15 — Changes from the proposal (P18)

**Written 2026-10-09.** Source material for the methods chapter's "Changes from the proposal" section: every
place where the study differs from `coco-cola-proposal.docx`, what was done instead, and why, each tied to
its decision so it can be checked. Nothing here is new analysis.

| # | The proposal said | What the study did | Why | Decision |
|---|---|---|---|---|
| 1 | Coca-Cola Zero Sugar videos on YouTube and Instagram | YouTube **Shorts** against Instagram **Reels** only | Long YouTube videos against Reels would mix up platform with format; matched short vertical format makes the platform comparison fair | D-001 |
| 2 | Zero Sugar promotional videos | Two corpora of 150 (brand family, variant recorded), then the analysis narrowed to the **192 usable Zero Sugar videos** (Instagram 120, YouTube 72) | Too few Zero Sugar videos existed for 150 per platform; the supervisor asked for Zero Sugar only on 23 September | D-013, D-014, D-030, D-039 |
| 3 | Engagement = (likes + comments + shares) / views | (likes + comments) / **followers**, ranked within platform and follower tier; high/low = median split | Shares are not public on either platform; Instagram does not publish reliable Reel views; raw rates differ about 55-fold between platforms | D-005, docs/06 |
| 4 | Stratified train/test split | **Account-grouped** cross-validation, 5 folds x 3 repeats | Videos from one account are not independent; a random split lets the model learn the account instead of the content | D-006, D-044 |
| 5 | Aspect ratio as a video feature | Dropped | Every video is vertical by construction, so it carries no information | D-024, D-036 |
| 6 | 60-80 features across Blocks A-E | **20 content features**, fixed in priority order before any engagement value was seen | At 192 videos more features overfit and make SHAP unstable | D-007, D-030, D-036 |
| 7 | Product visibility, logo visibility (automated) | Automated detection failed its validation; **hand-coded** by the researcher on all 192 | Neither whole-image CLIP nor a container detector passed the gates fixed in advance | D-033, D-037, D-049 |
| 8 | Music type | Automated genre labels not measurable; **hand-coded by ear** from a short fixed list | AudioSet genre scores were indistinguishable from nonsense labels on this corpus | D-033, D-049 |
| 9 | Call to action, influencer, celebrity, humour | A local vision-language model's labels failed agreement with the researcher's codes; **hand-coded** on all 192 | Best alpha 0.38 against the 0.67 required | D-038, D-049 |
| 10 | Emotional tone of the voice, campaign type, sponsored content | Dropped on 24 September, then **hand-coded** on all 192 at the researcher's request | No model could measure them; the researcher wanted nothing in the proposal missing | D-032, D-049 |
| 11 | Emotion | Measured on the English translation of speech only, for the 119 videos with speech | The emotion model is English-only; translation flattens nuance (stated) | D-031, D-040 |
| 12 | Posting time | UTC hour in the models; **local hour** added as a sensitivity analysis; the global account (77 videos) stays in UTC | The data carry no time zone; markets were mapped to zones afterwards | D-036, D-050 |
| 13 | Keywords | Six keyword groups merged into three features | Applied strictly, the feature budget would have deleted all six and the text hypothesis's instrument | D-036 |
| 14 | No statistical-analysis section; RQ9 missing from the numbering | Mixed-effects tests of H1-H10 with Benjamini-Hochberg correction; RQ9 added: does content predict beyond reach? | The framework lists a statistical stage and H1-H7 imply formal tests | D-042 |
| 15 | A paired comparison of the same video on both platforms (implied by H7) | Not run | Only 2 cross-posted pairs were found against the 20 needed | D-040 |
| 16 | Per-platform effects (H9, SHAP by platform) | One pooled model explained per platform, plus an exploratory Instagram-only model; **no YouTube-only model** | 72 YouTube videos from 5 channels (58 from one) cannot support account-grouped testing | D-041 |
| 17 | Threshold optimisation | The registered F1-maximising threshold reported, with Youden's J beside it; ROC-AUC the headline | The F1 rule labels almost every video "high" on this near-even split | D-044 |
| 18 | SHAP on XGBoost / Random Forest | SHAP on the pooled XGBoost and two Instagram models, interpreted only where a stability rule fixed in advance was met | Small samples make SHAP rankings unstable | D-047 |
| 19 | Not in the proposal | A **prediction tool**, now requested by the supervisor; re-scoped to an honest base rate, video diagnostics and an exploratory Instagram score | No pooled model beat reach for new accounts, so the pre-registered fallback applies | D-017, D-046 |
| 20 | Not in the proposal | The hand-coded measures reported as a **declared addition**, beside the pre-registered results, never in place of them | They were measured after the main results existed | D-049, D-050 |

**Collection routes the methods chapter must state** (D-010): YouTube Data API v3; a commercial
scraping service (Apify) for Instagram, which is against Instagram's terms of service; yt-dlp, logged out
for Instagram and through a spare signed-in account for YouTube video files; ten login-only Reels saved by
hand and their counts read from screenshots. Full record: [12-data-collection-record.md](12-data-collection-record.md).

# 5.12 pilot - which local model labels best (D-038)

10 of the researcher's 60 coded videos (5 per platform, seed 20260929), drawn before any model ran. Rule fixed in advance: highest agreement on the four checked constructs, a model 'unsure' counting as not agreeing; ties -> more valid answers, then faster. Prompt version `93ee43248ea4`, temperature 0, seed 20260929.

| Model | Digest | Agreement (checked 4) | Valid answers | Sec / video | Share on GPU |
|---|---|---|---|---|---|
| `qwen3-vl:4b` | `1343d82ebee3` | **70%** (26/37) | 9/10 | 22.6 | 1.0 |
| `qwen2.5vl:3b` | `fb90415cde1e` | **62%** (23/37) | 10/10 | 99.8 | 1.0 |

**Chosen by the rule: `qwen3-vl:4b`.**

Per construct, pilot videos only (model vs researcher, researcher-unsure left out):

| Model | has_celebrity | has_influencer | has_cta | humour_present |
|---|---|---|---|---|
| `qwen3-vl:4b` | 8/10 | 6/9 | 5/10 | 7/8 |
| `qwen2.5vl:3b` | 10/10 | 6/9 | 6/10 | 1/8 |

Ten videos cannot measure reliability - that is 4.2's job, on the 50 coded videos the pilot did not use. The pilot only picks the model.

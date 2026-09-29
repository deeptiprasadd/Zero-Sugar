# 5.12 pilot - which local model labels best (D-038)

10 of the researcher's 60 coded videos (5 per platform, seed 20260929), drawn before any model ran. Rule fixed in advance: highest agreement on the four checked constructs, a model 'unsure' counting as not agreeing; ties -> more valid answers, then faster. Prompt version `93ee43248ea4`, temperature 0, seed 20260929, model reasoning off.

| Model | Digest | Agreement (checked 4) | Valid answers | Sec / video | Share on GPU |
|---|---|---|---|---|---|
| `qwen3-vl:4b` | `1343d82ebee3` | **57%** (21/37) | 10/10 | 2.9 | 1.0 |

**Re-run rule (D-038, written before this run): Qwen3-VL with reasoning off is used only if it reaches Qwen2.5-VL 3B's 62% (23/37) from `annotation_pilot.md`. It reached 57% (21/37), so Qwen2.5-VL 3B is used.** (This run had one model in it, so the script's automatic 'chosen' line did not apply and was replaced by this one.)

Per construct, pilot videos only (model vs researcher, researcher-unsure left out):

| Model | has_celebrity | has_influencer | has_cta | humour_present |
|---|---|---|---|---|
| `qwen3-vl:4b` | 8/10 | 5/9 | 4/10 | 4/8 |

Ten videos cannot measure reliability - that is 4.2's job, on the 50 coded videos the pilot did not use. The pilot only picks the model.

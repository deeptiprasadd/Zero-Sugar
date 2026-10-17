# G4 - does the tool measure exactly as the study did? (task 12.8, rules fixed in D-055 section 6)

The 10 videos drawn on 17 October before any pipeline run (serving_parity_sample.csv), each measured from its file with the caption the corpus holds and its recorded collaboration flag, in a fresh empty folder, **twice**. Compared: the inputs of the models (21 for Instagram, the 20 content features for YouTube) against the values the models were trained on, and for Instagram the score position. Primary rule: every input identical, missing equal to missing, in both runs. Secondary: counts and flags identical, continuous values within 1e-6. No engagement value is read out.

**Verdict: FAIL** - model inputs and outputs identical in 417 of 420 comparisons (both runs); the flattened features behind them identical in 1439 of 1460; run 1 against run 2: 14 differences. About 254 s per video.

| Video | Speech | Run | Model inputs identical | Features identical | Seconds |
|---|---|---|---|---|---|
| instagram Da4ZFCUssvp | yes | 1 | 20/22 | 62/73 | 610 |
| instagram DTAgD-IExL- | yes | 1 | 22/22 | 73/73 | 331 |
| instagram Da8In57ug3r | yes | 1 | 22/22 | 73/73 | 322 |
| instagram DcGF4VEIxbT | no | 1 | 22/22 | 73/73 | 193 |
| instagram Cd5oWJNsfI0 | no | 1 | 22/22 | 73/73 | 182 |
| youtube Uf__4_hjwoM | yes | 1 | 20/20 | 73/73 | 222 |
| youtube YEo8ShllJ1g | yes | 1 | 20/20 | 73/73 | 271 |
| youtube vFrcDKzucBI | yes | 1 | 20/20 | 73/73 | 250 |
| youtube 7P6P4bSZr5g | no | 1 | 20/20 | 73/73 | 226 |
| youtube Fi3fytTXkoA | no | 1 | 20/20 | 73/73 | 209 |
| instagram Da4ZFCUssvp | yes | 2 | 21/22 | 63/73 | 405 |
| instagram DTAgD-IExL- | yes | 2 | 22/22 | 73/73 | 282 |
| instagram Da8In57ug3r | yes | 2 | 22/22 | 73/73 | 331 |
| instagram DcGF4VEIxbT | no | 2 | 22/22 | 73/73 | 164 |
| instagram Cd5oWJNsfI0 | no | 2 | 22/22 | 73/73 | 142 |
| youtube Uf__4_hjwoM | yes | 2 | 20/20 | 73/73 | 206 |
| youtube YEo8ShllJ1g | yes | 2 | 20/20 | 73/73 | 191 |
| youtube vFrcDKzucBI | yes | 2 | 20/20 | 73/73 | 166 |
| youtube 7P6P4bSZr5g | no | 2 | 20/20 | 73/73 | 179 |
| youtube Fi3fytTXkoA | no | 2 | 20/20 | 73/73 | 196 |

## Every difference

| Run | Video | Level | Measure | Tool | Study | Within 1e-6 |
|---|---|---|---|---|---|---|
| 1 | instagram Da4ZFCUssvp | feature | word_count | 133 | 94 | no |
| 1 | instagram Da4ZFCUssvp | feature | words_per_min | 96.1 | 67.9 | no |
| 1 | instagram Da4ZFCUssvp | feature | pitch_std_semitones | 5.713 | 3.945 | no |
| 1 | instagram Da4ZFCUssvp | feature | voiced_frac | 0.7702 | 0.7129 | no |
| 1 | instagram Da4ZFCUssvp | feature | talk_dur_frac | 0.42 | 0.382 | no |
| 1 | instagram Da4ZFCUssvp | feature | pitch_median_talk_hz | 205.3 | 218.5 | no |
| 1 | instagram Da4ZFCUssvp | feature | pitch_std_talk_semitones | 5.713 | 3.945 | no |
| 1 | instagram Da4ZFCUssvp | feature | kw_together | True | False | no |
| 1 | instagram Da4ZFCUssvp | feature | sentiment_speech | -0.0104 | 0.0364 | no |
| 1 | instagram Da4ZFCUssvp | feature | emotion_score | 0.2661 | 0.6333 | no |
| 1 | instagram Da4ZFCUssvp | feature | kw_experience | True | False | no |
| 1 | instagram Da4ZFCUssvp | model input | talk_dur_frac | 0.42 | 0.382 | no |
| 1 | instagram Da4ZFCUssvp | output | instagram score position | 93.3 | 92.5 | no |
| 2 | instagram Da4ZFCUssvp | feature | word_count | 127 | 94 | no |
| 2 | instagram Da4ZFCUssvp | feature | words_per_min | 91.7 | 67.9 | no |
| 2 | instagram Da4ZFCUssvp | feature | pitch_median_hz | 200.5 | 202.8 | no |
| 2 | instagram Da4ZFCUssvp | feature | pitch_std_semitones | 4.179 | 3.945 | no |
| 2 | instagram Da4ZFCUssvp | feature | voiced_frac | 0.7233 | 0.7129 | no |
| 2 | instagram Da4ZFCUssvp | feature | talk_dur_frac | 0.3721 | 0.382 | no |
| 2 | instagram Da4ZFCUssvp | feature | pitch_median_talk_hz | 207.2 | 218.5 | no |
| 2 | instagram Da4ZFCUssvp | feature | pitch_std_talk_semitones | 4.179 | 3.945 | no |
| 2 | instagram Da4ZFCUssvp | feature | sentiment_speech | 0.0398 | 0.0364 | no |
| 2 | instagram Da4ZFCUssvp | feature | emotion_score | 0.4257 | 0.6333 | no |
| 2 | instagram Da4ZFCUssvp | model input | talk_dur_frac | 0.3721 | 0.382 | no |

Code: `python -m src.serve.parity --run`. Automated-label columns are not compared (the tool does not run them, D-038).

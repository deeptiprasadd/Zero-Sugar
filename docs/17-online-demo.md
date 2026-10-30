# Online demo on Render (D-066)

The tool measures a new video with about 6 GB of models and a graphics card, so it runs on the researcher's computer
(`python -m src.serve.app`). Render has neither, so the site published there is a **demo**: the redesigned pages with the
saved results of the six example videos, the About page and nothing that measures. The demo is switched on by the
environment variable `COKE_DEMO=1`, which `render.yaml` sets.

## What the demo needs (all in the repository)
| File | What it is |
|---|---|
| `render.yaml` | Render blueprint: web service, build and start commands, health page `/healthz` |
| `requirements-render.txt` | Six packages (Flask, gunicorn, numpy, pandas, scikit-learn, joblib) |
| `models/` five small files | `base_rate.json`, `instagram_content_logreg.joblib`, `reference_quantiles.json`, `model_card.json`, `serving_schema.json` (about 0.3 MB) |
| `deploy/examples.json`, `deploy/results/` | The six example cards and their saved results (no video, no folder path) |
| `.gitattributes` | Keeps the model files' bytes unchanged so their fingerprints still match on Render |

The videos, `data/`, the other models and the speech and picture libraries are not needed and are not published.

## Deploy
1. Push the repository to GitHub (it is public).
2. On render.com: **New +** > **Blueprint**, choose the repository, confirm `reelmetrics`. The free plan is enough.
3. When the build finishes, open the address Render shows. `/healthz` answers "ok".

Free services sleep after a quiet spell; the first visit afterwards takes about half a minute.

## Refresh the demo files (only if an example, a model or a sentence changes)
```
python -m src.serve.examples --export-demo
```
Then commit `deploy/` and the five `models/` files again.

## Check before pushing
```
python -m src.serve.app --check                      # laptop mode
set COKE_DEMO=1 && python -m src.serve.app --check   # demo mode (PowerShell: $env:COKE_DEMO=1)
```
Both must say "wording ok" for every page.

## Quick check and results in Google Drive (D-071, D-072)
The public site also offers a **quick check**: the visitor enters the platform, the account's followers and the
caption, and gets the typical result for that account size, the caption beside the 192 and ideas worth testing - in a
few seconds, with no video. Each result can be kept in the researcher's Google Drive (folder "ReelMetrics data" and
Sheet "ReelMetrics checks"): no caption text, no link, no personal data.

To switch on Drive saving:
1. Once, on the researcher's computer: `python -m src.serve.drive_login secrets/<OAuth client file>.json`
   (signs in, creates the folder and Sheet, prints one line `REELMETRICS_GOOGLE = '''...'''`).
2. In the Render dashboard: the service > **Environment** > add `REELMETRICS_GOOGLE` with the text between the triple
   quotes as its value > **Save** (Render redeploys).

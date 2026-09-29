"""Task 4.2 - Krippendorff's alpha, researcher vs automated labels, per checked construct (D-038).

Rules, fixed before any model ran (D-038):
    * nominal alpha, two coders (researcher, model); "unsure" on either side is missing
    * primary sample: the 50 coded videos the 5.12 pilot did not use; all 60 reported too
    * 95% interval from 2,000 bootstrap resamples of videos (seed 20260929)
    * a construct is dropped if the point alpha < 0.67, if alpha cannot be computed, or if the
      model said "unsure" on more than 20% of the construct's videos

The manual codes file is only read, never written. No engagement value is read.

Usage:
    python -m src.features.reliability
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features.annotate import CHECKED, CODES, PILOT_SAMPLE, SUMMARY  # noqa: E402

ALPHA_MIN = 0.67
MAX_UNSURE = 0.20
N_BOOT = 2000
SEED = 20260929
REPORT = config.REPORTS / "annotation_reliability.md"
RESULT = config.INTERIM / "annotation_reliability.csv"   # read by 5.11 rule 3


def alpha_nominal(a: np.ndarray, b: np.ndarray) -> float:
    """Krippendorff's alpha for two coders, nominal data, pairs with a missing value dropped."""
    keep = pd.notna(a) & pd.notna(b)
    a, b = a[keep], b[keep]
    if len(a) < 2:
        return float("nan")
    vals = np.concatenate([a, b])
    cats = sorted(set(vals))
    if len(cats) < 2:
        return float("nan")
    n = len(vals)
    d_o = float((a != b).sum()) * 2 / n          # observed disagreement (coincidence matrix)
    counts = pd.Series(vals).value_counts()
    d_e = (n * n - float((counts ** 2).sum())) / (n * (n - 1))
    return 1 - d_o / d_e if d_e > 0 else float("nan")


def boot_ci(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    out = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(a), len(a))
        v = alpha_nominal(a[i], b[i])
        if not np.isnan(v):
            out.append(v)
    if len(out) < N_BOOT / 2:
        return float("nan"), float("nan")
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def table(m: pd.DataFrame) -> list[dict]:
    rows = []
    for f in CHECKED:
        human = m[f].where(m[f] != "unsure").to_numpy(dtype=object)
        auto = m[f"auto_{f}"]
        unsure_share = float((auto == "unsure").mean())
        machine = auto.where(auto != "unsure").to_numpy(dtype=object)
        human = np.array([x if pd.notna(x) else None for x in human], dtype=object)
        machine = np.array([x if pd.notna(x) else None for x in machine], dtype=object)
        keep = np.array([x is not None and y is not None for x, y in zip(human, machine)])
        a_ = alpha_nominal(human[keep], machine[keep])
        lo, hi = boot_ci(human[keep], machine[keep])
        agree = float((human[keep] == machine[keep]).mean()) if keep.any() else float("nan")
        passed = (not np.isnan(a_)) and a_ >= ALPHA_MIN and unsure_share <= MAX_UNSURE
        rows.append({"construct": f, "n_pairs": int(keep.sum()),
                     "human_unsure": int((m[f] == "unsure").sum()),
                     "model_unsure": int((auto == "unsure").sum()), "model_unsure_share": unsure_share,
                     "agreement": agree, "alpha": a_, "ci_lo": lo, "ci_hi": hi, "passed": passed,
                     "human_yes": int((human[keep] == "yes").sum()),
                     "model_yes": int((machine[keep] == "yes").sum())})
    return rows


def fmt(x: float, p: str = ".2f") -> str:
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else format(x, p)


def main() -> dict[str, bool]:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    codes = pd.read_csv(CODES, dtype={"media_id": str})
    coded60 = SUMMARY.parent / "annotation" / "coded60_summary.csv"
    src = SUMMARY if SUMMARY.exists() and (not coded60.exists() or
                                           SUMMARY.stat().st_mtime > coded60.stat().st_mtime) else coded60
    auto = pd.read_csv(src, dtype={"media_id": str})   # same labels either way: one cache
    pilot = pd.read_csv(PILOT_SAMPLE, dtype={"media_id": str})
    m = codes.merge(auto, on=["platform", "media_id"], how="left")
    missing = int(m["valid"].isna().sum())
    if missing:
        raise SystemExit(f"{missing} coded videos have no automated label - run 5.12 first")
    m["in_pilot"] = m.set_index(["platform", "media_id"]).index.isin(
        pilot.set_index(["platform", "media_id"]).index)
    held = m[~m["in_pilot"]]

    prim = table(held)
    full = table(m)
    lines = ["# 4.2 annotation reliability - researcher vs model (D-038)", "",
             f"Researcher's 60 blind codes (`manual_codes_FINAL.csv`, read only) against the 5.12 "
             f"automated labels. **Primary: the {len(held)} coded videos the pilot did not use.** "
             "Nominal Krippendorff's alpha; 'unsure' on either side is missing; 95% interval from "
             f"{N_BOOT:,} bootstrap resamples. Rule fixed before any model ran: keep only if alpha "
             f">= {ALPHA_MIN} and the model said 'unsure' on at most {MAX_UNSURE:.0%} of videos.", "",
             "## Primary (held-out videos)", "",
             "| Construct | Pairs | Agreement | Alpha | 95% CI | Researcher yes | Model yes | Unsure (researcher / model) | Kept? |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in prim:
        lines.append(f"| `{r['construct']}` | {r['n_pairs']} | {fmt(r['agreement'], '.0%')} | "
                     f"**{fmt(r['alpha'], '.3f')}** | {fmt(r['ci_lo'])} to {fmt(r['ci_hi'])} | "
                     f"{r['human_yes']} | {r['model_yes']} | {r['human_unsure']} / {r['model_unsure']} | "
                     f"{'**yes**' if r['passed'] else 'no - dropped'} |")
    lines += ["", f"## All {len(m)} coded videos (including the 10 pilot videos)", "",
              "| Construct | Pairs | Agreement | Alpha | 95% CI |", "|---|---|---|---|---|"]
    for r in full:
        lines.append(f"| `{r['construct']}` | {r['n_pairs']} | {fmt(r['agreement'], '.0%')} | "
                     f"{fmt(r['alpha'], '.3f')} | {fmt(r['ci_lo'])} to {fmt(r['ci_hi'])} |")
    lines += ["", "Alpha corrects agreement for chance. When one answer dominates - most videos have "
              "no celebrity - high raw agreement can sit beside a low alpha, because agreeing on "
              "'no' is what chance alone would produce.", "",
              "The three constructs without a manual check (`product_vs_lifestyle`, `ugc_vs_brand`, "
              "`promotional_language`) have no alpha and are reported only as unvalidated "
              "automated labels (D-023, D-038). They do not enter any model."]
    text = "\n".join(lines) + "\n"
    REPORT.write_text(text, encoding="utf-8")
    pd.DataFrame(prim).to_csv(RESULT, index=False)
    print(text)
    print(f"-> {REPORT.relative_to(config.ROOT)}")
    return {r["construct"]: r["passed"] for r in prim}


if __name__ == "__main__":
    main()

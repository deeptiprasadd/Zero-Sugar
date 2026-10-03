"""docs/08 sections 4 and 7.9.6 - minimum detectable effects for the focus set, before any test.

Uses only sample sizes and how videos are spread over accounts - no engagement value is read.

Videos from one account are not independent, so each n is shrunk by the design effect
    DEFF = 1 + (m_eff - 1) * ICC,   m_eff = sum(m_i^2) / sum(m_i)
(m_i = videos per account; m_eff is the size-weighted cluster size, which matters here because one
channel holds 58 videos). The ICC is only known once model (a) is fitted, so the minimum detectable
effect is given for ICC 0, 0.1 and 0.3; the fitted ICC is reported beside every null (7.9.6).

Effects, 80% power, two-sided alpha 0.05 (and 0.05/8 as the strictest Benjamini-Hochberg rank):
    d  - standardised difference for a yes/no feature split into halves
    r  - correlation for a continuous feature (Fisher z)
    dr - difference between the two platforms' correlations (H9, H10 - exploratory)

Usage:
    python -m src.stats.power
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.stats.power import TTestIndPower

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

OUT = config.REPORTS / "power_analysis.md"
ICCS = (0.0, 0.1, 0.3)
POWER = 0.80


def m_eff(counts: pd.Series) -> float:
    return float((counts ** 2).sum() / counts.sum())


def n_eff(n: int, me: float, icc: float) -> float:
    return n / (1 + (me - 1) * icc)


def mde_d(n: float, alpha: float) -> float:
    return float(TTestIndPower().solve_power(nobs1=n / 2, ratio=1.0, alpha=alpha, power=POWER))


def mde_r(n: float, alpha: float) -> float:
    return float(np.tanh((norm.ppf(1 - alpha / 2) + norm.ppf(POWER)) / np.sqrt(n - 3)))


def mde_dr(n1: float, n2: float, alpha: float = 0.05) -> float:
    """Smallest detectable gap between two correlations, as a Fisher-z difference."""
    return float((norm.ppf(1 - alpha / 2) + norm.ppf(POWER)) * np.sqrt(1 / (n1 - 3) + 1 / (n2 - 3)))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dv = pd.read_parquet(config.PROCESSED / "dependent_variable.parquet")
    focus = dv[dv["in_focus"] & (dv["dv_status"] == "ok")]
    sets = {"Focus set, pooled": focus,
            "Focus set, Instagram": focus[focus["platform"] == "instagram"],
            "Focus set, YouTube": focus[focus["platform"] == "youtube"]}
    lines = ["# Power analysis - minimum detectable effects (docs/08 sections 4 and 7.9.6)", "",
             "Computed from sample sizes and the spread of videos over accounts only; **no engagement "
             "value was read**. 80% power. `d` = standardised difference for a yes/no feature split in "
             "halves; `r` = correlation for a continuous feature. Columns give the effect at ICC 0 / "
             "0.1 / 0.3 (share of engagement variance that belongs to the account; the fitted value "
             "comes from model (a) and is reported with every null).", "",
             "| Test family | n | Accounts | m_eff | d, alpha 0.05 | r, alpha 0.05 | r, alpha 0.05/8 |",
             "|---|---|---|---|---|---|---|"]
    rows = {}
    for name, d in sets.items():
        c = d.groupby("account").size()
        me = m_eff(c)
        cells = []
        for fn, a in [(mde_d, 0.05), (mde_r, 0.05), (mde_r, 0.05 / 8)]:
            cells.append(" / ".join(f"{fn(n_eff(len(d), me, i), a):.2f}" for i in ICCS))
        rows[name] = (len(d), c.size, me)
        lines.append(f"| {name} | {len(d)} | {c.size} | {me:.1f} | {cells[0]} | {cells[1]} | {cells[2]} |")
    ni, ny = rows["Focus set, Instagram"][0], rows["Focus set, YouTube"][0]
    mi, my = rows["Focus set, Instagram"][2], rows["Focus set, YouTube"][2]
    dr = " / ".join(f"{mde_dr(n_eff(ni, mi, i), n_eff(ny, my, i)):.2f}" for i in ICCS)
    lines += ["", f"**H9 / H10 (exploratory):** the smallest detectable difference between the two "
              f"platforms' correlations, as a Fisher-z gap, is {dr} at ICC 0 / 0.1 / 0.3 - roughly a "
              "correlation of 0.4 on one platform against none on the other at ICC 0. Platform "
              "differences in predictors of ordinary size cannot be detected; H9 and H10 stay "
              "estimates with intervals (7.9.7).", "",
              f"**YouTube:** {ny} videos in {rows['Focus set, YouTube'][1]} accounts, size-weighted "
              f"cluster size {my:.1f} (one channel holds 58). At any realistic ICC its effective n is "
              "small, which is why no YouTube-only model is fitted (D-041).", "",
              "**This is a cautious upper bound.** The design effect fully applies only to a feature "
              "that is constant within an account. Most of the 20 measures vary from video to video "
              "inside an account, and the mixed model uses that within-account variation, so the real "
              "minimum detectable effect lies between the ICC-0 column and the ICC columns.", "",
              "Reading: Cohen's d 0.2 / 0.5 / 0.8 = small / medium / large; r 0.1 / 0.3 / 0.5 the "
              "same. **Only medium-to-large effects are detectable in the pooled focus set, and only "
              "large ones within a platform.** A null is reported as 'not detected at this sample size' "
              "with the value from this table, never as 'no effect'."]
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

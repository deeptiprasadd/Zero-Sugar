"""P11 - repeat check of the hand codes, exactly as fixed in D-050.

The 40 videos coded both on 15 September (`manual_codes_FINAL.csv`) and on 9 October
(`focus_codes_FINAL.csv`). Four questions were asked in the same words; product visibility is compared
as "none" vs "a can or bottle" against 15 September's "no product" vs a pack. Krippendorff's alpha,
nominal; "unsure" and blank are missing. Both code files are only read. No engagement value is read.

Usage:
    python -m src.coding.repeat_check
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.features.reliability import alpha_nominal  # noqa: E402  (checked against the reference package)

OLD = config.DATA / "coding" / "manual_codes_FINAL.csv"
NEW = config.DATA / "coding" / "focus_codes_FINAL.csv"
SAMPLE = config.DATA / "coding" / "focus_sample.csv"
OUT = config.REPORTS / "repeat_check.md"
SEED = 20261009
N_BOOT = 2000
SAME_WORDING = ["has_celebrity", "has_influencer", "humour_present", "has_cta"]


def band(a: float) -> str:
    if not np.isfinite(a):
        return "not estimable"
    return "reliable" if a >= 0.80 else ("tentative" if a >= 0.667 else "weakly reliable")


def boot(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    vals = [alpha_nominal(a[i], b[i]) for i in (rng.integers(0, len(a), len(a)) for _ in range(N_BOOT))]
    vals = [v for v in vals if np.isfinite(v)]
    if len(vals) < N_BOOT / 2:
        return float("nan"), float("nan")
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def pairs(m: pd.DataFrame, construct: str) -> tuple[np.ndarray, np.ndarray]:
    if construct == "product_any":
        old = m["zero_sugar_visible"].map({"no_product": "none", "zero_sugar": "pack", "other_coca_cola": "pack"})
        new = m["product_visibility"].map({"none": "none", "brief": "pack", "prominent": "pack"})
    else:
        old = m[f"{construct}_old"].where(m[f"{construct}_old"].isin(["yes", "no"]))
        new = m[f"{construct}_new"].where(m[f"{construct}_new"].isin(["yes", "no"]))
    keep = old.notna() & new.notna()
    return old[keep].to_numpy(object), new[keep].to_numpy(object)


def rows(m: pd.DataFrame) -> list[list]:
    out = []
    for c in SAME_WORDING + ["product_any"]:
        a, b = pairs(m, c)
        al = alpha_nominal(a, b) if len(a) else float("nan")
        lo, hi = boot(a, b) if len(a) > 1 else (float("nan"), float("nan"))
        agree = float((a == b).mean()) if len(a) else float("nan")
        yes_old = int((a == ("pack" if c == "product_any" else "yes")).sum())
        yes_new = int((b == ("pack" if c == "product_any" else "yes")).sum())
        ci = "-" if not np.isfinite(lo) else f"{lo:.2f} to {hi:.2f}"
        out.append([c if c != "product_any" else "product visibility (none vs any)", len(a), f"{agree:.0%}",
                    "n/a" if not np.isfinite(al) else f"{al:.2f}", ci, f"{yes_old} / {yes_new}", band(al)])
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    old = pd.read_csv(OLD, dtype=str, keep_default_na=False)
    new = pd.read_csv(NEW, dtype=str, keep_default_na=False)
    m = old.merge(new, on=["platform", "media_id"], suffixes=("_old", "_new"))
    s = pd.read_csv(SAMPLE, dtype=str, keep_default_na=False)
    ai = set(s.loc[s["caption"].str.contains("Mourinho", case=False), "media_id"])
    m["ai_characters"] = m["media_id"].isin(ai)
    head = ["Construct", "Pairs", "Raw agreement", "Alpha", "95% CI", "Yes 15 Sep / 9 Oct", "Band (D-050)"]

    lines = ["# P11 - repeat check of the hand codes (D-050)", "",
             f"{len(m)} videos coded on 15 September and on 9 October (Instagram "
             f"{int((m['platform'] == 'instagram').sum())}, YouTube {int((m['platform'] == 'youtube').sum())}; "
             f"{int(m['ai_characters'].sum())} are AI-character Shorts). Same coder, about three weeks apart. "
             "Krippendorff's alpha, nominal; 'unsure' and blank are missing; 2,000 bootstrap resamples "
             f"(seed {SEED}). Bands fixed in D-050: >= 0.80 reliable, 0.667-0.80 tentative, below 0.667 weakly "
             "reliable. No construct is dropped for a low value.", "",
             "## Main result - FINAL codes (after rule A, D-049)", "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows(m)]
    lines += ["", f"## Sensitivity - without the {int(m['ai_characters'].sum())} AI-character Shorts", "",
              "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows(m[~m["ai_characters"]])]
    lines += ["", "Nine of the 14 new questions have no earlier answer to compare with: their repeat reliability "
              "is not measured."]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

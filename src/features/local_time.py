"""P10 - posting time in local time, exactly as fixed in D-050.

Each market of the focus set (192 videos) is mapped to one time zone (IANA names, daylight saving handled by zoneinfo). Regional
accounts get an approximate zone; Global/US keeps UTC because it has no single audience. No engagement
value is read.

Outputs:
    data/interim/local_time.csv      per video: zone, its quality, local hour, local weekend flag
    reports/local_time.md            how many videos change day or hour band

Usage:
    python -m src.features.local_time
"""
from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402

OUT = config.INTERIM / "local_time.csv"
REPORT = config.REPORTS / "local_time.md"

# market -> (zone, quality), fixed in D-050
ZONES = {
    "Bolivia": ("America/La_Paz", "country"), "Brazil": ("America/Sao_Paulo", "capital zone of a multi-zone country"),
    "Chile": ("America/Santiago", "country"), "Colombia": ("America/Bogota", "country"),
    "Costa Rica": ("America/Costa_Rica", "country"), "El Salvador": ("America/El_Salvador", "country"),
    "India": ("Asia/Kolkata", "country"), "Indonesia": ("Asia/Jakarta", "capital zone of a multi-zone country"),
    "Kenya": ("Africa/Nairobi", "country"), "Malaysia": ("Asia/Kuala_Lumpur", "country"),
    "Panama": ("America/Panama", "country"), "Singapore": ("Asia/Singapore", "country"),
    "South Korea": ("Asia/Seoul", "country"), "Thailand": ("Asia/Bangkok", "country"),
    "Turkiye": ("Europe/Istanbul", "country"),
    "Europe": ("Europe/Paris", "regional, approximate"), "MENA": ("Asia/Dubai", "regional, approximate"),
    "LatAm/Mexico": ("America/Mexico_City", "regional, approximate"),
    "Global/US": ("UTC", "global - UTC kept"),
}


def band(h: int) -> str:
    return "night 0-6" if h < 6 else "morning 6-12" if h < 12 else "afternoon 12-18" if h < 18 else "evening 18-24"


def build() -> pd.DataFrame:
    dv = pd.read_parquet(config.PROCESSED / "dependent_variable.parquet",
                         columns=["platform", "media_id", "market", "posted_at", "in_focus", "dv_status"])
    dv = dv[dv["in_focus"] & (dv["dv_status"] == "ok")]      # D-050 maps the focus set's markets only
    unknown = sorted(set(dv["market"].dropna()) - set(ZONES))
    if unknown:
        raise SystemExit(f"markets without a zone (add them to D-050 first): {unknown}")
    rows = []
    for r in dv.itertuples():
        zone, quality = ZONES[r.market]
        utc = r.posted_at.tz_convert("UTC")
        loc = utc.tz_convert(ZoneInfo(zone))
        rows.append({"platform": r.platform, "media_id": r.media_id, "market": r.market, "tz": zone,
                     "tz_quality": quality, "posting_hour_utc": utc.hour, "posting_hour_local": loc.hour,
                     "is_weekend_utc": utc.weekday() >= 5, "is_weekend_local": loc.weekday() >= 5,
                     "local_day_differs": utc.date() != loc.date(), "in_focus": bool(r.in_focus and r.dv_status == "ok")})
    return pd.DataFrame(rows)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t = build()
    t.to_csv(OUT, index=False, encoding="utf-8")
    f = t[t["in_focus"]]
    lines = ["# P10 - posting time in local time (D-050)", "",
             f"Focus set: {len(f)} videos. Zones by market as fixed in D-050; daylight saving handled by zoneinfo.", "",
             "| Zone quality | Videos |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in f["tz_quality"].value_counts().items()]
    moved = f[f["tz_quality"] != "global - UTC kept"]
    lines += ["", f"Of the {len(moved)} videos with a local zone: the local date differs from the UTC date for "
              f"{int(moved['local_day_differs'].sum())}; the weekend flag changes for "
              f"{int((moved['is_weekend_local'] != moved['is_weekend_utc']).sum())}; the hour band changes for "
              f"{int((moved['posting_hour_local'].map(band) != moved['posting_hour_utc'].map(band)).sum())}.", "",
              "| Hour band | UTC (all 192) | Local (Global/US stays UTC) |", "|---|---|---|"]
    for b in ["night 0-6", "morning 6-12", "afternoon 12-18", "evening 18-24"]:
        lines.append(f"| {b} | {int((f['posting_hour_utc'].map(band) == b).sum())} | "
                     f"{int((f['posting_hour_local'].map(band) == b).sum())} |")
    lines += ["", f"Saved: `{OUT.relative_to(config.ROOT).as_posix()}`. The sensitivity re-run of the models with local "
              "time is in `reports/model_comparison_added.md`."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

# P10 - posting time in local time (D-050)

Focus set: 192 videos. Zones by market as fixed in D-050; daylight saving handled by zoneinfo.

| Zone quality | Videos |
|---|---|
| country | 84 |
| global - UTC kept | 77 |
| capital zone of a multi-zone country | 17 |
| regional, approximate | 14 |

Of the 115 videos with a local zone: the local date differs from the UTC date for 7; the weekend flag changes for 1; the hour band changes for 93.

| Hour band | UTC (all 192) | Local (Global/US stays UTC) |
|---|---|---|
| night 0-6 | 28 | 2 |
| morning 6-12 | 50 | 46 |
| afternoon 12-18 | 77 | 81 |
| evening 18-24 | 37 | 63 |

Saved: `data/interim/local_time.csv`. The sensitivity re-run of the models with local time is in `reports/model_comparison_added.md`.

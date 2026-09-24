"""Project paths and credentials.

Reads `.env` from the project root with a minimal parser so python-dotenv is not a
dependency. Never log or print the values.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Windows consoles default to cp1252, which cannot encode the box-drawing, arrow and
# warning glyphs used in progress output; printing one raises UnicodeEncodeError and
# kills a collection run at the reporting step, after the API quota has been spent.
# Reconfiguring here (rather than sanitising every f-string) fixes stdout for every
# module that imports config, including redirected output.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass  # already-wrapped or non-reconfigurable stream; fall through harmlessly

ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "data"
RAW = DATA / "raw"
MEDIA = DATA / "media"
MEDIA_YT = MEDIA / "youtube"
MEDIA_IG = MEDIA / "instagram"
INTERIM = DATA / "interim"
FEATURES_CACHE = INTERIM / "features"
PROCESSED = DATA / "processed"

DOCS = ROOT / "docs"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
MODELS = ROOT / "models"

ACCOUNTS_CSV = DOCS / "accounts.csv"

for _d in (RAW, MEDIA_YT, MEDIA_IG, FEATURES_CACHE, PROCESSED, FIGURES, MODELS):
    _d.mkdir(parents=True, exist_ok=True)


def _load_env(path: Path = ROOT / ".env") -> dict[str, str]:
    """Parse KEY=VALUE lines. Ignores blanks, comments, and surrounding quotes."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


_ENV = _load_env()


def get(name: str, default: str | None = None) -> str | None:
    """Credential lookup: real environment first, then `.env`."""
    return os.environ.get(name) or _ENV.get(name) or default


def require(name: str) -> str:
    """Same as get(), but fail with an actionable message instead of a None downstream."""
    val = get(name)
    if not val:
        raise SystemExit(
            f"Missing {name}.\n"
            f"  Copy .env.example to .env and fill it in.\n"
            f"  Expected location: {ROOT / '.env'}"
        )
    return val

"""
utils/date_helpers.py
──────────────────────────────────────────────────────────────────────────────
Shared date manipulations.
"""
from datetime import datetime, timezone
from src.core.constants import ISO_8601_FORMAT, YYYY_MM_FORMAT


def utc_now() -> datetime:
    """Returns a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

def parse_iso_date(date_str: str) -> datetime:
    """Safely parse naive or aware ISO datetimes from strings."""
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise ValueError(f"Invalid ISO format: {date_str}")

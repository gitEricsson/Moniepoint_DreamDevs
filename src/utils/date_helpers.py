from datetime import datetime, timezone
from src.core.constants import ISO_8601_FORMAT, YYYY_MM_FORMAT

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def parse_iso_date(date_str: str) -> datetime:
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise ValueError(f"Invalid ISO format: {date_str}")

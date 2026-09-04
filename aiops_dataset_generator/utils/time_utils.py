from datetime import datetime, timedelta, timezone
from typing import List
import numpy as np

DEFAULT_BASE_TIME = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)

def format_iso(dt: datetime) -> str:
    """Format datetime into standard ISO 8601 string UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def parse_iso(iso_str: str) -> datetime:
    """Parse ISO 8601 string to timezone-aware UTC datetime."""
    clean_str = iso_str.replace("Z", "+00:00")
    return datetime.fromisoformat(clean_str).astimezone(timezone.utc)


def timestamp_to_epoch(dt: datetime) -> float:
    """Return UNIX timestamp in seconds."""
    return dt.timestamp()


def generate_timestamps(
    start_time: datetime,
    duration_minutes: int,
    interval_seconds: int
) -> List[datetime]:
    """Generates sequential timestamps at a fixed interval."""
    total_steps = int((duration_minutes * 60) / interval_seconds)
    timestamps = [
        start_time + timedelta(seconds=i * interval_seconds)
        for i in range(total_steps)
    ]
    return timestamps


def add_jitter(
    dt: datetime,
    np_rng: np.random.Generator,
    max_jitter_seconds: float = 2.0
) -> datetime:
    """Adds small random noise/jitter to a timestamp."""
    jitter = float(np_rng.uniform(-max_jitter_seconds, max_jitter_seconds))
    return dt + timedelta(seconds=jitter)

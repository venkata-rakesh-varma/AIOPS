"""
Utility package containing random number management, time formatting, and IO helpers.
"""

from .random_utils import SeedManager, get_rng, sample_noise, sample_weibull_delay
from .time_utils import (
    format_iso,
    parse_iso,
    generate_timestamps,
    add_jitter,
    timestamp_to_epoch,
)
from .io_utils import (
    ensure_directories,
    write_jsonl,
    append_csv_records,
    write_parquet_from_records,
    save_json,
    load_json,
)

__all__ = [
    "SeedManager",
    "get_rng",
    "sample_noise",
    "sample_weibull_delay",
    "format_iso",
    "parse_iso",
    "generate_timestamps",
    "add_jitter",
    "timestamp_to_epoch",
    "ensure_directories",
    "write_jsonl",
    "append_csv_records",
    "write_parquet_from_records",
    "save_json",
    "load_json",
]

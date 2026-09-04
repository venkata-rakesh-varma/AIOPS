import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Union
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

def ensure_directories(base_dir: Union[str, Path]) -> Dict[str, Path]:
    """
    Creates standard output directory tree:
    data/
      raw/
      ground_truth/
      processed/
      graph/
      train/
      validation/
      test/
      hard_test/
    """
    base = Path(base_dir)
    dirs = {
        "base": base,
        "raw": base / "raw",
        "ground_truth": base / "ground_truth",
        "processed": base / "processed",
        "graph": base / "graph",
        "train": base / "train",
        "validation": base / "validation",
        "test": base / "test",
        "hard_test": base / "hard_test",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def write_jsonl(filepath: Union[str, Path], records: List[Dict[str, Any]], append: bool = False):
    """Writes list of dicts to JSONL file line by line."""
    mode = "a" if append else "w"
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def append_csv_records(
    filepath: Union[str, Path],
    records: List[Dict[str, Any]],
    fieldnames: List[str] = None
):
    """Appends records to CSV file, creating headers if file doesn't exist or is empty."""
    if not records:
        return
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists() and path.stat().st_size > 0

    if fieldnames is None:
        fieldnames = list(records[0].keys())

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for r in records:
            # Filter keys to fieldnames to maintain clean schema
            filtered = {k: r.get(k, None) for k in fieldnames}
            writer.writerow(filtered)


def write_parquet_from_records(
    filepath: Union[str, Path],
    records: List[Dict[str, Any]]
):
    """Converts a list of dict records into PyArrow / Parquet file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(records)
    table = pa.Table.from_pandas(df)
    pq.write_table(table, str(path))


def save_json(filepath: Union[str, Path], data: Any, indent: int = 2):
    """Saves data structures into formatted JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=str)


def load_json(filepath: Union[str, Path]) -> Any:
    """Loads JSON file."""
    path = Path(filepath)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

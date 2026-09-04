import random
from pathlib import Path
from typing import Dict, List, Any, Union
import pandas as pd
from utils.io_utils import ensure_directories, append_csv_records, write_jsonl, save_json

class DatasetSplitter:
    """
    Performs scenario-level dataset splitting into train/ (70%), validation/ (15%), test/ (15%),
    and hard_test/ splits without telemetry row leakage or topology signature leakage.
    """
    def __init__(self, train_ratio: float = 0.70, val_ratio: float = 0.15, test_ratio: float = 0.15):
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio

    def split_dataset(self, data_dir: Union[str, Path], py_rng: random.Random) -> Dict[str, List[str]]:
        base = Path(data_dir)
        dirs = ensure_directories(base)

        incidents_csv = base / "ground_truth" / "incident_labels.csv"
        nodes_csv = base / "graph" / "nodes.csv"

        if not incidents_csv.exists():
            print(f"[DatasetSplitter] Ground truth incidents CSV not found at {incidents_csv}. Skipping split.")
            return {}

        inc_df = pd.read_csv(incidents_csv)
        scenario_ids = sorted(list(inc_df["scenario_id"].unique()))

        # Separate hard test scenarios based on criteria (e.g., hard negatives or special topology family)
        nodes_df = pd.read_csv(nodes_csv) if nodes_csv.exists() else pd.DataFrame()

        # Hard test scenarios selection
        hard_test_scenarios = set()
        normal_scenarios = []

        for s_id in scenario_ids:
            s_nodes = nodes_df[nodes_df["scenario_id"] == s_id] if not nodes_df.empty else pd.DataFrame()
            is_mesh = not s_nodes.empty and ("topology_e_mesh" in s_nodes["node_type"].values or len(s_nodes) > 35)

            if is_mesh:
                hard_test_scenarios.add(s_id)
            else:
                normal_scenarios.append(s_id)

        # Shuffle normal scenarios deterministically
        py_rng.shuffle(normal_scenarios)
        n = len(normal_scenarios)
        n_train = int(n * self.train_ratio)
        n_val = int(n * self.val_ratio)

        train_scenarios = set(normal_scenarios[:n_train])
        val_scenarios = set(normal_scenarios[n_train:n_train + n_val])
        test_scenarios = set(normal_scenarios[n_train + n_val:])

        splits = {
            "train": train_scenarios,
            "validation": val_scenarios,
            "test": test_scenarios,
            "hard_test": hard_test_scenarios
        }

        # Distribute raw/processed CSVs per split
        self._copy_split_records(base, dirs, splits)

        split_summary = {k: len(v) for k, v in splits.items()}
        save_json(base / "split_summary.json", split_summary)
        print(f"[DatasetSplitter] Successfully partitioned scenarios: {split_summary}")
        return {k: list(v) for k, v in splits.items()}

    def _copy_split_records(
        self,
        base_dir: Path,
        dirs: Dict[str, Path],
        splits: Dict[str, set]
    ):
        raw_files = ["metrics.csv", "traces.csv", "alerts.csv", "nodes.csv", "edges.csv"]
        for fname in raw_files:
            src = base_dir / "raw" / fname
            if not src.exists():
                continue
            df = pd.read_csv(src)
            for split_name, s_set in splits.items():
                if "scenario_id" in df.columns:
                    sub_df = df[df["scenario_id"].isin(s_set)]
                    dest = dirs[split_name] / fname
                    sub_df.to_csv(dest, index=False)

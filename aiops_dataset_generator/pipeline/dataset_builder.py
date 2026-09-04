import time
import json
from pathlib import Path
from typing import Dict, List, Any, Union
import multiprocessing as mp
from functools import partial

from utils.random_utils import SeedManager
from utils.io_utils import (
    ensure_directories,
    write_jsonl,
    append_csv_records,
    write_parquet_from_records,
    save_json
)
from generators.scenario_generator import ScenarioGenerator
from graph.graph_exporter import GraphExporter

def _generate_single_scenario_worker(
    scenario_idx: int,
    global_seed: int,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    seed_manager = SeedManager(global_seed)
    gen = ScenarioGenerator(seed_manager, config)
    return gen.generate_scenario(scenario_idx)

class DatasetBuilder:
    """
    Multiprocessing-enabled reproducible dataset generation pipeline.
    Writes raw telemetry, ground truth datasets, processed candidate datasets, graph JSON stores,
    and dataset metadata manifests.
    """
    def __init__(self, global_seed: int = 42, config: Dict[str, Any] = None):
        self.global_seed = global_seed
        self.config = config or {}
        self.seed_manager = SeedManager(global_seed)

    def build_dataset(
        self,
        num_scenarios: int,
        output_dir: Union[str, Path],
        num_workers: int = 1
    ) -> Dict[str, Path]:
        dirs = ensure_directories(output_dir)
        start_time = time.time()

        print(f"[DatasetBuilder] Generating {num_scenarios} scenarios using seed={self.global_seed} across {num_workers} worker process(es)...")

        scenarios_data = []

        if num_workers > 1:
            worker_func = partial(_generate_single_scenario_worker, global_seed=self.global_seed, config=self.config)
            with mp.Pool(processes=num_workers) as pool:
                scenarios_data = pool.map(worker_func, range(num_scenarios))
        else:
            gen = ScenarioGenerator(self.seed_manager, self.config)
            for idx in range(num_scenarios):
                scenarios_data.append(gen.generate_scenario(idx))

        # Sort scenarios by scenario_id to guarantee exact canonical deterministic output order
        scenarios_data.sort(key=lambda s: s["scenario_id"])

        print("[DatasetBuilder] Writing dataset files to disk...")

        graphs_collection = {}
        processed_ts_records = []

        raw_metrics_all = []
        raw_logs_all = []
        raw_traces_all = []
        raw_alerts_all = []
        raw_nodes_all = []
        raw_edges_all = []

        gt_anomaly_all = []
        gt_alert_all = []
        gt_incident_all = []
        gt_root_cause_all = []
        gt_propagation_all = []
        gt_remediation_all = []

        proc_anomaly_all = []
        proc_correlation_all = []
        proc_rc_candidates_all = []
        proc_propagation_all = []
        proc_remediation_all = []

        for scenario in scenarios_data:
            s_id = scenario["scenario_id"]
            graph_obj = scenario["graph"]

            graphs_collection[s_id] = graph_obj.to_dict()

            raw_metrics_all.extend(scenario["raw"]["metrics"])
            raw_logs_all.extend(scenario["raw"]["logs"])
            raw_traces_all.extend(scenario["raw"]["traces"])
            raw_alerts_all.extend(scenario["raw"]["alerts"])
            raw_nodes_all.extend(scenario["raw"]["nodes"])
            raw_edges_all.extend(scenario["raw"]["edges"])

            gt_anomaly_all.extend(scenario["ground_truth"]["anomaly_labels"])
            gt_alert_all.extend(scenario["ground_truth"]["alert_labels"])
            gt_incident_all.extend(scenario["ground_truth"]["incident_labels"])
            gt_root_cause_all.extend(scenario["ground_truth"]["root_cause_labels"])
            gt_propagation_all.extend(scenario["ground_truth"]["propagation_labels"])
            gt_remediation_all.extend(scenario["ground_truth"]["remediation_labels"])

            proc_anomaly_all.extend(scenario["processed"]["anomaly_detection"])
            proc_correlation_all.extend(scenario["processed"]["incident_correlation"])
            proc_rc_candidates_all.extend(scenario["processed"]["root_cause_candidates"])
            proc_propagation_all.extend(scenario["processed"]["propagation"])
            proc_remediation_all.extend(scenario["processed"]["remediation"])

            processed_ts_records.extend(scenario["raw"]["metrics"])

        # 1. Write Raw Telemetry
        append_csv_records(dirs["raw"] / "metrics.csv", raw_metrics_all)
        write_jsonl(dirs["raw"] / "logs.jsonl", raw_logs_all)
        append_csv_records(dirs["raw"] / "traces.csv", raw_traces_all)
        append_csv_records(dirs["raw"] / "alerts.csv", raw_alerts_all)
        append_csv_records(dirs["raw"] / "nodes.csv", raw_nodes_all)
        append_csv_records(dirs["raw"] / "edges.csv", raw_edges_all)

        # 2. Write Ground Truth Datasets
        append_csv_records(dirs["ground_truth"] / "anomaly_labels.csv", gt_anomaly_all)
        append_csv_records(dirs["ground_truth"] / "alert_labels.csv", gt_alert_all)
        append_csv_records(dirs["ground_truth"] / "incident_labels.csv", gt_incident_all)
        append_csv_records(dirs["ground_truth"] / "root_cause_labels.csv", gt_root_cause_all)
        append_csv_records(dirs["ground_truth"] / "propagation_labels.csv", gt_propagation_all)
        append_csv_records(dirs["ground_truth"] / "remediation_labels.csv", gt_remediation_all)

        # 3. Write Processed ML Datasets
        append_csv_records(dirs["processed"] / "anomaly_detection.csv", proc_anomaly_all)
        append_csv_records(dirs["processed"] / "incident_correlation.csv", proc_correlation_all)
        append_csv_records(dirs["processed"] / "root_cause_candidates.csv", proc_rc_candidates_all)
        append_csv_records(dirs["processed"] / "propagation.csv", proc_propagation_all)
        append_csv_records(dirs["processed"] / "remediation.csv", proc_remediation_all)
        write_parquet_from_records(dirs["processed"] / "time_series.parquet", processed_ts_records)

        # 4. Write Graph Representations
        append_csv_records(dirs["graph"] / "nodes.csv", raw_nodes_all)
        append_csv_records(dirs["graph"] / "edges.csv", raw_edges_all)
        save_json(dirs["graph"] / "graphs.json", graphs_collection)

        # 5. Save Manifest & Statistics
        elapsed = round(time.time() - start_time, 2)
        manifest = {
            "generator_version": "1.0.0",
            "global_seed": self.global_seed,
            "num_scenarios": num_scenarios,
            "elapsed_seconds": elapsed,
            "counts": {
                "metrics": len(raw_metrics_all),
                "logs": len(raw_logs_all),
                "traces": len(raw_traces_all),
                "alerts": len(raw_alerts_all),
                "incidents": len(gt_incident_all),
                "nodes": len(raw_nodes_all),
                "edges": len(raw_edges_all)
            }
        }
        save_json(dirs["base"] / "manifest.json", manifest)

        stats = {
            "root_cause_distribution": self._compute_distribution(gt_root_cause_all, "root_cause_type"),
            "severity_distribution": self._compute_distribution(gt_incident_all, "severity"),
            "remediation_distribution": self._compute_distribution(gt_remediation_all, "recommended_action"),
            "topology_distribution": self._compute_distribution(raw_nodes_all, "node_type")
        }
        save_json(dirs["base"] / "dataset_statistics.json", stats)

        print(f"[DatasetBuilder] Generation complete in {elapsed}s. Saved files to '{output_dir}'.")
        return dirs

    def _compute_distribution(self, records: List[Dict[str, Any]], key: str) -> Dict[str, int]:
        dist = {}
        for r in records:
            val = r.get(key, "unknown")
            dist[val] = dist.get(val, 0) + 1
        return dist

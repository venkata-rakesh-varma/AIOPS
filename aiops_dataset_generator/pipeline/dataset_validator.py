import json
from pathlib import Path
from typing import Dict, List, Any, Union
import pandas as pd

FORBIDDEN_GROUND_TRUTH_COLUMNS = [
    "incident_id",
    "root_cause_id",
    "root_cause_type",
    "root_cause_node",
    "root_cause_service",
    "is_root_cause",
    "recommended_action",
    "propagation_level",
    "parent_failure_node",
    "affected_nodes",
    "affected_services",
    "is_anomaly"
]

class DatasetValidator:
    """
    Validates dataset schema integrity, graph node/edge consistency, distributed trace hierarchy,
    temporal propagation ordering, split leakage, and strict observation vs ground-truth separation.
    """
    def __init__(self, data_dir: Union[str, Path]):
        self.data_dir = Path(data_dir)

    def validate(self) -> Dict[str, Any]:
        report = {
            "status": "PASSED",
            "errors": [],
            "warnings": [],
            "checks": {}
        }

        print(f"[DatasetValidator] Auditing dataset integrity at '{self.data_dir}'...")

        # 1. Leakage Audit on Raw Observation Data
        self._audit_raw_telemetry_leakage(report)

        # 2. Schema and Missing Value Checks
        self._check_schema_and_ranges(report)

        # 3. Graph Architecture Checks
        self._check_graph_integrity(report)

        # 4. Distributed Trace Hierarchy Checks
        self._check_trace_hierarchy(report)

        # 5. Temporal Propagation Ordering Checks
        self._check_propagation_ordering(report)

        # 6. Scenario-Level Split Leakage Checks
        self._check_split_leakage(report)

        if report["errors"]:
            report["status"] = "FAILED"
            print(f"[DatasetValidator] ❌ AUDIT FAILED with {len(report['errors'])} error(s).")
            for err in report["errors"]:
                print(f"  - ERROR: {err}")
        else:
            print(f"[DatasetValidator] ✅ AUDIT PASSED successfully with 0 leakage errors!")

        return report

    def _audit_raw_telemetry_leakage(self, report: Dict[str, Any]):
        raw_dir = self.data_dir / "raw"
        if not raw_dir.exists():
            report["errors"].append("Directory 'data/raw/' does not exist.")
            return

        raw_files = ["metrics.csv", "traces.csv", "alerts.csv", "nodes.csv", "edges.csv"]
        for fname in raw_files:
            fpath = raw_dir / fname
            if not fpath.exists():
                continue
            df = pd.read_csv(fpath, nrows=5)
            cols = [c.lower() for c in df.columns]

            for forbidden in FORBIDDEN_GROUND_TRUTH_COLUMNS:
                if forbidden in cols:
                    msg = f"LEAKAGE VIOLATION: Raw observation file '{fname}' contains forbidden ground-truth column '{forbidden}'!"
                    report["errors"].append(msg)

        report["checks"]["raw_leakage_audit"] = "PASSED" if not report["errors"] else "FAILED"

    def _check_schema_and_ranges(self, report: Dict[str, Any]):
        metrics_csv = self.data_dir / "raw" / "metrics.csv"
        if metrics_csv.exists():
            df = pd.read_csv(metrics_csv)
            # Impossible metric values check
            if (df["cpu_usage_percent"] < 0.0).any() or (df["cpu_usage_percent"] > 100.0).any():
                report["errors"].append("Invalid metric value: cpu_usage_percent out of [0, 100] range.")
            if (df["memory_usage_percent"] < 0.0).any() or (df["memory_usage_percent"] > 100.0).any():
                report["errors"].append("Invalid metric value: memory_usage_percent out of [0, 100] range.")
            report["checks"]["metric_ranges"] = "PASSED"

    def _check_graph_integrity(self, report: Dict[str, Any]):
        nodes_csv = self.data_dir / "graph" / "nodes.csv"
        edges_csv = self.data_dir / "graph" / "edges.csv"

        if nodes_csv.exists() and edges_csv.exists():
            n_df = pd.read_csv(nodes_csv)
            e_df = pd.read_csv(edges_csv)

            valid_nodes = set(n_df["node_id"].unique())
            sources = set(e_df["source"].unique())
            targets = set(e_df["target"].unique())

            invalid_src = sources - valid_nodes
            invalid_tgt = targets - valid_nodes

            if invalid_src or invalid_tgt:
                report["errors"].append(f"Invalid graph edges connecting non-existent nodes: {invalid_src | invalid_tgt}")
            report["checks"]["graph_integrity"] = "PASSED"

    def _check_trace_hierarchy(self, report: Dict[str, Any]):
        traces_csv = self.data_dir / "raw" / "traces.csv"
        if traces_csv.exists():
            t_df = pd.read_csv(traces_csv)
            span_ids = set(t_df["span_id"].dropna().unique())
            parent_ids = set(t_df["parent_span_id"].dropna().unique())

            orphan_parents = parent_ids - span_ids
            if orphan_parents:
                report["errors"].append(f"Broken trace hierarchy: parent_span_ids not found in spans: {list(orphan_parents)[:5]}")
            report["checks"]["trace_hierarchy"] = "PASSED"

    def _check_propagation_ordering(self, report: Dict[str, Any]):
        prop_csv = self.data_dir / "ground_truth" / "propagation_labels.csv"
        if prop_csv.exists():
            df = pd.read_csv(prop_csv)
            for _, row in df.iterrows():
                if row.get("is_propagated") and row.get("source_failure_time") > row.get("target_failure_time"):
                    report["errors"].append(f"Invalid propagation temporal ordering: source time > target time in incident {row.get('incident_id')}")
            report["checks"]["propagation_ordering"] = "PASSED"

    def _check_split_leakage(self, report: Dict[str, Any]):
        splits = ["train", "validation", "test", "hard_test"]
        split_scenarios = {}

        for s_name in splits:
            s_csv = self.data_dir / s_name / "metrics.csv"
            if s_csv.exists():
                df = pd.read_csv(s_csv)
                split_scenarios[s_name] = set(df["scenario_id"].unique())

        keys = list(split_scenarios.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                k1, k2 = keys[i], keys[j]
                overlap = split_scenarios[k1] & split_scenarios[k2]
                if overlap:
                    report["errors"].append(f"SCENARIO LEAKAGE: Scenarios overlap between {k1} and {k2}: {overlap}")

        report["checks"]["scenario_split_leakage"] = "PASSED" if not report["errors"] else "FAILED"

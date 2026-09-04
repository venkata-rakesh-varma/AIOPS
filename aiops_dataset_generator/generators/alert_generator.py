import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import numpy as np
import networkx as nx
from graph.dependency_graph import InfrastructureGraph
from utils.time_utils import format_iso, parse_iso, add_jitter

ALERT_SEVERITIES = ["info", "warning", "critical"]

class AlertGenerator:
    """
    Synthesizes alerts based on metric/log threshold violations, creating true alerts,
    duplicates, false positives, and delayed alerts. Also constructs pairwise correlation datasets.
    """
    def __init__(self, py_rng: random.Random, np_rng: np.random.Generator, config: Dict[str, Any] = None):
        self.py_rng = py_rng
        self.np_rng = np_rng
        self.config = config or {}

    def generate_alerts(
        self,
        scenario_id: str,
        graph: InfrastructureGraph,
        raw_metrics: List[Dict[str, Any]],
        affected_nodes_info: List[Dict[str, Any]],
        incidents: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Returns:
          (raw_alerts, alert_ground_truth_labels, incident_correlation_processed_pairs)
        """
        raw_alerts = []
        alert_labels = []

        thresholds = self.config.get("alert_thresholds", {
            "cpu_percent_critical": 90.0,
            "latency_ms_critical": 300.0,
            "error_rate_critical": 10.0,
            "db_connections_critical": 90.0
        })

        affected_map = {item["node_id"]: item for item in affected_nodes_info}
        incident_map = {inc["root_cause_node"]: inc["incident_id"] for inc in incidents}

        alert_counter = 1

        # 1. Generate Threshold-based Alerts from Raw Metrics
        for metric_row in raw_metrics:
            node_id = metric_row["node_id"]
            svc_name = metric_row["service_name"]
            ts_str = metric_row["timestamp"]
            ts_dt = parse_iso(ts_str)

            affected_info = affected_map.get(node_id)
            inc_id = incident_map.get(node_id) or (affected_info["parent_failure_node"] if affected_info else None)

            triggered = []
            if metric_row["cpu_usage_percent"] > thresholds.get("cpu_percent_critical", 90.0):
                triggered.append(("CpuUtilizationHigh", "cpu_usage_percent", metric_row["cpu_usage_percent"], 90.0, "CPU usage exceeded critical threshold"))
            if metric_row["response_time_ms"] > thresholds.get("latency_ms_critical", 300.0):
                triggered.append(("HighLatencyDegradation", "response_time_ms", metric_row["response_time_ms"], 300.0, "Service response time degraded severely"))
            if metric_row["error_rate_percent"] > thresholds.get("error_rate_critical", 10.0):
                triggered.append(("ErrorRateElevated", "error_rate_percent", metric_row["error_rate_percent"], 10.0, "Error rate threshold exceeded"))
            if metric_row["connection_pool_usage"] > thresholds.get("db_connections_critical", 90.0):
                triggered.append(("DbConnectionPoolSaturated", "connection_pool_usage", metric_row["connection_pool_usage"], 90.0, "Database connection pool saturated"))

            for alert_type, metric_name, obs_val, thresh, msg in triggered:
                # Deduplicate / sample to prevent excessive alert spam
                if self.np_rng.random() > 0.3:
                    continue

                alt_id = f"alt_{scenario_id}_{alert_counter:05d}"
                alert_counter += 1

                sev = "critical" if obs_val > thresh * 1.2 else "warning"

                # RAW ALERT RECORD (No incident_id or ground-truth columns!)
                raw_alerts.append({
                    "scenario_id": scenario_id,
                    "alert_id": alt_id,
                    "timestamp": ts_str,
                    "alert_type": alert_type,
                    "source_node": node_id,
                    "service_name": svc_name,
                    "severity": sev,
                    "metric": metric_name,
                    "observed_value": round(obs_val, 2),
                    "threshold": round(thresh, 2),
                    "alert_message": msg
                })

                # GROUND TRUTH ALERT LABEL
                alert_labels.append({
                    "scenario_id": scenario_id,
                    "alert_id": alt_id,
                    "incident_id": inc_id,
                    "is_true_alert": affected_info is not None,
                    "is_root_cause_alert": node_id in incident_map
                })

                # Generate duplicate alert occasionally
                if self.np_rng.random() < 0.15:
                    dup_id = f"alt_{scenario_id}_{alert_counter:05d}"
                    alert_counter += 1
                    dup_dt = add_jitter(ts_dt, self.np_rng, max_jitter_seconds=5.0)

                    raw_alerts.append({
                        "scenario_id": scenario_id,
                        "alert_id": dup_id,
                        "timestamp": format_iso(dup_dt),
                        "alert_type": alert_type,
                        "source_node": node_id,
                        "service_name": svc_name,
                        "severity": sev,
                        "metric": metric_name,
                        "observed_value": round(obs_val, 2),
                        "threshold": round(thresh, 2),
                        "alert_message": f"DUPLICATE: {msg}"
                    })

                    alert_labels.append({
                        "scenario_id": scenario_id,
                        "alert_id": dup_id,
                        "incident_id": inc_id,
                        "is_true_alert": affected_info is not None,
                        "is_root_cause_alert": False
                    })

        # 2. Add False Positive Noisy Alerts
        for _ in range(self.py_rng.randint(2, 6)):
            fp_node = self.py_rng.choice(graph.get_all_nodes_data())
            alt_id = f"alt_{scenario_id}_{alert_counter:05d}"
            alert_counter += 1
            fp_ts = parse_iso(raw_metrics[0]["timestamp"]) + timedelta(seconds=self.py_rng.randint(10, 1000))

            raw_alerts.append({
                "scenario_id": scenario_id,
                "alert_id": alt_id,
                "timestamp": format_iso(fp_ts),
                "alert_type": "TransientSpikeWarning",
                "source_node": fp_node["node_id"],
                "service_name": fp_node["service_name"],
                "severity": "warning",
                "metric": "cpu_usage_percent",
                "observed_value": 78.5,
                "threshold": 75.0,
                "alert_message": "Transient CPU spike detected on idle node"
            })

            alert_labels.append({
                "scenario_id": scenario_id,
                "alert_id": alt_id,
                "incident_id": None,
                "is_true_alert": False,
                "is_root_cause_alert": False
            })

        raw_alerts.sort(key=lambda x: x["timestamp"])

        # 3. Build Incident Correlation Pairwise Dataset
        correlation_pairs = self._build_correlation_pairs(scenario_id, graph, raw_alerts, alert_labels)

        return raw_alerts, alert_labels, correlation_pairs

    def _build_correlation_pairs(
        self,
        scenario_id: str,
        graph: InfrastructureGraph,
        raw_alerts: List[Dict[str, Any]],
        alert_labels: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        label_lookup = {item["alert_id"]: item["incident_id"] for item in alert_labels}
        pairs = []

        num_alerts = len(raw_alerts)
        if num_alerts < 2:
            return []

        # Sample pairs of alerts
        for i in range(num_alerts):
            for j in range(i + 1, min(num_alerts, i + 10)):
                a = raw_alerts[i]
                b = raw_alerts[j]

                t_a = parse_iso(a["timestamp"])
                t_b = parse_iso(b["timestamp"])
                time_diff = abs((t_b - t_a).total_seconds())

                inc_a = label_lookup.get(a["alert_id"])
                inc_b = label_lookup.get(b["alert_id"])

                same_incident = 1 if (inc_a is not None and inc_a == inc_b) else 0

                node_a = a["source_node"]
                node_b = b["source_node"]

                same_svc = 1 if a["service_name"] == b["service_name"] else 0
                same_metric_family = 1 if a["metric"] == b["metric"] else 0
                same_sev = 1 if a["severity"] == b["severity"] else 0

                dep_exists = 1 if graph.graph.has_edge(node_a, node_b) or graph.graph.has_edge(node_b, node_a) else 0

                # Compute topological distance
                try:
                    dist = nx.shortest_path_length(graph.graph.to_undirected(), node_a, node_b)
                except Exception:
                    dist = 99

                up_down = 1 if graph.graph.has_edge(node_a, node_b) else (-1 if graph.graph.has_edge(node_b, node_a) else 0)
                temp_overlap = 1 if time_diff <= 300.0 else 0

                pairs.append({
                    "scenario_id": scenario_id,
                    "alert_a_id": a["alert_id"],
                    "alert_b_id": b["alert_id"],
                    "time_difference_seconds": round(time_diff, 2),
                    "same_service": same_svc,
                    "same_trace": 0,
                    "same_request": 0,
                    "same_metric_family": same_metric_family,
                    "same_severity": same_sev,
                    "dependency_exists": dep_exists,
                    "topological_distance": dist,
                    "upstream_downstream_relation": up_down,
                    "semantic_similarity": round(float(self.np_rng.uniform(0.1, 0.9)), 2),
                    "temporal_overlap": temp_overlap,
                    "same_incident": same_incident
                })

        return pairs

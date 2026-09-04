import random
from datetime import datetime
from typing import Dict, List, Any
import numpy as np

from utils.random_utils import SeedManager
from utils.time_utils import DEFAULT_BASE_TIME, format_iso
from graph.dependency_graph import InfrastructureGraph, compute_topology_signature
from .topology_generator import TopologyGenerator
from .incident_generator import IncidentGenerator
from .failure_propagation import FailurePropagationEngine
from .metric_generator import MetricGenerator
from .log_generator import LogGenerator
from .trace_generator import TraceGenerator
from .alert_generator import AlertGenerator
from .remediation_generator import RemediationGenerator

class ScenarioGenerator:
    """
    Synthesizes a complete reproducible scenario combining graph topology, causal failure propagation,
    raw observable telemetry streams, ground truth datasets, and processed candidate ranking datasets.
    """
    def __init__(self, seed_manager: SeedManager, config: Dict[str, Any] = None):
        self.seed_manager = seed_manager
        self.config = config or {}

    def generate_scenario(self, scenario_index: int) -> Dict[str, Any]:
        scenario_id = f"scen_{scenario_index:06d}"
        py_rng, np_rng = self.seed_manager.get_scenario_rng(scenario_index)

        # 1. Topology
        top_gen = TopologyGenerator(py_rng, np_rng)
        topology_id = f"top_{scenario_index:04d}"
        graph = top_gen.generate(
            scenario_id=scenario_id,
            topology_id=topology_id,
            min_services=self.config.get("topology", {}).get("min_services", 8),
            max_services=self.config.get("topology", {}).get("max_services", 35)
        )
        topo_sig = compute_topology_signature(graph)

        # Determine Scenario Parameters
        is_multi_incident = py_rng.random() < self.config.get("incident", {}).get("multi_incident_probability", 0.20)
        is_hard_neg = py_rng.random() < self.config.get("incident", {}).get("hard_negative_probability", 0.30)

        # 2. Incidents
        inc_gen = IncidentGenerator(py_rng, np_rng)
        incidents = inc_gen.generate_incidents(
            scenario_id=scenario_id,
            graph=graph,
            base_time=DEFAULT_BASE_TIME,
            is_multi_incident=is_multi_incident,
            is_hard_negative=is_hard_neg
        )

        # 3. Causal Failure Propagation
        prop_engine = FailurePropagationEngine(py_rng, np_rng)
        all_affected_info = []
        propagation_records = []

        for inc in incidents:
            affected_info, p_recs = prop_engine.propagate_failures(inc, graph)
            all_affected_info.extend(affected_info)
            propagation_records.extend(p_recs)

        # 4. Telemetry Generation
        metric_gen = MetricGenerator(py_rng, np_rng, self.config)
        raw_metrics, anomaly_labels, anomaly_processed = metric_gen.generate_metrics(
            scenario_id=scenario_id,
            graph=graph,
            affected_nodes_info=all_affected_info,
            incidents=incidents,
            start_time=DEFAULT_BASE_TIME
        )

        log_gen = LogGenerator(py_rng, np_rng, self.config)
        raw_logs = log_gen.generate_logs(
            scenario_id=scenario_id,
            graph=graph,
            affected_nodes_info=all_affected_info,
            start_time=DEFAULT_BASE_TIME
        )

        trace_gen = TraceGenerator(py_rng, np_rng, self.config)
        raw_traces = trace_gen.generate_traces(
            scenario_id=scenario_id,
            graph=graph,
            affected_nodes_info=all_affected_info,
            start_time=DEFAULT_BASE_TIME
        )

        alert_gen = AlertGenerator(py_rng, np_rng, self.config)
        raw_alerts, alert_labels, correlation_pairs = alert_gen.generate_alerts(
            scenario_id=scenario_id,
            graph=graph,
            raw_metrics=raw_metrics,
            affected_nodes_info=all_affected_info,
            incidents=incidents
        )

        remed_gen = RemediationGenerator(py_rng, np_rng)
        remed_gt_labels, remed_processed = remed_gen.generate_remediation(scenario_id, incidents)

        # 5. Build Ground Truth Labels
        incident_labels = []
        root_cause_labels = []

        for inc in incidents:
            incident_labels.append({
                "scenario_id": scenario_id,
                "incident_id": inc["incident_id"],
                "start_time": format_iso(inc["start_time"]),
                "detection_time": format_iso(inc["detection_time"]),
                "end_time": format_iso(inc["end_time"]),
                "severity": inc["severity"],
                "blast_radius": inc["blast_radius"],
                "propagation_depth": inc["propagation_depth"]
            })

            root_cause_labels.append({
                "scenario_id": scenario_id,
                "incident_id": inc["incident_id"],
                "root_cause_id": inc["root_cause_id"],
                "root_cause_type": inc["root_cause_type"],
                "root_cause_node": inc["root_cause_node"],
                "root_cause_service": inc["root_cause_service"]
            })

        # 6. Build Root Cause Candidate Ranking Dataset (processed/root_cause_candidates.csv)
        root_cause_candidates = self._build_root_cause_candidates(
            scenario_id=scenario_id,
            graph=graph,
            incidents=incidents,
            py_rng=py_rng,
            np_rng=np_rng
        )

        return {
            "scenario_id": scenario_id,
            "topology_id": topology_id,
            "topology_family": graph.family_name,
            "topology_signature": topo_sig,
            "is_hard_negative": is_hard_neg,
            "graph": graph,
            "raw": {
                "metrics": raw_metrics,
                "logs": raw_logs,
                "traces": raw_traces,
                "alerts": raw_alerts,
                "nodes": graph.get_all_nodes_data(),
                "edges": graph.get_all_edges_data()
            },
            "ground_truth": {
                "anomaly_labels": anomaly_labels,
                "alert_labels": alert_labels,
                "incident_labels": incident_labels,
                "root_cause_labels": root_cause_labels,
                "propagation_labels": propagation_records,
                "remediation_labels": remed_gt_labels
            },
            "processed": {
                "anomaly_detection": anomaly_processed,
                "incident_correlation": correlation_pairs,
                "root_cause_candidates": root_cause_candidates,
                "propagation": propagation_records,
                "remediation": remed_processed
            }
        }

    def _build_root_cause_candidates(
        self,
        scenario_id: str,
        graph: InfrastructureGraph,
        incidents: List[Dict[str, Any]],
        py_rng: random.Random,
        np_rng: np.random.Generator
    ) -> List[Dict[str, Any]]:
        candidates = []
        nodes = graph.get_all_nodes_data()

        for inc in incidents:
            rc_node = inc["root_cause_node"]
            inc_id = inc["incident_id"]
            rc_type = inc["root_cause_type"]

            for n in nodes:
                is_rc = (n["node_id"] == rc_node)

                # Generate feature evidence scores where non-rc nodes can sometimes score high in single features
                if is_rc:
                    t_score = round(float(np_rng.uniform(0.75, 0.98)), 2)
                    sev_score = round(float(np_rng.uniform(0.70, 0.95)), 2)
                    top_score = round(float(np_rng.uniform(0.80, 0.99)), 2)
                    m_score = round(float(np_rng.uniform(0.70, 0.95)), 2)
                    l_score = round(float(np_rng.uniform(0.65, 0.95)), 2)
                    tr_score = round(float(np_rng.uniform(0.75, 0.98)), 2)
                    up_score = round(float(np_rng.uniform(0.85, 0.99)), 2)
                else:
                    # Non-root-cause candidates: some have high individual scores (e.g. API Gateway high error rate)
                    t_score = round(float(np_rng.uniform(0.10, 0.85)), 2)
                    sev_score = round(float(np_rng.uniform(0.10, 0.90)), 2)
                    top_score = round(float(np_rng.uniform(0.10, 0.60)), 2)
                    m_score = round(float(np_rng.uniform(0.10, 0.80)), 2)
                    l_score = round(float(np_rng.uniform(0.05, 0.70)), 2)
                    tr_score = round(float(np_rng.uniform(0.10, 0.85)), 2)
                    up_score = round(float(np_rng.uniform(0.05, 0.50)), 2)

                candidates.append({
                    "scenario_id": scenario_id,
                    "incident_id": inc_id,
                    "candidate_node_id": n["node_id"],
                    "candidate_service": n["service_name"],
                    "candidate_root_cause_type": rc_type if is_rc else py_rng.choice(["cpu_saturation", "network_latency", "slow_query"]),
                    "temporal_score": t_score,
                    "severity_score": sev_score,
                    "topology_score": top_score,
                    "metric_anomaly_score": m_score,
                    "log_evidence_score": l_score,
                    "trace_evidence_score": tr_score,
                    "upstream_score": up_score,
                    "is_root_cause": 1 if is_rc else 0
                })

        return candidates

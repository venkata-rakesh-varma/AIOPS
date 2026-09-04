import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import numpy as np
from graph.dependency_graph import InfrastructureGraph
from utils.random_utils import sample_weibull_delay

class FailurePropagationEngine:
    """
    Simulates causal downstream failure propagation along dependency graph paths preserving strict temporal order.
    """
    def __init__(self, py_rng: random.Random, np_rng: np.random.Generator):
        self.py_rng = py_rng
        self.np_rng = np_rng

    def propagate_failures(
        self,
        incident: Dict[str, Any],
        graph: InfrastructureGraph
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Returns:
          (affected_nodes_list, propagation_ground_truth_records)
        """
        root_node_id = incident["root_cause_node"]
        start_time = incident["start_time"]
        end_time = incident["end_time"]
        incident_id = incident["incident_id"]
        scenario_id = incident["scenario_id"]

        affected_nodes_map = {
            root_node_id: {
                "node_id": root_node_id,
                "failure_start_time": start_time,
                "failure_end_time": end_time,
                "propagation_delay_seconds": 0.0,
                "parent_failure_node": None,
                "propagation_level": 0,
                "is_root_cause": True
            }
        }

        propagation_records = []
        downstream = graph.get_downstream_nodes(root_node_id, max_depth=5)
        max_depth_seen = 0

        for target_node_id, level, parent_id in downstream:
            max_depth_seen = max(max_depth_seen, level)
            parent_info = affected_nodes_map.get(parent_id)
            parent_start = parent_info["failure_start_time"] if parent_info else start_time

            delay = sample_weibull_delay(self.np_rng, a=1.8, scale=12.0)
            target_start = parent_start + timedelta(seconds=delay)
            target_end = end_time + timedelta(seconds=delay * 0.5)

            affected_nodes_map[target_node_id] = {
                "node_id": target_node_id,
                "failure_start_time": target_start,
                "failure_end_time": target_end,
                "propagation_delay_seconds": round(delay, 2),
                "parent_failure_node": parent_id,
                "propagation_level": level,
                "is_root_cause": False
            }

            edge_data = graph.graph.get_edge_data(parent_id, target_node_id) or {}
            dep_type = edge_data.get("dependency_type", "HTTP")

            propagation_records.append({
                "scenario_id": scenario_id,
                "incident_id": incident_id,
                "source_node_id": parent_id,
                "target_node_id": target_node_id,
                "parent_failure_node": parent_id,
                "propagation_level": level,
                "propagation_delay_seconds": round(delay, 2),
                "source_failure_time": parent_start.isoformat(),
                "target_failure_time": target_start.isoformat(),
                "dependency_type": dep_type,
                "is_propagated": True
            })

        # Generate negative node-pair examples (where connected nodes did NOT propagate failure)
        all_nodes = [n["node_id"] for n in graph.get_all_nodes_data()]
        for u in all_nodes:
            for v in graph.graph.successors(u):
                if u not in affected_nodes_map or v not in affected_nodes_map:
                    edge_data = graph.graph.get_edge_data(u, v) or {}
                    propagation_records.append({
                        "scenario_id": scenario_id,
                        "incident_id": incident_id,
                        "source_node_id": u,
                        "target_node_id": v,
                        "parent_failure_node": u,
                        "propagation_level": 0,
                        "propagation_delay_seconds": 0.0,
                        "source_failure_time": start_time.isoformat(),
                        "target_failure_time": start_time.isoformat(),
                        "dependency_type": edge_data.get("dependency_type", "HTTP"),
                        "is_propagated": False
                    })

        incident["blast_radius"] = len(affected_nodes_map)
        incident["propagation_depth"] = max_depth_seen

        affected_list = list(affected_nodes_map.values())
        return affected_list, propagation_records

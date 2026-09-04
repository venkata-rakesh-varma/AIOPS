import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import numpy as np
from graph.dependency_graph import InfrastructureGraph
from utils.time_utils import DEFAULT_BASE_TIME

ROOT_CAUSE_CATEGORIES = [
    "cpu_saturation", "memory_exhaustion", "disk_exhaustion", "network_latency",
    "packet_loss", "database_connection_exhaustion", "database_slow_queries",
    "database_outage", "redis_failure", "kafka_broker_failure", "message_queue_backlog",
    "service_crash", "container_restart_loop", "kubernetes_pod_failure",
    "kubernetes_node_failure", "deployment_bug", "configuration_error",
    "authentication_failure", "dns_failure", "load_balancer_failure",
    "api_rate_limiting", "dependency_timeout", "memory_leak", "traffic_spike",
    "deadlock", "storage_failure", "certificate_expiration", "external_api_failure"
]

SEVERITIES = ["low", "medium", "high", "critical"]

class IncidentGenerator:
    """
    Generates single or multi-incident root cause specifications.
    """
    def __init__(self, py_rng: random.Random, np_rng: np.random.Generator):
        self.py_rng = py_rng
        self.np_rng = np_rng

    def generate_incidents(
        self,
        scenario_id: str,
        graph: InfrastructureGraph,
        base_time: datetime = DEFAULT_BASE_TIME,
        is_multi_incident: bool = False,
        is_hard_negative: bool = False
    ) -> List[Dict[str, Any]]:
        nodes = graph.get_all_nodes_data()
        if not nodes:
            return []

        # If hard negative scenario with no incident, return empty incident list
        if is_hard_negative and self.py_rng.random() < 0.5:
            return []

        incidents = []
        num_incidents = 2 if is_multi_incident else 1

        for i in range(num_incidents):
            inc_id = f"inc_{scenario_id}_{i+1:02d}"
            root_node = self.py_rng.choice(nodes)
            rc_type = self.py_rng.choice(ROOT_CAUSE_CATEGORIES)
            severity = self.py_rng.choice(SEVERITIES)

            # Offset start time for overlapping / simultaneous incidents
            offset_seconds = self.py_rng.randint(60, 300) * i
            start_dt = base_time + timedelta(minutes=5, seconds=offset_seconds)
            duration_minutes = self.py_rng.randint(10, 20)
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            detection_dt = start_dt + timedelta(seconds=self.py_rng.randint(15, 120))

            incidents.append({
                "scenario_id": scenario_id,
                "incident_id": inc_id,
                "root_cause_id": f"rc_{inc_id}",
                "root_cause_type": rc_type,
                "root_cause_node": root_node["node_id"],
                "root_cause_service": root_node["service_name"],
                "start_time": start_dt,
                "detection_time": detection_dt,
                "end_time": end_dt,
                "severity": severity,
                "blast_radius": 0,  # Computed post-propagation
                "propagation_depth": 0
            })

        return incidents

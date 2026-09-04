import random
import numpy as np
from typing import Dict, List, Any

class ServiceGenerator:
    """
    Generates service-level configuration, SLA expectations, and operational thresholds.
    """
    def __init__(self, py_rng: random.Random, np_rng: np.random.Generator):
        self.py_rng = py_rng
        self.np_rng = np_rng

    def generate_service_metadata(self, service_name: str, node_type: str) -> Dict[str, Any]:
        baseline_latency = {
            "api_gateway": 10.0,
            "load_balancer": 2.0,
            "web_service": 25.0,
            "auth_service": 15.0,
            "order_service": 30.0,
            "payment_service": 45.0,
            "inventory_service": 20.0,
            "postgresql": 8.0,
            "mysql": 10.0,
            "redis": 2.0,
            "kafka": 5.0,
            "mongodb": 12.0,
            "elasticsearch": 15.0
        }.get(node_type, 20.0)

        return {
            "service_name": service_name,
            "node_type": node_type,
            "sla_latency_ms": baseline_latency * 3.0,
            "target_availability": 0.999,
            "max_concurrency": self.py_rng.choice([100, 500, 1000, 5000]),
            "retry_policy": self.py_rng.choice(["exponential_backoff", "fixed_retry", "no_retry"])
        }

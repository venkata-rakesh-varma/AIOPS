import random
import numpy as np
from typing import Dict, Any

class InfrastructureGenerator:
    """
    Generates Kubernetes nodes, pods, containers, and physical host environment metadata.
    """
    def __init__(self, py_rng: random.Random, np_rng: np.random.Generator):
        self.py_rng = py_rng
        self.np_rng = np_rng

    def generate_host_metadata(self, host_id: str, region: str, zone: str) -> Dict[str, Any]:
        return {
            "host_id": host_id,
            "region": region,
            "zone": zone,
            "instance_type": self.py_rng.choice(["c5.2xlarge", "m5.xlarge", "r5.2xlarge", "t3.medium"]),
            "kernel_version": "5.15.0-88-generic",
            "os_name": "Ubuntu 22.04 LTS"
        }

    def generate_k8s_metadata(self, container_id: str, service_name: str) -> Dict[str, Any]:
        return {
            "cluster_name": "k8s-prod-cluster-01",
            "namespace": "production",
            "pod_name": f"{service_name}-pod-{self.py_rng.randint(100, 999)}",
            "container_id": container_id,
            "node_name": f"k8s-worker-{self.py_rng.randint(1, 10)}"
        }

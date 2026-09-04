import random
import numpy as np
from typing import Dict, List, Any, Tuple
from graph.dependency_graph import InfrastructureGraph

TOPOLOGY_FAMILIES = [
    "topology_a_3tier",
    "topology_b_ecommerce",
    "topology_c_caching_search",
    "topology_d_kafka_event",
    "topology_e_mesh"
]

NODE_TYPES = [
    "api_gateway", "load_balancer", "web_service", "auth_service",
    "user_service", "order_service", "payment_service", "inventory_service",
    "notification_service", "recommendation_service", "postgresql", "mysql",
    "redis", "mongodb", "kafka", "rabbitmq", "elasticsearch", "object_storage",
    "k8s_node", "container", "vm_instance"
]

DEPENDENCY_TYPES = ["HTTP", "TCP", "DATABASE", "CACHE", "MESSAGE_QUEUE", "STORAGE", "DNS"]

REGIONS = ["us-east-1", "us-west-2", "eu-central-1", "ap-southeast-1"]
ZONES = ["a", "b", "c"]

class TopologyGenerator:
    """
    Generates realistic infrastructure graph topologies across 5 distinct families.
    """
    def __init__(self, py_rng: random.Random, np_rng: np.random.Generator):
        self.py_rng = py_rng
        self.np_rng = np_rng

    def generate(
        self,
        scenario_id: str,
        topology_id: str,
        family_name: str = None,
        min_services: int = 8,
        max_services: int = 50
    ) -> InfrastructureGraph:
        if not family_name or family_name not in TOPOLOGY_FAMILIES:
            family_name = self.py_rng.choice(TOPOLOGY_FAMILIES)

        graph = InfrastructureGraph(scenario_id=scenario_id, topology_id=topology_id, family_name=family_name)
        num_services = self.py_rng.randint(min_services, max_services)
        region = self.py_rng.choice(REGIONS)

        if family_name == "topology_a_3tier":
            self._build_3tier(graph, num_services, region)
        elif family_name == "topology_b_ecommerce":
            self._build_ecommerce(graph, num_services, region)
        elif family_name == "topology_c_caching_search":
            self._build_caching_search(graph, num_services, region)
        elif family_name == "topology_d_kafka_event":
            self._build_kafka_event(graph, num_services, region)
        else:
            self._build_complex_mesh(graph, num_services, region)

        return graph

    def _add_node_helper(
        self,
        graph: InfrastructureGraph,
        node_id: str,
        node_type: str,
        service_name: str,
        region: str,
        criticality: str = "medium"
    ):
        zone = f"{region}{self.py_rng.choice(ZONES)}"
        host_id = f"host-{self.py_rng.randint(100, 999)}"
        container_id = f"ct-{self.py_rng.randint(1000, 9999)}"
        version = f"v{self.py_rng.randint(1, 3)}.{self.py_rng.randint(0, 9)}.0"
        cpu_cap = float(self.py_rng.choice([2.0, 4.0, 8.0, 16.0]))
        mem_cap = float(self.py_rng.choice([4.0, 8.0, 16.0, 32.0, 64.0]))
        replicas = self.py_rng.randint(1, 5)

        graph.add_infrastructure_node(
            node_id=node_id,
            node_type=node_type,
            service_name=service_name,
            environment="production",
            region=region,
            zone=zone,
            host_id=host_id,
            container_id=container_id,
            version=version,
            cpu_capacity=cpu_cap,
            memory_capacity=mem_cap,
            replica_count=replicas,
            criticality=criticality
        )

    def _build_3tier(self, graph: InfrastructureGraph, num_services: int, region: str):
        self._add_node_helper(graph, "gw_01", "api_gateway", "api_gateway", region, "critical")
        self._add_node_helper(graph, "lb_01", "load_balancer", "load_balancer", region, "critical")
        self._add_node_helper(graph, "auth_01", "auth_service", "auth_service", region, "high")
        self._add_node_helper(graph, "web_01", "web_service", "web_service", region, "high")
        self._add_node_helper(graph, "db_01", "postgresql", "postgresql", region, "critical")

        graph.add_dependency_edge("lb_01", "gw_01", "HTTP", 5.0, "critical")
        graph.add_dependency_edge("gw_01", "auth_01", "HTTP", 12.0, "high")
        graph.add_dependency_edge("gw_01", "web_01", "HTTP", 15.0, "high")
        graph.add_dependency_edge("auth_01", "db_01", "DATABASE", 8.0, "critical")
        graph.add_dependency_edge("web_01", "db_01", "DATABASE", 10.0, "critical")

        for i in range(2, num_services - 4):
            svc_id = f"sub_svc_{i}"
            self._add_node_helper(graph, svc_id, "web_service", f"sub_service_{i}", region, "low")
            graph.add_dependency_edge("web_01", svc_id, "HTTP", 10.0, "low")
            graph.add_dependency_edge(svc_id, "db_01", "DATABASE", 12.0, "medium")

    def _build_ecommerce(self, graph: InfrastructureGraph, num_services: int, region: str):
        self._add_node_helper(graph, "gw_01", "api_gateway", "api_gateway", region, "critical")
        self._add_node_helper(graph, "auth_01", "auth_service", "auth_service", region, "high")
        self._add_node_helper(graph, "order_01", "order_service", "order_service", region, "critical")
        self._add_node_helper(graph, "pay_01", "payment_service", "payment_service", region, "critical")
        self._add_node_helper(graph, "inv_01", "inventory_service", "inventory_service", region, "high")
        self._add_node_helper(graph, "db_master", "postgresql", "postgresql", region, "critical")
        self._add_node_helper(graph, "cache_01", "redis", "redis", region, "high")
        self._add_node_helper(graph, "mq_01", "kafka", "kafka", region, "high")

        graph.add_dependency_edge("gw_01", "auth_01", "HTTP", 10.0, "high")
        graph.add_dependency_edge("gw_01", "order_01", "HTTP", 15.0, "critical")
        graph.add_dependency_edge("order_01", "pay_01", "HTTP", 25.0, "critical")
        graph.add_dependency_edge("order_01", "inv_01", "HTTP", 20.0, "high")
        graph.add_dependency_edge("order_01", "cache_01", "CACHE", 3.0, "high")
        graph.add_dependency_edge("pay_01", "db_master", "DATABASE", 10.0, "critical")
        graph.add_dependency_edge("inv_01", "db_master", "DATABASE", 12.0, "high")
        graph.add_dependency_edge("order_01", "mq_01", "MESSAGE_QUEUE", 5.0, "medium")

        for i in range(1, max(1, num_services - 7)):
            svc_id = f"ecom_aux_{i}"
            self._add_node_helper(graph, svc_id, "user_service", f"user_service_{i}", region, "low")
            graph.add_dependency_edge("gw_01", svc_id, "HTTP", 15.0, "low")
            graph.add_dependency_edge(svc_id, "cache_01", "CACHE", 4.0, "low")

    def _build_caching_search(self, graph: InfrastructureGraph, num_services: int, region: str):
        self._add_node_helper(graph, "gw_01", "api_gateway", "api_gateway", region, "critical")
        self._add_node_helper(graph, "rec_01", "recommendation_service", "recommendation_service", region, "high")
        self._add_node_helper(graph, "es_01", "elasticsearch", "elasticsearch", region, "critical")
        self._add_node_helper(graph, "redis_01", "redis", "redis", region, "critical")
        self._add_node_helper(graph, "mongo_01", "mongodb", "mongodb", region, "high")

        graph.add_dependency_edge("gw_01", "rec_01", "HTTP", 15.0, "high")
        graph.add_dependency_edge("rec_01", "redis_01", "CACHE", 2.0, "critical")
        graph.add_dependency_edge("rec_01", "es_01", "HTTP", 18.0, "high")
        graph.add_dependency_edge("rec_01", "mongo_01", "DATABASE", 14.0, "high")

        for i in range(1, max(1, num_services - 4)):
            svc_id = f"search_node_{i}"
            self._add_node_helper(graph, svc_id, "user_service", f"search_aux_{i}", region, "medium")
            graph.add_dependency_edge("gw_01", svc_id, "HTTP", 12.0, "medium")
            graph.add_dependency_edge(svc_id, "es_01", "HTTP", 20.0, "high")

    def _build_kafka_event(self, graph: InfrastructureGraph, num_services: int, region: str):
        self._add_node_helper(graph, "ingest_01", "api_gateway", "ingestion_gateway", region, "critical")
        self._add_node_helper(graph, "kafka_broker", "kafka", "kafka", region, "critical")
        self._add_node_helper(graph, "notif_01", "notification_service", "notification_service", region, "high")
        self._add_node_helper(graph, "user_01", "user_service", "user_service", region, "medium")
        self._add_node_helper(graph, "db_event", "mysql", "mysql", region, "high")

        graph.add_dependency_edge("ingest_01", "kafka_broker", "MESSAGE_QUEUE", 5.0, "critical")
        graph.add_dependency_edge("kafka_broker", "notif_01", "MESSAGE_QUEUE", 10.0, "high")
        graph.add_dependency_edge("kafka_broker", "user_01", "MESSAGE_QUEUE", 12.0, "medium")
        graph.add_dependency_edge("notif_01", "db_event", "DATABASE", 15.0, "high")

        for i in range(1, max(1, num_services - 4)):
            consumer_id = f"consumer_{i}"
            self._add_node_helper(graph, consumer_id, "web_service", f"kafka_consumer_{i}", region, "low")
            graph.add_dependency_edge("kafka_broker", consumer_id, "MESSAGE_QUEUE", 8.0, "low")
            graph.add_dependency_edge(consumer_id, "db_event", "DATABASE", 10.0, "low")

    def _build_complex_mesh(self, graph: InfrastructureGraph, num_services: int, region: str):
        node_ids = []
        for i in range(num_services):
            node_id = f"node_{i:02d}"
            node_type = self.py_rng.choice(NODE_TYPES)
            svc_name = f"mesh_svc_{i}"
            crit = self.py_rng.choice(["low", "medium", "high", "critical"])
            self._add_node_helper(graph, node_id, node_type, svc_name, region, crit)
            node_ids.append(node_id)

        # Create random mesh dependencies ensuring connected graph
        for i in range(1, len(node_ids)):
            parent = self.py_rng.choice(node_ids[:i])
            child = node_ids[i]
            dep_type = self.py_rng.choice(DEPENDENCY_TYPES)
            lat = float(self.py_rng.uniform(2.0, 35.0))
            graph.add_dependency_edge(parent, child, dep_type, lat, "medium")

        # Add cross-mesh edges for complexity
        for _ in range(num_services):
            u = self.py_rng.choice(node_ids)
            v = self.py_rng.choice(node_ids)
            if u != v and not graph.graph.has_edge(u, v):
                dep_type = self.py_rng.choice(DEPENDENCY_TYPES)
                graph.add_dependency_edge(u, v, dep_type, 10.0, "low")

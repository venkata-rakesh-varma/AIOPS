import hashlib
import json
import networkx as nx
from typing import Dict, List, Any, Optional, Tuple

class InfrastructureGraph:
    """
    NetworkX-backed dependency graph representing multi-tier cloud infrastructure.
    """
    def __init__(self, scenario_id: str, topology_id: str, family_name: str):
        self.scenario_id = scenario_id
        self.topology_id = topology_id
        self.family_name = family_name
        self.graph = nx.DiGraph(scenario_id=scenario_id, topology_id=topology_id, family=family_name)

    def add_infrastructure_node(
        self,
        node_id: str,
        node_type: str,
        service_name: str,
        environment: str = "production",
        region: str = "us-east-1",
        zone: str = "us-east-1a",
        host_id: str = "host-01",
        container_id: str = "ct-01",
        version: str = "v1.2.0",
        cpu_capacity: float = 4.0,
        memory_capacity: float = 16.0,
        replica_count: int = 3,
        criticality: str = "high"
    ):
        self.graph.add_node(
            node_id,
            node_id=node_id,
            node_type=node_type,
            service_name=service_name,
            environment=environment,
            region=region,
            zone=zone,
            host_id=host_id,
            container_id=container_id,
            version=version,
            cpu_capacity=cpu_capacity,
            memory_capacity=memory_capacity,
            replica_count=replica_count,
            criticality=criticality,
            scenario_id=self.scenario_id,
            topology_id=self.topology_id
        )

    def add_dependency_edge(
        self,
        source: str,
        target: str,
        dependency_type: str = "HTTP",
        latency: float = 15.0,
        criticality: str = "medium"
    ):
        if source in self.graph and target in self.graph:
            self.graph.add_edge(
                source,
                target,
                source=source,
                target=target,
                dependency_type=dependency_type,
                latency=latency,
                criticality=criticality,
                scenario_id=self.scenario_id,
                topology_id=self.topology_id
            )

    def get_downstream_nodes(self, node_id: str, max_depth: int = 5) -> List[Tuple[str, int, str]]:
        """
        Returns list of (downstream_node_id, depth, parent_node_id) using BFS.
        """
        visited = {node_id: (0, None)}
        queue = [(node_id, 0)]
        results = []

        while queue:
            curr, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for successor in self.graph.successors(curr):
                if successor not in visited:
                    visited[successor] = (depth + 1, curr)
                    queue.append((successor, depth + 1))
                    results.append((successor, depth + 1, curr))

        return results

    def get_upstream_nodes(self, node_id: str) -> List[str]:
        """Returns nodes that depend directly on this node (predecessors in DiGraph)."""
        if node_id in self.graph:
            return list(self.graph.predecessors(node_id))
        return []

    def get_all_nodes_data(self) -> List[Dict[str, Any]]:
        return [data for _, data in self.graph.nodes(data=True)]

    def get_all_edges_data(self) -> List[Dict[str, Any]]:
        return [data for _, _, data in self.graph.edges(data=True)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "topology_id": self.topology_id,
            "family_name": self.family_name,
            "nodes": self.get_all_nodes_data(),
            "edges": self.get_all_edges_data()
        }


def compute_topology_signature(graph: InfrastructureGraph) -> str:
    """
    Computes a deterministic MD5 hash signature of graph structure and node/edge distributions.
    Used for splitting and anti-leakage checks.
    """
    node_types = sorted([d.get("node_type", "") for d in graph.get_all_nodes_data()])
    edge_types = sorted([d.get("dependency_type", "") for d in graph.get_all_edges_data()])
    in_degrees = sorted([deg for _, deg in graph.graph.in_degree()])
    out_degrees = sorted([deg for _, deg in graph.graph.out_degree()])

    summary = {
        "family": graph.family_name,
        "num_nodes": graph.graph.number_of_nodes(),
        "num_edges": graph.graph.number_of_edges(),
        "node_types": node_types,
        "edge_types": edge_types,
        "in_degrees": in_degrees,
        "out_degrees": out_degrees
    }
    raw_bytes = json.dumps(summary, sort_keys=True).encode("utf-8")
    return hashlib.md5(raw_bytes).hexdigest()

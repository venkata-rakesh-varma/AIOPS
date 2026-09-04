from pathlib import Path
from typing import List, Dict, Any, Union
from .dependency_graph import InfrastructureGraph
from utils.io_utils import append_csv_records, save_json

class GraphExporter:
    """
    Exports topology graphs into CSV files and multi-scenario JSON graph stores compatible with
    NetworkX, Neo4j, PyTorch Geometric, and DGL.
    """

    NODE_FIELDNAMES = [
        "scenario_id",
        "topology_id",
        "node_id",
        "node_type",
        "service_name",
        "environment",
        "region",
        "zone",
        "host_id",
        "container_id",
        "version",
        "cpu_capacity",
        "memory_capacity",
        "replica_count",
        "criticality"
    ]

    EDGE_FIELDNAMES = [
        "scenario_id",
        "topology_id",
        "source",
        "target",
        "dependency_type",
        "latency",
        "criticality"
    ]

    @classmethod
    def export_graph_to_dir(
        cls,
        graph: InfrastructureGraph,
        graph_dir: Union[str, Path]
    ):
        g_dir = Path(graph_dir)
        nodes_csv = g_dir / "nodes.csv"
        edges_csv = g_dir / "edges.csv"

        append_csv_records(nodes_csv, graph.get_all_nodes_data(), cls.NODE_FIELDNAMES)
        append_csv_records(edges_csv, graph.get_all_edges_data(), cls.EDGE_FIELDNAMES)

    @classmethod
    def save_graphs_collection(
        cls,
        graphs_dict: Dict[str, Dict[str, Any]],
        output_file: Union[str, Path]
    ):
        save_json(output_file, graphs_dict, indent=2)

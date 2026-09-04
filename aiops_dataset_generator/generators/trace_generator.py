import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import numpy as np
from graph.dependency_graph import InfrastructureGraph
from utils.time_utils import format_iso, add_jitter

class TraceGenerator:
    """
    Generates distributed request traces with strict parent-child span hierarchy,
    fan-out/fan-in, retries, and downstream accumulated latency propagation.
    """
    def __init__(self, py_rng: random.Random, np_rng: np.random.Generator, config: Dict[str, Any] = None):
        self.py_rng = py_rng
        self.np_rng = np_rng
        self.config = config or {}

    def generate_traces(
        self,
        scenario_id: str,
        graph: InfrastructureGraph,
        affected_nodes_info: List[Dict[str, Any]],
        start_time: datetime,
        duration_minutes: int = 30,
        num_traces: int = 40
    ) -> List[Dict[str, Any]]:
        affected_map = {item["node_id"]: item for item in affected_nodes_info}
        missing_prob = self.config.get("telemetry", {}).get("missing_trace_probability", 0.05)
        traces = []

        # Find entrypoint nodes (nodes with in-degree 0 or API Gateway)
        entrypoints = [
            n["node_id"] for n in graph.get_all_nodes_data()
            if graph.graph.in_degree(n["node_id"]) == 0 or "gateway" in n["node_type"] or "balancer" in n["node_type"]
        ]
        if not entrypoints:
            entrypoints = [n["node_id"] for n in graph.get_all_nodes_data()[:1]]

        for t_idx in range(num_traces):
            if self.np_rng.random() < missing_prob:
                continue

            trace_id = f"tr_{scenario_id}_{t_idx+1:05d}"
            offset_sec = float(self.np_rng.uniform(0, duration_minutes * 60))
            t_start = start_time + timedelta(seconds=offset_sec)

            root_node_id = self.py_rng.choice(entrypoints)
            span_counter = 1

            spans_buffer = []
            self._recursive_build_spans(
                scenario_id=scenario_id,
                trace_id=trace_id,
                graph=graph,
                curr_node_id=root_node_id,
                parent_span_id=None,
                curr_start=t_start,
                affected_map=affected_map,
                spans_buffer=spans_buffer,
                span_counter_ref=[span_counter],
                depth=0,
                max_depth=4
            )

            traces.extend(spans_buffer)

        traces.sort(key=lambda x: x["start_time"])
        return traces

    def _recursive_build_spans(
        self,
        scenario_id: str,
        trace_id: str,
        graph: InfrastructureGraph,
        curr_node_id: str,
        parent_span_id: str,
        curr_start: datetime,
        affected_map: Dict[str, Any],
        spans_buffer: List[Dict[str, Any]],
        span_counter_ref: List[int],
        depth: int,
        max_depth: int
    ) -> float:
        """
        Recursively builds spans down dependency paths, returning total duration_ms accumulated downstream.
        """
        node_data = graph.graph.nodes[curr_node_id]
        svc_name = node_data["service_name"]

        span_id = f"sp_{trace_id[3:]}_{span_counter_ref[0]:03d}"
        span_counter_ref[0] += 1

        affected_info = affected_map.get(curr_node_id)
        is_affected = False
        if affected_info and affected_info["failure_start_time"] <= curr_start <= affected_info["failure_end_time"]:
            is_affected = True

        # Base execution time
        self_exec_ms = float(self.np_rng.uniform(2.0, 10.0))
        if is_affected:
            self_exec_ms += float(self.np_rng.uniform(150.0, 800.0))

        downstream_ms = 0.0
        successors = list(graph.graph.successors(curr_node_id))

        # Build downstream child spans
        if depth < max_depth and successors:
            # Fan-out: call 1 to 3 downstream dependencies
            chosen_children = self.py_rng.sample(successors, min(len(successors), self.py_rng.randint(1, 3)))
            child_start = curr_start + timedelta(milliseconds=self_exec_ms * 0.5)

            for child_id in chosen_children:
                c_dur = self._recursive_build_spans(
                    scenario_id=scenario_id,
                    trace_id=trace_id,
                    graph=graph,
                    curr_node_id=child_id,
                    parent_span_id=span_id,
                    curr_start=child_start,
                    affected_map=affected_map,
                    spans_buffer=spans_buffer,
                    span_counter_ref=span_counter_ref,
                    depth=depth + 1,
                    max_depth=max_depth
                )
                downstream_ms += c_dur
                child_start = child_start + timedelta(milliseconds=c_dur)

        total_duration_ms = self_exec_ms + downstream_ms
        status = "OK"
        error_msg = None

        if is_affected or total_duration_ms > 500.0:
            if self.np_rng.random() < 0.6:
                status = "ERROR"
                error_msg = self.py_rng.choice([
                    "HTTP 504 Gateway Timeout",
                    "ConnectionRefusedError",
                    "DeadlineExceededException",
                    "ServiceUnavailable503"
                ])

        # Raw trace span record (No ground truth labels!)
        spans_buffer.append({
            "scenario_id": scenario_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "service_name": svc_name,
            "operation": f"POST /{svc_name}/v1/handle",
            "start_time": format_iso(curr_start),
            "duration_ms": round(total_duration_ms, 2),
            "status": status,
            "error": error_msg,
            "dependency": curr_node_id
        })

        return total_duration_ms

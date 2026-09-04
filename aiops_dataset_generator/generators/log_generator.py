import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import numpy as np
from graph.dependency_graph import InfrastructureGraph
from utils.time_utils import format_iso, add_jitter

LOG_LEVELS = ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]

# Linguistic variations for realistic event logging
LOG_TEMPLATES = {
    "db_timeout": [
        "database connection timeout after {timeout}ms",
        "DB connection timed out trying to execute query",
        "connection acquisition exceeded pool timeout limit of {timeout}ms",
        "unable to obtain DB connection from active pool",
        "pool exhausted while waiting for database handle"
    ],
    "cpu_high": [
        "high CPU utilization detected: {val}% threshold exceeded",
        "thread pool saturated due to high CPU load",
        "CPU throttle active on container cgroup",
        "high CPU usage warning on worker host"
    ],
    "memory_leak": [
        "JVM heap memory usage exceeded {val}% threshold",
        "potential memory leak detected in worker thread heap space",
        "garbage collection pause duration high: {val}ms",
        "out of memory warning: available memory critically low"
    ],
    "network_latency": [
        "packet loss observed on upstream network interface",
        "high latency detected calling downstream dependency: {val}ms",
        "socket connection timed out waiting for HTTP response",
        "TCP connection reset by peer"
    ],
    "kafka_backlog": [
        "Kafka consumer lag spike detected on topic orders: {val} messages behind",
        "broker unreachable or partition leader rebalancing in progress",
        "commit offset timed out for consumer group order-processing"
    ],
    "pod_crash": [
        "container restarted with exit code 137 (OOMKilled)",
        "health check liveness probe failed 3 times",
        "pod crash loop backoff detected on replica",
        "failed to start container: image pull or crash error"
    ],
    "normal": [
        "processed incoming request successfully in {val}ms",
        "service heartbeat check status OK",
        "scheduled background task executed cleanly",
        "cache hit ratio nominal at {val}%"
    ]
}

ERROR_CODES = [
    "ERR_DB_TIMEOUT_504", "ERR_HTTP_GATEWAY_TIMEOUT_504", "ERR_KAFKA_BROKER_UNAVAILABLE",
    "ERR_REDIS_CONNECTION_REFUSED", "ERR_OOM_KILLED_137", "ERR_SERVICE_UNAVAILABLE_503",
    "ERR_AUTH_TOKEN_EXPIRED_401", "ERR_TOO_MANY_REQUESTS_429"
]

class LogGenerator:
    """
    Generates structured JSONL log streams with rich linguistic variations and realistic log levels.
    """
    def __init__(self, py_rng: random.Random, np_rng: np.random.Generator, config: Dict[str, Any] = None):
        self.py_rng = py_rng
        self.np_rng = np_rng
        self.config = config or {}

    def generate_logs(
        self,
        scenario_id: str,
        graph: InfrastructureGraph,
        affected_nodes_info: List[Dict[str, Any]],
        start_time: datetime,
        duration_minutes: int = 30
    ) -> List[Dict[str, Any]]:
        nodes = graph.get_all_nodes_data()
        affected_map = {item["node_id"]: item for item in affected_nodes_info}
        missing_prob = self.config.get("telemetry", {}).get("missing_log_probability", 0.03)

        logs = []
        log_counter = 1

        for node in nodes:
            node_id = node["node_id"]
            svc_name = node["service_name"]
            affected_info = affected_map.get(node_id)

            # Generate baseline log count
            num_logs = self.py_rng.randint(20, 50)
            for _ in range(num_logs):
                if self.np_rng.random() < missing_prob:
                    continue

                offset_sec = float(self.np_rng.uniform(0, duration_minutes * 60))
                log_dt = start_time + timedelta(seconds=offset_sec)
                log_dt = add_jitter(log_dt, self.np_rng, max_jitter_seconds=1.0)

                log_id = f"log_{scenario_id}_{log_counter:06d}"
                log_counter += 1
                req_id = f"req_{scenario_id}_{self.py_rng.randint(10000, 99999)}"
                trace_id = f"tr_{scenario_id}_{self.py_rng.randint(1000, 9999)}"

                level = self.py_rng.choice(["DEBUG", "INFO", "INFO", "INFO", "WARN"])
                event_type = "system_event"

                # Check if log falls inside anomalous failure window
                if affected_info and affected_info["failure_start_time"] <= log_dt <= affected_info["failure_end_time"]:
                    level = self.py_rng.choice(["WARN", "ERROR", "CRITICAL"])
                    event_type = "anomaly_event"

                    template_category = self.py_rng.choice([
                        "db_timeout", "cpu_high", "memory_leak", "network_latency",
                        "kafka_backlog", "pod_crash"
                    ])
                    template = self.py_rng.choice(LOG_TEMPLATES[template_category])
                    msg = template.format(
                        val=self.py_rng.randint(85, 99),
                        timeout=self.py_rng.randint(1000, 5000)
                    )
                    err_code = self.py_rng.choice(ERROR_CODES)
                else:
                    template = self.py_rng.choice(LOG_TEMPLATES["normal"])
                    msg = template.format(val=self.py_rng.randint(5, 45))
                    err_code = None

                # RAW OBSERVABLE LOG RECORD (Strictly NO ground-truth labels!)
                logs.append({
                    "scenario_id": scenario_id,
                    "timestamp": format_iso(log_dt),
                    "log_id": log_id,
                    "node_id": node_id,
                    "service_name": svc_name,
                    "log_level": level,
                    "event_type": event_type,
                    "message": msg,
                    "error_code": err_code,
                    "request_id": req_id,
                    "trace_id": trace_id
                })

        logs.sort(key=lambda x: x["timestamp"])
        return logs

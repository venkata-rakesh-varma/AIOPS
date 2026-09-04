import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import numpy as np
from graph.dependency_graph import InfrastructureGraph
from utils.time_utils import generate_timestamps, format_iso, parse_iso
from utils.random_utils import sample_noise

class MetricGenerator:
    """
    Generates time-series infrastructure, application, database, Kafka, and Kubernetes metrics
    with baseline diversity, noise, seasonality, missingness, and incident anomalies.
    """
    def __init__(self, py_rng: random.Random, np_rng: np.random.Generator, config: Dict[str, Any] = None):
        self.py_rng = py_rng
        self.np_rng = np_rng
        self.config = config or {}

    def generate_metrics(
        self,
        scenario_id: str,
        graph: InfrastructureGraph,
        affected_nodes_info: List[Dict[str, Any]],
        incidents: List[Dict[str, Any]],
        start_time: datetime,
        duration_minutes: int = 30,
        interval_seconds: int = 10
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Returns:
          (raw_metrics, anomaly_ground_truth_labels, anomaly_processed_records)
        """
        timestamps = generate_timestamps(start_time, duration_minutes, interval_seconds)
        nodes = graph.get_all_nodes_data()

        affected_lookup = {item["node_id"]: item for item in affected_nodes_info}
        incident_lookup = {inc["root_cause_node"]: inc for inc in incidents}

        raw_metrics = []
        anomaly_labels = []
        anomaly_processed = []

        missing_prob = self.config.get("telemetry", {}).get("missing_metric_probability", 0.05)
        noise_lvl = self.config.get("telemetry", {}).get("noise_level", 0.10)

        for node in nodes:
            node_id = node["node_id"]
            node_type = node["node_type"]
            svc_name = node["service_name"]

            affected_info = affected_lookup.get(node_id)
            root_inc = incident_lookup.get(node_id)

            # Baseline parameters per service type
            base_cpu, base_mem, base_lat = self._get_baselines(node_type)

            for idx, ts in enumerate(timestamps):
                # Apply random missingness
                if self.np_rng.random() < missing_prob:
                    continue

                # Seasonality + trend
                sine_wave = np.sin(idx / 10.0) * 5.0
                noise = sample_noise(self.np_rng, scale=noise_lvl * 5.0)

                cpu_val = min(100.0, max(0.0, base_cpu + sine_wave + noise))
                mem_val = min(100.0, max(0.0, base_mem + sine_wave * 0.2 + sample_noise(self.np_rng, scale=2.0)))
                mem_avail = max(100.0, (100.0 - mem_val) * node["memory_capacity"] * 10.0)
                disk_val = min(100.0, max(10.0, 45.0 + idx * 0.01 + sample_noise(self.np_rng, scale=1.0)))
                disk_io_wait = max(0.0, 1.5 + sample_noise(self.np_rng, scale=0.5))

                net_lat = max(0.5, base_lat + sample_noise(self.np_rng, scale=2.0))
                pkt_loss = max(0.0, float(self.np_rng.exponential(0.01)))
                net_tp = max(1.0, 150.0 + sine_wave * 10.0 + sample_noise(self.np_rng, scale=15.0))

                req_rate = max(0.0, 50.0 + sine_wave * 8.0 + sample_noise(self.np_rng, scale=5.0))
                resp_time = net_lat + 5.0
                err_rate = max(0.0, float(self.np_rng.exponential(0.1)))
                http_5xx = err_rate * 0.3
                http_4xx = err_rate * 0.7

                active_conn = max(1, int(15 + sine_wave + sample_noise(self.np_rng, scale=3.0)))
                conn_pool_use = min(100.0, max(0.0, active_conn * 2.0))
                query_lat = max(1.0, base_lat * 0.8 + sample_noise(self.np_rng, scale=1.5))
                slow_queries = int(max(0, sample_noise(self.np_rng, loc=0.2, scale=0.5)))
                tps = max(0.0, 120.0 + sine_wave * 15.0)

                consumer_lag = int(max(0, 10 + sample_noise(self.np_rng, scale=5.0)))
                producer_rate = max(0.0, 50.0 + sine_wave * 5.0)
                broker_cpu = cpu_val

                pod_restarts = 0
                pod_cpu = cpu_val
                pod_mem = mem_val
                node_cpu = cpu_val
                node_mem = mem_val

                is_anomaly = False
                anomaly_type = "normal"

                # Inject anomalous behavior if within affected failure window
                if affected_info and affected_info["failure_start_time"] <= ts <= affected_info["failure_end_time"]:
                    is_anomaly = True
                    rc_type = root_inc["root_cause_type"] if root_inc else "cascading_failure"

                    if "cpu" in rc_type:
                        cpu_val = min(100.0, cpu_val + self.np_rng.uniform(40.0, 60.0))
                        pod_cpu = cpu_val
                        anomaly_type = "point_anomaly"
                    elif "memory" in rc_type:
                        mem_val = min(100.0, mem_val + (idx * 0.8))  # Gradual leak
                        mem_avail = max(10.0, mem_avail * 0.1)
                        pod_mem = mem_val
                        anomaly_type = "collective_anomaly"
                    elif "latency" in rc_type or "network" in rc_type:
                        net_lat = net_lat * self.np_rng.uniform(5.0, 20.0)
                        resp_time = net_lat + 20.0
                        pkt_loss = self.np_rng.uniform(5.0, 25.0)
                        anomaly_type = "contextual_anomaly"
                    elif "database" in rc_type:
                        conn_pool_use = min(100.0, 85.0 + self.np_rng.uniform(10.0, 15.0))
                        query_lat = query_lat * self.np_rng.uniform(4.0, 12.0)
                        slow_queries += int(self.np_rng.uniform(5, 20))
                        err_rate = self.np_rng.uniform(15.0, 45.0)
                        http_5xx = err_rate * 0.8
                        anomaly_type = "point_anomaly"
                    elif "kafka" in rc_type or "queue" in rc_type:
                        consumer_lag += int(self.np_rng.uniform(2000, 8000))
                        anomaly_type = "collective_anomaly"
                    elif "crash" in rc_type or "restart" in rc_type:
                        pod_restarts += self.py_rng.randint(1, 4)
                        err_rate = self.np_rng.uniform(30.0, 80.0)
                        anomaly_type = "point_anomaly"
                    else:
                        resp_time *= self.np_rng.uniform(2.0, 5.0)
                        err_rate = self.np_rng.uniform(5.0, 20.0)
                        anomaly_type = "contextual_anomaly"

                ts_str = format_iso(ts)

                # RAW TELEMETRY RECORD (No Ground Truth Labels!)
                raw_metrics.append({
                    "scenario_id": scenario_id,
                    "timestamp": ts_str,
                    "node_id": node_id,
                    "service_name": svc_name,
                    "region": node["region"],
                    "zone": node["zone"],
                    "cpu_usage_percent": round(cpu_val, 2),
                    "memory_usage_percent": round(mem_val, 2),
                    "memory_available_mb": round(mem_avail, 2),
                    "disk_usage_percent": round(disk_val, 2),
                    "disk_io_wait": round(disk_io_wait, 2),
                    "network_latency_ms": round(net_lat, 2),
                    "packet_loss_percent": round(pkt_loss, 2),
                    "network_throughput_mbps": round(net_tp, 2),
                    "request_rate": round(req_rate, 2),
                    "response_time_ms": round(resp_time, 2),
                    "error_rate_percent": round(err_rate, 2),
                    "http_5xx_rate": round(http_5xx, 2),
                    "http_4xx_rate": round(http_4xx, 2),
                    "active_connections": active_conn,
                    "connection_pool_usage": round(conn_pool_use, 2),
                    "query_latency_ms": round(query_lat, 2),
                    "slow_query_count": slow_queries,
                    "transactions_per_second": round(tps, 2),
                    "consumer_lag": consumer_lag,
                    "producer_rate": round(producer_rate, 2),
                    "broker_cpu": round(broker_cpu, 2),
                    "pod_restart_count": pod_restarts,
                    "pod_cpu": round(pod_cpu, 2),
                    "pod_memory": round(pod_mem, 2),
                    "node_cpu": round(node_cpu, 2),
                    "node_memory": round(node_mem, 2)
                })

                # GROUND TRUTH ANOMALY RECORD
                anomaly_labels.append({
                    "scenario_id": scenario_id,
                    "timestamp": ts_str,
                    "node_id": node_id,
                    "is_anomaly": is_anomaly,
                    "anomaly_type": anomaly_type,
                    "incident_id": root_inc["incident_id"] if root_inc else (affected_info["parent_failure_node"] if affected_info else None)
                })

                # PROCESSED ANOMALY DETECTION DATASET
                anomaly_processed.append({
                    "scenario_id": scenario_id,
                    "timestamp": ts_str,
                    "node_id": node_id,
                    "cpu_usage_percent": round(cpu_val, 2),
                    "memory_usage_percent": round(mem_val, 2),
                    "network_latency_ms": round(net_lat, 2),
                    "response_time_ms": round(resp_time, 2),
                    "error_rate_percent": round(err_rate, 2),
                    "connection_pool_usage": round(conn_pool_use, 2),
                    "is_anomaly": is_anomaly,
                    "anomaly_type": anomaly_type
                })

        return raw_metrics, anomaly_labels, anomaly_processed

    def _get_baselines(self, node_type: str) -> Tuple[float, float, float]:
        if "db" in node_type or "postgres" in node_type or "mysql" in node_type:
            return (35.0, 60.0, 5.0)
        elif "redis" in node_type:
            return (15.0, 40.0, 1.5)
        elif "kafka" in node_type:
            return (40.0, 50.0, 4.0)
        elif "gateway" in node_type or "balancer" in node_type:
            return (30.0, 35.0, 8.0)
        else:
            return (45.0, 55.0, 15.0)

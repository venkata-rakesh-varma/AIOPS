# AIOps Incident Correlation & Self-Healing Infrastructure Synthetic Dataset Generator

A reproducible, high-fidelity synthetic data generation framework designed for research and production machine learning in **AIOps**, **Incident Correlation**, **Root Cause Analysis (RCA)**, **Graph Neural Networks (GNNs)**, **Failure Propagation Prediction**, and **Autonomous Infrastructure Remediation**.

---

## 1. Project Purpose & Architecture

Modern cloud infrastructures generate complex, high-velocity, multi-modal telemetry streams (metrics, logs, traces, alerts). When an infrastructure anomaly occurs, failure propagates downstream through dependency graph paths, producing cascades of noisy alerts and correlated telemetry anomalies.

This project simulates multi-tier microservices, cloud servers, databases, caches, message queues, Kubernetes pods, and network layers under normal operating conditions and 28 distinct root-cause incident scenarios. 

```
                                +---------------------------+
                                |    config/config.yaml     |
                                +-------------+-------------+
                                              |
                                              v
                                +---------------------------+
                                |  utils/ (seed, time, IO)  |
                                +-------------+-------------+
                                              |
                                              v
+---------------------------------------------------------------------------------------+
| GENERATORS & GRAPH ENGINE                                                             |
|                                                                                       |
|  Topology: topology_generator.py -> dependency_graph.py                                |
|  Infrastructure/Services: service_generator.py, infrastructure_generator.py           |
|  Causality & Propagation: incident_generator.py, failure_propagation.py               |
|  Telemetry: metric_generator.py, log_generator.py, trace_generator.py, alert_gen.py  |
|  Remediation: remediation_generator.py                                                |
|  Scenario Builder: scenario_generator.py (synthesizes single reproducible scenario)   |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
| DATA PIPELINE & EXPORTER                                                              |
|                                                                                       |
|  1. graph_exporter.py    -> Nodes/edges CSV & scenario graph collection JSON          |
|  2. dataset_builder.py   -> Multi-processing engine creating raw/ground_truth/proc  |
|  3. dataset_splitter.py  -> Scenario-level train/val/test/hard_test splits           |
|  4. dataset_validator.py -> Integrity, anti-leakage, trace validation & statistics    |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
| OUTPUT STRUCTURE (data/raw/, data/ground_truth/, data/processed/, data/graph/)        |
+---------------------------------------------------------------------------------------+
```

---

## 2. Directory Structure & Output Files

The generated dataset is structured into distinct logical layers:

```
data/
├── raw/                          # Raw Observable Telemetry (Strictly NO ground truth!)
│   ├── metrics.csv
│   ├── logs.jsonl
│   ├── traces.csv
│   ├── alerts.csv
│   ├── nodes.csv
│   └── edges.csv
│
├── ground_truth/                 # Ground Truth Supervised Labels (Joined via scenario_id)
│   ├── anomaly_labels.csv
│   ├── alert_labels.csv
│   ├── incident_labels.csv
│   ├── root_cause_labels.csv
│   ├── propagation_labels.csv
│   └── remediation_labels.csv
│
├── processed/                    # Task-Specific Machine Learning Datasets
│   ├── anomaly_detection.csv
│   ├── incident_correlation.csv
│   ├── root_cause_candidates.csv
│   ├── propagation.csv
│   ├── remediation.csv
│   └── time_series.parquet
│
├── graph/                        # Topology Graph Datasets & Neo4j/GNN Formats
│   ├── nodes.csv
│   ├── edges.csv
│   └── graphs.json
│
├── train/                        # Scenario-Level Train Split (70%)
├── validation/                   # Scenario-Level Validation Split (15%)
├── test/                         # Scenario-Level Test Split (15%)
├── hard_test/                    # Hard Evaluation Split (Unseen topology/extreme noise)
│
├── manifest.json                 # Dataset Generation Manifest & Checksums
└── dataset_statistics.json       # Distribution Summary Statistics
```

---

## 3. Strict Observation vs. Ground-Truth Separation

To prevent target label leakage during ML model inference:

- **Raw Observation Files (`data/raw/`)**: Contain **ONLY** features accessible to an observability system at runtime (`timestamp`, `node_id`, `service_name`, `cpu_usage_percent`, `message`, `trace_id`, `span_id`, `observed_value`, `threshold`). Forbidden ground-truth columns (`incident_id`, `root_cause_type`, `is_root_cause`, `recommended_action`, `propagation_level`) are **STRICTLY PROHIBITED** from raw files.
- **Ground-Truth Files (`data/ground_truth/`)**: Contain target labels linked via `scenario_id`, `alert_id`, `node_id`, or `incident_id` for offline model training and evaluation.

---

## 4. Root Cause Incident Categories (28 Types)

1. `cpu_saturation`
2. `memory_exhaustion`
3. `disk_exhaustion`
4. `network_latency`
5. `packet_loss`
6. `database_connection_exhaustion`
7. `database_slow_queries`
8. `database_outage`
9. `redis_failure`
10. `kafka_broker_failure`
11. `message_queue_backlog`
12. `service_crash`
13. `container_restart_loop`
14. `kubernetes_pod_failure`
15. `kubernetes_node_failure`
16. `deployment_bug`
17. `configuration_error`
18. `authentication_failure`
19. `dns_failure`
20. `load_balancer_failure`
21. `api_rate_limiting`
22. `dependency_timeout`
23. `memory_leak`
24. `traffic_spike`
25. `deadlock`
26. `storage_failure`
27. `certificate_expiration`
28. `external_api_failure`

---

## 5. Machine Learning Task Readiness

### Task 1: Anomaly Detection
- **Input**: `data/raw/metrics.csv`
- **Target**: `is_anomaly` (in `data/ground_truth/anomaly_labels.csv` or `data/processed/anomaly_detection.csv`)
- **Model Compatibility**: Isolation Forest, Autoencoders, LSTM/Transformer Time-Series Anomaly Detectors.

### Task 2: Incident Alert Correlation
- **Input**: Pairwise alert features in `data/processed/incident_correlation.csv` (`time_difference_seconds`, `same_service`, `dependency_exists`, `topological_distance`, `semantic_similarity`)
- **Target**: `same_incident` (1 = belongs to same incident, 0 = distinct/unrelated alert)
- **Model Compatibility**: XGBoost, LightGBM, Pairwise Siamese Networks.

### Task 3: Root Cause Classification & Multi-Signal Ranking
- **Input**: Candidate node evidence vectors in `data/processed/root_cause_candidates.csv` (`temporal_score`, `severity_score`, `topology_score`, `metric_anomaly_score`, `log_evidence_score`, `trace_evidence_score`)
- **Target**: `is_root_cause` (1 = true root cause, 0 = downstream affected node)
- **Model Compatibility**: RankNet, LambdaMART, Multi-Modal Fusion Networks.

### Task 4: Failure Propagation Path Prediction
- **Input**: Directed node pairs in `data/processed/propagation.csv` (`source_node_id`, `target_node_id`, `dependency_type`, `propagation_delay_seconds`)
- **Target**: `is_propagated` (1 = failure propagated across dependency edge, 0 = unpropagated)
- **Model Compatibility**: Temporal Graph Neural Networks (T-GNN), GraphSAGE, GAT.

### Task 5: Self-Healing Remediation Recommendation
- **Input**: Root cause type, service metadata, blast radius, risk level in `data/processed/remediation.csv`
- **Target**: `recommended_action` (`scale_out_service`, `restart_container`, `increase_connection_pool`, `rollback_deployment`)
- **Model Compatibility**: Reinforcement Learning (DQN, PPO), Multi-Class Classification.

### Task 6: Graph Neural Network (GNN) Root Cause Localization
- **Input**: Scenario graphs in `data/graph/graphs.json` and node/edge attributes in `data/graph/nodes.csv` & `data/graph/edges.csv`
- **Model Compatibility**: PyTorch Geometric (`torch_geometric`), DGL, NetworkX.

---

## 6. How to Run Generator & Validation

### Installation
```bash
pip install -r requirements.txt
```

### 1. Generate 1,000 Scenarios (Default Seed 42)
```bash
python generate_dataset.py --seed 42 --scenarios 1000 --num-workers 4
```

### 2. Generate Custom Seed Dataset
```bash
python generate_dataset.py --seed 123 --scenarios 5000 --output-dir custom_data/
```

### 3. Run Anti-Leakage & Data Integrity Validator
```bash
python validate_dataset.py --data-dir data/
```

---

## 7. Importing Graphs into Neo4j

To import generated topology graphs into Neo4j Graph Database:

```cypher
// Import Nodes
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
CREATE (n:Node {
  id: row.node_id,
  type: row.node_type,
  service: row.service_name,
  scenario_id: row.scenario_id,
  topology_id: row.topology_id,
  criticality: row.criticality
});

// Import Edges
LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS row
MATCH (a:Node {id: row.source, scenario_id: row.scenario_id})
MATCH (b:Node {id: row.target, scenario_id: row.scenario_id})
CREATE (a)-[r:DEPENDS_ON {
  type: row.dependency_type,
  latency: toFloat(row.latency)
}]->(b);
```

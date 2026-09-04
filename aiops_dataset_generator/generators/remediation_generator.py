import random
from typing import Dict, List, Any, Tuple
import numpy as np

REMEDIATION_MAP = {
    "cpu_saturation": [
        ("scale_out_service", 0.92, 180, "low", False, True, True),
        ("restart_container", 0.65, 60, "medium", False, True, False),
        ("increase_cpu_limit", 0.85, 300, "medium", True, True, True)
    ],
    "memory_exhaustion": [
        ("restart_service", 0.95, 90, "low", False, True, False),
        ("increase_memory", 0.88, 300, "medium", True, True, True),
        ("rollback_deployment", 0.90, 240, "high", True, True, True)
    ],
    "memory_leak": [
        ("restart_service", 0.98, 90, "low", False, True, False),
        ("rollback_deployment", 0.92, 240, "high", True, True, True),
        ("increase_memory", 0.50, 300, "medium", True, True, True)
    ],
    "database_connection_exhaustion": [
        ("increase_connection_pool", 0.94, 120, "medium", True, True, True),
        ("restart_application", 0.70, 90, "medium", False, True, False),
        ("scale_database", 0.89, 600, "high", True, True, True)
    ],
    "kafka_broker_failure": [
        ("scale_brokers", 0.90, 400, "high", True, True, True),
        ("increase_consumers", 0.80, 150, "medium", False, True, True),
        ("restart_consumer", 0.60, 60, "low", False, True, False)
    ],
    "deployment_bug": [
        ("rollback_deployment", 0.99, 180, "high", True, True, True),
        ("restart_service", 0.20, 60, "low", False, True, False),
        ("scale_out_service", 0.30, 180, "low", False, True, True)
    ]
}

DEFAULT_ACTIONS = [
    ("restart_container", 0.85, 90, "low", False, True, False),
    ("scale_out_service", 0.80, 180, "low", False, True, True),
    ("rollback_deployment", 0.75, 240, "high", True, True, True)
]

class RemediationGenerator:
    """
    Synthesizes recommended remediation actions, alternative candidate actions,
    recovery times, risk levels, and safety allowlist labels.
    """
    def __init__(self, py_rng: random.Random, np_rng: np.random.Generator):
        self.py_rng = py_rng
        self.np_rng = np_rng

    def generate_remediation(
        self,
        scenario_id: str,
        incidents: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Returns:
          (remediation_ground_truth_labels, remediation_processed_records)
        """
        gt_labels = []
        processed_records = []

        for inc in incidents:
            rc_type = inc["root_cause_type"]
            target_node = inc["root_cause_node"]
            inc_id = inc["incident_id"]

            actions_pool = REMEDIATION_MAP.get(rc_type, DEFAULT_ACTIONS)

            # Best action
            primary = actions_pool[0]
            alts = [a[0] for a in actions_pool[1:]]

            rec_action, prob, rec_time, risk, human_app, allowlist, rollback = primary

            gt_labels.append({
                "scenario_id": scenario_id,
                "incident_id": inc_id,
                "root_cause_type": rc_type,
                "target_node": target_node,
                "recommended_action": rec_action,
                "alternative_actions": "|".join(alts),
                "action_success_probability": prob,
                "estimated_recovery_time": rec_time,
                "risk_level": risk,
                "requires_human_approval": human_app,
                "is_allowlisted": allowlist,
                "rollback_available": rollback
            })

            processed_records.append({
                "scenario_id": scenario_id,
                "incident_id": inc_id,
                "root_cause_type": rc_type,
                "target_node": target_node,
                "recommended_action": rec_action,
                "alternative_actions": "|".join(alts),
                "action_success_probability": prob,
                "estimated_recovery_time": rec_time,
                "risk_level": risk,
                "requires_human_approval": human_app,
                "is_allowlisted": allowlist,
                "rollback_available": rollback
            })

        return gt_labels, processed_records

import random
import numpy as np
from typing import Generator, List, Any

class SeedManager:
    """
    Manages deterministic random seeds per scenario to guarantee exact output reproducibility
    even when running across multiple parallel worker processes.
    """
    def __init__(self, global_seed: int = 42):
        self.global_seed = global_seed

    def get_scenario_seed(self, scenario_id: int) -> int:
        # Use prime multiplier to prevent seed overlap across scenario indices
        return (self.global_seed + (scenario_id * 10007)) & 0x7FFFFFFF

    def get_scenario_rng(self, scenario_id: int) -> tuple[random.Random, np.random.Generator]:
        seed = self.get_scenario_seed(scenario_id)
        py_rng = random.Random(seed)
        np_rng = np.random.default_rng(seed)
        return py_rng, np_rng


def get_rng(seed: int) -> tuple[random.Random, np.random.Generator]:
    py_rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    return py_rng, np_rng


def sample_noise(np_rng: np.random.Generator, loc: float = 0.0, scale: float = 1.0) -> float:
    return float(np_rng.normal(loc, scale))


def sample_weibull_delay(np_rng: np.random.Generator, a: float = 1.5, scale: float = 10.0) -> float:
    """
    Samples realistic causal propagation delay in seconds using a Weibull distribution.
    """
    return float(np_rng.weibull(a) * scale)

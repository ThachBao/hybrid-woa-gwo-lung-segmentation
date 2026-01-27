# interface chung cho mọi optimizer + utils lịch sử
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Dict, Optional, Tuple
import numpy as np

FitnessFn = Callable[[np.ndarray], float]


@dataclass
class OptimizerBase:
    n_agents: int = 30
    n_iters: int = 50
    seed: Optional[int] = None

    def _rng(self) -> np.random.Generator:
        return np.random.default_rng(self.seed)

    def optimize(
        self,
        fitness_fn: FitnessFn,
        *,
        dim: int,
        lb: float | np.ndarray,
        ub: float | np.ndarray,
        repair_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None,
        init_pop: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, float, List[Dict]]:
        raise NotImplementedError

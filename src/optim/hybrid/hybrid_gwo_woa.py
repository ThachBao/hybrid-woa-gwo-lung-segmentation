from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple
import numpy as np

from src.optim.base import OptimizerBase, FitnessFn
from src.optim.hybrid import optimize_pa1, optimize_pa2, optimize_pa3, optimize_pa4, optimize_pa5, optimize_pa6


_STRATEGY = {
    "PA1": optimize_pa1,
    "PA2": optimize_pa2,
    "PA3": optimize_pa3,
    "PA4": optimize_pa4,
    "PA5": optimize_pa5,
    "PA6": optimize_pa6,
}


class HybridGWO_WOA(OptimizerBase):
    def __init__(
        self,
        n_agents: int = 30,
        n_iters: int = 50,
        seed: int | None = None,
        strategy: str = "PA1",
        woa_b: float = 1.0,
        share_interval: int = 10,  # chá»‰ dÃ¹ng cho PA5
    ):
        super().__init__(n_agents=n_agents, n_iters=n_iters, seed=seed)
        self.strategy = str(strategy).upper()
        self.woa_b = float(woa_b)
        requested_share_interval = int(share_interval)
        # PA5 is defined and benchmarked with periodic sharing every 10 iterations.
        self.share_interval = 10 if self.strategy == "PA5" else requested_share_interval

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
        if self.strategy not in _STRATEGY:
            raise ValueError(f"strategy pháº£i thuá»™c {list(_STRATEGY.keys())}")

        fn = _STRATEGY[self.strategy]
        return fn(
            fitness_fn,
            dim=dim,
            lb=lb,
            ub=ub,
            n_agents=self.n_agents,
            n_iters=self.n_iters,
            seed=self.seed,
            repair_fn=repair_fn,
            init_pop=init_pop,
            woa_b=self.woa_b,
            share_interval=self.share_interval,
        )

# Whale Optimization Algorithm
from __future__ import annotations

from typing import Callable, List, Dict, Optional, Tuple
import numpy as np

from .base import OptimizerBase, FitnessFn
from .bounds import as_bounds, clamp


class WOA(OptimizerBase):
    """
    Whale Optimization Algorithm (WOA):
    - D = |C*X* - X| ; X(t+1)= X* - A*D  (p<0.5, |A|<1)
    - X(t+1)= X_rand - A*D              (p<0.5, |A|>=1)
    - X(t+1)= D' * exp(b*l) * cos(2*pi*l) + X*   (p>=0.5)
    - A = 2*a*r - a ; C = 2*r ; a giảm tuyến tính 2 -> 0
    Ghi chú: điều kiện |A|<1 trong không gian vector có nhiều cách diễn giải;
    ở đây dùng max(|A|) < 1 để quyết định khai thác.
    """

    def __init__(self, n_agents: int = 30, n_iters: int = 50, seed: Optional[int] = None, b: float = 1.0):
        super().__init__(n_agents=n_agents, n_iters=n_iters, seed=seed)
        self.b = float(b)

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
        rng = self._rng()
        lb_arr, ub_arr = as_bounds(lb, ub, dim)

        if self.n_agents < 2:
            raise ValueError("n_agents phải >= 2.")

        if init_pop is None:
            pop = rng.uniform(lb_arr, ub_arr, size=(self.n_agents, dim))
        else:
            pop = np.asarray(init_pop, dtype=float).copy()
            if pop.shape != (self.n_agents, dim):
                raise ValueError("init_pop phải có shape (n_agents, dim).")

        def _repair_row(x: np.ndarray) -> np.ndarray:
            x = clamp(x, lb_arr, ub_arr)
            if repair_fn is not None:
                x = repair_fn(x)
            return x

        pop = np.vstack([_repair_row(pop[i]) for i in range(self.n_agents)])
        fitness = np.array([float(fitness_fn(pop[i])) for i in range(self.n_agents)], dtype=float)

        best_idx = int(np.argmin(fitness))
        best_x = pop[best_idx].copy()
        best_f = float(fitness[best_idx])

        history: List[Dict] = []

        for t in range(self.n_iters):
            if self.n_iters <= 1:
                a = 0.0
            else:
                a = 2.0 - 2.0 * (t / (self.n_iters - 1))

            for i in range(self.n_agents):
                x = pop[i]

                r1 = float(rng.random())
                r2 = float(rng.random())
                A = 2.0 * a * r1 - a
                C = 2.0 * r2

                p = rng.random()

                if p < 0.5:
                    # khai thác nếu |A|<1, thăm dò nếu |A|>=1
                    if abs(A) < 1.0:
                        D = np.abs(C * best_x - x)
                        x_new = best_x - A * D
                    else:
                        rand_idx = int(rng.integers(0, self.n_agents))
                        X_rand = pop[rand_idx]
                        D = np.abs(C * X_rand - x)
                        x_new = X_rand - A * D
                else:
                    D_prime = np.abs(best_x - x)
                    l = float(rng.uniform(-1.0, 1.0))
                    x_new = D_prime * np.exp(self.b * l) * np.cos(2.0 * np.pi * l) + best_x

                pop[i] = _repair_row(x_new)

            fitness = np.array([float(fitness_fn(pop[i])) for i in range(self.n_agents)], dtype=float)
            curr_best_idx = int(np.argmin(fitness))
            curr_best_f = float(fitness[curr_best_idx])
            if curr_best_f < best_f:
                best_f = curr_best_f
                best_x = pop[curr_best_idx].copy()

            history.append(
                {
                    "iter": t,
                    "best_f": float(best_f),
                    "best_x": best_x.copy(),
                    "mean_f": float(np.mean(fitness)),
                }
            )

        return best_x, float(best_f), history

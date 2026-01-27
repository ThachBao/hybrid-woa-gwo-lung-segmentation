# Grey Wolf Optimizer
from __future__ import annotations

from typing import Callable, List, Dict, Optional, Tuple
import numpy as np

from .base import OptimizerBase, FitnessFn
from .bounds import as_bounds, clamp


class GWO(OptimizerBase):
    """
    Grey Wolf Optimizer (GWO):
    - A = 2*a*r1 - a
    - C = 2*r2
    - D = |C*X_leader - X|
    - X_leader_component = X_leader - A*D
    - X_new = (X1 + X2 + X3)/3
    - a giảm tuyến tính từ 2 -> 0
    """

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
            raise ValueError("n_agents phải >= 2 (khuyến nghị >= 4).")

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

        history: List[Dict] = []

        def _leaders(pop_: np.ndarray, fit_: np.ndarray):
            idx = np.argsort(fit_)  # minimize
            alpha = pop_[idx[0]].copy()
            alpha_f = float(fit_[idx[0]])
            beta = pop_[idx[1]].copy() if idx.size > 1 else alpha.copy()
            delta = pop_[idx[2]].copy() if idx.size > 2 else beta.copy()
            return alpha, beta, delta, alpha_f

        alpha, beta, delta, best_f = _leaders(pop, fitness)
        best_x = alpha.copy()

        for t in range(self.n_iters):
            if self.n_iters <= 1:
                a = 0.0
            else:
                a = 2.0 - 2.0 * (t / (self.n_iters - 1))

            new_pop = np.empty_like(pop)

            for i in range(self.n_agents):
                x = pop[i]

                def _component(leader: np.ndarray) -> np.ndarray:
                    r1 = rng.random(dim)
                    r2 = rng.random(dim)
                    A = 2.0 * a * r1 - a
                    C = 2.0 * r2
                    D = np.abs(C * leader - x)
                    return leader - A * D

                X1 = _component(alpha)
                X2 = _component(beta)
                X3 = _component(delta)
                x_new = (X1 + X2 + X3) / 3.0

                x_new = _repair_row(x_new)
                new_pop[i] = x_new

            pop = new_pop
            fitness = np.array([float(fitness_fn(pop[i])) for i in range(self.n_agents)], dtype=float)

            alpha, beta, delta, alpha_f = _leaders(pop, fitness)
            if alpha_f < best_f:
                best_f = alpha_f
                best_x = alpha.copy()

            history.append(
                {
                    "iter": t,
                    "best_f": float(best_f),
                    "best_x": best_x.copy(),
                    "mean_f": float(np.mean(fitness)),
                }
            )

        return best_x, float(best_f), history

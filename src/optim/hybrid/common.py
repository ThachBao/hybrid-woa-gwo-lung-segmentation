from __future__ import annotations

from typing import Callable, Optional, Tuple
import numpy as np
from src.optim.bounds import as_bounds, clamp

FitnessFn = Callable[[np.ndarray], float]


def make_repair_row(
    lb_arr: np.ndarray,
    ub_arr: np.ndarray,
    repair_fn: Optional[Callable[[np.ndarray], np.ndarray]],
):
    def _repair_row(x: np.ndarray) -> np.ndarray:
        x = clamp(x, lb_arr, ub_arr)
        if repair_fn is not None:
            x = repair_fn(x)
        return x
    return _repair_row


def init_population(rng: np.random.Generator, n_agents: int, dim: int, lb_arr: np.ndarray, ub_arr: np.ndarray, repair_row):
    pop = rng.uniform(lb_arr, ub_arr, size=(n_agents, dim))
    return np.vstack([repair_row(pop[i]) for i in range(n_agents)])


def eval_pop(fitness_fn: FitnessFn, pop: np.ndarray) -> np.ndarray:
    return np.array([float(fitness_fn(pop[i])) for i in range(pop.shape[0])], dtype=float)


def best_of(pop: np.ndarray, fit: np.ndarray) -> Tuple[np.ndarray, float, int]:
    idx = int(np.argmin(fit))
    return pop[idx].copy(), float(fit[idx]), idx


def gwo_step(rng: np.random.Generator, pop: np.ndarray, fit: np.ndarray, a: float, repair_row) -> np.ndarray:
    dim = pop.shape[1]
    idx = np.argsort(fit)
    alpha = pop[idx[0]]
    beta = pop[idx[1]] if idx.size > 1 else alpha
    delta = pop[idx[2]] if idx.size > 2 else beta

    new_pop = np.empty_like(pop)
    for i in range(pop.shape[0]):
        x = pop[i]

        def _comp(leader: np.ndarray) -> np.ndarray:
            r1 = rng.random(dim)
            r2 = rng.random(dim)
            A = 2.0 * a * r1 - a
            C = 2.0 * r2
            D = np.abs(C * leader - x)
            return leader - A * D

        X1 = _comp(alpha)
        X2 = _comp(beta)
        X3 = _comp(delta)
        new_pop[i] = repair_row((X1 + X2 + X3) / 3.0)

    return new_pop


def woa_step(rng: np.random.Generator, pop: np.ndarray, fit: np.ndarray, best_x: np.ndarray, a: float, b: float, repair_row) -> np.ndarray:
    dim = pop.shape[1]
    new_pop = pop.copy()

    for i in range(pop.shape[0]):
        x = pop[i]
        r1 = rng.random(dim)
        r2 = rng.random(dim)
        A = 2.0 * a * r1 - a
        C = 2.0 * r2
        p = rng.random()

        if p < 0.5:
            if float(np.max(np.abs(A))) < 1.0:
                D = np.abs(C * best_x - x)
                x_new = best_x - A * D
            else:
                ridx = int(rng.integers(0, pop.shape[0]))
                X_rand = pop[ridx]
                D = np.abs(C * X_rand - x)
                x_new = X_rand - A * D
        else:
            Dp = np.abs(best_x - x)
            l = float(rng.uniform(-1.0, 1.0))
            x_new = Dp * np.exp(b * l) * np.cos(2.0 * np.pi * l) + best_x

        new_pop[i] = repair_row(x_new)

    return new_pop

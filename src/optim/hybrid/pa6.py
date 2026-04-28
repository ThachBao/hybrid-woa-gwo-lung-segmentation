from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from .common import FitnessFn, as_bounds, best_of, eval_pop, init_population, make_repair_row


def _compute_woa_A(rng: np.random.Generator, a: float, n_agents: int, dim: int) -> np.ndarray:
    r1 = rng.random((n_agents, dim))
    return 2.0 * a * r1 - a


def _woa_update(
    rng: np.random.Generator,
    pop: np.ndarray,
    best_x: np.ndarray,
    A: np.ndarray,
    b: float,
    repair_row,
) -> np.ndarray:
    n_agents, dim = pop.shape
    new_pop = np.empty_like(pop)

    for i in range(n_agents):
        x = pop[i]
        A_i = A[i]
        C_i = 2.0 * rng.random(dim)
        p = float(rng.random())

        if p < 0.5:
            if np.mean(np.abs(A_i)) < 1.0:
                D = np.abs(C_i * best_x - x)
                x_new = best_x - A_i * D
            else:
                ridx = int(rng.integers(0, n_agents))
                x_rand = pop[ridx]
                D = np.abs(C_i * x_rand - x)
                x_new = x_rand - A_i * D
        else:
            D_prime = np.abs(best_x - x)
            l = float(rng.uniform(-1.0, 1.0))
            x_new = D_prime * np.exp(b * l) * np.cos(2.0 * np.pi * l) + best_x

        new_pop[i] = repair_row(x_new)

    return new_pop


def _gwo_update(rng: np.random.Generator, pop: np.ndarray, fit: np.ndarray, a: float, repair_row) -> np.ndarray:
    n_agents, dim = pop.shape
    idx = np.argsort(fit)
    alpha = pop[idx[0]]
    beta = pop[idx[1]] if idx.size > 1 else alpha
    delta = pop[idx[2]] if idx.size > 2 else beta

    new_pop = np.empty_like(pop)
    for i in range(n_agents):
        x = pop[i]

        def _component(leader: np.ndarray) -> np.ndarray:
            r1 = rng.random(dim)
            r2 = rng.random(dim)
            A = 2.0 * a * r1 - a
            C = 2.0 * r2
            D = np.abs(C * leader - x)
            return leader - A * D

        x_new = (_component(alpha) + _component(beta) + _component(delta)) / 3.0
        new_pop[i] = repair_row(x_new)

    return new_pop


def optimize_pa6(
    fitness_fn: FitnessFn,
    *,
    dim: int,
    lb: float | np.ndarray,
    ub: float | np.ndarray,
    n_agents: int,
    n_iters: int,
    seed: int | None,
    repair_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    init_pop: Optional[np.ndarray] = None,
    woa_b: float = 1.0,
    share_interval: int = 1,
    stagnation_limit: int = 10,
    recovery_rounds: int = 3,
    switch_threshold: float = 1.0,
    reinit_frac: float = 0.2,
    local_refine_delta: int = 2,
    local_refine_rounds: int = 3,
) -> Tuple[np.ndarray, float, List[Dict]]:
    del share_interval, reinit_frac, local_refine_delta, local_refine_rounds

    rng = np.random.default_rng(seed)
    lb_arr, ub_arr = as_bounds(lb, ub, dim)
    repair_row = make_repair_row(lb_arr, ub_arr, repair_fn)

    patience = max(1, int(stagnation_limit))
    recovery_window = max(1, int(recovery_rounds))
    explore_threshold = float(switch_threshold)

    if init_pop is None:
        pop = init_population(rng, n_agents, dim, lb_arr, ub_arr, repair_row)
    else:
        pop = np.asarray(init_pop, dtype=float).copy()
        if pop.shape != (n_agents, dim):
            raise ValueError("init_pop phải có shape (n_agents, dim).")
        pop = np.vstack([repair_row(pop[i]) for i in range(n_agents)])

    fit = eval_pop(fitness_fn, pop)
    best_x, best_f, _ = best_of(pop, fit)
    history: List[Dict] = []

    stagnation_count = 0
    forced_woa_rounds = 0

    for t in range(n_iters):
        a = 0.0 if n_iters <= 1 else 2.0 - 2.0 * (t / (n_iters - 1))
        A = _compute_woa_A(rng, a, n_agents, dim)
        mean_abs_A = float(np.mean(np.abs(A)))

        if forced_woa_rounds > 0:
            phase = "WOA-RECOVERY"
            pop = _woa_update(rng, pop, best_x, A, woa_b, repair_row)
            forced_woa_rounds -= 1
        elif mean_abs_A >= explore_threshold:
            phase = "WOA-EXPLORATION"
            pop = _woa_update(rng, pop, best_x, A, woa_b, repair_row)
        else:
            phase = "GWO-EXPLOITATION"
            pop = _gwo_update(rng, pop, fit, a, repair_row)

        pop = np.vstack([repair_row(pop[i]) for i in range(n_agents)])
        fit = eval_pop(fitness_fn, pop)
        curr_best_x, curr_best_f, _ = best_of(pop, fit)

        if curr_best_f < best_f - 1e-12:
            best_x = curr_best_x.copy()
            best_f = float(curr_best_f)
            stagnation_count = 0
        else:
            stagnation_count += 1
            if stagnation_count >= patience:
                forced_woa_rounds = recovery_window
                stagnation_count = 0

        history.append(
            {
                "iter": t,
                "best_f": float(best_f),
                "best_x": best_x.copy(),
                "mean_f": float(np.mean(fit)),
                "phase": phase,
                "a": float(a),
                "mean_abs_A": mean_abs_A,
                "forced_woa_rounds": int(forced_woa_rounds),
            }
        )

    return best_x, float(best_f), history

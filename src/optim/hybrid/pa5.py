from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from .common import (
    FitnessFn,
    as_bounds,
    best_of,
    eval_pop,
    gwo_step,
    init_population,
    make_repair_row,
    woa_step,
)


def _parallelize_init_from_base(
    base: np.ndarray,
    rng: np.random.Generator,
    lb_arr: np.ndarray,
    ub_arr: np.ndarray,
    repair_row,
    n_agents_gwo: int,
    n_agents_woa: int,
) -> Tuple[np.ndarray, np.ndarray]:
    span = np.maximum(ub_arr - lb_arr, 1e-12)
    noise_gwo = rng.normal(loc=0.0, scale=0.015, size=(n_agents_gwo, base.shape[1])) * span
    noise_woa = rng.normal(loc=0.0, scale=0.015, size=(n_agents_woa, base.shape[1])) * span
    perm_gwo = rng.permutation(base.shape[0])[:n_agents_gwo]
    perm_woa = rng.permutation(base.shape[0])[:n_agents_woa]

    pop_gwo = np.vstack([repair_row(base[perm_gwo[i]] + noise_gwo[i]) for i in range(n_agents_gwo)])
    pop_woa = np.vstack([repair_row(base[perm_woa[i]] + noise_woa[i]) for i in range(n_agents_woa)])
    return pop_gwo, pop_woa


def _refine_thresholds_local(
    best_x: np.ndarray,
    fitness_fn: FitnessFn,
    repair_row,
    *,
    deltas: Tuple[int, ...] = (2, 1),
    passes_per_delta: int = 1,
) -> Tuple[np.ndarray, float]:
    current_x = repair_row(np.asarray(best_x, dtype=float))
    current_f = float(fitness_fn(current_x))

    for delta in deltas:
        for _ in range(max(1, int(passes_per_delta))):
            changed = False
            for idx in range(current_x.size):
                candidate_best_x = current_x
                candidate_best_f = current_f
                for step in (-delta, delta):
                    cand_x = current_x.copy()
                    cand_x[idx] = cand_x[idx] + step
                    cand_x = repair_row(cand_x)
                    cand_f = float(fitness_fn(cand_x))
                    if cand_f < candidate_best_f - 1e-12:
                        candidate_best_x = cand_x
                        candidate_best_f = cand_f
                if candidate_best_f < current_f - 1e-12:
                    current_x = candidate_best_x
                    current_f = candidate_best_f
                    changed = True
            if not changed:
                break

    return current_x, float(current_f)


def optimize_pa5(
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
    share_interval: int = 10,
    stagnation_patience: int = 3,
    min_share_gap: int = 2,
) -> Tuple[np.ndarray, float, List[Dict]]:
    """
    PA5 = parallel co-evolution.
    - `n_agents` là số agent cho mỗi nhánh GWO/WOA.
    - Tổng số agent nội bộ = 2 * `n_agents`.
    - Share định kỳ mỗi `share_interval` vòng.
    - Nếu bị stagnation đủ lâu thì share sớm hơn.
    """
    if share_interval <= 0:
        raise ValueError("share_interval phải >= 1")
    if n_agents < 1:
        raise ValueError("n_agents phải >= 1 cho mỗi population của PA5.")
    if stagnation_patience <= 0:
        raise ValueError("stagnation_patience phải >= 1")
    if min_share_gap < 0:
        raise ValueError("min_share_gap phải >= 0")

    rng = np.random.default_rng(seed)
    lb_arr, ub_arr = as_bounds(lb, ub, dim)
    repair_row = make_repair_row(lb_arr, ub_arr, repair_fn)

    n_agents_gwo = int(n_agents)
    n_agents_woa = int(n_agents)

    if init_pop is None:
        pop_gwo = init_population(rng, n_agents_gwo, dim, lb_arr, ub_arr, repair_row)
        pop_woa = init_population(rng, n_agents_woa, dim, lb_arr, ub_arr, repair_row)
    else:
        base = np.asarray(init_pop, dtype=float).copy()
        if base.shape != (n_agents, dim):
            raise ValueError("init_pop phải có shape (n_agents, dim).")
        base = np.vstack([repair_row(base[i]) for i in range(n_agents)])
        pop_gwo, pop_woa = _parallelize_init_from_base(
            base, rng, lb_arr, ub_arr, repair_row, n_agents_gwo, n_agents_woa
        )

    fit_gwo = eval_pop(fitness_fn, pop_gwo)
    fit_woa = eval_pop(fitness_fn, pop_woa)

    best_x_gwo, best_f_gwo, _ = best_of(pop_gwo, fit_gwo)
    best_x_woa, best_f_woa, _ = best_of(pop_woa, fit_woa)

    if best_f_gwo <= best_f_woa:
        best_x, best_f = best_x_gwo.copy(), float(best_f_gwo)
    else:
        best_x, best_f = best_x_woa.copy(), float(best_f_woa)

    history: List[Dict] = []
    stagnation_counter = 0
    last_share_iter = -share_interval

    for t in range(n_iters):
        a = 0.0 if n_iters <= 1 else 2.0 - 2.0 * (t / (n_iters - 1))

        pop_gwo = gwo_step(rng, pop_gwo, fit_gwo, a, repair_row)
        fit_gwo = eval_pop(fitness_fn, pop_gwo)
        best_x_gwo, best_f_gwo, _ = best_of(pop_gwo, fit_gwo)

        pop_woa = woa_step(rng, pop_woa, fit_woa, best_x_woa, a, woa_b, repair_row)
        fit_woa = eval_pop(fitness_fn, pop_woa)
        best_x_woa, best_f_woa, _ = best_of(pop_woa, fit_woa)

        improved = False
        if best_f_gwo < best_f:
            best_f = float(best_f_gwo)
            best_x = best_x_gwo.copy()
            improved = True
        if best_f_woa < best_f:
            best_f = float(best_f_woa)
            best_x = best_x_woa.copy()
            improved = True

        if improved:
            stagnation_counter = 0
        else:
            stagnation_counter += 1

        periodic_share = (t + 1) % share_interval == 0
        early_share = (
            stagnation_counter >= stagnation_patience
            and (t - last_share_iter) >= min_share_gap
        )
        share_now = periodic_share or early_share
        share_reason = "periodic" if periodic_share else ("stagnation" if early_share else None)

        if share_now:
            worst_gwo = int(np.argmax(fit_gwo))
            worst_woa = int(np.argmax(fit_woa))

            pop_gwo[worst_gwo] = best_x_woa.copy()
            fit_gwo[worst_gwo] = float(fitness_fn(pop_gwo[worst_gwo]))

            pop_woa[worst_woa] = best_x_gwo.copy()
            fit_woa[worst_woa] = float(fitness_fn(pop_woa[worst_woa]))

            best_x_gwo, best_f_gwo, _ = best_of(pop_gwo, fit_gwo)
            best_x_woa, best_f_woa, _ = best_of(pop_woa, fit_woa)

            last_share_iter = t
            stagnation_counter = 0

            if best_f_gwo < best_f:
                best_f = float(best_f_gwo)
                best_x = best_x_gwo.copy()
            if best_f_woa < best_f:
                best_f = float(best_f_woa)
                best_x = best_x_woa.copy()

        history.append(
            {
                "iter": t,
                "best_f": float(best_f),
                "best_x": best_x.copy(),
                "mean_f": float((np.sum(fit_gwo) + np.sum(fit_woa)) / float(n_agents_gwo + n_agents_woa)),
                "phase": "parallel_co_evolution",
                "shared": bool(share_now),
                "share_reason": share_reason,
                "stagnation_counter": int(stagnation_counter),
            }
        )

    refined_x, refined_f = _refine_thresholds_local(
        best_x,
        fitness_fn,
        repair_row,
        deltas=(4, 2, 1),
        passes_per_delta=3,
    )
    if refined_f < best_f - 1e-12:
        best_x = refined_x
        best_f = float(refined_f)
        if history:
            history[-1]["best_f"] = best_f
            history[-1]["best_x"] = best_x.copy()

    return best_x, float(best_f), history

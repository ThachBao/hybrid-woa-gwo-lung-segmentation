from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple
import numpy as np

from .common import (
    FitnessFn,
    as_bounds,
    make_repair_row,
    init_population,
    eval_pop,
    best_of,
    gwo_step,
    woa_step,
)


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
    share_interval: int = 1,
) -> Tuple[np.ndarray, float, List[Dict]]:
    """
    PA5: Parallel with Information Sharing
    - duy trì 2 quần thể: pop_gwo và pop_woa
    - mỗi vòng: pop_gwo chạy 1 step GWO, pop_woa chạy 1 step WOA
    - mỗi share_interval: thay cá thể tệ nhất của quần thể này bằng best của quần thể kia
    """
    if share_interval <= 0:
        raise ValueError("share_interval phải >= 1")

    rng = np.random.default_rng(seed)
    lb_arr, ub_arr = as_bounds(lb, ub, dim)
    repair_row = make_repair_row(lb_arr, ub_arr, repair_fn)

    if init_pop is None:
        pop_gwo = init_population(rng, n_agents, dim, lb_arr, ub_arr, repair_row)
        pop_woa = init_population(rng, n_agents, dim, lb_arr, ub_arr, repair_row)
    else:
        base = np.asarray(init_pop, dtype=float).copy()
        if base.shape != (n_agents, dim):
            raise ValueError("init_pop phải có shape (n_agents, dim).")
        base = np.vstack([repair_row(base[i]) for i in range(n_agents)])
        pop_gwo = base.copy()
        pop_woa = base.copy()

    fit_gwo = eval_pop(fitness_fn, pop_gwo)
    fit_woa = eval_pop(fitness_fn, pop_woa)

    best_x_gwo, best_f_gwo, _ = best_of(pop_gwo, fit_gwo)
    best_x_woa, best_f_woa, _ = best_of(pop_woa, fit_woa)

    if best_f_gwo <= best_f_woa:
        best_x, best_f = best_x_gwo.copy(), float(best_f_gwo)
    else:
        best_x, best_f = best_x_woa.copy(), float(best_f_woa)

    history: List[Dict] = []

    for t in range(n_iters):
        a = 0.0 if n_iters <= 1 else 2.0 - 2.0 * (t / (n_iters - 1))

        # step GWO
        pop_gwo = gwo_step(rng, pop_gwo, fit_gwo, a, repair_row)
        fit_gwo = eval_pop(fitness_fn, pop_gwo)
        best_x_gwo, best_f_gwo, _ = best_of(pop_gwo, fit_gwo)

        # step WOA (dùng best hiện tại của quần thể WOA)
        pop_woa = woa_step(rng, pop_woa, fit_woa, best_x_woa, a, woa_b, repair_row)
        fit_woa = eval_pop(fitness_fn, pop_woa)
        best_x_woa, best_f_woa, _ = best_of(pop_woa, fit_woa)

        # trao đổi best
        if t % share_interval == 0:
            worst_gwo = int(np.argmax(fit_gwo))
            worst_woa = int(np.argmax(fit_woa))

            pop_gwo[worst_gwo] = best_x_woa.copy()
            fit_gwo[worst_gwo] = float(fitness_fn(pop_gwo[worst_gwo]))
            pop_woa[worst_woa] = best_x_gwo.copy()
            fit_woa[worst_woa] = float(fitness_fn(pop_woa[worst_woa]))

            best_x_gwo, best_f_gwo, _ = best_of(pop_gwo, fit_gwo)
            best_x_woa, best_f_woa, _ = best_of(pop_woa, fit_woa)

        # best toàn cục
        if best_f_gwo < best_f:
            best_f = float(best_f_gwo)
            best_x = best_x_gwo.copy()
        if best_f_woa < best_f:
            best_f = float(best_f_woa)
            best_x = best_x_woa.copy()

        mean_f = float((np.mean(fit_gwo) + np.mean(fit_woa)) / 2.0)
        history.append({"iter": t, "best_f": best_f, "best_x": best_x.copy(), "mean_f": mean_f})

    return best_x, float(best_f), history

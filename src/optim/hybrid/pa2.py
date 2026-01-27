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


def optimize_pa2(
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
    share_interval: int = 1,  # không dùng trong PA2
) -> Tuple[np.ndarray, float, List[Dict]]:
    """
    PA2: Sequential Reverse (WOA -> GWO)
    - WOA chạy nửa đầu (T1 iterations)
    - Chuyển TOÀN BỘ quần thể từ WOA sang GWO
    - GWO chạy nửa sau (T2 iterations) với quần thể từ WOA
    - Tham số 'a' được reset về 2 khi bắt đầu phase 2
    """
    rng = np.random.default_rng(seed)
    lb_arr, ub_arr = as_bounds(lb, ub, dim)
    repair_row = make_repair_row(lb_arr, ub_arr, repair_fn)

    T1 = n_iters // 2
    T2 = n_iters - T1

    # Khởi tạo quần thể ban đầu
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

    # Phase 1: WOA
    for t in range(T1):
        # Tham số a giảm theo T1, không phải n_iters
        a = 0.0 if T1 <= 1 else 2.0 - 2.0 * (t / (T1 - 1))
        pop = woa_step(rng, pop, fit, best_x, a, woa_b, repair_row)
        fit = eval_pop(fitness_fn, pop)
        bx, bf, _ = best_of(pop, fit)
        if bf < best_f:
            best_f, best_x = bf, bx
        history.append({"iter": t, "best_f": best_f, "best_x": best_x.copy(), "mean_f": float(np.mean(fit))})

    # Phase 2: GWO - CHUYỂN TOÀN BỘ quần thể từ WOA sang GWO
    # Không tạo quần thể mới, tiếp tục với quần thể hiện tại
    for t2 in range(T2):
        t = T1 + t2
        # Tham số a giảm theo T2, bắt đầu lại từ 2
        a = 0.0 if T2 <= 1 else 2.0 - 2.0 * (t2 / (T2 - 1))
        pop = gwo_step(rng, pop, fit, a, repair_row)
        fit = eval_pop(fitness_fn, pop)
        bx, bf, _ = best_of(pop, fit)
        if bf < best_f:
            best_f, best_x = bf, bx
        history.append({"iter": t, "best_f": best_f, "best_x": best_x.copy(), "mean_f": float(np.mean(fit))})

    return best_x, float(best_f), history

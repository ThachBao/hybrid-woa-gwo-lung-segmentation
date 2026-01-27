# src/benchmarks/benchmark.py
from __future__ import annotations

import numpy as np
from scipy.special import gamma

from .benchmark_func import (
    sphere, schwefel_2_22, schwefel_2_21, max_absolute, quartic_noise,
    generalized_power, weighted_sphere, composite_quadratic, quartic_noise_simple,
    rastrigin, rastrigin_modified, ackley, griewank, schwefel_2_6_simple,
    weierstrass, michalewicz_modified, multimodal, branin
)

FUNCTIONS = [
    sphere, schwefel_2_22, schwefel_2_21, max_absolute, quartic_noise,
    generalized_power, weighted_sphere, composite_quadratic, quartic_noise_simple,
    rastrigin, rastrigin_modified, ackley, griewank, schwefel_2_6_simple,
    weierstrass, michalewicz_modified, multimodal, branin
]

BENCHMARK_NAMES = [
    "sphere", "schwefel_2_22", "schwefel_2_21", "max_absolute", "quartic_noise",
    "generalized_power", "weighted_sphere", "composite_quadratic", "quartic_noise_simple",
    "rastrigin", "rastrigin_modified", "ackley", "griewank", "schwefel_2_6_simple",
    "weierstrass", "michalewicz_modified", "multimodal", "branin"
]


def benchmark_functions(x: np.ndarray, fun_index: int) -> float:
    if 0 <= fun_index < len(FUNCTIONS):
        if fun_index == 17 and len(x) < 2:
            raise ValueError("Hàm Branin yêu cầu vector x có ít nhất 2 chiều.")
        return float(FUNCTIONS[fun_index](x))
    raise ValueError(f"fun_index phải từ 0 đến {len(FUNCTIONS) - 1}")


def set_bounds(fun_index: int, dim: int) -> tuple[np.ndarray, np.ndarray]:
    # giống map bounds trong file bạn gửi:contentReference[oaicite:8]{index=8}
    bounds = {
        0: (-5, 5),
        1: (-10, 10),
        2: (-100, 100),
        3: (-100, 100),
        4: (-1.28, 1.28),
        5: (-2, 2),
        6: (-5.12, 5.12),
        7: (-100, 100),
        8: (-1.28, 1.28),
        9: (-5.12, 5.12),
        10: (-5.12, 5.12),
        11: (-32, 32),
        12: (-600, 600),
        13: (-100, 100),
        14: (-0.5, 0.5),
        15: (-100, 100),
        16: (-10, 10),
        17: ([-5, 0], [10, 15]),
    }

    if fun_index == 17:
        lb = np.zeros(dim, dtype=float)
        ub = np.zeros(dim, dtype=float)
        lb[0], ub[0] = bounds[17][0][0], bounds[17][1][0]
        lb[1], ub[1] = bounds[17][0][1], bounds[17][1][1]
        if dim > 2:
            lb[2:], ub[2:] = -5, 10
        return lb, ub

    lb_val, ub_val = bounds[fun_index]
    return np.full(dim, lb_val, dtype=float), np.full(dim, ub_val, dtype=float)


def levy(dim: int) -> np.ndarray:
    beta = 1.5
    sigma = (
        gamma(1 + beta) * np.sin(np.pi * beta / 2)
        / (gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))
    ) ** (1 / beta)
    u = np.random.normal(0, sigma, dim)
    v = np.random.normal(0, 1, dim)
    return u / (np.abs(v) ** (1 / beta))


def space_bound(position: np.ndarray, ub: np.ndarray, lb: np.ndarray) -> np.ndarray:
    return np.clip(position, lb, ub)

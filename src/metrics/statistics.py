from __future__ import annotations

from typing import Dict, Iterable, List

import numpy as np

try:
    from scipy.stats import wilcoxon
except Exception:  # pragma: no cover
    wilcoxon = None


def standard_deviation(values: Iterable[float], ddof: int = 1) -> float:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0 or arr.size <= ddof:
        return 0.0
    return float(np.std(arr, ddof=ddof))


def convergence_iteration(history: List[Dict], tol: float = 1e-6) -> int:
    if not history:
        return 0
    best_series = np.asarray([float(h.get("best_f", 0.0)) for h in history], dtype=float)
    final_best = float(best_series[-1])
    hit = np.where(np.abs(best_series - final_best) <= tol)[0]
    if hit.size == 0:
        return int(best_series.size)
    return int(hit[0] + 1)


def wilcoxon_signed_rank(x: Iterable[float], y: Iterable[float]) -> Dict[str, float | int | None | str]:
    x_arr = np.asarray(list(x), dtype=float)
    y_arr = np.asarray(list(y), dtype=float)
    if x_arr.size == 0 or y_arr.size == 0 or x_arr.size != y_arr.size:
        return {"n": int(min(x_arr.size, y_arr.size)), "statistic": None, "pvalue": None, "status": "invalid"}
    if wilcoxon is None:
        return {"n": int(x_arr.size), "statistic": None, "pvalue": None, "status": "scipy_missing"}
    if np.allclose(x_arr, y_arr):
        return {"n": int(x_arr.size), "statistic": 0.0, "pvalue": 1.0, "status": "identical"}

    stat, pvalue = wilcoxon(x_arr, y_arr, zero_method="wilcox", alternative="two-sided")
    return {"n": int(x_arr.size), "statistic": float(stat), "pvalue": float(pvalue), "status": "ok"}

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np


class OtsuUnsupportedError(RuntimeError):
    """Kept for backward compatibility; exact DP Otsu no longer needs this in normal cases."""


@dataclass
class OtsuResult:
    thresholds: np.ndarray
    best_f: float | None
    history: list[dict]


def is_otsu_supported(k: int, max_supported_k: int = 4) -> bool:
    del max_supported_k
    return int(k) >= 1


class OtsuMulti:
    """
    Exact multi-level Otsu via dynamic programming on a 256-bin grayscale histogram.

    - Supports k >= 1 for uint8-style grayscale images.
    - Deterministic; does not use n_agents / n_iters / seed.
    - Main API: optimize_with_image(...).
    """

    def __init__(self, n_agents=None, n_iters=None, seed=None, max_supported_k: int = 4):
        self.n_agents = n_agents
        self.n_iters = n_iters
        self.seed = seed
        self.max_supported_k = int(max_supported_k)

    @staticmethod
    def _validate_gray_image(image: np.ndarray) -> np.ndarray:
        arr = np.asarray(image)
        if arr.ndim != 2:
            raise ValueError("OTSU yêu cầu ảnh xám 2D.")
        if arr.size == 0:
            raise ValueError("Ảnh đầu vào rỗng.")
        if np.isnan(arr).any():
            raise ValueError("Ảnh chứa NaN.")
        return arr

    @staticmethod
    def _to_uint8(image: np.ndarray) -> np.ndarray:
        arr = np.asarray(image)
        if arr.dtype == np.uint8:
            return arr

        arr = arr.astype(np.float64)
        vmin = float(np.min(arr))
        vmax = float(np.max(arr))
        if vmax <= vmin:
            return np.zeros_like(arr, dtype=np.uint8)

        arr = (arr - vmin) / (vmax - vmin)
        arr = np.clip(np.round(arr * 255.0), 0, 255)
        return arr.astype(np.uint8)

    @staticmethod
    def _class_score(prefix_p: np.ndarray, prefix_m: np.ndarray, a: int, b: int) -> float:
        if a > b:
            return -np.inf

        omega = prefix_p[b + 1] - prefix_p[a]
        if omega <= 1e-15:
            return -np.inf

        mu = prefix_m[b + 1] - prefix_m[a]
        return float((mu * mu) / omega)

    def _compute_thresholds_dp(self, image_u8: np.ndarray, k: int) -> np.ndarray:
        if k < 1:
            raise ValueError("k phải >= 1.")

        hist = np.bincount(image_u8.ravel(), minlength=256).astype(np.float64)
        total = float(hist.sum())
        if total <= 0.0:
            raise ValueError("Histogram rỗng.")

        p = hist / total
        bins = np.arange(256, dtype=np.float64)

        prefix_p = np.zeros(257, dtype=np.float64)
        prefix_m = np.zeros(257, dtype=np.float64)
        prefix_p[1:] = np.cumsum(p)
        prefix_m[1:] = np.cumsum(p * bins)

        n_classes = int(k) + 1
        L = 256

        score = np.full((L, L), -np.inf, dtype=np.float64)
        for a in range(L):
            for b in range(a, L):
                score[a, b] = self._class_score(prefix_p, prefix_m, a, b)

        dp = np.full((n_classes + 1, L), -np.inf, dtype=np.float64)
        ptr = np.full((n_classes + 1, L), -1, dtype=np.int32)

        for b in range(L):
            dp[1, b] = score[0, b]

        for c in range(2, n_classes + 1):
            for b in range(c - 1, L):
                best_val = -np.inf
                best_t = -1

                for t in range(c - 2, b):
                    prev = dp[c - 1, t]
                    curr = score[t + 1, b]
                    if not np.isfinite(prev) or not np.isfinite(curr):
                        continue

                    val = prev + curr
                    if val > best_val:
                        best_val = val
                        best_t = t

                dp[c, b] = best_val
                ptr[c, b] = best_t

        if not np.isfinite(dp[n_classes, L - 1]):
            raise RuntimeError("Không tìm được nghiệm Otsu đa ngưỡng hợp lệ.")

        thresholds = np.zeros(int(k), dtype=np.float64)
        b = L - 1
        c = n_classes

        for idx in range(int(k) - 1, -1, -1):
            t = int(ptr[c, b])
            if t < 0:
                raise RuntimeError("Backtrack thất bại khi truy vết thresholds.")
            thresholds[idx] = float(t)
            b = t
            c -= 1

        return np.sort(thresholds)

    def _compute_thresholds(self, image: np.ndarray, k: int) -> np.ndarray:
        gray = self._validate_gray_image(image)
        gray_u8 = self._to_uint8(gray)
        return self._compute_thresholds_dp(gray_u8, int(k))

    def optimize_with_image(
        self,
        image: np.ndarray,
        dim: int,
        fitness_fn: Optional[Callable[[np.ndarray], float]] = None,
        repair_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    ):
        thresholds = self._compute_thresholds(image, int(dim))

        if repair_fn is not None:
            thresholds = np.asarray(repair_fn(thresholds), dtype=float)
            thresholds = np.sort(thresholds)

        best_f = None if fitness_fn is None else float(fitness_fn(thresholds))
        history = [
            {
                "iter": 0,
                "best_f": None if best_f is None else float(best_f),
                "mean_f": None if best_f is None else float(best_f),
                "phase": "exact_multi_otsu_dp",
            }
        ]
        return thresholds, best_f, history

    def optimize(self, fitness_fn, dim, lb, ub, repair_fn=None, init_pop=None):
        del fitness_fn, dim, lb, ub, repair_fn, init_pop
        raise RuntimeError(
            "OTSU chuẩn cần ảnh đầu vào trực tiếp. "
            "Hãy gọi optimize_with_image(image=..., dim=..., fitness_fn=..., repair_fn=...)."
        )

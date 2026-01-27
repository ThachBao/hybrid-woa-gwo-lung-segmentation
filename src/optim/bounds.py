# clamp/bound + xử lý ràng buộc (sort ngưỡng, unique)
from __future__ import annotations

from typing import Tuple
import numpy as np


def as_bounds(lb: float | np.ndarray, ub: float | np.ndarray, dim: int) -> Tuple[np.ndarray, np.ndarray]:
    lb_arr = np.full(dim, float(lb), dtype=float) if np.isscalar(lb) else np.asarray(lb, dtype=float).reshape(-1)
    ub_arr = np.full(dim, float(ub), dtype=float) if np.isscalar(ub) else np.asarray(ub, dtype=float).reshape(-1)
    if lb_arr.size != dim or ub_arr.size != dim:
        raise ValueError("lb/ub phải có kích thước = dim (hoặc là scalar).")
    return lb_arr, ub_arr


def clamp(x: np.ndarray, lb: np.ndarray, ub: np.ndarray) -> np.ndarray:
    return np.clip(x, lb, ub)


def repair_threshold_vector(
    x: np.ndarray,
    *,
    k: int,
    lb: int = 0,
    ub: int = 255,
    integer: bool = True,
    ensure_unique: bool = True,
    avoid_endpoints: bool = True,  # NEW: tránh ngưỡng chạm 0/255
) -> np.ndarray:
    """
    Chuẩn hóa vector ngưỡng:
    - clip vào [lb, ub]
    - (tuỳ chọn) làm tròn về int
    - sort tăng dần
    - (tuỳ chọn) ép strict-increasing để tránh trùng
    - (tuỳ chọn) tránh ngưỡng chạm biên lb/ub (giảm dồn ngưỡng)
    """
    x = np.asarray(x, dtype=float).reshape(-1)
    if x.size != k:
        raise ValueError("x phải có độ dài đúng bằng k.")

    if integer:
        x = np.rint(x)

    # Nếu tránh endpoints, thu hẹp range
    effective_lb = lb + 1 if avoid_endpoints else lb
    effective_ub = ub - 1 if avoid_endpoints else ub

    x = np.clip(x, effective_lb, effective_ub)
    x.sort()

    if ensure_unique:
        if (effective_ub - effective_lb + 1) < k:
            raise ValueError(f"Không thể đảm bảo unique vì miền [{effective_lb}, {effective_ub}] quá nhỏ so với k={k}.")

        # forward pass: đảm bảo x[i] >= x[i-1] + 1
        for i in range(1, k):
            if x[i] <= x[i - 1]:
                x[i] = x[i - 1] + 1

        # nếu vượt ub, kéo lùi từ cuối
        if x[-1] > effective_ub:
            x[-1] = effective_ub
            for i in range(k - 2, -1, -1):
                if x[i] >= x[i + 1]:
                    x[i] = x[i + 1] - 1

        if x[0] < effective_lb or x[-1] > effective_ub:
            raise ValueError("Repair unique thất bại do ràng buộc biên.")

    if integer:
        x = x.astype(int)

    return x

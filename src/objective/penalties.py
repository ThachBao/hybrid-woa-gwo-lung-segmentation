"""
Penalty functions to prevent threshold clustering and empty regions
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


def _to_sorted_int_thresholds(t: np.ndarray, lb: int = 0, ub: int = 255) -> np.ndarray:
    """Chuẩn hóa và sắp xếp ngưỡng"""
    x = np.asarray(t, dtype=float).ravel()
    x = np.clip(x, lb, ub)
    x = np.rint(x).astype(int)
    x.sort()
    return x


def penalty_min_gap(t: np.ndarray, lb: int = 0, ub: int = 255, min_gap: int = 3) -> float:
    """
    Hinge penalty: khuyến khích khoảng cách giữa các ngưỡng >= min_gap.
    Trả về giá trị ~ [0..] (đã chuẩn hoá theo range).
    """
    x = _to_sorted_int_thresholds(t, lb, ub)
    if x.size < 2:
        return 0.0
    r = float(ub - lb)
    d = np.diff(x).astype(float) / r
    g = float(min_gap) / r
    p = np.maximum(0.0, g - d)
    return float(np.mean(p * p))


def penalty_gap_variance(t: np.ndarray, lb: int = 0, ub: int = 255) -> float:
    """
    Var của gap (chuẩn hoá theo range). Var nhỏ -> gap đều hơn.
    """
    x = _to_sorted_int_thresholds(t, lb, ub)
    if x.size < 2:
        return 0.0
    r = float(ub - lb)
    d = np.diff(x).astype(float) / r
    return float(np.var(d))


def penalty_end_margin(t: np.ndarray, lb: int = 0, ub: int = 255, margin: int = 3) -> float:
    """
    Ép ngưỡng không quá sát biên lb/ub. (chuẩn hoá theo range)
    """
    x = _to_sorted_int_thresholds(t, lb, ub)
    if x.size == 0:
        return 0.0
    r = float(ub - lb)
    m = float(margin) / r
    t0 = (float(x[0]) - lb) / r
    t1 = (ub - float(x[-1])) / r
    p0 = max(0.0, m - t0)
    p1 = max(0.0, m - t1)
    return float(p0 * p0 + p1 * p1)


def region_proportions(gray_u8: np.ndarray, t: np.ndarray, lb: int = 0, ub: int = 255) -> np.ndarray:
    """
    Chia ảnh theo thresholds bằng np.digitize -> p_c (c=0..K)
    """
    g = np.asarray(gray_u8)
    if g.ndim == 3:
        g = g[..., 0]
    if g.dtype != np.uint8:
        g = np.clip(g, 0, 255).astype(np.uint8)

    x = _to_sorted_int_thresholds(t, lb, ub)
    # labels in [0..K]
    labels = np.digitize(g.ravel(), x, right=True)
    counts = np.bincount(labels, minlength=x.size + 1).astype(float)
    p = counts / max(1.0, counts.sum())
    return p


def penalty_min_region_size(gray_u8: np.ndarray, t: np.ndarray, p_min: float = 0.01, lb: int = 0, ub: int = 255) -> float:
    """
    Ép mỗi vùng chiếm ít nhất p_min tỷ lệ pixel.
    """
    p = region_proportions(gray_u8, t, lb, ub)
    q = np.maximum(0.0, float(p_min) - p)
    return float(np.mean(q * q))


def penalty_quantile_prior(gray_u8: np.ndarray, t: np.ndarray, lb: int = 0, ub: int = 255) -> float:
    """
    Ép thresholds gần các quantile của ảnh (prior trải đều theo CDF).
    Dùng MSE chuẩn hoá theo range.
    """
    x = _to_sorted_int_thresholds(t, lb, ub).astype(float)
    k = x.size
    if k == 0:
        return 0.0
    g = np.asarray(gray_u8)
    if g.ndim == 3:
        g = g[..., 0]
    g = g.astype(float).ravel()

    # target percentiles: i/(k+1)
    qs = np.array([(i + 1) / (k + 1) for i in range(k)], dtype=float)
    target = np.quantile(g, qs)

    r = float(ub - lb)
    return float(np.mean(((x - target) / r) ** 2))


@dataclass
class PenaltyWeights:
    """Trọng số cho các penalty functions"""
    w_gap: float = 0.0      # Min gap between thresholds
    w_var: float = 0.0      # Gap variance (uniform spacing)
    w_end: float = 0.0      # End margin (avoid 0/255)
    w_size: float = 0.0     # Min region size
    w_q: float = 0.0        # Quantile prior


@dataclass
class PenaltyParams:
    """Tham số cho các penalty functions"""
    min_gap: int = 3        # Khoảng cách tối thiểu giữa ngưỡng
    end_margin: int = 3     # Khoảng cách tối thiểu từ biên
    p_min: float = 0.01     # Tỷ lệ pixel tối thiểu mỗi vùng (1%)


def total_penalty(
    gray_u8: np.ndarray,
    t: np.ndarray,
    weights: PenaltyWeights,
    params: PenaltyParams,
    lb: int = 0,
    ub: int = 255
) -> float:
    """
    Tổng penalty có trọng số.
    
    Args:
        gray_u8: Ảnh grayscale
        t: Vector ngưỡng
        weights: Trọng số các penalty
        params: Tham số các penalty
        lb: Lower bound (default: 0)
        ub: Upper bound (default: 255)
    
    Returns:
        Tổng penalty (càng nhỏ càng tốt)
    """
    P = 0.0
    if weights.w_gap:
        P += weights.w_gap * penalty_min_gap(t, lb, ub, min_gap=params.min_gap)
    if weights.w_var:
        P += weights.w_var * penalty_gap_variance(t, lb, ub)
    if weights.w_end:
        P += weights.w_end * penalty_end_margin(t, lb, ub, margin=params.end_margin)
    if weights.w_size:
        P += weights.w_size * penalty_min_region_size(gray_u8, t, p_min=params.p_min, lb=lb, ub=ub)
    if weights.w_q:
        P += weights.w_q * penalty_quantile_prior(gray_u8, t, lb, ub)
    return float(P)

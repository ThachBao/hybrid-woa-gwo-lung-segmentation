# Fuzzy Entropy (tính trên histogram/ảnh)
# src/objective/fuzzy_entropy.py
from __future__ import annotations

import numpy as np


def _shannon_s(mu: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """
    S(mu) = -mu ln(mu) - (1-mu) ln(1-mu)
    (theo Shannon function trong De Luca & Termini):contentReference[oaicite:1]{index=1}
    """
    mu = np.clip(mu, eps, 1.0 - eps)
    return -(mu * np.log(mu) + (1.0 - mu) * np.log(1.0 - mu))


def _sanitize_thresholds(thresholds: np.ndarray, lo: int = 0, hi: int = 255) -> np.ndarray:
    """
    Chuẩn hoá ngưỡng: clip, sort, round về int, ép tăng dần tối thiểu 1.
    """
    t = np.asarray(thresholds, dtype=float)
    t = np.clip(t, lo, hi)
    t = np.sort(t)
    t = np.rint(t).astype(int)
    # ép tăng dần (tránh trùng ngưỡng)
    for i in range(1, len(t)):
        if t[i] <= t[i - 1]:
            t[i] = min(hi, t[i - 1] + 1)
    # nếu vẫn bị dồn lên hi gây trùng, cắt bớt
    t = np.unique(t)
    return t


def _triangular_memberships_from_thresholds(thresholds: np.ndarray) -> np.ndarray:
    """
    Tạo membership (m x 256) cho m = k+1 lớp, dựa trên các ngưỡng k.
    - Dùng tam giác theo tâm lớp (center) và biên trái/phải theo trung điểm giữa các tâm.
    - Không dùng tham số 'fuzziness' ngoài; hoàn toàn suy ra từ thresholds.
    """
    t = _sanitize_thresholds(thresholds)
    bounds = np.concatenate(([0], t, [255])).astype(float)  # b0..b_{m}
    m = len(bounds) - 1  # số lớp

    centers = 0.5 * (bounds[:-1] + bounds[1:])  # c0..c_{m-1}
    left_edges = np.empty(m, dtype=float)
    right_edges = np.empty(m, dtype=float)

    for i in range(m):
        if i == 0:
            left_edges[i] = 0.0
        else:
            left_edges[i] = 0.5 * (centers[i - 1] + centers[i])

        if i == m - 1:
            right_edges[i] = 255.0
        else:
            right_edges[i] = 0.5 * (centers[i] + centers[i + 1])

    g = np.arange(256, dtype=float)[None, :]  # (1, 256)
    mu = np.zeros((m, 256), dtype=float)

    for i in range(m):
        l, c, r = left_edges[i], centers[i], right_edges[i]

        # tăng từ l -> c
        if c > l:
            mask = (g >= l) & (g <= c)
            mu[i, mask[0]] = (g[0, mask[0]] - l) / (c - l)
        else:
            # trường hợp hiếm khi c==l
            mask = (g == c)
            mu[i, mask[0]] = 1.0

        # giảm từ c -> r
        if r > c:
            mask = (g >= c) & (g <= r)
            mu[i, mask[0]] = np.maximum(mu[i, mask[0]], (r - g[0, mask[0]]) / (r - c))
        else:
            mask = (g == c)
            mu[i, mask[0]] = 1.0

    mu = np.clip(mu, 0.0, 1.0)
    return mu


def fuzzy_entropy_objective(image_u8: np.ndarray, thresholds: np.ndarray, eps: float = 1e-12) -> float:
    """
    Tính fuzzy entropy của ảnh với các ngưỡng cho trước.
    
    Mục tiêu: MAXIMIZE fuzzy entropy
    - Optimizer MINIMIZE → trả về -entropy
    - Giá trị entropy thực (E) luôn DƯƠNG
    - Giá trị trả về (-E) luôn ÂM để optimizer minimize
    
    E = sum_{g=0..255} p(g) * mean_{class}( S(mu_class(g)) )
    với S theo Shannon function trong De Luca & Termini
    
    Returns:
        -E (âm của entropy) để dùng với optimizer minimize
        Entropy thực E = -return_value (luôn dương)
    """
    img = np.asarray(image_u8)
    if img.ndim != 2:
        raise ValueError("image_u8 phải là ảnh xám 2D (H, W).")
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)

    hist = np.bincount(img.ravel(), minlength=256).astype(float)
    total = hist.sum()
    if total <= 0:
        return 0.0

    p = hist / total  # p(g)
    mu = _triangular_memberships_from_thresholds(thresholds)  # (m, 256)

    s = _shannon_s(mu, eps=eps)  # (m, 256)
    e_g = s.mean(axis=0)         # (256,)
    E = float(np.sum(p * e_g))   # Entropy thực (dương)
    return -E  # Trả về âm để optimizer minimize

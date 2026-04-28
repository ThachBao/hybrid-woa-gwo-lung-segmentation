from __future__ import annotations

import numpy as np


def sanitize_thresholds(thresholds: np.ndarray, lo: int = 0, hi: int = 255) -> np.ndarray:
    t = np.asarray(thresholds, dtype=float).reshape(-1)
    t = np.clip(t, lo, hi)
    t = np.sort(t)
    t = np.rint(t).astype(int)
    for i in range(1, len(t)):
        if t[i] <= t[i - 1]:
            t[i] = min(hi, t[i - 1] + 1)
    return t


def _s_membership(x: np.ndarray, a: float, b: float) -> np.ndarray:
    if b <= a:
        return (x >= b).astype(float)

    mid = 0.5 * (a + b)
    mu = np.zeros_like(x, dtype=float)

    left = (x > a) & (x <= mid)
    right = (x > mid) & (x < b)
    mu[x >= b] = 1.0

    mu[left] = 2.0 * ((x[left] - a) / (b - a)) ** 2
    mu[right] = 1.0 - 2.0 * ((x[right] - b) / (b - a)) ** 2
    return np.clip(mu, 0.0, 1.0)


def s_shaped_fuzzy_partition(thresholds: np.ndarray) -> np.ndarray:
    t = sanitize_thresholds(thresholds)
    k = len(t)
    gray_levels = np.arange(256, dtype=float)

    if k == 0:
        return np.ones((1, 256), dtype=float)

    ext = np.concatenate(([0.0], t.astype(float), [255.0]))
    widths = []
    for i, thr in enumerate(t.astype(float), start=1):
        gap_left = max(1.0, thr - ext[i - 1])
        gap_right = max(1.0, ext[i + 1] - thr)
        widths.append(max(1.0, 0.5 * min(gap_left, gap_right)))

    s_curves = np.asarray(
        [_s_membership(gray_levels, thr - width, thr + width) for thr, width in zip(t.astype(float), widths)],
        dtype=float,
    )

    mu = np.zeros((k + 1, 256), dtype=float)
    mu[0] = 1.0 - s_curves[0]
    for i in range(1, k):
        mu[i] = s_curves[i - 1] - s_curves[i]
    mu[k] = s_curves[-1]

    mu = np.clip(mu, 0.0, 1.0)
    denom = np.sum(mu, axis=0, keepdims=True)
    denom = np.where(denom <= 1e-12, 1.0, denom)
    return mu / denom


def fuzzy_entropy_value(image_u8: np.ndarray, thresholds: np.ndarray, eps: float = 1e-12) -> float:
    img = np.asarray(image_u8)
    if img.ndim != 2:
        raise ValueError("image_u8 phải là ảnh xám 2D (H, W).")
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)

    hist = np.bincount(img.ravel(), minlength=256).astype(float)
    total = float(hist.sum())
    if total <= 0.0:
        return 0.0

    p = hist / total
    mu = s_shaped_fuzzy_partition(thresholds)

    entropy_total = 0.0
    for i in range(mu.shape[0]):
        weighted = p * mu[i]
        class_mass = float(np.sum(weighted))
        if class_mass <= eps:
            continue
        q = weighted / class_mass
        q = np.clip(q, eps, 1.0)
        entropy_total += -float(np.sum(q * np.log(q)))

    return entropy_total


def fuzzy_entropy_objective(image_u8: np.ndarray, thresholds: np.ndarray, eps: float = 1e-12) -> float:
    return -float(fuzzy_entropy_value(image_u8, thresholds, eps=eps))

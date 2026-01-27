# wrapper: vector ngưỡng -> fitness (min/max)
# src/objective/thresholding.py
from __future__ import annotations

import numpy as np


def sanitize_thresholds(thresholds: np.ndarray, lo: int = 0, hi: int = 255) -> np.ndarray:
    t = np.asarray(thresholds, dtype=float)
    t = np.clip(t, lo, hi)
    t = np.sort(t)
    t = np.rint(t).astype(int)
    for i in range(1, len(t)):
        if t[i] <= t[i - 1]:
            t[i] = min(hi, t[i - 1] + 1)
    return np.unique(t)


def apply_multi_threshold(image_u8: np.ndarray, thresholds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Trả về:
    - labels: 0..k (k=len(thresholds))
    - segmented_u8: ánh xạ nhãn -> mức xám đều (0..255)
    """
    img = np.asarray(image_u8)
    if img.ndim != 2:
        raise ValueError("image_u8 phải là ảnh xám 2D (H, W).")
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)

    t = sanitize_thresholds(thresholds)
    labels = np.digitize(img, t, right=True).astype(np.int32)  # 0..k
    k = len(t)
    if k == 0:
        return labels, img.copy()

    segmented = np.rint(labels * (255.0 / k)).astype(np.uint8)
    return labels, segmented

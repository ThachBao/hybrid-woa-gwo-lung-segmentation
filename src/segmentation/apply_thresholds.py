# áp ngưỡng lên ảnh xám -> ảnh phân đoạn
# src/segmentation/apply_thresholds.py
from __future__ import annotations

import numpy as np
from src.objective.thresholding import apply_multi_threshold, sanitize_thresholds


def apply_thresholds_labels(gray_u8: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    t = sanitize_thresholds(thresholds)
    labels, _ = apply_multi_threshold(gray_u8, t)
    return labels


def apply_thresholds(gray_u8: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    t = sanitize_thresholds(thresholds)
    _, seg = apply_multi_threshold(gray_u8, t)
    return seg

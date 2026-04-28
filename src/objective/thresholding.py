from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ThresholdClassInfo:
    index: int
    name: str
    lower_bound: int
    upper_bound: int
    pixel_count: int
    mean_intensity: int


def sanitize_thresholds(thresholds: np.ndarray, lo: int = 0, hi: int = 255) -> np.ndarray:
    t = np.asarray(thresholds, dtype=float)
    t = np.clip(t, lo, hi)
    t = np.sort(t)
    t = np.rint(t).astype(int)
    for i in range(1, len(t)):
        if t[i] <= t[i - 1]:
            t[i] = min(hi, t[i - 1] + 1)
    return np.unique(t)


def _class_name(index: int, n_classes: int) -> str:
    if n_classes == 2:
        return "dark" if index == 0 else "bright"
    if n_classes == 3:
        return ("dark", "medium", "bright")[index]
    return f"class_{index}"


def decode_threshold_classes(
    image_u8: np.ndarray,
    thresholds: np.ndarray,
) -> tuple[np.ndarray, list[ThresholdClassInfo]]:
    """
    Decode an image into m+1 threshold classes and describe each class.

    Return:
    - labels: 0..k (k=len(thresholds))
    - classes: metadata for each class, including representative mean intensity
    """
    img = np.asarray(image_u8)
    if img.ndim != 2:
        raise ValueError("image_u8 must be a 2D grayscale image.")
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)

    t = sanitize_thresholds(thresholds)
    labels = np.digitize(img, t, right=True).astype(np.int32)
    n_classes = len(t) + 1

    bounds = np.concatenate(([-1], t.astype(int), [255]))
    classes: list[ThresholdClassInfo] = []
    for class_idx in range(n_classes):
        mask = labels == class_idx
        if np.any(mask):
            mean_intensity = int(np.rint(np.mean(img[mask])))
            pixel_count = int(np.count_nonzero(mask))
        else:
            lower = int(bounds[class_idx] + 1)
            upper = int(bounds[class_idx + 1])
            mean_intensity = int(np.clip(np.rint(0.5 * (lower + upper)), 0, 255))
            pixel_count = 0

        classes.append(
            ThresholdClassInfo(
                index=class_idx,
                name=_class_name(class_idx, n_classes),
                lower_bound=int(bounds[class_idx] + 1),
                upper_bound=int(bounds[class_idx + 1]),
                pixel_count=pixel_count,
                mean_intensity=mean_intensity,
            )
        )

    return labels, classes


def apply_multi_threshold(image_u8: np.ndarray, thresholds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Return:
    - labels: 0..k (k=len(thresholds))
    - segmented_u8: piecewise-constant reconstruction using class means
    """
    img = np.asarray(image_u8)
    if img.ndim != 2:
        raise ValueError("image_u8 must be a 2D grayscale image.")
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)

    labels, classes = decode_threshold_classes(img, thresholds)
    if not classes:
        return labels, img.copy()

    segmented = np.zeros_like(img, dtype=np.uint8)
    for class_info in classes:
        mask = labels == class_info.index
        if not np.any(mask):
            continue
        segmented[mask] = np.uint8(class_info.mean_intensity)
    return labels, segmented

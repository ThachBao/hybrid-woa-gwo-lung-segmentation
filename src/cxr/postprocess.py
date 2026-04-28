from __future__ import annotations

from typing import Dict, Tuple

import cv2
import numpy as np
from scipy import ndimage as ndi


def remove_small_regions(mask: np.ndarray, min_area: int = 1200) -> np.ndarray:
    binary = (mask > 0).astype(np.uint8)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    out = np.zeros_like(binary)
    for idx in range(1, num):
        if int(stats[idx, cv2.CC_STAT_AREA]) >= min_area:
            out[labels == idx] = 1
    return out.astype(np.uint8) * 255


def fill_mask_holes(mask: np.ndarray) -> np.ndarray:
    filled = ndi.binary_fill_holes(mask > 0)
    return filled.astype(np.uint8) * 255


def keep_two_largest_components(mask: np.ndarray) -> Tuple[np.ndarray, Dict]:
    binary = (mask > 0).astype(np.uint8)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    areas = [(idx, int(stats[idx, cv2.CC_STAT_AREA])) for idx in range(1, num)]
    areas.sort(key=lambda item: item[1], reverse=True)
    out = np.zeros_like(binary)
    for idx, _area in areas[:2]:
        out[labels == idx] = 1
    info = {
        "num_components": int(max(num - 1, 0)),
        "component_areas": [area for _, area in areas],
    }
    return out.astype(np.uint8) * 255, info


def smooth_mask(mask: np.ndarray) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    smoothed = cv2.morphologyEx((mask > 0).astype(np.uint8) * 255, cv2.MORPH_CLOSE, kernel, iterations=1)
    smoothed = cv2.GaussianBlur(smoothed, (7, 7), 0)
    return (smoothed > 127).astype(np.uint8) * 255


def expand_underfilled_mask(mask: np.ndarray, target_area_ratio: float = 0.23) -> Tuple[np.ndarray, bool]:
    binary = (mask > 0).astype(np.uint8) * 255
    area_ratio = float(np.count_nonzero(binary) / max(binary.size, 1))
    if area_ratio <= 0.0 or area_ratio >= target_area_ratio:
        return binary, False

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
    expanded = cv2.dilate(binary, kernel, iterations=1)
    expanded = fill_mask_holes(expanded)
    expanded, _ = keep_two_largest_components(expanded)
    return expanded, True


def postprocess_lung_mask(mask: np.ndarray) -> Dict:
    notes = []
    binary = (mask > 0).astype(np.uint8) * 255
    binary = remove_small_regions(binary)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    binary = fill_mask_holes(binary)
    binary, cc_info = keep_two_largest_components(binary)
    final_mask = smooth_mask(binary)
    final_mask, expanded = expand_underfilled_mask(final_mask)

    area_ratio = float(np.count_nonzero(final_mask) / max(final_mask.size, 1))
    if area_ratio < 0.04:
        notes.append("Predicted lung mask area is small")
    if area_ratio > 0.65:
        notes.append("Predicted lung mask area is very large")
    if cc_info["num_components"] == 0:
        notes.append("No connected lung component survived postprocessing")

    qc_info = {
        **cc_info,
        "final_area_ratio": area_ratio,
        "expanded_underfilled_mask": expanded,
        "low_confidence": bool(notes or cc_info["num_components"] == 0),
        "notes": notes,
    }
    return {"final_mask": final_mask, "qc_info": qc_info}

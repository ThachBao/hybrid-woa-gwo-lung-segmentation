from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import cv2
import numpy as np


def load_cxr_image(path: str | Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(str(path))
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def normalize_to_uint8(img: np.ndarray) -> np.ndarray:
    arr = np.asarray(img)
    if arr.dtype == np.uint8:
        return arr.copy()
    arr = arr.astype(np.float32)
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))
    if max_val <= min_val:
        return np.zeros(arr.shape, dtype=np.uint8)
    out = (arr - min_val) * (255.0 / (max_val - min_val))
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def resize_cxr(img: np.ndarray, size: Tuple[int, int] = (512, 512)) -> np.ndarray:
    width, height = int(size[0]), int(size[1])
    return cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)


def apply_clahe(img: np.ndarray) -> np.ndarray:
    gray = normalize_to_uint8(img)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def denoise_cxr(img: np.ndarray) -> np.ndarray:
    gray = normalize_to_uint8(img)
    return cv2.medianBlur(gray, 3)


def preprocess_cxr(img: np.ndarray) -> Dict[str, Any]:
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    original_shape = tuple(int(v) for v in img.shape[:2])
    gray_original = resize_cxr(normalize_to_uint8(img), size=(512, 512))
    normalized = normalize_to_uint8(gray_original)
    enhanced = apply_clahe(normalized)
    denoised = denoise_cxr(enhanced)

    return {
        "gray_original": gray_original,
        "gray_preprocessed": denoised,
        "preprocessing_info": {
            "original_shape": original_shape,
            "output_shape": tuple(int(v) for v in denoised.shape[:2]),
            "resize": [512, 512],
            "normalize": "uint8_0_255",
            "clahe": {"clipLimit": 2.0, "tileGridSize": [8, 8]},
            "denoise": "median_blur_3",
        },
    }

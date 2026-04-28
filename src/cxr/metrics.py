from __future__ import annotations

from typing import Any, Dict, Optional

import cv2
import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


def _binary(mask: np.ndarray) -> np.ndarray:
    return (np.asarray(mask) > 0).astype(np.uint8)


def compute_dsc(gt: np.ndarray, pred: np.ndarray) -> float:
    gt_b = _binary(gt)
    pred_b = _binary(pred)
    denom = int(gt_b.sum() + pred_b.sum())
    if denom == 0:
        return 1.0
    inter = int(np.logical_and(gt_b, pred_b).sum())
    return float((2.0 * inter) / denom)


def compute_iou(gt: np.ndarray, pred: np.ndarray) -> float:
    gt_b = _binary(gt)
    pred_b = _binary(pred)
    union = int(np.logical_or(gt_b, pred_b).sum())
    if union == 0:
        return 1.0
    inter = int(np.logical_and(gt_b, pred_b).sum())
    return float(inter / union)


def compute_psnr(a: np.ndarray, b: np.ndarray) -> float:
    return float(peak_signal_noise_ratio(a, b, data_range=255))


def compute_ssim(a: np.ndarray, b: np.ndarray) -> float:
    return float(structural_similarity(a, b, data_range=255))


def compute_cxr_metrics(
    gray: np.ndarray,
    pred_mask: np.ndarray,
    gt_mask: Optional[np.ndarray] = None,
    *,
    fe: Optional[float] = None,
    runtime: Optional[float] = None,
    qc_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    pred = (_binary(pred_mask) * 255).astype(np.uint8)
    gray_u8 = np.clip(gray, 0, 255).astype(np.uint8)
    metrics: Dict[str, Any] = {
        "fe": fe,
        "time": runtime,
        "qc_info": qc_info or {},
        "dsc": None,
        "iou": None,
    }

    if gt_mask is not None:
        gt = (_binary(gt_mask) * 255).astype(np.uint8)
        if gt.shape != pred.shape:
            gt = cv2.resize(gt, (pred.shape[1], pred.shape[0]), interpolation=cv2.INTER_NEAREST)
        metrics["dsc"] = compute_dsc(gt, pred)
        metrics["iou"] = compute_iou(gt, pred)
        metrics["psnr"] = compute_psnr(gt, pred)
        metrics["ssim"] = compute_ssim(gt, pred)
    else:
        masked_gray = (gray_u8 * (pred > 0)).astype(np.uint8)
        metrics["psnr"] = compute_psnr(gray_u8, masked_gray)
        metrics["ssim"] = compute_ssim(gray_u8, masked_gray)

    return metrics

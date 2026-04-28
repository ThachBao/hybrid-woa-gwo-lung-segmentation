from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np


def save_gray_png(path: str | Path, gray: np.ndarray) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.clip(gray, 0, 255).astype(np.uint8))
    return path.as_posix()


def save_mask_png(path: str | Path, mask: np.ndarray) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), ((mask > 0).astype(np.uint8) * 255))
    return path.as_posix()


def build_overlay(gray: np.ndarray, mask: np.ndarray) -> np.ndarray:
    base = cv2.cvtColor(np.clip(gray, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    color = np.zeros_like(base)
    color[:, :, 1] = 220
    color[:, :, 2] = 40
    binary = mask > 0
    overlay = base.copy()
    overlay[binary] = cv2.addWeighted(base, 0.55, color, 0.45, 0)[binary]
    contours, _ = cv2.findContours(binary.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (0, 255, 255), 2)
    return overlay


def save_overlay_png(path: str | Path, gray: np.ndarray, mask: np.ndarray) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), build_overlay(gray, mask))
    return path.as_posix()


def build_convergence_payload(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    points = []
    for idx, item in enumerate(history or []):
        best_f = float(item.get("best_f", 0.0))
        points.append({
            "iter": int(item.get("iter", idx)),
            "best_f": best_f,
            "fe": float(-best_f),
            "shared": bool(item.get("shared", False)),
            "share_reason": item.get("share_reason"),
        })
    return {"points": points}

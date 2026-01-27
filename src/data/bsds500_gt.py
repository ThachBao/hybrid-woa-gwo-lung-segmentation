"""
BSDS500 Ground Truth utilities for boundary mask and DICE calculation.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from scipy.io import loadmat  # type: ignore
except Exception:  # pragma: no cover
    loadmat = None

from src.segmentation.io import read_image_gray


def _is_mat(path: str | os.PathLike) -> bool:
    return str(path).lower().endswith(".mat")


def _safe_ravel(x):
    return np.ravel(x) if isinstance(x, np.ndarray) else np.array([x], dtype=object)


def read_bsds_gt_boundary_mask(gt_path: str | os.PathLike, thr: float = 0.5, fuse: str = "max") -> np.ndarray:
    """
    Đọc GT boundary mask từ:
    - .mat (BSDS500 groundTruth): gộp nhiều annotator -> 1 mask
    - ảnh (png/jpg...): threshold -> mask
    Trả về mask bool (H,W).
    """
    p = str(gt_path)

    # Case 1: ảnh mask
    if not _is_mat(p):
        g = read_image_gray(p).astype(np.float32) / 255.0
        return (g > float(thr))

    # Case 2: .mat
    if loadmat is None:
        raise RuntimeError("Thiếu scipy để đọc .mat (scipy.io.loadmat).")

    mat = loadmat(p, squeeze_me=True, struct_as_record=False)
    if "groundTruth" not in mat:
        raise ValueError(f"Không thấy key 'groundTruth' trong: {p}")

    gt = mat["groundTruth"]
    items = _safe_ravel(gt)

    boundaries: List[np.ndarray] = []
    for item in items:
        # struct_as_record=False thường cho object có attribute Boundaries / Segmentation
        b = None
        if hasattr(item, "Boundaries"):
            b = getattr(item, "Boundaries")
        elif hasattr(item, "boundaries"):
            b = getattr(item, "boundaries")

        if b is None:
            continue

        b_arr = np.asarray(b, dtype=np.float32)
        boundaries.append(b_arr)

    if not boundaries:
        raise ValueError(f"Không trích xuất được Boundaries từ: {p}")

    stack = np.stack(boundaries, axis=0)  # (A,H,W)
    if fuse.lower() == "mean":
        fused = stack.mean(axis=0)
    else:
        fused = stack.max(axis=0)

    return (fused > float(thr))


def seg_to_boundary_mask(seg_u8_or_labels: np.ndarray) -> np.ndarray:
    """
    Tạo boundary mask từ ảnh phân đoạn (uint8) hoặc label map (int).
    Boundary = pixel có khác nhãn/giá trị với hàng xóm 4-neighborhood.
    """
    x = np.asarray(seg_u8_or_labels)
    if x.ndim == 3:
        x = x[..., 0]
    if x.ndim != 2:
        raise ValueError("seg phải là 2D.")

    b = np.zeros_like(x, dtype=bool)
    b[:-1, :] |= (x[:-1, :] != x[1:, :])
    b[:, :-1] |= (x[:, :-1] != x[:, 1:])
    return b


def dice_binary(a: np.ndarray, b: np.ndarray, eps: float = 1e-12) -> float:
    """
    Dice = 2|A∩B| / (|A|+|B|) cho mask nhị phân.
    """
    a = np.asarray(a, dtype=bool).ravel()
    b = np.asarray(b, dtype=bool).ravel()
    if a.shape != b.shape:
        raise ValueError("Hai mask phải cùng kích thước.")
    inter = float(np.sum(a & b))
    sa = float(np.sum(a))
    sb = float(np.sum(b))
    return float((2.0 * inter) / (sa + sb + eps))


def build_pairs(images_dir: str | os.PathLike, gt_dir: str | os.PathLike) -> List[Tuple[str, str]]:
    """
    Ghép ảnh với GT theo stem (tên file không đuôi), tìm GT trong gt_dir (đệ quy).
    Hỗ trợ GT là .mat hoặc ảnh.
    """
    images_dir = str(images_dir)
    gt_dir = str(gt_dir)

    # index GT by stem
    gt_map: Dict[str, str] = {}
    for dirpath, _, filenames in os.walk(gt_dir):
        for fn in filenames:
            low = fn.lower()
            if low.endswith(".mat") or low.endswith(".png") or low.endswith(".jpg") or low.endswith(".jpeg") or low.endswith(".bmp") or low.endswith(".tif") or low.endswith(".tiff"):
                stem = Path(fn).stem
                if stem not in gt_map:
                    gt_map[stem] = os.path.join(dirpath, fn)

    pairs: List[Tuple[str, str]] = []
    for dirpath, _, filenames in os.walk(images_dir):
        for fn in filenames:
            low = fn.lower()
            if low.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")):
                stem = Path(fn).stem
                if stem in gt_map:
                    pairs.append((os.path.join(dirpath, fn), gt_map[stem]))

    pairs.sort(key=lambda t: Path(t[0]).stem)
    return pairs

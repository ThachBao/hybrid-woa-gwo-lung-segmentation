from __future__ import annotations

from typing import Dict, Optional, Tuple
import numpy as np

try:
    from skimage.metrics import peak_signal_noise_ratio, structural_similarity
except Exception:  # pragma: no cover
    peak_signal_noise_ratio = None
    structural_similarity = None


def to_uint8_gray(img: np.ndarray) -> np.ndarray:
    arr = np.asarray(img)
    if arr.ndim == 3:
        arr = arr[..., 0]
    if arr.ndim != 2:
        raise ValueError("Ảnh phải là grayscale 2D.")
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return arr


def to_float(img: np.ndarray) -> np.ndarray:
    return np.asarray(img, dtype=np.float64)


def compute_psnr(img_true: np.ndarray, img_test: np.ndarray, data_range: float = 255.0) -> float:
    """
    PSNR càng cao càng tốt.
    Công thức chuẩn: 10 * log10(MAX^2 / MSE). :contentReference[oaicite:5]{index=5}
    """
    a = to_float(to_uint8_gray(img_true))
    b = to_float(to_uint8_gray(img_test))
    if a.shape != b.shape:
        raise ValueError("img_true và img_test phải cùng shape.")

    if peak_signal_noise_ratio is not None:
        return float(peak_signal_noise_ratio(a, b, data_range=data_range))

    # fallback (không dùng skimage)
    mse = float(np.mean((a - b) ** 2))
    if mse == 0.0:
        return float("inf")
    return float(10.0 * np.log10((data_range ** 2) / mse))


def compute_ssim(img_true: np.ndarray, img_test: np.ndarray, data_range: float = 255.0) -> float:
    """
    SSIM càng gần 1 càng tốt. :contentReference[oaicite:6]{index=6}
    Lưu ý data_range khi ảnh float. :contentReference[oaicite:7]{index=7}
    """
    a = to_float(to_uint8_gray(img_true))
    b = to_float(to_uint8_gray(img_test))
    if a.shape != b.shape:
        raise ValueError("img_true và img_test phải cùng shape.")

    if structural_similarity is None:
        raise RuntimeError("Thiếu scikit-image để tính SSIM (skimage.metrics.structural_similarity).")

    return float(structural_similarity(a, b, data_range=data_range, channel_axis=None))


def to_bool_mask(x: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """
    Chuyển về mask nhị phân.
    - Nếu x là bool -> giữ nguyên
    - Nếu x là uint8 -> dùng x > threshold (threshold mặc định 0.5, thường dùng 0 hoặc 127 tùy dữ liệu)
    """
    arr = np.asarray(x)
    if arr.dtype == bool:
        return arr
    if arr.ndim == 3:
        arr = arr[..., 0]
    return (arr.astype(np.float64) > float(threshold))


def dice_binary(mask_true: np.ndarray, mask_pred: np.ndarray, eps: float = 1e-12) -> float:
    """
    Dice cho 2 mask nhị phân.
    DSC = 2|A∩B| / (|A|+|B|). :contentReference[oaicite:8]{index=8}
    """
    a = to_bool_mask(mask_true).ravel()
    b = to_bool_mask(mask_pred).ravel()
    if a.shape != b.shape:
        raise ValueError("mask_true và mask_pred phải cùng số phần tử.")

    inter = float(np.sum(a & b))
    sa = float(np.sum(a))
    sb = float(np.sum(b))
    return float((2.0 * inter) / (sa + sb + eps))


def dice_multiclass(
    labels_true: np.ndarray,
    labels_pred: np.ndarray,
    num_classes: Optional[int] = None,
    ignore_label: Optional[int] = None,
    eps: float = 1e-12,
) -> Tuple[float, Dict[int, float]]:
    """
    Dice cho segmentation đa lớp (nhãn nguyên 0..C-1).
    Trả về (mean_dice, dice_per_class).
    - ignore_label: bỏ qua 1 nhãn (ví dụ background = 0) nếu cần.
    """
    lt = np.asarray(labels_true)
    lp = np.asarray(labels_pred)
    if lt.ndim == 3:
        lt = lt[..., 0]
    if lp.ndim == 3:
        lp = lp[..., 0]
    if lt.shape != lp.shape:
        raise ValueError("labels_true và labels_pred phải cùng shape.")

    lt = lt.astype(np.int64)
    lp = lp.astype(np.int64)

    if num_classes is None:
        num_classes = int(max(lt.max(initial=0), lp.max(initial=0)) + 1)

    dices: Dict[int, float] = {}
    vals: list[float] = []

    for c in range(num_classes):
        if ignore_label is not None and c == int(ignore_label):
            continue
        a = (lt == c)
        b = (lp == c)
        inter = float(np.sum(a & b))
        sa = float(np.sum(a))
        sb = float(np.sum(b))
        d = float((2.0 * inter) / (sa + sb + eps))
        dices[c] = d
        vals.append(d)

    mean_dice = float(np.mean(vals)) if vals else 0.0
    return mean_dice, dices

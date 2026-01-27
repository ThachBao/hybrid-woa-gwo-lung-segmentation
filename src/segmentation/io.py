# đọc/ghi ảnh, chuẩn hóa grayscale
# src/segmentation/io.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional
import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None


def ensure_dir(path: str | os.PathLike) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def to_uint8_gray(img: np.ndarray) -> np.ndarray:
    arr = np.asarray(img)
    if arr.ndim == 3:
        # nếu RGB/BGR -> lấy kênh đầu tiên nếu không biết thứ tự
        arr = arr[..., 0]
    if arr.ndim != 2:
        raise ValueError("Ảnh phải có dạng 2D (grayscale) sau khi chuyển đổi.")
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return arr


def read_image_gray(path: str | os.PathLike) -> np.ndarray:
    p = str(path)
    if cv2 is not None:
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(p)
        return to_uint8_gray(img)

    if Image is None:
        raise RuntimeError("Không có cv2 hoặc PIL để đọc ảnh.")

    im = Image.open(p).convert("L")
    return np.array(im, dtype=np.uint8)


def decode_image_gray(file_bytes: bytes) -> np.ndarray:
    if cv2 is not None:
        buf = np.frombuffer(file_bytes, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError("Không giải mã được ảnh.")
        return to_uint8_gray(img)

    if Image is None:
        raise RuntimeError("Không có cv2 hoặc PIL để decode ảnh.")

    from io import BytesIO

    im = Image.open(BytesIO(file_bytes)).convert("L")
    return np.array(im, dtype=np.uint8)


def save_image_gray(path: str | os.PathLike, image_u8: np.ndarray) -> None:
    p = str(path)
    ensure_dir(Path(p).parent)
    img = to_uint8_gray(image_u8)

    if cv2 is not None:
        ok = cv2.imwrite(p, img)
        if not ok:
            raise IOError(f"Không ghi được ảnh: {p}")
        return

    if Image is None:
        raise RuntimeError("Không có cv2 hoặc PIL để ghi ảnh.")

    Image.fromarray(img, mode="L").save(p)


def list_image_files(root: str | os.PathLike, exts: Optional[Iterable[str]] = None) -> List[str]:
    root = str(root)
    exts = exts or (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")
    exts = tuple(e.lower() for e in exts)

    paths: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(exts):
                paths.append(os.path.join(dirpath, fn))
    paths.sort()
    return paths

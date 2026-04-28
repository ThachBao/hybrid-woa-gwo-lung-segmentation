from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
DEFAULT_CXR_ROOT = Path("dataset") / "Chest Xray"

_CASES: Dict[str, Dict] = {}
_ROOT = DEFAULT_CXR_ROOT
_DATASET_DIR = DEFAULT_CXR_ROOT
_IMAGE_DIR = DEFAULT_CXR_ROOT / "CXR_png"
_MASK_DIR = DEFAULT_CXR_ROOT / "masks"


def _source_name(case_id: str) -> str:
    upper = case_id.upper()
    if upper.startswith("MCUCXR"):
        return "montgomery"
    if upper.startswith("CHNCXR"):
        return "other"
    return "other"


def _image_files(directory: Path) -> Iterable[Path]:
    if not directory.exists():
        return []
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def _resolve_dataset_dirs(root_dir: str | Path) -> Tuple[Path, Path, Path]:
    """Resolve the actual Lung Segmentation folder while keeping the public root stable.

    Some downloaded archives extract as:
    - dataset/Chest Xray/CXR_png
    - dataset/Chest Xray/Lung Segmentation/CXR_png
    - dataset/Chest Xray/data/Lung Segmentation/CXR_png
    """
    root = Path(root_dir)
    preferred = [
        root,
        root / "Lung Segmentation",
        root / "data" / "Lung Segmentation",
    ]
    for base in preferred:
        image_dir = base / "CXR_png"
        mask_dir = base / "masks"
        if image_dir.exists() and mask_dir.exists():
            return base, image_dir, mask_dir

    for image_dir in root.rglob("CXR_png") if root.exists() else []:
        if not image_dir.is_dir():
            continue
        base = image_dir.parent
        mask_dir = base / "masks"
        if mask_dir.exists():
            return base, image_dir, mask_dir

    return root, root / "CXR_png", root / "masks"


def _mask_lookup(mask_dir: Path) -> Dict[str, Path]:
    lookup: Dict[str, Path] = {}
    for path in _image_files(mask_dir):
        stem = path.stem
        candidates = {
            stem,
            stem.replace("_mask", ""),
            stem.replace("-mask", ""),
            stem.replace(" mask", ""),
        }
        for key in candidates:
            lookup.setdefault(key, path)
    return lookup


def scan_cxr_dataset(root_dir: str | Path = DEFAULT_CXR_ROOT) -> List[Dict]:
    """Scan CXR images and masks, mapping pairs by file stem.

    Images are read from ``CXR_png`` and masks from ``masks`` under ``root_dir``.
    Cases without masks are kept for qualitative demo, but ``has_mask`` is false.
    """
    global _CASES, _ROOT, _DATASET_DIR, _IMAGE_DIR, _MASK_DIR

    _ROOT = Path(root_dir)
    _DATASET_DIR, image_dir, mask_dir = _resolve_dataset_dirs(_ROOT)
    _IMAGE_DIR = image_dir
    _MASK_DIR = mask_dir
    masks = _mask_lookup(mask_dir)

    cases: Dict[str, Dict] = {}
    for image_path in _image_files(image_dir):
        case_id = image_path.stem
        mask_path = masks.get(case_id)
        source = _source_name(case_id)
        cases[case_id] = {
            "case_id": case_id,
            "image_path": image_path.as_posix(),
            "mask_path": mask_path.as_posix() if mask_path else None,
            "source_name": source,
            "has_mask": bool(mask_path and mask_path.exists()),
            "dataset_dir": _DATASET_DIR.as_posix(),
        }

    _CASES = dict(sorted(cases.items(), key=lambda item: (item[1]["source_name"] != "montgomery", item[0])))
    return list(_CASES.values())


def get_dataset_paths() -> Dict[str, str]:
    if not _CASES:
        scan_cxr_dataset(_ROOT)
    return {
        "dataset_root": _ROOT.as_posix(),
        "dataset_dir": _DATASET_DIR.as_posix(),
        "image_dir": _IMAGE_DIR.as_posix(),
        "mask_dir": _MASK_DIR.as_posix(),
    }


def list_cases(source: str = "all") -> List[Dict]:
    if not _CASES:
        scan_cxr_dataset(_ROOT)

    source = str(source or "all").lower()
    if source == "all":
        return list(_CASES.values())
    if source == "montgomery":
        return [case for case in _CASES.values() if case["source_name"] == "montgomery"]
    if source == "other":
        return [case for case in _CASES.values() if case["source_name"] != "montgomery"]
    raise ValueError("source must be one of: all, montgomery, other")


def load_case(case_id: str) -> Dict:
    if not _CASES:
        scan_cxr_dataset(_ROOT)
    try:
        return _CASES[case_id]
    except KeyError as exc:
        raise KeyError(f"CXR case not found: {case_id}") from exc


def load_image(case_id: str) -> np.ndarray:
    case = load_case(case_id)
    img = cv2.imread(case["image_path"], cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(case["image_path"])
    return img


def load_mask(case_id: str) -> Optional[np.ndarray]:
    case = load_case(case_id)
    mask_path = case.get("mask_path")
    if not mask_path:
        return None
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return None
    return (mask > 0).astype(np.uint8) * 255

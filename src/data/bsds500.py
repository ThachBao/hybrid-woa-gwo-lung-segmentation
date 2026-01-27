"""
BSDS500 dataset loader - Load images with ground truth boundaries
"""
from __future__ import annotations

import os
from typing import List, Tuple

import numpy as np

from src.segmentation.io import read_image_gray
from src.data.bsds500_gt import build_pairs, read_bsds_gt_boundary_mask


def load_bsds500(
    split: str = "train",
    root: str = "dataset/BDS500",
    gt_thr: float = 0.5,
    gt_fuse: str = "max",
    limit: int = 0,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Load BSDS500 dataset với ground truth boundaries
    
    Args:
        split: "train", "val", hoặc "test"
        root: Đường dẫn root của BDS500
        gt_thr: Threshold để tạo binary mask từ GT
        gt_fuse: "max" hoặc "mean" để gộp nhiều annotator
        limit: Giới hạn số ảnh (0 = không giới hạn)
    
    Returns:
        List of (image_gray, gt_boundary_mask)
        - image_gray: (H, W) uint8
        - gt_boundary_mask: (H, W) bool
    
    Example:
        >>> data = load_bsds500("train", limit=10)
        >>> for img, gt in data:
        ...     print(img.shape, gt.shape)
    """
    images_dir = os.path.join(root, "images", split)
    gt_dir = os.path.join(root, "ground_truth", split)
    
    if not os.path.exists(images_dir):
        raise FileNotFoundError(f"Không tìm thấy thư mục ảnh: {images_dir}")
    
    if not os.path.exists(gt_dir):
        raise FileNotFoundError(f"Không tìm thấy thư mục ground truth: {gt_dir}")
    
    # Build pairs (image_path, gt_path)
    pairs = build_pairs(images_dir, gt_dir)
    
    if limit > 0:
        pairs = pairs[:limit]
    
    # Load images and GT
    dataset = []
    for img_path, gt_path in pairs:
        try:
            # Load image
            img = read_image_gray(img_path)
            
            # Load GT boundary mask
            gt = read_bsds_gt_boundary_mask(gt_path, thr=gt_thr, fuse=gt_fuse)
            
            # Ensure same shape
            if img.shape != gt.shape:
                raise ValueError(f"Shape mismatch: img={img.shape}, gt={gt.shape}")
            
            dataset.append((img, gt))
        except Exception as e:
            print(f"Warning: Không thể load {img_path}: {e}")
            continue
    
    return dataset


def load_bsds500_info(
    split: str = "train",
    root: str = "dataset/BDS500",
) -> List[Tuple[str, str, str]]:
    """
    Load thông tin về dataset (không load ảnh vào memory)
    
    Returns:
        List of (image_id, image_path, gt_path)
    """
    images_dir = os.path.join(root, "images", split)
    gt_dir = os.path.join(root, "ground_truth", split)
    
    pairs = build_pairs(images_dir, gt_dir)
    
    result = []
    for img_path, gt_path in pairs:
        from pathlib import Path
        image_id = Path(img_path).stem
        result.append((image_id, img_path, gt_path))
    
    return result

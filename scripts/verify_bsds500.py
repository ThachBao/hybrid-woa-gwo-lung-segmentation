#!/usr/bin/env python
"""
Script kiểm tra tính toàn vẹn của BSDS500 dataset
"""
import os
import sys
import glob

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.bsds500_gt import build_pairs, read_bsds_gt_boundary_mask
from src.segmentation.io import read_image_gray


def verify_bsds500():
    """Kiểm tra tính toàn vẹn của BSDS500"""
    
    splits = ['train', 'val', 'test']
    expected_counts = {'train': 200, 'val': 100, 'test': 200}
    
    print("="*60)
    print("KIỂM TRA BỘ DỮ LIỆU BSDS500")
    print("="*60)
    
    all_ok = True
    
    for split in splits:
        print(f"\n{split.upper()}:")
        
        # Kiểm tra images
        img_dir = f"dataset/BDS500/images/{split}"
        if not os.path.exists(img_dir):
            print(f"  ✗ Thư mục không tồn tại: {img_dir}")
            all_ok = False
            continue
            
        img_files = glob.glob(f"{img_dir}/*.jpg")
        
        # Kiểm tra ground truth
        gt_dir = f"dataset/BDS500/ground_truth/{split}"
        if not os.path.exists(gt_dir):
            print(f"  ✗ Thư mục không tồn tại: {gt_dir}")
            all_ok = False
            continue
            
        gt_files = glob.glob(f"{gt_dir}/*.mat")
        
        print(f"  Images: {len(img_files)}/{expected_counts[split]}")
        print(f"  Ground Truth: {len(gt_files)}/{expected_counts[split]}")
        
        if len(img_files) != expected_counts[split]:
            print(f"  ⚠️  Số lượng ảnh không đúng!")
            all_ok = False
        
        if len(gt_files) != expected_counts[split]:
            print(f"  ⚠️  Số lượng GT không đúng!")
            all_ok = False
        
        # Kiểm tra matching
        img_ids = set([os.path.splitext(os.path.basename(f))[0] for f in img_files])
        gt_ids = set([os.path.splitext(os.path.basename(f))[0] for f in gt_files])
        
        if img_ids == gt_ids:
            print(f"  ✓ Matching: OK")
        else:
            print(f"  ✗ Matching: FAILED")
            all_ok = False
            missing_gt = img_ids - gt_ids
            missing_img = gt_ids - img_ids
            if missing_gt:
                print(f"    Missing GT: {list(missing_gt)[:5]}...")
            if missing_img:
                print(f"    Missing Images: {list(missing_img)[:5]}...")
        
        # Kiểm tra ghép cặp
        try:
            pairs = build_pairs(img_dir, gt_dir)
            print(f"  Pairs found: {len(pairs)}")
            
            if len(pairs) != expected_counts[split]:
                print(f"  ⚠️  Số cặp không đúng!")
                all_ok = False
        except Exception as e:
            print(f"  ✗ Lỗi khi ghép cặp: {e}")
            all_ok = False
            continue
        
        # Test đọc 1 ảnh
        if pairs:
            img_path, gt_path = pairs[0]
            try:
                gray = read_image_gray(img_path)
                gt_mask = read_bsds_gt_boundary_mask(gt_path)
                print(f"  ✓ Sample read: {os.path.basename(img_path)}")
                print(f"    Image shape: {gray.shape}")
                print(f"    Image dtype: {gray.dtype}")
                print(f"    Image range: [{gray.min()}, {gray.max()}]")
                print(f"    GT shape: {gt_mask.shape}")
                print(f"    GT dtype: {gt_mask.dtype}")
                print(f"    Boundary pixels: {gt_mask.sum()} ({gt_mask.sum()/gt_mask.size*100:.2f}%)")
            except Exception as e:
                print(f"  ✗ Sample read failed: {e}")
                all_ok = False
    
    print("\n" + "="*60)
    if all_ok:
        print("✓ KIỂM TRA HOÀN TẤT - TẤT CẢ ĐỀU OK")
    else:
        print("✗ KIỂM TRA HOÀN TẤT - CÓ LỖI")
    print("="*60)
    
    return all_ok


if __name__ == "__main__":
    success = verify_bsds500()
    sys.exit(0 if success else 1)

"""
Evaluate global thresholds on BSDS500 test set
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
import numpy as np

from src.segmentation.io import read_image_gray
from src.segmentation.apply_thresholds import apply_thresholds
from src.data.bsds500_gt import build_pairs, read_bsds_gt_boundary_mask, seg_to_boundary_mask, dice_binary


def main():
    ap = argparse.ArgumentParser(description="Đánh giá ngưỡng tối ưu toàn cục trên BSDS500")
    ap.add_argument("--images_root", type=str, default="dataset/BDS500/images")
    ap.add_argument("--gt_root", type=str, default="dataset/BDS500/ground_truth")
    ap.add_argument("--split", type=str, default="test")
    ap.add_argument("--thresholds_json", type=str, required=True, help="File JSON chứa ngưỡng tối ưu")
    ap.add_argument("--gt_thr", type=float, default=0.5)
    ap.add_argument("--gt_fuse", type=str, default="max")
    ap.add_argument("--out_csv", type=str, default="")  # Nếu rỗng thì không lưu CSV
    ap.add_argument("--limit", type=int, default=0)  # Giới hạn số ảnh test
    args = ap.parse_args()

    print("=" * 80)
    print("ĐÁNH GIÁ NGƯỠNG TỐI ƯU TOÀN CỤC TRÊN BSDS500")
    print("=" * 80)

    # Đọc ngưỡng từ file JSON
    with open(args.thresholds_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    t = np.array(data["thresholds"], dtype=int)
    
    print(f"Đã tải ngưỡng từ: {args.thresholds_json}")
    print(f"  k = {data.get('k', len(t))}")
    print(f"  Ngưỡng: {t.tolist()}")
    print(f"  Algorithm: {data.get('algo', 'N/A')} {data.get('strategy', '')}")
    print(f"  Mean DICE (train): {data.get('mean_boundary_dice', 'N/A'):.4f}")
    print(f"  Số ảnh train: {data.get('num_images', 'N/A')}")
    print("=" * 80)

    images_dir = os.path.join(args.images_root, args.split)
    gt_dir = os.path.join(args.gt_root, args.split)
    pairs = build_pairs(images_dir, gt_dir)
    
    if args.limit and args.limit > 0:
        pairs = pairs[:args.limit]
    
    if not pairs:
        raise RuntimeError("Không tìm được cặp (image, gt).")

    print(f"\nĐang đánh giá trên {len(pairs)} ảnh từ split '{args.split}'...")
    print("-" * 80)

    start_time = time.time()
    dices = []
    rows = []
    
    for idx, (img_path, gt_path) in enumerate(pairs):
        gray = read_image_gray(img_path)
        seg = apply_thresholds(gray, t)
        pred_b = seg_to_boundary_mask(seg)
        gt_b = read_bsds_gt_boundary_mask(gt_path, thr=args.gt_thr, fuse=args.gt_fuse)
        dice = dice_binary(gt_b, pred_b)
        dices.append(dice)
        
        img_name = os.path.basename(img_path)
        print(f"[{idx+1}/{len(pairs)}] {img_name}: DICE={dice:.4f}")
        
        if args.out_csv:
            rows.append({
                "index": idx,
                "image": img_path,
                "gt": gt_path,
                "dice_boundary": float(dice),
            })

    eval_time = time.time() - start_time
    mean_dice = float(np.mean(dices))
    std_dice = float(np.std(dices))
    min_dice = float(np.min(dices))
    max_dice = float(np.max(dices))

    print("=" * 80)
    print("KẾT QUẢ ĐÁNH GIÁ")
    print("=" * 80)
    print(f"Split: {args.split}")
    print(f"Số ảnh: {len(pairs)}")
    print(f"Thời gian: {eval_time:.2f}s")
    print(f"Mean Boundary-DICE: {mean_dice:.4f}")
    print(f"Std DICE: {std_dice:.4f}")
    print(f"Min DICE: {min_dice:.4f}")
    print(f"Max DICE: {max_dice:.4f}")
    print("=" * 80)

    # So sánh với train
    if "mean_boundary_dice" in data:
        train_dice = data["mean_boundary_dice"]
        diff = mean_dice - train_dice
        print(f"\nSo sánh với train:")
        print(f"  Train DICE: {train_dice:.4f}")
        print(f"  Test DICE:  {mean_dice:.4f}")
        print(f"  Chênh lệch: {diff:+.4f} ({diff/train_dice*100:+.2f}%)")
        print("=" * 80)

    # Lưu CSV nếu cần
    if args.out_csv:
        os.makedirs(os.path.dirname(args.out_csv) if os.path.dirname(args.out_csv) else ".", exist_ok=True)
        with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["index", "image", "gt", "dice_boundary", "mean_dice", "std_dice"]
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                rr = dict(r)
                rr["mean_dice"] = ""
                rr["std_dice"] = ""
                w.writerow(rr)
            # Dòng cuối: summary
            w.writerow({
                "index": "",
                "image": "",
                "gt": "",
                "dice_boundary": "",
                "mean_dice": mean_dice,
                "std_dice": std_dice,
            })
        print(f"\n✓ Đã lưu kết quả chi tiết vào: {args.out_csv}")


if __name__ == "__main__":
    main()

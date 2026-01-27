"""
Phân tích kết quả đánh giá BDS500
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np


def load_results(json_path: str) -> List[Dict]:
    """Load kết quả từ JSON file"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_results(results: List[Dict]):
    """Phân tích và in báo cáo"""
    print("=" * 80)
    print("PHÂN TÍCH KẾT QUẢ BDS500")
    print("=" * 80)
    
    # Filter out errors
    valid_results = [r for r in results if "error" not in r]
    error_results = [r for r in results if "error" in r]
    
    if error_results:
        print(f"\n⚠️  Có {len(error_results)} lỗi:")
        for r in error_results[:5]:  # Show first 5 errors
            print(f"  - {r['image_id']} / {r['algorithm']}: {r['error']}")
        if len(error_results) > 5:
            print(f"  ... và {len(error_results) - 5} lỗi khác")
    
    print(f"\nTổng số kết quả hợp lệ: {len(valid_results)}")
    
    # Group by algorithm
    algorithms = sorted(set(r["algorithm"] for r in valid_results))
    
    print(f"\nThuật toán: {algorithms}")
    print()
    
    # Statistics by algorithm
    print("=" * 80)
    print("THỐNG KÊ THEO THUẬT TOÁN")
    print("=" * 80)
    
    algo_stats = {}
    for algo in algorithms:
        algo_results = [r for r in valid_results if r["algorithm"] == algo]
        
        if not algo_results:
            continue
        
        dices = [r["dice"] for r in algo_results]
        entropies = [r["entropy"] for r in algo_results]
        times = [r["time"] for r in algo_results]
        
        stats = {
            "n": len(algo_results),
            "dice_mean": float(np.mean(dices)),
            "dice_std": float(np.std(dices)),
            "dice_min": float(np.min(dices)),
            "dice_max": float(np.max(dices)),
            "dice_median": float(np.median(dices)),
            "entropy_mean": float(np.mean(entropies)),
            "entropy_std": float(np.std(entropies)),
            "time_mean": float(np.mean(times)),
            "time_std": float(np.std(times)),
        }
        
        algo_stats[algo] = stats
        
        print(f"\n{algo}:")
        print(f"  Số ảnh: {stats['n']}")
        print(f"  DICE:")
        print(f"    Mean:   {stats['dice_mean']:.4f}")
        print(f"    Std:    {stats['dice_std']:.4f}")
        print(f"    Median: {stats['dice_median']:.4f}")
        print(f"    Range:  [{stats['dice_min']:.4f}, {stats['dice_max']:.4f}]")
        print(f"  Entropy:")
        print(f"    Mean:   {stats['entropy_mean']:.4f}")
        print(f"    Std:    {stats['entropy_std']:.4f}")
        print(f"  Time:")
        print(f"    Mean:   {stats['time_mean']:.2f}s")
        print(f"    Std:    {stats['time_std']:.2f}s")
    
    # Ranking by DICE
    print()
    print("=" * 80)
    print("RANKING (theo DICE mean)")
    print("=" * 80)
    
    ranked = sorted(algo_stats.items(), key=lambda x: x[1]["dice_mean"], reverse=True)
    
    for rank, (algo, stats) in enumerate(ranked, 1):
        print(f"{rank}. {algo:15s} DICE={stats['dice_mean']:.4f} ± {stats['dice_std']:.4f}")
    
    # Best/Worst images
    print()
    print("=" * 80)
    print("BEST/WORST IMAGES")
    print("=" * 80)
    
    # Group by image
    images = sorted(set(r["image_id"] for r in valid_results))
    
    image_stats = {}
    for img_id in images:
        img_results = [r for r in valid_results if r["image_id"] == img_id]
        dices = [r["dice"] for r in img_results]
        
        if dices:
            image_stats[img_id] = {
                "dice_mean": float(np.mean(dices)),
                "dice_std": float(np.std(dices)),
                "dice_min": float(np.min(dices)),
                "dice_max": float(np.max(dices)),
            }
    
    # Top 5 best
    best_images = sorted(image_stats.items(), key=lambda x: x[1]["dice_mean"], reverse=True)[:5]
    print("\nTop 5 ảnh tốt nhất (DICE cao):")
    for img_id, stats in best_images:
        print(f"  {img_id}: {stats['dice_mean']:.4f} ± {stats['dice_std']:.4f}")
    
    # Top 5 worst
    worst_images = sorted(image_stats.items(), key=lambda x: x[1]["dice_mean"])[:5]
    print("\nTop 5 ảnh khó nhất (DICE thấp):")
    for img_id, stats in worst_images:
        print(f"  {img_id}: {stats['dice_mean']:.4f} ± {stats['dice_std']:.4f}")
    
    # Variance analysis
    print()
    print("=" * 80)
    print("PHÂN TÍCH VARIANCE")
    print("=" * 80)
    
    print("\nĐộ biến thiên giữa các thuật toán (theo ảnh):")
    high_variance_images = sorted(image_stats.items(), key=lambda x: x[1]["dice_std"], reverse=True)[:5]
    for img_id, stats in high_variance_images:
        print(f"  {img_id}: std={stats['dice_std']:.4f}, "
              f"range=[{stats['dice_min']:.4f}, {stats['dice_max']:.4f}]")
    
    print()
    print("=" * 80)
    print("CẢNH BÁO")
    print("=" * 80)
    print("Nếu chỉ chạy 1 seed:")
    print("  - Không thể kết luận thuật toán nào tốt hơn")
    print("  - Kết quả có thể do may mắn")
    print("  - Cần chạy nhiều seed và tính mean/std")
    print()
    print("Để so sánh thuật toán đúng cách:")
    print("  - Chạy ít nhất 30 seeds khác nhau")
    print("  - Tính mean và std của DICE cho mỗi thuật toán")
    print("  - Dùng statistical test (paired t-test, Wilcoxon signed-rank)")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Phân tích kết quả BDS500")
    parser.add_argument("json_file", type=str, help="Đường dẫn đến file JSON kết quả")
    args = parser.parse_args()
    
    if not Path(args.json_file).exists():
        print(f"ERROR: Không tìm thấy file: {args.json_file}")
        return
    
    results = load_results(args.json_file)
    analyze_results(results)


if __name__ == "__main__":
    main()

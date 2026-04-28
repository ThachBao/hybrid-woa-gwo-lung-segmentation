"""
Đánh giá toàn bộ dataset BDS500 với K=10 và Seed=42

CẢNH BÁO: Đây là chế độ DEBUG/REPRODUCIBILITY
- Chỉ 1 seed → không đủ dữ liệu để kết luận thuật toán nào tốt hơn
- Chỉ dùng để kiểm tra pipeline và debug
- Để so sánh thuật toán, cần chạy nhiều seed và tính mean/std
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np

from src.data.bsds500 import load_bsds500
from src.objective.fuzzy_entropy_s import fuzzy_entropy_objective
from src.optim.bounds import repair_threshold_vector
from src.optim.gwo import GWO
from src.optim.woa import WOA
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA
from src.segmentation.apply_thresholds import apply_thresholds
from src.data.bsds500_gt import seg_to_boundary_mask, dice_binary

# ============================================================
# SETUP LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CẤU HÌNH CỐ ĐỊNH (KHÔNG THAY ĐỔI)
# ============================================================
K = 3       # Số ngưỡng (11 lớp)
SEED = 42       # Seed cố định cho reproducibility
LB = 0          # Lower bound
UB = 255        # Upper bound

# Tham số optimizer
N_AGENTS = 30
N_ITERS = 80
WOA_B = 1.0
SHARE_INTERVAL = 10

# Dataset
SPLIT = "train"  # "train", "val", hoặc "test"
LIMIT = 0        # 0 = không giới hạn, >0 = giới hạn số ảnh

# Output
OUTPUT_DIR = "outputs/bds500_eval"

# ============================================================
# THUẬT TOÁN CẦN ĐÁNH GIÁ
# ============================================================
ALGORITHMS = {
    "GWO": {"type": "GWO"},
    "WOA": {"type": "WOA"},
    "HYBRID-PA1": {"type": "HYBRID", "strategy": "PA1"},
    "HYBRID-PA2": {"type": "HYBRID", "strategy": "PA2"},
    "HYBRID-PA3": {"type": "HYBRID", "strategy": "PA3"},
    "HYBRID-PA4": {"type": "HYBRID", "strategy": "PA4"},
    "HYBRID-PA5": {"type": "HYBRID", "strategy": "PA5"},
    "HYBRID-PA6": {"type": "HYBRID", "strategy": "PA6"},
}


def make_optimizer(algo_config: Dict, seed: int):
    """Tạo optimizer từ config"""
    algo_type = algo_config["type"]
    
    if algo_type == "GWO":
        return GWO(n_agents=N_AGENTS, n_iters=N_ITERS, seed=seed)
    
    elif algo_type == "WOA":
        return WOA(n_agents=N_AGENTS, n_iters=N_ITERS, seed=seed, b=WOA_B)
    
    elif algo_type == "HYBRID":
        strategy = algo_config.get("strategy", "PA1")
        return HybridGWO_WOA(
            n_agents=N_AGENTS,
            n_iters=N_ITERS,
            seed=seed,
            strategy=strategy,
            woa_b=WOA_B,
            share_interval=SHARE_INTERVAL,
        )
    
    else:
        raise ValueError(f"Unknown algorithm type: {algo_type}")


def repair_fn(x: np.ndarray) -> np.ndarray:
    """Repair function cho ngưỡng"""
    return repair_threshold_vector(
        x, k=K, lb=LB, ub=UB,
        integer=True,
        ensure_unique=True,
        avoid_endpoints=True,
    )


def evaluate_single_image(
    image_id: str,
    img: np.ndarray,
    gt_boundary: np.ndarray,
    algo_name: str,
    algo_config: Dict,
) -> Dict:
    """
    Đánh giá 1 ảnh với 1 thuật toán
    
    Returns:
        Dict chứa kết quả
    """
    # Fix seed để reproducible
    np.random.seed(SEED)
    
    # Tạo fitness function
    def fitness_fn(x: np.ndarray) -> float:
        return float(fuzzy_entropy_objective(img, repair_fn(x)))
    
    # Tạo optimizer
    optimizer = make_optimizer(algo_config, seed=SEED)
    
    # Chạy optimization
    start_time = time.time()
    best_x, best_f, history = optimizer.optimize(
        fitness_fn,
        dim=K,
        lb=np.full(K, LB, dtype=float),
        ub=np.full(K, UB, dtype=float),
        repair_fn=repair_fn,
        init_pop=None,
    )
    elapsed_time = time.time() - start_time
    
    # Repair final thresholds
    best_x = repair_fn(best_x)
    
    # Apply thresholds
    segmented = apply_thresholds(img, best_x)
    
    # Extract boundary từ segmentation
    pred_boundary = seg_to_boundary_mask(segmented)
    
    # Tính DICE
    dice = dice_binary(pred_boundary, gt_boundary)
    
    # Entropy (maximize) = -best_f
    entropy = -best_f
    
    return {
        "image_id": image_id,
        "algorithm": algo_name,
        "seed": SEED,
        "K": K,
        "dice": float(dice),
        "entropy": float(entropy),
        "best_f": float(best_f),
        "time": float(elapsed_time),
        "thresholds": best_x.tolist(),
        "n_iters": len(history),
    }


def main():
    """Main evaluation loop"""
    print("=" * 80)
    print("ĐÁNH GIÁ BDS500 - K=10, SEED=42")
    print("=" * 80)
    print(f"Cấu hình:")
    print(f"  K = {K} (số ngưỡng)")
    print(f"  SEED = {SEED}")
    print(f"  N_AGENTS = {N_AGENTS}")
    print(f"  N_ITERS = {N_ITERS}")
    print(f"  SPLIT = {SPLIT}")
    print(f"  LIMIT = {LIMIT if LIMIT > 0 else 'không giới hạn'}")
    print(f"  Thuật toán: {list(ALGORITHMS.keys())}")
    print()
    
    # Load dataset
    print("Đang load dataset...")
    dataset = load_bsds500(split=SPLIT, limit=LIMIT)
    print(f"✓ Đã load {len(dataset)} ảnh từ split '{SPLIT}'")
    print()
    
    if len(dataset) == 0:
        print("ERROR: Không có ảnh nào được load!")
        return
    
    # Tạo output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(OUTPUT_DIR, f"k{K}_seed{SEED}_{SPLIT}_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    print(f"Output directory: {run_dir}")
    print()
    
    # Evaluate
    results: List[Dict] = []
    total_images = len(dataset)
    total_algos = len(ALGORITHMS)
    total_runs = total_images * total_algos
    
    print(f"Bắt đầu đánh giá: {total_images} ảnh × {total_algos} thuật toán = {total_runs} runs")
    print("=" * 80)
    
    run_count = 0
    for img_idx, (img, gt_boundary) in enumerate(dataset):
        image_id = f"img_{img_idx:04d}"
        
        print(f"\n[{img_idx+1}/{total_images}] Image: {image_id}, Shape: {img.shape}")
        
        for algo_name, algo_config in ALGORITHMS.items():
            run_count += 1
            print(f"  [{run_count}/{total_runs}] {algo_name}...", end=" ", flush=True)
            
            try:
                result = evaluate_single_image(
                    image_id, img, gt_boundary, algo_name, algo_config
                )
                results.append(result)
                
                print(f"DICE={result['dice']:.4f}, Entropy={result['entropy']:.4f}, "
                      f"Time={result['time']:.2f}s")
                
            except Exception as e:
                print(f"ERROR: {e}")
                results.append({
                    "image_id": image_id,
                    "algorithm": algo_name,
                    "seed": SEED,
                    "K": K,
                    "error": str(e),
                })
    
    print()
    print("=" * 80)
    print("HOÀN THÀNH ĐÁNH GIÁ")
    print("=" * 80)
    
    # Save results
    output_file = os.path.join(run_dir, f"results_k{K}_seed{SEED}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Đã lưu kết quả: {output_file}")
    
    # Tính summary statistics
    print()
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    # Group by algorithm
    algo_stats = {}
    for algo_name in ALGORITHMS.keys():
        algo_results = [r for r in results if r.get("algorithm") == algo_name and "error" not in r]
        
        if algo_results:
            dices = [r["dice"] for r in algo_results]
            entropies = [r["entropy"] for r in algo_results]
            times = [r["time"] for r in algo_results]
            
            algo_stats[algo_name] = {
                "n_images": len(algo_results),
                "dice_mean": float(np.mean(dices)),
                "dice_std": float(np.std(dices)),
                "dice_min": float(np.min(dices)),
                "dice_max": float(np.max(dices)),
                "entropy_mean": float(np.mean(entropies)),
                "time_mean": float(np.mean(times)),
            }
    
    # Print summary
    for algo_name, stats in algo_stats.items():
        print(f"\n{algo_name}:")
        print(f"  DICE: {stats['dice_mean']:.4f} ± {stats['dice_std']:.4f} "
              f"[{stats['dice_min']:.4f}, {stats['dice_max']:.4f}]")
        print(f"  Entropy: {stats['entropy_mean']:.4f}")
        print(f"  Time: {stats['time_mean']:.2f}s")
    
    # Save summary
    summary_file = os.path.join(run_dir, f"summary_k{K}_seed{SEED}.json")
    summary_data = {
        "config": {
            "K": K,
            "SEED": SEED,
            "N_AGENTS": N_AGENTS,
            "N_ITERS": N_ITERS,
            "SPLIT": SPLIT,
            "n_images": total_images,
            "algorithms": list(ALGORITHMS.keys()),
        },
        "statistics": algo_stats,
        "warning": "Chỉ 1 seed - không đủ dữ liệu để kết luận thuật toán nào tốt hơn. "
                   "Kết quả chỉ dùng để debug và kiểm tra pipeline.",
    }
    
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Đã lưu summary: {summary_file}")
    
    print()
    print("=" * 80)
    print("CẢNH BÁO")
    print("=" * 80)
    print("Kết quả này chỉ dùng để:")
    print("  - Kiểm tra pipeline chạy đúng chưa")
    print("  - Debug thuật toán")
    print("  - Reproducibility (với seed=42)")
    print()
    print("KHÔNG được dùng để:")
    print("  - Kết luận thuật toán nào tốt hơn")
    print("  - So sánh hiệu năng")
    print()
    print("Để so sánh thuật toán, cần:")
    print("  - Chạy nhiều seed khác nhau (ví dụ: 30 seeds)")
    print("  - Tính mean và std của DICE")
    print("  - Dùng statistical test (t-test, Wilcoxon, etc.)")
    print("=" * 80)


if __name__ == "__main__":
    main()

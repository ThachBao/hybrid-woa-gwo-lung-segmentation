"""
Test script để kiểm tra compare_gwo_woa_strategies.py hoạt động đúng.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
from src.objective.fuzzy_entropy import fuzzy_entropy_objective
from src.objective.thresholding_with_penalties import (
    compute_fe_stability_convergence,
    compute_fe_stability_jitter,
)
from src.optim.bounds import repair_threshold_vector
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA

def test_compare_script():
    """Test các thành phần chính của script"""
    print("=" * 80)
    print("TEST COMPARE GWO-WOA SCRIPT")
    print("=" * 80)
    
    # Test 1: Tạo ảnh test
    print("\n1. Tạo ảnh test...")
    np.random.seed(42)
    gray = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    print(f"   ✓ Ảnh test: {gray.shape}")
    
    # Test 2: Repair function
    print("\n2. Test repair function...")
    k = 4
    lb = 0
    ub = 255
    
    def repair_fn(x):
        return repair_threshold_vector(
            x, k=k, lb=lb, ub=ub,
            integer=True, ensure_unique=True, avoid_endpoints=True
        )
    
    test_x = np.array([50, 100, 150, 200])
    repaired = repair_fn(test_x)
    print(f"   Input: {test_x}")
    print(f"   Repaired: {repaired}")
    print(f"   ✓ Repair function works")
    
    # Test 3: Fitness function
    print("\n3. Test fitness function...")
    def fitness_fn(x):
        return float(fuzzy_entropy_objective(gray, repair_fn(x)))
    
    fe = fitness_fn(test_x)
    print(f"   FE: {fe:.6f}")
    print(f"   ✓ Fitness function works")
    
    # Test 4: HybridGWO_WOA
    print("\n4. Test HybridGWO_WOA...")
    strategies = ["PA1", "PA2", "PA3"]
    
    for strat in strategies:
        print(f"\n   Testing {strat}...")
        opt = HybridGWO_WOA(
            n_agents=5,
            n_iters=3,
            seed=42,
            strategy=strat,
            woa_b=1.0,
            share_interval=1,
        )
        
        best_x, best_f, history = opt.optimize(
            fitness_fn,
            dim=k,
            lb=np.full(k, lb, dtype=float),
            ub=np.full(k, ub, dtype=float),
            repair_fn=repair_fn,
            init_pop=None,
        )
        
        fe_best = float(-best_f)
        print(f"     FE best: {fe_best:.6f}")
        print(f"     Thresholds: {best_x}")
        print(f"     History length: {len(history)}")
        print(f"     ✓ {strat} works")
    
    # Test 5: FE Stability (Jitter)
    print("\n5. Test FE Stability (Jitter)...")
    stab_j = compute_fe_stability_jitter(
        gray, repaired, repair_fn,
        n_samples=5, delta=2, seed=42
    )
    print(f"   FE original: {stab_j['fe_original']:.6f}")
    print(f"   FE mean: {stab_j['fe_mean']:.6f}")
    print(f"   FE std: {stab_j['fe_std']:.6f}")
    print(f"   ✓ Jitter stability works")
    
    # Test 6: FE Stability (Convergence)
    print("\n6. Test FE Stability (Convergence)...")
    mock_history = [
        {"best_f": -5.0 + i * 0.1} for i in range(20)
    ]
    stab_c = compute_fe_stability_convergence(mock_history, last_w=5)
    print(f"   FE first: {stab_c['fe_first']:.6f}")
    print(f"   FE last: {stab_c['fe_last']:.6f}")
    print(f"   FE last std: {stab_c['fe_last_std']:.6f}")
    print(f"   ✓ Convergence stability works")
    
    print("\n" + "=" * 80)
    print("✅ TẤT CẢ TEST ĐỀU PASS!")
    print("=" * 80)
    print("\nScript compare_gwo_woa_strategies.py sẵn sàng sử dụng!")
    print("\nChạy quick test:")
    print("  Windows: run_compare_quick_test.bat")
    print("  Linux/Mac: python -m src.runner.compare_gwo_woa_strategies --root dataset/BDS500/images/val --limit 5 --k 10 --n_agents 10 --n_iters 20 --seed 42")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_compare_script()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

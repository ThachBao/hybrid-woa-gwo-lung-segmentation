"""
Test script: Verify optimization logs
"""
import numpy as np
from src.segmentation.io import read_image_gray
from src.objective.fuzzy_entropy import fuzzy_entropy_objective
from src.optim.bounds import repair_threshold_vector
from src.optim.gwo import GWO

def test_optimization_logs():
    """Test that optimization logs work correctly"""
    print("=" * 80)
    print("TEST: OPTIMIZATION LOGS")
    print("=" * 80)
    
    # Load image
    gray = read_image_gray("dataset/lena.gray.bmp")
    print(f"Image loaded: shape={gray.shape}")
    
    # Parameters
    k = 5
    lb, ub = 0, 255
    n_agents = 10
    n_iters = 20
    
    print(f"\nParameters:")
    print(f"  k = {k}")
    print(f"  n_agents = {n_agents}")
    print(f"  n_iters = {n_iters}")
    
    # Repair function
    def repair_fn(x):
        return repair_threshold_vector(
            x, k=k, lb=lb, ub=ub,
            integer=True,
            ensure_unique=True,
            avoid_endpoints=False
        )
    
    # Fitness function
    def fitness_fn(x):
        t = repair_fn(x)
        return float(fuzzy_entropy_objective(gray, t))
    
    # Optimizer
    print(f"\nCreating GWO optimizer...")
    opt = GWO(n_agents=n_agents, n_iters=n_iters, seed=42)
    
    # Optimize
    print(f"\nRunning optimization...")
    print("-" * 80)
    best_x, best_f, history = opt.optimize(
        fitness_fn,
        dim=k,
        lb=np.full(k, lb, dtype=float),
        ub=np.full(k, ub, dtype=float),
        repair_fn=repair_fn,
        init_pop=None
    )
    print("-" * 80)
    
    # Verify history
    print(f"\n✓ Optimization completed")
    print(f"  Best thresholds: {repair_fn(best_x).tolist()}")
    print(f"  Best f: {best_f:.6f}")
    print(f"  Entropy: {-best_f:.6f}")
    print(f"  History length: {len(history)}")
    
    # Check history structure
    assert len(history) == n_iters, f"History length mismatch: {len(history)} != {n_iters}"
    print(f"\n✓ History length correct: {len(history)} iterations")
    
    # Check history content
    for i, it in enumerate(history):
        assert "iter" in it, f"Missing 'iter' in history[{i}]"
        assert "best_f" in it, f"Missing 'best_f' in history[{i}]"
        assert "mean_f" in it, f"Missing 'mean_f' in history[{i}]"
        assert it["iter"] == i, f"Iter mismatch: {it['iter']} != {i}"
    
    print(f"✓ History structure correct")
    
    # Show some iterations
    print(f"\nSample iterations:")
    for i in [0, n_iters//4, n_iters//2, 3*n_iters//4, n_iters-1]:
        it = history[i]
        print(f"  Iter {it['iter']:2d}: best_f={it['best_f']:.6f}, mean_f={it['mean_f']:.6f}")
    
    # Check improvement
    first_f = history[0]["best_f"]
    last_f = history[-1]["best_f"]
    improvement = first_f - last_f
    
    print(f"\nImprovement:")
    print(f"  First: {first_f:.6f}")
    print(f"  Last: {last_f:.6f}")
    print(f"  Improvement: {improvement:.6f}")
    
    if improvement > 0:
        print(f"  ✓ Optimization improved (better fitness)")
    else:
        print(f"  ⚠️  No improvement (may need more iterations)")
    
    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED!")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        test_optimization_logs()
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

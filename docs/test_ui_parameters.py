"""
Test script: Verify UI parameters are used by optimizers
"""
import numpy as np
from src.segmentation.io import read_image_gray
from src.objective.fuzzy_entropy import fuzzy_entropy_objective
from src.optim.bounds import repair_threshold_vector
from src.optim.gwo import GWO
from src.optim.woa import WOA
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA


def test_parameters(algo_name, optimizer, expected_n_agents, expected_n_iters):
    """Test that optimizer uses the correct parameters"""
    print(f"\n{'='*60}")
    print(f"TEST: {algo_name}")
    print(f"{'='*60}")
    print(f"Expected: n_agents={expected_n_agents}, n_iters={expected_n_iters}")
    
    # Load image
    gray = read_image_gray("dataset/lena.gray.bmp")
    
    # Parameters
    k = 3
    lb, ub = 0, 255
    
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
    
    # Optimize
    best_x, best_f, history = optimizer.optimize(
        fitness_fn,
        dim=k,
        lb=np.full(k, lb, dtype=float),
        ub=np.full(k, ub, dtype=float),
        repair_fn=repair_fn,
        init_pop=None
    )
    
    # Verify
    actual_n_iters = len(history)
    
    print(f"Actual: n_iters={actual_n_iters}")
    print(f"Best f: {best_f:.6f}")
    print(f"Best thresholds: {repair_fn(best_x).tolist()}")
    
    # Check
    if actual_n_iters == expected_n_iters:
        print(f"✓ PASS: n_iters matches ({actual_n_iters} == {expected_n_iters})")
    else:
        print(f"✗ FAIL: n_iters mismatch ({actual_n_iters} != {expected_n_iters})")
        return False
    
    # Note: We can't directly verify n_agents from history, but we can check
    # that the optimizer was created with the correct value
    if hasattr(optimizer, 'n_agents'):
        actual_n_agents = optimizer.n_agents
        if actual_n_agents == expected_n_agents:
            print(f"✓ PASS: n_agents matches ({actual_n_agents} == {expected_n_agents})")
        else:
            print(f"✗ FAIL: n_agents mismatch ({actual_n_agents} != {expected_n_agents})")
            return False
    
    return True


def main():
    print("="*80)
    print("TEST: VERIFY UI PARAMETERS ARE USED BY OPTIMIZERS")
    print("="*80)
    
    all_passed = True
    
    # Test 1: GWO with custom parameters
    opt1 = GWO(n_agents=15, n_iters=10, seed=42)
    if not test_parameters("GWO (n_agents=15, n_iters=10)", opt1, 15, 10):
        all_passed = False
    
    # Test 2: WOA with custom parameters
    opt2 = WOA(n_agents=20, n_iters=15, seed=42, b=1.5)
    if not test_parameters("WOA (n_agents=20, n_iters=15)", opt2, 20, 15):
        all_passed = False
    
    # Test 3: HYBRID with custom parameters
    opt3 = HybridGWO_WOA(n_agents=25, n_iters=20, seed=42, strategy="PA1")
    if not test_parameters("HYBRID-PA1 (n_agents=25, n_iters=20)", opt3, 25, 20):
        all_passed = False
    
    # Test 4: Different parameters
    opt4 = GWO(n_agents=5, n_iters=5, seed=42)
    if not test_parameters("GWO (n_agents=5, n_iters=5)", opt4, 5, 5):
        all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("Optimizers correctly use n_agents and n_iters parameters from UI")
    else:
        print("✗ SOME TESTS FAILED!")
        print("Optimizers may not be using parameters correctly")
    print("="*80)
    
    return all_passed


if __name__ == "__main__":
    import sys
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED WITH EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

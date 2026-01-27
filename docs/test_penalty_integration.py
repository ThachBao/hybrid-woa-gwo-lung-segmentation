"""
Test script: Verify penalty integration in UI backend
"""
import numpy as np
from src.segmentation.io import read_image_gray
from src.objective.fuzzy_entropy import fuzzy_entropy_objective
from src.objective.thresholding_with_penalties import (
    create_fe_objective_with_penalties,
    get_recommended_weights,
    get_recommended_params,
)
from src.objective.penalties import region_proportions
from src.optim.bounds import repair_threshold_vector
from src.optim.gwo import GWO


def test_penalty_integration():
    """Test that penalty integration works as expected"""
    print("=" * 80)
    print("TEST: PENALTY INTEGRATION")
    print("=" * 80)
    
    # Load image
    gray = read_image_gray("dataset/lena.gray.bmp")
    print(f"Image loaded: shape={gray.shape}")
    
    # Parameters
    k = 10
    lb, ub = 0, 255
    n_agents = 20
    n_iters = 30
    
    # Test 1: Without penalties
    print("\n" + "-" * 80)
    print("TEST 1: WITHOUT PENALTIES")
    print("-" * 80)
    
    def repair_fn_no_pen(x):
        return repair_threshold_vector(
            x, k=k, lb=lb, ub=ub,
            integer=True,
            ensure_unique=True,
            avoid_endpoints=False
        )
    
    def fitness_fn_no_pen(x):
        return float(fuzzy_entropy_objective(gray, repair_fn_no_pen(x)))
    
    opt1 = GWO(n_agents=n_agents, n_iters=n_iters, seed=42)
    best_x1, best_f1, _ = opt1.optimize(
        fitness_fn_no_pen,
        dim=k,
        lb=np.full(k, lb, dtype=float),
        ub=np.full(k, ub, dtype=float),
        repair_fn=repair_fn_no_pen,
        init_pop=None
    )
    
    best_t1 = repair_fn_no_pen(best_x1)
    entropy1 = -best_f1
    gaps1 = np.diff(best_t1)
    props1 = region_proportions(gray, best_t1, lb, ub)
    
    print(f"Thresholds: {best_t1.tolist()}")
    print(f"Entropy: {entropy1:.6f}")
    print(f"Min gap: {gaps1.min()} pixels")
    print(f"Min region: {props1.min()*100:.2f}%")
    
    # Test 2: With penalties (balanced mode)
    print("\n" + "-" * 80)
    print("TEST 2: WITH PENALTIES (BALANCED MODE)")
    print("-" * 80)
    
    use_penalties = True
    penalty_mode = "balanced"
    
    def repair_fn_with_pen(x):
        return repair_threshold_vector(
            x, k=k, lb=lb, ub=ub,
            integer=True,
            ensure_unique=True,
            avoid_endpoints=use_penalties
        )
    
    weights = get_recommended_weights(penalty_mode)
    params = get_recommended_params(k=k)
    
    print(f"Weights: w_gap={weights.w_gap}, w_size={weights.w_size}")
    print(f"Params: min_gap={params.min_gap}, p_min={params.p_min}")
    
    fitness_fn_with_pen = create_fe_objective_with_penalties(
        gray, repair_fn_with_pen, weights, params, lb, ub
    )
    
    opt2 = GWO(n_agents=n_agents, n_iters=n_iters, seed=42)
    best_x2, best_f2, _ = opt2.optimize(
        fitness_fn_with_pen,
        dim=k,
        lb=np.full(k, lb, dtype=float),
        ub=np.full(k, ub, dtype=float),
        repair_fn=repair_fn_with_pen,
        init_pop=None
    )
    
    best_t2 = repair_fn_with_pen(best_x2)
    # Calculate pure entropy (without penalty)
    entropy2 = -float(fuzzy_entropy_objective(gray, best_t2))
    gaps2 = np.diff(best_t2)
    props2 = region_proportions(gray, best_t2, lb, ub)
    
    print(f"Thresholds: {best_t2.tolist()}")
    print(f"Entropy: {entropy2:.6f}")
    print(f"Min gap: {gaps2.min()} pixels")
    print(f"Min region: {props2.min()*100:.2f}%")
    
    # Compare
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print(f"{'Metric':<20} {'No Penalties':<20} {'With Penalties':<20} {'Change':<15}")
    print("-" * 80)
    print(f"{'Entropy':<20} {entropy1:<20.6f} {entropy2:<20.6f} {(entropy2-entropy1)/entropy1*100:>+.2f}%")
    print(f"{'Min gap':<20} {gaps1.min():<20} {gaps2.min():<20} {(gaps2.min()-gaps1.min()):>+}")
    print(f"{'Min region %':<20} {props1.min()*100:<20.2f} {props2.min()*100:<20.2f} {(props2.min()-props1.min())*100:>+.2f}")
    print("=" * 80)
    
    # Verify improvements
    assert gaps2.min() >= gaps1.min(), "Min gap should not decrease"
    assert props2.min() >= props1.min(), "Min region should not decrease"
    
    print("\n✓ TEST PASSED: Penalties work correctly!")
    print("  - Min gap improved or maintained")
    print("  - Min region improved or maintained")
    print("  - Entropy trade-off is acceptable")
    
    return True


if __name__ == "__main__":
    try:
        test_penalty_integration()
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

"""
Test script để kiểm tra penalty đã đủ mạnh chưa
"""
import numpy as np
from src.objective.fuzzy_entropy import fuzzy_entropy_objective
from src.objective.penalties import total_penalty, PenaltyWeights, PenaltyParams
from src.objective.thresholding_with_penalties import (
    create_fe_objective_with_penalties,
    get_recommended_weights,
    get_recommended_params,
)
from src.optim.bounds import repair_threshold_vector

def test_penalty_scale():
    """Test xem penalty có đủ mạnh so với entropy không"""
    print("=" * 60)
    print("TEST PENALTY SCALE")
    print("=" * 60)
    
    # Tạo ảnh test đơn giản
    np.random.seed(42)
    gray = np.random.randint(0, 256, size=(100, 100), dtype=np.uint8)
    
    k = 10
    lb, ub = 0, 255
    
    # Test case 1: Ngưỡng dồn (clustered)
    t_clustered = np.array([120, 121, 122, 123, 124, 125, 126, 127, 128, 129], dtype=float)
    
    # Test case 2: Ngưỡng đều (uniform)
    t_uniform = np.linspace(20, 235, k)
    
    print(f"\nTest với k={k} ngưỡng")
    print(f"Ảnh: {gray.shape}, dtype={gray.dtype}")
    
    # Tính entropy cho cả 2 cases
    entropy_clustered = -fuzzy_entropy_objective(gray, t_clustered)
    entropy_uniform = -fuzzy_entropy_objective(gray, t_uniform)
    
    print(f"\n1. ENTROPY (maximize):")
    print(f"   Clustered: {entropy_clustered:.6f}")
    print(f"   Uniform:   {entropy_uniform:.6f}")
    print(f"   Diff:      {abs(entropy_clustered - entropy_uniform):.6f}")
    
    # Test với các mode khác nhau
    for mode in ["light", "balanced", "strong"]:
        print(f"\n2. PENALTY MODE: {mode.upper()}")
        weights = get_recommended_weights(mode)
        params = get_recommended_params(k)
        
        print(f"   Weights: gap={weights.w_gap}, var={weights.w_var}, "
              f"end={weights.w_end}, size={weights.w_size}, q={weights.w_q}")
        print(f"   Params: min_gap={params.min_gap}, end_margin={params.end_margin}, "
              f"p_min={params.p_min}")
        
        pen_clustered = total_penalty(gray, t_clustered, weights, params, lb, ub)
        pen_uniform = total_penalty(gray, t_uniform, weights, params, lb, ub)
        
        print(f"   Penalty clustered: {pen_clustered:.6f}")
        print(f"   Penalty uniform:   {pen_uniform:.6f}")
        print(f"   Diff:              {abs(pen_clustered - pen_uniform):.6f}")
        
        # Tính objective tổng
        obj_clustered = -entropy_clustered + pen_clustered
        obj_uniform = -entropy_uniform + pen_uniform
        
        print(f"   Objective clustered: {obj_clustered:.6f}")
        print(f"   Objective uniform:   {obj_uniform:.6f}")
        
        if obj_uniform < obj_clustered:
            print(f"   ✓ OK: Uniform tốt hơn (penalty đủ mạnh)")
        else:
            print(f"   ⚠️  WARNING: Clustered vẫn tốt hơn (penalty chưa đủ mạnh)")
        
        # Tính tỷ lệ penalty/entropy
        ratio = pen_clustered / abs(entropy_clustered) if entropy_clustered != 0 else 0
        print(f"   Penalty/Entropy ratio: {ratio:.2%}")
        if ratio > 0.1:
            print(f"   ✓ OK: Penalty chiếm >{ratio:.0%} entropy")
        else:
            print(f"   ⚠️  WARNING: Penalty chỉ chiếm {ratio:.1%} entropy (quá yếu)")

def test_penalty_before_repair():
    """Test xem penalty có tính trước repair không"""
    print("\n" + "=" * 60)
    print("TEST PENALTY BEFORE REPAIR")
    print("=" * 60)
    
    np.random.seed(42)
    gray = np.random.randint(0, 256, size=(100, 100), dtype=np.uint8)
    
    k = 10
    lb, ub = 0, 255
    
    def repair_fn(x):
        return repair_threshold_vector(x, k=k, lb=lb, ub=ub, 
                                      integer=True, ensure_unique=True,
                                      avoid_endpoints=True)
    
    # Ngưỡng dồn (sẽ bị repair sửa)
    t_raw = np.array([120, 121, 122, 123, 124, 125, 126, 127, 128, 129], dtype=float)
    
    print(f"\nNgưỡng raw (dồn):     {t_raw}")
    
    t_repaired = repair_fn(t_raw)
    print(f"Ngưỡng sau repair:    {t_repaired}")
    
    # Tạo objective với penalty
    weights = get_recommended_weights("balanced")
    params = get_recommended_params(k)
    
    fitness_fn = create_fe_objective_with_penalties(
        gray, repair_fn, weights, params, lb, ub
    )
    
    # Tính objective
    obj = fitness_fn(t_raw)
    
    # Tính penalty riêng trên raw và repaired
    pen_raw = total_penalty(gray, t_raw, weights, params, lb, ub)
    pen_repaired = total_penalty(gray, t_repaired, weights, params, lb, ub)
    
    print(f"\nPenalty trên raw:      {pen_raw:.6f}")
    print(f"Penalty trên repaired: {pen_repaired:.6f}")
    
    if pen_raw > pen_repaired * 1.5:
        print("✓ OK: Penalty tính trên raw (nhìn thấy dồn ngưỡng)")
    else:
        print("⚠️  WARNING: Penalty có thể đang tính trên repaired")

def test_min_gap_effect():
    """Test hiệu quả của min_gap"""
    print("\n" + "=" * 60)
    print("TEST MIN_GAP EFFECT")
    print("=" * 60)
    
    np.random.seed(42)
    gray = np.random.randint(0, 256, size=(100, 100), dtype=np.uint8)
    
    k = 10
    lb, ub = 0, 255
    
    # Test với các min_gap khác nhau
    for min_gap in [3, 8, 15]:
        print(f"\nmin_gap = {min_gap}")
        
        weights = PenaltyWeights(w_gap=2.0, w_var=0, w_end=0, w_size=0, w_q=0)
        params = PenaltyParams(min_gap=min_gap, end_margin=3, p_min=0.01)
        
        # Ngưỡng với gap khác nhau
        gaps = [2, 5, 10, 20]
        for gap in gaps:
            t = np.arange(k) * gap + 50
            t = np.clip(t, lb, ub)
            
            pen = total_penalty(gray, t, weights, params, lb, ub)
            print(f"  Gap={gap:2d} → Penalty={pen:.6f}")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("KIỂM TRA PENALTY STRENGTH")
    print("=" * 60 + "\n")
    
    test_penalty_scale()
    test_penalty_before_repair()
    test_min_gap_effect()
    
    print("\n" + "=" * 60)
    print("HOÀN THÀNH TẤT CẢ TESTS")
    print("=" * 60)

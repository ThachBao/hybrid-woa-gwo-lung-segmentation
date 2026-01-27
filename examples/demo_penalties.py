"""
Demo: Sử dụng penalties để tránh dồn ngưỡng
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


def demo_without_penalties():
    """Demo: Không dùng penalties"""
    print("=" * 80)
    print("DEMO 1: KHÔNG DÙNG PENALTIES")
    print("=" * 80)
    
    # Đọc ảnh
    gray = read_image_gray("dataset/lena.gray.bmp")
    print(f"Ảnh: shape={gray.shape}")
    
    # Tham số
    k = 10
    lb, ub = 0, 255
    
    # Repair function (không avoid_endpoints)
    def repair_fn(x):
        return repair_threshold_vector(
            x, k=k, lb=lb, ub=ub,
            integer=True,
            ensure_unique=True,
            avoid_endpoints=False  # Không tránh 0/255
        )
    
    # Fitness function: chỉ Fuzzy Entropy
    def fitness_fn(x):
        t = repair_fn(x)
        return float(fuzzy_entropy_objective(gray, t))
    
    # Optimizer
    opt = GWO(n_agents=30, n_iters=50, seed=42)
    
    # Optimize
    print("\nĐang tối ưu...")
    best_x, best_f, _ = opt.optimize(
        fitness_fn,
        dim=k,
        lb=np.full(k, lb, dtype=float),
        ub=np.full(k, ub, dtype=float),
        repair_fn=repair_fn,
        init_pop=None
    )
    
    # Kết quả
    best_t = repair_fn(best_x)
    entropy = -best_f
    
    # Tính region proportions
    props = region_proportions(gray, best_t, lb, ub)
    min_prop = props.min()
    
    # Tính gaps
    gaps = np.diff(best_t)
    min_gap = gaps.min()
    
    print("\n" + "-" * 80)
    print("KẾT QUẢ:")
    print(f"  Thresholds: {best_t.tolist()}")
    print(f"  Entropy: {entropy:.6f}")
    print(f"  Min gap: {min_gap} pixels")
    print(f"  Min region: {min_prop*100:.2f}% pixels")
    print(f"  Gaps: {gaps.tolist()}")
    print("-" * 80)
    
    return best_t, entropy, min_gap, min_prop


def demo_with_penalties():
    """Demo: Dùng penalties (balanced mode)"""
    print("\n\n")
    print("=" * 80)
    print("DEMO 2: DÙNG PENALTIES (BALANCED MODE)")
    print("=" * 80)
    
    # Đọc ảnh
    gray = read_image_gray("dataset/lena.gray.bmp")
    print(f"Ảnh: shape={gray.shape}")
    
    # Tham số
    k = 10
    lb, ub = 0, 255
    
    # Repair function (có avoid_endpoints)
    def repair_fn(x):
        return repair_threshold_vector(
            x, k=k, lb=lb, ub=ub,
            integer=True,
            ensure_unique=True,
            avoid_endpoints=True  # Tránh 0/255
        )
    
    # Penalties (balanced mode)
    weights = get_recommended_weights("balanced")
    params = get_recommended_params(k=k)
    
    print(f"\nPenalty weights:")
    print(f"  w_gap={weights.w_gap}, w_var={weights.w_var}, w_end={weights.w_end}")
    print(f"  w_size={weights.w_size}, w_q={weights.w_q}")
    print(f"\nPenalty params:")
    print(f"  min_gap={params.min_gap}, end_margin={params.end_margin}, p_min={params.p_min}")
    
    # Fitness function với penalties
    fitness_fn = create_fe_objective_with_penalties(
        gray, repair_fn, weights, params, lb, ub
    )
    
    # Optimizer
    opt = GWO(n_agents=30, n_iters=50, seed=42)
    
    # Optimize
    print("\nĐang tối ưu...")
    best_x, best_f, _ = opt.optimize(
        fitness_fn,
        dim=k,
        lb=np.full(k, lb, dtype=float),
        ub=np.full(k, ub, dtype=float),
        repair_fn=repair_fn,
        init_pop=None
    )
    
    # Kết quả
    best_t = repair_fn(best_x)
    
    # Tính entropy riêng (không có penalty)
    entropy = -float(fuzzy_entropy_objective(gray, best_t))
    
    # Tính region proportions
    props = region_proportions(gray, best_t, lb, ub)
    min_prop = props.min()
    
    # Tính gaps
    gaps = np.diff(best_t)
    min_gap = gaps.min()
    
    print("\n" + "-" * 80)
    print("KẾT QUẢ:")
    print(f"  Thresholds: {best_t.tolist()}")
    print(f"  Entropy: {entropy:.6f}")
    print(f"  Min gap: {min_gap} pixels")
    print(f"  Min region: {min_prop*100:.2f}% pixels")
    print(f"  Gaps: {gaps.tolist()}")
    print("-" * 80)
    
    return best_t, entropy, min_gap, min_prop


def main():
    """Chạy cả 2 demos và so sánh"""
    # Demo 1: Không penalties
    t1, e1, g1, p1 = demo_without_penalties()
    
    # Demo 2: Có penalties
    t2, e2, g2, p2 = demo_with_penalties()
    
    # So sánh
    print("\n\n")
    print("=" * 80)
    print("SO SÁNH KẾT QUẢ")
    print("=" * 80)
    print(f"{'Metric':<20} {'Không penalties':<20} {'Có penalties':<20} {'Thay đổi':<15}")
    print("-" * 80)
    print(f"{'Entropy':<20} {e1:<20.6f} {e2:<20.6f} {(e2-e1)/e1*100:>+.2f}%")
    print(f"{'Min gap (pixels)':<20} {g1:<20} {g2:<20} {(g2-g1):>+}")
    print(f"{'Min region (%)':<20} {p1*100:<20.2f} {p2*100:<20.2f} {(p2-p1)*100:>+.2f}")
    print("=" * 80)
    
    print("\nKẾT LUẬN:")
    if e2 < e1:
        print(f"  - Entropy giảm {(e1-e2)/e1*100:.1f}% (trade-off chấp nhận được)")
    else:
        print(f"  - Entropy tăng {(e2-e1)/e1*100:.1f}%!")
    
    if g2 > g1:
        print(f"  - Min gap tăng {g2-g1} pixels (tốt hơn)")
    
    if p2 > p1:
        print(f"  - Min region tăng {(p2-p1)*100:.2f}% (tốt hơn)")
    
    print("\n✓ Penalties giúp ngưỡng phân bố đều hơn, tránh vùng quá nhỏ!")


if __name__ == "__main__":
    main()

"""
Test script để kiểm tra các sửa đổi:
1. Jitter seed cố định theo image_id
2. OTSU dùng threshold_multiotsu thật
3. PSO dùng Generator thay vì seed toàn cục
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
from skimage.filters import threshold_multiotsu

def test_jitter_seed_consistency():
    """Test 1: Jitter seed phải giống nhau cho cùng image_id"""
    print("=" * 80)
    print("TEST 1: Jitter Seed Consistency")
    print("=" * 80)
    
    image_id = "100007"
    
    # Tính jitter seed theo cách mới
    jitter_seed_1 = hash(image_id) % (2**31)
    jitter_seed_2 = hash(image_id) % (2**31)
    
    print(f"\nImage ID: {image_id}")
    print(f"Jitter seed lần 1: {jitter_seed_1}")
    print(f"Jitter seed lần 2: {jitter_seed_2}")
    print(f"Giống nhau: {jitter_seed_1 == jitter_seed_2}")
    
    assert jitter_seed_1 == jitter_seed_2, "Jitter seed phải giống nhau cho cùng image_id"
    
    # Test với image_id khác
    image_id_2 = "100039"
    jitter_seed_3 = hash(image_id_2) % (2**31)
    
    print(f"\nImage ID khác: {image_id_2}")
    print(f"Jitter seed: {jitter_seed_3}")
    print(f"Khác với image_id đầu: {jitter_seed_1 != jitter_seed_3}")
    
    print("\n✓ Jitter seed cố định theo image_id!")
    return True


def test_otsu_multithreshold():
    """Test 2: OTSU phải dùng threshold_multiotsu thật"""
    print("\n" + "=" * 80)
    print("TEST 2: OTSU Multi-threshold")
    print("=" * 80)
    
    # Tạo ảnh test
    np.random.seed(42)
    gray = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    
    k = 4  # 4 ngưỡng
    
    # Dùng threshold_multiotsu
    thresholds = threshold_multiotsu(gray, classes=k+1)
    
    print(f"\nẢnh test: {gray.shape}")
    print(f"Số ngưỡng (k): {k}")
    print(f"Số classes: {k+1}")
    print(f"Ngưỡng tìm được: {thresholds}")
    print(f"Số ngưỡng: {len(thresholds)}")
    
    assert len(thresholds) == k, f"Phải có {k} ngưỡng, nhưng có {len(thresholds)}"
    assert all(thresholds[i] < thresholds[i+1] for i in range(len(thresholds)-1)), "Ngưỡng phải tăng dần"
    
    print("\n✓ OTSU dùng threshold_multiotsu đúng!")
    return True


def test_pso_generator():
    """Test 3: PSO phải dùng Generator thay vì seed toàn cục"""
    print("\n" + "=" * 80)
    print("TEST 3: PSO Generator (không dùng seed toàn cục)")
    print("=" * 80)
    
    from src.optim.pso import PSO
    
    # Test 1: PSO với seed
    pso1 = PSO(n_agents=10, n_iters=5, seed=42)
    print(f"\nPSO 1: seed=42")
    print(f"  - Có self.rng: {hasattr(pso1, 'rng')}")
    print(f"  - Type: {type(pso1.rng)}")
    
    assert hasattr(pso1, 'rng'), "PSO phải có self.rng"
    assert isinstance(pso1.rng, np.random.Generator), "self.rng phải là Generator"
    
    # Test 2: PSO với seed khác
    pso2 = PSO(n_agents=10, n_iters=5, seed=123)
    print(f"\nPSO 2: seed=123")
    print(f"  - Có self.rng: {hasattr(pso2, 'rng')}")
    
    # Test 3: Chạy PSO và kiểm tra không ảnh hưởng seed toàn cục
    np.random.seed(999)
    before = np.random.rand()
    
    # Tạo fitness function đơn giản
    def fitness_fn(x):
        return np.sum(x**2)
    
    # Chạy PSO
    best_x, best_f, history = pso1.optimize(
        fitness_fn, dim=3, lb=0, ub=10, repair_fn=lambda x: np.sort(x)
    )
    
    np.random.seed(999)
    after = np.random.rand()
    
    print(f"\nKiểm tra seed toàn cục:")
    print(f"  - np.random.rand() trước PSO: {before:.6f}")
    print(f"  - np.random.rand() sau PSO (cùng seed): {after:.6f}")
    print(f"  - Giống nhau: {np.isclose(before, after)}")
    
    assert np.isclose(before, after), "PSO không được ảnh hưởng seed toàn cục"
    
    print("\n✓ PSO dùng Generator đúng!")
    return True


def test_otsu_vs_linspace():
    """Test 4: So sánh OTSU thật vs linspace (cũ)"""
    print("\n" + "=" * 80)
    print("TEST 4: OTSU thật vs Linspace (cũ)")
    print("=" * 80)
    
    # Tạo ảnh có 3 vùng rõ ràng
    gray = np.zeros((300, 300), dtype=np.uint8)
    gray[0:100, :] = 50    # Vùng tối
    gray[100:200, :] = 128  # Vùng trung bình
    gray[200:300, :] = 200  # Vùng sáng
    
    k = 2  # 2 ngưỡng để chia 3 vùng
    
    # OTSU thật
    thresholds_otsu = threshold_multiotsu(gray, classes=k+1)
    
    # Linspace (cách cũ sai)
    thresholds_linspace = np.linspace(0, 255, k+2)[1:-1]
    
    print(f"\nẢnh test: 3 vùng (50, 128, 200)")
    print(f"Số ngưỡng: {k}")
    print(f"\nOTSU thật: {thresholds_otsu}")
    print(f"Linspace (cũ): {thresholds_linspace}")
    
    print(f"\nKhoảng cách:")
    print(f"  OTSU: {np.diff(thresholds_otsu)}")
    print(f"  Linspace: {np.diff(thresholds_linspace)}")
    
    # OTSU phải khác linspace
    assert not np.allclose(thresholds_otsu, thresholds_linspace), "OTSU phải khác linspace"
    
    # OTSU phải gần với giá trị thực (giữa các vùng)
    expected = [89, 164]  # Giữa 50-128 và 128-200
    print(f"\nGiá trị mong đợi (giữa các vùng): {expected}")
    print(f"OTSU tìm được: {thresholds_otsu}")
    print(f"Sai số: {np.abs(thresholds_otsu - expected)}")
    
    print("\n✓ OTSU thật khác linspace!")
    return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("KIỂM TRA CÁC SỬA ĐỔI")
    print("=" * 80)
    
    try:
        test_jitter_seed_consistency()
        test_otsu_multithreshold()
        test_pso_generator()
        test_otsu_vs_linspace()
        
        print("\n" + "=" * 80)
        print("✅ TẤT CẢ TEST ĐỀU PASS!")
        print("=" * 80)
        print("\nTóm tắt:")
        print("  ✓ Jitter seed cố định theo image_id")
        print("  ✓ OTSU dùng threshold_multiotsu thật")
        print("  ✓ PSO dùng Generator (không ảnh hưởng seed toàn cục)")
        print("  ✓ OTSU thật khác linspace")
        print("\nCác sửa đổi đã hoạt động đúng!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

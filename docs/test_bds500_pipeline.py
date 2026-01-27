"""
Test script để kiểm tra BDS500 pipeline hoạt động đúng
"""
import numpy as np

def test_load_bds500():
    """Test load dataset"""
    print("=" * 60)
    print("TEST 1: Load BDS500 Dataset")
    print("=" * 60)
    
    try:
        from src.data.bsds500 import load_bsds500
        
        # Load 2 ảnh đầu tiên từ train set
        data = load_bsds500(split="train", limit=2)
        
        print(f"✓ Đã load {len(data)} ảnh")
        
        for i, (img, gt) in enumerate(data):
            print(f"\nẢnh {i+1}:")
            print(f"  Image shape: {img.shape}, dtype: {img.dtype}")
            print(f"  GT shape: {gt.shape}, dtype: {gt.dtype}")
            print(f"  GT is bool: {gt.dtype == bool}")
            print(f"  GT boundary pixels: {np.sum(gt)} / {gt.size} ({np.sum(gt)/gt.size*100:.2f}%)")
        
        print("\n✓ OK: Load dataset thành công")
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_apply_thresholds():
    """Test apply thresholds"""
    print("\n" + "=" * 60)
    print("TEST 2: Apply Thresholds")
    print("=" * 60)
    
    try:
        from src.segmentation.apply_thresholds import apply_thresholds
        
        # Tạo ảnh test
        img = np.random.randint(0, 256, size=(100, 100), dtype=np.uint8)
        thresholds = np.array([50, 100, 150, 200])
        
        seg = apply_thresholds(img, thresholds)
        
        print(f"Image shape: {img.shape}")
        print(f"Thresholds: {thresholds}")
        print(f"Segmented shape: {seg.shape}")
        print(f"Unique labels: {np.unique(seg)}")
        print(f"Expected labels: 0 to {len(thresholds)}")
        
        # Kiểm tra số lớp
        n_labels = len(np.unique(seg))
        expected_labels = len(thresholds) + 1
        
        if n_labels == expected_labels:
            print(f"\n✓ OK: Số lớp đúng ({n_labels} lớp)")
            return True
        else:
            print(f"\n✗ ERROR: Số lớp sai (có {n_labels}, mong đợi {expected_labels})")
            return False
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_boundary_extraction():
    """Test extract boundary từ segmentation"""
    print("\n" + "=" * 60)
    print("TEST 3: Boundary Extraction")
    print("=" * 60)
    
    try:
        from src.data.bsds500_gt import seg_to_boundary_mask
        
        # Tạo segmentation đơn giản
        seg = np.zeros((100, 100), dtype=np.uint8)
        seg[25:75, 25:75] = 1  # Hình vuông
        
        boundary = seg_to_boundary_mask(seg)
        
        print(f"Segmentation shape: {seg.shape}")
        print(f"Boundary shape: {boundary.shape}")
        print(f"Boundary dtype: {boundary.dtype}")
        print(f"Boundary pixels: {np.sum(boundary)}")
        
        # Kiểm tra boundary có pixel không
        if np.sum(boundary) > 0:
            print(f"\n✓ OK: Boundary extraction thành công")
            return True
        else:
            print(f"\n✗ ERROR: Không có boundary pixel nào")
            return False
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dice_calculation():
    """Test tính DICE score"""
    print("\n" + "=" * 60)
    print("TEST 4: DICE Calculation")
    print("=" * 60)
    
    try:
        from src.data.bsds500_gt import dice_binary
        
        # Test case 1: Perfect match
        a = np.array([1, 1, 0, 0], dtype=bool)
        b = np.array([1, 1, 0, 0], dtype=bool)
        dice1 = dice_binary(a, b)
        print(f"Perfect match: DICE = {dice1:.4f} (expected: 1.0000)")
        
        # Test case 2: No overlap
        a = np.array([1, 1, 0, 0], dtype=bool)
        b = np.array([0, 0, 1, 1], dtype=bool)
        dice2 = dice_binary(a, b)
        print(f"No overlap: DICE = {dice2:.4f} (expected: 0.0000)")
        
        # Test case 3: Partial overlap
        a = np.array([1, 1, 1, 0], dtype=bool)
        b = np.array([1, 1, 0, 0], dtype=bool)
        dice3 = dice_binary(a, b)
        print(f"Partial overlap: DICE = {dice3:.4f} (expected: 0.8000)")
        
        # Kiểm tra
        if abs(dice1 - 1.0) < 0.01 and abs(dice2 - 0.0) < 0.01 and abs(dice3 - 0.8) < 0.01:
            print(f"\n✓ OK: DICE calculation đúng")
            return True
        else:
            print(f"\n✗ ERROR: DICE calculation sai")
            return False
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_pipeline():
    """Test toàn bộ pipeline"""
    print("\n" + "=" * 60)
    print("TEST 5: Full Pipeline")
    print("=" * 60)
    
    try:
        from src.data.bsds500 import load_bsds500
        from src.objective.fuzzy_entropy import fuzzy_entropy_objective
        from src.optim.bounds import repair_threshold_vector
        from src.optim.gwo import GWO
        from src.segmentation.apply_thresholds import apply_thresholds
        from src.data.bsds500_gt import seg_to_boundary_mask, dice_binary
        
        # Load 1 ảnh
        print("Loading dataset...")
        data = load_bsds500(split="train", limit=1)
        
        if len(data) == 0:
            print("✗ ERROR: Không load được ảnh")
            return False
        
        img, gt_boundary = data[0]
        print(f"✓ Loaded image: {img.shape}")
        
        # Setup
        K = 3  # Ít ngưỡng để test nhanh
        lb, ub = 0, 255
        
        def repair_fn(x):
            return repair_threshold_vector(x, k=K, lb=lb, ub=ub, 
                                          integer=True, ensure_unique=True)
        
        def fitness_fn(x):
            return float(fuzzy_entropy_objective(img, repair_fn(x)))
        
        # Run optimizer (ít vòng lặp để test nhanh)
        print("Running optimizer...")
        optimizer = GWO(n_agents=10, n_iters=5, seed=42)
        
        best_x, best_f, history = optimizer.optimize(
            fitness_fn,
            dim=K,
            lb=np.full(K, lb, dtype=float),
            ub=np.full(K, ub, dtype=float),
            repair_fn=repair_fn,
            init_pop=None,
        )
        
        print(f"✓ Optimization done: best_f={best_f:.6f}")
        print(f"  Thresholds: {best_x}")
        
        # Apply thresholds
        print("Applying thresholds...")
        seg = apply_thresholds(img, best_x)
        print(f"✓ Segmentation done: {seg.shape}, unique={np.unique(seg)}")
        
        # Extract boundary
        print("Extracting boundary...")
        pred_boundary = seg_to_boundary_mask(seg)
        print(f"✓ Boundary extracted: {np.sum(pred_boundary)} pixels")
        
        # Calculate DICE
        print("Calculating DICE...")
        dice = dice_binary(pred_boundary, gt_boundary)
        print(f"✓ DICE = {dice:.4f}")
        
        print(f"\n✓ OK: Full pipeline hoạt động")
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("KIỂM TRA BDS500 PIPELINE")
    print("=" * 60 + "\n")
    
    results = []
    
    results.append(("Load Dataset", test_load_bds500()))
    results.append(("Apply Thresholds", test_apply_thresholds()))
    results.append(("Boundary Extraction", test_boundary_extraction()))
    results.append(("DICE Calculation", test_dice_calculation()))
    results.append(("Full Pipeline", test_full_pipeline()))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    print()
    if all_passed:
        print("✓ TẤT CẢ TESTS ĐỀU PASS")
        print("Pipeline sẵn sàng để chạy đánh giá BDS500")
    else:
        print("✗ CÓ TESTS FAIL")
        print("Cần sửa lỗi trước khi chạy đánh giá")
    
    print("=" * 60)

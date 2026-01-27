"""
Test script: Verify all imports work correctly
"""
import sys

def test_import(module_path, description):
    """Test importing a module"""
    try:
        __import__(module_path)
        print(f"✅ {description}: OK")
        return True
    except Exception as e:
        print(f"❌ {description}: FAILED")
        print(f"   Error: {e}")
        return False

def main():
    print("=" * 80)
    print("TESTING ALL IMPORTS")
    print("=" * 80)
    
    tests = [
        # Core modules
        ("src.optim.gwo", "GWO optimizer"),
        ("src.optim.woa", "WOA optimizer"),
        ("src.optim.hybrid.hybrid_gwo_woa", "Hybrid GWO-WOA optimizer"),
        
        # Runner scripts
        ("src.runner.run_single", "run_single.py"),
        ("src.runner.run_dataset", "run_dataset.py"),
        ("src.runner.run_benchmark", "run_benchmark.py"),
        ("src.runner.eval_dice_bsds500", "eval_dice_bsds500.py"),
        ("src.runner.learn_global_thresholds_bsds500", "learn_global_thresholds_bsds500.py"),
        ("src.runner.eval_global_thresholds_bsds500", "eval_global_thresholds_bsds500.py"),
        
        # UI
        ("src.ui.app", "Web UI app"),
        
        # Objective functions
        ("src.objective.fuzzy_entropy", "Fuzzy Entropy"),
        ("src.objective.penalties", "Penalties"),
        ("src.objective.thresholding_with_penalties", "Thresholding with penalties"),
        
        # Data
        ("src.data.bsds500", "BDS500 dataset"),
        ("src.data.bsds500_gt", "BDS500 ground truth"),
        
        # Segmentation
        ("src.segmentation.io", "Segmentation IO"),
        ("src.segmentation.apply_thresholds", "Apply thresholds"),
        
        # Metrics
        ("src.metrics.quality", "Quality metrics"),
    ]
    
    print()
    results = []
    for module_path, description in tests:
        result = test_import(module_path, description)
        results.append(result)
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())

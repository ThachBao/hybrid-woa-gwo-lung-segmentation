"""
Test script: Verify save results feature
"""
import os
import json
import yaml
from pathlib import Path

def test_save_results():
    """Test that results are saved correctly"""
    print("=" * 80)
    print("TEST: SAVE RESULTS FEATURE")
    print("=" * 80)
    
    # Check if outputs/runs directory exists
    runs_dir = Path("outputs/runs")
    if not runs_dir.exists():
        print("❌ outputs/runs directory does not exist yet")
        print("   Run the UI and segment an image first")
        return False
    
    # Find the most recent run
    run_dirs = sorted(runs_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not run_dirs:
        print("❌ No runs found in outputs/runs")
        print("   Run the UI and segment an image first")
        return False
    
    latest_run = run_dirs[0]
    print(f"\n✓ Found latest run: {latest_run.name}")
    
    # Check required files
    required_files = ["config.yaml", "summary.json", "gray.png"]
    
    print("\nChecking required files:")
    all_found = True
    for filename in required_files:
        filepath = latest_run / filename
        if filepath.exists():
            print(f"  ✓ {filename}")
        else:
            print(f"  ❌ {filename} (missing)")
            all_found = False
    
    if not all_found:
        return False
    
    # Check config.yaml
    print("\nChecking config.yaml:")
    with open(latest_run / "config.yaml") as f:
        config = yaml.safe_load(f)
    
    required_keys = ["image_name", "timestamp", "k", "n_agents", "n_iters", "algorithms"]
    for key in required_keys:
        if key in config:
            print(f"  ✓ {key}: {config[key]}")
        else:
            print(f"  ❌ {key} (missing)")
            return False
    
    # Check summary.json
    print("\nChecking summary.json:")
    with open(latest_run / "summary.json") as f:
        summary = json.load(f)
    
    required_keys = ["image_name", "timestamp", "total_time", "best_overall_algo", "results"]
    for key in required_keys:
        if key in summary:
            if key == "results":
                print(f"  ✓ {key}: {list(summary[key].keys())}")
            else:
                print(f"  ✓ {key}: {summary[key]}")
        else:
            print(f"  ❌ {key} (missing)")
            return False
    
    # Check algorithm directories
    print("\nChecking algorithm directories:")
    for algo in config["algorithms"]:
        algo_dir = latest_run / algo
        if algo_dir.exists():
            print(f"  ✓ {algo}/")
            
            # Check files in algorithm directory
            algo_files = ["best.json", "segmented.png"]
            for filename in algo_files:
                filepath = algo_dir / filename
                if filepath.exists():
                    print(f"    ✓ {filename}")
                else:
                    print(f"    ❌ {filename} (missing)")
        else:
            print(f"  ❌ {algo}/ (missing)")
            return False
    
    # Check best.json structure
    print("\nChecking best.json structure:")
    first_algo = config["algorithms"][0]
    with open(latest_run / first_algo / "best.json") as f:
        best = json.load(f)
    
    required_keys = ["algorithm", "thresholds", "best_f", "entropy", "time", "metrics"]
    for key in required_keys:
        if key in best:
            if key == "thresholds":
                print(f"  ✓ {key}: {len(best[key])} thresholds")
            elif key == "metrics":
                print(f"  ✓ {key}: {list(best[key].keys())}")
            else:
                print(f"  ✓ {key}: {best[key]}")
        else:
            print(f"  ❌ {key} (missing)")
            return False
    
    print("\n" + "=" * 80)
    print("✓ ALL CHECKS PASSED!")
    print("=" * 80)
    print(f"\nResults saved in: {latest_run}")
    print("\nStructure:")
    print(f"{latest_run.name}/")
    print("├── config.yaml          # Configuration")
    print("├── summary.json         # Summary of all algorithms")
    print("├── gray.png             # Original grayscale image")
    for algo in config["algorithms"]:
        print(f"└── {algo}/")
        print(f"    ├── best.json        # Best result")
        print(f"    ├── history.jsonl    # Convergence history")
        print(f"    └── segmented.png    # Segmented image")
    
    return True


if __name__ == "__main__":
    try:
        success = test_save_results()
        if not success:
            print("\n⚠️  Run the UI and segment an image to test this feature:")
            print("   python -m src.ui.app")
            print("   Then open http://127.0.0.1:5000 and segment an image")
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

"""
Test script to verify BDS500 evaluation response structure
"""

# Simulate the response structure
response_old = {
    "n_images": 5,
    "n_algorithms": 3,
    "total_runs": 15,
    "total_time": 29.34,
    "statistics": {  # ❌ Wrong key name
        "GWO": {
            "dice_mean": 0.7123,
            "dice_std": 0.0478,
        }
    }
}

response_new = {
    "success": True,
    "run_dir": "outputs/bds500_eval/k10_seed42_test_20260123_103115",
    "results_file": "results_k10_seed42.json",
    "summary_file": "summary_k10_seed42.json",
    "stats": {  # ✅ Correct key name
        "total_images": 5,
        "successful": 5,
        "failed": 0,
    },
    "algo_stats": {  # ✅ Correct key name
        "GWO": {
            "n_images": 5,
            "dice_mean": 0.7123,
            "dice_std": 0.0478,
            "dice_min": 0.6234,
            "dice_max": 0.7987,
            "entropy_mean": 0.0368,
            "time_mean": 11.89,
        },
        "WOA": {
            "n_images": 5,
            "dice_mean": 0.7089,
            "dice_std": 0.0501,
            "dice_min": 0.6123,
            "dice_max": 0.7856,
            "entropy_mean": 0.0361,
            "time_mean": 12.01,
        },
        "PA1": {
            "n_images": 5,
            "dice_mean": 0.7234,
            "dice_std": 0.0456,
            "dice_min": 0.6543,
            "dice_max": 0.8123,
            "entropy_mean": 0.0376,
            "time_mean": 12.34,
        },
    },
    "total_time": 29.34,
}

# Simulate JavaScript code
def displayBDS500Results(data):
    """Simulate the JavaScript function"""
    print("Testing response structure...")
    
    # This is what JavaScript expects
    try:
        stats = data["stats"]  # Should exist
        algo_stats = data.get("algo_stats", {})  # Should exist
        
        print(f"✅ stats found: {stats}")
        print(f"✅ algo_stats found: {len(algo_stats)} algorithms")
        
        # Display summary
        print(f"\n📊 Tổng quan:")
        print(f"  Total images: {stats['total_images']}")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        
        # Display algorithm comparison
        print(f"\n🏆 So sánh thuật toán:")
        for algo_name, algo_data in algo_stats.items():
            print(f"  {algo_name}:")
            print(f"    DICE: {algo_data['dice_mean']:.4f} ± {algo_data['dice_std']:.4f}")
            print(f"    Entropy: {algo_data['entropy_mean']:.4f}")
            print(f"    Time: {algo_data['time_mean']:.2f}s")
        
        print("\n✅ Response structure is CORRECT!")
        return True
        
    except KeyError as e:
        print(f"❌ Missing key: {e}")
        print("Response structure is WRONG!")
        return False

# Test old response (should fail)
print("=" * 60)
print("Testing OLD response structure:")
print("=" * 60)
displayBDS500Results(response_old)

print("\n" + "=" * 60)
print("Testing NEW response structure:")
print("=" * 60)
displayBDS500Results(response_new)

"""
Test runs list API directly (without server)
"""
import os
import json
import yaml

runs_dir = os.path.join("outputs", "runs")

if not os.path.exists(runs_dir):
    print("❌ outputs/runs directory not found!")
    exit(1)

print(f"✓ Found runs directory: {runs_dir}")

runs = []
for run_name in os.listdir(runs_dir):
    run_path = os.path.join(runs_dir, run_name)
    if not os.path.isdir(run_path):
        continue
    
    summary_path = os.path.join(run_path, "summary.json")
    config_path = os.path.join(run_path, "config.yaml")
    
    if not os.path.exists(summary_path):
        print(f"⚠️  {run_name}: No summary.json")
        continue
    
    try:
        with open(summary_path, "r") as f:
            summary = json.load(f)
        
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
        
        algorithms = config.get("algorithms", [])
        if isinstance(algorithms, list):
            algorithms = algorithms
        else:
            algorithms = []
        
        run_info = {
            "run_name": run_name,
            "image_name": summary.get("image_name", "unknown"),
            "timestamp": summary.get("timestamp", ""),
            "total_time": summary.get("total_time", 0),
            "best_algo": summary.get("best_overall_algo", ""),
            "best_entropy": summary.get("best_overall_entropy", 0),
            "algorithms": algorithms,
            "k": config.get("k", 10),
            "n_agents": config.get("n_agents", 30),
            "n_iters": config.get("n_iters", 80),
            "use_penalties": config.get("use_penalties", False),
        }
        
        runs.append(run_info)
        print(f"✓ {run_name}: {run_info['image_name']}, {len(algorithms)} algos")
    except Exception as e:
        print(f"❌ {run_name}: Error - {e}")
        continue

print(f"\n{'='*60}")
print(f"Total runs found: {len(runs)}")
print(f"{'='*60}")

if runs:
    print("\nFirst run details:")
    print(json.dumps(runs[0], indent=2))

"""
Chạy so sánh PA1..PA5 với seed sweep (0..30) trong 1 lệnh.

Lưu kết quả chỉ gồm:
<<<<<<< HEAD
- fe_best
- jitter_fe_std
- conv_fe_last_std
=======
- fe_best: FE tốt nhất
- mean_fe: FE trung bình
- std_fe: Độ lệch chuẩn FE (đo độ ổn định)
- worst_fe: FE tệ nhất
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba

Có hỗ trợ quét share_interval cho PA5.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.objective.fuzzy_entropy import fuzzy_entropy_objective
<<<<<<< HEAD
from src.objective.thresholding_with_penalties import (
    compute_fe_stability_convergence,
    compute_fe_stability_jitter,
)
=======
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
from src.optim.bounds import repair_threshold_vector
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA
from src.segmentation.io import ensure_dir, list_image_files, read_image_gray


def _parse_list_int(s: Optional[str]) -> List[int]:
    if not s:
        return []
    out: List[int] = []
    for p in s.split(","):
        p = p.strip()
        if not p:
            continue
        out.append(int(p))
    return out


def _parse_strategies(s: Optional[str]) -> List[str]:
    if not s:
        return ["PA1", "PA2", "PA3", "PA4", "PA5"]
    parts = [p.strip().upper() for p in s.split(",") if p.strip()]
    return parts or ["PA1", "PA2", "PA3", "PA4", "PA5"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, required=True, help="Thư mục chứa ảnh grayscale")
    ap.add_argument("--out_root", type=str, default="outputs/compareGWO-WOA")

    # cố định theo yêu cầu (vẫn cho override nếu cần)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--n_agents", type=int, default=30)
    ap.add_argument("--n_iters", type=int, default=100)

    # seed sweep
    ap.add_argument("--seed_start", type=int, default=0)
    ap.add_argument("--seed_end", type=int, default=30)  # inclusive

    ap.add_argument("--lb", type=int, default=0)
    ap.add_argument("--ub", type=int, default=255)

    # WOA parameter
    ap.add_argument("--woa_b", type=float, default=1.0)

    # PA5 knowledge transfer (share_interval)
    ap.add_argument("--share_interval", type=int, default=1)
    ap.add_argument(
        "--pa5_share_intervals",
        type=str,
        default="",
        help="Danh sách share_interval để quét cho PA5, ví dụ: 1,2,3,5,10. Nếu bỏ trống thì dùng --share_interval.",
    )

    ap.add_argument("--strategies", type=str, default="PA1,PA2,PA3,PA4,PA5")
    ap.add_argument("--limit", type=int, default=0)

<<<<<<< HEAD
    # FE stability (jitter)
    ap.add_argument("--jitter_samples", type=int, default=20)
    ap.add_argument("--jitter_delta", type=int, default=2)
    ap.add_argument("--jitter_seed", type=int, default=42)

    # FE stability (convergence)
    ap.add_argument("--conv_last_w", type=int, default=10)

=======
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
    args = ap.parse_args()

    strategies = _parse_strategies(args.strategies)
    k = int(args.k)

    seed_start = int(args.seed_start)
    seed_end = int(args.seed_end)
    if seed_end < seed_start:
        raise SystemExit("seed_end phải >= seed_start")

    lb = int(args.lb)
    ub = int(args.ub)

    pa5_intervals = _parse_list_int(args.pa5_share_intervals)
    if not pa5_intervals:
        pa5_intervals = [int(args.share_interval)]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(
        args.out_root,
        f"SWEEP_k{k}_iters{args.n_iters}_agents{args.n_agents}_seed{seed_start}-{seed_end}_{ts}",
    )
    ensure_dir(run_dir)
    ensure_dir(os.path.join(run_dir, "per_image"))

    img_paths = list_image_files(args.root)
    if args.limit and args.limit > 0:
        img_paths = img_paths[: int(args.limit)]

    if not img_paths:
        raise SystemExit(f"Không tìm thấy ảnh trong: {args.root}")

    def repair_fn(x: np.ndarray) -> np.ndarray:
        return repair_threshold_vector(
            x,
            k=k,
            lb=lb,
            ub=ub,
            integer=True,
            ensure_unique=True,
            avoid_endpoints=True,
        )

    # rows: chỉ giữ FE + stability FE
    rows: List[Dict] = []

    print("=" * 80)
    print(f"BẮT ĐẦU SEED SWEEP")
    print("=" * 80)
    print(f"Số ảnh: {len(img_paths)}")
    print(f"Strategies: {', '.join(strategies)}")
    print(f"Seeds: {seed_start} đến {seed_end} ({seed_end - seed_start + 1} seeds)")
    print(f"k={k}, n_agents={args.n_agents}, n_iters={args.n_iters}")
    if "PA5" in strategies and len(pa5_intervals) > 1:
        print(f"PA5 share_intervals: {pa5_intervals}")
    print(f"Tổng số runs: {len(img_paths)} ảnh × {seed_end - seed_start + 1} seeds × {len(strategies)} strategies")
    if "PA5" in strategies and len(pa5_intervals) > 1:
        total_pa5_runs = len(img_paths) * (seed_end - seed_start + 1) * len(pa5_intervals)
        total_other_runs = len(img_paths) * (seed_end - seed_start + 1) * (len(strategies) - 1)
        print(f"  = {total_other_runs} (PA1-PA4) + {total_pa5_runs} (PA5 với {len(pa5_intervals)} intervals)")
    print("=" * 80)

    total_runs = 0
    completed_runs = 0
    
    # Tính tổng số runs
    for idx, p in enumerate(img_paths):
        for seed in range(seed_start, seed_end + 1):
            for strat in strategies:
                interval_list = pa5_intervals if strat == "PA5" else [int(args.share_interval)]
                total_runs += len(interval_list)

    for idx, p in enumerate(img_paths):
        gray = read_image_gray(p)
        image_key = f"{idx:05d}_{Path(p).name}"

        print(f"\n{'=' * 80}")
        print(f"[ẢNH {idx+1}/{len(img_paths)}] {Path(p).name}")
        print(f"{'=' * 80}")
        print(f"Kích thước: {gray.shape}")

        per_image: Dict = {
            "image_index": idx,
            "image_name": Path(p).name,
            "image_path": p,
            "k": k,
            "runs": [],
        }

        for seed in range(seed_start, seed_end + 1):
            print(f"\n  [SEED {seed}] ({seed - seed_start + 1}/{seed_end - seed_start + 1})")
            
            for strat_idx, strat in enumerate(strategies):
                interval_list = pa5_intervals if strat == "PA5" else [int(args.share_interval)]

                for interval_idx, interval in enumerate(interval_list):
                    completed_runs += 1
                    progress = (completed_runs / total_runs) * 100
                    
                    if strat == "PA5" and len(pa5_intervals) > 1:
                        print(f"    [{strat_idx+1}/{len(strategies)}] {strat} (interval={interval}, {interval_idx+1}/{len(interval_list)}) - {progress:.1f}% hoàn thành")
                    else:
                        print(f"    [{strat_idx+1}/{len(strategies)}] {strat} - {progress:.1f}% hoàn thành")
                    opt = HybridGWO_WOA(
                        n_agents=int(args.n_agents),
                        n_iters=int(args.n_iters),
                        seed=int(seed),
                        strategy=strat,
                        woa_b=float(args.woa_b),
                        share_interval=int(interval),
                    )

                    def fitness_fn(x: np.ndarray) -> float:
                        return float(fuzzy_entropy_objective(gray, repair_fn(x)))

                    t0 = time.time()
                    best_x, best_f, history = opt.optimize(
                        fitness_fn,
                        dim=k,
                        lb=np.full(k, lb, dtype=float),
                        ub=np.full(k, ub, dtype=float),
                        repair_fn=repair_fn,
                        init_pop=None,
                    )
                    elapsed = time.time() - t0

                    best_x = repair_fn(best_x)
                    fe_best = float(-best_f)

                    print(f"      ✓ FE={fe_best:.6f}, Time={elapsed:.2f}s")

<<<<<<< HEAD
                    stab_j = compute_fe_stability_jitter(
                        gray,
                        best_x,
                        repair_fn,
                        n_samples=int(args.jitter_samples),
                        delta=int(args.jitter_delta),
                        seed=int(args.jitter_seed),
                    )
                    stab_c = compute_fe_stability_convergence(history, last_w=int(args.conv_last_w))

=======
                    # Chỉ lưu FE_best, không cần stability metrics
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
                    row = {
                        "image_name": Path(p).name,
                        "strategy": strat,
                        "seed": int(seed),
                        "pa5_share_interval": int(interval) if strat == "PA5" else "",
                        "fe_best": fe_best,
<<<<<<< HEAD
                        "jitter_fe_std": float(stab_j.get("fe_std", 0.0)),
                        "conv_fe_last_std": float(stab_c.get("fe_last_std", 0.0)),
=======
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
                    }
                    rows.append(row)
                    per_image["runs"].append(row)

        with open(os.path.join(run_dir, "per_image", f"{image_key}.json"), "w", encoding="utf-8") as f:
            json.dump(per_image, f, ensure_ascii=False, indent=2)
        
        print(f"\n  ✓ Đã lưu kết quả ảnh {idx+1}/{len(img_paths)}")

    # sort: FE lớn -> bé
    print(f"\n{'=' * 80}")
    print(f"Đang sắp xếp kết quả theo FE giảm dần...")
    rows_sorted = sorted(rows, key=lambda r: float(r["fe_best"]), reverse=True)

    results_csv = os.path.join(run_dir, "results_sorted.csv")
    print(f"Đang lưu results_sorted.csv...")
    with open(results_csv, "w", newline="", encoding="utf-8") as f:
<<<<<<< HEAD
        fieldnames = ["image_name", "strategy", "seed", "pa5_share_interval", "fe_best", "jitter_fe_std", "conv_fe_last_std"]
=======
        fieldnames = ["image_name", "strategy", "seed", "pa5_share_interval", "fe_best"]
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_sorted)

<<<<<<< HEAD
    # summary theo (strategy, pa5_share_interval)
=======
    # summary theo (strategy, pa5_share_interval) với MeanFE, StdFE, WorstFE
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
    print(f"Đang tạo summary...")
    group: Dict[Tuple[str, str], List[Dict]] = {}
    for r in rows:
        key = (str(r["strategy"]), str(r["pa5_share_interval"]))
        group.setdefault(key, []).append(r)

    summary_rows: List[Dict] = []
    for (strategy, interval), rs in group.items():
        fe = np.array([float(x["fe_best"]) for x in rs], dtype=float)
<<<<<<< HEAD
        js = np.array([float(x["jitter_fe_std"]) for x in rs], dtype=float)
        cs = np.array([float(x["conv_fe_last_std"]) for x in rs], dtype=float)
=======
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba

        summary_rows.append(
            {
                "strategy": strategy,
                "pa5_share_interval": interval,
                "n_records": int(len(rs)),
<<<<<<< HEAD
                "fe_mean": float(fe.mean()),
                "fe_std": float(fe.std(ddof=0)),
                "jitter_fe_std_mean": float(js.mean()),
                "conv_fe_last_std_mean": float(cs.mean()),
            }
        )

    summary_rows_sorted = sorted(summary_rows, key=lambda r: float(r["fe_mean"]), reverse=True)
=======
                "mean_fe": float(fe.mean()),
                "std_fe": float(fe.std(ddof=0)),
                "worst_fe": float(fe.min()),  # FE nhỏ nhất = worst
                "best_fe": float(fe.max()),   # FE lớn nhất = best
            }
        )

    summary_rows_sorted = sorted(summary_rows, key=lambda r: float(r["mean_fe"]), reverse=True)
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba

    summary_csv = os.path.join(run_dir, "summary_sorted.csv")
    print(f"Đang lưu summary_sorted.csv...")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "strategy",
            "pa5_share_interval",
            "n_records",
<<<<<<< HEAD
            "fe_mean",
            "fe_std",
            "jitter_fe_std_mean",
            "conv_fe_last_std_mean",
=======
            "mean_fe",
            "std_fe",
            "worst_fe",
            "best_fe",
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(summary_rows_sorted)

    config = {
        "root": args.root,
        "n_images": len(img_paths),
        "k": k,
        "n_agents": int(args.n_agents),
        "n_iters": int(args.n_iters),
        "seed_start": seed_start,
        "seed_end": seed_end,
        "strategies": strategies,
        "woa_b": float(args.woa_b),
        "pa5_share_intervals": pa5_intervals,
<<<<<<< HEAD
        "jitter_samples": int(args.jitter_samples),
        "jitter_delta": int(args.jitter_delta),
        "jitter_seed": int(args.jitter_seed),
        "conv_last_w": int(args.conv_last_w),
=======
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
    }
    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 80}")
    print(f"✅ HOÀN THÀNH SEED SWEEP!")
    print(f"{'=' * 80}")
    print(f"Tổng số runs: {completed_runs}")
    print(f"Kết quả đã lưu tại:")
    print(f"  📁 {run_dir}")
    print(f"  📄 results_sorted.csv ({len(rows_sorted)} dòng, đã sort theo FE giảm dần)")
<<<<<<< HEAD
    print(f"  📄 summary_sorted.csv ({len(summary_rows_sorted)} dòng, đã sort theo FE mean giảm dần)")
    print(f"  📄 config.json")
    print(f"  📁 per_image/ ({len(img_paths)} files)")
    print(f"\n🏆 Strategy tốt nhất (theo FE mean):")
=======
    print(f"  📄 summary_sorted.csv ({len(summary_rows_sorted)} dòng, đã sort theo Mean FE giảm dần)")
    print(f"  📄 config.json")
    print(f"  📁 per_image/ ({len(img_paths)} files)")
    print(f"\n🏆 Strategy tốt nhất (theo Mean FE):")
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
    if summary_rows_sorted:
        best = summary_rows_sorted[0]
        print(f"  Strategy: {best['strategy']}")
        if best['pa5_share_interval']:
            print(f"  PA5 share_interval: {best['pa5_share_interval']}")
<<<<<<< HEAD
        print(f"  FE mean: {best['fe_mean']:.6f}")
        print(f"  Jitter std mean: {best['jitter_fe_std_mean']:.6f}")
        print(f"  Conv std mean: {best['conv_fe_last_std_mean']:.6f}")
=======
        print(f"  Mean FE: {best['mean_fe']:.6f}")
        print(f"  Std FE: {best['std_fe']:.6f}")
        print(f"  Worst FE: {best['worst_fe']:.6f}")
        print(f"  Best FE: {best['best_fe']:.6f}")
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
    print(f"{'=' * 80}")
    print(run_dir)


if __name__ == "__main__":
    main()

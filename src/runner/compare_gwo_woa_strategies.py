"""
So sánh các phương án kết hợp GWO-WOA (PA1..PA5) trên nhiều ảnh.

Kết quả lưu theo từng ảnh và từng strategy:
- fe_best: FE tốt nhất (FE = -best_f vì fuzzy_entropy_objective trả về -FE)
- mean_fe: FE trung bình
- std_fe: Độ lệch chuẩn FE (đo độ ổn định)
- worst_fe: FE tệ nhất
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np

from src.objective.fuzzy_entropy import fuzzy_entropy_objective
from src.optim.bounds import repair_threshold_vector
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA
from src.segmentation.io import ensure_dir, list_image_files, read_image_gray


def _parse_strategies(s: str) -> List[str]:
    parts = [p.strip().upper() for p in (s or "").split(",") if p.strip()]
    if not parts:
        return ["PA1", "PA2", "PA3", "PA4", "PA5"]
    return parts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, required=True, help="Thư mục chứa ảnh grayscale")
    ap.add_argument("--out_root", type=str, default="outputs/compareGWO-WOA")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--n_agents", type=int, default=30)
    ap.add_argument("--n_iters", type=int, default=80)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--lb", type=int, default=0)
    ap.add_argument("--ub", type=int, default=255)
    ap.add_argument("--woa_b", type=float, default=1.0)
    ap.add_argument("--share_interval", type=int, default=1)
    ap.add_argument("--strategies", type=str, default="PA1,PA2,PA3,PA4,PA5")

    args = ap.parse_args()

    strategies = _parse_strategies(args.strategies)
    k = int(args.k)
    lb = int(args.lb)
    ub = int(args.ub)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(
        args.out_root,
        f"k{k}_iters{args.n_iters}_agents{args.n_agents}_seed{args.seed}_{ts}",
    )
    ensure_dir(run_dir)
    ensure_dir(os.path.join(run_dir, "per_image"))

    img_paths = list_image_files(args.root)
    if args.limit and args.limit > 0:
        img_paths = img_paths[: args.limit]

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

    rows: List[Dict] = []

    print("=" * 80)
    print(f"BẮT ĐẦU SO SÁNH GWO-WOA STRATEGIES")
    print("=" * 80)
    print(f"Số ảnh: {len(img_paths)}")
    print(f"Strategies: {', '.join(strategies)}")
    print(f"k={k}, n_agents={args.n_agents}, n_iters={args.n_iters}, seed={args.seed}")
    print("=" * 80)

    for idx, p in enumerate(img_paths):
        gray = read_image_gray(p)
        image_key = f"{idx:05d}_{Path(p).name}"

        print(f"\n[{idx+1}/{len(img_paths)}] Đang xử lý: {Path(p).name}")
        print(f"  Kích thước ảnh: {gray.shape}")

        per_image: Dict[str, Dict] = {
            "image_index": idx,
            "image_path": p,
            "k": k,
            "strategies": {},
        }

        for strat_idx, strat in enumerate(strategies):
            print(f"  [{strat_idx+1}/{len(strategies)}] Strategy: {strat}")
            opt = HybridGWO_WOA(
                n_agents=int(args.n_agents),
                n_iters=int(args.n_iters),
                seed=int(args.seed),
                strategy=strat,
                woa_b=float(args.woa_b),
                share_interval=int(args.share_interval),
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

            print(f"    ✓ Hoàn thành trong {elapsed:.2f}s, FE={fe_best:.6f}")

            # Chỉ lưu các chỉ số FE quan trọng
            row = {
                "image_name": Path(p).name,
                "strategy": strat,
                "seed": int(args.seed),
                "share_interval": int(args.share_interval) if strat == "PA5" else "",
                "fe_best": fe_best,
            }
            rows.append(row)

            per_image["strategies"][strat] = {
                "fe_best": fe_best,
                "thresholds": best_x.tolist(),
                "time_sec": float(elapsed),
            }

        with open(os.path.join(run_dir, "per_image", f"{image_key}.json"), "w", encoding="utf-8") as f:
            json.dump(per_image, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ Đã lưu kết quả ảnh {idx+1}/{len(img_paths)}")

    # Sắp xếp theo FE giảm dần
    rows_sorted = sorted(rows, key=lambda r: float(r["fe_best"]), reverse=True)
    
    csv_path = os.path.join(run_dir, "results_sorted.csv")
    print(f"\n{'=' * 80}")
    print(f"Đang lưu kết quả vào CSV...")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["image_name", "strategy", "seed", "share_interval", "fe_best"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_sorted)

    # Tính toán summary với MeanFE, StdFE, WorstFE
    summary_rows: List[Dict] = []
    for strat in strategies:
        strat_rows = [r for r in rows if r["strategy"] == strat]
        fe = np.array([r["fe_best"] for r in strat_rows], dtype=float)

        summary_rows.append({
            "strategy": strat,
            "share_interval": int(args.share_interval) if strat == "PA5" else "",
            "n_images": int(len(strat_rows)),
            "mean_fe": float(fe.mean()),
            "std_fe": float(fe.std(ddof=0)),
            "worst_fe": float(fe.min()),  # FE nhỏ nhất = worst
            "best_fe": float(fe.max()),   # FE lớn nhất = best
        })

    summary_rows_sorted = sorted(summary_rows, key=lambda r: float(r["mean_fe"]), reverse=True)
    
    summary_csv = os.path.join(run_dir, "summary_sorted.csv")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["strategy", "share_interval", "n_images", "mean_fe", "std_fe", "worst_fe", "best_fe"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(summary_rows_sorted)

    config = {
        "root": args.root,
        "n_images": len(img_paths),
        "k": k,
        "n_agents": int(args.n_agents),
        "n_iters": int(args.n_iters),
        "seed": int(args.seed),
        "woa_b": float(args.woa_b),
        "share_interval": int(args.share_interval),
        "strategies": strategies,
    }
    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 80}")
    print(f"✅ HOÀN THÀNH!")
    print(f"{'=' * 80}")
    print(f"Kết quả đã lưu tại:")
    print(f"  📁 {run_dir}")
    print(f"  📄 results_sorted.csv ({len(rows_sorted)} dòng)")
    print(f"  📄 summary_sorted.csv ({len(summary_rows_sorted)} dòng)")
    print(f"  📄 config.json")
    print(f"  📁 per_image/ ({len(img_paths)} files)")
    print(f"\n🏆 Strategy tốt nhất (theo Mean FE):")
    if summary_rows_sorted:
        best = summary_rows_sorted[0]
        print(f"  Strategy: {best['strategy']}")
        if best['share_interval']:
            print(f"  Share interval: {best['share_interval']}")
        print(f"  Mean FE: {best['mean_fe']:.6f}")
        print(f"  Std FE: {best['std_fe']:.6f}")
        print(f"  Worst FE: {best['worst_fe']:.6f}")
        print(f"  Best FE: {best['best_fe']:.6f}")
    print(f"{'=' * 80}")
    print(run_dir)


if __name__ == "__main__":
    main()

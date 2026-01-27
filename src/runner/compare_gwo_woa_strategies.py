"""
So sánh các phương án kết hợp GWO-WOA (PA1..PA5) trên nhiều ảnh.

Kết quả lưu theo từng ảnh và từng strategy:
- fe_best: FE tốt nhất (FE = -best_f vì fuzzy_entropy_objective trả về -FE)
- stability_jitter_*: ổn định khi jitter ngưỡng (std càng nhỏ càng ổn định)
- stability_conv_*: ổn định hội tụ (std càng nhỏ càng ổn định)
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
from src.objective.thresholding_with_penalties import (
    compute_fe_stability_convergence,
    compute_fe_stability_jitter,
)
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

    # FE stability (jitter)
    ap.add_argument("--jitter_samples", type=int, default=20)
    ap.add_argument("--jitter_delta", type=int, default=2)
    ap.add_argument("--jitter_seed", type=int, default=42)

    # FE stability (convergence)
    ap.add_argument("--conv_last_w", type=int, default=10)

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

            stab_j = compute_fe_stability_jitter(
                gray,
                best_x,
                repair_fn,
                n_samples=int(args.jitter_samples),
                delta=int(args.jitter_delta),
                seed=int(args.jitter_seed),
            )
            stab_c = compute_fe_stability_convergence(history, last_w=int(args.conv_last_w))

            row = {
                "image_index": idx,
                "image_name": Path(p).name,
                "image_path": p,
                "strategy": strat,
                "k": k,
                "n_agents": int(args.n_agents),
                "n_iters": int(args.n_iters),
                "seed": int(args.seed),
                "woa_b": float(args.woa_b),
                "share_interval": int(args.share_interval),
                "fe_best": fe_best,
                "time_sec": float(elapsed),
                "thresholds": ",".join(map(str, best_x.tolist())),
                "jitter_fe_original": float(stab_j.get("fe_original", 0.0)),
                "jitter_fe_mean": float(stab_j.get("fe_mean", 0.0)),
                "jitter_fe_std": float(stab_j.get("fe_std", 0.0)),
                "jitter_fe_min": float(stab_j.get("fe_min", 0.0)),
                "jitter_fe_max": float(stab_j.get("fe_max", 0.0)),
                "conv_fe_first": float(stab_c.get("fe_first", 0.0)),
                "conv_fe_last": float(stab_c.get("fe_last", 0.0)),
                "conv_fe_last_mean": float(stab_c.get("fe_last_mean", 0.0)),
                "conv_fe_last_std": float(stab_c.get("fe_last_std", 0.0)),
                "conv_fe_improvement": float(stab_c.get("fe_improvement", 0.0)),
            }
            rows.append(row)

            per_image["strategies"][strat] = {
                "fe_best": fe_best,
                "thresholds": best_x.tolist(),
                "time_sec": float(elapsed),
                "stability_jitter": stab_j,
                "stability_convergence": stab_c,
            }

        with open(os.path.join(run_dir, "per_image", f"{image_key}.json"), "w", encoding="utf-8") as f:
            json.dump(per_image, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ Đã lưu kết quả ảnh {idx+1}/{len(img_paths)}")

    csv_path = os.path.join(run_dir, "results.csv")
    print(f"\n{'=' * 80}")
    print(f"Đang lưu kết quả vào CSV...")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = list(rows[0].keys()) if rows else []
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    summary: Dict[str, Dict] = {
        "config": {
            "root": args.root,
            "n_images": len(img_paths),
            "k": k,
            "n_agents": int(args.n_agents),
            "n_iters": int(args.n_iters),
            "seed": int(args.seed),
            "woa_b": float(args.woa_b),
            "share_interval": int(args.share_interval),
            "strategies": strategies,
            "jitter_samples": int(args.jitter_samples),
            "jitter_delta": int(args.jitter_delta),
            "jitter_seed": int(args.jitter_seed),
            "conv_last_w": int(args.conv_last_w),
        },
        "by_strategy": {},
    }

    for strat in strategies:
        strat_rows = [r for r in rows if r["strategy"] == strat]
        fe = np.array([r["fe_best"] for r in strat_rows], dtype=float)
        t = np.array([r["time_sec"] for r in strat_rows], dtype=float)

        summary["by_strategy"][strat] = {
            "n_images": int(len(strat_rows)),
            "fe_mean": float(fe.mean()),
            "fe_std": float(fe.std(ddof=0)),
            "time_mean_sec": float(t.mean()),
        }

    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 80}")
    print(f"✅ HOÀN THÀNH!")
    print(f"{'=' * 80}")
    print(f"Kết quả đã lưu tại:")
    print(f"  📁 {run_dir}")
    print(f"  📄 results.csv")
    print(f"  📄 summary.json")
    print(f"  📁 per_image/ ({len(img_paths)} files)")
    print(f"{'=' * 80}")
    print(run_dir)


if __name__ == "__main__":
    main()

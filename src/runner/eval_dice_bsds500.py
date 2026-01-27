"""
Evaluate DICE score on BSDS500 dataset
"""
from __future__ import annotations

import argparse
import csv
import os
import numpy as np

from src.objective.fuzzy_entropy import fuzzy_entropy_objective
from src.optim.bounds import repair_threshold_vector
from src.optim.gwo import GWO
from src.optim.woa import WOA
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA

from src.segmentation.io import read_image_gray
from src.segmentation.apply_thresholds import apply_thresholds

from src.data.bsds500_gt import (
    build_pairs,
    read_bsds_gt_boundary_mask,
    seg_to_boundary_mask,
    dice_binary,
)


def make_optimizer(algo: str, n_agents: int, n_iters: int, seed: int | None, strategy: str, woa_b: float, share_interval: int):
    algo_u = algo.upper()
    if algo_u == "GWO":
        return GWO(n_agents=n_agents, n_iters=n_iters, seed=seed)
    if algo_u == "WOA":
        return WOA(n_agents=n_agents, n_iters=n_iters, seed=seed, b=woa_b)
    if algo_u == "HYBRID":
        return HybridGWO_WOA(n_agents=n_agents, n_iters=n_iters, seed=seed, strategy=strategy.upper(), woa_b=woa_b, share_interval=share_interval)
    raise ValueError("algo phải là: GWO | WOA | HYBRID")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images_root", type=str, default="dataset/BDS500/images")
    ap.add_argument("--gt_root", type=str, default="dataset/BDS500/ground_truth")
    ap.add_argument("--split", type=str, default="test")  # train|val|test
    ap.add_argument("--out_csv", type=str, default="outputs/runs/dice_bsds500.csv")

    ap.add_argument("--algo", type=str, default="GWO")
    ap.add_argument("--strategy", type=str, default="PA1")
    ap.add_argument("--k", type=int, default=10)

    ap.add_argument("--n_agents", type=int, default=30)
    ap.add_argument("--n_iters", type=int, default=80)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--woa_b", type=float, default=1.0)
    ap.add_argument("--share_interval", type=int, default=1)

    ap.add_argument("--gt_thr", type=float, default=0.5)  # threshold GT boundary
    ap.add_argument("--gt_fuse", type=str, default="max")  # max|mean (nếu .mat)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    images_dir = os.path.join(args.images_root, args.split)
    gt_dir = os.path.join(args.gt_root, args.split)

    pairs = build_pairs(images_dir, gt_dir)
    if args.limit and args.limit > 0:
        pairs = pairs[: args.limit]

    print(f"Found {len(pairs)} image pairs in {args.split} split")
    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)

    rows = []
    dice_list = []

    for idx, (img_path, gt_path) in enumerate(pairs):
        print(f"\n[{idx+1}/{len(pairs)}] Processing: {os.path.basename(img_path)}")
        
        gray = read_image_gray(img_path)

        k = int(args.k)
        lb, ub = 0, 255

        def repair_fn(x: np.ndarray) -> np.ndarray:
            return repair_threshold_vector(x, k=k, lb=lb, ub=ub, integer=True, ensure_unique=True)

        def fitness_fn(x: np.ndarray) -> float:
            return float(fuzzy_entropy_objective(gray, repair_fn(x)))  # minimize (-entropy)

        opt = make_optimizer(args.algo, args.n_agents, args.n_iters, int(args.seed) + idx, args.strategy, args.woa_b, args.share_interval)
        best_x, best_f, _ = opt.optimize(
            fitness_fn,
            dim=k,
            lb=np.full(k, lb, dtype=float),
            ub=np.full(k, ub, dtype=float),
            repair_fn=repair_fn,
            init_pop=None,
        )

        best_x = repair_fn(best_x)
        seg = apply_thresholds(gray, best_x)  # uint8 segmented image

        pred_b = seg_to_boundary_mask(seg)
        gt_b = read_bsds_gt_boundary_mask(gt_path, thr=args.gt_thr, fuse=args.gt_fuse)

        d = dice_binary(gt_b, pred_b)
        dice_list.append(d)

        print(f"  best_f={best_f:.6f}, DICE={d:.4f}")

        rows.append(
            {
                "index": idx,
                "image": img_path,
                "gt": gt_path,
                "dice_boundary": float(d),
                "best_f": float(best_f),
                "thresholds": ",".join(map(str, best_x.tolist())),
            }
        )

    mean_dice = float(np.mean(dice_list)) if dice_list else 0.0

    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["mean_dice"] if rows else ["mean_dice"])
        if rows:
            w.writeheader()
            for r in rows:
                rr = dict(r)
                rr["mean_dice"] = ""
                w.writerow(rr)
            w.writerow({"mean_dice": mean_dice})
        else:
            w.writeheader()
            w.writerow({"mean_dice": mean_dice})

    print(f"\n{'='*60}")
    print(f"Results saved to: {args.out_csv}")
    print(f"Mean DICE (Boundary): {mean_dice:.4f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

"""
Learn global optimal thresholds on BSDS500 train set by optimizing Boundary-DICE
"""
from __future__ import annotations

import argparse
import json
import os
import time
import numpy as np

from src.optim.bounds import repair_threshold_vector
from src.optim.gwo import GWO
from src.optim.woa import WOA
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA

from src.segmentation.io import read_image_gray
from src.segmentation.apply_thresholds import apply_thresholds

from src.data.bsds500_gt import build_pairs, read_bsds_gt_boundary_mask, seg_to_boundary_mask, dice_binary


def make_optimizer(algo: str, n_agents: int, n_iters: int, seed: int | None, strategy: str, woa_b: float, share_interval: int):
    algo_u = algo.upper()
    if algo_u == "GWO":
        return GWO(n_agents=n_agents, n_iters=n_iters, seed=seed)
    if algo_u == "WOA":
        return WOA(n_agents=n_agents, n_iters=n_iters, seed=seed, b=woa_b)
    if algo_u == "HYBRID":
        return HybridGWO_WOA(n_agents=n_agents, n_iters=n_iters, seed=seed, strategy=strategy.upper(), woa_b=woa_b, share_interval=share_interval)
    raise ValueError("algo pháº£i lÃ : GWO | WOA | HYBRID")


def main():
    ap = argparse.ArgumentParser(description="TÃ¬m ngÆ°á»¡ng tá»‘i Æ°u toÃ n cá»¥c trÃªn BSDS500 train set")
    ap.add_argument("--images_root", type=str, default="dataset/BDS500/images")
    ap.add_argument("--gt_root", type=str, default="dataset/BDS500/ground_truth")
    ap.add_argument("--split", type=str, default="train")  # train|val|test (Ä‘á»ƒ há»c global)
    ap.add_argument("--k", type=int, default=10)

    ap.add_argument("--algo", type=str, default="GWO")
    ap.add_argument("--strategy", type=str, default="PA1")
    ap.add_argument("--n_agents", type=int, default=30)
    ap.add_argument("--n_iters", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--woa_b", type=float, default=1.0)
    ap.add_argument("--share_interval", type=int, default=10)

    ap.add_argument("--gt_thr", type=float, default=0.5)
    ap.add_argument("--gt_fuse", type=str, default="max")  # max|mean náº¿u .mat
    ap.add_argument("--limit", type=int, default=0)  # giá»›i háº¡n sá»‘ áº£nh train Ä‘á»ƒ cháº¡y nhanh

    ap.add_argument("--out_dir", type=str, default="outputs/runs/global_thresholds")
    args = ap.parse_args()

    print("=" * 80)
    print("Há»ŒC NGÆ¯á» NG Tá»I Æ¯U TOÃ€N Cá»¤C TRÃŠN BSDS500")
    print("=" * 80)
    print(f"Split: {args.split}")
    print(f"Algorithm: {args.algo} {f'({args.strategy})' if args.algo.upper() == 'HYBRID' else ''}")
    print(f"k={args.k}, n_agents={args.n_agents}, n_iters={args.n_iters}")
    print("=" * 80)

    images_dir = os.path.join(args.images_root, args.split)
    gt_dir = os.path.join(args.gt_root, args.split)

    pairs = build_pairs(images_dir, gt_dir)
    if args.limit and args.limit > 0:
        pairs = pairs[: args.limit]
    if not pairs:
        raise RuntimeError("KhÃ´ng tÃ¬m Ä‘Æ°á»£c cáº·p (image, gt). Kiá»ƒm tra Ä‘Æ°á»ng dáº«n vÃ  tÃªn file (stem) pháº£i khá»›p.")

    print(f"\nTÃ¬m tháº¥y {len(pairs)} cáº·p áº£nh-GT")
    print("Äang táº£i áº£nh vÃ  ground truth vÃ o bá»™ nhá»›...")

    os.makedirs(args.out_dir, exist_ok=True)

    # Preload Ä‘á»ƒ objective nhanh hÆ¡n
    load_start = time.time()
    images = []
    gts = []
    for idx, (img_path, gt_path) in enumerate(pairs):
        if (idx + 1) % 10 == 0:
            print(f"  ÄÃ£ táº£i {idx + 1}/{len(pairs)} áº£nh...")
        gray = read_image_gray(img_path)
        gt_b = read_bsds_gt_boundary_mask(gt_path, thr=args.gt_thr, fuse=args.gt_fuse)
        images.append(gray)
        gts.append(gt_b)
    
    load_time = time.time() - load_start
    print(f"âœ“ ÄÃ£ táº£i xong {len(pairs)} áº£nh trong {load_time:.2f}s")

    k = int(args.k)
    lb, ub = 0, 255

    def repair_fn(x: np.ndarray) -> np.ndarray:
        return repair_threshold_vector(x, k=k, lb=lb, ub=ub, integer=True, ensure_unique=True)

    # Objective: minimize (1 - mean Dice)
    # Tá»‘i Æ°u Ä‘á»ƒ tÃ¬m ngÆ°á»¡ng cÃ³ mean DICE cao nháº¥t trÃªn toÃ n bá»™ train set
    eval_count = [0]
    
    def objective(x: np.ndarray) -> float:
        t = repair_fn(x)
        dices = []
        for gray, gt_b in zip(images, gts):
            seg = apply_thresholds(gray, t)
            pred_b = seg_to_boundary_mask(seg)
            dices.append(dice_binary(gt_b, pred_b))
        mean_dice = float(np.mean(dices)) if dices else 0.0
        
        eval_count[0] += 1
        if eval_count[0] % 10 == 0:
            print(f"  Evaluation {eval_count[0]}: mean_dice={mean_dice:.4f}, thresholds={t.tolist()}")
        
        return float(1.0 - mean_dice)  # minimize (1 - DICE)

    print("\n" + "=" * 80)
    print("Báº®T Äáº¦U Tá»I Æ¯U NGÆ¯á» NG")
    print("=" * 80)
    
    opt_start = time.time()
    opt = make_optimizer(args.algo, args.n_agents, args.n_iters, args.seed, args.strategy, args.woa_b, args.share_interval)

    best_x, best_f, history = opt.optimize(
        objective,
        dim=k,
        lb=np.full(k, lb, dtype=float),
        ub=np.full(k, ub, dtype=float),
        repair_fn=repair_fn,
        init_pop=None,
    )

    opt_time = time.time() - opt_start
    best_x = repair_fn(best_x)
    best_mean_dice = 1.0 - float(best_f)

    print("=" * 80)
    print("Káº¾T QUáº¢ Tá»I Æ¯U")
    print("=" * 80)
    print(f"Thá»i gian tá»‘i Æ°u: {opt_time:.2f}s")
    print(f"Sá»‘ láº§n Ä‘Ã¡nh giÃ¡: {eval_count[0]}")
    print(f"Mean Boundary-DICE: {best_mean_dice:.4f}")
    print(f"NgÆ°á»¡ng tá»‘i Æ°u: {best_x.tolist()}")
    print("=" * 80)

    # LÆ°u káº¿t quáº£
    out = {
        "k": k,
        "thresholds": best_x.tolist(),
        "mean_boundary_dice": best_mean_dice,
        "algo": args.algo.upper(),
        "strategy": args.strategy.upper() if args.algo.upper() == "HYBRID" else "",
        "n_agents": args.n_agents,
        "n_iters": args.n_iters,
        "seed": args.seed,
        "gt_thr": args.gt_thr,
        "gt_fuse": args.gt_fuse,
        "num_images": len(pairs),
        "split": args.split,
        "optimization_time": opt_time,
        "load_time": load_time,
    }

    out_file = os.path.join(args.out_dir, "global_thresholds.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\nâœ“ ÄÃ£ lÆ°u káº¿t quáº£ vÃ o: {out_file}")
    print(f"\nÄá»ƒ test ngÆ°á»¡ng nÃ y trÃªn test set, cháº¡y:")
    print(f"python -m src.runner.eval_global_thresholds_bsds500 \\")
    print(f"  --thresholds_json {out_file} \\")
    print(f"  --split test")


if __name__ == "__main__":
    main()

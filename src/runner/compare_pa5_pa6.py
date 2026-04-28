from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from src.data.bsds500_gt import build_pairs, read_bsds_gt_boundary_mask, seg_to_boundary_mask
from src.metrics.quality import boundary_dice_binary, compute_psnr, compute_ssim
from src.metrics.statistics import standard_deviation, wilcoxon_signed_rank
from src.objective.fuzzy_entropy_s import fuzzy_entropy_value
from src.optim.bounds import repair_threshold_vector
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA
from src.segmentation.apply_thresholds import apply_thresholds
from src.segmentation.io import ensure_dir, list_image_files, read_image_gray


def _parse_strategies(text: str) -> List[str]:
    parts = [p.strip().upper() for p in (text or "").split(",") if p.strip()]
    return parts or ["PA5", "PA6"]


def _load_pairs(images_root: str, gt_root: str | None, limit: int) -> List[Tuple[str, str | None]]:
    if gt_root:
        pairs = [(img, gt) for img, gt in build_pairs(images_root, gt_root)]
    else:
        pairs = [(img, None) for img in list_image_files(images_root)]
    return pairs[:limit] if limit > 0 else pairs


def _base_seed(seed: int, image_name: str) -> int:
    acc = int(seed)
    for idx, ch in enumerate(str(image_name)):
        acc = (acc * 131 + (idx + 1) * ord(ch)) % (2**31 - 1)
    return int(acc)


def _summary_rows(rows: List[Dict], strategies: List[str]) -> List[Dict]:
    out: List[Dict] = []
    for strategy in strategies:
        rs = [r for r in rows if r["strategy"] == strategy]
        fe = [r["fe"] for r in rs]
        boundary_dsc = [r["boundary_dsc"] for r in rs if r["boundary_dsc"] is not None]
        psnr = [r["psnr"] for r in rs]
        ssim = [r["ssim"] for r in rs]
        times = [r["time_sec"] for r in rs]
        out.append(
            {
                "strategy": strategy,
                "n_images": len(rs),
                "mean_fe": float(np.mean(fe)) if fe else 0.0,
                "sd_fe": standard_deviation(fe),
                "mean_boundary_dsc": float(np.mean(boundary_dsc)) if boundary_dsc else None,
                "sd_boundary_dsc": standard_deviation(boundary_dsc) if boundary_dsc else None,
                "mean_psnr": float(np.mean(psnr)) if psnr else 0.0,
                "sd_psnr": standard_deviation(psnr),
                "mean_ssim": float(np.mean(ssim)) if ssim else 0.0,
                "sd_ssim": standard_deviation(ssim),
                "mean_time_sec": float(np.mean(times)) if times else 0.0,
                "sd_time_sec": standard_deviation(times),
            }
        )
    return out


def _wilcoxon_rows(rows: List[Dict], base: str, challenger: str) -> List[Dict]:
    by_image: Dict[str, Dict[str, Dict]] = {}
    for row in rows:
        by_image.setdefault(row["image_name"], {})[row["strategy"]] = row

    paired = [(vals[base], vals[challenger]) for vals in by_image.values() if base in vals and challenger in vals]
    if not paired:
        return []

    metrics = ["fe", "boundary_dsc", "psnr", "ssim", "time_sec"]
    out: List[Dict] = []
    for metric in metrics:
        x = [left[metric] for left, right in paired if left[metric] is not None and right[metric] is not None]
        y = [right[metric] for left, right in paired if left[metric] is not None and right[metric] is not None]
        stat = wilcoxon_signed_rank(x, y)
        out.append({"metric": metric, "base": base, "challenger": challenger, **stat})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images_root", type=str, required=True)
    ap.add_argument("--gt_root", type=str, default="")
    ap.add_argument("--out_root", type=str, default="outputs/compare_pa5_pa6")
    ap.add_argument("--strategies", type=str, default="PA5,PA6")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--n_agents", type=int, default=30)
    ap.add_argument("--n_iters", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--lb", type=int, default=0)
    ap.add_argument("--ub", type=int, default=255)
    ap.add_argument("--woa_b", type=float, default=1.0)
    ap.add_argument("--share_interval", type=int, default=10)
    args = ap.parse_args()

    strategies = _parse_strategies(args.strategies)
    pairs = _load_pairs(args.images_root, args.gt_root or None, int(args.limit))
    if not pairs:
        raise SystemExit("KhÃƒÂ´ng tÃƒÂ¬m thÃ¡ÂºÂ¥y Ã¡ÂºÂ£nh phÃƒÂ¹ hÃ¡Â»Â£p.")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(args.out_root, f"k{args.k}_seed{args.seed}_{ts}")
    ensure_dir(run_dir)
    ensure_dir(os.path.join(run_dir, "per_image"))

    def repair_fn(x: np.ndarray) -> np.ndarray:
        return repair_threshold_vector(
            x,
            k=int(args.k),
            lb=int(args.lb),
            ub=int(args.ub),
            integer=True,
            ensure_unique=True,
            avoid_endpoints=False,
        )

    rows: List[Dict] = []

    for idx, (img_path, gt_path) in enumerate(pairs):
        gray = read_image_gray(img_path)
        gt_boundary = read_bsds_gt_boundary_mask(gt_path) if gt_path else None
        image_name = Path(img_path).name
        base_seed = _base_seed(int(args.seed), image_name)
        shared_init = np.random.default_rng(base_seed).uniform(
            int(args.lb),
            int(args.ub),
            size=(int(args.n_agents), int(args.k)),
        )

        per_image: Dict[str, Dict] = {
            "image_name": image_name,
            "image_path": img_path,
            "base_seed": base_seed,
            "results": {},
        }

        for strategy in strategies:
            optimizer = HybridGWO_WOA(
                n_agents=int(args.n_agents),
                n_iters=int(args.n_iters),
                seed=base_seed,
                strategy=strategy,
                woa_b=float(args.woa_b),
                share_interval=int(args.share_interval),
            )

            def fitness_fn(x: np.ndarray) -> float:
                return -float(fuzzy_entropy_value(gray, repair_fn(x)))

            t0 = time.time()
            best_x, best_f, history = optimizer.optimize(
                fitness_fn,
                dim=int(args.k),
                lb=np.full(int(args.k), int(args.lb), dtype=float),
                ub=np.full(int(args.k), int(args.ub), dtype=float),
                repair_fn=repair_fn,
                init_pop=shared_init.copy(),
            )
            elapsed = float(time.time() - t0)

            best_x = repair_fn(best_x)
            seg = apply_thresholds(gray, best_x)
            pred_boundary = seg_to_boundary_mask(seg)

            boundary_dsc = boundary_dice_binary(gt_boundary, pred_boundary) if gt_boundary is not None else None
            fe = float(fuzzy_entropy_value(gray, best_x))

            row = {
                "image_name": image_name,
                "strategy": strategy,
                "seed": base_seed,
                "thresholds": ",".join(map(str, np.asarray(best_x, dtype=int).tolist())),
                "best_f": float(best_f),
                "fe": fe,
                "boundary_dsc": float(boundary_dsc) if boundary_dsc is not None else None,
                "psnr": float(compute_psnr(gray, seg, data_range=255.0)),
                "ssim": float(compute_ssim(gray, seg, data_range=255.0)),
                "time_sec": elapsed,
            }
            rows.append(row)
            per_image["results"][strategy] = row

        with open(os.path.join(run_dir, "per_image", f"{idx:05d}_{image_name}.json"), "w", encoding="utf-8") as f:
            json.dump(per_image, f, ensure_ascii=False, indent=2)

    if not rows:
        raise SystemExit("KhÃƒÂ´ng cÃƒÂ³ kÃ¡ÂºÂ¿t quÃ¡ÂºÂ£ hÃ¡Â»Â£p lÃ¡Â»â€¡.")

    summary_rows = _summary_rows(rows, strategies)
    wilcoxon_rows = _wilcoxon_rows(rows, strategies[0], strategies[1]) if len(strategies) >= 2 else []

    with open(os.path.join(run_dir, "results.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with open(os.path.join(run_dir, "summary.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    if wilcoxon_rows:
        with open(os.path.join(run_dir, "wilcoxon.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(wilcoxon_rows[0].keys()))
            writer.writeheader()
            writer.writerows(wilcoxon_rows)

    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                **vars(args),
                "note": "Secondary runner. Main report flow should use evaluate_main.py.",
                "metric_name": "boundary_dsc",
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(run_dir)


if __name__ == "__main__":
    main()

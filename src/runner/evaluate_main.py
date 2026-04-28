from __future__ import annotations

import argparse
import csv
import json
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

from src.data.bsds500_gt import build_pairs, read_bsds_gt_boundary_mask, seg_to_boundary_mask
from src.metrics.quality import boundary_dice_binary, compute_psnr, compute_ssim
from src.metrics.statistics import convergence_iteration, standard_deviation, wilcoxon_signed_rank
from src.objective.fuzzy_entropy_s import fuzzy_entropy_value
from src.optim.bounds import repair_threshold_vector
from src.optim.gwo import GWO
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA
from src.optim.otsu import OtsuMulti, OtsuUnsupportedError
from src.optim.pso import PSO
from src.optim.woa import WOA
from src.segmentation.apply_thresholds import apply_thresholds
from src.segmentation.io import ensure_dir, list_image_files, read_image_gray


SUPPORTED_ALGOS = ("OTSU", "PSO", "WOA", "GWO", "PA5", "PA6")


def _parse_algos(text: str) -> List[str]:
    parts = [p.strip().upper() for p in (text or "").split(",") if p.strip()]
    algos = parts or ["OTSU", "PSO", "WOA", "GWO", "PA5"]
    invalid = [algo for algo in algos if algo not in SUPPORTED_ALGOS]
    if invalid:
        raise ValueError(f"Unsupported algorithms: {invalid}. Supported: {list(SUPPORTED_ALGOS)}")
    return algos


def _parse_seeds(text: str, seed_start: int, n_seeds: int) -> List[int]:
    if text.strip():
        return [int(part.strip()) for part in text.split(",") if part.strip()]
    return [seed_start + idx for idx in range(max(1, int(n_seeds)))]


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


def _shared_init(seed: int, n_agents: int, k: int, lb: int, ub: int) -> np.ndarray:
    return np.random.default_rng(seed).uniform(lb, ub, size=(n_agents, k))


def _make_optimizer(algo: str, args, seed: int):
    if algo == "GWO":
        return GWO(n_agents=int(args.n_agents), n_iters=int(args.n_iters), seed=seed)
    if algo == "WOA":
        return WOA(n_agents=int(args.n_agents), n_iters=int(args.n_iters), seed=seed, b=float(args.woa_b))
    if algo == "PSO":
        return PSO(n_agents=int(args.n_agents), n_iters=int(args.n_iters), seed=seed)
    if algo == "PA5":
        return HybridGWO_WOA(
            n_agents=int(args.n_agents),
            n_iters=int(args.n_iters),
            seed=seed,
            strategy="PA5",
            woa_b=float(args.woa_b),
            share_interval=int(args.share_interval),
        )
    if algo == "PA6":
        return HybridGWO_WOA(
            n_agents=int(args.n_agents),
            n_iters=int(args.n_iters),
            seed=seed,
            strategy="PA6",
            woa_b=float(args.woa_b),
            share_interval=int(args.share_interval),
        )
    if algo == "OTSU":
        return OtsuMulti()
    raise ValueError(f"Unsupported algorithm: {algo}")


def _run_algorithm(
    algo: str,
    gray: np.ndarray,
    fitness_fn,
    repair_fn,
    shared_init: np.ndarray,
    run_seed: int,
    args,
) -> Tuple[np.ndarray, float, List[Dict]]:
    if algo == "OTSU":
        opt = _make_optimizer(algo, args, run_seed)
        best_x, best_f, history = opt.optimize_with_image(
            gray,
            int(args.k),
            fitness_fn=fitness_fn,
            repair_fn=repair_fn,
        )
        if best_f is None:
            best_f = float(fitness_fn(best_x))
        return np.asarray(best_x, dtype=float), float(best_f), history

    opt = _make_optimizer(algo, args, run_seed)
    best_x, best_f, history = opt.optimize(
        fitness_fn,
        dim=int(args.k),
        lb=np.full(int(args.k), int(args.lb), dtype=float),
        ub=np.full(int(args.k), int(args.ub), dtype=float),
        repair_fn=repair_fn,
        init_pop=shared_init.copy(),
    )
    best_x = np.asarray(repair_fn(best_x), dtype=float)
    return best_x, float(best_f), history


def _summary_rows(rows: List[Dict], algos: Sequence[str]) -> List[Dict]:
    summary: List[Dict] = []
    dsc_key = "boundary_dsc"

    for algo in algos:
        algo_rows = [row for row in rows if row["algo"] == algo]
        if not algo_rows:
            continue

        def arr(key: str) -> np.ndarray:
            vals = [row[key] for row in algo_rows if row.get(key) is not None]
            return np.asarray(vals, dtype=float)

        fe = arr("FE")
        dsc = arr(dsc_key)
        psnr = arr("PSNR")
        ssim = arr("SSIM")
        time_arr = arr("time")
        row = {
            "algo": algo,
            "mean_FE": float(fe.mean()) if fe.size else 0.0,
            "sd_FE": standard_deviation(fe),
            "mean_PSNR": float(psnr.mean()) if psnr.size else 0.0,
            "sd_PSNR": standard_deviation(psnr),
            "mean_SSIM": float(ssim.mean()) if ssim.size else 0.0,
            "sd_SSIM": standard_deviation(ssim),
            "mean_time": float(time_arr.mean()) if time_arr.size else 0.0,
            "sd_time": standard_deviation(time_arr),
        }
        row["mean_boundary_dsc"] = float(dsc.mean()) if dsc.size else None
        row["sd_boundary_dsc"] = standard_deviation(dsc) if dsc.size else None

        summary.append(row)

    return summary


def _wilcoxon_rows(rows: List[Dict], base_algo: str, algos: Iterable[str]) -> List[Dict]:
    grouped: Dict[Tuple[str, int], Dict[str, Dict]] = defaultdict(dict)
    for row in rows:
        grouped[(row["image_name"], int(row["seed"]))][row["algo"]] = row

    metrics = ["FE", "boundary_dsc", "PSNR", "SSIM", "time"]
    output: List[Dict] = []

    for algo in algos:
        if algo == base_algo:
            continue
        pairs = [
            (vals[base_algo], vals[algo])
            for vals in grouped.values()
            if base_algo in vals and algo in vals
        ]
        if not pairs:
            continue

        for metric in metrics:
            x = [left[metric] for left, right in pairs if left.get(metric) is not None and right.get(metric) is not None]
            y = [right[metric] for left, right in pairs if left.get(metric) is not None and right.get(metric) is not None]
            stat = wilcoxon_signed_rank(x, y)
            output.append(
                {
                    "base_algo": base_algo,
                    "challenger_algo": algo,
                    "metric": metric,
                    "mean_base": float(np.mean(x)) if x else None,
                    "mean_challenger": float(np.mean(y)) if y else None,
                    "delta_mean": (float(np.mean(x)) - float(np.mean(y))) if x and y else None,
                    **stat,
                }
            )

    return output


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images_root", type=str, required=True, help="Image split to evaluate, e.g. dataset/BDS500/images/val")
    ap.add_argument("--gt_root", type=str, default="", help="Matching ground-truth root, e.g. dataset/BDS500/ground_truth/val")
    ap.add_argument("--out_root", type=str, default="outputs/evaluate_main")
    ap.add_argument("--algos", type=str, default="OTSU,PSO,WOA,GWO,PA5")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--n_agents", type=int, default=30)
    ap.add_argument("--n_iters", type=int, default=100)
    ap.add_argument("--seed_start", type=int, default=42)
    ap.add_argument("--n_seeds", type=int, default=5)
    ap.add_argument("--seeds", type=str, default="")
    ap.add_argument("--lb", type=int, default=0)
    ap.add_argument("--ub", type=int, default=255)
    ap.add_argument("--woa_b", type=float, default=1.0)
    ap.add_argument("--share_interval", type=int, default=10)
    args = ap.parse_args()

    algos = _parse_algos(args.algos)
    if "PA5" not in algos:
        raise SystemExit("PA5 must be included in evaluate_main because it is the main method for the report.")

    seeds = _parse_seeds(args.seeds, int(args.seed_start), int(args.n_seeds))
    pairs = _load_pairs(args.images_root, args.gt_root or None, int(args.limit))
    if not pairs:
        raise SystemExit("Không tìm thấy ảnh phù hợp cho evaluate_main.")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    split_name = Path(args.images_root).name or "split"
    run_dir = os.path.join(args.out_root, f"{split_name}_k{args.k}_{len(seeds)}seeds_{ts}")
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
    unsupported_rows: List[Dict] = []

    for image_idx, (img_path, gt_path) in enumerate(pairs):
        gray = read_image_gray(img_path)
        gt_boundary = read_bsds_gt_boundary_mask(gt_path) if gt_path else None
        image_name = Path(img_path).name
        per_image: Dict[str, object] = {
            "image_index": image_idx,
            "image_name": image_name,
            "image_path": img_path,
            "gt_path": gt_path,
            "runs": [],
        }

        for seed in seeds:
            run_seed = _base_seed(int(seed), image_name)
            shared_init = _shared_init(run_seed, int(args.n_agents), int(args.k), int(args.lb), int(args.ub))

            def fitness_fn(x: np.ndarray) -> float:
                return -float(fuzzy_entropy_value(gray, repair_fn(x)))

            for algo in algos:
                try:
                    t0 = time.time()
                    best_x, best_f, history = _run_algorithm(
                        algo,
                        gray,
                        fitness_fn,
                        repair_fn,
                        shared_init,
                        run_seed,
                        args,
                    )
                    elapsed = float(time.time() - t0)
                except OtsuUnsupportedError as exc:
                    unsupported_rows.append(
                        {
                            "image_name": image_name,
                            "seed": run_seed,
                            "algo": algo,
                            "status": "unsupported",
                            "reason": str(exc),
                        }
                    )
                    continue

                best_x = np.asarray(repair_fn(best_x), dtype=float)
                seg = apply_thresholds(gray, best_x)
                fe = float(fuzzy_entropy_value(gray, best_x))
                dsc_value = boundary_dice_binary(gt_boundary, seg_to_boundary_mask(seg)) if gt_boundary is not None else None

                row = {
                    "image_name": image_name,
                    "seed": run_seed,
                    "algo": algo,
                    "thresholds": ",".join(map(str, np.asarray(best_x, dtype=int).tolist())),
                    "best_f": float(best_f),
                    "FE": fe,
                    "PSNR": float(compute_psnr(gray, seg, data_range=255.0)),
                    "SSIM": float(compute_ssim(gray, seg, data_range=255.0)),
                    "time": elapsed,
                    "convergence_iteration": int(convergence_iteration(history)),
                }
                row["boundary_dsc"] = float(dsc_value) if dsc_value is not None else None

                rows.append(row)
                per_image["runs"].append(row)

        with open(os.path.join(run_dir, "per_image", f"{image_idx:05d}_{image_name}.json"), "w", encoding="utf-8") as f:
            json.dump(per_image, f, ensure_ascii=False, indent=2)

    if not rows:
        raise SystemExit("Không có kết quả hợp lệ để tổng hợp.")

    summary_rows = _summary_rows(rows, algos)
    wilcoxon_rows = _wilcoxon_rows(rows, "PA5", algos)

    results_fields = [
        "image_name",
        "seed",
        "algo",
        "thresholds",
        "best_f",
        "FE",
        "boundary_dsc",
        "PSNR",
        "SSIM",
        "time",
        "convergence_iteration",
    ]
    with open(os.path.join(run_dir, "results.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results_fields)
        writer.writeheader()
        writer.writerows(rows)

    summary_fields = [
        "algo",
        "mean_FE",
        "sd_FE",
        "mean_boundary_dsc",
        "sd_boundary_dsc",
        "mean_PSNR",
        "sd_PSNR",
        "mean_SSIM",
        "sd_SSIM",
        "mean_time",
        "sd_time",
    ]
    with open(os.path.join(run_dir, "summary.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    with open(os.path.join(run_dir, "wilcoxon_pa5_vs_baselines.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "base_algo",
                "challenger_algo",
                "metric",
                "mean_base",
                "mean_challenger",
                "delta_mean",
                "n",
                "statistic",
                "pvalue",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(wilcoxon_rows)

    if unsupported_rows:
        with open(os.path.join(run_dir, "unsupported.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(unsupported_rows[0].keys()))
            writer.writeheader()
            writer.writerows(unsupported_rows)

    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                **vars(args),
                "algos": algos,
                "seeds": seeds,
                "main_flow": "evaluate_main.py",
                "main_method": "PA5",
                "dsc_metric_name": "boundary_dsc",
                "init_fairness": "same image + same base seed + same shared init population; only optimizer differs",
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(run_dir)


if __name__ == "__main__":
    main()

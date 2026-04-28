# src/runner/compare_algorithms_fe.py
"""
Quick train-time tuning runner.

This runner is intentionally limited to FE and time so it can be used for
fast screening before the main report flow in evaluate_main.py.
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

from src.metrics.statistics import standard_deviation
from src.objective.fuzzy_entropy_s import fuzzy_entropy_objective
from src.optim.bounds import repair_threshold_vector
from src.optim.gwo import GWO
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA
from src.optim.otsu import OtsuMulti, OtsuUnsupportedError
from src.optim.pso import PSO
from src.optim.woa import WOA
from src.segmentation.io import ensure_dir, list_image_files, read_image_gray


def _parse_algos(text: str) -> List[str]:
    parts = [p.strip().upper() for p in (text or "").split(",") if p.strip()]
    return parts or ["GWO", "WOA", "PSO", "OTSU", "HYBRID"]


def _base_seed(seed: int, image_name: str) -> int:
    acc = int(seed)
    for idx, ch in enumerate(str(image_name)):
        acc = (acc * 131 + (idx + 1) * ord(ch)) % (2**31 - 1)
    return int(acc)


def _make_optimizer(algo_u: str, args, seed: int) -> object:
    if algo_u == "GWO":
        return GWO(n_agents=int(args.n_agents), n_iters=int(args.n_iters), seed=seed)
    if algo_u == "WOA":
        return WOA(n_agents=int(args.n_agents), n_iters=int(args.n_iters), seed=seed, b=float(args.woa_b))
    if algo_u == "PSO":
        return PSO(n_agents=int(args.n_agents), n_iters=int(args.n_iters), seed=seed)
    if algo_u == "HYBRID":
        return HybridGWO_WOA(
            n_agents=int(args.n_agents),
            n_iters=int(args.n_iters),
            seed=seed,
            strategy=str(args.hybrid_strategy).upper(),
            woa_b=float(args.woa_b),
            share_interval=int(args.share_interval),
        )
    if algo_u == "OTSU":
        return OtsuMulti()
    raise ValueError("algo phÃ¡ÂºÂ£i lÃƒÂ : GWO | WOA | PSO | OTSU | HYBRID")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, required=True, help="Directory containing grayscale images")
    ap.add_argument("--out_root", type=str, default="outputs/compare_baselines_train")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--n_agents", type=int, default=30)
    ap.add_argument("--n_iters", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--lb", type=int, default=0)
    ap.add_argument("--ub", type=int, default=255)
    ap.add_argument("--woa_b", type=float, default=1.0)
    ap.add_argument("--share_interval", type=int, default=10)
    ap.add_argument("--hybrid_strategy", type=str, default="PA5")
    ap.add_argument("--algos", type=str, default="GWO,WOA,PSO,OTSU,HYBRID")
    args = ap.parse_args()

    algos = _parse_algos(args.algos)

    k = int(args.k)
    lb = int(args.lb)
    ub = int(args.ub)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(
        args.out_root,
        f"train_k{k}_iters{args.n_iters}_agents{args.n_agents}_seed{args.seed}_share{args.share_interval}_{ts}",
    )
    ensure_dir(run_dir)
    ensure_dir(os.path.join(run_dir, "per_image"))

    img_paths = list_image_files(args.root)
    if args.limit and args.limit > 0:
        img_paths = img_paths[: args.limit]
    if not img_paths:
        raise SystemExit(f"KhÃƒÂ´ng tÃƒÂ¬m thÃ¡ÂºÂ¥y Ã¡ÂºÂ£nh trong: {args.root}")

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

    for idx, p in enumerate(img_paths):
        gray = read_image_gray(p)
        image_name = Path(p).name
        image_key = f"{idx:05d}_{image_name}"
        image_seed = _base_seed(int(args.seed), image_name)
        shared_init = np.random.default_rng(image_seed).uniform(lb, ub, size=(int(args.n_agents), k))

        def fitness_fn(x: np.ndarray) -> float:
            return float(fuzzy_entropy_objective(gray, repair_fn(x)))

        per_image: Dict[str, Dict] = {
            "image_index": idx,
            "image_path": p,
            "k": k,
            "base_seed": image_seed,
            "results": {},
        }

        for algo_u in algos:
            t0 = time.time()
            label = algo_u if algo_u != "HYBRID" else f"HYBRID-{str(args.hybrid_strategy).upper()}"

            try:
                if algo_u == "OTSU":
                    opt = _make_optimizer(algo_u, args, image_seed)
                    best_x, best_f, history = opt.optimize_with_image(
                        gray,
                        k,
                        fitness_fn=fitness_fn,
                        repair_fn=repair_fn,
                    )
                    best_f = float(best_f) if best_f is not None else float(fitness_fn(best_x))
                else:
                    opt = _make_optimizer(algo_u, args, image_seed)
                    best_x, best_f, history = opt.optimize(
                        fitness_fn,
                        dim=k,
                        lb=np.full(k, lb, dtype=float),
                        ub=np.full(k, ub, dtype=float),
                        repair_fn=repair_fn,
                        init_pop=shared_init.copy(),
                    )
                    best_x = repair_fn(best_x)
                    best_f = float(best_f)
            except OtsuUnsupportedError as exc:
                per_image["results"][label] = {"status": "unsupported", "reason": str(exc)}
                continue

            elapsed = float(time.time() - t0)
            fe_best = float(-best_f)

            row = {
                "image_name": image_name,
                "algo": label,
                "seed": image_seed,
                "fe_best": fe_best,
                "time_sec": elapsed,
            }
            rows.append(row)

            per_image["results"][label] = {
                "status": "ok",
                "fe_best": fe_best,
                "best_f": float(best_f),
                "thresholds": np.asarray(best_x, dtype=float).tolist(),
                "time_sec": elapsed,
                "n_history": int(len(history)) if isinstance(history, list) else 0,
            }

        with open(os.path.join(run_dir, "per_image", f"{image_key}.json"), "w", encoding="utf-8") as f:
            json.dump(per_image, f, ensure_ascii=False, indent=2)

    if not rows:
        raise SystemExit("KhÃƒÂ´ng cÃƒÂ³ kÃ¡ÂºÂ¿t quÃ¡ÂºÂ£ hÃ¡Â»Â£p lÃ¡Â»â€¡ Ã„â€˜Ã¡Â»Æ’ ghi ra file.")

    rows_sorted = sorted(rows, key=lambda r: float(r["fe_best"]), reverse=True)
    results_csv = os.path.join(run_dir, "results_sorted.csv")
    with open(results_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["image_name", "algo", "seed", "fe_best", "time_sec"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_sorted)

    summary_rows: List[Dict] = []
    for algo in sorted(set(r["algo"] for r in rows)):
        fe = np.asarray([r["fe_best"] for r in rows if r["algo"] == algo], dtype=float)
        times = np.asarray([r["time_sec"] for r in rows if r["algo"] == algo], dtype=float)
        summary_rows.append(
            {
                "algo": algo,
                "n_images": int(fe.size),
                "mean_fe": float(fe.mean()) if fe.size else 0.0,
                "sd_fe": standard_deviation(fe),
                "best_fe": float(fe.max()) if fe.size else 0.0,
                "worst_fe": float(fe.min()) if fe.size else 0.0,
                "mean_time": float(times.mean()) if times.size else 0.0,
                "sd_time": standard_deviation(times),
            }
        )

    summary_rows = sorted(summary_rows, key=lambda r: float(r["mean_fe"]), reverse=True)
    summary_csv = os.path.join(run_dir, "summary_sorted.csv")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["algo", "n_images", "mean_fe", "sd_fe", "best_fe", "worst_fe", "mean_time", "sd_time"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    config = {
        "root": args.root,
        "n_images": len(img_paths),
        "k": k,
        "n_agents": int(args.n_agents),
        "n_iters": int(args.n_iters),
        "seed": int(args.seed),
        "woa_b": float(args.woa_b),
        "hybrid_strategy": str(args.hybrid_strategy).upper(),
        "share_interval": int(args.share_interval),
        "algos": algos,
        "note": "Quick tuning runner. Only FE and time are exported here.",
    }
    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(run_dir)


if __name__ == "__main__":
    main()

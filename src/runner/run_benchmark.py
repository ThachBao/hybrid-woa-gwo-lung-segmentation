# src/runner/run_benchmark.py
from __future__ import annotations

import argparse
import csv
import os
import numpy as np

from src.benchmarks.benchmark import BENCHMARK_NAMES, benchmark_functions, set_bounds
from src.optim.gwo import GWO
from src.optim.woa import WOA
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA


def make_optimizer(algo: str, n_agents: int, n_iters: int, seed: int | None, strategy: str, woa_b: float, share_interval: int):
    algo_u = algo.upper()
    if algo_u == "GWO":
        return GWO(n_agents=n_agents, n_iters=n_iters, seed=seed)
    if algo_u == "WOA":
        return WOA(n_agents=n_agents, n_iters=n_iters, seed=seed, b=woa_b)
    if algo_u in ("HYBRID", "GWO_WOA", "GWO-WOA"):
        return HybridGWO_WOA(
            n_agents=n_agents,
            n_iters=n_iters,
            seed=seed,
            strategy=strategy,
            woa_b=woa_b,
            share_interval=share_interval,
        )
    raise ValueError("algo pháº£i lÃ : GWO | WOA | HYBRID")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", type=str, default="GWO")
    ap.add_argument("--strategy", type=str, default="PA1")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--n_agents", type=int, default=50)
    ap.add_argument("--n_iters", type=int, default=1000)
    ap.add_argument("--dim", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--woa_b", type=float, default=1.0)
    ap.add_argument("--share_interval", type=int, default=10)
    ap.add_argument("--out", type=str, default="outputs/runs/benchmark_results.csv")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    rows = []
    for fun_idx, fun_name in enumerate(BENCHMARK_NAMES):
        dim = 2 if fun_idx == 17 else args.dim
        lb, ub = set_bounds(fun_idx, dim)

        best_list = []
        for r in range(args.runs):
            seed = None if args.seed is None else args.seed + 1000 * fun_idx + r
            opt = make_optimizer(args.algo, args.n_agents, args.n_iters, seed, args.strategy.upper(), args.woa_b, args.share_interval)

            def fitness_fn(x: np.ndarray) -> float:
                return float(benchmark_functions(np.asarray(x, dtype=float), fun_idx))

            best_x, best_f, history = opt.optimize(
                fitness_fn,
                dim=dim,
                lb=lb,
                ub=ub,
                repair_fn=None,
                init_pop=None,
            )
            best_list.append(float(best_f))

        arr = np.asarray(best_list, dtype=float)
        rows.append(
            {
                "fun_index": fun_idx,
                "fun_name": fun_name,
                "dim": dim,
                "algo": args.algo.upper(),
                "strategy": args.strategy.upper() if args.algo.upper() == "HYBRID" else "",
                "runs": args.runs,
                "n_agents": args.n_agents,
                "n_iters": args.n_iters,
                "best_mean": float(arr.mean()),
                "best_std": float(arr.std(ddof=1)) if args.runs > 1 else 0.0,
                "best_min": float(arr.min()),
                "best_max": float(arr.max()),
            }
        )

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(args.out)


if __name__ == "__main__":
    main()

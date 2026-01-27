# src/runner/run_dataset.py
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from datetime import datetime
import uuid
from typing import Any, Dict

import numpy as np
import yaml

from src.objective.fuzzy_entropy import fuzzy_entropy_objective
from src.optim.bounds import repair_threshold_vector
from src.optim.gwo import GWO
from src.optim.woa import WOA
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA
from src.segmentation.io import list_image_files, read_image_gray, save_image_gray, ensure_dir
from src.segmentation.apply_thresholds import apply_thresholds


def _read_yaml(path: str | os.PathLike) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _make_run_dir(base: str = "outputs/runs", tag: str = "dataset") -> str:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    rid = uuid.uuid4().hex[:8]
    run_dir = os.path.join(base, f"{ts}_{tag}_{rid}")
    ensure_dir(run_dir)
    return run_dir


def _make_optimizer(algo: str, params: Dict[str, Any]):
    algo_u = str(algo).upper()
    n_agents = int(params.get("n_agents", 30))
    n_iters = int(params.get("n_iters", 80))
    seed = params.get("seed", None)
    seed = None if seed in ("", "null", "None") else (int(seed) if seed is not None else None)

    if algo_u == "GWO":
        return GWO(n_agents=n_agents, n_iters=n_iters, seed=seed)
    if algo_u == "WOA":
        woa_b = float(params.get("woa_b", 1.0))
        return WOA(n_agents=n_agents, n_iters=n_iters, seed=seed, b=woa_b)
    if algo_u in ("HYBRID", "GWO_WOA", "GWO-WOA"):
        strategy = str(params.get("strategy", "PA1")).upper()
        woa_b = float(params.get("woa_b", 1.0))
        share_interval = int(params.get("share_interval", 1))
        return HybridGWO_WOA(
            n_agents=n_agents,
            n_iters=n_iters,
            seed=seed,
            strategy=strategy,
            woa_b=woa_b,
            share_interval=share_interval,
        )
    raise ValueError("algo phải là: GWO | WOA | HYBRID")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, required=True)  # thư mục chứa ảnh (có thể là BSDS500 root hoặc thư mục con)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--save_images", action="store_true")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--algo", type=str, default="GWO")
    ap.add_argument("--strategy", type=str, default="PA1")
    ap.add_argument("--n_agents", type=int, default=30)
    ap.add_argument("--n_iters", type=int, default=80)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lb", type=int, default=0)
    ap.add_argument("--ub", type=int, default=255)
    ap.add_argument("--out_dir", type=str, default="")
    ap.add_argument("--config_task", type=str, default="configs/task_thresholding.yaml")
    ap.add_argument("--config_gwo", type=str, default="configs/gwo.yaml")
    ap.add_argument("--config_woa", type=str, default="configs/woa.yaml")
    ap.add_argument("--config_hybrid", type=str, default="configs/hybrid.yaml")
    args = ap.parse_args()

    cfg_task = _read_yaml(args.config_task)
    cfg_gwo = _read_yaml(args.config_gwo)
    cfg_woa = _read_yaml(args.config_woa)
    cfg_hybrid = _read_yaml(args.config_hybrid)

    merged: Dict[str, Any] = {}
    for d in (cfg_task, cfg_gwo, cfg_woa, cfg_hybrid):
        merged.update(d)

    merged["k"] = int(args.k)
    merged["algo"] = str(args.algo).upper()
    merged["strategy"] = str(args.strategy).upper()
    merged["n_agents"] = int(args.n_agents)
    merged["n_iters"] = int(args.n_iters)
    merged["seed"] = int(args.seed)
    merged["lb"] = int(args.lb)
    merged["ub"] = int(args.ub)

    run_dir = args.out_dir.strip() or _make_run_dir(tag=f"{merged['algo']}_k{merged['k']}")
    ensure_dir(run_dir)

    img_paths = list_image_files(args.root)
    if args.limit and args.limit > 0:
        img_paths = img_paths[: args.limit]

    k = int(merged["k"])
    lb = int(merged["lb"])
    ub = int(merged["ub"])

    def repair_fn(x: np.ndarray) -> np.ndarray:
        return repair_threshold_vector(x, k=k, lb=lb, ub=ub, integer=True, ensure_unique=True)

    rows = []
    for idx, p in enumerate(img_paths):
        gray = read_image_gray(p)

        def fitness_fn(x: np.ndarray) -> float:
            return float(fuzzy_entropy_objective(gray, repair_fn(x)))

        opt = _make_optimizer(merged["algo"], merged)

        best_x, best_f, history = opt.optimize(
            fitness_fn,
            dim=k,
            lb=np.full(k, lb, dtype=float),
            ub=np.full(k, ub, dtype=float),
            repair_fn=repair_fn,
            init_pop=None,
        )

        best_x = repair_fn(best_x)

        out_seg_path = ""
        if args.save_images:
            rel = Path(p).name
            out_seg_path = os.path.join(run_dir, "segmented", f"{idx:05d}_{rel}")
            ensure_dir(Path(out_seg_path).parent)
            seg = apply_thresholds(gray, best_x)
            save_image_gray(out_seg_path, seg)

        rows.append(
            {
                "index": idx,
                "image_path": p,
                "best_f": float(best_f),
                "thresholds": ",".join(map(str, best_x.tolist())),
                "segmented_path": out_seg_path,
            }
        )

    with open(os.path.join(run_dir, "summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["index"])
        if rows:
            w.writeheader()
            w.writerows(rows)

    with open(os.path.join(run_dir, "config_used.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(merged, f, allow_unicode=True, sort_keys=False)

    print(run_dir)


if __name__ == "__main__":
    main()

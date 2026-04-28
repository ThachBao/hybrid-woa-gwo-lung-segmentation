from __future__ import annotations

import argparse
import sys

from src.runner.compare_pa5_pa6 import main as compare_main


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, required=True)
    ap.add_argument("--gt_root", type=str, default="")
    ap.add_argument("--out_root", type=str, default="outputs/compareGWO-WOA")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--n_agents", type=int, default=30)
    ap.add_argument("--n_iters", type=int, default=80)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--lb", type=int, default=0)
    ap.add_argument("--ub", type=int, default=255)
    ap.add_argument("--woa_b", type=float, default=1.0)
    ap.add_argument("--share_interval", type=int, default=10)
    ap.add_argument("--strategies", type=str, default="PA1,PA2,PA3,PA4,PA5,PA6")
    args = ap.parse_args()

    sys.argv = [
        "compare_pa5_pa6",
        "--images_root", args.root,
        "--gt_root", args.gt_root,
        "--out_root", args.out_root,
        "--limit", str(args.limit),
        "--k", str(args.k),
        "--n_agents", str(args.n_agents),
        "--n_iters", str(args.n_iters),
        "--seed", str(args.seed),
        "--lb", str(args.lb),
        "--ub", str(args.ub),
        "--woa_b", str(args.woa_b),
        "--share_interval", str(args.share_interval),
        "--strategies", args.strategies,
    ]
    compare_main()


if __name__ == "__main__":
    main()

# ui/app.py
from __future__ import annotations

import base64
from io import BytesIO
import json
import logging
import os
import shutil
import yaml

import numpy as np
from flask import Flask, jsonify, render_template, request

from src.objective.fuzzy_entropy import fuzzy_entropy_objective
from src.objective.thresholding_with_penalties import (
    create_fe_objective_with_penalties,
    get_recommended_weights,
    get_recommended_params,
)
from src.optim.bounds import repair_threshold_vector
from src.optim.gwo import GWO
from src.optim.woa import WOA
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA
from src.optim.pso import PSO
from src.optim.otsu import OtsuMulti
from src.segmentation.io import decode_image_gray, read_image_gray
from src.segmentation.apply_thresholds import apply_thresholds
from src.metrics.quality import compute_psnr, compute_ssim, dice_binary, to_bool_mask
from src.data.bsds500_gt import (
    build_pairs,
    read_bsds_gt_boundary_mask,
    seg_to_boundary_mask,
    dice_binary as dice_boundary,
)

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None

# benchmark (phải tồn tại trong src/benchmarks)
try:
    from src.benchmarks.benchmark import BENCHMARK_NAMES, benchmark_functions, set_bounds  # type: ignore
except Exception:  # pragma: no cover
    BENCHMARK_NAMES = None
    benchmark_functions = None
    set_bounds = None


app = Flask(__name__, template_folder="templates", static_folder="static")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

K_FIXED = 10  # cố định k = 10

# BDS500 dataset paths
BDS500_ROOT = "dataset/BDS500"
BDS500_IMAGES_ROOT = f"{BDS500_ROOT}/images"
BDS500_GT_ROOT = f"{BDS500_ROOT}/ground_truth"


def _img_to_data_url_gray(img_u8: np.ndarray) -> str:
    if Image is None:
        raise RuntimeError("Thiếu Pillow (PIL) để encode ảnh base64.")
    im = Image.fromarray(np.asarray(img_u8, dtype=np.uint8), mode="L")
    buf = BytesIO()
    im.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _make_optimizer(
    algo: str,
    *,
    n_agents: int,
    n_iters: int,
    seed: int | None,
    strategy: str,
    woa_b: float,
    share_interval: int,
):
    algo_u = str(algo).upper()
    if algo_u == "GWO":
        return GWO(n_agents=n_agents, n_iters=n_iters, seed=seed)
    if algo_u == "WOA":
        return WOA(n_agents=n_agents, n_iters=n_iters, seed=seed, b=woa_b)
    if algo_u == "PSO":
        return PSO(n_agents=n_agents, n_iters=n_iters, seed=seed)
    if algo_u == "OTSU":
        return OtsuMulti(n_agents=n_agents, n_iters=n_iters, seed=seed)
    if algo_u == "HYBRID":
        return HybridGWO_WOA(
            n_agents=n_agents,
            n_iters=n_iters,
            seed=seed,
            strategy=str(strategy).upper(),
            woa_b=woa_b,
            share_interval=share_interval,
        )
    raise ValueError("algo phải là: GWO | WOA | PSO | OTSU | HYBRID")


def _history_to_best_series(history) -> list[float]:
    series: list[float] = []
    if isinstance(history, list):
        for it in history:
            if isinstance(it, dict) and "best_f" in it:
                series.append(float(it["best_f"]))
    return series


def _log_optimization_progress(algo_name: str, history: list, n_agents: int, n_iters: int):
    """Log chi tiết quá trình tối ưu"""
    if not history:
        return
    
    logger.info(f"\n{'='*60}")
    logger.info(f"CHI TIẾT TỐI ƯU: {algo_name}")
    logger.info(f"{'='*60}")
    logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}")
    logger.info(f"Tổng số vòng lặp thực tế: {len(history)}")
    
    # Log một số vòng lặp quan trọng
    important_iters = []
    
    # Vòng đầu
    if len(history) > 0:
        important_iters.append(0)
    
    # Vòng 25%, 50%, 75%
    for pct in [0.25, 0.5, 0.75]:
        idx = int(len(history) * pct)
        if 0 < idx < len(history):
            important_iters.append(idx)
    
    # Vòng cuối
    if len(history) > 1:
        important_iters.append(len(history) - 1)
    
    logger.info(f"\nCác vòng lặp quan trọng:")
    for idx in important_iters:
        if idx < len(history):
            it = history[idx]
            best_f = it.get("best_f", 0)
            entropy = -best_f
            mean_f = it.get("mean_f", 0)
            logger.info(f"  Iter {idx:3d}/{len(history)-1}: best_f={best_f:.6f} (Entropy={entropy:.6f}), mean_f={mean_f:.6f}")
    
    # Thống kê cải thiện
    if len(history) >= 2:
        first_f = history[0].get("best_f", 0)
        last_f = history[-1].get("best_f", 0)
        improvement = first_f - last_f
        improvement_pct = (improvement / abs(first_f) * 100) if first_f != 0 else 0
        
        logger.info(f"\nCải thiện:")
        logger.info(f"  Đầu: best_f={first_f:.6f} (Entropy={-first_f:.6f})")
        logger.info(f"  Cuối: best_f={last_f:.6f} (Entropy={-last_f:.6f})")
        logger.info(f"  Cải thiện: {improvement:.6f} ({improvement_pct:+.2f}%)")
    
    logger.info(f"{'='*60}\n")


def _save_run_results(
    run_dir: str,
    gray: np.ndarray,
    results: dict,
    params: dict,
    image_name: str = "uploaded",
) -> None:
    """
    Lưu kết quả phân đoạn vào thư mục outputs/runs
    
    Args:
        run_dir: Đường dẫn thư mục lưu kết quả
        gray: Ảnh grayscale gốc
        results: Dict chứa kết quả các thuật toán
        params: Dict chứa tham số
        image_name: Tên ảnh
    """
    import json
    import yaml
    from datetime import datetime
    
    os.makedirs(run_dir, exist_ok=True)
    
    # 1. Lưu ảnh gốc
    if Image is not None:
        gray_img = Image.fromarray(gray, mode="L")
        gray_img.save(os.path.join(run_dir, "gray.png"))
    
    # 2. Lưu config
    config = {
        "image_name": image_name,
        "timestamp": datetime.now().isoformat(),
        "k": params.get("k", 10),
        "n_agents": params.get("n_agents", 30),
        "n_iters": params.get("n_iters", 80),
        "seed": params.get("seed"),
        "woa_b": params.get("woa_b", 1.0),
        "share_interval": params.get("share_interval", 1),
        "use_penalties": params.get("use_penalties", False),
        "penalty_mode": params.get("penalty_mode", "balanced"),
        "algorithms": list(results.keys()),
    }
    
    with open(os.path.join(run_dir, "config.yaml"), "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    # 3. Lưu kết quả từng thuật toán
    for algo_name, result in results.items():
        algo_dir = os.path.join(run_dir, algo_name)
        os.makedirs(algo_dir, exist_ok=True)
        
        # Lưu best.json
        best_data = {
            "algorithm": algo_name,
            "thresholds": result.get("thresholds", []),
            "best_f": result.get("best_f", 0.0),
            "entropy": -result.get("best_f", 0.0),
            "time": result.get("time", 0.0),
            "metrics": result.get("metrics", {}),
        }
        
        with open(os.path.join(algo_dir, "best.json"), "w") as f:
            json.dump(best_data, f, indent=2)
        
        # Lưu history.jsonl
        if "best_series" in result:
            with open(os.path.join(algo_dir, "history.jsonl"), "w") as f:
                for i, best_f in enumerate(result["best_series"]):
                    f.write(json.dumps({"iter": i, "best_f": best_f}) + "\n")
        
        # Lưu ảnh phân đoạn
        if "seg_data_url" in result and Image is not None:
            # Decode base64 image
            data_url = result["seg_data_url"]
            if data_url.startswith("data:image/png;base64,"):
                b64_data = data_url.split(",")[1]
                img_data = base64.b64decode(b64_data)
                seg_img = Image.open(BytesIO(img_data))
                seg_img.save(os.path.join(algo_dir, "segmented.png"))
    
    # 4. Lưu summary
    summary = {
        "image_name": image_name,
        "timestamp": datetime.now().isoformat(),
        "total_time": params.get("total_time", 0.0),
        "best_overall_algo": params.get("best_overall_algo", ""),
        "best_overall_f": params.get("best_overall_f", 0.0),
        "best_overall_entropy": -params.get("best_overall_f", 0.0),
        "results": {
            algo: {
                "entropy": -res.get("best_f", 0.0),
                "time": res.get("time", 0.0),
                "metrics": res.get("metrics", {}),
            }
            for algo, res in results.items()
        }
    }
    
    with open(os.path.join(run_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"✓ Đã lưu kết quả vào: {run_dir}")


def _create_run_dir(prefix: str = "ui") -> str:
    """
    Tạo thư mục cho run mới
    
    Args:
        prefix: Tiền tố cho tên thư mục (ui, bds500, etc.)
    
    Returns:
        Đường dẫn thư mục
    """
    from datetime import datetime
    import hashlib
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]
    run_name = f"{timestamp}_{prefix}_{random_suffix}"
    run_dir = os.path.join("outputs", "runs", run_name)
    
    return run_dir


def _run_all_benchmarks(n_agents, n_iters, seed, woa_b, share_interval, 
                        run_gwo, run_woa, run_hybrid, hybrid_strategies):
    """Chạy TẤT CẢ 18 hàm benchmark với dim cố định = 30"""
    if BENCHMARK_NAMES is None or benchmark_functions is None or set_bounds is None:
        logger.error("Không tìm thấy module benchmark")
        return {"error": "missing benchmark functions"}
    
    all_results = []
    dim = 30  # dim CỐ ĐỊNH = 30, không phụ thuộc vào n_agents
    
    logger.info(f"Sẽ chạy {len(BENCHMARK_NAMES)} hàm benchmark với dim={dim}, n_agents={n_agents}")
    
    # Chạy tất cả 18 hàm
    for fun_idx in range(len(BENCHMARK_NAMES)):
        fun_1 = fun_idx + 1
        fun_name = BENCHMARK_NAMES[fun_idx]
        
        logger.info("-" * 60)
        logger.info(f"BENCHMARK F{fun_1}: {fun_name}")
        logger.info("-" * 60)
        
        try:
            lb, ub = set_bounds(fun_idx, dim)
            logger.info(f"Bounds: lb={lb[0] if isinstance(lb, np.ndarray) else lb}, ub={ub[0] if isinstance(ub, np.ndarray) else ub}")
            
            def fitness_fn(x: np.ndarray) -> float:
                return float(benchmark_functions(np.asarray(x, dtype=float), fun_idx))
            
            results = {}
            
            def seed_for(offset: int) -> int | None:
                if seed is None:
                    return None
                return seed + offset
            
            if run_gwo:
                logger.info(f"  → Chạy GWO cho F{fun_1}...")
                opt = _make_optimizer("GWO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(10), 
                                    strategy="PA1", woa_b=woa_b, share_interval=share_interval)
                _, best_f, history = opt.optimize(fitness_fn, dim=dim, lb=lb, ub=ub, repair_fn=None, init_pop=None)
                results["GWO"] = {"best_f": float(best_f), "series": _history_to_best_series(history)}
                logger.info(f"  → GWO hoàn thành: best_f={best_f:.6e}")
            
            if run_woa:
                logger.info(f"  → Chạy WOA cho F{fun_1}...")
                opt = _make_optimizer("WOA", n_agents=n_agents, n_iters=n_iters, seed=seed_for(20), 
                                    strategy="PA1", woa_b=woa_b, share_interval=share_interval)
                _, best_f, history = opt.optimize(fitness_fn, dim=dim, lb=lb, ub=ub, repair_fn=None, init_pop=None)
                results["WOA"] = {"best_f": float(best_f), "series": _history_to_best_series(history)}
                logger.info(f"  → WOA hoàn thành: best_f={best_f:.6e}")
            
            if run_hybrid:
                for strategy in hybrid_strategies:
                    strategy = strategy.strip().upper()
                    if not strategy:
                        continue
                    logger.info(f"  → Chạy HYBRID-{strategy} cho F{fun_1}...")
                    opt = _make_optimizer("HYBRID", n_agents=n_agents, n_iters=n_iters, 
                                        seed=seed_for(30 + hash(strategy) % 100),
                                        strategy=strategy, woa_b=woa_b, share_interval=share_interval)
                    _, best_f, history = opt.optimize(fitness_fn, dim=dim, lb=lb, ub=ub, repair_fn=None, init_pop=None)
                    results[f"HYBRID-{strategy}"] = {"best_f": float(best_f), "series": _history_to_best_series(history)}
                    logger.info(f"  → HYBRID-{strategy} hoàn thành: best_f={best_f:.6e}")
            
            all_results.append({
                "fun": fun_1,
                "fun_name": fun_name,
                "dim": dim,
                "results": results,
            })
            logger.info(f"✓ F{fun_1} hoàn thành")
            
        except Exception as e:
            logger.error(f"✗ Lỗi khi chạy F{fun_1}: {e}", exc_info=True)
            all_results.append({
                "fun": fun_1,
                "fun_name": fun_name,
                "dim": dim,
                "error": str(e),
            })
    
    logger.info(f"Hoàn thành {len(all_results)}/{len(BENCHMARK_NAMES)} hàm benchmark")
    return all_results


def _run_benchmark_internal(fun_1, dim, n_agents, n_iters, seed, woa_b, share_interval, 
                            run_gwo, run_woa, run_hybrid, hybrid_strategies):
    """Helper function để chạy benchmark cho 1 hàm cụ thể"""
    if BENCHMARK_NAMES is None or benchmark_functions is None or set_bounds is None:
        return {"error": "missing benchmark functions"}
    
    fun_idx = fun_1 - 1
    if fun_idx < 0 or fun_idx >= len(BENCHMARK_NAMES):
        return {"error": "fun phải trong [1..18]"}
    
    lb, ub = set_bounds(fun_idx, dim)
    
    def fitness_fn(x: np.ndarray) -> float:
        return float(benchmark_functions(np.asarray(x, dtype=float), fun_idx))
    
    results = {}
    
    def seed_for(offset: int) -> int | None:
        if seed is None:
            return None
        return seed + offset
    
    try:
        if run_gwo:
            opt = _make_optimizer("GWO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(10), 
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            _, best_f, history = opt.optimize(fitness_fn, dim=dim, lb=lb, ub=ub, repair_fn=None, init_pop=None)
            results["GWO"] = {"best_f": float(best_f), "series": _history_to_best_series(history)}
        
        if run_woa:
            opt = _make_optimizer("WOA", n_agents=n_agents, n_iters=n_iters, seed=seed_for(20), 
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            _, best_f, history = opt.optimize(fitness_fn, dim=dim, lb=lb, ub=ub, repair_fn=None, init_pop=None)
            results["WOA"] = {"best_f": float(best_f), "series": _history_to_best_series(history)}
        
        if run_hybrid:
            for strategy in hybrid_strategies:
                strategy = strategy.strip().upper()
                if not strategy:
                    continue
                opt = _make_optimizer("HYBRID", n_agents=n_agents, n_iters=n_iters, 
                                    seed=seed_for(30 + hash(strategy) % 100),
                                    strategy=strategy, woa_b=woa_b, share_interval=share_interval)
                _, best_f, history = opt.optimize(fitness_fn, dim=dim, lb=lb, ub=ub, repair_fn=None, init_pop=None)
                results[f"HYBRID-{strategy}"] = {"best_f": float(best_f), "series": _history_to_best_series(history)}
        
        return {
            "fun": fun_1,
            "fun_name": BENCHMARK_NAMES[fun_idx],
            "dim": dim,
            "results": results,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
def index():
    f_names = []
    if BENCHMARK_NAMES is not None:
        # hiển thị F1..F18
        f_names = [{"id": i + 1, "name": BENCHMARK_NAMES[i]} for i in range(len(BENCHMARK_NAMES))]
    return render_template("index.html", k_fixed=K_FIXED, benchmark_list=f_names)


@app.get("/api/bds500/list")
def api_bds500_list():
    """Lấy danh sách ảnh từ BDS500 dataset theo split"""
    import os
    import random
    
    split = request.args.get("split", "test")  # train, val, test
    limit = int(request.args.get("limit", "50"))  # giới hạn số ảnh trả về
    random_select = request.args.get("random", "false") == "true"
    
    try:
        images_dir = os.path.join(BDS500_IMAGES_ROOT, split)
        gt_dir = os.path.join(BDS500_GT_ROOT, split)
        
        if not os.path.exists(images_dir):
            return jsonify({"error": f"Không tìm thấy thư mục: {images_dir}"}), 404
        
        # Lấy danh sách ảnh có ground truth
        pairs = build_pairs(images_dir, gt_dir)
        
        if random_select and len(pairs) > limit:
            pairs = random.sample(pairs, limit)
        elif len(pairs) > limit:
            pairs = pairs[:limit]
        
        # Trả về danh sách với thông tin cơ bản
        result = []
        for img_path, gt_path in pairs:
            from pathlib import Path
            stem = Path(img_path).stem
            result.append({
                "id": stem,
                "name": Path(img_path).name,
                "path": img_path,
                "gt_path": gt_path,
                "has_gt": True,
            })
        
        return jsonify({
            "split": split,
            "total": len(result),
            "images": result,
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách BDS500: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.post("/api/segment_bds500")
def api_segment_bds500():
    """Phân đoạn ảnh từ BDS500 dataset và tính DICE score"""
    import time
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info("BẮT ĐẦU XỬ LÝ PHÂN ĐOẠN ẢNH TỪ BDS500")
    logger.info("=" * 80)
    
    try:
        # Lấy thông tin ảnh từ request
        image_path = request.form.get("image_path", "").strip()
        gt_path = request.form.get("gt_path", "").strip()
        
        if not image_path:
            return jsonify({"error": "missing image_path"}), 400
        
        logger.info(f"Image path: {image_path}")
        logger.info(f"GT path: {gt_path}")
        
        # Đọc ảnh
        gray = read_image_gray(image_path)
        logger.info(f"Ảnh đã được đọc: shape={gray.shape}")
        
        # Lấy các tham số khác giống như api_segment
        n_agents = int(request.form.get("n_agents", "30"))
        n_iters = int(request.form.get("n_iters", "80"))
        seed_raw = request.form.get("seed", "").strip()
        seed = None if seed_raw == "" else int(seed_raw)
        woa_b = float(request.form.get("woa_b", "1.0"))
        share_interval = int(request.form.get("share_interval", "1"))
        
        run_gwo = request.form.get("run_gwo", "0") == "1"
        run_woa = request.form.get("run_woa", "0") == "1"
        run_pso = request.form.get("run_pso", "0") == "1"
        run_otsu = request.form.get("run_otsu", "0") == "1"
        run_hybrid = request.form.get("run_hybrid", "0") == "1"
        hybrid_strategies = request.form.get("hybrid_strategies", "PA1").split(",")
        
        gt_thr = float(request.form.get("gt_thr", "0.5"))
        gt_fuse = request.form.get("gt_fuse", "max")
        
        logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed}")
        logger.info(f"Thuật toán: GWO={run_gwo}, WOA={run_woa}, PSO={run_pso}, OTSU={run_otsu}, HYBRID={run_hybrid}")
        logger.info(f"Hybrid strategies: {hybrid_strategies}")
        logger.info(f"GT params: thr={gt_thr}, fuse={gt_fuse}")
        
        if not (run_gwo or run_woa or run_pso or run_otsu or run_hybrid):
            return jsonify({"error": "Phải chọn ít nhất 1 thuật toán"}), 400
        
        # Đọc ground truth boundary mask nếu có
        gt_boundary_mask = None
        if gt_path and os.path.exists(gt_path):
            try:
                gt_boundary_mask = read_bsds_gt_boundary_mask(gt_path, thr=gt_thr, fuse=gt_fuse)
                logger.info(f"Ground truth boundary mask đã được đọc: shape={gt_boundary_mask.shape}")
            except Exception as e:
                logger.warning(f"Không thể đọc ground truth: {e}")
        
        # Phân đoạn ảnh (giống như api_segment)
        k = K_FIXED
        lb, ub = 0, 255
        
        # Parse penalty settings
        use_penalties = request.form.get("use_penalties", "0") == "1"
        penalty_mode = request.form.get("penalty_mode", "balanced")
        
        logger.info(f"Penalty settings: use_penalties={use_penalties}, mode={penalty_mode}")

        def repair_fn(x: np.ndarray) -> np.ndarray:
            return repair_threshold_vector(
                x, k=k, lb=lb, ub=ub, 
                integer=True, 
                ensure_unique=True,
                avoid_endpoints=use_penalties  # Tránh 0/255 khi dùng penalties
            )

        # Create fitness function with or without penalties
        if use_penalties:
            weights = get_recommended_weights(penalty_mode)
            params = get_recommended_params(k=k)
            logger.info(f"Using penalties: w_gap={weights.w_gap}, w_size={weights.w_size}, min_gap={params.min_gap}, p_min={params.p_min}")
            fitness_fn = create_fe_objective_with_penalties(gray, repair_fn, weights, params, lb, ub)
        else:
            def fitness_fn(x: np.ndarray) -> float:
                return float(fuzzy_entropy_objective(gray, repair_fn(x)))

        results = {}
        best_overall = None
        best_overall_f = float('inf')
        best_overall_algo = ""

        def seed_for(offset: int) -> int | None:
            if seed is None:
                return None
            return seed + offset

        # Tạo quần thể khởi tạo chung cho tất cả thuật toán (để so sánh công bằng)
        shared_init_pop = None
        if seed is not None:
            rng_init = np.random.default_rng(seed)
            shared_init_pop = rng_init.uniform(lb, ub, size=(n_agents, k))
            logger.info(f"Đã tạo quần thể khởi tạo chung với seed={seed}")

        # Chạy các thuật toán
        if run_gwo:
            logger.info("-" * 60)
            logger.info("CHẠY THUẬT TOÁN GWO")
            logger.info("-" * 60)
            logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed_for(10)}")
            algo_start = time.time()
            opt = _make_optimizer("GWO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(10), 
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=shared_init_pop
            )
            algo_time = time.time() - algo_start
            
            # Log chi tiết quá trình tối ưu
            _log_optimization_progress("GWO", history, n_agents, n_iters)
            
            best_x = repair_fn(best_x)
            seg = apply_thresholds(gray, best_x)
            
            # Tính metrics
            metrics = {}
            try:
                metrics["psnr"] = compute_psnr(gray, seg, data_range=255.0)
                metrics["ssim"] = compute_ssim(gray, seg, data_range=255.0)
                
                # Tính DICE nếu có ground truth
                if gt_boundary_mask is not None:
                    pred_boundary = seg_to_boundary_mask(seg)
                    metrics["dice"] = dice_boundary(gt_boundary_mask, pred_boundary)
                    logger.info(f"GWO metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}, DICE={metrics['dice']:.4f}")
                else:
                    logger.info(f"GWO metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}")
            except Exception as e:
                logger.warning(f"Không thể tính metrics cho GWO: {e}")
            
            results["GWO"] = {
                "thresholds": [int(v) for v in np.asarray(best_x).ravel().tolist()],
                "best_f": float(best_f),
                "time": algo_time,
                "seg_data_url": _img_to_data_url_gray(seg),
                "best_series": _history_to_best_series(history),
                "metrics": metrics,
            }
            logger.info(f"GWO hoàn thành: best_f={best_f:.6f} (Entropy={-best_f:.6f}), time={algo_time:.2f}s")
            if best_f < best_overall_f:
                best_overall_f = best_f
                best_overall = best_x
                best_overall_algo = "GWO"

        if run_woa:
            logger.info("-" * 60)
            logger.info("CHẠY THUẬT TOÁN WOA")
            logger.info("-" * 60)
            logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed_for(20)}, woa_b={woa_b}")
            algo_start = time.time()
            opt = _make_optimizer("WOA", n_agents=n_agents, n_iters=n_iters, seed=seed_for(20),
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=shared_init_pop
            )
            algo_time = time.time() - algo_start
            
            # Log chi tiết quá trình tối ưu
            _log_optimization_progress("WOA", history, n_agents, n_iters)
            
            best_x = repair_fn(best_x)
            seg = apply_thresholds(gray, best_x)
            
            metrics = {}
            try:
                metrics["psnr"] = compute_psnr(gray, seg, data_range=255.0)
                metrics["ssim"] = compute_ssim(gray, seg, data_range=255.0)
                
                if gt_boundary_mask is not None:
                    pred_boundary = seg_to_boundary_mask(seg)
                    metrics["dice"] = dice_boundary(gt_boundary_mask, pred_boundary)
                    logger.info(f"WOA metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}, DICE={metrics['dice']:.4f}")
                else:
                    logger.info(f"WOA metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}")
            except Exception as e:
                logger.warning(f"Không thể tính metrics cho WOA: {e}")
            
            results["WOA"] = {
                "thresholds": [int(v) for v in np.asarray(best_x).ravel().tolist()],
                "best_f": float(best_f),
                "time": algo_time,
                "seg_data_url": _img_to_data_url_gray(seg),
                "best_series": _history_to_best_series(history),
                "metrics": metrics,
            }
            logger.info(f"WOA hoàn thành: best_f={best_f:.6f} (Entropy={-best_f:.6f}), time={algo_time:.2f}s")
            if best_f < best_overall_f:
                best_overall_f = best_f
                best_overall = best_x
                best_overall_algo = "WOA"

        if run_pso:
            logger.info("-" * 60)
            logger.info("CHẠY THUẬT TOÁN PSO")
            logger.info("-" * 60)
            logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed_for(25)}")
            algo_start = time.time()
            opt = _make_optimizer("PSO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(25),
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=shared_init_pop
            )
            algo_time = time.time() - algo_start
            
            # Log chi tiết quá trình tối ưu
            _log_optimization_progress("PSO", history, n_agents, n_iters)
            
            best_x = repair_fn(best_x)
            seg = apply_thresholds(gray, best_x)
            
            metrics = {}
            try:
                metrics["psnr"] = compute_psnr(gray, seg, data_range=255.0)
                metrics["ssim"] = compute_ssim(gray, seg, data_range=255.0)
                
                if gt_boundary_mask is not None:
                    pred_boundary = seg_to_boundary_mask(seg)
                    metrics["dice"] = dice_boundary(gt_boundary_mask, pred_boundary)
                    logger.info(f"PSO metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}, DICE={metrics['dice']:.4f}")
                else:
                    logger.info(f"PSO metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}")
            except Exception as e:
                logger.warning(f"Không thể tính metrics cho PSO: {e}")
            
            results["PSO"] = {
                "thresholds": [int(v) for v in np.asarray(best_x).ravel().tolist()],
                "best_f": float(best_f),
                "time": algo_time,
                "seg_data_url": _img_to_data_url_gray(seg),
                "best_series": _history_to_best_series(history),
                "metrics": metrics,
            }
            logger.info(f"PSO hoàn thành: best_f={best_f:.6f} (Entropy={-best_f:.6f}), time={algo_time:.2f}s")
            if best_f < best_overall_f:
                best_overall_f = best_f
                best_overall = best_x
                best_overall_algo = "PSO"

        if run_otsu:
            logger.info("-" * 60)
            logger.info("CHẠY THUẬT TOÁN OTSU")
            logger.info("-" * 60)
            logger.info(f"Tham số: Otsu là deterministic (không dùng n_agents, n_iters, seed)")
            logger.info(f"Image shape: {gray.shape}, k={k}")
            algo_start = time.time()
            
            # OTSU: Với K>4, threshold_multiotsu quá chậm (exponential complexity)
            # Giải pháp: K<=4 dùng Otsu chính xác, K>4 dùng evenly-spaced
            from skimage.filters import threshold_multiotsu
            logger.info("Bắt đầu tính Otsu thresholds...")
            
            if k <= 4:
                # Dùng Otsu chính xác cho K nhỏ
                logger.info(f"K={k} <= 4: Dùng threshold_multiotsu (chính xác)")
                try:
                    thresholds = threshold_multiotsu(gray, classes=k+1)
                    logger.info(f"Otsu thresholds tính xong: {thresholds}")
                except Exception as e:
                    logger.error(f"Lỗi khi tính Otsu thresholds: {e}", exc_info=True)
                    # Fallback to evenly-spaced
                    logger.info("Fallback: Dùng evenly-spaced thresholds")
                    thresholds = np.linspace(0, 255, k+2)[1:-1]
            else:
                # K>4: Dùng evenly-spaced (nhanh)
                logger.info(f"K={k} > 4: Dùng evenly-spaced thresholds (nhanh)")
                thresholds = np.linspace(0, 255, k+2)[1:-1]
                logger.info(f"Evenly-spaced thresholds: {thresholds}")
            
            try:
                logger.info("Đang repair thresholds...")
                best_x = repair_fn(np.array(thresholds))
                logger.info(f"Thresholds sau repair: {best_x}")
                
                logger.info("Đang tính fitness...")
                best_f = fitness_fn(best_x)
                logger.info(f"Fitness tính xong: {best_f}")
                
                history = [{"iter": 0, "best_f": float(best_f), "mean_f": float(best_f)}]
                algo_time = time.time() - algo_start
                
                # Log chi tiết quá trình tối ưu
                _log_optimization_progress("OTSU", history, n_agents, n_iters)
                
                best_x = repair_fn(best_x)
                seg = apply_thresholds(gray, best_x)
                
                metrics = {}
                try:
                    metrics["psnr"] = compute_psnr(gray, seg, data_range=255.0)
                    metrics["ssim"] = compute_ssim(gray, seg, data_range=255.0)
                    
                    if gt_boundary_mask is not None:
                        pred_boundary = seg_to_boundary_mask(seg)
                        metrics["dice"] = dice_boundary(gt_boundary_mask, pred_boundary)
                        logger.info(f"OTSU metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}, DICE={metrics['dice']:.4f}")
                    else:
                        logger.info(f"OTSU metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}")
                except Exception as e:
                    logger.warning(f"Không thể tính metrics cho OTSU: {e}")
                
                results["OTSU"] = {
                    "thresholds": [int(v) for v in np.asarray(best_x).ravel().tolist()],
                    "best_f": float(best_f),
                    "time": algo_time,
                    "seg_data_url": _img_to_data_url_gray(seg),
                    "best_series": _history_to_best_series(history),
                    "metrics": metrics,
                }
                logger.info(f"OTSU hoàn thành: best_f={best_f:.6f} (Entropy={-best_f:.6f}), time={algo_time:.2f}s")
                if best_f < best_overall_f:
                    best_overall_f = best_f
                    best_overall = best_x
                    best_overall_algo = "OTSU"
            except Exception as e:
                logger.error(f"Lỗi khi chạy OTSU: {e}", exc_info=True)

        if run_hybrid:
            for strategy in hybrid_strategies:
                strategy = strategy.strip().upper()
                if not strategy:
                    continue
                logger.info("-" * 60)
                logger.info(f"CHẠY THUẬT TOÁN HYBRID-{strategy}")
                logger.info("-" * 60)
                logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, strategy={strategy}, woa_b={woa_b}, share_interval={share_interval}")
                algo_start = time.time()
                opt = _make_optimizer("HYBRID", n_agents=n_agents, n_iters=n_iters, 
                                    seed=seed_for(30 + hash(strategy) % 100),
                                    strategy=strategy, woa_b=woa_b, share_interval=share_interval)
                best_x, best_f, history = opt.optimize(
                    fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                    repair_fn=repair_fn, init_pop=shared_init_pop
                )
                algo_time = time.time() - algo_start
                
                # Log chi tiết quá trình tối ưu
                _log_optimization_progress(f"HYBRID-{strategy}", history, n_agents, n_iters)
                
                best_x = repair_fn(best_x)
                seg = apply_thresholds(gray, best_x)
                algo_name = f"HYBRID-{strategy}"
                
                metrics = {}
                try:
                    metrics["psnr"] = compute_psnr(gray, seg, data_range=255.0)
                    metrics["ssim"] = compute_ssim(gray, seg, data_range=255.0)
                    
                    if gt_boundary_mask is not None:
                        pred_boundary = seg_to_boundary_mask(seg)
                        metrics["dice"] = dice_boundary(gt_boundary_mask, pred_boundary)
                        logger.info(f"{algo_name} metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}, DICE={metrics['dice']:.4f}")
                    else:
                        logger.info(f"{algo_name} metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}")
                except Exception as e:
                    logger.warning(f"Không thể tính metrics cho {algo_name}: {e}")
                
                results[algo_name] = {
                    "thresholds": [int(v) for v in np.asarray(best_x).ravel().tolist()],
                    "best_f": float(best_f),
                    "time": algo_time,
                    "seg_data_url": _img_to_data_url_gray(seg),
                    "best_series": _history_to_best_series(history),
                    "metrics": metrics,
                }
                logger.info(f"HYBRID-{strategy} hoàn thành: best_f={best_f:.6f} (Entropy={-best_f:.6f}), time={algo_time:.2f}s")
                if best_f < best_overall_f:
                    best_overall_f = best_f
                    best_overall = best_x
                    best_overall_algo = algo_name

        seg_time = time.time() - start_time
        logger.info("=" * 80)
        logger.info(f"PHÂN ĐOẠN ẢNH HOÀN THÀNH - Thuật toán tốt nhất: {best_overall_algo}")
        logger.info(f"  best_f (minimize): {best_overall_f:.6f}")
        logger.info(f"  Entropy (maximize): {-best_overall_f:.6f}")
        logger.info(f"Tổng thời gian phân đoạn: {seg_time:.2f}s")
        logger.info("=" * 80)

        response_data = {
            "k": k,
            "gray_data_url": _img_to_data_url_gray(gray),
            "results": results,
            "best_overall_algo": best_overall_algo,
            "best_overall_f": float(best_overall_f),
            "segmentation_time": seg_time,
            "has_ground_truth": gt_boundary_mask is not None,
            "image_name": os.path.basename(image_path),
        }

        # BẮT BUỘC chạy benchmark
        if BENCHMARK_NAMES is not None:
            logger.info("")
            logger.info("=" * 80)
            logger.info("BẮT ĐẦU CHẠY BENCHMARK (18 HÀM)")
            logger.info("=" * 80)
            benchmark_start = time.time()
            benchmark_results = _run_all_benchmarks(
                n_agents, n_iters, seed, woa_b, share_interval,
                run_gwo, run_woa, run_hybrid, hybrid_strategies
            )
            benchmark_time = time.time() - benchmark_start
            response_data["benchmark"] = benchmark_results
            response_data["benchmark_time"] = benchmark_time
            logger.info("=" * 80)
            logger.info(f"BENCHMARK HOÀN THÀNH - Thời gian: {benchmark_time:.2f}s")
            logger.info("=" * 80)

        total_time = time.time() - start_time
        response_data["total_time"] = total_time
        logger.info(f"TỔNG THỜI GIAN: {total_time:.2f}s")

        # Lưu kết quả vào outputs/runs
        try:
            run_dir = _create_run_dir("ui")
            
            # Parse penalty settings
            use_penalties = request.form.get("use_penalties", "0") == "1"
            penalty_mode = request.form.get("penalty_mode", "balanced")
            
            params = {
                "k": k,
                "n_agents": n_agents,
                "n_iters": n_iters,
                "seed": seed,
                "woa_b": woa_b,
                "share_interval": share_interval,
                "use_penalties": use_penalties,
                "penalty_mode": penalty_mode,
                "total_time": total_time,
                "best_overall_algo": best_overall_algo,
                "best_overall_f": best_overall_f,
            }
            
            _save_run_results(run_dir, gray, results, params, image_name="uploaded")
            response_data["run_dir"] = run_dir
            logger.info(f"✓ Kết quả đã lưu: {run_dir}")
        except Exception as e:
            logger.warning(f"Không thể lưu kết quả: {e}")

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"LỖI XẢY RA: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.post("/api/segment")
def api_segment():
    import time
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info("BẮT ĐẦU XỬ LÝ PHÂN ĐOẠN ẢNH")
    logger.info("=" * 80)
    
    f = request.files.get("image")
    if f is None:
        logger.error("Không tìm thấy file ảnh trong request")
        return jsonify({"error": "missing image"}), 400

    try:
        n_agents = int(request.form.get("n_agents", "30"))
        n_iters = int(request.form.get("n_iters", "80"))
        seed_raw = request.form.get("seed", "").strip()
        seed = None if seed_raw == "" else int(seed_raw)
        woa_b = float(request.form.get("woa_b", "1.0"))
        share_interval = int(request.form.get("share_interval", "1"))
        
        run_gwo = request.form.get("run_gwo", "0") == "1"
        run_woa = request.form.get("run_woa", "0") == "1"
        run_pso = request.form.get("run_pso", "0") == "1"
        run_otsu = request.form.get("run_otsu", "0") == "1"
        run_hybrid = request.form.get("run_hybrid", "0") == "1"
        hybrid_strategies = request.form.get("hybrid_strategies", "PA1").split(",")
        
        logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed}")
        logger.info(f"Thuật toán: GWO={run_gwo}, WOA={run_woa}, PSO={run_pso}, OTSU={run_otsu}, HYBRID={run_hybrid}")
        logger.info(f"Hybrid strategies: {hybrid_strategies}")
        logger.info(f"woa_b={woa_b}, share_interval={share_interval}")
    except Exception as e:
        logger.error(f"Lỗi khi parse tham số: {e}")
        return jsonify({"error": f"invalid params: {e}"}), 400

    if not (run_gwo or run_woa or run_pso or run_otsu or run_hybrid):
        logger.error("Không có thuật toán nào được chọn")
        return jsonify({"error": "Phải chọn ít nhất 1 thuật toán"}), 400

    logger.info("Đang đọc và xử lý ảnh...")
    gray = decode_image_gray(f.read())
    logger.info(f"Ảnh đã được đọc: shape={gray.shape}")

    k = K_FIXED
    lb, ub = 0, 255
    
    # Parse penalty settings
    use_penalties = request.form.get("use_penalties", "0") == "1"
    penalty_mode = request.form.get("penalty_mode", "balanced")
    
    logger.info(f"Penalty settings: use_penalties={use_penalties}, mode={penalty_mode}")

    def repair_fn(x: np.ndarray) -> np.ndarray:
        return repair_threshold_vector(
            x, k=k, lb=lb, ub=ub, 
            integer=True, 
            ensure_unique=True,
            avoid_endpoints=use_penalties  # Tránh 0/255 khi dùng penalties
        )

    # Create fitness function with or without penalties
    if use_penalties:
        weights = get_recommended_weights(penalty_mode)
        params = get_recommended_params(k=k)
        logger.info(f"Using penalties: w_gap={weights.w_gap}, w_size={weights.w_size}, min_gap={params.min_gap}, p_min={params.p_min}")
        fitness_fn = create_fe_objective_with_penalties(gray, repair_fn, weights, params, lb, ub)
    else:
        def fitness_fn(x: np.ndarray) -> float:
            return float(fuzzy_entropy_objective(gray, repair_fn(x)))

    results = {}
    best_overall = None
    best_overall_f = float('inf')
    best_overall_algo = ""

    def seed_for(offset: int) -> int | None:
        if seed is None:
            return None
        return seed + offset

    # Tạo quần thể khởi tạo chung cho tất cả thuật toán (để so sánh công bằng)
    shared_init_pop = None
    if seed is not None:
        rng_init = np.random.default_rng(seed)
        shared_init_pop = rng_init.uniform(lb, ub, size=(n_agents, k))
        logger.info(f"Đã tạo quần thể khởi tạo chung với seed={seed}")

    try:
        # Chạy GWO
        if run_gwo:
            logger.info("-" * 60)
            logger.info("CHẠY THUẬT TOÁN GWO")
            logger.info("-" * 60)
            logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed_for(10)}")
            algo_start = time.time()
            opt = _make_optimizer("GWO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(10), 
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=shared_init_pop
            )
            algo_time = time.time() - algo_start
            
            # Log chi tiết quá trình tối ưu
            _log_optimization_progress("GWO", history, n_agents, n_iters)
            
            best_x = repair_fn(best_x)
            seg = apply_thresholds(gray, best_x)
            
            # Tính metrics so sánh ảnh gốc và ảnh phân đoạn
            metrics = {}
            try:
                metrics["psnr"] = compute_psnr(gray, seg, data_range=255.0)
                metrics["ssim"] = compute_ssim(gray, seg, data_range=255.0)
                logger.info(f"GWO metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}")
            except Exception as e:
                logger.warning(f"Không thể tính metrics cho GWO: {e}")
            
            results["GWO"] = {
                "thresholds": [int(v) for v in np.asarray(best_x).ravel().tolist()],
                "best_f": float(best_f),
                "time": algo_time,
                "seg_data_url": _img_to_data_url_gray(seg),
                "best_series": _history_to_best_series(history),
                "metrics": metrics,
            }
            logger.info(f"GWO hoàn thành: best_f={best_f:.6f} (Entropy={-best_f:.6f}), time={algo_time:.2f}s")
            if best_f < best_overall_f:
                best_overall_f = best_f
                best_overall = best_x
                best_overall_algo = "GWO"

        # Chạy WOA
        if run_woa:
            logger.info("-" * 60)
            logger.info("CHẠY THUẬT TOÁN WOA")
            logger.info("-" * 60)
            logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed_for(20)}, woa_b={woa_b}")
            algo_start = time.time()
            opt = _make_optimizer("WOA", n_agents=n_agents, n_iters=n_iters, seed=seed_for(20),
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=shared_init_pop
            )
            algo_time = time.time() - algo_start
            
            # Log chi tiết quá trình tối ưu
            _log_optimization_progress("WOA", history, n_agents, n_iters)
            
            best_x = repair_fn(best_x)
            seg = apply_thresholds(gray, best_x)
            
            # Tính metrics so sánh ảnh gốc và ảnh phân đoạn
            metrics = {}
            try:
                metrics["psnr"] = compute_psnr(gray, seg, data_range=255.0)
                metrics["ssim"] = compute_ssim(gray, seg, data_range=255.0)
                logger.info(f"WOA metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}")
            except Exception as e:
                logger.warning(f"Không thể tính metrics cho WOA: {e}")
            
            results["WOA"] = {
                "thresholds": [int(v) for v in np.asarray(best_x).ravel().tolist()],
                "best_f": float(best_f),
                "time": algo_time,
                "seg_data_url": _img_to_data_url_gray(seg),
                "best_series": _history_to_best_series(history),
                "metrics": metrics,
            }
            logger.info(f"WOA hoàn thành: best_f={best_f:.6f} (Entropy={-best_f:.6f}), time={algo_time:.2f}s")
            if best_f < best_overall_f:
                best_overall_f = best_f
                best_overall = best_x
                best_overall_algo = "WOA"

        # Chạy PSO
        if run_pso:
            logger.info("-" * 60)
            logger.info("CHẠY THUẬT TOÁN PSO")
            logger.info("-" * 60)
            logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed_for(25)}")
            algo_start = time.time()
            opt = _make_optimizer("PSO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(25),
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=shared_init_pop
            )
            algo_time = time.time() - algo_start
            
            # Log chi tiết quá trình tối ưu
            _log_optimization_progress("PSO", history, n_agents, n_iters)
            
            best_x = repair_fn(best_x)
            seg = apply_thresholds(gray, best_x)
            
            # Tính metrics so sánh ảnh gốc và ảnh phân đoạn
            metrics = {}
            try:
                metrics["psnr"] = compute_psnr(gray, seg, data_range=255.0)
                metrics["ssim"] = compute_ssim(gray, seg, data_range=255.0)
                logger.info(f"PSO metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}")
            except Exception as e:
                logger.warning(f"Không thể tính metrics cho PSO: {e}")
            
            results["PSO"] = {
                "thresholds": [int(v) for v in np.asarray(best_x).ravel().tolist()],
                "best_f": float(best_f),
                "time": algo_time,
                "seg_data_url": _img_to_data_url_gray(seg),
                "best_series": _history_to_best_series(history),
                "metrics": metrics,
            }
            logger.info(f"PSO hoàn thành: best_f={best_f:.6f} (Entropy={-best_f:.6f}), time={algo_time:.2f}s")
            if best_f < best_overall_f:
                best_overall_f = best_f
                best_overall = best_x
                best_overall_algo = "PSO"

        # Chạy OTSU
        if run_otsu:
            logger.info("-" * 60)
            logger.info("CHẠY THUẬT TOÁN OTSU")
            logger.info("-" * 60)
            logger.info(f"Tham số: Otsu là deterministic (không dùng n_agents, n_iters, seed)")
            logger.info(f"Image shape: {gray.shape}, k={k}")
            algo_start = time.time()
            
            # OTSU: Với K>4, threshold_multiotsu quá chậm (exponential complexity)
            # Giải pháp: K<=4 dùng Otsu chính xác, K>4 dùng evenly-spaced
            from skimage.filters import threshold_multiotsu
            logger.info("Bắt đầu tính Otsu thresholds...")
            
            if k <= 4:
                # Dùng Otsu chính xác cho K nhỏ
                logger.info(f"K={k} <= 4: Dùng threshold_multiotsu (chính xác)")
                try:
                    thresholds = threshold_multiotsu(gray, classes=k+1)
                    logger.info(f"Otsu thresholds tính xong: {thresholds}")
                except Exception as e:
                    logger.error(f"Lỗi khi tính Otsu thresholds: {e}", exc_info=True)
                    # Fallback to evenly-spaced
                    logger.info("Fallback: Dùng evenly-spaced thresholds")
                    thresholds = np.linspace(0, 255, k+2)[1:-1]
            else:
                # K>4: Dùng evenly-spaced (nhanh)
                logger.info(f"K={k} > 4: Dùng evenly-spaced thresholds (nhanh)")
                thresholds = np.linspace(0, 255, k+2)[1:-1]
                logger.info(f"Evenly-spaced thresholds: {thresholds}")
            
            try:
                logger.info("Đang repair thresholds...")
                best_x = repair_fn(np.array(thresholds))
                logger.info(f"Thresholds sau repair: {best_x}")
                
                logger.info("Đang tính fitness...")
                best_f = fitness_fn(best_x)
                logger.info(f"Fitness tính xong: {best_f}")
                
                history = [{"iter": 0, "best_f": float(best_f), "mean_f": float(best_f)}]
                algo_time = time.time() - algo_start
                
                # Log chi tiết quá trình tối ưu
                _log_optimization_progress("OTSU", history, n_agents, n_iters)
                
                best_x = repair_fn(best_x)
                seg = apply_thresholds(gray, best_x)
                
                # Tính metrics so sánh ảnh gốc và ảnh phân đoạn
                metrics = {}
                try:
                    metrics["psnr"] = compute_psnr(gray, seg, data_range=255.0)
                    metrics["ssim"] = compute_ssim(gray, seg, data_range=255.0)
                    logger.info(f"OTSU metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}")
                except Exception as e:
                    logger.warning(f"Không thể tính metrics cho OTSU: {e}")
                
                results["OTSU"] = {
                    "thresholds": [int(v) for v in np.asarray(best_x).ravel().tolist()],
                    "best_f": float(best_f),
                    "time": algo_time,
                    "seg_data_url": _img_to_data_url_gray(seg),
                    "best_series": _history_to_best_series(history),
                    "metrics": metrics,
                }
                logger.info(f"OTSU hoàn thành: best_f={best_f:.6f} (Entropy={-best_f:.6f}), time={algo_time:.2f}s")
                if best_f < best_overall_f:
                    best_overall_f = best_f
                    best_overall = best_x
                    best_overall_algo = "OTSU"
            except Exception as e:
                logger.error(f"Lỗi khi chạy OTSU: {e}", exc_info=True)

        # Chạy HYBRID với các strategies
        if run_hybrid:
            for strategy in hybrid_strategies:
                strategy = strategy.strip().upper()
                if not strategy:
                    continue
                logger.info("-" * 60)
                logger.info(f"CHẠY THUẬT TOÁN HYBRID-{strategy}")
                logger.info("-" * 60)
                logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, strategy={strategy}, woa_b={woa_b}, share_interval={share_interval}")
                algo_start = time.time()
                opt = _make_optimizer("HYBRID", n_agents=n_agents, n_iters=n_iters, 
                                    seed=seed_for(30 + hash(strategy) % 100),
                                    strategy=strategy, woa_b=woa_b, share_interval=share_interval)
                best_x, best_f, history = opt.optimize(
                    fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                    repair_fn=repair_fn, init_pop=shared_init_pop
                )
                algo_time = time.time() - algo_start
                
                # Log chi tiết quá trình tối ưu
                _log_optimization_progress(f"HYBRID-{strategy}", history, n_agents, n_iters)
                
                best_x = repair_fn(best_x)
                seg = apply_thresholds(gray, best_x)
                algo_name = f"HYBRID-{strategy}"
                
                # Tính metrics so sánh ảnh gốc và ảnh phân đoạn
                metrics = {}
                try:
                    metrics["psnr"] = compute_psnr(gray, seg, data_range=255.0)
                    metrics["ssim"] = compute_ssim(gray, seg, data_range=255.0)
                    logger.info(f"{algo_name} metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}")
                except Exception as e:
                    logger.warning(f"Không thể tính metrics cho {algo_name}: {e}")
                
                results[algo_name] = {
                    "thresholds": [int(v) for v in np.asarray(best_x).ravel().tolist()],
                    "best_f": float(best_f),
                    "time": algo_time,
                    "seg_data_url": _img_to_data_url_gray(seg),
                    "best_series": _history_to_best_series(history),
                    "metrics": metrics,
                }
                logger.info(f"HYBRID-{strategy} hoàn thành: best_f={best_f:.6f} (Entropy={-best_f:.6f}), time={algo_time:.2f}s")
                if best_f < best_overall_f:
                    best_overall_f = best_f
                    best_overall = best_x
                    best_overall_algo = algo_name

        seg_time = time.time() - start_time
        logger.info("=" * 80)
        logger.info(f"PHÂN ĐOẠN ẢNH HOÀN THÀNH - Thuật toán tốt nhất: {best_overall_algo}")
        logger.info(f"  best_f (minimize): {best_overall_f:.6f}")
        logger.info(f"  Entropy (maximize): {-best_overall_f:.6f}")
        logger.info(f"Tổng thời gian phân đoạn: {seg_time:.2f}s")
        logger.info("=" * 80)

        response_data = {
            "k": k,
            "gray_data_url": _img_to_data_url_gray(gray),
            "results": results,
            "best_overall_algo": best_overall_algo,
            "best_overall_f": float(best_overall_f),
            "segmentation_time": seg_time,
        }

        # BẮT BUỘC chạy benchmark cho TẤT CẢ 18 hàm với dim = n_agents
        if BENCHMARK_NAMES is not None:
            logger.info("")
            logger.info("=" * 80)
            logger.info("BẮT ĐẦU CHẠY BENCHMARK (18 HÀM)")
            logger.info("=" * 80)
            benchmark_start = time.time()
            benchmark_results = _run_all_benchmarks(
                n_agents, n_iters, seed, woa_b, share_interval,
                run_gwo, run_woa, run_hybrid, hybrid_strategies
            )
            benchmark_time = time.time() - benchmark_start
            response_data["benchmark"] = benchmark_results
            response_data["benchmark_time"] = benchmark_time
            logger.info("=" * 80)
            logger.info(f"BENCHMARK HOÀN THÀNH - Thời gian: {benchmark_time:.2f}s")
            logger.info("=" * 80)

        total_time = time.time() - start_time
        response_data["total_time"] = total_time
        logger.info(f"TỔNG THỜI GIAN: {total_time:.2f}s")

        # Lưu kết quả vào outputs/runs
        try:
            run_dir = _create_run_dir("bds500")
            
            # Parse penalty settings
            use_penalties = request.form.get("use_penalties", "0") == "1"
            penalty_mode = request.form.get("penalty_mode", "balanced")
            
            params = {
                "k": k,
                "n_agents": n_agents,
                "n_iters": n_iters,
                "seed": seed,
                "woa_b": woa_b,
                "share_interval": share_interval,
                "use_penalties": use_penalties,
                "penalty_mode": penalty_mode,
                "gt_thr": gt_thr,
                "gt_fuse": gt_fuse,
                "total_time": total_time,
                "best_overall_algo": best_overall_algo,
                "best_overall_f": best_overall_f,
            }
            
            image_name = os.path.basename(image_path) if image_path else "bds500"
            _save_run_results(run_dir, gray, results, params, image_name=image_name)
            response_data["run_dir"] = run_dir
            logger.info(f"✓ Kết quả đã lưu: {run_dir}")
        except Exception as e:
            logger.warning(f"Không thể lưu kết quả: {e}")

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"LỖI XẢY RA: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.post("/api/benchmark_compare")
def api_benchmark_compare():
    if BENCHMARK_NAMES is None or benchmark_functions is None or set_bounds is None:
        return jsonify({"error": "missing src/benchmarks (benchmark.py, benchmark_func.py)"}), 400

    try:
        fun_1 = int(request.form.get("fun", "1"))
        dim = int(request.form.get("dim", "30"))
        n_agents = int(request.form.get("n_agents", "50"))
        n_iters = int(request.form.get("n_iters", "200"))
        seed_raw = request.form.get("seed", "").strip()
        seed = None if seed_raw == "" else int(seed_raw)
        woa_b = float(request.form.get("woa_b", "1.0"))
        share_interval = int(request.form.get("share_interval", "1"))

        run_gwo = request.form.get("run_gwo", "1") == "1"
        run_woa = request.form.get("run_woa", "1") == "1"
        run_hybrid = request.form.get("run_hybrid", "1") == "1"
        hybrid_strategies = request.form.get("hybrid_strategies", "PA1").split(",")
    except Exception as e:
        return jsonify({"error": f"invalid params: {e}"}), 400

    result = _run_benchmark_internal(fun_1, dim, n_agents, n_iters, seed, woa_b, share_interval,
                                     run_gwo, run_woa, run_hybrid, hybrid_strategies)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)


@app.get("/api/runs/list")
def api_runs_list():
    """Lấy danh sách tất cả runs đã lưu"""
    try:
        runs_dir = os.path.join("outputs", "runs")
        
        if not os.path.exists(runs_dir):
            return jsonify({"runs": []})
        
        runs = []
        for run_name in os.listdir(runs_dir):
            run_path = os.path.join(runs_dir, run_name)
            if not os.path.isdir(run_path):
                continue
            
            # Đọc summary.json
            summary_path = os.path.join(run_path, "summary.json")
            config_path = os.path.join(run_path, "config.yaml")
            
            if not os.path.exists(summary_path):
                continue
            
            try:
                with open(summary_path, "r") as f:
                    summary = json.load(f)
                
                config = {}
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = yaml.safe_load(f)
                
                # Lấy thông tin cơ bản
                algorithms = config.get("algorithms", [])
                if isinstance(algorithms, list):
                    algorithms = algorithms
                else:
                    algorithms = []
                
                run_info = {
                    "run_name": run_name,
                    "run_path": run_path,
                    "image_name": summary.get("image_name", "unknown"),
                    "timestamp": summary.get("timestamp", ""),
                    "total_time": summary.get("total_time", 0),
                    "best_algo": summary.get("best_overall_algo", ""),
                    "best_entropy": summary.get("best_overall_entropy", 0),
                    "algorithms": algorithms,
                    "k": config.get("k", 10),
                    "n_agents": config.get("n_agents", 30),
                    "n_iters": config.get("n_iters", 80),
                    "use_penalties": config.get("use_penalties", False),
                }
                
                runs.append(run_info)
            except Exception as e:
                logger.warning(f"Không thể đọc run {run_name}: {e}")
                continue
        
        # Sắp xếp theo timestamp (mới nhất trước)
        runs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return jsonify({"runs": runs, "total": len(runs)})
    
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách runs: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.get("/api/runs/<run_name>")
def api_run_detail(run_name):
    """Lấy chi tiết một run"""
    try:
        run_path = os.path.join("outputs", "runs", run_name)
        
        if not os.path.exists(run_path):
            return jsonify({"error": "Run not found"}), 404
        
        # Đọc summary
        summary_path = os.path.join(run_path, "summary.json")
        if not os.path.exists(summary_path):
            return jsonify({"error": "Summary not found"}), 404
        
        with open(summary_path, "r") as f:
            summary = json.load(f)
        
        # Đọc config
        config_path = os.path.join(run_path, "config.yaml")
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
        
        # Đọc ảnh gốc
        gray_path = os.path.join(run_path, "gray.png")
        gray_data_url = None
        if os.path.exists(gray_path) and Image is not None:
            with open(gray_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                gray_data_url = f"data:image/png;base64,{b64}"
        
        # Đọc kết quả từng thuật toán
        algorithms = {}
        for algo_name in config.get("algorithms", []):
            algo_dir = os.path.join(run_path, algo_name)
            if not os.path.exists(algo_dir):
                continue
            
            # Đọc best.json
            best_path = os.path.join(algo_dir, "best.json")
            if os.path.exists(best_path):
                with open(best_path, "r") as f:
                    best = json.load(f)
                
                # Đọc ảnh phân đoạn
                seg_path = os.path.join(algo_dir, "segmented.png")
                seg_data_url = None
                if os.path.exists(seg_path) and Image is not None:
                    with open(seg_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        seg_data_url = f"data:image/png;base64,{b64}"
                
                # Đọc history
                history_path = os.path.join(algo_dir, "history.jsonl")
                history = []
                if os.path.exists(history_path):
                    with open(history_path, "r") as f:
                        for line in f:
                            history.append(json.loads(line))
                
                algorithms[algo_name] = {
                    "best": best,
                    "seg_data_url": seg_data_url,
                    "history": history,
                }
        
        return jsonify({
            "run_name": run_name,
            "summary": summary,
            "config": config,
            "gray_data_url": gray_data_url,
            "algorithms": algorithms,
        })
    
    except Exception as e:
        logger.error(f"Lỗi khi lấy chi tiết run: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.delete("/api/runs/<run_name>")
def api_run_delete(run_name):
    """Xóa một run"""
    try:
        run_path = os.path.join("outputs", "runs", run_name)
        
        if not os.path.exists(run_path):
            return jsonify({"error": "Run not found"}), 404
        
        # Xóa thư mục
        import shutil
        shutil.rmtree(run_path)
        
        logger.info(f"✓ Đã xóa run: {run_name}")
        return jsonify({"success": True, "message": f"Deleted {run_name}"})
    
    except Exception as e:
        logger.error(f"Lỗi khi xóa run: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.post("/api/eval_bds500")
def api_eval_bds500():
    """
    Đánh giá toàn bộ dataset BDS500
    
    Form params:
        - split: "train", "val", hoặc "test"
        - limit: số ảnh giới hạn (0 = không giới hạn)
        - k: số ngưỡng (default: 10)
        - seed: random seed (default: 42)
        - n_agents: số cá thể (default: 30)
        - n_iters: số vòng lặp (default: 80)
        - algorithms: danh sách thuật toán (comma-separated)
    """
    import time
    from datetime import datetime
    
    logger.info("=" * 80)
    logger.info("BẮT ĐẦU ĐÁNH GIÁ BDS500")
    logger.info("=" * 80)
    
    try:
        # Parse parameters
        split = request.form.get("split", "train")
        limit = int(request.form.get("limit", "0"))
        k = int(request.form.get("k", "10"))
        seed_raw = request.form.get("seed", "42").strip()
        seed = None if seed_raw == "" else int(seed_raw)
        n_agents = int(request.form.get("n_agents", "30"))
        n_iters = int(request.form.get("n_iters", "80"))
        woa_b = float(request.form.get("woa_b", "1.0"))
        share_interval = int(request.form.get("share_interval", "1"))
        
        # Parse algorithms
        algos_str = request.form.get("algorithms", "GWO,WOA,HYBRID-PA1")
        algorithms = [a.strip() for a in algos_str.split(",") if a.strip()]
        
        logger.info(f"Cấu hình:")
        logger.info(f"  Split: {split}")
        logger.info(f"  Limit: {limit if limit > 0 else 'không giới hạn'}")
        logger.info(f"  K: {k}")
        logger.info(f"  Seed: {seed}")
        logger.info(f"  N_agents: {n_agents}")
        logger.info(f"  N_iters: {n_iters}")
        logger.info(f"  Algorithms: {algorithms}")
        
        # Load dataset
        from src.data.bsds500 import load_bsds500
        
        logger.info(f"Đang load dataset BDS500 split='{split}'...")
        start_load = time.time()
        
        try:
            dataset = load_bsds500(split=split, limit=limit)
        except Exception as e:
            logger.error(f"Lỗi khi load dataset: {e}", exc_info=True)
            return jsonify({"error": f"Lỗi khi load dataset: {str(e)}"}), 400
        
        load_time = time.time() - start_load
        
        logger.info(f"✓ Đã load {len(dataset)} ảnh trong {load_time:.2f}s")
        
        if len(dataset) == 0:
            return jsonify({"error": "Không có ảnh nào được load"}), 400
        
        # Setup
        lb, ub = 0, 255
        
        def repair_fn(x):
            return repair_threshold_vector(
                x, k=k, lb=lb, ub=ub,
                integer=True, ensure_unique=True, avoid_endpoints=True
            )
        
        # Tạo shared init_pop
        shared_init_pop = None
        if seed is not None:
            rng_init = np.random.default_rng(seed)
            shared_init_pop = rng_init.uniform(lb, ub, size=(n_agents, k))
            logger.info(f"Đã tạo quần thể khởi tạo chung với seed={seed}")
        
        # Evaluate
        results = []
        total_images = len(dataset)
        total_algos = len(algorithms)
        total_runs = total_images * total_algos
        
        logger.info(f"Bắt đầu đánh giá: {total_images} ảnh × {total_algos} thuật toán = {total_runs} runs")
        logger.info("=" * 80)
        
        run_count = 0
        overall_start = time.time()
        
        for img_idx, (img, gt_boundary) in enumerate(dataset):
            image_id = f"img_{img_idx:04d}"
            
            logger.info(f"\n[{img_idx+1}/{total_images}] Image: {image_id}, Shape: {img.shape}")
            
            for algo_name in algorithms:
                run_count += 1
                algo_start_time = time.time()
                
                logger.info(f"  [{run_count}/{total_runs}] {algo_name}...")
                
                try:
                    # Fix seed
                    if seed is not None:
                        np.random.seed(seed)
                        logger.info(f"    - Đã set seed={seed}")
                    
                    # Create fitness function
                    def fitness_fn(x):
                        return float(fuzzy_entropy_objective(img, repair_fn(x)))
                    
                    logger.info(f"    - Đang tạo optimizer {algo_name}...")
                    
                    # Create optimizer
                    algo_upper = algo_name.upper()
                    if algo_upper == "GWO":
                        opt = _make_optimizer("GWO", n_agents=n_agents, n_iters=n_iters,
                                            seed=seed, strategy="PA1", woa_b=woa_b,
                                            share_interval=share_interval)
                    elif algo_upper == "WOA":
                        opt = _make_optimizer("WOA", n_agents=n_agents, n_iters=n_iters,
                                            seed=seed, strategy="PA1", woa_b=woa_b,
                                            share_interval=share_interval)
                    elif algo_upper == "PSO":
                        opt = _make_optimizer("PSO", n_agents=n_agents, n_iters=n_iters,
                                            seed=seed, strategy="PA1", woa_b=woa_b,
                                            share_interval=share_interval)
                    elif algo_upper == "OTSU":
                        # OTSU không cần optimizer, dùng threshold_multiotsu trực tiếp
                        from skimage.filters import threshold_multiotsu
                        opt = None  # Đánh dấu để xử lý riêng
                    elif algo_upper.startswith("HYBRID-") or algo_upper.startswith("PA"):
                        # Support both "HYBRID-PA1" and "PA1" formats
                        if algo_upper.startswith("HYBRID-"):
                            strategy = algo_upper.replace("HYBRID-", "")
                        else:
                            strategy = algo_upper
                        
                        logger.info(f"    - Strategy: {strategy}")
                        opt = _make_optimizer("HYBRID", n_agents=n_agents, n_iters=n_iters,
                                            seed=seed, strategy=strategy, woa_b=woa_b,
                                            share_interval=share_interval)
                    else:
                        raise ValueError(f"Unknown algorithm: {algo_name}")
                    
                    logger.info(f"    - Đang chạy optimization...")
                    
                    # Run optimization
                    if algo_upper == "OTSU":
                        # OTSU: Dùng threshold_multiotsu trực tiếp
                        from skimage.filters import threshold_multiotsu
                        thresholds = threshold_multiotsu(img, classes=k+1)
                        best_x = repair_fn(np.array(thresholds))
                        best_f = fitness_fn(best_x)
                        history = [{"iter": 0, "best_f": float(best_f), "mean_f": float(best_f)}]
                    else:
                        # Các thuật toán khác: Dùng optimizer
                        best_x, best_f, history = opt.optimize(
                            fitness_fn,
                            dim=k,
                            lb=np.full(k, lb, dtype=float),
                            ub=np.full(k, ub, dtype=float),
                            repair_fn=repair_fn,
                            init_pop=shared_init_pop,
                        )
                    algo_time = time.time() - algo_start_time
                    
                    logger.info(f"    - Hoàn thành optimization trong {algo_time:.2f}s")
                    logger.info(f"    - Đang tính DICE score...")
                    
                    # Apply thresholds
                    best_x = repair_fn(best_x)
                    seg = apply_thresholds(img, best_x)
                    
                    # Extract boundary
                    pred_boundary = seg_to_boundary_mask(seg)
                    
                    # Calculate DICE
                    dice = dice_boundary(gt_boundary, pred_boundary)
                    
                    # Tính FE đúng (không có penalty)
                    from src.objective.thresholding_with_penalties import (
                        compute_true_fe,
                        compute_fe_stability_jitter,
                        compute_fe_stability_convergence,
                    )
                    
                    fe_true = compute_true_fe(img, best_x)
                    
                    # Tính độ ổn định FE (jitter)
                    # Dùng seed cố định theo image_id để mọi thuật toán có cùng jitter
                    jitter_seed = hash(image_id) % (2**31)  # Seed cố định cho mỗi ảnh
                    fe_stab_jitter = compute_fe_stability_jitter(
                        img, best_x, repair_fn,
                        n_samples=20, delta=2, seed=jitter_seed
                    )
                    
                    # Tính độ ổn định FE (convergence)
                    fe_stab_conv = compute_fe_stability_convergence(history, last_w=10)
                    
                    results.append({
                        "image_id": image_id,
                        "algorithm": algo_name,
                        "seed": seed,
                        "k": k,
                        # DICE metrics
                        "dice": float(dice),
                        # FE metrics
                        "fe": float(fe_true),  # FE đúng (không có penalty)
                        "fe_jitter_mean": float(fe_stab_jitter["fe_mean"]),
                        "fe_jitter_std": float(fe_stab_jitter["fe_std"]),  # Độ ổn định jitter
                        "fe_conv_std": float(fe_stab_conv["fe_last_std"]),  # Độ ổn định convergence
                        "fe_improvement": float(fe_stab_conv["fe_improvement"]),
                        # Other
                        "best_f": float(best_f),  # Có thể chứa penalty
                        "time": float(algo_time),
                        "thresholds": best_x.tolist(),
                        "n_iters": len(history),
                    })
                    
                    logger.info(f"    ✓ DICE={dice:.4f}, FE={fe_true:.4f}, FE_jitter_std={fe_stab_jitter['fe_std']:.6f}, Time={algo_time:.2f}s")
                    
                except Exception as e:
                    logger.error(f"    ✗ ERROR: {e}", exc_info=True)
                    results.append({
                        "image_id": image_id,
                        "algorithm": algo_name,
                        "seed": seed,
                        "k": k,
                        "error": str(e),
                    })
        
        total_time = time.time() - overall_start
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("HOÀN THÀNH ĐÁNH GIÁ BDS500")
        logger.info("=" * 80)
        logger.info(f"Tổng thời gian: {total_time:.2f}s ({total_time/60:.2f} phút)")
        
        # Calculate summary statistics - TÁCH DICE và FE
        dice_stats = {}
        fe_stats = {}
        
        for algo_name in algorithms:
            algo_results = [r for r in results if r.get("algorithm") == algo_name and "error" not in r]
            
            if algo_results:
                # DICE statistics
                dices = [r["dice"] for r in algo_results]
                dice_stats[algo_name] = {
                    "n_images": len(algo_results),
                    "dice_mean": float(np.mean(dices)),
                    "dice_std": float(np.std(dices)),
                    "dice_min": float(np.min(dices)),
                    "dice_max": float(np.max(dices)),
                }
                
                # FE statistics
                fes = [r["fe"] for r in algo_results]
                times = [r["time"] for r in algo_results]
                
                fe_stats[algo_name] = {
                    "n_images": len(algo_results),
                    "fe_mean": float(np.mean(fes)),
                    "fe_std": float(np.std(fes)),
                    "fe_min": float(np.min(fes)),
                    "fe_max": float(np.max(fes)),
                    "time_mean": float(np.mean(times)),
                }
        
        # Log summary
        logger.info("")
        logger.info("DICE STATISTICS:")
        for algo_name, stats in dice_stats.items():
            logger.info(f"  {algo_name}:")
            logger.info(f"    DICE: {stats['dice_mean']:.4f} ± {stats['dice_std']:.4f}")
        
        logger.info("")
        logger.info("FE STATISTICS:")
        for algo_name, stats in fe_stats.items():
            logger.info(f"  {algo_name}:")
            logger.info(f"    FE: {stats['fe_mean']:.4f} ± {stats['fe_std']:.4f}")
            logger.info(f"    Time: {stats['time_mean']:.2f}s")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join("outputs", "bds500_eval", f"k{k}_seed{seed}_{split}_{timestamp}")
        os.makedirs(run_dir, exist_ok=True)
        
        # Save detailed results
        results_file = os.path.join(run_dir, f"results_k{k}_seed{seed}.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save summary
        summary_data = {
            "config": {
                "k": k,
                "seed": seed,
                "n_agents": n_agents,
                "n_iters": n_iters,
                "split": split,
                "n_images": total_images,
                "algorithms": algorithms,
            },
            "dice_statistics": dice_stats,
            "fe_statistics": fe_stats,
            "total_time": total_time,
            "warning": "Chỉ 1 seed - không đủ dữ liệu để kết luận thuật toán nào tốt hơn.",
        }
        
        summary_file = os.path.join(run_dir, f"summary_k{k}_seed{seed}.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Đã lưu kết quả: {run_dir}")
        logger.info("=" * 80)
        
        return jsonify({
            "success": True,
            "run_dir": run_dir,
            "results_file": results_file,
            "summary_file": summary_file,
            "stats": {
                "total_images": total_images,
                "successful": len([r for r in results if "error" not in r]),
                "failed": len([r for r in results if "error" in r]),
            },
            "dice_stats": dice_stats,
            "fe_stats": fe_stats,
            "total_time": total_time,
        })
        
    except Exception as e:
        logger.error(f"LỖI ĐÁNH GIÁ BDS500: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

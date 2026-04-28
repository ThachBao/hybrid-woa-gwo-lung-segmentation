# ui/app.py
from __future__ import annotations

import base64
from io import BytesIO
import glob
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
import yaml

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, send_file

from src.objective.fuzzy_entropy_s import fuzzy_entropy_objective
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
from src.metrics.quality import compute_psnr, compute_ssim
from src.metrics.statistics import convergence_iteration, standard_deviation, wilcoxon_signed_rank
from src.data.cxr_dataset import (
    DEFAULT_CXR_ROOT,
    get_dataset_paths as get_cxr_dataset_paths,
    list_cases as list_cxr_cases,
    load_case as load_cxr_case,
    scan_cxr_dataset,
)
from src.cxr.lung_mask import segmented_to_lung_mask
from src.cxr.metrics import compute_cxr_metrics
from src.cxr.pipeline import run_pa5_cxr
from src.cxr.postprocess import postprocess_lung_mask
from src.cxr.preprocess import load_cxr_image, preprocess_cxr
from src.cxr.visualization import (
    build_convergence_payload,
    save_gray_png,
    save_mask_png,
    save_overlay_png,
)
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


def _get_light_penalty_setup(k: int):
    weights = get_recommended_weights("light")
    params = get_recommended_params(k=k)

    # Moderate penalty: still FE-led, but strong enough to reduce clustered
    # thresholds, empty regions, edge-hugging solutions, and odd quantiles.
    weights.w_gap = 0.8
    weights.w_var = 0.15
    weights.w_end = 0.08
    weights.w_size = 0.9
    weights.w_q = 0.25

    params.min_gap = max(5, min(params.min_gap, 8))
    params.end_margin = min(params.end_margin, 3)
    params.p_min = min(params.p_min, 0.01)
    return weights, params


def _build_threshold_objective(gray: np.ndarray, k: int, lb: int = 0, ub: int = 255):
    """Build a more stable thresholding objective for single-image runs.

    For higher-k multilevel thresholding, FE-only often clusters thresholds and
    creates near-empty regions. A moderate penalty keeps FE as the main driver
    while making single-run results less brittle.
    """
    use_penalties = int(k) >= 8
    penalty_mode = "light" if use_penalties else None
    avoid_endpoints = bool(use_penalties)

    def repair_fn(x: np.ndarray) -> np.ndarray:
        return repair_threshold_vector(
            x,
            k=int(k),
            lb=lb,
            ub=ub,
            integer=True,
            ensure_unique=True,
            avoid_endpoints=avoid_endpoints,
        )

    if use_penalties:
        weights, params = _get_light_penalty_setup(k=int(k))
        fitness_fn = create_fe_objective_with_penalties(
            gray,
            repair_fn,
            weights=weights,
            params=params,
            lb=lb,
            ub=ub,
        )
        objective_label = f"FE + {penalty_mode} penalties"
    else:
        fitness_fn = lambda x: fuzzy_entropy_objective(gray, repair_fn(x))
        objective_label = "FE thuần"

    return repair_fn, fitness_fn, use_penalties, penalty_mode, objective_label


def _refine_thresholds_local(
    best_x: np.ndarray,
    fitness_fn,
    repair_fn,
    *,
    deltas: tuple[int, ...] = (4, 2, 1),
    passes_per_delta: int = 2,
) -> tuple[np.ndarray, float]:
    """Polish threshold vectors with a small deterministic coordinate search."""
    current_x = repair_fn(np.asarray(best_x, dtype=float))
    current_f = float(fitness_fn(current_x))

    for delta in deltas:
        for _ in range(max(1, int(passes_per_delta))):
            changed = False
            for idx in range(current_x.size):
                candidate_best_x = current_x
                candidate_best_f = current_f
                for step in (-delta, delta):
                    cand_x = current_x.copy()
                    cand_x[idx] = cand_x[idx] + step
                    cand_x = repair_fn(cand_x)
                    cand_f = float(fitness_fn(cand_x))
                    if cand_f < candidate_best_f - 1e-12:
                        candidate_best_x = cand_x
                        candidate_best_f = cand_f
                if candidate_best_f < current_f - 1e-12:
                    current_x = candidate_best_x
                    current_f = candidate_best_f
                    changed = True
            if not changed:
                break

    return current_x, float(current_f)

K_FIXED = 10
SHARE_INTERVAL_FIXED = 10
MAIN_HYBRID_STRATEGIES = ("PA5", "PA6")

# BDS500 dataset paths
BDS500_ROOT = "dataset/BDS500"
BDS500_IMAGES_ROOT = f"{BDS500_ROOT}/images"
BDS500_GT_ROOT = f"{BDS500_ROOT}/ground_truth"

HYBRID_SEED_OFFSETS = {
    "PA1": 31,
    "PA2": 32,
    "PA3": 33,
    "PA4": 34,
    "PA5": 35,
    "PA6": 36,
}


def _hybrid_seed_offset(strategy: str) -> int:
    return HYBRID_SEED_OFFSETS.get(str(strategy).strip().upper(), 39)


def _stable_string_seed(value: str) -> int:
    text = str(value)
    acc = 0
    for idx, ch in enumerate(text):
        acc = (acc * 131 + (idx + 1) * ord(ch)) % (2**31 - 1)
    return acc


def _base_init_population(base_seed: int | None, n_agents: int, k: int, lb: int, ub: int) -> np.ndarray | None:
    if base_seed is None:
        return None
    rng = np.random.default_rng(int(base_seed))
    return rng.uniform(lb, ub, size=(n_agents, k))


def _normalize_main_hybrid_strategies(strategies: list[str]) -> list[str]:
    normalized = []
    for strategy in strategies:
        s = str(strategy).strip().upper()
        if s in MAIN_HYBRID_STRATEGIES and s not in normalized:
            normalized.append(s)
    return normalized


def _sample_sd(values: np.ndarray) -> float:
    arr = np.asarray(values, dtype=float)
    if arr.size <= 1:
        return 0.0
    return float(np.std(arr, ddof=1))


@app.get("/api/precomputed_fe")
def api_precomputed_fe():
    """
    Đọc dữ liệu FE đã tính trước từ outputs/compare_baselines_train
    Trả về thuật toán tốt nhất dựa trên 4 chỉ số: best_fe, mean_fe, std_fe, worst_fe
    """
    try:
        # Tìm thư mục kết quả mới nhất
        base_dir = "outputs/compare_baselines_train"
        if not os.path.exists(base_dir):
            return jsonify({"error": "Không tìm thấy thư mục kết quả"}), 404
        
        # Lấy thư mục con mới nhất
        subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
        if not subdirs:
            return jsonify({"error": "Không có kết quả nào"}), 404
        
        latest_dir = sorted(subdirs)[-1]
        summary_file = os.path.join(base_dir, latest_dir, "summary_sorted.csv")
        
        if not os.path.exists(summary_file):
            return jsonify({"error": "Không tìm thấy file summary_sorted.csv"}), 404
        
        # Đọc CSV
        import csv
        rows = []
        with open(summary_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({
                    "algo": row.get("algo", ""),
                    "best_fe": float(row.get("best_fe", 0)),
                    "mean_fe": float(row.get("mean_fe", 0)),
                    "std_fe": float(row.get("std_fe", 0)),
                    "worst_fe": float(row.get("worst_fe", 0)),
                })
        
        if not rows:
            return jsonify({"error": "File CSV rá»—ng"}), 404
        
        # Chọn thuật toán tốt nhất theo thứ tự ưu tiên:
        # 1. mean_fe cao nhất
        # 2. best_fe cao nhất
        # 3. std_fe thấp nhất
        # 4. worst_fe cao nhất
        best_row = max(rows, key=lambda r: (r["mean_fe"], r["best_fe"], -r["std_fe"], r["worst_fe"]))
        
        return jsonify({
            "rows": rows,
            "best_algo": best_row["algo"],
        })
        
    except Exception as e:
        logger.error(f"Lỗi khi đọc precomputed FE: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.get("/api/export_benchmark")
def api_export_benchmark():
    """
    Xuất dữ liệu benchmark để hiển thị:
    - Bảng 1: FE statistics từ summary_sorted.csv
    - Top 6 ảnh tốt nhất từ results_sorted.csv
    """
    try:
        # Tìm thư mục kết quả mới nhất
        base_dir = "outputs/compare_baselines_train"
        if not os.path.exists(base_dir):
            return jsonify({"error": "Không tìm thấy thư mục kết quả"}), 404
        
        subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
        if not subdirs:
            return jsonify({"error": "Không có kết quả nào"}), 404
        
        latest_dir = sorted(subdirs)[-1]
        result_dir = os.path.join(base_dir, latest_dir)
        
        # Đọc summary_sorted.csv cho Bảng 1
        summary_file = os.path.join(result_dir, "summary_sorted.csv")
        rows = []
        best_algo = ""
        
        if os.path.exists(summary_file):
            import csv
            with open(summary_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append({
                        "algo": row.get("algo", ""),
                        "best_fe": float(row.get("best_fe", 0)),
                        "mean_fe": float(row.get("mean_fe", 0)),
                        "std_fe": float(row.get("std_fe", 0)),
                        "worst_fe": float(row.get("worst_fe", 0)),
                    })
            
            if rows:
                best_row = max(rows, key=lambda r: (r["mean_fe"], r["best_fe"], -r["std_fe"], r["worst_fe"]))
                best_algo = best_row["algo"]
        
        # Đọc results_sorted.csv cho top 6 ảnh
        results_file = os.path.join(result_dir, "results_sorted.csv")
        top6 = []
        
        if os.path.exists(results_file):
            import csv
            with open(results_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    if count >= 6:
                        break
                    
                    image_name = row.get("image_name", "")
                    algo = row.get("algo", "")
                    fe_best = float(row.get("fe_best", 0))
                    
                    # Tìm đường dẫn ảnh
                    # Giả sử image_name là dạng "12003.jpg"
                    image_path = f"dataset/BDS500/images/train/{image_name}"
                    
                    top6.append({
                        "image_name": image_name,
                        "algo": algo,
                        "fe_best": fe_best,
                        "image_path": image_path,
                    })
                    count += 1
        
        return jsonify({
            "rows": rows,
            "best_algo": best_algo,
            "top6": top6,
        })
        
    except Exception as e:
        logger.error(f"Lá»—i khi export benchmark: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.get("/api/image")
def api_image():
    """
    Trả về ảnh dạng base64
    Cho phép đọc trong dataset/BDS500/images/**, dataset/Chest Xray/** và outputs/runs/**
    """
    try:
        path = request.args.get("path", "")
        path = path.replace("\\", "/")
        logger.info(f"API /api/image called with path: {path}")
        
        # Kiểm tra path traversal
        if ".." in path or path.startswith("/"):
            logger.warning(f"Invalid path (traversal): {path}")
            return jsonify({"error": "Invalid path"}), 400
        
        # Chỉ cho phép đọc trong dataset/BDS500/images, dataset/Chest Xray hoặc outputs/runs
        if not (
            path.startswith("dataset/BDS500/images/")
            or path.startswith("dataset/Chest Xray/")
            or path.startswith("outputs/runs/")
        ):
            logger.warning(f"Path not allowed: {path}")
            return jsonify({"error": "Path not allowed"}), 403
        
        if not os.path.exists(path):
            logger.warning(f"File not found: {path}")
            return jsonify({"error": "File not found"}), 404
        
        logger.info(f"Reading image file: {path}")
        # Đọc và encode base64
        with open(path, "rb") as f:
            img_data = f.read()
            b64 = base64.b64encode(img_data).decode("utf-8")
        
        # Xác định mime type
        ext = os.path.splitext(path)[1].lower()
        mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
        
        logger.info(f"Successfully loaded image: {path}, size: {len(img_data)} bytes")
        return jsonify({
            "data_url": f"data:{mime_type};base64,{b64}"
        })
        
    except Exception as e:
        logger.error(f"Lỗi khi đọc ảnh: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.post("/api/generate_histogram")
def api_generate_histogram():
    """
    Tạo histogram chart động với các thuật toán được chọn
    """
    try:
        data = request.get_json()
        run_name = data.get("run_name")
        selected_algos = data.get("algorithms", [])  # List of algorithm names
        
        if not run_name:
            return jsonify({"error": "Missing run_name"}), 400
        
        # Đọc dữ liệu từ run
        run_dir = os.path.join("outputs/runs", run_name)
        if not os.path.exists(run_dir):
            return jsonify({"error": "Run not found"}), 404
        
        # Đọc histogram.json
        histogram_path = os.path.join(run_dir, "histogram.json")
        if not os.path.exists(histogram_path):
            return jsonify({"error": "Histogram data not found"}), 404
        
        with open(histogram_path, 'r') as f:
            histogram_data = json.load(f)
        
        # Đọc config để lấy k
        config_path = os.path.join(run_dir, "config.yaml")
        k = 10
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                k = config.get("k", 10)
        
        # Đọc thresholds từ các thuật toán được chọn
        results = {}
        for algo_name in selected_algos:
            algo_dir = os.path.join(run_dir, "algorithms", algo_name)
            if not os.path.exists(algo_dir):
                algo_dir = os.path.join(run_dir, algo_name)
            result_json = os.path.join(algo_dir, "result.json")
            best_json = os.path.join(algo_dir, "best.json")
            source_file = result_json if os.path.exists(result_json) else best_json

            if os.path.exists(source_file):
                with open(source_file, 'r', encoding='utf-8') as f:
                    best_data = json.load(f)
                    results[algo_name] = {
                        "thresholds": best_data.get("thresholds", [])
                    }
        
        # Tạo histogram chart
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from io import BytesIO
        
        bins = histogram_data.get("bins", [])
        counts = histogram_data.get("counts", [])
        
        if not bins or not counts:
            return jsonify({"error": "Histogram data empty"}), 400
        
        # Color map
        color_map = {
            'GWO': '#2563eb',
            'WOA': '#7c3aed',
            'PSO': '#dc2626',
            'OTSU': '#f59e0b',
            'HYBRID-PA5': '#16a34a',
            'HYBRID-PA6': '#0f766e',
            'HYBRID-PA1': '#38b2ac',
            'HYBRID-PA2': '#ed64a6',
            'HYBRID-PA3': '#ecc94b',
            'HYBRID-PA4': '#667eea',
        }
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot histogram bars
        ax.bar(bins, counts, width=1.0, color=(0.388, 0.4, 0.945, 0.5), 
               edgecolor=(0.388, 0.4, 0.945, 1.0), linewidth=0.5, label='Tần suất')
        
        # Plot threshold lines for selected algorithms only
        for algo_name, result in results.items():
            thresholds = result.get("thresholds", [])
            color = color_map.get(algo_name, '#718096')
            
            for threshold in thresholds:
                ax.axvline(x=threshold, color=color, linewidth=2, label=algo_name, alpha=0.8)
        
        # Remove duplicate labels
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='upper right', fontsize=10)
        
        # Labels and title
        ax.set_xlabel('Cường độ điểm ảnh (0-255)', fontsize=12)
        ax.set_ylabel('Tần suất', fontsize=12)
        ax.set_title(f'Phân tích Histogram & Ngưỡng (K = {k})', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Save to BytesIO
        buf = BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        
        # Encode to base64
        img_b64 = base64.b64encode(buf.read()).decode('utf-8')
        data_url = f"data:image/png;base64,{img_b64}"
        
        return jsonify({"data_url": data_url})
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo histogram: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


def _analyze_threshold_regions(gray: np.ndarray, thresholds: list) -> dict:
    """
    Phân tích tỷ lệ pixel trong mỗi vùng ngưỡng
    
    Args:
        gray: Ảnh grayscale
        thresholds: Danh sách ngưỡng đã sắp xếp
    
    Returns:
        Dict chứa phân tích cho mỗi vùng
    """
    hist = np.bincount(gray.ravel(), minlength=256)
    total_pixels = hist.sum()
    
    # Thêm biên 0 và 255
    t = [0] + sorted(thresholds) + [255]
    k = len(thresholds)
    
    regions = []
    for i in range(k + 1):
        start = t[i]
        end = t[i + 1]
        
        # Tính số pixel trong vùng
        if i == 0:
            # Vùng 0: [0 .. t[0]]
            count = hist[0:start+1].sum()
        elif i == k:
            # Vùng cuối: [t[k-1]+1 .. 255]
            count = hist[start+1:256].sum()
        else:
            # Vùng giữa: [t[i-1]+1 .. t[i]]
            count = hist[start+1:end+1].sum()
        
        ratio = (count / total_pixels * 100) if total_pixels > 0 else 0
        
        regions.append({
            "region": i,
            "range": f"[{start+1 if i > 0 else 0}, {end}]",
            "count": int(count),
            "ratio": round(float(ratio), 2),
            "is_small": bool(ratio < 1.0),  # Convert to Python bool for JSON serialization
        })
    
    return {
        "regions": regions,
        "total_pixels": int(total_pixels),
        "k": k,
    }


def _img_to_data_url_gray(img_u8: np.ndarray) -> str:
    if Image is None:
        raise RuntimeError("Thiếu Pillow (PIL) để encode ảnh base64.")
    im = Image.fromarray(np.asarray(img_u8, dtype=np.uint8))
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


def _format_algo_params_for_log(
    algo: str,
    *,
    n_agents: int,
    n_iters: int,
    seed: int | None = None,
    strategy: str | None = None,
    woa_b: float | None = None,
    share_interval: int | None = None,
) -> str:
    algo_u = str(algo).upper()
    if algo_u == "GWO":
        return f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed}"
    if algo_u == "WOA":
        return f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed}, woa_b={woa_b}"
    if algo_u == "PSO":
        return f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed}"
    if algo_u == "OTSU":
        return "Tham số: Otsu là deterministic (không dùng n_agents, n_iters, seed)"
    if algo_u == "HYBRID":
        strategy_u = str(strategy).upper()
        if strategy_u == "PA5":
            return (
                f"Tham số: n_agents={n_agents}, n_iters={n_iters}, strategy={strategy_u}, "
                f"woa_b={woa_b}, share_interval={share_interval}"
            )
        if strategy_u == "PA6":
            return (
                f"Tham số: n_agents={n_agents}, n_iters={n_iters}, strategy={strategy_u}, "
                f"woa_b={woa_b}, stagnation_limit=10, recovery_rounds=3, switch_threshold=1.0"
            )
        return f"Tham số: n_agents={n_agents}, n_iters={n_iters}, strategy={strategy_u}, woa_b={woa_b}"
    return f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed}"


def _history_to_best_series(history) -> list[float]:
    series: list[float] = []
    if isinstance(history, list):
        for it in history:
            if isinstance(it, dict) and "best_f" in it:
                series.append(float(it["best_f"]))
    return series


def _safe_run_token(value: str) -> str:
    text = str(value or "uploaded")
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text)[:80] or "uploaded"


def _cxr_asset_url(path: str | Path) -> str:
    rel = Path(path).as_posix()
    return f"/api/image?path={rel}"


def _read_uploaded_gray(file_storage) -> np.ndarray:
    data = np.frombuffer(file_storage.read(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("Không đọc được file ảnh upload")
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def _resize_binary_mask(mask: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    resized = cv2.resize((mask > 0).astype(np.uint8) * 255, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return (resized > 0).astype(np.uint8) * 255


def _save_cxr_history(
    *,
    run_dir: str,
    run_name: str,
    case_id: str,
    image_path: str,
    mask_path: str | None,
    k: int,
    seed: int,
    n_agents: int,
    n_iters: int,
    gray_original: np.ndarray,
    gray_preprocessed: np.ndarray,
    raw_mask: np.ndarray | None,
    final_mask: np.ndarray,
    overlay_gray: np.ndarray,
    gt_mask: np.ndarray | None,
    thresholds: list[int],
    fe: float,
    metrics: dict,
    qc_info: dict,
    convergence: dict,
    runtime: float,
) -> dict:
    os.makedirs(run_dir, exist_ok=True)
    created_at = datetime.now().isoformat()

    paths = {
        "gray": os.path.join(run_dir, "gray.png"),
        "preprocessed": os.path.join(run_dir, "preprocessed.png"),
        "mask": os.path.join(run_dir, "mask.png"),
        "overlay": os.path.join(run_dir, "overlay.png"),
        "convergence": os.path.join(run_dir, "convergence.json"),
        "thresholds": os.path.join(run_dir, "thresholds.json"),
        "metrics": os.path.join(run_dir, "metrics.json"),
    }
    save_gray_png(paths["gray"], gray_original)
    save_gray_png(paths["preprocessed"], gray_preprocessed)
    if raw_mask is not None:
        raw_mask_path = os.path.join(run_dir, "raw_pa5_mask.png")
        raw_overlay_path = os.path.join(run_dir, "raw_pa5_overlay.png")
        save_mask_png(raw_mask_path, raw_mask)
        save_overlay_png(raw_overlay_path, overlay_gray, raw_mask)
        paths["raw_mask"] = raw_mask_path
        paths["raw_overlay"] = raw_overlay_path
    save_mask_png(paths["mask"], final_mask)
    save_overlay_png(paths["overlay"], overlay_gray, final_mask)
    if gt_mask is not None:
        gt_path = os.path.join(run_dir, "gt_mask.png")
        gt_overlay_path = os.path.join(run_dir, "gt_overlay.png")
        save_mask_png(gt_path, gt_mask)
        save_overlay_png(gt_overlay_path, overlay_gray, gt_mask)
        paths["gt_mask"] = gt_path
        paths["gt_overlay"] = gt_overlay_path

    with open(paths["convergence"], "w", encoding="utf-8") as f:
        json.dump(convergence, f, indent=2, ensure_ascii=False)
    with open(paths["thresholds"], "w", encoding="utf-8") as f:
        json.dump({"thresholds": thresholds}, f, indent=2, ensure_ascii=False)
    with open(paths["metrics"], "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    config = {
        "mode": "cxr_demo",
        "case_id": case_id,
        "image_path": image_path,
        "mask_path": mask_path,
        "dataset_root": DEFAULT_CXR_ROOT.as_posix(),
        "k": k,
        "seed": seed,
        "n_agents": n_agents,
        "n_iters": n_iters,
        "share_interval": 10,
        "algorithm_main": "PA5",
        "objective_name": "FE",
        "created_at": created_at,
    }
    with open(os.path.join(run_dir, "config.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    summary = {
        "run_name": run_name,
        "mode": "cxr_demo",
        "case_id": case_id,
        "created_at": created_at,
        "algorithm_main": "PA5",
        "thresholds": thresholds,
        "fe": fe,
        "dsc": metrics.get("dsc"),
        "iou": metrics.get("iou"),
        "psnr": metrics.get("psnr"),
        "ssim": metrics.get("ssim"),
        "time": runtime,
        "qc_info": qc_info,
    }
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return paths


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
    benchmark_data: list = None,
    histogram_data: dict = None,
) -> None:
    os.makedirs(run_dir, exist_ok=True)

    created_at = params.get("created_at") or datetime.now().isoformat()
    image_path = params.get("image_path", "")
    image_id = params.get("image_id") or os.path.splitext(os.path.basename(image_name))[0] or "uploaded"
    selected_algorithms = list(results.keys())
    algorithms_root = os.path.join(run_dir, "algorithms")
    os.makedirs(algorithms_root, exist_ok=True)

    if Image is not None:
        Image.fromarray(gray).save(os.path.join(run_dir, "gray.png"))

    config = {
        "mode": "single",
        "image_id": image_id,
        "image_name": image_name,
        "image_path": image_path,
        "k": params.get("k", 10),
        "seed": params.get("seed"),
        "n_agents": params.get("n_agents", 30),
        "n_iters": params.get("n_iters", 80),
        "selected_algorithms": selected_algorithms,
        "objective_name": params.get("objective_name", "FE thuần"),
        "penalty_mode": params.get("penalty_mode"),
        "share_interval": params.get("share_interval", SHARE_INTERVAL_FIXED),
        "created_at": created_at,
        "woa_b": params.get("woa_b", 1.0),
        "use_penalties": params.get("use_penalties", False),
    }
    with open(os.path.join(run_dir, "config.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    ranking = _build_single_ranking(results)
    algorithms_summary: dict[str, dict] = {}

    for algo_name, result in results.items():
        algo_dir = os.path.join(algorithms_root, algo_name)
        os.makedirs(algo_dir, exist_ok=True)

        thresholds = [int(v) for v in result.get("thresholds", [])]
        metrics = result.get("metrics", {}) or {}
        best_series = result.get("best_series", []) or []

        seg_path = os.path.join(algo_dir, "segmented.png")
        if "seg_data_url" in result and Image is not None:
            _save_data_url_png(result["seg_data_url"], seg_path)

        overlay_path = os.path.join(algo_dir, "overlay.png")
        if Image is not None:
            overlay_img = _make_boundary_overlay(gray, thresholds)
            Image.fromarray(overlay_img).save(overlay_path)

        histogram_path = os.path.join(algo_dir, "histogram.png")
        if histogram_data:
            try:
                _save_algo_histogram_chart(histogram_path, histogram_data, thresholds, algo_name, int(params.get("k", 10)))
            except Exception as e:
                logger.warning(f"Không thể tạo histogram cho {algo_name}: {e}")

        result_json = {
            "algorithm": algo_name,
            "fe": float(-result.get("best_f", 0.0)),
            "entropy": float(-result.get("best_f", 0.0)),
            "boundary_dsc": metrics.get("boundary_dsc"),
            "psnr": metrics.get("psnr"),
            "ssim": metrics.get("ssim"),
            "time": result.get("time", 0.0),
            "thresholds": thresholds,
            "best_f": result.get("best_f", 0.0),
            "convergence_iterations": int(convergence_iteration([{"best_f": v} for v in best_series])) if best_series else None,
            "objective_name": params.get("objective_name", "FE thuần"),
            "penalty_mode": params.get("penalty_mode"),
            "history_length": len(best_series),
            "paths": {
                "segmented": os.path.relpath(seg_path).replace("\\", "/") if os.path.exists(seg_path) else None,
                "overlay": os.path.relpath(overlay_path).replace("\\", "/") if os.path.exists(overlay_path) else None,
                "histogram": os.path.relpath(histogram_path).replace("\\", "/") if os.path.exists(histogram_path) else None,
            },
            "metrics": metrics,
        }
        with open(os.path.join(algo_dir, "result.json"), "w", encoding="utf-8") as f:
            json.dump(result_json, f, indent=2, ensure_ascii=False)
        with open(os.path.join(algo_dir, "best.json"), "w", encoding="utf-8") as f:
            json.dump(result_json, f, indent=2, ensure_ascii=False)

        with open(os.path.join(algo_dir, "history.jsonl"), "w", encoding="utf-8") as f:
            for i, best_f in enumerate(best_series):
                f.write(json.dumps({"iter": i, "best_f": best_f}, ensure_ascii=False) + "\n")

        algorithms_summary[algo_name] = {
            "algorithm": algo_name,
            "fe": float(-result.get("best_f", 0.0)),
            "entropy": float(-result.get("best_f", 0.0)),
            "boundary_dsc": metrics.get("boundary_dsc"),
            "psnr": metrics.get("psnr"),
            "ssim": metrics.get("ssim"),
            "time": result.get("time", 0.0),
            "thresholds": thresholds,
            "history_length": len(best_series),
            "paths": result_json["paths"],
        }

    summary = {
        "run_name": os.path.basename(run_dir),
        "mode": "single",
        "image_id": image_id,
        "image_name": image_name,
        "created_at": created_at,
        "best_overall_algo": params.get("best_overall_algo", ""),
        "best_overall_f": params.get("best_overall_f", 0.0),
        "best_overall_entropy": float(-params.get("best_overall_f", 0.0)),
        "ranking": ranking,
        "algorithms_summary": algorithms_summary,
        "total_time": params.get("total_time", 0.0),
    }
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    if benchmark_data:
        with open(os.path.join(run_dir, "benchmark.json"), "w", encoding="utf-8") as f:
            json.dump(benchmark_data, f, indent=2, ensure_ascii=False)

    if histogram_data:
        with open(os.path.join(run_dir, "histogram.json"), "w", encoding="utf-8") as f:
            json.dump(histogram_data, f, indent=2, ensure_ascii=False)
        try:
            _save_histogram_chart(run_dir, histogram_data, results, params.get("k", 10))
        except Exception as e:
            logger.warning(f"Không thể tạo histogram chart: {e}")

    logger.info(f"✓ Đã lưu kết quả vào: {run_dir}")



def _save_histogram_chart(run_dir: str, histogram_data: dict, results: dict, k: int) -> None:
    """
    Tạo và lưu ảnh histogram chart với matplotlib
    
    Args:
        run_dir: Đường dẫn thư mục lưu kết quả
        histogram_data: Dict chứa bins và counts
        results: Dict chứa kết quả các thuật toán (để lấy thresholds)
        k: Số ngưỡng
    """
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        
        bins = histogram_data.get("bins", [])
        counts = histogram_data.get("counts", [])
        
        if not bins or not counts:
            logger.warning("Histogram data rỗng, bỏ qua việc tạo chart")
            return
        
        logger.info(f"Đang tạo histogram chart với {len(bins)} bins...")
        
        # Color map for algorithms
        color_map = {
            'GWO': '#2563eb',
            'WOA': '#7c3aed',
            'PSO': '#dc2626',
            'OTSU': '#f59e0b',
            'HYBRID-PA5': '#16a34a',
            'HYBRID-PA6': '#0f766e',
            'HYBRID-PA1': '#38b2ac',
            'HYBRID-PA2': '#ed64a6',
            'HYBRID-PA3': '#ecc94b',
            'HYBRID-PA4': '#667eea',
        }
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot histogram bars (dùng tuple RGBA thay vì string)
        ax.bar(bins, counts, width=1.0, color=(0.388, 0.4, 0.945, 0.5), 
               edgecolor=(0.388, 0.4, 0.945, 1.0), linewidth=0.5, label='Tần suất')
        
        # Plot threshold lines for each algorithm
        max_count = max(counts) if counts else 1
        for algo_name, result in results.items():
            thresholds = result.get("thresholds", [])
            color = color_map.get(algo_name, '#718096')
            
            for threshold in thresholds:
                ax.axvline(x=threshold, color=color, linewidth=2, label=algo_name, alpha=0.8)
        
        # Remove duplicate labels in legend
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='upper right', fontsize=10)
        
        # Set labels and title
        ax.set_xlabel('Cường độ điểm ảnh (0-255)', fontsize=12)
        ax.set_ylabel('Tần suất', fontsize=12)
        ax.set_title(f'Phân tích Histogram & Ngưỡng (K = {k})', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Save figure
        output_path = os.path.join(run_dir, "histogram_chart.png")
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"✓ Đã lưu histogram chart: {output_path}")
        
    except ImportError as e:
        logger.warning(f"Matplotlib không được cài đặt: {e}")
    except Exception as e:
        logger.error(f"Lỗi khi tạo histogram chart: {e}", exc_info=True)


def _slugify_run_part(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(value).strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "unknown"


def _run_name_from_mode(mode: str, image_id: str, k: int, n_seeds: int | None = None) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_part = _slugify_run_part(image_id)
    if mode == "single_image_multi_seed":
        return f"{timestamp}__multiseed__{image_part}__k{k}__{int(n_seeds or 0)}seeds"
    return f"{timestamp}__single__{image_part}__k{k}"


def _create_run_dir(mode: str, image_id: str, k: int, n_seeds: int | None = None) -> str:
    run_name = _run_name_from_mode(mode, image_id, k, n_seeds=n_seeds)
    run_dir = os.path.join("outputs", "runs", run_name)
    counter = 2
    while os.path.exists(run_dir):
        alt_name = f"{run_name}__r{counter}"
        run_dir = os.path.join("outputs", "runs", alt_name)
        counter += 1
    return run_dir


def _make_boundary_overlay(gray: np.ndarray, thresholds: list[int] | np.ndarray) -> np.ndarray:
    gray_u8 = np.asarray(gray, dtype=np.uint8)
    seg = apply_thresholds(gray_u8, thresholds)
    boundary = seg_to_boundary_mask(seg)
    rgb = np.stack([gray_u8, gray_u8, gray_u8], axis=-1)
    rgb[boundary > 0] = np.array([255, 48, 48], dtype=np.uint8)
    return rgb


def _save_data_url_png(data_url: str, output_path: str) -> None:
    if not data_url.startswith("data:image/png;base64,"):
        raise ValueError("Unsupported image data URL")
    b64_data = data_url.split(",", 1)[1]
    img_data = base64.b64decode(b64_data)
    seg_img = Image.open(BytesIO(img_data))
    seg_img.save(output_path)


def _save_algo_histogram_chart(output_path: str, histogram_data: dict, thresholds: list[int], algo_name: str, k: int) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    bins = histogram_data.get("bins", [])
    counts = histogram_data.get("counts", [])
    if not bins or not counts:
        return

    color_map = {
        'GWO': '#2563eb',
        'WOA': '#7c3aed',
        'PSO': '#dc2626',
        'OTSU': '#f59e0b',
        'HYBRID-PA5': '#16a34a',
        'PA5': '#16a34a',
        'HYBRID-PA6': '#0f766e',
        'PA6': '#0f766e',
    }
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(bins, counts, width=1.0, color=(0.388, 0.4, 0.945, 0.35), edgecolor=(0.388, 0.4, 0.945, 0.8), linewidth=0.5)
    for threshold in thresholds:
        ax.axvline(x=threshold, color=color_map.get(algo_name, '#718096'), linewidth=2, alpha=0.85)
    ax.set_title(f"Histogram & Thresholds - {algo_name} (K={k})", fontsize=13, fontweight='bold')
    ax.set_xlabel("Gray level")
    ax.set_ylabel("Frequency")
    ax.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_path, format='png', dpi=140, bbox_inches='tight')
    plt.close(fig)


def _build_single_ranking(results: dict[str, dict]) -> list[dict]:
    ordered = sorted(results.items(), key=lambda item: float(item[1].get("best_f", float("inf"))))
    ranking = []
    for idx, (algo_name, result) in enumerate(ordered, start=1):
        metrics = result.get("metrics", {}) or {}
        ranking.append({
            "rank": idx,
            "algorithm": algo_name,
            "fe": float(-result.get("best_f", 0.0)),
            "boundary_dsc": metrics.get("boundary_dsc"),
            "psnr": metrics.get("psnr"),
            "ssim": metrics.get("ssim"),
            "time": result.get("time"),
        })
    return ranking


def _save_multi_seed_eval_run(
    run_dir: str,
    gray: np.ndarray,
    *,
    image_name: str,
    image_path: str,
    gt_path: str,
    k: int,
    seeds: list[int],
    n_agents: int,
    n_iters: int,
    woa_b: float,
    share_interval: int,
    objective_name: str,
    penalty_mode: str | None,
    algorithms: list[str],
    results: list[dict],
    summary_stats: dict,
    wilcoxon_rows: list[dict],
    total_time: float,
    detail_results_file: str,
    detail_summary_file: str,
    source_single_run_dir: str = "",
) -> None:
    os.makedirs(run_dir, exist_ok=True)

    created_at = datetime.now().isoformat()
    image_id = os.path.splitext(os.path.basename(image_name))[0]
    successful_rows = [row for row in results if "error" not in row]
    algorithms_root = os.path.join(run_dir, "algorithms")
    os.makedirs(algorithms_root, exist_ok=True)

    if Image is not None:
        Image.fromarray(gray).save(os.path.join(run_dir, "gray.png"))

    stochastic_algorithms = [algo for algo in algorithms if str(algo).upper() != "OTSU"]
    deterministic_baseline = None
    if "OTSU" in summary_stats:
        deterministic_baseline = {
            "algorithm": "OTSU",
            **summary_stats["OTSU"],
            "note": "SD = 0 (deterministic)",
        }

    ranking_primary = [
        {
            "rank": idx + 1,
            "algorithm": algo_name,
            "fe_mean": summary_stats[algo_name].get("fe_mean"),
            "fe_sd": summary_stats[algo_name].get("fe_sd"),
        }
        for idx, algo_name in enumerate(
            sorted(
                [algo for algo in stochastic_algorithms if algo in summary_stats],
                key=lambda name: (
                    -summary_stats[name].get("fe_mean", float("-inf")),
                    summary_stats[name].get("fe_sd", float("inf")),
                ),
            )
        )
    ]

    stochastic_summary = {}
    if ranking_primary:
        best_fe_mean_algo = ranking_primary[0]["algorithm"]
        best_fe_sd_algo = min(
            [algo for algo in stochastic_algorithms if algo in summary_stats],
            key=lambda name: summary_stats[name].get("fe_sd", float("inf")),
        )
        stochastic_summary = {
            "best_fe_mean": {
                "algorithm": best_fe_mean_algo,
                "value": summary_stats[best_fe_mean_algo].get("fe_mean"),
            },
            "lowest_fe_sd": {
                "algorithm": best_fe_sd_algo,
                "value": summary_stats[best_fe_sd_algo].get("fe_sd"),
            },
        }

    config = {
        "mode": "single_image_multi_seed",
        "image_id": image_id,
        "image_name": image_name,
        "image_path": image_path,
        "gt_path": gt_path,
        "k": k,
        "start_seed": min(seeds) if seeds else None,
        "seeds": seeds,
        "n_seeds": len(seeds),
        "n_agents": n_agents,
        "n_iters": n_iters,
        "selected_algorithms": algorithms,
        "objective_name": objective_name,
        "penalty_mode": penalty_mode,
        "share_interval": share_interval,
        "created_at": created_at,
        "woa_b": woa_b,
        "source_single_run_dir": source_single_run_dir,
    }
    with open(os.path.join(run_dir, "config.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    with open(os.path.join(run_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(successful_rows, f, indent=2, ensure_ascii=False)

    comparisons = []
    grouped_wilcoxon: dict[str, dict[str, dict]] = {}
    for row in wilcoxon_rows:
        challenger = row.get("challenger")
        metric = str(row.get("metric", "")).lower()
        if challenger == "OTSU":
            continue
        grouped_wilcoxon.setdefault(challenger, {})[metric] = row
    base_algorithm = wilcoxon_rows[0]["base"] if wilcoxon_rows else "PA5"
    for challenger, metrics in grouped_wilcoxon.items():
        comparisons.append({
            "vs": challenger,
            "boundary_dsc_delta_mean": metrics.get("boundary_dsc", {}).get("delta_mean"),
            "boundary_dsc_p": metrics.get("boundary_dsc", {}).get("pvalue"),
            "fe_delta_mean": metrics.get("fe", {}).get("delta_mean"),
            "fe_p": metrics.get("fe", {}).get("pvalue"),
            "psnr_delta_mean": metrics.get("psnr", {}).get("delta_mean"),
            "psnr_p": metrics.get("psnr", {}).get("pvalue"),
            "ssim_delta_mean": metrics.get("ssim", {}).get("delta_mean"),
            "ssim_p": metrics.get("ssim", {}).get("pvalue"),
        })
    wilcoxon_json = {"base_algorithm": base_algorithm, "comparisons": comparisons}
    with open(os.path.join(run_dir, "wilcoxon.json"), "w", encoding="utf-8") as f:
        json.dump(wilcoxon_json, f, indent=2, ensure_ascii=False)

    for algo_name in algorithms:
        algo_rows = [row for row in successful_rows if row.get("algorithm") == algo_name]
        if not algo_rows:
            continue
        algo_dir = os.path.join(algorithms_root, algo_name)
        os.makedirs(algo_dir, exist_ok=True)

        representative = max(
            algo_rows,
            key=lambda row: (
                row.get("fe", float("-inf")),
                row.get("boundary_dsc", float("-inf")),
                -row.get("time", float("inf")),
            ),
        )
        stat = summary_stats.get(algo_name, {})
        result_json = {
            "algorithm": algo_name,
            "mode": "single_image_multi_seed",
            "seed": representative.get("seed"),
            "fe": representative.get("fe"),
            "boundary_dsc": representative.get("boundary_dsc"),
            "psnr": representative.get("psnr"),
            "ssim": representative.get("ssim"),
            "time": representative.get("time"),
            "thresholds": representative.get("thresholds", []),
            "best_f": representative.get("best_f"),
            "objective_name": objective_name,
            "penalty_mode": penalty_mode,
            "summary_stat": stat,
        }
        with open(os.path.join(algo_dir, "result.json"), "w", encoding="utf-8") as f:
            json.dump(result_json, f, indent=2, ensure_ascii=False)
        with open(os.path.join(algo_dir, "best.json"), "w", encoding="utf-8") as f:
            json.dump(result_json, f, indent=2, ensure_ascii=False)
        with open(os.path.join(algo_dir, "per_seed.json"), "w", encoding="utf-8") as f:
            json.dump(sorted(algo_rows, key=lambda row: row.get("seed", 0)), f, indent=2, ensure_ascii=False)

        if Image is not None:
            seg = apply_thresholds(gray, representative.get("thresholds", []))
            Image.fromarray(seg).save(os.path.join(algo_dir, "segmented.png"))
            overlay = _make_boundary_overlay(gray, representative.get("thresholds", []))
            Image.fromarray(overlay).save(os.path.join(algo_dir, "overlay.png"))

    summary = {
        "run_name": os.path.basename(run_dir),
        "mode": "single_image_multi_seed",
        "image_id": image_id,
        "image_name": image_name,
        "created_at": created_at,
        "n_seeds": len(seeds),
        "total_time": total_time,
        "summary_statistics": summary_stats,
        "ranking_primary": ranking_primary,
        "stochastic_summary": stochastic_summary,
        "deterministic_baseline": deterministic_baseline,
        "detail_results_file": detail_results_file,
        "detail_summary_file": detail_summary_file,
        "wilcoxon_file": os.path.relpath(os.path.join(run_dir, "wilcoxon.json")).replace("\\", "/"),
        "base_algorithm": base_algorithm,
    }
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


def _select_top_benchmarks(all_results, top_k: int = 6, focus_algo: str = "HYBRID-PA5"):
    """Chọn top_k hàm benchmark để hiển thị.

    Tiêu chí (minimize best_f):
      - Nếu focus_algo tồn tại trong ít nhất 1 hàm: ưu tiên các hàm mà focus_algo có hạng (rank) cao,
        và nếu focus_algo thắng thì ưu tiên thắng rõ (margin = best_thứ_2 - best_thứ_1 lớn).
      - Nếu focus_algo không tồn tại: fallback theo best_f nhỏ nhất (thuật toán tốt nhất của từng hàm).

    Kết quả trả về là danh sách con của all_results (tối đa top_k phần tử).
    """
    import math

    # focus_algo có mặt ở ít nhất 1 hàm không?
    focus_present = any(
        (isinstance(bm, dict) and (not bm.get("error")) and isinstance(bm.get("results"), dict) and (focus_algo in bm["results"]))
        for bm in (all_results or [])
    )

    scored = []
    for bm in (all_results or []):
        if not isinstance(bm, dict) or bm.get("error"):
            continue
        results = bm.get("results")
        if not isinstance(results, dict) or not results:
            continue

        # gom best_f theo thuật toán
        vals = []  # (algo, best_f)
        for algo, res in results.items():
            if not isinstance(res, dict):
                continue
            v = res.get("best_f", None)
            if v is None:
                continue
            try:
                vals.append((str(algo), float(v)))
            except Exception:
                continue

        if not vals:
            continue

        vals_sorted = sorted(vals, key=lambda kv: kv[1])  # nhỏ hơn là tốt hơn
        best_algo, best_val = vals_sorted[0]
        second_val = vals_sorted[1][1] if len(vals_sorted) > 1 else math.inf

        if focus_present:
            algos_only = [a for a, _ in vals_sorted]
            if focus_algo in algos_only:
                focus_val = dict(vals_sorted)[focus_algo]
                rank = 1 + algos_only.index(focus_algo)
                # margin chỉ tính khi focus_algo là hạng 1
                margin = (second_val - best_val) if (best_algo == focus_algo and math.isfinite(second_val)) else 0.0
            else:
                focus_val = math.inf
                rank = 999
                margin = 0.0

            sort_key = (rank, -margin, focus_val, bm.get("fun", 0))
        else:
            margin = (second_val - best_val) if math.isfinite(second_val) else 0.0
            sort_key = (best_val, -margin, bm.get("fun", 0))

        scored.append((sort_key, bm))

    scored.sort(key=lambda x: x[0])
    return [bm for _, bm in scored[: max(0, int(top_k))]]


def _run_all_benchmarks(n_agents, n_iters, seed, woa_b, share_interval, 
                        run_gwo, run_woa, run_pso, run_otsu, run_hybrid, hybrid_strategies):
    """Chạy CỐ ĐỊNH 6 hàm benchmark: F1, F3, F8, F12, F13, F16 với dim cố định = 30"""
    if BENCHMARK_NAMES is None or benchmark_functions is None or set_bounds is None:
        logger.error("Không tìm thấy module benchmark")
        return {"error": "missing benchmark functions"}
    
    all_results = []
    dim = 30  # dim CỐ ĐỊNH = 30, không phụ thuộc vào n_agents
    
    # Chỉ chạy cố định 6 hàm: F1, F3, F8, F12, F13, F16
    selected_functions = [1, 3, 8, 12, 13, 16]  # Danh sách hàm cố định
    logger.info(f"Sẽ chạy CỐ ĐỊNH {len(selected_functions)} hàm benchmark: F{', F'.join(map(str, selected_functions))} với dim={dim}, n_agents={n_agents}")
    
    for fun_1 in selected_functions:
        fun_idx = fun_1 - 1  # Chuyển từ F1 (1-indexed) sang index (0-indexed)
        
        if fun_idx >= len(BENCHMARK_NAMES):
            logger.warning(f"Bỏ qua F{fun_1} - vượt quá số hàm có sẵn")
            continue
            
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
                del offset
                return seed
            
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
            
            if run_pso:
                logger.info(f"  → Chạy PSO cho F{fun_1}...")
                opt = _make_optimizer("PSO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(40), 
                                    strategy="PA1", woa_b=woa_b, share_interval=share_interval)
                _, best_f, history = opt.optimize(fitness_fn, dim=dim, lb=lb, ub=ub, repair_fn=None, init_pop=None)
                results["PSO"] = {"best_f": float(best_f), "series": _history_to_best_series(history)}
                logger.info(f"  → PSO hoàn thành: best_f={best_f:.6e}")
            
            if run_otsu:
                logger.info(f"  → Chạy OTSU cho F{fun_1}...")
                if dim <= 4:
                    logger.info("  → Benchmark OTSU không dùng trong mode benchmark function; bỏ qua để tránh OTSU giả.")
                    results["OTSU"] = {"status": "unsupported", "reason": "Benchmark functions do not provide image histograms for true multi-Otsu."}
                else:
                    results["OTSU"] = {"status": "unsupported", "reason": f"True multi-Otsu unsupported for k={dim}."}
            
            if run_hybrid:
                for strategy in hybrid_strategies:
                    strategy = strategy.strip().upper()
                    if not strategy:
                        continue
                    logger.info(f"  → Chạy HYBRID-{strategy} cho F{fun_1}...")
                    opt = _make_optimizer("HYBRID", n_agents=n_agents, n_iters=n_iters, 
                                        seed=seed_for(_hybrid_seed_offset(strategy)),
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
    
    logger.info(f"Hoàn thành {len(all_results)}/{len(selected_functions)} hàm benchmark")
    
    # Không cần lọc top nữa vì đã chỉ chạy F1-F6
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
        del offset
        return seed
    
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
                hybrid_seed_offset = _hybrid_seed_offset(strategy)
                opt = _make_optimizer("HYBRID", n_agents=n_agents, n_iters=n_iters, 
                                    seed=seed_for(hybrid_seed_offset),
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
        # Chỉ hiển thị 6 hàm cố định: F1, F3, F8, F12, F13, F16
        selected_functions = [1, 3, 8, 12, 13, 16]
        f_names = [{"id": fun_id, "name": BENCHMARK_NAMES[fun_id - 1]} 
                   for fun_id in selected_functions 
                   if fun_id - 1 < len(BENCHMARK_NAMES)]
    return render_template("index.html", k_fixed=K_FIXED, benchmark_list=f_names)


@app.get("/api/bds500/list")
def api_bds500_list():
    """Lấy danh sách ảnh từ BDS500 dataset theo split"""
    import os
    import random
    
    split = request.args.get("split", "test")  # train, val, test
    limit = int(request.args.get("limit", "0"))  # 0 = không giới hạn số ảnh trả về
    random_select = request.args.get("random", "false") == "true"
    
    try:
        images_dir = os.path.join(BDS500_IMAGES_ROOT, split)
        gt_dir = os.path.join(BDS500_GT_ROOT, split)
        
        if not os.path.exists(images_dir):
            return jsonify({"error": f"Không tìm thấy thư mục: {images_dir}"}), 404
        
        # Lấy danh sách ảnh có ground truth
        pairs = build_pairs(images_dir, gt_dir)
        
        if random_select and limit > 0 and len(pairs) > limit:
            pairs = random.sample(pairs, limit)
        elif limit > 0 and len(pairs) > limit:
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


@app.get("/api/cxr/cases")
def api_cxr_cases():
    try:
        source = request.args.get("source", "all")
        root = request.args.get("root", DEFAULT_CXR_ROOT.as_posix())
        scan_cxr_dataset(root)
        cases = list_cxr_cases(source)
        paths = get_cxr_dataset_paths()
        return jsonify({**paths, "source": source, "total": len(cases), "cases": cases})
    except Exception as e:
        logger.error(f"Lỗi khi đọc dataset CXR: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.post("/api/cxr/segment")
def api_cxr_segment():
    try:
        preset = request.form.get("preset", "FAST").upper()
        if preset == "FULL":
            defaults = {"k": 8, "seed": 42, "n_agents": 20, "n_iters": 60}
        else:
            defaults = {"k": 6, "seed": 42, "n_agents": 10, "n_iters": 25}

        k = int(request.form.get("k") or defaults["k"])
        seed = int(request.form.get("seed") or defaults["seed"])
        n_agents = int(request.form.get("n_agents") or defaults["n_agents"])
        n_iters = int(request.form.get("n_iters") or defaults["n_iters"])

        case_id = request.form.get("case_id", "").strip()
        image_path = ""
        mask_path = None
        gt_mask = None

        if case_id:
            scan_cxr_dataset(DEFAULT_CXR_ROOT)
            case = load_cxr_case(case_id)
            image_path = case["image_path"]
            mask_path = case.get("mask_path")
            raw_img = load_cxr_image(image_path)
            if mask_path and os.path.exists(mask_path):
                gt_raw = load_cxr_image(mask_path)
                gt_mask = (gt_raw > 0).astype(np.uint8) * 255
        elif "image" in request.files and request.files["image"].filename:
            upload = request.files["image"]
            raw_img = _read_uploaded_gray(upload)
            case_id = Path(upload.filename).stem or "uploaded"
            image_path = f"uploaded:{upload.filename}"
        else:
            return jsonify({"error": "Cần case_id hoặc image file"}), 400

        if "gt_mask" in request.files and request.files["gt_mask"].filename:
            gt_mask = _read_uploaded_gray(request.files["gt_mask"])
            mask_path = f"uploaded:{request.files['gt_mask'].filename}"

        prep = preprocess_cxr(raw_img)
        gray_original = prep["gray_original"]
        gray_preprocessed = prep["gray_preprocessed"]
        if gt_mask is not None:
            gt_mask = _resize_binary_mask(gt_mask, gray_original.shape)

        pa5_result = run_pa5_cxr(
            gray_preprocessed,
            k=k,
            seed=seed,
            n_agents=n_agents,
            n_iters=n_iters,
            objective="cxr_fe_shape",
        )
        lung_result = segmented_to_lung_mask(
            pa5_result["segmented"],
            gray_preprocessed,
            pa5_result["thresholds"],
            allow_fallback=False,
        )
        raw_pa5_mask = lung_result["candidate_mask"]
        raw_metrics = compute_cxr_metrics(
            gray_original,
            raw_pa5_mask,
            gt_mask,
            fe=pa5_result["fe"],
            runtime=pa5_result["runtime"],
            qc_info={},
        )
        post = postprocess_lung_mask(lung_result["candidate_mask"])
        final_mask = post["final_mask"]
        qc_info = {
            **post["qc_info"],
            "region_scores": lung_result["region_scores"][:20],
            "mask_source": lung_result.get("selected_source"),
            "candidate_quality": lung_result.get("candidate_quality"),
            "fallback_quality": lung_result.get("fallback_quality"),
            "fallback_info": lung_result.get("fallback_info"),
            "threshold_union_info": lung_result.get("threshold_union_info"),
            "objective_name": pa5_result.get("objective_name"),
            "objective_score": pa5_result.get("objective_score"),
            "shape_score": pa5_result.get("shape_score"),
            "shape_penalty": pa5_result.get("shape_penalty"),
        }
        metrics = compute_cxr_metrics(
            gray_original,
            final_mask,
            gt_mask,
            fe=pa5_result["fe"],
            runtime=pa5_result["runtime"],
            qc_info=qc_info,
        )
        convergence = build_convergence_payload(pa5_result["history"])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = f"{timestamp}__cxr_demo__{_safe_run_token(case_id)}__k{k}"
        run_dir = os.path.join("outputs", "runs", run_name)
        paths = _save_cxr_history(
            run_dir=run_dir,
            run_name=run_name,
            case_id=case_id,
            image_path=image_path,
            mask_path=mask_path,
            k=k,
            seed=seed,
            n_agents=n_agents,
            n_iters=n_iters,
            gray_original=gray_original,
            gray_preprocessed=gray_preprocessed,
            raw_mask=raw_pa5_mask,
            final_mask=final_mask,
            overlay_gray=gray_original,
            gt_mask=gt_mask,
            thresholds=pa5_result["thresholds"],
            fe=pa5_result["fe"],
            metrics=metrics,
            qc_info=qc_info,
            convergence=convergence,
            runtime=pa5_result["runtime"],
        )

        return jsonify({
            "success": True,
            "run_name": run_name,
            "thresholds": pa5_result["thresholds"],
            "fe": pa5_result["fe"],
            "objective_score": pa5_result.get("objective_score"),
            "shape_score": pa5_result.get("shape_score"),
            "shape_penalty": pa5_result.get("shape_penalty"),
            "raw_dsc": raw_metrics.get("dsc"),
            "raw_iou": raw_metrics.get("iou"),
            "dsc": metrics.get("dsc"),
            "iou": metrics.get("iou"),
            "psnr": metrics.get("psnr"),
            "ssim": metrics.get("ssim"),
            "time": pa5_result["runtime"],
            "qc_info": qc_info,
            "original_url": _cxr_asset_url(paths["gray"]),
            "preprocessed_url": _cxr_asset_url(paths["preprocessed"]),
            "raw_mask_url": _cxr_asset_url(paths["raw_mask"]) if paths.get("raw_mask") else None,
            "raw_overlay_url": _cxr_asset_url(paths["raw_overlay"]) if paths.get("raw_overlay") else None,
            "mask_url": _cxr_asset_url(paths["mask"]),
            "overlay_url": _cxr_asset_url(paths["overlay"]),
            "gt_mask_url": _cxr_asset_url(paths["gt_mask"]) if paths.get("gt_mask") else None,
            "gt_overlay_url": _cxr_asset_url(paths["gt_overlay"]) if paths.get("gt_overlay") else None,
            "convergence": convergence,
            "history_run_dir": run_dir,
            "config": {
                "preset": preset,
                "k": k,
                "seed": seed,
                "n_agents": n_agents,
                "n_iters": n_iters,
                "share_interval": 10,
                "algorithm_main": "PA5",
                "objective_name": pa5_result.get("objective_name", "CXR-FE-shape"),
                "dataset_root": DEFAULT_CXR_ROOT.as_posix(),
            },
        })
    except Exception as e:
        logger.error(f"Lỗi CXR segment: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.get("/api/cxr/history/list")
def api_cxr_history_list():
    return api_history_list()


@app.get("/api/cxr/history/detail/<run_name>")
def api_cxr_history_detail(run_name):
    return api_history_detail(run_name)


@app.post("/api/segment_bds500")
def api_segment_bds500():
    """Phân đoạn ảnh từ BDS500 dataset và tính Boundary DSC score"""
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
        
        # Lấy các tham số khác
        n_agents = int(request.form.get("n_agents", "30"))
        n_iters = int(request.form.get("n_iters", "80"))
        
        seed_raw = request.form.get("seed", "42").strip()
        seed = None if seed_raw == "" else int(seed_raw)
        
        # CỐ ĐỊNH woa_b = 1.0
        woa_b = 1.0
        
        share_interval = SHARE_INTERVAL_FIXED
        k = int(request.form.get("k", str(K_FIXED)))
        
        run_gwo = request.form.get("run_gwo", "0") == "1"
        run_woa = request.form.get("run_woa", "0") == "1"
        run_pso = request.form.get("run_pso", "0") == "1"
        run_otsu = False
        run_hybrid = request.form.get("run_hybrid", "0") == "1"
        
        hybrid_strategies_raw = request.form.get("hybrid_strategies", "PA5").strip()
        hybrid_strategies = _normalize_main_hybrid_strategies(
            [s.strip().upper() for s in hybrid_strategies_raw.split(",") if s.strip()]
        ) if run_hybrid else []
        run_hybrid = run_hybrid and bool(hybrid_strategies)
        
        gt_thr = float(request.form.get("gt_thr", "0.5"))
        gt_fuse = request.form.get("gt_fuse", "max")
        
        logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed}")
        logger.info(f"Thuật toán: GWO={run_gwo}, WOA={run_woa}, PSO={run_pso}, OTSU={run_otsu}, HYBRID={run_hybrid}")
        logger.info(f"Hybrid strategies: {hybrid_strategies}")
        logger.info(f"GT params: thr={gt_thr}, fuse={gt_fuse}")
        logger.info(f"CẤU HÌNH: seed={seed}, share_interval={share_interval}, HYBRID={hybrid_strategies}")
        
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
        lb, ub = 0, 255
        repair_fn, fitness_fn, use_penalties, penalty_mode, objective_label = _build_threshold_objective(
            gray, k, lb, ub
        )

        logger.info(f"Main branch dùng objective: {objective_label}")

        results = {}
        best_overall = None
        best_overall_f = float('inf')
        best_overall_algo = ""

        def seed_for(offset: int) -> int | None:
            del offset
            return seed

        base_init_pop = _base_init_population(seed, n_agents, k, lb, ub)

        def init_pop_for(_: str) -> np.ndarray | None:
            return None if base_init_pop is None else base_init_pop.copy()

        # Chạy các thuật toán
        if run_gwo:
            logger.info("-" * 60)
            logger.info("CHẠY THUẬT TOÁN GWO")
            logger.info("-" * 60)
            logger.info(_format_algo_params_for_log("GWO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(10)))
            algo_start = time.time()
            opt = _make_optimizer("GWO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(10), 
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=init_pop_for("GWO")
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
                
                # Tính Boundary DSC nếu có ground truth
                if gt_boundary_mask is not None:
                    pred_boundary = seg_to_boundary_mask(seg)
                    metrics["boundary_dsc"] = dice_boundary(gt_boundary_mask, pred_boundary)
                    logger.info(
                        f"GWO metrics: PSNR={metrics['psnr']:.2f}, "
                        f"SSIM={metrics['ssim']:.4f}, Boundary DSC={metrics['boundary_dsc']:.4f}"
                    )
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
                "region_analysis": _analyze_threshold_regions(gray, best_x),
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
            logger.info(_format_algo_params_for_log("WOA", n_agents=n_agents, n_iters=n_iters, seed=seed_for(20), woa_b=woa_b))
            algo_start = time.time()
            opt = _make_optimizer("WOA", n_agents=n_agents, n_iters=n_iters, seed=seed_for(20),
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=init_pop_for("WOA")
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
                    metrics["boundary_dsc"] = dice_boundary(gt_boundary_mask, pred_boundary)
                    logger.info(
                        f"WOA metrics: PSNR={metrics['psnr']:.2f}, "
                        f"SSIM={metrics['ssim']:.4f}, Boundary DSC={metrics['boundary_dsc']:.4f}"
                    )
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
                "region_analysis": _analyze_threshold_regions(gray, best_x),
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
            logger.info(_format_algo_params_for_log("PSO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(25)))
            algo_start = time.time()
            opt = _make_optimizer("PSO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(25),
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=init_pop_for("PSO")
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
                    metrics["boundary_dsc"] = dice_boundary(gt_boundary_mask, pred_boundary)
                    logger.info(
                        f"PSO metrics: PSNR={metrics['psnr']:.2f}, "
                        f"SSIM={metrics['ssim']:.4f}, Boundary DSC={metrics['boundary_dsc']:.4f}"
                    )
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
                "region_analysis": _analyze_threshold_regions(gray, best_x),
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
            logger.info(_format_algo_params_for_log("OTSU", n_agents=n_agents, n_iters=n_iters))
            logger.info(f"Image shape: {gray.shape}, k={k}")
            algo_start = time.time()
            otsu_variant = "multiotsu"
            
            try:
                best_x, best_f, history = OtsuMulti().optimize_with_image(
                    image=gray,
                    dim=k,
                    fitness_fn=fitness_fn,
                    repair_fn=repair_fn,
                )
                algo_time = time.time() - algo_start

                # Log optimization progress
                _log_optimization_progress("OTSU", history, n_agents, n_iters)
                best_x = repair_fn(best_x)
                seg = apply_thresholds(gray, best_x)
                
                metrics = {}
                try:
                    metrics["psnr"] = compute_psnr(gray, seg, data_range=255.0)
                    metrics["ssim"] = compute_ssim(gray, seg, data_range=255.0)
                    
                    if gt_boundary_mask is not None:
                        pred_boundary = seg_to_boundary_mask(seg)
                        metrics["boundary_dsc"] = dice_boundary(gt_boundary_mask, pred_boundary)
                        logger.info(
                            f"OTSU metrics: PSNR={metrics['psnr']:.2f}, "
                            f"SSIM={metrics['ssim']:.4f}, Boundary DSC={metrics['boundary_dsc']:.4f}"
                        )
                    else:
                        logger.info(f"OTSU metrics: PSNR={metrics['psnr']:.2f}, SSIM={metrics['ssim']:.4f}")
                except Exception as e:
                    logger.warning(f"Không thể tính metrics cho OTSU: {e}")
                
                results["OTSU"] = {
                    "thresholds": [int(v) for v in np.asarray(best_x).ravel().tolist()],
                    "best_f": float(best_f),
                    "time": algo_time,
                    "variant": otsu_variant,
                    "seg_data_url": _img_to_data_url_gray(seg),
                    "best_series": _history_to_best_series(history),
                    "metrics": metrics,
                    "region_analysis": _analyze_threshold_regions(gray, best_x),
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
                logger.info(
                    _format_algo_params_for_log(
                        "HYBRID",
                        n_agents=n_agents,
                        n_iters=n_iters,
                        strategy=strategy,
                        woa_b=woa_b,
                        share_interval=share_interval,
                    )
                )
                algo_start = time.time()
                hybrid_seed_offset = _hybrid_seed_offset(strategy)
                opt = _make_optimizer("HYBRID", n_agents=n_agents, n_iters=n_iters, 
                                    seed=seed_for(hybrid_seed_offset),
                                    strategy=strategy, woa_b=woa_b, share_interval=share_interval)
                best_x, best_f, history = opt.optimize(
                    fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                    repair_fn=repair_fn, init_pop=init_pop_for(f"HYBRID-{strategy}")
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
                        metrics["boundary_dsc"] = dice_boundary(gt_boundary_mask, pred_boundary)
                        logger.info(
                            f"{algo_name} metrics: PSNR={metrics['psnr']:.2f}, "
                            f"SSIM={metrics['ssim']:.4f}, Boundary DSC={metrics['boundary_dsc']:.4f}"
                        )
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
                    "region_analysis": _analyze_threshold_regions(gray, best_x),
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

        # Tính histogram cho ảnh gốc
        hist = np.bincount(gray.ravel(), minlength=256).astype(int).tolist()
        
        response_data = {
            "k": k,
            "config": {
                "k": k,
                "n_agents": n_agents,
                "n_iters": n_iters,
                "seed": seed,
                "woa_b": woa_b,
                "share_interval": share_interval,
                "use_penalties": use_penalties,
                "penalty_mode": penalty_mode,
                "algorithms": {
                    "GWO": run_gwo,
                    "WOA": run_woa,
                    "PSO": run_pso,
                    "OTSU": run_otsu,
                    "PA5": "PA5" in hybrid_strategies,
                    "PA6": "PA6" in hybrid_strategies,
                },
            },
            "gray_data_url": _img_to_data_url_gray(gray),
            "results": results,
            "best_overall_algo": best_overall_algo,
            "best_overall_f": float(best_overall_f),
            "segmentation_time": seg_time,
            "has_ground_truth": gt_boundary_mask is not None,
            "image_name": os.path.basename(image_path),
            "histogram": {
                "bins": list(range(256)),
                "counts": hist,
            }
        }

        # BẮT BUỘC chạy benchmark
        if BENCHMARK_NAMES is not None:
            logger.info("")
            logger.info("=" * 80)
            logger.info("BẮT ĐẦU CHẠY BENCHMARK (CỐ ĐỊNH 6 HÀM: F1, F3, F8, F12, F13, F16)")
            logger.info("=" * 80)
            benchmark_start = time.time()
            benchmark_results = _run_all_benchmarks(
                n_agents, n_iters, seed, woa_b, share_interval,
                run_gwo, run_woa, run_pso, run_otsu, run_hybrid, hybrid_strategies
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
            run_dir = _create_run_dir("single", "uploaded", k)

            params = {
                "k": k,
                "n_agents": n_agents,
                "n_iters": n_iters,
                "seed": seed,
                "woa_b": woa_b,
                "share_interval": share_interval,
                "use_penalties": use_penalties,
                "penalty_mode": penalty_mode,
                "objective_name": objective_label,
                "total_time": total_time,
                "best_overall_algo": best_overall_algo,
                "best_overall_f": best_overall_f,
                "image_id": "uploaded",
                "image_path": "",
            }
            
            # Lưu kèm benchmark data nếu có
            benchmark_to_save = response_data.get("benchmark", None)
            histogram_to_save = response_data.get("histogram", None)
            _save_run_results(
                run_dir,
                gray,
                results,
                params,
                image_name="uploaded",
                benchmark_data=benchmark_to_save,
                histogram_data=histogram_to_save,
            )
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
        
        seed_raw = request.form.get("seed", "42").strip()
        seed = None if seed_raw == "" else int(seed_raw)
        
        # CỐ ĐỊNH woa_b = 1.0
        woa_b = 1.0
        
        share_interval = SHARE_INTERVAL_FIXED
        
        run_gwo = request.form.get("run_gwo", "0") == "1"
        run_woa = request.form.get("run_woa", "0") == "1"
        run_pso = request.form.get("run_pso", "0") == "1"
        run_otsu = False
        run_hybrid = request.form.get("run_hybrid", "0") == "1"
        
        hybrid_strategies_raw = request.form.get("hybrid_strategies", "PA5").strip()
        hybrid_strategies = _normalize_main_hybrid_strategies(
            [s.strip().upper() for s in hybrid_strategies_raw.split(",") if s.strip()]
        ) if run_hybrid else []
        run_hybrid = run_hybrid and bool(hybrid_strategies)
        
        logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed}")
        logger.info(f"Thuật toán: GWO={run_gwo}, WOA={run_woa}, PSO={run_pso}, OTSU={run_otsu}, HYBRID={run_hybrid}")
        logger.info(f"Hybrid strategies: {hybrid_strategies}")
        logger.info(f"CẤU HÌNH: seed={seed}, woa_b=1.0, share_interval={share_interval}, HYBRID={hybrid_strategies}")
    except Exception as e:
        logger.error(f"Lỗi khi parse tham số: {e}")
        return jsonify({"error": f"invalid params: {e}"}), 400

    if not (run_gwo or run_woa or run_pso or run_otsu or run_hybrid):
        logger.error("Không có thuật toán nào được chọn")
        return jsonify({"error": "Phải chọn ít nhất 1 thuật toán"}), 400

    logger.info("Đang đọc và xử lý ảnh...")
    gray = decode_image_gray(f.read())
    logger.info(f"Ảnh đã được đọc: shape={gray.shape}")

    lb, ub = 0, 255
    repair_fn, fitness_fn, use_penalties, penalty_mode, objective_label = _build_threshold_objective(
        gray, k, lb, ub
    )

    logger.info(f"Main branch d?ng objective: {objective_label}")

    results = {}
    best_overall = None
    best_overall_f = float('inf')
    best_overall_algo = ""

    def seed_for(offset: int) -> int | None:
        del offset
        return seed

    base_init_pop = _base_init_population(seed, n_agents, k, lb, ub)

    def init_pop_for(_: str) -> np.ndarray | None:
        return None if base_init_pop is None else base_init_pop.copy()

    try:
        # Chạy GWO
        if run_gwo:
            logger.info("-" * 60)
            logger.info("CHẠY THUẬT TOÁN GWO")
            logger.info("-" * 60)
            logger.info(_format_algo_params_for_log("GWO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(10)))
            algo_start = time.time()
            opt = _make_optimizer("GWO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(10), 
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=init_pop_for("GWO")
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
                "region_analysis": _analyze_threshold_regions(gray, best_x),
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
            logger.info(_format_algo_params_for_log("WOA", n_agents=n_agents, n_iters=n_iters, seed=seed_for(20), woa_b=woa_b))
            algo_start = time.time()
            opt = _make_optimizer("WOA", n_agents=n_agents, n_iters=n_iters, seed=seed_for(20),
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=init_pop_for("WOA")
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
                "region_analysis": _analyze_threshold_regions(gray, best_x),
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
            logger.info(_format_algo_params_for_log("PSO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(25)))
            algo_start = time.time()
            opt = _make_optimizer("PSO", n_agents=n_agents, n_iters=n_iters, seed=seed_for(25),
                                strategy="PA1", woa_b=woa_b, share_interval=share_interval)
            best_x, best_f, history = opt.optimize(
                fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                repair_fn=repair_fn, init_pop=init_pop_for("PSO")
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
                "region_analysis": _analyze_threshold_regions(gray, best_x),
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
            logger.info(_format_algo_params_for_log("OTSU", n_agents=n_agents, n_iters=n_iters))
            logger.info(f"Image shape: {gray.shape}, k={k}")
            algo_start = time.time()
            
            try:
                best_x, best_f, history = OtsuMulti().optimize_with_image(
                    image=gray,
                    dim=k,
                    fitness_fn=fitness_fn,
                    repair_fn=repair_fn,
                )
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
                    "variant": otsu_variant,
                    "seg_data_url": _img_to_data_url_gray(seg),
                    "best_series": _history_to_best_series(history),
                    "metrics": metrics,
                    "region_analysis": _analyze_threshold_regions(gray, best_x),
                }
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
                logger.info(
                    _format_algo_params_for_log(
                        "HYBRID",
                        n_agents=n_agents,
                        n_iters=n_iters,
                        strategy=strategy,
                        woa_b=woa_b,
                        share_interval=share_interval,
                    )
                )
                algo_start = time.time()
                opt = _make_optimizer("HYBRID", n_agents=n_agents, n_iters=n_iters, 
                                    seed=seed_for(_hybrid_seed_offset(strategy)),
                                    strategy=strategy, woa_b=woa_b, share_interval=share_interval)
                best_x, best_f, history = opt.optimize(
                    fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
                    repair_fn=repair_fn, init_pop=init_pop_for(f"HYBRID-{strategy}")
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
                    "region_analysis": _analyze_threshold_regions(gray, best_x),
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

        # Tính histogram cho ảnh gốc
        hist = np.bincount(gray.ravel(), minlength=256).astype(int).tolist()
        
        response_data = {
            "k": k,
            "config": {
                "k": k,
                "n_agents": n_agents,
                "n_iters": n_iters,
                "seed": seed,
                "woa_b": woa_b,
                "share_interval": share_interval,
                "use_penalties": use_penalties,
                "penalty_mode": penalty_mode,
                "algorithms": {
                    "GWO": run_gwo,
                    "WOA": run_woa,
                    "PSO": run_pso,
                    "OTSU": run_otsu,
                    "PA5": "PA5" in hybrid_strategies,
                    "PA6": "PA6" in hybrid_strategies,
                },
            },
            "gray_data_url": _img_to_data_url_gray(gray),
            "results": results,
            "best_overall_algo": best_overall_algo,
            "best_overall_f": float(best_overall_f),
            "segmentation_time": seg_time,
            "histogram": {
                "bins": list(range(256)),
                "counts": hist,
            }
        }

        # BẮT BUỘC chạy benchmark cho CỐ ĐỊNH 6 hàm đã chọn
        if BENCHMARK_NAMES is not None:
            logger.info("")
            logger.info("=" * 80)
            logger.info("BẮT ĐẦU CHẠY BENCHMARK (CỐ ĐỊNH 6 HÀM: F1, F3, F8, F12, F13, F16)")
            logger.info("=" * 80)
            benchmark_start = time.time()
            benchmark_results = _run_all_benchmarks(
                n_agents, n_iters, seed, woa_b, share_interval,
                run_gwo, run_woa, run_pso, run_otsu, run_hybrid, hybrid_strategies
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
            image_id = os.path.splitext(os.path.basename(image_path))[0]
            run_dir = _create_run_dir("single", image_id, k)

            params = {
                "k": k,
                "n_agents": n_agents,
                "n_iters": n_iters,
                "seed": seed,
                "woa_b": woa_b,
                "share_interval": share_interval,
                "use_penalties": use_penalties,
                "penalty_mode": penalty_mode,
                "objective_name": objective_label,
                "gt_thr": gt_thr,
                "gt_fuse": gt_fuse,
                "total_time": total_time,
                "best_overall_algo": best_overall_algo,
                "best_overall_f": best_overall_f,
                "image_id": image_id,
                "image_path": image_path,
            }
            
            # Lưu kèm benchmark data nếu có
            benchmark_to_save = response_data.get("benchmark", None)
            histogram_to_save = response_data.get("histogram", None)
            _save_run_results(
                run_dir,
                gray,
                results,
                params,
                image_name=os.path.basename(image_path),
                benchmark_data=benchmark_to_save,
                histogram_data=histogram_to_save,
            )
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
        share_interval = SHARE_INTERVAL_FIXED

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
    Danh gia toan bo dataset BDS500 va tong hop mean/std qua nhieu seed.
    """
    import time
    from datetime import datetime

    logger.info("=" * 80)
    logger.info("BAT DAU DANH GIA BDS500")
    logger.info("=" * 80)

    try:
        k = int(request.form.get("k", "10"))
        image_path = str(request.form.get("image_path", "")).strip()
        gt_path = str(request.form.get("gt_path", "")).strip()
        seeds_raw = request.form.get("seeds", "").strip()
        seed_raw = request.form.get("seed", "42").strip()
        seed_start_raw = request.form.get("seed_start", "42").strip()
        seed_count_raw = request.form.get("seed_count", "").strip()
        source_run_dir = str(request.form.get("source_run_dir", "")).strip()
        n_agents = int(request.form.get("n_agents", "30"))
        n_iters = int(request.form.get("n_iters", "80"))
        woa_b = float(request.form.get("woa_b", "1.0"))
        share_interval = SHARE_INTERVAL_FIXED

        if seed_count_raw:
            seed_start = int(seed_start_raw) if seed_start_raw else 42
            seed_count = int(seed_count_raw)
            if seed_count <= 0:
                return jsonify({"error": "So luong seed phai > 0"}), 400
            seeds = list(range(seed_start, seed_start + seed_count))
        elif seeds_raw:
            seeds = [int(x.strip()) for x in seeds_raw.split(",") if x.strip()]
        elif seed_raw:
            seeds = [int(seed_raw)]
        else:
            seeds = [42]
        if not seeds:
            return jsonify({"error": "Danh sach seeds rong"}), 400

        algos_str = request.form.get("algorithms", "GWO,WOA,PSO,PA5,PA6")
        algorithms = [a.strip().upper() for a in algos_str.split(",") if a.strip() and a.strip().upper() != "OTSU"]

        logger.info(
            f"Cau hinh: mode=single_image_multi_seed, k={k}, "
            f"seeds={seeds}, n_agents={n_agents}, n_iters={n_iters}"
        )
        logger.info(f"Algorithms: {algorithms}")

        from src.objective.thresholding_with_penalties import compute_true_fe

        if not image_path:
            return jsonify({"error": "Can image_path tu tab phan doan"}), 400
        if not gt_path:
            return jsonify({"error": "Can gt_path cua anh BDS500 de tinh trung binh nhieu seed"}), 400
        if not os.path.exists(image_path):
            return jsonify({"error": f"Khong tim thay image_path: {image_path}"}), 400
        if not os.path.exists(gt_path):
            return jsonify({"error": f"Khong tim thay gt_path: {gt_path}"}), 400

        img = read_image_gray(image_path)
        gt_boundary = read_bsds_gt_boundary_mask(gt_path, thr=0.5, fuse="max")
        if img.shape != gt_boundary.shape:
            return jsonify({
                "error": f"Shape mismatch giua anh va GT: img={img.shape}, gt={gt_boundary.shape}"
            }), 400

        image_id = os.path.splitext(os.path.basename(image_path))[0]
        eval_items = [(image_id, img, gt_boundary)]

        lb, ub = 0, 255
        results = []

        results = []
        total_images = len(eval_items)
        total_algos = len(algorithms)
        total_runs = total_images * total_algos * len(seeds)
        run_count = 0
        overall_start = time.time()

        for seed in seeds:
            base_init_pop = _base_init_population(seed, n_agents, k, lb, ub)

            def seed_for(offset: int) -> int:
                del offset
                return int(seed)

            def init_pop_for(_: str) -> np.ndarray:
                if base_init_pop is None:
                    raise ValueError("base_init_pop must not be None in eval mode")
                return base_init_pop.copy()

            for img_idx, (image_id, img, gt_boundary) in enumerate(eval_items):
                logger.info(f"[{img_idx+1}/{total_images}] {image_id}, seed={seed}")

                for algo_name in algorithms:
                    run_count += 1
                    algo_start_time = time.time()
                    logger.info(f"  [{run_count}/{total_runs}] {algo_name}...")

                    try:
                        repair_fn, fitness_fn, use_penalties, penalty_mode, objective_label = _build_threshold_objective(
                            img, k, lb, ub
                        )
                        if algo_name == algorithms[0]:
                            logger.info(f"Evaluation dùng objective: {objective_label}")

                        algo_upper = algo_name.upper()
                        if algo_upper == "GWO":
                            algo_seed = seed_for(10)
                            opt = _make_optimizer("GWO", n_agents=n_agents, n_iters=n_iters, seed=algo_seed,
                                                  strategy="PA1", woa_b=woa_b, share_interval=share_interval)
                        elif algo_upper == "WOA":
                            algo_seed = seed_for(20)
                            opt = _make_optimizer("WOA", n_agents=n_agents, n_iters=n_iters, seed=algo_seed,
                                                  strategy="PA1", woa_b=woa_b, share_interval=share_interval)
                        elif algo_upper == "PSO":
                            algo_seed = seed_for(25)
                            opt = _make_optimizer("PSO", n_agents=n_agents, n_iters=n_iters, seed=algo_seed,
                                                  strategy="PA1", woa_b=woa_b, share_interval=share_interval)
                        elif algo_upper == "OTSU":
                            algo_seed = seed
                            opt = None
                        elif algo_upper.startswith("HYBRID-") or algo_upper.startswith("PA"):
                            strategy = algo_upper.replace("HYBRID-", "") if algo_upper.startswith("HYBRID-") else algo_upper
                            algo_seed = seed_for(_hybrid_seed_offset(strategy))
                            opt = _make_optimizer("HYBRID", n_agents=n_agents, n_iters=n_iters, seed=algo_seed,
                                                  strategy=strategy, woa_b=woa_b, share_interval=share_interval)
                        else:
                            raise ValueError(f"Unknown algorithm: {algo_name}")

                        if algo_upper == "OTSU":
                            otsu_variant = "multiotsu"
                            opt = OtsuMulti()
                            best_x, best_f, history = opt.optimize_with_image(
                                image=img,
                                dim=k,
                                fitness_fn=fitness_fn,
                                repair_fn=repair_fn,
                            )
                        else:
                            best_x, best_f, history = opt.optimize(
                                fitness_fn,
                                dim=k,
                                lb=np.full(k, lb, dtype=float),
                                ub=np.full(k, ub, dtype=float),
                                repair_fn=repair_fn,
                                init_pop=init_pop_for(algo_name),
                            )

                        algo_time = time.time() - algo_start_time
                        best_x = repair_fn(best_x)
                        seg = apply_thresholds(img, best_x)
                        pred_boundary = seg_to_boundary_mask(seg)
                        boundary_dsc = dice_boundary(gt_boundary, pred_boundary)
                        psnr = compute_psnr(img, seg, data_range=255.0)
                        ssim = compute_ssim(img, seg, data_range=255.0)
                        fe_true = compute_true_fe(img, best_x)

                        results.append({
                            "image_id": image_id,
                            "algorithm": algo_name,
                            "algorithm_variant": otsu_variant if algo_upper == "OTSU" else "optimizer",
                            "seed": seed,
                            "k": k,
                            "boundary_dsc": float(boundary_dsc),
                            "fe": float(fe_true),
                            "best_f": float(best_f),
                            "psnr": float(psnr),
                            "ssim": float(ssim),
                            "time": float(algo_time),
                            "thresholds": best_x.tolist(),
                        })
                    except Exception as e:
                        logger.error(f"    ERROR: {e}", exc_info=True)
                        results.append({
                            "image_id": image_id,
                            "algorithm": algo_name,
                            "seed": seed,
                            "k": k,
                            "error": str(e),
                        })

        total_time = time.time() - overall_start

        summary_stats = {}
        for algo_name in algorithms:
            algo_results = [r for r in results if r.get("algorithm") == algo_name and "error" not in r]
            if not algo_results:
                continue

            def arr(key):
                return np.asarray([r[key] for r in algo_results], dtype=float)

            boundary_dsc_arr = arr("boundary_dsc")
            fe_arr = arr("fe")
            psnr_arr = arr("psnr")
            ssim_arr = arr("ssim")
            time_arr = arr("time")

            summary_stats[algo_name] = {
                "n_runs": len(algo_results),
                "n_images": total_images,
                "n_seeds": len(seeds),
                "boundary_dsc_mean": float(np.mean(boundary_dsc_arr)),
                "boundary_dsc_sd": _sample_sd(boundary_dsc_arr),
                "fe_mean": float(np.mean(fe_arr)),
                "fe_sd": _sample_sd(fe_arr),
                "psnr_mean": float(np.mean(psnr_arr)),
                "psnr_sd": _sample_sd(psnr_arr),
                "ssim_mean": float(np.mean(ssim_arr)),
                "ssim_sd": _sample_sd(ssim_arr),
                "time_mean": float(np.mean(time_arr)),
                "time_sd": _sample_sd(time_arr),
            }

        wilcoxon_rows = []
        base_algo_name = None
        if "PA5" in algorithms:
            base_algo_name = "PA5"
        elif "HYBRID-PA5" in algorithms:
            base_algo_name = "HYBRID-PA5"
        if base_algo_name is not None:
            paired_rows = {}
            for row in results:
                if "error" in row:
                    continue
                key = (row["image_id"], row["seed"])
                paired_rows.setdefault(key, {})[row["algorithm"]] = row

            for challenger in [a for a in algorithms if a != base_algo_name and str(a).upper() != "OTSU"]:
                pairs = [
                    (vals[base_algo_name], vals[challenger])
                    for vals in paired_rows.values()
                    if base_algo_name in vals and challenger in vals
                ]
                if not pairs:
                    continue
                for metric in ["boundary_dsc", "fe", "psnr", "ssim"]:
                    x = [a[metric] for a, _ in pairs]
                    y = [b[metric] for _, b in pairs]
                    stat = wilcoxon_signed_rank(x, y)
                    mean_x = float(np.mean(x)) if x else 0.0
                    mean_y = float(np.mean(y)) if y else 0.0
                    wilcoxon_rows.append({
                        "base": base_algo_name,
                        "challenger": challenger,
                        "metric": metric,
                        "mean_base": mean_x,
                        "mean_challenger": mean_y,
                        "delta_mean": mean_x - mean_y,
                        **stat,
                    })

        run_dir = _create_run_dir("single_image_multi_seed", image_id, k, n_seeds=len(seeds))
        results_file = os.path.join(run_dir, "results.json")
        summary_file = os.path.join(run_dir, "summary.json")

        _save_multi_seed_eval_run(
            run_dir,
            img,
            image_name=os.path.basename(image_path),
            image_path=image_path,
            gt_path=gt_path,
            k=k,
            seeds=seeds,
            n_agents=n_agents,
            n_iters=n_iters,
            woa_b=woa_b,
            share_interval=share_interval,
            objective_name=objective_label,
            penalty_mode=penalty_mode,
            algorithms=algorithms,
            results=results,
            summary_stats=summary_stats,
            wilcoxon_rows=wilcoxon_rows,
            total_time=total_time,
            detail_results_file=results_file,
            detail_summary_file=summary_file,
            source_single_run_dir=source_run_dir,
        )

        return jsonify({
            "success": True,
            "run_dir": run_dir,
            "history_run_dir": run_dir,
            "results_file": results_file,
            "summary_file": summary_file,
            "stats": {
                "mode": "single_image_multi_seed",
                "total_images": total_images,
                "successful": len([r for r in results if "error" not in r]),
                "failed": len([r for r in results if "error" in r]),
                "n_seeds": len(seeds),
                "total_runs": total_runs,
            },
            "summary_stats": summary_stats,
            "wilcoxon": wilcoxon_rows,
            "total_time": total_time,
        })

    except Exception as e:
        logger.error(f"LOI DANH GIA BDS500: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.get("/api/history/list")
def api_history_list():
    """Lấy danh sách tất cả các lần chạy từ outputs/runs"""
    try:
        from src.runner.history_manager import HistoryManager
        manager = HistoryManager("outputs/runs")
        runs_data = [run.get_summary() for run in manager.list_runs()]
        return jsonify({
            "total": len(runs_data),
            "runs": runs_data,
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy lịch sử: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.get("/api/history/detail/<run_name>")
def api_history_detail(run_name):
    """Lấy chi tiết một lần chạy với tất cả thông tin"""
    try:
        from src.runner.history_manager import HistoryManager
        manager = HistoryManager("outputs/runs")
        detail = manager.get_run_detail(run_name)
        if detail is None:
            return jsonify({"error": "Không tìm thấy run"}), 404
        return jsonify(detail)
    except Exception as e:
        logger.error(f"Lỗi khi lấy chi tiết run: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.get("/api/history/export/<run_name>")
def api_history_export_run(run_name):
    try:
        from src.runner.history_manager import HistoryManager

        manager = HistoryManager("outputs/runs")
        archive = manager.export_run(run_name)
        return send_file(
            archive,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{run_name}.zip",
        )
    except FileNotFoundError:
        return jsonify({"error": "Không tìm thấy run"}), 404
    except Exception as e:
        logger.error(f"Lỗi khi export run: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.post("/api/history/export")
def api_history_export():
    """Export tóm tắt lịch sử ra JSON"""
    try:
        from src.runner.history_manager import HistoryManager
        import tempfile
        manager = HistoryManager("outputs/runs")
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        # Export to temp file
        manager.export_summary(output_path)
        
        return send_file(
            output_path,
            mimetype='application/json',
            as_attachment=True,
            download_name='history_summary.json'
        )
    except Exception as e:
        logger.error(f"Lỗi khi export lịch sử: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)


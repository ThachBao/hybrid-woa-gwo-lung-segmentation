"""
Fuzzy Entropy objective with penalties to prevent threshold clustering
"""
from __future__ import annotations

import numpy as np
from typing import Callable

from src.objective.fuzzy_entropy_s import fuzzy_entropy_objective
from src.objective.penalties import (
    total_penalty,
    PenaltyWeights,
    PenaltyParams,
)


def create_fe_objective_with_penalties(
    gray_image: np.ndarray,
    repair_fn: Callable[[np.ndarray], np.ndarray],
    weights: PenaltyWeights | None = None,
    params: PenaltyParams | None = None,
    lb: int = 0,
    ub: int = 255,
) -> Callable[[np.ndarray], float]:
    """
    Tạo objective function = Fuzzy Entropy + Penalties
    
    QUAN TRỌNG: Penalty tính trên x_raw (trước repair), Entropy tính trên x_repair
    Điều này đảm bảo penalty "nhìn thấy" ngưỡng dồn thật, không bị repair che mất.
    
    Objective: minimize (-Entropy + Penalties)
    - Entropy càng lớn càng tốt → -Entropy càng nhỏ càng tốt
    - Penalties càng nhỏ càng tốt (ít dồn ngưỡng, ít vùng rỗng)
    
    Args:
        gray_image: Ảnh grayscale (H, W) uint8
        repair_fn: Hàm repair ngưỡng (chỉ dùng cho entropy)
        weights: Trọng số penalties (None = dùng mặc định)
        params: Tham số penalties (None = dùng mặc định)
        lb: Lower bound (default: 0)
        ub: Upper bound (default: 255)
    
    Returns:
        fitness_fn(x) -> float (minimize)
    
    Example:
        >>> weights = PenaltyWeights(w_gap=2.0, w_size=1.0)
        >>> params = PenaltyParams(min_gap=8, p_min=0.01)
        >>> fitness_fn = create_fe_objective_with_penalties(
        ...     gray, repair_fn, weights, params
        ... )
        >>> # Dùng với optimizer
        >>> best_x, best_f, _ = optimizer.optimize(fitness_fn, ...)
    """
    # Default weights: TĂNG MẠNH để cạnh tranh với entropy
    if weights is None:
        weights = PenaltyWeights(
            w_gap=2.0,     # TĂNG - tránh gap quá nhỏ
            w_var=1.0,     # Khuyến khích đều
            w_end=0.5,     # Tránh biên
            w_size=1.0,    # Tránh vùng rỗng
            w_q=1.0,       # BẬT quantile prior
        )
    
    # Default params: TĂNG min_gap
    if params is None:
        params = PenaltyParams(
            min_gap=8,       # TĂNG từ 3 lên 8 pixels
            end_margin=3,    # 3 pixels từ biên
            p_min=0.01,      # 1% pixels mỗi vùng
        )
    
    def fitness_fn(x: np.ndarray) -> float:
        """
        Objective function: minimize (-Entropy + Penalties)
        
        PIPELINE MỚI:
        1. x_raw → Penalty (nhìn thấy ngưỡng dồn thật)
        2. x_raw → repair → Entropy (đảm bảo hợp lệ)
        """
        x_raw = np.asarray(x, dtype=float)
        
        # BƯỚC 1: Tính penalty trên x_raw (TRƯỚC repair)
        # Điều này đảm bảo penalty "nhìn thấy" ngưỡng dồn thật
        pen = total_penalty(gray_image, x_raw, weights, params, lb, ub)
        
        # BƯỚC 2: Repair để tính entropy
        x_repair = repair_fn(x_raw)
        base = float(fuzzy_entropy_objective(gray_image, x_repair))
        
        return base + pen
    
    return fitness_fn


def get_recommended_weights(mode: str = "balanced") -> PenaltyWeights:
    """
    Lấy trọng số penalties khuyến nghị
    
    Args:
        mode: "light", "balanced", "strong"
    
    Returns:
        PenaltyWeights
    
    Note:
        Weights được TĂNG MẠNH để penalties cạnh tranh trực tiếp với entropy
        - Entropy thường: 0.03 - 0.08
        - Penalties cần ~0.02-0.05 để có tác dụng thực sự
        - Tập trung vào gap và size (quan trọng nhất)
    """
    if mode == "light":
        return PenaltyWeights(
            w_gap=1.0,     # Nhẹ - tránh gap quá nhỏ
            w_var=0.5,     # Nhẹ - khuyến khích đều
            w_end=0.3,     # Nhẹ - tránh biên
            w_size=1.5,    # Nhẹ - tránh vùng rỗng
            w_q=0.5,       # Nhẹ - quantile prior
        )
    elif mode == "balanced":
        return PenaltyWeights(
            w_gap=2.0,     # TĂNG - ép gap lớn hơn
            w_var=1.0,     # Cân bằng - khuyến khích đều
            w_end=0.5,     # Cân bằng - tránh biên
            w_size=1.0,    # GIẢM - không quá mạnh (để entropy quyết định)
            w_q=1.0,       # BẬT - khuyến khích theo quantile
        )
    elif mode == "strong":
        return PenaltyWeights(
            w_gap=3.0,     # RẤT MẠNH - ép gap lớn
            w_var=2.0,     # Mạnh - ép đều
            w_end=1.0,     # Mạnh - ép xa biên
            w_size=2.0,    # Mạnh - tránh vùng rỗng
            w_q=1.5,       # Mạnh - quantile prior
        )
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'light', 'balanced', or 'strong'.")


def get_recommended_params(k: int = 10) -> PenaltyParams:
    """
    Lấy tham số penalties khuyến nghị dựa trên số ngưỡng k
    
    Args:
        k: Số ngưỡng
    
    Returns:
        PenaltyParams
    
    Note:
        TĂNG min_gap để ngăn dồn ngưỡng hiệu quả hơn
    """
    # min_gap: TĂNG lên 8-15 pixels tùy k
    # Công thức: ít nhất 8, tối đa 15
    ideal_gap = 255 // (k + 1)  # Khoảng cách lý tưởng nếu chia đều
    min_gap = max(8, min(15, ideal_gap // 2))  # Lấy 50% ideal, nhưng ít nhất 8
    
    # p_min: ít nhất 0.5% cho mỗi vùng
    # Với k ngưỡng → k+1 vùng
    p_min = max(0.005, 0.5 / (k + 1))
    
    return PenaltyParams(
        min_gap=min_gap,
        end_margin=5,  # TĂNG từ 3 lên 5
        p_min=p_min,
    )



def compute_fe_stability_jitter(
    gray_image: np.ndarray,
    thresholds: np.ndarray,
    repair_fn: Callable[[np.ndarray], np.ndarray],
    *,
    n_samples: int = 20,
    delta: int = 2,
    seed: int = 42,
) -> dict:
    """
    Tính độ ổn định FE khi ngưỡng bị nhiễu nhỏ (jitter).
    
    Đo "threshold sensitivity": FE thay đổi bao nhiêu khi ngưỡng thay đổi ±delta.
    
    Args:
        gray_image: Ảnh grayscale
        thresholds: Bộ ngưỡng gốc (đã tối ưu)
        repair_fn: Hàm repair ngưỡng
        n_samples: Số mẫu jitter (default: 20)
        delta: Biên jitter ±delta (default: 2)
        seed: Random seed
    
    Returns:
        dict với:
            - fe_mean: FE trung bình
            - fe_std: Độ lệch chuẩn FE (càng nhỏ càng ổn định)
            - fe_min: FE nhỏ nhất
            - fe_max: FE lớn nhất
            - fe_original: FE của ngưỡng gốc
    """
    rng = np.random.default_rng(seed)
    thresholds = np.asarray(thresholds, dtype=float)
    k = len(thresholds)
    
    # FE gốc
    fe_original = -float(fuzzy_entropy_objective(gray_image, thresholds))
    
    # FE với jitter
    fes = [fe_original]
    for _ in range(n_samples):
        jitter = rng.integers(-delta, delta + 1, size=k)
        t_jittered = repair_fn(thresholds + jitter)
        fe = -float(fuzzy_entropy_objective(gray_image, t_jittered))
        fes.append(fe)
    
    return {
        "fe_mean": float(np.mean(fes)),
        "fe_std": float(np.std(fes)),
        "fe_min": float(np.min(fes)),
        "fe_max": float(np.max(fes)),
        "fe_original": fe_original,
    }


def compute_fe_stability_convergence(
    history: list,
    *,
    last_w: int = 10,
) -> dict:
    """
    Tính độ ổn định FE trong quá trình hội tụ.
    
    Đo "convergence stability": FE dao động bao nhiêu ở cuối quá trình tối ưu.
    
    Args:
        history: Lịch sử tối ưu (list of dicts với key "best_f")
        last_w: Số vòng lặp cuối để tính (default: 10)
    
    Returns:
        dict với:
            - fe_last_mean: FE trung bình W vòng cuối
            - fe_last_std: Độ lệch chuẩn FE W vòng cuối (càng nhỏ càng ổn định)
            - fe_improvement: Cải thiện từ đầu đến cuối
            - fe_first: FE vòng đầu
            - fe_last: FE vòng cuối
    
    Note:
        history["best_f"] là giá trị minimize, nên FE = -best_f
    """
    if not history or len(history) == 0:
        return {
            "fe_last_mean": 0.0,
            "fe_last_std": 0.0,
            "fe_improvement": 0.0,
            "fe_first": 0.0,
            "fe_last": 0.0,
        }
    
    # Lấy best_f từ history
    best_fs = [h.get("best_f", 0.0) for h in history]
    
    # FE = -best_f (vì đang minimize -FE)
    fes = [-f for f in best_fs]
    
    # W vòng cuối
    last_fes = fes[-last_w:] if len(fes) >= last_w else fes
    
    return {
        "fe_last_mean": float(np.mean(last_fes)),
        "fe_last_std": float(np.std(last_fes)),
        "fe_improvement": float(fes[-1] - fes[0]) if len(fes) > 0 else 0.0,
        "fe_first": float(fes[0]) if len(fes) > 0 else 0.0,
        "fe_last": float(fes[-1]) if len(fes) > 0 else 0.0,
    }


def compute_true_fe(
    gray_image: np.ndarray,
    thresholds: np.ndarray,
) -> float:
    """
    Tính FE thực (không có penalty).
    
    Dùng để lấy FE đúng khi best_f có chứa penalty.
    
    Args:
        gray_image: Ảnh grayscale
        thresholds: Bộ ngưỡng
    
    Returns:
        FE (Fuzzy Entropy) - giá trị dương, càng lớn càng tốt
    """
    return -float(fuzzy_entropy_objective(gray_image, thresholds))

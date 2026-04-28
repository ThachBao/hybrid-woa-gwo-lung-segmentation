from __future__ import annotations

import time
from typing import Any, Dict

import cv2
import numpy as np

from src.objective.fuzzy_entropy_s import fuzzy_entropy_objective, fuzzy_entropy_value
from src.objective.thresholding import sanitize_thresholds
from src.optim.bounds import repair_threshold_vector
from src.optim.hybrid.pa5 import optimize_pa5
from src.cxr.lung_mask import threshold_regions_to_lung_mask
from src.segmentation.apply_thresholds import apply_thresholds


def _cxr_geometry_penalty(quality: Dict[str, Any]) -> float:
    area_ratio = float(quality.get("area_ratio", 0.0))
    major_count = int(quality.get("major_component_count", 0))
    penalty = 0.0
    if major_count != 2:
        penalty += 1.0
    if area_ratio < 0.12:
        penalty += (0.12 - area_ratio) / 0.12
    if area_ratio > 0.34:
        penalty += (area_ratio - 0.34) / 0.34
    penalty += max(0.0, 0.35 - float(quality.get("separation_score", 0.0)))
    penalty += max(0.0, 0.45 - float(quality.get("bottom_score", 0.0)))
    penalty += max(0.0, 0.45 - float(quality.get("width_score", 0.0)))
    return float(penalty)


def cxr_threshold_objective_value(gray: np.ndarray, thresholds: np.ndarray, *, geometry_gray: np.ndarray | None = None) -> Dict[str, Any]:
    thresholds = sanitize_thresholds(thresholds).astype(int)
    fe = float(fuzzy_entropy_value(gray, thresholds))
    geom_gray = gray if geometry_gray is None else geometry_gray
    segmented = apply_thresholds(geom_gray, thresholds)
    lung = threshold_regions_to_lung_mask(segmented, geom_gray, thresholds)
    quality = lung["candidate_quality"]
    shape_score = float(quality.get("score", 0.0))
    penalty = _cxr_geometry_penalty(quality)
    composite_score = fe + 12.0 * shape_score - 8.0 * penalty
    return {
        "score": float(composite_score),
        "fe": fe,
        "shape_score": shape_score,
        "shape_penalty": penalty,
        "quality": quality,
    }


def run_pa5_cxr(
    gray_preprocessed: np.ndarray,
    k: int,
    seed: int,
    n_agents: int,
    n_iters: int,
    *,
    objective: str = "cxr_fe_shape",
) -> Dict[str, Any]:
    gray = np.asarray(gray_preprocessed)
    if gray.ndim != 2:
        raise ValueError("gray_preprocessed must be a 2D grayscale image")
    if gray.dtype != np.uint8:
        gray = np.clip(gray, 0, 255).astype(np.uint8)

    k = int(k)
    n_agents = int(n_agents)
    n_iters = int(n_iters)
    share_interval = 10
    geometry_gray = cv2.resize(gray, (128, 128), interpolation=cv2.INTER_AREA)
    fitness_cache: Dict[tuple[int, ...], float] = {}

    def repair_fn(x: np.ndarray) -> np.ndarray:
        return repair_threshold_vector(
            x,
            k=k,
            lb=0,
            ub=255,
            integer=True,
            ensure_unique=True,
            avoid_endpoints=False,
        )

    objective = str(objective or "cxr_fe_shape").lower()

    def fitness_fn(x: np.ndarray) -> float:
        thresholds = repair_fn(x)
        cache_key = tuple(int(v) for v in thresholds)
        if cache_key in fitness_cache:
            return fitness_cache[cache_key]
        if objective == "fe":
            value = fuzzy_entropy_objective(gray, thresholds)
        else:
            value = -cxr_threshold_objective_value(gray, thresholds, geometry_gray=geometry_gray)["score"]
        fitness_cache[cache_key] = float(value)
        return float(value)

    start = time.time()
    best_x, best_f, history = optimize_pa5(
        fitness_fn,
        dim=k,
        lb=0,
        ub=255,
        n_agents=n_agents,
        n_iters=n_iters,
        seed=seed,
        repair_fn=repair_fn,
        share_interval=share_interval,
    )
    runtime = time.time() - start

    thresholds = sanitize_thresholds(best_x).astype(int).tolist()
    segmented = apply_thresholds(gray, np.asarray(thresholds, dtype=int))
    objective_info = cxr_threshold_objective_value(gray, np.asarray(thresholds, dtype=int))

    return {
        "thresholds": thresholds,
        "best_f": float(best_f),
        "fe": float(objective_info["fe"]),
        "objective_score": float(objective_info["score"]),
        "shape_score": float(objective_info["shape_score"]),
        "shape_penalty": float(objective_info["shape_penalty"]),
        "objective_quality": objective_info["quality"],
        "segmented": segmented,
        "history": history,
        "runtime": float(runtime),
        "share_interval": share_interval,
        "objective_name": "FE" if objective == "fe" else "CXR-FE-shape",
        "algorithm_main": "PA5",
    }

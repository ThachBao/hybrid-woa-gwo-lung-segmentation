"""
Objective functions for image segmentation
"""
from src.objective.fuzzy_entropy_s import fuzzy_entropy_objective
from src.objective.penalties import (
    PenaltyWeights,
    PenaltyParams,
    total_penalty,
    penalty_min_gap,
    penalty_gap_variance,
    penalty_end_margin,
    penalty_min_region_size,
    penalty_quantile_prior,
)
from src.objective.thresholding_with_penalties import (
    create_fe_objective_with_penalties,
    get_recommended_weights,
    get_recommended_params,
)

__all__ = [
    "fuzzy_entropy_objective",
    "PenaltyWeights",
    "PenaltyParams",
    "total_penalty",
    "penalty_min_gap",
    "penalty_gap_variance",
    "penalty_end_margin",
    "penalty_min_region_size",
    "penalty_quantile_prior",
    "create_fe_objective_with_penalties",
    "get_recommended_weights",
    "get_recommended_params",
]

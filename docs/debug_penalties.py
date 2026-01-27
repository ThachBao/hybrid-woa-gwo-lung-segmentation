"""
Debug: Check actual penalty values
"""
import numpy as np
from src.segmentation.io import read_image_gray
from src.objective.fuzzy_entropy import fuzzy_entropy_objective
from src.objective.penalties import (
    penalty_min_gap,
    penalty_min_region_size,
    penalty_end_margin,
    penalty_gap_variance,
    PenaltyWeights,
    PenaltyParams,
    total_penalty,
)

# Load image
gray = read_image_gray("dataset/lena.gray.bmp")
print(f"Image: shape={gray.shape}")

# Example thresholds (clustered)
t_bad = np.array([0, 6, 32, 155, 165, 184, 196, 211, 233, 249])
print(f"\nBad thresholds (clustered): {t_bad.tolist()}")

# Calculate individual penalties
lb, ub = 0, 255
min_gap = 5
p_min = 0.045

p_gap = penalty_min_gap(t_bad, lb, ub, min_gap=min_gap)
p_size = penalty_min_region_size(gray, t_bad, p_min=p_min, lb=lb, ub=ub)
p_end = penalty_end_margin(t_bad, lb, ub, margin=3)
p_var = penalty_gap_variance(t_bad, lb, ub)

print(f"\nIndividual penalties (raw):")
print(f"  penalty_min_gap: {p_gap:.8f}")
print(f"  penalty_min_region_size: {p_size:.8f}")
print(f"  penalty_end_margin: {p_end:.8f}")
print(f"  penalty_gap_variance: {p_var:.8f}")

# Calculate entropy
entropy = -float(fuzzy_entropy_objective(gray, t_bad))
print(f"\nEntropy: {entropy:.6f}")

# Calculate weighted penalties with NEW weights (balanced mode)
weights = PenaltyWeights(w_gap=1.0, w_var=1.0, w_end=0.5, w_size=2.0, w_q=0.0)
params = PenaltyParams(min_gap=min_gap, end_margin=3, p_min=p_min)

total_pen = total_penalty(gray, t_bad, weights, params, lb, ub)
print(f"\nTotal penalty (weighted): {total_pen:.8f}")

# Show weighted components
print(f"\nWeighted components:")
print(f"  w_gap * p_gap = {weights.w_gap} * {p_gap:.8f} = {weights.w_gap * p_gap:.8f}")
print(f"  w_size * p_size = {weights.w_size} * {p_size:.8f} = {weights.w_size * p_size:.8f}")
print(f"  w_end * p_end = {weights.w_end} * {p_end:.8f} = {weights.w_end * p_end:.8f}")
print(f"  w_var * p_var = {weights.w_var} * {p_var:.8f} = {weights.w_var * p_var:.8f}")

# Compare magnitudes
print(f"\nMagnitude comparison:")
print(f"  Entropy: {entropy:.6f}")
print(f"  Total penalty: {total_pen:.6f}")
print(f"  Ratio (penalty/entropy): {total_pen/entropy*100:.2f}%")

# Test with good thresholds
t_good = np.array([5, 36, 39, 44, 55, 68, 87, 110, 131, 150])
print(f"\n\nGood thresholds (more spread): {t_good.tolist()}")

p_gap_good = penalty_min_gap(t_good, lb, ub, min_gap=min_gap)
p_size_good = penalty_min_region_size(gray, t_good, p_min=p_min, lb=lb, ub=ub)
total_pen_good = total_penalty(gray, t_good, weights, params, lb, ub)
entropy_good = -float(fuzzy_entropy_objective(gray, t_good))

print(f"\nGood penalties:")
print(f"  penalty_min_gap: {p_gap_good:.8f}")
print(f"  penalty_min_region_size: {p_size_good:.8f}")
print(f"  Total penalty: {total_pen_good:.8f}")
print(f"  Entropy: {entropy_good:.6f}")

print(f"\nDifference:")
print(f"  Δ Penalty: {total_pen - total_pen_good:.8f} (bad - good)")
print(f"  Δ Entropy: {entropy - entropy_good:.8f} (bad - good)")

# What weights would make penalty significant?
target_penalty_ratio = 0.10  # 10% of entropy
target_penalty = entropy * target_penalty_ratio
scale_factor = target_penalty / total_pen if total_pen > 0 else 1.0

print(f"\n\nRECOMMENDED WEIGHTS:")
print(f"  To make penalty ~{target_penalty_ratio*100:.0f}% of entropy:")
print(f"  Scale factor: {scale_factor:.1f}x")
print(f"  w_gap: {weights.w_gap * scale_factor:.1f}")
print(f"  w_size: {weights.w_size * scale_factor:.1f}")
print(f"  w_end: {weights.w_end * scale_factor:.1f}")
print(f"  w_var: {weights.w_var * scale_factor:.1f}")

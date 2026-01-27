"""
Analyze gaps in thresholds
"""
import numpy as np

# Bad thresholds
t_bad = np.array([0, 6, 32, 155, 165, 184, 196, 211, 233, 249])
gaps_bad = np.diff(t_bad)
print("Bad thresholds:", t_bad.tolist())
print("Gaps:", gaps_bad.tolist())
print(f"Min gap: {gaps_bad.min()}, Max gap: {gaps_bad.max()}, Mean: {gaps_bad.mean():.1f}")

# Good thresholds
t_good = np.array([5, 36, 39, 44, 55, 68, 87, 110, 131, 150])
gaps_good = np.diff(t_good)
print("\nGood thresholds:", t_good.tolist())
print("Gaps:", gaps_good.tolist())
print(f"Min gap: {gaps_good.min()}, Max gap: {gaps_good.max()}, Mean: {gaps_good.mean():.1f}")

# Check penalty_min_gap calculation
min_gap = 5
lb, ub = 0, 255
r = float(ub - lb)

print(f"\n\nPenalty calculation (min_gap={min_gap}):")
print("Bad thresholds:")
d_bad = gaps_bad.astype(float) / r
g = float(min_gap) / r
p_bad = np.maximum(0.0, g - d_bad)
print(f"  Normalized gaps: {d_bad}")
print(f"  Target gap (normalized): {g:.6f}")
print(f"  Penalties: {p_bad}")
print(f"  Mean squared: {np.mean(p_bad * p_bad):.8f}")

print("\nGood thresholds:")
d_good = gaps_good.astype(float) / r
p_good = np.maximum(0.0, g - d_good)
print(f"  Normalized gaps: {d_good}")
print(f"  Penalties: {p_good}")
print(f"  Mean squared: {np.mean(p_good * p_good):.8f}")

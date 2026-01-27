# FE Stability Integration - Complete Summary

## Overview

This document describes the integration of FE (Fuzzy Entropy) stability metrics into the BDS500 evaluation system. The system now computes and displays stability metrics alongside DICE scores, providing a comprehensive evaluation of algorithm performance.

## Problem Statement

Previously, the BDS500 evaluation only showed DICE scores and entropy values. However:

1. **Incorrect FE calculation**: When using penalties, `entropy = -best_f` was WRONG because `best_f` contains penalty terms
2. **Missing stability metrics**: No way to measure how stable the FE values are across different conditions
3. **Single table display**: DICE and FE metrics were mixed in one table, making comparison difficult

## Solution

### 1. FE Stability Metrics

Three types of FE stability are now computed:

#### A. True FE (without penalties)
- **Function**: `compute_true_fe(gray_image, thresholds)`
- **Purpose**: Compute the actual FE value without penalty terms
- **Usage**: Replaces the incorrect `entropy = -best_f` calculation

#### B. Jitter Stability (Threshold Sensitivity)
- **Function**: `compute_fe_stability_jitter(gray_image, thresholds, repair_fn, n_samples=20, delta=2, seed=42)`
- **Purpose**: Measures how much FE changes when thresholds vary by ±delta (±2 gray levels)
- **Metric**: `fe_jitter_std` - lower is better (more stable)
- **Interpretation**: A stable algorithm produces similar FE values even when thresholds are slightly perturbed

#### C. Convergence Stability
- **Function**: `compute_fe_stability_convergence(history, last_w=10)`
- **Purpose**: Measures how much FE fluctuates in the last W iterations
- **Metric**: `fe_last_std` - lower is better (more stable convergence)
- **Interpretation**: A stable algorithm converges smoothly without oscillations

### 2. Backend Changes

#### File: `src/objective/thresholding_with_penalties.py`

Added three new functions:

```python
def compute_true_fe(gray_image, thresholds) -> float:
    """Compute FE without penalties."""
    return -float(fuzzy_entropy_objective(gray_image, thresholds))

def compute_fe_stability_jitter(gray_image, thresholds, repair_fn, 
                                n_samples=20, delta=2, seed=42) -> dict:
    """Compute threshold sensitivity stability."""
    # Returns: fe_mean, fe_std, fe_min, fe_max, fe_original

def compute_fe_stability_convergence(history, last_w=10) -> dict:
    """Compute convergence stability."""
    # Returns: fe_last_mean, fe_last_std, fe_improvement, fe_first, fe_last
```

#### File: `src/ui/app.py`

Updated `/api/eval_bds500` endpoint:

**Before:**
```python
# WRONG: best_f contains penalties
entropy = -best_f

# Single algo_stats dictionary
algo_stats = {...}

return jsonify({
    "algo_stats": algo_stats,  # Mixed DICE and FE
})
```

**After:**
```python
# CORRECT: Compute true FE
fe_true = compute_true_fe(gray, best_x)

# Compute stability metrics
fe_stab_jitter = compute_fe_stability_jitter(
    gray, best_x, repair_fn, n_samples=20, delta=2, seed=seed
)
fe_stab_conv = compute_fe_stability_convergence(history, last_w=10)

# Store results
results.append({
    "dice": float(dice),
    "fe": float(fe_true),
    "fe_jitter_mean": float(fe_stab_jitter["fe_mean"]),
    "fe_jitter_std": float(fe_stab_jitter["fe_std"]),
    "fe_conv_std": float(fe_stab_conv["fe_last_std"]),
    "fe_improvement": float(fe_stab_conv["fe_improvement"]),
})

# Separate DICE and FE statistics
dice_stats = {...}  # DICE metrics only
fe_stats = {...}    # FE metrics only

return jsonify({
    "dice_stats": dice_stats,
    "fe_stats": fe_stats,
})
```

### 3. Frontend Changes

#### File: `src/ui/static/app.js`

Updated `displayBDS500Results()` function:

**Before:**
- Single table with mixed DICE and Entropy columns
- Used `data.algo_stats`

**After:**
- Two separate tables:
  1. **DICE Table**: Shows DICE mean, std, min, max
  2. **FE Table**: Shows FE mean, std, jitter_std, conv_std, time
- Uses `data.dice_stats` and `data.fe_stats`

```javascript
function displayBDS500Results(data) {
  const diceStats = data.dice_stats || {};
  const feStats = data.fe_stats || {};
  
  // DICE comparison table
  if (Object.keys(diceStats).length > 0) {
    // Display DICE metrics: mean, std, min, max
  }
  
  // FE comparison table
  if (Object.keys(feStats).length > 0) {
    // Display FE metrics: mean, std, jitter_std, conv_std, time
    // Add explanatory notes about stability metrics
  }
}
```

#### File: `src/ui/static/index.css`

Added new CSS classes:

```css
.fe-cell {
  color: #2b6cb0;
  font-size: 14px;
}

.stability-note {
  margin-top: 16px;
  padding: 16px;
  background: #edf2f7;
  border-left: 4px solid #4299e1;
  border-radius: 6px;
}
```

## Results Structure

### Backend Response

```json
{
  "success": true,
  "stats": {
    "total_images": 10,
    "successful": 10,
    "failed": 0
  },
  "dice_stats": {
    "GWO": {
      "n_images": 10,
      "dice_mean": 0.7234,
      "dice_std": 0.0456,
      "dice_min": 0.6543,
      "dice_max": 0.7891
    }
  },
  "fe_stats": {
    "GWO": {
      "n_images": 10,
      "fe_mean": 5.234567,
      "fe_std": 0.123456,
      "fe_min": 5.012345,
      "fe_max": 5.456789,
      "fe_jitter_std_mean": 0.000234,
      "fe_conv_std_mean": 0.000156,
      "time_mean": 12.34
    }
  },
  "total_time": 256.78
}
```

### Frontend Display

#### Table 1: DICE Score Comparison
| Algorithm | DICE (Mean) | DICE (Std) | DICE (Min) | DICE (Max) | Số ảnh |
|-----------|-------------|------------|------------|------------|--------|
| 🏆 PSO    | 0.7301      | 0.0423     | 0.6678     | 0.7945     | 10     |
| GWO       | 0.7234      | 0.0456     | 0.6543     | 0.7891     | 10     |
| WOA       | 0.7156      | 0.0489     | 0.6421     | 0.7823     | 10     |

#### Table 2: Fuzzy Entropy & Stability Comparison
| Algorithm | FE (Mean) | FE (Std) | FE Jitter Std ↓ | FE Conv Std ↓ | Thời gian |
|-----------|-----------|----------|-----------------|---------------|-----------|
| 🏆 PSO    | 5.267890  | 0.134567 | 0.000198        | 0.000123      | 11.23s    |
| GWO       | 5.234567  | 0.123456 | 0.000234        | 0.000156      | 12.34s    |
| WOA       | 5.198765  | 0.134567 | 0.000345        | 0.000234      | 13.45s    |

**Chú thích:**
- **FE Jitter Std ↓**: Độ ổn định khi ngưỡng thay đổi nhỏ (±2 mức xám). Càng thấp = càng ổn định.
- **FE Conv Std ↓**: Độ ổn định hội tụ trong 10 vòng lặp cuối. Càng thấp = hội tụ càng ổn định.

## Performance Considerations

### Computational Cost

FE stability computation is expensive:

- **Without stability**: 1 FE calculation per evaluation
- **With jitter stability (n_samples=20)**: 21 FE calculations per evaluation (1 original + 20 jittered)
- **Total overhead**: ~21x more FE calculations

For a typical BDS500 evaluation:
- 10 images × 3 algorithms × 30 agents × 80 iterations = 72,000 fitness evaluations
- With stability: 72,000 × 21 = 1,512,000 FE calculations
- Estimated time increase: ~20x longer

### Optimization Tips

1. **Reduce n_samples**: Use `n_samples=10` instead of 20 for faster evaluation
2. **Reduce delta**: Use `delta=1` instead of 2 for less perturbation
3. **Selective evaluation**: Only compute stability for final results, not during optimization
4. **Parallel processing**: Jitter samples can be computed in parallel

## Usage

### 1. Start the UI

```bash
python src/ui/app.py
```

### 2. Navigate to "Đánh giá BDS500" Tab

### 3. Configure Evaluation

- Select algorithms (GWO, WOA, PSO, OTSU, PA1-PA5)
- Set k (number of thresholds)
- Set seed for reproducibility
- Set n_agents and n_iters
- Choose split (test/train/val)

### 4. Run Evaluation

Click "Chạy đánh giá" and wait for results.

### 5. View Results

Two separate tables will be displayed:
1. **DICE Score Comparison**: Focus on segmentation quality
2. **FE & Stability Comparison**: Focus on optimization quality and stability

## Testing

Run the test script to verify the integration:

```bash
python docs/test_fe_stability_ui.py
```

Expected output:
```
✅ ALL TESTS PASSED!

Summary:
  ✓ FE stability functions work correctly
  ✓ Backend returns dice_stats and fe_stats separately
  ✓ Frontend displays 2 separate tables
  ✓ DICE table shows: mean, std, min, max
  ✓ FE table shows: mean, std, jitter_std, conv_std, time
```

## Files Modified

1. **Backend**:
   - `src/objective/thresholding_with_penalties.py` - Added 3 stability functions
   - `src/ui/app.py` - Updated `/api/eval_bds500` endpoint

2. **Frontend**:
   - `src/ui/static/app.js` - Updated `displayBDS500Results()` function
   - `src/ui/static/index.css` - Added CSS for FE table and stability notes

3. **Documentation**:
   - `docs/test_fe_stability_ui.py` - Test script
   - `docs/FE_STABILITY_INTEGRATION.md` - This document

## Future Enhancements

### 1. Run-to-Run Stability

Currently not implemented. Would require:
- Multiple runs with different seeds
- Compute `fe_std_final` across runs
- Add to UI as a third stability metric

### 2. Configurable Stability Parameters

Add UI controls for:
- `n_samples` (jitter sample count)
- `delta` (jitter magnitude)
- `last_w` (convergence window size)

### 3. Stability-Aware Optimization

Implement `create_fe_objective_stable()` to optimize for both FE and stability:

```python
loss(t) = -mean(FE(t+Δ)) + λ·std(FE(t+Δ)) + penalties(t)
```

This would directly optimize for stable thresholds during the optimization process.

## Conclusion

The FE stability integration provides a comprehensive evaluation framework for BDS500 that:

1. ✅ Correctly computes FE without penalty contamination
2. ✅ Measures threshold sensitivity (jitter stability)
3. ✅ Measures convergence stability
4. ✅ Separates DICE and FE metrics into distinct tables
5. ✅ Provides clear visual comparison of algorithm performance

The system is now ready for production use and can help researchers identify algorithms that not only achieve high DICE scores but also produce stable, robust results.

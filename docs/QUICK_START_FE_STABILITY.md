# Quick Start: FE Stability Evaluation

## 🚀 Start in 3 Steps

### Step 1: Start the UI
```bash
python src/ui/app.py
```

### Step 2: Open Browser
```
http://127.0.0.1:5000
```

### Step 3: Run Evaluation
1. Click tab "Đánh giá BDS500"
2. Select algorithms: ☑ GWO ☑ WOA ☑ PSO
3. Click "Chạy đánh giá"
4. Wait ~30 minutes
5. View 2 tables with results

## 📊 What You'll See

### Table 1: DICE Score Comparison
| Algorithm | DICE Mean | DICE Std | Min | Max |
|-----------|-----------|----------|-----|-----|
| 🏆 PSO    | 0.7301    | 0.0423   | 0.6678 | 0.7945 |
| GWO       | 0.7234    | 0.0456   | 0.6543 | 0.7891 |
| WOA       | 0.7156    | 0.0489   | 0.6421 | 0.7823 |

**Interpretation**: PSO has highest DICE → Best segmentation quality

### Table 2: FE & Stability Comparison
| Algorithm | FE Mean | Jitter Std ↓ | Conv Std ↓ | Time |
|-----------|---------|--------------|------------|------|
| 🏆 PSO    | 5.2679  | 0.000198     | 0.000123   | 11.23s |
| GWO       | 5.2346  | 0.000234     | 0.000156   | 12.34s |
| WOA       | 5.1988  | 0.000345     | 0.000234   | 13.45s |

**Interpretation**: 
- PSO has highest FE → Best optimization quality
- PSO has lowest Jitter Std → Most stable to noise
- PSO has lowest Conv Std → Smoothest convergence

## 🎯 Key Metrics

### Jitter Std (Threshold Sensitivity)
- **< 0.001**: Excellent ⭐⭐⭐⭐⭐
- **0.001 - 0.005**: Good ⭐⭐⭐⭐
- **0.005 - 0.01**: Fair ⭐⭐⭐
- **> 0.01**: Poor ⭐⭐

### Conv Std (Convergence Stability)
- **< 0.001**: Excellent ⭐⭐⭐⭐⭐
- **0.001 - 0.005**: Good ⭐⭐⭐⭐
- **0.005 - 0.01**: Fair ⭐⭐⭐
- **> 0.01**: Poor ⭐⭐

## ⚡ Quick Test (5 minutes)

For fast testing:
```
k: 3
n_agents: 20
n_iters: 30
split: test (5 images)
algorithms: GWO, WOA
```

## 📚 Full Documentation

- **User Guide**: `docs/HUONG_DAN_DO_ON_DINH_FE.md`
- **Technical Details**: `docs/FE_STABILITY_INTEGRATION.md`
- **Vietnamese Summary**: `docs/TOM_TAT_DO_ON_DINH_FE.md`

## ✅ Verify Installation

```bash
python docs/test_fe_stability_ui.py
```

Expected output:
```
✅ ALL TESTS PASSED!
```

## 🎉 You're Ready!

Start evaluating your algorithms with stability metrics now!

# Quick Start: BDS500 UI Evaluation

## ✅ Status: COMPLETE & READY TO USE

---

## 🚀 Quick Start (3 Steps)

### 1. Start Server
```bash
python -m src.ui.app
```

### 2. Open Browser
```
http://localhost:5000
```

### 3. Use BDS500 Tab
1. Click **"📊 Đánh giá BDS500"** tab
2. Configure and click **"🚀 Bắt đầu đánh giá"**
3. View results!

---

## 📋 What You Can Do

### Configure Dataset
- **Split**: test/train/val
- **Limit**: 1-500 images

### Select Algorithms
- GWO, WOA, PA1, PA2, PA3, PA4, PA5
- Select at least 1

### Set Parameters
- **k**: 2-20 (number of thresholds)
- **seed**: 0-9999 (for reproducibility)
- **n_agents**: 5-500 (population size)
- **n_iters**: 1-5000 (iterations)

### View Results
- Summary statistics
- DICE scores comparison
- Best algorithm highlighted
- Saved results location

---

## 📊 Example Usage

### Quick Test (10 images, 3 algorithms)
```
Split: test
Limit: 10
Algorithms: GWO, WOA, PA1
k: 10
seed: 42
n_agents: 30
n_iters: 80

Time: ~2-5 minutes
```

### Full Evaluation (200 images, all algorithms)
```
Split: test
Limit: 200
Algorithms: All 7
k: 10
seed: 42
n_agents: 30
n_iters: 80

Time: ~2-3 hours
```

---

## ✅ Verification

### Test Everything Works
```bash
python docs/test_bds500_ui_complete.py
```

Expected output:
```
============================================================
TEST SUMMARY
============================================================
Backend API                    ✅ PASSED
Frontend HTML                  ✅ PASSED
Frontend JavaScript            ✅ PASSED
Frontend CSS                   ✅ PASSED
Integration Completeness       ✅ PASSED
============================================================
Total: 5/5 tests passed
============================================================

🎉 ALL TESTS PASSED! BDS500 UI integration is complete.
```

---

## 📁 Results Location

Results saved to:
```
outputs/bds500_eval/YYYYMMDD_HHMMSS/
├── results.json          # Detailed results
├── evaluation.log        # Logs
└── summary.json          # Statistics
```

---

## ⚠️ Important Notes

### About Seed
- Single seed (e.g., 42) is for **debug only**
- For valid comparison: use **30+ different seeds**
- UI shows warning about this

### Processing Time
- 10 images × 3 algos ≈ 2-5 minutes
- 200 images × 7 algos ≈ 2-3 hours

### Memory Usage
- ~500MB RAM for 200 images

---

## 🎯 What You Get

### Summary Cards
- Total images processed
- Successful/failed counts
- Total time

### Comparison Table
- DICE scores (mean, std, min, max)
- Entropy mean
- Time mean
- Best algorithm highlighted in green

### Files
- Results JSON with all details
- Logs for debugging
- Can analyze later with scripts

---

## 📚 Full Documentation

- `BDS500_UI_INTEGRATION.md` - Complete integration details
- `BDS500_UI_COMPLETE_SUMMARY.md` - Vietnamese summary
- `docs/EVAL_BDS500_K10_SEED42.md` - Evaluation system
- `EVAL_BDS500_QUICKSTART.md` - Quick start guide

---

## 🔧 Troubleshooting

### Server won't start
```bash
# Check if port 5000 is in use
netstat -ano | findstr :5000

# Use different port
set FLASK_RUN_PORT=5001
python -m src.ui.app
```

### Import errors
```bash
# Verify installation
python -c "from src.ui.app import app; print('OK')"
```

### Tests fail
```bash
# Run individual tests
python docs/test_bds500_api.py
python docs/test_bds500_pipeline.py
```

---

## ✅ Ready to Use!

Everything is set up and tested. Just:
1. Start server
2. Open browser
3. Use the UI

**Have fun evaluating! 🎉**

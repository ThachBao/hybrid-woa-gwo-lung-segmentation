# So Sánh GWO-WOA Strategies (PA1..PA5)

## Quick Start

### 1. Test nhanh (5 ảnh, 10 agents, 20 iterations)

**Windows**:
```bash
<<<<<<< HEAD
run_compare_quick_test.bat
=======
.\run_compare_quick_test.bat
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
```

**Linux/Mac**:
```bash
python -m src.runner.compare_gwo_woa_strategies \
  --root dataset/BDS500/images/val \
  --limit 5 --k 10 --n_agents 10 --n_iters 20 --seed 42
```

### 2. Chạy đầy đủ (tất cả ảnh, 30 agents, 80 iterations)

**Windows**:
```bash
<<<<<<< HEAD
run_compare_full.bat
=======
.\run_compare_full.bat
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
```

**Linux/Mac**:
```bash
python -m src.runner.compare_gwo_woa_strategies \
  --root dataset/BDS500/images/val \
  --k 10 --n_agents 30 --n_iters 80 --seed 42
```

### 3. Chạy nhiều seed (30 seeds)

**Windows**:
```bash
<<<<<<< HEAD
run_compare_multi_seed.bat
=======
.\run_compare_multi_seed.bat
>>>>>>> a858546ab813e65700045d86b86a0f25e328c3ba
```

**Linux/Mac**:
```bash
for seed in $(seq 0 29); do
  python -m src.runner.compare_gwo_woa_strategies \
    --root dataset/BDS500/images/val \
    --k 10 --n_agents 30 --n_iters 80 --seed "$seed"
done
```

## Kết Quả

Kết quả lưu trong `outputs/compareGWO-WOA/`:
- `results.csv` - Kết quả chi tiết
- `summary.json` - Tóm tắt theo strategy
- `per_image/*.json` - Kết quả từng ảnh

## Chỉ Số

- **FE Best**: FE tốt nhất (cao = tốt)
- **Jitter Std**: Độ ổn định ngưỡng (thấp = ổn định)
- **Conv Std**: Độ ổn định hội tụ (thấp = mượt)
- **Time**: Thời gian chạy (thấp = nhanh)

## Tài Liệu

Xem chi tiết: `docs/HUONG_DAN_SO_SANH_GWO_WOA.md`

## Files

- `src/runner/compare_gwo_woa_strategies.py` - Script chính
- `run_compare_*.bat` - Scripts Windows
- `docs/HUONG_DAN_SO_SANH_GWO_WOA.md` - Hướng dẫn chi tiết

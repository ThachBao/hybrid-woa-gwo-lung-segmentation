# Tóm tắt: Tối ưu ngưỡng toàn cục

## Đã hoàn thành

### 1. Script học ngưỡng toàn cục
**File:** `src/runner/learn_global_thresholds_bsds500.py`

**Chức năng:**
- Tìm 1 bộ ngưỡng tối ưu cho toàn bộ train set
- Tối ưu theo Boundary-DICE (không phải Fuzzy Entropy)
- Objective: minimize (1 - mean_DICE) trên tất cả ảnh train
- Preload tất cả ảnh vào RAM để tối ưu nhanh hơn
- Hiển thị progress mỗi 10 evaluations
- Lưu kết quả vào JSON

**Usage:**
```bash
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train \
  --k 10 \
  --algo HYBRID \
  --strategy PA3 \
  --n_agents 50 \
  --n_iters 200 \
  --limit 100 \
  --out_dir outputs/runs/my_thresholds
```

**Output:** `global_thresholds.json`
```json
{
  "k": 10,
  "thresholds": [4, 39, 67, 71, 77, 94, 128, 136, 175, 188],
  "mean_boundary_dice": 0.3456,
  "algo": "HYBRID",
  "strategy": "PA3",
  "n_agents": 50,
  "n_iters": 200,
  "num_images": 100,
  "split": "train",
  "optimization_time": 3600.5,
  "load_time": 45.2
}
```

### 2. Script đánh giá ngưỡng toàn cục
**File:** `src/runner/eval_global_thresholds_bsds500.py`

**Chức năng:**
- Đánh giá ngưỡng đã học trên test set
- Tính mean DICE, std, min, max
- So sánh với train DICE
- Lưu kết quả chi tiết vào CSV (optional)

**Usage:**
```bash
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test \
  --thresholds_json outputs/runs/my_thresholds/global_thresholds.json \
  --out_csv outputs/runs/my_thresholds/test_results.csv
```

**Output:**
```
================================================================================
KẾT QUẢ ĐÁNH GIÁ
================================================================================
Split: test
Số ảnh: 200
Thời gian: 5.23s
Mean Boundary-DICE: 0.3201
Std DICE: 0.0456
Min DICE: 0.1234
Max DICE: 0.5678
================================================================================

So sánh với train:
  Train DICE: 0.3456
  Test DICE:  0.3201
  Chênh lệch: -0.0255 (-7.38%)
================================================================================
```

### 3. Documentation
- `docs/GLOBAL_THRESHOLDS.md`: Hướng dẫn chi tiết đầy đủ
- `README_TOI_UU_NGUONG.md`: Hướng dẫn nhanh bằng tiếng Việt
- `SUMMARY_GLOBAL_THRESHOLDS.md`: File này

## Quy trình sử dụng

### Test nhanh (5-10 phút)
```bash
# Học trên 10 ảnh
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train --k 10 --algo GWO --n_agents 20 --n_iters 50 --limit 10 \
  --out_dir outputs/runs/quick

# Test trên 10 ảnh
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test --thresholds_json outputs/runs/quick/global_thresholds.json --limit 10
```

### Chất lượng cao (1-2 giờ)
```bash
# Học trên 100 ảnh với HYBRID-PA3
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train --k 10 --algo HYBRID --strategy PA3 \
  --n_agents 50 --n_iters 200 --limit 100 \
  --out_dir outputs/runs/best

# Test trên toàn bộ test set
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test --thresholds_json outputs/runs/best/global_thresholds.json \
  --out_csv outputs/runs/best/test_results.csv
```

## Ưu điểm của phương pháp mới

### So với Fuzzy Entropy:
1. **Tối ưu trực tiếp theo metric đánh giá** (DICE)
2. **Kết quả tốt hơn** trên ground truth
3. **Có thể so sánh** train vs test DICE
4. **Phát hiện overfitting** dễ dàng

### So với tối ưu từng ảnh:
1. **Có ngưỡng chung** để dùng cho mọi ảnh
2. **Nhanh hơn** khi inference (không cần tối ưu lại)
3. **Generalize tốt hơn** trên test set
4. **Phù hợp cho production** (1 bộ ngưỡng cố định)

## Kết quả test

### Test với 3 ảnh train, 5 ảnh test:
- **Train DICE**: 0.2183
- **Test DICE**: 0.1650
- **Chênh lệch**: -24.43% (do quá ít ảnh train)

### Kết quả mong đợi với dataset đầy đủ:
- **Train DICE**: 0.35 - 0.45
- **Test DICE**: 0.30 - 0.40
- **Chênh lệch**: 5-15%

## Tham số khuyến nghị

| Mục đích | limit | n_agents | n_iters | algo | Thời gian |
|----------|-------|----------|---------|------|-----------|
| Test nhanh | 10-20 | 20 | 50 | GWO | 5-10 phút |
| Cân bằng | 50-100 | 40 | 150 | HYBRID-PA3 | 1-2 giờ |
| Tốt nhất | 200 | 50 | 300 | HYBRID-PA3 | 4-6 giờ |

## Files tạo ra

```
src/runner/
├── learn_global_thresholds_bsds500.py    # Script học ngưỡng
└── eval_global_thresholds_bsds500.py     # Script đánh giá

docs/
└── GLOBAL_THRESHOLDS.md                  # Hướng dẫn chi tiết

README_TOI_UU_NGUONG.md                   # Hướng dẫn nhanh
SUMMARY_GLOBAL_THRESHOLDS.md              # File này

outputs/runs/
└── [tên_thư_mục]/
    ├── global_thresholds.json            # Ngưỡng tối ưu
    └── test_results.csv                  # Kết quả test (optional)
```

## Cách sử dụng ngưỡng đã học

Sau khi có file `global_thresholds.json`, bạn có thể:

1. **Dùng trong code Python:**
```python
import json
import numpy as np
from src.segmentation.apply_thresholds import apply_thresholds

# Load ngưỡng
with open("outputs/runs/best/global_thresholds.json") as f:
    data = json.load(f)
thresholds = np.array(data["thresholds"], dtype=int)

# Áp dụng cho ảnh mới
seg = apply_thresholds(gray_image, thresholds)
```

2. **Test trên split khác:**
```bash
# Test trên val set
python -m src.runner.eval_global_thresholds_bsds500 \
  --split val \
  --thresholds_json outputs/runs/best/global_thresholds.json
```

3. **So sánh nhiều thuật toán:**
```bash
# Học với GWO
python -m src.runner.learn_global_thresholds_bsds500 \
  --algo GWO --out_dir outputs/runs/gwo ...

# Học với HYBRID-PA3
python -m src.runner.learn_global_thresholds_bsds500 \
  --algo HYBRID --strategy PA3 --out_dir outputs/runs/pa3 ...

# So sánh test DICE
python -m src.runner.eval_global_thresholds_bsds500 \
  --thresholds_json outputs/runs/gwo/global_thresholds.json ...
python -m src.runner.eval_global_thresholds_bsds500 \
  --thresholds_json outputs/runs/pa3/global_thresholds.json ...
```

## Next steps

1. **Chạy với dataset đầy đủ**: Dùng `--limit 200` để học trên toàn bộ train set
2. **Thử các thuật toán khác**: So sánh GWO, WOA, HYBRID-PA1, PA3, PA5
3. **Tăng iterations**: Thử `--n_iters 300-500` để cải thiện kết quả
4. **Cross-validation**: Học trên train, validate trên val, test trên test
5. **Ensemble**: Kết hợp nhiều bộ ngưỡng từ các thuật toán khác nhau

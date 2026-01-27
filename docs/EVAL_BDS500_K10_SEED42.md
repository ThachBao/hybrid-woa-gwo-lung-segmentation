# Đánh Giá BDS500 với K=10 và Seed=42

## Tổng Quan

Script đánh giá toàn bộ dataset BDS500 với cấu hình cố định:
- **K = 10** (10 ngưỡng → 11 lớp)
- **Seed = 42** (reproducibility)

## ⚠️ CẢNH BÁO QUAN TRỌNG

**Đây là chế độ DEBUG/REPRODUCIBILITY**

### Chỉ dùng để:
- ✅ Kiểm tra pipeline chạy đúng chưa
- ✅ Debug thuật toán
- ✅ Reproducibility (với seed=42)
- ✅ Kiểm tra code không có bug

### KHÔNG được dùng để:
- ❌ Kết luận thuật toán nào tốt hơn
- ❌ So sánh hiệu năng
- ❌ Viết báo cáo khoa học

### Lý do:
- Chỉ 1 seed → kết quả có thể do may mắn
- Không có thông tin về độ ổn định (variance)
- Không đủ dữ liệu để statistical test

---

## I. CẤU TRÚC FILES

### 1. `src/data/bsds500.py` (MỚI)
Load dataset với ground truth boundaries

```python
from src.data.bsds500 import load_bsds500

# Load train set
data = load_bsds500(split="train", limit=10)

for img, gt_boundary in data:
    print(img.shape, gt_boundary.shape)
    # img: (H, W) uint8
    # gt_boundary: (H, W) bool
```

### 2. `src/runner/eval_bds500_k10_seed42.py` (MỚI)
Script đánh giá chính

**Cấu hình cố định:**
```python
K = 10          # Số ngưỡng
SEED = 42       # Seed cố định
N_AGENTS = 30
N_ITERS = 80
```

**Thuật toán:**
- GWO
- WOA
- HYBRID-PA1
- HYBRID-PA2
- HYBRID-PA3
- HYBRID-PA4
- HYBRID-PA5

### 3. `src/runner/analyze_bds500_results.py` (MỚI)
Phân tích kết quả

---

## II. CÁCH CHẠY

### Bước 1: Chạy Đánh Giá

```bash
# Chạy trên train set (mặc định)
python -m src.runner.eval_bds500_k10_seed42

# Hoặc chỉnh sửa SPLIT trong file để chạy test/val
```

**Thời gian ước tính:**
- Train set (~200 ảnh): ~2-3 giờ
- Test set (~100 ảnh): ~1-1.5 giờ

**Output:**
```
outputs/bds500_eval/k10_seed42_train_YYYYMMDD_HHMMSS/
├── results_k10_seed42.json      # Kết quả chi tiết
└── summary_k10_seed42.json      # Thống kê tổng hợp
```

### Bước 2: Phân Tích Kết Quả

```bash
python -m src.runner.analyze_bds500_results \
    outputs/bds500_eval/k10_seed42_train_YYYYMMDD_HHMMSS/results_k10_seed42.json
```

---

## III. CẤU TRÚC KẾT QUẢ

### `results_k10_seed42.json`

```json
[
  {
    "image_id": "img_0000",
    "algorithm": "GWO",
    "seed": 42,
    "K": 10,
    "dice": 0.6234,
    "entropy": 0.0456,
    "best_f": -0.0456,
    "time": 12.34,
    "thresholds": [23, 45, 67, 89, 111, 133, 155, 177, 199, 221],
    "n_iters": 80
  },
  ...
]
```

### `summary_k10_seed42.json`

```json
{
  "config": {
    "K": 10,
    "SEED": 42,
    "N_AGENTS": 30,
    "N_ITERS": 80,
    "SPLIT": "train",
    "n_images": 200,
    "algorithms": ["GWO", "WOA", "HYBRID-PA1", ...]
  },
  "statistics": {
    "GWO": {
      "n_images": 200,
      "dice_mean": 0.6234,
      "dice_std": 0.0456,
      "dice_min": 0.4567,
      "dice_max": 0.7890,
      "entropy_mean": 0.0456,
      "time_mean": 12.34
    },
    ...
  },
  "warning": "Chỉ 1 seed - không đủ dữ liệu..."
}
```

---

## IV. PHÂN TÍCH KẾT QUẢ

Script `analyze_bds500_results.py` sẽ in:

### 1. Thống Kê Theo Thuật Toán
```
GWO:
  Số ảnh: 200
  DICE:
    Mean:   0.6234
    Std:    0.0456
    Median: 0.6189
    Range:  [0.4567, 0.7890]
  Entropy:
    Mean:   0.0456
    Std:    0.0012
  Time:
    Mean:   12.34s
    Std:    2.45s
```

### 2. Ranking
```
RANKING (theo DICE mean)
1. HYBRID-PA3      DICE=0.6345 ± 0.0423
2. GWO             DICE=0.6234 ± 0.0456
3. HYBRID-PA1      DICE=0.6189 ± 0.0478
...
```

### 3. Best/Worst Images
```
Top 5 ảnh tốt nhất (DICE cao):
  img_0042: 0.7890 ± 0.0123
  img_0156: 0.7654 ± 0.0234
  ...

Top 5 ảnh khó nhất (DICE thấp):
  img_0089: 0.4567 ± 0.0345
  img_0123: 0.4789 ± 0.0456
  ...
```

### 4. Variance Analysis
```
Độ biến thiên giữa các thuật toán (theo ảnh):
  img_0089: std=0.0345, range=[0.4567, 0.5234]
  ...
```

---

## V. GIẢI THÍCH METRICS

### DICE Score
- **Range**: [0, 1]
- **Ý nghĩa**: Độ tương đồng giữa boundary dự đoán và ground truth
- **Cao hơn = tốt hơn**
- **Công thức**: `DICE = 2|A∩B| / (|A|+|B|)`

### Entropy (Fuzzy Entropy De Luca)
- **Range**: [0, ∞)
- **Ý nghĩa**: Độ không chắc chắn của phân đoạn
- **Cao hơn = nhiều thông tin hơn**
- **Lưu ý**: Không phải metric chất lượng trực tiếp

---

## VI. TÙỲ CHỈNH

### Thay Đổi Dataset Split

Sửa trong `eval_bds500_k10_seed42.py`:
```python
SPLIT = "test"  # "train", "val", hoặc "test"
```

### Giới Hạn Số Ảnh (Debug Nhanh)

```python
LIMIT = 10  # Chỉ chạy 10 ảnh đầu tiên
```

### Thêm/Bớt Thuật Toán

```python
ALGORITHMS = {
    "GWO": {"type": "GWO"},
    "WOA": {"type": "WOA"},
    # Bỏ comment để thêm
    # "HYBRID-PA1": {"type": "HYBRID", "strategy": "PA1"},
}
```

### Thay Đổi Tham Số Optimizer

```python
N_AGENTS = 50   # Tăng số cá thể
N_ITERS = 100   # Tăng số vòng lặp
```

---

## VII. BƯỚC TIẾP THEO (Nếu Muốn So Sánh Thuật Toán)

### 1. Chạy Nhiều Seeds

Tạo script mới `eval_bds500_multi_seed.py`:

```python
SEEDS = [42, 123, 456, 789, 1011, ...]  # 30 seeds

for seed in SEEDS:
    # Chạy đánh giá với mỗi seed
    # Lưu kết quả riêng
```

### 2. Tính Mean/Std Across Seeds

```python
# Với mỗi thuật toán
for algo in algorithms:
    dices_across_seeds = []
    for seed in seeds:
        dice = get_dice(algo, seed)
        dices_across_seeds.append(dice)
    
    mean_dice = np.mean(dices_across_seeds)
    std_dice = np.std(dices_across_seeds)
```

### 3. Statistical Test

```python
from scipy.stats import ttest_rel, wilcoxon

# Paired t-test
t_stat, p_value = ttest_rel(dices_algo1, dices_algo2)

# Wilcoxon signed-rank test (non-parametric)
w_stat, p_value = wilcoxon(dices_algo1, dices_algo2)

# Nếu p_value < 0.05 → có sự khác biệt có ý nghĩa
```

---

## VIII. CHECKLIST

### Trước Khi Chạy:
- [ ] Đã có dataset BDS500 trong `dataset/BDS500/`
- [ ] Đã cài đặt dependencies: `scipy`, `numpy`, `pyyaml`
- [ ] Đã kiểm tra cấu trúc thư mục đúng

### Sau Khi Chạy:
- [ ] Kiểm tra không có lỗi trong output
- [ ] Xem summary statistics
- [ ] Phân tích best/worst images
- [ ] Lưu ý: KHÔNG kết luận thuật toán nào tốt hơn

### Nếu Muốn Báo Cáo:
- [ ] Chạy nhiều seeds (ít nhất 30)
- [ ] Tính mean/std
- [ ] Làm statistical test
- [ ] Ghi rõ: "Results are averaged over 30 independent runs"

---

## IX. TROUBLESHOOTING

### Lỗi: "Không tìm thấy thư mục"
```bash
# Kiểm tra cấu trúc
ls dataset/BDS500/images/train/
ls dataset/BDS500/ground_truth/train/
```

### Lỗi: "Thiếu scipy"
```bash
pip install scipy
```

### Chạy quá lâu
```python
# Giảm số ảnh để test
LIMIT = 10

# Hoặc giảm số vòng lặp
N_ITERS = 40
```

### Out of Memory
```python
# Chạy từng batch nhỏ
# Hoặc giảm N_AGENTS
N_AGENTS = 20
```

---

## X. KẾT LUẬN

Script này cung cấp:
- ✅ Pipeline đánh giá hoàn chỉnh
- ✅ Kết quả reproducible (seed=42)
- ✅ Phân tích chi tiết

Nhưng nhớ:
- ⚠️ Chỉ 1 seed → không đủ để kết luận
- ⚠️ Cần nhiều seeds để so sánh thuật toán
- ⚠️ Cần statistical test để chứng minh

---

**Ngày tạo:** 2026-01-22  
**Người tạo:** Kiro AI Assistant

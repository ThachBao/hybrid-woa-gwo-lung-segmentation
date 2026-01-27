# Đánh Giá BDS500 - Quick Start

## ⚠️ QUAN TRỌNG

**K=10, Seed=42 chỉ dùng để DEBUG**
- ✅ Kiểm tra pipeline
- ✅ Reproducibility
- ❌ KHÔNG dùng để kết luận thuật toán nào tốt hơn

---

## Quick Start

### 1. Test Pipeline (Bắt Buộc)

```bash
python docs/test_bds500_pipeline.py
```

**Kết quả mong đợi:**
```
✓ TẤT CẢ TESTS ĐỀU PASS
Pipeline sẵn sàng để chạy đánh giá BDS500
```

---

### 2. Chạy Đánh Giá (Debug Mode)

```bash
# Chạy trên 10 ảnh đầu tiên (test nhanh)
# Sửa LIMIT=10 trong eval_bds500_k10_seed42.py

python -m src.runner.eval_bds500_k10_seed42
```

**Thời gian:**
- 10 ảnh: ~5-10 phút
- 200 ảnh (full train): ~2-3 giờ

---

### 3. Phân Tích Kết Quả

```bash
python -m src.runner.analyze_bds500_results \
    outputs/bds500_eval/k10_seed42_train_*/results_k10_seed42.json
```

---

## Cấu Trúc Files

```
src/
├── data/
│   ├── bsds500.py              # Load dataset (MỚI)
│   └── bsds500_gt.py           # GT utilities
├── runner/
│   ├── eval_bds500_k10_seed42.py      # Script chính (MỚI)
│   └── analyze_bds500_results.py      # Phân tích (MỚI)
└── ...

docs/
├── test_bds500_pipeline.py     # Test pipeline (MỚI)
└── EVAL_BDS500_K10_SEED42.md   # Hướng dẫn chi tiết (MỚI)
```

---

## Tùy Chỉnh

### Giới Hạn Số Ảnh (Debug Nhanh)

Sửa trong `eval_bds500_k10_seed42.py`:
```python
LIMIT = 10  # Chỉ chạy 10 ảnh
```

### Chọn Split

```python
SPLIT = "test"  # "train", "val", hoặc "test"
```

### Chọn Thuật Toán

```python
ALGORITHMS = {
    "GWO": {"type": "GWO"},
    # Bỏ comment để thêm
    # "WOA": {"type": "WOA"},
}
```

---

## Kết Quả

### Output Directory
```
outputs/bds500_eval/k10_seed42_train_YYYYMMDD_HHMMSS/
├── results_k10_seed42.json      # Chi tiết từng ảnh
└── summary_k10_seed42.json      # Thống kê tổng hợp
```

### Metrics
- **DICE**: [0, 1] - Cao hơn = tốt hơn
- **Entropy**: [0, ∞) - Thông tin về phân đoạn
- **Time**: Thời gian chạy (giây)

---

## Bước Tiếp Theo

### Để So Sánh Thuật Toán Đúng Cách:

1. **Chạy nhiều seeds** (ít nhất 30)
2. **Tính mean/std** của DICE
3. **Statistical test** (t-test, Wilcoxon)

### Ví dụ:

```python
SEEDS = [42, 123, 456, ..., 999]  # 30 seeds

for seed in SEEDS:
    # Chạy đánh giá
    # Lưu kết quả
    
# Tính mean/std across seeds
# Statistical test
```

---

## Troubleshooting

### "Không tìm thấy thư mục"
```bash
ls dataset/BDS500/images/train/
ls dataset/BDS500/ground_truth/train/
```

### "Thiếu scipy"
```bash
pip install scipy
```

### Chạy quá lâu
```python
LIMIT = 10      # Giảm số ảnh
N_ITERS = 40    # Giảm số vòng lặp
```

---

## Tài Liệu Chi Tiết

Xem: `docs/EVAL_BDS500_K10_SEED42.md`

---

**Ngày:** 2026-01-22  
**Trạng thái:** ✅ Sẵn sàng

# Tối ưu ngưỡng toàn cục trên BSDS500

## Mục đích

Tìm **1 bộ ngưỡng tốt nhất** để dùng cho tất cả ảnh trong dataset, thay vì tối ưu riêng cho từng ảnh.

## Quy trình 2 bước

### Bước 1: Học ngưỡng trên train set

```bash
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train \
  --k 10 \
  --algo HYBRID \
  --strategy PA3 \
  --n_agents 40 \
  --n_iters 150 \
  --limit 50 \
  --out_dir outputs/runs/my_thresholds
```

**Kết quả:**
- File `outputs/runs/my_thresholds/global_thresholds.json`
- Chứa ngưỡng tối ưu và mean DICE trên train

### Bước 2: Test ngưỡng trên test set

```bash
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test \
  --thresholds_json outputs/runs/my_thresholds/global_thresholds.json \
  --out_csv outputs/runs/my_thresholds/test_results.csv
```

**Kết quả:**
- Mean DICE trên test set
- So sánh với train DICE
- File CSV chi tiết

## Ví dụ nhanh (5 phút)

```bash
# Học trên 10 ảnh train
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train \
  --k 10 \
  --algo GWO \
  --n_agents 20 \
  --n_iters 50 \
  --limit 10 \
  --out_dir outputs/runs/quick_test

# Test trên 10 ảnh test
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test \
  --thresholds_json outputs/runs/quick_test/global_thresholds.json \
  --limit 10
```

## Ví dụ chất lượng cao (1-2 giờ)

```bash
# Học trên 100 ảnh train với HYBRID-PA3
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train \
  --k 10 \
  --algo HYBRID \
  --strategy PA3 \
  --n_agents 50 \
  --n_iters 200 \
  --limit 100 \
  --out_dir outputs/runs/best_thresholds

# Test trên toàn bộ test set (200 ảnh)
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test \
  --thresholds_json outputs/runs/best_thresholds/global_thresholds.json \
  --out_csv outputs/runs/best_thresholds/test_results.csv
```

## Tham số quan trọng

| Tham số | Mô tả | Giá trị khuyến nghị |
|---------|-------|---------------------|
| `--limit` | Số ảnh train | 50-100 (test nhanh), 200 (đầy đủ) |
| `--n_agents` | Số agents | 30-50 |
| `--n_iters` | Số iterations | 100-200 |
| `--algo` | Thuật toán | HYBRID (tốt nhất) |
| `--strategy` | Strategy | PA3 (tốt nhất) |

## Kết quả mong đợi

- **Train DICE**: 0.3 - 0.5 (càng cao càng tốt)
- **Test DICE**: Thường thấp hơn train 5-15%
- **Nếu chênh lệch > 20%**: Overfitting, cần tăng số ảnh train

## So sánh với cách cũ

| Tiêu chí | Cách cũ (Fuzzy Entropy) | Cách mới (Global DICE) |
|----------|-------------------------|------------------------|
| Objective | Maximize Entropy | Maximize DICE |
| Cần GT? | Không | Có |
| Kết quả | Tốt cho ảnh đơn lẻ | Tốt cho toàn dataset |
| Tốc độ | Nhanh | Chậm hơn |
| DICE score | Thấp hơn | Cao hơn |

## Xem thêm

- Chi tiết đầy đủ: `docs/GLOBAL_THRESHOLDS.md`
- Hướng dẫn BDS500: `HUONG_DAN_BDS500.md`

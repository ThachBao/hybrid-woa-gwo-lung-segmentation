# Hướng dẫn tối ưu ngưỡng toàn cục trên BSDS500

## Tổng quan

Có 2 cách tối ưu ngưỡng:

### 1. Tối ưu theo Fuzzy Entropy (cách cũ)
- **Mục tiêu**: Maximize Entropy của ảnh
- **Ưu điểm**: Không cần ground truth
- **Nhược điểm**: Không đảm bảo tốt nhất theo ground truth

### 2. Tối ưu theo Boundary-DICE (cách mới - KHUYẾN NGHỊ)
- **Mục tiêu**: Maximize DICE score với ground truth
- **Ưu điểm**: Tối ưu trực tiếp theo metric đánh giá
- **Nhược điểm**: Cần ground truth

## Quy trình tối ưu ngưỡng toàn cục

### Bước 1: Học ngưỡng tối ưu trên train set

Tìm 1 bộ ngưỡng tốt nhất cho toàn bộ train set (không phải từng ảnh riêng lẻ).

```bash
# Ví dụ 1: Chạy nhanh với 50 ảnh đầu tiên
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train \
  --k 10 \
  --algo GWO \
  --n_agents 30 \
  --n_iters 100 \
  --limit 50 \
  --out_dir outputs/runs/global_thresholds

# Ví dụ 2: Chạy đầy đủ với HYBRID-PA3 (tốt hơn nhưng lâu hơn)
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train \
  --k 10 \
  --algo HYBRID \
  --strategy PA3 \
  --n_agents 50 \
  --n_iters 200 \
  --limit 100 \
  --out_dir outputs/runs/global_thresholds_pa3

# Ví dụ 3: Chạy toàn bộ 200 ảnh train (MẤT NHIỀU GIỜ!)
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train \
  --k 10 \
  --algo HYBRID \
  --strategy PA3 \
  --n_agents 50 \
  --n_iters 300 \
  --out_dir outputs/runs/global_thresholds_full
```

**Tham số:**
- `--split`: train/val/test (dùng train để học)
- `--k`: Số ngưỡng (mặc định: 10)
- `--algo`: GWO/WOA/HYBRID
- `--strategy`: PA1/PA2/PA3/PA4/PA5 (cho HYBRID)
- `--n_agents`: Số agents (30-50)
- `--n_iters`: Số iterations (100-300)
- `--limit`: Giới hạn số ảnh (0 = tất cả)
- `--out_dir`: Thư mục lưu kết quả

**Kết quả:**
- File `global_thresholds.json` chứa ngưỡng tối ưu
- Hiển thị mean DICE trên train set

### Bước 2: Test ngưỡng trên test set

Dùng ngưỡng vừa học để đánh giá trên test set.

```bash
# Test ngưỡng vừa học
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test \
  --thresholds_json outputs/runs/global_thresholds/global_thresholds.json \
  --out_csv outputs/runs/global_thresholds/test_results.csv

# Test trên toàn bộ test set (200 ảnh)
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test \
  --thresholds_json outputs/runs/global_thresholds_pa3/global_thresholds.json \
  --out_csv outputs/runs/global_thresholds_pa3/test_results.csv

# Test nhanh với 10 ảnh đầu
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test \
  --thresholds_json outputs/runs/global_thresholds/global_thresholds.json \
  --limit 10
```

**Tham số:**
- `--split`: test/val (dùng test để đánh giá cuối cùng)
- `--thresholds_json`: File JSON chứa ngưỡng (từ bước 1)
- `--out_csv`: File CSV lưu kết quả chi tiết (optional)
- `--limit`: Giới hạn số ảnh test (0 = tất cả)

**Kết quả:**
- Mean DICE trên test set
- So sánh với train DICE
- File CSV chi tiết (nếu có `--out_csv`)

## Ví dụ đầy đủ

### Ví dụ 1: Test nhanh (5-10 phút)

```bash
# Bước 1: Học trên 20 ảnh train
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train \
  --k 10 \
  --algo GWO \
  --n_agents 20 \
  --n_iters 50 \
  --limit 20 \
  --out_dir outputs/runs/quick_test

# Bước 2: Test trên 10 ảnh test
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test \
  --thresholds_json outputs/runs/quick_test/global_thresholds.json \
  --limit 10
```

### Ví dụ 2: Chất lượng tốt (1-2 giờ)

```bash
# Bước 1: Học trên 100 ảnh train với HYBRID-PA3
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train \
  --k 10 \
  --algo HYBRID \
  --strategy PA3 \
  --n_agents 40 \
  --n_iters 150 \
  --limit 100 \
  --out_dir outputs/runs/quality_test

# Bước 2: Test trên toàn bộ test set
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test \
  --thresholds_json outputs/runs/quality_test/global_thresholds.json \
  --out_csv outputs/runs/quality_test/test_results.csv
```

### Ví dụ 3: Tốt nhất (nhiều giờ)

```bash
# Bước 1: Học trên toàn bộ 200 ảnh train
python -m src.runner.learn_global_thresholds_bsds500 \
  --split train \
  --k 10 \
  --algo HYBRID \
  --strategy PA3 \
  --n_agents 50 \
  --n_iters 300 \
  --out_dir outputs/runs/best_thresholds

# Bước 2: Test trên toàn bộ test set
python -m src.runner.eval_global_thresholds_bsds500 \
  --split test \
  --thresholds_json outputs/runs/best_thresholds/global_thresholds.json \
  --out_csv outputs/runs/best_thresholds/test_results.csv
```

## Kết quả mong đợi

### Train DICE
- **Tốt**: > 0.3
- **Rất tốt**: > 0.4
- **Xuất sắc**: > 0.5

### Test DICE
- Thường thấp hơn train DICE một chút (5-10%)
- Nếu chênh lệch quá lớn (>20%) → overfitting

## So sánh các thuật toán

| Thuật toán | Tốc độ | Chất lượng | Khuyến nghị |
|------------|--------|------------|-------------|
| GWO | Nhanh | Tốt | Test nhanh |
| WOA | Trung bình | Tốt | Cân bằng |
| HYBRID-PA1 | Trung bình | Rất tốt | Khuyến nghị |
| HYBRID-PA3 | Chậm | Xuất sắc | Kết quả tốt nhất |

## Tips

1. **Bắt đầu với test nhanh**: Dùng `--limit 20` và `--n_iters 50` để test
2. **Tăng dần**: Nếu kết quả tốt, tăng `--limit` và `--n_iters`
3. **Dùng HYBRID-PA3**: Cho kết quả tốt nhất (nhưng chậm hơn)
4. **Monitor progress**: Script sẽ in ra DICE mỗi 10 evaluations
5. **Lưu kết quả**: Luôn dùng `--out_csv` để lưu kết quả chi tiết

## Troubleshooting

**Q: Script chạy quá lâu?**
A: Giảm `--limit`, `--n_agents`, hoặc `--n_iters`

**Q: DICE quá thấp (<0.2)?**
A: Tăng `--n_iters` hoặc thử thuật toán khác (HYBRID-PA3)

**Q: Train DICE cao nhưng test DICE thấp?**
A: Overfitting. Tăng `--limit` (dùng nhiều ảnh train hơn)

**Q: Muốn so sánh nhiều thuật toán?**
A: Chạy nhiều lần với `--out_dir` khác nhau, sau đó so sánh test DICE

## File output

### global_thresholds.json
```json
{
  "k": 10,
  "thresholds": [5, 25, 45, 65, 85, 105, 125, 145, 165, 185],
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

### test_results.csv
```csv
index,image,gt,dice_boundary,mean_dice,std_dice
0,path/to/img1.jpg,path/to/gt1.mat,0.3234,,
1,path/to/img2.jpg,path/to/gt2.mat,0.3567,,
...
,,,,0.3401,0.0456
```

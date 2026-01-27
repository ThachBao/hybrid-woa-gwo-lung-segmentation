# Giải Thích Logs

## Logs Trong Script So Sánh

### 1. Script Cũ (`compare_gwo_woa_strategies.py`)

#### Logs Bắt Đầu
```
================================================================================
BẮT ĐẦU SO SÁNH GWO-WOA STRATEGIES
================================================================================
Số ảnh: 100
Strategies: PA1, PA2, PA3, PA4, PA5
k=10, n_agents=30, n_iters=80, seed=42
================================================================================
```

#### Logs Từng Ảnh
```
[1/100] Đang xử lý: image001.jpg
  Kích thước ảnh: (481, 321)
  [1/5] Strategy: PA1
    ✓ Hoàn thành trong 12.34s, FE=5.234567
  [2/5] Strategy: PA2
    ✓ Hoàn thành trong 13.45s, FE=5.198765
  ...
  ✓ Đã lưu kết quả ảnh 1/100
```

#### Logs Kết Thúc
```
================================================================================
Đang lưu kết quả vào CSV...
================================================================================
✅ HOÀN THÀNH!
================================================================================
Kết quả đã lưu tại:
  📁 outputs/compareGWO-WOA/k10_iters80_agents30_seed42_20260126_190000
  📄 results.csv
  📄 summary.json
  📁 per_image/ (100 files)
================================================================================
```

### 2. Script Mới (`compare_gwo_woa_seed_sweep.py`)

#### Logs Bắt Đầu
```
================================================================================
BẮT ĐẦU SEED SWEEP
================================================================================
Số ảnh: 100
Strategies: PA1, PA2, PA3, PA4, PA5
Seeds: 0 đến 30 (31 seeds)
k=10, n_agents=30, n_iters=100
Tổng số runs: 100 ảnh × 31 seeds × 5 strategies
================================================================================
```

#### Logs Từng Ảnh
```
================================================================================
[ẢNH 1/100] image001.jpg
================================================================================
Kích thước: (481, 321)

  [SEED 0] (1/31)
    [1/5] PA1 - 0.1% hoàn thành
      ✓ FE=5.234567, Time=12.34s
    [2/5] PA2 - 0.2% hoàn thành
      ✓ FE=5.198765, Time=13.45s
    ...
  
  [SEED 1] (2/31)
    [1/5] PA1 - 0.6% hoàn thành
      ✓ FE=5.245678, Time=12.56s
    ...

  ✓ Đã lưu kết quả ảnh 1/100
```

#### Logs PA5 Với Nhiều Share Intervals
```
  [SEED 0] (1/31)
    [5/5] PA5 (interval=1, 1/6) - 0.5% hoàn thành
      ✓ FE=5.198765, Time=14.23s
    [5/5] PA5 (interval=2, 2/6) - 0.6% hoàn thành
      ✓ FE=5.212345, Time=14.45s
    [5/5] PA5 (interval=3, 3/6) - 0.7% hoàn thành
      ✓ FE=5.234567, Time=14.67s
    ...
```

#### Logs Kết Thúc
```
================================================================================
Đang sắp xếp kết quả theo FE giảm dần...
Đang lưu results_sorted.csv...
Đang tạo summary...
Đang lưu summary_sorted.csv...

================================================================================
✅ HOÀN THÀNH SEED SWEEP!
================================================================================
Tổng số runs: 15500
Kết quả đã lưu tại:
  📁 outputs/compareGWO-WOA/SWEEP_k10_iters100_agents30_seed0-30_20260126_190000
  📄 results_sorted.csv (15500 dòng, đã sort theo FE giảm dần)
  📄 summary_sorted.csv (5 dòng, đã sort theo FE mean giảm dần)
  📄 config.json
  📁 per_image/ (100 files)

🏆 Strategy tốt nhất (theo FE mean):
  Strategy: PA3
  FE mean: 5.267890
  Jitter std mean: 0.000198
  Conv std mean: 0.000123
================================================================================
```

## Ý Nghĩa Các Logs

### Progress Percentage
```
[1/5] PA1 - 0.1% hoàn thành
```
- `[1/5]`: Strategy thứ 1 trong 5 strategies
- `0.1%`: Tiến trình tổng thể (số runs đã hoàn thành / tổng số runs)

### FE và Time
```
✓ FE=5.234567, Time=12.34s
```
- `FE`: Fuzzy Entropy tốt nhất tìm được (cao = tốt)
- `Time`: Thời gian chạy optimization (giây)

### Kết Quả Cuối
```
📄 results_sorted.csv (15500 dòng, đã sort theo FE giảm dần)
```
- Số dòng = số ảnh × số seeds × số strategies
- Ví dụ: 100 ảnh × 31 seeds × 5 strategies = 15,500 dòng

### Strategy Tốt Nhất
```
🏆 Strategy tốt nhất (theo FE mean):
  Strategy: PA3
  FE mean: 5.267890
  Jitter std mean: 0.000198
  Conv std mean: 0.000123
```
- Tự động hiển thị strategy có FE mean cao nhất
- Kèm theo các chỉ số ổn định

## Ước Tính Thời Gian

### Script Cũ (1 seed)
```
Số ảnh: 100
Strategies: 5
Thời gian mỗi run: ~12s

Tổng thời gian = 100 × 5 × 12s = 6000s ≈ 1.7 giờ
```

### Script Mới (31 seeds)
```
Số ảnh: 100
Strategies: 5
Seeds: 31
Thời gian mỗi run: ~12s

Tổng thời gian = 100 × 5 × 31 × 12s = 186,000s ≈ 52 giờ
```

### PA5 Share Interval Sweep (6 intervals)
```
Số ảnh: 100
Strategy: PA5 only
Seeds: 31
Intervals: 6
Thời gian mỗi run: ~14s

Tổng thời gian = 100 × 1 × 31 × 6 × 14s = 260,400s ≈ 72 giờ
```

## Tips Đọc Logs

### 1. Theo Dõi Tiến Trình
Nhìn vào `% hoàn thành` để biết còn bao lâu nữa.

### 2. Kiểm Tra FE
FE cao = tốt. Nếu FE quá thấp (< 1.0) có thể có vấn đề.

### 3. Kiểm Tra Time
Nếu time quá lâu (> 60s) có thể cần giảm n_agents hoặc n_iters.

### 4. Xem Strategy Tốt Nhất
Cuối cùng sẽ hiển thị strategy tốt nhất, không cần mở file CSV.

## Troubleshooting

### Logs Không Hiển Thị
**Nguyên nhân**: Output bị buffer

**Cách sửa**: Thêm `-u` flag:
```bash
python -u -m src.runner.compare_gwo_woa_seed_sweep ...
```

### Logs Quá Nhiều
**Nguyên nhân**: Chạy nhiều ảnh × nhiều seeds

**Cách sửa**: Redirect vào file:
```bash
python -m src.runner.compare_gwo_woa_seed_sweep ... > log.txt 2>&1
```

### Muốn Xem Logs Sau Khi Chạy
Logs được lưu trong terminal, có thể copy hoặc redirect vào file.

## Kết Luận

Logs giúp bạn:
- ✅ Biết tiến trình đang chạy đến đâu
- ✅ Ước tính thời gian còn lại
- ✅ Phát hiện lỗi sớm
- ✅ Xem kết quả ngay khi hoàn thành

Chúc bạn chạy thành công! 🎉

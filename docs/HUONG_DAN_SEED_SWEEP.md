# Hướng Dẫn Seed Sweep (Chạy 1 Lệnh = Seed 0..30)

## Mục Tiêu

Chạy so sánh PA1..PA5 với nhiều seeds (0-30) trong **1 lệnh duy nhất**, tự động:
- Cố định: 30 agents, 100 iterations
- Chỉ lưu: FE + Jitter Stability + Convergence Stability
- Tự động sort theo FE giảm dần
- Hỗ trợ quét share_interval cho PA5

## Lỗi PowerShell và Cách Sửa

### Lỗi: "run_compare_multi_seed.bat is not recognized"

**Nguyên nhân**: PowerShell không tự động tìm file trong thư mục hiện tại.

**Cách sửa**: Thêm `.\` trước tên file:

```powershell
# SAI
run_compare_multi_seed.bat

# ĐÚNG
.\run_sweep_full.bat
```

## Cách Chạy

### Option 1: Quick Test (Khuyến nghị)

**Windows PowerShell**:
```powershell
.\run_sweep_quick_test.bat
```

**Hoặc trực tiếp**:
```bash
python -m src.runner.compare_gwo_woa_seed_sweep ^
  --root dataset/BDS500/images/val ^
  --limit 5 ^
  --k 10 ^
  --n_agents 10 ^
  --n_iters 20 ^
  --seed_start 0 ^
  --seed_end 2
```

**Thời gian**: ~5-10 phút
**Mô tả**: 5 ảnh, 10 agents, 20 iters, 3 seeds (0-2)

### Option 2: Full Sweep (Chính thức)

**Windows PowerShell**:
```powershell
.\run_sweep_full.bat
```

**Hoặc trực tiếp**:
```bash
python -m src.runner.compare_gwo_woa_seed_sweep ^
  --root dataset/BDS500/images/val ^
  --k 10 ^
  --n_agents 30 ^
  --n_iters 100 ^
  --seed_start 0 ^
  --seed_end 30 ^
  --strategies PA1,PA2,PA3,PA4,PA5
```

**Thời gian**: ~30-60 giờ
**Mô tả**: Tất cả ảnh val, 30 agents, 100 iters, 31 seeds (0-30)

### Option 3: PA5 Share Interval Sweep

**Windows PowerShell**:
```powershell
.\run_sweep_pa5_intervals.bat
```

**Hoặc trực tiếp**:
```bash
python -m src.runner.compare_gwo_woa_seed_sweep ^
  --root dataset/BDS500/images/val ^
  --k 10 ^
  --n_agents 30 ^
  --n_iters 100 ^
  --seed_start 0 ^
  --seed_end 30 ^
  --strategies PA5 ^
  --pa5_share_intervals 1,2,3,5,10,20
```

**Thời gian**: ~30-60 giờ
**Mô tả**: Chỉ PA5, test 6 giá trị share_interval khác nhau

## Tham Số

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `--root` | (required) | Thư mục ảnh |
| `--k` | 10 | Số ngưỡng |
| `--n_agents` | 30 | Số agents (cố định) |
| `--n_iters` | 100 | Số iterations (cố định) |
| `--seed_start` | 0 | Seed bắt đầu |
| `--seed_end` | 30 | Seed kết thúc (inclusive) |
| `--strategies` | PA1,PA2,PA3,PA4,PA5 | Strategies |
| `--pa5_share_intervals` | "" | Share intervals cho PA5 (ví dụ: 1,2,3,5,10) |
| `--limit` | 0 | Giới hạn số ảnh (0 = tất cả) |

## Kết Quả

Thư mục kết quả: `outputs/compareGWO-WOA/SWEEP_k10_iters100_agents30_seed0-30_TIMESTAMP/`

```
├── results_sorted.csv       # Chi tiết, đã sort theo FE giảm dần
├── summary_sorted.csv       # Tóm tắt theo strategy, đã sort theo FE mean giảm dần
├── config.json              # Cấu hình chạy
└── per_image/               # Kết quả từng ảnh
    ├── 00000_image1.jpg.json
    └── ...
```

### results_sorted.csv

**Các cột**:
- `image_name` - Tên ảnh
- `strategy` - PA1, PA2, PA3, PA4, PA5
- `seed` - Seed (0-30)
- `pa5_share_interval` - Share interval (chỉ PA5)
- `fe_best` - FE tốt nhất (cao = tốt)
- `jitter_fe_std` - Độ ổn định jitter (thấp = ổn định)
- `conv_fe_last_std` - Độ ổn định convergence (thấp = mượt)

**Đã sort**: FE giảm dần (cao nhất ở đầu)

### summary_sorted.csv

**Các cột**:
- `strategy` - PA1, PA2, PA3, PA4, PA5
- `pa5_share_interval` - Share interval (chỉ PA5)
- `n_records` - Số records
- `fe_mean` - FE trung bình (cao = tốt)
- `fe_std` - FE std
- `jitter_fe_std_mean` - Jitter stability trung bình (thấp = ổn định)
- `conv_fe_last_std_mean` - Convergence stability trung bình (thấp = mượt)

**Đã sort**: FE mean giảm dần (cao nhất ở đầu)

## Phân Tích Kết Quả

### 1. Tìm Strategy Tốt Nhất

Mở `summary_sorted.csv`:
- Dòng đầu tiên = strategy tốt nhất (FE mean cao nhất)
- So sánh `jitter_fe_std_mean` và `conv_fe_last_std_mean` (thấp = tốt)

**Ví dụ**:
```csv
strategy,pa5_share_interval,n_records,fe_mean,fe_std,jitter_fe_std_mean,conv_fe_last_std_mean
PA3,,3100,5.267890,0.123456,0.000198,0.000123
PA1,,3100,5.234567,0.134567,0.000234,0.000156
PA5,1,3100,5.198765,0.145678,0.000345,0.000234
```

**Kết luận**: PA3 tốt nhất (FE cao nhất, ổn định nhất)

### 2. Tìm Share Interval Tốt Nhất Cho PA5

Chạy PA5 sweep, mở `summary_sorted.csv`:
- Lọc các dòng có `strategy = PA5`
- Dòng đầu tiên = share_interval tốt nhất

**Ví dụ**:
```csv
strategy,pa5_share_interval,n_records,fe_mean,fe_std,jitter_fe_std_mean,conv_fe_last_std_mean
PA5,3,3100,5.245678,0.123456,0.000210,0.000145
PA5,5,3100,5.234567,0.125678,0.000220,0.000150
PA5,1,3100,5.198765,0.134567,0.000345,0.000234
```

**Kết luận**: share_interval=3 tốt nhất cho PA5

## Lưu Ý Quan Trọng

### 1. Chạy từ thư mục gốc

```bash
cd Da_VerMoi
python -m src.runner.compare_gwo_woa_seed_sweep ...
```

### 2. PowerShell: Dùng `.\` trước tên file

```powershell
# ĐÚNG
.\run_sweep_full.bat

# SAI
run_sweep_full.bat
```

### 3. Seed 0-30 = 31 seeds

- `--seed_start 0 --seed_end 30` = 31 seeds (0, 1, 2, ..., 30)
- `--seed_start 0 --seed_end 29` = 30 seeds (0, 1, 2, ..., 29)

### 4. Thời gian chạy

- Quick test (5 ảnh, 3 seeds): ~5-10 phút
- Full sweep (all ảnh, 31 seeds): ~30-60 giờ
- PA5 intervals (6 intervals, 31 seeds): ~30-60 giờ

### 5. Kiểm tra ảnh val

```bash
ls dataset/BDS500/images/val/
```

Nếu rỗng → lỗi "Không tìm thấy ảnh"

## Troubleshooting

### Lỗi: "ModuleNotFoundError: No module named 'src'"

**Nguyên nhân**: Không chạy từ thư mục gốc

**Cách sửa**:
```bash
cd Da_VerMoi
python -m src.runner.compare_gwo_woa_seed_sweep ...
```

### Lỗi: "Không tìm thấy ảnh"

**Nguyên nhân**: Đường dẫn `--root` sai hoặc thư mục rỗng

**Cách sửa**: Kiểm tra:
```bash
ls dataset/BDS500/images/val/
```

### Lỗi: "Repair unique thất bại"

**Nguyên nhân**: k quá lớn so với miền ngưỡng

**Cách sửa**: Giảm k:
```bash
--k 5
```

## So Sánh Script Cũ vs Mới

### Script Cũ (`compare_gwo_woa_strategies.py`)

- Chạy 1 seed mỗi lần
- Cần vòng lặp bash để chạy nhiều seeds
- Lưu nhiều thông tin (thresholds, time, ...)
- Không sort tự động

### Script Mới (`compare_gwo_woa_seed_sweep.py`)

- ✅ Chạy nhiều seeds trong 1 lệnh
- ✅ Cố định 30 agents, 100 iterations
- ✅ Chỉ lưu FE + stability (gọn hơn)
- ✅ Tự động sort theo FE giảm dần
- ✅ Hỗ trợ quét share_interval cho PA5

## Kết Luận

Script mới giúp bạn:
1. Chạy 1 lệnh thay vì vòng lặp bash
2. Kết quả đã sort sẵn
3. Dễ phân tích (chỉ FE + stability)
4. Tìm share_interval tốt nhất cho PA5

Chúc bạn so sánh thành công! 🎉

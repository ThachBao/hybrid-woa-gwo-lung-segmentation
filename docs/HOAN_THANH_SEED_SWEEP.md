# ✅ Hoàn Thành: Seed Sweep Script

## Tóm Tắt

Đã tạo script mới `compare_gwo_woa_seed_sweep.py` theo yêu cầu:
- ✅ Chạy 1 lệnh = seed 0-30 (31 seeds)
- ✅ Cố định: 30 agents, 100 iterations
- ✅ Chỉ lưu: FE + Jitter Std + Conv Std
- ✅ Tự động sort theo FE giảm dần
- ✅ Hỗ trợ quét share_interval cho PA5

## Files Đã Tạo

### Script Chính
- ✅ `src/runner/compare_gwo_woa_seed_sweep.py`

### Scripts Windows
- ✅ `run_sweep_quick_test.bat` - Quick test (5 ảnh, 3 seeds)
- ✅ `run_sweep_full.bat` - Full sweep (all ảnh, 31 seeds)
- ✅ `run_sweep_pa5_intervals.bat` - PA5 share_interval sweep

### Tài Liệu
- ✅ `docs/HUONG_DAN_SEED_SWEEP.md` - Hướng dẫn chi tiết
- ✅ `README_SEED_SWEEP.md` - Quick start
- ✅ `docs/HOAN_THANH_SEED_SWEEP.md` - File này

## Sửa Lỗi PowerShell

### Lỗi Gặp Phải

```powershell
PS C:\Users\Admin\Desktop\Da_VerMoi> run_compare_multi_seed.bat
run_compare_multi_seed.bat : The term 'run_compare_multi_seed.bat' is not recognized...
```

### Nguyên Nhân

PowerShell không tự động tìm file trong thư mục hiện tại.

### Cách Sửa

Thêm `.\` trước tên file:

```powershell
# SAI
run_sweep_full.bat

# ĐÚNG
.\run_sweep_full.bat
```

## Cách Sử Dụng

### Quick Test (Khuyến nghị)

**PowerShell**:
```powershell
.\run_sweep_quick_test.bat
```

**Trực tiếp**:
```bash
python -m src.runner.compare_gwo_woa_seed_sweep ^
  --root dataset/BDS500/images/val ^
  --limit 5 --k 10 --n_agents 10 --n_iters 20 ^
  --seed_start 0 --seed_end 2
```

**Thời gian**: ~5-10 phút

### Full Sweep (Chính thức)

**PowerShell**:
```powershell
.\run_sweep_full.bat
```

**Trực tiếp**:
```bash
python -m src.runner.compare_gwo_woa_seed_sweep ^
  --root dataset/BDS500/images/val ^
  --k 10 --n_agents 30 --n_iters 100 ^
  --seed_start 0 --seed_end 30 ^
  --strategies PA1,PA2,PA3,PA4,PA5
```

**Thời gian**: ~30-60 giờ

### PA5 Share Interval Sweep

**PowerShell**:
```powershell
.\run_sweep_pa5_intervals.bat
```

**Trực tiếp**:
```bash
python -m src.runner.compare_gwo_woa_seed_sweep ^
  --root dataset/BDS500/images/val ^
  --k 10 --n_agents 30 --n_iters 100 ^
  --seed_start 0 --seed_end 30 ^
  --strategies PA5 ^
  --pa5_share_intervals 1,2,3,5,10,20
```

**Thời gian**: ~30-60 giờ

## Kết Quả

### Cấu Trúc Thư Mục

```
outputs/compareGWO-WOA/SWEEP_k10_iters100_agents30_seed0-30_TIMESTAMP/
├── results_sorted.csv       # Chi tiết, đã sort theo FE giảm dần
├── summary_sorted.csv       # Tóm tắt, đã sort theo FE mean giảm dần
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
- **Dòng đầu tiên** = strategy tốt nhất (FE mean cao nhất)
- So sánh `jitter_fe_std_mean` và `conv_fe_last_std_mean` (thấp = tốt)

**Ví dụ**:
```csv
strategy,pa5_share_interval,n_records,fe_mean,fe_std,jitter_fe_std_mean,conv_fe_last_std_mean
PA3,,3100,5.267890,0.123456,0.000198,0.000123
PA1,,3100,5.234567,0.134567,0.000234,0.000156
PA5,1,3100,5.198765,0.145678,0.000345,0.000234
```

**Kết luận**: **PA3 tốt nhất** (FE cao nhất, ổn định nhất)

### 2. Tìm Share Interval Tốt Nhất Cho PA5

Chạy PA5 sweep, mở `summary_sorted.csv`:
- Lọc các dòng có `strategy = PA5`
- **Dòng đầu tiên** = share_interval tốt nhất

**Ví dụ**:
```csv
strategy,pa5_share_interval,n_records,fe_mean,fe_std,jitter_fe_std_mean,conv_fe_last_std_mean
PA5,3,3100,5.245678,0.123456,0.000210,0.000145
PA5,5,3100,5.234567,0.125678,0.000220,0.000150
PA5,1,3100,5.198765,0.134567,0.000345,0.000234
```

**Kết luận**: **share_interval=3 tốt nhất** cho PA5

## Khác Biệt So Với Script Cũ

### Script Cũ (`compare_gwo_woa_strategies.py`)

- Chạy 1 seed mỗi lần
- Cần vòng lặp bash để chạy nhiều seeds
- Lưu nhiều thông tin (thresholds, time, ...)
- Không sort tự động
- Phù hợp: Chạy thử nghiệm nhanh

### Script Mới (`compare_gwo_woa_seed_sweep.py`)

- ✅ Chạy nhiều seeds trong 1 lệnh
- ✅ Cố định 30 agents, 100 iterations
- ✅ Chỉ lưu FE + stability (gọn hơn)
- ✅ Tự động sort theo FE giảm dần
- ✅ Hỗ trợ quét share_interval cho PA5
- ✅ Phù hợp: Chạy chính thức để so sánh

## Lưu Ý Quan Trọng

### 1. Chạy từ thư mục gốc

```bash
cd Da_VerMoi
python -m src.runner.compare_gwo_woa_seed_sweep ...
```

### 2. PowerShell: Dùng `.\` trước tên file

```powershell
.\run_sweep_full.bat
```

### 3. Seed 0-30 = 31 seeds

- `--seed_start 0 --seed_end 30` = **31 seeds** (0, 1, 2, ..., 30)
- `--seed_start 0 --seed_end 29` = **30 seeds** (0, 1, 2, ..., 29)

### 4. Thời gian chạy

- Quick test (5 ảnh, 3 seeds): ~5-10 phút
- Full sweep (all ảnh, 31 seeds): ~30-60 giờ
- PA5 intervals (6 intervals, 31 seeds): ~30-60 giờ

### 5. PA1-PA4: Không có tham số chuyển giao

Chỉ PA5 có `share_interval` (tần suất trao đổi best giữa 2 quần thể).

## Tài Liệu

- **Chi tiết**: `docs/HUONG_DAN_SEED_SWEEP.md`
- **Quick start**: `README_SEED_SWEEP.md`
- **Tóm tắt**: `docs/HOAN_THANH_SEED_SWEEP.md` (file này)

## Kết Luận

✅ Script seed sweep đã sẵn sàng!

Bạn có thể:
1. Chạy quick test để kiểm tra (~5 phút)
2. Chạy full sweep để so sánh chính thức (~30-60 giờ)
3. Chạy PA5 sweep để tìm share_interval tốt nhất (~30-60 giờ)

Kết quả đã được sort sẵn, dễ dàng phân tích!

Chúc bạn so sánh thành công! 🎉

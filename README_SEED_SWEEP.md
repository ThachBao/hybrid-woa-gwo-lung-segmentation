# Seed Sweep: So Sánh PA1-PA5 (1 Lệnh = Seed 0-30)

## ⚠️ Lỗi PowerShell và Cách Sửa

### Lỗi: "run_compare_multi_seed.bat is not recognized"

**Cách sửa**: Thêm `.\` trước tên file:

```powershell
# SAI
run_sweep_full.bat

# ĐÚNG
.\run_sweep_full.bat
```

## 🚀 Quick Start

### 1. Quick Test (5 phút)

```powershell
.\run_sweep_quick_test.bat
```

Hoặc:
```bash
python -m src.runner.compare_gwo_woa_seed_sweep ^
  --root dataset/BDS500/images/val ^
  --limit 5 --k 10 --n_agents 10 --n_iters 20 ^
  --seed_start 0 --seed_end 2
```

### 2. Full Sweep (30-60 giờ)

```powershell
.\run_sweep_full.bat
```

Hoặc:
```bash
python -m src.runner.compare_gwo_woa_seed_sweep ^
  --root dataset/BDS500/images/val ^
  --k 10 --n_agents 30 --n_iters 100 ^
  --seed_start 0 --seed_end 30 ^
  --strategies PA1,PA2,PA3,PA4,PA5
```

### 3. PA5 Share Interval Sweep (30-60 giờ)

```powershell
.\run_sweep_pa5_intervals.bat
```

Hoặc:
```bash
python -m src.runner.compare_gwo_woa_seed_sweep ^
  --root dataset/BDS500/images/val ^
  --k 10 --n_agents 30 --n_iters 100 ^
  --seed_start 0 --seed_end 30 ^
  --strategies PA5 ^
  --pa5_share_intervals 1,2,3,5,10,20
```

## 📊 Kết Quả

Thư mục: `outputs/compareGWO-WOA/SWEEP_k10_iters100_agents30_seed0-30_TIMESTAMP/`

- `results_sorted.csv` - Chi tiết, đã sort theo FE giảm dần
- `summary_sorted.csv` - Tóm tắt theo strategy, đã sort theo FE mean giảm dần
- `config.json` - Cấu hình
- `per_image/*.json` - Kết quả từng ảnh

## 🎯 Phân Tích

### Tìm Strategy Tốt Nhất

Mở `summary_sorted.csv` → Dòng đầu = tốt nhất

### Tìm Share Interval Tốt Nhất (PA5)

Chạy PA5 sweep → Mở `summary_sorted.csv` → Lọc PA5 → Dòng đầu = tốt nhất

## 📝 Đặc Điểm

- ✅ Cố định: 30 agents, 100 iterations
- ✅ Chỉ lưu: FE + Jitter Std + Conv Std
- ✅ Tự động sort theo FE giảm dần
- ✅ 1 lệnh = nhiều seeds (0-30)
- ✅ Hỗ trợ quét share_interval cho PA5

## 📚 Tài Liệu

Chi tiết: `docs/HUONG_DAN_SEED_SWEEP.md`

## 🔧 Files

- `src/runner/compare_gwo_woa_seed_sweep.py` - Script chính
- `run_sweep_*.bat` - Scripts Windows
- `docs/HUONG_DAN_SEED_SWEEP.md` - Hướng dẫn chi tiết

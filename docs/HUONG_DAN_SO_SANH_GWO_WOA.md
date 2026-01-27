# Hướng Dẫn So Sánh GWO-WOA Strategies (PA1..PA5)

## Mục Tiêu

So sánh các phương án kết hợp GWO-WOA (PA1, PA2, PA3, PA4, PA5) trên nhiều ảnh grayscale với các chỉ số:
- **FE Best**: FE tốt nhất tìm được
- **Jitter Stability**: Độ ổn định khi ngưỡng thay đổi nhỏ (±2 mức xám)
- **Convergence Stability**: Độ ổn định hội tụ (10 vòng lặp cuối)

## Cài Đặt

### 1. Vào thư mục project

```bash
cd Da_VerMoi
```

### 2. Tạo thư mục output (đã tạo sẵn)

```bash
mkdir -p outputs/compareGWO-WOA
```

## Cách Chạy

### Option 1: Quick Test (Khuyến nghị để test)

**Windows**:
```bash
run_compare_quick_test.bat
```

**Linux/Mac**:
```bash
python -m src.runner.compare_gwo_woa_strategies \
  --root dataset/BDS500/images/val \
  --out_root outputs/compareGWO-WOA \
  --limit 5 \
  --k 10 \
  --n_agents 10 \
  --n_iters 20 \
  --seed 42
```

**Thời gian**: ~5-10 phút
**Mô tả**: Chạy 5 ảnh, 10 agents, 20 iterations

### Option 2: Full Run (1 seed)

**Windows**:
```bash
run_compare_full.bat
```

**Linux/Mac**:
```bash
python -m src.runner.compare_gwo_woa_strategies \
  --root dataset/BDS500/images/val \
  --out_root outputs/compareGWO-WOA \
  --k 10 \
  --n_agents 30 \
  --n_iters 80 \
  --seed 42
```

**Thời gian**: ~1-2 giờ (tùy số ảnh)
**Mô tả**: Chạy tất cả ảnh trong val, 30 agents, 80 iterations

### Option 3: Multi-Seed (30 seeds)

**Windows**:
```bash
run_compare_multi_seed.bat
```

**Linux/Mac**:
```bash
for seed in $(seq 0 29); do
  python -m src.runner.compare_gwo_woa_strategies \
    --root dataset/BDS500/images/val \
    --out_root outputs/compareGWO-WOA \
    --k 10 \
    --n_agents 30 \
    --n_iters 80 \
    --seed "$seed"
done
```

**Thời gian**: ~30-60 giờ (30 lần × 1-2 giờ)
**Mô tả**: Chạy 30 lần với seed khác nhau (0..29)

### Option 4: Multi-Seed Quick Test

**Windows**:
```bash
run_compare_multi_seed_quick.bat
```

**Linux/Mac**:
```bash
for seed in $(seq 0 29); do
  python -m src.runner.compare_gwo_woa_strategies \
    --root dataset/BDS500/images/val \
    --out_root outputs/compareGWO-WOA \
    --limit 5 \
    --k 10 \
    --n_agents 10 \
    --n_iters 20 \
    --seed "$seed"
done
```

**Thời gian**: ~2-5 giờ (30 lần × 5-10 phút)
**Mô tả**: Chạy 30 lần với 5 ảnh, 10 agents, 20 iterations

## Tham Số

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `--root` | (required) | Thư mục chứa ảnh grayscale |
| `--out_root` | `outputs/compareGWO-WOA` | Thư mục lưu kết quả |
| `--limit` | 0 | Giới hạn số ảnh (0 = tất cả) |
| `--k` | 10 | Số ngưỡng |
| `--n_agents` | 30 | Số agents |
| `--n_iters` | 80 | Số iterations |
| `--seed` | 42 | Random seed |
| `--lb` | 0 | Lower bound |
| `--ub` | 255 | Upper bound |
| `--woa_b` | 1.0 | WOA parameter b |
| `--share_interval` | 1 | Share interval |
| `--strategies` | `PA1,PA2,PA3,PA4,PA5` | Strategies to compare |
| `--jitter_samples` | 20 | Số mẫu jitter |
| `--jitter_delta` | 2 | Delta jitter (±2) |
| `--jitter_seed` | 42 | Seed cho jitter |
| `--conv_last_w` | 10 | Window size cho convergence |

## Kết Quả

Mỗi lần chạy tạo một thư mục trong `outputs/compareGWO-WOA/`:

```
outputs/compareGWO-WOA/
└── k10_iters80_agents30_seed42_20260126_190000/
    ├── results.csv          # Kết quả chi tiết (mỗi dòng = 1 ảnh × 1 strategy)
    ├── summary.json         # Tóm tắt theo strategy
    └── per_image/           # Kết quả từng ảnh
        ├── 00000_image1.jpg.json
        ├── 00001_image2.jpg.json
        └── ...
```

### results.csv

Mỗi dòng chứa:
- `image_index`, `image_name`, `image_path`
- `strategy` (PA1, PA2, PA3, PA4, PA5)
- `k`, `n_agents`, `n_iters`, `seed`
- `fe_best` - FE tốt nhất
- `time_sec` - Thời gian chạy
- `thresholds` - Ngưỡng tìm được
- `jitter_fe_original`, `jitter_fe_mean`, `jitter_fe_std`, `jitter_fe_min`, `jitter_fe_max`
- `conv_fe_first`, `conv_fe_last`, `conv_fe_last_mean`, `conv_fe_last_std`, `conv_fe_improvement`

### summary.json

```json
{
  "config": {
    "root": "dataset/BDS500/images/val",
    "n_images": 100,
    "k": 10,
    "n_agents": 30,
    "n_iters": 80,
    "seed": 42,
    "strategies": ["PA1", "PA2", "PA3", "PA4", "PA5"]
  },
  "by_strategy": {
    "PA1": {
      "n_images": 100,
      "fe_mean": 5.234567,
      "fe_std": 0.123456,
      "jitter_std_mean": 0.000234,
      "conv_last_std_mean": 0.000156,
      "time_mean_sec": 12.34
    },
    "PA2": { ... },
    ...
  }
}
```

### per_image/*.json

Mỗi file chứa kết quả của 1 ảnh cho tất cả strategies:

```json
{
  "image_index": 0,
  "image_path": "dataset/BDS500/images/val/image1.jpg",
  "k": 10,
  "strategies": {
    "PA1": {
      "fe_best": 5.234567,
      "thresholds": [25, 50, 75, 100, 125, 150, 175, 200, 225, 250],
      "time_sec": 12.34,
      "stability_jitter": {
        "fe_original": 5.234567,
        "fe_mean": 5.234890,
        "fe_std": 0.000234,
        "fe_min": 5.234000,
        "fe_max": 5.235000
      },
      "stability_convergence": {
        "fe_first": 4.500000,
        "fe_last": 5.234567,
        "fe_last_mean": 5.234500,
        "fe_last_std": 0.000156,
        "fe_improvement": 0.734567
      }
    },
    "PA2": { ... },
    ...
  }
}
```

## Phân Tích Kết Quả

### 1. So sánh FE Mean

Strategy nào có `fe_mean` cao nhất → Tối ưu tốt nhất

### 2. So sánh Jitter Stability

Strategy nào có `jitter_std_mean` thấp nhất → Ổn định nhất với nhiễu ngưỡng

### 3. So sánh Convergence Stability

Strategy nào có `conv_last_std_mean` thấp nhất → Hội tụ mượt nhất

### 4. So sánh Thời gian

Strategy nào có `time_mean_sec` thấp nhất → Nhanh nhất

## Ví Dụ Phân Tích

Giả sử `summary.json` có:

```json
{
  "by_strategy": {
    "PA1": {
      "fe_mean": 5.234567,
      "jitter_std_mean": 0.000234,
      "conv_last_std_mean": 0.000156,
      "time_mean_sec": 12.34
    },
    "PA2": {
      "fe_mean": 5.198765,
      "jitter_std_mean": 0.000345,
      "conv_last_std_mean": 0.000234,
      "time_mean_sec": 13.45
    },
    "PA3": {
      "fe_mean": 5.267890,
      "jitter_std_mean": 0.000198,
      "conv_last_std_mean": 0.000123,
      "time_mean_sec": 11.23
    }
  }
}
```

**Kết luận**:
- **FE tốt nhất**: PA3 (5.267890) 🏆
- **Ổn định jitter tốt nhất**: PA3 (0.000198) 🏆
- **Hội tụ mượt nhất**: PA3 (0.000123) 🏆
- **Nhanh nhất**: PA3 (11.23s) 🏆

→ **PA3 là strategy tốt nhất!**

## Lưu Ý

### Thời gian chạy

- **Quick test**: ~5-10 phút
- **Full run (1 seed)**: ~1-2 giờ
- **Multi-seed (30 seeds)**: ~30-60 giờ
- **Multi-seed quick**: ~2-5 giờ

### Số lượng seed

- `seq 0 29` = 30 seeds (0, 1, 2, ..., 29)
- `seq 0 30` = 31 seeds (0, 1, 2, ..., 30)

### Chọn strategies

Mặc định chạy tất cả PA1..PA5. Để chạy một số strategies:

```bash
python -m src.runner.compare_gwo_woa_strategies \
  --root dataset/BDS500/images/val \
  --strategies "PA1,PA3,PA5" \
  ...
```

## Troubleshooting

### Lỗi: "Không tìm thấy ảnh"

Kiểm tra đường dẫn `--root` có đúng không:

```bash
ls dataset/BDS500/images/val/
```

### Lỗi: "Module not found"

Chạy từ thư mục gốc của project:

```bash
cd Da_VerMoi
python -m src.runner.compare_gwo_woa_strategies ...
```

### Chạy quá lâu

Giảm số ảnh, agents, hoặc iterations:

```bash
--limit 5 --n_agents 10 --n_iters 20
```

## Files Liên Quan

- `src/runner/compare_gwo_woa_strategies.py` - Script chính
- `run_compare_quick_test.bat` - Quick test (Windows)
- `run_compare_full.bat` - Full run (Windows)
- `run_compare_multi_seed.bat` - Multi-seed (Windows)
- `run_compare_multi_seed_quick.bat` - Multi-seed quick (Windows)
- `docs/HUONG_DAN_SO_SANH_GWO_WOA.md` - Tài liệu này

## Kết Luận

Script này giúp bạn so sánh các strategies PA1..PA5 một cách toàn diện với các chỉ số:
- FE (chất lượng tối ưu)
- Jitter Stability (ổn định với nhiễu)
- Convergence Stability (ổn định hội tụ)
- Time (hiệu quả)

Chúc bạn so sánh thành công! 🎉

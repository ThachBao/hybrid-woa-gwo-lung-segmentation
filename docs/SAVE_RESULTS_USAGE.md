# Hướng dẫn: Lưu và xem lại kết quả

## Tổng quan

Mỗi khi chạy phân đoạn ảnh qua Web UI, kết quả sẽ tự động được lưu vào thư mục `outputs/runs` để bạn có thể xem lại sau này.

## Cấu trúc thư mục

```
outputs/runs/
└── 20260122_100012_ui_46357eb8/          # Tên thư mục: timestamp_prefix_hash
    ├── config.yaml                        # Cấu hình đã dùng
    ├── summary.json                       # Tóm tắt kết quả
    ├── gray.png                           # Ảnh gốc (grayscale)
    ├── GWO/                               # Kết quả GWO
    │   ├── best.json                      # Ngưỡng tốt nhất
    │   ├── history.jsonl                  # Lịch sử convergence
    │   └── segmented.png                  # Ảnh phân đoạn
    ├── WOA/                               # Kết quả WOA
    │   ├── best.json
    │   ├── history.jsonl
    │   └── segmented.png
    └── HYBRID-PA3/                        # Kết quả Hybrid
        ├── best.json
        ├── history.jsonl
        └── segmented.png
```

## Tên thư mục

Format: `YYYYMMDD_HHMMSS_prefix_hash`

- `YYYYMMDD_HHMMSS`: Timestamp (năm-tháng-ngày_giờ-phút-giây)
- `prefix`: Nguồn ảnh
  - `ui`: Upload từ UI
  - `bds500`: Chọn từ BDS500 dataset
- `hash`: 8 ký tự random để tránh trùng

**Ví dụ**: `20260122_143052_ui_a3f7b2c1`

## Files trong mỗi run

### 1. `config.yaml` - Cấu hình

Chứa tất cả tham số đã dùng:

```yaml
image_name: uploaded
timestamp: '2026-01-22T14:30:52.123456'
k: 10
n_agents: 30
n_iters: 80
seed: 42
woa_b: 1.0
share_interval: 1
use_penalties: true
penalty_mode: balanced
algorithms:
  - GWO
  - WOA
  - HYBRID-PA3
```

### 2. `summary.json` - Tóm tắt

Tóm tắt kết quả tất cả thuật toán:

```json
{
  "image_name": "uploaded",
  "timestamp": "2026-01-22T14:30:52.123456",
  "total_time": 45.67,
  "best_overall_algo": "HYBRID-PA3",
  "best_overall_f": -0.048234,
  "best_overall_entropy": 0.048234,
  "results": {
    "GWO": {
      "entropy": 0.047123,
      "time": 12.34,
      "metrics": {
        "psnr": 28.45,
        "ssim": 0.8234,
        "dice": 0.4567
      }
    },
    "WOA": {
      "entropy": 0.046789,
      "time": 13.21,
      "metrics": {...}
    },
    "HYBRID-PA3": {
      "entropy": 0.048234,
      "time": 15.89,
      "metrics": {...}
    }
  }
}
```

### 3. `gray.png` - Ảnh gốc

Ảnh grayscale gốc đã được xử lý.

### 4. Thư mục thuật toán (GWO, WOA, HYBRID-PA3, ...)

Mỗi thuật toán có thư mục riêng chứa:

#### `best.json` - Kết quả tốt nhất

```json
{
  "algorithm": "HYBRID-PA3",
  "thresholds": [12, 34, 56, 78, 90, 112, 134, 156, 178, 200],
  "best_f": -0.048234,
  "entropy": 0.048234,
  "time": 15.89,
  "metrics": {
    "psnr": 28.45,
    "ssim": 0.8234,
    "dice": 0.4567
  }
}
```

#### `history.jsonl` - Lịch sử convergence

Mỗi dòng là một iteration:

```jsonl
{"iter": 0, "best_f": -0.035123}
{"iter": 1, "best_f": -0.038456}
{"iter": 2, "best_f": -0.041234}
...
{"iter": 79, "best_f": -0.048234}
```

#### `segmented.png` - Ảnh phân đoạn

Ảnh sau khi áp dụng ngưỡng.

## Cách sử dụng

### 1. Chạy phân đoạn qua UI

```bash
python -m src.ui.app
```

Mở http://127.0.0.1:5000, upload ảnh và chạy phân đoạn.

### 2. Xem kết quả đã lưu

Kết quả tự động lưu vào `outputs/runs/`. Kiểm tra logs để biết đường dẫn:

```
✓ Kết quả đã lưu: outputs/runs/20260122_143052_ui_a3f7b2c1
```

### 3. Xem lại kết quả

#### Xem summary
```bash
cat outputs/runs/20260122_143052_ui_a3f7b2c1/summary.json
```

#### Xem config
```bash
cat outputs/runs/20260122_143052_ui_a3f7b2c1/config.yaml
```

#### Xem ngưỡng tốt nhất
```bash
cat outputs/runs/20260122_143052_ui_a3f7b2c1/GWO/best.json
```

#### Xem ảnh
```bash
# Windows
start outputs/runs/20260122_143052_ui_a3f7b2c1/gray.png
start outputs/runs/20260122_143052_ui_a3f7b2c1/GWO/segmented.png

# Linux/Mac
xdg-open outputs/runs/20260122_143052_ui_a3f7b2c1/gray.png
```

### 4. So sánh nhiều runs

```bash
# List tất cả runs
ls outputs/runs/

# So sánh entropy
jq '.best_overall_entropy' outputs/runs/*/summary.json

# So sánh thời gian
jq '.total_time' outputs/runs/*/summary.json
```

## Phân tích kết quả

### Python script để đọc kết quả

```python
import json
import yaml
from pathlib import Path

# Đọc run mới nhất
runs_dir = Path("outputs/runs")
latest_run = max(runs_dir.glob("*"), key=lambda p: p.stat().st_mtime)

print(f"Latest run: {latest_run.name}")

# Đọc config
with open(latest_run / "config.yaml") as f:
    config = yaml.safe_load(f)
print(f"Algorithms: {config['algorithms']}")

# Đọc summary
with open(latest_run / "summary.json") as f:
    summary = json.load(f)
print(f"Best algorithm: {summary['best_overall_algo']}")
print(f"Best entropy: {summary['best_overall_entropy']:.6f}")

# Đọc kết quả từng thuật toán
for algo in config['algorithms']:
    with open(latest_run / algo / "best.json") as f:
        best = json.load(f)
    print(f"\n{algo}:")
    print(f"  Entropy: {best['entropy']:.6f}")
    print(f"  Time: {best['time']:.2f}s")
    print(f"  Thresholds: {best['thresholds']}")
```

### Vẽ biểu đồ convergence

```python
import json
import matplotlib.pyplot as plt
from pathlib import Path

run_dir = Path("outputs/runs/20260122_143052_ui_a3f7b2c1")

plt.figure(figsize=(10, 6))

for algo_dir in run_dir.glob("*/"):
    if algo_dir.is_dir() and (algo_dir / "history.jsonl").exists():
        # Đọc history
        iters = []
        best_fs = []
        with open(algo_dir / "history.jsonl") as f:
            for line in f:
                data = json.loads(line)
                iters.append(data["iter"])
                best_fs.append(-data["best_f"])  # Convert to entropy
        
        # Vẽ
        plt.plot(iters, best_fs, label=algo_dir.name, marker='o', markersize=2)

plt.xlabel("Iteration")
plt.ylabel("Entropy")
plt.title("Convergence Comparison")
plt.legend()
plt.grid(True)
plt.savefig("convergence.png")
plt.show()
```

## Test tính năng

Chạy script test:

```bash
python test_save_results.py
```

Script sẽ kiểm tra:
- ✓ Thư mục outputs/runs tồn tại
- ✓ Run mới nhất có đầy đủ files
- ✓ Config.yaml có đầy đủ thông tin
- ✓ Summary.json có đầy đủ kết quả
- ✓ Mỗi thuật toán có thư mục riêng
- ✓ best.json có đầy đủ thông tin

## Quản lý kết quả

### Xóa runs cũ

```bash
# Xóa runs cũ hơn 7 ngày (Linux/Mac)
find outputs/runs -type d -mtime +7 -exec rm -rf {} +

# Xóa runs cụ thể
rm -rf outputs/runs/20260122_143052_ui_a3f7b2c1
```

### Backup kết quả

```bash
# Nén tất cả runs
tar -czf runs_backup.tar.gz outputs/runs/

# Nén run cụ thể
tar -czf run_20260122.tar.gz outputs/runs/20260122_*
```

### Tìm run tốt nhất

```bash
# Tìm run có entropy cao nhất
jq -r '[.best_overall_entropy, input_filename] | @tsv' outputs/runs/*/summary.json | sort -rn | head -1
```

## Lưu ý

1. **Tự động lưu**: Kết quả tự động lưu sau mỗi lần chạy phân đoạn
2. **Không ghi đè**: Mỗi run có thư mục riêng (timestamp + hash)
3. **Dung lượng**: Mỗi run ~1-5 MB tùy số thuật toán
4. **Lỗi lưu**: Nếu lưu thất bại, UI vẫn trả về kết quả (chỉ warning)
5. **CLI vs UI**: CLI đã lưu từ trước, UI mới thêm tính năng này

## Ví dụ thực tế

### Ví dụ 1: So sánh GWO vs WOA vs Hybrid

```bash
# Chạy UI
python -m src.ui.app

# Upload ảnh, chọn cả 3 thuật toán, chạy
# Kết quả lưu tại: outputs/runs/20260122_143052_ui_a3f7b2c1

# So sánh entropy
cat outputs/runs/20260122_143052_ui_a3f7b2c1/summary.json | jq '.results | to_entries | .[] | {algo: .key, entropy: .value.entropy}'
```

### Ví dụ 2: Test penalties

```bash
# Run 1: Không dùng penalties
# → outputs/runs/20260122_143052_ui_a3f7b2c1

# Run 2: Dùng penalties (balanced)
# → outputs/runs/20260122_143215_ui_b4e8c3d2

# So sánh
diff <(jq '.results.GWO.entropy' outputs/runs/20260122_143052_ui_a3f7b2c1/summary.json) \
     <(jq '.results.GWO.entropy' outputs/runs/20260122_143215_ui_b4e8c3d2/summary.json)
```

### Ví dụ 3: Đánh giá trên BDS500

```bash
# Chạy trên nhiều ảnh BDS500
# Mỗi ảnh tạo 1 run

# Tính DICE trung bình
jq -s 'map(.results.GWO.metrics.dice) | add / length' outputs/runs/20260122_*_bds500_*/summary.json
```

## Kết luận

Tính năng lưu kết quả giúp:
- ✅ Xem lại kết quả cũ
- ✅ So sánh nhiều runs
- ✅ Phân tích convergence
- ✅ Backup và chia sẻ
- ✅ Tái tạo kết quả (có config)

**Mọi kết quả đều được lưu tự động!** 🎉

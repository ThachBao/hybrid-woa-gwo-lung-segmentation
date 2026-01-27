# Tính năng mới: Tự động lưu kết quả ✅

## Tổng quan

Mỗi khi chạy phân đoạn ảnh qua Web UI, kết quả sẽ **tự động được lưu** vào `outputs/runs` để bạn có thể xem lại sau này.

## Tính năng

### 1. Tự động lưu kết quả
- ✅ Mỗi run tạo thư mục riêng với timestamp
- ✅ Lưu config, summary, ảnh gốc, ảnh phân đoạn
- ✅ Lưu kết quả từng thuật toán riêng biệt
- ✅ Lưu lịch sử convergence

### 2. Cấu trúc rõ ràng
```
outputs/runs/20260122_143052_ui_a3f7b2c1/
├── config.yaml          # Cấu hình
├── summary.json         # Tóm tắt
├── gray.png             # Ảnh gốc
├── GWO/
│   ├── best.json
│   ├── history.jsonl
│   └── segmented.png
├── WOA/
│   └── ...
└── HYBRID-PA3/
    └── ...
```

### 3. Dễ dàng xem lại
- Xem summary: `cat outputs/runs/.../summary.json`
- Xem config: `cat outputs/runs/.../config.yaml`
- Xem ảnh: `start outputs/runs/.../GWO/segmented.png`
- So sánh runs: `jq '.best_overall_entropy' outputs/runs/*/summary.json`

## Thay đổi code

### Files đã sửa

**`src/ui/app.py`**:
1. Thêm import `json`, `yaml`
2. Thêm hàm `_save_run_results()` - Lưu kết quả
3. Thêm hàm `_create_run_dir()` - Tạo thư mục run
4. Cập nhật `api_segment()` - Lưu kết quả sau khi chạy
5. Cập nhật `api_segment_bds500()` - Lưu kết quả sau khi chạy

### Hàm mới

#### `_create_run_dir(prefix="ui")`
Tạo thư mục cho run mới với format: `YYYYMMDD_HHMMSS_prefix_hash`

**Tham số**:
- `prefix`: "ui" (upload) hoặc "bds500" (dataset)

**Returns**: Đường dẫn thư mục (ví dụ: `outputs/runs/20260122_143052_ui_a3f7b2c1`)

#### `_save_run_results(run_dir, gray, results, params, image_name)`
Lưu tất cả kết quả vào thư mục run.

**Lưu gì**:
1. `config.yaml` - Tham số đã dùng
2. `summary.json` - Tóm tắt kết quả
3. `gray.png` - Ảnh gốc
4. Mỗi thuật toán:
   - `best.json` - Ngưỡng tốt nhất
   - `history.jsonl` - Lịch sử convergence
   - `segmented.png` - Ảnh phân đoạn

## Cách sử dụng

### 1. Chạy phân đoạn qua UI

```bash
python -m src.ui.app
```

Mở http://127.0.0.1:5000, upload ảnh và chạy phân đoạn.

### 2. Kiểm tra logs

Sau khi chạy xong, logs sẽ hiển thị:
```
✓ Kết quả đã lưu: outputs/runs/20260122_143052_ui_a3f7b2c1
```

### 3. Xem kết quả

```bash
# Xem summary
cat outputs/runs/20260122_143052_ui_a3f7b2c1/summary.json

# Xem config
cat outputs/runs/20260122_143052_ui_a3f7b2c1/config.yaml

# Xem ngưỡng GWO
cat outputs/runs/20260122_143052_ui_a3f7b2c1/GWO/best.json

# Xem ảnh
start outputs/runs/20260122_143052_ui_a3f7b2c1/GWO/segmented.png
```

## Ví dụ files

### `config.yaml`
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

### `summary.json`
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
    }
  }
}
```

### `GWO/best.json`
```json
{
  "algorithm": "GWO",
  "thresholds": [12, 34, 56, 78, 90, 112, 134, 156, 178, 200],
  "best_f": -0.047123,
  "entropy": 0.047123,
  "time": 12.34,
  "metrics": {
    "psnr": 28.45,
    "ssim": 0.8234,
    "dice": 0.4567
  }
}
```

### `GWO/history.jsonl`
```jsonl
{"iter": 0, "best_f": -0.035123}
{"iter": 1, "best_f": -0.038456}
{"iter": 2, "best_f": -0.041234}
...
{"iter": 79, "best_f": -0.047123}
```

## Test

Chạy script test:
```bash
python test_save_results.py
```

Script sẽ kiểm tra:
- ✓ Thư mục outputs/runs tồn tại
- ✓ Run mới nhất có đầy đủ files
- ✓ Config có đầy đủ thông tin
- ✓ Summary có đầy đủ kết quả
- ✓ Mỗi thuật toán có thư mục riêng

## So sánh với CLI

| Feature | CLI (run_single.py) | UI (app.py) |
|---------|---------------------|-------------|
| **Lưu kết quả** | ✅ Có từ trước | ✅ Mới thêm |
| **Thư mục** | `outputs/runs/YYYYMMDD_HHMMSS_ALGO_hash/` | `outputs/runs/YYYYMMDD_HHMMSS_prefix_hash/` |
| **Config** | `config_used.yaml` | `config.yaml` |
| **Summary** | Không có | `summary.json` ✅ |
| **Nhiều thuật toán** | 1 thuật toán/run | Nhiều thuật toán/run ✅ |
| **Ảnh gốc** | `gray.png` | `gray.png` |
| **Ảnh phân đoạn** | `segmented.png` | `ALGO/segmented.png` |
| **Best result** | `best.json` | `ALGO/best.json` |
| **History** | `history.jsonl` | `ALGO/history.jsonl` |

## Lợi ích

### 1. Xem lại kết quả cũ
Không cần chạy lại, chỉ cần mở file đã lưu.

### 2. So sánh nhiều runs
```bash
# So sánh entropy
jq '.best_overall_entropy' outputs/runs/*/summary.json

# So sánh thời gian
jq '.total_time' outputs/runs/*/summary.json

# Tìm run tốt nhất
jq -r '[.best_overall_entropy, input_filename] | @tsv' outputs/runs/*/summary.json | sort -rn | head -1
```

### 3. Phân tích convergence
```python
import json
import matplotlib.pyplot as plt

# Đọc history
with open("outputs/runs/.../GWO/history.jsonl") as f:
    history = [json.loads(line) for line in f]

# Vẽ biểu đồ
iters = [h["iter"] for h in history]
entropies = [-h["best_f"] for h in history]
plt.plot(iters, entropies)
plt.show()
```

### 4. Backup và chia sẻ
```bash
# Nén run
tar -czf run_20260122.tar.gz outputs/runs/20260122_*

# Chia sẻ
# Gửi file .tar.gz cho người khác
```

### 5. Tái tạo kết quả
Có config.yaml → Có thể chạy lại với cùng tham số.

## Lưu ý

1. **Tự động**: Không cần làm gì, kết quả tự động lưu
2. **Không ghi đè**: Mỗi run có thư mục riêng
3. **Dung lượng**: ~1-5 MB/run tùy số thuật toán
4. **Lỗi**: Nếu lưu thất bại, UI vẫn trả về kết quả (chỉ warning)
5. **Response**: API response có thêm field `run_dir`

## Response API

API response giờ có thêm field `run_dir`:

```json
{
  "k": 10,
  "gray_data_url": "data:image/png;base64,...",
  "results": {...},
  "best_overall_algo": "HYBRID-PA3",
  "best_overall_f": -0.048234,
  "total_time": 45.67,
  "run_dir": "outputs/runs/20260122_143052_ui_a3f7b2c1"
}
```

Frontend có thể hiển thị link để user biết kết quả đã lưu ở đâu.

## Tài liệu

Chi tiết xem: **[docs/SAVE_RESULTS_USAGE.md](docs/SAVE_RESULTS_USAGE.md)**

## Kết luận

✅ **Tính năng hoàn thành!**

- ✅ Tự động lưu kết quả mỗi run
- ✅ Cấu trúc rõ ràng, dễ xem lại
- ✅ Hỗ trợ nhiều thuật toán
- ✅ Lưu đầy đủ thông tin
- ✅ Dễ dàng so sánh và phân tích

**Mọi kết quả đều được lưu tự động!** 🎉

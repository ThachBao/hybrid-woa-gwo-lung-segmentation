# Changelog - BDS500 Integration

## Tính năng mới đã thêm

### 1. Module xử lý BDS500 Ground Truth
**File:** `src/data/bsds500_gt.py`

Các function chính:
- `read_bsds_gt_boundary_mask()`: Đọc boundary mask từ file .mat hoặc ảnh
- `seg_to_boundary_mask()`: Tạo boundary mask từ ảnh phân đoạn
- `dice_binary()`: Tính DICE score giữa 2 mask nhị phân
- `build_pairs()`: Ghép ảnh với ground truth theo tên file

### 2. API Endpoints mới
**File:** `src/ui/app.py`

#### GET `/api/bds500/list`
Lấy danh sách ảnh từ BDS500 dataset

**Parameters:**
- `split`: train/val/test (default: test)
- `limit`: số ảnh tối đa (default: 50)
- `random`: true/false - chọn ngẫu nhiên (default: false)

**Response:**
```json
{
  "split": "test",
  "total": 50,
  "images": [
    {
      "id": "100007",
      "name": "100007.jpg",
      "path": "dataset/BDS500/images/test/100007.jpg",
      "gt_path": "dataset/BDS500/ground_truth/test/100007.mat",
      "has_gt": true
    }
  ]
}
```

#### POST `/api/segment_bds500`
Phân đoạn ảnh từ BDS500 và tính DICE score

**Form Data:**
- `image_path`: đường dẫn ảnh
- `gt_path`: đường dẫn ground truth
- `n_agents`, `n_iters`, `seed`, `woa_b`, `share_interval`: tham số tối ưu
- `run_gwo`, `run_woa`, `run_hybrid`: thuật toán chạy
- `hybrid_strategies`: strategies cho hybrid
- `gt_thr`: threshold cho GT (default: 0.5)
- `gt_fuse`: cách gộp annotators (default: max)

**Response:** Giống `/api/segment` nhưng thêm:
- `has_ground_truth`: true/false
- `image_name`: tên file ảnh
- `metrics.dice`: DICE score (nếu có GT)

### 3. UI Updates
**Files:** `src/ui/templates/index.html`, `src/ui/static/index.css`, `src/ui/static/app.js`

**Tính năng:**
- Radio buttons để chọn nguồn ảnh: Upload hoặc BDS500
- Dropdown chọn split (test/train/val)
- Button "Tải danh sách" và "Chọn ngẫu nhiên"
- Danh sách ảnh có thể click để chọn
- Hiển thị DICE score trong kết quả (với background xanh lá)
- Hiển thị tên file ảnh khi chọn từ BDS500

### 4. Evaluation Script
**File:** `src/runner/eval_dice_bsds500.py`

Script để đánh giá DICE trên toàn bộ dataset

**Usage:**
```bash
python -m src.runner.eval_dice_bsds500 \
  --split test \
  --algo GWO \
  --k 10 \
  --n_agents 30 \
  --n_iters 80 \
  --limit 10 \
  --out_csv outputs/runs/dice_test_gwo.csv
```

**Output:** File CSV với các cột:
- index, image, gt, dice_boundary, best_f, thresholds, mean_dice

### 5. Documentation
**File:** `docs/BDS500_USAGE.md`

Hướng dẫn chi tiết:
- Cách sử dụng UI với BDS500
- Cách chạy evaluation script
- Giải thích DICE score
- Cấu trúc dataset
- Lưu ý và best practices

## Thay đổi trong code hiện có

### `src/ui/app.py`
- Thêm import: `read_image_gray`, `dice_binary`, các function từ `bsds500_gt`
- Thêm constants: `BDS500_ROOT`, `BDS500_IMAGES_ROOT`, `BDS500_GT_ROOT`
- Cập nhật logic tính metrics: thêm DICE khi có ground truth

### `src/ui/static/app.js`
- Thêm logic xử lý chọn nguồn ảnh
- Thêm function load danh sách BDS500
- Thêm function chọn ngẫu nhiên
- Cập nhật `displaySegmentationResults()` để hiển thị DICE
- Cập nhật form submit để gọi API phù hợp

### `src/ui/static/index.css`
- Thêm styles cho source selector
- Thêm styles cho BDS500 controls và list
- Thêm styles cho DICE metric (background xanh lá)

## Testing

### Test 1: Import module
```bash
python -c "from src.data.bsds500_gt import build_pairs; print('OK')"
```

### Test 2: Build pairs
```bash
python -c "from src.data.bsds500_gt import build_pairs; pairs = build_pairs('dataset/BDS500/images/test', 'dataset/BDS500/ground_truth/test'); print(f'Found {len(pairs)} pairs')"
```
Output: Found 200 pairs ✓

### Test 3: Read GT mask
```bash
python -c "from src.data.bsds500_gt import read_bsds_gt_boundary_mask; mask = read_bsds_gt_boundary_mask('dataset/BDS500/ground_truth/test/100007.mat'); print(f'Shape: {mask.shape}')"
```
Output: Shape: (321, 481) ✓

### Test 4: Eval script
```bash
python -m src.runner.eval_dice_bsds500 --split test --algo GWO --k 10 --n_agents 10 --n_iters 10 --limit 2 --out_csv src/outputs/runs/dice_test_demo.csv
```
Output: Mean DICE: 0.1114 ✓

## Dependencies

Tất cả dependencies đã có trong `requirements.txt`:
- `scipy>=1.10` - để đọc file .mat
- `numpy>=1.24` - xử lý array
- `opencv-python>=4.8` - đọc ảnh
- `Flask>=3.0` - web server

## Cấu trúc thư mục mới

```
src/
├── data/
│   ├── bsds500_gt.py          # NEW: BDS500 ground truth utilities
│   └── bsds500.py             # Existing
├── runner/
│   ├── eval_dice_bsds500.py   # NEW: Evaluation script
│   └── ...
└── ui/
    ├── app.py                 # UPDATED: Added BDS500 endpoints
    ├── static/
    │   ├── app.js             # UPDATED: BDS500 UI logic
    │   └── index.css          # UPDATED: BDS500 styles
    └── templates/
        └── index.html         # UPDATED: BDS500 UI elements

docs/
└── BDS500_USAGE.md            # NEW: Usage documentation

CHANGELOG_BDS500.md            # NEW: This file
```

## Cách sử dụng

### 1. Chạy UI
```bash
python -m src.ui.app
```
Mở: http://127.0.0.1:5000

### 2. Chọn ảnh từ BDS500
1. Chọn "🗂️ BDS500 Dataset"
2. Chọn split (test/train/val)
3. Click "🔄 Tải danh sách" hoặc "🎲 Chọn ngẫu nhiên"
4. Click vào ảnh để chọn
5. Chọn thuật toán và chạy

### 3. Đánh giá toàn bộ dataset
```bash
python -m src.runner.eval_dice_bsds500 \
  --split test \
  --algo HYBRID \
  --strategy PA3 \
  --k 10 \
  --n_agents 30 \
  --n_iters 80 \
  --out_csv outputs/runs/dice_test_pa3.csv
```

## Kết quả mong đợi

- **DICE score**: 0.0 - 1.0 (càng cao càng tốt)
- **Typical values**: 0.1 - 0.3 cho boundary detection
- **Good performance**: > 0.5

## Notes

1. DICE được tính trên **boundary mask**, không phải region mask
2. BSDS500 có nhiều annotators, script tự động gộp bằng max/mean
3. Chạy toàn bộ dataset mất nhiều thời gian, dùng `--limit` để test
4. DICE chỉ có khi chọn từ BDS500, không có khi upload ảnh

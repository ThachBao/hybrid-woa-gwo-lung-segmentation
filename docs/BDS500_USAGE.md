# Hướng dẫn sử dụng BDS500 Dataset

## Tính năng mới

### 1. Chọn ảnh từ BDS500 Dataset trong UI

UI hiện hỗ trợ 2 cách chọn ảnh:
- **Upload ảnh**: Upload ảnh từ máy tính (như trước)
- **BDS500 Dataset**: Chọn ảnh từ dataset BDS500 có sẵn

Khi chọn từ BDS500:
- Có thể chọn split: `test`, `train`, hoặc `val`
- Có thể tải danh sách ảnh hoặc chọn ngẫu nhiên
- Tự động tính **DICE score** (Boundary-DICE) với ground truth

### 2. DICE Score

**DICE (Boundary-DICE)** được tính khi:
- Chọn ảnh từ BDS500 dataset
- Ground truth có sẵn (file .mat)

DICE đo độ tương đồng giữa:
- Boundary mask từ ảnh phân đoạn (predicted)
- Boundary mask từ ground truth (BSDS500 annotations)

Công thức: `DICE = 2|A∩B| / (|A|+|B|)`

Giá trị DICE:
- 0.0 = không khớp
- 1.0 = khớp hoàn toàn
- Thường > 0.5 là tốt

### 3. Chạy UI

```bash
python -m src.ui.app
```

Mở trình duyệt: http://127.0.0.1:5000

**Các bước:**
1. Chọn "🗂️ BDS500 Dataset"
2. Chọn split (test/train/val)
3. Click "🔄 Tải danh sách" hoặc "🎲 Chọn ngẫu nhiên"
4. Click vào ảnh trong danh sách để chọn
5. Chọn thuật toán và tham số
6. Click "🚀 Chạy phân đoạn & Benchmark"

Kết quả sẽ hiển thị:
- PSNR, SSIM (so với ảnh gốc)
- **DICE** (so với ground truth) - chỉ khi chọn từ BDS500

## Đánh giá DICE trên toàn bộ dataset

### Chạy evaluation script

```bash
# Test split với GWO
python -m src.runner.eval_dice_bsds500 \
  --split test \
  --algo GWO \
  --k 10 \
  --n_agents 30 \
  --n_iters 80 \
  --limit 10 \
  --out_csv outputs/runs/dice_test_gwo.csv

# Test split với HYBRID-PA3
python -m src.runner.eval_dice_bsds500 \
  --split test \
  --algo HYBRID \
  --strategy PA3 \
  --k 10 \
  --n_agents 30 \
  --n_iters 80 \
  --limit 10 \
  --out_csv outputs/runs/dice_test_pa3.csv

# Train split với WOA
python -m src.runner.eval_dice_bsds500 \
  --split train \
  --algo WOA \
  --k 10 \
  --n_agents 30 \
  --n_iters 80 \
  --limit 10 \
  --out_csv outputs/runs/dice_train_woa.csv
```

### Tham số

- `--images_root`: Thư mục chứa ảnh (mặc định: `dataset/BDS500/images`)
- `--gt_root`: Thư mục chứa ground truth (mặc định: `dataset/BDS500/ground_truth`)
- `--split`: Split để đánh giá (`test`, `train`, `val`)
- `--algo`: Thuật toán (`GWO`, `WOA`, `HYBRID`)
- `--strategy`: Strategy cho HYBRID (`PA1`, `PA2`, `PA3`, `PA4`, `PA5`)
- `--k`: Số ngưỡng (mặc định: 10)
- `--n_agents`: Số agents (mặc định: 30)
- `--n_iters`: Số iterations (mặc định: 80)
- `--seed`: Random seed (mặc định: 0)
- `--limit`: Giới hạn số ảnh (0 = tất cả)
- `--gt_thr`: Threshold cho GT boundary (mặc định: 0.5)
- `--gt_fuse`: Cách gộp nhiều annotators (`max` hoặc `mean`)
- `--out_csv`: File CSV output

### Kết quả

File CSV sẽ chứa:
- `index`: Thứ tự ảnh
- `image`: Đường dẫn ảnh
- `gt`: Đường dẫn ground truth
- `dice_boundary`: DICE score
- `best_f`: Best fitness value
- `thresholds`: Các ngưỡng tìm được
- `mean_dice`: Mean DICE (dòng cuối)

## Cấu trúc Dataset

```
dataset/BDS500/
├── images/
│   ├── test/     (200 ảnh)
│   ├── train/    (200 ảnh)
│   └── val/      (100 ảnh)
└── ground_truth/
    ├── test/     (200 file .mat)
    ├── train/    (200 file .mat)
    └── val/      (100 file .mat)
```

## Lưu ý

1. **DICE vs PSNR/SSIM**:
   - DICE: Đo độ chính xác boundary (cần ground truth)
   - PSNR/SSIM: Đo độ tương đồng với ảnh gốc (không cần ground truth)

2. **Boundary-DICE**:
   - BSDS500 ground truth là boundary annotations
   - DICE được tính trên boundary mask, không phải region mask
   - Phù hợp cho bài toán edge detection và segmentation

3. **Performance**:
   - Chạy toàn bộ test split (200 ảnh) mất ~2-3 giờ với n_iters=80
   - Dùng `--limit` để test nhanh với số ảnh nhỏ hơn
   - Tăng `n_agents` và `n_iters` để cải thiện kết quả

4. **Ground Truth Format**:
   - File .mat chứa struct `groundTruth` với nhiều annotators
   - Mỗi annotator có `Boundaries` (boundary mask)
   - Script tự động gộp nhiều annotators thành 1 mask

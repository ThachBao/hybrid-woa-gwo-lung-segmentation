# Hướng dẫn sử dụng BDS500 Dataset

## Tính năng mới

Bạn có thể chọn ảnh từ dataset BDS500 có sẵn thay vì upload ảnh. Khi chọn từ BDS500, hệ thống sẽ tự động tính **DICE score** để đánh giá độ chính xác của phân đoạn so với ground truth.

## Cách sử dụng trong UI

### Bước 1: Chạy ứng dụng
```bash
python -m src.ui.app
```

Mở trình duyệt: http://127.0.0.1:5000

### Bước 2: Chọn nguồn ảnh
- Chọn **"🗂️ BDS500 Dataset"** thay vì "📤 Upload ảnh"

### Bước 3: Chọn split
- **Test**: 200 ảnh để test
- **Train**: 200 ảnh để train
- **Val**: 100 ảnh để validation

### Bước 4: Tải danh sách hoặc chọn ngẫu nhiên
- **🔄 Tải danh sách**: Hiển thị tối đa 50 ảnh đầu tiên
- **🎲 Chọn ngẫu nhiên**: Chọn 1 ảnh ngẫu nhiên

### Bước 5: Chọn ảnh
- Click vào ảnh trong danh sách (ảnh được chọn sẽ có màu tím)

### Bước 6: Chọn thuật toán và tham số
- Chọn GWO, WOA, hoặc HYBRID
- Điều chỉnh n_agents, n_iters, v.v.

### Bước 7: Chạy
- Click **"🚀 Chạy phân đoạn & Benchmark"**

### Kết quả
Kết quả sẽ hiển thị:
- **PSNR**: Peak Signal-to-Noise Ratio (so với ảnh gốc)
- **SSIM**: Structural Similarity Index (so với ảnh gốc)
- **DICE**: Dice Coefficient (so với ground truth) - **CHỈ CÓ KHI CHỌN TỪ BDS500**

DICE score càng cao càng tốt (0.0 - 1.0):
- < 0.3: Kém
- 0.3 - 0.5: Trung bình
- 0.5 - 0.7: Tốt
- > 0.7: Rất tốt

## Đánh giá trên toàn bộ dataset

Nếu muốn đánh giá trên nhiều ảnh cùng lúc:

```bash
# Đánh giá 10 ảnh đầu tiên trong test set với GWO
python -m src.runner.eval_dice_bsds500 \
  --split test \
  --algo GWO \
  --k 10 \
  --n_agents 30 \
  --n_iters 80 \
  --limit 10 \
  --out_csv outputs/runs/dice_test_gwo.csv

# Đánh giá với HYBRID-PA3
python -m src.runner.eval_dice_bsds500 \
  --split test \
  --algo HYBRID \
  --strategy PA3 \
  --k 10 \
  --n_agents 30 \
  --n_iters 80 \
  --limit 10 \
  --out_csv outputs/runs/dice_test_pa3.csv
```

Kết quả sẽ được lưu vào file CSV với các thông tin:
- Tên ảnh
- DICE score
- Best fitness value
- Các ngưỡng tìm được
- Mean DICE (trung bình)

## Lưu ý

1. **DICE chỉ có khi chọn từ BDS500**: Nếu upload ảnh thì chỉ có PSNR và SSIM
2. **Thời gian chạy**: Mỗi ảnh mất khoảng 30-60 giây tùy vào n_agents và n_iters
3. **Chạy toàn bộ dataset**: 200 ảnh mất ~2-3 giờ, nên dùng `--limit` để test trước
4. **DICE là Boundary-DICE**: Đo độ chính xác của boundary, không phải region

## Ví dụ kết quả

```
[1/10] Processing: 100007.jpg
  best_f=-0.050102, DICE=0.0788

[2/10] Processing: 100039.jpg
  best_f=-0.044363, DICE=0.1439

...

Mean DICE (Boundary): 0.1114
```

## Cấu trúc dataset

```
dataset/BDS500/
├── images/
│   ├── test/     (200 ảnh .jpg)
│   ├── train/    (200 ảnh .jpg)
│   └── val/      (100 ảnh .jpg)
└── ground_truth/
    ├── test/     (200 file .mat)
    ├── train/    (200 file .mat)
    └── val/      (100 file .mat)
```

Mỗi file .mat chứa boundary annotations từ nhiều người (annotators), hệ thống tự động gộp lại thành 1 mask.

## Câu hỏi thường gặp

**Q: Tại sao DICE score thấp?**
A: DICE đo boundary, không phải region. Boundary detection khó hơn region segmentation. DICE > 0.3 đã là tốt.

**Q: Có thể tăng DICE không?**
A: Có, tăng n_agents và n_iters, hoặc thử các thuật toán khác nhau (HYBRID thường tốt hơn).

**Q: Tại sao không có DICE khi upload ảnh?**
A: Vì không có ground truth. DICE chỉ tính được khi có ground truth từ BDS500.

**Q: Có thể thêm ảnh của mình vào BDS500 không?**
A: Có, nhưng cần tạo ground truth (file .mat) theo format của BSDS500.

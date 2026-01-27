# Image Segmentation with Fuzzy Entropy & Metaheuristic Optimization

Hệ thống phân đoạn ảnh sử dụng Fuzzy Entropy kết hợp với các thuật toán tối ưu metaheuristic (GWO, WOA, Hybrid) và penalties để tránh dồn ngưỡng.

## 📋 Mục lục

- [Tính năng](#-tính-năng)
- [Cài đặt](#-cài-đặt)
- [Chạy ứng dụng](#-chạy-ứng-dụng)
- [Hướng dẫn sử dụng](#-hướng-dẫn-sử-dụng)
- [Chạy scripts](#-chạy-scripts)
- [Tài liệu](#-tài-liệu)
- [Cấu trúc thư mục](#-cấu-trúc-thư-mục)

## ✨ Tính năng

### 1. Phân đoạn ảnh với Fuzzy Entropy
- Tối ưu ngưỡng phân đoạn đa mức (k=10 ngưỡng)
- 3 thuật toán: GWO, WOA, Hybrid (PA1-PA5)
- Tự động chạy benchmark trên 18 hàm chuẩn

### 2. Penalties để tránh dồn ngưỡng
- ✅ Ép khoảng cách tối thiểu giữa ngưỡng
- ✅ Tránh vùng rỗng (< 1% pixels)
- ✅ Khuyến khích phân bố đều
- ✅ 3 chế độ: Light / Balanced / Strong

### 3. Tích hợp BDS500 Dataset
- Chọn ảnh từ train/val/test split
- Tính DICE score với ground truth
- Đánh giá chất lượng phân đoạn

### 4. Tối ưu ngưỡng toàn cục
- Học ngưỡng tốt nhất trên tập train
- Đánh giá trên tập test
- Tối ưu theo Boundary-DICE

### 5. Giao diện Web
- Upload ảnh hoặc chọn từ BDS500
- Chọn thuật toán và tham số
- Hiển thị kết quả phân đoạn
- So sánh nhiều thuật toán
- Xem benchmark results
- **Tự động lưu kết quả vào outputs/runs** ⭐ MỚI

## 🔧 Cài đặt

### Yêu cầu hệ thống
- Python 3.8+
- Windows/Linux/MacOS

### Bước 1: Clone repository
```bash
git clone <repository-url>
cd <project-folder>
```

### Bước 2: Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### Dependencies chính:
- `numpy` - Tính toán số học
- `scipy` - Đọc file .mat (ground truth)
- `Pillow` - Xử lý ảnh
- `Flask` - Web framework
- `scikit-image` - Metrics (PSNR, SSIM)

## 🚀 Chạy ứng dụng

### Chạy Web UI (Khuyến nghị)

```bash
python -m src.ui.app
```

Sau đó mở trình duyệt: **http://127.0.0.1:5000**

### Giao diện Web

#### 1. Upload ảnh
- Chọn tab "Upload Image"
- Chọn file ảnh (.jpg, .png, .bmp)
- Cấu hình tham số
- Nhấn "Segment"

#### 2. Chọn từ BDS500
- Chọn tab "BDS500 Dataset"
- Chọn split: train/val/test
- Nhấn "Load List" hoặc "Random"
- Click vào ảnh để chọn
- Nhấn "Segment"

#### 3. Cấu hình tham số

**Thuật toán**:
- ☑️ GWO (Grey Wolf Optimizer)
- ☑️ WOA (Whale Optimization Algorithm)
- ☑️ HYBRID (PA1, PA2, PA3, PA4, PA5)

**Tham số tối ưu**:
- `n_agents`: Số cá thể (default: 30)
- `n_iters`: Số vòng lặp (default: 80)
- `seed`: Random seed (để tái tạo kết quả)
- `woa_b`: Tham số WOA (default: 1.0)
- `share_interval`: Khoảng chia sẻ Hybrid (default: 1)

**Penalties** (Tránh dồn ngưỡng):
- ☑️ Use Penalties
- Chế độ: Light / **Balanced** / Strong

**Ground Truth** (BDS500):
- `gt_thr`: Ngưỡng boundary (default: 0.5)
- `gt_fuse`: Cách gộp nhiều GT (max/mean)

#### 4. Xem kết quả

**Segmentation Results**:
- Ảnh gốc (grayscale)
- Ảnh phân đoạn (mỗi thuật toán)
- Ngưỡng tìm được
- Entropy (maximize)
- Thời gian chạy
- Metrics: PSNR, SSIM, DICE (nếu có GT)

**Benchmark Results**:
- Kết quả 18 hàm benchmark
- So sánh GWO vs WOA vs Hybrid
- Biểu đồ convergence

## 📝 Chạy scripts

### 1. Phân đoạn ảnh đơn

```bash
python -m src.runner.run_single ^
  --image dataset/lena.gray.bmp ^
  --k 10 ^
  --algo HYBRID ^
  --strategy PA3 ^
  --n_agents 30 ^
  --n_iters 100 ^
  --seed 42
```

**Tham số**:
- `--image`: Đường dẫn ảnh
- `--k`: Số ngưỡng (default: 10)
- `--algo`: GWO | WOA | HYBRID
- `--strategy`: PA1 | PA2 | PA3 | PA4 | PA5 (cho HYBRID)
- `--n_agents`: Số cá thể (default: 30)
- `--n_iters`: Số vòng lặp (default: 100)
- `--seed`: Random seed

### 2. Phân đoạn dataset BDS500

```bash
python -m src.runner.run_dataset ^
  --images_root dataset/BDS500/images ^
  --gt_root dataset/BDS500/ground_truth ^
  --split test ^
  --k 10 ^
  --algo HYBRID ^
  --strategy PA3 ^
  --n_agents 30 ^
  --n_iters 100 ^
  --limit 10
```

**Tham số thêm**:
- `--split`: train | val | test
- `--limit`: Giới hạn số ảnh (0 = tất cả)
- `--gt_thr`: Ngưỡng boundary GT (default: 0.5)
- `--gt_fuse`: max | mean

### 3. Đánh giá DICE score

```bash
python -m src.runner.eval_dice_bsds500 ^
  --images_root dataset/BDS500/images ^
  --gt_root dataset/BDS500/ground_truth ^
  --split test ^
  --k 10 ^
  --algo HYBRID ^
  --strategy PA3 ^
  --n_agents 30 ^
  --n_iters 100
```

### 4. Học ngưỡng toàn cục (Global Thresholds)

**Bước 1: Học trên tập train**
```bash
python -m src.runner.learn_global_thresholds_bsds500 ^
  --images_root dataset/BDS500/images ^
  --gt_root dataset/BDS500/ground_truth ^
  --split train ^
  --k 10 ^
  --algo HYBRID ^
  --strategy PA3 ^
  --n_agents 30 ^
  --n_iters 200 ^
  --limit 50 ^
  --out_dir outputs/runs/global_thresholds
```

Kết quả: `outputs/runs/global_thresholds/global_thresholds.json`

**Bước 2: Đánh giá trên tập test**
```bash
python -m src.runner.eval_global_thresholds_bsds500 ^
  --images_root dataset/BDS500/images ^
  --gt_root dataset/BDS500/ground_truth ^
  --split test ^
  --thresholds_json outputs/runs/global_thresholds/global_thresholds.json
```

### 5. Chạy benchmark

```bash
python -m src.runner.run_benchmark ^
  --fun 1 ^
  --dim 30 ^
  --algo HYBRID ^
  --strategy PA3 ^
  --n_agents 50 ^
  --n_iters 200
```

**Tham số**:
- `--fun`: Hàm benchmark (1-18)
- `--dim`: Số chiều (default: 30)

### 6. Demo penalties

```bash
python -m examples.demo_penalties
```

So sánh kết quả có/không có penalties.

## 📚 Tài liệu

### Hướng dẫn chi tiết

1. **[BDS500_USAGE.md](docs/BDS500_USAGE.md)** - Hướng dẫn sử dụng BDS500 dataset
2. **[PENALTIES_USAGE.md](docs/PENALTIES_USAGE.md)** - Hướng dẫn sử dụng penalties
3. **[GLOBAL_THRESHOLDS.md](docs/GLOBAL_THRESHOLDS.md)** - Tối ưu ngưỡng toàn cục
4. **[SAVE_RESULTS_USAGE.md](docs/SAVE_RESULTS_USAGE.md)** - Lưu và xem lại kết quả ⭐ MỚI
5. **[TOM_TAT_HOAN_THANH.md](docs/TOM_TAT_HOAN_THANH.md)** - Tóm tắt penalties (Tiếng Việt)
6. **[VISUAL_COMPARISON.md](docs/VISUAL_COMPARISON.md)** - So sánh trực quan

### Tài liệu kỹ thuật

- **[PENALTY_INTEGRATION_COMPLETE.md](docs/PENALTY_INTEGRATION_COMPLETE.md)** - Chi tiết tích hợp penalties
- **[SUMMARY_PENALTY_FIX.md](docs/SUMMARY_PENALTY_FIX.md)** - Sửa lỗi penalty weights
- **[FIX_ENTROPY_DISPLAY.md](docs/FIX_ENTROPY_DISPLAY.md)** - Hiển thị Entropy đúng

## 📁 Cấu trúc thư mục

```
.
├── dataset/                    # Dữ liệu
│   ├── BDS500/                # BDS500 dataset
│   │   ├── images/           # Ảnh gốc
│   │   │   ├── train/
│   │   │   ├── val/
│   │   │   └── test/
│   │   └── ground_truth/     # Ground truth
│   │       ├── train/
│   │       ├── val/
│   │       └── test/
│   ├── lena.bmp
│   └── lena.gray.bmp
│
├── src/                       # Source code
│   ├── benchmarks/           # Hàm benchmark
│   │   ├── benchmark.py
│   │   └── benchmark_func.py
│   ├── data/                 # Xử lý dữ liệu
│   │   ├── bsds500.py
│   │   └── bsds500_gt.py
│   ├── metrics/              # Metrics
│   │   └── quality.py
│   ├── objective/            # Objective functions
│   │   ├── fuzzy_entropy.py
│   │   ├── penalties.py
│   │   ├── thresholding.py
│   │   └── thresholding_with_penalties.py
│   ├── optim/                # Optimizers
│   │   ├── base.py
│   │   ├── bounds.py
│   │   ├── gwo.py
│   │   ├── woa.py
│   │   └── hybrid/
│   │       ├── hybrid_gwo_woa.py
│   │       ├── pa1.py
│   │       ├── pa2.py
│   │       ├── pa3.py
│   │       ├── pa4.py
│   │       └── pa5.py
│   ├── runner/               # Scripts chạy
│   │   ├── run_single.py
│   │   ├── run_dataset.py
│   │   ├── run_benchmark.py
│   │   ├── eval_dice_bsds500.py
│   │   ├── learn_global_thresholds_bsds500.py
│   │   └── eval_global_thresholds_bsds500.py
│   ├── segmentation/         # Phân đoạn
│   │   ├── apply_thresholds.py
│   │   └── io.py
│   └── ui/                   # Web UI
│       ├── app.py
│       ├── static/
│       │   ├── app.js
│       │   └── index.css
│       └── templates/
│           └── index.html
│
├── examples/                  # Ví dụ
│   └── demo_penalties.py
│
├── docs/                      # Tài liệu
│   ├── BDS500_USAGE.md
│   ├── PENALTIES_USAGE.md
│   ├── GLOBAL_THRESHOLDS.md
│   └── ...
│
├── configs/                   # Config files
│   ├── gwo.yaml
│   ├── woa.yaml
│   ├── hybrid.yaml
│   └── task_thresholding.yaml
│
├── requirements.txt           # Dependencies
└── README.md                  # File này
```

## 🎯 Ví dụ sử dụng

### Ví dụ 1: Phân đoạn ảnh đơn giản

```bash
# Chạy Web UI
python -m src.ui.app

# Mở trình duyệt: http://127.0.0.1:5000
# Upload ảnh → Chọn GWO → Segment
# Kết quả tự động lưu vào outputs/runs/
```

### Ví dụ 2: So sánh 3 thuật toán

```bash
# Trong Web UI:
# ☑️ GWO
# ☑️ WOA
# ☑️ HYBRID (PA1, PA3, PA5)
# → Segment
# → Xem kết quả so sánh
# → Kết quả lưu tại outputs/runs/YYYYMMDD_HHMMSS_ui_hash/
```

### Ví dụ 3: Xem lại kết quả đã lưu

```bash
# Xem run mới nhất
ls -lt outputs/runs/ | head -2

# Xem summary
cat outputs/runs/20260122_143052_ui_a3f7b2c1/summary.json

# Xem config
cat outputs/runs/20260122_143052_ui_a3f7b2c1/config.yaml

# Xem ảnh kết quả
start outputs/runs/20260122_143052_ui_a3f7b2c1/GWO/segmented.png
```

### Ví dụ 3: Dùng penalties

```bash
# Trong Web UI:
# ☑️ Use Penalties
# Chọn mode: Balanced
# → Segment
# → So sánh với/không có penalties
# → Kết quả lưu với thông tin penalties
```

### Ví dụ 4: Đánh giá trên BDS500

```bash
# Trong Web UI:
# Tab: BDS500 Dataset
# Split: test
# Load List → Chọn ảnh
# → Segment
# → Xem DICE score
```

### Ví dụ 5: Tối ưu ngưỡng toàn cục

```bash
# Bước 1: Học trên train (50 ảnh)
python -m src.runner.learn_global_thresholds_bsds500 ^
  --images_root dataset/BDS500/images ^
  --gt_root dataset/BDS500/ground_truth ^
  --split train ^
  --k 10 ^
  --algo HYBRID ^
  --strategy PA3 ^
  --n_agents 30 ^
  --n_iters 200 ^
  --limit 50

# Bước 2: Test trên test set
python -m src.runner.eval_global_thresholds_bsds500 ^
  --images_root dataset/BDS500/images ^
  --gt_root dataset/BDS500/ground_truth ^
  --split test ^
  --thresholds_json outputs/runs/global_thresholds/global_thresholds.json
```

## 📊 Hiểu kết quả

### Entropy (Fuzzy Entropy)
- **Khoảng giá trị**: 0.01 - 0.10
- **Giá trị thường**: 0.03 - 0.08
- **Giá trị tốt**: 0.04 - 0.06
- **Mục tiêu**: Maximize (càng lớn càng tốt)

### DICE Score (Boundary-DICE)
- **Khoảng giá trị**: 0.0 - 1.0
- **Giá trị tốt**: > 0.3
- **Giá trị xuất sắc**: > 0.5
- **Mục tiêu**: Maximize (càng lớn càng tốt)

### PSNR (Peak Signal-to-Noise Ratio)
- **Khoảng giá trị**: 0 - ∞ dB
- **Giá trị tốt**: > 30 dB
- **Mục tiêu**: Maximize

### SSIM (Structural Similarity Index)
- **Khoảng giá trị**: 0.0 - 1.0
- **Giá trị tốt**: > 0.8
- **Mục tiêu**: Maximize

### Penalties
- **Min gap**: Khoảng cách tối thiểu giữa ngưỡng (pixels)
- **Min region**: Tỷ lệ pixel nhỏ nhất của vùng (%)
- **Gap variance**: Phương sai khoảng cách (càng nhỏ càng đều)

## ⚙️ Tham số khuyến nghị

### Phân đoạn nhanh (Quick)
```
n_agents: 20
n_iters: 50
algo: GWO
penalties: Light
```

### Phân đoạn cân bằng (Balanced) ⭐
```
n_agents: 30
n_iters: 80
algo: HYBRID (PA3)
penalties: Balanced
```

### Phân đoạn chất lượng cao (High Quality)
```
n_agents: 50
n_iters: 200
algo: HYBRID (PA3, PA5)
penalties: Strong
```

### Tối ưu ngưỡng toàn cục
```
n_agents: 30
n_iters: 200
algo: HYBRID (PA3)
limit: 50-100 ảnh train
```

## 🐛 Xử lý lỗi

### Lỗi: "Module not found"
```bash
# Cài đặt lại dependencies
pip install -r requirements.txt
```

### Lỗi: "Cannot read .mat file"
```bash
# Cài đặt scipy
pip install scipy
```

### Lỗi: "Port 5000 already in use"
```bash
# Đổi port trong app.py (dòng cuối):
app.run(host="127.0.0.1", port=5001, debug=True)
```

### Lỗi: "BDS500 dataset not found"
```bash
# Kiểm tra đường dẫn:
# dataset/BDS500/images/test/
# dataset/BDS500/ground_truth/test/
```

## 📞 Liên hệ & Hỗ trợ

- **Issues**: Tạo issue trên GitHub
- **Documentation**: Xem thư mục `docs/`
- **Examples**: Xem thư mục `examples/`

## 📄 License

[Thêm license của bạn ở đây]

## 🙏 Acknowledgments

- BDS500 Dataset: Berkeley Segmentation Dataset
- Fuzzy Entropy: Zhao et al.
- GWO: Mirjalili et al.
- WOA: Mirjalili & Lewis

---

**Chúc bạn phân đoạn ảnh thành công!** 🎉

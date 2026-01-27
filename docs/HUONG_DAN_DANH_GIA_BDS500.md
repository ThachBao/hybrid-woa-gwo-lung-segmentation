# Hướng Dẫn Đánh Giá Thuật Toán Trên BDS500 Dataset

## 📚 Mục Lục
1. [Đánh Giá BDS500 Là Gì?](#đánh-giá-bds500-là-gì)
2. [Tại Sao Cần Đánh Giá?](#tại-sao-cần-đánh-giá)
3. [BDS500 Dataset Là Gì?](#bds500-dataset-là-gì)
4. [Quy Trình Đánh Giá](#quy-trình-đánh-giá)
5. [Các Tham Số](#các-tham-số)
6. [Kết Quả Đánh Giá](#kết-quả-đánh-giá)
7. [Ví Dụ Cụ Thể](#ví-dụ-cụ-thể)

---

## Đánh Giá BDS500 Là Gì?

### Khái Niệm Đơn Giản
**Đánh giá BDS500** là quá trình kiểm tra xem các thuật toán tối ưu ngưỡng (GWO, WOA, PA1-PA5) hoạt động tốt như thế nào trên một tập dữ liệu chuẩn.

### So Sánh Với Thực Tế
Giống như:
- **Thi học sinh giỏi**: Nhiều học sinh (thuật toán) làm cùng một bộ đề (BDS500), sau đó so sánh điểm số
- **Đua xe**: Nhiều xe (thuật toán) chạy trên cùng một đường đua (BDS500), xem xe nào nhanh nhất

### Mục Đích
- **So sánh** các thuật toán: GWO vs WOA vs PA1 vs PA2...
- **Đánh giá khách quan**: Dùng dữ liệu chuẩn, không phải ảnh ngẫu nhiên
- **Có kết quả đo lường**: DICE score, Entropy, Time

---

## Tại Sao Cần Đánh Giá?

### 1. Không Thể Tin Vào 1 Ảnh
❌ **Sai:**
```
Chạy GWO trên 1 ảnh → Kết quả tốt → "GWO là tốt nhất!"
```

✅ **Đúng:**
```
Chạy GWO trên 200 ảnh → Tính trung bình → "GWO có DICE = 0.72 ± 0.05"
```

### 2. Cần So Sánh Công Bằng
- **Cùng ảnh**: Tất cả thuật toán chạy trên cùng 200 ảnh
- **Cùng tham số**: k=10, n_agents=30, n_iters=80
- **Cùng seed**: seed=42 (để reproducible)

### 3. Cần Kết Quả Khoa Học
Để viết báo cáo/luận văn, cần:
- **Bảng so sánh**: DICE mean, std, min, max
- **Biểu đồ**: So sánh trực quan
- **Thống kê**: Thuật toán nào tốt nhất?

---

## BDS500 Dataset Là Gì?

### Giới Thiệu
**Berkeley Segmentation Dataset (BSDS500)** là tập dữ liệu chuẩn cho phân đoạn ảnh.

### Đặc Điểm
- **500 ảnh** tự nhiên (phong cảnh, động vật, người...)
- **Có ground truth**: Mỗi ảnh có "đáp án đúng" do con người vẽ
- **Chia 3 phần**:
  - **Train**: 200 ảnh (để huấn luyện)
  - **Val**: 100 ảnh (để validation)
  - **Test**: 200 ảnh (để test cuối cùng)

### Ground Truth Là Gì?
**Ground truth** = "Đáp án đúng" = Biên (boundary) được vẽ bởi con người

**Ví dụ:**
```
Ảnh gốc:        Ground Truth:      Kết quả thuật toán:
[Con mèo]   →   [Viền con mèo]  →  [Viền tìm được]
                (do người vẽ)       (do thuật toán)
```

**So sánh:**
- Ground truth: Viền "đúng" (do người vẽ)
- Kết quả thuật toán: Viền "tìm được" (do máy tính)
- **DICE score**: Đo độ giống nhau (0-1, càng cao càng tốt)

---

## Quy Trình Đánh Giá

### Bước 1: Chọn Dataset
```
Split: test (200 ảnh)
Limit: 10 (chỉ lấy 10 ảnh đầu để test nhanh)
```

### Bước 2: Chọn Thuật Toán
```
✓ GWO (Grey Wolf Optimizer)
✓ WOA (Whale Optimization Algorithm)
✓ PA1 (Hybrid Phase Approach 1)
```

### Bước 3: Đặt Tham Số
```
k = 10          (số ngưỡng)
seed = 42       (random seed)
n_agents = 30   (số cá thể)
n_iters = 80    (số vòng lặp)
```

### Bước 4: Chạy Đánh Giá
Hệ thống sẽ:
```
FOR mỗi ảnh trong 10 ảnh:
    FOR mỗi thuật toán (GWO, WOA, PA1):
        1. Chạy thuật toán tối ưu
        2. Tìm ngưỡng tốt nhất
        3. Phân đoạn ảnh
        4. Trích xuất biên (boundary)
        5. So sánh với ground truth
        6. Tính DICE score
        7. Lưu kết quả
```

**Tổng cộng:** 10 ảnh × 3 thuật toán = **30 lần chạy**

### Bước 5: Xem Kết Quả
Sau khi chạy xong, bạn sẽ thấy:
- **Bảng so sánh**: DICE mean, std, min, max
- **Thống kê**: Thuật toán nào tốt nhất
- **File kết quả**: Lưu trong `outputs/bds500_eval/`

---

## Các Tham Số

### 1. Split (Phần Dataset)
- **train**: 200 ảnh để huấn luyện
- **val**: 100 ảnh để validation
- **test**: 200 ảnh để test cuối cùng

**Khuyến nghị:** Dùng **test** để đánh giá cuối cùng

### 2. Limit (Giới Hạn Số Ảnh)
- **0**: Không giới hạn (chạy hết 200 ảnh)
- **10**: Chỉ chạy 10 ảnh đầu (test nhanh)
- **50**: Chạy 50 ảnh (cân bằng)

**Khuyến nghị:**
- Test nhanh: **10 ảnh** (~5-10 phút)
- Đánh giá đầy đủ: **200 ảnh** (~2-3 giờ)

### 3. k (Số Ngưỡng)
- Số ngưỡng để phân đoạn ảnh
- **k=10**: Chia ảnh thành 11 vùng

**Ví dụ:**
```
k=2:  [0, 85, 170, 255]     → 3 vùng
k=5:  [0, 51, 102, 153, 204, 255] → 6 vùng
k=10: [0, 25, 51, ..., 255] → 11 vùng
```

### 4. seed (Random Seed)
- Để kết quả có thể lặp lại (reproducible)
- **seed=42**: Mỗi lần chạy cho kết quả giống nhau

**⚠️ LƯU Ý QUAN TRỌNG:**
- **Seed cố định (42)** chỉ để **DEBUG**
- **Để so sánh thuật toán**, cần chạy **30+ seeds khác nhau**

**Ví dụ:**
```
Sai:  seed=42 → GWO tốt hơn WOA → "GWO là tốt nhất!"
Đúng: seed=1,2,3,...,30 → Tính trung bình → "GWO tốt hơn WOA"
```

### 5. n_agents (Số Cá Thể)
- Số lượng "cá thể" trong quần thể
- **30**: Cân bằng giữa tốc độ và chất lượng
- **50**: Chất lượng cao hơn, chậm hơn

### 6. n_iters (Số Vòng Lặp)
- Số vòng lặp tối ưu
- **80**: Cân bằng
- **100**: Chất lượng cao hơn, chậm hơn

---

## Kết Quả Đánh Giá

### 1. DICE Score
**DICE score** đo độ giống nhau giữa:
- Biên tìm được (thuật toán)
- Biên đúng (ground truth)

**Công thức:**
```
DICE = 2 × (Giao) / (Tổng)
```

**Giá trị:**
- **0.0**: Hoàn toàn khác nhau (tệ)
- **0.5**: Giống 50%
- **0.7**: Giống 70% (tốt)
- **1.0**: Giống 100% (hoàn hảo)

**Ví dụ:**
```
Ground Truth:  ████░░░░  (4 pixel biên)
Thuật toán:    ███░░░░░  (3 pixel biên)
Giao:          ███░░░░░  (3 pixel chung)
DICE = 2×3/(4+3) = 6/7 = 0.857
```

### 2. Entropy
- Độ đo "độ hỗn loạn" của ảnh sau phân đoạn
- **Càng cao càng tốt** (ảnh phân đoạn rõ ràng)

### 3. Time
- Thời gian chạy (giây)
- **Càng thấp càng tốt** (nhanh hơn)

### 4. Bảng Kết Quả
```
┌──────────┬────────────┬──────────┬──────────┬──────────┬──────────┐
│ Thuật    │ DICE       │ DICE     │ DICE     │ DICE     │ Time     │
│ toán     │ (Mean)     │ (Std)    │ (Min)    │ (Max)    │ (Mean)   │
├──────────┼────────────┼──────────┼──────────┼──────────┼──────────┤
│🏆 PA1    │ 0.7234     │ 0.0456   │ 0.6543   │ 0.8123   │ 12.34s   │
│  GWO     │ 0.7123     │ 0.0478   │ 0.6234   │ 0.7987   │ 11.89s   │
│  WOA     │ 0.7089     │ 0.0501   │ 0.6123   │ 0.7856   │ 12.01s   │
└──────────┴────────────┴──────────┴──────────┴──────────┴──────────┘
```

**Giải thích:**
- **PA1** có DICE mean cao nhất (0.7234) → **Tốt nhất**
- **GWO** nhanh nhất (11.89s)
- **WOA** có độ ổn định thấp nhất (std cao)

---

## Ví Dụ Cụ Thể

### Ví Dụ 1: Test Nhanh (10 Ảnh)

**Cấu hình:**
```
Split: test
Limit: 10
Thuật toán: GWO, WOA, PA1
k: 10
seed: 42
n_agents: 30
n_iters: 80
```

**Quá trình:**
```
[1/10] Image: img_0000
  [1/30] GWO... DICE=0.7234, Time=12.34s
  [2/30] WOA... DICE=0.7189, Time=11.89s
  [3/30] PA1... DICE=0.7345, Time=13.56s

[2/10] Image: img_0001
  [4/30] GWO... DICE=0.6987, Time=12.01s
  [5/30] WOA... DICE=0.7012, Time=11.67s
  [6/30] PA1... DICE=0.7123, Time=13.23s

...

[10/10] Image: img_0009
  [28/30] GWO... DICE=0.7456, Time=12.45s
  [29/30] WOA... DICE=0.7389, Time=11.98s
  [30/30] PA1... DICE=0.7567, Time=13.78s
```

**Kết quả:**
```
Tổng thời gian: 380.5s (6.3 phút)

Thống kê:
  GWO: DICE=0.7234 ± 0.0456, Time=12.34s
  WOA: DICE=0.7189 ± 0.0478, Time=11.89s
  PA1: DICE=0.7345 ± 0.0423, Time=13.56s

Thuật toán tốt nhất: PA1 (DICE cao nhất)
```

### Ví Dụ 2: Đánh Giá Đầy Đủ (200 Ảnh)

**Cấu hình:**
```
Split: test
Limit: 200 (hoặc 0 = không giới hạn)
Thuật toán: GWO, WOA, PA1, PA2, PA3, PA4, PA5
k: 10
seed: 42
n_agents: 30
n_iters: 80
```

**Thời gian:**
```
200 ảnh × 7 thuật toán × 12s/thuật toán ≈ 4.7 giờ
```

**Kết quả:**
```
┌──────────┬────────────┬──────────┐
│ Thuật    │ DICE       │ Time     │
│ toán     │ (Mean±Std) │ (Mean)   │
├──────────┼────────────┼──────────┤
│🏆 PA3    │ 0.7456±0.04│ 13.2s    │
│  PA1     │ 0.7423±0.04│ 13.5s    │
│  PA4     │ 0.7389±0.05│ 13.8s    │
│  GWO     │ 0.7234±0.05│ 12.3s    │
│  WOA     │ 0.7189±0.05│ 11.9s    │
│  PA2     │ 0.7156±0.05│ 13.1s    │
│  PA5     │ 0.7123±0.06│ 14.2s    │
└──────────┴────────────┴──────────┘
```

**Kết luận:**
- **PA3** tốt nhất về DICE score
- **WOA** nhanh nhất
- **PA5** có độ ổn định thấp nhất

---

## Câu Hỏi Thường Gặp

### 1. Tại sao cần 200 ảnh? 1 ảnh không đủ sao?
**Trả lời:** 1 ảnh có thể "may mắn" hoặc "không may". 200 ảnh cho kết quả **trung bình** và **ổn định** hơn.

**Ví dụ:**
```
Ảnh 1: GWO tốt hơn WOA
Ảnh 2: WOA tốt hơn GWO
Ảnh 3: GWO tốt hơn WOA
...
→ Cần nhiều ảnh để biết thuật toán nào tốt hơn THỰC SỰ
```

### 2. DICE score là gì? Tại sao quan trọng?
**Trả lời:** DICE score đo độ giống nhau giữa kết quả và đáp án đúng.

**Ví dụ thực tế:**
```
Bài thi:     Đáp án:      Điểm:
A, B, C, D   A, B, C, D   100% (DICE=1.0)
A, B, X, D   A, B, C, D   75%  (DICE=0.75)
X, Y, Z, W   A, B, C, D   0%   (DICE=0.0)
```

### 3. Tại sao seed=42 chỉ để debug?
**Trả lời:** Seed cố định cho kết quả giống nhau mỗi lần chạy, nhưng không đại diện cho **hiệu suất thực**.

**Ví dụ:**
```
Seed=42:  GWO=0.72, WOA=0.71 → GWO tốt hơn
Seed=43:  GWO=0.70, WOA=0.73 → WOA tốt hơn
Seed=44:  GWO=0.71, WOA=0.72 → WOA tốt hơn
...
→ Cần chạy nhiều seeds để biết thuật toán nào tốt hơn THỰC SỰ
```

### 4. Limit=10 hay 200?
**Trả lời:**
- **Limit=10**: Test nhanh (~5-10 phút), để kiểm tra code
- **Limit=200**: Đánh giá đầy đủ (~2-3 giờ), để viết báo cáo

### 5. Kết quả lưu ở đâu?
**Trả lời:** Trong thư mục `outputs/bds500_eval/YYYYMMDD_HHMMSS/`

**Cấu trúc:**
```
outputs/bds500_eval/20260122_123456/
├── results.json          # Kết quả chi tiết từng ảnh
├── summary.json          # Thống kê tổng hợp
└── evaluation.log        # Logs chi tiết
```

---

## Tóm Tắt

### Đánh Giá BDS500 Là:
✅ So sánh các thuật toán trên dữ liệu chuẩn
✅ Đo lường khách quan bằng DICE score
✅ Có kết quả thống kê (mean, std, min, max)
✅ Lưu kết quả để phân tích sau

### Quy Trình:
1. Chọn dataset (test, 10 ảnh)
2. Chọn thuật toán (GWO, WOA, PA1)
3. Đặt tham số (k=10, seed=42)
4. Chạy đánh giá (10×3=30 runs)
5. Xem kết quả (bảng so sánh)

### Kết Quả:
- **DICE score**: Độ chính xác (0-1, càng cao càng tốt)
- **Time**: Thời gian (giây, càng thấp càng tốt)
- **Bảng so sánh**: Thuật toán nào tốt nhất?

---

**Bây giờ bạn đã hiểu rõ về đánh giá BDS500! 🎉**

Nếu còn thắc mắc, hãy hỏi thêm!

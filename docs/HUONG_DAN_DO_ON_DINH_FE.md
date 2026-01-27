# Hướng Dẫn Sử Dụng Độ Ổn Định FE

## Giới Thiệu Nhanh

Hệ thống đánh giá BDS500 hiện đã tích hợp các chỉ số độ ổn định FE (Fuzzy Entropy). Bạn có thể đánh giá không chỉ chất lượng phân đoạn (DICE) mà còn độ ổn định của thuật toán.

## Các Chỉ Số Độ Ổn Định

### 1. FE Jitter Std (Độ Ổn Định Ngưỡng)
- **Ý nghĩa**: Đo FE thay đổi bao nhiêu khi ngưỡng thay đổi nhỏ (±2 mức xám)
- **Cách tính**: Tạo 20 mẫu ngưỡng với nhiễu ngẫu nhiên ±2, tính std của FE
- **Giải thích**: 
  - Giá trị thấp (< 0.001) = Rất ổn định
  - Giá trị cao (> 0.01) = Không ổn định, nhạy cảm với nhiễu
- **Ví dụ**: 
  - GWO: 0.000234 → Rất ổn định
  - WOA: 0.000345 → Ổn định
  - Thuật toán X: 0.015000 → Không ổn định

### 2. FE Conv Std (Độ Ổn Định Hội Tụ)
- **Ý nghĩa**: Đo FE dao động bao nhiêu trong 10 vòng lặp cuối
- **Cách tính**: Lấy std của FE trong 10 iteration cuối cùng
- **Giải thích**:
  - Giá trị thấp (< 0.001) = Hội tụ mượt mà
  - Giá trị cao (> 0.01) = Hội tụ dao động, không ổn định
- **Ví dụ**:
  - PSO: 0.000123 → Hội tụ rất mượt
  - GWO: 0.000156 → Hội tụ tốt
  - Thuật toán Y: 0.025000 → Hội tụ dao động

## Cách Sử Dụng

### Bước 1: Khởi Động UI

```bash
cd /path/to/project
python src/ui/app.py
```

Mở trình duyệt: http://127.0.0.1:5000

### Bước 2: Vào Tab "Đánh giá BDS500"

Click vào tab thứ 3 trong giao diện.

### Bước 3: Cấu Hình

```
Số ngưỡng (k): 4
Seed: 42
Số agents: 30
Số iterations: 80
Split: test
```

### Bước 4: Chọn Thuật Toán

Chọn ít nhất 2 thuật toán để so sánh:
- ☑ GWO
- ☑ WOA
- ☑ PSO
- ☐ OTSU
- ☐ PA1-PA5

### Bước 5: Chạy Đánh Giá

Click "Chạy đánh giá" và đợi (có thể mất 5-30 phút tùy cấu hình).

### Bước 6: Xem Kết Quả

Hai bảng sẽ hiển thị:

#### Bảng 1: So Sánh DICE Score
```
🏆 PSO    0.7301 ± 0.0423  [0.6678 - 0.7945]
   GWO    0.7234 ± 0.0456  [0.6543 - 0.7891]
   WOA    0.7156 ± 0.0489  [0.6421 - 0.7823]
```

**Cách đọc**:
- PSO có DICE cao nhất (0.7301) → Phân đoạn tốt nhất
- PSO có std thấp nhất (0.0423) → Kết quả ổn định nhất

#### Bảng 2: So Sánh FE & Độ Ổn Định
```
🏆 PSO    FE: 5.267890  Jitter: 0.000198  Conv: 0.000123  Time: 11.23s
   GWO    FE: 5.234567  Jitter: 0.000234  Conv: 0.000156  Time: 12.34s
   WOA    FE: 5.198765  Jitter: 0.000345  Conv: 0.000234  Time: 13.45s
```

**Cách đọc**:
- PSO có FE cao nhất (5.267890) → Tối ưu tốt nhất
- PSO có Jitter thấp nhất (0.000198) → Ổn định với nhiễu ngưỡng
- PSO có Conv thấp nhất (0.000123) → Hội tụ mượt mà nhất
- PSO nhanh nhất (11.23s) → Hiệu quả nhất

## Giải Thích Kết Quả

### Trường Hợp 1: Thuật Toán Tốt
```
DICE: 0.75 ± 0.03
FE: 5.5
Jitter Std: 0.0002
Conv Std: 0.0001
```

**Đánh giá**: ⭐⭐⭐⭐⭐
- DICE cao → Phân đoạn tốt
- FE cao → Tối ưu tốt
- Jitter thấp → Ổn định với nhiễu
- Conv thấp → Hội tụ mượt

### Trường Hợp 2: Thuật Toán Trung Bình
```
DICE: 0.70 ± 0.05
FE: 5.2
Jitter Std: 0.0008
Conv Std: 0.0005
```

**Đánh giá**: ⭐⭐⭐
- DICE trung bình → Phân đoạn khá
- FE trung bình → Tối ưu khá
- Jitter cao hơn → Hơi nhạy nhiễu
- Conv cao hơn → Hội tụ hơi dao động

### Trường Hợp 3: Thuật Toán Kém
```
DICE: 0.65 ± 0.08
FE: 4.8
Jitter Std: 0.0025
Conv Std: 0.0020
```

**Đánh giá**: ⭐⭐
- DICE thấp → Phân đoạn kém
- FE thấp → Tối ưu kém
- Jitter rất cao → Rất nhạy nhiễu
- Conv rất cao → Hội tụ dao động mạnh

## Lưu Ý Quan Trọng

### 1. Thời Gian Chạy

Tính độ ổn định làm tăng thời gian ~20x:
- Không có ổn định: 5 phút
- Có ổn định: 100 phút (1.5 giờ)

**Khuyến nghị**:
- Test nhanh: Dùng 5 ảnh, k=3, n_iters=50
- Đánh giá đầy đủ: Dùng 10 ảnh, k=4, n_iters=80

### 2. Seed

Luôn dùng cùng seed để so sánh công bằng:
```
Seed: 42  (khuyến nghị)
```

### 3. Số Ảnh

- 5 ảnh: Test nhanh (~30 phút)
- 10 ảnh: Đánh giá tốt (~1 giờ)
- 50 ảnh: Đánh giá đầy đủ (~5 giờ)

### 4. Chọn Thuật Toán

Đừng chọn quá nhiều thuật toán cùng lúc:
- 2-3 thuật toán: Tốt
- 4-5 thuật toán: Chấp nhận được
- 6+ thuật toán: Quá lâu

## Ví Dụ Thực Tế

### Ví Dụ 1: So Sánh GWO vs WOA

**Cấu hình**:
```
k: 4
seed: 42
n_agents: 30
n_iters: 80
split: test (10 ảnh)
algorithms: GWO, WOA
```

**Kết quả**:
```
DICE:
  GWO: 0.7234 ± 0.0456
  WOA: 0.7156 ± 0.0489

FE & Stability:
  GWO: FE=5.234567, Jitter=0.000234, Conv=0.000156
  WOA: FE=5.198765, Jitter=0.000345, Conv=0.000234
```

**Kết luận**:
- GWO tốt hơn WOA về cả DICE và FE
- GWO ổn định hơn WOA (Jitter và Conv đều thấp hơn)
- **Khuyến nghị**: Dùng GWO

### Ví Dụ 2: So Sánh PSO vs GWO vs WOA

**Cấu hình**:
```
k: 4
seed: 42
n_agents: 30
n_iters: 80
split: test (10 ảnh)
algorithms: PSO, GWO, WOA
```

**Kết quả**:
```
DICE:
  PSO: 0.7301 ± 0.0423  🏆
  GWO: 0.7234 ± 0.0456
  WOA: 0.7156 ± 0.0489

FE & Stability:
  PSO: FE=5.267890, Jitter=0.000198, Conv=0.000123  🏆
  GWO: FE=5.234567, Jitter=0.000234, Conv=0.000156
  WOA: FE=5.198765, Jitter=0.000345, Conv=0.000234
```

**Kết luận**:
- PSO tốt nhất về mọi mặt
- PSO có DICE cao nhất và ổn định nhất
- PSO có FE cao nhất và ổn định nhất
- **Khuyến nghị**: Dùng PSO

## Xử Lý Lỗi

### Lỗi 1: "Không tìm thấy ảnh"
```
Error: No images found in split 'test'
```

**Giải pháp**: Kiểm tra thư mục dataset:
```bash
ls dataset/BDS500/images/test/
```

### Lỗi 2: "Out of memory"
```
Error: MemoryError
```

**Giải pháp**: Giảm số ảnh hoặc giảm n_agents:
```
n_agents: 20 (thay vì 30)
n_iters: 50 (thay vì 80)
```

### Lỗi 3: "Timeout"
```
Error: Request timeout
```

**Giải pháp**: Đánh giá đang chạy, đợi thêm hoặc giảm cấu hình.

## Câu Hỏi Thường Gặp

### Q1: Tại sao có 2 bảng?
**A**: Bảng 1 cho DICE (chất lượng phân đoạn), Bảng 2 cho FE và ổn định (chất lượng tối ưu).

### Q2: Chỉ số nào quan trọng nhất?
**A**: 
- Nếu quan tâm phân đoạn: DICE
- Nếu quan tâm tối ưu: FE
- Nếu quan tâm ổn định: Jitter Std và Conv Std

### Q3: Jitter Std bao nhiêu là tốt?
**A**:
- < 0.001: Rất tốt
- 0.001 - 0.005: Tốt
- 0.005 - 0.01: Trung bình
- > 0.01: Kém

### Q4: Tại sao chạy lâu?
**A**: Tính ổn định cần tính FE nhiều lần (21x). Để nhanh hơn:
- Giảm số ảnh
- Giảm n_agents và n_iters
- Chọn ít thuật toán hơn

### Q5: Có thể tắt tính ổn định không?
**A**: Hiện tại không. Tính năng này sẽ được thêm trong tương lai.

## Tài Liệu Tham Khảo

- **Chi tiết kỹ thuật**: `docs/FE_STABILITY_INTEGRATION.md`
- **Tóm tắt tiếng Việt**: `docs/TOM_TAT_DO_ON_DINH_FE.md`
- **Test script**: `docs/test_fe_stability_ui.py`

## Liên Hệ

Nếu có vấn đề, kiểm tra:
1. Log trong terminal (nơi chạy `python src/ui/app.py`)
2. Console trong trình duyệt (F12)
3. File log trong `outputs/bds500_eval/`

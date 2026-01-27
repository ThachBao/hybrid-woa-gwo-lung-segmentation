# Tóm Tắt Tích Hợp Độ Ổn Định FE

## Tổng Quan

Tài liệu này mô tả việc tích hợp các chỉ số độ ổn định FE (Fuzzy Entropy) vào hệ thống đánh giá BDS500. Hệ thống hiện tại tính toán và hiển thị các chỉ số ổn định cùng với điểm DICE, cung cấp đánh giá toàn diện về hiệu suất thuật toán.

## Vấn Đề

Trước đây, đánh giá BDS500 chỉ hiển thị điểm DICE và giá trị entropy. Tuy nhiên:

1. **Tính FE sai**: Khi dùng penalties, `entropy = -best_f` là SAI vì `best_f` chứa cả penalty
2. **Thiếu chỉ số ổn định**: Không có cách đo độ ổn định của FE
3. **Hiển thị 1 bảng**: DICE và FE trộn lẫn trong 1 bảng, khó so sánh

## Giải Pháp

### 1. Các Chỉ Số Độ Ổn Định FE

Ba loại độ ổn định FE được tính toán:

#### A. FE Thực (không có penalty)
- **Hàm**: `compute_true_fe(gray_image, thresholds)`
- **Mục đích**: Tính FE thực sự không có penalty
- **Sử dụng**: Thay thế cách tính sai `entropy = -best_f`

#### B. Độ Ổn Định Jitter (Độ Nhạy Ngưỡng)
- **Hàm**: `compute_fe_stability_jitter(gray_image, thresholds, repair_fn, n_samples=20, delta=2, seed=42)`
- **Mục đích**: Đo FE thay đổi bao nhiêu khi ngưỡng thay đổi ±delta (±2 mức xám)
- **Chỉ số**: `fe_jitter_std` - càng thấp càng tốt (càng ổn định)
- **Ý nghĩa**: Thuật toán ổn định cho FE tương tự ngay cả khi ngưỡng bị nhiễu nhẹ

#### C. Độ Ổn Định Hội Tụ
- **Hàm**: `compute_fe_stability_convergence(history, last_w=10)`
- **Mục đích**: Đo FE dao động bao nhiêu trong W vòng lặp cuối
- **Chỉ số**: `fe_last_std` - càng thấp càng tốt (hội tụ càng ổn định)
- **Ý nghĩa**: Thuật toán ổn định hội tụ mượt mà không dao động

### 2. Thay Đổi Backend

#### File: `src/objective/thresholding_with_penalties.py`

Thêm 3 hàm mới:

```python
def compute_true_fe(gray_image, thresholds) -> float:
    """Tính FE không có penalties."""
    return -float(fuzzy_entropy_objective(gray_image, thresholds))

def compute_fe_stability_jitter(gray_image, thresholds, repair_fn, 
                                n_samples=20, delta=2, seed=42) -> dict:
    """Tính độ ổn định khi ngưỡng thay đổi nhỏ."""
    # Trả về: fe_mean, fe_std, fe_min, fe_max, fe_original

def compute_fe_stability_convergence(history, last_w=10) -> dict:
    """Tính độ ổn định hội tụ."""
    # Trả về: fe_last_mean, fe_last_std, fe_improvement, fe_first, fe_last
```

#### File: `src/ui/app.py`

Cập nhật endpoint `/api/eval_bds500`:

**Trước:**
```python
# SAI: best_f chứa penalties
entropy = -best_f

# 1 dictionary algo_stats
algo_stats = {...}

return jsonify({
    "algo_stats": algo_stats,  # DICE và FE trộn lẫn
})
```

**Sau:**
```python
# ĐÚNG: Tính FE thực
fe_true = compute_true_fe(gray, best_x)

# Tính các chỉ số ổn định
fe_stab_jitter = compute_fe_stability_jitter(
    gray, best_x, repair_fn, n_samples=20, delta=2, seed=seed
)
fe_stab_conv = compute_fe_stability_convergence(history, last_w=10)

# Lưu kết quả
results.append({
    "dice": float(dice),
    "fe": float(fe_true),
    "fe_jitter_mean": float(fe_stab_jitter["fe_mean"]),
    "fe_jitter_std": float(fe_stab_jitter["fe_std"]),
    "fe_conv_std": float(fe_stab_conv["fe_last_std"]),
    "fe_improvement": float(fe_stab_conv["fe_improvement"]),
})

# Tách riêng thống kê DICE và FE
dice_stats = {...}  # Chỉ DICE
fe_stats = {...}    # Chỉ FE

return jsonify({
    "dice_stats": dice_stats,
    "fe_stats": fe_stats,
})
```

### 3. Thay Đổi Frontend

#### File: `src/ui/static/app.js`

Cập nhật hàm `displayBDS500Results()`:

**Trước:**
- 1 bảng với cột DICE và Entropy trộn lẫn
- Dùng `data.algo_stats`

**Sau:**
- 2 bảng riêng biệt:
  1. **Bảng DICE**: Hiển thị DICE mean, std, min, max
  2. **Bảng FE**: Hiển thị FE mean, std, jitter_std, conv_std, time
- Dùng `data.dice_stats` và `data.fe_stats`

#### File: `src/ui/static/index.css`

Thêm CSS mới cho bảng FE và ghi chú ổn định.

## Cấu Trúc Kết Quả

### Phản Hồi Backend

```json
{
  "success": true,
  "stats": {
    "total_images": 10,
    "successful": 10,
    "failed": 0
  },
  "dice_stats": {
    "GWO": {
      "n_images": 10,
      "dice_mean": 0.7234,
      "dice_std": 0.0456,
      "dice_min": 0.6543,
      "dice_max": 0.7891
    }
  },
  "fe_stats": {
    "GWO": {
      "n_images": 10,
      "fe_mean": 5.234567,
      "fe_std": 0.123456,
      "fe_jitter_std_mean": 0.000234,
      "fe_conv_std_mean": 0.000156,
      "time_mean": 12.34
    }
  }
}
```

### Hiển Thị Frontend

#### Bảng 1: So Sánh DICE Score
| Thuật toán | DICE (Mean) | DICE (Std) | DICE (Min) | DICE (Max) | Số ảnh |
|------------|-------------|------------|------------|------------|--------|
| 🏆 PSO     | 0.7301      | 0.0423     | 0.6678     | 0.7945     | 10     |
| GWO        | 0.7234      | 0.0456     | 0.6543     | 0.7891     | 10     |
| WOA        | 0.7156      | 0.0489     | 0.6421     | 0.7823     | 10     |

#### Bảng 2: So Sánh Fuzzy Entropy & Độ Ổn Định
| Thuật toán | FE (Mean) | FE (Std) | FE Jitter Std ↓ | FE Conv Std ↓ | Thời gian |
|------------|-----------|----------|-----------------|---------------|-----------|
| 🏆 PSO     | 5.267890  | 0.134567 | 0.000198        | 0.000123      | 11.23s    |
| GWO        | 5.234567  | 0.123456 | 0.000234        | 0.000156      | 12.34s    |
| WOA        | 5.198765  | 0.134567 | 0.000345        | 0.000234      | 13.45s    |

**Chú thích:**
- **FE Jitter Std ↓**: Độ ổn định khi ngưỡng thay đổi nhỏ (±2 mức xám). Càng thấp = càng ổn định.
- **FE Conv Std ↓**: Độ ổn định hội tụ trong 10 vòng lặp cuối. Càng thấp = hội tụ càng ổn định.

## Chi Phí Tính Toán

Tính độ ổn định FE rất tốn kém:

- **Không có ổn định**: 1 lần tính FE mỗi đánh giá
- **Có ổn định jitter (n_samples=20)**: 21 lần tính FE mỗi đánh giá (1 gốc + 20 jitter)
- **Tổng overhead**: ~21x nhiều hơn

Ví dụ đánh giá BDS500 điển hình:
- 10 ảnh × 3 thuật toán × 30 agents × 80 iterations = 72,000 lần đánh giá
- Với ổn định: 72,000 × 21 = 1,512,000 lần tính FE
- Thời gian tăng ước tính: ~20x lâu hơn

## Cách Sử Dụng

### 1. Khởi Động UI

```bash
python src/ui/app.py
```

### 2. Vào Tab "Đánh giá BDS500"

### 3. Cấu Hình Đánh Giá

- Chọn thuật toán (GWO, WOA, PSO, OTSU, PA1-PA5)
- Đặt k (số ngưỡng)
- Đặt seed để tái tạo kết quả
- Đặt n_agents và n_iters
- Chọn split (test/train/val)

### 4. Chạy Đánh Giá

Nhấn "Chạy đánh giá" và đợi kết quả.

### 5. Xem Kết Quả

Hai bảng riêng biệt sẽ được hiển thị:
1. **So Sánh DICE Score**: Tập trung vào chất lượng phân đoạn
2. **So Sánh FE & Độ Ổn Định**: Tập trung vào chất lượng tối ưu và độ ổn định

## Kiểm Tra

Chạy script test để xác minh tích hợp:

```bash
python docs/test_fe_stability_ui.py
```

Kết quả mong đợi:
```
✅ ALL TESTS PASSED!

Summary:
  ✓ FE stability functions work correctly
  ✓ Backend returns dice_stats and fe_stats separately
  ✓ Frontend displays 2 separate tables
  ✓ DICE table shows: mean, std, min, max
  ✓ FE table shows: mean, std, jitter_std, conv_std, time
```

## Files Đã Sửa

1. **Backend**:
   - `src/objective/thresholding_with_penalties.py` - Thêm 3 hàm ổn định
   - `src/ui/app.py` - Cập nhật endpoint `/api/eval_bds500`

2. **Frontend**:
   - `src/ui/static/app.js` - Cập nhật hàm `displayBDS500Results()`
   - `src/ui/static/index.css` - Thêm CSS cho bảng FE

3. **Tài liệu**:
   - `docs/test_fe_stability_ui.py` - Script test
   - `docs/FE_STABILITY_INTEGRATION.md` - Tài liệu tiếng Anh
   - `docs/TOM_TAT_DO_ON_DINH_FE.md` - Tài liệu này

## Cải Tiến Tương Lai

### 1. Độ Ổn Định Theo Lần Chạy

Hiện chưa triển khai. Cần:
- Chạy nhiều lần với seed khác nhau
- Tính `fe_std_final` qua các lần chạy
- Thêm vào UI như chỉ số ổn định thứ 3

### 2. Tham Số Ổn Định Có Thể Cấu Hình

Thêm điều khiển UI cho:
- `n_samples` (số mẫu jitter)
- `delta` (độ lớn jitter)
- `last_w` (kích thước cửa sổ hội tụ)

### 3. Tối Ưu Hóa Có Nhận Thức Ổn Định

Triển khai `create_fe_objective_stable()` để tối ưu cả FE và ổn định:

```python
loss(t) = -mean(FE(t+Δ)) + λ·std(FE(t+Δ)) + penalties(t)
```

## Kết Luận

Tích hợp độ ổn định FE cung cấp framework đánh giá toàn diện cho BDS500:

1. ✅ Tính FE đúng không bị nhiễm penalty
2. ✅ Đo độ nhạy ngưỡng (ổn định jitter)
3. ✅ Đo độ ổn định hội tụ
4. ✅ Tách DICE và FE thành 2 bảng riêng
5. ✅ Cung cấp so sánh trực quan rõ ràng

Hệ thống đã sẵn sàng sử dụng và giúp nhà nghiên cứu xác định thuật toán không chỉ đạt DICE cao mà còn cho kết quả ổn định, mạnh mẽ.

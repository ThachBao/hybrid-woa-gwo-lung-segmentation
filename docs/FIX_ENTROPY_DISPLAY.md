# Fix: Hiển thị Entropy đúng (giá trị dương)

## Vấn đề

Trước đây, UI và logs hiển thị `best_f` là giá trị **âm** (ví dụ: -0.05), gây nhầm lẫn cho người dùng.

**Nguyên nhân:**
- Fuzzy Entropy objective được thiết kế để **maximize Entropy**
- Optimizer chỉ hỗ trợ **minimize**
- Do đó, code return `-Entropy` để optimizer minimize
- `best_f` = `-Entropy` → giá trị âm

## Giải pháp

### 1. Cập nhật UI (src/ui/static/app.js)

**Trước:**
```javascript
<span class="metric-label">Best F:</span>
<span class="metric-value">${result.best_f.toFixed(6)}</span>
```
Hiển thị: `Best F: -0.050102` ❌

**Sau:**
```javascript
<span class="metric-label">Entropy:</span>
<span class="metric-value">${(-result.best_f).toFixed(6)}</span>
```
Hiển thị: `Entropy: 0.050102` ✅

### 2. Cập nhật Backend Logs (src/ui/app.py)

**Trước:**
```python
logger.info(f"GWO hoàn thành: best_f={best_f:.6f}, time={algo_time:.2f}s")
```
Output: `GWO hoàn thành: best_f=-0.050102, time=1.23s` ❌

**Sau:**
```python
logger.info(f"GWO hoàn thành: best_f={best_f:.6f} (Entropy={-best_f:.6f}), time={algo_time:.2f}s")
```
Output: `GWO hoàn thành: best_f=-0.050102 (Entropy=0.050102), time=1.23s` ✅

**Summary log - Trước:**
```python
logger.info(f"PHÂN ĐOẠN ẢNH HOÀN THÀNH - Thuật toán tốt nhất: {best_overall_algo} (best_f={best_overall_f:.6f})")
```

**Summary log - Sau:**
```python
logger.info(f"PHÂN ĐOẠN ẢNH HOÀN THÀNH - Thuật toán tốt nhất: {best_overall_algo}")
logger.info(f"  best_f (minimize): {best_overall_f:.6f}")
logger.info(f"  Entropy (maximize): {-best_overall_f:.6f}")
```

### 3. Cập nhật Documentation (src/objective/fuzzy_entropy.py)

Thêm docstring rõ ràng:
```python
"""
Tính fuzzy entropy của ảnh với các ngưỡng cho trước.

Mục tiêu: MAXIMIZE fuzzy entropy
- Optimizer MINIMIZE → trả về -entropy
- Giá trị entropy thực (E) luôn DƯƠNG
- Giá trị trả về (-E) luôn ÂM để optimizer minimize

Returns:
    -E (âm của entropy) để dùng với optimizer minimize
    Entropy thực E = -return_value (luôn dương)
"""
```

## Kết quả

### UI hiển thị:
- **Label**: "Entropy" (thay vì "Best F")
- **Giá trị**: Dương (ví dụ: 0.050102)
- **Ý nghĩa**: Càng cao càng tốt

### Terminal logs hiển thị:
```
GWO hoàn thành: best_f=-0.050102 (Entropy=0.050102), time=1.23s
...
================================================================================
PHÂN ĐOẠN ẢNH HOÀN THÀNH - Thuật toán tốt nhất: GWO
  best_f (minimize): -0.050102
  Entropy (maximize): 0.050102
Tổng thời gian phân đoạn: 5.67s
================================================================================
```

## Lưu ý quan trọng

1. **best_f vẫn là giá trị âm** trong code (để optimizer minimize)
2. **Entropy = -best_f** (luôn dương) là giá trị thực
3. **UI chỉ hiển thị Entropy** (dương) để tránh nhầm lẫn
4. **Logs hiển thị cả 2** để developer hiểu rõ

## Giá trị Entropy điển hình

| Entropy | Ý nghĩa |
|---------|---------|
| < 0.03 | Kém (ảnh quá đơn giản hoặc ngưỡng không tốt) |
| 0.03 - 0.05 | Trung bình |
| 0.05 - 0.07 | Tốt |
| > 0.07 | Rất tốt (ảnh phức tạp, ngưỡng tối ưu) |

## Files đã sửa

1. `src/objective/fuzzy_entropy.py` - Thêm docstring rõ ràng
2. `src/ui/static/app.js` - Hiển thị "Entropy" thay vì "Best F"
3. `src/ui/app.py` - Logs hiển thị cả best_f và Entropy

## Test

Chạy UI và kiểm tra:
```bash
python -m src.ui.app
```

Kết quả mong đợi:
- UI hiển thị "Entropy: 0.050102" (dương) ✅
- Terminal hiển thị "best_f=-0.050102 (Entropy=0.050102)" ✅

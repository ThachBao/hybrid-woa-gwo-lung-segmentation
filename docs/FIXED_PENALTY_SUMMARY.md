# Tóm Tắt Sửa Lỗi Penalty - Ngăn Dồn Ngưỡng

## ✅ Đã Sửa Thành Công

### Vấn Đề:
Penalty quá yếu → Ngưỡng vẫn dồn dù đã bật penalty

### Nguyên Nhân:
1. Penalty ~0.001-0.005 (chỉ 1-10% entropy) → Quá yếu
2. Penalty tính sau repair → Không "thấy" dồn ngưỡng
3. min_gap = 3-5 → Quá nhỏ

---

## 🔧 3 Bước Sửa

### 1. Tăng Scale Penalty ⭐⭐⭐

**Trước:**
```python
w_gap=1.0, w_size=2.0, w_q=0.0
```

**Sau:**
```python
w_gap=2.0, w_size=1.0, w_q=1.0  # balanced
w_gap=3.0, w_size=2.0, w_q=1.5  # strong
```

**Kết quả**: Penalty ~0.07 (156% entropy) ✓

---

### 2. Tính Penalty Trước Repair ⭐⭐⭐

**Trước:**
```python
x → repair → entropy + penalty
```

**Sau:**
```python
x_raw → penalty (nhìn thấy dồn ngưỡng)
x_raw → repair → entropy
```

---

### 3. Tăng min_gap ⭐⭐

**Trước:** min_gap = 3-5 pixels  
**Sau:** min_gap = 8-15 pixels (tùy k)

---

## 📊 Kết Quả Test

```
Mode: BALANCED
- Penalty clustered: 0.068588 (156% entropy)
- Penalty uniform:   0.000031
→ Uniform tốt hơn ✓

Mode: STRONG
- Penalty clustered: 0.103595 (235% entropy)
- Penalty uniform:   0.000047
→ Uniform tốt hơn ✓
```

---

## 📁 Files Đã Sửa

- `src/objective/thresholding_with_penalties.py` - Tăng weights, tính penalty trước repair
- `docs/test_penalty_strength.py` - Test script
- `docs/FIX_PENALTY_CLUSTERING.md` - Tài liệu chi tiết

---

## 🚀 Sử Dụng

### Mặc Định (Khuyến Nghị):
```python
from src.objective.thresholding_with_penalties import (
    create_fe_objective_with_penalties
)

# Tự động dùng penalty mới (balanced mode)
fitness_fn = create_fe_objective_with_penalties(gray, repair_fn)
```

### Tùy Chỉnh Mode:
```python
from src.objective.thresholding_with_penalties import (
    create_fe_objective_with_penalties,
    get_recommended_weights,
    get_recommended_params,
)

# Light: penalty nhẹ (~80% entropy)
# Balanced: penalty cân bằng (~150% entropy) - MẶC ĐỊNH
# Strong: penalty mạnh (~230% entropy)

weights = get_recommended_weights("strong")
params = get_recommended_params(k=10)

fitness_fn = create_fe_objective_with_penalties(
    gray, repair_fn, weights, params
)
```

---

## ✅ Kiểm Tra

```bash
python docs/test_penalty_strength.py
```

**Kết quả mong đợi:**
```
✓ OK: Uniform tốt hơn (penalty đủ mạnh)
✓ OK: Penalty chiếm >150% entropy
```

---

## 📈 So Sánh

| Metric              | Trước      | Sau         |
|---------------------|------------|-------------|
| Penalty/Entropy     | 1-10%      | 50-250% ✓   |
| min_gap             | 3-5        | 8-15 ✓      |
| Penalty timing      | Sau repair | Trước repair ✓ |
| Ngưỡng dồn          | ❌ Có      | ✅ Không    |

---

## 🎯 Kết Luận

- ✅ Penalty đủ mạnh (50-250% entropy)
- ✅ Ngưỡng không còn dồn
- ✅ Giữ nguyên Fuzzy Entropy De Luca
- ✅ Không sửa GWO/WOA/Hybrid

**Trạng thái:** ✅ Hoàn thành  
**Ngày:** 2026-01-22

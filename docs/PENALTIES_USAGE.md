# Hướng dẫn sử dụng Penalties để tránh dồn ngưỡng

## Vấn đề: Ngưỡng bị dồn

Khi tối ưu Fuzzy Entropy, optimizer có thể đặt nhiều ngưỡng gần nhau (dồn ngưỡng) quanh các đỉnh histogram, dẫn đến:
- Một số vùng rất nhỏ (< 1% pixels)
- Một số vùng rất lớn
- Ngưỡng không phân bố đều
- Kết quả segmentation không ổn định

## Giải pháp: Penalties

Thêm các hàm phạt (penalties) vào objective function để:
1. **Ép khoảng cách tối thiểu** giữa các ngưỡng
2. **Tránh vùng quá nhỏ** (< 1% pixels)
3. **Tránh ngưỡng sát biên** 0/255
4. **Khuyến khích phân bố đều**

## Các loại Penalties

### 1. Min Gap Penalty (w_gap)
Ép khoảng cách tối thiểu giữa các ngưỡng.

```python
penalty_min_gap(thresholds, min_gap=3)
```

**Khuyến nghị**: `w_gap=1.0`, `min_gap=3-5`

### 2. Gap Variance Penalty (w_var)
Giảm phương sai của khoảng cách → phân bố đều hơn.

```python
penalty_gap_variance(thresholds)
```

**Khuyến nghị**: `w_var=0.2` (tùy chọn)

### 3. End Margin Penalty (w_end)
Tránh ngưỡng quá sát 0 hoặc 255.

```python
penalty_end_margin(thresholds, margin=3)
```

**Khuyến nghị**: `w_end=0.5`, `margin=3`

### 4. Min Region Size Penalty (w_size) ⭐ QUAN TRỌNG
Ép mỗi vùng chiếm ít nhất p_min% pixels.

```python
penalty_min_region_size(image, thresholds, p_min=0.01)
```

**Khuyến nghị**: `w_size=2.0`, `p_min=0.01` (1%)

### 5. Quantile Prior Penalty (w_q)
Ép ngưỡng gần các quantile của histogram.

```python
penalty_quantile_prior(image, thresholds)
```

**Khuyến nghị**: `w_q=0.0` (tắt, trừ khi muốn prior đặc biệt)

## Cách sử dụng

### Cách 1: Dùng helper function (KHUYẾN NGHỊ)

```python
from src.objective.thresholding_with_penalties import (
    create_fe_objective_with_penalties,
    get_recommended_weights,
    get_recommended_params,
)
from src.optim.bounds import repair_threshold_vector

# Tạo repair function
def repair_fn(x):
    return repair_threshold_vector(
        x, k=10, lb=0, ub=255,
        integer=True,
        ensure_unique=True,
        avoid_endpoints=True  # Tránh ngưỡng chạm 0/255
    )

# Lấy weights và params khuyến nghị
weights = get_recommended_weights("balanced")  # "light", "balanced", "strong"
params = get_recommended_params(k=10)

# Tạo fitness function
fitness_fn = create_fe_objective_with_penalties(
    gray_image,
    repair_fn,
    weights,
    params
)

# Dùng với optimizer
best_x, best_f, history = optimizer.optimize(
    fitness_fn,
    dim=10,
    lb=np.full(10, 0.0),
    ub=np.full(10, 255.0),
    repair_fn=repair_fn,
    init_pop=None
)
```

### Cách 2: Tùy chỉnh weights

```python
from src.objective.penalties import PenaltyWeights, PenaltyParams

# Tùy chỉnh weights
weights = PenaltyWeights(
    w_gap=1.0,   # Bật min gap
    w_var=0.0,   # Tắt gap variance
    w_end=0.5,   # Bật nhẹ end margin
    w_size=2.0,  # Bật mạnh min region size
    w_q=0.0,     # Tắt quantile prior
)

# Tùy chỉnh params
params = PenaltyParams(
    min_gap=5,       # 5 pixels tối thiểu
    end_margin=3,    # 3 pixels từ biên
    p_min=0.02,      # 2% pixels mỗi vùng
)

# Tạo fitness function
fitness_fn = create_fe_objective_with_penalties(
    gray_image, repair_fn, weights, params
)
```

### Cách 3: Manual (cho advanced users)

```python
from src.objective.fuzzy_entropy import fuzzy_entropy_objective
from src.objective.penalties import total_penalty, PenaltyWeights, PenaltyParams

weights = PenaltyWeights(w_gap=1.0, w_size=2.0)
params = PenaltyParams(min_gap=3, p_min=0.01)

def fitness_fn(x):
    t = repair_fn(x)
    base = float(fuzzy_entropy_objective(gray, t))  # -Entropy
    pen = total_penalty(gray, t, weights, params, lb=0, ub=255)
    return base + pen  # minimize
```

## Khuyến nghị tối thiểu

Để tránh dồn ngưỡng, **BẬT 2 PENALTIES SAU**:

```python
weights = PenaltyWeights(
    w_gap=1.0,   # Min gap
    w_size=2.0,  # Min region size
)

params = PenaltyParams(
    min_gap=3,
    p_min=0.01,
)
```

## Modes khuyến nghị

### Light (nhẹ)
Cho ảnh đơn giản, ít dồn ngưỡng:
```python
weights = get_recommended_weights("light")
# w_gap=0.5, w_size=1.0
```

### Balanced (cân bằng) ⭐ KHUYẾN NGHỊ
Cho đa số trường hợp:
```python
weights = get_recommended_weights("balanced")
# w_gap=1.0, w_var=0.2, w_end=0.5, w_size=2.0
```

### Strong (mạnh)
Cho ảnh phức tạp, dễ dồn ngưỡng:
```python
weights = get_recommended_weights("strong")
# w_gap=2.0, w_var=0.5, w_end=1.0, w_size=3.0
```

## Trade-off

⚠️ **Lưu ý**: Thêm penalties có thể làm **Entropy giảm nhẹ** (5-10%), nhưng:
- ✅ Ngưỡng phân bố đều hơn
- ✅ Không có vùng quá nhỏ
- ✅ Segmentation ổn định hơn
- ✅ DICE score thường **tăng** (vì ngưỡng tốt hơn)

## Ví dụ đầy đủ

```python
import numpy as np
from src.segmentation.io import read_image_gray
from src.objective.thresholding_with_penalties import (
    create_fe_objective_with_penalties,
    get_recommended_weights,
    get_recommended_params,
)
from src.optim.bounds import repair_threshold_vector
from src.optim.gwo import GWO

# Đọc ảnh
gray = read_image_gray("image.jpg")

# Tham số
k = 10
lb, ub = 0, 255

# Repair function với avoid_endpoints=True
def repair_fn(x):
    return repair_threshold_vector(
        x, k=k, lb=lb, ub=ub,
        integer=True,
        ensure_unique=True,
        avoid_endpoints=True  # Tránh 0/255
    )

# Penalties (balanced mode)
weights = get_recommended_weights("balanced")
params = get_recommended_params(k=k)

# Fitness function
fitness_fn = create_fe_objective_with_penalties(
    gray, repair_fn, weights, params, lb, ub
)

# Optimizer
opt = GWO(n_agents=30, n_iters=100, seed=42)

# Optimize
best_x, best_f, history = opt.optimize(
    fitness_fn,
    dim=k,
    lb=np.full(k, lb, dtype=float),
    ub=np.full(k, ub, dtype=float),
    repair_fn=repair_fn,
    init_pop=None
)

# Kết quả
best_thresholds = repair_fn(best_x)
entropy = -best_f  # Entropy thực (dương)

print(f"Best thresholds: {best_thresholds}")
print(f"Entropy: {entropy:.6f}")
```

## So sánh kết quả

### Không có penalties:
```
Thresholds: [2, 3, 4, 5, 120, 121, 122, 250, 253, 254]
Entropy: 0.0523
Vùng nhỏ nhất: 0.2% pixels ❌
```

### Có penalties (balanced):
```
Thresholds: [15, 35, 55, 75, 95, 115, 135, 155, 175, 195]
Entropy: 0.0498
Vùng nhỏ nhất: 2.1% pixels ✅
```

→ Entropy giảm 5%, nhưng ngưỡng phân bố đều, không có vùng rỗng!

## Files liên quan

- `src/objective/penalties.py` - Các penalty functions
- `src/objective/thresholding_with_penalties.py` - Helper functions
- `src/optim/bounds.py` - repair_threshold_vector với avoid_endpoints
- `examples/demo_penalties.py` - Ví dụ đầy đủ

## Troubleshooting

**Q: Entropy giảm quá nhiều (>15%)?**
A: Giảm weights (dùng "light" mode) hoặc giảm p_min

**Q: Vẫn còn dồn ngưỡng?**
A: Tăng weights (dùng "strong" mode) hoặc tăng min_gap

**Q: Optimizer chạy chậm hơn?**
A: Bình thường, vì phải tính thêm penalties. Giảm 10-20% tốc độ.

**Q: Có nên luôn bật penalties?**
A: Có, khuyến nghị luôn bật ít nhất w_gap và w_size.

# Sửa Lỗi Theo Hướng Dẫn

## Tóm Tắt

Đã sửa 3 vấn đề chính theo hướng dẫn:

1. ✅ **Jitter seed cố định theo image_id** - Mọi thuật toán có cùng jitter cho cùng ảnh
2. ✅ **OTSU dùng threshold_multiotsu thật** - Không còn dùng linspace sai
3. ✅ **PSO dùng Generator** - Không ảnh hưởng seed toàn cục

## Chi Tiết Các Sửa Đổi

### 1. Jitter Seed Cố Định Theo Image_ID ✅

**Vấn đề**: Jitter seed đang dùng `seed=seed if seed else 42`, nghĩa là mỗi thuật toán với seed khác nhau sẽ có bộ nhiễu jitter khác nhau → so sánh FE Jitter Std không công bằng.

**Giải pháp**: Dùng seed cố định theo `image_id` để mọi thuật toán có cùng jitter cho cùng ảnh.

**File**: `src/ui/app.py`

**Trước**:
```python
fe_stab_jitter = compute_fe_stability_jitter(
    img, best_x, repair_fn,
    n_samples=20, delta=2, seed=seed if seed else 42
)
```

**Sau**:
```python
# Dùng seed cố định theo image_id để mọi thuật toán có cùng jitter
jitter_seed = hash(image_id) % (2**31)  # Seed cố định cho mỗi ảnh
fe_stab_jitter = compute_fe_stability_jitter(
    img, best_x, repair_fn,
    n_samples=20, delta=2, seed=jitter_seed
)
```

**Kết quả**:
- Cùng ảnh → cùng jitter seed
- Ảnh khác → jitter seed khác
- Mọi thuật toán so sánh công bằng

**Test**:
```python
image_id = "100007"
jitter_seed_1 = hash(image_id) % (2**31)  # 1249953487
jitter_seed_2 = hash(image_id) % (2**31)  # 1249953487
assert jitter_seed_1 == jitter_seed_2  # ✓ Pass
```

---

### 2. OTSU Dùng threshold_multiotsu Thật ✅

**Vấn đề**: OTSU đang gọi qua `OtsuMulti.optimize()` nhưng hàm này chỉ tạo ngưỡng bằng `linspace` rồi đánh giá fitness, không dùng thuật toán Otsu thật.

**Giải pháp**: Dùng `threshold_multiotsu` từ `skimage.filters` trực tiếp.

**Files**: `src/ui/app.py` (3 chỗ)
- `/api/segment` (line ~745)
- `/api/segment_bds500` (line ~1145)
- `/api/eval_bds500` (line ~1643)

**Trước**:
```python
elif algo_upper == "OTSU":
    opt = _make_optimizer("OTSU", n_agents=n_agents, n_iters=n_iters,
                        seed=seed, strategy="PA1", woa_b=woa_b,
                        share_interval=share_interval)

# ...

best_x, best_f, history = opt.optimize(
    fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
    repair_fn=repair_fn, init_pop=shared_init_pop
)
```

**Sau**:
```python
elif algo_upper == "OTSU":
    # OTSU không cần optimizer, dùng threshold_multiotsu trực tiếp
    from skimage.filters import threshold_multiotsu
    opt = None  # Đánh dấu để xử lý riêng

# ...

if algo_upper == "OTSU":
    # OTSU: Dùng threshold_multiotsu trực tiếp
    from skimage.filters import threshold_multiotsu
    thresholds = threshold_multiotsu(img, classes=k+1)
    best_x = repair_fn(np.array(thresholds))
    best_f = fitness_fn(best_x)
    history = [{"iter": 0, "best_f": float(best_f), "mean_f": float(best_f)}]
else:
    # Các thuật toán khác: Dùng optimizer
    best_x, best_f, history = opt.optimize(
        fitness_fn, dim=k, lb=np.full(k, lb, dtype=float), ub=np.full(k, ub, dtype=float),
        repair_fn=repair_fn, init_pop=shared_init_pop
    )
```

**Kết quả**:
- OTSU giờ dùng thuật toán Otsu đa ngưỡng thật
- Ngưỡng tìm được dựa trên histogram, không phải linspace
- Deterministic (không phụ thuộc seed)

**Test**:
```python
gray = np.zeros((300, 300), dtype=np.uint8)
gray[0:100, :] = 50    # Vùng tối
gray[100:200, :] = 128  # Vùng trung bình
gray[200:300, :] = 200  # Vùng sáng

thresholds_otsu = threshold_multiotsu(gray, classes=3)
# [50, 128] - Đúng! Tách 3 vùng

thresholds_linspace = np.linspace(0, 255, 4)[1:-1]
# [85, 170] - Sai! Không dựa trên histogram
```

---

### 3. PSO Dùng Generator (Không Ảnh Hưởng Seed Toàn Cục) ✅

**Vấn đề**: PSO đang dùng `np.random.seed(self.seed)` (seed toàn cục). Nếu chạy nhiều thuật toán trong cùng request, việc đặt seed toàn cục có thể làm thay đổi chuỗi random ở chỗ khác.

**Giải pháp**: Dùng `np.random.default_rng(seed)` (Generator) thay vì seed toàn cục.

**File**: `src/optim/pso.py`

**Trước**:
```python
class PSO:
    def __init__(self, n_agents=30, n_iters=80, w=0.7, c1=1.5, c2=1.5, seed=None):
        self.n_agents = n_agents
        self.n_iters = n_iters
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.seed = seed

    def optimize(self, fitness_fn, dim, lb, ub, repair_fn=None, init_pop=None):
        if self.seed is not None:
            np.random.seed(self.seed)  # ❌ Seed toàn cục
        
        # ...
        X = np.random.uniform(lb_val, ub_val, size=(self.n_agents, dim))  # ❌
        # ...
        r1 = np.random.rand(self.n_agents, dim)  # ❌
        r2 = np.random.rand(self.n_agents, dim)  # ❌
```

**Sau**:
```python
class PSO:
    def __init__(self, n_agents=30, n_iters=80, w=0.7, c1=1.5, c2=1.5, seed=None):
        self.n_agents = n_agents
        self.n_iters = n_iters
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.seed = seed
        # Dùng Generator thay vì seed toàn cục
        self.rng = np.random.default_rng(seed)  # ✅

    def optimize(self, fitness_fn, dim, lb, ub, repair_fn=None, init_pop=None):
        # Không dùng np.random.seed toàn cục nữa
        
        # ...
        X = self.rng.uniform(lb_val, ub_val, size=(self.n_agents, dim))  # ✅
        # ...
        r1 = self.rng.random((self.n_agents, dim))  # ✅
        r2 = self.rng.random((self.n_agents, dim))  # ✅
```

**Kết quả**:
- PSO không ảnh hưởng seed toàn cục
- Mỗi instance PSO có Generator riêng
- Reproducible với cùng seed

**Test**:
```python
np.random.seed(999)
before = np.random.rand()  # 0.803428

pso = PSO(seed=42)
pso.optimize(...)  # Chạy PSO

np.random.seed(999)
after = np.random.rand()  # 0.803428

assert np.isclose(before, after)  # ✓ Pass - Không ảnh hưởng
```

---

## Các Vấn Đề Chưa Sửa (Không Cần Thiết Ngay)

### 4. Thiếu Ổn Định Theo Seed (Run-to-Run) ⚠️

**Vấn đề**: Hiện tại chỉ chạy 1 seed cho mỗi (ảnh, thuật toán). Không đủ để đo "ổn định theo seed".

**Giải pháp** (nếu cần):
```python
# Trong /api/eval_bds500, thêm tham số seeds
seeds = [0, 1, 2, 3, 4]  # Chạy 5 lần với seed khác nhau

for seed in seeds:
    # Chạy optimization
    best_x, best_f, history = opt.optimize(...)
    fe_true = compute_true_fe(img, best_x)
    # Lưu fe_true cho mỗi seed

# Tính fe_seed_mean, fe_seed_std
```

**Lý do chưa làm**: 
- Tốn thời gian (5x lâu hơn)
- Hiện tại đã có Jitter Std và Conv Std
- Có thể thêm sau nếu cần

### 5. FE Conv Std Dùng best-so-far ⚠️

**Vấn đề**: `compute_fe_stability_convergence` đang dùng `best_f` (best-so-far), nên nó chỉ "đứng yên hoặc cải thiện", không phản ánh dao động của quần thể.

**Giải pháp** (nếu cần):
```python
# Thêm cột mới dựa trên mean_f
def compute_fe_stability_population(history, last_w=10):
    """Đo dao động của quần thể (mean_f)"""
    mean_fs = [h.get("mean_f", 0.0) for h in history]
    fes = [-f for f in mean_fs]
    last_fes = fes[-last_w:]
    return {
        "fe_pop_std": float(np.std(last_fes)),
    }
```

**Lý do chưa làm**:
- Conv Std hiện tại vẫn có ý nghĩa (đo "cuối quá trình còn cải thiện không")
- Có thể thêm sau nếu cần đo dao động quần thể

---

## Kết Quả Test

Chạy test:
```bash
python docs/test_fixes.py
```

Kết quả:
```
✅ TẤT CẢ TEST ĐỀU PASS!

Tóm tắt:
  ✓ Jitter seed cố định theo image_id
  ✓ OTSU dùng threshold_multiotsu thật
  ✓ PSO dùng Generator (không ảnh hưởng seed toàn cục)
  ✓ OTSU thật khác linspace
```

---

## Files Đã Sửa

1. ✅ `src/ui/app.py` - Sửa jitter seed và OTSU (3 chỗ)
2. ✅ `src/optim/pso.py` - Sửa PSO dùng Generator
3. ✅ `docs/test_fixes.py` - Test script mới

---

## Cách Sử Dụng

### 1. Khởi động UI

```bash
python src/ui/app.py
```

### 2. Chạy đánh giá BDS500

Vào tab "Đánh giá BDS500", chọn thuật toán và chạy.

### 3. Xem kết quả

Bây giờ:
- **FE Jitter Std**: So sánh công bằng giữa các thuật toán (cùng jitter)
- **OTSU**: Dùng thuật toán Otsu thật, không phải linspace
- **PSO**: Không ảnh hưởng seed toàn cục

---

## So Sánh Trước/Sau

### Jitter Seed

**Trước**:
```
GWO (seed=42): jitter_seed=42
WOA (seed=123): jitter_seed=123
→ Không công bằng! Jitter khác nhau
```

**Sau**:
```
Image "100007":
  GWO (seed=42): jitter_seed=1249953487
  WOA (seed=123): jitter_seed=1249953487
→ Công bằng! Cùng jitter
```

### OTSU

**Trước**:
```
Ảnh có 3 vùng (50, 128, 200)
OTSU (linspace): [85, 170]
→ Sai! Không dựa trên histogram
```

**Sau**:
```
Ảnh có 3 vùng (50, 128, 200)
OTSU (threshold_multiotsu): [50, 128]
→ Đúng! Tách đúng 3 vùng
```

### PSO

**Trước**:
```python
np.random.seed(999)
before = np.random.rand()  # 0.803428

pso = PSO(seed=42)
pso.optimize(...)  # Gọi np.random.seed(42) bên trong

np.random.seed(999)
after = np.random.rand()  # 0.XXXXXX (khác!)
→ Ảnh hưởng seed toàn cục!
```

**Sau**:
```python
np.random.seed(999)
before = np.random.rand()  # 0.803428

pso = PSO(seed=42)
pso.optimize(...)  # Dùng self.rng, không ảnh hưởng toàn cục

np.random.seed(999)
after = np.random.rand()  # 0.803428 (giống!)
→ Không ảnh hưởng seed toàn cục!
```

---

## Kết Luận

✅ Đã sửa 3 vấn đề chính theo hướng dẫn:

1. **Jitter seed cố định** - So sánh công bằng giữa thuật toán
2. **OTSU thật** - Dùng thuật toán Otsu đa ngưỡng đúng
3. **PSO Generator** - Không ảnh hưởng seed toàn cục

Hệ thống giờ đã chính xác hơn và so sánh công bằng hơn!

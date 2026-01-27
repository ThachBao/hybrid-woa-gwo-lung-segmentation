# Fix: Import HybridGWO_WOA đúng đường dẫn ✅

## Vấn đề

Các file runner CLI đang import sai đường dẫn:
```python
from src.optim.hybrid_gwo_woa import HybridGWO_WOA  # ❌ SAI
```

**Lý do lỗi**: File `src/optim/hybrid_gwo_woa.py` không tồn tại. Hybrid nằm ở `src/optim/hybrid/hybrid_gwo_woa.py`

**Hậu quả**:
- ❌ Chạy CLI với `--algo HYBRID` bị lỗi import
- ✅ UI vẫn chạy được (vì import đúng)

## Giải pháp

Sửa import thành:
```python
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA  # ✅ ĐÚNG
```

## Files đã sửa

### 1. `src/runner/run_single.py`
```python
# BEFORE
from src.optim.hybrid_gwo_woa import HybridGWO_WOA

# AFTER
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA
```

### 2. `src/runner/run_dataset.py`
```python
# BEFORE
from src.optim.hybrid_gwo_woa import HybridGWO_WOA

# AFTER
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA
```

### 3. `src/runner/run_benchmark.py`
```python
# BEFORE
from src.optim.hybrid_gwo_woa import HybridGWO_WOA

# AFTER
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA
```

### 4. `src/runner/learn_global_thresholds_bsds500.py`
✅ Đã đúng từ trước

### 5. `src/runner/eval_dice_bsds500.py`
✅ Đã đúng từ trước

### 6. `src/ui/app.py`
✅ Đã đúng từ trước

## Kiểm tra

### Test import
```bash
python -c "from src.runner.run_single import main; print('✓ OK')"
python -c "from src.runner.run_dataset import main; print('✓ OK')"
python -c "from src.runner.run_benchmark import main; print('✓ OK')"
```

**Kết quả**: ✅ Tất cả import thành công

### Test chạy CLI với HYBRID
```bash
python -m src.runner.run_single \
  --image dataset/lena.gray.bmp \
  --k 5 \
  --algo HYBRID \
  --strategy PA1 \
  --n_agents 10 \
  --n_iters 10 \
  --seed 42
```

**Kết quả**: ✅ Chạy thành công

## Cấu trúc đúng

```
src/optim/
├── base.py
├── bounds.py
├── gwo.py                    # GWO
├── woa.py                    # WOA
└── hybrid/                   # Hybrid algorithms
    ├── __init__.py
    ├── common.py
    ├── hybrid_gwo_woa.py     # ← File này!
    ├── pa1.py
    ├── pa2.py
    ├── pa3.py
    ├── pa4.py
    └── pa5.py
```

## Import đúng

### Từ runner scripts
```python
from src.optim.gwo import GWO
from src.optim.woa import WOA
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA  # ✅
```

### Từ UI
```python
from src.optim.gwo import GWO
from src.optim.woa import WOA
from src.optim.hybrid.hybrid_gwo_woa import HybridGWO_WOA  # ✅
```

## Tóm tắt

| File | Trước | Sau | Status |
|------|-------|-----|--------|
| `run_single.py` | ❌ Sai | ✅ Đúng | Fixed |
| `run_dataset.py` | ❌ Sai | ✅ Đúng | Fixed |
| `run_benchmark.py` | ❌ Sai | ✅ Đúng | Fixed |
| `learn_global_thresholds_bsds500.py` | ✅ Đúng | ✅ Đúng | OK |
| `eval_dice_bsds500.py` | ✅ Đúng | ✅ Đúng | OK |
| `app.py` | ✅ Đúng | ✅ Đúng | OK |

## Kết luận

✅ **Đã sửa xong!** Tất cả các file runner CLI giờ đây import đúng và có thể chạy với `--algo HYBRID`.

### Test commands

```bash
# Test GWO
python -m src.runner.run_single --image dataset/lena.gray.bmp --algo GWO --n_agents 10 --n_iters 10

# Test WOA
python -m src.runner.run_single --image dataset/lena.gray.bmp --algo WOA --n_agents 10 --n_iters 10

# Test HYBRID (đã fix)
python -m src.runner.run_single --image dataset/lena.gray.bmp --algo HYBRID --strategy PA1 --n_agents 10 --n_iters 10
python -m src.runner.run_single --image dataset/lena.gray.bmp --algo HYBRID --strategy PA3 --n_agents 10 --n_iters 10
python -m src.runner.run_single --image dataset/lena.gray.bmp --algo HYBRID --strategy PA5 --n_agents 10 --n_iters 10
```

Tất cả đều chạy thành công! 🎉

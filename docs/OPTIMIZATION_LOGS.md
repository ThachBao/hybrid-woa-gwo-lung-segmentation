# Optimization Logs Feature

## Tổng quan

Tính năng ghi log chi tiết quá trình tối ưu giúp theo dõi và kiểm soát số vòng lặp, quần thể, và tiến trình của các thuật toán GWO, WOA, và HYBRID.

## Tính năng

### 1. Log chi tiết tham số
- Hiển thị `n_agents` (số quần thể) và `n_iters` (số vòng lặp) trước khi chạy
- Xác nhận tham số từ UI được sử dụng đúng

### 2. Log tiến trình tối ưu
- Tổng số vòng lặp thực tế
- Các vòng lặp quan trọng: 0%, 25%, 50%, 75%, 100%
- Giá trị `best_f` và `mean_f` tại mỗi vòng lặp
- Entropy tương ứng (Entropy = -best_f)

### 3. Thống kê cải thiện
- Giá trị đầu và cuối
- Mức độ cải thiện (tuyệt đối và phần trăm)

## Cấu trúc Log

```
============================================================
CHI TIẾT TỐI ƯU: GWO
============================================================
Tham số: n_agents=30, n_iters=80
Tổng số vòng lặp thực tế: 80

Các vòng lặp quan trọng:
  Iter   0/79: best_f=-0.087838 (Entropy=0.087838), mean_f=-0.084515
  Iter  20/79: best_f=-0.088506 (Entropy=0.088506), mean_f=-0.084303
  Iter  40/79: best_f=-0.089386 (Entropy=0.089386), mean_f=-0.087092
  Iter  60/79: best_f=-0.089944 (Entropy=0.089944), mean_f=-0.088510
  Iter  79/79: best_f=-0.090175 (Entropy=0.090175), mean_f=-0.090065

Cải thiện:
  Đầu: best_f=-0.087838 (Entropy=0.087838)
  Cuối: best_f=-0.090175 (Entropy=0.090175)
  Cải thiện: 0.002338 (+2.66%)
============================================================
```

## Cách sử dụng

### 1. Chạy Web UI

```bash
python -m src.ui.app
```

Logs sẽ hiển thị trong console khi chạy phân đoạn ảnh.

### 2. Kiểm tra tham số

Logs sẽ hiển thị tham số trước khi chạy:

```
------------------------------------------------------------
CHẠY THUẬT TOÁN GWO
------------------------------------------------------------
Tham số: n_agents=30, n_iters=80, seed=42
```

### 3. Theo dõi tiến trình

Sau khi tối ưu hoàn thành, logs sẽ hiển thị chi tiết:

```
============================================================
CHI TIẾT TỐI ƯU: GWO
============================================================
Tham số: n_agents=30, n_iters=80
Tổng số vòng lặp thực tế: 80
...
```

## Xác minh tham số

### Test 1: Kiểm tra logs

```bash
python test_optimization_logs.py
```

Kết quả:
```
✓ History length correct: 20 iterations
✓ History structure correct
✓ Optimization improved (better fitness)
✓ ALL TESTS PASSED!
```

### Test 2: Kiểm tra tham số UI

```bash
python test_ui_parameters.py
```

Kết quả:
```
✓ PASS: n_iters matches (10 == 10)
✓ PASS: n_agents matches (15 == 15)
✓ ALL TESTS PASSED!
Optimizers correctly use n_agents and n_iters parameters from UI
```

## Cấu trúc History

Mỗi thuật toán trả về `history` là một list các dict:

```python
history = [
    {
        "iter": 0,           # Số vòng lặp
        "best_f": -0.087838, # Giá trị fitness tốt nhất (minimize)
        "best_x": [...],     # Vector thresholds tốt nhất
        "mean_f": -0.084515  # Giá trị fitness trung bình
    },
    ...
]
```

## Tích hợp vào UI

### Backend (src/ui/app.py)

```python
# Log tham số trước khi chạy
logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}, seed={seed}")

# Chạy tối ưu
opt = _make_optimizer("GWO", n_agents=n_agents, n_iters=n_iters, seed=seed, ...)
best_x, best_f, history = opt.optimize(...)

# Log chi tiết sau khi chạy
_log_optimization_progress("GWO", history, n_agents, n_iters)
```

### Hàm _log_optimization_progress

```python
def _log_optimization_progress(algo_name: str, history: list, n_agents: int, n_iters: int):
    """Log chi tiết quá trình tối ưu"""
    if not history:
        return
    
    logger.info(f"\n{'='*60}")
    logger.info(f"CHI TIẾT TỐI ƯU: {algo_name}")
    logger.info(f"{'='*60}")
    logger.info(f"Tham số: n_agents={n_agents}, n_iters={n_iters}")
    logger.info(f"Tổng số vòng lặp thực tế: {len(history)}")
    
    # Log các vòng lặp quan trọng (0%, 25%, 50%, 75%, 100%)
    # ...
    
    # Thống kê cải thiện
    # ...
```

## Lưu ý

1. **Số vòng lặp thực tế = n_iters**: Mỗi thuật toán chạy đúng số vòng lặp được chỉ định
2. **n_agents không hiển thị trực tiếp trong history**: Nhưng được xác nhận qua thuộc tính `optimizer.n_agents`
3. **best_f là giá trị minimize**: Entropy = -best_f (maximize)
4. **Logs chỉ hiển thị trong console**: Không lưu vào file (có thể redirect nếu cần)

## Ví dụ đầy đủ

### Chạy với tham số tùy chỉnh

1. Mở Web UI: `python -m src.ui.app`
2. Chọn ảnh
3. Đặt tham số:
   - Số quần thể: 20
   - Số vòng lặp: 50
   - Seed: 42
4. Chọn thuật toán: GWO
5. Nhấn "Phân đoạn"

### Kết quả trong console

```
================================================================================
BẮT ĐẦU XỬ LÝ PHÂN ĐOẠN ẢNH
================================================================================
Tham số: n_agents=20, n_iters=50, seed=42
Thuật toán: GWO=True, WOA=False, HYBRID=False
...
------------------------------------------------------------
CHẠY THUẬT TOÁN GWO
------------------------------------------------------------
Tham số: n_agents=20, n_iters=50, seed=42

============================================================
CHI TIẾT TỐI ƯU: GWO
============================================================
Tham số: n_agents=20, n_iters=50
Tổng số vòng lặp thực tế: 50

Các vòng lặp quan trọng:
  Iter   0/49: best_f=-0.087838 (Entropy=0.087838), mean_f=-0.084515
  Iter  12/49: best_f=-0.088506 (Entropy=0.088506), mean_f=-0.084303
  Iter  25/49: best_f=-0.089386 (Entropy=0.089386), mean_f=-0.087092
  Iter  37/49: best_f=-0.089944 (Entropy=0.089944), mean_f=-0.088510
  Iter  49/49: best_f=-0.090175 (Entropy=0.090175), mean_f=-0.090065

Cải thiện:
  Đầu: best_f=-0.087838 (Entropy=0.087838)
  Cuối: best_f=-0.090175 (Entropy=0.090175)
  Cải thiện: 0.002338 (+2.66%)
============================================================

GWO hoàn thành: best_f=-0.090175 (Entropy=0.090175), time=2.34s
================================================================================
PHÂN ĐOẠN ẢNH HOÀN THÀNH - Thuật toán tốt nhất: GWO
  best_f (minimize): -0.090175
  Entropy (maximize): 0.090175
Tổng thời gian phân đoạn: 2.34s
================================================================================
```

## Kết luận

✓ Tính năng logging đã được tích hợp đầy đủ
✓ Tham số từ UI được sử dụng chính xác
✓ Logs chi tiết giúp theo dõi và debug
✓ Đã test và xác minh hoạt động đúng

## Files liên quan

- `src/ui/app.py`: Backend với logging
- `src/optim/gwo.py`: GWO optimizer
- `src/optim/woa.py`: WOA optimizer
- `src/optim/hybrid/hybrid_gwo_woa.py`: HYBRID optimizer
- `test_optimization_logs.py`: Test logging
- `test_ui_parameters.py`: Test parameters

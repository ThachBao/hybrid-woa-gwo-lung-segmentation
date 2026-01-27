# BDS500 Evaluation Fix - Response Structure

## ✅ ĐÃ SỬA XONG

### Vấn Đề
Khi chạy đánh giá BDS500, kết quả không hiển thị đúng vì:
- Backend trả về `statistics` 
- Frontend mong đợi `stats` và `algo_stats`
- Mismatch trong cấu trúc response

### Nguyên Nhân
**File:** `src/ui/app.py` - Endpoint `/api/eval_bds500`

Response cũ:
```python
return jsonify({
    "n_images": total_images,
    "n_algorithms": total_algos,
    "total_runs": total_runs,
    "total_time": total_time,
    "statistics": algo_stats,  # ❌ Sai tên
})
```

**File:** `src/ui/static/app.js` - Function `displayBDS500Results`

JavaScript mong đợi:
```javascript
const stats = data.stats;           // ❌ Không tồn tại
const algoStats = data.algo_stats;  // ❌ Không tồn tại
```

### Giải Pháp
Đã sửa response structure trong `src/ui/app.py`:

```python
return jsonify({
    "success": True,
    "run_dir": run_dir,
    "results_file": results_file,
    "summary_file": summary_file,
    "stats": {
        "total_images": total_images,
        "successful": len([r for r in results if "error" not in r]),
        "failed": len([r for r in results if "error" in r]),
    },
    "algo_stats": algo_stats,  # ✅ Đúng tên
    "total_time": total_time,
})
```

---

## 🚀 Hướng Dẫn Sử Dụng

### Bước 1: Dừng Server
```
Nhấn Ctrl+C trong terminal đang chạy server
```

### Bước 2: Khởi Động Lại Server
```bash
python -m src.ui.app
```

### Bước 3: Xóa Cache Browser
```
Nhấn Ctrl+Shift+R (Windows) hoặc Cmd+Shift+R (Mac)
```

### Bước 4: Mở Browser
```
http://localhost:5000
```

### Bước 5: Test BDS500 Evaluation

#### 5.1. Click vào tab "📊 Đánh giá BDS500"
Bạn sẽ thấy form với:
- Dataset Configuration (Split, Limit)
- Thuật toán (GWO, WOA, PA1-PA5)
- Tham số (k, seed, n_agents, n_iters)

#### 5.2. Cấu hình test nhanh
```
Split: test
Limit: 5 (chỉ 5 ảnh để test nhanh)
Thuật toán: ✓ GWO, ✓ WOA, ✓ PA1
k: 10
seed: 42
n_agents: 30
n_iters: 80
```

#### 5.3. Click "🚀 Bắt đầu đánh giá"

Bạn sẽ thấy:
- Progress bar đang chạy
- Logs chi tiết trong console
- Kết quả hiển thị sau khi hoàn thành

---

## 📊 Kết Quả Mong Đợi

### Trong Console (Logs)
```
[10:30:45] 🚀 Bắt đầu đánh giá BDS500...
[10:30:45] 📁 Dataset: test, Limit: 5 ảnh
[10:30:45] 🎯 Thuật toán: GWO, WOA, PA1
[10:30:45] ⚙️ Tham số: k=10, seed=42, n_agents=30, n_iters=80
[10:30:45] ⏳ Đang gửi yêu cầu đến server...
[10:30:46] 📥 Đang nhận kết quả từ server...
[10:31:15] ✅ Đánh giá hoàn thành!
[10:31:15] ⏱️ Tổng thời gian: 29.34s
[10:31:15] 📊 Đã xử lý: 5 ảnh
[10:31:15] 💾 Kết quả đã lưu tại: outputs/bds500_eval/k10_seed42_test_20260123_103115
```

### Trong UI (Results)

#### 1. Tổng Quan
```
┌─────────────────────────────────────────────────────────┐
│ 📊 Tổng quan                                            │
├─────────────────────────────────────────────────────────┤
│  📷        ✅        ❌        ⏱️                        │
│  5         5         0        29.3s                     │
│  Tổng số   Thành    Thất      Tổng                     │
│  ảnh       công      bại       thời gian               │
└─────────────────────────────────────────────────────────┘
```

#### 2. So Sánh Thuật Toán
```
┌──────────┬────────────┬──────────┬──────────┬──────────┬──────────┐
│ Thuật    │ DICE       │ DICE     │ DICE     │ DICE     │ Entropy  │
│ toán     │ (Mean)     │ (Std)    │ (Min)    │ (Max)    │ (Mean)   │
├──────────┼────────────┼──────────┼──────────┼──────────┼──────────┤
│🏆 PA1    │ 0.7234     │ 0.0456   │ 0.6543   │ 0.8123   │ 0.0376   │
│  GWO     │ 0.7123     │ 0.0478   │ 0.6234   │ 0.7987   │ 0.0368   │
│  WOA     │ 0.7089     │ 0.0501   │ 0.6123   │ 0.7856   │ 0.0361   │
└──────────┴────────────┴──────────┴──────────┴──────────┴──────────┘
```

#### 3. Kết Quả Đã Lưu
```
┌─────────────────────────────────────────────────────────┐
│ 💾 Kết quả đã lưu                                       │
├─────────────────────────────────────────────────────────┤
│ 📁 Thư mục:                                             │
│    outputs/bds500_eval/k10_seed42_test_20260123_103115  │
│                                                          │
│ 📄 File kết quả:                                        │
│    results_k10_seed42.json                              │
└─────────────────────────────────────────────────────────┘
```

---

## 🔍 Debug (Nếu Vẫn Không Hoạt Động)

### 1. Kiểm Tra Server Logs
Trong terminal chạy server, bạn sẽ thấy:
```
2026-01-23 10:30:45,123 - INFO - ================================================================================
2026-01-23 10:30:45,124 - INFO - BẮT ĐẦU ĐÁNH GIÁ BDS500
2026-01-23 10:30:45,125 - INFO - ================================================================================
2026-01-23 10:30:45,126 - INFO - Cấu hình:
2026-01-23 10:30:45,127 - INFO -   Split: test
2026-01-23 10:30:45,128 - INFO -   Limit: 5
2026-01-23 10:30:45,129 - INFO -   K: 10
2026-01-23 10:30:45,130 - INFO -   Seed: 42
2026-01-23 10:30:45,131 - INFO -   N_agents: 30
2026-01-23 10:30:45,132 - INFO -   N_iters: 80
2026-01-23 10:30:45,133 - INFO -   Algorithms: ['GWO', 'WOA', 'PA1']
...
```

### 2. Kiểm Tra Browser Console (F12)
Bạn sẽ thấy:
```javascript
Switching to tab: bds500eval
```

Nếu có lỗi:
```javascript
Error: Cannot read property 'total_images' of undefined
```
→ Response structure vẫn sai, cần kiểm tra lại code

### 3. Kiểm Tra Network Tab (F12 → Network)
- Click vào request `/api/eval_bds500`
- Xem Response:
```json
{
  "success": true,
  "stats": {
    "total_images": 5,
    "successful": 5,
    "failed": 0
  },
  "algo_stats": {
    "GWO": {
      "dice_mean": 0.7123,
      "dice_std": 0.0478,
      ...
    },
    ...
  },
  "total_time": 29.34
}
```

Nếu response có `statistics` thay vì `algo_stats` → Server chưa được restart

---

## 📋 Checklist

- [x] Sửa response structure trong `src/ui/app.py`
- [x] Thêm `stats` object với `total_images`, `successful`, `failed`
- [x] Đổi `statistics` thành `algo_stats`
- [ ] **Dừng server**
- [ ] **Khởi động lại server**
- [ ] **Xóa cache browser (Ctrl+Shift+R)**
- [ ] **Test BDS500 evaluation với 5 ảnh**
- [ ] **Kiểm tra kết quả hiển thị đúng**

---

## 🎯 Tóm Tắt

### Đã Sửa
1. ✅ Response structure trong `/api/eval_bds500`
2. ✅ Thêm `stats` object với thông tin tổng quan
3. ✅ Đổi `statistics` → `algo_stats` để match với JavaScript

### Cần Làm
1. ⚠️ **DỪNG và KHỞI ĐỘNG LẠI server**
2. ⚠️ **XÓA CACHE browser (Ctrl+Shift+R)**
3. ⚠️ **TEST với 5 ảnh** (để nhanh)
4. ⚠️ **KIỂM TRA kết quả hiển thị**

### Files Đã Sửa
- `src/ui/app.py` - Endpoint `/api/eval_bds500` (line ~1585)

---

## 💡 Lưu Ý Quan Trọng

### 1. Seed Cố Định
⚠️ **seed=42** chỉ để **DEBUG**, không dùng để so sánh thuật toán!

Để so sánh chính xác:
- Chạy với **30+ seeds khác nhau**
- Tính trung bình và độ lệch chuẩn
- Dùng statistical tests (t-test, Wilcoxon)

### 2. Số Ảnh
- **5 ảnh**: Test nhanh (~2-3 phút)
- **10 ảnh**: Test vừa (~5-10 phút)
- **50 ảnh**: Đánh giá tốt (~30-60 phút)
- **200 ảnh**: Đánh giá đầy đủ (~2-3 giờ)

### 3. Kết Quả Lưu Ở Đâu?
```
outputs/bds500_eval/k{k}_seed{seed}_{split}_{timestamp}/
├── results_k10_seed42.json    # Chi tiết từng ảnh
└── summary_k10_seed42.json    # Thống kê tổng hợp
```

---

**BÂY GIỜ BDS500 EVALUATION SẼ HOẠT ĐỘNG! Hãy khởi động lại server và test! 🚀**

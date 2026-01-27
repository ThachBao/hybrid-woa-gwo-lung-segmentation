# Test History UI - Hướng Dẫn

## Vấn Đề
Tab "Lịch sử chạy" và "Đánh giá BDS500" hiển thị trống.

## Nguyên Nhân
1. Server chưa chạy hoặc cần khởi động lại
2. JavaScript chưa load history khi mở trang lần đầu (đã sửa)

## Giải Pháp

### Bước 1: Kiểm Tra Runs Có Sẵn
```bash
python test_runs_list_direct.py
```

**Kết quả mong đợi:**
```
✓ Found runs directory: outputs\runs
✓ 20260122_171948_ui_20aef927: uploaded, 7 algos
✓ 20260122_173631_ui_554eea69: uploaded, 7 algos
...
Total runs found: 6
```

### Bước 2: Khởi Động Server
```bash
python -m src.ui.app
```

**Lưu ý:** Nếu server đang chạy, hãy **DỪNG và KHỞI ĐỘNG LẠI** để load code mới!

### Bước 3: Mở Browser
```
http://localhost:5000
```

### Bước 4: Kiểm Tra Tab Lịch Sử
1. Click vào tab **"📜 Lịch sử chạy"**
2. Bạn sẽ thấy danh sách 6 runs
3. Click **"👁️ Xem"** để xem chi tiết
4. Click **"🗑️ Xóa"** để xóa run

### Bước 5: Kiểm Tra Tab BDS500 Eval
1. Click vào tab **"📊 Đánh giá BDS500"**
2. Bạn sẽ thấy form cấu hình
3. Chọn split, algorithms, parameters
4. Click **"🚀 Bắt đầu đánh giá"**

## Thay Đổi Đã Thực Hiện

### 1. JavaScript (`src/ui/static/app.js`)
- ✅ Thêm auto-load history khi trang mở:
```javascript
document.addEventListener('DOMContentLoaded', () => {
  loadHistory();
});
```

### 2. Backend API (`src/ui/app.py`)
- ✅ Cải thiện xử lý algorithms list
- ✅ API `/api/runs/list` hoạt động tốt

## Kiểm Tra API Trực Tiếp

### Test với Python (server phải chạy)
```bash
python test_history_api.py
```

### Test với cURL (server phải chạy)
```bash
curl http://localhost:5000/api/runs/list
```

## Debug

### Nếu vẫn trống:

1. **Mở Developer Console trong browser** (F12)
2. Xem tab **Console** có lỗi gì không
3. Xem tab **Network** khi click vào tab "Lịch sử chạy"
4. Kiểm tra xem request `/api/runs/list` có được gọi không

### Kiểm Tra Response
Trong Network tab, click vào request `/api/runs/list` và xem Response:
```json
{
  "runs": [
    {
      "run_name": "20260122_192409_ui_b25dd724",
      "image_name": "uploaded",
      "timestamp": "2026-01-22T19:24:09.348066",
      "total_time": 220.59,
      "best_algo": "HYBRID-PA5",
      "best_entropy": 0.0377,
      "algorithms": ["GWO", "WOA", "HYBRID-PA1", ...],
      "k": 10,
      "n_agents": 30,
      "n_iters": 80,
      "use_penalties": true
    },
    ...
  ],
  "total": 6
}
```

## Lỗi Thường Gặp

### 1. Server chưa chạy
```
ERROR: Server is not running!
Please start server with: python -m src.ui.app
```

**Giải pháp:** Khởi động server

### 2. Port đã được sử dụng
```
Address already in use
```

**Giải pháp:** 
- Tìm và kill process đang dùng port 5000
- Hoặc dùng port khác: `set FLASK_RUN_PORT=5001`

### 3. JavaScript error
Mở Console (F12) và xem lỗi. Thường là:
- `loadHistory is not defined` → Reload trang
- `fetch failed` → Server chưa chạy
- `Cannot read property` → Dữ liệu không đúng format

## Kết Quả Mong Đợi

### Tab Lịch Sử
```
┌─────────────────────────────────────────────────────────┐
│ 📜 Lịch sử chạy                    [🔄 Làm mới]         │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📷 uploaded                    [👁️ Xem] [🗑️ Xóa]   │ │
│ │ 🕐 22/01/2026 19:24:09                              │ │
│ │                                                      │ │
│ │ Thuật toán tốt nhất: HYBRID-PA5                     │ │
│ │ Entropy: 0.037673                                   │ │
│ │ Thời gian: 220.59s                                  │ │
│ │ Tham số: k=10, n=30, iter=80                        │ │
│ │                                                      │ │
│ │ [GWO] [WOA] [PA1] [PA2] [PA3] [PA4] [PA5] [🛡️ Pen] │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📷 uploaded                    [👁️ Xem] [🗑️ Xóa]   │ │
│ │ ...                                                  │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Tab BDS500 Eval
```
┌─────────────────────────────────────────────────────────┐
│ 📊 Đánh giá thuật toán trên BDS500 Dataset             │
│ Chạy đánh giá toàn bộ dataset với ground truth...      │
├─────────────────────────────────────────────────────────┤
│ 📁 Dataset Configuration                                │
│   Split: [Test ▼]    Limit: [10]                       │
│                                                          │
│ 🎯 Thuật toán                                           │
│   [✓] 🐺 GWO  [✓] 🐋 WOA  [✓] 🔀 PA1  [ ] 🔀 PA2      │
│   ...                                                    │
└─────────────────────────────────────────────────────────┘
```

## Tóm Tắt

1. ✅ Code đã sửa xong
2. ✅ API hoạt động tốt
3. ✅ Có 6 runs sẵn sàng hiển thị
4. ⚠️ **CẦN KHỞI ĐỘNG LẠI SERVER** để load code mới
5. ⚠️ **MỞ BROWSER VÀ KIỂM TRA**

**Nếu vẫn không hiển thị, hãy mở Developer Console (F12) và gửi screenshot lỗi!**

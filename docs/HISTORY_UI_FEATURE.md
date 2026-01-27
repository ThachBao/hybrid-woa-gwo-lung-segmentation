# Tính năng mới: UI Lịch sử chạy ✅

## Tổng quan

Thêm tab "Lịch sử chạy" vào Web UI để xem, quản lý và xem lại các lần chạy đã lưu.

## Tính năng

### 1. Tab Navigation
- ✅ 2 tabs: "Phân đoạn ảnh" và "Lịch sử chạy"
- ✅ Chuyển đổi dễ dàng giữa các tabs
- ✅ UI đẹp với hiệu ứng chuyển động

### 2. Danh sách lịch sử
- ✅ Hiển thị tất cả runs đã lưu
- ✅ Sắp xếp theo thời gian (mới nhất trước)
- ✅ Thông tin tóm tắt:
  - Tên ảnh
  - Thời gian chạy
  - Thuật toán tốt nhất
  - Entropy
  - Thời gian thực thi
  - Tham số (k, n_agents, n_iters)
  - Danh sách thuật toán
  - Có dùng penalties không

### 3. Xem chi tiết run
- ✅ Click "Xem" để mở modal chi tiết
- ✅ Hiển thị:
  - Tóm tắt (summary)
  - Cấu hình (config)
  - Ảnh gốc
  - Kết quả từng thuật toán:
    - Entropy, thời gian
    - Metrics (PSNR, SSIM, DICE)
    - Ngưỡng
    - Ảnh phân đoạn

### 4. Xóa run
- ✅ Click "Xóa" để xóa run
- ✅ Xác nhận trước khi xóa
- ✅ Tự động refresh danh sách

### 5. Làm mới
- ✅ Nút "Làm mới" để reload danh sách
- ✅ Tự động load khi mở tab

## API Endpoints mới

### 1. `GET /api/runs/list`
Lấy danh sách tất cả runs.

**Response**:
```json
{
  "runs": [
    {
      "run_name": "20260122_143052_ui_a3f7b2c1",
      "run_path": "outputs/runs/20260122_143052_ui_a3f7b2c1",
      "image_name": "uploaded",
      "timestamp": "2026-01-22T14:30:52.123456",
      "total_time": 45.67,
      "best_algo": "HYBRID-PA3",
      "best_entropy": 0.048234,
      "algorithms": ["GWO", "WOA", "HYBRID-PA3"],
      "k": 10,
      "n_agents": 30,
      "n_iters": 80,
      "use_penalties": true
    }
  ],
  "total": 1
}
```

### 2. `GET /api/runs/<run_name>`
Lấy chi tiết một run.

**Response**:
```json
{
  "run_name": "20260122_143052_ui_a3f7b2c1",
  "summary": {...},
  "config": {...},
  "gray_data_url": "data:image/png;base64,...",
  "algorithms": {
    "GWO": {
      "best": {
        "algorithm": "GWO",
        "thresholds": [12, 34, ...],
        "entropy": 0.047123,
        "time": 12.34,
        "metrics": {...}
      },
      "seg_data_url": "data:image/png;base64,...",
      "history": [...]
    }
  }
}
```

### 3. `DELETE /api/runs/<run_name>`
Xóa một run.

**Response**:
```json
{
  "success": true,
  "message": "Deleted 20260122_143052_ui_a3f7b2c1"
}
```

## Files đã sửa/thêm

### 1. `src/ui/app.py`
**Thêm**:
- Import `shutil`
- `@app.get("/api/runs/list")` - API lấy danh sách runs
- `@app.get("/api/runs/<run_name>")` - API lấy chi tiết run
- `@app.delete("/api/runs/<run_name>")` - API xóa run

### 2. `src/ui/templates/index.html`
**Thêm**:
- Tabs navigation (`<nav class="tabs-nav">`)
- Tab "Phân đoạn ảnh" (wrap existing content)
- Tab "Lịch sử chạy" với:
  - History header
  - History list
  - Run detail modal

### 3. `src/ui/static/index.css`
**Thêm CSS cho**:
- Tabs navigation (`.tabs-nav`, `.tab-btn`)
- Tab content (`.tab-content`)
- History container (`.history-container`)
- History items (`.history-item`)
- Modal (`.modal`, `.modal-content`)
- Run detail sections

### 4. `src/ui/static/app.js`
**Thêm JavaScript cho**:
- Tab switching
- `loadHistory()` - Load danh sách runs
- `viewRunDetail(runName)` - Xem chi tiết run
- `deleteRun(runName)` - Xóa run
- `formatTimestamp()` - Format thời gian
- Event handlers

## Cách sử dụng

### 1. Chạy Web UI
```bash
python -m src.ui.app
```

Mở http://127.0.0.1:5000

### 2. Xem lịch sử
- Click tab "📜 Lịch sử chạy"
- Danh sách runs sẽ tự động load
- Mỗi item hiển thị:
  - Tên ảnh
  - Thời gian
  - Thuật toán tốt nhất
  - Entropy
  - Thời gian chạy
  - Tham số
  - Danh sách thuật toán

### 3. Xem chi tiết
- Click nút "👁️ Xem" trên run muốn xem
- Modal sẽ hiển thị:
  - Tóm tắt
  - Cấu hình
  - Ảnh gốc
  - Kết quả từng thuật toán (entropy, metrics, ngưỡng, ảnh)
- Click "×" hoặc click ngoài modal để đóng

### 4. Xóa run
- Click nút "🗑️ Xóa" trên run muốn xóa
- Xác nhận trong dialog
- Run sẽ bị xóa và danh sách tự động refresh

### 5. Làm mới
- Click nút "🔄 Làm mới" để reload danh sách

## Screenshots (mô tả)

### Tab Navigation
```
┌─────────────────────────────────────────────────────┐
│  🖼️ Phân đoạn ảnh  │  📜 Lịch sử chạy              │
│  ─────────────────   ─────────────────              │
└─────────────────────────────────────────────────────┘
```

### History List
```
┌─────────────────────────────────────────────────────┐
│ 📜 Lịch sử chạy                    🔄 Làm mới       │
├─────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────┐ │
│ │ 📷 uploaded              👁️ Xem    🗑️ Xóa      │ │
│ │ 🕐 22/01/2026 14:30:52                          │ │
│ │                                                 │ │
│ │ Thuật toán: HYBRID-PA3  │ Entropy: 0.048234    │ │
│ │ Thời gian: 45.67s       │ k=10, n=30, iter=80  │ │
│ │                                                 │ │
│ │ [GWO] [WOA] [HYBRID-PA3] [🛡️ Penalties]        │ │
│ └─────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 📷 100007.jpg            👁️ Xem    🗑️ Xóa      │ │
│ │ ...                                             │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Run Detail Modal
```
┌─────────────────────────────────────────────────────┐
│ Chi tiết: 20260122_143052_ui_a3f7b2c1          ×   │
├─────────────────────────────────────────────────────┤
│ 📊 Tóm tắt                                          │
│ ┌──────────┬──────────┬──────────┬──────────┐      │
│ │ Ảnh      │ Thời gian│ Tổng TG  │ Algo     │      │
│ │ uploaded │ 14:30:52 │ 45.67s   │ HYBRID   │      │
│ └──────────┴──────────┴──────────┴──────────┘      │
│                                                     │
│ ⚙️ Cấu hình                                         │
│ ┌──────────┬──────────┬──────────┬──────────┐      │
│ │ k=10     │ n=30     │ iter=80  │ Penalties│      │
│ └──────────┴──────────┴──────────┴──────────┘      │
│                                                     │
│ 🖼️ Ảnh gốc                                         │
│ [Grayscale image]                                   │
│                                                     │
│ 🎯 Kết quả các thuật toán                          │
│ ┌─────────────────────────────────────────────┐    │
│ │ GWO                                         │    │
│ │ Entropy: 0.047123 │ Time: 12.34s           │    │
│ │ PSNR: 28.45       │ SSIM: 0.8234           │    │
│ │ Thresholds: [12, 34, 56, ...]              │    │
│ │ [Segmented image]                           │    │
│ └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

## Lợi ích

### 1. Quản lý dễ dàng
- Xem tất cả runs trong một nơi
- Không cần mở file explorer
- Tìm kiếm nhanh theo thời gian

### 2. So sánh trực quan
- Xem kết quả nhiều runs cùng lúc
- So sánh entropy, metrics
- Xem ảnh phân đoạn trực tiếp

### 3. Tiết kiệm thời gian
- Không cần chạy lại để xem kết quả
- Xem chi tiết ngay trong browser
- Xóa runs không cần thiết dễ dàng

### 4. Trải nghiệm tốt hơn
- UI đẹp, dễ sử dụng
- Responsive, mượt mà
- Thông tin đầy đủ

## Test

### Test API endpoints
```bash
# List runs
curl http://127.0.0.1:5000/api/runs/list

# Get run detail
curl http://127.0.0.1:5000/api/runs/20260122_143052_ui_a3f7b2c1

# Delete run
curl -X DELETE http://127.0.0.1:5000/api/runs/20260122_143052_ui_a3f7b2c1
```

### Test UI
1. Chạy app: `python -m src.ui.app`
2. Mở http://127.0.0.1:5000
3. Chạy phân đoạn ảnh (tạo run mới)
4. Click tab "Lịch sử chạy"
5. Verify danh sách hiển thị
6. Click "Xem" → Verify modal hiển thị đúng
7. Click "Xóa" → Verify run bị xóa

## Kết luận

✅ **Tính năng hoàn thành!**

- ✅ Tab navigation
- ✅ Danh sách lịch sử
- ✅ Xem chi tiết run
- ✅ Xóa run
- ✅ Làm mới danh sách
- ✅ UI đẹp, responsive
- ✅ API endpoints đầy đủ

**Giờ đây bạn có thể quản lý lịch sử chạy ngay trong Web UI!** 🎉

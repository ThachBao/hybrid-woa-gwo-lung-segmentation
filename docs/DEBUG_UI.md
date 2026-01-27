# Debug UI - Hướng Dẫn Chi Tiết

## Vấn Đề Hiện Tại
- Tab "Lịch sử chạy" và "Đánh giá BDS500" hiển thị trống
- Console có lỗi: `content/context.js:3 error: TypeError: Cannot read properties of null (reading 'data')`

## Phân Tích Lỗi

### 1. Lỗi `content/context.js`
- **Nguồn**: Đây là lỗi từ **browser extension**, KHÔNG phải từ code của chúng ta
- **Giải pháp**: Tắt các extensions hoặc bỏ qua lỗi này

### 2. UI Trống
- **Nguyên nhân**: JavaScript có thể chưa được load đúng cách
- **Đã sửa**: Thêm null checks cho tất cả event listeners

## Các Thay Đổi Đã Thực Hiện

### 1. Thêm Null Checks
```javascript
// Trước
formSeg.addEventListener("submit", ...);

// Sau
if (formSeg) {
  formSeg.addEventListener("submit", ...);
}
```

### 2. Auto-load History
```javascript
document.addEventListener('DOMContentLoaded', () => {
  if (historyList && typeof loadHistory === 'function') {
    loadHistory();
  }
});
```

## Hướng Dẫn Debug

### Bước 1: Kiểm Tra Server
```bash
# Dừng server cũ (Ctrl+C)
# Khởi động lại
python -m src.ui.app
```

### Bước 2: Test API Trực Tiếp
```bash
# Trong terminal khác
python test_runs_list_direct.py
```

**Kết quả mong đợi:**
```
✓ Found runs directory: outputs\runs
✓ 20260122_192409_ui_b25dd724: uploaded, 7 algos
...
Total runs found: 6
```

### Bước 3: Test API qua HTTP
Mở browser và truy cập:
```
http://localhost:5000/api/runs/list
```

**Kết quả mong đợi:** JSON với danh sách runs

### Bước 4: Test Simple HTML
Mở file `test_simple.html` trong browser (với server đang chạy)

**Kết quả mong đợi:** Hiển thị danh sách runs

### Bước 5: Kiểm Tra UI Chính
1. Mở `http://localhost:5000`
2. **XÓA CACHE**: Nhấn `Ctrl+Shift+R` (Windows) hoặc `Cmd+Shift+R` (Mac)
3. Mở Developer Tools (F12)
4. Tab **Console**: Xem có lỗi gì (bỏ qua lỗi từ extensions)
5. Tab **Network**: Click vào tab "Lịch sử chạy"
6. Tìm request `/api/runs/list` trong Network tab
7. Click vào request đó → Xem **Response**

## Debug Chi Tiết

### Kiểm Tra Elements Tồn Tại
Mở Console (F12) và chạy:
```javascript
console.log('historyList:', document.getElementById('historyList'));
console.log('formBDS500Eval:', document.getElementById('formBDS500Eval'));
console.log('loadHistory:', typeof loadHistory);
```

**Kết quả mong đợi:**
```
historyList: <div id="historyList">...</div>
formBDS500Eval: <form id="formBDS500Eval">...</form>
loadHistory: function
```

### Gọi loadHistory Thủ Công
Trong Console:
```javascript
loadHistory();
```

Xem có lỗi gì không.

### Kiểm Tra Network Request
1. Mở Network tab
2. Click vào tab "Lịch sử chạy"
3. Tìm request `/api/runs/list`
4. Kiểm tra:
   - **Status**: Phải là 200
   - **Response**: Phải có `{"runs": [...], "total": 6}`

## Các Lỗi Thường Gặp

### 1. Server Chưa Chạy
```
Failed to fetch
```
**Giải pháp:** Khởi động server

### 2. CORS Error
```
Access to fetch at 'http://localhost:5000/api/runs/list' from origin 'null' has been blocked by CORS policy
```
**Giải pháp:** Mở file HTML qua server, không phải file://

### 3. JavaScript Không Load
```
loadHistory is not defined
```
**Giải pháp:** 
- Xóa cache (Ctrl+Shift+R)
- Kiểm tra file app.js có được load không (Network tab)

### 4. Elements Null
```
Cannot read properties of null
```
**Giải pháp:** 
- Đã thêm null checks
- Khởi động lại server

## Tắt Browser Extensions

Nếu vẫn thấy lỗi `content/context.js`:

### Chrome/Edge
1. Menu → Extensions → Manage Extensions
2. Tắt tất cả extensions
3. Reload trang

### Firefox
1. Menu → Add-ons
2. Disable tất cả add-ons
3. Reload trang

## Test Cuối Cùng

### 1. Khởi động server
```bash
python -m src.ui.app
```

### 2. Mở browser (Incognito/Private mode)
```
http://localhost:5000
```

### 3. Kiểm tra từng tab
- ✅ Tab "Phân đoạn ảnh": Form hiển thị
- ✅ Tab "Đánh giá BDS500": Form hiển thị
- ✅ Tab "Lịch sử chạy": Danh sách 6-7 runs

## Nếu Vẫn Không Hoạt Động

Gửi cho tôi:
1. Screenshot của Console (F12 → Console tab)
2. Screenshot của Network tab khi click vào "Lịch sử chạy"
3. Kết quả của `python test_runs_list_direct.py`
4. Kết quả của `python check_status.py`

## Tóm Tắt

1. ✅ Code đã được sửa với null checks
2. ✅ Auto-load history đã được thêm
3. ⚠️ Lỗi `content/context.js` là từ browser extension (bỏ qua)
4. ⚠️ **CẦN**: Khởi động lại server
5. ⚠️ **CẦN**: Xóa cache browser (Ctrl+Shift+R)
6. ⚠️ **CẦN**: Tắt extensions nếu cần

**Hãy thử lại với các bước trên!**

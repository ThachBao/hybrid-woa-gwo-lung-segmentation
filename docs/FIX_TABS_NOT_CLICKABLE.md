# Fix: Tabs Không Click Được

## Vấn Đề
- Không thể click vào tab "📊 Đánh giá BDS500"
- Không thể click vào tab "📜 Lịch sử chạy"
- Chỉ tab "🖼️ Phân đoạn ảnh" hiển thị

## Nguyên Nhân Có Thể
1. JavaScript chưa được load
2. Event listeners chưa được add
3. CSS đang block clicks
4. Browser cache

## Giải Pháp

### Bước 1: Kiểm Tra Console
1. Mở Developer Tools (F12)
2. Tab **Console**
3. Reload trang (Ctrl+R)
4. Tìm các dòng log:
   ```
   Found tab buttons: 3
   Adding click listener to tab: segment
   Adding click listener to tab: bds500eval
   Adding click listener to tab: history
   ```

**Nếu KHÔNG thấy:** JavaScript chưa load → Xem Bước 2
**Nếu THẤY:** Event listeners đã add → Xem Bước 3

### Bước 2: Kiểm Tra JavaScript Load
Trong Console, chạy:
```javascript
console.log('app.js loaded:', typeof document.querySelectorAll);
```

**Nếu undefined:** JavaScript bị lỗi → Xem lỗi trong Console

### Bước 3: Test Click Thủ Công
Trong Console, chạy:
```javascript
const btn = document.querySelector('[data-tab="history"]');
console.log('History button:', btn);
btn.click();
```

**Nếu không hoạt động:** CSS có thể đang block → Xem Bước 4

### Bước 4: Kiểm Tra CSS
Trong Console, chạy:
```javascript
const btn = document.querySelector('[data-tab="history"]');
console.log('Button style:', window.getComputedStyle(btn));
console.log('Pointer events:', window.getComputedStyle(btn).pointerEvents);
```

**Nếu `pointerEvents: 'none'`:** CSS đang block clicks

### Bước 5: Xóa Cache và Reload
1. Mở Developer Tools (F12)
2. Click chuột phải vào nút Reload
3. Chọn **"Empty Cache and Hard Reload"**
4. Hoặc nhấn **Ctrl+Shift+R**

### Bước 6: Test File HTML Đơn Giản
Mở file `test_tabs.html` trong browser:
```
file:///path/to/test_tabs.html
```

**Nếu hoạt động:** Vấn đề ở main app → Xem Bước 7
**Nếu KHÔNG hoạt động:** Vấn đề ở browser → Thử browser khác

### Bước 7: Kiểm Tra HTML Structure
Trong Console, chạy:
```javascript
console.log('Tab buttons:', document.querySelectorAll('.tab-btn'));
console.log('Tab contents:', document.querySelectorAll('.tab-content'));
console.log('BDS500 tab:', document.getElementById('tabBDS500Eval'));
console.log('History tab:', document.getElementById('tabHistory'));
```

**Nếu null:** Elements không tồn tại → HTML có vấn đề

## Quick Fix

### Fix 1: Force Reload JavaScript
Thêm timestamp vào script tag trong `index.html`:
```html
<script src="{{ url_for('static', filename='app.js') }}?v={{ timestamp }}"></script>
```

### Fix 2: Inline Tab Switching
Thêm trực tiếp vào HTML:
```html
<button class="tab-btn active" data-tab="segment" onclick="switchTab('segment')">
```

Và thêm function:
```javascript
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('tab' + tabName.charAt(0).toUpperCase() + tabName.slice(1)).classList.add('active');
}
```

### Fix 3: Wrap trong DOMContentLoaded
Trong `app.js`, wrap tab switching code:
```javascript
document.addEventListener('DOMContentLoaded', () => {
    const tabButtons = document.querySelectorAll('.tab-btn');
    // ... rest of code
});
```

## Test Nhanh

### Test 1: Console Command
```javascript
// Test click programmatically
document.querySelector('[data-tab="history"]').click();
```

### Test 2: Add Inline Handler
Trong Console:
```javascript
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.onclick = () => {
        alert('Clicked: ' + btn.dataset.tab);
    };
});
```

Sau đó click vào tabs. Nếu alert hiện → Event listeners hoạt động.

## Checklist Debug

- [ ] Console có log "Found tab buttons: 3"?
- [ ] Console có lỗi JavaScript?
- [ ] Click vào tab có log "Tab clicked: ..."?
- [ ] `test_tabs.html` hoạt động?
- [ ] Đã xóa cache (Ctrl+Shift+R)?
- [ ] Đã khởi động lại server?
- [ ] Thử browser khác (Chrome/Firefox/Edge)?

## Nếu Vẫn Không Hoạt Động

### Giải pháp tạm thời: Dùng onclick inline
Sửa trong `index.html`:
```html
<button class="tab-btn active" data-tab="segment" onclick="window.switchToTab('segment')">
    🖼️ Phân đoạn ảnh
</button>
<button class="tab-btn" data-tab="bds500eval" onclick="window.switchToTab('bds500eval')">
    📊 Đánh giá BDS500
</button>
<button class="tab-btn" data-tab="history" onclick="window.switchToTab('history')">
    📜 Lịch sử chạy
</button>
```

Và thêm vào `app.js`:
```javascript
window.switchToTab = function(tabName) {
    console.log('Switching to tab:', tabName);
    
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    if (tabName === 'segment') {
        document.getElementById('tabSegment').classList.add('active');
    } else if (tabName === 'bds500eval') {
        document.getElementById('tabBDS500Eval').classList.add('active');
    } else if (tabName === 'history') {
        document.getElementById('tabHistory').classList.add('active');
        if (typeof loadHistory === 'function') {
            loadHistory();
        }
    }
};
```

## Tóm Tắt

1. ✅ Đã thêm debug logging
2. ✅ Đã tạo test file `test_tabs.html`
3. ⚠️ **CẦN**: Mở Console và xem logs
4. ⚠️ **CẦN**: Xóa cache (Ctrl+Shift+R)
5. ⚠️ **CẦN**: Khởi động lại server

**Hãy làm theo các bước trên và cho tôi biết kết quả trong Console!**

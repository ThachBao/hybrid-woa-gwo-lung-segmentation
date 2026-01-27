"""Quick status check"""
import os

print('=' * 60)
print('KIỂM TRA NHANH')
print('=' * 60)

runs_dir = 'outputs/runs'
print(f'✓ Thư mục runs: {os.path.exists(runs_dir)}')

if os.path.exists(runs_dir):
    runs = [d for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))]
    print(f'✓ Số runs: {len(runs)}')
    if runs:
        print(f'✓ Runs mới nhất: {sorted(runs)[-3:]}')

print('\n' + '=' * 60)
print('⚠️ QUAN TRỌNG - HƯỚNG DẪN SỬ DỤNG')
print('=' * 60)
print('1. DỪNG server nếu đang chạy (Ctrl+C)')
print('2. KHỞI ĐỘNG LẠI: python -m src.ui.app')
print('3. MỞ BROWSER: http://localhost:5000')
print('4. CLICK vào tab "📜 Lịch sử chạy"')
print(f'5. BẠN SẼ THẤY {len(runs)} RUNS!')
print('\nNếu vẫn trống:')
print('- Mở Developer Console (F12)')
print('- Xem tab Console có lỗi gì')
print('- Xem tab Network, tìm request /api/runs/list')
print('=' * 60)

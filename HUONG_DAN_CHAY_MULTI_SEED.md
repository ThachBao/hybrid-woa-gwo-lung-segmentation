# Hướng Dẫn Chạy Multi-Seed Comparison

## Tổng Quan

Các file đã được sửa để:
- ✅ Thêm tham số `share_interval` cho PA5 (mặc định = 4)
- ✅ Chỉ lưu các chỉ số FE quan trọng: **FE_best, Mean FE, Std FE, Worst FE**
- ✅ Không ảnh hưởng đến các file khác trong dự án

## Cách Chạy

### 1. Test Nhanh (5 ảnh)
```powershell
.\run_compare_quick_test.ps1
```
hoặc
```powershell
.\run_compare_quick_test.bat
```

### 2. Test Đầy Đủ (tất cả ảnh, 1 seed)
```powershell
.\run_compare_full.ps1
```

### 3. Multi-Seed (30 seeds) - Đánh Giá Độ Ổn Định
```powershell
.\run_compare_multi_seed.ps1
```
hoặc
```powershell
.\run_compare_multi_seed.bat
```

## Thay Đổi Share Interval cho PA5

Mở file `run_compare_multi_seed.bat` hoặc `run_compare_multi_seed.ps1` và sửa dòng:

```bat
--share_interval 4
```

Thành giá trị bạn muốn, ví dụ:
- `--share_interval 1` (chia sẻ mỗi iteration)
- `--share_interval 2` (chia sẻ mỗi 2 iterations)
- `--share_interval 5` (chia sẻ mỗi 5 iterations)
- `--share_interval 10` (chia sẻ mỗi 10 iterations)

## Kết Quả

Sau khi chạy xong, kết quả sẽ được lưu trong `outputs/compareGWO-WOA/`:

### 1. results_sorted.csv
Chứa kết quả từng ảnh, từng strategy, từng seed:
- `image_name`: Tên ảnh
- `strategy`: PA1, PA2, PA3, PA4, hoặc PA5
- `seed`: Seed đã dùng
- `share_interval`: Giá trị share_interval (chỉ cho PA5)
- `fe_best`: Giá trị FE tốt nhất

### 2. summary_sorted.csv
Tổng hợp theo strategy (đã sắp xếp theo Mean FE giảm dần):
- `strategy`: PA1, PA2, PA3, PA4, hoặc PA5
- `share_interval`: Giá trị share_interval (chỉ cho PA5)
- `n_records`: Số lượng runs
- `mean_fe`: **FE trung bình** (càng cao càng tốt)
- `std_fe`: **Độ lệch chuẩn FE** (càng thấp càng ổn định)
- `worst_fe`: **FE tệ nhất** (giá trị FE thấp nhất)
- `best_fe`: **FE tốt nhất** (giá trị FE cao nhất)

### 3. config.json
Cấu hình đã dùng để chạy

### 4. per_image/
Thư mục chứa kết quả chi tiết từng ảnh (JSON format)

## Đánh Giá Kết Quả

### Strategy Tốt Nhất
Xem dòng đầu tiên trong `summary_sorted.csv`:
- **Mean FE cao nhất** = Strategy tốt nhất về chất lượng
- **Std FE thấp nhất** = Strategy ổn định nhất

### So Sánh PA5 với Các Share Interval Khác Nhau
Nếu muốn test nhiều giá trị share_interval cho PA5, chạy nhiều lần với các giá trị khác nhau:

```powershell
# Test với share_interval = 1
# Sửa file .bat/.ps1 thành --share_interval 1
.\run_compare_multi_seed.ps1

# Test với share_interval = 4
# Sửa file .bat/.ps1 thành --share_interval 4
.\run_compare_multi_seed.ps1

# Test với share_interval = 10
# Sửa file .bat/.ps1 thành --share_interval 10
.\run_compare_multi_seed.ps1
```

Sau đó so sánh các file `summary_sorted.csv` để tìm giá trị tốt nhất.

## Lưu Ý

- Multi-seed với 30 seeds sẽ mất **RẤT NHIỀU THỜI GIAN** (có thể vài giờ đến vài ngày tùy số ảnh)
- Nên chạy test nhanh trước để đảm bảo mọi thứ hoạt động đúng
- Kết quả được sắp xếp theo Mean FE giảm dần (cao nhất ở trên)
- Các file khác trong dự án **KHÔNG BỊ ẢNH HƯỞNG**

## Ví Dụ Kết Quả

### summary_sorted.csv
```csv
strategy,share_interval,n_records,mean_fe,std_fe,worst_fe,best_fe
PA5,4,150,5.234567,0.012345,5.198765,5.267890
PA4,,150,5.223456,0.015678,5.187654,5.256789
PA3,,150,5.212345,0.018901,5.176543,5.245678
PA2,,150,5.201234,0.021234,5.165432,5.234567
PA1,,150,5.190123,0.024567,5.154321,5.223456
```

Trong ví dụ này:
- **PA5 với share_interval=4** là tốt nhất (Mean FE = 5.234567)
- **PA5** cũng ổn định nhất (Std FE = 0.012345)

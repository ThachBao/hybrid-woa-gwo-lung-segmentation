# 🫁 Phân Đoạn Vùng Phổi Từ Ảnh X-Quang Sử Dụng Thuật Toán Tối Ưu Hóa Lai WOA–GWO

## 📌 1. Giới Thiệu

Trong lĩnh vực y học hiện đại, ảnh X-quang ngực (Chest X-ray) đóng vai trò quan trọng trong việc phát hiện và chẩn đoán các bệnh lý về phổi như viêm phổi, lao phổi và các tổn thương hô hấp khác. Tuy nhiên, việc xác định chính xác vùng phổi trong ảnh X-quang thường gặp nhiều thách thức do nhiễu, độ tương phản thấp và sự chồng lấn giữa các cấu trúc giải phẫu.

Dự án này đề xuất một giải pháp phân đoạn vùng phổi dựa trên phương pháp phân đoạn đa ngưỡng, kết hợp với thuật toán tối ưu hóa lai giữa **Whale Optimization Algorithm (WOA)** và **Grey Wolf Optimization (GWO)**. Hàm mục tiêu sử dụng là **Fuzzy Entropy**, giúp cải thiện khả năng phân tách trong các ảnh có nhiễu và biên mờ.

Hệ thống được triển khai dưới dạng một **ứng dụng web tương tác**, cho phép người dùng tải lên ảnh, điều chỉnh tham số và trực quan hóa kết quả phân đoạn một cách dễ dàng.

---

## 🎯 2. Mục Tiêu Dự Án

- **Phân đoạn tự động vùng phổi** từ ảnh X-quang mà không sử dụng mô hình học sâu (phương pháp unsupervised).
- **Tối ưu hóa ngưỡng phân đoạn** bằng thuật toán lai WOA–GWO để đạt hiệu quả cao.
- **Đánh giá kết quả** bằng các chỉ số định lượng như Dice (DSC), IoU, SSIM và PSNR.
- **Xây dựng giao diện web** để trực quan hóa toàn bộ quy trình phân đoạn và so sánh kết quả.

---

## ⚙️ 3. Quy Trình Hệ Thống (Pipeline)

```
Ảnh X-Quang Đầu Vào (Input Image)
        ↓
Tiền Xử Lý (Preprocessing)
- Lọc nhiễu, chuẩn hóa độ sáng
        ↓
Tối Ưu Hóa Lai WOA–GWO
- Tìm ngưỡng phân đoạn tối ưu
- Sử dụng Fuzzy Entropy làm hàm mục tiêu
        ↓
Phân Đoạn Đa Ngưỡng (Multi-threshold Segmentation)
        ↓
Hậu Xử Lý (Post-processing)
- Lọc nhiễu, tinh chỉnh mask
        ↓
Kết Quả Xuất Ra (Output)
- Mask phân đoạn
- Overlay trên ảnh gốc
- Các chỉ số đánh giá
- Đồ thị hội tụ
```

---

## 🧠 4. Phương Pháp Đề Xuất

### 4.1 Whale Optimization Algorithm (WOA)
- **Mô phỏng hành vi săn mồi của cá voi**: Thuật toán này tập trung vào khả năng khám phá không gian tìm kiếm rộng lớn, giúp tránh bị mắc kẹt ở cực trị cục bộ.
- **Ứng dụng**: Phù hợp cho các bài toán cần khám phá toàn diện.

### 4.2 Grey Wolf Optimization (GWO)
- **Mô phỏng hành vi săn mồi của sói xám**: Thuật toán nhấn mạnh khả năng khai thác nghiệm tốt trong vùng lân cận, giúp hội tụ nhanh chóng.
- **Ứng dụng**: Hiệu quả trong việc tinh chỉnh nghiệm cuối cùng.

### 4.3 Thuật Toán Lai WOA–GWO (Hybrid)
- **Kết hợp ưu điểm**: Kết hợp khả năng khám phá của WOA và khả năng khai thác của GWO.
- **Cải thiện hiệu suất**: Tăng khả năng hội tụ toàn cục và tránh rơi vào cực trị cục bộ, đặc biệt hiệu quả cho bài toán phân đoạn ảnh y tế.

### 4.4 Hàm Mục Tiêu: Fuzzy Entropy
- **Nguyên lý**: Đo lường độ mờ và entropy trong ảnh, ưu tiên các ngưỡng phân tách rõ ràng giữa các vùng.
- **Ưu điểm**: Xử lý tốt các ảnh có nhiễu cao và biên không rõ ràng, phù hợp với ảnh X-quang y tế.

---

## 📊 5. Bộ Dữ Liệu (Dataset)

Dự án sử dụng bộ dữ liệu **Chest X-ray Masks and Labels** từ Kaggle, bao gồm:
- **Ảnh X-quang gốc**: Các ảnh ngực với độ phân giải cao.
- **Ground Truth Masks**: Các mask phân đoạn vùng phổi được gán nhãn thủ công bởi chuyên gia y tế.

**Mục đích sử dụng**:
- Huấn luyện và đánh giá mô hình phân đoạn.
- So sánh kết quả phân đoạn với ground truth để tính toán các chỉ số chất lượng.

**Lưu ý**: Bộ dữ liệu được chia thành tập train/val/test để đảm bảo đánh giá công bằng.

---

## 🌐 6. Tính Năng Chính Của Hệ Thống

### 6.1 Tải Lên Và Chọn Ảnh
- **Upload ảnh tùy chỉnh**: Hỗ trợ định dạng PNG/JPG.
- **Chọn từ dataset có sẵn**: Lựa chọn nhanh từ bộ dữ liệu Chest X-ray.

### 6.2 Điều Chỉnh Tham Số
- **Số ngưỡng (k)**: Mặc định 10 ngưỡng cho phân đoạn chi tiết.
- **Seed ngẫu nhiên**: Để tái tạo kết quả.
- **Số agents (n_agents)**: Số cá thể trong quần thể (mặc định 30).
- **Số vòng lặp (n_iters)**: Số thế hệ tối ưu hóa (mặc định 80).

### 6.3 Hiển Thị Kết Quả
- **Ảnh gốc**: Hiển thị ảnh X-quang đầu vào.
- **Ảnh sau tiền xử lý**: Kết quả lọc nhiễu và chuẩn hóa.
- **Mask phân đoạn**: Vùng phổi được tách ra.
- **Overlay**: Chồng mask lên ảnh gốc để so sánh trực quan.
- **Ground Truth**: So sánh với mask chuẩn để đánh giá.

### 6.4 Phân Tích Và Đánh Giá
- **Đồ thị hội tụ**: Theo dõi quá trình tối ưu hóa entropy qua các thế hệ.
- **Các chỉ số định lượng**:
  - **Dice (DSC)**: Độ tương đồng với ground truth.
  - **IoU (Intersection over Union)**: Độ phủ của vùng phân đoạn.
  - **SSIM**: Độ tương tự cấu trúc.
  - **PSNR**: Chất lượng ảnh sau phân đoạn.

---

## 🖥️ 7. Yêu Cầu Hệ Thống

- **Hệ điều hành**: Windows/Linux/macOS
- **Python**: Phiên bản 3.8 trở lên
- **CPU**: Tối thiểu 2 lõi (khuyến nghị 4 lõi trở lên cho tốc độ nhanh)
- **RAM**: Tối thiểu 4GB (khuyến nghị 8GB)
- **Không gian lưu trữ**: Tối thiểu 1GB cho dataset và kết quả

### 7.1 Cài Đặt

1. **Clone repository**:
   ```bash
   git clone <repository-url>
   cd <project-folder>
   ```

2. **Cài đặt dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### 7.2 Chạy Ứng Dụng

```bash
python -m src.ui.app
```

Sau đó mở trình duyệt và truy cập: **http://127.0.0.1:5000**

### 7.3 Sử Dụng Giao Diện Web

1. **Chọn tab "Upload Image"** hoặc **"Chest X-ray Dataset"**.
2. **Tải lên ảnh** hoặc chọn từ danh sách.
3. **Cấu hình tham số**: Chọn thuật toán (WOA, GWO, Hybrid), điều chỉnh k, n_agents, n_iters.
4. **Nhấn "Segment"** để chạy phân đoạn.
5. **Xem kết quả**: Mask, overlay, metrics và convergence curve.

---

##  8. Cài đặt

### 8.1 Clone project

```bash
git clone https://github.com/ThachBao/Hybrid-woa-gwo-lung-segmentation.git
cd your-repo
```

### 8.2 Cài đặt thư viện

```bash
pip install -r requirements.txt
```

## ▶️ 9. Chạy ứng dụng

```bash
python -m src.ui.app  
```

Truy cập trình duyệt: http://127.0.0.1:5000

## 🧪 10. Hướng dẫn sử dụng

**Chọn nguồn ảnh:**
- Upload file
- Hoặc chọn dataset có sẵn

**Cấu hình tham số:**
- k: số ngưỡng
- seed: giá trị khởi tạo
- n_agents: số agent
- n_iters: số vòng lặp

**Nhấn "Chạy phân đoạn phổi"**

**Quan sát kết quả:**
- Mask
- Overlay
- Ground Truth
- Metrics
- Convergence curve

## 📈 11. Đánh giá

Các chỉ số sử dụng:
- **Dice (DSC)**: đo độ trùng lặp
- **IoU**: đo mức độ giao nhau
- **SSIM**: đo độ tương đồng cấu trúc
- **PSNR**: đo chất lượng ảnh

## 🚀 12. Ưu điểm

- Không cần dữ liệu huấn luyện
- Không phụ thuộc GPU
- Dễ triển khai
- Có khả năng giải thích (Explainable AI)
- Có giao diện web trực quan

## ⚠️ 13. Hạn chế

- Độ chính xác thấp hơn Deep Learning trong một số trường hợp phức tạp
- Phụ thuộc vào chất lượng ảnh đầu vào
- Khó xử lý các trường hợp bệnh nặng hoặc bất thường lớn

## 🔮 14. Hướng phát triển

- Kết hợp với Deep Learning (Hybrid AI)
- Tối ưu tốc độ hội tụ
- Mở rộng sang CT, MRI
- Triển khai thành hệ thống hỗ trợ chẩn đoán

## 👨‍💻 15. Tác giả

Nhóm sinh viên
Trường Đại học Công Thương TP.HCM (HUIT)

---

## 📚 16. Tài Liệu Tham Khảo

- [Grey Wolf Optimizer (GWO)](https://www.sciencedirect.com/science/article/pii/S0965997813001853)
- [Whale Optimization Algorithm (WOA)](https://www.sciencedirect.com/science/article/pii/S0965997816300163)
- [Chest X-ray Dataset on Kaggle](https://www.kaggle.com/datasets/nikhilpandey360/chest-xray-masks-and-labels)

---

## 🤝 17. Đóng Góp

Dự án này là một phần của nghiên cứu về ứng dụng trí tuệ nhân tạo trong y học. Mọi đóng góp, phản hồi hoặc cải tiến đều được chào đón!

**Liên hệ**: [thachbao2910@gmail.com]

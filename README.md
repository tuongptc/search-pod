# LogoVectorize

Công cụ tự động kết nối Google Drive, lấy các file logo PNG, vector hóa và cho phép tìm kiếm bằng hình ảnh nhanh chóng. Lý tưởng cho designer, team marketing cần quản lý và sử dụng thư viện logo hiệu quả.

## Tính năng

- **Đồng bộ với Google Drive**: Tự động truy xuất tất cả file logo PNG từ thư mục được chỉ định
- **Vector hóa tự động**: Chuyển đổi logo PNG thành định dạng vector
- **Tìm kiếm bằng hình ảnh**: Cho phép người dùng tìm kiếm logo tương tự bằng cách tải lên hình ảnh
- **Hiệu suất cao**: Giải pháp tìm kiếm nhanh chóng với kỹ thuật vector embedding

## Hướng dẫn cài đặt và sử dụng

### Yêu cầu
- Python 3.8 trở lên
- Tài khoản Google Cloud với API Drive được kích hoạt

### Cài đặt

1. Clone repository này:
```bash
git clone https://github.com/your-username/LogoVectorize.git
cd LogoVectorize
```

2. Cài đặt các gói phụ thuộc:
```bash
pip install -r requirements.txt
```

3. Thiết lập Service Account:
   - Tạo Service Account trên [Google Cloud Console](https://console.cloud.google.com/)
   - Tạo và tải xuống file `service-account-key.json`
   - Đặt file `service-account-key.json` vào thư mục gốc của dự án
   - Chia sẻ thư mục Google Drive chứa logo với địa chỉ email của Service Account và cấp quyền "Viewer"

### Cách sử dụng

1. Chạy ứng dụng:
```bash
python3 app.py
```

2. Truy cập vào web UI qua địa chỉ:
```
http://localhost:3000
```

### Chạy ứng dụng ở chế độ nền (daemon)

Để chạy ứng dụng ở chế độ nền, bạn có thể sử dụng các phương pháp sau:

#### Sử dụng nohup (Linux/Mac):
```bash
nohup python3 app.py > output.log 2>&1 &
```

#### Sử dụng screen (Linux/Mac):
```bash
# Cài đặt screen nếu chưa có
# Ubuntu/Debian: sudo apt-get install screen
# CentOS/RHEL: sudo yum install screen
# macOS: brew install screen

# Tạo session mới
screen -S logovectorize

# Chạy ứng dụng
python3 app.py

# Thoát screen (giữ ứng dụng chạy): Nhấn Ctrl+A, sau đó nhấn D
# Để quay lại session: screen -r logovectorize
```

#### Sử dụng PM2 (Nếu có Node.js):
```bash
# Cài đặt PM2
npm install -g pm2

# Chạy ứng dụng với PM2
pm2 start app.py --name "logovectorize" --interpreter python3

# Kiểm tra trạng thái
pm2 status

# Dừng ứng dụng
pm2 stop logovectorize
```

#### Trên Windows:
Tạo file batch script (run_app.bat):
```batch
@echo off
start /min python app.py
```

## Xử lý sự cố

Nếu bạn gặp vấn đề với việc kết nối Google Drive, hãy kiểm tra:
- File `service-account-key.json` đã đúng và có trong thư mục gốc
- Service Account đã được cấp quyền truy cập thư mục Google Drive
- API Drive đã được kích hoạt trên Google Cloud Console

## Đóng góp

Mọi đóng góp đều được hoan nghênh! Vui lòng tạo issue hoặc pull request để cải thiện dự án.

## Giấy phép

[MIT License](LICENSE)

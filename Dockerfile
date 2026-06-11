FROM python:3.12-slim

# Thiết lập thư mục làm việc
WORKDIR /code

# Cấu hình biến môi trường để matplotlib/seaborn không bị lỗi phân quyền ghi cache
ENV MPLCONFIGDIR=/tmp/matplotlib_cache
ENV PYTHONUNBUFFERED=1

# Cài đặt các thư viện hệ thống cần thiết (nếu có)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Sao chép requirements.txt và cài đặt các thư viện Python
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Phân quyền cho thư mục /code để tránh lỗi quyền ghi (nếu có ghi dữ liệu tạm)
RUN chmod -R 777 /code

# Expose cổng 7860 (đây là cổng mặc định mà Hugging Face Spaces yêu cầu)
EXPOSE 7860

# Khởi chạy ứng dụng FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]

FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# Cài đặt Python 3.10 và các dependencies hệ thống
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3-setuptools \
    ffmpeg \
    exiftool \
    libreoffice \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Link python3.10 sang python
RUN ln -s /usr/bin/python3.10 /usr/bin/python

WORKDIR /app

# Copy thư mục markitdown package để cài đặt
COPY packages/ /app/packages/

# Cài đặt thư viện markitdown core
RUN python -m pip --no-cache-dir install /app/packages/markitdown[all]

# Copy thư mục server
COPY server/ /app/server/

# Cài đặt dependencies cho server (bao gồm onnxruntime-gpu, Flask, OCR...)
# Gỡ onnxruntime bản CPU (nếu có bị cài theo) để ưu tiên GPU
RUN python -m pip uninstall -y onnxruntime || true && \
    python -m pip --no-cache-dir install -r /app/server/requirements.txt

# Mở port 5000
EXPOSE 5000

# Khởi chạy server
WORKDIR /app/server
CMD ["python", "app.py"]

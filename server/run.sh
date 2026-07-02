#!/bin/bash
# ─────────────────────────────────────────────
# Khởi động: Hệ Thống Chuyển Đổi Văn Bản
# Bộ Ngoại Giao Việt Nam
# ─────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/../venv"

echo ""
echo "🇻🇳  Hệ Thống Chuyển Đổi Văn Bản — Bộ Ngoại Giao"
echo "─────────────────────────────────────────────────"

# Kích hoạt virtual environment
if [ -d "$VENV_DIR" ]; then
    echo "✔  Kích hoạt virtual environment..."
    source "$VENV_DIR/bin/activate"
else
    echo "⚠  Không tìm thấy venv, dùng Python hệ thống."
fi

# Cài dependencies
echo "✔  Kiểm tra dependencies..."
pip install -q flask flask-cors

# Chạy server
echo "$SCRIPT_DIR  Khởi động server tại http://localhost:5000"

cd "$SCRIPT_DIR"
python app.py

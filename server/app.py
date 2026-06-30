"""
Flask API Server — Hệ Thống Chuyển Đổi Văn Bản
Bộ Ngoại Giao Nước Cộng Hòa Xã Hội Chủ Nghĩa Việt Nam
"""
import os
import sys
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from markitdown import MarkItDown
from werkzeug.utils import secure_filename

# Thêm thư mục server/ vào path để import ocr_converter
sys.path.insert(0, os.path.dirname(__file__))
from ocr_converter import TesseractPdfConverter, _dep_error as _ocr_dep_error

MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB

ALLOWED_EXTENSIONS = {
    "pdf","docx","doc","xlsx","xls","pptx","ppt",
    "txt","md","csv","rtf","html","htm","xml","json",
    "jpg","jpeg","png","gif","bmp","webp","tiff",
    "mp3","wav","m4a","ogg","epub","ipynb","zip","msg",
}

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
CORS(app)

md_converter = MarkItDown(enable_plugins=False)

# Đăng ký Tesseract OCR converter ở priority -1.0
# (ưu tiên cao hơn built-in PdfConverter ở priority 0.0)
# Nếu Tesseract chưa cài, converter tự động bị bỏ qua (accepts() trả False)
_ocr_converter = TesseractPdfConverter()
md_converter.register_converter(_ocr_converter, priority=-1.0)

if _ocr_dep_error:
    print(f"⚠️  Tesseract OCR chưa sẵn sàng: {_ocr_dep_error}")
    print("   Chạy: sudo apt install tesseract-ocr tesseract-ocr-vie && pip install pymupdf pytesseract Pillow")
else:
    print("✔  Tesseract OCR đã sẵn sàng (hỗ trợ PDF ảnh scan, tiếng Việt)")


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "MarkItDown — Bộ Ngoại Giao",
        "ocr": "tesseract" if not _ocr_dep_error else "unavailable",
    })


@app.route("/api/convert", methods=["POST"])
def convert():
    if "file" not in request.files:
        return jsonify({"error": "Không tìm thấy file trong yêu cầu."}), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({"error": "Vui lòng chọn một file."}), 400

    if not allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[-1].upper() if "." in file.filename else "không rõ"
        return jsonify({"error": f"Định dạng .{ext} chưa được hỗ trợ."}), 415

    filename = secure_filename(file.filename)
    suffix = Path(filename).suffix
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            file.save(tmp_path)

        result = md_converter.convert(tmp_path)

        return jsonify({
            "markdown": result.markdown,
            "title": result.title or Path(filename).stem,
            "filename": filename,
            "size": os.path.getsize(tmp_path),
        })

    except Exception as e:
        app.logger.error(f"Lỗi chuyển đổi '{filename}': {e}", exc_info=True)
        return jsonify({"error": f"Không thể chuyển đổi file này: {str(e)}"}), 500

    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"\n🇻🇳  Hệ Thống Chuyển Đổi Văn Bản — Bộ Ngoại Giao")
    print(f"   Đang chạy tại: http://localhost:{port}\n")
    app.run(host=host, port=port, debug=False)

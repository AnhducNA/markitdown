"""
Flask API Server — Hệ Thống Chuyển Đổi Văn Bản
Bộ Ngoại Giao Nước Cộng Hòa Xã Hội Chủ Nghĩa Việt Nam
"""
import os
import re
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from markitdown import MarkItDown
from werkzeug.utils import secure_filename

# Thêm thư mục server/ vào path để import ocr_converter
sys.path.insert(0, os.path.dirname(__file__))
from ocr_converter import (
    RapidPdfConverter, 
    MarkerPdfConverter,
    _dep_error as _ocr_dep_error,
    _marker_dep_error
)
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

md_converter_rapid = MarkItDown(enable_plugins=False)
md_converter_rapid.register_converter(RapidPdfConverter(), priority=-1.0)

md_converter_marker = MarkItDown(enable_plugins=False)
md_converter_marker.register_converter(MarkerPdfConverter(), priority=-1.0)

if _ocr_dep_error:
    print(f"⚠️  Rapid OCR chưa sẵn sàng: {_ocr_dep_error}")
else:
    print("✔  Rapid OCR đã sẵn sàng (hỗ trợ PDF ảnh scan, tiếng Việt)")

if _marker_dep_error:
    print(f"⚠️  Marker OCR (GPU) chưa sẵn sàng: {_marker_dep_error}")
else:
    print("✔  Marker OCR đã sẵn sàng (tối ưu hóa bởi GPU)")

def _convert_legacy_office(path: str) -> tuple[str, str | None]:
    """Convert legacy Office files (.doc, .ppt) to OpenXML so MarkItDown can process them."""
    ext = Path(path).suffix.lower()
    mapping = {".doc": ".docx", ".ppt": ".pptx"}
    if ext not in mapping:
        return path, None

    libreoffice = shutil.which("soffice") or shutil.which("libreoffice")
    if libreoffice is None:
        raise RuntimeError(
            "Chuyển đổi .doc/.ppt cần LibreOffice/soffice được cài đặt trên hệ thống."
        )

    outdir = tempfile.mkdtemp(prefix="markitdown-office-")
    result = subprocess.run(
        [
            libreoffice,
            "--headless",
            "--convert-to",
            mapping[ext],
            "--outdir",
            outdir,
            path,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        shutil.rmtree(outdir, ignore_errors=True)
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"LibreOffice chuyển đổi thất bại: {stderr or 'Không có thông tin lỗi.'}"
        )

    converted = Path(outdir) / (Path(path).stem + mapping[ext])
    if not converted.exists():
        shutil.rmtree(outdir, ignore_errors=True)
        raise RuntimeError(
            "LibreOffice đã chạy nhưng không tạo được file chuyển đổi."
        )

    return str(converted), outdir


def _yaml_quote(value: str) -> str:
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _build_metadata_header(form: dict) -> str:
    department = (form.get('department') or '').strip()
    category = (form.get('category') or '').strip()
    author = (form.get('author') or '').strip()
    created_at = (form.get('created_at') or '').strip()
    description = (form.get('description') or '').strip()
    tags = (form.get('tags') or '').strip()

    lines = []
    if department:
        lines.append(f'department: {_yaml_quote(department)}')
    if category:
        lines.append(f'category: {_yaml_quote(category)}')
    if author:
        lines.append(f'author: {_yaml_quote(author)}')
    if created_at:
        lines.append(f'created_at: {_yaml_quote(created_at)}')
    if description:
        lines.append('description: |')
        for line in description.splitlines() or ['']:
            lines.append(f'  {line.rstrip()}')
    if tags:
        tag_items = [tag.strip() for tag in tags.split(',') if tag.strip()]
        if tag_items:
            lines.append('tags:')
            for tag in tag_items:
                lines.append(f'  - {_yaml_quote(tag)}')

    if not lines:
        return ''

    return '---\n' + '\n'.join(lines) + '\n---\n\n'


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
        "ocr_rapid": "available" if not _ocr_dep_error else "unavailable",
        "ocr_marker": "available" if not _marker_dep_error else "unavailable",
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

    converted_path = None
    converted_dir = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            file.save(tmp_path)

        if Path(tmp_path).suffix.lower() in {".doc", ".ppt"}:
            converted_path, converted_dir = _convert_legacy_office(tmp_path)
            source_path = converted_path
        else:
            source_path = tmp_path

        ocr_engine = request.form.get("ocr_engine", "rapid")
        if ocr_engine == "marker":
            converter_instance = md_converter_marker
        else:
            converter_instance = md_converter_rapid

        result = converter_instance.convert(source_path)
        header = _build_metadata_header(request.form)
        markdown = header + result.markdown if header else result.markdown

        return jsonify({
            "markdown": markdown,
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
        if converted_path:
            try:
                os.unlink(converted_path)
            except Exception:
                pass
        if converted_dir:
            try:
                shutil.rmtree(converted_dir, ignore_errors=True)
            except Exception:
                pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"\n🇻🇳  Hệ Thống Chuyển Đổi Văn Bản — Bộ Ngoại Giao")
    print(f"   Đang chạy tại: http://localhost:{port}\n")
    app.run(host=host, port=port, debug=False)

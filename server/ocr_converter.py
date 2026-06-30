"""
Tesseract OCR Converter cho PDF ảnh scan.
Tích hợp vào MarkItDown như một DocumentConverter tuỳ chỉnh.
Hoạt động hoàn toàn offline — không cần internet hay API key.
"""
import io
import sys
from typing import BinaryIO, Any

from markitdown import DocumentConverter, DocumentConverterResult, StreamInfo

# ── Load dependencies ──────────────────────────────────────────
_fitz = None
_pytesseract = None
_Image = None
_dep_error = None

try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image

    _fitz = fitz
    _pytesseract = pytesseract
    _Image = Image
except ImportError as e:
    _dep_error = str(e)

# ── Cấu hình ngôn ngữ OCR ─────────────────────────────────────
# "vie+eng" = tiếng Việt ưu tiên, fallback tiếng Anh
OCR_LANG = "vie+eng"

# Ngưỡng: trang có ít hơn X ký tự text → coi là ảnh scan
TEXT_THRESHOLD = 30

# DPI render PDF → ảnh trước khi OCR (300 = chất lượng tốt)
RENDER_DPI = 300

ACCEPTED_EXTENSIONS = [".pdf"]
ACCEPTED_MIMETYPES  = ["application/pdf", "application/x-pdf"]


class TesseractPdfConverter(DocumentConverter):
    """
    Converter PDF dùng Tesseract OCR.
    - Trang nào có text layer đủ → dùng text layer (nhanh).
    - Trang nào là ảnh scan (text rỗng / quá ít) → render ảnh → OCR.
    Hoàn toàn offline, hỗ trợ tiếng Việt.
    """

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        if _dep_error:
            return False  # Không có deps → không nhận

        ext      = (stream_info.extension or "").lower()
        mimetype = (stream_info.mimetype  or "").lower()

        if ext in ACCEPTED_EXTENSIONS:
            return True
        for m in ACCEPTED_MIMETYPES:
            if mimetype.startswith(m):
                return True
        return False

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        if _dep_error:
            raise ImportError(
                f"TesseractPdfConverter cần PyMuPDF và pytesseract: {_dep_error}"
            )

        pdf_bytes = file_stream.read()
        doc = _fitz.open(stream=pdf_bytes, filetype="pdf")

        page_texts = []
        ocr_pages  = 0

        for page_num, page in enumerate(doc, start=1):
            # Thử lấy text layer trước
            text = page.get_text("text").strip()

            if len(text) >= TEXT_THRESHOLD:
                # Trang có text → dùng trực tiếp
                page_texts.append(text)
            else:
                # Trang là ảnh scan → render → OCR
                ocr_pages += 1
                mat = _fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
                pix = page.get_pixmap(matrix=mat, colorspace=_fitz.csRGB)
                img_bytes = pix.tobytes("png")
                img = _Image.open(io.BytesIO(img_bytes))

                ocr_text = _pytesseract.image_to_string(
                    img,
                    lang=OCR_LANG,
                    config="--psm 3",  # auto page segmentation
                ).strip()

                if ocr_text:
                    page_texts.append(f"<!-- Trang {page_num} — OCR -->\n{ocr_text}")

        doc.close()

        markdown = "\n\n---\n\n".join(page_texts).strip()

        # Thêm ghi chú nếu có trang OCR
        if ocr_pages > 0:
            note = f"\n\n> ℹ️ {ocr_pages} trang được nhận dạng bằng Tesseract OCR (tiếng Việt)."
            markdown += note

        if not markdown:
            markdown = "_Không trích xuất được nội dung từ file PDF này._"

        return DocumentConverterResult(markdown=markdown)

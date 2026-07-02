"""
PaddleOCR Converter cho PDF ảnh scan.
Tích hợp vào MarkItDown như một DocumentConverter tuỳ chỉnh.
Hoạt động hoàn toàn offline — không cần internet hay API key.
"""
import io
import sys
import os
from typing import BinaryIO, Any

# Disable oneDNN (MKLDNN) to avoid ConvertPirAttribute2RuntimeAttribute errors on CPU with PaddlePaddle 3.x
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

from markitdown import DocumentConverter, DocumentConverterResult, StreamInfo

# ── Load dependencies ──────────────────────────────────────────
_fitz = None
_paddleocr = None
_dep_error = None

try:
    import fitz  # PyMuPDF
    import numpy as np
    from paddleocr import PaddleOCR

    _fitz = fitz
    # Khởi tạo PaddleOCR (lang='vi' cho tiếng Việt, use_angle_cls=True cho chữ nghiêng)
    _paddleocr = PaddleOCR(use_angle_cls=True, lang='vi')
except ImportError as e:
    _dep_error = str(e)
except Exception as e:
    _dep_error = str(e)

# ── Cấu hình ─────────────────────────────────────
# Ngưỡng: trang có ít hơn X ký tự text → coi là ảnh scan
TEXT_THRESHOLD = 30

# DPI render PDF → ảnh trước khi OCR (300 = chất lượng tốt)
RENDER_DPI = 300

ACCEPTED_EXTENSIONS = [".pdf"]
ACCEPTED_MIMETYPES  = ["application/pdf", "application/x-pdf"]


class PaddlePdfConverter(DocumentConverter):
    """
    Converter PDF dùng Paddle OCR.
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
                f"PaddlePdfConverter cần PyMuPDF, numpy và paddleocr: {_dep_error}"
            )

        pdf_bytes = file_stream.read()
        doc = _fitz.open(stream=pdf_bytes, filetype="pdf")

        page_texts = []
        ocr_pages  = 0

        for page_num, page in enumerate(doc, start=1):
            # Thử lấy text layer trước
            text = page.get_text("text").strip()
            has_images = len(page.get_images()) > 0

            # Heuristic: Nếu trang có cực ít text (< TEXT_THRESHOLD)
            # HOẶC trang có ít text (< 200 ký tự) và có chứa ảnh (rất có thể là văn bản scan có chèn thêm header/watermark text)
            # -> Tiến hành chạy OCR.
            if len(text) < TEXT_THRESHOLD or (len(text) < 200 and has_images):
                # Trang là ảnh scan → render → OCR
                ocr_pages += 1
                mat = _fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
                pix = page.get_pixmap(matrix=mat, colorspace=_fitz.csRGB)
                
                # Convert fitz pixmap to numpy array for PaddleOCR
                import numpy as np
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                
                # If image has an alpha channel (RGBA), convert to RGB
                if pix.n == 4:
                    import cv2
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)

                # Run PaddleOCR
                result = _paddleocr.ocr(img_array)
                
                # Extract text from PaddleOCR output structure
                ocr_lines = []
                # result can be [None] or a list of lines
                if result and result[0]:
                    for line in result[0]:
                        # line[1][0] is the text string, line[1][1] is confidence
                        ocr_lines.append(line[1][0])
                
                ocr_text = "\n".join(ocr_lines).strip()

                if ocr_text:
                    page_texts.append(f"<!-- Trang {page_num} — OCR -->\n{ocr_text}")
            else:
                # Trang có đủ text layer → dùng trực tiếp
                page_texts.append(text)

        doc.close()

        markdown = "\n\n---\n\n".join(page_texts).strip()

        # Thêm ghi chú nếu có trang OCR
        if ocr_pages > 0:
            note = f"\n\n> ℹ️ {ocr_pages} trang được nhận dạng bằng Paddle OCR (tiếng Việt)."
            markdown += note

        if not markdown:
            markdown = "_Không trích xuất được nội dung từ file PDF này._"

        return DocumentConverterResult(markdown=markdown)

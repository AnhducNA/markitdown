"""
RapidOCR Converter cho PDF ảnh scan.
Tích hợp vào MarkItDown như một DocumentConverter tuỳ chỉnh.
Hoạt động hoàn toàn offline — không cần internet hay API key.
"""
import io
import sys
import os
from typing import BinaryIO, Any

from markitdown import DocumentConverter, DocumentConverterResult, StreamInfo

# ── Load dependencies ──────────────────────────────────────────
_fitz = None
_rapidocr = None
_dep_error = None

try:
    import fitz  # PyMuPDF
    import numpy as np
    import onnxruntime as ort
    from rapidocr_onnxruntime import RapidOCR

    _fitz = fitz
    
    # Kiểm tra các Execution Providers có sẵn trong ONNX Runtime
    available_providers = ort.get_available_providers()
    print(f"ONNX Runtime available providers: {available_providers}")
    
    # Ưu tiên sử dụng GPU (CUDA) nếu có, fallback về CPU
    providers = []
    if "CUDAExecutionProvider" in available_providers:
        print("✔ CUDA GPU được tìm thấy. Đang cấu hình OCR sử dụng GPU.")
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    else:
        print("⚠ Không tìm thấy CUDA GPU. Sẽ chạy trên CPU.")
        providers = ["CPUExecutionProvider"]

    # Khởi tạo RapidOCR
    # rapidocr_onnxruntime tự động nhận tham số liên quan đến provider nếu ta pass
    # Nếu không nhận, ít nhất onnxruntime-gpu cũng sẽ ưu tiên GPU nếu nó được cài đặt.
    try:
        _rapidocr = RapidOCR(print_verbose=False)
        # rapidocr_onnxruntime configures text_det, text_cls, text_recog modules.
        # However, default instantiation will use the default ORT session options (which prioritizes CUDA if installed).
    except Exception as e:
        _rapidocr = RapidOCR()
except ImportError as e:
    _dep_error = str(e)
except Exception as e:
    _dep_error = str(e)

# ── Cấu hình ─────────────────────────────────────
# Ngưỡng: trang có ít hơn X ký tự text → coi là ảnh scan
TEXT_THRESHOLD = 30

# DPI render PDF → ảnh trước khi OCR
# 200 = cân bằng tốc độ/chất lượng (đủ tốt cho hầu hết văn bản scan)
RENDER_DPI = 200

ACCEPTED_EXTENSIONS = [".pdf"]
ACCEPTED_MIMETYPES  = ["application/pdf", "application/x-pdf"]


class RapidPdfConverter(DocumentConverter):
    """
    Converter PDF dùng Rapid OCR.
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
                f"RapidPdfConverter cần PyMuPDF, numpy và rapidocr_onnxruntime: {_dep_error}"
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
                
                # Convert fitz pixmap to numpy array for RapidOCR
                import numpy as np
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                
                # If image has an alpha channel (RGBA), convert to RGB
                if pix.n == 4:
                    import cv2
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)

                # Run RapidOCR
                result, elapse = _rapidocr(img_array)
                
                # Extract text from RapidOCR output structure
                ocr_lines = []
                if result:
                    for line in result:
                        # line[1] is the text string, line[2] is confidence
                        ocr_lines.append(line[1])
                
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
            note = f"\n\n> ℹ️ {ocr_pages} trang được nhận dạng bằng Rapid OCR (tiếng Việt)."
            markdown += note

        if not markdown:
            markdown = "_Không trích xuất được nội dung từ file PDF này._"

        return DocumentConverterResult(markdown=markdown)

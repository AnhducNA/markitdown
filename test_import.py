import os
import sys
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server"))
from ocr_converter import RapidPdfConverter, _dep_error

print("Dependency Error:", _dep_error)

pdf_path = "/home/anhduc/workspace/markitdown/ngay_van_hoa.pdf"

if not os.path.exists(pdf_path):
    print("File not found:", pdf_path)
    sys.exit(1)

with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

if not _dep_error:
    converter = RapidPdfConverter()
    print("Converter instantiated successfully.")
    
    # Mock file_stream and stream_info
    class MockStream:
        def read(self):
            return pdf_bytes
    class MockInfo:
        extension = ".pdf"
        mimetype = "application/pdf"
        
    try:
        result = converter.convert(MockStream(), MockInfo())
        print("----- OCR RESULT -----")
        print(result.markdown)
        print("----------------------")
    except Exception as e:
        import traceback
        traceback.print_exc()

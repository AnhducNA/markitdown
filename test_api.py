import requests
import os

url = "http://localhost:5000/api/convert"
pdf_path = "/home/anhduc/workspace/markitdown/ngay_van_hoa.pdf"

if not os.path.exists(pdf_path):
    print("PDF not found:", pdf_path)
    exit(1)

try:
    with open(pdf_path, "rb") as f:
        files = {"file": f}
        # We don't need any special form data, but let's send it empty
        response = requests.post(url, files=files)
        
    print("Status Code:", response.status_code)
    if response.status_code == 200:
        res_json = response.json()
        print("Title:", res_json.get("title"))
        print("Filename:", res_json.get("filename"))
        print("Size:", res_json.get("size"))
        print("Markdown (first 500 chars):")
        print(res_json.get("markdown")[:500])
    else:
        print("Error Response:", response.text)
except Exception as e:
    print("Request failed:", e)

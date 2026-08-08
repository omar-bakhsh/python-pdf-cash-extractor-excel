import glob
import os
import io
import re
import fitz
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pdfs = glob.glob(r"\\DESKTOP-U37AB2R\Desktop\سكانات\*.pdf")

for p in pdfs:
    doc = fitz.open(p)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=300)
    img = Image.open(io.BytesIO(pix.tobytes())).convert("L")
    text = pytesseract.image_to_string(img, lang="ara+eng", config="--psm 6")
    print("=" * 60)
    print("FILE:", os.path.basename(p))
    print(text)
    print("=" * 60)

# -*- coding: utf-8 -*-
"""
يقرأ فاتورة PDF ممسوحة ضوئيًا (صورة) ويحاول يستخرج الحقول الأساسية
باستخدام Tesseract OCR المحلي (بدون API / بدون إنترنت)

التثبيت (مرة وحدة على ويندوز):
    1) pip install pytesseract pdf2image
    2) تنزيل Tesseract-OCR (برنامج exe):
       https://github.com/UB-Mannheim/tesseract/wiki
       أثناء التثبيت فعّل حزمة اللغة العربية (Arabic) من قائمة الخيارات
    3) تنزيل Poppler for Windows (يحتاجه pdf2image):
       https://github.com/oschwartz10612/poppler-windows/releases
       وفك الضغط وسجل مسار مجلد bin تحت POPPLER_PATH تحت

⚠️ ملاحظة صدق: هذا الملف مطبوع (كمبيوتر) ما عدا التوقيع، فـ OCR للأرقام
والنص الإنجليزي غالبًا دقيق، لكن الاسم العربي وبعض الحقول قد تحتاج تصحيح يدوي.
لذلك السكريبت *يعرض* النتيجة ويطلب تأكيدك قبل ما يرسلها للإكسل.
"""
import re
import sys
import pytesseract
import fitz
from PIL import Image, ImageEnhance
import io

# عدّل هذي المسارات حسب جهازك
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def ocr_pdf_text(pdf_path: str) -> str:
    """يحول أول صفحة من PDF لصورة، ثم يستخرج كل النص منها (عربي + إنجليزي)"""
    try:
        with fitz.open(pdf_path) as doc:
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes()))

            # تحويل لتدرج رمادي + تحسين التباين يرفع دقة Tesseract بشكل ملحوظ
            # على الفواتير المصورة بالسكانر، خصوصًا مع النص العربي المختلط بالإنجليزي
            img = img.convert("L")
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)

            # psm 6 = "افترض كتلة نص موحدة" وهو مناسب لفواتير جدولية أكثر من
            # الوضع الافتراضي (psm 3) الذي يحاول يفصل أعمدة الجدول عن بعض بشكل خاطئ
            text = pytesseract.image_to_string(img, lang="ara+eng", config="--psm 6")
            return text
    except Exception as e:
        print(f"خطأ أثناء المعالجة أو قراءة الملف {pdf_path}: {e}")
        return ""

def parse_fields(raw_text: str) -> dict:
    """
    يحاول يطلع الحقول المهمة بالبحث عن الأنماط الثابتة في قالب هذه الفاتورة
    (رقم الفاتورة، الاسم، الصافي). يحتاج ضبط دقيق حسب اختلاف القوالب.

    ملاحظة إصلاح: Tesseract يشوّه كلمة "الفاتورة" العربية بثبات (تطلع
    "الفائور" أو "الفا:ور" ...الخ)، فالمطابقة الحرفية القديمة "رقم الفاتور"
    كانت تفشل في كل الفواتير تقريبًا ولا تستخرج رقم الفاتورة إطلاقًا. الحل:
    نعتمد فقط على الجذر الثابت بصريًا "الفا" ونسمح بأي تشويه بعده قبل الرقم.
    نفس المشكلة تصير مع "اسم العميل" — كلمة "اسم" كثيرًا ما تختلط بنص
    إنجليزي مموّه، فنعتمد فقط على "العميل" وهي أثبت.
    """
    data = {}

    m = re.search(r"الفا[^\d]{0,15}(\d{3,6})", raw_text)
    if m:
        data["invoice_number"] = m.group(1)

    m = re.search(r"العميل\s*[:\-]?\s*([\u0600-\u06FF][\u0600-\u06FF ]{2,40})", raw_text)
    if m:
        data["customer_name"] = m.group(1).strip()

    # Priority 1: Search for 'المدفوع' or 'Paid' (bottom summary of the invoice)
    m_paid = re.findall(r"(?:المدفوع|Paid|paid)\s*[:\-=]?\s*(\d{2,5}\.\d{2})", raw_text, re.IGNORECASE)
    if m_paid:
        data["net_total_guess"] = float(m_paid[-1])
    else:
        # Priority 2: Search for 'Net' at bottom
        m_net = re.findall(r"Net[^\d]{0,15}(\d{2,5}\.\d{2})", raw_text, re.IGNORECASE)
        if m_net:
            data["net_total_guess"] = float(m_net[-1])
        else:
            # Priority 3: Search for 'الاجمالي مع الضريبه' - take the LAST match
            m_gt = re.findall(r"(?:الاجمالي|الاطمالي)\s*(?:مع\s*الضريب[هة])?[^\d]{0,15}(\d{2,5}\.\d{2})", raw_text)
            if m_gt:
                data["net_total_guess"] = float(m_gt[-1])
            else:
                numbers = re.findall(r"\d{2,6}\.\d{2}", raw_text)
                if numbers:
                    data["net_total_guess"] = float(max(numbers, key=lambda x: float(x)))

    return data


def extract_invoice(pdf_path: str) -> dict:
    raw_text = ocr_pdf_text(pdf_path)
    
    if not raw_text.strip():
        print(f"لم يتم استخراج أي نص من الملف: {pdf_path}")
        return {}
        
    fields = parse_fields(raw_text)

    print("=" * 50)
    print("النص الخام المستخرج (للمراجعة فقط):")
    print(raw_text[:800])
    print("=" * 50)
    print("الحقول المستخرجة تلقائيًا:")
    for k, v in fields.items():
        print(f"  {k}: {v}")
    print("=" * 50)

    confirm = input("اضغط Enter لو البيانات صحيحة، أو اكتب 'تعديل' لتصحيحها يدويًا: ")
    if confirm.strip() == "تعديل":
        fields["customer_name"] = input(f"اسم العميل [{fields.get('customer_name','')}]: ") or fields.get("customer_name", "")
        fields["invoice_number"] = input(f"رقم الفاتورة [{fields.get('invoice_number','')}]: ") or fields.get("invoice_number", "")

    return fields


if __name__ == "__main__":
    # مسار اختباري يعتمد على المدخلات من سطر الأوامر أو يستخدم مسار افتراضي
    test_path = sys.argv[1] if len(sys.argv) > 1 else r"Day_test_صفحة2.pdf"
    result = extract_invoice(test_path)
    print("\nالبيانات النهائية المعتمدة:")
    print(result)

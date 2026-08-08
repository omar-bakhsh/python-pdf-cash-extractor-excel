@echo off
chcp 65001 >nul
title تسجيل الفواتير في الإكسل

echo ====================================================
echo   تشغيل سكريبت تسجيل الفواتير
echo ====================================================
echo.

REM تنظيف متغيرات البيئة الخاصة ببرامج أخرى (مثل BioTime) لتجنب تعارض نسخ Python
set PYTHONHOME=
set PYTHONPATH=

REM تأكد إن Python موجود
where python >nul 2>nul
if errorlevel 1 (
    echo [خطأ] Python غير مثبت أو غير مضاف لـ PATH.
    echo نزّل Python من https://www.python.org/downloads/
    echo وتأكد من تفعيل خيار "Add Python to PATH" أثناء التثبيت.
    pause
    exit /b 1
)

REM الانتقال لمجلد هذا الملف نفسه (حيث يوجد كود بايثون)
cd /d "C:\Users\Dell\OneDrive\Desktop\AUTOMATION\pdf-invoice-to-excel"

REM تثبيت المكتبات المطلوبة (يتخطى تلقائيًا لو مثبتة أصلًا)
echo جاري التأكد من المكتبات المطلوبة...
python -m pip install --quiet --disable-pip-version-check pandas xlwings pytesseract PyMuPDF

echo.
echo تشغيل السكريبت...
echo ----------------------------------------------------
python batch_process_invoices.py

echo ----------------------------------------------------
echo انتهى التشغيل.
pause

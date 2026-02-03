# Script สำหรับติดตั้งไลบรารีทั้งหมด - Drowning Detection System
# สำหรับ Python 3.10.9

Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[!] คำแนะนำ [!]" -ForegroundColor Yellow
Write-Host ""
Write-Host "สคริปต์นี้เป็นการติดตั้งแบบพื้นฐานโดยใช้ Python และ pip ที่อยู่ในระบบ" -ForegroundColor Yellow
Write-Host "สำหรับการติดตั้งที่แนะนำ (ใช้ Conda และรองรับ GPU) กรุณาทำตามขั้นตอนในไฟล์ SETUP_GUIDE.md" -ForegroundColor Yellow
Write-Host ""
Read-Host "กด Enter เพื่อดำเนินการติดตั้งแบบพื้นฐานต่อ หรือกด Ctrl+C เพื่อยกเลิก"
Write-Host "ติดตั้งไลบรารี Drowning Detection System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ตรวจสอบ Python version
Write-Host "[1/4] ตรวจสอบ Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ไม่พบ Python! กรุณาติดตั้ง Python 3.10.9 ก่อน" -ForegroundColor Red
    Read-Host "กด Enter เพื่อออก"
    exit 1
}
Write-Host $pythonVersion
Write-Host ""

# อัปเดต pip
Write-Host "[2/4] อัปเดต pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip
Write-Host ""

# ติดตั้งไลบรารี
Write-Host "[3/4] ติดตั้งไลบรารีจาก requirements.txt..." -ForegroundColor Yellow
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: การติดตั้งล้มเหลว! กรุณาตรวจสอบ error messages ด้านบน" -ForegroundColor Red
    Read-Host "กด Enter เพื่อออก"
    exit 1
}
Write-Host ""

# ตรวจสอบการติดตั้ง
Write-Host "[4/4] ตรวจสอบการติดตั้ง..." -ForegroundColor Yellow
python -c "import cv2; import torch; import numpy; from ultralytics import YOLO; from telegram import Bot; from dotenv import load_dotenv; print('✓ ไลบรารีทั้งหมดติดตั้งสำเร็จ!')"
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "WARNING: บางไลบรารีอาจติดตั้งไม่สำเร็จ กรุณาตรวจสอบ error messages" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ ติดตั้งสำเร็จ!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}
Write-Host ""
Read-Host "กด Enter เพื่อออก"

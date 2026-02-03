@echo off
REM Script สำหรับติดตั้งไลบรารีทั้งหมด - Drowning Detection System
REM สำหรับ Python 3.10.9

echo.
echo [!] คำแนะนำ [!]
echo.
echo สคริปต์นี้เป็นการติดตั้งแบบพื้นฐานโดยใช้ Python และ pip ที่อยู่ในระบบ
echo สำหรับการติดตั้งที่แนะนำ (ใช้ Conda และรองรับ GPU) กรุณาทำตามขั้นตอนในไฟล์ SETUP_GUIDE.md
echo.
pause

echo ========================================
echo ติดตั้งไลบรารี Drowning Detection System
echo ========================================
echo.

REM ตรวจสอบ Python version
echo [1/4] ตรวจสอบ Python version...
python --version
if errorlevel 1 (
    echo ERROR: ไม่พบ Python! กรุณาติดตั้ง Python 3.10.9 ก่อน
    pause
    exit /b 1
)
echo.

REM อัปเดต pip
echo [2/4] อัปเดต pip...
python -m pip install --upgrade pip
echo.

REM ติดตั้งไลบรารี
echo [3/4] ติดตั้งไลบรารีจาก requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: การติดตั้งล้มเหลว! กรุณาตรวจสอบ error messages ด้านบน
    pause
    exit /b 1
)
echo.

REM ตรวจสอบการติดตั้ง
echo [4/4] ตรวจสอบการติดตั้ง...
python -c "import cv2; import torch; import numpy; from ultralytics import YOLO; from telegram import Bot; from dotenv import load_dotenv; print('✓ ไลบรารีทั้งหมดติดตั้งสำเร็จ!')"
if errorlevel 1 (
    echo.
    echo WARNING: บางไลบรารีอาจติดตั้งไม่สำเร็จ กรุณาตรวจสอบ error messages
) else (
    echo.
    echo ========================================
    echo ✓ ติดตั้งสำเร็จ!
    echo ========================================
)
echo.
pause

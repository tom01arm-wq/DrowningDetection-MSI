# คู่มือการติดตั้งไลบรารี - Drowning Detection System

## ข้อกำหนดเบื้องต้น

- Python 3.10.9 (ตรวจสอบด้วย `python --version`)
- pip (Python package manager)

## วิธีติดตั้ง

### 1. ตรวจสอบ Python Version

```bash
python --version
```

ควรแสดง: `Python 3.10.9`

### 2. อัปเดต pip (แนะนำ)

```bash
python -m pip install --upgrade pip
```

### 3. ติดตั้งไลบรารีทั้งหมด

#### วิธีที่ 1: ติดตั้งจาก requirements.txt (แนะนำ)

```bash
python -m pip install -r requirements.txt
```

#### วิธีที่ 2: ติดตั้งทีละตัว (ถ้ามีปัญหา)

```bash
# Core libraries
python -m pip install "numpy>=1.21.0,<1.25.0"
python -m pip install "opencv-python>=4.5.0,<4.9.0"
python -m pip install "python-dotenv>=0.19.0,<1.0.0"

# Telegram Bot
python -m pip install "python-telegram-bot>=20.0,<21.0"

# YOLO and PyTorch
python -m pip install "ultralytics>=8.0.0,<9.0.0"
python -m pip install "torch>=2.0.0,<3.0.0"
python -m pip install "torchvision>=0.15.0,<0.16.0"
```

### 4. ติดตั้ง PyTorch สำหรับ GPU (ถ้ามี NVIDIA GPU)

ถ้ามี NVIDIA GPU และต้องการใช้ CUDA:

```bash
# สำหรับ CUDA 11.8
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# สำหรับ CUDA 12.1
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# สำหรับ CPU only (ถ้าไม่มี GPU)
python -m pip install torch torchvision
```

### 5. ตรวจสอบการติดตั้ง

```bash
python -c "import cv2; import torch; import numpy; from ultralytics import YOLO; from telegram import Bot; from dotenv import load_dotenv; print('All libraries installed successfully!')"
```

## การแก้ปัญหา

### ปัญหา: pip ไม่พบคำสั่ง

**แก้ไข:**
```bash
python -m pip install --upgrade pip
```

### ปัญหา: ติดตั้ง PyTorch ไม่สำเร็จ

**แก้ไข:**
- ติดตั้ง PyTorch แยกก่อน: `python -m pip install torch torchvision`
- จากนั้นติดตั้งไลบรารีอื่นๆ

### ปัญหา: opencv-python ติดตั้งไม่สำเร็จ

**แก้ไข:**
```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install opencv-python
```

### ปัญหา: python-telegram-bot มี conflict

**แก้ไข:**
```bash
python -m pip install --upgrade python-telegram-bot
```

## ตรวจสอบเวอร์ชันที่ติดตั้ง

```bash
python -m pip list
```

หรือตรวจสอบทีละตัว:

```bash
python -c "import cv2; print('OpenCV:', cv2.__version__)"
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import numpy; print('NumPy:', numpy.__version__)"
python -c "import ultralytics; print('Ultralytics:', ultralytics.__version__)"
```

## หมายเหตุ

- ไลบรารีทั้งหมดรองรับ Python 3.10.9
- PyTorch จะติดตั้งแบบ CPU โดย default (ถ้าต้องการ GPU ให้ติดตั้งแยก)
- ใช้ virtual environment แนะนำเพื่อแยก dependencies

## สร้าง Virtual Environment (แนะนำ)

```bash
# สร้าง virtual environment
python -m venv venv

# เปิดใช้งาน (Windows)
venv\Scripts\activate

# เปิดใช้งาน (Linux/Mac)
source venv/bin/activate

# ติดตั้งไลบรารี
python -m pip install -r requirements.txt
```


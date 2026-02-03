# คู่มือการติดตั้ง PyTorch สำหรับ GPU (CUDA)

## สถานะปัจจุบัน

ตรวจสอบแล้ว: PyTorch ติดตั้งแบบ **CPU-only** (`2.0.1+cpu`)
- CUDA Available: **False**
- ต้องติดตั้ง PyTorch แบบ CUDA เพื่อใช้ GPU


## ถอนการติดตั้งตัวเก่า
python -m pip uninstall -y torch torchvision torchaudio

## วิธีติดตั้ง PyTorch สำหรับ GPU
### ขั้นตอนที่ 1: ตรวจสอบ CUDA Version ในระบบ
**Windows:**
```cmd
nvidia-smi
```
ดูที่บรรทัด "CUDA Version" (ใช้ 12.1,)

### ขั้นตอนที่ 2: ติดตั้ง PyTorch แบบ CUDA

#### สำหรับ CUDA 11.8
```bash
python -m pip uninstall torch torchvision torchaudio
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### สำหรับ CUDA 12.1
```bash
python -m pip uninstall torch torchvision torchaudio
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### สำหรับ CUDA 12.4 (ล่าสุด)
```bash
python -m pip uninstall torch torchvision torchaudio
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### ขั้นตอนที่ 3: ตรวจสอบการติดตั้ง

```bash
python -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```
python -c "import torch; print('CUDA Available:', torch.cuda.is_available())"

ควรแสดง:
```
CUDA Available: True
GPU: [ชื่อ GPU ของคุณ]
```

## วิธีตรวจสอบ CUDA Version

### Windows
1. เปิด Command Prompt
2. รัน: `nvidia-smi`
3. ดูที่ "CUDA Version" ในตาราง

### หรือตรวจสอบใน Python
```python
import torch
print(torch.version.cuda)  # แสดง CUDA version ที่ PyTorch รองรับ
```

## หมายเหตุ

- **ต้องมี NVIDIA GPU** และติดตั้ง NVIDIA Driver แล้ว
- **ต้องมี CUDA Toolkit** ติดตั้งในระบบ (หรือใช้ CUDA ที่มาพร้อม PyTorch)
- **ตรวจสอบ CUDA version** ให้ตรงกับ PyTorch ที่ติดตั้ง

## Troubleshooting

### ปัญหา: CUDA Available: False หลังติดตั้ง

**วิธีแก้:**
1. ตรวจสอบว่า NVIDIA Driver ติดตั้งแล้ว: `nvidia-smi`
2. ตรวจสอบ CUDA version ให้ตรงกัน
3. Restart terminal/IDE หลังติดตั้ง
4. ตรวจสอบว่า PyTorch ติดตั้งถูกต้อง: `python -c "import torch; print(torch.__version__)"`

### ปัญหา: Out of Memory (OOM)

**วิธีแก้:**
1. ลด batch size
2. ลด resolution ของวิดีโอ
3. ใช้ GPU device อื่น (ถ้ามีหลาย GPU)

## หลังจากติดตั้งเสร็จ

1. รันโปรแกรม: `python main.py`
2. ควรเห็นข้อความ: `[GPU] ตรวจพบ GPU: [ชื่อ GPU]`
3. ระบบจะใช้ GPU อัตโนมัติ


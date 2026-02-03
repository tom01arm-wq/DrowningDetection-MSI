# คู่มือการติดตั้ง (สำหรับ Conda และ GPU)

คู่มือนี้สำหรับผู้ที่ต้องการติดตั้งโปรเจกต์ในสภาพแวดล้อมของ Conda เพื่อการจัดการ Dependencies ที่ดีกว่า และสำหรับผู้ที่ต้องการใช้ GPU (NVIDIA) เพื่อเพิ่มความเร็วในการประมวลผล

## ขั้นตอนการติดตั้ง

### 1. ติดตั้ง Miniconda
หากยังไม่มี Miniconda หรือ Anaconda, ให้ดาวน์โหลดและติดตั้งจากหน้าเว็บทางการ:
- [Miniconda Download Page](https://docs.conda.io/en/latest/miniconda.html)

เลือกเวอร์ชันที่ตรงกับระบบปฏิบัติการของคุณ (Windows/Linux/macOS) และติดตั้งตามขั้นตอน.

### 2. สร้างและเปิดใช้งาน Conda Environment
หลังจากติดตั้ง Conda เสร็จแล้ว, ให้เปิด **Anaconda Prompt** (หรือ Terminal บน Mac/Linux) แล้วรันคำสั่งต่อไปนี้เพื่อสร้าง environment ใหม่ชื่อ `drowning_detection` โดยใช้ Python 3.10:

```bash
conda create -n drowning_detection python=3.10
```

จากนั้นเปิดใช้งาน environment นี้ทุกครั้งก่อนเริ่มทำงานกับโปรเจกต์:

```bash
conda activate drowning_detection
```

คุณจะเห็น `(drowning_detection)` นำหน้า command prompt ของคุณ ซึ่งหมายความว่าคุณอยู่ใน environment ที่ถูกต้องแล้ว.

### 3. ติดตั้ง PyTorch พร้อม CUDA Support
สำหรับ GPU NVIDIA GeForce RTX 3050 ของคุณ, คุณต้องติดตั้ง PyTorch เวอร์ชันที่รองรับ CUDA เพื่อให้โปรแกรมสามารถใช้ GPU ได้.

**สำคัญ:** รันคำสั่งนี้ *ก่อน* การติดตั้งจาก `requirements.txt` เพื่อให้แน่ใจว่าได้เวอร์ชันที่ถูกต้องสำหรับ GPU ของคุณ.

```bash
# คำสั่งสำหรับติดตั้ง PyTorch v2.1+ กับ CUDA 12.1 (แนะนำสำหรับ RTX 30 series)
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**วิธีตรวจสอบว่าติดตั้ง PyTorch และ GPU สำเร็จ:**
เมื่อติดตั้งเสร็จแล้ว, ให้ลองรัน Python interpreter ใน terminal ของคุณ (ที่ยัง activate environment อยู่) แล้วพิมพ์คำสั่งนี้:
```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
```
ผลลัพธ์ที่ถูกต้องควรจะแสดง `CUDA available: True` และชื่อการ์ดจอ `NVIDIA GeForce RTX 3050 Laptop GPU` ของคุณ.

### 4. ติดตั้ง OpenCV และ Dependencies อื่นๆ
เมื่อติดตั้ง PyTorch เรียบร้อยแล้ว, ให้ติดตั้งไลบรารีที่เหลือทั้งหมดที่โปรเจกต์ต้องการจากไฟล์ `requirements.txt`.

```bash
pip install -r requirements.txt
```
**หมายเหตุ:** หากไฟล์ `requirements.txt` มี `torch` หรือ `opencv-python` อยู่แล้ว, คำสั่ง `pip` อาจจะข้ามการติดตั้งไปเพราะเราได้ติดตั้งเวอร์ชันที่ถูกต้องไปแล้วในขั้นตอนก่อนหน้า. หากคุณพบข้อผิดพลาดที่เกี่ยวกับการติดตั้ง, ลองเปิดไฟล์ `requirements.txt` และลบบรรทัดที่มี `torch`, `torchvision`, `torchaudio` ออกชั่วคราวก่อนรันคำสั่งนี้อีกครั้ง.

### 5. ตั้งค่า Environment Variables
โปรเจกต์นี้ต้องใช้ไฟล์ `.env` ในการตั้งค่าต่างๆ. ให้คัดลอกไฟล์ `.env.example` ไปเป็นไฟล์ใหม่ชื่อ `.env`:

```bash
# บน Windows
copy .env.example .env
```

จากนั้นเปิดไฟล์ `.env` ด้วย Text Editor และกรอกข้อมูลที่จำเป็น เช่น `TELEGRAM_TOKEN` และ `TELEGRAM_CHAT_ID` ตามคำแนะนำในไฟล์ `ENV_SETUP.md`.

### 6. รันโปรแกรม
เมื่อทำตามขั้นตอนทั้งหมดแล้ว, คุณพร้อมที่จะรันโปรแกรม:

```bash
python main.py
```
โปรแกรมควรจะเริ่มต้นทำงาน และใน Console ควรมีข้อความแจ้งว่า `System starting on: GPU` ซึ่งเป็นการยืนยันว่าโปรแกรมกำลังใช้การ์ดจอของคุณ.
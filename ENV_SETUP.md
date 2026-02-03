# คู่มือการตั้งค่าไฟล์ .env

## ปัญหาที่พบบ่อย

### 1. ไม่พบไฟล์ .env
**อาการ:** `ENV_ERROR: ไม่พบไฟล์ .env ที่ ...`

**วิธีแก้:**
1. คัดลอกไฟล์ `.env.example` เป็น `.env`
2. เปิดไฟล์ `.env` และกรอกค่าตามต้องการ

**Windows:**
```cmd
copy .env.example .env
```

**Linux/Mac:**
```bash
cp .env.example .env
```

### 2. Environment Variable หายไป
**อาการ:** `ENV_MISSING: TELEGRAM_TOKEN` หรือตัวแปรอื่นๆ

**วิธีแก้:**
1. ตรวจสอบว่าไฟล์ `.env` มีตัวแปรที่ต้องการครบทุกตัว
2. ตรวจสอบว่าไม่มีช่องว่างรอบเครื่องหมาย `=`
3. ตรวจสอบว่าไม่มี `#` อยู่หน้าบรรทัดที่ต้องการใช้

**ตัวอย่างที่ถูกต้อง:**
```
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

**ตัวอย่างที่ผิด:**
```
TELEGRAM_TOKEN = 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz  # มีช่องว่าง
# TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz  # ถูก comment
TELEGRAM_TOKEN=  # ค่าว่าง
```

### 3. Path ไม่ถูกต้อง
**อาการ:** `FileNotFoundError` หรือ `Model not found`

**วิธีแก้:**
- ใช้ relative path จากโฟลเดอร์โปรเจกต์: `models/best.pt`
- หรือใช้ absolute path: `C:/Users/.../models/best.pt`
- ตรวจสอบว่าไฟล์มีอยู่จริง

### 4. ค่า Type ไม่ถูกต้อง
**อาการ:** `ValueError: invalid literal for int()` หรือ `ValueError: could not convert string to float`

**วิธีแก้:**
- `RISK_THRESHOLD` ต้องเป็นตัวเลข (integer): `50`
- `VIDEO_FPS` ต้องเป็นตัวเลขทศนิยม (float): `20.0`
- `SEND_VIDEO` ต้องเป็น boolean: `true`, `false`, `1`, `0`, `yes`, `no`

## วิธีสร้างไฟล์ .env

### ขั้นตอนที่ 1: คัดลอกไฟล์ template
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

### ขั้นตอนที่ 2: แก้ไขไฟล์ .env

เปิดไฟล์ `.env` ด้วย text editor (Notepad, VS Code, etc.) และกรอกค่าตามนี้:

#### 1. Telegram Configuration
```env
TELEGRAM_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id
```

**วิธีหา Telegram Token:**
1. เปิด Telegram และค้นหา `@BotFather`
2. ส่งคำสั่ง `/newbot` และทำตามคำแนะนำ
3. คัดลอก Token ที่ได้มา

**วิธีหา Chat ID:**
1. เปิด Telegram และค้นหา `@userinfobot`
2. ส่งข้อความใดๆ ไป
3. Bot จะส่ง Chat ID กลับมา

#### 2. Model Paths
```env
DETECTION_MODEL_PATH=models/best.pt
POSE_MODEL_PATH=yolo11n-pose.pt
```

ตรวจสอบว่าไฟล์โมเดลมีอยู่ในตำแหน่งที่ระบุ

#### 3. Detection Settings
```env
RISK_THRESHOLD=50
ALERT_COOLDOWN_SEC=10.0
```

#### 4. Video Settings
```env
VIDEO_BUFFER_LEN=300
VIDEO_FPS=20.0
VIDEO_DURATION_SEC=5.0
VIDEO_CODEC=mp4v
```

#### 5. Alert Settings
```env
ALERT_TEXT=⚠️ DANGER: Drowning detected!
SEND_VIDEO=true
SEND_PHOTO=true
SEND_MESSAGE=true
ALERT_SNAPSHOT_PATH=alert_snapshot.jpg
ALERT_VIDEO_PATH=alert_video.mp4
```

#### 6. Pose Detection Parameters
```env
POSE_KP_CONF_MIN=0.5
POSE_AXIS_HORIZONTAL_DY_MAX=20.0
POSE_AXIS_VERTICAL_SH_HIP_MIN=30.0
POSE_AXIS_VERTICAL_HIP_KNEE_MIN=20.0
POSE_ARM_WINDOW_SEC=2.0
POSE_ARM_Y_STD_MIN=15.0
POSE_ARM_NEAR_SHOULDER_PX=50.0
POSE_HEAD_GAP_MIN=30.0
POSE_HEAD_HOLD_SEC=2.0
POSE_SCORE_AXIS=30
POSE_SCORE_ARM=30
POSE_SCORE_HEAD=40
```

### ขั้นตอนที่ 3: ตรวจสอบไฟล์ .env

รันโปรแกรมเพื่อตรวจสอบ:
```bash
python main.py
```

ถ้ามี error ให้ตรวจสอบ:
1. ไฟล์ `.env` มีอยู่จริง
2. ทุกตัวแปรมีค่า (ไม่มีค่าว่าง)
3. Path ถูกต้อง
4. Type ของค่าถูกต้อง

## ตัวอย่างไฟล์ .env ที่ใช้งานได้

```env
# Telegram
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# Models
DETECTION_MODEL_PATH=models/best.pt
POSE_MODEL_PATH=yolo11n-pose.pt

# Detection
RISK_THRESHOLD=50
ALERT_COOLDOWN_SEC=10.0

# Video
VIDEO_BUFFER_LEN=300
VIDEO_FPS=20.0
VIDEO_DURATION_SEC=5.0
VIDEO_CODEC=mp4v

# Alert
ALERT_TEXT=⚠️ DANGER: Drowning detected!
SEND_VIDEO=true
SEND_PHOTO=true
SEND_MESSAGE=true
ALERT_SNAPSHOT_PATH=alert_snapshot.jpg
ALERT_VIDEO_PATH=alert_video.mp4

# Pose Detection
POSE_KP_CONF_MIN=0.5
POSE_AXIS_HORIZONTAL_DY_MAX=20.0
POSE_AXIS_VERTICAL_SH_HIP_MIN=30.0
POSE_AXIS_VERTICAL_HIP_KNEE_MIN=20.0
POSE_ARM_WINDOW_SEC=2.0
POSE_ARM_Y_STD_MIN=15.0
POSE_ARM_NEAR_SHOULDER_PX=50.0
POSE_HEAD_GAP_MIN=30.0
POSE_HEAD_HOLD_SEC=2.0
POSE_SCORE_AXIS=30
POSE_SCORE_ARM=30
POSE_SCORE_HEAD=40
```

## หมายเหตุ

- **อย่า commit ไฟล์ `.env` ลง Git** (ควรมีใน `.gitignore`)
- ไฟล์ `.env.example` เป็น template ที่ปลอดภัยต่อการ commit
- ตรวจสอบ path ของโมเดลให้ถูกต้อง
- ตรวจสอบ Telegram Token และ Chat ID ให้ถูกต้อง


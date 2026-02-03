# แผนการ Refactoring - Drowning Detection System

## 📋 สารบัญ
1. [การวิเคราะห์ปัญหา](#การวิเคราะห์ปัญหา)
2. [โครงสร้างใหม่](#โครงสร้างใหม่)
3. [แผนการ Refactoring](#แผนการ-refactoring)
4. [ฟีเจอร์ใหม่](#ฟีเจอร์ใหม่)
5. [การแก้บั๊กและปรับปรุงประสิทธิภาพ](#การแก้บั๊กและปรับปรุงประสิทธิภาพ)

---

## 🔍 การวิเคราะห์ปัญหา

### ปัญหาหลักที่พบ

#### 1. **Architecture Issues**
- `main.py` รวมทุกอย่างไว้ (227 บรรทัด) - ละเมิด Single Responsibility Principle
- Configuration loading ผสมกับ business logic
- Model loading ไม่มี error handling ที่ดี
- ไม่มี separation of concerns

#### 2. **Code Quality Issues**
- Telegram async handling ไม่ถูกต้อง: ใช้ `asyncio.create_task()` ใน sync context
- Object Detection ไม่ได้ใช้จริง (แค่วาดกล่อง, ไม่มี logic)
- Video buffer อาจมี memory leak (copy frames หลายครั้ง)
- Hardcoded values (device="0", conf=0.5, conf=0.6)
- ไม่มี type hints ในหลายฟังก์ชัน

#### 3. **Missing Features**
- ไม่มี logging system (ใช้ print() ทั้งหมด)
- ไม่มี config validation
- ไม่มี graceful shutdown
- ไม่มี health check/monitoring
- ไม่มี statistics/metrics tracking
- ไม่รองรับ multiple video sources
- ไม่มี recording to file option

#### 4. **Security Issues**
- `test_bot.py` และ `testvideo.py` มี hardcoded credentials
- ไม่มี `.env.example` template

#### 5. **Unused Code**
- `src/logic.py` - ไม่ถูกใช้
- `src/detector.py` - ไฟล์ว่าง
- `debug_model.py` - อาจเป็น temporary file

---

## 🏗️ โครงสร้างใหม่

```
DrowningDetection_MSI/
├── .env                    # Configuration (ต้องสร้าง)
├── .env.example            # Template สำหรับ .env
├── main.py                 # Entry point (สั้นลงมาก)
├── requirements.txt
│
├── src/
│   ├── __init__.py
│   │
│   ├── config/             # Configuration management
│   │   ├── __init__.py
│   │   ├── loader.py       # โหลดและ validate .env
│   │   └── settings.py     # Config dataclass
│   │
│   ├── models/             # Model management
│   │   ├── __init__.py
│   │   ├── loader.py       # โหลด YOLO models
│   │   └── manager.py      # จัดการ models lifecycle
│   │
│   ├── detection/          # Detection logic
│   │   ├── __init__.py
│   │   ├── processor.py    # DrowningProcessor (refactored)
│   │   ├── detector.py     # Object detection logic (เติมให้ใช้งานได้)
│   │   └── tracker.py      # Person tracking (optional)
│   │
│   ├── video/              # Video handling
│   │   ├── __init__.py
│   │   ├── capture.py      # VideoCapture wrapper
│   │   ├── buffer.py       # Video buffer management
│   │   └── writer.py       # Video writing utilities
│   │
│   ├── alert/              # Alert system
│   │   ├── __init__.py
│   │   ├── manager.py      # AlertManager class
│   │   └── worker.py       # Background alert worker
│   │
│   ├── telegram/           # Telegram integration
│   │   ├── __init__.py
│   │   ├── bot.py          # TelegramBot (refactored)
│   │   └── sender.py       # Message/media sender
│   │
│   ├── utils/              # Utilities
│   │   ├── __init__.py
│   │   ├── logger.py       # Logging system
│   │   ├── exceptions.py   # Custom exceptions
│   │   └── helpers.py      # Helper functions
│   │
│   └── core/               # Core application
│       ├── __init__.py
│       ├── app.py          # Main application class
│       └── loop.py         # Main processing loop
│
├── data/
│   ├── snapshots/
│   ├── test_videos/
│   └── recordings/         # สำหรับบันทึกวิดีโอถ้าต้องการ
│
├── models/
│   ├── best.pt
│   └── yolo11n-pose.pt
│
└── tests/                  # Tests (optional)
    ├── __init__.py
    ├── test_config.py
    ├── test_processor.py
    └── test_telegram.py
```

---

## 📝 แผนการ Refactoring

### Phase 1: Foundation (พื้นฐาน)

#### 1.1 สร้าง Configuration System
**ไฟล์:** `src/config/loader.py`, `src/config/settings.py`

**งาน:**
- แยก config loading ออกจาก `main.py`
- สร้าง `Settings` dataclass สำหรับ type safety
- เพิ่ม config validation
- สร้าง `.env.example` template
- เพิ่ม default values สำหรับ optional configs

**ผลลัพธ์:**
- Config management เป็นระบบ
- Type-safe configuration
- ง่ายต่อการทดสอบ

#### 1.2 สร้าง Logging System
**ไฟล์:** `src/utils/logger.py`

**งาน:**
- แทนที่ `print()` ทั้งหมดด้วย proper logging
- รองรับ log levels (DEBUG, INFO, WARNING, ERROR)
- รองรับ file logging (optional)
- Format logs ให้อ่านง่าย

**ผลลัพธ์:**
- Debugging ง่ายขึ้น
- สามารถ track system behavior
- Production-ready logging

#### 1.3 สร้าง Exception System
**ไฟล์:** `src/utils/exceptions.py`

**งาน:**
- สร้าง custom exceptions:
  - `ConfigError`
  - `ModelLoadError`
  - `VideoCaptureError`
  - `TelegramError`
- ใช้แทน generic exceptions

**ผลลัพธ์:**
- Error handling ชัดเจนขึ้น
- ง่ายต่อการ debug

---

### Phase 2: Core Components (ส่วนหลัก)

#### 2.1 Refactor Model Management
**ไฟล์:** `src/models/loader.py`, `src/models/manager.py`

**งาน:**
- แยก model loading ออกจาก `main.py`
- เพิ่ม error handling ที่ดีขึ้น
- รองรับ model validation
- เพิ่ม model caching/reuse
- รองรับ GPU/CPU auto-detection

**ผลลัพธ์:**
- Model management เป็นระบบ
- Error handling ดีขึ้น
- รองรับการขยาย

#### 2.2 Refactor Video Handling
**ไฟล์:** `src/video/capture.py`, `src/video/buffer.py`, `src/video/writer.py`

**งาน:**
- สร้าง `VideoCapture` wrapper class
- แยก video buffer logic
- ปรับปรุง memory management (ลดการ copy)
- สร้าง video writer utilities
- รองรับ multiple sources (webcam, file, RTSP)

**ผลลัพธ์:**
- Memory efficient
- รองรับหลายแหล่งวิดีโอ
- Code reuse ได้

#### 2.3 Refactor Detection Processor
**ไฟล์:** `src/detection/processor.py`

**งาน:**
- ปรับปรุง `DrowningProcessor`:
  - แยก visualization logic
  - เพิ่ม type hints
  - ปรับปรุง error handling
  - เพิ่ม documentation
- ลบ dependency จาก OpenCV ใน logic layer

**ผลลัพธ์:**
- Separation of concerns
- Testable code
- Maintainable

#### 2.4 สร้าง Object Detector
**ไฟล์:** `src/detection/detector.py`

**งาน:**
- เติม `detector.py` ให้ใช้งานได้
- สร้าง `ObjectDetector` class
- เพิ่ม logic สำหรับ person detection
- รองรับ integration กับ pose detection

**ผลลัพธ์:**
- Object detection ใช้งานได้จริง
- สามารถใช้ร่วมกับ pose detection

---

### Phase 3: Alert & Communication (แจ้งเตือนและการสื่อสาร)

#### 3.1 Refactor Telegram Bot
**ไฟล์:** `src/telegram/bot.py`, `src/telegram/sender.py`

**งาน:**
- แก้ async handling ให้ถูกต้อง
- แยก sender logic
- เพิ่ม retry mechanism
- เพิ่ม rate limiting
- ปรับปรุง error handling

**ผลลัพธ์:**
- Non-blocking I/O ทำงานถูกต้อง
- Reliable message delivery
- Better error recovery

#### 3.2 สร้าง Alert Manager
**ไฟล์:** `src/alert/manager.py`, `src/alert/worker.py`

**งาน:**
- สร้าง `AlertManager` class
- แยก alert worker logic
- เพิ่ม alert queue system
- เพิ่ม cooldown management
- รองรับ multiple alert types

**ผลลัพธ์:**
- Alert system เป็นระบบ
- ไม่ block main loop
- Reliable alert delivery

---

### Phase 4: Application Core (แกนหลักแอปพลิเคชัน)

#### 4.1 สร้าง Main Application Class
**ไฟล์:** `src/core/app.py`

**งาน:**
- สร้าง `DrowningDetectionApp` class
- รวมทุก component เข้าด้วยกัน
- จัดการ lifecycle (start, stop, shutdown)
- เพิ่ม graceful shutdown
- เพิ่ม health check

**ผลลัพธ์:**
- Application structure ชัดเจน
- Easy to test
- Production-ready

#### 4.2 สร้าง Main Loop
**ไฟล์:** `src/core/loop.py`

**งาน:**
- แยก main loop logic
- เพิ่ม FPS tracking
- เพิ่ม performance monitoring
- เพิ่ม error recovery

**ผลลัพธ์:**
- Main loop clean และ maintainable
- Performance tracking
- Robust error handling

#### 4.3 Refactor main.py
**ไฟล์:** `main.py`

**งาน:**
- ทำให้ `main.py` สั้นลงมาก (เหลือ ~20-30 บรรทัด)
- ใช้ `DrowningDetectionApp` class
- เพิ่ม CLI argument support (optional)
- เพิ่ม signal handling

**ผลลัพธ์:**
- Entry point สะอาด
- Easy to understand
- Professional structure

---

## ✨ ฟีเจอร์ใหม่

### 1. Logging System
- File logging (optional)
- Log rotation
- Different log levels
- Structured logging

### 2. Statistics & Metrics
- FPS tracking
- Detection rate
- Alert count
- Performance metrics
- Export to file (optional)

### 3. Health Check System
- Model status check
- Video source status
- Telegram connection check
- System resource monitoring

### 4. Recording System
- Optional video recording to file
- Configurable recording duration
- Automatic file management

### 5. Multiple Video Sources
- Webcam (current)
- Video file
- RTSP stream
- IP camera

### 6. Configuration Management
- `.env.example` template
- Config validation
- Default values
- Runtime config reload (optional)

### 7. Graceful Shutdown
- Signal handling (SIGINT, SIGTERM)
- Clean resource cleanup
- Save state (optional)

### 8. Error Recovery
- Auto-reconnect video source
- Model reload on error
- Telegram retry mechanism

---

## 🐛 การแก้บั๊กและปรับปรุงประสิทธิภาพ

### Bugs ที่ต้องแก้

#### 1. **Telegram Async Handling Bug**
**ปัญหา:** ใช้ `asyncio.create_task()` ใน sync context
```python
# ปัจจุบัน (ผิด)
loop = asyncio.get_event_loop()
if loop.is_running():
    asyncio.create_task(...)  # ❌ จะไม่ทำงาน
```

**แก้ไข:**
- ใช้ `threading` + `asyncio.run()` แทน
- หรือใช้ `asyncio.run_coroutine_threadsafe()`
- หรือใช้ proper async/await pattern

#### 2. **Memory Leak ใน Video Buffer**
**ปัญหา:** Copy frames หลายครั้ง
```python
# ปัจจุบัน
video_buffer.append(frame.copy())  # Copy 1
snapshot_for_thread = annotated_frame.copy()  # Copy 2
buffer_for_thread = list(video_buffer)  # Copy 3
```

**แก้ไข:**
- ใช้ reference counting
- Copy เฉพาะเมื่อจำเป็น
- ใช้ memory-efficient buffer

#### 3. **Object Detection ไม่ได้ใช้**
**ปัญหา:** แค่วาดกล่อง ไม่มี logic

**แก้ไข:**
- สร้าง `ObjectDetector` class
- เพิ่ม person detection logic
- Integrate กับ pose detection

#### 4. **Hardcoded Values**
**ปัญหา:** device="0", conf=0.5, conf=0.6

**แก้ไข:**
- ย้ายไปใน config
- ใช้ config values

#### 5. **Error Handling ไม่ดี**
**ปัญหา:** ใช้ bare `except Exception`

**แก้ไข:**
- ใช้ specific exceptions
- เพิ่ม error logging
- เพิ่ม error recovery

### Performance Improvements

#### 1. **Model Inference Optimization**
- Batch processing (ถ้าเป็นไปได้)
- Model quantization (optional)
- GPU optimization

#### 2. **Video Processing Optimization**
- Frame skipping (ถ้า FPS ต่ำ)
- Resolution scaling (optional)
- Multi-threading สำหรับ processing

#### 3. **Memory Optimization**
- Reduce frame copying
- Efficient buffer management
- Garbage collection tuning

#### 4. **Alert System Optimization**
- Queue-based alert system
- Batch sending (optional)
- Compression สำหรับ media

---

## 📊 Timeline และลำดับความสำคัญ

### Priority 1 (Critical - ต้องทำก่อน)
1. ✅ สร้าง Configuration System
2. ✅ สร้าง Logging System
3. ✅ แก้ Telegram Async Bug
4. ✅ Refactor Model Management
5. ✅ สร้าง Alert Manager

### Priority 2 (Important - ควรทำ)
6. ✅ Refactor Video Handling
7. ✅ Refactor Detection Processor
8. ✅ สร้าง Main Application Class
9. ✅ Refactor main.py

### Priority 3 (Nice to have)
10. ✅ สร้าง Object Detector
11. ✅ เพิ่ม Statistics & Metrics
12. ✅ เพิ่ม Health Check
13. ✅ เพิ่ม Recording System

---

## 🧪 Testing Strategy

### Unit Tests
- Config loading
- Model loading
- Detection logic
- Alert system

### Integration Tests
- End-to-end flow
- Telegram integration
- Video processing

### Performance Tests
- FPS measurement
- Memory usage
- CPU/GPU usage

---

## 📝 Notes

- เก็บ backward compatibility ไว้ (ถ้าเป็นไปได้)
- Document ทุกการเปลี่ยนแปลง
- ใช้ type hints ทุกที่
- Follow PEP 8
- ใช้ meaningful variable names
- เพิ่ม docstrings

---

## ✅ Checklist

### Phase 1
- [ ] สร้าง `src/config/` module
- [ ] สร้าง `src/utils/logger.py`
- [ ] สร้าง `src/utils/exceptions.py`
- [ ] สร้าง `.env.example`

### Phase 2
- [ ] สร้าง `src/models/` module
- [ ] สร้าง `src/video/` module
- [ ] Refactor `src/detection/processor.py`
- [ ] เติม `src/detection/detector.py`

### Phase 3
- [ ] Refactor `src/telegram/` module
- [ ] สร้าง `src/alert/` module

### Phase 4
- [ ] สร้าง `src/core/app.py`
- [ ] สร้าง `src/core/loop.py`
- [ ] Refactor `main.py`

### Cleanup
- [ ] ลบ unused files (`src/logic.py`, `debug_model.py`)
- [ ] ลบ hardcoded credentials จาก test files
- [ ] Update `requirements.txt` ถ้าจำเป็น
- [ ] สร้าง README.md (optional)


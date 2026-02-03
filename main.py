"""ระบบตรวจจับการจมน้ำ - YOLOv11 Standard + ID Tracking + Telegram Alert

ใช้โมเดล YOLOv11 มาตรฐาน (yolo11m.pt) ตรวจจับคน (class person)
ติดแท็ก ID1, ID2, ... และแจ้งเตือนเมื่อคนหายไป 40 วินาที

รองรับการกำหนดพื้นที่:
- พื้นที่สีฟ้า = สระว่ายน้ำ (เปิดการติดตาม)
- พื้นที่สีเขียว = นอกสระ (ไม่ติดตาม)
"""

import os
import cv2
import torch
import time
import json
import numpy as np
from collections import deque
from ultralytics import YOLO
from dotenv import load_dotenv
from src.telegram_utils import TelegramBot
from src.alert_manager import AlertManager

# --- โหลด Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
ZONES_FILE = os.path.join(BASE_DIR, "zones.json")
if not os.path.exists(ENV_PATH):
    raise RuntimeError(f"ENV_ERROR: ไม่พบไฟล์ .env ที่ {ENV_PATH}")
load_dotenv(ENV_PATH, override=True)


def _get_env(name: str, default: str = None) -> str:
    value = os.getenv(name, default)
    return value if value else default


def _get_env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def _get_env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def _get_env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name, str(default)).strip().lower()
    return val in ("1", "true", "yes", "y", "on")


def _open_capture(source):
    """เปิด video source (webcam หรือ RTSP)"""
    if isinstance(source, str) and source.strip().lower().startswith("rtsp://"):
        for transport in ["tcp", "udp"]:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{transport}|stimeout;5000000"
            cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
            if cap.isOpened():
                print(f"📹 RTSP เปิดสำเร็จ (transport={transport})")
                return cap
            cap.release()
    return cv2.VideoCapture(source)


# ==================== ZONE MANAGEMENT ====================

def load_zones():
    """โหลดพื้นที่จากไฟล์ zones.json"""
    if os.path.exists(ZONES_FILE):
        try:
            with open(ZONES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("pool_zone"), data.get("safe_zone")
        except Exception as e:
            print(f"⚠️ โหลด zones.json ไม่สำเร็จ: {e}")
    return None, None


def save_zones(pool_zone, safe_zone):
    """บันทึกพื้นที่ลงไฟล์ zones.json"""
    data = {"pool_zone": pool_zone, "safe_zone": safe_zone}
    with open(ZONES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ บันทึกพื้นที่ลง {ZONES_FILE} เรียบร้อย")


def point_in_zone(point, zone):
    """ตรวจสอบว่าจุดอยู่ในพื้นที่หรือไม่ (รองรับ polygon)"""
    if zone is None:
        return False
    
    # แปลง zone เป็น numpy array
    pts = np.array(zone, dtype=np.int32)
    
    # ใช้ pointPolygonTest
    result = cv2.pointPolygonTest(pts, point, False)
    return result >= 0


def draw_zones(frame, pool_zone, safe_zone):
    """วาดพื้นที่บนเฟรม"""
    overlay = frame.copy()
    
    # วาดพื้นที่สระว่ายน้ำ (สีฟ้า)
    if pool_zone and len(pool_zone) >= 3:
        pts = np.array(pool_zone, dtype=np.int32)
        cv2.fillPoly(overlay, [pts], (255, 200, 100))  # สีฟ้าอ่อน
        cv2.polylines(frame, [pts], True, (255, 150, 0), 3)  # ขอบสีฟ้าเข้ม
    
    # วาดพื้นที่ปลอดภัย (สีเขียว)
    if safe_zone and len(safe_zone) >= 3:
        pts = np.array(safe_zone, dtype=np.int32)
        cv2.fillPoly(overlay, [pts], (100, 255, 100))  # สีเขียวอ่อน
        cv2.polylines(frame, [pts], True, (0, 200, 0), 3)  # ขอบสีเขียวเข้ม
    
    # ผสมภาพ
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
    return frame


class ZoneSelector:
    """คลาสสำหรับเลือกพื้นที่ด้วยการคลิกเมาส์"""
    
    def __init__(self, window_name):
        self.window_name = window_name
        self.points = []
        self.current_zone = None
        self.done = False
        
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.points.append((x, y))
        elif event == cv2.EVENT_RBUTTONDOWN:
            if len(self.points) >= 3:
                self.current_zone = self.points.copy()
                self.done = True
    
    def select_zone(self, frame, zone_name, color):
        """ให้ผู้ใช้เลือกพื้นที่"""
        self.points = []
        self.current_zone = None
        self.done = False
        
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        print(f"\n📍 กำหนด{zone_name}:")
        print("   - คลิกซ้าย = เพิ่มจุด")
        print("   - คลิกขวา = ยืนยัน (ต้องมีอย่างน้อย 3 จุด)")
        print("   - กด 's' = ข้าม (ไม่กำหนดพื้นที่นี้)")
        print("   - กด 'r' = รีเซ็ตจุด")
        
        while not self.done:
            display = frame.copy()
            
            # วาดจุดที่คลิก
            for i, pt in enumerate(self.points):
                cv2.circle(display, pt, 6, color, -1)
                cv2.putText(display, str(i+1), (pt[0]+10, pt[1]-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # วาดเส้นเชื่อม
            if len(self.points) > 1:
                for i in range(len(self.points) - 1):
                    cv2.line(display, self.points[i], self.points[i+1], color, 2)
            
            # วาดเส้นปิด polygon (ถ้ามีอย่างน้อย 3 จุด)
            if len(self.points) >= 3:
                cv2.line(display, self.points[-1], self.points[0], color, 2, cv2.LINE_AA)
                pts = np.array(self.points, dtype=np.int32)
                overlay = display.copy()
                cv2.fillPoly(overlay, [pts], (*color[:3], 50))
                cv2.addWeighted(overlay, 0.3, display, 0.7, 0, display)
            
            # แสดงคำแนะนำ
            cv2.putText(display, f"Selecting: {zone_name}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(display, f"Points: {len(self.points)} | Left-click: Add | Right-click: Done | 's': Skip | 'r': Reset",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow(self.window_name, display)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s'):  # Skip
                print(f"   ⏭️ ข้าม{zone_name}")
                return None
            elif key == ord('r'):  # Reset
                self.points = []
                print("   🔄 รีเซ็ตจุด")
            elif key == ord('q'):  # Quit
                return None
        
        print(f"   ✅ กำหนด{zone_name}เรียบร้อย ({len(self.current_zone)} จุด)")
        return self.current_zone


def setup_zones(cap):
    """ตั้งค่าพื้นที่ก่อนเริ่มระบบ"""
    print("\n" + "=" * 60)
    print("🎯 โหมดกำหนดพื้นที่ (Zone Setup)")
    print("=" * 60)
    
    # โหลดพื้นที่เดิม
    pool_zone, safe_zone = load_zones()
    
    if pool_zone or safe_zone:
        print("\n📂 พบพื้นที่ที่บันทึกไว้:")
        if pool_zone:
            print(f"   🔵 พื้นที่สระว่ายน้ำ: {len(pool_zone)} จุด")
        if safe_zone:
            print(f"   🟢 พื้นที่ปลอดภัย: {len(safe_zone)} จุด")
        
        # อ่านเฟรมแรก
        ok, frame = cap.read()
        if not ok:
            print("❌ ไม่สามารถอ่านเฟรมจากกล้องได้")
            return pool_zone, safe_zone
        
        # แสดงพื้นที่เดิม
        display = draw_zones(frame.copy(), pool_zone, safe_zone)
        cv2.putText(display, "Press 'y' to use saved zones, 'n' to reset, 'q' to quit",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow("Zone Setup", display)
        
        print("\n❓ ต้องการใช้พื้นที่เดิมหรือไม่?")
        print("   'y' = ใช้พื้นที่เดิม")
        print("   'n' = กำหนดใหม่")
        print("   'q' = ออก")
        
        while True:
            key = cv2.waitKey(0) & 0xFF
            if key == ord('y'):
                print("✅ ใช้พื้นที่เดิม")
                cv2.destroyWindow("Zone Setup")
                return pool_zone, safe_zone
            elif key == ord('n'):
                print("🔄 กำหนดพื้นที่ใหม่...")
                pool_zone, safe_zone = None, None
                break
            elif key == ord('q'):
                cv2.destroyWindow("Zone Setup")
                return None, None
    
    # อ่านเฟรมแรก
    ok, frame = cap.read()
    if not ok:
        print("❌ ไม่สามารถอ่านเฟรมจากกล้องได้")
        return None, None
    
    selector = ZoneSelector("Zone Setup")
    
    # กำหนดพื้นที่สระว่ายน้ำ (สีฟ้า)
    pool_zone = selector.select_zone(frame.copy(), "พื้นที่สระว่ายน้ำ (Pool Zone)", (255, 150, 0))
    
    # กำหนดพื้นที่ปลอดภัย (สีเขียว) - optional
    safe_zone = selector.select_zone(frame.copy(), "พื้นที่ปลอดภัย (Safe Zone)", (0, 200, 0))
    
    cv2.destroyWindow("Zone Setup")
    
    # บันทึกพื้นที่
    if pool_zone or safe_zone:
        save_zones(pool_zone, safe_zone)
    
    return pool_zone, safe_zone


def main():
    print("\n" + "=" * 60)
    print("🏊 ระบบตรวจจับการจมน้ำ - YOLOv11 Standard + ID Tracking")
    print("=" * 60 + "\n")

    # --- Configuration ---
    TELEGRAM_TOKEN = _get_env("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = _get_env("TELEGRAM_CHAT_ID")
    VIDEO_SOURCE = _get_env("VIDEO_SOURCE", "0")
    SHOW_VIDEO = _get_env_bool("SHOW_VIDEO", True)
    
    # Model settings
    MODEL_NAME = "yolo11m.pt"  # โมเดลมาตรฐานจาก Ultralytics
    CONFIDENCE_THRESHOLD = _get_env_float("DET_CONF", 0.5)
    
    # Tracking & Alert settings
    MISSING_ALERT_SEC = _get_env_float("MISSING_ALERT_SEC", 40)  # แจ้งเตือนเมื่อหายไป 40 วินาที
    REPEAT_ALERT_INTERVAL = 10  # ส่งแจ้งเตือนซ้ำทุก 10 วินาทีหลังจาก 40 วินาที
    
    # Alert settings
    ALERT_COOLDOWN_SEC = _get_env_float("ALERT_COOLDOWN_SEC", 0)
    ALERT_TEXT = _get_env("ALERT_TEXT", "แจ้งเตือนพบคนจมน้ำ")
    SEND_MESSAGE = _get_env_bool("SEND_MESSAGE", True)
    SEND_PHOTO = _get_env_bool("SEND_PHOTO", True)
    SEND_VIDEO = _get_env_bool("SEND_VIDEO", True)
    SNAPSHOT_PATH = os.path.join(BASE_DIR, _get_env("ALERT_SNAPSHOT_PATH", "alert_snapshot.jpg"))
    VIDEO_PATH = os.path.join(BASE_DIR, _get_env("ALERT_VIDEO_PATH", "alert_video.mp4"))
    VIDEO_BUFFER_LEN = _get_env_int("VIDEO_BUFFER_LEN", 100)
    VIDEO_FPS = _get_env_float("VIDEO_FPS", 30)
    VIDEO_DURATION_SEC = _get_env_float("VIDEO_DURATION_SEC", 3)
    VIDEO_CODEC = _get_env("VIDEO_CODEC", "avc1")

    # --- ตรวจสอบ Telegram ---
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(" Error: กรุณาตั้งค่า TELEGRAM_TOKEN และ TELEGRAM_CHAT_ID ใน .env")
        return

    # --- สร้าง Telegram Bot และ Alert Manager ---
    bot = TelegramBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    print(f" Telegram Bot พร้อมใช้งาน (Chat ID: {TELEGRAM_CHAT_ID})")

    alert_manager = AlertManager(
        bot_obj=bot,
        alert_text=ALERT_TEXT,
        send_message=SEND_MESSAGE,
        send_photo=SEND_PHOTO,
        send_video=SEND_VIDEO,
        snapshot_path=SNAPSHOT_PATH,
        video_path=VIDEO_PATH,
        video_duration_sec=VIDEO_DURATION_SEC,
        video_fps=VIDEO_FPS,
        video_codec=VIDEO_CODEC,
        alert_cooldown_sec=ALERT_COOLDOWN_SEC,
    )

    # --- โหลดโมเดล YOLOv11 มาตรฐาน ---
    device = "0" if torch.cuda.is_available() else "cpu"
    print(f"💻 Device: {'CUDA GPU' if device == '0' else 'CPU'}")
    print(f"📦 กำลังโหลดโมเดล: {MODEL_NAME}")
    
    try:
        model = YOLO(MODEL_NAME)
        print(f"✅ โหลดโมเดลสำเร็จ!")
        print(f"📋 Classes: {model.names}")
    except Exception as e:
        print(f"❌ CRITICAL: โหลดโมเดลไม่สำเร็จ: {e}")
        return

    # --- เปิดกล้อง ---
    video_source = VIDEO_SOURCE
    if isinstance(video_source, str) and video_source.isnumeric():
        video_source = int(video_source)
    
    print(f"📹 กำลังเปิดกล้อง: {video_source}")
    cap = _open_capture(video_source)
    
    if not cap.isOpened():
        print("❌ Error: ไม่สามารถเปิดกล้องได้")
        return

    # --- กำหนดพื้นที่ (Zone Setup) ---
    pool_zone, safe_zone = setup_zones(cap)
    
    if pool_zone:
        print(f"\n🔵 พื้นที่สระว่ายน้ำ: {len(pool_zone)} จุด (เปิดการติดตาม)")
    else:
        print("\n⚠️ ไม่ได้กำหนดพื้นที่สระ - ติดตามทั้งเฟรม")
    
    if safe_zone:
        print(f"🟢 พื้นที่ปลอดภัย: {len(safe_zone)} จุด (ไม่ติดตาม)")

    # --- ตัวแปรสำหรับ Tracking ---
    video_buffer = deque(maxlen=VIDEO_BUFFER_LEN)
    track_id_to_display = {}  # แปลง track_id -> ID1, ID2, ...
    next_display_id = 1
    person_state = {}  # เก็บสถานะของแต่ละ ID
    
    # --- ระบบจำกัด ID ตามจำนวนคนทั้งหมด ---
    # จำนวน ID สูงสุด = จำนวนคนที่เคยเห็นพร้อมกัน (Pool + Safe)
    max_total_count = 0  # จำนวนคนสูงสุดที่เคยเห็นทั้งหมด
    max_pool_count = 0  # จำนวนคนสูงสุดที่เคยเห็นในสระ
    active_pool_ids = set()  # ID ที่กำลังอยู่ในสระ
    active_safe_ids = set()  # ID ที่กำลังอยู่ใน Safe Zone
    ids_entered_from_safe = set()  # ID ที่เข้ามาจาก Safe Zone (สามารถสร้าง ID ใหม่ได้)
    
    # --- Re-identification: ติดตามคนที่ดำน้ำแล้วโผล่ขึ้นมา ---
    submerged_persons = {}  # เก็บข้อมูลคนที่หายไป (อาจดำน้ำ) {display_id: {"position": (x,y), "time": ts, "state": {...}}}
    REIDENTIFY_DISTANCE_PX = _get_env_float("REIDENTIFY_DISTANCE_PX", 150)  # ระยะทางที่ถือว่าใกล้เคียง (พิกเซล)
    REIDENTIFY_TIME_SEC = _get_env_float("REIDENTIFY_TIME_SEC", 60)  # เวลาที่รอ re-identify (วินาที)
    
    # --- นับจำนวนคนที่หายไปใน Pool Zone ---
    missing_in_pool_count = 0  # จำนวนคนที่หายไปใน Pool Zone (อาจจมน้ำ)
    exited_to_safe_ids = set()  # ID ที่ออกจาก pool ไป safe zone (ไม่นับว่าหายไป)
    
    # --- ระบบแจ้งเตือนแบบขั้นบันได (Tiered Missing Alerts) ---
    MISSING_ALERT_TIERS = [
        {"seconds": 20, "message": "🏊 ID{id} ดำน้ำได้ 20 วินาทีแล้ว", "level": 1},
        {"seconds": 25, "message": "🏊 ID{id} ดำน้ำได้ 25 วินาทีแล้ว", "level": 2},
        {"seconds": 30, "message": "⚠️ ID{id} มีโอกาสเสี่ยงจมน้ำได้ 30 วินาทีแล้ว ให้รีบทำการตรวจสอบ", "level": 3},
        {"seconds": 35, "message": "🚨 ID{id} มีโอกาสเสี่ยงจมน้ำได้ 35 วินาทีแล้ว ให้รีบทำการตรวจสอบโดยด่วน", "level": 4},
        {"seconds": 40, "message": "🆘 ID{id} เสี่ยงจมน้ำสูงได้ 40 วินาทีแล้ว ให้รีบทำการตรวจสอบโดยด่วน", "level": 5},
    ]
    
    # สีสำหรับแสดงผล
    COLORS = {
        "normal": (0, 255, 0),        # เขียว - ปกติ
        "outside": (128, 128, 128),   # เทา - นอกพื้นที่สระ
        "missing": (0, 0, 255),       # แดง - หายไป/ดำน้ำ
    }

    print(f"\n⏱️  Missing Alert: {MISSING_ALERT_SEC} วินาที (แจ้งเตือนซ้ำทุก 10 วินาทีหลัง 40s)")
    print(f"⏱️  Alert Cooldown: {ALERT_COOLDOWN_SEC} วินาที")
    print("\n" + "=" * 60)
    print("🎬 เริ่มการทำงาน - 'q'=ออก, 'z'=กำหนดพื้นที่, 's'=หยุดแจ้งเตือน")
    print("=" * 60 + "\n")

    # ส่งข้อความเริ่มต้น
    bot.send_message("🏊 ระบบตรวจจับการจมน้ำเริ่มทำงานแล้ว (YOLOv11 Standard)")

    try:
        while cap.isOpened():
            ts = time.time()
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            video_buffer.append((ts, frame.copy()))
            annotated_frame = frame.copy()
            
            # --- วาดพื้นที่ (Zones) ---
            annotated_frame = draw_zones(annotated_frame, pool_zone, safe_zone)
            
            # --- YOLO Tracking ---
            try:
                results = model.track(
                    frame,
                    device=device,
                    conf=CONFIDENCE_THRESHOLD,
                    persist=True,
                    verbose=False,
                    classes=[0]  # class 0 = person
                )
            except Exception:
                results = model.predict(
                    frame,
                    device=device,
                    conf=CONFIDENCE_THRESHOLD,
                    verbose=False,
                    classes=[0]
                )

            seen_track_ids = set()
            
            # รีเซ็ต active IDs สำหรับเฟรมนี้
            current_frame_pool_ids = set()
            current_frame_safe_ids = set()

            # --- ประมวลผลผลลัพธ์ ---
            if results and len(results) > 0 and results[0].boxes is not None:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf_score = float(box.conf[0])
                    
                    # คำนวณตำแหน่งกึ่งกลาง
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    current_pos = (center_x, center_y)

                    # ดึง track_id
                    track_id = None
                    if hasattr(box, "id") and box.id is not None:
                        try:
                            track_id = int(box.id[0])
                        except:
                            pass

                    if track_id is None:
                        continue

                    # --- ตรวจสอบว่าอยู่ในพื้นที่ไหน (ก่อน assign ID) ---
                    in_pool = point_in_zone(current_pos, pool_zone) if pool_zone else True
                    in_safe = point_in_zone(current_pos, safe_zone) if safe_zone else False
                    
                    # --- Re-identification & ID Assignment ---
                    reidentified_display_id = None
                    is_new_from_safe = False
                    
                    if track_id not in track_id_to_display:
                        # === กรณี 1: คนใหม่โผล่ใน Pool Zone โดยตรง ===
                        if in_pool and not in_safe:
                            # ต้อง Re-identify เป็น ID ที่หายไปก่อนหน้า (ถ้ามี)
                            # หาคนที่หายไปที่ใกล้ที่สุด
                            best_match_id = None
                            best_match_dist = float('inf')
                            
                            for sub_display_id, sub_info in list(submerged_persons.items()):
                                sub_pos = sub_info["position"]
                                sub_time = sub_info["time"]
                                time_since_submerged = ts - sub_time
                                
                                if time_since_submerged <= REIDENTIFY_TIME_SEC:
                                    dist = ((current_pos[0] - sub_pos[0])**2 + (current_pos[1] - sub_pos[1])**2)**0.5
                                    if dist < best_match_dist:
                                        best_match_dist = dist
                                        best_match_id = sub_display_id
                            
                            # ถ้ามีคนหายไปอยู่ → บังคับ re-identify (ไม่สร้าง ID ใหม่)
                            if best_match_id is not None:
                                reidentified_display_id = best_match_id
                                sub_info = submerged_persons[best_match_id]
                                # กู้คืนสถานะเดิม
                                person_state[track_id] = sub_info["state"].copy()
                                person_state[track_id]["last_seen"] = ts
                                person_state[track_id]["last_position"] = current_pos
                                person_state[track_id]["counted_as_missing"] = False
                                # ลบออกจาก submerged
                                del submerged_persons[best_match_id]
                                # ลดจำนวนคนหายไป
                                if missing_in_pool_count > 0:
                                    missing_in_pool_count -= 1
                                print(f"🔄 Re-identified: ID{best_match_id} โผล่ขึ้นมาใน Pool Zone (dist={best_match_dist:.1f}px)")
                                track_id_to_display[track_id] = reidentified_display_id
                            else:
                                # ไม่มีคนหายไป → สร้าง ID ใหม่ได้ถ้าจำนวนคนเพิ่มขึ้น
                                # ตรวจสอบจำนวนคนปัจจุบัน (รวม Pool + Safe)
                                current_total = len(current_frame_pool_ids) + len(current_frame_safe_ids)
                                if max_total_count == 0 or current_total < max_total_count or next_display_id <= max_total_count:
                                    track_id_to_display[track_id] = next_display_id
                                    print(f"👤 คนใหม่ใน Pool Zone: ID{next_display_id}")
                                    next_display_id += 1
                                else:
                                    # มีคนครบแล้ว แต่ไม่มีใครหายไป → ข้ามคนนี้
                                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                                    cv2.putText(annotated_frame, "UNKNOWN (waiting re-id)", (x1, max(0, y1 - 10)),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                                    continue
                        
                        # === กรณี 2: คนใหม่เข้ามาจาก Safe Zone ===
                        elif in_safe:
                            # สามารถสร้าง ID ใหม่ได้
                            track_id_to_display[track_id] = next_display_id
                            ids_entered_from_safe.add(next_display_id)
                            print(f"🚶 คนใหม่เข้ามาจาก Safe Zone: ID{next_display_id}")
                            next_display_id += 1
                            is_new_from_safe = True
                        
                        # === กรณี 3: นอกพื้นที่ทั้งหมด ===
                        else:
                            track_id_to_display[track_id] = next_display_id
                            next_display_id += 1
                    
                    display_id = track_id_to_display[track_id]
                    seen_track_ids.add(track_id)
                    
                    # ถ้าอยู่ในพื้นที่ปลอดภัย = ติดแท็ก ID แต่ไม่ติดตามความเสี่ยง
                    if in_safe:
                        # บันทึกว่า ID นี้ออกจาก Pool ไป Safe Zone (ไม่นับว่าหายไป)
                        exited_to_safe_ids.add(display_id)
                        current_frame_safe_ids.add(display_id)  # เพิ่มเข้า Safe Zone ในเฟรมนี้
                        # ลบออกจาก submerged_persons ถ้ามี (เพราะโผล่ขึ้นมาแล้ว)
                        if display_id in submerged_persons:
                            del submerged_persons[display_id]
                            if missing_in_pool_count > 0:
                                missing_in_pool_count -= 1
                        # วาด bounding box สีเขียวเข้ม (Safe Zone)
                        safe_color = (0, 200, 100)  # สีเขียวเข้ม
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), safe_color, 2)
                        cv2.circle(annotated_frame, (center_x, y1), 8, safe_color, -1)
                        cv2.putText(annotated_frame, f"ID{display_id} SAFE", (x1, max(0, y1 - 10)),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, safe_color, 2)
                        continue
                    
                    # ถ้าไม่อยู่ในพื้นที่สระ (และมีการกำหนดพื้นที่สระ) = ไม่ติดตาม
                    if not in_pool and pool_zone:
                        active_pool_ids.discard(display_id)
                        # วาด bounding box สีเทา (นอกพื้นที่)
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), COLORS["outside"], 2)
                        cv2.putText(annotated_frame, f"ID{display_id} OUTSIDE", (x1, max(0, y1 - 10)),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["outside"], 2)
                        continue

                    # === อยู่ในพื้นที่สระว่ายน้ำ - เปิดการติดตาม ===
                    
                    # เพิ่ม ID เข้า current_frame_pool_ids
                    current_frame_pool_ids.add(display_id)
                    
                    # สร้างหรืออัพเดทสถานะ
                    if track_id not in person_state:
                        person_state[track_id] = {
                            "display_id": display_id,
                            "last_seen": ts,
                            "last_position": current_pos,
                            "missing_alerted": False,
                            "missing_alert_level": 0,  # ระดับการแจ้งเตือนที่ส่งไปแล้ว (0 = ยังไม่เคย)
                            "last_repeat_alert": 0,  # เวลาที่ส่งแจ้งเตือนซ้ำครั้งล่าสุด
                            "acknowledged": False,  # กดปุ่ม S หยุดแจ้งเตือนแล้วหรือไม่
                        }

                    state = person_state[track_id]

                    # อัพเดทสถานะ - คนโผล่ขึ้นมาแล้ว รีเซ็ตทุกอย่าง
                    state["last_seen"] = ts
                    state["last_position"] = current_pos
                    state["missing_alerted"] = False
                    state["missing_alert_level"] = 0  # รีเซ็ตระดับแจ้งเตือน
                    state["last_repeat_alert"] = 0
                    state["acknowledged"] = False  # รีเซ็ตเมื่อคนโผล่ขึ้นมา
                    state["submerged_logged"] = False  # รีเซ็ต flag สำหรับ print

                    # เลือกสีและ label - คนในสระปกติ
                    color = COLORS["normal"]
                    status = "IN POOL"

                    # วาด bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    
                    # วาด ID บนศีรษะ
                    cv2.circle(annotated_frame, (center_x, y1), 8, color, -1)
                    label = f"ID{display_id} {status} {conf_score:.0%}"
                    cv2.putText(annotated_frame, label, (x1, max(0, y1 - 10)),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # --- อัปเดต active IDs หลังจบ loop ---
            active_pool_ids = current_frame_pool_ids.copy()
            active_safe_ids = current_frame_safe_ids.copy()
            
            # อัปเดตจำนวนคนทั้งหมดและในสระ
            total_visible = len(active_pool_ids) + len(active_safe_ids)
            if total_visible > max_total_count:
                max_total_count = total_visible
                print(f"📊 อัปเดตจำนวนคนทั้งหมดสูงสุด: {max_total_count} คน (Pool: {len(active_pool_ids)}, Safe: {len(active_safe_ids)})")
            if len(active_pool_ids) > max_pool_count:
                max_pool_count = len(active_pool_ids)
                print(f"📊 อัปเดตจำนวนคนในสระสูงสุด: {max_pool_count} คน")

            # --- ตรวจสอบคนที่หายไป ---
            for tid, state in list(person_state.items()):
                if tid in seen_track_ids:
                    continue

                time_missing = ts - state["last_seen"]
                display_id = state["display_id"]
                last_pos = state.get("last_position")
                
                # ตรวจสอบว่าหายไปใน Pool Zone หรือไม่ (ไม่ใช่ออกไป Safe Zone)
                was_in_pool = point_in_zone(last_pos, pool_zone) if (pool_zone and last_pos) else True
                exited_safely = display_id in exited_to_safe_ids
                
                # --- บันทึกลง submerged_persons สำหรับ Re-identification ---
                if was_in_pool and not exited_safely and display_id not in submerged_persons:
                    if time_missing >= 1.0 and not state.get("submerged_logged", False):  # หายไปอย่างน้อย 1 วินาที
                        submerged_persons[display_id] = {
                            "position": last_pos,
                            "time": state["last_seen"],
                            "state": state.copy(),
                        }
                        state["submerged_logged"] = True  # ป้องกัน print ซ้ำ
                        print(f" ID{display_id} หายไปใน Pool Zone (อาจดำน้ำ) - รอ re-identify")
                
                # --- นับจำนวนคนที่หายไปใน Pool Zone ---
                if was_in_pool and not exited_safely:
                    if time_missing >= MISSING_ALERT_SEC and not state.get("counted_as_missing"):
                        missing_in_pool_count += 1
                        state["counted_as_missing"] = True
                        print(f"⚠️ ID{display_id} หายไปใน Pool Zone นานกว่า {MISSING_ALERT_SEC}s - นับว่าหายไป (รวม: {missing_in_pool_count})")

                # --- แจ้งเตือนแบบขั้นบันได (Tiered Alerts) ---
                # แจ้งเตือนทุกคนที่หายไปใน Pool Zone (ถ้ายังไม่กด S หยุด)
                if was_in_pool and not exited_safely and not state.get("acknowledged", False):
                    current_alert_level = state.get("missing_alert_level", 0)
                    
                    for tier in MISSING_ALERT_TIERS:
                        tier_seconds = tier["seconds"]
                        tier_level = tier["level"]
                        tier_message = tier["message"]
                        
                        # ถ้าหายไปครบเวลาตาม tier และยังไม่เคยแจ้งเตือนระดับนี้
                        if time_missing >= tier_seconds and current_alert_level < tier_level:
                            msg = tier_message.format(id=display_id)
                            print(f"📢 แจ้งเตือนระดับ {tier_level}: {msg}")
                            alert_manager.trigger_alert(annotated_frame, video_buffer, custom_text=msg)
                            state["missing_alert_level"] = tier_level
                            state["missing_alerted"] = True
                            state["last_repeat_alert"] = ts
                            break  # แจ้งเตือนทีละระดับ
                    
                    # --- แจ้งเตือนซ้ำทุก REPEAT_ALERT_INTERVAL วินาที เมื่อเกิน 40 วินาที ---
                    if time_missing >= 40 and current_alert_level >= 5:
                        last_repeat = state.get("last_repeat_alert", 0)
                        if ts - last_repeat >= REPEAT_ALERT_INTERVAL:  # ส่งซ้ำตาม interval
                            msg = f"🆘🆘 ID{display_id} หายไปนานกว่า {int(time_missing)} วินาที! กด 'S' เพื่อหยุดแจ้งเตือน"
                            print(f"� แจ้งเตือนซ้ำ: {msg}")
                            alert_manager.trigger_alert(annotated_frame, video_buffer, custom_text=msg)
                            state["last_repeat_alert"] = ts
                
                # --- ลบ submerged_persons ที่หมดเวลา ---
                for sub_id in list(submerged_persons.keys()):
                    if ts - submerged_persons[sub_id]["time"] > REIDENTIFY_TIME_SEC:
                        del submerged_persons[sub_id]

            # --- Alert Manager ---
            alert_manager.process_frame(frame)

            # --- วาด Status Panel ---
            height, width = annotated_frame.shape[:2]
            overlay = annotated_frame.copy()
            cv2.rectangle(overlay, (10, 10), (480, 185), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, annotated_frame, 0.4, 0, annotated_frame)
            
            current_time_str = time.strftime("%H:%M:%S")
            status_color = (0, 0, 255) if missing_in_pool_count > 0 else (0, 255, 0)
            status_text = "MISSING DETECTED!" if missing_in_pool_count > 0 else "MONITORING"
            
            cv2.putText(annotated_frame, f"Status: {status_text}", (20, 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
            
            # แสดงจำนวนคนทั้งหมด (Pool + Safe)
            total_current = len(active_pool_ids) + len(active_safe_ids)
            cv2.putText(annotated_frame, f"Total: {total_current}/{max_total_count} | Missing: {missing_in_pool_count}", (20, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(annotated_frame, f"Time: {current_time_str}", (20, 85),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # แสดงจำนวนคนใน Pool Zone และ Safe Zone
            pool_info_color = (255, 200, 100)
            cv2.putText(annotated_frame, f"Pool: {len(active_pool_ids)} | Safe: {len(active_safe_ids)} | Submerged: {len(submerged_persons)}", (20, 110),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, pool_info_color, 1)
            
            # แสดงจำนวนคนที่หายไปใน Pool Zone
            missing_color = (0, 0, 255) if missing_in_pool_count > 0 else (255, 255, 255)
            cv2.putText(annotated_frame, f"Missing in Pool: {missing_in_pool_count}", (20, 135),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, missing_color, 1)
            
            # แสดง ID ที่ใช้อยู่
            all_visible_ids = sorted(list(active_pool_ids | active_safe_ids))
            ids_str = ", ".join([f"ID{i}" for i in all_visible_ids]) if all_visible_ids else "None"
            cv2.putText(annotated_frame, f"IDs: {ids_str}", (20, 160),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            cv2.putText(annotated_frame, "'z'=zones | 'q'=quit | 's'=stop alert", (20, 175),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            # --- แสดงผล ---
            if SHOW_VIDEO:
                cv2.imshow("Drowning Detection - YOLOv11", annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('z'):
                    # กำหนดพื้นที่ใหม่
                    print("\n🔄 กำหนดพื้นที่ใหม่...")
                    pool_zone, safe_zone = setup_zones(cap)
                    if pool_zone:
                        print(f"✅ อัปเดตพื้นที่สระเรียบร้อย ({len(pool_zone)} จุด)")
                elif key == ord('s'):
                    # หยุดการแจ้งเตือนและรีเซ็ตคนจมน้ำ (ได้รับการช่วยเหลือแล้ว)
                    rescued_count = 0
                    rescued_ids = []
                    tids_to_remove = []
                    
                    for tid, state in person_state.items():
                        # เฉพาะคนที่กำลังแจ้งเตือนอยู่ (หายไปในสระ)
                        if state.get("missing_alert_level", 0) > 0 or state.get("submerged_logged", False):
                            display_id = state['display_id']
                            rescued_ids.append(display_id)
                            tids_to_remove.append(tid)
                            rescued_count += 1
                            
                            # ลบออกจาก submerged_persons
                            if display_id in submerged_persons:
                                del submerged_persons[display_id]
                            
                            # ลด missing_in_pool_count ถ้าเคยนับว่าหายไป
                            if state.get("counted_as_missing", False):
                                missing_in_pool_count = max(0, missing_in_pool_count - 1)
                            
                            print(f"🟢 ID{display_id} ได้รับการช่วยเหลือแล้ว - รีเซ็ตสถานะ")
                    
                    # ลบ person_state ของคนที่ได้รับการช่วยเหลือ
                    for tid in tids_to_remove:
                        del person_state[tid]
                    
                    if rescued_count > 0:
                        ids_str = ", ".join([f"ID{i}" for i in rescued_ids])
                        bot.send_message(f"🟢 ยืนยันการช่วยเหลือ: {ids_str} ({rescued_count} คน) - หยุดการแจ้งเตือน")
                        print(f"🟢 ช่วยเหลือเรียบร้อย {rescued_count} คน - หยุดการแจ้งเตือนและรีเซ็ตสถานะ")
                    else:
                        print("ℹ️ ไม่มีคนจมน้ำที่ต้องช่วยเหลือ")

    except KeyboardInterrupt:
        print("\n หยุดโดยผู้ใช้")

    finally:
        cap.release()
        if SHOW_VIDEO:
            cv2.destroyAllWindows()
        bot.send_message(" ระบบตรวจจับการจมน้ำหยุดทำงานแล้ว")
        print("\n ระบบหยุดทำงานแล้ว")


if __name__ == "__main__":
    main()

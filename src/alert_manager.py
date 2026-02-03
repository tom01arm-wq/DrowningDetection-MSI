import os
import cv2
import numpy as np
import threading
from collections import deque
import time
from datetime import datetime
from .telegram_utils import TelegramBot

class AlertManager:
    """
    คลาสสำหรับจัดการระบบแจ้งเตือนไปยัง Telegram แบบ Non-blocking.
    """
    def __init__(self,
                 bot_obj: TelegramBot,
                 alert_text: str,
                 send_message: bool,
                 send_photo: bool,
                 send_video: bool,
                 snapshot_path: str,
                 video_path: str,
                 video_duration_sec: float,
                 video_fps: float,
                 video_codec: str,
                 alert_cooldown_sec: float):
        """
        เริ่มต้น AlertManager.

        พารามิเตอร์:
            bot_obj (TelegramBot): อินสแตนซ์ของ TelegramBot สำหรับส่งข้อความ.
            alert_text (str): ข้อความแจ้งเตือนหลัก.
            send_message (bool): ส่งข้อความหรือไม่.
            send_photo (bool): ส่งรูปภาพหรือไม่.
            send_video (bool): ส่งวิดีโอหรือไม่.
            snapshot_path (str): เส้นทางสำหรับบันทึกรูปภาพ snapshot.
            video_path (str): เส้นทางสำหรับบันทึกวิดีโอ.
            video_duration_sec (float): ระยะเวลาของวิดีโอที่ต้องการบันทึก (วินาที).
            video_fps (float): เฟรมเรตของวิดีโอ.
            video_codec (str): Codec สำหรับบันทึกวิดีโอ.
            alert_cooldown_sec (float): ระยะเวลา Cooldown ระหว่างการแจ้งเตือน (วินาที).
        """
        self.bot = bot_obj
        self.alert_text = alert_text
        self.send_message = send_message
        self.send_photo = send_photo
        self.send_video = send_video
        self.snapshot_path = snapshot_path
        self.video_path = video_path
        self.video_duration_sec = video_duration_sec
        self.video_fps = video_fps
        self.video_codec = video_codec
        self.alert_cooldown_sec = alert_cooldown_sec

        self.last_alert_time = 0.0
        self.alert_thread = None
        self.alert_lock = threading.Lock() # ใช้สำหรับป้องกัน Race Condition
        
        # ตัวแปรสำหรับระบบบันทึกวิดีโอแบบต่อเนื่อง (Post-Event Recording)
        self.recording = False
        self.recording_frames = []
        self.frames_remaining = 0
        self.current_alert_caption = self.alert_text

    def process_frame(self, frame):
        """
        รับเฟรมจาก Main Loop ตลอดเวลา
        หากอยู่ในสถานะ Recording จะทำการเก็บเฟรมนี้เข้าวิดีโอ
        """
        with self.alert_lock:
            if self.recording:
                # แก้ไข: ทำสำเนาเฟรมก่อนนำไปประมวลผล เพื่อป้องกันการแก้ไขข้อมูลต้นฉบับ
                frame_to_record = frame.copy()
                
                # ประทับเวลา (Timestamp) ลงบนเฟรมเพื่อตรวจสอบว่าเป็นภาพใหม่จริง
                timestamp_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                cv2.putText(frame_to_record, timestamp_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
                
                self.recording_frames.append(frame_to_record)
                self.frames_remaining -= 1
                
                # เมื่อบันทึกครบตามจำนวนที่ต้องการแล้ว
                if self.frames_remaining <= 0:
                    self.recording = False
                    print(f" [AlertManager] บันทึกวิดีโอครบแล้ว ({len(self.recording_frames)} เฟรม) -> เริ่มส่งข้อมูล")
                    # เริ่ม Thread สำหรับ Save และ Send
                    threading.Thread(
                        target=self._save_and_send_video_task,
                        args=(self.recording_frames, self.current_alert_caption),
                        daemon=True
                    ).start()

    def _extract_frames_from_prebuffer(self, pre_buffer: deque, now_ts: float) -> list:
        if pre_buffer is None or len(pre_buffer) == 0:
            return []

        target_frames = int(round(float(self.video_duration_sec) * float(self.video_fps)))
        if target_frames <= 0:
            target_frames = 1

        # รองรับทั้ง 2 แบบ:
        # - deque[(ts, frame)]
        # - deque[frame]
        first_item = pre_buffer[0]
        has_ts = isinstance(first_item, tuple) and len(first_item) == 2

        if has_ts:
            start_ts = float(now_ts) - float(self.video_duration_sec)
            window = [f for (t, f) in pre_buffer if float(t) >= start_ts]
            if len(window) == 0:
                window = [pre_buffer[-1][1]]
        else:
            # ไม่มี timestamp: ใช้จำนวนเฟรมย้อนหลังตาม target
            window = list(pre_buffer)[-target_frames:]

        # Resample เฉพาะกรณีเฟรมเยอะเกิน (คุมความยาว)
        # ถ้าเฟรมไม่พอ: ไม่ pad ที่นี่ เพื่อหลีกเลี่ยงคลิปนิ่งจากการซ้ำเฟรมเดียว
        if len(window) > target_frames:
            idxs = np.linspace(0, len(window) - 1, num=target_frames)
            frames = [window[int(round(i))] for i in idxs]
        else:
            frames = list(window)

        # deep copy กันเฟรมถูกแก้ไขทีหลัง
        return [f.copy() for f in frames]

    def _read_video_frame_count(self, video_path: str, max_frames: int = 5) -> int:
        try:
            cap = cv2.VideoCapture(video_path)
            count = 0
            while count < max_frames:
                ok, _ = cap.read()
                if not ok:
                    break
                count += 1
            cap.release()
            return int(count)
        except Exception:
            return 0

    def _save_and_send_video_task(self, frames: list, caption_text: str):
        """
        ฟังก์ชัน Worker สำหรับบันทึกและส่งวิดีโอใน thread แยก
        """
        if not frames:
            print(" [VideoThread] ไม่มีข้อมูลเฟรมภาพ")
            return

        # ---- Verification: ตรวจสอบความแตกต่างของเฟรม ----
        if len(frames) > 1:
            # เปรียบเทียบข้อมูล pixel ของเฟรมแรกและเฟรมสุดท้าย
            are_frames_identical = np.array_equal(frames[0], frames[-1])
            print(f" [VideoThread-Debug] Frame-Check: เฟรมแรกและเฟรมสุดท้าย 'เหมือนกัน': {are_frames_identical}")
            if are_frames_identical:
                print(" [VideoThread-Warning] วิดีโออาจไม่มีการเคลื่อนไหว (Static Video)!")
        # ------------------------------------------------

        try:
            # 1. เตรียมพารามิเตอร์
            height, width = frames[0].shape[:2]
            fps = float(self.video_fps)
            
            # ลบไฟล์เดิมทิ้งก่อน
            if os.path.exists(self.video_path):
                try:
                    os.remove(self.video_path)
                except OSError:
                    pass

            print(f" [VideoThread] เริ่มบันทึกวิดีโอ... ({len(frames)} เฟรม, {width}x{height}, {fps} FPS)")

            # 2. เลือก Codec ที่เหมาะสมที่สุดสำหรับ Telegram (mp4v)
            selected_codec = 'mp4v'
            fourcc = cv2.VideoWriter_fourcc(*selected_codec)
            out = cv2.VideoWriter(self.video_path, fourcc, fps, (width, height), isColor=True)
            if not out.isOpened():
                print(f" [VideoThread] CRITICAL: ไม่สามารถสร้างไฟล์วิดีโอได้ (Codec '{selected_codec}' ใช้งานไม่ได้)")
                return

            print(f" [VideoThread] ✔ เลือกใช้งาน Codec: '{selected_codec}'")

            # 3. เขียนเฟรมลงไฟล์
            for frame in frames:
                out.write(frame)
                time.sleep(0.0005) # ป้องกัน CPU 100%
            
            out.release()

            # 4. ตรวจสอบไฟล์และส่ง
            if os.path.exists(self.video_path) and os.path.getsize(self.video_path) > 0:
                size_mb = os.path.getsize(self.video_path) / (1024 * 1024)
                print(f" [VideoThread] บันทึกเสร็จสิ้น ({size_mb:.2f} MB) -> กำลังส่งเข้า Telegram...")
                self.bot.send_media(self.video_path, mode="video", caption=caption_text)
            else:
                print(" [VideoThread] ผิดพลาด: ไฟล์วิดีโอมีขนาด 0 หรือไม่ถูกสร้าง")

        except Exception as e:
            print(f" [VideoThread] Exception: {e}")

    def _send_immediate_task(self, snapshot_frame: 'np.ndarray', caption_text: str):
        print(" [AlertThread] เริ่มส่งข้อความและรูปภาพ...")

        try:
            if self.send_message:
                self.bot.send_message(f"{caption_text}")
                print(" [AlertThread] เริ่มส่งข้อความ (non-blocking)")

            if self.send_photo and snapshot_frame is not None:
                try:
                    cv2.imwrite(self.snapshot_path, snapshot_frame)
                    if os.path.exists(self.snapshot_path) and os.path.getsize(self.snapshot_path) > 0:
                        self.bot.send_media(self.snapshot_path, mode="photo", caption=caption_text)
                        print(" [AlertThread] เริ่มส่งรูปภาพ (non-blocking)")
                    else:
                        print(" [AlertThread] ไฟล์รูปภาพไม่ถูกสร้าง หรือมีขนาดเป็น 0")
                except Exception as e:
                    print(f" [AlertThread] เกิดข้อผิดพลาดในการส่งรูปภาพ: {e}")

        except Exception as e:
            print(f" [AlertThread] เกิดข้อผิดพลาด: {e}")

    def trigger_alert(self, snapshot_frame: 'np.ndarray', pre_buffer: deque, custom_text: str = None) -> bool:
        with self.alert_lock:
            current_time = time.time()
            if (current_time - self.last_alert_time < self.alert_cooldown_sec) or self.recording:
                return False

            self.last_alert_time = current_time
            print(" !!! ตรวจพบ !!! -> เริ่มระบบแจ้งเตือนและบันทึกวิดีโอ")

            text_to_send = custom_text if custom_text else self.alert_text
            self.current_alert_caption = text_to_send

            threading.Thread(
                target=self._send_immediate_task,
                args=(snapshot_frame.copy(), text_to_send),
                daemon=True,
            ).start()

            if not self.send_video:
                self.recording = False
                self.recording_frames = []
                self.frames_remaining = 0
                return True

            total_target = int(round(float(self.video_duration_sec) * float(self.video_fps)))
            if total_target <= 0:
                total_target = 1

            # บังคับให้มี post-event frames อย่างน้อย 1 วินาที (กันคลิปนิ่งจาก prebuffer)
            min_post_frames = int(round(float(self.video_fps) * 1.0))
            if min_post_frames < 1:
                min_post_frames = 1
            if min_post_frames >= total_target:
                min_post_frames = max(1, total_target - 1)

            pre_frames = self._extract_frames_from_prebuffer(pre_buffer, current_time)
            max_pre_frames = max(1, total_target - min_post_frames)
            if len(pre_frames) > max_pre_frames:
                pre_frames = pre_frames[-max_pre_frames:]

            self.recording_frames = list(pre_frames)
            self.frames_remaining = max(0, total_target - len(self.recording_frames))

            self.recording = True
            return True
import os
import asyncio
import threading
from telegram import Bot
from telegram.request import HTTPXRequest

class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id


    async def send_message_async(self, text: str):
        try:
            # สร้าง request config และ bot instance ใหม่สำหรับ loop นี้โดยเฉพาะ
            request_config = HTTPXRequest(read_timeout=60, write_timeout=60, connect_timeout=60)
            bot = Bot(token=self.token, request=request_config)
            async with bot:
                await bot.send_message(chat_id=self.chat_id, text=text)
            print("LOG: Successfully sent message")
        except Exception as e:
            print(f"LOG_ERROR: Failed to send message: {e}")

    async def send_media_async(self, file_path, mode="photo", caption=""):
        if not os.path.exists(file_path):
            print(f"LOG_ERROR: File not found: {file_path}")
            return

        try:
            # สร้าง request config และ bot instance ใหม่สำหรับ loop นี้โดยเฉพาะ
            # กำหนด Timeout เพื่อรองรับไฟล์วิดีโอขนาดใหญ่
            request_config = HTTPXRequest(read_timeout=60, write_timeout=60, connect_timeout=60)
            bot = Bot(token=self.token, request=request_config)
            async with bot:
                with open(file_path, 'rb') as f:
                    if mode.lower() == "video":
                        print(f"LOG: กำลังส่งวิดีโอ... (ขนาด: {os.path.getsize(file_path) / 1024 / 1024:.2f} MB)")
                        await bot.send_video(
                            chat_id=self.chat_id,
                            video=f,
                            caption=caption,
                            supports_streaming=True
                        )
                    else:
                        print(f"LOG: กำลังส่งรูปภาพ...")
                        await bot.send_photo(
                            chat_id=self.chat_id,
                            photo=f,
                            caption=caption
                        )
            print(f"LOG: Successfully sent {mode}")
        except Exception as e:
            print(f"LOG_ERROR: Failed to send {mode}: {e}")

    def _run_async_in_thread(self, coro):
        """รัน async function ใน thread แยกด้วย event loop ใหม่ (non-blocking)"""
        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(coro)
            except Exception as e:
                print(f"LOG_ERROR: Async thread error: {e}")
            finally:
                try:
                    # ปิด pending tasks
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
                finally:
                    loop.close()
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        return thread

    def send_media(self, file_path, mode="photo", caption=""):
        """ส่ง media แบบ non-blocking ใน thread แยก"""
        coro = self.send_media_async(file_path, mode, caption)
        self._run_async_in_thread(coro)

    def send_message(self, text: str):
        """ส่งข้อความแบบ non-blocking ใน thread แยก"""
        coro = self.send_message_async(text)
        self._run_async_in_thread(coro)
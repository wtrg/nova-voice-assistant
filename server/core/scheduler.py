import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import Optional, Callable

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apscheduler.schedulers.background import BackgroundScheduler
from core.database import (
    get_due_tasks, 
    update_task_status, 
    add_task, 
    snooze_task
)
from core.tts import tts_engine
from core.agent import assistant_agent
from core.os_control import open_application

logger = logging.getLogger("Scheduler")

class ProactiveScheduler:
    def __init__(self, on_user_input_request: Optional[Callable] = None):
        self.scheduler = BackgroundScheduler()
        self.on_user_input_request = on_user_input_request # Callback khi cần lắng nghe giọng nói phản hồi
        self.is_running = False

    def check_and_notify_tasks(self):
        """Hàm kiểm tra định kỳ các nhiệm vụ đến hạn"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        due_tasks = get_due_tasks(now_str)
        
        for task in due_tasks:
            logger.info(f"Phát hiện task đến hạn: {task['title']}")
            
            # Tạm thời cập nhật hoãn 10 phút để tránh bị nhắc liên tục trong cùng 1 phút
            next_snooze = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")
            snooze_task(task["id"], next_snooze)
            
            # Mở app nếu có cấu hình
            app_to_open = task.get("app_to_open")
            if app_to_open:
                open_application(app_to_open)
                
            # Kích hoạt chuỗi nhắc nhở chủ động + hỏi đuôi + đàm thoại liên tục
            try:
                from core.audio_pipeline import audio_pipeline
                audio_pipeline.handle_proactive_reminder(task)
            except Exception as e:
                logger.error(f"Lỗi khi thực hiện đàm thoại nhắc việc: {e}")


    def start(self):
        """Khởi động tiến trình kiểm tra lịch trình ngầm"""
        if not self.is_running:
            self.scheduler.add_job(
                self.check_and_notify_tasks, 
                'interval', 
                seconds=15, 
                id='check_due_tasks'
            )
            self.scheduler.start()
            self.is_running = True
            logger.info("Proactive Scheduler đã được khởi động.")

    def stop(self):
        """Dừng tiến trình scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Proactive Scheduler đã dừng.")

    def add_schedule(self, title: str, scheduled_time: str, app_to_open: str = "") -> int:
        """Hẹn lịch trình mới"""
        task_id = add_task(title=title, scheduled_time=scheduled_time, app_to_open=app_to_open)
        logger.info(f"Đã lên lịch thành công cho '{title}' vào lúc {scheduled_time}")
        return task_id

scheduler_engine = ProactiveScheduler()

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    print("Khởi động thử nghiệm Scheduler trong 5 giây...")
    scheduler_engine.start()
    time.sleep(2)
    scheduler_engine.stop()
    print("Thử nghiệm Scheduler thành công.")

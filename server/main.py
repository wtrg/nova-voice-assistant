import sys
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Đảm bảo mã hóa UTF-8 cho Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import USER_NAME, ASSISTANT_PERSONA, ASSISTANT_NAME, TTS_PROVIDER
from core.database import init_db, add_task, get_all_active_tasks, update_task_status
from core.scheduler import scheduler_engine
from core.agent import assistant_agent
from core.tts import tts_engine
from core.audio_pipeline import audio_pipeline

def print_banner():

    banner = f"""
========================================================================
   {ASSISTANT_NAME.upper()} - BẠN THÂN KỶ LUẬT & TRỢ LÝ GIỌNG NÓI CHỦ ĐỘNG
   * Hệ điều hành: Windows / Android Companion
   * Giọng nói: Cuppy Neural Voice (Saydi Cuppy)
   * Não bộ AI: Google Gemini 3.5 Flash Lite (Phong cách bạn thân)
   * Lắng nghe STT: Groq Whisper Large V3 | Đánh thức: 'Hey Nova'
========================================================================
"""
    print(banner)

def interactive_cli():
    """Giao diện dòng lệnh tương tác cho người dùng"""
    print("\nCác cách bạn có thể nói chuyện với Nova:")
    print(" 1. Gõ câu nói tự nhiên (VD: 'Nova ơi tớ lười quá', 'Mở Chrome giúp tớ')")
    print(" 2. 'nhắc nhở t đi ăn vào 1 phút nữa' hoặc 'add Viết_báo_cáo 1 code'")
    print(" 3. 'tasks' để xem toàn bộ danh sách việc cần làm")
    print(" 4. 'voice' để nói trực tiếp qua Micro (Groq Whisper nhận diện)")
    print(" 5. 'listen' để bật chế độ ngầm nghe Wake-word ('Hey Nova')")
    print(" 6. 'quit' hoặc 'exit' để dừng ứng dụng\n")


    while True:
        try:
            user_input = input(f"[{USER_NAME}] > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit"]:
                print("Đang dừng trợ lý ảo... Hẹn gặp lại bạn!")
                scheduler_engine.stop()
                break

            elif user_input.lower() == "tasks":
                tasks = get_all_active_tasks()
                if not tasks:
                    print("[INFO] Hiện không có nhiệm vụ nào đang chờ.")
                else:
                    print(f"\n--- DANH SÁCH NHIỆM VỤ ({len(tasks)}) ---")
                    for t in tasks:
                        app_info = f" (Mở kèm: {t['app_to_open']})" if t['app_to_open'] else ""
                        print(f" • [ID {t['id']}] {t['title']} | Giờ: {t['scheduled_time']}{app_info} | Trạng thái: {t['status']}")
                    print("--------------------------------\n")

            elif user_input.lower().startswith("add "):
                import shlex
                try:
                    parts = shlex.split(user_input)
                    if len(parts) >= 3:
                        title = parts[1]
                        mins = int(parts[2])
                        app = parts[3] if len(parts) > 3 else ""
                        due_time = (datetime.now() + timedelta(minutes=mins)).strftime("%Y-%m-%d %H:%M")
                        task_id = add_task(title=title, scheduled_time=due_time, app_to_open=app)
                        msg = f"Đã lên lịch '{title}' sau {mins} phút nữa (lúc {due_time})."
                        print(f"[THÀNH CÔNG] {msg}")
                        tts_engine.speak(f"Đã lên lịch {title} sau {mins} phút nữa cho cậu rồi nhé!")
                    else:
                        print("[LỖI] Cú pháp: add <tên_việc> <số_phút> [tên_app] (Ví dụ: add \"Lập trình\" 1 notepad)")
                except Exception as e:
                    print(f"[LỖI] Cú pháp không hợp lệ: {e}. Ví dụ đúng: add \"Lập trình\" 1 notepad")


            elif user_input.lower() == "voice":
                print("[INFO] Đang mở Microphone để lắng nghe câu lệnh...")
                audio_pipeline.trigger_conversation()

            elif user_input.lower() == "listen":
                print("[INFO] Khởi động vòng lặp Wake Word ngầm. Nói 'Hey Jarvis' để đánh thức...")
                t = threading.Thread(target=audio_pipeline.start_wake_word_listener, daemon=True)
                t.start()

            else:
                # Xử lý ngôn ngữ tự nhiên thông qua AI Agent
                reply, action = assistant_agent.process_command(user_input)
                print(f"[TRỢ LÝ]: {reply}")
                if action.get("action") != "none":
                    print(f"[HÀNH ĐỘNG]: {action}")
                
                # Phát âm thanh trả lời
                tts_engine.speak(reply, wait_until_done=False)

        except (KeyboardInterrupt, EOFError):
            scheduler_engine.stop()
            break

def main():
    # 1. Khởi tạo Database
    init_db()
    
    # 2. Bật Scheduler kiểm tra lịch trình định kỳ
    scheduler_engine.start()
    
    # 3. In thông tin
    print_banner()
    
    # 4. Chạy CLI tương tác
    interactive_cli()

if __name__ == "__main__":
    main()

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Cấu hình UTF-8 cho Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.database import init_db, add_task, get_due_tasks, update_task_status, get_all_active_tasks
from core.agent import assistant_agent
from core.os_control import open_application
from core.tts import tts_engine

def test_full_pipeline():
    print("=== BẮT ĐẦU KIỂM THỬ TOÀN BỘ PIPELINE CỦA TRỢ LÝ ===")
    
    # 1. Khởi tạo DB
    print("\n[BƯỚC 1]: Khởi tạo cơ sở dữ liệu SQLite...")
    init_db()
    print("  -> Thành công.")

    # 2. Kiểm tra tạo lịch trình chủ động
    print("\n[BƯỚC 2]: Thử nghiệm lên lịch trình chủ động...")
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    task_id = add_task(
        title="Lập trình dự án AI", 
        scheduled_time=now_time, 
        description="Viết code core module",
        app_to_open="notepad"
    )
    print(f"  -> Đã tạo task ID {task_id} đến hạn lúc {now_time}")
    
    # Lấy task đến hạn
    due = get_due_tasks(now_time)
    assert len(due) > 0, "Không tìm thấy task đến hạn!"
    print(f"  -> Phát hiện {len(due)} task cần nhắc nhở.")

    # 3. Kiểm tra Não bộ sinh lời thoại nhắc nhở đôn đốc
    print("\n[BƯỚC 3]: Kiểm tra AI sinh lời thoại đôn đốc nhắc nhở (Proactive Voice Prompt)...")
    prompt = assistant_agent.generate_proactive_prompt(due[0])
    print(f"  -> Lời thoại đôn đốc: '{prompt}'")
    assert len(prompt) > 0

    # 4. Kiểm tra xử lý phản hồi từ chối / xin hoãn giờ của người dùng
    print("\n[BƯỚC 4]: Kiểm tra phản hồi tâm lý khi người dùng xin hoãn giờ...")
    reply_snooze, act_snooze = assistant_agent.process_command("Tớ mệt quá cho hoãn 10 phút nữa đi", current_task=due[0])
    print(f"  -> Người dùng: 'Tớ mệt quá cho hoãn 10 phút nữa đi'")
    print(f"  -> Trợ lý trả lời: '{reply_snooze}'")
    print(f"  -> Hành động ghi nhận: {act_snooze}")
    assert act_snooze["action"] == "snooze"

    # 5. Kiểm tra lệnh mở ứng dụng bằng ngôn ngữ tự nhiên
    print("\n[BƯỚC 5]: Kiểm tra lệnh mở ứng dụng bằng giọng nói...")
    reply_app, act_app = assistant_agent.process_command("Mở notepad lên giúp tớ với nào")
    print(f"  -> Người dùng: 'Mở notepad lên giúp tớ với nào'")
    print(f"  -> Trợ lý trả lời: '{reply_app}'")
    print(f"  -> Hành động: {act_app}")
    assert act_app["action"] == "open_app"

    # 6. Kiểm tra hoàn thành task
    print("\n[BƯỚC 6]: Kiểm tra báo cáo hoàn thành nhiệm vụ...")
    reply_done, act_done = assistant_agent.process_command("Tớ đã làm xong rồi nhé!", current_task=due[0])
    print(f"  -> Người dùng: 'Tớ đã làm xong rồi nhé!'")
    print(f"  -> Trợ lý trả lời: '{reply_done}'")
    print(f"  -> Hành động: {act_done}")
    assert act_done["action"] == "complete_task"

    # 7. Kiểm tra sinh âm thanh giọng nói (TTS)
    print("\n[BƯỚC 7]: Kiểm tra phát giọng nói qua Loa...")
    tts_engine.speak("Kiểm thử hệ thống thành công! Mọi thứ đã sẵn sàng phục vụ bạn.", wait_until_done=True)
    print("  -> Đã phát giọng nói thành công!")

    print("\n=== TOÀN BỘ CÁC BƯỚC KIỂM THỬ ĐÃ THÀNH CÔNG RỰC RỠ! ===")

if __name__ == "__main__":
    test_full_pipeline()

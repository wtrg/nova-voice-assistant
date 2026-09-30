import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import DB_PATH


def init_db():
    """Khởi tạo các bảng cơ sở dữ liệu nếu chưa tồn tại"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Bảng lưu trữ nhiệm vụ và lịch trình nhắc nhở
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        scheduled_time TEXT NOT NULL, -- Định dạng YYYY-MM-DD HH:MM
        status TEXT DEFAULT 'pending', -- pending, completed, snoozed, cancelled
        recurrence TEXT DEFAULT 'none', -- none, daily, weekdays, weekly
        app_to_open TEXT, -- Tên ứng dụng mở kèm (vd: 'code', 'chrome', 'excel')
        snooze_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Bảng ghi nhật ký đôn đốc & lý do hoãn (phục vụ AI phân tích tâm lý)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interaction_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        user_response TEXT,
        ai_reply TEXT,
        action_taken TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )
    """)

    conn.commit()
    conn.close()

def add_task(title: str, scheduled_time: str, description: str = "", app_to_open: str = "", recurrence: str = "none") -> int:
    """Thêm một nhiệm vụ nhắc nhở mới"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO tasks (title, description, scheduled_time, app_to_open, recurrence)
    VALUES (?, ?, ?, ?, ?)
    """, (title, description, scheduled_time, app_to_open, recurrence))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_due_tasks(current_time_str: str) -> List[Dict[str, Any]]:
    """Lấy danh sách các task đến hạn cần nhắc nhở"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM tasks 
    WHERE status IN ('pending', 'snoozed') AND scheduled_time <= ?
    ORDER BY scheduled_time ASC
    """, (current_time_str,))
    rows = cursor.fetchall()
    tasks = [dict(row) for row in rows]
    conn.close()
    return tasks

def update_task_status(task_id: int, status: str):
    """Cập nhật trạng thái nhiệm vụ (completed, snoozed, cancelled)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    conn.commit()
    conn.close()

def snooze_task(task_id: int, new_scheduled_time: str):
    """Hoãn nhiệm vụ sang một mốc giờ mới và tăng biến đếm hoãn"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tasks 
    SET scheduled_time = ?, status = 'snoozed', snooze_count = snooze_count + 1 
    WHERE id = ?
    """, (new_scheduled_time, task_id))
    conn.commit()
    conn.close()

def log_interaction(task_id: Optional[int], user_response: str, ai_reply: str, action_taken: str):
    """Lưu lại lịch sử đối thoại giữa người dùng và trợ lý"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO interaction_logs (task_id, user_response, ai_reply, action_taken)
    VALUES (?, ?, ?, ?)
    """, (task_id, user_response, ai_reply, action_taken))
    conn.commit()
    conn.close()

def get_all_active_tasks() -> List[Dict[str, Any]]:
    """Lấy toàn bộ các task đang chờ hoặc bị hoãn"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE status IN ('pending', 'snoozed') ORDER BY scheduled_time ASC")
    rows = cursor.fetchall()
    tasks = [dict(row) for row in rows]
    conn.close()
    return tasks

# Khởi tạo database khi import
init_db()

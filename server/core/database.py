import sys
import uuid
import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


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
        status TEXT DEFAULT 'pending', -- pending, completed, snoozed, cancelled, device_schedule_failed
        recurrence TEXT DEFAULT 'none', -- none, daily, weekdays, weekly
        app_to_open TEXT, -- Tên ứng dụng mở kèm (vd: 'code', 'chrome', 'excel')
        snooze_count INTEGER DEFAULT 0,
        reminder_id TEXT, -- Canonical reminder ID UUID
        scheduling_status TEXT DEFAULT 'pending_device_ack', -- pending_device_ack, confirmed, device_schedule_failed
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Safe migration: bổ sung cột reminder_id và scheduling_status nếu database đã tồn tại từ trước
    cursor.execute("PRAGMA table_info(tasks)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    if "reminder_id" not in existing_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN reminder_id TEXT")
    if "scheduling_status" not in existing_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN scheduling_status TEXT DEFAULT 'pending_device_ack'")

    # Safe migration Stage 9: Deduplicate existing reminder_ids before unique index creation
    cursor.execute("""
    SELECT reminder_id, COUNT(*) FROM tasks 
    WHERE reminder_id IS NOT NULL 
    GROUP BY reminder_id HAVING COUNT(*) > 1
    """)
    duplicate_rows = cursor.fetchall()
    for row in duplicate_rows:
        dup_rem_id = row[0]
        cursor.execute("SELECT id FROM tasks WHERE reminder_id = ? ORDER BY id ASC", (dup_rem_id,))
        task_ids = [t[0] for t in cursor.fetchall()]
        for tid in task_ids[1:]:
            new_uuid = str(uuid.uuid4())
            cursor.execute("UPDATE tasks SET reminder_id = ? WHERE id = ?", (new_uuid, tid))

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_reminder_id
    ON tasks(reminder_id)
    WHERE reminder_id IS NOT NULL
    """)

    # Bảng lưu trữ các lượt đã xử lý để đảm bảo idempotency (V3.1 Stage 6 & 7, V3.2 P0-04, P0-05)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_turns (
        session_id TEXT NOT NULL,
        turn_id TEXT NOT NULL,
        request_hash TEXT NOT NULL,
        status TEXT NOT NULL, -- 'processing', 'completed', 'failed'
        response_json TEXT,
        processing_started_at TEXT DEFAULT CURRENT_TIMESTAMP,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        attempt_count INTEGER DEFAULT 1,
        PRIMARY KEY (session_id, turn_id)
    )
    """)

    # Non-destructive migration cho bảng processed_turns
    cursor.execute("PRAGMA table_info(processed_turns)")
    pt_cols = [c[1] for c in cursor.fetchall()]
    if "processing_started_at" not in pt_cols:
        cursor.execute("ALTER TABLE processed_turns ADD COLUMN processing_started_at TEXT DEFAULT NULL")
    if "attempt_count" not in pt_cols:
        cursor.execute("ALTER TABLE processed_turns ADD COLUMN attempt_count INTEGER DEFAULT 1")


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

def add_task(title: str, scheduled_time: str, description: str = "", app_to_open: str = "", recurrence: str = "none", reminder_id: Optional[str] = None, scheduling_status: str = "pending_device_ack") -> int:
    """Thêm một nhiệm vụ nhắc nhở mới với canonical reminder_id"""
    import uuid
    if not reminder_id:
        reminder_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO tasks (title, description, scheduled_time, app_to_open, recurrence, reminder_id, scheduling_status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, description, scheduled_time, app_to_open, recurrence, reminder_id, scheduling_status))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def add_tasks_atomic(tasks_data: List[Dict[str, Any]]) -> List[int]:
    """Thêm danh sách nhiệm vụ theo transaction nguyên tử: nếu một task lỗi, rollback toàn bộ."""
    if not tasks_data:
        return []
    import uuid
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    created_ids = []
    try:
        for t in tasks_data:
            r_id = t.get("reminder_id") or str(uuid.uuid4())
            sched_status = t.get("scheduling_status") or "pending_device_ack"
            cursor.execute("""
            INSERT INTO tasks (title, description, scheduled_time, app_to_open, recurrence, reminder_id, scheduling_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                t.get("title", "Nhiệm vụ"),
                t.get("description", ""),
                t.get("scheduled_time", ""),
                t.get("app_to_open", ""),
                t.get("recurrence", "none"),
                r_id,
                sched_status
            ))
            created_ids.append(cursor.lastrowid)
        conn.commit()
        return created_ids
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def update_task_device_ack(reminder_id: str, status: str, error: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Cập nhật trạng thái device ACK (confirmed hoặc device_schedule_failed) (P1-03).
    Bảng chuyển trạng thái:
    - pending_device_ack -> confirmed (hợp lệ)
    - pending_device_ack -> device_schedule_failed (hợp lệ)
    - confirmed -> confirmed (idempotent 200 OK)
    - confirmed -> device_schedule_failed (bất hợp lệ -> từ chối, trả về lỗi conflict)
    - device_schedule_failed -> device_schedule_failed (idempotent 200 OK)
    - device_schedule_failed -> confirmed (cho phép khôi phục khi thiết bị thử lại thành công)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT scheduling_status FROM tasks
    WHERE reminder_id = ? OR CAST(id AS TEXT) = ?
    """, (reminder_id, reminder_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return (False, "not_found")

    current_status = row[0]
    if current_status == "confirmed":
        if status == "confirmed":
            conn.close()
            return (True, "already_confirmed")
        elif status == "device_schedule_failed":
            conn.close()
            return (False, "invalid_transition_from_confirmed")

    if current_status == "device_schedule_failed" and status == "device_schedule_failed":
        conn.close()
        return (True, "already_failed")

    if status == "device_schedule_failed":
        cursor.execute("""
        UPDATE tasks 
        SET scheduling_status = ?, status = 'device_schedule_failed' 
        WHERE reminder_id = ? OR CAST(id AS TEXT) = ?
        """, (status, reminder_id, reminder_id))
    else:
        cursor.execute("""
        UPDATE tasks 
        SET scheduling_status = ? 
        WHERE reminder_id = ? OR CAST(id AS TEXT) = ?
        """, (status, reminder_id, reminder_id))

    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return (updated, None)


def get_due_tasks(current_time_str: str) -> List[Dict[str, Any]]:
    """Lấy danh sách các task đến hạn cần nhắc nhở (bỏ qua các task lỗi phần cứng)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM tasks 
    WHERE status IN ('pending', 'snoozed') AND (scheduling_status IS NULL OR scheduling_status != 'device_schedule_failed') AND scheduled_time <= ?
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
    """Lấy toàn bộ các task đang chờ hoặc bị hoãn (bỏ qua task lỗi phần cứng)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE status IN ('pending', 'snoozed') AND (scheduling_status IS NULL OR scheduling_status != 'device_schedule_failed') ORDER BY scheduled_time ASC")
    rows = cursor.fetchall()
    tasks = [dict(row) for row in rows]
    conn.close()
    return tasks

def get_task_by_reminder_id(reminder_id: str) -> Optional[Dict[str, Any]]:
    """Tìm một task theo canonical reminder_id hoặc numeric ID"""
    if not reminder_id:
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE reminder_id = ? OR CAST(id AS TEXT) = ?", (reminder_id, reminder_id))
    row = cursor.fetchone()
    task = dict(row) if row else None
    conn.close()
    return task

def compute_request_hash(endpoint: str, session_id: str, turn_id: str, user_text: str = "", in_conversation: bool = False, generate_audio: bool = False, **extra) -> str:
    """Tạo SHA-256 fingerprint chuẩn hóa cho truy vấn đàm thoại / chat (P0-07)"""
    normalized = {
        "endpoint": str(endpoint).strip(),
        "session_id": str(session_id).strip(),
        "turn_id": str(turn_id).strip(),
        "user_text": str(user_text).strip(),
        "in_conversation": bool(in_conversation),
        "generate_audio": bool(generate_audio)
    }
    for k, v in sorted(extra.items()):
        if isinstance(v, str):
            normalized[k] = v.strip()
        elif isinstance(v, bool):
            normalized[k] = bool(v)
        else:
            normalized[k] = v
    raw = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def claim_turn(session_id: str, turn_id: str, request_hash: str, lease_seconds: int = 60) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Xác nhận quyền thực thi turn_id một cách an toàn và chống race-condition (V3.2 P0-04 & P0-05):
    - Trả về ("claimed", None): Lượt này độc quyền thực thi side-effect.
    - Trả về ("completed", response_data): Lượt đã xử lý trước đó -> Replay chính xác kết quả cũ.
    - Trả về ("mismatch", None): Cùng turn_id nhưng request payload khác -> HTTP 409 Conflict.
    - Trả về ("processing", None): Đang có luồng khác chạy cùng turn_id (hoặc lease chưa hết hạn).
    - Thử lại sau khi thất bại: chuyển trạng thái failed -> processing bằng atomic compare-and-swap.
    - Hết hạn lease (backend crash): atomic reclaim phiên xử lý bị kẹt.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO processed_turns (session_id, turn_id, request_hash, status, processing_started_at, updated_at, attempt_count)
        VALUES (?, ?, ?, 'processing', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
        """, (session_id, turn_id, request_hash))
        conn.commit()
        return ("claimed", None)
    except sqlite3.IntegrityError:
        cursor.execute("""
        SELECT status, request_hash, response_json, updated_at, attempt_count,
               (strftime('%s', 'now') - strftime('%s', updated_at)) AS age_sec
        FROM processed_turns
        WHERE session_id = ? AND turn_id = ?
        """, (session_id, turn_id))
        row = cursor.fetchone()
        if not row:
            return ("failed", None)
        status, stored_hash, response_json, updated_at, attempt_count, age_sec = row
        if stored_hash != request_hash:
            return ("mismatch", None)

        if status == "completed" and response_json:
            try:
                return ("completed", json.loads(response_json))
            except Exception:
                return ("completed", None)

        if status == "failed":
            # P0-04: Atomic compare-and-swap: FAILED -> PROCESSING
            cursor.execute("""
            UPDATE processed_turns
            SET status = 'processing', updated_at = CURRENT_TIMESTAMP, attempt_count = attempt_count + 1
            WHERE session_id = ? AND turn_id = ? AND status = 'failed'
            """, (session_id, turn_id))
            conn.commit()
            if cursor.rowcount == 1:
                return ("claimed", None)
            return ("processing", None)

        if status == "processing":
            # P0-05: Kiểm tra lease timeout (crash recovery)
            age = age_sec if (age_sec is not None) else 0
            if age > lease_seconds:
                cursor.execute("""
                UPDATE processed_turns
                SET status = 'processing', updated_at = CURRENT_TIMESTAMP, attempt_count = attempt_count + 1
                WHERE session_id = ? AND turn_id = ? AND status = 'processing'
                  AND (strftime('%s', 'now') - strftime('%s', updated_at)) > ?
                """, (session_id, turn_id, lease_seconds))
                conn.commit()
                if cursor.rowcount == 1:
                    return ("claimed", None)
            return ("processing", None)

        return ("failed", None)
    finally:
        conn.close()


def complete_turn(session_id: str, turn_id: str, response_data: Dict[str, Any]):
    """Ghi nhận lượt đã hoàn tất kèm response chuẩn hóa để replay khi retry (Stage 7)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE processed_turns
    SET status = 'completed', response_json = ?, updated_at = CURRENT_TIMESTAMP
    WHERE session_id = ? AND turn_id = ?
    """, (json.dumps(response_data), session_id, turn_id))
    conn.commit()
    conn.close()

def fail_turn(session_id: str, turn_id: str):
    """Đánh dấu lượt thất bại để cho phép thử lại nếu cần"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE processed_turns
    SET status = 'failed', updated_at = CURRENT_TIMESTAMP
    WHERE session_id = ? AND turn_id = ?
    """, (session_id, turn_id))
    conn.commit()
    conn.close()

# Khởi tạo database khi import
init_db()

import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from core.agent import Agent
from core.database import init_db
from config import DB_PATH

def test_atomic_schedule_valid_plus_invalid_inserts_zero_tasks():
    """
    Kỳ vọng: Nếu Gemini trả về 1 task hợp lệ và 1 task không parse được thời gian,
    hệ thống phải trả về schedule_requires_clarification và DB delta PHẢI BẰNG 0.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tasks")
    initial_count = cur.fetchone()[0]
    conn.close()

    agent = Agent()
    agent.gemini_key = "dummy_key_for_mock"

    # Giả lập phản hồi từ Gemini với 1 task hợp lệ và 1 task thời gian vô nghĩa
    mock_candidate = {
        "content": {
            "parts": [
                {
                    "functionCall": {
                        "name": "schedule_tasks",
                        "args": {
                            "tasks": [
                                {"title": "Task A Hop Le", "scheduled_time": "14:30"},
                                {"title": "Task B Khong Hop Le", "scheduled_time": "thời gian mơ hồ vô định"}
                            ]
                        }
                    }
                }
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"candidates": [mock_candidate]}

    with patch("requests.post", return_value=mock_resp):
        reply, action = agent._call_gemini_chat("Đặt lịch cho tớ")

    assert action["type"] == "schedule_requires_clarification"
    assert action["action"] == "schedule_requires_clarification"
    assert action["task_title"] == "Task B Khong Hop Le"

    # Kiểm tra số lượng bản ghi trong database: PHẢI HOÀN TOÀN KHÔNG ĐỔI
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tasks")
    final_count = cur.fetchone()[0]
    conn.close()

    assert final_count == initial_count, f"Delta phải bằng 0 nhưng ban đầu {initial_count}, kết thúc {final_count}"

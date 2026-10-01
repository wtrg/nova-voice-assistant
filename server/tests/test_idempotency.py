import sys
import uuid
import sqlite3
import concurrent.futures
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from server import app
from config import DB_PATH
import core.database as db

client = TestClient(app)

def test_same_turn_retry_returns_exact_same_response_and_single_side_effect():
    """
    Stage 6 & 7: Same session_id + turn_id + request payload returns original response
    and executes side-effects (e.g. reminder DB insertion) at most once.
    """
    session_id = f"session_idem_{uuid.uuid4().hex[:8]}"
    turn_id = f"turn_idem_{uuid.uuid4().hex[:8]}"
    unique_title = f"Học bài buổi tối {uuid.uuid4().hex[:6]}"

    from unittest.mock import MagicMock
    from core.agent import assistant_agent

    assistant_agent.gemini_key = "dummy_key_for_test"

    mock_candidate = {
        "content": {
            "parts": [
                {
                    "functionCall": {
                        "name": "schedule_tasks",
                        "args": {
                            "tasks": [
                                {"title": unique_title, "scheduled_time": "14:30"}
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

    payload = {
        "user_text": f"Nhắc tôi {unique_title} lúc 14h30",
        "in_conversation": False,
        "session_id": session_id,
        "turn_id": turn_id,
        "generate_audio": False
    }

    with patch("requests.post", return_value=mock_resp):
        # First request
        res1 = client.post("/api/dialogue", json=payload)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["turn_id"] == turn_id

        # Second request (retry of same turn)
        res2 = client.post("/api/dialogue", json=payload)
        assert res2.status_code == 200
        data2 = res2.json()

        # Responses must be completely identical
        assert data1 == data2

    # Verify side effect (database tasks) happened EXACTLY ONCE
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE title = ?", (unique_title,))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1, f"Expected exactly 1 task in database, found {count}"

def test_same_turn_different_payload_returns_409():
    """
    Stage 6: Different payload reusing same turn ID must be rejected with HTTP 409 Conflict
    """
    session_id = f"session_mismatch_{uuid.uuid4().hex[:8]}"
    turn_id = f"turn_mismatch_{uuid.uuid4().hex[:8]}"

    payload1 = {
        "user_text": "Bật đèn phòng khách",
        "session_id": session_id,
        "turn_id": turn_id
    }
    payload2 = {
        "user_text": "Tắt điều hòa",
        "session_id": session_id,
        "turn_id": turn_id
    }

    res1 = client.post("/api/dialogue", json=payload1)
    assert res1.status_code == 200

    res2 = client.post("/api/dialogue", json=payload2)
    assert res2.status_code == 409
    assert "Turn ID already used with different payload" in res2.json()["error"]

def test_concurrent_duplicate_requests_single_execution():
    """
    Stage 8: Two requests with the same ID arriving concurrently:
    only one owns execution, both safely handle the turn without duplicate side effects.
    """
    session_id = f"session_race_{uuid.uuid4().hex[:8]}"
    turn_id = f"turn_race_{uuid.uuid4().hex[:8]}"
    race_title = f"Nhiệm vụ đua {uuid.uuid4().hex[:6]}"

    from unittest.mock import MagicMock
    from core.agent import assistant_agent
    assistant_agent.gemini_key = "dummy_key_for_test"

    mock_candidate = {
        "content": {
            "parts": [
                {
                    "functionCall": {
                        "name": "schedule_tasks",
                        "args": {
                            "tasks": [
                                {"title": race_title, "scheduled_time": "15:00"}
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

    payload = {
        "user_text": f"Lên lịch {race_title} lúc 15h",
        "session_id": session_id,
        "turn_id": turn_id,
        "generate_audio": False
    }

    def send_req():
        with patch("requests.post", return_value=mock_resp):
            return client.post("/api/dialogue", json=payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(send_req)
        future2 = executor.submit(send_req)
        res1 = future1.result()
        res2 = future2.result()

    statuses = [res1.status_code, res2.status_code]
    assert 200 in statuses, f"At least one request must succeed, got {statuses}"
    for s in statuses:
        assert s in [200, 409], f"Unexpected status code {s}"

    # Side-effects in database MUST be exactly 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE title = ?", (race_title,))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1, f"Concurrent identical requests must produce exactly 1 task, found {count}"

def test_sqlite_unique_reminder_id_constraint():
    """
    Stage 9: Unique index enforces that identical reminder_id cannot be inserted twice
    """
    unique_rem_id = f"unique_rem_{uuid.uuid4().hex}"
    
    # First insert
    tid1 = db.add_task("Unique Task 1", "2026-10-02 09:00", reminder_id=unique_rem_id)
    assert tid1 > 0

    # Second insert with same reminder_id must fail
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO tasks (title, scheduled_time, reminder_id)
        VALUES ('Unique Task 2', '2026-10-02 09:00', ?)
        """, (unique_rem_id,))
        conn.commit()
        assert False, "SQLite must enforce UNIQUE constraint on reminder_id"
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

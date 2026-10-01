import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import app
from core.database import (
    add_tasks_atomic,
    get_due_tasks,
    get_all_active_tasks,
    update_task_device_ack
)

client = TestClient(app)

def test_turn_id_preserved_when_provided_by_client():
    """Stage 5 Invariant: client turn_id survives round trip through dialogue and chat"""
    client_turn_id_dialogue = f"turn-client-uuid-{uuid.uuid4().hex[:8]}"
    
    # Test /api/dialogue
    payload_dialogue = {
        "user_text": "tạm biệt, tắt mic đi",
        "in_conversation": True,
        "session_id": "test_turn_session",
        "turn_id": client_turn_id_dialogue
    }
    res_dialogue = client.post("/api/dialogue", json=payload_dialogue)
    assert res_dialogue.status_code == 200
    data_dialogue = res_dialogue.json()
    assert data_dialogue["turn_id"] == client_turn_id_dialogue, "Backend must echo back client turn_id"

    # Idempotency: same payload returns exact same response
    res_dialogue_replay = client.post("/api/dialogue", json=payload_dialogue)
    assert res_dialogue_replay.status_code == 200
    assert res_dialogue_replay.json() == data_dialogue

    # Mismatched payload reusing same turn ID must return 409
    res_mismatch = client.post("/api/dialogue", json={
        "user_text": "câu nói khác hoàn toàn",
        "in_conversation": True,
        "session_id": "test_turn_session",
        "turn_id": client_turn_id_dialogue
    })
    assert res_mismatch.status_code == 409

    # Test /api/chat with distinct turn ID
    client_turn_id_chat = f"turn-client-uuid-{uuid.uuid4().hex[:8]}"
    res_chat = client.post("/api/chat", json={
        "text": "mở youtube",
        "session_id": "test_turn_session",
        "turn_id": client_turn_id_chat
    })
    assert res_chat.status_code == 200
    data_chat = res_chat.json()
    assert data_chat["turn_id"] == client_turn_id_chat, "Backend must echo back client turn_id in chat"

def test_canonical_reminder_id_persisted_and_device_ack_confirmed():
    """Stage 8 & Stage 9: canonical reminder_id persisted in DB and confirmed via device ACK"""
    canonical_id = f"rem_{uuid.uuid4().hex[:12]}"
    task_payload = [{
        "reminder_id": canonical_id,
        "title": "Học bài giải tích",
        "scheduled_time": "2099-01-01 08:00",
        "app_to_open": "",
        "scheduling_status": "pending_device_ack"
    }]
    created_ids = add_tasks_atomic(task_payload)
    assert len(created_ids) == 1

    # Verify task in active tasks has reminder_id and pending_device_ack
    all_tasks = get_all_active_tasks()
    found = [t for t in all_tasks if t.get("reminder_id") == canonical_id]
    assert len(found) == 1
    assert found[0]["scheduling_status"] == "pending_device_ack"

    # Dispatch confirmed ACK via HTTP endpoint
    ack_res = client.post(f"/api/reminders/{canonical_id}/device-ack", json={
        "status": "confirmed"
    })
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["ok"] is True
    assert ack_data["status"] == "confirmed"
    assert ack_data["updated"] is True

    # Check that database now has confirmed
    all_tasks_after = get_all_active_tasks()
    found_after = [t for t in all_tasks_after if t.get("reminder_id") == canonical_id]
    assert len(found_after) == 1
    assert found_after[0]["scheduling_status"] == "confirmed"

def test_device_ack_failure_marks_task_failed_and_excluded_from_due():
    """Stage 9: Native scheduling failure excludes reminder from active due reminders"""
    canonical_id = f"rem_fail_{uuid.uuid4().hex[:12]}"
    task_payload = [{
        "reminder_id": canonical_id,
        "title": "Uống nước lọc",
        "scheduled_time": "2000-01-01 08:00",  # past due
        "app_to_open": "",
        "scheduling_status": "pending_device_ack"
    }]
    add_tasks_atomic(task_payload)

    # Dispatch failed ACK
    ack_res = client.post(f"/api/reminders/{canonical_id}/device-ack", json={
        "status": "device_schedule_failed",
        "error": "Exact alarm denied by system policy"
    })
    assert ack_res.status_code == 200
    assert ack_res.json()["updated"] is True

    # Failed tasks must NOT appear in due tasks or active tasks
    due = get_due_tasks("2099-12-31 23:59")
    failed_due = [t for t in due if t.get("reminder_id") == canonical_id]
    assert len(failed_due) == 0, "Failed native schedule must not be delivered as due reminder"

    active = get_all_active_tasks()
    failed_active = [t for t in active if t.get("reminder_id") == canonical_id]
    assert len(failed_active) == 0, "Failed native schedule must not remain in active tasks"

def test_device_ack_endpoint_validations():
    """Stage 11: Server endpoint must validate status (422) and unknown reminder (404)"""
    # 1. Invalid status returns 422
    res_invalid_status = client.post("/api/reminders/some-valid-id/device-ack", json={
        "status": "arbitrary_unknown_status"
    })
    assert res_invalid_status.status_code == 422

    # 2. Unknown reminder returns 404
    non_existent_id = f"non-existent-rem-{uuid.uuid4().hex}"
    res_not_found = client.post(f"/api/reminders/{non_existent_id}/device-ack", json={
        "status": "confirmed"
    })
    assert res_not_found.status_code == 404
    assert res_not_found.json()["error"] == "Reminder not found"

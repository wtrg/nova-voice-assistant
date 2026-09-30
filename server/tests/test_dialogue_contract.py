import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import app

client = TestClient(app)

def test_dialogue_contract_exit_conversation():
    response = client.post("/api/dialogue", json={
        "user_text": "tạm biệt, tắt mic đi",
        "in_conversation": True,
        "session_id": "test_session_1"
    })
    assert response.status_code == 200
    data = response.json()
    
    assert "turn_id" in data
    assert uuid.UUID(data["turn_id"])
    assert "reply" in data
    assert "action" in data
    assert isinstance(data["action"], dict)
    assert data["action"]["type"] == "exit_conversation"
    assert data["continue_listening"] is False

def test_dialogue_contract_agree_conversation():
    response = client.post("/api/dialogue", json={
        "user_text": "có, nói chuyện với tớ đi",
        "in_conversation": False,
        "session_id": "test_session_2"
    })
    assert response.status_code == 200
    data = response.json()
    
    assert "turn_id" in data
    assert uuid.UUID(data["turn_id"])
    assert "reply" in data
    assert isinstance(data["action"], dict)
    assert data["action"]["type"] == "start_conversation"
    assert data["continue_listening"] is True

def test_chat_contract_returns_turn_id_and_dict_action():
    response = client.post("/api/chat", json={
        "text": "mở youtube",
        "session_id": "test_session_3"
    })
    assert response.status_code == 200
    data = response.json()
    
    assert "turn_id" in data
    assert uuid.UUID(data["turn_id"])
    assert "reply" in data
    assert "action" in data
    assert isinstance(data["action"], dict)
    assert data["action"]["action"] == "open_app"
    assert data["action"]["target"] == "youtube"

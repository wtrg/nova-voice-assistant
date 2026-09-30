import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import app

client = TestClient(app)

def test_health_voice_endpoint():
    response = client.get("/health/voice")
    # Status code can be 200 or 503 depending on model availability, but must return valid JSON structure
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "model_loaded" in data
    assert "cache_writable" in data

def test_cuppy_tts_empty_validation():
    response = client.get("/api/cuppy-tts?text=")
    assert response.status_code == 400
    assert "Text is required" in response.text

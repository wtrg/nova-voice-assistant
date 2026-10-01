import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import app
from config import SERVER_VERSION, MIN_CLIENT_VERSION

client = TestClient(app)

def test_health_ready_contract():
    """V4-01 & V4-02: GET /health/ready returns comprehensive readiness status"""
    res = client.get("/health/ready")
    assert res.status_code in (200, 503)
    data = res.json()
    assert "ok" in data
    assert "version" in data
    assert "server_version" in data
    assert "min_client_version" in data
    assert "llm" in data
    assert "tts" in data
    assert "database" in data
    assert "tts_primary" in data
    assert "tts_primary_ready" in data
    assert "tts_fallback_ready" in data
    assert data["version"] == SERVER_VERSION
    assert data["database"] is True

def test_version_handshake_headers():
    """V4-17: Server injects version handshake headers into all responses"""
    res = client.get(
        "/health",
        headers={
            "X-Nova-Client-Version": "2.0.0",
            "X-Nova-Build-SHA": "test-sha-123"
        }
    )
    assert res.status_code == 200
    assert res.headers.get("X-Nova-Server-Version") == SERVER_VERSION
    assert res.headers.get("X-Nova-Min-Client-Version") == MIN_CLIENT_VERSION

import os
import sys
import pytest
from pathlib import Path

# Add server directory to sys.path
SERVER_DIR = Path(__file__).resolve().parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from config import NOVA_VOICE, VIENEU_MODE
from core.vieneu_engine import nova_engine, NovaNeuralTTS
from core.tts import tts_engine


def test_nova_voice_configured():
    """Kiểm tra giọng nói Nova được cấu hình là Xuân Tiên."""
    assert NOVA_VOICE == "Xuân Tiên"
    assert VIENEU_MODE == "v3nano"


def test_nova_voice_loaded():
    """Kiểm tra mô hình VieNeu v3nano và giọng Xuân Tiên đã được nạp thành công."""
    health = nova_engine.get_health()
    assert health["model_loaded"] is True, "VieNeu model chưa được nạp"
    assert health["voice_loaded"] is True, "Giọng Xuân Tiên chưa được nạp"
    assert health["status"] == "ok"
    assert health["voice_name"] == "Xuân Tiên"


def test_synthesize_xuantien_returns_valid_wav():
    """Kiểm tra tổng hợp giọng Xuân Tiên tạo file WAV hợp lệ."""
    import soundfile as sf
    test_phrase = "Chào bạn, tớ là Nova đây nè."
    wav_path = nova_engine.synthesize(test_phrase)

    assert wav_path is not None, "synthesize trả về None"
    assert wav_path.exists(), f"File âm thanh sinh ra không tồn tại: {wav_path}"
    assert wav_path.stat().st_size > 1000, "File âm thanh sinh ra quá nhỏ (< 1KB)"

    info = sf.info(str(wav_path))
    assert info.samplerate in [24000, 48000], f"Sample rate không hợp lệ: {info.samplerate}"
    assert info.channels == 1, "Audio phải là kênh Mono"
    assert info.duration > 0.5, "Thời lượng âm thanh phải > 0.5s"


def test_tts_engine_synthesizes_successfully():
    """Kiểm tra tts_engine cấp cao sinh âm thanh thành công qua VieNeu."""
    out_file = tts_engine.synthesize("Xin chào cậu nhé!")
    assert out_file != "", "tts_engine phải sinh được âm thanh"
    p = Path(out_file)
    assert p.exists()
    assert p.stat().st_size > 500


def test_tts_health_status():
    """Kiểm tra endpoint get_tts_health trả về trạng thái khỏe mạnh."""
    h = tts_engine.get_tts_health()
    assert h["model_loaded"] is True
    assert h["voice_loaded"] is True
    assert h["voice_name"] == "Xuân Tiên"
    assert h["tts_primary"] == "vieneu"

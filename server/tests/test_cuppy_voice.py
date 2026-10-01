import os
import sys
import pytest
from pathlib import Path

# Add server directory to sys.path
SERVER_DIR = Path(__file__).resolve().parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from config import CUPPY_REFERENCE_WAV, CUPPY_REFERENCE_DENOISE
from core.vieneu_cuppy import cuppy_engine, CuppyNeuralTTS


def test_cuppy_reference_path_exists():
    """Kiểm tra đường dẫn reference WAV được cấu hình và file tồn tại."""
    assert CUPPY_REFERENCE_WAV is not None and len(CUPPY_REFERENCE_WAV) > 0
    ref_path = Path(CUPPY_REFERENCE_WAV)
    assert ref_path.exists(), f"File Cuppy reference WAV không tồn tại tại: {ref_path}"
    assert ref_path.stat().st_size > 1000, "File reference WAV quá nhỏ (< 1KB)"


def test_cuppy_voice_loaded():
    """Kiểm tra Cuppy voice đã được nạp thành công từ reference WAV."""
    health = cuppy_engine.get_health()
    assert health["model_loaded"] is True, "VieNeu v3turbo model chưa được load"
    assert health["voice_loaded"] is True, "Voice 'cuppy' chưa được đăng ký thành công"
    assert health["voice_source"] == "reference_wav", f"Nguồn voice không phải reference_wav mà là {health['voice_source']}"
    assert health["reference_exists"] is True
    assert health["reference_duration"] > 0.0


def test_cuppy_reference_missing_does_not_crash(monkeypatch, tmp_path):
    """Kiểm tra khi reference WAV bị thiếu, engine không bị crash mà fallback an toàn."""
    fake_path = tmp_path / "non_existent_voice.wav"
    monkeypatch.setattr("core.vieneu_cuppy.CUPPY_REFERENCE_WAV", str(fake_path))
    
    # Khởi tạo một instance riêng biệt để kiểm tra fallback
    test_tts = CuppyNeuralTTS.__new__(CuppyNeuralTTS)
    test_tts.tts = None
    test_tts.voice_source = "none"
    test_tts.reference_exists = False
    test_tts.reference_duration = 0.0
    test_tts.reference_path = None
    test_tts.model_loaded = False
    test_tts.voice_loaded = False
    import threading
    test_tts._infer_lock = threading.Lock()
    
    # Gọi _init_engine không được raise Exception
    test_tts._init_engine()
    
    assert test_tts.reference_exists is False
    assert test_tts.voice_source in ["preset_json", "none"]


def test_cache_changes_when_voice_changes(tmp_path):
    """Kiểm tra cache fingerprint thay đổi khi đổi file voice reference."""
    f1 = tmp_path / "sample1.wav"
    f1.write_bytes(b"RIFFdummydata1234567890")
    
    f2 = tmp_path / "sample2.wav"
    f2.write_bytes(b"RIFFdummydata9876543210diff")
    
    test_tts = CuppyNeuralTTS.__new__(CuppyNeuralTTS)
    test_tts.voice_source = "reference_wav"
    test_tts.reference_path = f1
    fp1 = test_tts._voice_fingerprint()
    
    test_tts.reference_path = f2
    fp2 = test_tts._voice_fingerprint()
    
    assert fp1 != fp2, f"Fingerprint phải khác nhau khi đổi file: {fp1} vs {fp2}"


def test_synthesize_returns_valid_wav():
    """Kiểm tra quá trình synthesize tạo file WAV hợp lệ, không rỗng và đọc được."""
    import soundfile as sf
    test_phrase = "Chào bạn, tớ là Cuppy đây nè."
    wav_path = cuppy_engine.synthesize(test_phrase)
    
    assert wav_path is not None, "synthesize trả về None"
    assert wav_path.exists(), f"File âm thanh sinh ra không tồn tại: {wav_path}"
    assert wav_path.stat().st_size > 1000, "File âm thanh sinh ra quá nhỏ (< 1KB)"
    
    # Đọc lại và kiểm tra sample rate 48000 Hz
    info = sf.info(str(wav_path))
    assert info.samplerate == 48000, f"Sample rate kỳ vọng 48000, thực tế {info.samplerate}"
    assert info.channels == 1, "Audio kênh phải là Mono"
    assert info.duration > 0.5, "Thời lượng âm thanh phải > 0.5s"


def test_health_reports_reference_voice():
    """Kiểm tra hàm get_health báo cáo đầy đủ thông tin về reference voice."""
    health = cuppy_engine.get_health()
    assert health["status"] == "ok"
    assert "reference_duration" in health
    assert "voice_source" in health
    assert health["voice_source"] == "reference_wav"
    assert health["cache_writable"] is True

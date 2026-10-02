import io
import time
import os
import sys
import hashlib
import logging
import threading
from pathlib import Path
from typing import Optional
import soundfile as sf

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("NovaNeuralTTS")

ROOT_DIR = Path(__file__).resolve().parent.parent
from config import (
    NOVA_VOICE,
    VIENEU_MODE,
    VIENEU_SPEED,
    DATA_DIR
)

CACHE_DIR = DATA_DIR / "tts_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class NovaNeuralTTS:
    """Động cơ tổng hợp giọng nói AI VieNeu siêu nhẹ cho Nova (Mặc định: Xuân Tiên - v3nano)."""
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.tts = None
        self.mode = VIENEU_MODE or "v3nano"
        self.voice_name = NOVA_VOICE or "Xuân Tiên"
        self.model_loaded = False
        self.voice_loaded = False
        self._infer_lock = threading.Lock()
        self._init_engine()

    def _init_engine(self):
        """Khởi tạo VieNeu engine (v3nano) và kiểm tra giọng Xuân Tiên có sẵn."""
        try:
            from vieneu import Vieneu
            logger.info(f"Đang khởi tạo mô hình VieNeu mode '{self.mode}'...")
            self.tts = Vieneu(mode=self.mode)
            self.model_loaded = True
            
            # Kiểm tra giọng có sẵn trong danh sách preset
            preset_voices = getattr(self.tts, "_preset_voices", {})
            if self.voice_name in preset_voices:
                self.voice_loaded = True
                logger.info(f"Đã nạp thành công giọng '{self.voice_name}' từ VieNeu {self.mode}!")
            else:
                # Nếu không tìm thấy chính xác tên (do dấu), fallback sang giọng đầu tiên hoặc alias
                logger.warning(f"Không tìm thấy tên giọng '{self.voice_name}', đang tìm kiếm giọng phù hợp...")
                matched = None
                for k in preset_voices.keys():
                    if "tiên" in k.lower() or "xuan" in k.lower():
                        matched = k
                        break
                if matched:
                    self.voice_name = matched
                    self.voice_loaded = True
                    logger.info(f"Đã khớp giọng thay thế: '{self.voice_name}'")
                elif preset_voices:
                    self.voice_name = list(preset_voices.keys())[0]
                    self.voice_loaded = True
                    logger.info(f"Dùng giọng mặc định: '{self.voice_name}'")
                else:
                    self.voice_loaded = True

        except Exception as e:
            logger.error(f"Lỗi khởi tạo VieNeu mode {self.mode}: {e}")
            self.tts = None
            self.model_loaded = False
            self.voice_loaded = False

    def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[Path]:
        """Tổng hợp câu nói ra file WAV chất lượng cao và lưu cache."""
        clean = (text or "").strip()
        if not clean or not self.tts or not self.model_loaded:
            return None

        clean_text = clean.replace("*", "").replace("#", "").replace("_", "").replace("`", "").strip()
        if len(clean_text) > 2000:
            clean_text = clean_text[:2000]

        target_voice = voice or self.voice_name
        cache_key = f"{self.mode}|{target_voice}|{clean_text}"
        text_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:20]
        cache_path = CACHE_DIR / f"nova_{text_hash}.wav"

        if cache_path.exists() and cache_path.stat().st_size > 1000:
            return cache_path

        with self._infer_lock:
            if cache_path.exists() and cache_path.stat().st_size > 1000:
                return cache_path
            try:
                t0 = time.time()
                wav = self.tts.infer(clean_text, voice=target_voice, steps=6, cfg=1.5)
                sample_rate = 24000 if self.mode == "v3nano" else 48000
                sf.write(str(cache_path), wav, sample_rate)
                dur = time.time() - t0
                logger.info(f"Sinh giọng '{target_voice}' thành công ({dur:.2f}s) cho hash {text_hash[:8]}")
                return cache_path
            except Exception as e:
                logger.error(f"Lỗi infer giọng từ VieNeu: {e}")
                return None

    def synthesize_bytes(self, text: str, voice: Optional[str] = None) -> bytes:
        p = self.synthesize(text, voice=voice)
        if p and p.exists():
            return p.read_bytes()
        return b""

    def get_health(self) -> dict:
        return {
            "status": "ok" if (self.model_loaded and self.voice_loaded) else "degraded",
            "model_loaded": self.model_loaded,
            "voice_loaded": self.voice_loaded,
            "voice_name": self.voice_name,
            "mode": self.mode,
            "cache_writable": CACHE_DIR.exists() and os.access(str(CACHE_DIR), os.W_OK),
            "warm": self.model_loaded
        }


nova_engine = NovaNeuralTTS.get_instance()

import io
import json
import time
import os
import sys
import hashlib
import logging
import threading
from pathlib import Path
from typing import Optional
import numpy as np
import soundfile as sf

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("CuppyNeuralTTS")

ROOT_DIR = Path(__file__).resolve().parent.parent
from config import (
    CUPPY_REFERENCE_WAV,
    CUPPY_REFERENCE_DENOISE,
    DATA_DIR
)

preset_env = os.getenv("CUPPY_VOICE_PRESET_PATH")
if preset_env:
    MASTER_VOICES_PATH = Path(preset_env)
else:
    MASTER_VOICES_PATH = DATA_DIR / "extended_voices_master.json"

CACHE_DIR = DATA_DIR / "cuppy_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class CuppyNeuralTTS:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.tts = None
        self.voice_source = "none"
        self.reference_exists = False
        self.reference_duration = 0.0
        self.reference_path: Optional[Path] = None
        self.model_loaded = False
        self.voice_loaded = False
        self._infer_lock = threading.Lock()
        self._init_engine()

    def _init_engine(self):
        """Khởi tạo VieNeu v3turbo và nạp mẫu giọng Cuppy reference một lần duy nhất khi boot."""
        ref_path = Path(CUPPY_REFERENCE_WAV) if CUPPY_REFERENCE_WAV else None
        has_ref = bool(ref_path and ref_path.exists())
        has_preset = bool(MASTER_VOICES_PATH and MASTER_VOICES_PATH.exists())

        if not has_ref and not has_preset:
            logger.info("Khong co Reference WAV hoac Preset JSON hop le, bo qua khoi tao local Vieneu.")
            self.model_loaded = False
            self.voice_loaded = False
            self.voice_source = "none"
            return

        try:
            from vieneu import Vieneu
            logger.info("Dang khoi tao Vieneu model v3turbo...")
            self.tts = Vieneu(mode="v3turbo")
            self.model_loaded = True
        except Exception as e:
            logger.error(f"Loi khoi tao Vieneu model v3turbo: {e}")
            self.tts = None
            self.model_loaded = False
            return

        # 1. Ưu tiên hàng đầu: Nạp và clone giọng từ Reference WAV
        if has_ref:
            try:
                try:
                    info = sf.info(str(ref_path))
                    self.reference_duration = round(float(info.duration), 2)
                except Exception as e_info:
                    logger.warning(f"Khong the doc thong so WAV info: {e_info}")
                    self.reference_duration = 0.0

                logger.info(f"Dang dang ky voice 'cuppy' tu reference WAV: {ref_path} ({self.reference_duration}s)...")
                self.tts.add_voice(
                    "cuppy",
                    str(ref_path),
                    denoise=CUPPY_REFERENCE_DENOISE
                )
                self.voice_source = "reference_wav"
                self.reference_exists = True
                self.reference_path = ref_path
                self.voice_loaded = True
                logger.info("Da dang ky thanh cong giong Cuppy tu reference WAV!")
            except Exception as e_ref:
                logger.error(f"Loi dang ky voice tu reference WAV: {e_ref}")
                self.reference_exists = False
                self.voice_loaded = False

        # 2. Fallback: Nếu không có WAV hoặc lỗi, thử nạp từ Preset JSON cũ
        if not self.voice_loaded and MASTER_VOICES_PATH.exists():
            try:
                with open(MASTER_VOICES_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)

                v = data.get("presets", {}).get("Saydi - Cuppy — Trợ lý ảo nữ")
                if v:
                    self.tts._preset_voices["cuppy"] = {
                        "description": v.get("description", ""),
                        "gender": v.get("gender", "female"),
                        "style": "tu_nhien",
                        "aliases": ["cuppy-vi", "saydi-cuppy-vi", "cuppy"],
                        "speaker_emb": np.asarray(v["speaker_emb"], dtype=np.float32),
                        "codes": np.asarray(v["codes"], dtype=np.int64) if v.get("codes") else None,
                    }
                    if hasattr(self.tts, "_register_aliases"):
                        self.tts._register_aliases("cuppy", ["cuppy-vi", "saydi-cuppy-vi"])
                    self.voice_source = "preset_json"
                    self.voice_loaded = True
                    logger.info("Da nap thanh cong preset giong Cuppy tu JSON master!")
                else:
                    logger.warning("Khong tim thay preset Cuppy trong master JSON!")
            except Exception as e_json:
                logger.error(f"Loi nap preset Cuppy tu JSON: {e_json}")

        # In banner logging trạng thái khởi động theo chuẩn kiến trúc Nova
        logger.info("=" * 60)
        logger.info(f"VieNeu v3turbo: {'READY' if self.model_loaded else 'FAILED'}")
        logger.info(f"Cuppy reference: {'FOUND' if self.reference_exists else 'NOT_FOUND'}")
        logger.info(f"Cuppy voice: {'LOADED' if self.voice_loaded else 'NOT_LOADED'}")
        logger.info(f"Voice source: {self.voice_source}")
        logger.info(f"Fallback used: {str(self.voice_source != 'reference_wav').lower()}")
        logger.info("=" * 60)

    def _voice_fingerprint(self) -> str:
        """Tạo fingerprint định danh file voice reference để tự động làm mới cache khi đổi file WAV."""
        if self.voice_source == "reference_wav" and self.reference_path and self.reference_path.exists():
            try:
                stat = self.reference_path.stat()
                raw = f"{self.reference_path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
                return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
            except Exception:
                return "ref_fallback"
        return f"src_{self.voice_source}"

    def synthesize(self, text: str) -> Optional[Path]:
        """Sinh file WAV mới bằng giọng Cuppy clone từ reference WAV."""
        clean = (text or "").strip()
        if not clean or not self.tts or not self.voice_loaded:
            return None

        # Clean markdown symbols
        clean_text = clean.replace("*", "").replace("#", "").replace("_", "").replace("`", "").strip()
        # Giới hạn tối đa 3000 ký tự
        if len(clean_text) > 3000:
            clean_text = clean_text[:3000]

        # Fingerprint nhận biết khi file mẫu giọng thay đổi
        fp = self._voice_fingerprint()
        cache_input = f"{fp}|{clean_text}"
        text_hash = hashlib.sha256(cache_input.encode("utf-8")).hexdigest()
        cache_path = CACHE_DIR / f"cuppy_{text_hash}.wav"

        if cache_path.exists() and cache_path.stat().st_size > 1000:
            return cache_path

        # Thread lock an toàn bảo vệ mô hình khi nhiều request gọi song song
        with self._infer_lock:
            if cache_path.exists() and cache_path.stat().st_size > 1000:
                return cache_path
            try:
                t0 = time.time()
                wav = self.tts.infer(clean_text, voice="cuppy")
                sf.write(str(cache_path), wav, 48000)
                dur = time.time() - t0
                logger.info(f"Sinh giong Cuppy thanh cong ({dur:.2f}s) cho hash {text_hash[:8]}")
                return cache_path
            except Exception as e:
                logger.error(f"Loi infer Cuppy tu VieNeu: {e}")
                return None

    def synthesize_bytes(self, text: str) -> bytes:
        p = self.synthesize(text)
        if p and p.exists():
            return p.read_bytes()
        return b""

    def get_health(self) -> dict:
        return {
            "status": "ok" if (self.model_loaded and self.voice_loaded) else "degraded",
            "model_loaded": self.model_loaded,
            "voice_loaded": self.voice_loaded,
            "voice_source": self.voice_source,
            "reference_exists": self.reference_exists,
            "reference_duration": self.reference_duration,
            "cache_writable": CACHE_DIR.exists() and os.access(str(CACHE_DIR), os.W_OK),
            "warm": self.model_loaded
        }


cuppy_engine = CuppyNeuralTTS.get_instance()

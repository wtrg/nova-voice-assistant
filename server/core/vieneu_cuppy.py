import io
import json
import time
import os
import sys
import hashlib
import logging
import threading
from pathlib import Path
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
preset_env = os.getenv("CUPPY_VOICE_PRESET_PATH")
if preset_env:
    MASTER_VOICES_PATH = Path(preset_env)
else:
    p1 = ROOT_DIR / "data" / "extended_voices_master.json"
    p2 = Path(r"C:\Users\Lenovo\Documents\Codex\2026-08-29\x20\work\wtstudio-source\extended_voices_master.json")
    MASTER_VOICES_PATH = p1 if p1.exists() else p2

CACHE_DIR = ROOT_DIR / "data" / "cuppy_cache"
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
        self._infer_lock = threading.Lock()
        self._init_engine()

    def _init_engine(self):
        try:
            from vieneu import Vieneu
            logger.info("Dang khoi tao Vieneu model v3turbo...")
            self.tts = Vieneu(mode="v3turbo")

            if MASTER_VOICES_PATH.exists():
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
                    self.tts._register_aliases("cuppy", ["cuppy-vi", "saydi-cuppy-vi"])
                    logger.info("Da nap thanh cong preset giong Cuppy goc!")
                else:
                    logger.warning("Khong tim thay preset Saydi - Cuppy trong master json!")
        except Exception as e:
            logger.error(f"Loi khoi tao Vieneu Cuppy TTS: {e}")
            self.tts = None

    def synthesize(self, text: str) -> Path:
        clean = (text or "").strip()
        if not clean or not self.tts:
            return None

        # Clean markdown symbols
        clean_text = clean.replace("*", "").replace("#", "").replace("_", "").replace("`", "").strip()
        # Giới hạn tối đa 3000 ký tự (chuẩn độ dài đoạn văn/kể chuyện)
        if len(clean_text) > 3000:
            clean_text = clean_text[:3000]

        text_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()
        cache_path = CACHE_DIR / f"cuppy_{text_hash}.wav"

        if cache_path.exists() and cache_path.stat().st_size > 1000:
            return cache_path

        # Các request chạy trong thread pool; model và file cache cần được dùng tuần tự.
        with self._infer_lock:
            if cache_path.exists() and cache_path.stat().st_size > 1000:
                return cache_path
            try:
                t0 = time.time()
                wav = self.tts.infer(clean_text, voice="cuppy")
                sf.write(str(cache_path), wav, 48000)
                logger.info("Sinh giong Cuppy (%.2fs) cho hash %s", time.time() - t0, text_hash[:8])
                return cache_path
            except Exception as e:
                logger.error("Loi infer Cuppy: %s", e)
                return None

    def synthesize_bytes(self, text: str) -> bytes:
        p = self.synthesize(text)
        if p and p.exists():
            return p.read_bytes()
        return b""

    def get_health(self) -> dict:
        return {
            "status": "ok" if self.tts else "degraded",
            "model_loaded": self.tts is not None,
            "voice_loaded": (self.tts is not None and hasattr(self.tts, "_preset_voices") and "cuppy" in self.tts._preset_voices),
            "cache_writable": CACHE_DIR.exists() and os.access(str(CACHE_DIR), os.W_OK),
            "warm": self.tts is not None
        }

cuppy_engine = CuppyNeuralTTS.get_instance()

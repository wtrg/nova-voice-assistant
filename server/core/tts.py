import os
import time
import asyncio
import logging
import requests
from pathlib import Path
from typing import Optional
import pygame
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import (
    TTS_PROVIDER,
    CUPPY_TTS_URL,
    CUPPY_LOCAL_URL,
    CUPPY_VOICE,
    CUPPY_SPEED,
    ELEVENLABS_API_KEY, 
    ELEVENLABS_VOICE_ID, 
    EDGE_TTS_VOICE,
    SAYDI_API_KEY,
    SAYDI_VOICE,
    DATA_DIR
)

logger = logging.getLogger("TTS")
AUDIO_CACHE_DIR = DATA_DIR / "tts_cache"
AUDIO_CACHE_DIR.mkdir(exist_ok=True)

# Khởi tạo pygame mixer cho việc phát âm thanh
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init()
except Exception as e:
    logger.warning(f"Không thể khởi tạo pygame.mixer: {e}")

class TextToSpeech:
    def __init__(self):
        self.provider = TTS_PROVIDER
        self.cuppy_url = CUPPY_TTS_URL
        self.cuppy_local = CUPPY_LOCAL_URL
        self.cuppy_voice = CUPPY_VOICE
        self.cuppy_speed = CUPPY_SPEED
        self.eleven_key = ELEVENLABS_API_KEY
        self.eleven_voice = ELEVENLABS_VOICE_ID
        self.edge_voice = EDGE_TTS_VOICE
        self.saydi_key = SAYDI_API_KEY
        self.saydi_voice = SAYDI_VOICE

    def _generate_cuppy_tts(self, text: str, output_path: str) -> bool:
        """Sinh giọng nói trợ lý ảo Cuppy thông qua Vieneu Neural TTS Engine"""
        try:
            from core.vieneu_cuppy import cuppy_engine
            p = cuppy_engine.synthesize(text)
            if p and p.exists() and p.stat().st_size > 1000:
                import shutil
                shutil.copyfile(str(p), output_path)
                return True
        except Exception as e:
            logger.warning(f"Local Vieneu Cuppy error: {e}")

        # Dự phòng các endpoint nếu có
        endpoints = [
            f"{self.cuppy_local}",
            "http://127.0.0.1:5055/v1/audio/speech",
            f"{self.cuppy_url}"
        ]
        
        headers = {"Content-Type": "application/json"}
        
        for target_url in endpoints:
            try:
                if "speech" in target_url:
                    payload = {"model": "tts-1", "input": text, "voice": self.cuppy_voice, "response_format": "mp3"}
                else:
                    payload = {"text": text, "voice": self.cuppy_voice, "speed": self.cuppy_speed, "format": "mp3"}
                    
                response = requests.post(target_url, json=payload, headers=headers, timeout=1.5)
                if response.status_code == 200 and len(response.content) > 1000:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    return True
                else:
                    logger.warning(f"Cuppy TTS {target_url} trả về {response.status_code}")
            except Exception as e:
                logger.warning(f"Không kết nối được Cuppy TTS tại {target_url}: {e}")
                
        return False


    async def _generate_edge_tts(self, text: str, output_path: str):
        """Sinh giọng nói tiếng Việt tự nhiên dự phòng bằng Edge-TTS"""
        import edge_tts
        communicate = edge_tts.Communicate(text, self.edge_voice)
        await communicate.save(output_path)

    def _generate_saydi_tts(self, text: str, output_path: str) -> bool:
        """Sinh giọng nói Cuppy thông qua Saydi AI Voice Studio API (voice.saydi.ai)"""
        if not self.saydi_key:
            return False
        try:
            url = "https://voice.saydi.ai/api/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {self.saydi_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "tts-1",
                "voice": self.saydi_voice or "Saydi - Cuppy — Trợ lý ảo nữ",
                "input": text,
                "response_format": "mp3"
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=12.0)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"[TTS] Đã sinh giọng Cuppy thành công từ Saydi AI ({len(resp.content)} bytes)")
                return True
            else:
                logger.warning(f"[TTS] Saydi AI trả về {resp.status_code}: {resp.text[:150]}")
        except Exception as e:
            logger.warning(f"[TTS] Không thể kết nối Saydi AI API: {e}")
        return False

    def _generate_elevenlabs_clone(self, text: str, output_path: str) -> bool:
        """Sinh giọng nói clone bằng ElevenLabs API"""
        if not self.eleven_key or not self.eleven_voice:
            return False
            
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.eleven_voice}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.eleven_key
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.85}
        }
        try:
            res = requests.post(url, json=data, headers=headers, timeout=5)
            if res.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(res.content)
                return True
        except Exception as e:
            logger.error(f"Lỗi ElevenLabs: {e}")
        return False

    def synthesize(self, text: str) -> str:
        """Chuyển văn bản thành file âm thanh mp3"""
        timestamp = int(time.time() * 1000)
        output_file = str(AUDIO_CACHE_DIR / f"speech_{timestamp}.mp3")
        
        success = False
        # Ưu tiên 1: Giọng Cuppy Vieneu / Local endpoint
        if self.provider == "cuppy" or self.cuppy_url:
            success = self._generate_cuppy_tts(text, output_file)

        # Ưu tiên 2: Saydi AI Voice Studio (voice.saydi.ai) với giọng Cuppy trực tuyến
        if not success and self.saydi_key:
            success = self._generate_saydi_tts(text, output_file)
            
        if not success and self.provider == "elevenlabs":
            success = self._generate_elevenlabs_clone(text, output_file)
            
        if not success:
            # Fallback an toàn về Edge-TTS chỉ khi Cuppy hoàn toàn mất kết nối
            logger.warning("[TTS] Cuppy TTS khong phan hoi, tam dung giong du phong Edge-TTS...")
            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(lambda: asyncio.run(self._generate_edge_tts(text, output_file)))
                    future.result(timeout=10)
                success = True
            except Exception as e:
                logger.error(f"Lỗi Edge-TTS fallback: {e}")

        if not success:
            # Fallback 4: Prebuilt bundled response audio if available
            bundled_candidates = [
                ROOT_DIR.parent / "client" / "www" / "assets" / "cuppy_ok.wav",
                ROOT_DIR / "data" / "cuppy_ok.wav"
            ]
            for bc in bundled_candidates:
                if bc.exists():
                    import shutil
                    wav_file = str(AUDIO_CACHE_DIR / f"speech_{timestamp}.wav")
                    shutil.copyfile(str(bc), wav_file)
                    return wav_file

        if success and Path(output_file).exists():
            # F-14: Kiểm tra magic bytes và điều chỉnh phần mở rộng file chính xác (WAV vs MP3)
            try:
                with open(output_file, "rb") as f:
                    header = f.read(12)
                if header.startswith(b"RIFF") and b"WAVE" in header:
                    wav_file = str(AUDIO_CACHE_DIR / f"speech_{timestamp}.wav")
                    Path(output_file).rename(wav_file)
                    return wav_file
            except Exception:
                pass
            return output_file

        return ""

    def get_tts_health(self) -> dict:
        """Kiểm tra sức khỏe hệ thống TTS (V4-04)"""
        cuppy_available = False
        try:
            from core.vieneu_cuppy import cuppy_engine
            cuppy_available = cuppy_engine.get_health().get("model_loaded", False)
        except Exception:
            pass
        if not cuppy_available:
            cuppy_available = bool(self.cuppy_url or self.saydi_key)

        return {
            "tts_primary": "cuppy",
            "tts_primary_ready": cuppy_available,
            "tts_fallback_ready": True
        }

    def speak(self, text: str, wait_until_done: bool = True):
        """Phát âm thanh câu nói qua loa máy tính/điện thoại"""
        if not text or not text.strip():
            return
            
        audio_path = self.synthesize(text)
        if not audio_path or not os.path.exists(audio_path):
            logger.error("Không tạo được file âm thanh để phát.")
            return

        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            
            if wait_until_done:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Lỗi phát âm thanh qua pygame: {e}")

tts_engine = TextToSpeech()

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    print("Đang thử nghiệm phát giọng Cuppy...")
    tts_engine.speak("Chào cậu! Tớ là Nova đây, tớ đang dùng giọng Cuppy để nói chuyện với cậu nè!")
    print("Hoàn tất phát giọng Cuppy thành công.")

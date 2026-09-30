import sys
from pathlib import Path
import logging
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import GROQ_API_KEY

logger = logging.getLogger("STT")

class SpeechToText:
    def __init__(self):
        self.groq_key = GROQ_API_KEY

    def transcribe_audio_file(self, audio_file_path: str) -> str:
        """
        Chuyển file âm thanh thành văn bản tiếng Việt.
        Ưu tiên dùng Groq Whisper API (cực nhanh ~200ms).
        Nếu không có key, fallback sang Google Speech Recognition.
        """
        if self.groq_key:
            try:
                url = "https://api.groq.com/openai/v1/audio/transcriptions"
                headers = {"Authorization": f"Bearer {self.groq_key}"}
                with open(audio_file_path, "rb") as f:
                    files = {"file": f}
                    data = {
                        "model": "whisper-large-v3",
                        "language": "vi",
                        "response_format": "json"
                    }
                    response = requests.post(url, headers=headers, files=files, data=data, timeout=15)
                    if response.status_code == 200:
                        text = response.json().get("text", "").strip()
                        return text
                    else:
                        logger.warning(f"Groq STT lỗi {response.status_code}, fallback sang Google STT.")
            except Exception as e:
                logger.error(f"Lỗi khi gọi Groq STT: {e}")

        # Fallback về SpeechRecognition (Google STT tiếng Việt miễn phí)
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_file_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language="vi-VN")
                return text.strip()
        except Exception as e:
            logger.error(f"Lỗi nhận diện âm thanh qua Google STT: {e}")
            return ""

    def listen_from_microphone(self, timeout_sec: int = 5) -> str:
        """
        Ghi âm trực tiếp từ microphone máy tính và chuyển thành chữ.
        """
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True
            
            with sr.Microphone() as source:
                logger.info("Đang lắng nghe âm thanh từ microphone...")
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio_data = recognizer.listen(source, timeout=timeout_sec, phrase_time_limit=10)
                
                # Nếu có Groq Key, gửi file wav lên Groq Whisper để nhận diện chuẩn nhất
                if self.groq_key:
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp_path = tmp.name
                        tmp.write(audio_data.get_wav_data())
                    try:
                        text = self.transcribe_audio_file(tmp_path)
                        os.remove(tmp_path)
                        if text:
                            return text
                    except Exception:
                        pass
                
                # Fallback về Google STT
                text = recognizer.recognize_google(audio_data, language="vi-VN")
                return text.strip()
        except sr.WaitTimeoutError:
            logger.info("Hết thời gian chờ, không có giọng nói.")
            return ""
        except sr.UnknownValueError:
            logger.info("Không hiểu được âm thanh người dùng nói.")
            return ""
        except Exception as e:
            logger.warning(f"Lỗi thu âm từ mic: {e}")
            return ""


stt_engine = SpeechToText()

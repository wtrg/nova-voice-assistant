import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
# Ưu tiên nạp server/.env trước, sau đó nạp file .env ở thư mục gốc (nếu có)
load_dotenv(BASE_DIR / ".env")
load_dotenv()

DATA_DIR = Path(os.getenv("NOVA_DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Phiên bản hệ thống & Handshake
SERVER_VERSION = "2.0.0"
MIN_CLIENT_VERSION = "2.0.0"
NOVA_API_BASE_URL = os.getenv("NOVA_API_BASE_URL", "https://nova-voice-assistant-6l5s.onrender.com")

# Cấu hình Cơ sở dữ liệu SQLite
DB_PATH = DATA_DIR / "assistant.db"

# Tên trợ lý & Chủ nhân
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Nova")
USER_NAME = os.getenv("USER_NAME", "Cậu")
ASSISTANT_PERSONA = os.getenv("ASSISTANT_PERSONA", "best_friend")

# Cấu hình AI Brain (LLM)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq") # "groq" hoặc "gemini"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")

# Cấu hình Voice TTS (Cuppy / Edge-TTS / ElevenLabs)
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "cuppy")
CUPPY_TTS_URL = os.getenv("CUPPY_TTS_URL", "")
CUPPY_LOCAL_URL = os.getenv("CUPPY_LOCAL_URL", "http://127.0.0.1:5055/api/tts")
CUPPY_VOICE = os.getenv("CUPPY_VOICE", "cuppy")
CUPPY_SPEED = float(os.getenv("CUPPY_SPEED", "1.0"))
DEFAULT_CUPPY_REFERENCE_WAV = r"C:/Users/Lenovo/AppData/Local/WTStudio/saydi-tts-service/cuppy_sample_8_12s.wav"
CUPPY_REFERENCE_WAV = os.getenv(
    "CUPPY_REFERENCE_WAV",
    DEFAULT_CUPPY_REFERENCE_WAV
)
CUPPY_REFERENCE_DENOISE = (
    os.getenv("CUPPY_REFERENCE_DENOISE", "true").lower()
    in ("1", "true", "yes", "on")
)
STRICT_CUPPY_MODE = (
    os.getenv("STRICT_CUPPY_MODE", "true").lower()
    in ("1", "true", "yes", "on")
)


ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "vi-VN-HoaiMyNeural")

# Cấu hình Saydi AI Voice Studio (voice.saydi.ai)
SAYDI_API_KEY = os.getenv("SAYDI_API_KEY", "")
SAYDI_VOICE = os.getenv("SAYDI_VOICE", "Saydi - Cuppy — Trợ lý ảo nữ")

# Cấu hình Wake Word
WAKE_WORD = os.getenv("WAKE_WORD", "hey_nova")
WAKE_WORD_SENSITIVITY = float(os.getenv("WAKE_WORD_SENSITIVITY", "0.5"))

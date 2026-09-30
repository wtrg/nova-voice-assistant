import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

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
CUPPY_TTS_URL = os.getenv("CUPPY_TTS_URL", "https://logo-world-limousines-cups.trycloudflare.com/api/tts")
CUPPY_LOCAL_URL = os.getenv("CUPPY_LOCAL_URL", "http://127.0.0.1:5055/api/tts")
CUPPY_VOICE = os.getenv("CUPPY_VOICE", "cuppy")
CUPPY_SPEED = float(os.getenv("CUPPY_SPEED", "1.0"))

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "vi-VN-HoaiMyNeural")

# Cấu hình Wake Word
WAKE_WORD = os.getenv("WAKE_WORD", "hey_nova")
WAKE_WORD_SENSITIVITY = float(os.getenv("WAKE_WORD_SENSITIVITY", "0.5"))

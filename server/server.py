import os
import sys
import re
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import USER_NAME, ASSISTANT_NAME, DATA_DIR
from core.agent import assistant_agent
from core.tts import tts_engine, AUDIO_CACHE_DIR
from core.stt import stt_engine
from core.database import get_all_active_tasks, add_task
from core.scheduler import scheduler_engine

from fastapi.staticfiles import StaticFiles

from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import time

app = FastAPI(title="Nova Voice Assistant Mobile API")

# F-06: Middleware giới hạn tần suất gọi API (Rate Limiting) chống cạn kiệt tài nguyên
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests_per_minute: int = 120):
        super().__init__(app)
        self.max_requests = max_requests_per_minute
        self.clients = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/download") or path.startswith("/static") or path.startswith("/qr"):
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        self.clients[client_ip] = [t for t in self.clients[client_ip] if now - t < 60]
        if len(self.clients[client_ip]) >= self.max_requests:
            return JSONResponse(status_code=429, content={"error": "Too Many Requests. Vui lòng thử lại sau giây lát."})
        self.clients[client_ip].append(now)
        return await call_next(request)

app.add_middleware(RateLimitMiddleware, max_requests_per_minute=120)

# F-06: Giới hạn CORS chỉ cho phép nguồn gốc tin cậy (Localhost, Capacitor, Cloudflare Tunnel)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^capacitor://localhost$|^https://.*\.trycloudflare\.com$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

# Phục vụ thư mục static
(ROOT_DIR / "static").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "static")), name="static")

@app.on_event("startup")
async def startup_event():
    pass # Mobile app handles proactive notifications locally via native AlarmManager

@app.on_event("shutdown")
async def shutdown_event():
    pass

@app.api_route("/download/nova.apk", methods=["GET", "HEAD"])
async def download_apk():
    """Phục vụ tải trực tiếp tệp cài đặt APK cho điện thoại Android"""
    apk_path = ROOT_DIR / "static" / "Nova_Assistant.apk"
    if apk_path.exists():
        return FileResponse(
            apk_path,
            media_type="application/vnd.android.package-archive",
            filename="Nova_Assistant.apk"
        )
    return JSONResponse(status_code=404, content={"error": "APK not found"})

@app.get("/qr/apk")
async def qr_apk():
    """Trả về hình ảnh mã QR tải APK"""
    qr_path = ROOT_DIR / "static" / "qr_nova_apk.png"
    if qr_path.exists():
        return FileResponse(qr_path, media_type="image/png")
    return JSONResponse(status_code=404, content={"error": "QR not found"})

@app.get("/qr/web")
async def qr_web():
    """Trả về hình ảnh mã QR mở Web App"""
    qr_path = ROOT_DIR / "static" / "qr_nova_web.png"
    if qr_path.exists():
        return FileResponse(qr_path, media_type="image/png")
    return JSONResponse(status_code=404, content={"error": "QR not found"})



class ChatRequest(BaseModel):
    text: str
    session_id: Optional[str] = "default"

class ProactiveRequest(BaseModel):
    title: str = "Học bài"
    snooze_count: int = 0
    app_to_open: str = ""

class DialogueRequest(BaseModel):
    user_text: str
    in_conversation: bool = False
    session_id: Optional[str] = "default"
    generate_audio: Optional[bool] = False

@app.get("/health")
async def health():
    return {"status": "ok", "service": "nova_voice_assistant"}

@app.get("/api/cuppy-tts")
async def get_cuppy_tts(text: str):
    """API sinh giọng nói Cuppy siêu tốc bằng Vieneu model v3turbo"""
    if not text or not text.strip():
        return JSONResponse(status_code=400, content={"error": "Text is required"})
    # Vieneu suy luận đồng bộ và có thể mất hàng chục giây. Không chặn event loop
    # vì app vẫn phải nhận câu trả lời hội thoại trong lúc TTS đang tạo chunk khác.
    def synthesize_cuppy():
        from core.vieneu_cuppy import cuppy_engine
        return cuppy_engine.synthesize(text.strip())

    wav_path = await run_in_threadpool(synthesize_cuppy)
    if wav_path and wav_path.exists():
        return FileResponse(wav_path, media_type="audio/wav")
    return JSONResponse(status_code=500, content={"error": "Could not synthesize audio"})

@app.api_route("/api/tts", methods=["GET", "POST"])
async def get_tts_alias(req: Request, text: Optional[str] = None):
    """F-13 & BE-01: Hỗ trợ cả GET /api/tts?text= và POST /api/tts {text: ...}"""
    target_text = text
    if not target_text and req.method == "POST":
        try:
            body = await req.json()
            target_text = body.get("text") or body.get("input")
        except Exception:
            pass
    if not target_text:
        target_text = req.query_params.get("text")
    return await get_cuppy_tts(target_text or "")

@app.post("/v1/audio/speech")
async def openai_speech_alias(req: Request):
    """F-13: Tương thích chuẩn OpenAI Audio Speech endpoint"""
    try:
        data = await req.json()
    except Exception:
        data = {}
    text = data.get("input") or data.get("text") or ""
    return await get_cuppy_tts(text)

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Phục vụ file âm thanh giọng Cuppy cho điện thoại phát qua loa (F-14)"""
    file_path = AUDIO_CACHE_DIR / filename
    if file_path.exists():
        try:
            with open(file_path, "rb") as f:
                header = f.read(12)
            if header.startswith(b"RIFF") and b"WAVE" in header:
                return FileResponse(file_path, media_type="audio/wav")
        except Exception:
            pass
        return FileResponse(file_path, media_type="audio/mpeg")
    return JSONResponse(status_code=404, content={"error": "Audio not found"})

@app.get("/api/tasks")
async def list_tasks():
    """Lấy danh sách các nhiệm vụ kỷ luật"""
    tasks = get_all_active_tasks()
    return {"tasks": tasks}

@app.post("/api/proactive-prompt")
async def get_proactive_prompt(req: ProactiveRequest):
    """Sinh câu thoại đôn đốc nhắc việc kèm câu hỏi đuôi trò chuyện và audio Cuppy"""
    task_mock = {
        "title": req.title,
        "snooze_count": req.snooze_count,
        "app_to_open": req.app_to_open
    }
    prompt = await run_in_threadpool(assistant_agent.generate_proactive_prompt, task_mock)
    audio_path = await run_in_threadpool(tts_engine.synthesize, prompt)
    audio_url = f"/audio/{Path(audio_path).name}" if audio_path else ""
    return {
        "prompt": prompt,
        "audio_url": audio_url
    }

@app.post("/api/dialogue")
async def handle_dialogue(req: DialogueRequest):
    """
    Xử lý đàm thoại 2 chiều thông minh (F-07: Cách ly phiên theo session_id):
    1. Kiểm tra từ khóa dừng: 'kết thúc', 'thôi', 'tạm biệt' -> Tắt mic
    2. Nếu người dùng nói 'có', 'ừ' sau lời nhắc -> Bật đàm thoại liên tục
    3. Tự động giữ mở mic sau mỗi câu trả lời nếu đang trong phiên
    """
    clean_text = req.user_text.strip()
    session_id = req.session_id or "default"
    
    # 1. Kiểm tra người dùng muốn kết thúc cuộc trò chuyện
    if assistant_agent.is_exit_phrase(clean_text):
        assistant_agent.clear_history(session_id=session_id)
        reply = "Okela, cậu tập trung làm việc nha! Tớ tắt mic đây, khi nào cần cứ gọi Hey Nova nhé!"
        audio_path = await run_in_threadpool(tts_engine.synthesize, reply) if req.generate_audio else None
        return {
            "reply": reply,
            "audio_url": f"/audio/{Path(audio_path).name}" if audio_path else "",
            "action": "exit_conversation",
            "continue_listening": False
        }
        
    # 2. Kiểm tra người dùng đồng ý trò chuyện sau lời nhắc
    if not req.in_conversation and assistant_agent.is_agree_to_chat(clean_text):
        reply = "Okela, buôn chuyện tí nào! Cậu đang cảm thấy thế nào rồi?"
        audio_path = await run_in_threadpool(tts_engine.synthesize, reply) if req.generate_audio else None
        return {
            "reply": reply,
            "audio_url": f"/audio/{Path(audio_path).name}" if audio_path else "",
            "action": "start_conversation",
            "continue_listening": True
        }
        
    # 3. Xử lý câu lệnh hoặc hội thoại thông thường qua Gemini (cách ly theo session_id)
    reply, action = await run_in_threadpool(assistant_agent.process_command, clean_text, session_id=session_id)
    if isinstance(action, dict) and action.get("action") == "upstream_error":
        error_code = action.get("error_code", "upstream_error")
        status_code = 429 if error_code == "quota_exceeded" else 503
        return JSONResponse(status_code=status_code, content={
            "error": reply,
            "error_code": error_code,
            "retryable": bool(action.get("retryable", False))
        })
    audio_path = await run_in_threadpool(tts_engine.synthesize, reply) if req.generate_audio else None
    
    return {
        "reply": reply,
        "audio_url": f"/audio/{Path(audio_path).name}" if audio_path else "",
        "action": action.get("action", "chat") if isinstance(action, dict) else "chat",
        "continue_listening": req.in_conversation
    }

@app.post("/api/chat")
async def chat_text(req: ChatRequest):
    """Nhận câu nói dạng text từ điện thoại, sinh câu trả lời bạn thân & file giọng Cuppy (F-07: session-isolated)"""
    session_id = req.session_id or "default"
    reply, action = await run_in_threadpool(assistant_agent.process_command, req.text, session_id=session_id)
    if isinstance(action, dict) and action.get("action") == "upstream_error":
        error_code = action.get("error_code", "upstream_error")
        status_code = 429 if error_code == "quota_exceeded" else 503
        return JSONResponse(status_code=status_code, content={
            "error": reply,
            "error_code": error_code,
            "retryable": bool(action.get("retryable", False))
        })
    audio_path = await run_in_threadpool(tts_engine.synthesize, reply)
    audio_url = f"/audio/{Path(audio_path).name}" if audio_path else ""
    return {
        "reply": reply,
        "action": action,
        "audio_url": audio_url
    }

@app.post("/api/voice-upload")
async def voice_upload(file: UploadFile = File(...), in_conversation: bool = Form(False), session_id: str = Form("default")):
    """Nhận file âm thanh thu từ mic điện thoại, dùng Groq Whisper dịch & Cuppy đọc lại (F-15: giới hạn 15MB)"""
    MAX_UPLOAD_BYTES = 15 * 1024 * 1024
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        return JSONResponse(status_code=413, content={"error": "File âm thanh vượt quá giới hạn 15MB"})

    safe_filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', file.filename or "audio.wav")
    temp_path = DATA_DIR / f"upload_{int(time.time()*1000)}_{safe_filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(content)
        
    user_text = await run_in_threadpool(stt_engine.transcribe_audio_file, str(temp_path))
    if temp_path.exists():
        try:
            temp_path.unlink()
        except Exception:
            pass
        
    if not user_text:
        return {"error": "Không nghe rõ câu nói", "continue_listening": in_conversation}
        
    dialogue_req = DialogueRequest(user_text=user_text, in_conversation=in_conversation, session_id=session_id)
    result = await handle_dialogue(dialogue_req)
    result["user_text"] = user_text
    return result

@app.get("/", response_class=HTMLResponse)
async def mobile_index():
    """Giao diện Web App tương tác trên điện thoại Android"""
    html_file = ROOT_DIR / "mobile_ui.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<h1>Nova Mobile API is running</h1>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

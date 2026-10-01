import os
import sys
import re
import uuid
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
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

from config import (
    USER_NAME, ASSISTANT_NAME, DATA_DIR,
    SERVER_VERSION, MIN_CLIENT_VERSION,
    GROQ_API_KEY, GEMINI_API_KEY, LLM_PROVIDER
)
from core.agent import assistant_agent
from core.tts import tts_engine, AUDIO_CACHE_DIR
from core.stt import stt_engine
from core.database import get_all_active_tasks, add_task, init_db, get_db_connection
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

@app.middleware("http")
async def version_handshake_middleware(request: Request, call_next):
    """V4-17: Version Handshake Middleware"""
    response = await call_next(request)
    response.headers["X-Nova-Server-Version"] = SERVER_VERSION
    response.headers["X-Nova-Min-Client-Version"] = MIN_CLIENT_VERSION
    return response

@app.on_event("startup")
async def startup_event():
    """V4-02: Production startup validation and migration"""
    try:
        init_db()
        conn = get_db_connection(timeout=5.0)
        conn.execute("SELECT 1 FROM tasks LIMIT 1")
        conn.close()
        print(f"[STARTUP] SQLite Database: OK (WAL mode, {SERVER_VERSION})")
    except Exception as e:
        print(f"[STARTUP ERROR] Database initialization failed: {e}")

    llm_ready = bool(GROQ_API_KEY or GEMINI_API_KEY)
    if llm_ready:
        print(f"[STARTUP] LLM Provider: OK ({LLM_PROVIDER})")
    else:
        print(f"[STARTUP WARNING] LLM Provider degraded: Neither GROQ_API_KEY nor GEMINI_API_KEY configured.")

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

@app.get("/download")
async def download_page():
    page_path = ROOT_DIR / "static" / "download.html"
    if page_path.exists():
        return FileResponse(page_path, media_type="text/html")
    return FileResponse(ROOT_DIR / "static" / "Nova_Assistant.apk", media_type="application/vnd.android.package-archive", filename="Nova_Assistant.apk")

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
    turn_id: Optional[str] = None

class ProactiveRequest(BaseModel):
    title: str = "Học bài"
    snooze_count: int = 0
    app_to_open: str = ""

class DialogueRequest(BaseModel):
    user_text: str
    in_conversation: bool = False
    session_id: Optional[str] = "default"
    generate_audio: Optional[bool] = False
    turn_id: Optional[str] = None

class DialogueResponse(BaseModel):
    turn_id: str
    reply: str
    audio_url: Optional[str] = ""
    action: Dict[str, Any]
    continue_listening: bool = False

class ChatResponse(BaseModel):
    turn_id: str
    reply: str
    audio_url: Optional[str] = ""
    action: Dict[str, Any]

class DeviceAckRequest(BaseModel):
    status: str  # "confirmed" | "device_schedule_failed"
    error: Optional[str] = None

@app.get("/health")
async def health():
    return {"status": "ok", "service": "nova_voice_assistant"}

@app.get("/health/ready")
async def health_ready():
    """Kiểm tra toàn diện trạng thái sẵn sàng của backend (V4-01, V4-02, V4-04, V4-17)"""
    db_ok = False
    try:
        conn = get_db_connection(timeout=2.0)
        conn.execute("SELECT 1 FROM tasks LIMIT 1")
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    llm_ok = bool(GROQ_API_KEY or GEMINI_API_KEY)
    tts_health = tts_engine.get_tts_health()
    tts_ok = bool(tts_health.get("tts_primary_ready") or tts_health.get("tts_fallback_ready", True))
    overall_ok = db_ok and tts_ok
    status_code = 200 if overall_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "ok": overall_ok,
            "version": SERVER_VERSION,
            "server_version": SERVER_VERSION,
            "min_client_version": MIN_CLIENT_VERSION,
            "llm": llm_ok,
            "tts": tts_ok,
            "database": db_ok,
            "tts_primary": tts_health.get("tts_primary", "vieneu"),
            "tts_primary_ready": tts_health.get("tts_primary_ready", False),
            "tts_voice_name": tts_health.get("voice_name", "Xuân Tiên"),
            "tts_fallback_ready": tts_health.get("tts_fallback_ready", True)
        }
    )

@app.get("/health/voice")
async def health_voice():
    """Kiểm tra sức khỏe động cơ giọng nói Nova Neural TTS (Xuân Tiên)"""
    try:
        from core.vieneu_engine import nova_engine
        h = nova_engine.get_health()
        status_code = 200 if h.get("model_loaded") else 503
        return JSONResponse(status_code=status_code, content=h)
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e), "model_loaded": False})

@app.get("/api/cuppy-tts")
@app.get("/api/nova-tts")
async def get_cuppy_tts(text: str):
    """API sinh giọng nói Nova Xuân Tiên (hỗ trợ cả /api/nova-tts và tương thích ngược với /api/cuppy-tts)"""
    if not text or not text.strip():
        return JSONResponse(status_code=400, content={"error": "Text is required"})

    def synthesize_safe():
        try:
            from core.vieneu_engine import nova_engine
            p = nova_engine.synthesize(text.strip())
            if p and p.exists() and p.stat().st_size > 1000:
                return str(p)
        except Exception:
            pass
        return tts_engine.synthesize(text.strip())

    audio_path = await run_in_threadpool(synthesize_safe)
    if audio_path and Path(audio_path).exists() and Path(audio_path).stat().st_size > 500:
        media_type = "audio/wav" if str(audio_path).endswith(".wav") else "audio/mpeg"
        return FileResponse(audio_path, media_type=media_type)
    return JSONResponse(status_code=503, content={"error": "Voice synthesis failed"})

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

@app.post("/api/reminders/{reminder_id}/device-ack")
async def device_ack_reminder(reminder_id: str, req: DeviceAckRequest):
    """Xác nhận trạng thái đặt lịch phần cứng Android (Stage 9 & 11, P1-03)"""
    if req.status not in ["confirmed", "device_schedule_failed"]:
        return JSONResponse(status_code=422, content={"error": "Invalid status", "status": req.status})

    from core.database import get_task_by_reminder_id, update_task_device_ack
    task = get_task_by_reminder_id(reminder_id)
    if not task:
        return JSONResponse(status_code=404, content={"error": "Reminder not found", "reminder_id": reminder_id})

    updated, reason = update_task_device_ack(reminder_id, req.status, req.error)
    if reason == "invalid_transition_from_confirmed":
        return JSONResponse(status_code=409, content={"error": "Cannot transition from confirmed to failed", "reminder_id": reminder_id})
    return {"ok": True, "reminder_id": reminder_id, "status": req.status, "updated": bool(updated)}

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

class DialogueServiceResult:
    def __init__(self, status_code: int, data: Dict[str, Any], is_error: bool = False):
        self.status_code = status_code
        self.data = data
        self.is_error = is_error

async def process_dialogue(req: DialogueRequest, endpoint: str = "dialogue") -> DialogueServiceResult:
    """Core dialogue service layer cô lập logic nghiệp vụ khỏi HTTP transport (P0-08, P0-09)"""
    clean_text = req.user_text.strip()
    session_id = req.session_id or "default"
    turn_id = req.turn_id.strip() if (req.turn_id and req.turn_id.strip()) else str(uuid.uuid4())

    from core.database import compute_request_hash, claim_turn, complete_turn, fail_turn
    req_hash = compute_request_hash(endpoint, session_id, turn_id, clean_text, req.in_conversation, req.generate_audio)
    claim_status, cached_response = claim_turn(session_id, turn_id, req_hash)

    if claim_status == "completed" and cached_response:
        return DialogueServiceResult(200, cached_response)
    elif claim_status == "mismatch":
        return DialogueServiceResult(409, {"error": "Turn ID already used with different payload", "turn_id": turn_id}, is_error=True)
    elif claim_status == "processing":
        return DialogueServiceResult(409, {"error": "Turn is currently being processed", "turn_id": turn_id, "retryable": True}, is_error=True)

    try:
        # 1. Kiểm tra người dùng muốn kết thúc cuộc trò chuyện
        if assistant_agent.is_exit_phrase(clean_text):
            assistant_agent.clear_history(session_id=session_id)
            reply = "Okela, cậu tập trung làm việc nha! Tớ tắt mic đây, khi nào cần cứ gọi Hey Nova nhé!"
            audio_path = await run_in_threadpool(tts_engine.synthesize, reply) if req.generate_audio else None
            resp_data = {
                "turn_id": turn_id,
                "reply": reply,
                "audio_url": f"/audio/{Path(audio_path).name}" if audio_path else "",
                "action": {"type": "exit_conversation", "action": "exit_conversation"},
                "continue_listening": False
            }
            complete_turn(session_id, turn_id, resp_data)
            return DialogueServiceResult(200, resp_data)

        # 2. Kiểm tra người dùng đồng ý trò chuyện sau lời nhắc
        if not req.in_conversation and assistant_agent.is_agree_to_chat(clean_text):
            reply = "Okela, buôn chuyện tí nào! Cậu đang cảm thấy thế nào rồi?"
            audio_path = await run_in_threadpool(tts_engine.synthesize, reply) if req.generate_audio else None
            resp_data = {
                "turn_id": turn_id,
                "reply": reply,
                "audio_url": f"/audio/{Path(audio_path).name}" if audio_path else "",
                "action": {"type": "start_conversation", "action": "start_conversation"},
                "continue_listening": True
            }
            complete_turn(session_id, turn_id, resp_data)
            return DialogueServiceResult(200, resp_data)

        # 3. Xử lý câu lệnh hoặc hội thoại thông thường qua Gemini (cách ly theo session_id)
        reply, action = await run_in_threadpool(assistant_agent.process_command, clean_text, session_id=session_id)
        if isinstance(action, dict) and action.get("action") == "upstream_error":
            fail_turn(session_id, turn_id)
            error_code = action.get("error_code", "upstream_error")
            status_code = 429 if error_code == "quota_exceeded" else 503
            return DialogueServiceResult(status_code, {
                "turn_id": turn_id,
                "error": reply,
                "error_code": error_code,
                "retryable": bool(action.get("retryable", False))
            }, is_error=True)

        audio_path = await run_in_threadpool(tts_engine.synthesize, reply) if req.generate_audio else None
        formatted_action = action if isinstance(action, dict) else {"type": "chat", "action": action or "chat"}

        resp_data = {
            "turn_id": turn_id,
            "reply": reply,
            "audio_url": f"/audio/{Path(audio_path).name}" if audio_path else "",
            "action": formatted_action,
            "continue_listening": req.in_conversation
        }
        complete_turn(session_id, turn_id, resp_data)
        return DialogueServiceResult(200, resp_data)
    except Exception as e:
        fail_turn(session_id, turn_id)
        raise e

@app.post("/api/dialogue", response_model=DialogueResponse)
async def handle_dialogue(req: DialogueRequest):
    """
    Xử lý đàm thoại 2 chiều thông minh (V3.2: Service layer, Idempotency & crash recovery)
    """
    result = await process_dialogue(req, endpoint="dialogue")
    if result.is_error:
        return JSONResponse(status_code=result.status_code, content=result.data)
    return result.data

@app.post("/api/chat", response_model=ChatResponse)
async def chat_text(req: ChatRequest):
    """Nhận câu nói dạng text từ điện thoại, sinh câu trả lời bạn thân & file giọng Cuppy (V3.2: Idempotency)"""
    session_id = req.session_id or "default"
    turn_id = req.turn_id.strip() if (req.turn_id and req.turn_id.strip()) else str(uuid.uuid4())

    from core.database import compute_request_hash, claim_turn, complete_turn, fail_turn
    req_hash = compute_request_hash("chat", session_id, turn_id, req.text, False, False)
    claim_status, cached_response = claim_turn(session_id, turn_id, req_hash)

    if claim_status == "completed" and cached_response:
        return cached_response
    elif claim_status == "mismatch":
        return JSONResponse(status_code=409, content={"error": "Turn ID already used with different payload", "turn_id": turn_id})
    elif claim_status == "processing":
        return JSONResponse(status_code=409, content={"error": "Turn is currently being processed", "turn_id": turn_id, "retryable": True})

    try:
        reply, action = await run_in_threadpool(assistant_agent.process_command, req.text, session_id=session_id)
        if isinstance(action, dict) and action.get("action") == "upstream_error":
            fail_turn(session_id, turn_id)
            error_code = action.get("error_code", "upstream_error")
            status_code = 429 if error_code == "quota_exceeded" else 503
            return JSONResponse(status_code=status_code, content={
                "turn_id": turn_id,
                "error": reply,
                "error_code": error_code,
                "retryable": bool(action.get("retryable", False))
            })
        audio_path = await run_in_threadpool(tts_engine.synthesize, reply)
        audio_url = f"/audio/{Path(audio_path).name}" if audio_path else ""
        formatted_action = action if isinstance(action, dict) else {"type": "chat", "action": action or "chat"}
        resp_data = {
            "turn_id": turn_id,
            "reply": reply,
            "action": formatted_action,
            "audio_url": audio_url
        }
        complete_turn(session_id, turn_id, resp_data)
        return resp_data
    except Exception as e:
        fail_turn(session_id, turn_id)
        raise e

@app.post("/api/voice-upload")
async def voice_upload(
    file: UploadFile = File(...),
    in_conversation: bool = Form(False),
    session_id: str = Form("default"),
    turn_id: Optional[str] = Form(None)
):
    """Nhận file âm thanh thu từ mic điện thoại, dùng Groq Whisper dịch & Cuppy đọc lại (P0-08, P0-09)"""
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
        return {"error": "Không nghe rõ câu nói", "continue_listening": in_conversation, "turn_id": turn_id}
        
    dialogue_req = DialogueRequest(
        user_text=user_text,
        in_conversation=in_conversation,
        session_id=session_id,
        turn_id=turn_id,
        generate_audio=False
    )
    result = await process_dialogue(dialogue_req, endpoint="voice-upload")
    if result.is_error:
        return JSONResponse(status_code=result.status_code, content=result.data)

    resp = dict(result.data)
    resp["user_text"] = user_text
    return resp

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

from pydantic import BaseModel
from typing import Optional

class VoiceHealthResponse(BaseModel):
    status: str
    model_loaded: bool
    voice_loaded: bool
    cache_writable: bool
    warm: bool
    latency_ms: Optional[float] = None

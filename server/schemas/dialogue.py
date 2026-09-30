from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union

class TaskItem(BaseModel):
    task_id: Union[int, str]
    title: str
    scheduled_time: str
    scheduled_at_epoch_ms: Optional[int] = None
    timezone: str = "Asia/Ho_Chi_Minh"
    app_to_open: Optional[str] = ""

class ScheduleAction(BaseModel):
    type: str = "schedule_tasks"
    action: str = "schedule_tasks"  # backward compatibility
    task_ids: List[Union[int, str]] = Field(default_factory=list)
    summary: List[str] = Field(default_factory=list)
    tasks: List[TaskItem] = Field(default_factory=list)

class ClarifyAction(BaseModel):
    type: str = "schedule_requires_clarification"
    action: str = "schedule_requires_clarification"
    task_title: Optional[str] = ""
    reason: str = "missing_or_unparsed_time"

class OpenAppAction(BaseModel):
    type: str = "open_app"
    action: str = "open_app"
    app_name: str
    success: bool = True
    msg: Optional[str] = ""

class DialogueResponse(BaseModel):
    turn_id: str
    reply: str
    action: Union[ScheduleAction, ClarifyAction, OpenAppAction, Dict[str, Any], str] = "chat"
    audio_url: str = ""
    continue_listening: bool = False

import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone
import uuid
import logging
import requests
from typing import Dict, Any, Tuple, Optional, List

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import (
    LLM_PROVIDER,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    DEFAULT_MODEL,
    ASSISTANT_NAME,
    USER_NAME
)
from core.os_control import open_application
from core.database import (
    add_task, 
    add_tasks_atomic,
    update_task_status, 
    snooze_task, 
    get_all_active_tasks,
    log_interaction
)

logger = logging.getLogger("Agent")

SCHEDULE_TOOLS = [{
    "function_declarations": [{
        "name": "schedule_tasks",
        "description": "Lên lịch một hoặc nhiều nhiệm vụ nhắc nhở cho người dùng khi người dùng yêu cầu hẹn giờ hoặc khi hai bên đã thảo luận thống nhất xong lịch trình.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tasks": {
                    "type": "ARRAY",
                    "description": "Danh sách các nhiệm vụ cần lên lịch",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "title": {"type": "STRING", "description": "Tên nhiệm vụ hoặc công việc cần làm"},
                            "scheduled_time": {"type": "STRING", "description": "Giờ hẹn thông báo, ví dụ '14:30', '15:00', '18h', hoặc '+15m'"},
                            "app_to_open": {"type": "STRING", "description": "Tên ứng dụng mở kèm nếu có (vd: code, chrome, spotify, youtube)"}
                        },
                        "required": ["title", "scheduled_time"]
                    }
                }
            },
            "required": ["tasks"]
        }
    }]
}]

try:
    from zoneinfo import ZoneInfo
    VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:
    VN_TZ = timezone(timedelta(hours=7))

def parse_time_str(time_str: str) -> str:
    """Chuyển đổi chuỗi thời gian tự nhiên thành YYYY-MM-DD HH:MM theo múi giờ Việt Nam"""
    if not time_str or not time_str.strip():
        return ""
    now = datetime.now(VN_TZ) if VN_TZ else datetime.now()
    clean = time_str.strip().lower()
    
    # 1. Dạng tương đối: '+10m', '15 phút', 'sau 30p'
    m_rel = re.search(r'(\d+)\s*(?:m|p|phút)', clean)
    if '+' in clean or 'phút' in clean or 'sau' in clean:
        if m_rel:
            minutes = int(m_rel.group(1))
            return (now + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")
            
    # 2. Dạng giờ cụ thể: '14h', '14:30', '15h30'
    m_hm = re.search(r'(\d{1,2})[:hH](\d{0,2})', clean)
    if m_hm:
        h = int(m_hm.group(1))
        m = int(m_hm.group(2)) if m_hm.group(2) else 0
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        # Nếu giờ đã qua trong ngày (quá 2 phút trước), đặt lịch cho ngày mai
        if target < now - timedelta(minutes=2):
            target += timedelta(days=1)
        return target.strftime("%Y-%m-%d %H:%M")
        
    # 3. Yêu cầu hoãn rõ ràng ("lát nữa", "chút nữa", "tẹo nữa")
    if any(k in clean for k in ["lát nữa", "chút nữa", "tẹo nữa"]):
        return (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")

    # F-12: Tuyệt đối không tự ý fallback +10m nếu không phân tích được thời gian
    return ""


class AssistantAgent:
    def __init__(self):
        self.gemini_key = GEMINI_API_KEY
        self.groq_key = GROQ_API_KEY
        # Dùng model còn hỗ trợ generateContent; vẫn cho phép cấu hình qua GEMINI_MODEL.
        import os
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
        # F-07: Cách ly lịch sử hội thoại theo session_id, tránh dùng chung giữa các người dùng
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}

    def get_session_history(self, session_id: str = "default") -> List[Dict[str, Any]]:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def clear_history(self, session_id: str = "default"):
        """Xóa bộ nhớ cuộc trò chuyện khi kết thúc phiên theo session_id"""
        if session_id in self.sessions:
            self.sessions[session_id] = []

    def get_system_prompt(self, current_task: Optional[Dict[str, Any]] = None) -> str:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        task_info = f"Nhiệm vụ đang nhắc: {current_task.get('title')}" if current_task else "Không có nhiệm vụ nhắc nhở tức thì."
        return (
            f"Bạn là {ASSISTANT_NAME}, trợ lý ảo thông minh, bạn thân kỷ luật và ấm áp của {USER_NAME}.\n"
            f"Thời điểm hiện tại: {now_str}.\n"
            f"Trạng thái công việc: {task_info}\n"
            f"Xưng hô: 'tớ - cậu'.\n"
            f"QUY TẮC:\n"
            f"1. Trả lời tự nhiên, ấm áp, thông minh, ngắn gọn như trò chuyện ngoài đời.\n"
            f"2. Nếu người dùng yêu cầu kể chuyện, hãy kể câu chuyện trọn vẹn, giàu cảm xúc.\n"
            f"3. Không sử dụng ký tự Markdown (*, #, gạch đầu dòng) để máy đọc mượt mà.\n"
            f"4. Khi người dùng muốn hẹn giờ, lên lịch, hãy gọi function schedule_tasks."
        )

    def _call_gemini_chat(self, user_text: str, current_task: Optional[Dict[str, Any]] = None, session_id: str = "default") -> Tuple[str, Dict[str, Any]]:
        """Gửi tin nhắn kèm lịch sử hội thoại lên Gemini và xử lý Tool Calling (F-07: session-isolated)"""
        if not self.gemini_key:
            return "Nova chưa được cấu hình khóa AI trên máy chủ.", {"action": "upstream_error", "error_code": "missing_api_key", "retryable": False}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
        
        # Chỉ ghi lịch sử khi request thành công để một lượt lỗi không bị gửi lặp ở lần thử sau.
        history = self.get_session_history(session_id) + [{
            "role": "user",
            "parts": [{"text": user_text}]
        }]
        
        # Giữ lại tối đa 12 lượt hội thoại gần nhất để vừa nhanh vừa nhớ ngữ cảnh
        if len(history) > 12:
            history = history[-12:]

        payload = {
            "systemInstruction": {
                "parts": [{"text": self.get_system_prompt(current_task)}]
            },
            "contents": history,
            "tools": SCHEDULE_TOOLS,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800
            }
        }

        try:
            res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
            if res.status_code == 200:
                data = res.json()
                candidate = data['candidates'][0]
                content = candidate.get('content', {})
                parts = content.get('parts', [])
                
                reply_text = ""
                action_result = {"action": "chat"}

                for part in parts:
                    # 1. Kiểm tra nếu Gemini gọi function `schedule_tasks`
                    if "functionCall" in part:
                        fc = part["functionCall"]
                        if fc.get("name") == "schedule_tasks":
                            args = fc.get("args", {})
                            tasks_list = args.get("tasks", [])
                            scheduled_summaries = []
                            detailed_tasks = []

                            # BƯỚC 1 (PHASE 7 ATOMIC VALIDATION): Kiểm tra toàn bộ danh sách TRƯỚC KHI ghi CSDL
                            validated_tasks = []
                            for t in tasks_list:
                                t_title = t.get("title", "Nhiệm vụ")
                                t_raw_time = t.get("scheduled_time", "")
                                t_app = t.get("app_to_open", "")
                                formatted_time = parse_time_str(t_raw_time)
                                
                                if not formatted_time:
                                    # Nếu BẤT KỲ task nào không parse được thời gian: KHÔNG CHÈN BẤT KỲ TASK NÀO VÀO CSDL
                                    reply_text = f"Tớ nghe rõ là cậu muốn nhắc việc '{t_title}', nhưng chưa rõ là vào lúc nào. Cậu muốn tớ nhắc lúc mấy giờ (ví dụ 14h30 hoặc sau 15 phút)?"
                                    action_result = {
                                        "type": "schedule_requires_clarification",
                                        "action": "schedule_requires_clarification",
                                        "task_title": t_title,
                                        "reason": "missing_or_unparsed_time"
                                    }
                                    return reply_text, action_result

                                # BƯỚC 2 (PHASE 6 TIMEZONE CONVERSION): Chuyển đổi timestamp có múi giờ VN_TZ
                                try:
                                    dt = datetime.strptime(formatted_time, "%Y-%m-%d %H:%M")
                                    dt = dt.replace(tzinfo=VN_TZ)
                                    epoch_ms = int(dt.timestamp() * 1000)
                                except Exception:
                                    epoch_ms = None

                                validated_tasks.append({
                                    "reminder_id": str(uuid.uuid4()),
                                    "title": t_title,
                                    "scheduled_time": formatted_time,
                                    "epoch_ms": epoch_ms,
                                    "app_to_open": t_app
                                })

                            # BƯỚC 3 (PHASE 7 ATOMIC INSERT): Chèn toàn bộ các task hợp lệ trong 1 transaction
                            created_task_ids = add_tasks_atomic([
                                {
                                    "title": vt["title"],
                                    "scheduled_time": vt["scheduled_time"],
                                    "app_to_open": vt["app_to_open"]
                                } for vt in validated_tasks
                            ])

                            for idx, vt in enumerate(validated_tasks):
                                task_id = created_task_ids[idx] if idx < len(created_task_ids) else (idx + 1)
                                time_display = vt["scheduled_time"].split(" ")[-1]
                                scheduled_summaries.append(f"{vt['title']} lúc {time_display}")
                                detailed_tasks.append({
                                    "reminder_id": vt["reminder_id"],
                                    "task_id": task_id,
                                    "title": vt["title"],
                                    "scheduled_time": vt["scheduled_time"],
                                    "scheduled_at_epoch_ms": vt["epoch_ms"],
                                    "timezone": "Asia/Ho_Chi_Minh",
                                    "app_to_open": vt["app_to_open"]
                                })

                            action_result = {
                                "type": "schedule_tasks",
                                "action": "schedule_tasks",
                                "task_ids": created_task_ids,
                                "summary": scheduled_summaries,
                                "tasks": detailed_tasks
                            }

                            if scheduled_summaries:
                                items_str = ", ".join(scheduled_summaries)
                                reply_text = f"Chốt đơn luôn! Tớ đã ghi nhớ lịch: {items_str}. Đến giờ tớ sẽ réo cậu ngay, chuẩn bị tinh thần tập trung làm việc nha!"
                            else:
                                reply_text = "Tớ đã ghi nhận lịch của cậu rồi nhé!"
                            break
                            
                    # 2. Lấy câu trả lời văn bản thông thường
                    if "text" in part:
                        reply_text += part["text"]

                # Làm sạch ký tự markdown cho giọng đọc Cuppy
                reply_text = reply_text.replace("*", "").replace("#", "").strip()
                if not reply_text:
                    reply_text = "Tớ nghe rồi nè! Cậu có muốn tớ nhắc việc gì hay mở app gì không?"

                # Lưu câu trả lời vào lịch sử session
                history.append({
                    "role": "model",
                    "parts": [{"text": reply_text}]
                })
                self.sessions[session_id] = history[-12:]
                 
                return reply_text, action_result
            else:
                logger.warning("Gemini API trả HTTP %s cho model %s", res.status_code, self.gemini_model)
                if res.status_code == 404:
                    return "Mô hình AI đang cấu hình không còn khả dụng.", {"action": "upstream_error", "error_code": "model_unavailable", "retryable": False}
                if res.status_code in (401, 403):
                    return "Máy chủ chưa xác thực được với dịch vụ AI.", {"action": "upstream_error", "error_code": "api_key_invalid", "retryable": False}
                if res.status_code == 429:
                    return "Dịch vụ AI đang giới hạn lượt dùng.", {"action": "upstream_error", "error_code": "quota_exceeded", "retryable": False}
                return "Dịch vụ AI đang tạm thời gặp lỗi.", {"action": "upstream_error", "error_code": "upstream_http_error", "retryable": res.status_code >= 500}
        except requests.exceptions.Timeout:
            logger.warning("Gemini API timeout cho model %s", self.gemini_model)
            return "Dịch vụ AI phản hồi quá lâu.", {"action": "upstream_error", "error_code": "upstream_timeout", "retryable": True}
        except requests.exceptions.RequestException as e:
            logger.warning("Không thể kết nối Gemini API: %s", type(e).__name__)
            return "Máy chủ không kết nối được với dịch vụ AI.", {"action": "upstream_error", "error_code": "upstream_network_error", "retryable": True}
        except (KeyError, IndexError, TypeError, ValueError) as e:
            logger.error("Phản hồi Gemini không hợp lệ: %s", type(e).__name__)
            return "Dịch vụ AI trả dữ liệu không hợp lệ.", {"action": "upstream_error", "error_code": "upstream_bad_response", "retryable": False}

    def process_command(self, user_text: str, current_task: Optional[Dict[str, Any]] = None, session_id: str = "default") -> Tuple[str, Dict[str, Any]]:
        """
        Xử lý yêu cầu thông minh kết hợp lệnh nhanh cực nhạy và trí tuệ Gemini.
        """
        user_text_clean = user_text.lower().strip()
        import random

        # A. Lệnh nhanh: Mở ứng dụng (siêu nhạy <10ms)
        if any(kw in user_text_clean for kw in ["mở", "bật", "khởi động", "chạy", "open", "launch"]):
            for prefix in ["mở ứng dụng", "mở phần mềm", "bật app", "mở trang", "mở web", "mở", "bật", "chạy"]:
                if prefix in user_text_clean:
                    target = user_text_clean.split(prefix, 1)[1].strip()
                    for filler in ["giúp tao", "giúp tớ", "giúp mình", "hộ tao", "hộ tớ", "cho tôi", "hộ với", "với nhé", "với", "nhé", "đi", "nào", "lên"]:
                        target = target.replace(filler, "").strip()
                    if target:
                        success, msg = open_application(target)
                        action_result = {"action": "open_app", "target": target, "status": success}
                        quick_replies = [
                            f"Okela, tớ mở {target.title()} cho cậu rồi nè. Bắt đầu ngay thôi nào!",
                            f"Xong rồi nhé, {target.title()} đã lên sóng! Làm việc nghiêm túc nha!",
                            f"Mở {target.title()} rồi đó, cấm lướt linh tinh đấy!"
                        ]
                        reply = random.choice(quick_replies)
                        log_interaction(current_task["id"] if current_task else None, user_text, reply, str(action_result))
                        return reply, action_result

        # B. Lệnh nhanh: Báo hoàn thành công việc
        if any(kw in user_text_clean for kw in ["xong rồi", "hoàn thành", "làm xong", "đã xong", "done"]):
            if current_task:
                update_task_status(current_task["id"], "completed")
                action_result = {"action": "complete_task", "task_id": current_task["id"]}
            else:
                action_result = {"action": "complete_task"}
            quick_dones = [
                "Đỉnh chóp luôn Cậu ơi! Làm xong sớm thế này có phải nhẹ đầu không!",
                "Giỏi quá ta! Hoàn thành xong một việc lớn rồi đấy, nghỉ tí rồi chiến tiếp nha!",
                "Tuyệt vời! Cậu làm tốt lắm, tớ đã lưu vào sổ hoàn thành rồi nhé!"
            ]
            reply = random.choice(quick_dones)
            log_interaction(current_task["id"] if current_task else None, user_text, reply, str(action_result))
            return reply, action_result

        # C. Lệnh nhanh: Xin hoãn giờ
        if any(kw in user_text_clean for kw in ["hoãn", "chờ", "đợi", "thêm phút", "lát nữa", "tí nữa", "snooze", "buồn ngủ"]):
            match_mins = re.search(r"(\d+)\s*(phút|p|m)", user_text_clean)
            minutes = int(match_mins.group(1)) if match_mins else 5
            if minutes > 15:
                minutes = 10
                
            if current_task:
                new_time = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")
                snooze_task(current_task["id"], new_time)
                action_result = {"action": "snooze", "minutes": minutes, "task_id": current_task["id"]}
            else:
                action_result = {"action": "snooze", "minutes": minutes}
                
            snooze_replies = [
                f"Lại lười rồi đúng không? Tớ cho đúng {minutes} phút thôi đấy, hết giờ là tớ réo tiếp đó nha!",
                f"Được rồi, gia hạn thêm {minutes} phút. Đừng có lướt điện thoại nữa đấy nhé!",
                f"Nghỉ {minutes} phút nữa thôi đấy, dậy làm việc ngay đi nha!"
            ]
            reply = random.choice(snooze_replies)
            log_interaction(current_task["id"] if current_task else None, user_text, reply, str(action_result))
            return reply, action_result

        # D. Toàn bộ hội thoại, thảo luận xếp lịch, hỏi đáp kiến thức -> Đưa vào Gemini
        reply, action_result = self._call_gemini_chat(user_text, current_task, session_id=session_id)
        log_interaction(current_task["id"] if current_task else None, user_text, reply, str(action_result))
        return reply, action_result

    def is_exit_phrase(self, text: str) -> bool:
        """Kiểm tra xem người dùng có muốn dừng cuộc trò chuyện không"""
        clean = text.lower().strip()
        exit_keywords = [
            "kết thúc", "dừng lại", "thôi", "tạm biệt", "bye", "nghỉ nói", 
            "tắt mic", "không nói nữa", "đi làm việc đây", "hết", "stop", "dừng", "thôi nha"
        ]
        return any(kw in clean for kw in exit_keywords)

    def is_agree_to_chat(self, text: str) -> bool:
        """Kiểm tra xem người dùng có đồng ý trò chuyện tiếp không"""
        clean = text.lower().strip()
        agree_keywords = [
            "có", "ừ", "uh", "ok", "nói chuyện đi", "buôn đi", "được", "yes", "nói đi", "trò chuyện", "muốn"
        ]
        return any(kw in clean for kw in agree_keywords)

    def generate_proactive_prompt(self, task: Dict[str, Any]) -> str:
        """Sinh lời thoại nhắc việc mang tính bạn thân đôn đốc kèm câu hỏi đuôi mời trò chuyện"""
        title = task["title"]
        snooze_count = task.get("snooze_count", 0)
        app = task.get("app_to_open", "")
        
        prompt_instruction = f"Đến giờ làm '{title}', bạn của bạn đã hoãn {snooze_count} lần. Hãy nói 1 câu giục bạn ấy vào bàn làm việc ngay lập tức, phong cách bạn thân dí dỏm."
        if app:
            prompt_instruction += f" Nhắc thêm là bạn sẵn sàng mở app {app} lên hộ."
            
        reply, _ = self._call_gemini_chat(prompt_instruction, task)
        base_prompt = reply if reply else f"Ê {USER_NAME}! Đến giờ làm {title} rồi kìa, vào bàn làm ngay thôi nào!"
        
        # Thêm câu hỏi đuôi thân thiện mời trò chuyện
        tag_question = " Cậu có muốn trò chuyện với tớ một chút không?"
        return base_prompt + tag_question


assistant_agent = AssistantAgent()
Agent = AssistantAgent

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    reply, act = assistant_agent.process_command("Chiều nay tớ muốn học tiếng Anh lúc 18h và tập gym lúc 20h, lên lịch giúp tớ nhé")
    print("Nova phản hồi:", reply)
    print("Action:", act)

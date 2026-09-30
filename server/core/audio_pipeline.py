import sys
import time
import logging
from pathlib import Path
from typing import Optional, Callable
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import WAKE_WORD, WAKE_WORD_SENSITIVITY, USER_NAME
from core.tts import tts_engine
from core.stt import stt_engine
from core.agent import assistant_agent

logger = logging.getLogger("AudioPipeline")

class AudioPipeline:
    def __init__(self, on_command_processed: Optional[Callable] = None):
        self.wake_word = WAKE_WORD
        self.sensitivity = WAKE_WORD_SENSITIVITY
        self.on_command_processed = on_command_processed
        self.oww_model = None
        self.is_listening = False

    def _init_wakeword_model(self):
        """Khởi tạo mô hình openWakeWord ONNX"""
        if self.oww_model is None:
            try:
                import openwakeword
                from openwakeword.model import Model
                # Tải mô hình ONNX hey_jarvis
                self.oww_model = Model(wakeword_models=['hey_jarvis_v0.1.onnx'], inference_framework="onnx")
                logger.info(f"Đã nạp openWakeWord models: {list(self.oww_model.models.keys())}")
            except Exception as e:
                logger.warning(f"Chưa thể nạp openWakeWord: {e}")


    def trigger_conversation(self, initial_prompt: Optional[str] = None):
        """Kích hoạt một phiên hội thoại giọng nói với người dùng"""
        if initial_prompt:
            tts_engine.speak(initial_prompt, wait_until_done=True)
        else:
            tts_engine.speak("Dạ, tớ nghe đây!", wait_until_done=True)

        print("\n[MIC ACTIVE] Đang lắng nghe câu nói của bạn...")
        user_speech = stt_engine.listen_from_microphone(timeout_sec=5)
        
        if not user_speech:
            print("[MIC TIMEOUT] Không phát hiện câu nói nào.")
            return

        print(f"[USER NÓI]: {user_speech}")
        
        # Não bộ AI phân tích và đưa ra hành động
        reply, action = assistant_agent.process_command(user_speech)
        print(f"[AI PHẢN HỒI]: {reply}")
        if action.get("action") != "none":
            print(f"[ACTION ĐÃ THỰC THI]: {action}")

        # Phát giọng nói trả lời
        tts_engine.speak(reply, wait_until_done=True)
        
        if self.on_command_processed:
            self.on_command_processed(user_speech, reply, action)

    def handle_proactive_reminder(self, task: dict):
        """Xử lý khi đến giờ nhắc nhở chủ động: Nhắc + Hỏi đuôi + Hội thoại liên tục nếu user đồng ý"""
        prompt = assistant_agent.generate_proactive_prompt(task)
        print(f"\n[NOVA NHẮC VIỆC]: {prompt}")
        tts_engine.speak(prompt, wait_until_done=True)

        # Lắng nghe câu trả lời xem user có muốn trò chuyện không
        print("\n[MIC LẮNG NGHE]: Cậu có muốn trò chuyện với tớ không? (Đang nghe...)")
        user_answer = stt_engine.listen_from_microphone(timeout_sec=6)
        print(f"[BẠN NÓI]: {user_answer if user_answer else '(Không nói gì)'}")

        if user_answer and assistant_agent.is_agree_to_chat(user_answer):
            self.start_continuous_dialogue_session()
        else:
            goodbye = "Được rồi nè, vậy cậu bắt tay vào việc luôn đi nha!"
            print(f"[NOVA]: {goodbye}")
            tts_engine.speak(goodbye, wait_until_done=True)

    def start_continuous_dialogue_session(self):
        """Bật chế độ hội thoại liên tục cho đến khi người dùng nói 'kết thúc'"""
        intro = "Okela, buôn chuyện tí nào! Cậu đang cảm thấy thế nào rồi?"
        print(f"\n[CHẾ ĐỘ HỘI THOẠI BẬT] - Nói 'kết thúc' hoặc 'tạm biệt' để dừng.")
        print(f"[NOVA]: {intro}")
        tts_engine.speak(intro, wait_until_done=True)

        while True:
            print("\n[MIC ĐANG MỞ LIÊN TỤC] Hãy nói chuyện với Nova...")
            user_speech = stt_engine.listen_from_microphone(timeout_sec=7)
            if not user_speech:
                continue

            print(f"[BẠN]: {user_speech}")
            
            # Kiểm tra từ khóa kết thúc
            if assistant_agent.is_exit_phrase(user_speech):
                bye_msg = "Okela, cậu tập trung làm việc nha! Tớ tắt mic đây, khi nào cần cứ gọi Hey Nova nhé!"
                print(f"[NOVA]: {bye_msg}")
                tts_engine.speak(bye_msg, wait_until_done=True)
                print("[ĐÃ TẮT MIC & KẾT THÚC HỘI THOẠI]")
                break

            # Xử lý hội thoại qua Gemini
            reply, action = assistant_agent.process_command(user_speech)
            print(f"[NOVA]: {reply}")
            tts_engine.speak(reply, wait_until_done=True)


    def start_wake_word_listener(self):
        """Vòng lặp chạy ngầm lắng nghe từ khóa kích hoạt (Wake Word)"""
        self._init_wakeword_model()
        if not self.oww_model:
            logger.warning("Không có mô hình Wake Word, chuyển sang chế độ gõ lệnh terminal.")
            return

        import sounddevice as sd
        self.is_listening = True
        CHUNK_SIZE = 1280 # 80ms tại 16000Hz theo chuẩn openWakeWord

        print(f"\n[WAKE WORD ACTIVATED] Hãy nói 'Hey Jarvis' hoặc từ khóa để kích hoạt...")

        def audio_callback(indata, frames, time_info, status):
            if not self.is_listening:
                return
            audio_data = np.frombuffer(indata, dtype=np.int16)
            
            # Đưa âm thanh vào model openWakeWord
            prediction = self.oww_model.predict(audio_data)
            
            for model_name, score in self.oww_model.prediction_buffer.items():
                if score[-1] >= self.sensitivity:
                    print(f"\n[WAKE WORD DETECTED] Phát hiện từ khóa '{model_name}' (Độ tin cậy: {score[-1]:.2f})!")
                    self.oww_model.reset()
                    # Tạm dừng stream để hội thoại
                    self.trigger_conversation()
                    break

        try:
            with sd.RawInputStream(samplerate=16000, blocksize=CHUNK_SIZE, dtype='int16',
                                   channels=1, callback=audio_callback):
                while self.is_listening:
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Lỗi micro stream: {e}")
        finally:
            self.is_listening = False

audio_pipeline = AudioPipeline()

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    print("Khởi chạy thử nghiệm Audio Pipeline...")
    audio_pipeline._init_wakeword_model()

# Smart Voice Assistant (Trợ Lý Giọng Nói Kỷ Luật & Nhắc Lịch Chủ Động)

Trợ lý ảo chạy trên laptop Windows với khả năng:
1. **Đánh thức bằng giọng nói (Wake Word):** Hỗ trợ gọi rảnh tay *"Hey Jarvis"* bằng mô hình `openWakeWord` (ONNX runtime cực nhẹ, chạy offline 100% trên CPU).
2. **Nhắc nhở chủ động 2 chiều (Proactive Accountability):** Đến giờ hẹn, trợ lý tự động cất tiếng nói đôn đốc, thương lượng nếu bạn lười hoặc xin hoãn giờ thay vì chỉ kêu chuông vô tri.
3. **Mở ứng dụng Windows nhanh:** Nhận diện giọng nói mở tức thì các app như VS Code, Chrome, Notion, Spotify, Excel, Word,...
4. **Voice Cloning (Clone giọng nói người thật):** Tích hợp ElevenLabs API để clone giọng người yêu, bạn thân hoặc mentor; tích hợp sẵn `edge-tts` tiếng Việt tự nhiên miễn phí 100%.

---

## Cấu Trúc Dự Án

```
smart_voice_assistant/
├── config.py                 # File nạp biến môi trường và thiết lập
├── main.py                   # Điểm khởi chạy chính (CLI + Voice + Scheduler)
├── requirements.txt          # Thư viện phụ thuộc
├── .env                      # File cấu hình API key, Persona, Voice ID
├── core/
│   ├── audio_pipeline.py     # Microphone stream, VAD, Wake-word listener
│   ├── stt.py                # Nhận diện giọng nói (Groq Whisper / Google STT)
│   ├── tts.py                # Phát giọng nói & Voice Cloning (ElevenLabs / Edge-TTS)
│   ├── agent.py              # Não bộ AI, phân tích tâm lý kỷ luật & Function Calling
│   ├── os_control.py         # Mở ứng dụng & phím tắt Windows
│   ├── scheduler.py          # Lên lịch nhắc nhở chủ động (APScheduler)
│   └── database.py           # Lưu trữ CSDL SQLite (Nhiệm vụ, lịch sử tương tác)
└── tests/
    └── test_flow.py          # Kịch bản kiểm thử toàn bộ pipeline
```

---

## Hướng Dẫn Sử Dụng

### 1. Cài đặt môi trường
Dự án yêu cầu **Python 3.10+**. Cài các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

### 2. Kiểm thử nhanh toàn bộ hệ thống
Chạy kịch bản kiểm thử tự động để kiểm tra CSDL, NLP, mở app và phát âm thanh:
```bash
python tests/test_flow.py
```

### 3. Khởi chạy Trợ lý ảo
Chạy file `main.py`:
```bash
python main.py
```

Tại màn hình giao diện, bạn có các lựa chọn:
* **Gõ câu nói tự nhiên:**
  * *"Mở Chrome giúp tớ"* -> Trợ lý mở Google Chrome và cất tiếng xác nhận.
  * *"Hôm nay có việc gì?"* -> Trợ lý đọc danh sách lịch trình.
  * *"Tớ buồn ngủ quá cho hoãn 10 phút đi"* -> Trợ lý thương lượng và dời lịch 10 phút.
* **Lên lịch nhanh:**
  * Gõ: `add <tên_việc> <số_phút> [tên_app]`
  * Ví dụ: `add Viết_code 1 code` (Nhắc viết code sau 1 phút và mở sẵn VS Code).
* **Bật lắng nghe Micro trực tiếp:**
  * Gõ `voice` -> Nói vào Micro của laptop.
* **Bật chế độ Wake-word rảnh tay:**
  * Gõ `listen` -> Nói *"Hey Jarvis"* bất kỳ lúc nào để đánh thức trợ lý.

---

## Hướng Dẫn Clone Giọng Nói Với ElevenLabs
1. Đăng ký tài khoản trên [ElevenLabs](https://elevenlabs.io/).
2. Vào mục **Voices** -> **Add Generative or Cloned Voice** -> **Instant Voice Cloning**.
3. Tải lên 1-2 phút file ghi âm giọng nói mẫu (người yêu, idol hoặc bạn thân).
4. Sao chép `Voice ID` và `API Key` dán vào file `.env`:
   ```env
   TTS_PROVIDER="elevenlabs"
   ELEVENLABS_API_KEY="your_api_key_here"
   ELEVENLABS_VOICE_ID="your_voice_id_here"
   ```
Mỗi khi trợ lý nhắc việc hay phản hồi, âm thanh cất lên sẽ chính là giọng của người đó!

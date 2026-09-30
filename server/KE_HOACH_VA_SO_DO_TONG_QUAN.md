# TÀI LIỆU THIẾT KẾ KIẾN TRÚC & KẾ HOẠCH TRIỂN KHAI
# TRỢ LÝ GIỌNG NÓI NHẮC LỊCH TRÌNH CHỦ ĐỘNG (PROACTIVE AI ACCOUNTABILITY ASSISTANT)

> **Hệ điều hành mục tiêu:** Windows (Laptop / PC)  
> **Ngôn ngữ:** Python 3.10+  
> **Phiên bản tài liệu:** 1.0.0  
> **Trạng thái:** Đã kiểm thử kỹ thuật (PoC Passed)

---

## MỤC LỤC
1. [TỔNG QUAN Ý TƯỞNG & ĐỊNH VỊ SẢN PHẨM](#1-tổng-quan-ý-tưởng--định-vị-sản-phẩm)
2. [SƠ ĐỒ KIẾN TRÚC TỔNG THỂ (SYSTEM ARCHITECTURE)](#2-sơ-đồ-kiến-trúc-tổng-thể-system-architecture)
3. [SƠ ĐỒ LUỒNG TƯƠNG TÁC THỜI GIAN THỰC (SEQUENCE FLOW)](#3-sơ-đồ-luồng-tương-tác-thời-gian-thực-sequence-flow)
4. [CHI TIẾT 3 LUỒNG HOẠT ĐỘNG CỐT LÕI](#4-chi-tiết-3-luồng-hoạt-động-cốt-lõi)
5. [CÔNG NGHỆ & CÁC REPO MÃ NGUỒN MỞ ĐI TRƯỚC](#5-công-nghệ--các-repo-mã-nguồn-mở-đi-trước)
6. [BÁO CÁO KẾT QUẢ KIỂM THỬ TRÊN MÁY TÍNH THỰC TẾ](#6-báo-cáo-kết-quả-kiểm-thử-trên-máy-tính-thực-tế)
7. [KẾ HOẠCH TRIỂN KHAI CHI TIẾT (ROADMAP 4 PHASE)](#7-kế-hoạch-triển-khai-chi-tiết-roadmap-4-phase)
8. [HƯỚNG DẪN CÀI ĐẶT & CHẠY DỰ ÁN](#8-hướng-dẫn-cài-đặt--chạy-dự-án)

---

## 1. TỔNG QUAN Ý TƯỞNG & ĐỊNH VỊ SẢN PHẨM

Hầu hết các ứng dụng quản lý thời gian hiện tại (Google Calendar, To-Do list, Báo thức) đều mang tính **Thụ động (Passive)**: Chỉ phát chuông reng reng hoặc hiện thông báo trên màn hình mà người dùng dễ dàng gạt bỏ để lướt mạng xã hội. Các chatbot AI như Siri hay Google Assistant thì mang tính **Phản ứng (Reactive)**: Phải đợi người dùng gọi mới trả lời.

### Sự Đột Phá Của Sản Phẩm:
* **Chủ động cất tiếng nói (Proactive Speech):** Đến giờ hẹn, trợ lý tự kích hoạt loa và gọi tên người dùng.
* **Tương tác đôn đốc 2 chiều (Accountability Loop):** Khi người dùng than mệt, xin hoãn, AI không đồng ý ngay mà biết thương lượng, khuyên nhủ, giữ kỷ luật thép.
* **Tự động mở công cụ làm việc:** Giảm tối đa lực cản hành vi (Friction) bằng cách tự khởi chạy các ứng dụng Windows (VS Code, Chrome, Notion, Excel,...).
* **Clone giọng nói cá nhân:** Sử dụng giọng của người thân, người yêu hoặc người bạn kính trọng để tạo sự gắn kết cảm xúc và động lực thực thi.

---

## 2. SƠ ĐỒ KIẾN TRÚC TỔNG THỂ (SYSTEM ARCHITECTURE)

```mermaid
flowchart TD
    subgraph HARDWARE [TẦNG PHẦN CỨNG & OS WINDOWS]
        Mic[Microphone Laptop]
        Speaker[Loa / Tai Nghe Laptop]
        WinOS[Windows OS: Process & Registry]
    end

    subgraph INPUT_OUTPUT [TẦNG ÂM THANH & TỪ KHÓA]
        WakeWord[openWakeWord: Bắt từ khóa 'Hey Jarvis']
        VAD[Silero VAD: Phát hiện giọng nói]
        STT[Whisper STT: Chuyển giọng nói -> Text]
        TTS[TTS & Voice Clone: ElevenLabs / Edge-TTS]
        Mic --> WakeWord
        Mic --> VAD --> STT
        TTS --> Speaker
    end

    subgraph BRAIN [TẦNG NÃO BỘ & PHÂN TÍCH TÂM LÝ]
        Agent[Accountability Agent: Phân tích ý định & Kỷ luật]
        Persona[Persona System Prompt: Cương nhu đúng lúc]
        ToolRouter{Bộ Điều Phối Hành Động}
        STT --> Agent
        Agent --> Persona --> ToolRouter
    end

    subgraph MANAGEMENT [TẦNG LỊCH TRÌNH & THỰC THI]
        Scheduler[APScheduler: Quét lịch mỗi 15 giây]
        Database[(SQLite: Nhiệm vụ, Trạng thái, Lịch sử hoãn)]
        OSController[Windows Controller: os.startfile / subprocess]
        
        Scheduler <--> Database
        Scheduler -->|Đến giờ hẹn| Agent
        ToolRouter -->|Mở App| OSController --> WinOS
        ToolRouter -->|Đổi Lịch/Hoãn| Database
        ToolRouter -->|Câu Nói Trả Lời| TTS
    end
```

---

## 3. SƠ ĐỒ LUỒNG TƯƠNG TÁC THỜI GIAN THỰC (SEQUENCE FLOW)

```mermaid
sequenceDiagram
    autonumber
    actor User as Người Dùng
    participant Sched as Background Scheduler
    participant Brain as AI Brain (Agent)
    participant TTS as Voice Clone TTS (Loa)
    participant Ear as Mic & Whisper STT
    participant OS as Windows Controller

    Note over Sched: Vòng lặp ngầm kiểm tra lịch hẹn
    Sched->>Sched: Phát hiện đến giờ hẹn (VD: 08:30 - Task "Lập trình AI")
    Sched->>Brain: Gọi Agent xử lý Task "Lập trình AI"
    Brain->>Brain: Sinh câu thoại nhắc việc mang tính thúc giục
    Brain->>TTS: Chuyển câu thoại thành âm thanh giọng clone
    TTS->>User: Phát qua loa: "8h30 rồi Nam! Vào bàn lập trình AI đi nào, tớ mở VS Code nhé?"

    Note over User,Ear: Tự động mở Microphone chờ phản hồi (5 giây)
    
    alt Trường hợp 1: Người dùng đồng ý làm việc
        User->>Ear: "Ừ, mở lên giúp tớ đi"
        Ear->>Brain: Text: "Ừ, mở lên giúp tớ đi"
        Brain->>OS: Lệnh: Khởi chạy "code.exe"
        OS->>User: Màn hình VS Code lập tức bật lên
        Brain->>TTS: "Tớ mở rồi nhé! Tập trung 45 phút rồi nghỉ giải lao!"
        TTS->>User: Phát câu khích lệ qua loa
    else Trường hợp 2: Người dùng trì hoãn / xin hoãn
        User->>Ear: "Buồn ngủ quá, cho nằm thêm 15 phút đi..."
        Ear->>Brain: Text: "Buồn ngủ quá, cho nằm thêm 15 phút đi"
        Brain->>Brain: Kiểm tra lịch sử: Đã hoãn lần nào chưa?
        Brain->>Sched: Cập nhật lùi lịch hẹn lại 10 phút
        Brain->>TTS: "Không được đâu! Cậu hoãn 2 lần rồi. Ngồi dậy rửa mặt đi, tớ chỉ cho đúng 5 phút thôi đấy!"
        TTS->>User: Phát giọng nhắc nhở nghiêm khắc
    else Trường hợp 3: Người dùng báo xong việc
        User->>Ear: "Tớ xong việc rồi nhé!"
        Ear->>Brain: Nhận diện task hoàn thành
        Brain->>Sched: Cập nhật status = 'completed' trong CSDL
        Brain->>TTS: "Tuyệt vời lắm! Cậu làm tốt lắm, đánh dấu hoàn thành rồi nhé."
        TTS->>User: Phát lời chúc mừng
    end

    Note over User,Ear: Nhánh kích hoạt tự do ngoài giờ hẹn:
    User->>Ear: "Hey Jarvis, mở Google Chrome"
    Ear->>OS: Bật Chrome tức thì
```

---

## 4. CHI TIẾT 3 LUỒNG HOẠT ĐỘNG CỐT LÕI

### 4.1. Luồng Nhắc Nhở Chủ Động (Proactive Notification)
* **Kích hoạt:** `APScheduler` chạy ngầm, truy vấn bảng `tasks` trong SQLite mỗi 15-30 giây.
* **Xử lý:** Khi `scheduled_time <= thời gian hiện tại`, không phát chuông tít tít đơn thuần mà chuyển sang module `core.agent.generate_proactive_prompt(task)`.
* **Cảm xúc:** Câu nói thay đổi tùy theo số lần người dùng đã hoãn (`snooze_count`):
  * Lần 0: Thân thiện, vui vẻ, mời gọi vào bàn.
  * Lần 1: Nghiêm túc hơn, nhấn mạnh cam kết.
  * Lần 2+: Cảnh báo báo động đỏ, dứt khoát.

### 4.2. Luồng Đối Thoại & Đôn Đốc Kỷ Luật (Accountability Negotiation)
* Sau khi phát loa, micro tự động mở để nghe câu trả lời trong khoảng 5-7 giây.
* Bộ lọc phân tích ngôn ngữ tự nhiên phân loại vào các nhóm ý định:
  * **Xin hoãn (Snooze):** Trích xuất số phút xin hoãn, nếu xin quá 30 phút sẽ tự ép về 10-15 phút.
  * **Chấp thuận (Accept/Open app):** Nhận diện tên ứng dụng cần mở.
  * **Hoàn thành (Done):** Cập nhật trạng thái `completed`.

### 4.3. Luồng Điều Khiển Hệ Điều Hành (Windows Automation)
* Sử dụng `os.startfile(app_name)` kết hợp bảng tra cứu ứng dụng thông minh.
* Hỗ trợ mở app không cần đường dẫn tuyệt đối: `code` (VS Code), `chrome`, `notepad`, `spotify`, `excel`, `word`, `calc`, `notion`...
* Hỗ trợ mở trực tiếp các website công việc (YouTube, GitHub, ChatGPT, Google Docs).

---

## 5. CÔNG NGHỆ & CÁC REPO MÃ NGUỒN MỞ ĐI TRƯỚC

| Thành phần | Thư viện / Repo kế thừa | Đánh giá & Ứng dụng |
| :--- | :--- | :--- |
| **Wake Word Detection** | [openWakeWord](https://github.com/dscripka/openWakeWord) | Chạy mô hình ONNX offline 100% trên CPU Windows, siêu nhẹ, không tốn GPU, nhận diện từ khóa *"Hey Jarvis"* chuẩn xác. |
| **Speech-to-Text (STT)** | `Groq Whisper` / `SpeechRecognition` | Groq Whisper đạt tốc độ cực nhanh (<300ms) hỗ trợ tiếng Việt; có sẵn Google STT tiếng Việt miễn phí dự phòng. |
| **Voice Cloning & TTS** | `ElevenLabs API` & `Edge-TTS` | ElevenLabs clone giọng người thật tự nhiên nhất thế giới; `Edge-TTS` cung cấp giọng đọc tiếng Việt mượt mà miễn phí không giới hạn. |
| **Quản lý lịch trình** | `APScheduler` + `sqlite3` | Lên lịch tác vụ định kỳ chính xác, nhẹ và ổn định khi chạy nền Windows Service. |
| **Điều khiển OS** | Tư tưởng từ [OpenInterpreter/01](https://github.com/OpenInterpreter/01) | Ánh xạ lệnh ngôn ngữ tự nhiên thành thao tác điều khiển ứng dụng Windows. |

---

## 6. BÁO CÁO KẾT QUẢ KIỂM THỬ TRÊN MÁY TÍNH THỰC TẾ

Toàn bộ hệ thống đã được chạy kiểm thử tự động trực tiếp trên máy laptop Windows thông qua kịch bản `tests/test_flow.py`:

```
=== KẾT QUẢ KIỂM THỬ THỰC TẾ TRÊN MÁY TÍNH ===
1. Khởi tạo SQLite Database                     -> ĐẠT (Tạo bảng tasks & interaction_logs)
2. Thử nghiệm lên lịch trình tự động            -> ĐẠT (Bắt đúng task đến hạn)
3. AI sinh câu nhắc đôn đốc theo ngữ cảnh       -> ĐẠT (Tự đề xuất mở kèm app notepad)
4. Phân tích phản hồi xin hoãn giờ              -> ĐẠT (Lùi lịch 10 phút, tăng biến đếm)
5. Lệnh giọng nói mở ứng dụng Windows           -> ĐẠT (Mở Notepad/Chrome tức thì)
6. Báo cáo hoàn thành nhiệm vụ                  -> ĐẠT (Đánh dấu status = 'completed')
7. Phát giọng nói qua Loa Realtek laptop        -> ĐẠT (Âm thanh trong trẻo, không trễ)
8. Tải mô hình Wake-word ONNX (hey_jarvis)      -> ĐẠT (Nạp thành công vào bộ nhớ)
---------------------------------------------------------------------------------
TỔNG KẾT: TẤT CẢ 8 HẠNG MỤC TEST HOÀN TOÀN KHÔNG CÓ LỖI (EXIT CODE 0)
```

---

## 7. KẾ HOẠCH TRIỂN KHAI CHI TIẾT (ROADMAP 4 PHASE)

```mermaid
gantt
    title Kế Hoạch Triển Khai Trợ Lý Kỷ Luật Giọng Nói
    dateFormat  YYYY-MM-DD
    section Phase 1: Nền Tảng & Logic
    Chốt kiến trúc & các luồng              :done,    p1_1, 2026-09-29, 1d
    Xây dựng PoC Engine (Code, DB, TTS, OS) :done,    p1_2, 2026-09-29, 1d
    section Phase 2: Cá Nhân Hóa & Giọng Clone
    Nạp mẫu giọng clone (ElevenLabs)        :active,  p2_1, 2026-09-30, 2d
    Test thực tế Micro trong phòng ồn       :         p2_2, 2026-10-02, 2d
    section Phase 3: Kỷ Luật & Mở Rộng
    Bổ sung App Windows thường dùng         :         p3_1, 2026-10-04, 2d
    Tích hợp Kỹ thuật Pomodoro & 2-phút     :         p3_2, 2026-10-06, 2d
    section Phase 4: Đóng Gói
    Tạo icon khay hệ thống (System Tray)    :         p4_1, 2026-10-08, 3d
    Giao diện Dashboard xem lịch trực quan  :         p4_2, 2026-10-11, 4d
```

---

## 8. HƯỚNG DẪN CÀI ĐẶT & CHẠY DỰ ÁN

### 8.1. Vị trí thư mục dự án
Mã nguồn nằm tại:  
`C:\Users\Lenovo\.gemini\antigravity\scratch\smart_voice_assistant`

### 8.2. Cấu hình file `.env`
Mở file `.env` để tùy chỉnh thông tin:
```ini
USER_NAME="Tên của bạn"
ASSISTANT_PERSONA="strict" # 'strict' (kỷ luật thép) hoặc 'caring' (nhẹ nhàng)
TTS_PROVIDER="edge-tts"    # Đổi sang "elevenlabs" khi có API key clone giọng
ELEVENLABS_API_KEY=""
ELEVENLABS_VOICE_ID=""     # ID giọng clone của bạn
```

### 8.3. Khởi chạy ứng dụng
Mở PowerShell tại thư mục dự án:
```powershell
python main.py
```
* Gõ câu lệnh trực tiếp: *"Mở Visual Studio Code giúp tớ"*.
* Thêm lịch hẹn nhanh: `add "Viết báo cáo" 1 code` (sau 1 phút tự động nhắc và mở VS Code).
* Bật nghe Wake-word ngầm: Gõ `listen` và nói *"Hey Jarvis"*.

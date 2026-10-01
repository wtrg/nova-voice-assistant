# 🔮 Nova Assistant — Trợ Lý Ảo Đàm Thoại AI Tiếng Việt Thông Minh (v2.0.0)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Android%20%7C%20Web%20%7C%20FastAPI-green.svg)](https://github.com/wtrg/nova-voice-assistant)
[![TTS Engine](https://img.shields.io/badge/TTS-Vieneu%20Cuppy%20v3turbo-purple.svg)](https://github.com/wtrg/nova-voice-assistant)
[![Client Tests](https://img.shields.io/badge/Client%20CI-Passing-brightgreen.svg)](https://github.com/wtrg/nova-voice-assistant/actions)
[![Backend Tests](https://img.shields.io/badge/Backend%20CI-25%2F25%20Passing-brightgreen.svg)](https://github.com/wtrg/nova-voice-assistant/actions)
[![Android CI](https://img.shields.io/badge/Android%20CI-Passing-brightgreen.svg)](https://github.com/wtrg/nova-voice-assistant/actions)

**Nova Assistant** là hệ thống trợ lý ảo đàm thoại hai chiều thời gian thực (Full-Duplex Voice Assistant) thuần tiếng Việt, kết hợp giữa ứng dụng di động Android gốc, Web View tương tác hiện đại và máy chủ AI đa tầng với giọng đọc Cuppy độc quyền.

---

## ⚡ Hướng Dẫn Cài Đặt Nhanh (Quick Start)

### 👤 Dành Cho Người Dùng Thông Thường (Normal User)
Cài đặt và sử dụng ngay trong **6 bước đơn giản** — không cần cài đặt Python, Node.js hay cấu hình máy chủ:

1. **Tải bộ cài đặt**: Tải file `Nova_Assistant.apk` mới nhất từ mục [Releases](https://github.com/wtrg/nova-voice-assistant/releases).
2. **Cài đặt APK**: Mở file `.apk` trên điện thoại Android của bạn và chọn **Cài đặt** (Cho phép cài ứng dụng từ nguồn không xác định nếu được hỏi).
3. **Mở Nova**: Nhấn vào biểu tượng Nova trên màn hình chính. Trình hướng dẫn khởi chạy lần đầu (First-Run Wizard) sẽ tự động xuất hiện.
4. **Cấp quyền cần thiết**: Cấp quyền **Microphone** (để nói chuyện) và quyền **Thông báo / Báo thức chính xác** (để đặt lịch nhắc nhở).
5. **(Tùy chọn) Đặt làm Trợ lý Mặc định**: Chọn Nova làm Default Assistant trong cài đặt hệ thống để gọi trợ lý bằng cử chỉ vuốt góc hoặc giữ nút nguồn.
6. **Sẵn sàng sử dụng**: Trò chuyện ngay với Nova bằng cách chạm vào quả cầu AI hoặc nói các câu lệnh như *"Nhắc tớ 10 phút nữa uống nước"*, *"Mở YouTube bài Nắng Ấm Xa Dần"*.

---

### 💻 Dành Cho Lập Trình Viên & Triển Khai Máy Chủ (Developer & Self-Hosting)

#### 1. Triển Khai Backend với Docker (Khuyến Nghị)
```bash
# Clone repository
git clone https://github.com/wtrg/nova-voice-assistant.git
cd nova-voice-assistant

# Thiết lập biến môi trường
cp server/.env.example server/.env
# Thêm GEMINI_API_KEY hoặc GROQ_API_KEY vào server/.env

# Khởi chạy bằng Docker Compose
docker compose up -d --build
```
Máy chủ sẽ tự động chạy tại cổng `8000` với SQLite WAL volume bền vững tại `./server/data`. Kiểm tra trạng thái: `GET http://localhost:8000/health/ready`.

#### 2. Chạy Backend Thủ Công (Python FastAPI)
Yêu cầu Python 3.11+ và FFmpeg:
```bash
cd server
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Chạy Kiểm Thử Backend (Pytest)
```bash
python -m pytest server/tests -v
```

#### 4. Biên Dịch & Kiểm Thử Client (Android / Web)
Yêu cầu Node.js 22+, JDK 21 và Android SDK 34+:
```bash
cd client
npm ci

# Chạy toàn bộ test suites của client (Cú pháp, Turn State Machine, Reminder Contract, Voice Mapping):
npm test

# Đồng bộ tài nguyên Web sang Android:
npx cap sync android

# Kiểm thử & Biên dịch Android:
cd android
./gradlew testDebugUnitTest
./gradlew assembleDebug
```
File APK sau khi biên dịch nằm tại: `client/android/app/build/outputs/apk/debug/app-debug.apk`.

---

## 🌟 Điểm Nổi Bật (Key Features & Invariants)

- 🎙️ **Đàm Thoại Tự Nhiên & In-App STT**:
  - Tự động phát hiện khoảng dừng nói (silence detection) trong 2.2 giây, không popup gián đoạn.
  - Phối hợp quyền sở hữu âm thanh (AudioOwnershipCoordinator) bảo đảm STT, Hotword và TTS không bao giờ tranh chấp micro.
- 🔊 **Giọng Nói Cuppy Đa Tầng Fallback**:
  - Chuỗi dự phòng 4 cấp độ: Vieneu Cuppy Local $\to$ Remote Cuppy Service $\to$ Edge-TTS $\to$ Âm thanh phòng thu nạp sẵn offline.
  - 100% không bao giờ kẹt trạng thái `SPEAKING` khi mạng gián đoạn.
- ⏰ **Nhắc Nhở & Báo Thức Tin Cậy (Zero Divergence)**:
  - Báo thức Android AlarmManager là căn cứ thực thi duy nhất trên di động (`1 reminder = 1 canonical ID = 1 AlarmManager = 1 ACK = 1 delivery`).
  - Hỗ trợ lưu trữ bền vững, sống sót qua khởi động lại máy (Reboot Receiver) và khôi phục hàng đợi outbox ACK khi mất mạng.
- 📱 **Hỗ Trợ Trợ Lý Mặc Định Hệ Thống (Default Assistant)**:
  - Tích hợp chuẩn `VoiceInteractionService` của Android, mở trợ lý qua thao tác giữ nút nguồn hoặc cử chỉ hệ điều hành.
  - Hỗ trợ Background Wake-Word ("Hey Nova") chạy hoàn toàn offline trên thiết bị (Mặc định TẮT, người dùng có thể bật trong Cài đặt).
- 🛡️ **Bảo Mật & Hoạt Động Offline**:
  - 100% tài nguyên giao diện (CSS, JS, Font) được đóng gói offline trong APK — hoạt động ngay cả ở chế độ máy bay.
  - Loại bỏ hoàn toàn API key khỏi ứng dụng client; mọi giao tiếp đi qua HTTPS backend với cơ chế kiểm tra phiên bản (Version Handshake).

---

## 🏗️ Kiến Trúc Hệ Thống (System Architecture)

```mermaid
graph TD
    User([👤 Người Dùng]) -->|Giọng nói vi-VN| ClientApp[📱 Nova Android Client]
    
    subgraph Client [Tầng Khách - Client App]
        ClientApp --> AudioCoord[Audio Ownership Coordinator]
        AudioCoord --> NativeSTT[Speech Recognition / Web Speech]
        AudioCoord --> Hotword[Hey Nova Detector (Offline)]
        NativeSTT --> TurnController[Turn State Machine]
        TurnController --> NativeBridge[Capacitor Native Bridge]
    end

    NativeBridge -->|Lệnh mở App / Báo thức| NativeAlarm[AlarmManager & Deep Links]
    NativeBridge -->|HTTP API / Handshake| Backend[🌐 Production Backend FastAPI]

    subgraph Server [Tầng Máy Chủ - Server]
        Backend --> Agent[🧠 Multi-LLM Agent: Gemini / Groq]
        Backend --> ReminderDB[(SQLite WAL Database)]
        Agent --> TTSFallback[🔊 Multi-Tier TTS Fallback Pipeline]
        TTSFallback -->|Cuppy / Edge-TTS / Prebuilt| ClientPlayer[Hardware MediaPlayer]
    end
```

---

## 📁 Cấu Trúc Mã Nguồn (Directory Structure)

```text
nova-voice-assistant/
├── client/                     # Ứng dụng Android & Web UI (Capacitor)
│   ├── android/                # Mã nguồn Android Studio gốc (Java / Gradle)
│   │   └── app/src/main/
│   │       ├── java/com/nova/assistant/
│   │       │   ├── MainActivity.java
│   │       │   ├── AudioOwnershipCoordinator.java
│   │       │   ├── NovaAlarmReceiver.java
│   │       │   ├── NovaAlarmService.java
│   │       │   ├── NovaBootReceiver.java
│   │       │   ├── NovaHotwordService.java
│   │       │   └── NovaVoiceInteractionService.java
│   │       └── AndroidManifest.xml
│   ├── www/                    # Giao diện điều khiển Web (Offline Assets, Tailwind)
│   │   ├── index.html          # Logic đàm thoại, Orb animation, Audio Pipeline
│   │   ├── js/
│   │   │   ├── config/AppConfig.js
│   │   │   ├── onboarding/FirstRunWizard.js
│   │   │   ├── reminders/ReminderClient.js
│   │   │   ├── turn/TurnController.js
│   │   │   └── diagnostics/DiagnosticsPanel.js
│   │   └── assets/             # CSS cục bộ & âm thanh phòng thu Cuppy
│   └── tests/                  # Bộ test tự động của Client (Node.js/Acorn)
├── server/                     # Máy chủ AI & Neural TTS (Python FastAPI)
│   ├── core/
│   │   ├── agent.py            # Quản lý LLM (Gemini / Groq)
│   │   ├── database.py         # Kết nối SQLite với chế độ WAL & busy timeout
│   │   ├── vieneu_cuppy.py     # Engine tổng hợp Cuppy Neural TTS
│   │   ├── tts.py              # Đa luồng Fallback TTS
│   │   └── scheduler.py        # Quản lý nhắc việc & lịch hẹn
│   ├── tests/                  # Bộ test hợp đồng API, Idempotency & Timezone
│   ├── server.py               # FastAPI endpoints & Middleware
│   └── config.py               # Cấu hình biến môi trường
├── .github/workflows/          # CI/CD Workflows (Client, Backend, Android, Release)
├── Dockerfile                  # Container production hóa cho Backend
├── docker-compose.yml          # Triển khai production với volume bền vững
└── README.md
```

---

## 📄 Giấy Phép (License)

Dự án được phát hành theo giấy phép [MIT License](LICENSE).

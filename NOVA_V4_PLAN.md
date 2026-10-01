<USER_REQUEST>
# NOVA V4 — PRODUCTION READY / INSTALL & RUN

Repository:

```text
wtrg/nova-voice-assistant
```

Baseline audit:

```text
78497952629636f401e49ee80703529cc043c2a5
```

# MỤC TIÊU CUỐI

Fresh install phải đạt:

```text
Install APK
→ mở Nova
→ cấp quyền cần thiết
→ backend tự kết nối
→ nói / chat được ngay
→ Cuppy phát được
→ reminder hoạt động
→ reboot vẫn còn reminder
→ chọn Nova làm Default Assistant
→ gọi Nova bằng system assistant gesture
→ background wake-word nếu user bật
```

Không yêu cầu người dùng:

```text
nhập IP 192.168.x.x
chạy Cloudflare tunnel
sửa source code
điền Gemini key vào APK
mở Android Studio
chạy backend bằng tay trên laptop
```

---

# PHASE 0 — MERGE V3.3 BLOCKERS TRƯỚC

V4 không được xây trên runtime lỗi.

Bắt buộc đóng:

```text
index.html syntax error
crash-window idempotency
ACK failed→confirmed state bug
snooze backend/native divergence
ACK outbox restart recovery
legacy conversation TTS globals
```

Thêm:

```text
index.html syntax parse test
runtime initialization smoke test
```

Gate:

```text
Client CI  GREEN
Backend CI GREEN
Android CI GREEN
```

Chưa đạt thì STOP.

---

# V4-01 — ONE-INSTALL BACKEND BOOTSTRAP

## Xóa hardcode development

Loại khỏi production:

```text
http://192.168.100.48:8000
cattle-end-rivers-sisters.trycloudflare.com
10.0.2.2 fallback trong release APK
```

Development URL chỉ tồn tại trong debug build.

## Production config

Tạo duy nhất:

```text
NOVA_API_BASE_URL
```

Ví dụ release:

```text
https://api.nova.example.com
```

Android + WebView dùng cùng một config.

Không duplicate URL trong:

```text
index.html
MainActivity.java
ReminderClient
DiagnosticsPanel
TTS
```

## Startup

App mở:

```text
GET /health/ready
```

Response:

```json
{
  "ok": true,
  "version": "...",
  "llm": true,
  "tts": true,
  "database": true
}
```

Nếu healthy:

```text
READY
```

Nếu offline:

```text
Nova Offline
```

không crash.

---

# V4-02 — PRODUCTION BACKEND PHẢI LUÔN SẴN

Backend không được phụ thuộc laptop cá nhân.

Thêm:

```text
Dockerfile
.dockerignore
production env validation
persistent database volume
healthcheck
startup migration
graceful shutdown
```

Nếu vẫn SQLite:

```text
1 persistent volume
controlled worker count
WAL mode
busy_timeout
transaction-safe side effects
```

Không để database nằm filesystem ephemeral.

## Server startup validation

Thiếu:

```text
GEMINI_API_KEY
database
required model/config
```

thì `/health/ready` phải báo degraded rõ ràng.

Không startup kiểu “server chạy nhưng chat chắc chắn lỗi”.

---

# V4-03 — KHÔNG ĐỂ API KEY TRONG APK

Production client:

```text
GEMINI_API_KEY = NONE
GROQ_API_KEY = NONE
```

Xóa Gemini direct-call production path nếu còn.

Luồng duy nhất:

```text
Android
→ Nova Backend
→ Gemini/Groq
```

API key chỉ ở server environment.

Nếu giữ BYOK:

```text
developer/debug mode only
```

không phải default flow.

---

# V4-04 — TTS PHẢI CÓ FALLBACK THỰC SỰ

Không phụ thuộc Quick Tunnel Cuppy.

Server TTS chain:

```text
1. local/stable Cuppy
2. stable remote Cuppy service
3. Edge TTS fallback
4. bundled system response audio
```

`/api/cuppy-tts` luôn trả contract thống nhất.

Nếu Cuppy unavailable:

```text
response vẫn được đọc
app không treo SPEAKING
```

Health:

```json
{
  "tts_primary": "cuppy",
  "tts_primary_ready": true,
  "tts_fallback_ready": true
}
```

---

# V4-05 — FIRST RUN SETUP

Fresh install hiển thị wizard một lần.

## Step 1

```text
Microphone
```

## Step 2

```text
Notifications
```

## Step 3

```text
Exact Alarm
```

Chỉ yêu cầu nếu user bật reminders.

## Step 4

```text
Full-screen alarm permission/status
```

nếu thiết bị yêu cầu.

## Step 5

```text
Set Nova as Default Assistant
```

## Step 6

```text
Test backend
Test microphone
Test speaker
```

Kết thúc:

```text
Nova is ready
```

Không hỏi URL server trong normal onboarding.

Server configuration chuyển vào:

```text
Developer Settings
```

---

# V4-06 — DEFAULT ASSISTANT HOÀN CHỈNH

Hiện đã có:

```text
NovaVoiceInteractionService
NovaVoiceInteractionSessionService
NovaVoiceInteractionSession
voice_interaction_service.xml
```

nhưng implementation chưa đủ.

## VoiceInteractionService

Implement lifecycle:

```text
onReady
onShutdown
onLaunchVoiceAssistFromKeyguard
onPrepareToShowSession
onShowSessionFailed
```

Theo dõi:

```text
isActiveService()
```

UI Settings phải hiển thị thật:

```text
Default Assistant:
✓ Nova active
hoặc
✗ Nova not selected
```

Không dựa vào assumption.

## Invocation

Power button / system gesture:

```text
Android
→ VoiceInteractionService
→ VoiceInteractionSession
→ MainActivity/assistant surface
→ auto_listen
→ STT
```

Không tạo hai microphone session.

Không tạo hai conversation turn.

---

# V4-07 — FIX RECOGNITION SERVICE

Hiện:

```text
NovaRecognitionService
→ ERROR_CLIENT
```

Không được ship trạng thái đó rồi gọi là recognition service hoàn chỉnh.

Chọn một trong hai:

### Production choice

`NovaRecognitionService` phải bridge sang engine STT thực tế.

Hoặc:

```text
remove recognitionService khỏi voice_interaction_service.xml
```

nếu hệ thống không cần nó.

Không giữ fake service chỉ để Settings nhận diện.

---

# V4-08 — BACKGROUND “HEY NOVA”

Không dùng endless `SpeechRecognizer` loop.

Tạo:

```text
NovaHotwordService
```

với:

```text
android:foregroundServiceType="microphone"
```

và permission tương ứng.

Hotword engine phải:

```text
on-device
low-power
offline
chỉ detect keyword
```

Không stream raw microphone lên server để chờ wake word.

## User control

Settings:

```text
[ ] Hey Nova
```

Default OFF.

User bật:

```text
request mic
start hotword service while app visible
persistent notification
```

Detect:

```text
"Hey Nova"
→ stop/pause detector
→ launch one assistant session
→ start normal STT
```

Session kết thúc:

```text
restart detector
```

## Screen-off

Test:

```text
screen on
screen off
lock screen
app background
app task removed
network offline
```

Nếu OEM kill service:

```text
UI phải báo Background Wake Word unavailable
```

Không claim 100% nếu thiết bị không cho.

---

# V4-09 — AUDIO OWNERSHIP

Hotword / STT / TTS không được tranh microphone.

State:

```text
HOTWORD
LISTENING
WAITING_LLM
SPEAKING
IDLE
```

Invariant:

```text
HOTWORD → LISTENING
HOTWORD detector paused

LISTENING → WAITING_LLM
microphone released

WAITING_LLM → SPEAKING
no microphone capture

SPEAKING complete
→ HOTWORD hoặc IDLE
```

Interrupt:

```text
SPEAKING → LISTENING
```

chỉ một owner.

---

# V4-10 — ALARM PERMISSION CLEANUP

Manifest hiện khai báo cả:

```text
SCHEDULE_EXACT_ALARM
USE_EXACT_ALARM
```

Production phải chọn đúng một policy.

Cho Nova:

```text
SCHEDULE_EXACT_ALARM
```

là default hướng an toàn hơn cho general assistant.

Không xin permission khi chưa dùng reminder.

Add diagnostics:

```text
exactAlarmGranted
notificationsGranted
fullScreenIntentGranted
```

Alarm không exact:

```text
Nova phải nói rõ
```

không giả success.

---

# V4-11 — FULL SCREEN ALARM

Trước khi dùng full-screen intent:

```text
canUseFullScreenIntent()
```

Nếu false:

```text
heads-up notification
+ action mở Settings
```

Không assume permission.

Test:

```text
screen unlocked
screen locked
Doze
notification permission denied
full-screen intent denied
```

---

# V4-12 — REMOVE QUERY_ALL_PACKAGES

Production không dùng:

```xml
QUERY_ALL_PACKAGES
```

nếu không thật sự bắt buộc.

Repo đã có `<queries>` cho:

```text
YouTube
Maps
Chrome
Zalo
Facebook
TikTok
Spotify
Telegram
...
```

Dùng targeted package visibility.

Bỏ lint disable:

```text
QueryAllPackagesPermission
```

---

# V4-13 — HTTPS PRODUCTION

Production:

```text
usesCleartextTraffic=false
```

Không HTTP backend.

Debug build có thể cho:

```text
192.168.x.x
10.0.2.2
```

qua debug-only network security config.

Release:

```text
HTTPS only
```

---

# V4-14 — OFFLINE/NETWORK FAILURE UX

Nếu backend mất mạng:

Nova vẫn phải:

```text
mở app
mở camera
mở Maps
mở YouTube
cancel reminder
show reminders
basic local commands
```

AI chat:

```text
show offline state
```

không spinning vô hạn.

TTS:

```text
fallback local/system response
```

---

# V4-15 — REMOVE REMOTE UI DEPENDENCY

Không tải Tailwind CDN trong privileged WebView production.

Build CSS vào:

```text
client/www/assets/
```

APK phải render UI khi:

```text
airplane mode
```

---

# V4-16 — APP CONFIG SINGLE SOURCE

Tạo object duy nhất:

```text
AppConfig
```

bao gồm:

```text
apiBaseUrl
environment
appVersion
buildSha
featureHotword
featureDefaultAssistant
ttsMode
```

JS lấy config từ native bridge/build asset.

Không hardcode cùng thông tin ở nhiều file.

---

# V4-17 — VERSION HANDSHAKE

Client gửi:

```text
X-Nova-Client-Version
X-Nova-Build-SHA
```

Server trả:

```text
server_version
min_client_version
```

Nếu APK quá cũ:

```text
show Update Required
```

Không để client/server contract mismatch âm thầm.

---

# V4-18 — DIAGNOSTICS SCREEN

Một màn duy nhất:

```text
Backend          ✓
LLM              ✓
TTS              ✓
Microphone       ✓
Notifications    ✓
Exact alarm      ✓
Full-screen      ✓
Default assistant✓
Hotword          ✓
```

Nút:

```text
Run Self Test
```

Self-test không gọi side-effect thật.

---

# V4-19 — RELEASE BUILD

Hiện release APK không tương ứng HEAD mới nhất.

Thêm:

```text
.github/workflows/release.yml
```

Trigger:

```text
tag v*
```

Pipeline:

```text
checkout
npm ci
client tests
backend tests
cap sync
Android unit tests
lint
assembleRelease
sign APK
build AAB
SHA256
upload GitHub Release
```

Release không được build thủ công từ máy cá nhân.

---

# V4-20 — SIGNING

Release signing qua GitHub Secrets:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD
```

Không commit keystore.

CI output:

```text
Nova_Assistant.apk
Nova_Assistant.aab
SHA256SUMS.txt
```

---

# V4-21 — VERSIONING

Không để:

```text
versionCode 1
versionName 1.0
```

mãi.

Release workflow/build config phải tăng version.

Ví dụ final V4:

```text
versionName 2.0.0
versionCode 20000
```

---

# V4-22 — REAL INSTALL SMOKE TEST

Test APK release thật:

```text
adb install
launch
fresh data
grant mic
send text
voice input
receive TTS
create reminder
cancel reminder
reboot restore
```

Nếu instrumentation không test được permission UI:

```text
DEVICE TEST REQUIRED
```

---

# V4-23 — DEVICE MATRIX

Tối thiểu:

```text
Android 12
Android 13
Android 14
Android 15
Android 16
```

Trên ít nhất:

```text
Pixel/AOSP
Samsung
một OEM khác nếu có
```

Test:

```text
fresh install
screen off
power-button assistant
lock screen
Hey Nova
alarm exact
alarm fallback
reboot
app swipe-away
network loss
network recovery
mic interruption
phone call interruption
Bluetooth headset
```

---

# V4-24 — FINAL README

README Quick Start phải có 2 path.

## Normal user

```text
1. Download APK
2. Install
3. Open Nova
4. Grant requested permissions
5. Optional: Set Nova as Default Assistant
6. Done
```

Không có Python/Node trong normal-user flow.

## Developer

Riêng section:

```text
Backend development
Android build
Environment variables
Self-hosting
```

---

# IMPLEMENT ORDER

```text
1. Merge V3.3 reliability blockers
2. Production backend + stable HTTPS URL
3. Remove client API keys/hardcoded LAN/tunnels
4. Production TTS fallback
5. First-run onboarding
6. Default Assistant lifecycle
7. Recognition service real implementation
8. Background hotword service
9. Audio ownership integration
10. Permission/exact alarm/full-screen cleanup
11. HTTPS + remove QUERY_ALL_PACKAGES + local CSS
12. Diagnostics/version handshake
13. Release signing pipeline
14. Device matrix
15. Publish final APK
```

Không làm UI redesign giữa chừng.

---

# FINAL ACCEPTANCE TEST

Một máy Android mới chưa cài Nova:

```text
download latest Nova_Assistant.apk
install
open
grant microphone + notifications
Nova tự tìm production backend
user nói: "Nova ơi chào tớ đi"
Nova nghe
backend trả lời
Cuppy phát

user nói:
"Nhắc tớ 10 phút nữa uống nước"
alarm được xác nhận
tắt màn hình
10 phút sau alarm reo

reboot phone
future reminder vẫn tồn tại

set Nova as Default Assistant
long-press power
Nova mở
mic bắt đầu
conversation hoạt động

enable Hey Nova
lock phone
say "Hey Nova"
Nova bắt đầu assistant session
```

Nếu một bước fail:

```text
V4 NOT DONE
```

---

# DEFINITION OF DONE

V4 hoàn tất khi:

```text
fresh install không cần nhập IP
fresh install không cần Gemini key
không cần Cloudflare Quick Tunnel
production backend luôn có stable HTTPS endpoint
AI chat works
voice input works
TTS works
reminders work
reboot restore works
offline degradation works
Default Assistant works on supported device
background wake word works when enabled on supported device
runtime JS parses
all CI green
release APK signed automatically
release APK built from final HEAD
README normal-user install flow <= 6 steps
```

Sau V4:

```text
STOP FEATURE DEVELOPMENT
```

Chỉ bugfix phát sinh từ device testing/release.
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-10-01T17:10:59+07:00.
</ADDITIONAL_METADATA>
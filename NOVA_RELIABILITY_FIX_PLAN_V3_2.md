<USER_REQUEST>
làm the cái đây tiếp đi 

# NOVA RELIABILITY FINAL FIX PLAN V3.2

Baseline audited:

```text
a85f0fef1f174b31483920f8e18986afce18323c
```

## Mục tiêu duy nhất

Kết thúc toàn bộ reliability debt hiện tại trước khi làm Hotword / Default Assistant.

Sau V3.2 phải đảm bảo:

```text
1 user turn
→ 1 turn_id
→ 1 backend execution
→ 1 response
→ 1 TTS sequence
→ zero stale callback
```

và:

```text
1 reminder
→ 1 reminder_id
→ 1 DB row
→ 1 native alarm
→ 1 ACK state
→ 1 delivery
```

Không mở thêm feature cho đến khi các invariant dưới đây đạt.

---

# P0-01 — FIX TTS FAILURE PATH BỊ TỰ CANCEL

## Lỗi hiện tại

Trong `playSingleVoiceChunk()`:

```js
onAudioFailed()
```

đang gọi:

```js
audioRegistry.cancelRequest(requestId)
```

sau đó lại kiểm tra:

```js
if (reqEntry.cancelled) return;
```

=> request tự đánh dấu cancelled rồi bỏ luôn fallback/finish.

Có thể dẫn tới:

```text
TTS timeout
→ request tự cancel
→ không fallback
→ không finish chunk
→ sequence không chạy tiếp
→ UI kẹt SPEAKING
```

## Fix bắt buộc

Tách:

```js
cancelRequest(requestId)
```

khỏi:

```js
finalizeRequest(requestId)
removeRequest(requestId)
```

Semantics:

```text
cancelRequest
= user interrupt / stale turn
= cancelled=true
= clear timers
= remove request
```

```text
finalizeRequest
= request kết thúc bình thường hoặc fail bình thường
= clear timers
= remove request
= KHÔNG set cancelled=true
```

`onAudioFailed()` phải:

```text
finalize original request
→ kiểm tra ownerTurn
→ tạo fallback request
→ fallback hoặc finishChunk
```

Không gọi `cancelRequest()`.

## Test bắt buộc

```text
35s timeout
→ fallback chạy
→ chunk kết thúc
→ sequence tiếp tục
```

```text
playAudioUrl throw
→ fallback chạy
→ không treo SPEAKING
```

```text
user interrupt
→ cancelRequest
→ fallback KHÔNG chạy
```

---

# P0-02 — OWNER-TURN TẤT CẢ TIMER CÒN LẠI

Không được còn timer production nào có thể mutate conversation nhưng nằm ngoài registry.

Audit toàn bộ:

```text
setTimeout(
setInterval(
_nativeTTSSafetyTimer
speechSynthesis fallback timer
250ms speak UI timer
HTML5 audio timeout
```

Các timer liên quan turn/TTS phải thuộc:

```text
requestId
ownerTurnId
```

Mỗi callback:

```js
if (!isOwnerTurnCurrent(ownerTurnId)) return;
```

Interrupt phải clear toàn bộ timer của turn cũ.

Không dùng global:

```js
window._nativeTTSSafetyTimer
window._nativeTTSFinishedCallback
```

cho production conversation path.

---

# P0-03 — LOẠI LEGACY NATIVE TTS GLOBAL CALLBACK KHỎI CONVERSATION

Hiện vẫn tồn tại:

```js
playNativeAndroidTTS()
window._nativeTTSFinishedCallback
window._nativeTTSSafetyTimer
window.onNovaSpeechEnded
window.onNativeTTSFailed
```

## Fix

Mọi audio dùng trong conversation phải đi qua:

```text
requestId
AudioRequestRegistry
onNovaAudioEvent(requestId, event)
```

Không dùng callback global cho turn-aware speech.

Nếu cần giữ legacy API cho compatibility:

```text
legacy path chỉ dùng ngoài conversation
không được mutate TurnController
```

---

# P0-04 — BACKEND IDEMPOTENCY STATE MACHINE HOÀN CHỈNH

Hiện:

```text
new → claimed
processing → reject
completed → replay
failed → có thể chạy lại không atomic
```

Sửa thành state machine:

```text
NEW
↓ atomic INSERT
PROCESSING
↓
COMPLETED
```

Failure:

```text
PROCESSING
↓
FAILED
```

Retry:

```text
FAILED
↓ atomic compare-and-swap
PROCESSING
```

Chỉ một process được quyền đổi:

```sql
UPDATE processed_turns
SET status='processing',
    updated_at=CURRENT_TIMESTAMP
WHERE session_id=?
  AND turn_id=?
  AND status='failed';
```

Check:

```text
rowcount == 1
```

Nếu `0`:

```text
request khác đã claim
→ không execute
```

---

# P0-05 — PROCESSING LEASE / CRASH RECOVERY

Không để record:

```text
processing
```

kẹt vĩnh viễn khi backend crash.

Thêm:

```text
processing_started_at
updated_at
attempt_count
```

Ví dụ lease:

```text
60 seconds
```

Nếu:

```text
status=processing
AND updated_at older than lease
```

thì request mới được atomic reclaim.

Không reclaim request còn đang hợp lệ.

Test:

```text
processing fresh → reject/retryable
processing stale → đúng 1 request reclaim
```

---

# P0-06 — CLIENT XỬ LÝ BACKEND PROCESSING ĐÚNG

Backend trả:

```json
{
  "retryable": true,
  "error": "Turn is currently being processed"
}
```

Client hiện không được chạy vòng:

```text
URL1 → 409
URL2 → 409
URL3 → 409
→ báo lỗi
```

## Fix

Nếu cùng `turn_id` trả:

```text
processing
```

thì:

```text
wait 300ms
retry same endpoint

wait 600ms
retry

wait 1200ms
retry
```

Sau đó mới failover endpoint.

Tất cả retry giữ nguyên:

```text
session_id
turn_id
request payload
```

Nếu request đầu đã hoàn tất:

```text
retry nhận cached completed response
```

UI không báo lỗi giả.

---

# P0-07 — IDEMPOTENCY HASH PHẢI BAO PHỦ TOÀN REQUEST

Fingerprint `/api/dialogue` phải gồm:

```text
endpoint
session_id
turn_id
user_text
in_conversation
generate_audio
```

`/api/chat` tương tự với các field có ảnh hưởng response.

Canonical JSON:

```text
stable keys
normalized strings
explicit booleans
```

Same turn ID nhưng request khác:

```text
HTTP 409
```

---

# P0-08 — FIX `/api/voice-upload`

Hiện route có nguy cơ:

```python
result = await handle_dialogue(...)
result["user_text"] = ...
```

trong khi `result` có thể là `JSONResponse`.

## Fix

Không gọi HTTP route function như service function.

Tách core:

```python
async def process_dialogue(req) -> DialogueServiceResult
```

Sau đó:

```text
/api/dialogue → process_dialogue()
/api/voice-upload → STT → process_dialogue()
```

Route wrapper mới chịu trách nhiệm tạo HTTP response.

Không mutate `JSONResponse`.

---

# P0-09 — VOICE-UPLOAD CŨNG PHẢI CÓ TURN ID

`/api/voice-upload` thêm:

```text
turn_id
```

Client tạo ID trước upload.

Sau STT:

```text
same upload retry
→ same turn_id
→ same dialogue execution
→ zero duplicate side effects
```

Nếu user upload lại nội dung khác với cùng turn ID:

```text
409
```

---

# P1-01 — DEVICE ACK PHẢI CÓ KẾT QUẢ CUỐI

Hiện:

```js
this.sendDeviceAck(...)
```

fire-and-forget.

Sửa thành:

```js
const ackPersistence = await this.sendDeviceAck(...)
```

Kết quả scheduling phải phân biệt:

```js
{
  nativeScheduled: true,
  serverAckPersisted: true
}
```

hoặc:

```js
{
  nativeScheduled: true,
  serverAckPersisted: false,
  serverAckRetryable: true
}
```

Không reschedule native alarm chỉ vì ACK HTTP fail.

---

# P1-02 — ACK OUTBOX BỀN VỮNG

Nếu app/WebView chết trước khi ACK gửi thành công, retry trong JS mất theo.

Tạo local ACK outbox:

```text
reminder_id
status
error
created_at
attempt_count
```

Persist bằng:

```text
Android SharedPreferences / native storage
```

ưu tiên native thay vì chỉ localStorage.

Flow:

```text
AlarmManager success
→ persist ACK outbox
→ gửi server
→ server success
→ remove outbox
```

App startup:

```text
flush pending ACK outbox
```

Như vậy:

```text
native scheduled + app killed
```

không làm server pending mãi.

---

# P1-03 — SERVER DEVICE ACK IDEMPOTENT

Endpoint:

```text
POST /api/reminders/{id}/device-ack
```

phải idempotent.

Ví dụ:

```text
confirmed → confirmed
```

gửi lại nhiều lần vẫn:

```text
200 OK
```

Không tạo side effect mới.

Không cho transition vô lý:

```text
confirmed → device_schedule_failed
```

trừ khi có explicit recovery rule.

State transition table phải được định nghĩa rõ.

---

# P1-04 — TIMESTAMP VALIDATION

Trước native scheduling:

```text
scheduled_at_epoch_ms > now
```

Nếu:

```text
0
NaN
past timestamp
absurd future timestamp
```

→ fail closed.

Không schedule alarm lập tức vì parse lỗi.

Android bridge cũng validate lại, không chỉ JS.

---

# P1-05 — ALARM REQUEST CODE COLLISION HARDENING

Canonical identity là:

```text
reminder_id UUID
```

`PendingIntent requestCode` chỉ là implementation detail.

Không dùng requestCode làm identity chính.

Persist:

```text
reminder_id
request_code
epoch
title
```

Khi cancel/restore:

```text
resolve bằng reminder_id
```

Nếu phát hiện requestCode collision:

```text
generate/probe deterministic alternate requestCode
```

Không overwrite alarm khác.

---

# P1-06 — SNOOZE IDENTITY

Không tái dùng mù quáng reminder ID cũ cho snooze nếu semantics là reminder mới.

Chọn một contract và giữ nhất quán:

Option khuyến nghị:

```text
original reminder_id
→ completed/snoozed

new snooze reminder
→ new reminder_id
→ parent_reminder_id = original
```

Như vậy tránh DB/native identity nhập nhằng.

---

# P1-07 — ALARM SERVICE FINAL OWNERSHIP TEST

Xác nhận:

```text
stopAudio()
```

không bao giờ dừng:

```text
NovaAlarmService
```

Chỉ các action sau được dừng alarm:

```text
STOP
SNOOZE
CLAIM
SAFETY_TIMEOUT
fatal alert failure
```

Test unit nếu được.

Sau đó:

```text
DEVICE TEST REQUIRED
```

---

# P1-08 — ALARM FALLBACK KHÔNG ĐƯỢC IM LẶNG

Flow:

```text
cuppy_alarm.wav fail
→ system alarm ringtone
```

Nếu ringtone fail:

```text
foreground notification vẫn tồn tại
vibration tiếp tục nếu có thể
service sống tới timeout/user action
```

Không silent `finishAlarmSession()` ngay nếu vẫn còn cách alert user.

---

# P1-09 — TEST THẬT PRODUCTION MODULE

Không thêm test kiểu copy logic:

```js
function fakeFinishSpeaking() {}
function simulateSequence() {}
```

Test phải import:

```text
AudioRequestRegistry
TurnController
ReminderDeliveryPolicy
backend idempotency functions
```

Nếu logic trong `index.html` chưa test được:

```text
extract thành module
index.html import module đó
test import cùng module đó
```

Một implementation duy nhất.

---

# TEST MATRIX BẮT BUỘC

## Audio

```text
1. normal TTS success
2. native failed event
3. native timeout
4. bridge throw
5. fallback success
6. fallback fail
7. interrupt trước 200ms
8. interrupt lúc chunk đang chạy
9. interrupt lúc fallback
10. Turn B bắt đầu trước callback cuối của A
11. stale A cannot finish B
12. stale A cannot start next chunk
```

## Backend

```text
13. same turn sequential retry
14. same turn concurrent retry
15. same turn different payload
16. failed → retry
17. two concurrent retries after failed
18. stale processing lease reclaim
19. fresh processing cannot reclaim
20. server restart with processing row
21. generate_audio difference → mismatch
22. exact response replay
```

## Voice upload

```text
23. successful upload
24. upstream error
25. same turn upload retry
26. schedule request through upload
27. duplicate upload → one reminder only
```

## Reminder

```text
28. native valid ACK
29. malformed ACK
30. wrong reminder_id ACK
31. timestamp zero
32. past timestamp
33. ACK network unavailable
34. app killed with pending ACK
35. restart flushes ACK outbox
36. ACK duplicate
37. reboot restore
38. snooze
39. cancel
```

---

# CI BẮT BUỘC

Phải xanh đồng thời:

```text
Client State Machine & Parity Tests
Backend Contract & Reliability Tests
Android CI
```

Android phải chạy:

```bash
./gradlew testDebugUnitTest --no-daemon
./gradlew lintDebug --no-daemon
./gradlew assembleDebug --no-daemon
```

Không:

```text
|| true
skip test
disable assertion
mock away production logic
```

---

# DEVICE TEST BẮT BUỘC SAU CI

Không code thêm feature trước khi test:

```text
foreground reminder
background reminder
screen-off reminder
app swiped away
reboot before reminder
exact-alarm denied
notification denied
network disconnected
Cuppy server unavailable
rapid interrupt A → B
snooze
cancel
```

Mỗi case ghi:

```text
PASS
FAIL
DEVICE TEST REQUIRED
```

Không ghi “fixed” nếu chưa test.

---

# THỨ TỰ IMPLEMENT DUY NHẤT

```text
1. fix onAudioFailed cleanup/cancel semantics
2. migrate remaining conversation TTS off global callbacks
3. bind every TTS timer to request + ownerTurn
4. atomic failed→processing retry
5. processing lease recovery
6. client processing backoff/replay
7. complete request fingerprint
8. refactor dialogue service layer
9. add voice-upload turn_id/idempotency
10. await device ACK
11. persistent device ACK outbox
12. ACK state transition hardening
13. timestamp validation
14. alarm identity/snooze hardening
15. production-module regression tests
16. all CI green
17. physical device matrix
```

Không đổi thứ tự nếu P0 chưa xanh.

---

# KHÔNG LÀM TRONG V3.2

Không làm:

```text
background Hey Nova
new hotword engine
Default Assistant redesign
UI redesign
new personality
new LLM provider
new TTS engine
new feature
performance optimization không liên quan
```

Không refactor code không liên quan.

Không “tiện tay” sửa kiến trúc khác.

---

# DEFINITION OF DONE

Chỉ kết thúc V3.2 khi toàn bộ điều kiện này đúng:

```text
TTS timeout không treo conversation
TTS failure luôn kết thúc hoặc fallback deterministic
interrupt xóa mọi async work của turn cũ
Turn A không thể mutate Turn B
không còn global callback trong production conversation audio path

same turn_id không execute side effect hai lần
concurrent retry không duplicate
failed retry có atomic claim
backend crash không khóa turn vĩnh viễn
processing retry cuối cùng nhận cached response

voice-upload cũng idempotent
voice-upload không mutate JSONResponse

native ACK malformed = failure
ACK mất mạng có persistent retry
app restart flush ACK pending
server/device state hội tụ

reminder timestamp invalid không schedule
one reminder_id = one logical reminder

client CI green
backend CI green
Android CI green
device reliability matrix hoàn thành
```

## Commit cuối cùng nên tối đa khoảng 6 commit

```text
fix(audio): make failure cleanup and all async TTS work turn-owned
fix(backend): complete crash-safe turn idempotency and replay
fix(voice): make upload path use shared idempotent dialogue service
fix(reminder): make device ACK durable and fail-closed
fix(alarm): harden reminder identity timestamps and snooze lifecycle
test(reliability): cover all final V3.2 invariants
```

Sau commit cuối:

```text
STOP
```

Không làm thêm feature.

Audit lại HEAD một lần.

Nếu toàn bộ DoD pass thì mới mở milestone:

```text
V4 — Background Hey Nova + Default Assistant
```
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-10-01T15:33:11+07:00.
</ADDITIONAL_METADATA>
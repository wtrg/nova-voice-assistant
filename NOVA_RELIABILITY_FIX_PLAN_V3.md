# NOVA RELIABILITY FIX V3 SPECIFICATION & IMPLEMENTATION

Repository: `wtrg/nova-voice-assistant`
Baseline audited HEAD: `f7df7a35a1ab5f34e07b6470be16aa47aa00fc8f`

## Invariants & Architecture Rules

1. **One Reminder, Exactly One Delivery**:
   - Android native runtime uses `AlarmManager` as the exclusive authority.
   - Browser runtime uses local `setInterval` fallback only when `window.AndroidNova` is absent.
   - When native alarm fires, the exact local reminder is marked delivered by canonical `reminder_id`.
2. **Request-Scoped Audio Events**:
   - `MainActivity.dispatchAudioEvent()` emits only `onNovaAudioEvent(requestId, event)` when `requestId` is present.
   - Legacy global callbacks (`onNovaSpeechStarted`, `onNovaSpeechEnded`, `onNativeAudioFailed`) are restricted to empty/no-request-ID calls only.
   - Stale completions and stale failures are rejected without affecting active turns.
3. **Interrupt Cancels Timers & Eliminates Fallback**:
   - Each audio request owns its lifecycle (`connectTimeout`, `cancelled`).
   - Interrupt/cancel operations clear pending timeouts, mark requests cancelled, invoke native audio stop, and suppress error clip playback.
4. **Authoritative Alarm Session Lifetime**:
   - `NovaAlarmService` loops alarm audio until explicit `STOP`, `SNOOZE`, successful `CLAIM` from WebView, or a 120s safety timeout.
   - Audio completion does not terminate the session prematurely.
   - WebView claims session via `claimAlarmSession`; stale sessions are rejected and do not cause duplicate triggers.
5. **Turn ID End-to-End Correlation**:
   - Client creates `turn_id` and transmits it to `/api/dialogue` and `/api/chat`.
   - Server reuses client `turn_id` (generating UUID only if omitted) and echoes it in responses.
   - Conversation state machine handles direct text input transition from `IDLE` -> `WAITING_LLM`.
6. **Backend Dependency Hardening**:
   - `python-multipart` added to runtime and dev dependencies to ensure robust FastAPI `File`/`Form` support.
7. **Android CI Hardening**:
   - Workflow upgraded to Node 22 with `npx cap sync android` step.
   - Zero `|| true` on `lintDebug` and unit tests.
8. **Canonical Reminder Identity Persistence & Reboot Survival**:
   - Backend DB persists `reminder_id` and `scheduling_status` with automatic non-destructive column migration.
   - Android persists `reminderId + "|||" + title + "|||" + timestamp` in SharedPreferences.
   - `NovaBootReceiver` restores native alarms using the identical canonical UUID and deterministic request codes.
9. **Two-Phase Reminder Commit (Device ACK)**:
   - Status transitions: `pending_device_ack` -> `confirmed` / `device_schedule_failed`.
   - `POST /api/reminders/{reminder_id}/device-ack` updates DB state; queries for active/due tasks exclude failed schedules.
10. **TTS Prefetch Ordering**:
    - Chunk N playback starts first; chunk N+1 prefetch is requested only after chunk N is actively playing.
    - Cancelled turns immediately abort downstream prefetching.
11. **Feature Claims Accuracy**:
    - Background/screen-off hotword and default assistant are marked `DEVICE TEST REQUIRED` and not claimed complete.

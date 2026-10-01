# NOVA RELIABILITY FIX V3.1 SPECIFICATION & IMPLEMENTATION

Repository: `wtrg/nova-voice-assistant`
Baseline audited HEAD: `beb562e17d5bd042acef479bc8ccd6b2605309a0`

## Core Invariants & Architecture Rules

1. **Owner-Turn Correlation for All Async Speech Operations**:
   - Every audio playback, sequential chunk chain, fallback error playback, and timer captures `ownerTurnId` at turn initialization.
   - Any callback or timer arriving after the active turn has changed is safely dropped without mutating the active turn.
   - Stale Turn A can never invoke `finishTurn()` on active Turn B.

2. **Cancellable, Request-Bound Timer Registries (`AudioRequestRegistry.js`)**:
   - Production logic extracted into `client/www/js/conversation/AudioRequestRegistry.js`.
   - All timers (200ms trigger start, 2s fallback continuation, 35s connection timeout, safety timers) are tracked in per-request timer registries.
   - User interrupt (`cancelCurrentTurn`, `cancelAllRequests`) atomically marks entries cancelled and clears all pending timers.

3. **Backend Turn Idempotency & Replay Protection**:
   - SQLite table `processed_turns` tracks `(session_id, turn_id)` with request SHA-256 payload hash and execution status (`processing`, `completed`).
   - Retries with the exact same payload replay the cached response without re-executing non-idempotent side effects (such as reminder database insertions).
   - Reusing a Turn ID with a conflicting payload returns HTTP 409 Conflict.
   - Concurrent requests for the same turn are serialized safely.

4. **Unique Canonical Reminder ID Enforcement**:
   - Partial unique SQLite index `idx_tasks_reminder_id ON tasks(reminder_id) WHERE reminder_id IS NOT NULL` enforces global uniqueness across all tasks.
   - Safe migration deduplicates existing records before creating the unique index.

5. **Fail-Closed Native ACK Validation & Bounded Retries (`ReminderDeliveryPolicy.js`)**:
   - Extracted into `client/www/js/reminders/ReminderDeliveryPolicy.js`.
   - Native ACK parsing validates JSON structure, boolean `ok`, and exact `reminder_id` match. Malformed or mismatched ACKs fail closed.
   - Server ACK endpoint `/api/reminders/{reminder_id}/device-ack` validates payload status (422 Unprocessable Entity for invalid values, 404 Not Found for non-existent reminders).
   - Client implements bounded exponential retry (delays: 300ms, 900ms, 1800ms) for transient network drops without re-scheduling native alarms.

6. **Decoupled Assistant Audio and Alarm Audio Lifecycles**:
   - `MainActivity.java` decouples assistant speech interruption (`stopAssistantAudioInternal`) from native alarm operations (`stopAlarmSessionInternal`).
   - Tapping mic or interrupting conversation audio never inadvertently silences an active alarm session.

7. **Alarm Media Error Fallback & Clean Terminal State**:
   - `NovaAlarmService.java` falls back to `RingtoneManager` system alarms when primary asset media player errors occur.
   - Alarm session termination cleanly resets `currentSessionId = ""`, `currentState = SessionState.IDLE`, and `isAlarmRinging = false`.

8. **Toolchain & Configuration Modernization**:
   - Synchronized all documentation and CI workflows to Node 22 and JDK 21.
   - Updated default wake word to `hey_nova`.
   - Removed machine-specific path fallbacks in `server/core/vieneu_cuppy.py`.
   - Updated `.env.example` with Gemini and Cuppy configuration keys.

9. **Physical Device Validation Status**:
   - Background screen-off hotword and default assistant remain explicitly marked `DEVICE TEST REQUIRED` and are NOT claimed as complete.

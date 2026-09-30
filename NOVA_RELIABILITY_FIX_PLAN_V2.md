<USER_REQUEST>
# AGENT PROMPT — NOVA RELIABILITY FIX V2

You are the primary senior engineer responsible for repairing:

`wtrg/nova-voice-assistant`

You must implement `NOVA_RELIABILITY_FIX_PLAN_V2.md` against the current repository HEAD.

This is an implementation task, not a documentation task.

Your job is to inspect the real runtime code, change it, add regression tests, run the relevant checks, and prove the required invariants.

## Non-negotiable rules

1. Read the current repository before changing anything.
2. Do not assume comments, README claims, or commit messages are correct.
3. Do not mark a phase complete because a module/file exists. Verify the production runtime actually calls it.
4. Do not leave duplicate execution paths for reminders, TTS, or conversation state.
5. Preserve backward compatibility only where it does not violate correctness.
6. Prefer small, reviewable PR-sized commits/stages.
7. Do not start background hotword work until reminder/conversation P0 work is stable.
8. Never claim a test passed unless you actually ran it.
9. Never claim Android runtime behavior is verified by JS/Python unit tests alone.
10. If physical-device validation is unavailable, label it exactly as `DEVICE TEST REQUIRED`.
11. Do not rewrite unrelated features unnecessarily.
12. Do not add placeholder services that always succeed/fail.
13. Do not keep architecture modules that are test-only and unused by runtime.
14. Do not solve race conditions primarily with arbitrary sleeps/timeouts.
15. Never let Nova say a reminder was successfully scheduled before native Android ACK confirms it.
16. Do not silently downgrade exact scheduling without exposing the degraded state.
17. Do not hide CI failures.

---

# Required invariants

Final runtime must enforce:

```text
1 user request
→ 1 turn
→ 1 assistant reply
→ 1 TTS stream
→ 1 audio playback
```

and:

```text
1 reminder
→ 1 canonical reminder ID
→ 1 native AlarmManager registration
→ 1 notification
→ 1 alarm playback
```

No stale callback from an old turn may mutate the active turn.

No dynamic AI reply may be replaced by a fixed WAV unless an explicit static `speechKey` requests it.

---

# Work order

Implement in this order unless a hard dependency requires otherwise.

## Stage 1 — Reminder single source

Audit:

```text
client/www/index.html
client/www/js/reminders/ReminderClient.js
client/android/app/src/main/java/com/nova/assistant/MainActivity.java
server/core/agent.py
server/server.py
```

Goals:

- `ReminderClient` becomes the only web-layer owner allowed to call native `scheduleNativeAlarm()`.
- `addLocalTask()` must never schedule native alarms.
- direct Gemini must return structured schedule actions and must not directly persist/schedule reminders.
- backend Gemini and direct Gemini must converge on one reminder processing path.
- introduce/use one canonical reminder ID.
- delete/cancel/snooze must operate on that same identity.
- one reminder request must create exactly one native alarm.

Add regression tests proving exactly one native scheduling call per reminder action.

Do not continue if the runtime can still schedule the same reminder twice.

---

## Stage 2 — Alarm service lifecycle

Audit:

```text
NovaAlarmService.java
NovaAlarmReceiver.java
NovaBootReceiver.java
MainActivity.java
AndroidManifest.xml
```

Fix:

- `isAlarmRinging` lifecycle.
- wakelock acquire/release ordering.
- fallback ringtone reference and stop behavior.
- service completion must call `stopForeground(true)` and `stopSelf()`.
- STOP/SNOOZE/completion/error use one safe finalization function.
- alarm must not become silent because Activity/WebView opens slowly.
- introduce safe native → WebView alarm handoff with session ID / claim ACK.
- alarm must remain functional without network/backend.

Add Android tests where possible and clearly mark device-only validation.

---

## Stage 3 — Reminder correctness

Fix:

- timezone-aware epoch conversion;
- multi-task validation before DB insert;
- atomic task creation;
- native ACK determines success wording;
- exact-alarm denied state is exposed honestly.

Required tests:

```text
valid local time → correct epoch on UTC CI runner
valid + invalid multi-task → inserts zero tasks
native schedule failure → UI/voice must not say success
```

---

## Stage 4 — Conversation runtime state machine

Wire the existing:

```text
ConversationStateMachine.js
TurnController.js
```

into real runtime.

Must cover:

```text
startListening
finalizeAndSubmitUtterance
sendUserUtterance
callBackendDialogue
speakNovaResponse
handleOrbClick
native STT callbacks
native audio callbacks
```

Rules:

- one active turn;
- one active STT session;
- one active TTS request;
- old callbacks rejected;
- final STT result submitted once.

Preserve `turn_id` from backend or use one client-originated ID end-to-end.

---

## Stage 5 — TTS request IDs and priority

Replace shared mutable globals such as:

```text
_nativeTTSFinishedCallback
onNativeAudioFailed
onNovaSpeechStarted
```

with request-aware events.

Bridge/events must carry:

```text
turn_id
tts_request_id
```

Every callback must be correlated.

Then enforce:

```text
live current speech > prefetch > background
```

Do not allow prefetch to delay the current chunk.

If old inference cannot be interrupted, mark it cancelled and suppress obsolete result/prefetch.

---

## Stage 6 — CI and tests

Fix backend CI.

Pin compatible dependencies.

Add Android CI running:

```text
lintDebug
testDebugUnitTest
assembleDebug
```

Add or expand:

```text
backend contract tests
client runtime tests
reminder duplicate tests
timezone tests
atomic scheduling tests
stale TTS callback tests
text↔audio parity tests
Android alarm tests
```

No stage is complete with red required CI.

---

## Stage 7 — Typed contracts

Wire FastAPI response models into routes.

Do not leave schemas as unused documentation.

Ensure all actions are consistently objects.

Remove string/object ambiguity.

---

## Stage 8 — Unify AI execution paths

Preferred production path:

```text
client → Nova backend → LLM
```

If direct Gemini remains:

- make it developer/debug-only, or
- force it to use the same action schema and same reminder pipeline;
- do not perform native side effects inside the LLM call function.

---

## Stage 9 — Native reminder repository

Replace Web localStorage as authoritative device reminder storage with native Room repository.

WebView becomes a client/UI of native reminder state.

---

## Stage 10 — Diagnostics

Wire diagnostics into actual UI.

At minimum report:

```text
backend
voice model
voice preset
mic permission
notification permission
exact alarm permission
alarm service state
default assistant state
hotword state
last STT error
last TTS latency
last reminder ACK
```

Never show unsupported features as working.

---

## Stage 11 — Native background Hey Nova

Only begin after all previous P0 reliability work is green.

Implement a true local hotword foreground service.

Do NOT use continuous WebView/Android `SpeechRecognizer` as the always-on hotword engine.

Must support:

```text
background
screen off
handoff to STT
resume hotword after conversation
```

Avoid two microphone consumers at once.

Mark all untested OEM/device behavior honestly.

---

## Stage 12 — Default assistant

`NovaRecognitionService` must not permanently return `ERROR_CLIENT`.

Either implement it correctly or remove the misleading registration and route system assistant invocation to the real STT pipeline.

Test lock-screen/default-assistant flows on actual Android devices where possible.

---

## Stage 13 — Security

Remove remote runtime JavaScript from the privileged WebView.

Bundle Tailwind/static assets locally.

Review WebView navigation allowlist.

Treat Cloudflare tunnel as API endpoint only.

Add device/API authentication to non-health backend endpoints.

Review exported Android components and permissions.

---

## Stage 14 — Config/docs cleanup

Remove machine-specific Cuppy fallback paths.

Synchronize:

```text
config.py
.env.example
README.md
requirements*
```

README must only claim features proven by code/tests.

---

# Verification protocol after every stage

1. Show exactly which files changed.
2. Explain the root cause fixed.
3. State the invariant now enforced.
4. Show tests added/updated.
5. Run relevant test commands.
6. Report exact command result summary.
7. List anything that still requires physical-device testing.
8. Do not move on if the stage introduces new failures.

---

# Required commands

Backend:

```bash
python -m pytest server/tests -v
```

Client:

```bash
cd client
npm test
```

Android:

```bash
cd client/android
./gradlew lintDebug
./gradlew testDebugUnitTest
./gradlew assembleDebug
```

If instrumentation environment exists:

```bash
./gradlew connectedDebugAndroidTest
```

---

# Mandatory regression scenarios

## Reminder duplicate

```text
create one reminder
→ exactly one native scheduling call
→ exactly one persisted reminder
→ exactly one alarm fire
```

## Reminder delete

```text
create
→ delete
→ native alarm absent
→ repository row absent
```

## Reminder snooze

```text
fire
→ snooze
→ original cleared
→ one replacement exists
```

## Timezone

```text
20:00 Asia/Ho_Chi_Minh
→ correct UTC epoch
→ convert back = 20:00 +07
```

## Atomic schedule

```text
task A valid
task B invalid
→ no DB inserts
```

## Text/audio parity

For every dynamic reply:

```text
normalize(concat(all TTS chunk text))
==
normalize(assistant reply)
```

## Stale callback

```text
Turn A TTS starts
→ interrupt
→ Turn B starts
→ late completion(A)
→ no state mutation of Turn B
```

## Alarm handoff

```text
native alarm fires
→ Activity opens slowly
→ WebView delayed
→ native alarm continues
→ WebView claim ACK
→ native alarm stops
→ dynamic assistant flow continues
```

---

# Device test matrix

Mark as `DEVICE TEST REQUIRED` when not runnable in the current environment.

Test at minimum:

```text
Pixel/AOSP
Samsung One UI
Xiaomi/HyperOS
```

Cases:

```text
foreground
background
screen off
swipe-away
reboot
battery saver
Doze
notification denied
exact alarm denied
Bluetooth
offline
```

Hotword cases:

```text
screen off 1 minute
screen off 30 minutes
after reboot
after swipe-away
```

---

# Definition of Done

Do not declare the project fixed until:

```text
backend CI green
client CI green
Android build CI green
```

and:

```text
100 normal turns → 0 text/audio mismatches
100 interrupts → 0 stale callback corruption
1 reminder → 1 alarm
delete → 0 alarms
snooze → 1 replacement
screen-off reminder works
background reminder works
reboot restore works
offline alarm works
```

For hotword:

```text
background + screen-off device tests pass
```

For default assistant:

```text
system invocation works on supported tested device
```

Anything not physically tested must be reported as:

```text
NOT VERIFIED ON DEVICE
```

not as completed.

---

# Final deliverable format

When finished, provide:

```text
1. Summary of changes
2. Commits/PR stages completed
3. Files changed
4. Bugs fixed
5. Tests added
6. Commands run
7. CI status
8. Device tests completed
9. Device tests still required
10. Remaining known risks
11. Any intentional deviations from the plan and why
```

Do not hide failures.

Do not replace missing implementation with comments or documentation.

Do not mark architecture modules as complete unless they are used by the real production runtime.

</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-10-01T03:36:13+07:00.
</ADDITIONAL_METADATA>
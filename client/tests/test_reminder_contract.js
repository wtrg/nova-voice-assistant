const assert = require('assert');
const { ReminderClient } = require('../www/js/reminders/ReminderClient');
const { generateReminderId, reminderIdToRequestCode } = require('../www/js/reminders/ReminderId');

console.log("Running test_reminder_contract.js...");

async function runTests() {
  // Test Case 0: Canonical ID properties
  const id1 = generateReminderId();
  const id2 = generateReminderId();
  assert.notStrictEqual(id1, id2, "Canonical IDs must be unique");
  const code1a = reminderIdToRequestCode(id1);
  const code1b = reminderIdToRequestCode(id1);
  assert.strictEqual(code1a, code1b, "Same ID must generate same request code");
  assert.ok(code1a >= 0, "Request code must be non-negative");
  console.log("✓ Canonical ID generation & request code pass");

  // Test Case 1: Exactly 1 native alarm call per reminder
  let nativeCallCount = 0;
  let receivedPayloads = [];

  global.window = {
    AndroidNova: {
      scheduleNativeAlarm: (jsonStr) => {
        nativeCallCount++;
        const parsed = JSON.parse(jsonStr);
        receivedPayloads.push(parsed);
        return JSON.stringify({
          ok: true,
          reminder_id: parsed.reminder_id,
          pending_intent_id: 12345,
          exact: true,
          scheduled_at_epoch_ms: parsed.scheduled_at_epoch_ms
        });
      },
      cancelNativeAlarm: (reminderId) => {
        return true;
      }
    }
  };

  const rc = new ReminderClient();
  const singleTaskAction = {
    action: "schedule_tasks",
    tasks: [
      {
        title: "Tập gym",
        scheduled_time: "2026-10-01 17:00",
        scheduled_at_epoch_ms: 1790800000000,
        timezone: "Asia/Ho_Chi_Minh"
      }
    ]
  };

  const res1 = await rc.processScheduleAction(singleTaskAction);
  assert.strictEqual(nativeCallCount, 1, "Must call native alarm EXACTLY ONCE for single task");
  assert.strictEqual(res1.successCount, 1);
  assert.strictEqual(res1.exactGranted, true);
  assert.ok(receivedPayloads[0].reminder_id, "Payload must include canonical reminder_id");
  assert.ok(res1.confirmedSpeech.includes("đã đặt chuông"), "Confirmed speech must confirm success when ok === true");
  console.log("✓ Invariant: 1 reminder -> exactly 1 native alarm registration pass");

  // Test Case 2: Native schedule failure -> voice must NOT say success
  global.window.AndroidNova.scheduleNativeAlarm = (jsonStr) => {
    return JSON.stringify({
      ok: false,
      reminder_id: "test_failed_id",
      error: "AlarmManager denied by system"
    });
  };

  const failedRes = await rc.processScheduleAction(singleTaskAction);
  assert.strictEqual(failedRes.successCount, 0, "Success count must be 0 on native rejection");
  assert.ok(!failedRes.confirmedSpeech.includes("xong xuôi"), "Must NEVER speak success on rejection");
  assert.ok(failedRes.confirmedSpeech.includes("Xin lỗi") || failedRes.confirmedSpeech.includes("từ chối"), 
    "Must speak error / apology on native rejection");
  console.log("✓ Invariant: Rejection never reports success pass");

  // Test Case 3: Exact alarm denied -> degraded state honestly exposed
  global.window.AndroidNova.scheduleNativeAlarm = (jsonStr) => {
    const parsed = JSON.parse(jsonStr);
    return JSON.stringify({
      ok: true,
      reminder_id: parsed.reminder_id,
      exact: false,
      scheduled_at_epoch_ms: parsed.scheduled_at_epoch_ms
    });
  };

  const degradedRes = await rc.processScheduleAction(singleTaskAction);
  assert.strictEqual(degradedRes.successCount, 1);
  assert.strictEqual(degradedRes.exactGranted, false, "exactGranted must be false");
  assert.ok(degradedRes.confirmedSpeech.includes("Báo thức chính xác"), 
    "Must warn user about Exact Alarm permission when exact is false");
  console.log("✓ Invariant: Exact alarm denied state honestly exposed pass");

  // Test Case 4: Delete reminder removes from active alarms
  const testId = receivedPayloads[0].reminder_id;
  assert.ok(rc.scheduledAlarms.has(testId), "Scheduled alarms map must track active alarm");
  const cancelSuccess = rc.cancelNativeAlarm(testId);
  assert.strictEqual(cancelSuccess, true);
  assert.strictEqual(rc.scheduledAlarms.has(testId), false, "Deleted reminder must be removed from map");
  console.log("✓ Invariant: Reminder delete operates on same canonical identity pass");

  // Test Case 5: Empty action handling
  const emptyRes = await rc.processScheduleAction(null);
  assert.strictEqual(emptyRes.successCount, 0);
  assert.ok(emptyRes.errors.length > 0);
  console.log("✓ Empty action handling pass");

  console.log("ALL REMINDER CONTRACT REGRESSION TESTS PASSED PERFECTLY!");
}

runTests().catch(err => {
  console.error("Test failed:", err);
  process.exit(1);
});

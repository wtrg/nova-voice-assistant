const assert = require('assert');
const { ReminderClient } = require('../www/js/reminders/ReminderClient');

console.log("Running test_reminder_contract.js...");

async function runTests() {
  const rc = new ReminderClient();

  // Test Case 1: Backend structured action with tasks
  const backendAction = {
    type: "schedule_tasks",
    action: "schedule_tasks",
    task_ids: [101, 102],
    summary: ["Học Toán lúc 20:00", "Uống nước lúc 21:00"],
    tasks: [
      {
        task_id: 101,
        title: "Học Toán",
        scheduled_time: "2026-10-01 20:00",
        scheduled_at_epoch_ms: 1790800000000,
        timezone: "Asia/Ho_Chi_Minh",
        app_to_open: ""
      },
      {
        task_id: 102,
        title: "Uống nước",
        scheduled_time: "2026-10-01 21:00",
        scheduled_at_epoch_ms: 1790803600000,
        timezone: "Asia/Ho_Chi_Minh",
        app_to_open: ""
      }
    ]
  };

  const result = await rc.processScheduleAction(backendAction);
  assert.strictEqual(result.successCount, 2, "Both tasks should be scheduled");
  assert.strictEqual(result.errors.length, 0, "No errors expected");
  assert.strictEqual(result.exactGranted, true, "Exact alarms should be granted");
  assert.strictEqual(rc.scheduledAlarms.size, 2, "Scheduled map must have 2 entries");
  console.log("✓ Process structured schedule action pass");

  // Test Case 2: Empty action handles gracefully
  const emptyResult = await rc.processScheduleAction(null);
  assert.strictEqual(emptyResult.successCount, 0);
  assert.ok(emptyResult.errors.length > 0);
  console.log("✓ Empty action handling pass");

  console.log("ALL REMINDER CONTRACT TESTS PASSED PERFECTLY!");
}

runTests().catch(err => {
  console.error("Test failed:", err);
  process.exit(1);
});

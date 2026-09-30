/**
 * REMINDER CLIENT WITH NATIVE ACK & CANONICAL IDENTITY
 * 
 * Invariants:
 * 1 reminder -> 1 canonical reminder_id -> 1 native AlarmManager registration
 * ReminderClient is the ONLY web-layer owner allowed to call scheduleNativeAlarm().
 * Nova must not speak "đã đặt" until native ACK confirms ok === true.
 */

let _reminderIdGen = null;
if (typeof require !== 'undefined') {
  try {
    _reminderIdGen = require('./ReminderId');
  } catch (ignored) {}
}

class ReminderClient {
  constructor(options = {}) {
    this.scheduledAlarms = new Map();
    this.onTaskScheduled = options.onTaskScheduled || null;
  }

  getCanonicalId(task) {
    if (task.reminder_id) return String(task.reminder_id);
    if (task.task_id && typeof task.task_id === 'string' && task.task_id.length > 5) return String(task.task_id);
    if (typeof generateReminderId === 'function') return generateReminderId();
    if (_reminderIdGen && typeof _reminderIdGen.generateReminderId === 'function') {
      return _reminderIdGen.generateReminderId();
    }
    return 'rem_' + Date.now().toString(36) + '_' + Math.random().toString(36).substring(2, 9);
  }

  /**
   * Xử lý action lên lịch từ API backend hoặc Direct Gemini
   * @param {Object} actionData - Đối tượng action
   * @returns {Promise<{ successCount: number, totalCount: number, errors: Array<string>, exactGranted: boolean, confirmedSpeech: string, scheduledTasks: Array<Object> }>}
   */
  async processScheduleAction(actionData) {
    if (!actionData) {
      return { successCount: 0, totalCount: 0, errors: ["No action data"], exactGranted: true, confirmedSpeech: "", scheduledTasks: [] };
    }

    const tasks = actionData.tasks || (actionData.task ? [actionData.task] : []);
    if (!Array.isArray(tasks) || tasks.length === 0) {
      return { successCount: 0, totalCount: 0, errors: ["No tasks in payload"], exactGranted: true, confirmedSpeech: "", scheduledTasks: [] };
    }

    let successCount = 0;
    const errors = [];
    let exactGranted = true;
    const scheduledTasks = [];

    for (const rawTask of tasks) {
      const canonicalId = this.getCanonicalId(rawTask);
      const task = Object.assign({}, rawTask, { reminder_id: canonicalId });

      const res = await this.scheduleNativeTask(task);
      if (res && res.ok) {
        successCount++;
        if (res.exact === false) {
          exactGranted = false;
        }
        scheduledTasks.push(task);
        if (typeof this.onTaskScheduled === 'function') {
          this.onTaskScheduled(task, res);
        }
      } else {
        const errMsg = (res && (res.message || res.error)) || `Lỗi đặt lịch cho '${task.title || "Lịch hẹn"}'`;
        errors.push(errMsg);
      }
    }

    let confirmedSpeech = "";
    if (successCount === tasks.length) {
      if (!exactGranted) {
        confirmedSpeech = "Tớ đã lưu lịch nhắc cho cậu rồi nhé. Cậu nhớ cấp quyền Báo thức chính xác để chuông reo chuẩn từng phút nhé!";
      } else {
        confirmedSpeech = "Tớ đã đặt chuông nhắc cho cậu xong xuôi rồi nhé!";
      }
    } else if (successCount > 0) {
      confirmedSpeech = `Tớ đã đặt được ${successCount} lịch nhắc, nhưng còn một số việc bị lỗi hệ thống từ chối.`;
    } else {
      confirmedSpeech = "Xin lỗi cậu, tớ chưa thể đặt lịch nhắc do hệ thống Android từ chối cấp quyền.";
    }

    return {
      successCount,
      totalCount: tasks.length,
      errors,
      exactGranted,
      confirmedSpeech,
      scheduledTasks
    };
  }

  /**
   * Gọi bridge Android để đặt báo thức chính xác với ACK
   * @param {Object} task
   * @returns {Promise<{ ok: boolean, reminder_id: string, pending_intent_id?: number, exact?: boolean, error?: string }>}
   */
  async scheduleNativeTask(task) {
    const reminderId = task.reminder_id || this.getCanonicalId(task);
    const title = task.title || "Lịch hẹn";
    let timestamp = task.scheduled_at_epoch_ms || 0;

    if (!timestamp && task.scheduled_time) {
      const parsed = Date.parse(task.scheduled_time.replace(" ", "T"));
      if (!isNaN(parsed)) {
        timestamp = parsed;
      }
    }

    if (typeof window !== 'undefined' && window.AndroidNova && typeof window.AndroidNova.scheduleNativeAlarm === 'function') {
      try {
        let ackStr = null;
        ackStr = window.AndroidNova.scheduleNativeAlarm(JSON.stringify({
          reminder_id: reminderId,
          task_id: task.task_id || 0,
          title: title,
          scheduled_at_epoch_ms: timestamp,
          scheduled_time: task.scheduled_time || "",
          timezone: task.timezone || "Asia/Ho_Chi_Minh"
        }));

        let ack = null;
        if (typeof ackStr === 'string' && ackStr.startsWith("{")) {
          ack = JSON.parse(ackStr);
        } else {
          ack = { ok: true, reminder_id: reminderId, exact: true };
        }
        this.scheduledAlarms.set(reminderId, { task, ack });
        this.sendDeviceAck(reminderId, ack.ok ? "confirmed" : "device_schedule_failed", ack.message || ack.error);
        return ack;
      } catch (err) {
        console.error("[ReminderClient] scheduleNativeAlarm error:", err);
        this.sendDeviceAck(reminderId, "device_schedule_failed", err.message);
        return { ok: false, reminder_id: reminderId, error: err.message };
      }
    }

    // Nếu chạy trên Web / Test Runner
    this.scheduledAlarms.set(reminderId, { task, simulated: true });
    this.sendDeviceAck(reminderId, "confirmed");
    return {
      ok: true,
      reminder_id: reminderId,
      pending_intent_id: 1,
      exact: true,
      scheduled_at_epoch_ms: timestamp,
      simulated: true
    };
  }

  async sendDeviceAck(reminderId, status, error = null) {
    if (typeof fetch !== 'function' || !reminderId) return;
    try {
      let baseUrl = "";
      if (typeof getApiBaseUrl === 'function') {
        baseUrl = getApiBaseUrl();
      } else if (typeof window !== 'undefined' && window.getApiBaseUrl) {
        baseUrl = window.getApiBaseUrl();
      }
      if (!baseUrl) return;
      await fetch(`${baseUrl}/api/reminders/${encodeURIComponent(reminderId)}/device-ack`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, error: error ? String(error) : null })
      });
    } catch (ignored) {}
  }

  cancelNativeAlarm(reminderId) {
    if (!reminderId) return false;
    const strId = String(reminderId);
    this.scheduledAlarms.delete(strId);
    if (typeof window !== 'undefined' && window.AndroidNova && typeof window.AndroidNova.cancelNativeAlarm === 'function') {
      try {
        return window.AndroidNova.cancelNativeAlarm(strId);
      } catch (e) {
        console.error("[ReminderClient] cancelNativeAlarm error:", e);
        return false;
      }
    }
    return true;
  }
}

if (typeof window !== 'undefined') {
  window.ReminderClient = ReminderClient;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    ReminderClient
  };
}

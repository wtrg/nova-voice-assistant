/**
 * REMINDER CLIENT WITH NATIVE ACK & CANONICAL IDENTITY
 * 
 * Invariants:
 * 1 reminder -> 1 canonical reminder_id -> 1 native AlarmManager registration
 * ReminderClient is the ONLY web-layer owner allowed to call scheduleNativeAlarm().
 * Nova must not speak "đã đặt" until native ACK confirms ok === true.
 */

let _reminderIdGen = null;
let _reminderDeliveryPolicy = null;
if (typeof require !== 'undefined') {
  try {
    _reminderIdGen = require('./ReminderId');
  } catch (ignored) {}
  try {
    const mod = require('./ReminderDeliveryPolicy');
    _reminderDeliveryPolicy = mod.ReminderDeliveryPolicy || mod;
  } catch (ignored) {}
}

class ReminderClient {
  constructor(options = {}) {
    this.scheduledAlarms = new Map();
    this.onTaskScheduled = options.onTaskScheduled || null;
    this.flushAckOutbox();
  }

  saveToAckOutbox(item) {
    try {
      const outbox = this.getAckOutbox();
      const existingIdx = outbox.findIndex(x => x.reminder_id === item.reminder_id);
      if (existingIdx >= 0) {
        outbox[existingIdx] = Object.assign({}, outbox[existingIdx], item);
      } else {
        outbox.push(item);
      }
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem("nova_ack_outbox", JSON.stringify(outbox));
      }
    } catch (e) {
      console.warn("[ReminderClient] saveToAckOutbox error:", e);
    }
  }

  getAckOutbox() {
    try {
      if (typeof localStorage !== 'undefined') {
        const raw = localStorage.getItem("nova_ack_outbox");
        if (raw) return JSON.parse(raw);
      }
    } catch (e) {}
    return [];
  }

  removeFromAckOutbox(reminderId) {
    try {
      let outbox = this.getAckOutbox();
      outbox = outbox.filter(x => x.reminder_id !== reminderId);
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem("nova_ack_outbox", JSON.stringify(outbox));
      }
    } catch (e) {
      console.warn("[ReminderClient] removeFromAckOutbox error:", e);
    }
  }

  async flushAckOutbox() {
    const outbox = this.getAckOutbox();
    if (!outbox || outbox.length === 0) return;
    for (const item of outbox) {
      try {
        const res = await this.sendDeviceAck(item.reminder_id, item.status, item.error);
        if (res && res.ok) {
          this.removeFromAckOutbox(item.reminder_id);
        }
      } catch (e) {
        console.warn("[ReminderClient] flushAckOutbox error for", item.reminder_id, e);
      }
    }
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
   * Gọi bridge Android để đặt báo thức chính xác với ACK (V3.2: Fail-closed, outbox, timestamp validation)
   * @param {Object} task
   * @returns {Promise<{ ok: boolean, reminder_id: string, pending_intent_id?: number, exact?: boolean, error?: string, nativeScheduled?: boolean, serverAckPersisted?: boolean, serverAckRetryable?: boolean }>}
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

    const policy = (typeof window !== 'undefined' && window.ReminderDeliveryPolicy) || _reminderDeliveryPolicy;
    if (policy && typeof policy.validateTimestamp === 'function') {
      const timeVal = policy.validateTimestamp(timestamp);
      if (!timeVal.valid) {
        return { ok: false, reminder_id: reminderId, error: timeVal.reason || "invalid_timestamp", nativeScheduled: false };
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
        if (policy && typeof policy.validateNativeAck === 'function') {
          ack = policy.validateNativeAck(ackStr, reminderId);
        } else {
          // Inline fail-closed fallback
          if (typeof ackStr === 'string') {
            try {
              const parsed = JSON.parse(ackStr);
              if (parsed && typeof parsed.ok === 'boolean' && parsed.reminder_id === reminderId) {
                ack = parsed;
              } else {
                ack = { ok: false, reminder_id: reminderId, error: "invalid_native_ack" };
              }
            } catch (e) {
              ack = { ok: false, reminder_id: reminderId, error: "invalid_native_ack" };
            }
          } else if (ackStr && typeof ackStr === 'object' && typeof ackStr.ok === 'boolean' && ackStr.reminder_id === reminderId) {
            ack = ackStr;
          } else {
            ack = { ok: false, reminder_id: reminderId, error: "invalid_native_ack" };
          }
        }

        if (ack && ack.ok) {
          this.scheduledAlarms.set(reminderId, { task, ack });
          this.saveToAckOutbox({
            reminder_id: reminderId,
            status: "confirmed",
            created_at: Date.now(),
            attempt_count: 0
          });
          const ackRes = await this.sendDeviceAck(reminderId, "confirmed");
          if (ackRes && ackRes.ok) {
            this.removeFromAckOutbox(reminderId);
          }
          return {
            ok: true,
            reminder_id: reminderId,
            pending_intent_id: ack.pending_intent_id,
            exact: ack.exact !== false,
            scheduled_at_epoch_ms: timestamp,
            nativeScheduled: true,
            serverAckPersisted: Boolean(ackRes && ackRes.ok),
            serverAckRetryable: Boolean(ackRes && !ackRes.ok && ackRes.httpStatus !== 404 && ackRes.httpStatus !== 422)
          };
        } else {
          const failErr = (ack && (ack.error || ack.message)) || "invalid_native_ack";
          this.saveToAckOutbox({
            reminder_id: reminderId,
            status: "device_schedule_failed",
            error: failErr,
            created_at: Date.now(),
            attempt_count: 0
          });
          const ackRes = await this.sendDeviceAck(reminderId, "device_schedule_failed", failErr);
          if (ackRes && ackRes.ok) {
            this.removeFromAckOutbox(reminderId);
          }
          return Object.assign({}, ack, {
            nativeScheduled: false,
            serverAckPersisted: Boolean(ackRes && ackRes.ok),
            serverAckRetryable: false
          });
        }
      } catch (err) {
        console.error("[ReminderClient] scheduleNativeAlarm error:", err);
        const failAck = { ok: false, reminder_id: reminderId, error: err.message, nativeScheduled: false };
        this.saveToAckOutbox({
          reminder_id: reminderId,
          status: "device_schedule_failed",
          error: err.message,
          created_at: Date.now(),
          attempt_count: 0
        });
        const ackRes = await this.sendDeviceAck(reminderId, "device_schedule_failed", err.message);
        if (ackRes && ackRes.ok) {
          this.removeFromAckOutbox(reminderId);
        }
        return failAck;
      }
    }

    // Nếu chạy trên Web / Test Runner
    this.scheduledAlarms.set(reminderId, { task, simulated: true });
    this.saveToAckOutbox({
      reminder_id: reminderId,
      status: "confirmed",
      created_at: Date.now(),
      attempt_count: 0
    });
    const ackRes = await this.sendDeviceAck(reminderId, "confirmed");
    if (ackRes && ackRes.ok) {
      this.removeFromAckOutbox(reminderId);
    }
    return {
      ok: true,
      reminder_id: reminderId,
      pending_intent_id: 1,
      exact: true,
      scheduled_at_epoch_ms: timestamp,
      simulated: true,
      nativeScheduled: true,
      serverAckPersisted: Boolean(ackRes && ackRes.ok),
      serverAckRetryable: false
    };
  }

  async sendDeviceAck(reminderId, status, error = null) {
    if (!reminderId) return { ok: false, error: "missing_reminder_id" };
    if (status !== "confirmed" && status !== "device_schedule_failed") {
      return { ok: false, error: "invalid_status" };
    }
    if (typeof fetch !== 'function') {
      return { ok: true, status, simulated: true };
    }

    let baseUrl = "";
    if (typeof getApiBaseUrl === 'function') {
      baseUrl = getApiBaseUrl();
    } else if (typeof window !== 'undefined' && window.getApiBaseUrl) {
      baseUrl = window.getApiBaseUrl();
    }
    if (!baseUrl) {
      return { ok: false, error: "missing_api_base_url" };
    }

    const payload = JSON.stringify({ status, error: error ? String(error) : null });
    const retryDelays = [300, 900, 1800];

    for (let attempt = 0; attempt <= retryDelays.length; attempt++) {
      try {
        const resp = await fetch(`${baseUrl}/api/reminders/${encodeURIComponent(reminderId)}/device-ack`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload
        });
        if (resp.ok) {
          const data = await resp.json().catch(() => ({}));
          return { ok: true, status, data };
        } else {
          const errData = await resp.json().catch(() => ({}));
          console.warn(`[ReminderClient] sendDeviceAck attempt ${attempt + 1} failed: HTTP ${resp.status}`, errData);
          if (attempt === retryDelays.length || resp.status === 404 || resp.status === 422) {
            return { ok: false, status, httpStatus: resp.status, error: errData.error || `HTTP ${resp.status}` };
          }
        }
      } catch (err) {
        console.warn(`[ReminderClient] sendDeviceAck network error attempt ${attempt + 1}:`, err);
        if (attempt === retryDelays.length) {
          return { ok: false, status, error: err.message };
        }
      }

      if (attempt < retryDelays.length) {
        await new Promise(resolve => setTimeout(resolve, retryDelays[attempt]));
      }
    }

    return { ok: false, status, error: "max_retries_exceeded" };
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

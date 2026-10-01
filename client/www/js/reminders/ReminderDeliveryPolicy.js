/**
 * REMINDER DELIVERY POLICY (V3.1 Reliability)
 * 
 * Invariants:
 * - Native Android AlarmManager is the exclusive authority on Android.
 * - Browser interval polling is enabled ONLY when native bridge is absent.
 * - Native ACK validation fails closed on malformed/mismatched data.
 */

class ReminderDeliveryPolicy {
  /**
   * Xác định môi trường có sử dụng Android AlarmManager native hay không
   */
  static isNativeAuthority(windowObj = null) {
    const w = windowObj || (typeof window !== 'undefined' ? window : null);
    return Boolean(w && w.AndroidNova && typeof w.AndroidNova.scheduleNativeAlarm === 'function');
  }

  /**
   * Cho phép polling kiểm tra reminder bằng JS interval chỉ trên trình duyệt web thuần
   */
  static shouldPollBrowserDelivery(windowObj = null) {
    return !ReminderDeliveryPolicy.isNativeAuthority(windowObj);
  }

  /**
   * Kiểm tra tính hợp lệ của Native ACK từ Android hardware
   * Bắt buộc:
   * - JSON parse thành công
   * - ok là kiểu boolean
   * - reminder_id khớp chính xác với ID đã yêu cầu
   */
  static validateNativeAck(ackRaw, expectedReminderId) {
    if (!expectedReminderId) {
      return { ok: false, error: "missing_expected_reminder_id" };
    }

    let ack = ackRaw;
    if (typeof ackRaw === 'string') {
      try {
        ack = JSON.parse(ackRaw);
      } catch (err) {
        return { ok: false, reminder_id: expectedReminderId, error: "invalid_native_ack" };
      }
    }

    if (!ack || typeof ack !== 'object' || Array.isArray(ack)) {
      return { ok: false, reminder_id: expectedReminderId, error: "invalid_native_ack" };
    }

    if (typeof ack.ok !== 'boolean') {
      return { ok: false, reminder_id: expectedReminderId, error: "invalid_native_ack" };
    }

    if (ack.reminder_id !== expectedReminderId) {
      return { ok: false, reminder_id: expectedReminderId, error: "mismatched_reminder_id" };
    }

    return {
      ok: ack.ok,
      reminder_id: ack.reminder_id,
      exact: ack.exact !== undefined ? Boolean(ack.exact) : true,
      pending_intent_id: ack.pending_intent_id,
      scheduled_at_epoch_ms: ack.scheduled_at_epoch_ms,
      error: ack.ok ? null : (ack.error || ack.message || "native_schedule_failed")
    };
  }
}

if (typeof window !== 'undefined') {
  window.ReminderDeliveryPolicy = ReminderDeliveryPolicy;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    ReminderDeliveryPolicy
  };
}

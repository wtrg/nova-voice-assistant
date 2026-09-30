/**
 * DIAGNOSTICS PANEL CONTROLLER
 * 
 * Kiểm tra toàn diện hệ thống theo Section 31 của Reliability Plan:
 * - Kết nối Backend & Latency
 * - Trạng thái Cuppy Neural TTS (/health/voice)
 * - Quyền Microphone
 * - Quyền Báo thức chính xác (Exact Alarm)
 * - Quyền Thông báo (Notification)
 */

class DiagnosticsPanel {
  constructor(apiBaseUrl) {
    this.apiBaseUrl = apiBaseUrl;
  }

  async runFullDiagnostics() {
    const results = {
      timestamp: new Date().toISOString(),
      backendReachable: false,
      backendLatencyMs: 0,
      cuppyVoiceStatus: "unknown",
      cuppyModelLoaded: false,
      exactAlarmGranted: false,
      notificationsEnabled: false,
      hasNativeBridge: false
    };

    // 1. Kiểm tra Native Android Bridge & Quyền
    if (typeof window !== 'undefined' && window.AndroidNova) {
      results.hasNativeBridge = true;
      if (typeof window.AndroidNova.canScheduleExactAlarms === 'function') {
        results.exactAlarmGranted = Boolean(window.AndroidNova.canScheduleExactAlarms());
      }
      if (typeof window.AndroidNova.areNotificationsEnabled === 'function') {
        results.notificationsEnabled = Boolean(window.AndroidNova.areNotificationsEnabled());
      }
    }

    // 2. Kiểm tra Backend & Đo độ trễ
    const t0 = performance.now();
    try {
      const res = await fetch(`${this.apiBaseUrl}/health`, { signal: AbortSignal.timeout(4000) });
      results.backendLatencyMs = Math.round(performance.now() - t0);
      if (res.ok) {
        results.backendReachable = true;
      }
    } catch (e) {
      results.backendReachable = false;
      results.backendLatencyMs = Math.round(performance.now() - t0);
    }

    // 3. Kiểm tra Cuppy Voice Health
    if (results.backendReachable) {
      try {
        const vRes = await fetch(`${this.apiBaseUrl}/health/voice`, { signal: AbortSignal.timeout(4000) });
        if (vRes.ok) {
          const vData = await vRes.json();
          results.cuppyVoiceStatus = vData.status || "ok";
          results.cuppyModelLoaded = Boolean(vData.model_loaded);
        }
      } catch (e) {
        results.cuppyVoiceStatus = "unreachable";
      }
    }

    return results;
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DiagnosticsPanel
  };
}

/**
 * DIAGNOSTICS PANEL CONTROLLER (V4-18)
 * 
 * Kiểm tra 9 hạng mục vận hành toàn diện mà không kích hoạt side-effect thật:
 * 1. Backend
 * 2. LLM
 * 3. TTS
 * 4. Microphone
 * 5. Notifications
 * 6. Exact alarm
 * 7. Full-screen
 * 8. Default assistant
 * 9. Hotword
 */

class DiagnosticsPanel {
  constructor(apiBaseUrl) {
    this.apiBaseUrl = apiBaseUrl || (typeof AppConfig !== 'undefined' ? AppConfig.getApiBaseUrl() : "");
  }

  async runFullDiagnostics() {
    const baseUrl = this.apiBaseUrl || (typeof AppConfig !== 'undefined' ? AppConfig.getApiBaseUrl() : "");
    const results = {
      timestamp: new Date().toISOString(),
      backendReachable: false,
      backendLatencyMs: 0,
      serverVersion: "",
      minClientVersion: "",
      llmReady: false,
      ttsReady: false,
      ttsPrimary: "vieneu",
      ttsPrimaryReady: false,
      databaseReady: false,
      microphoneGranted: false,
      notificationsEnabled: false,
      exactAlarmGranted: false,
      fullScreenGranted: false,
      defaultAssistantActive: false,
      hotwordAvailable: false,
      hotwordRunning: false,
      hasNativeBridge: false
    };

    // 1. Kiểm tra Native Android Bridge & Quyền hệ điều hành
    if (typeof window !== 'undefined' && window.AndroidNova) {
      results.hasNativeBridge = true;
      if (typeof window.AndroidNova.canScheduleExactAlarms === 'function') {
        results.exactAlarmGranted = Boolean(window.AndroidNova.canScheduleExactAlarms());
      }
      if (typeof window.AndroidNova.areNotificationsEnabled === 'function') {
        results.notificationsEnabled = Boolean(window.AndroidNova.areNotificationsEnabled());
      }
      if (typeof window.AndroidNova.canUseFullScreenIntent === 'function') {
        results.fullScreenGranted = Boolean(window.AndroidNova.canUseFullScreenIntent());
      }
      if (typeof window.AndroidNova.isDefaultAssistantActive === 'function') {
        results.defaultAssistantActive = Boolean(window.AndroidNova.isDefaultAssistantActive());
      }
      if (typeof window.AndroidNova.isHotwordServiceRunning === 'function') {
        results.hotwordRunning = Boolean(window.AndroidNova.isHotwordServiceRunning());
        results.hotwordAvailable = true;
      }
      if (typeof window.AndroidNova.isNativeSpeechAvailable === 'function') {
        results.microphoneGranted = Boolean(window.AndroidNova.isNativeSpeechAvailable());
      }
    }

    // 2. Kiểm tra Microphone qua Web Audio API nếu chưa có native result
    if (!results.microphoneGranted && typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        if (navigator.permissions && navigator.permissions.query) {
          const perm = await navigator.permissions.query({ name: 'microphone' });
          results.microphoneGranted = (perm.state === 'granted');
        }
      } catch (ignored) {}
    }

    // 3. Kiểm tra Backend Readiness (/health/ready) và đo độ trễ
    const t0 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    try {
      const res = await fetch(`${baseUrl}/health/ready`, {
        signal: (typeof AbortSignal !== 'undefined' && AbortSignal.timeout) ? AbortSignal.timeout(4000) : undefined,
        headers: {
          "X-Nova-Client-Version": (typeof AppConfig !== 'undefined' ? AppConfig.appVersion : "2.0.0"),
          "X-Nova-Build-SHA": (typeof AppConfig !== 'undefined' ? AppConfig.buildSha : "v2.0.0")
        }
      });
      const t1 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
      results.backendLatencyMs = Math.round(t1 - t0);

      if (res.ok || res.status === 503) {
        results.backendReachable = true;
        const data = await res.json();
        results.serverVersion = data.server_version || data.version || "";
        results.minClientVersion = data.min_client_version || "";
        results.llmReady = Boolean(data.llm);
        results.ttsReady = Boolean(data.tts);
        results.ttsPrimary = data.tts_primary || "vieneu";
        results.ttsPrimaryReady = Boolean(data.tts_primary_ready);
        results.databaseReady = Boolean(data.database);
      }
    } catch (e) {
      results.backendReachable = false;
      const t1 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
      results.backendLatencyMs = Math.round(t1 - t0);
    }

    return results;
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DiagnosticsPanel
  };
}

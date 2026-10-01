/**
 * APP CONFIG SINGLE SOURCE OF TRUTH (V4-16)
 * 
 * Invariant:
 * Cung cấp cấu hình thống nhất cho Android Native và Web Layer.
 * Không hardcode địa chỉ máy chủ phân tán ở nhiều file.
 */

(function(window) {
  'use strict';

  const AppConfig = {
    apiBaseUrl: "https://nova-voice-assistant-6l5s.onrender.com",
    environment: "production",
    appVersion: "2.0.0",
    buildSha: "v2.0.0",
    featureHotword: false,
    featureDefaultAssistant: true,
    ttsMode: "cuppy",

    init: function() {
      // 1. Đồng bộ cấu hình từ Native Android Bridge nếu đang chạy trong APK
      if (typeof window !== 'undefined' && window.AndroidNova && typeof window.AndroidNova.getAppConfigJson === 'function') {
        try {
          const raw = window.AndroidNova.getAppConfigJson();
          if (raw) {
            const parsed = JSON.parse(raw);
            Object.assign(this, parsed);
          }
        } catch (e) {
          console.warn("[AppConfig] Không thể đọc cấu hình từ Android bridge:", e);
        }
      } else if (typeof localStorage !== 'undefined') {
        // 2. Chế độ trình duyệt hoặc Developer Settings override
        const savedUrl = localStorage.getItem("nova_backend_url");
        if (savedUrl && savedUrl.trim()) {
          this.apiBaseUrl = savedUrl.trim().replace(/\/+$/, "");
        }
      }
    },

    getApiBaseUrl: function() {
      return this.apiBaseUrl;
    },

    setApiBaseUrl: function(url) {
      if (!url) return;
      this.apiBaseUrl = url.trim().replace(/\/+$/, "");
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem("nova_backend_url", this.apiBaseUrl);
      }
      if (typeof window !== 'undefined' && window.AndroidNova && typeof window.AndroidNova.setServerBaseUrl === 'function') {
        try {
          window.AndroidNova.setServerBaseUrl(this.apiBaseUrl);
        } catch (e) {}
      }
    }
  };

  AppConfig.init();

  if (typeof window !== 'undefined') {
    window.AppConfig = AppConfig;
    window.getApiBaseUrl = function() {
      return AppConfig.getApiBaseUrl();
    };
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AppConfig };
  }
})(typeof window !== 'undefined' ? window : global);

/**
 * Nova Cyber Infinity Soul — Visual Event Bridge
 * Section 22 of Nova Design System
 * Bridges existing TurnController & speech lifecycle events to NovaVisualState & NovaScene
 */
class VisualEventBridge {
  constructor(novaSceneInstance) {
    this.novaScene = novaSceneInstance;
    this.statusPill = null;
    this.statusLabel = null;
    this.micHeroWrapper = null;
    this.waveformEl = null;
    this.assistantSubtext = null;
    this._unsubscribe = null;
    this.init();
  }

  setScene(scene) {
    this.novaScene = scene;
  }

  init() {
    this._cacheDom();

    if (typeof NovaVisualState !== "undefined") {
      this._unsubscribe = NovaVisualState.subscribe((newState) => {
        this._applyStateToDom(newState);
        if (this.novaScene && typeof this.novaScene.setState === "function") {
          this.novaScene.setState(newState);
        }
      });
    }
  }

  _cacheDom() {
    if (typeof document === "undefined") return;
    this.statusPill = document.getElementById("statusPill");
    this.statusLabel = document.getElementById("statusLabel");
    this.micHeroWrapper = document.getElementById("micHeroWrapper");
    this.waveformEl = document.getElementById("waveformBox");
    this.assistantSubtext = document.getElementById("assistantSubtext");
  }

  _applyStateToDom(state) {
    this._cacheDom();

    // 1. Update Status Pill
    if (this.statusPill) {
      this.statusPill.className = `status-pill ${state}`;
    }

    // 2. Update Status Label & Subtext
    let labelText = "Sẵn sàng";
    let subtext = "Bạn cứ nói, Nova ở đây cùng bạn.";

    switch (state) {
      case "listening":
        labelText = "Đang lắng nghe...";
        subtext = "Nova đang chăm chú lắng nghe bạn.";
        break;
      case "thinking":
        labelText = "Đang suy nghĩ...";
        subtext = "Đang phân tích và xử lý thông tin...";
        break;
      case "speaking":
        labelText = "Đang phản hồi";
        subtext = "Nova đang trò chuyện cùng bạn.";
        break;
      case "error":
        labelText = "Lỗi kết nối";
        subtext = "Vui lòng thử lại hoặc kiểm tra kết nối.";
        break;
      case "idle":
      default:
        labelText = "Sẵn sàng lắng nghe";
        subtext = "Bạn cứ nói, Nova ở đây cùng bạn.";
        break;
    }

    if (this.statusLabel) this.statusLabel.textContent = labelText;
    if (this.assistantSubtext) this.assistantSubtext.textContent = subtext;

    // 3. Update Mic Button Halo
    if (this.micHeroWrapper) {
      if (state === "listening" || state === "speaking") {
        this.micHeroWrapper.classList.add("active");
      } else {
        this.micHeroWrapper.classList.remove("active");
      }
    }

    // 4. Update Waveform
    if (this.waveformEl) {
      if (state === "listening" || state === "speaking") {
        this.waveformEl.classList.add("active");
      } else {
        this.waveformEl.classList.remove("active");
      }
    }
  }

  // Lifecycle Hooks called from host application
  onMicStart() {
    if (typeof NovaVisualState !== "undefined") NovaVisualState.set("listening");
  }

  onMicStop() {
    if (typeof NovaVisualState !== "undefined" && NovaVisualState.get() === "listening") {
      NovaVisualState.set("thinking");
    }
  }

  onSpeechStart() {
    if (typeof NovaVisualState !== "undefined") NovaVisualState.set("speaking");
  }

  onSpeechEnd() {
    if (typeof NovaVisualState !== "undefined") NovaVisualState.set("idle");
  }

  onError() {
    if (typeof NovaVisualState !== "undefined") NovaVisualState.set("error");
  }

  destroy() {
    if (this._unsubscribe) this._unsubscribe();
  }
}

if (typeof window !== "undefined") {
  window.VisualEventBridge = VisualEventBridge;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = VisualEventBridge;
}

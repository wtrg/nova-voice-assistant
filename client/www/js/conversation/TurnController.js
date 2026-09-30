/**
 * TURN CONTROLLER
 * 
 * Quản lý định danh phiên đàm thoại (Correlation Turn ID).
 * Đảm bảo:
 * - 1 lượt đàm thoại duy nhất tại một thời điểm
 * - Loại bỏ hoàn toàn callback cũ / rác (stale callbacks)
 * - Xử lý ngắt lời (Interrupt) lập tức: hủy âm thanh và quay lại nghe
 */

function generateUuid() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'turn-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
}

class TurnController {
  constructor(stateMachine) {
    this.sm = stateMachine;
    this.activeTurnId = null;
    this.activeTtsRequestId = null;
    this.activeTurnMeta = null;
  }

  /**
   * Bắt đầu một lượt đàm thoại mới
   * @param {string} userText 
   * @returns {string} turnId
   */
  startNewTurn(userText = "") {
    // 1. Hủy bỏ lượt cũ nếu còn đang dang dở
    if (this.activeTurnId) {
      this.cancelCurrentTurn("new_turn_started");
    }

    const turnId = generateUuid();
    this.activeTurnId = turnId;
    this.activeTtsRequestId = null;
    this.activeTurnMeta = {
      turnId,
      userText,
      startTime: Date.now(),
      status: "active"
    };

    if (this.sm) {
      this.sm.transition("WAITING_LLM", { turnId, userText });
    }

    return turnId;
  }

  /**
   * Đăng ký một TTS request ID cho lượt hiện tại
   * @param {string} turnId 
   * @returns {string} ttsRequestId
   */
  createTtsRequest(turnId) {
    if (turnId !== this.activeTurnId) {
      console.warn(`[TurnController] Cannot create TTS for inactive turn: ${turnId}`);
      return null;
    }
    const ttsId = 'tts-' + Date.now() + '-' + Math.random().toString(36).substr(2, 6);
    this.activeTtsRequestId = ttsId;
    if (this.sm) {
      this.sm.transition("WAITING_TTS", { turnId, ttsRequestId: ttsId });
    }
    return ttsId;
  }

  /**
   * Kiểm tra xem một sự kiện (STT/TTS) có thuộc lượt active hiện tại không
   * @param {string} turnId 
   * @param {string} ttsRequestId 
   * @returns {boolean}
   */
  isCurrentTurn(turnId, ttsRequestId = null) {
    if (!turnId || turnId !== this.activeTurnId) {
      return false;
    }
    if (ttsRequestId && ttsRequestId !== this.activeTtsRequestId) {
      return false;
    }
    return true;
  }

  /**
   * Đánh dấu lượt hiện tại đang nói
   */
  markSpeaking(turnId) {
    if (this.isCurrentTurn(turnId)) {
      if (this.sm) {
        this.sm.transition("SPEAKING", { turnId });
      }
    }
  }

  /**
   * Kết thúc lượt đàm thoại thành công
   * @param {string} turnId 
   */
  finishTurn(turnId) {
    if (this.isCurrentTurn(turnId)) {
      if (this.activeTurnMeta) {
        this.activeTurnMeta.status = "completed";
        this.activeTurnMeta.duration = Date.now() - this.activeTurnMeta.startTime;
      }
      this.activeTurnId = null;
      this.activeTtsRequestId = null;
      if (this.sm) {
        this.sm.transition("IDLE", { turnId });
      }
    }
  }

  /**
   * Hủy bỏ lượt đàm thoại ngay lập tức khi người dùng ngắt lời
   * @param {string} reason 
   */
  cancelCurrentTurn(reason = "user_interrupt") {
    if (!this.activeTurnId) return;

    const cancelledId = this.activeTurnId;
    if (this.activeTurnMeta) {
      this.activeTurnMeta.status = "cancelled";
      this.activeTurnMeta.cancelReason = reason;
    }

    this.activeTurnId = null;
    this.activeTtsRequestId = null;

    if (this.sm) {
      this.sm.transition("CANCELLED", { turnId: cancelledId, reason });
    }

    // Dừng toàn bộ âm thanh phần cứng và web
    if (typeof window !== 'undefined') {
      if (window.AndroidNova && typeof window.AndroidNova.stopAudio === 'function') {
        try { window.AndroidNova.stopAudio(); } catch(e){}
      }
    }
  }
}

if (typeof window !== 'undefined') {
  window.TurnController = TurnController;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    TurnController
  };
}

/**
 * AUDIO REQUEST REGISTRY (V3.1 Reliability)
 * 
 * Invariants:
 * - Every async audio callback and timer belongs to exactly one owner turn.
 * - Every timer that can mutate speech/UI state is cancellable and owner-turn-bound.
 * - Stale callbacks or timers cannot start audio, continue a sequence, or finish another turn.
 */

class AudioRequestRegistry {
  constructor() {
    this.activeRequests = new Map();
  }

  /**
   * Đăng ký một request âm thanh với ownerTurnId và callbacks
   */
  registerRequest(requestId, { turnId = null, onStart = null, onDone = null, onFail = null, isFallback = false } = {}) {
    if (!requestId) return null;
    const reqEntry = {
      requestId,
      turnId,
      cancelled: false,
      timers: new Set(),
      onStart,
      onDone,
      onFail,
      isFallback,
      connectTimeout: null
    };
    this.activeRequests.set(requestId, reqEntry);
    return reqEntry;
  }

  getRequest(requestId) {
    return this.activeRequests.get(requestId) || null;
  }

  /**
   * Lên lịch một timer thuộc quyền sở hữu của request và owner turn
   */
  scheduleRequestTimer(requestId, fn, delayMs, turnController = null) {
    const req = this.getRequest(requestId);
    if (!req || req.cancelled) return null;

    let timerId = null;
    timerId = setTimeout(() => {
      if (req.timers) {
        req.timers.delete(timerId);
      }
      if (req.cancelled) return;
      if (req.turnId && turnController && !turnController.isCurrentTurn(req.turnId)) {
        return;
      }
      fn();
    }, delayMs);

    req.timers.add(timerId);
    return timerId;
  }

  /**
   * Xóa tất cả timers thuộc request
   */
  clearRequestTimers(requestId) {
    const req = this.getRequest(requestId);
    if (!req) return;
    if (req.timers) {
      for (const id of req.timers) {
        clearTimeout(id);
      }
      req.timers.clear();
    }
    if (req.connectTimeout) {
      clearTimeout(req.connectTimeout);
      req.connectTimeout = null;
    }
  }

  /**
   * Hoàn tất hoặc kết thúc request bình thường (kể cả fail)
   * Xóa timers, dọn dẹp entry khỏi activeRequests nhưng KHÔNG đánh dấu cancelled
   */
  finalizeRequest(requestId) {
    if (!requestId) return;
    const req = this.activeRequests.get(requestId);
    if (req) {
      this.clearRequestTimers(requestId);
      this.activeRequests.delete(requestId);
    }
  }

  /**
   * Hủy một request cụ thể do user ngắt lời hoặc stale turn
   */
  cancelRequest(requestId, reason = "user_cancel") {
    if (!requestId) return;
    const req = this.activeRequests.get(requestId);
    if (req) {
      req.cancelled = true;
      req.cancelReason = reason;
      this.clearRequestTimers(requestId);
      this.activeRequests.delete(requestId);
    }
  }

  /**
   * Lên lịch timer gắn với turnId (dành cho timer cấp turn như UI timeout 250ms)
   */
  scheduleTurnTimer(turnId, fn, delayMs, turnController = null) {
    if (!turnId) return null;
    if (!this.turnTimers) {
      this.turnTimers = new Map();
    }
    if (!this.turnTimers.has(turnId)) {
      this.turnTimers.set(turnId, new Set());
    }

    let timerId = null;
    timerId = setTimeout(() => {
      const set = this.turnTimers ? this.turnTimers.get(turnId) : null;
      if (set) {
        set.delete(timerId);
      }
      if (turnController && !turnController.isCurrentTurn(turnId)) {
        return;
      }
      fn();
    }, delayMs);

    this.turnTimers.get(turnId).add(timerId);
    return timerId;
  }

  /**
   * Xóa toàn bộ timer thuộc turnId
   */
  clearTurnTimers(turnId) {
    if (!turnId || !this.turnTimers || !this.turnTimers.has(turnId)) return;
    const timers = this.turnTimers.get(turnId);
    for (const id of timers) {
      clearTimeout(id);
    }
    timers.clear();
    this.turnTimers.delete(turnId);
  }

  /**
   * Hủy toàn bộ request và timer của một turn cụ thể
   */
  cancelAllForTurn(turnId, reason = "turn_cancelled") {
    if (!turnId) return;
    this.clearTurnTimers(turnId);
    for (const [reqId, req] of this.activeRequests.entries()) {
      if (req.turnId === turnId) {
        this.cancelRequest(reqId, reason);
      }
    }
  }

  /**
   * Hủy toàn bộ request âm thanh và timer đang hoạt động khi người dùng ngắt lời
   */
  cancelAllRequests(reason = "global_cancel") {
    if (this.turnTimers) {
      for (const [tid, timers] of this.turnTimers.entries()) {
        for (const id of timers) {
          clearTimeout(id);
        }
        timers.clear();
      }
      this.turnTimers.clear();
    }
    for (const [reqId, req] of this.activeRequests.entries()) {
      req.cancelled = true;
      req.cancelReason = reason;
      if (req.timers) {
        for (const id of req.timers) {
          clearTimeout(id);
        }
        req.timers.clear();
      }
      if (req.connectTimeout) {
        clearTimeout(req.connectTimeout);
        req.connectTimeout = null;
      }
    }
    this.activeRequests.clear();
  }

  /**
   * Kiểm tra owner turn có đang là turn active hiện tại không
   */
  isOwnerTurnCurrent(ownerTurnId, turnController = null) {
    if (!ownerTurnId || !turnController) return true;
    return turnController.isCurrentTurn(ownerTurnId);
  }

  /**
   * Điều phối sự kiện âm thanh nhận từ Android native hoặc Web player
   */
  dispatchAudioEvent(requestId, event, turnController = null) {
    if (!requestId) return false;

    const handler = this.activeRequests.get(requestId);
    if (!handler) {
      return false;
    }

    if (handler.cancelled) {
      this.clearRequestTimers(requestId);
      this.activeRequests.delete(requestId);
      return false;
    }

    if (handler.turnId && turnController && !turnController.isCurrentTurn(handler.turnId)) {
      this.clearRequestTimers(requestId);
      this.activeRequests.delete(requestId);
      return false;
    }

    if (event === "started") {
      if (handler.connectTimeout) {
        clearTimeout(handler.connectTimeout);
        handler.connectTimeout = null;
      }
      if (typeof handler.onStart === 'function') {
        handler.onStart();
      }
      return true;
    } else if (event === "completed") {
      this.clearRequestTimers(requestId);
      this.activeRequests.delete(requestId);
      if (typeof handler.onDone === 'function') {
        handler.onDone();
      }
      return true;
    } else if (event === "failed" || event === "cancelled") {
      this.clearRequestTimers(requestId);
      this.activeRequests.delete(requestId);
      if (typeof handler.onFail === 'function') {
        handler.onFail();
      }
      return true;
    }

    return false;
  }
}

if (typeof window !== 'undefined') {
  window.AudioRequestRegistry = AudioRequestRegistry;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    AudioRequestRegistry
  };
}

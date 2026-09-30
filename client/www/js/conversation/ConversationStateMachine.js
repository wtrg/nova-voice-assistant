/**
 * CONVERSATION STATE MACHINE
 * 
 * Quản lý trạng thái vòng đời của một lượt đàm thoại (Conversation Turn).
 * Invariant: Tránh race conditions, chỉ 1 trạng thái hợp lệ tại một thời điểm.
 */

const ConversationState = {
  IDLE: "IDLE",
  LISTENING: "LISTENING",
  FINALIZING_STT: "FINALIZING_STT",
  WAITING_LLM: "WAITING_LLM",
  WAITING_TTS: "WAITING_TTS",
  SPEAKING: "SPEAKING",
  REARMING_MIC: "REARMING_MIC",
  CANCELLED: "CANCELLED"
};

class ConversationStateMachine {
  constructor(initialState = ConversationState.IDLE) {
    this.state = initialState;
    this.listeners = [];
  }

  getState() {
    return this.state;
  }

  is(state) {
    return this.state === state;
  }

  canTransitionTo(nextState) {
    // CANCELLED hoặc IDLE có thể được kích hoạt từ bất kỳ trạng thái nào (ví dụ khi ngắt lời)
    if (nextState === ConversationState.IDLE || nextState === ConversationState.CANCELLED) {
      return true;
    }

    switch (this.state) {
      case ConversationState.IDLE:
        return nextState === ConversationState.LISTENING;

      case ConversationState.LISTENING:
        return nextState === ConversationState.FINALIZING_STT || nextState === ConversationState.IDLE;

      case ConversationState.FINALIZING_STT:
        return nextState === ConversationState.WAITING_LLM || nextState === ConversationState.LISTENING;

      case ConversationState.WAITING_LLM:
        return nextState === ConversationState.WAITING_TTS || nextState === ConversationState.SPEAKING;

      case ConversationState.WAITING_TTS:
        return nextState === ConversationState.SPEAKING || nextState === ConversationState.IDLE;

      case ConversationState.SPEAKING:
        return nextState === ConversationState.REARMING_MIC || nextState === ConversationState.IDLE;

      case ConversationState.REARMING_MIC:
        return nextState === ConversationState.LISTENING || nextState === ConversationState.IDLE;

      case ConversationState.CANCELLED:
        return nextState === ConversationState.IDLE || nextState === ConversationState.LISTENING || nextState === ConversationState.WAITING_LLM;

      default:
        return false;
    }
  }

  transition(nextState, context = {}) {
    if (!this.canTransitionTo(nextState)) {
      console.warn(`[StateMachine] Invalid transition: ${this.state} -> ${nextState}`);
      return false;
    }

    const prevState = this.state;
    this.state = nextState;

    for (const listener of this.listeners) {
      try {
        listener(nextState, prevState, context);
      } catch (e) {
        console.error("[StateMachine] Listener error:", e);
      }
    }
    return true;
  }

  onTransition(fn) {
    if (typeof fn === 'function') {
      this.listeners.push(fn);
    }
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    ConversationState,
    ConversationStateMachine
  };
}

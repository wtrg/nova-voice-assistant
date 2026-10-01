/**
 * Nova Cyber Infinity Soul — Visual State Store
 * Section 16 & 22 of Nova Design System
 */
class NovaVisualStateStore {
  constructor() {
    this.currentState = "idle"; // idle | listening | thinking | speaking | error | success
    this.listeners = new Set();
  }

  get() {
    return this.currentState;
  }

  set(state) {
    if (this.currentState === state) return;
    const prevState = this.currentState;
    this.currentState = state;
    this._notify(state, prevState);
  }

  subscribe(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  _notify(newState, prevState) {
    for (const listener of this.listeners) {
      try {
        listener(newState, prevState);
      } catch (err) {
        console.error("[NovaVisualState] Listener error:", err);
      }
    }
  }
}

const NovaVisualState = new NovaVisualStateStore();

if (typeof window !== "undefined") {
  window.NovaVisualState = NovaVisualState;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = NovaVisualState;
}

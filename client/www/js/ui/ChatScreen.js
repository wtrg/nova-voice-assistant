/**
 * Nova Cyber Infinity Soul — Chat Screen Controller
 * Section 26 of Nova Design System
 */
class ChatScreen {
  constructor() {
    this.container = null;
    this.input = null;
    this.sendBtn = null;
  }

  init() {
    this.container = document.getElementById("chatMessages");
    this.input = document.getElementById("chatInput");
    this.sendBtn = document.getElementById("chatSendBtn");

    if (this.input) {
      this.input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.submitMessage();
        }
      });
      this.input.addEventListener("input", () => {
        if (this.sendBtn) {
          if (this.input.value.trim().length > 0) {
            this.sendBtn.classList.add("send-active");
          } else {
            this.sendBtn.classList.remove("send-active");
          }
        }
      });
    }

    if (this.sendBtn) {
      this.sendBtn.addEventListener("click", () => this.submitMessage());
    }
  }

  submitMessage() {
    if (!this.input) return;
    const text = this.input.value.trim();
    if (!text) return;

    this.input.value = "";
    if (this.sendBtn) this.sendBtn.classList.remove("send-active");

    // Call global assistant text sender
    if (typeof window.sendUserUtterance === "function") {
      window.sendUserUtterance(text);
    }
  }

  appendUserMessage(text) {
    if (!this.container) return;
    const row = document.createElement("div");
    row.className = "message-row user";
    row.innerHTML = `<div class="message-bubble">${this._escapeHtml(text)}</div>`;
    this.container.appendChild(row);
    this.scrollToBottom();
  }

  appendNovaMessage(text, actionData = null) {
    if (!this.container) return;
    const row = document.createElement("div");
    row.className = "message-row nova";

    let contentHtml = `<div class="message-bubble">${this._escapeHtml(text)}`;

    // Render structured action card if provided
    if (actionData && actionData.items && actionData.items.length > 0) {
      contentHtml += `
        <div class="action-card">
          <div class="action-card-header">
            <span>🎯 ${this._escapeHtml(actionData.title || "Ưu tiên hôm nay")}</span>
          </div>
          ${actionData.items.map((item, idx) => `
            <div class="action-card-item">
              <span class="action-card-badge">${idx + 1}</span>
              <span>${this._escapeHtml(item)}</span>
            </div>
          `).join("")}
        </div>
      `;
    }

    contentHtml += `</div>`;
    row.innerHTML = `
      <div class="message-avatar-mini">
        <svg viewBox="0 0 512 512" width="16" height="16">
          <path d="M 256,256 C 290,210 330,172 384,172 C 440,172 478,210 478,256 C 478,302 440,340 384,340 C 330,340 290,302 256,256 C 222,210 182,172 128,172 C 72,172 34,210 34,256 C 34,302 72,340 128,340 C 182,340 222,302 256,256 Z"
                fill="none" stroke="#8CC8FF" stroke-width="40"/>
          <circle cx="256" cy="256" r="32" fill="#5AA9FF"/>
        </svg>
      </div>
      ${contentHtml}
    `;
    this.container.appendChild(row);
    this.scrollToBottom();
  }

  scrollToBottom() {
    if (this.container) {
      this.container.scrollTop = this.container.scrollHeight;
    }
  }

  _escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
}

if (typeof window !== "undefined") {
  window.ChatScreen = ChatScreen;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = ChatScreen;
}

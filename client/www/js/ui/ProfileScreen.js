/**
 * Nova Cyber Infinity Soul — Profile Screen Controller
 * Section 28 of Nova Design System
 */
class ProfileScreen {
  constructor() {
    this.container = null;
  }

  init() {
    this.container = document.getElementById("screen-profile");
    this.render();
  }

  render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="profile-content">
        <!-- Hero Card -->
        <div class="profile-hero-card">
          <div class="profile-avatar-circle">
            <div class="profile-avatar-inner">👑</div>
          </div>
          <div>
            <div class="profile-name">Người Bạn Đồng Hành</div>
            <div class="profile-badge-pro">★ Nova Pro</div>
            <div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">
              Đồng hành kiến tạo phiên bản tốt nhất của bạn.
            </div>
          </div>
        </div>

        <!-- Stats Row -->
        <div class="profile-stats-row">
          <div class="profile-stat-box">
            <div class="stat-value">248</div>
            <div class="stat-label">Ngày đồng hành</div>
          </div>
          <div class="profile-stat-box">
            <div class="stat-value">36</div>
            <div class="stat-label">Lịch hoàn thành</div>
          </div>
          <div class="profile-stat-box">
            <div class="stat-value">A+</div>
            <div class="stat-label">Tiến bộ kỷ luật</div>
          </div>
        </div>

        <!-- Settings Group 1: Voice & Assistant -->
        <div class="settings-group">
          <div class="settings-item" onclick="handleOpenAssistantSettings()">
            <div class="settings-item-left">
              <span class="settings-item-icon">⚙️</span>
              <div>
                <div style="font-weight: 600; color: var(--nova-silver-100);">Trợ lý mặc định hệ thống</div>
                <div style="font-size: 11px; color: var(--text-dim);">Nhấn giữ nguồn 0.5s gọi Nova</div>
              </div>
            </div>
            <span style="color: var(--text-dim);">›</span>
          </div>

          <div class="settings-item" onclick="playStudioCuppyVoice()">
            <div class="settings-item-left">
              <span class="settings-item-icon">🎙️</span>
              <div>
                <div style="font-weight: 600; color: var(--nova-silver-100);">Giọng nói độc quyền Cuppy</div>
                <div style="font-size: 11px; color: var(--text-dim);">Reference Voice Clone 48kHz</div>
              </div>
            </div>
            <span style="color: var(--nova-blue-bright); font-size: 11px;">▶ Nghe thử</span>
          </div>

          <div class="settings-item" onclick="toggleWakeWord()">
            <div class="settings-item-left">
              <span class="settings-item-icon">⚡</span>
              <div>
                <div style="font-weight: 600; color: var(--nova-silver-100);">Đánh thức "Hey Nova"</div>
                <div id="profileWakeStatus" style="font-size: 11px; color: var(--text-dim);">Chế độ rảnh tay: Đang tắt</div>
              </div>
            </div>
            <span style="color: var(--text-dim);">›</span>
          </div>
        </div>

        <!-- Settings Group 2: Connectivity & Diagnostics -->
        <div class="settings-group">
          <div class="settings-item" onclick="openServerConfigModal()">
            <div class="settings-item-left">
              <span class="settings-item-icon">🌐</span>
              <div>
                <div style="font-weight: 600; color: var(--nova-silver-100);">Cài đặt kết nối máy chủ</div>
                <div style="font-size: 11px; color: var(--text-dim);">Backend URL & AI Model</div>
              </div>
            </div>
            <span style="color: var(--text-dim);">›</span>
          </div>

          <div class="settings-item" onclick="if(window.diagnosticsPanel) window.diagnosticsPanel.open();">
            <div class="settings-item-left">
              <span class="settings-item-icon">📊</span>
              <div>
                <div style="font-weight: 600; color: var(--nova-silver-100);">Chẩn đoán hệ thống</div>
                <div style="font-size: 11px; color: var(--text-dim);">Ping, STT, TTS Health Check</div>
              </div>
            </div>
            <span style="color: var(--text-dim);">›</span>
          </div>

          <div class="settings-item" onclick="toggleHelpModal()">
            <div class="settings-item-left">
              <span class="settings-item-icon">💡</span>
              <div>
                <div style="font-weight: 600; color: var(--nova-silver-100);">4 Cách đánh thức Nova</div>
                <div style="font-size: 11px; color: var(--text-dim);">Hướng dẫn sử dụng toàn diện</div>
              </div>
            </div>
            <span style="color: var(--text-dim);">›</span>
          </div>
        </div>

        <!-- Settings Group 3: App Info -->
        <div class="settings-group">
          <div class="settings-item">
            <div class="settings-item-left">
              <span class="settings-item-icon">ℹ️</span>
              <div>
                <div style="font-weight: 600; color: var(--nova-silver-100);">Phiên bản ứng dụng</div>
                <div style="font-size: 11px; color: var(--text-dim);">Nova Cyber Infinity Soul v2.0.0</div>
              </div>
            </div>
            <span style="font-size: 11px; color: var(--nova-blue-bright);">Build 2026.10</span>
          </div>

          <div class="settings-item" onclick="localStorage.clear(); location.reload();">
            <div class="settings-item-left">
              <span class="settings-item-icon">🔄</span>
              <div>
                <div style="font-weight: 600; color: #FF6B81;">Xóa bộ nhớ đệm & Đặt lại</div>
                <div style="font-size: 11px; color: var(--text-dim);">Khôi phục cấu hình mặc định</div>
              </div>
            </div>
            <span style="color: #FF6B81;">›</span>
          </div>
        </div>
      </div>
    `;
  }
}

if (typeof window !== "undefined") {
  window.ProfileScreen = ProfileScreen;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = ProfileScreen;
}

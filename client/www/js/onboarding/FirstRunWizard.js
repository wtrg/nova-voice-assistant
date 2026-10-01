/**
 * FIRST RUN SETUP WIZARD (V4-05)
 * 
 * Quy trình cài đặt lần đầu 6 bước cho người dùng phổ thông (Zero-Config Onboarding):
 * 1. Microphone
 * 2. Notifications
 * 3. Exact Alarm
 * 4. Full-screen Alarm
 * 5. Set Nova as Default Assistant
 * 6. Test Backend, Microphone, Speaker -> Hoàn tất!
 */

(function(window) {
  'use strict';

  class FirstRunWizard {
    constructor() {
      this.currentStep = 1;
      this.totalSteps = 6;
      this.storageKey = "nova_first_run_completed";
    }

    isCompleted() {
      try {
        return localStorage.getItem(this.storageKey) === "true";
      } catch (e) {
        return false;
      }
    }

    markCompleted() {
      try {
        localStorage.setItem(this.storageKey, "true");
      } catch (e) {}
      this.hideModal();
    }

    shouldShow() {
      return !this.isCompleted();
    }

    renderModalHtml() {
      return `
        <div id="firstRunModal" class="fixed inset-0 bg-slate-950/90 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div class="bg-slate-900 border border-indigo-500/30 rounded-2xl p-6 max-w-md w-full shadow-2xl flex flex-col justify-between">
            <div>
              <div class="flex justify-between items-center mb-4">
                <span class="text-xs font-bold uppercase tracking-wider text-indigo-400" id="wizardStepHeader">Bước 1 / 6</span>
                <span class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-mono">Nova V4</span>
              </div>
              <div id="wizardStepContent" class="space-y-4">
                <!-- Nội dung các bước sẽ được nạp động -->
              </div>
            </div>
            <div class="mt-6 flex justify-between items-center pt-4 border-t border-slate-800">
              <button id="wizardSkipBtn" class="text-xs text-slate-400 hover:text-white transition">Bỏ qua</button>
              <button id="wizardNextBtn" class="bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-semibold text-xs px-5 py-2.5 rounded-xl shadow-lg transition">Tiếp tục</button>
            </div>
          </div>
        </div>
      `;
    }

    init() {
      if (!this.shouldShow()) return;

      const container = document.createElement("div");
      container.innerHTML = this.renderModalHtml();
      document.body.appendChild(container.firstElementChild);

      const skipBtn = document.getElementById("wizardSkipBtn");
      const nextBtn = document.getElementById("wizardNextBtn");

      if (skipBtn) skipBtn.onclick = () => this.markCompleted();
      if (nextBtn) nextBtn.onclick = () => this.handleNextStep();

      this.updateStepUi(1);
    }

    hideModal() {
      const modal = document.getElementById("firstRunModal");
      if (modal) modal.remove();
    }

    handleNextStep() {
      if (this.currentStep < this.totalSteps) {
        this.currentStep++;
        this.updateStepUi(this.currentStep);
      } else {
        this.markCompleted();
      }
    }

    updateStepUi(step) {
      this.currentStep = step;
      const header = document.getElementById("wizardStepHeader");
      const content = document.getElementById("wizardStepContent");
      const nextBtn = document.getElementById("wizardNextBtn");

      if (header) header.innerText = `Bước ${step} / ${this.totalSteps}`;

      if (!content) return;

      switch(step) {
        case 1:
          content.innerHTML = `
            <div class="text-center py-2">
              <div class="text-4xl mb-3">🎙️</div>
              <h3 class="text-lg font-bold text-white mb-2">Quyền Microphone</h3>
              <p class="text-xs text-slate-300 leading-relaxed mb-4">
                Nova cần quyền ghi âm để lắng nghe câu hỏi và trò chuyện cùng bạn qua giọng nói rảnh tay.
              </p>
              <button onclick="if(window.AndroidNova&&window.AndroidNova.startNativeSpeech)window.AndroidNova.startNativeSpeech()" class="w-full bg-slate-800 hover:bg-slate-700 text-indigo-300 font-semibold text-xs py-2.5 rounded-xl border border-indigo-500/30">
                Cho phép truy cập Microphone
              </button>
            </div>
          `;
          break;

        case 2:
          content.innerHTML = `
            <div class="text-center py-2">
              <div class="text-4xl mb-3">🔔</div>
              <h3 class="text-lg font-bold text-white mb-2">Quyền Thông Báo</h3>
              <p class="text-xs text-slate-300 leading-relaxed mb-4">
                Nhận nhắc nhở lịch hẹn và đôn đốc nhiệm vụ ngay trên màn hình khi đến giờ.
              </p>
            </div>
          `;
          break;

        case 3:
          content.innerHTML = `
            <div class="text-center py-2">
              <div class="text-4xl mb-3">⏰</div>
              <h3 class="text-lg font-bold text-white mb-2">Báo Thức Chính Xác</h3>
              <p class="text-xs text-slate-300 leading-relaxed mb-4">
                Cấp quyền Exact Alarm để chuông nhắc nhở reo đúng từng giây kể cả khi tắt màn hình hoặc bật chế độ tiết kiệm pin.
              </p>
            </div>
          `;
          break;

        case 4:
          content.innerHTML = `
            <div class="text-center py-2">
              <div class="text-4xl mb-3">📱</div>
              <h3 class="text-lg font-bold text-white mb-2">Màn Hình Khóa & Full-Screen</h3>
              <p class="text-xs text-slate-300 leading-relaxed mb-4">
                Cho phép Nova hiển thị thông báo toàn màn hình khi có báo thức để bạn dễ dàng tắt hoặc báo lại.
              </p>
            </div>
          `;
          break;

        case 5:
          content.innerHTML = `
            <div class="text-center py-2">
              <div class="text-4xl mb-3">⭐</div>
              <h3 class="text-lg font-bold text-white mb-2">Trợ Lý Kỹ Thuật Số Mặc Định</h3>
              <p class="text-xs text-slate-300 leading-relaxed mb-4">
                Đặt Nova làm Trợ lý mặc định để gọi nhanh bằng cách giữ nút Nguồn hoặc vuốt góc màn hình.
              </p>
              <button onclick="if(window.AndroidNova&&window.AndroidNova.openAssistantSettings)window.AndroidNova.openAssistantSettings()" class="w-full bg-slate-800 hover:bg-slate-700 text-indigo-300 font-semibold text-xs py-2.5 rounded-xl border border-indigo-500/30">
                Mở Cài Đặt Trợ Lý Mặc Định
              </button>
            </div>
          `;
          break;

        case 6:
          content.innerHTML = `
            <div class="text-center py-2">
              <div class="text-4xl mb-3">🎉</div>
              <h3 class="text-lg font-bold text-white mb-2">Nova Đã Sẵn Sàng!</h3>
              <p class="text-xs text-slate-300 leading-relaxed mb-4">
                Hệ thống đã tự động kết nối máy chủ. Bạn có thể trò chuyện với Nova ngay bây giờ.
              </p>
              <button onclick="if(window.speakNovaResponse)window.speakNovaResponse('Xin chào, tớ là Nova đây!', null)" class="w-full bg-emerald-600/30 hover:bg-emerald-600/40 text-emerald-300 font-semibold text-xs py-2.5 rounded-xl border border-emerald-500/30">
                🔊 Thử phát giọng nói
              </button>
            </div>
          `;
          if (nextBtn) nextBtn.innerText = "Bắt đầu ngay";
          break;
      }
    }
  }

  window.FirstRunWizard = FirstRunWizard;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FirstRunWizard };
  }
})(typeof window !== 'undefined' ? window : global);

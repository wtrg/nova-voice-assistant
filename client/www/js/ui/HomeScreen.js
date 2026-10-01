/**
 * Nova Cyber Infinity Soul — Home Screen Controller
 * Section 24 & 25 of Nova Design System
 */
class HomeScreen {
  constructor(appShell) {
    this.appShell = appShell;
  }

  init() {
    // Setup quick action pills click listeners
    const quickPills = document.querySelectorAll(".quick-action-pill");
    quickPills.forEach((pill) => {
      pill.addEventListener("click", () => {
        const text = pill.getAttribute("data-prompt") || pill.querySelector(".quick-action-title")?.textContent;
        if (text && typeof window.sendUserUtterance === "function") {
          window.sendUserUtterance(text);
        }
      });
    });

    // Setup push to talk button
    const pttBtn = document.getElementById("btnPushToTalk");
    if (pttBtn) {
      const startPTT = (e) => {
        e.preventDefault();
        if (typeof window.startPushToTalk === "function") {
          window.startPushToTalk();
        }
      };
      const stopPTT = (e) => {
        e.preventDefault();
        if (typeof window.stopPushToTalk === "function") {
          window.stopPushToTalk();
        }
      };
      pttBtn.addEventListener("mousedown", startPTT);
      pttBtn.addEventListener("mouseup", stopPTT);
      pttBtn.addEventListener("touchstart", startPTT, { passive: false });
      pttBtn.addEventListener("touchend", stopPTT, { passive: false });
    }
  }
}

if (typeof window !== "undefined") {
  window.HomeScreen = HomeScreen;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = HomeScreen;
}

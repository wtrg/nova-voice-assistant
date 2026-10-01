/**
 * Nova Cyber Infinity Soul — App Shell Controller
 * Section 6, 23, 24, 26, 27, 28 of Nova Design System
 */
class AppShell {
  constructor() {
    this.currentScreen = "home"; // splash | home | chat | explore | profile
    this.screens = {};
    this.navItems = {};
  }

  init() {
    // Cache screen elements
    const screenIds = ["splash", "home", "chat", "explore", "profile"];
    screenIds.forEach((id) => {
      const el = document.getElementById(`screen-${id}`);
      if (el) this.screens[id] = el;
    });

    // Cache bottom nav items
    const navIds = ["home", "explore", "chat", "profile"];
    navIds.forEach((id) => {
      const el = document.getElementById(`nav-${id}`);
      if (el) {
        this.navItems[id] = el;
        el.addEventListener("click", () => this.navigateTo(id));
      }
    });

    // Check first-run splash status
    const hasSeenSplash = localStorage.getItem("nova_splash_seen");
    if (!hasSeenSplash && this.screens["splash"]) {
      this.showScreen("splash");
    } else {
      this.showScreen("home");
    }
  }

  dismissSplash() {
    localStorage.setItem("nova_splash_seen", "true");
    this.showScreen("home");
    if (window.novaScene) {
      window.novaScene.resize();
    }
  }

  navigateTo(screenId) {
    if (screenId === "splash") {
      this.showScreen("splash");
      return;
    }
    this.showScreen(screenId);
  }

  showScreen(screenId) {
    if (!this.screens[screenId]) return;

    Object.keys(this.screens).forEach((id) => {
      if (this.screens[id]) {
        this.screens[id].classList.remove("active");
      }
    });

    this.screens[screenId].classList.add("active");
    this.currentScreen = screenId;

    // Update bottom nav active state
    Object.keys(this.navItems).forEach((id) => {
      if (this.navItems[id]) {
        if (id === screenId) {
          this.navItems[id].classList.add("active");
        } else {
          this.navItems[id].classList.remove("active");
        }
      }
    });

    // Resize 3D scene when switching to home
    if (screenId === "home" && window.novaScene) {
      setTimeout(() => {
        window.novaScene.resize();
      }, 50);
    }

    // Scroll chat to bottom when switching to chat
    if (screenId === "chat") {
      const container = document.getElementById("chatMessages");
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }
  }
}

if (typeof window !== "undefined") {
  window.AppShell = AppShell;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = AppShell;
}

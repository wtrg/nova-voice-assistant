/**
 * Nova Cyber Infinity Soul — Explore Screen Controller
 * Section 27 of Nova Design System
 */
class ExploreScreen {
  constructor(appShell) {
    this.appShell = appShell;
    this.categories = [
      { id: "all", label: "Tất cả" },
      { id: "productivity", label: "Năng suất" },
      { id: "creative", label: "Sáng tạo" },
      { id: "learning", label: "Học tập" },
      { id: "life", label: "Cuộc sống" },
    ];
    this.tools = [
      {
        id: "knowledge",
        category: "productivity",
        icon: "🧠",
        title: "Trí thức",
        desc: "Hỏi đáp · Phân tích · Tổng hợp · Insight",
        prompt: "Hãy giúp mình phân tích và tổng hợp kiến thức về: ",
      },
      {
        id: "docs",
        category: "productivity",
        icon: "📄",
        title: "Phân tích tài liệu",
        desc: "Tóm tắt · Trích xuất · Hiểu nhanh chính xác",
        prompt: "Hãy tóm tắt và trích xuất các ý chính của tài liệu này: ",
      },
      {
        id: "image_gen",
        category: "creative",
        icon: "🖼️",
        title: "Tạo hình ảnh AI",
        desc: "Biến ý tưởng thành hình ảnh đỉnh cao",
        prompt: "Hãy mô tả chi tiết prompt để tạo hình ảnh AI cho: ",
      },
      {
        id: "video_gen",
        category: "creative",
        icon: "🎬",
        title: "Tạo video",
        desc: "Kịch bản · Hình ảnh · Video chuyên nghiệp",
        prompt: "Lên kịch bản video ngắn triệu view về chủ đề: ",
      },
      {
        id: "voice_audio",
        category: "creative",
        icon: "🎙️",
        title: "Giọng nói & Âm thanh",
        desc: "Chuyển văn bản · Lồng tiếng · Giọng Xuân Tiên AI",
        prompt: "Đọc diễn cảm đoạn văn sau bằng giọng Xuân Tiên: ",
      },
      {
        id: "coding",
        category: "productivity",
        icon: "💻",
        title: "Hỗ trợ lập trình",
        desc: "Viết code · Giải thích · Tối ưu · Debug",
        prompt: "Giúp mình viết và tối ưu hàm xử lý sau: ",
      },
      {
        id: "study",
        category: "learning",
        icon: "🎓",
        title: "Học tập",
        desc: "Giải thích · Tóm tắt · Lộ trình cá nhân hóa",
        prompt: "Lập lộ trình học tập hiệu quả trong 30 ngày cho: ",
      },
      {
        id: "life_habits",
        category: "life",
        icon: "❤️",
        title: "Cuộc sống",
        desc: "Sức khỏe · Thói quen · Cân bằng cuộc sống",
        prompt: "Đưa ra 3 thói quen lành mạnh mỗi ngày để: ",
      },
    ];
    this.currentCategory = "all";
  }

  init() {
    this.renderCategories();
    this.renderTools();
  }

  renderCategories() {
    const container = document.getElementById("exploreCategories");
    if (!container) return;

    container.innerHTML = this.categories
      .map(
        (c) => `
        <button class="explore-pill ${c.id === this.currentCategory ? "active" : ""}"
                onclick="window.exploreScreenInstance.selectCategory('${c.id}')">
          ${c.label}
        </button>
      `
      )
      .join("");
  }

  selectCategory(catId) {
    this.currentCategory = catId;
    this.renderCategories();
    this.renderTools();
  }

  renderTools() {
    const container = document.getElementById("exploreToolsGrid");
    if (!container) return;

    const filtered =
      this.currentCategory === "all"
        ? this.tools
        : this.tools.filter((t) => t.category === this.currentCategory);

    container.innerHTML = filtered
      .map(
        (t) => `
        <div class="explore-card" onclick="window.exploreScreenInstance.onToolClick('${t.id}')">
          <div class="explore-card-icon">${t.icon}</div>
          <div class="explore-card-title">${t.title}</div>
          <div class="explore-card-desc">${t.desc}</div>
        </div>
      `
      )
      .join("");
  }

  onToolClick(toolId) {
    const tool = this.tools.find((t) => t.id === toolId);
    if (!tool) return;

    // Switch to Chat screen and prefill input
    if (window.appShellInstance) {
      window.appShellInstance.navigateTo("chat");
    }
    const input = document.getElementById("chatInput");
    if (input) {
      input.value = tool.prompt;
      input.focus();
    }
  }
}

if (typeof window !== "undefined") {
  window.ExploreScreen = ExploreScreen;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = ExploreScreen;
}

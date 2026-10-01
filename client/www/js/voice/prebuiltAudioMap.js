/**
 * PREBUILT AUDIO MAP & PARITY RESOLVER
 * 
 * P0 FIX: Tuyệt đối không match bằng substring .includes(...) trên câu trả lời AI động!
 * Mọi câu trả lời AI (isAiResponse = true / mode = 'dynamic') phải được đọc chính xác 100%
 * bằng TTS động (Dynamic VieNeu TTS / Native TTS) để đảm bảo text và audio đồng nhất hoàn toàn.
 */

const PREBUILT_AUDIO_MAP = {
  assistant_hello: "assets/cuppy_hello.wav",
  assistant_welcome: "assets/cuppy_welcome.wav",
  assistant_goodbye: "assets/cuppy_goodbye.wav",
  assistant_lets_chat: "assets/cuppy_lets_chat.wav",
  assistant_ok: "assets/cuppy_ok.wav",
  app_open_youtube: "assets/cuppy_open_youtube.wav",
  app_open_maps: "assets/cuppy_open_maps.wav",
  app_open_camera: "assets/cuppy_open_camera.wav",
  app_open_zalo: "assets/cuppy_open_zalo.wav",
  app_open_facebook: "assets/cuppy_open_facebook.wav",
  app_open_tiktok: "assets/cuppy_open_tiktok.wav",
  app_open_general: "assets/cuppy_open_general.wav",
  app_not_found: "assets/cuppy_app_not_found.wav",
  alarm_ring: "assets/cuppy_alarm.wav",
  network_error: "assets/cuppy_network_error.wav"
};

// Ánh xạ câu lệnh hệ thống tĩnh chính xác 100% (exact match, không dùng includes substring)
const EXACT_SYSTEM_PHRASES = {
  "đang mở youtube": "app_open_youtube",
  "đang mở zalo": "app_open_zalo",
  "đang mở facebook": "app_open_facebook",
  "đang mở tiktok": "app_open_tiktok",
  "đang mở camera": "app_open_camera",
  "đang mở google maps": "app_open_maps",
  "đang mở bản đồ": "app_open_maps",
  "chưa tìm thấy ứng dụng": "app_not_found",
  "tắt mic đây, khi nào cần cứ gọi hey nova nhé": "assistant_goodbye",
  "buôn chuyện tí nào! cậu đang cảm thấy thế nào rồi?": "assistant_lets_chat",
  "tớ là nova đây, tớ đang lắng nghe": "assistant_hello",
  "mạng hơi chập chờn khi kết nối giọng nói": "network_error"
};

/**
 * Phân giải đường dẫn âm thanh với cam kết Audio-Text Parity
 * @param {Object} opts
 * @param {string} opts.text - Nội dung văn bản
 * @param {boolean} opts.isAiResponse - Có phải câu trả lời AI động hay không
 * @param {string} opts.speechKey - Khóa âm thanh định trước (nếu có)
 * @param {string} opts.mode - 'dynamic' | 'prebuilt'
 * @returns {{ mode: 'dynamic'|'prebuilt', path: string|null }}
 */
function resolveVoicePlayback(opts = {}) {
  const isAi = Boolean(opts.isAiResponse || opts.mode === 'dynamic');
  
  // 1. Nếu là câu thoại AI động: BẮT BUỘC 100% DÙNG DYNAMIC TTS!
  // Tuyệt đối không bao giờ match đè bằng file WAV cố định!
  if (isAi) {
    return { mode: 'dynamic', path: null };
  }

  // 2. Nếu có speechKey chỉ định rõ ràng:
  if (opts.speechKey && PREBUILT_AUDIO_MAP[opts.speechKey]) {
    return { mode: 'prebuilt', path: PREBUILT_AUDIO_MAP[opts.speechKey] };
  }

  // 3. Nếu là lệnh hệ thống tĩnh: Chỉ match khi câu hoàn toàn trùng khớp (exact match)
  if (opts.text) {
    const clean = opts.text.toLowerCase().replace(/[*#_`~]/g, "").replace(/\s+/g, " ").trim();
    const mappedKey = EXACT_SYSTEM_PHRASES[clean];
    if (mappedKey && PREBUILT_AUDIO_MAP[mappedKey]) {
      return { mode: 'prebuilt', path: PREBUILT_AUDIO_MAP[mappedKey] };
    }
  }

  // Mặc định an toàn: TTS động
  return { mode: 'dynamic', path: null };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    PREBUILT_AUDIO_MAP,
    EXACT_SYSTEM_PHRASES,
    resolveVoicePlayback
  };
}

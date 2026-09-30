const assert = require('assert');
const { resolveVoicePlayback, PREBUILT_AUDIO_MAP } = require('../www/js/voice/prebuiltAudioMap');

console.log("Running test_voice_mapping.js...");

// Test Case 1: Dynamic AI response containing triggers MUST NOT map to fixed WAV
const dynamicReplies = [
  "Ê cậu ơi! Đến giờ làm Học Toán rồi kìa, vào bàn làm ngay thôi nào!",
  "Cậu có muốn tớ mở youtube bài hát Em Của Ngày Hôm Qua không?",
  "Hôm nay mạng hơi chập chờn một chút nhưng tớ vẫn nghe được cậu nói.",
  "Để tớ ghi nhớ lịch hẹn họp nhóm lúc 15h30 nhé.",
  "Chào cậu! Hôm nay cậu thấy thế nào, tớ là Nova đây, tớ đang lắng nghe tâm sự của cậu."
];

for (const reply of dynamicReplies) {
  const result = resolveVoicePlayback({
    text: reply,
    isAiResponse: true,
    mode: "dynamic"
  });
  assert.strictEqual(
    result.mode, 
    "dynamic", 
    `FAIL: Dynamic reply matched fixed audio! Text: "${reply}"`
  );
  assert.strictEqual(
    result.path, 
    null, 
    `FAIL: Dynamic reply returned non-null path! Text: "${reply}"`
  );
}
console.log("✓ Dynamic AI responses (100% parity) pass: 0 mismatch with prebuilt WAV");

// Test Case 2: Explicit speechKey maps to correct audio asset
assert.strictEqual(
  resolveVoicePlayback({ speechKey: "app_open_youtube" }).path,
  "assets/cuppy_open_youtube.wav"
);
assert.strictEqual(
  resolveVoicePlayback({ speechKey: "assistant_hello" }).path,
  "assets/cuppy_hello.wav"
);
assert.strictEqual(
  resolveVoicePlayback({ speechKey: "alarm_ring" }).path,
  "assets/cuppy_alarm.wav"
);
console.log("✓ Explicit speechKeys pass");

// Test Case 3: Exact static system command matches
const exactResult = resolveVoicePlayback({
  text: "đang mở youtube",
  isAiResponse: false
});
assert.strictEqual(exactResult.mode, "prebuilt");
assert.strictEqual(exactResult.path, "assets/cuppy_open_youtube.wav");
console.log("✓ Exact system commands pass");

console.log("ALL VOICE MAPPING TESTS PASSED PERFECTLY!");

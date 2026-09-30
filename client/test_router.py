import re, sys

def matchAppCommand(text):
    if not text:
        return None
    clean = text.lower().strip()
    clean = re.sub(r'[\?\,\.\!\;]', '', clean).strip()

    # Normalization
    clean = re.sub(r'\b(you\s*tube|u\s*tube|utube)\b', 'youtube', clean)
    clean = re.sub(r'\b(tóp\s*tóp|top\s*top)\b', 'tiktok', clean)
    clean = re.sub(r'\b(fb)\b', 'facebook', clean)
    clean = re.sub(r'\b(máy\s*ảnh)\b', 'camera', clean)

    # 1. Chỉ đường / Bản đồ: Phải bắt đầu bằng động từ dẫn đường hoặc mở bản đồ
    m_maps = re.match(r'^(?:chỉ đường|dẫn đường)\s*(?:đến|về|tới|qua)?\s*(.+)$', clean)
    if m_maps:
        dest = m_maps.group(1).strip()
        dest = re.sub(r'(?:giúp tớ|giúp tôi|hộ tớ|hộ tôi|nhé|nha|với|đi)$', '', dest).strip()
        return {'appName': 'maps', 'query': dest, 'displayName': 'Bản đồ'}

    m_maps_open = re.match(r'^(?:mở|bật|vào|hãy mở|hãy bật)\s+(?:ứng\s*dụng\s+|app\s+)?(?:bản\s*đồ|google\s*maps|maps?)(?:\s+(?:đến|về|tới|tìm)?\s*(.+))?$', clean)
    if m_maps_open:
        dest = (m_maps_open.group(1) or '').strip()
        dest = re.sub(r'(?:giúp tớ|giúp tôi|hộ tớ|hộ tôi|nhé|nha|với|đi)$', '', dest).strip()
        return {'appName': 'maps', 'query': dest, 'displayName': 'Bản đồ'}

    # 2. Camera / Chụp ảnh: Lệnh chụp ảnh hoặc mở camera
    if re.match(r'^(?:chụp ảnh|chụp hình|chụp một tấm hình|tự sướng)$', clean):
        return {'appName': 'camera', 'query': '', 'displayName': 'Camera'}
    if re.match(r'^(?:mở|bật|vào|hãy mở|hãy bật)\s+(?:ứng\s*dụng\s+|app\s+)?camera$', clean):
        return {'appName': 'camera', 'query': '', 'displayName': 'Camera'}

    # 3. YouTube / Nghe nhạc: Phải bắt đầu bằng lệnh nghe/bật/mở
    m_yt = re.match(r'^(?:mở|bật|vào|hãy mở|hãy bật)\s+(?:ứng\s*dụng\s+|app\s+)?youtube(?:\s+(?:bài\s*hát|video|bài|nhạc)?\s*(.+))?$', clean)
    if m_yt:
        q = (m_yt.group(1) or '').strip()
        q = re.sub(r'(?:giúp tớ|giúp tôi|hộ tớ|hộ tôi|nhé|nha|với|đi)$', '', q).strip()
        return {'appName': 'youtube', 'query': q, 'displayName': 'YouTube'}

    m_music = re.match(r'^(?:nghe|bật|mở|phát)\s+(?:nhạc|bài\s*hát|bài|ca\s*khúc)(?:\s+(.+))?$', clean)
    if m_music:
        q = (m_music.group(1) or '').strip()
        q = re.sub(r'(?:giúp tớ|giúp tôi|hộ tớ|hộ tôi|nhé|nha|với|đi)$', '', q).strip()
        return {'appName': 'youtube', 'query': q, 'displayName': 'YouTube'}

    # 4. Zalo
    if re.match(r'^(?:mở|bật|vào|hãy mở|hãy bật)\s+(?:ứng\s*dụng\s+|app\s+)?zalo$', clean):
        return {'appName': 'zalo', 'query': '', 'displayName': 'Zalo'}

    # 5. Facebook
    if re.match(r'^(?:mở|bật|vào|hãy mở|hãy bật)\s+(?:ứng\s*dụng\s+|app\s+)?facebook$', clean):
        return {'appName': 'facebook', 'query': '', 'displayName': 'Facebook'}

    # 6. TikTok
    if re.match(r'^(?:mở|bật|vào|hãy mở|hãy bật)\s+(?:ứng\s*dụng\s+|app\s+)?tiktok$', clean):
        return {'appName': 'tiktok', 'query': '', 'displayName': 'TikTok'}

    # 7. Messenger
    if re.match(r'^(?:mở|bật|vào|hãy mở|hãy bật)\s+(?:ứng\s*dụng\s+|app\s+)?(?:messenger|tin nhắn|nhắn tin)$', clean):
        return {'appName': 'messenger', 'query': '', 'displayName': 'Messenger'}

    # 8. Chrome / Trình duyệt
    if re.match(r'^(?:mở|bật|vào|hãy mở|hãy bật)\s+(?:ứng\s*dụng\s+|app\s+)?(?:chrome|trình duyệt|web)$', clean):
        return {'appName': 'chrome', 'query': '', 'displayName': 'Chrome'}

    # 9. Cài đặt hệ thống
    if re.match(r'^(?:mở|bật|vào|hãy mở|hãy bật)\s+(?:ứng\s*dụng\s+|app\s+)?(?:cài đặt|settings)$', clean):
        return {'appName': 'cài đặt', 'query': '', 'displayName': 'Cài đặt'}

    # 10. Báo thức / Đồng hồ
    if re.match(r'^(?:mở|bật|vào|hãy mở|hãy bật)\s+(?:ứng\s*dụng\s+|app\s+)?(?:báo thức|đồng hồ|clock|alarm)$', clean):
        return {'appName': 'báo thức', 'query': '', 'displayName': 'Đồng hồ báo thức'}

    # 11. Generic mở app khác: "mở app [tên]"
    genMatch = re.match(r'^(?:mở|bật|vào|hãy mở|hãy bật)\s+(?:ứng\s*dụng|app)\s+([a-z0-9\s]+)$', clean)
    if genMatch:
        app = genMatch.group(1).strip()
        ignoreList = ["lịch", "nhắc", "nói", "buôn", "chuyện", "bài", "thử", "mic", "gì", "sao", "thế"]
        if not any(w in app for w in ignoreList) and len(app) >= 2:
            return {'appName': app, 'query': '', 'displayName': app}

    return None

test_cases = [
    # Must match app commands
    ("mở youtube", "youtube"),
    ("mở youtube bài hát em của ngày hôm qua", "youtube"),
    ("nghe nhạc sơn tùng", "youtube"),
    ("bật bài cắt đôi nỗi sầu", "youtube"),
    ("chỉ đường đến hồ gươm", "maps"),
    ("dẫn đường về nhà", "maps"),
    ("mở bản đồ", "maps"),
    ("chụp ảnh", "camera"),
    ("chụp hình", "camera"),
    ("mở camera", "camera"),
    ("mở zalo", "zalo"),
    ("mở facebook", "facebook"),
    ("mở tiktok", "tiktok"),
    ("mở messenger", "messenger"),
    ("mở cài đặt", "cài đặt"),
    ("mở báo thức", "báo thức"),

    # MUST NOT MATCH (Conversational questions)
    ("cậu có thích nghe nhạc không?", None),
    ("bài hát này của ai sáng tác?", None),
    ("facebook do ai sáng lập?", None),
    ("bản đồ việt nam có bao nhiêu tỉnh?", None),
    ("camera hoạt động thế nào?", None),
    ("làm thế nào để dừng xe an toàn khi trời mưa?", None),
    ("hôm nay trời có mưa không?", None),
    ("tớ muốn hỏi bạn một câu", None),
    ("trình duyệt web nào tốt nhất?", None),
    ("đồng hồ sinh học là gì?", None),
]

all_passed = True
for inp, expected in test_cases:
    res = matchAppCommand(inp)
    actual = res['appName'] if res else None
    msg = f"PASSED: '{inp}' -> {actual}\n" if actual == expected else f"FAILED: '{inp}' -> Got {actual}, Expected {expected}\n"
    sys.stdout.buffer.write(msg.encode('utf-8'))
    if actual != expected:
        all_passed = False

if all_passed:
    sys.stdout.buffer.write(b"\nALL 26 TEST CASES PASSED PERFECTLY!\n")
    sys.exit(0)
else:
    sys.stdout.buffer.write(b"\nSOME TEST CASES FAILED!\n")
    sys.exit(1)

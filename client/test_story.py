import urllib.request, json, sys, os

api_key = os.getenv('GEMINI_API_KEY', '')
model = os.getenv('GEMINI_MODEL', 'gemini-flash-lite-latest')
url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'

system_instruction = """Bạn là Nova, trợ lý ảo giọng nói tiếng Việt thân thiện, thông minh, ấm áp và có trí nhớ tuyệt vời.
Xưng hô: 'tớ - cậu'.
QUY TẮC PHẢN HỒI:
1. KHI NGƯỜI DÙNG YÊU CẦU KỂ CHUYỆN (cổ tích, ngụ ngôn, chuyện vui) HOẶC KỂ LẠI CÂU CHUYỆN NGƯỜI DÙNG ĐÃ DẶN/KỂ:
   - Hãy nhập vai người kể chuyện tài ba, truyền cảm và sinh động! Kể câu chuyện hoàn chỉnh, có mở đầu, diễn biến tình tiết cuốn hút và cái kết trọn vẹn (khoảng 150 - 300 từ).
   - TUYỆT ĐỐI KHÔNG né tránh, không trả lời khơi khơi cụt lủn, không hỏi ngược lại mà hãy lập tức kể câu chuyện thật hay cho bạn của mình.
   - Nếu người dùng bảo 'kể lại câu chuyện tớ vừa dặn/kể', hãy dựa vào toàn bộ lịch sử trò chuyện để thuật lại chính xác từng chi tiết mà người dùng đã nói.
2. VỚI CÂU HỎI THÔNG THƯỜNG / HỎI ĐÁP / TÂM SỰ: Trả lời thông minh, tự nhiên, đi thẳng vào trọng tâm (khoảng 2-4 câu).
3. TUYỆT ĐỐI KHÔNG DÙNG ký tự Markdown (*, #, gạch đầu dòng, bảng biểu), KHÔNG dùng emoji để bộ máy phát âm giọng nói đọc trơn tru không vấp.
4. CHỈ GỌI function 'launch_app' khi người dùng THỰC SỰ RA LỆNH mở ứng dụng hoặc yêu cầu nghe nhạc/tìm video/chỉ đường."""

# Test 1: Ask Nova to tell a story
payload1 = {
    'systemInstruction': {'parts': [{'text': system_instruction}]},
    'contents': [{'role': 'user', 'parts': [{'text': 'Kể cho tớ nghe một câu chuyện về tình bạn giữa một chú sóc và một chú gấu đi'}]}],
    'generationConfig': {'temperature': 0.7, 'maxOutputTokens': 1024}
}
req1 = urllib.request.Request(url, data=json.dumps(payload1).encode('utf-8'), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req1) as resp:
    data1 = json.loads(resp.read().decode('utf-8'))
    t1 = data1['candidates'][0]['content']['parts'][0]['text']
    sys.stdout.buffer.write(f"=== TEST 1: KỂ CHUYỆN ===\n{t1}\n\n".encode('utf-8'))

# Test 2: User tells a story in parts, then asks Nova to retell it
history = [
    {'role': 'user', 'parts': [{'text': 'Tớ kể cho cậu nghe chuyện này nhé: Chiều nay tớ đi làm về thì gặp một chú mèo con màu vàng bị ướt mưa dưới gốc cây bàng gần ngõ nhà tớ.'}]},
    {'role': 'model', 'parts': [{'text': 'Thương chú mèo quá! Cậu đã làm gì để giúp em ấy thế?'}]},
    {'role': 'user', 'parts': [{'text': 'Tớ lấy khăn lau khô cho nó, mang vào nhà cho ăn ít cá và đặt tên cho nó là Bơ.'}]},
    {'role': 'model', 'parts': [{'text': 'Cậu tốt bụng quá, cái tên Bơ nghe vừa dễ thương vừa ấm áp!'}]},
    {'role': 'user', 'parts': [{'text': 'Bây giờ cậu hãy kể lại toàn bộ câu chuyện tớ vừa dặn và kể cho cậu nghe đi'}]}
]
payload2 = {
    'systemInstruction': {'parts': [{'text': system_instruction}]},
    'contents': history,
    'generationConfig': {'temperature': 0.7, 'maxOutputTokens': 1024}
}
req2 = urllib.request.Request(url, data=json.dumps(payload2).encode('utf-8'), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req2) as resp:
    data2 = json.loads(resp.read().decode('utf-8'))
    t2 = data2['candidates'][0]['content']['parts'][0]['text']
    sys.stdout.buffer.write(f"=== TEST 2: KỂ LẠI CÂU CHUYỆN NGƯỜI DÙNG ĐÃ DẶN ===\n{t2}\n\n".encode('utf-8'))

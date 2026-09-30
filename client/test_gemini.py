import urllib.request, json, sys, os

api_key = os.getenv('GEMINI_API_KEY', '')
model = os.getenv('GEMINI_MODEL', 'gemini-flash-lite-latest')
url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'

questions = [
    'Hôm nay trời có mưa không?',
    'Cậu có thích nghe nhạc không?',
    'Facebook là gì?',
    'Việt Nam có bao nhiêu tỉnh thành?',
    'Làm thế nào để dừng xe an toàn khi trời mưa?'
]

for q in questions:
    payload = {
        'systemInstruction': {
            'parts': [{'text': """Bạn là Nova, trợ lý ảo giọng nói tiếng Việt thân thiện, thông minh, ấm áp và tinh tế.
Quy tắc:
- Trả lời tự nhiên, thông minh, đúng trọng tâm, ngắn gọn vừa phải (khoảng 1-3 câu, tối đa 50-60 từ) để đọc bằng giọng nói nghe tự nhiên và dễ chịu nhất.
- Luôn trả lời thẳng vào câu hỏi của người dùng, không né tránh, không lạc đề.
- Giọng điệu ấm áp, thân thiện, xưng 'tớ - cậu'.
- KHÔNG dùng markdown (*, #, gạch đầu dòng, bảng biểu), KHÔNG dùng emoji.
- Đối với câu hỏi kiến thức, trò chuyện, tâm sự: Hãy giải đáp thông minh, súc tích. Tuyệt đối KHÔNG gọi function launch_app nếu người dùng chỉ hỏi kiến thức/hỏi thăm (ví dụ: 'Facebook là gì', 'Bạn có thích nghe nhạc không').
- CHỈ gọi function launch_app khi người dùng THỰC SỰ RA LỆNH thực hiện hành động (ví dụ: 'mở youtube', 'bật nhạc cho tớ', 'chỉ đường đến...')."""}]
        },
        'contents': [{'role': 'user', 'parts': [{'text': q}]}],
        'generationConfig': {
            'temperature': 0.6,
            'maxOutputTokens': 200
        }
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        text = data['candidates'][0]['content']['parts'][0]['text']
        sys.stdout.buffer.write(f"Q: {q}\nA: {text}\n---\n".encode('utf-8'))

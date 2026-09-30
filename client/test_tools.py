import urllib.request, json, sys, os

api_key = os.getenv('GEMINI_API_KEY', '')
model = os.getenv('GEMINI_MODEL', 'gemini-flash-lite-latest')
url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'

tools = [{
    'function_declarations': [
        {
            'name': 'schedule_tasks',
            'description': 'Lên lịch các nhiệm vụ nhắc nhở cho người dùng khi người dùng yêu cầu hoặc đã chốt lịch trình',
            'parameters': {
                'type': 'OBJECT',
                'properties': {
                    'tasks': {
                        'type': 'ARRAY',
                        'description': 'Danh sách công việc cần lên lịch',
                        'items': {
                            'type': 'OBJECT',
                            'properties': {
                                'title': {'type': 'STRING', 'description': 'Tên công việc'},
                                'scheduled_time': {'type': 'STRING', 'description': 'Giờ hẹn'}
                            },
                            'required': ['title', 'scheduled_time']
                        }
                    }
                },
                'required': ['tasks']
            }
        },
        {
            'name': 'launch_app',
            'description': 'Mở ứng dụng hoặc tìm kiếm sâu nội dung trong ứng dụng trên điện thoại (vd: mở bài hát hoặc video trên YouTube, mở Google Maps chỉ đường, mở Camera, Zalo, Facebook, TikTok, v.v.)',
            'parameters': {
                'type': 'OBJECT',
                'properties': {
                    'app_name': {
                        'type': 'STRING',
                        'description': 'Tên ứng dụng cần mở'
                    },
                    'query': {
                        'type': 'STRING',
                        'description': 'Nội dung tìm kiếm cụ thể'
                    }
                },
                'required': ['app_name']
            }
        }
    ]
}]

test_inputs = [
    'Mở YouTube bài hát Cắt đôi nỗi sầu',
    'Nhắc tớ 14h chiều nay học bài',
    'Facebook là gì?',
    'Bạn thích nghe nhạc không?'
]

for inp in test_inputs:
    payload = {
        'systemInstruction': {
            'parts': [{'text': """Bạn là Nova, trợ lý ảo giọng nói tiếng Việt thân thiện, thông minh, ấm áp và tinh tế.
Quy tắc phản hồi:
- Trả lời tự nhiên, thông minh, đúng trọng tâm, ngắn gọn vừa phải (khoảng 1-3 câu, tối đa 50-60 từ) để đọc bằng giọng nói nghe tự nhiên và dễ chịu nhất.
- Luôn trả lời thẳng vào câu hỏi của người dùng, không né tránh, không lạc đề.
- Giọng điệu ấm áp, thân thiện, xưng 'tớ - cậu'.
- KHÔNG dùng markdown (*, #, gạch đầu dòng, bảng biểu), KHÔNG dùng emoji.
- Đối với câu hỏi kiến thức, trò chuyện, tâm sự: Hãy giải đáp thông minh, súc tích. Tuyệt đối KHÔNG gọi function launch_app nếu người dùng chỉ hỏi kiến thức/hỏi thăm (ví dụ: 'Facebook là gì', 'Bạn có thích nghe nhạc không').
- CHỈ gọi function launch_app khi người dùng THỰC SỰ RA LỆNH mở ứng dụng hoặc nghe nhạc, chỉ đường (ví dụ: 'mở youtube', 'bật nhạc cho tớ', 'chỉ đường đến...').
- CHỈ gọi function schedule_tasks khi người dùng yêu cầu hẹn giờ hoặc lên lịch."""}]
        },
        'contents': [{'role': 'user', 'parts': [{'text': inp}]}],
        'tools': tools,
        'generationConfig': {
            'temperature': 0.6,
            'maxOutputTokens': 200
        }
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        part = data['candidates'][0]['content']['parts'][0]
        if 'functionCall' in part:
            fc = part['functionCall']
            name = fc['name']
            args = fc.get('args', {})
            sys.stdout.buffer.write(f"INP: {inp}\n-> FUNCTION CALL: {name} args={args}\n---\n".encode('utf-8'))
        else:
            text = part.get('text', '')
            sys.stdout.buffer.write(f"INP: {inp}\n-> TEXT: {text}\n---\n".encode('utf-8'))

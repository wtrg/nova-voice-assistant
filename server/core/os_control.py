import os
import subprocess
import webbrowser
import logging
from typing import Dict, Tuple

logger = logging.getLogger("OSControl")

# Bảng ánh xạ các từ khóa tiếng Việt / tiếng Anh sang ứng dụng thực tế trên Windows
WINDOWS_APPS = {
    # Lập trình & Công việc
    "code": "code",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "notepad": "notepad.exe",
    "ghi chú": "notepad.exe",
    "cmd": "cmd.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "quản lý file": "explorer.exe",
    
    # Trình duyệt web
    "chrome": "chrome",
    "google chrome": "chrome",
    "trình duyệt": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "cốc cốc": "coccoc",
    
    # Văn phòng
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "calculator": "calc.exe",
    "máy tính": "calc.exe",
    
    # Giải trí & Ghi chú
    "spotify": "spotify",
    "nhạc": "spotify",
    "notion": "notion",
    "zalo": "zalo",
    "telegram": "telegram"
}

# Các đường dẫn URL phím tắt thông dụng
WEB_SHORTCUTS = {
    "youtube": "https://www.youtube.com",
    "facebook": "https://www.facebook.com",
    "chatgpt": "https://chatgpt.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com"
}

def open_application(app_query: str) -> Tuple[bool, str]:
    """
    Tìm và khởi chạy ứng dụng hoặc trang web trên Windows dựa theo giọng nói của người dùng.
    """
    clean_query = app_query.lower().strip()
    
    # 1. Kiểm tra mở trang web nhanh
    for site_key, url in WEB_SHORTCUTS.items():
        if site_key in clean_query:
            try:
                webbrowser.open(url)
                return True, f"Đã mở trang {site_key.title()} trên trình duyệt cho bạn."
            except Exception as e:
                return False, f"Lỗi khi mở website {site_key}: {e}"
    
    # 2. Kiểm tra bảng ánh xạ ứng dụng cài đặt
    target_cmd = None
    matched_name = clean_query
    for key, cmd in WINDOWS_APPS.items():
        if key in clean_query:
            target_cmd = cmd
            matched_name = key
            break
            
    if not target_cmd:
        # F-04: Loại bỏ hoàn toàn shell=True và command execution tùy ý
        return False, f"Ứng dụng '{clean_query}' không nằm trong danh sách an toàn được phép mở."
    
    # Thực hiện lệnh khởi chạy an toàn trên Windows bằng os.startfile (không chạy shell)
    try:
        os.startfile(target_cmd)
        return True, f"Đã mở ứng dụng {matched_name}."
    except Exception as err:
        logger.error(f"Không thể mở ứng dụng '{matched_name}': {err}")
        return False, f"Không tìm thấy ứng dụng {matched_name} trên máy tính của bạn."

import sys

if __name__ == "__main__":
    # Đảm bảo in tiếng Việt trên console Windows không bị lỗi font/codec
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    success, msg = open_application("notepad")
    print(msg)


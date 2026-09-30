import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.agent import parse_time_str, assistant_agent
from core.database import get_all_active_tasks

def test_parse_time_str_valid_formats():
    t1 = parse_time_str("10 phút")
    assert t1 != ""
    assert datetime.strptime(t1, "%Y-%m-%d %H:%M")

    t2 = parse_time_str("+15m")
    assert t2 != ""
    assert datetime.strptime(t2, "%Y-%m-%d %H:%M")

    t3 = parse_time_str("14h30")
    assert t3 != ""
    assert datetime.strptime(t3, "%Y-%m-%d %H:%M")
    assert t3.endswith("14:30")

    t4 = parse_time_str("lát nữa")
    assert t4 != ""
    assert datetime.strptime(t4, "%Y-%m-%d %H:%M")

def test_parse_time_str_invalid_returns_empty():
    assert parse_time_str("") == ""
    assert parse_time_str("    ") == ""
    assert parse_time_str("không biết bao giờ") == ""
    assert parse_time_str("ngày mai") == "" # Không có giờ cụ thể
    assert parse_time_str("random text 123") == ""

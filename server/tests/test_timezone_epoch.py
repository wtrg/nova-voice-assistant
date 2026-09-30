import pytest
from datetime import datetime, timezone, timedelta
from core.agent import parse_time_str, VN_TZ

def test_timezone_epoch_conversion_utc_runner_invariant():
    """
    Kỳ vọng: Chuỗi '2026-10-01 20:00' theo giờ Việt Nam (UTC+7)
    phải tạo ra epoch timestamp khớp chuẩn xác 100% dù test chạy trên UTC runner.
    20:00 UTC+7 tương đương 13:00 UTC.
    """
    formatted_time = "2026-10-01 20:00"
    dt = datetime.strptime(formatted_time, "%Y-%m-%d %H:%M")
    dt = dt.replace(tzinfo=VN_TZ)
    epoch_ms = int(dt.timestamp() * 1000)

    # Khôi phục lại từ epoch với timezone UTC
    dt_utc = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
    assert dt_utc.year == 2026
    assert dt_utc.month == 10
    assert dt_utc.day == 1
    assert dt_utc.hour == 13
    assert dt_utc.minute == 0

    # Khôi phục lại với timezone VN_TZ
    dt_vn = datetime.fromtimestamp(epoch_ms / 1000, tz=VN_TZ)
    assert dt_vn.hour == 20
    assert dt_vn.minute == 0

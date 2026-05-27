from datetime import datetime
import pytz
from core.timezone_utils import utc_to_local


def test_utc_to_local_standard():
    dt_str = "2026-05-28T12:00:00Z"
    res = utc_to_local(dt_str, "Asia/Kolkata")
    
    assert res.hour == 17
    assert res.minute == 30
    assert res.tzinfo.zone == "Asia/Kolkata"


def test_utc_to_local_resilient_fallback():
    # ISO strings with different separators/formats
    dt_str_custom = "2026-05-28T12:00:00.123456"
    res = utc_to_local(dt_str_custom, "Asia/Kolkata")
    
    assert res.year == 2026
    assert res.month == 5
    assert res.day == 28

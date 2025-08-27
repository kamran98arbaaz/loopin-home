"""
Essential timezone utilities for LoopIn
"""
import pytz
from datetime import datetime, timezone

# Standard timezones
UTC = pytz.UTC
IST = pytz.timezone("Asia/Kolkata")

def now_utc():
    """Get current datetime in UTC"""
    return datetime.now(UTC)

def now_ist():
    """Get current datetime in IST"""
    return datetime.now(IST)

def to_utc(dt):
    """Convert datetime to UTC"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)

def to_ist(dt):
    """Convert datetime to IST"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)

def format_ist(dt, format_str='%Y-%m-%d %H:%M'):
    """Format datetime in IST"""
    if dt is None:
        return 'N/A'
    ist_dt = to_ist(dt)
    return ist_dt.strftime(format_str)

def ensure_timezone(dt, default_tz=UTC):
    """Ensure datetime has timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=default_tz)
    return dt

def is_within_hours(dt, hours=24, reference_time=None):
    """Check if datetime is within specified hours"""
    if dt is None:
        return False
    if reference_time is None:
        reference_time = now_utc()
    dt_utc = to_utc(dt)
    ref_utc = to_utc(reference_time)
    time_diff = ref_utc - dt_utc
    return time_diff.total_seconds() <= (hours * 3600)

def get_hours_ago(hours):
    """Get datetime that is specified hours ago"""
    from datetime import timedelta
    return now_utc() - timedelta(hours=hours)

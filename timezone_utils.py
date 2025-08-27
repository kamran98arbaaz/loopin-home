# timezone_utils.py
"""
Centralized timezone utilities for consistent time handling across the application.

This module provides standardized timezone functions to ensure all datetime operations
use UTC for storage and IST for display, maintaining consistency across the application.
"""

import pytz
from datetime import datetime, timezone

# Standard timezones used throughout the application
UTC = pytz.UTC
IST = pytz.timezone("Asia/Kolkata")

def now_utc():
    """
    Get current datetime in UTC.
    
    Returns:
        datetime: Current datetime with UTC timezone
    """
    return datetime.now(UTC)

def now_ist():
    """
    Get current datetime in IST.
    
    Returns:
        datetime: Current datetime with IST timezone
    """
    return datetime.now(IST)

def to_utc(dt):
    """
    Convert datetime to UTC timezone.
    
    Args:
        dt (datetime): Datetime object (can be naive or timezone-aware)
        
    Returns:
        datetime: Datetime converted to UTC
    """
    if dt is None:
        return None
        
    if dt.tzinfo is None:
        # Assume naive datetime is already in UTC
        return dt.replace(tzinfo=UTC)
    
    return dt.astimezone(UTC)

def to_ist(dt):
    """
    Convert datetime to IST timezone.
    
    Args:
        dt (datetime): Datetime object (can be naive or timezone-aware)
        
    Returns:
        datetime: Datetime converted to IST
    """
    if dt is None:
        return None
        
    if dt.tzinfo is None:
        # Assume naive datetime is in UTC
        dt = dt.replace(tzinfo=UTC)
    
    return dt.astimezone(IST)

def format_ist(dt, format_str='%Y-%m-%d %H:%M'):
    """
    Format datetime in IST timezone.
    
    Args:
        dt (datetime): Datetime object
        format_str (str): Format string for strftime
        
    Returns:
        str: Formatted datetime string in IST
    """
    if dt is None:
        return 'N/A'
        
    ist_dt = to_ist(dt)
    return ist_dt.strftime(format_str)

def ensure_timezone(dt, default_tz=UTC):
    """
    Ensure datetime has timezone information.
    
    Args:
        dt (datetime): Datetime object
        default_tz: Default timezone to apply if datetime is naive
        
    Returns:
        datetime: Timezone-aware datetime
    """
    if dt is None:
        return None
        
    if dt.tzinfo is None:
        return dt.replace(tzinfo=default_tz)
    
    return dt

def is_within_hours(dt, hours=24, reference_time=None):
    """
    Check if datetime is within specified hours from reference time.
    
    Args:
        dt (datetime): Datetime to check
        hours (int): Number of hours to check within
        reference_time (datetime): Reference time (defaults to current UTC time)
        
    Returns:
        bool: True if datetime is within specified hours
    """
    if dt is None:
        return False
        
    if reference_time is None:
        reference_time = now_utc()
    
    dt_utc = to_utc(dt)
    ref_utc = to_utc(reference_time)
    
    time_diff = ref_utc - dt_utc
    return time_diff.total_seconds() <= (hours * 3600)

def get_hours_ago(hours):
    """
    Get datetime that is specified hours ago from now in UTC.
    
    Args:
        hours (int): Number of hours ago
        
    Returns:
        datetime: UTC datetime that is specified hours ago
    """
    from datetime import timedelta
    return now_utc() - timedelta(hours=hours)

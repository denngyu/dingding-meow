"""喝水提醒间隔的校验、持久化和到期判断。"""

from settings_store import read_settings, update_settings


DEFAULT_WATER_REMINDER_MIN = 30
WATER_REMINDER_OPTIONS = (20, 30, 45, 60, 90)
MIN_WATER_REMINDER_MIN = 20
MAX_WATER_REMINDER_MIN = 180


def validate_water_reminder(value):
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return None
    if not MIN_WATER_REMINDER_MIN <= minutes <= MAX_WATER_REMINDER_MIN:
        return None
    return minutes


def load_water_reminder(path):
    try:
        data = read_settings(path)
        value = validate_water_reminder(data.get("water_reminder_minutes"))
    except (OSError, TypeError, AttributeError):
        value = None
    return DEFAULT_WATER_REMINDER_MIN if value is None else value


def save_water_reminder(path, minutes):
    minutes = validate_water_reminder(minutes)
    if minutes is None:
        raise ValueError("water reminder must be between 20 and 180 minutes")
    update_settings(path, water_reminder_minutes=minutes)


def reminder_due(now, anchor_ts, last_nudge_ts, interval_minutes, water, target):
    if water >= target:
        return False
    latest = max(anchor_ts or 0, last_nudge_ts or 0)
    return now - latest >= interval_minutes * 60

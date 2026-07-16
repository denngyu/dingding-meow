"""Windows 会话锁定检测与在座宽限判断。"""

import ctypes
import os


DESKTOP_SWITCHDESKTOP = 0x0100
SESSION_RESUME_SEC = 30


def is_session_locked(user32=None, platform_name=None):
    platform_name = os.name if platform_name is None else platform_name
    if platform_name != "nt":
        return False
    user32 = ctypes.windll.user32 if user32 is None else user32
    desktop = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
    if not desktop:
        return True
    try:
        return not bool(user32.SwitchDesktop(desktop))
    finally:
        user32.CloseDesktop(desktop)


def is_present(blocked, locked, last_seen, now, grace_seconds):
    if blocked or locked or not last_seen:
        return False
    return now - last_seen < grace_seconds


def session_gap_expired(away_since, now, locked=False, resume_seconds=SESSION_RESUME_SEC):
    """短暂检测不到脸时保留本次久坐；锁屏则立即结束。"""
    if locked:
        return True
    if away_since is None:
        return False
    return float(now) - float(away_since) > float(resume_seconds)

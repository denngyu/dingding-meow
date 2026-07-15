"""Windows 会话锁定检测与在座宽限判断。"""

import ctypes
import os


DESKTOP_SWITCHDESKTOP = 0x0100


def is_session_locked(user32=None, platform_name=None):
    platform_name = os.name if platform_name is None else platform_name
    if platform_name != "nt":
        return False
    user32 = ctypes.windll.user32 if user32 is None else user32
    desktop = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
    if not desktop:
        return True
    user32.CloseDesktop(desktop)
    return False


def is_present(blocked, locked, last_seen, now, grace_seconds):
    if blocked or locked or not last_seen:
        return False
    return now - last_seen < grace_seconds

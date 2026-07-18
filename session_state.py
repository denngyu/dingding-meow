"""Windows 会话锁定检测与在座宽限判断。"""

import ctypes
import os


DESKTOP_SWITCHDESKTOP = 0x0100
SESSION_RESUME_SEC = 30
WTS_CURRENT_SESSION = 0xFFFFFFFF
WTS_SESSION_INFO_EX = 25
WTS_SESSIONSTATE_LOCK = 0
WTS_SESSIONSTATE_UNLOCK = 1
WTS_SESSIONSTATE_UNKNOWN = 0xFFFFFFFF


class _WTSINFOEX_LEVEL1_W(ctypes.Structure):
    _fields_ = [
        ("SessionId", ctypes.c_uint32),
        ("SessionState", ctypes.c_int32),
        ("SessionFlags", ctypes.c_int32),
        ("WinStationName", ctypes.c_wchar * 33),
        ("UserName", ctypes.c_wchar * 21),
        ("DomainName", ctypes.c_wchar * 18),
        ("LogonTime", ctypes.c_int64),
        ("ConnectTime", ctypes.c_int64),
        ("DisconnectTime", ctypes.c_int64),
        ("LastInputTime", ctypes.c_int64),
        ("CurrentTime", ctypes.c_int64),
        ("IncomingBytes", ctypes.c_uint32),
        ("OutgoingBytes", ctypes.c_uint32),
        ("IncomingFrames", ctypes.c_uint32),
        ("OutgoingFrames", ctypes.c_uint32),
        ("IncomingCompressedBytes", ctypes.c_uint32),
        ("OutgoingCompressedBytes", ctypes.c_uint32),
    ]


class _WTSINFOEX_LEVEL_W(ctypes.Union):
    _fields_ = [("WTSInfoExLevel1", _WTSINFOEX_LEVEL1_W)]


class _WTSINFOEXW(ctypes.Structure):
    _fields_ = [
        ("Level", ctypes.c_uint32),
        ("Data", _WTSINFOEX_LEVEL_W),
    ]


def _lock_state_from_wts_flags(flags):
    flags = int(flags) & 0xFFFFFFFF
    if flags == WTS_SESSIONSTATE_LOCK:
        return True
    if flags == WTS_SESSIONSTATE_UNLOCK:
        return False
    return None


def query_wts_session_lock_state(wtsapi32=None, platform_name=None):
    """Return True/False from WTSSessionInfoEx, or None when unavailable."""
    platform_name = os.name if platform_name is None else platform_name
    if platform_name != "nt":
        return None
    try:
        wtsapi32 = wtsapi32 or ctypes.WinDLL("Wtsapi32.dll", use_last_error=True)
        query = wtsapi32.WTSQuerySessionInformationW
        free = wtsapi32.WTSFreeMemory
        query.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        query.restype = ctypes.c_int
        free.argtypes = [ctypes.c_void_p]
        free.restype = None
    except (AttributeError, OSError):
        return None

    buffer = ctypes.c_void_p()
    returned = ctypes.c_uint32()
    try:
        ok = query(
            None,
            WTS_CURRENT_SESSION,
            WTS_SESSION_INFO_EX,
            ctypes.byref(buffer),
            ctypes.byref(returned),
        )
        if not ok or not buffer.value or returned.value < ctypes.sizeof(_WTSINFOEXW):
            return None
        info = ctypes.cast(buffer, ctypes.POINTER(_WTSINFOEXW)).contents
        if info.Level != 1:
            return None
        return _lock_state_from_wts_flags(info.Data.WTSInfoExLevel1.SessionFlags)
    except (OSError, ValueError):
        return None
    finally:
        if buffer.value:
            try:
                free(buffer)
            except (OSError, ValueError):
                pass


def is_session_locked(user32=None, platform_name=None, prefer_wts=None):
    platform_name = os.name if platform_name is None else platform_name
    if platform_name != "nt":
        return False
    if prefer_wts is None:
        prefer_wts = user32 is None
    if prefer_wts:
        wts_locked = query_wts_session_lock_state(platform_name=platform_name)
        if wts_locked is not None:
            return wts_locked
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


def session_end_time(
    sit_start,
    away_since,
    now,
    locked=False,
    resume_seconds=SESSION_RESUME_SEC,
):
    """Return the timestamp that should close a pending sitting session."""
    if sit_start is None:
        return None
    if locked:
        return float(now)
    if session_gap_expired(away_since, now, resume_seconds=resume_seconds):
        return float(away_since)
    return None

"""窗口位置守护：多屏切单屏后把浮窗拽回主屏可见区域。

Windows 上用 user32.MonitorFromPoint 判断窗口中心点是否落在任何一块当前显示器上。
非 Windows 平台或 API 不可用时默认认为窗口可见，不做 snap，避免误干扰。
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes


_user32 = None
if sys.platform == "win32":
    try:
        _user32 = ctypes.windll.user32
    except (OSError, AttributeError):
        _user32 = None


class _POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


MONITOR_DEFAULTTONULL = 0


def is_point_on_monitor(x, y):
    """给定屏幕坐标 (x,y)，返回是否落在任何一块当前显示器上。

    非 Windows / API 拿不到 → 返回 True（不误 snap）。
    """
    if _user32 is None:
        return True
    try:
        _user32.MonitorFromPoint.restype = wintypes.HANDLE
        hmon = _user32.MonitorFromPoint(_POINT(int(x), int(y)), MONITOR_DEFAULTTONULL)
        return bool(hmon)
    except Exception:
        return True


def snap_target(sw, sh, win_w, win_h, margin_x=20, margin_y=30):
    """主屏右下角的窗口左上角目标坐标。"""
    return sw - win_w - margin_x, sh - win_h - margin_y


def needs_reposition(cur_x, cur_y, win_w, win_h, on_monitor_fn=None):
    """窗口中心点是否已经离开所有显示器。

    on_monitor_fn: 可注入的 (x,y)->bool 检查器；默认用 is_point_on_monitor。
    """
    if on_monitor_fn is None:
        on_monitor_fn = is_point_on_monitor
    center_x = cur_x + win_w // 2
    center_y = cur_y + win_h // 2
    return not on_monitor_fn(center_x, center_y)

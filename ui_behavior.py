"""桌面猫的简洁状态文案与悬停区域判断。"""


def _compact_minutes(seconds):
    minutes = max(0, int(seconds) // 60)
    if minutes < 1:
        return "<1分钟"
    hours, remain = divmod(minutes, 60)
    if not hours:
        return "%d分钟" % remain
    if not remain:
        return "%d小时" % hours
    return "%d小时%d分" % (hours, remain)


def compact_status(mode, sit_seconds=0, away_seconds=0, locked=False, water_nudge=False):
    if locked:
        return "已锁屏 · 离开"
    if mode in ("seated", "over"):
        if water_nudge:
            minutes = max(0, int(sit_seconds) // 60)
            return "💧 喝水 · 久坐%d分" % minutes
        return "久坐 " + _compact_minutes(sit_seconds)
    if mode == "away":
        return "已离开 " + _compact_minutes(away_seconds)
    if mode == "blocked":
        return "镜头被挡住了"
    if mode == "paused":
        return "检测已暂停"
    return "启动中…"


def status_label_y(cat_bottom, sprite_size, sprite_key):
    """Return the compact label baseline, compensating for transparent sprite padding."""
    base_y = cat_bottom - sprite_size - 4
    if sprite_key == "sleep":
        return base_y + 40
    return base_y


def detail_bubble_top(cat_center_y, bubble_height, mood):
    top = cat_center_y - 32 - 20 - bubble_height
    if mood == "seated":
        return top - 24
    return top


def video_bubble_top(hidden_top, progress, open_top=20):
    progress = max(0.0, min(1.0, progress))
    return int(hidden_top + (open_top - hidden_top) * progress)


def _contains(x, y, bounds):
    x1, y1, x2, y2 = bounds
    return x1 <= x <= x2 and y1 <= y <= y2


def pointer_keeps_details_open(x, y, cat_bounds, detail_bounds=None):
    if _contains(x, y, cat_bounds):
        return True
    return detail_bounds is not None and _contains(x, y, detail_bounds)

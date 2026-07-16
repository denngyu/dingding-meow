"""久坐满一小时后的中央叩屏提醒：水平翻滚、叩屏与返回时间轴。"""

import math
from typing import NamedTuple

from settings_store import read_settings, update_settings


SETTINGS_KEY = "center_nudge_enabled"
DEFAULT_ENABLED = True
TRIGGER_AFTER_SEC = 60 * 60

# 猫只沿 X 轴慢慢翻滚到屏幕中央，叩三次并停留，再翻滚回原位。
ROLL_SEC = 3.2
KNOCK_COUNT = 3
KNOCK_CYCLE_SEC = 0.95
KNOCK_SEC = KNOCK_COUNT * KNOCK_CYCLE_SEC
KNOCK_START = ROLL_SEC
KNOCK_END = KNOCK_START + KNOCK_SEC
HOLD_SEC = 4.0
ROLL_BACK_START = KNOCK_END + HOLD_SEC
TOTAL_DURATION = ROLL_BACK_START + ROLL_SEC
KNOCK_CONTACT_PROGRESS = 0.5


class TripSample(NamedTuple):
    phase: str
    x: int
    y: int
    sprite: str
    frame_progress: float
    facing: int
    show_message: bool
    rotation_degrees: float
    steam: float
    done: bool


def load_enabled(path):
    value = read_settings(path).get(SETTINGS_KEY, DEFAULT_ENABLED)
    return value if isinstance(value, bool) else DEFAULT_ENABLED


def save_enabled(path, enabled):
    enabled = bool(enabled)
    update_settings(path, **{SETTINGS_KEY: enabled})
    return enabled


def should_start(sit_seconds, mode, enabled, triggered, active):
    return (
        bool(enabled)
        and not triggered
        and not active
        and mode in ("seated", "over")
        and float(sit_seconds) >= TRIGGER_AFTER_SEC
    )


def should_cancel(mode, locked, paused, enabled):
    return (
        not enabled
        or bool(locked)
        or bool(paused)
        or mode not in ("seated", "over")
    )


def cat_center_target(screen_width, start_y, cat_local_x):
    """只把猫的水平中心移到屏幕中央，保留窗口原始 Y。"""
    return (
        int(round(screen_width / 2.0 - cat_local_x)),
        int(round(start_y)),
    )


def _clamp01(value):
    return max(0.0, min(1.0, float(value)))


def _facing(start_x, target_x):
    return 1 if target_x >= start_x else -1


def _smoothstep(value):
    value = _clamp01(value)
    return value * value * (3.0 - 2.0 * value)


def _lerp_int(start, end, progress):
    return int(round(float(start) + (float(end) - float(start)) * progress))


def _roll_turns(start_x, target_x):
    """按移动距离选择完整圈数，确保两端都以正向姿势衔接。"""
    distance = abs(float(target_x) - float(start_x))
    return max(1, int(round(distance / 280.0)))


def _steam_level(progress):
    progress = _clamp01(progress)
    # 两端慢慢淡入淡出，避免翻滚刚开始就突然冒出一团蒸汽。
    return math.sin(math.pi * progress) ** 1.35


def _knock_frame_progress(cycle_progress):
    """接触段锁定贴掌帧，周期尾回到与下一周期相同的准备帧。"""
    cycle_progress = _clamp01(cycle_progress)
    if cycle_progress < 0.24:
        return KNOCK_CONTACT_PROGRESS * _smoothstep(cycle_progress / 0.24)
    if cycle_progress < 0.64:
        return KNOCK_CONTACT_PROGRESS
    if cycle_progress < 0.86:
        retract = _smoothstep((cycle_progress - 0.64) / 0.22)
        return 0.6 + 0.4 * retract
    return 1.0


def sample_trip(elapsed, start, target):
    elapsed = max(0.0, float(elapsed))
    facing = _facing(start[0], target[0])
    turns = _roll_turns(start[0], target[0])

    if elapsed < KNOCK_START:
        progress = _clamp01(elapsed / ROLL_SEC)
        eased = _smoothstep(progress)
        return TripSample(
            "roll-in",
            _lerp_int(start[0], target[0], eased),
            start[1],
            "roll",
            0.0,
            facing,
            False,
            -facing * 360.0 * turns * eased,
            _steam_level(progress),
            False,
        )

    if elapsed < KNOCK_END:
        local = elapsed - KNOCK_START
        cycle_progress = (local % KNOCK_CYCLE_SEC) / KNOCK_CYCLE_SEC
        frame_progress = _knock_frame_progress(cycle_progress)
        return TripSample(
            "knock", target[0], target[1], "knock", frame_progress,
            facing, True, 0.0, 0.0, False,
        )

    if elapsed < ROLL_BACK_START:
        return TripSample(
            "hold", target[0], target[1], "knock", 0.0,
            facing, True, 0.0, 0.0, False,
        )

    if elapsed < TOTAL_DURATION:
        progress = _clamp01((elapsed - ROLL_BACK_START) / ROLL_SEC)
        eased = _smoothstep(progress)
        return TripSample(
            "roll-back",
            _lerp_int(target[0], start[0], eased),
            start[1],
            "roll",
            0.0,
            -facing,
            False,
            facing * 360.0 * turns * eased,
            _steam_level(progress),
            False,
        )

    return TripSample(
        "done", start[0], start[1], "roll", 0.0,
        -facing, False, 0.0, 0.0, True,
    )

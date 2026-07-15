"""盯盯喵图片角色的状态选择与素材加载。"""

from pathlib import Path
import sys

from PIL import Image


SPRITE_KEYS = (
    "idle",
    "watch",
    "tail",
    "over",
    "hold_cup",
    "drink",
    "away",
    "sleep",
)
DEFAULT_SPRITE_SIZE = 144
COLOR_KEY_ALPHA_CUTOFF = 96


def asset_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def sprite_path(key):
    if key not in SPRITE_KEYS:
        raise KeyError("unknown cat sprite: %s" % key)
    return asset_root() / "assets" / "cat_sprites" / (key + ".png")


def select_sprite(mood="seated", eyes_open=False, blink=False, cup_state=None, resting=False):
    if cup_state:
        state, progress = cup_state
        if state == "drink" and 0.2 <= progress <= 0.82:
            return "drink"
        return "hold_cup"
    if mood == "over":
        return "over"
    if mood in ("away", "blocked"):
        return "away"
    if mood == "paused":
        return "sleep"
    if mood == "init":
        return "tail"
    if resting and mood == "seated" and not eyes_open:
        return "sleep"
    if eyes_open and not blink:
        return "watch"
    return "idle"


def eye_hitbox(cx, bottom, size=DEFAULT_SPRITE_SIZE):
    return cx - 24, bottom - size + 30, cx + 24, bottom - size + 70


def load_sprite_images(size=DEFAULT_SPRITE_SIZE):
    images = {}
    for key in SPRITE_KEYS:
        with Image.open(sprite_path(key)) as source:
            image = source.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            # Windows Tk 的 transparentcolor 是色键透明，不支持半透明边缘；
            # 半透明像素会和 #FE00FE 混合成紫边，因此显示尺寸上改成二值 alpha。
            alpha = image.getchannel("A").point(
                lambda value: 255 if value >= COLOR_KEY_ALPHA_CUTOFF else 0
            )
            image.putalpha(alpha)
            images[key] = image
    return images

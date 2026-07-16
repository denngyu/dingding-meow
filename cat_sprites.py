"""盯盯喵图片角色的状态选择与素材加载。"""

from pathlib import Path
import math
import sys

from PIL import Image
import skin_system


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
KNOCK_FRAME_COUNT = 5
ROLL_FRAME_COUNT = 24
ROLL_SUBJECT_SCALE = 0.56
_KNOCK_FRAME_SPECS = (
    (0, 0, 0),
    (1, 29, -2),
    (2, 79, -3),
    (1, 29, -2),
    (0, 0, 0),
)
_ACTION_SOURCE_SIZE = 384


def asset_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def sprite_path(key, skin_id=skin_system.DEFAULT_SKIN_ID):
    if key not in SPRITE_KEYS:
        raise KeyError("unknown cat sprite: %s" % key)
    skin = skin_system.resolve_skin(asset_root(), skin_id)
    if skin is None:
        raise FileNotFoundError("no complete cat skin is available")
    return skin.sprite_dir / (key + ".png")


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
    # 稳定版没有与 watch.png 同造型的闭眼素材。若眨眼时切到 idle.png，
    # 会瞬间露出另一套坐姿的尾巴，形成约每 5 秒一次的闪图。
    if eyes_open:
        return "watch"
    return "idle"


def enforce_display_invariants(sprite_key, eyes_open=False):
    """Apply final UI invariants after all business-state pose selection."""
    if eyes_open and sprite_key in ("idle", "tail"):
        return "watch"
    return sprite_key


def eye_hitbox(cx, bottom, size=DEFAULT_SPRITE_SIZE):
    return cx - 24, bottom - size + 30, cx + 24, bottom - size + 70


def load_sprite_images(size=DEFAULT_SPRITE_SIZE, skin_id=skin_system.DEFAULT_SKIN_ID):
    images = {}
    for key in SPRITE_KEYS:
        with Image.open(sprite_path(key, skin_id=skin_id)) as source:
            image = source.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            # Windows Tk 的 transparentcolor 是色键透明，不支持半透明边缘；
            # 半透明像素会和 #FE00FE 混合成紫边，因此显示尺寸上改成二值 alpha。
            alpha = image.getchannel("A").point(
                lambda value: 255 if value >= COLOR_KEY_ALPHA_CUTOFF else 0
            )
            image.putalpha(alpha)
            images[key] = image
    return images


def _color_key_safe(image):
    image = image.convert("RGBA")
    alpha = image.getchannel("A").point(
        lambda value: 255 if value >= COLOR_KEY_ALPHA_CUTOFF else 0
    )
    image.putalpha(alpha)
    return image


def _load_normalized(path, size):
    with Image.open(path) as source:
        image = source.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    return _color_key_safe(image)


def knock_frame_path(index):
    if not 0 <= int(index) < KNOCK_FRAME_COUNT:
        raise IndexError(index)
    source_index = _KNOCK_FRAME_SPECS[int(index)][0]
    return asset_root() / "assets" / "cat_animations" / "knock" / ("frame_%02d.png" % source_index)


def roll_sprite_path():
    return asset_root() / "assets" / "cat_animations" / "roll" / "roll_ball.png"


def _translate_knock_frame(image, source_dx, source_dy):
    if not source_dx and not source_dy:
        return image
    scale = image.width / float(_ACTION_SOURCE_SIZE)
    dx = int(round(source_dx * scale))
    dy = int(round(source_dy * scale))
    translated = Image.new("RGBA", image.size, (0, 0, 0, 0))
    translated.alpha_composite(image, (dx, dy))
    return _color_key_safe(translated)


def load_knock_frames(size=DEFAULT_SPRITE_SIZE):
    frames = []
    for index, (_, dx, dy) in enumerate(_KNOCK_FRAME_SPECS):
        image = _load_normalized(knock_frame_path(index), size)
        frames.append(_translate_knock_frame(image, dx, dy))
    return frames


def load_roll_frames(size=DEFAULT_SPRITE_SIZE, frame_count=ROLL_FRAME_COUNT):
    """从独立毛球素材预生成完整一圈旋转帧，并返回底部对齐补偿。"""
    with Image.open(roll_sprite_path()) as source:
        base = source.convert("RGBA")
    bbox = base.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("roll sprite is empty")

    subject = base.crop(bbox)
    target_extent = max(1, int(round(float(size) * ROLL_SUBJECT_SCALE)))
    resize_scale = target_extent / float(max(subject.size))
    target_size = (
        max(1, int(round(subject.width * resize_scale))),
        max(1, int(round(subject.height * resize_scale))),
    )
    subject = subject.resize(target_size, Image.Resampling.LANCZOS)
    subject = _color_key_safe(subject)

    diagonal = int(math.ceil(math.hypot(subject.width, subject.height))) + 4
    canvas_size = max(int(size) + 16, diagonal)
    if canvas_size % 2:
        canvas_size += 1

    centered = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    paste_x = (canvas_size - subject.width) // 2
    paste_y = (canvas_size - subject.height) // 2
    centered.alpha_composite(subject, (paste_x, paste_y))
    centered = _color_key_safe(centered)

    centered_bbox = centered.getchannel("A").getbbox()
    centered_bottom_margin = canvas_size - centered_bbox[3]
    bottom_offset = centered_bottom_margin

    frames = []
    frame_count = max(1, int(frame_count))
    for index in range(frame_count):
        degrees = 360.0 * index / frame_count
        rotated = centered.rotate(
            degrees,
            resample=Image.Resampling.BICUBIC,
            expand=False,
        )
        frames.append(_color_key_safe(rotated))
    return frames, bottom_offset


def roll_frame_index(rotation_degrees, frame_count=ROLL_FRAME_COUNT):
    frame_count = max(1, int(frame_count))
    normalized = float(rotation_degrees) % 360.0
    return int(round(normalized / 360.0 * frame_count)) % frame_count

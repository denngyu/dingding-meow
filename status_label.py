"""为色键透明窗口生成无紫边的小型状态签。"""

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _load_font(size):
    fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf"):
        try:
            return ImageFont.truetype(str(fonts / name), size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_status_label(text, font_size=14):
    font = _load_font(font_size)
    probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    left, top, right, bottom = probe_draw.textbbox((0, 0), text, font=font)
    width = right - left + 16
    height = bottom - top + 8
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (0, 0, width - 1, height - 1),
        radius=7,
        fill=(247, 246, 243, 255),
        outline=(217, 216, 208, 255),
        width=1,
    )
    draw.text((8 - left, 4 - top), text, font=font, fill=(88, 92, 87, 255))
    return image

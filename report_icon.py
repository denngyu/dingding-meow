"""Build the self-contained cat favicon used by generated health reports."""

import base64
import io

from PIL import Image, ImageDraw

import cat_sprites


FAVICON_SIZE = 64


def _fallback_cat_icon():
    image = Image.new("RGBA", (FAVICON_SIZE, FAVICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    outline = (80, 82, 78, 255)
    fur = (190, 187, 178, 255)
    draw.polygon(((12, 25), (17, 7), (29, 20)), fill=fur, outline=outline)
    draw.polygon(((35, 20), (47, 7), (52, 25)), fill=fur, outline=outline)
    draw.ellipse((9, 14, 55, 58), fill=fur, outline=outline, width=2)
    draw.ellipse((20, 30, 26, 38), fill=(35, 36, 33, 255))
    draw.ellipse((38, 30, 44, 38), fill=(35, 36, 33, 255))
    draw.polygon(((29, 42), (35, 42), (32, 46)), fill=(221, 137, 133, 255))
    draw.arc((27, 42, 33, 50), 0, 120, fill=outline, width=1)
    draw.arc((31, 42, 37, 50), 60, 180, fill=outline, width=1)
    return image


def build_report_favicon_image(source_path=None):
    try:
        path = source_path or cat_sprites.sprite_path("idle")
        with Image.open(path) as source:
            source = source.convert("RGBA")
            bbox = source.getchannel("A").getbbox()
            if bbox is None:
                raise ValueError("empty cat sprite")
            left, top, right, bottom = bbox
            head_bottom = min(bottom, top + int((bottom - top) * 0.66))
            subject = source.crop((left, top, right, head_bottom))
            subject.thumbnail((58, 58), Image.Resampling.LANCZOS)
    except (OSError, ValueError):
        return _fallback_cat_icon()

    image = Image.new("RGBA", (FAVICON_SIZE, FAVICON_SIZE), (0, 0, 0, 0))
    x = (FAVICON_SIZE - subject.width) // 2
    y = (FAVICON_SIZE - subject.height) // 2
    image.alpha_composite(subject, (x, y))
    return image


def build_report_favicon_data_uri(source_path=None):
    buffer = io.BytesIO()
    build_report_favicon_image(source_path).save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return "data:image/png;base64," + encoded


def report_favicon_link(source_path=None):
    return '<link rel="icon" type="image/png" href="%s">' % build_report_favicon_data_uri(source_path)

"""统一的猫头图标：健康报告 favicon、托盘图标、exe 图标共用同一个裁剪源。"""

import base64
import io

from PIL import Image, ImageDraw

import cat_sprites


FAVICON_SIZE = 64
ICO_SIZES = ((16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256))


def _fallback_cat_icon(size=FAVICON_SIZE):
    """图片素材不可读时的兜底手绘头像。"""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    outline = (80, 82, 78, 255)
    fur = (190, 187, 178, 255)
    s = size / 64.0
    def r(a): return int(a * s)
    draw.polygon(((r(12), r(25)), (r(17), r(7)), (r(29), r(20))), fill=fur, outline=outline)
    draw.polygon(((r(35), r(20)), (r(47), r(7)), (r(52), r(25))), fill=fur, outline=outline)
    draw.ellipse((r(9), r(14), r(55), r(58)), fill=fur, outline=outline, width=max(1, r(2)))
    draw.ellipse((r(20), r(30), r(26), r(38)), fill=(35, 36, 33, 255))
    draw.ellipse((r(38), r(30), r(44), r(38)), fill=(35, 36, 33, 255))
    draw.polygon(((r(29), r(42)), (r(35), r(42)), (r(32), r(46))), fill=(221, 137, 133, 255))
    draw.arc((r(27), r(42), r(33), r(50)), 0, 120, fill=outline, width=1)
    draw.arc((r(31), r(42), r(37), r(50)), 60, 180, fill=outline, width=1)
    return image


def build_cat_head_image(size=FAVICON_SIZE, source_path=None):
    """裁 idle sprite 的猫头，居中放进 size×size 透明画布。所有场景的图标都走这里。"""
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
            target = max(8, int(size * 0.9))
            subject.thumbnail((target, target), Image.Resampling.LANCZOS)
    except (OSError, ValueError):
        return _fallback_cat_icon(size)

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - subject.width) // 2
    y = (size - subject.height) // 2
    image.alpha_composite(subject, (x, y))
    return image


def build_report_favicon_image(source_path=None):
    """向后兼容：健康报告页 favicon（固定 64×64）。"""
    return build_cat_head_image(FAVICON_SIZE, source_path)


def build_report_favicon_data_uri(source_path=None):
    buffer = io.BytesIO()
    build_report_favicon_image(source_path).save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return "data:image/png;base64," + encoded


def report_favicon_link(source_path=None):
    return '<link rel="icon" type="image/png" href="%s">' % build_report_favicon_data_uri(source_path)


def save_ico(path, source_path=None, sizes=ICO_SIZES):
    """把猫头写成 Windows 多尺寸 .ico，供 exe 图标和 .lnk IconLocation 使用。"""
    largest = max(w for w, _ in sizes)
    image = build_cat_head_image(largest, source_path)
    image.save(path, format="ICO", sizes=sizes)
    return path

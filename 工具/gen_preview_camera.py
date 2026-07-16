"""生成 promo 页监控气泡里的 mock 摄像头预览图。

思路：造一张"办公桌前一个人"的低保真剪影 + 绿色 face box + 橙色 cup box +
细扫描线 + 角上一个 REC 红点，让 promo 首屏的视频气泡从纯黑框升级成
"能看出是摄像头画面"的占位。

一次性脚本，产出 `assets/preview_camera.png`。以后想换真实截图直接覆盖该文件。
"""
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont


W, H = 480, 360
FACE_GREEN = (82, 201, 130, 240)
CUP_ORANGE = (255, 168, 92, 240)
REC_RED = (215, 68, 58, 255)


def _load_font(size):
    for name in (
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        if os.path.exists(name):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_office_backdrop(im):
    """深色暖调渐变 + 模糊办公室元素（显示器、窗、绿植、桌面）。"""
    draw = ImageDraw.Draw(im)
    for y in range(H):
        factor = 1 - y / H * 0.55
        draw.line(
            [(0, y), (W, y)],
            fill=(int(48 * factor), int(42 * factor), int(38 * factor)),
        )

    temp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp)
    td.rectangle([28, 32, 178, 208], fill=(45, 40, 36, 220))
    td.rectangle([40, 44, 168, 194], fill=(72, 92, 112, 190))
    td.rectangle([340, 12, 468, 128], fill=(128, 120, 108, 210))
    td.line([395, 14, 395, 126], fill=(65, 60, 54, 220), width=2)
    td.line([342, 68, 466, 68], fill=(65, 60, 54, 220), width=2)
    td.ellipse([362, 78, 420, 148], fill=(52, 72, 44, 210))
    td.ellipse([385, 68, 428, 130], fill=(58, 82, 50, 210))
    td.rectangle([0, 265, 480, 360], fill=(32, 26, 22, 245))
    td.rectangle([410, 175, 480, 300], fill=(52, 36, 32, 210))
    temp = temp.filter(ImageFilter.GaussianBlur(radius=6))
    im.paste(temp, (0, 0), temp)


def _draw_person(draw, cx, cy):
    """居中偏右的低保真剪影：肩+脖+头+发+五官。"""
    draw.ellipse([cx - 130, cy + 78, cx + 130, cy + 350], fill=(40, 44, 58))
    draw.rectangle([cx - 24, cy + 42, cx + 24, cy + 92], fill=(90, 74, 64))
    draw.ellipse([cx - 48, cy - 55, cx + 48, cy + 55], fill=(105, 84, 72))
    draw.chord([cx - 52, cy - 62, cx + 52, cy + 22], 200, 340, fill=(48, 34, 26))
    draw.ellipse([cx - 54, cy - 6, cx - 42, cy + 16], fill=(92, 72, 60))
    draw.ellipse([cx + 42, cy - 6, cx + 54, cy + 16], fill=(92, 72, 60))
    draw.ellipse([cx - 24, cy - 10, cx - 12, cy - 1], fill=(30, 22, 18))
    draw.ellipse([cx + 12, cy - 10, cx + 24, cy - 1], fill=(30, 22, 18))
    draw.ellipse([cx - 26, cy - 12, cx - 20, cy - 6], fill=(255, 255, 255, 180))
    draw.ellipse([cx + 14, cy - 12, cx + 20, cy - 6], fill=(255, 255, 255, 180))
    draw.arc([cx - 12, cy + 10, cx + 12, cy + 28], 0, 180, fill=(60, 40, 35), width=2)


def _draw_cup(draw, x, y):
    """桌上的马克杯，与橙色框对齐。"""
    draw.rectangle([x, y, x + 30, y + 40], fill=(148, 136, 122))
    draw.ellipse([x - 2, y - 5, x + 32, y + 6], fill=(168, 156, 142))
    draw.ellipse([x + 4, y + 2, x + 26, y + 10], fill=(88, 62, 42))
    draw.arc([x + 26, y + 10, x + 44, y + 32], 270, 90, fill=(148, 136, 122), width=3)


def _draw_scanlines_and_noise(draw):
    for y in range(0, H, 3):
        draw.line([(0, y), (W, y)], fill=(0, 0, 0, 14))
    rng = random.Random(42)
    for _ in range(360):
        rx, ry = rng.randint(0, W - 1), rng.randint(0, H - 1)
        v = rng.randint(200, 255)
        draw.point((rx, ry), fill=(v, v, v, rng.randint(20, 55)))


def _draw_vignette(im):
    """四角轻微暗角，营造摄像头感。"""
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([-80, -60, W + 80, H + 60], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=60))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    im.paste(dark, (0, 0), Image.eval(mask, lambda v: 255 - v))


def _draw_hud(draw, font_small, font_mono):
    draw.ellipse([14, 14, 24, 24], fill=REC_RED[:3])
    draw.text((30, 12), "REC", fill=REC_RED, font=font_small)
    draw.text((W - 132, H - 22), "CAM 0 · 12:34:56", fill=(210, 210, 210, 210), font=font_mono)


def _draw_detection_overlays(draw, person_cx, person_cy, cup_x, cup_y, font_small):
    face_pad = 12
    fb = (
        person_cx - 48 - face_pad,
        person_cy - 55 - face_pad,
        person_cx + 48 + face_pad,
        person_cy + 55 + face_pad,
    )
    draw.rectangle(fb, outline=FACE_GREEN, width=2)
    draw.text((fb[0] + 4, fb[1] - 15), "face 0.94", fill=FACE_GREEN, font=font_small)

    cup_pad = 5
    cbox = (cup_x - cup_pad, cup_y - 8, cup_x + 30 + cup_pad, cup_y + 40 + cup_pad)
    draw.rectangle(cbox, outline=CUP_ORANGE, width=2)
    draw.text((cbox[0] + 4, cbox[3] + 2), "cup 0.62", fill=CUP_ORANGE, font=font_small)


def build_preview(out_path="assets/preview_camera.png"):
    im = Image.new("RGB", (W, H), (28, 24, 22))
    _draw_office_backdrop(im)
    draw = ImageDraw.Draw(im, "RGBA")

    person_cx, person_cy = 245, 175
    cup_x, cup_y = 130, 290
    _draw_person(draw, person_cx, person_cy)
    _draw_cup(draw, cup_x, cup_y)

    _draw_scanlines_and_noise(draw)
    _draw_vignette(im)

    draw = ImageDraw.Draw(im, "RGBA")
    font_small = _load_font(11)
    font_mono = _load_font(10)
    _draw_detection_overlays(draw, person_cx, person_cy, cup_x, cup_y, font_small)
    _draw_hud(draw, font_small, font_mono)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    im.save(out_path, "PNG", optimize=True)
    return out_path, os.path.getsize(out_path)


if __name__ == "__main__":
    path, size = build_preview()
    print("saved:", path, size, "bytes")

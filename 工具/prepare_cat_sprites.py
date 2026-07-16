"""把4×2角色表拆成统一尺寸的透明PNG状态图。"""

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "cat_sprite_source.png"
SLEEP_SOURCE = ROOT / "assets" / "cat_sleep_source.png"
OUTPUT = ROOT / "assets" / "cat_sprites"
KEYS = ("idle", "watch", "tail", "over", "hold_cup", "drink", "away", "sleep")
CANVAS_SIZE = 384
SUBJECT_LIMIT = 340
CELL_OVERFLOW = {
    # Generated 4x2 sheets can let the curled sleeping body cross the left cell
    # boundary. Keep a small safe overlap so the rear is not cut into a straight
    # vertical edge. The neighbouring bottom-row subject stays outside this area.
    "sleep": (48, 0, 0, 0),
}


def remove_connected_background(cell):
    # 生成图偶尔会让耳朵或尾巴贴到网格边缘。先补一圈背景，
    # 避免 floodfill 的边缘种子直接落在角色上，把整块毛色灌空。
    border = 10
    background = cell.convert("RGB").getpixel((0, 0))
    work = ImageOps.expand(cell.convert("RGB"), border=border, fill=background)
    marker = (0, 255, 0)
    width, height = work.size
    seeds = []
    for x in range(0, width, 24):
        seeds.extend(((x, 0), (x, height - 1)))
    for y in range(0, height, 24):
        seeds.extend(((0, y), (width - 1, y)))
    for seed in seeds:
        if work.getpixel(seed) != marker:
            ImageDraw.floodfill(work, seed, marker, thresh=42)

    original = ImageOps.expand(cell.convert("RGBA"), border=border, fill=background + (255,))
    pixels = original.load()
    mask_pixels = work.load()
    for y in range(height):
        for x in range(width):
            if mask_pixels[x, y] == marker:
                r, g, b, _ = pixels[x, y]
                pixels[x, y] = (r, g, b, 0)
    return original.crop((border, border, width - border, height - border))


def normalize_sprite(sprite):
    alpha = sprite.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise RuntimeError("sprite is empty after background removal")
    left, top, right, bottom = bbox
    margin = 4
    bbox = (max(0, left - margin), max(0, top - margin),
            min(sprite.width, right + margin), min(sprite.height, bottom + margin))
    cropped = sprite.crop(bbox)
    scale = min(SUBJECT_LIMIT / cropped.width, SUBJECT_LIMIT / cropped.height)
    size = (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale)))
    cropped = cropped.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    x = (CANVAS_SIZE - cropped.width) // 2
    y = CANVAS_SIZE - cropped.height - 10
    canvas.alpha_composite(cropped, (x, y))
    return canvas


def sheet_cell(sheet, index, key):
    cell_w, cell_h = sheet.width // 4, sheet.height // 2
    col, row = index % 4, index // 4
    left_pad, top_pad, right_pad, bottom_pad = CELL_OVERFLOW.get(
        key,
        (0, 0, 0, 0),
    )
    return sheet.crop((
        max(0, col * cell_w - left_pad),
        max(0, row * cell_h - top_pad),
        min(sheet.width, (col + 1) * cell_w + right_pad),
        min(sheet.height, (row + 1) * cell_h + bottom_pad),
    ))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=KEYS)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--sleep-source", type=Path, default=SLEEP_SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--use-sheet-sleep", action="store_true")
    args = parser.parse_args(argv)
    source = args.source.resolve()
    sleep_source = args.sleep_source.resolve()
    output = args.output.resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as sheet:
        sheet = sheet.convert("RGBA")
        cell_w, cell_h = sheet.width // 4, sheet.height // 2
        if sheet.width % 4 or sheet.height % 2:
            raise ValueError("source sheet must be a 4x2 grid")
        for index, key in enumerate(KEYS):
            if args.only and key != args.only:
                continue
            if key == "sleep" and not args.use_sheet_sleep and sleep_source.exists():
                with Image.open(sleep_source) as custom_sleep:
                    cell = custom_sleep.convert("RGBA")
            else:
                cell = sheet_cell(sheet, index, key)
            sprite = normalize_sprite(remove_connected_background(cell))
            sprite.save(output / (key + ".png"), optimize=True)
            print(key, sprite.size, sprite.getchannel("A").getbbox())


if __name__ == "__main__":
    main()

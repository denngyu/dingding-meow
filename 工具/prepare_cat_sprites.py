"""把4×2角色表拆成统一尺寸的透明PNG状态图。"""

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "cat_sprite_source.png"
SLEEP_SOURCE = ROOT / "assets" / "cat_sleep_source.png"
OUTPUT = ROOT / "assets" / "cat_sprites"
KEYS = ("idle", "watch", "tail", "over", "hold_cup", "drink", "away", "sleep")
CANVAS_SIZE = 384
SUBJECT_LIMIT = 340


def remove_connected_background(cell):
    work = cell.convert("RGB").copy()
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

    original = cell.convert("RGBA")
    pixels = original.load()
    mask_pixels = work.load()
    for y in range(height):
        for x in range(width):
            if mask_pixels[x, y] == marker:
                r, g, b, _ = pixels[x, y]
                pixels[x, y] = (r, g, b, 0)
    return original


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


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=KEYS)
    args = parser.parse_args(argv)
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE) as sheet:
        sheet = sheet.convert("RGBA")
        cell_w, cell_h = sheet.width // 4, sheet.height // 2
        if sheet.width % 4 or sheet.height % 2:
            raise ValueError("source sheet must be a 4x2 grid")
        for index, key in enumerate(KEYS):
            if args.only and key != args.only:
                continue
            col, row = index % 4, index // 4
            if key == "sleep" and SLEEP_SOURCE.exists():
                with Image.open(SLEEP_SOURCE) as custom_sleep:
                    cell = custom_sleep.convert("RGBA")
            else:
                cell = sheet.crop((col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h))
            sprite = normalize_sprite(remove_connected_background(cell))
            sprite.save(OUTPUT / (key + ".png"), optimize=True)
            print(key, sprite.size, sprite.getchannel("A").getbbox())


if __name__ == "__main__":
    main()

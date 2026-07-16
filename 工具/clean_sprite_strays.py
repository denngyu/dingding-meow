"""扫 assets/cat_sprites/ 里每张精灵图，去掉 alpha 通道里跟主体不连通的小碎片。

背景：pet 运行时会先 resize 到 144，再按 alpha ≥ 96 二值化（色键透明需要），
`tail.png` 里的运动动线（右侧两个小弧）和 `away.png` 头顶几像素残影
都会被保留下来变成视觉上飘着的"("弧。这个脚本一次性把源图里那些不连通的
小块整个抹成透明，覆盖原文件。是**开发期**工具，pet.py 运行时不依赖 scipy。

用法：`python 工具/clean_sprite_strays.py [--dry-run]`
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
SPRITE_DIR = ROOT / "assets" / "cat_sprites"


def find_disconnected(alpha_array, min_alpha=96):
    binary = (alpha_array >= min_alpha).astype(np.uint8)
    labels, n = ndimage.label(binary)
    if n <= 1:
        return None, None, n
    sizes = ndimage.sum(binary, labels, range(1, n + 1))
    largest = int(np.argmax(sizes)) + 1
    to_erase = (labels > 0) & (labels != largest)
    return to_erase, sizes, n


def clean_sprite(path: Path, dry_run=False):
    with Image.open(path) as source:
        image = source.convert("RGBA")
    alpha = np.array(image.getchannel("A"))
    to_erase, sizes, n = find_disconnected(alpha)
    if to_erase is None:
        return {"path": path.name, "components": n, "cleaned": 0}

    ys, xs = np.where(to_erase)
    erased_px = int(to_erase.sum())
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if erased_px else None

    if not dry_run:
        # 把碎片像素 RGBA 全设 0
        rgba = np.array(image)
        rgba[to_erase] = (0, 0, 0, 0)
        Image.fromarray(rgba, mode="RGBA").save(path, "PNG", optimize=True)

    return {
        "path": path.name,
        "components": n,
        "cleaned": erased_px,
        "bbox": bbox,
        "sizes": [int(s) for s in sizes],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只报告不写盘")
    args = parser.parse_args()

    if not SPRITE_DIR.exists():
        print(f"找不到 {SPRITE_DIR}", file=sys.stderr)
        return 1

    reports = []
    for png in sorted(SPRITE_DIR.glob("*.png")):
        reports.append(clean_sprite(png, dry_run=args.dry_run))

    for r in reports:
        if r["cleaned"]:
            print(f"[{r['path']}] {r['components']} 块 → 清 {r['cleaned']} 像素 @ bbox={r['bbox']}"
                  f"  sizes={r['sizes']}")
        else:
            print(f"[{r['path']}] {r['components']} 块 → 干净, 无改动")
    print("Dry-run" if args.dry_run else "写盘完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

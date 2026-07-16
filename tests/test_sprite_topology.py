"""每张精灵图在运行时二值化后必须只剩一块主体，不允许有浮空碎片。

背景：color-key 透明窗口下，alpha 半透明会被拿掉；素材里 antialias 弱线
（tail.png 的运动动线、away.png 的头顶碎点等）会变成看得见的悬浮弧。
所以打包前必须保证每张 sprite 通过 `工具/clean_sprite_strays.py` 清理过。
"""
import unittest

import numpy as np
from PIL import Image

import cat_sprites


def _count_components(binary):
    """4-邻域连通块计数。纯 numpy 手写，不引入 scipy。"""
    h, w = binary.shape
    visited = np.zeros_like(binary, dtype=bool)
    components = 0
    stack = []
    for sy in range(h):
        for sx in range(w):
            if not binary[sy, sx] or visited[sy, sx]:
                continue
            components += 1
            stack.append((sy, sx))
            while stack:
                y, x = stack.pop()
                if y < 0 or y >= h or x < 0 or x >= w:
                    continue
                if visited[y, x] or not binary[y, x]:
                    continue
                visited[y, x] = True
                stack.append((y + 1, x))
                stack.append((y - 1, x))
                stack.append((y, x + 1))
                stack.append((y, x - 1))
    return components


class SpriteTopologyTests(unittest.TestCase):
    def test_every_sprite_is_a_single_connected_shape_at_runtime_size(self):
        size = cat_sprites.DEFAULT_SPRITE_SIZE
        cutoff = cat_sprites.COLOR_KEY_ALPHA_CUTOFF
        for key in cat_sprites.SPRITE_KEYS:
            with Image.open(cat_sprites.sprite_path(key)) as source:
                image = source.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            alpha = np.array(image.getchannel("A"))
            binary = alpha >= cutoff
            components = _count_components(binary)
            self.assertEqual(
                components,
                1,
                f"{key}.png 在 {size}×{size} 二值化后有 {components} 块，"
                "跑 `python 工具/clean_sprite_strays.py` 清一下浮空碎片。",
            )


if __name__ == "__main__":
    unittest.main()

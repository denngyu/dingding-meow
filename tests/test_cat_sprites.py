import re
import unittest
from pathlib import Path

from PIL import Image

import cat_sprites


class CatSpriteAssetTests(unittest.TestCase):
    def test_all_sprite_assets_are_normalized_rgba_images(self):
        for key in cat_sprites.SPRITE_KEYS:
            path = cat_sprites.sprite_path(key)
            self.assertTrue(path.exists(), path)
            with Image.open(path) as image:
                self.assertEqual(image.mode, "RGBA")
                self.assertEqual(image.size, (384, 384))

    def test_sprite_background_is_transparent_and_subject_is_present(self):
        for key in cat_sprites.SPRITE_KEYS:
            with Image.open(cat_sprites.sprite_path(key)) as image:
                alpha = image.getchannel("A")
                corners = [alpha.getpixel(point) for point in ((0, 0), (383, 0), (0, 383), (383, 383))]
                pixels = (
                    alpha.get_flattened_data()
                    if hasattr(alpha, "get_flattened_data")
                    else alpha.getdata()
                )
                coverage = sum(value > 16 for value in pixels) / (384 * 384)
                self.assertEqual(corners, [0, 0, 0, 0], key)
                self.assertGreater(coverage, 0.08, key)
                self.assertLess(coverage, 0.65, key)

    def test_promo_preview_uses_the_same_sprite_character(self):
        promo = (Path(__file__).resolve().parents[1] / "promo.html").read_text(encoding="utf-8")
        self.assertIn('src="assets/cat_sprites/watch.png"', promo)
        self.assertNotIn('<svg class="cat-svg"><use href="#cat"/></svg>', promo)

    def test_promo_camera_preview_uses_a_real_demo_frame(self):
        root = Path(__file__).resolve().parents[1]
        promo = (root / "promo.html").read_text(encoding="utf-8")

        self.assertTrue((root / "assets" / "preview_camera.png").exists())
        self.assertIn(
            '<img class="camera-demo" src="assets/preview_camera.png"',
            promo,
        )
        self.assertIn('alt="人脸与水杯本地检测演示画面"', promo)
        self.assertNotIn('<div class="face-box"></div>', promo)
        self.assertNotIn('<div class="cup-box"></div>', promo)

    def test_promo_stage_is_tall_enough_to_show_the_full_monitor_bubble(self):
        promo = (Path(__file__).resolve().parents[1] / "promo.html").read_text(
            encoding="utf-8"
        )
        ratio = re.search(r"\.stage\{[^}]*aspect-ratio:1/([0-9.]+)", promo)

        self.assertIsNotNone(ratio)
        self.assertGreaterEqual(float(ratio.group(1)), 1.30)

    def test_display_sprites_have_binary_alpha_for_windows_color_key(self):
        for key, image in cat_sprites.load_sprite_images().items():
            alpha = image.getchannel("A")
            extrema = set(alpha.getdata())
            self.assertLessEqual(extrema, {0, 255}, key)

    def test_sleep_sprite_uses_the_wide_curled_up_reference(self):
        with Image.open(cat_sprites.sprite_path("sleep")) as image:
            bbox = image.getchannel("A").getbbox()
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        self.assertGreater(width / height, 1.33)


class CatSpriteStateTests(unittest.TestCase):
    def test_business_states_select_the_expected_pose(self):
        cases = [
            ({"mood": "init"}, "tail"),
            ({"mood": "seated"}, "idle"),
            ({"mood": "seated", "resting": True}, "sleep"),
            ({"mood": "seated", "eyes_open": True}, "watch"),
            ({"mood": "seated", "eyes_open": True, "blink": True}, "idle"),
            ({"mood": "over"}, "over"),
            ({"mood": "away"}, "away"),
            ({"mood": "blocked"}, "away"),
            ({"mood": "paused"}, "sleep"),
            ({"mood": "seated", "cup_state": ("hold", 0.0)}, "hold_cup"),
            ({"mood": "seated", "resting": True, "cup_state": ("hold", 0.0)}, "hold_cup"),
            ({"mood": "seated", "cup_state": ("drink", 0.5)}, "drink"),
            ({"mood": "seated", "cup_state": ("drink", 0.05)}, "hold_cup"),
            ({"mood": "seated", "cup_state": ("drink", 0.95)}, "hold_cup"),
        ]
        for kwargs, expected in cases:
            self.assertEqual(cat_sprites.select_sprite(**kwargs), expected, kwargs)

    def test_eye_hitbox_stays_inside_the_displayed_sprite(self):
        self.assertEqual(cat_sprites.DEFAULT_SPRITE_SIZE, 144)
        box = cat_sprites.eye_hitbox(cx=118, bottom=404)
        self.assertEqual(box, (94, 290, 142, 330))


if __name__ == "__main__":
    unittest.main()

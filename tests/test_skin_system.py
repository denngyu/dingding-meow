import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

import cat_sprites
from skin_system import DEFAULT_SKIN_ID, discover_skins, load_skin, save_skin


class SkinSystemTests(unittest.TestCase):
    def test_project_has_classic_and_orange_complete_skins(self):
        skins = {skin.skin_id: skin for skin in discover_skins(cat_sprites.asset_root())}
        self.assertIn(DEFAULT_SKIN_ID, skins)
        self.assertIn("orange", skins)
        self.assertEqual(skins["orange"].label, "暖橘元气")

    def test_selected_skin_is_persisted_without_overwriting_other_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Path(folder) / "settings.json"
            settings.write_text(json.dumps({"onboarding_version": 2}), encoding="utf-8")
            self.assertEqual(
                save_skin(settings, cat_sprites.asset_root(), "orange"),
                "orange",
            )
            self.assertEqual(load_skin(settings, cat_sprites.asset_root()), "orange")
            data = json.loads(settings.read_text(encoding="utf-8"))
            self.assertEqual(data["onboarding_version"], 2)

    def test_invalid_saved_skin_falls_back_to_classic(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Path(folder) / "settings.json"
            settings.write_text(json.dumps({"skin_id": "missing"}), encoding="utf-8")
            self.assertEqual(load_skin(settings, cat_sprites.asset_root()), DEFAULT_SKIN_ID)

    def test_sprite_loader_can_load_the_orange_skin(self):
        images = cat_sprites.load_sprite_images(skin_id="orange")
        self.assertEqual(set(images), set(cat_sprites.SPRITE_KEYS))
        self.assertTrue(all(image.size == (144, 144) for image in images.values()))
        for key,image in images.items():
            alpha=image.getchannel("A")
            coverage=sum(value>0 for value in alpha.getdata())/(image.width*image.height)
            self.assertGreater(coverage,0.08,key)
            self.assertLess(coverage,0.65,key)

    def test_orange_open_eye_pose_is_not_the_tailed_pose(self):
        images = cat_sprites.load_sprite_images(skin_id="orange")
        self.assertNotEqual(images["watch"].tobytes(), images["idle"].tobytes())
        self.assertNotEqual(images["watch"].tobytes(), images["tail"].tobytes())
        for blink in (False, True):
            selected = cat_sprites.select_sprite(
                mood="seated",
                eyes_open=True,
                blink=blink,
            )
            selected = cat_sprites.enforce_display_invariants(
                selected,
                eyes_open=True,
            )
            self.assertEqual(selected, "watch")
            self.assertEqual(images[selected].tobytes(), images["watch"].tobytes())

    def test_orange_sleep_pose_is_not_cut_at_the_left_cell_boundary(self):
        path = cat_sprites.sprite_path("sleep", skin_id="orange")
        with Image.open(path) as image:
            alpha = image.convert("RGBA").getchannel("A")
        bbox = alpha.getbbox()
        self.assertIsNotNone(bbox)
        left, top, _, bottom = bbox
        opaque_on_left = sum(
            alpha.getpixel((left, y)) >= cat_sprites.COLOR_KEY_ALPHA_CUTOFF
            for y in range(top, bottom)
        )
        self.assertLess(
            opaque_on_left / float(bottom - top),
            0.20,
            "orange sleep sprite has a long straight left edge and was likely cell-cropped",
        )

    def test_orange_hold_cup_has_no_duplicate_center_legs(self):
        path = cat_sprites.sprite_path("hold_cup", skin_id="orange")
        with Image.open(path) as image:
            rgba = np.array(image.convert("RGBA"))
        center_below_glass = rgba[310:370, 155:229]
        dark_outline = (
            (center_below_glass[:, :, :3].max(axis=2) < 70)
            & (center_below_glass[:, :, 3] >= cat_sprites.COLOR_KEY_ALPHA_CUTOFF)
        )
        self.assertLess(
            int(dark_outline.sum()),
            600,
            "orange hold-cup sprite likely contains duplicated center legs below the glass",
        )


if __name__ == "__main__":
    unittest.main()

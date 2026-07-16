import importlib.util
import unittest
from pathlib import Path

from PIL import Image


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "工具" / "prepare_cat_animation_sheet.py"
spec = importlib.util.spec_from_file_location("prepare_cat_animation_sheet", SCRIPT_PATH)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class AnimationSheetGridTests(unittest.TestCase):
    def test_fractional_grid_boundaries_cover_every_source_pixel(self):
        self.assertTrue(hasattr(prepare, "grid_boundaries"))
        bounds = prepare.grid_boundaries(1777, 4)

        self.assertEqual(bounds[0], 0)
        self.assertEqual(bounds[-1], 1777)
        self.assertEqual(len(bounds), 5)
        self.assertTrue(all(left < right for left, right in zip(bounds, bounds[1:])))

    def test_subject_alignment_removes_cross_row_sprite_jumps(self):
        self.assertTrue(hasattr(prepare, "align_subject"))
        frame = Image.new("RGBA", (384, 384), (0, 0, 0, 0))
        frame.paste((120, 120, 120, 255), (20, 40, 220, 300))

        aligned = prepare.align_subject(frame, center_x=192, ground_y=360)
        bbox = aligned.getchannel("A").getbbox()

        self.assertEqual((bbox[0] + bbox[2]) / 2, 192)
        self.assertEqual(bbox[3], 360)

    def test_small_neighbor_cell_fragment_is_removed_before_alignment(self):
        frame = Image.new("RGBA", (384, 384), (0, 0, 0, 0))
        frame.paste((120, 120, 120, 255), (80, 80, 300, 340))
        frame.paste((120, 120, 120, 255), (378, 180, 384, 210))

        cleaned = prepare.keep_largest_alpha_component(frame)

        self.assertEqual(cleaned.getchannel("A").getpixel((381, 190)), 0)
        self.assertEqual(cleaned.getchannel("A").getpixel((150, 150)), 255)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

from water_input import (
    WATER_ACTION_RADIUS,
    WATER_DIALOG_HEIGHT,
    WATER_DIALOG_RADIUS,
    WATER_PRESET_RADIUS,
    WATER_PRESETS,
    parse_water_amount,
)


class WaterInputTests(unittest.TestCase):
    def test_presets_match_calibrated_amounts(self):
        self.assertEqual(
            WATER_PRESETS,
            (("一口", 50), ("一大口", 100), ("半杯", 150), ("一杯", 300)),
        )

    def test_presets_are_valid_manual_amounts(self):
        for _, amount in WATER_PRESETS:
            self.assertEqual(parse_water_amount(amount), amount)

    def test_accepts_a_typed_amount(self):
        self.assertEqual(parse_water_amount("50"), 50)
        self.assertEqual(parse_water_amount(" 350 "), 350)

    def test_rejects_empty_invalid_and_unreasonable_amounts(self):
        for value in ("", "abc", "12.5", "0", "-20", "5001"):
            with self.subTest(value=value):
                self.assertIsNone(parse_water_amount(value))

    def test_dialog_is_tall_enough_to_show_the_submit_button(self):
        self.assertGreaterEqual(WATER_DIALOG_HEIGHT, 420)

    def test_borderless_dialog_has_drag_handlers(self):
        source = (Path(__file__).resolve().parents[1] / "pet.py").read_text(encoding="utf-8")
        self.assertIn("def _drag_start(s,event):", source)
        self.assertIn("def _drag_move(s,event):", source)
        self.assertIn('widget.bind("<B1-Motion>",s._drag_move)', source)

    def test_dialog_uses_generous_rounded_corners(self):
        self.assertGreaterEqual(WATER_DIALOG_RADIUS, 22)
        self.assertGreaterEqual(WATER_PRESET_RADIUS, 12)
        self.assertGreaterEqual(WATER_ACTION_RADIUS, 14)


if __name__ == "__main__":
    unittest.main()

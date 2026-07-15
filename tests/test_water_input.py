import unittest

from water_input import WATER_DIALOG_HEIGHT, parse_water_amount


class WaterInputTests(unittest.TestCase):
    def test_accepts_a_typed_amount(self):
        self.assertEqual(parse_water_amount("50"), 50)
        self.assertEqual(parse_water_amount(" 350 "), 350)

    def test_rejects_empty_invalid_and_unreasonable_amounts(self):
        for value in ("", "abc", "12.5", "0", "-20", "5001"):
            with self.subTest(value=value):
                self.assertIsNone(parse_water_amount(value))

    def test_dialog_is_tall_enough_to_show_the_submit_button(self):
        self.assertGreaterEqual(WATER_DIALOG_HEIGHT, 340)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


PET_SOURCE = (Path(__file__).resolve().parents[1] / "pet.py").read_text(encoding="utf-8")


class ReportSemanticsTests(unittest.TestCase):
    def test_water_chart_keeps_its_goal(self):
        self.assertIn(
            'svg_bar(water_by_day, target=WATER_TARGET_ML, unit="ml")',
            PET_SOURCE,
        )

    def test_sitting_chart_has_no_fake_daily_goal(self):
        self.assertIn('svg_bar(sit_by_day, unit="分")', PET_SOURCE)
        self.assertNotIn('target=int(SIT_LIMIT_MIN*6)', PET_SOURCE)


if __name__ == "__main__":
    unittest.main()

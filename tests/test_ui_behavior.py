import unittest
from pathlib import Path

from ui_behavior import compact_status, detail_bubble_top, pointer_keeps_details_open, status_label_y, video_bubble_top


class UiBehaviorTests(unittest.TestCase):
    def test_compact_status_shows_only_the_useful_time(self):
        self.assertEqual(compact_status("seated", sit_seconds=45), "久坐 <1分钟")
        self.assertEqual(compact_status("seated", sit_seconds=32 * 60), "久坐 32分钟")
        self.assertEqual(compact_status("over", sit_seconds=92 * 60), "久坐 1小时32分")

    def test_compact_status_handles_lock_and_water_nudge(self):
        self.assertEqual(compact_status("away", locked=True), "已锁屏 · 离开")
        self.assertEqual(
            compact_status("seated", sit_seconds=32 * 60, water_nudge=True),
            "💧 喝水 · 久坐32分",
        )

    def test_details_open_from_cat_then_stay_open_over_panel(self):
        cat = (46, 260, 190, 404)
        panel = (13, 190, 223, 404)
        self.assertTrue(pointer_keeps_details_open(100, 330, cat, None))
        self.assertFalse(pointer_keeps_details_open(100, 210, cat, None))
        self.assertTrue(pointer_keeps_details_open(100, 210, cat, panel))
        self.assertFalse(pointer_keeps_details_open(5, 210, cat, panel))

    def test_sleep_status_moves_down_without_affecting_other_poses(self):
        self.assertEqual(status_label_y(404, 144, "idle"), 256)
        self.assertEqual(status_label_y(404, 144, "sleep"), 296)

    def test_seated_detail_bubble_moves_above_the_cat_ears(self):
        self.assertEqual(detail_bubble_top(328, 86, "seated"), 166)
        self.assertEqual(detail_bubble_top(328, 86, "away"), 190)

    def test_canvas_no_longer_draws_the_purple_context_hint(self):
        source = (Path(__file__).resolve().parents[1] / "pet.py").read_text(encoding="utf-8")
        self.assertNotIn('text="右键菜单"', source)

    def test_monitor_header_explains_the_low_cpu_preview(self):
        source = (Path(__file__).resolve().parents[1] / "pet.py").read_text(encoding="utf-8")
        self.assertNotIn('text="● LIVE"', source)
        self.assertIn('text="● 低频预览"', source)
        self.assertIn('text="省 CPU"', source)

    def test_open_video_bubble_settles_lower_without_changing_its_hidden_start(self):
        self.assertEqual(video_bubble_top(162, 0.0), 162)
        self.assertEqual(video_bubble_top(162, 0.5), 91)
        self.assertEqual(video_bubble_top(162, 1.0), 20)


if __name__ == "__main__":
    unittest.main()

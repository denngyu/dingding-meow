"""window_placement 的纯函数测试：不依赖真实显示器。"""
import unittest

from window_placement import needs_reposition, snap_target


class SnapTargetTests(unittest.TestCase):
    def test_bottom_right_with_default_margins(self):
        x, y = snap_target(1920, 1080, 236, 410)
        self.assertEqual(x, 1920 - 236 - 20)
        self.assertEqual(y, 1080 - 410 - 30)

    def test_custom_margins(self):
        x, y = snap_target(2560, 1440, 300, 500, margin_x=40, margin_y=60)
        self.assertEqual(x, 2560 - 300 - 40)
        self.assertEqual(y, 1440 - 500 - 60)


class NeedsRepositionTests(unittest.TestCase):
    def test_off_all_monitors(self):
        self.assertTrue(needs_reposition(3200, 1500, 236, 410, on_monitor_fn=lambda x, y: False))

    def test_still_on_monitor(self):
        self.assertFalse(needs_reposition(100, 200, 236, 410, on_monitor_fn=lambda x, y: True))

    def test_uses_window_center_not_top_left(self):
        calls = []

        def fake_check(x, y):
            calls.append((x, y))
            return True

        needs_reposition(100, 200, 236, 410, on_monitor_fn=fake_check)
        # 中心点 = (100 + 236//2, 200 + 410//2) = (218, 405)
        self.assertEqual(calls, [(218, 405)])

    def test_default_on_monitor_fn_does_not_crash(self):
        # 默认走 is_point_on_monitor；非 Windows / API 不可用时返回 True，
        # 因此 needs_reposition 返回 False；有 Windows 就按真实结果。至少不崩。
        result = needs_reposition(100, 100, 236, 410)
        self.assertIn(result, (True, False))


if __name__ == "__main__":
    unittest.main()

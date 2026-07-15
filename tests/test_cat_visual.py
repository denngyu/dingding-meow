import math
import unittest

from cat_visual import (
    TAIL_CYCLE_SEC,
    draw_cat,
    drink_prompt_delay_ms,
    ease_out_quart,
    sample_cat_pose,
    sample_drink_motion,
)


class RecordingCanvas:
    def __init__(self):
        self.calls = []

    def _record(self, kind, *args, **kwargs):
        self.calls.append((kind, args, kwargs))
        return len(self.calls)

    def create_arc(self, *args, **kwargs):
        return self._record("arc", *args, **kwargs)

    def create_line(self, *args, **kwargs):
        return self._record("line", *args, **kwargs)

    def create_oval(self, *args, **kwargs):
        return self._record("oval", *args, **kwargs)

    def create_polygon(self, *args, **kwargs):
        return self._record("polygon", *args, **kwargs)


class CatMotionTests(unittest.TestCase):
    def test_idle_tail_has_a_rest_and_loops_without_a_jump(self):
        start = sample_cat_pose(0.0, "seated")
        resting = sample_cat_pose(TAIL_CYCLE_SEC * 0.08, "seated")
        looped = sample_cat_pose(TAIL_CYCLE_SEC, "seated")

        self.assertAlmostEqual(start.tail_sway, 0.0, places=6)
        self.assertAlmostEqual(resting.tail_sway, 0.0, places=6)
        self.assertAlmostEqual(looped.tail_sway, start.tail_sway, places=6)

    def test_pose_changes_smoothly_at_render_rate(self):
        samples = [sample_cat_pose(i / 25.0, "seated") for i in range(150)]
        tail_steps = [abs(b.tail_sway - a.tail_sway) for a, b in zip(samples, samples[1:])]
        breath_steps = [abs(b.breath - a.breath) for a, b in zip(samples, samples[1:])]

        self.assertLess(max(tail_steps), 1.0)
        self.assertLess(max(breath_steps), 0.08)

    def test_overdue_motion_is_local_and_bounded(self):
        offsets = [sample_cat_pose(i / 100.0, "over").alert_offset for i in range(280)]

        self.assertTrue(any(abs(value) > 0.4 for value in offsets))
        self.assertLessEqual(max(abs(value) for value in offsets), 1.8)
        self.assertGreater(sum(abs(value) < 0.01 for value in offsets), 180)

    def test_drink_motion_starts_and_finishes_at_rest(self):
        start = sample_drink_motion(0.0)
        middle = sample_drink_motion(0.5)
        end = sample_drink_motion(1.0)

        self.assertEqual((start.lift, start.tilt), (0.0, 0.0))
        self.assertGreater(middle.lift, 0.95)
        self.assertGreater(middle.tilt, 30.0)
        self.assertEqual((end.lift, end.tilt), (0.0, 0.0))

    def test_drink_prompt_waits_for_the_animation(self):
        self.assertEqual(drink_prompt_delay_ms(2.4), 2400)
        self.assertEqual(drink_prompt_delay_ms(-1), 0)

    def test_panel_easing_is_fast_then_gentle(self):
        self.assertEqual(ease_out_quart(0.0), 0.0)
        self.assertEqual(ease_out_quart(1.0), 1.0)
        self.assertGreater(ease_out_quart(0.5), 0.8)
        values = [ease_out_quart(i / 20) for i in range(21)]
        self.assertTrue(all(a <= b for a, b in zip(values, values[1:])))


class CatDrawingTests(unittest.TestCase):
    def test_cat_draws_as_layered_vector_art_with_a_smooth_tail(self):
        canvas = RecordingCanvas()
        pose = sample_cat_pose(1.7, "seated")

        draw_cat(canvas, 118, 328, eyes_open=True, mood="seated", pose=pose)

        self.assertGreaterEqual(len(canvas.calls), 25)
        smooth_tail = [
            call for call in canvas.calls
            if call[0] == "line" and call[2].get("smooth") and call[2].get("width", 0) >= 8
        ]
        self.assertEqual(len(smooth_tail), 1)
        self.assertTrue(all(math.isfinite(value) for call in canvas.calls for value in call[1] if isinstance(value, (int, float))))


if __name__ == "__main__":
    unittest.main()

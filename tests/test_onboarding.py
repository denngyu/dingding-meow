import json
import tempfile
import unittest
from pathlib import Path

from onboarding import ONBOARDING_STEPS, ONBOARDING_VERSION, mark_onboarding_seen, should_show_onboarding


class OnboardingTests(unittest.TestCase):
    def test_tutorial_has_three_short_practical_steps(self):
        self.assertEqual(len(ONBOARDING_STEPS), 3)
        combined = " ".join(title + " " + body for title, body in ONBOARDING_STEPS)
        for phrase in (
            "鼠标",
            "右键",
            "本机",
            "日志",
            "CPU",
            "并非卡顿",
            "锁屏",
            "30 秒",
            "滚到中央",
            "关闭中央提醒",
        ):
            self.assertIn(phrase, combined)

    def test_first_launch_shows_once_and_preserves_existing_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps({"water_reminder_minutes": 20}), encoding="utf-8")
            self.assertTrue(should_show_onboarding(path))

            mark_onboarding_seen(path)

            self.assertFalse(should_show_onboarding(path))
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["onboarding_version"], ONBOARDING_VERSION)
            self.assertEqual(data["water_reminder_minutes"], 20)

    def test_older_tutorial_version_is_shown_again(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps({"onboarding_version": 0}), encoding="utf-8")
            self.assertTrue(should_show_onboarding(path))


if __name__ == "__main__":
    unittest.main()

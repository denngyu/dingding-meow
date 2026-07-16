import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
PET_SOURCE=(ROOT/"pet.py").read_text(encoding="utf-8")
SPRITE_SOURCE=(ROOT/"cat_sprites.py").read_text(encoding="utf-8")


class CenterNudgeIntegrationTests(unittest.TestCase):
    def test_runtime_exposes_default_on_toggle_and_knock_only_assets(self):
        self.assertIn("import center_nudge",PET_SOURCE)
        self.assertIn('"center_nudge_enabled":center_nudge.load_enabled(SETTINGS_PATH)',PET_SOURCE)
        self.assertIn("load_knock_frames",PET_SOURCE)
        self.assertIn("load_roll_frames",PET_SOURCE)
        self.assertNotIn("load_action_frames",PET_SOURCE)
        self.assertNotIn("build_daily_animation_frames",PET_SOURCE)
        self.assertNotIn("_wake_active",PET_SOURCE)
        self.assertNotIn('"walk"',SPRITE_SOURCE)

    def test_center_reminder_uses_horizontal_roll_motion(self):
        self.assertIn("_start_center_nudge",PET_SOURCE)
        self.assertNotIn("_draw_glass_pressure",PET_SOURCE)
        self.assertNotIn("glass_pressure",PET_SOURCE)
        self.assertIn("_draw_angry_steam",PET_SOURCE)
        self.assertIn("_set_center_nudge_window_position",PET_SOURCE)
        self.assertNotIn("sample.sprite==\"walk\"",PET_SOURCE)
        self.assertNotIn("无行走版直接出现在中央",PET_SOURCE)


if __name__ == "__main__":
    unittest.main()

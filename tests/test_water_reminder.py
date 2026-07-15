import json
import tempfile
import unittest
from pathlib import Path

from water_reminder import (
    DEFAULT_WATER_REMINDER_MIN,
    WATER_REMINDER_OPTIONS,
    load_water_reminder,
    reminder_due,
    save_water_reminder,
    validate_water_reminder,
)


class WaterReminderTests(unittest.TestCase):
    def test_default_is_thirty_minutes_and_twenty_is_available(self):
        self.assertEqual(DEFAULT_WATER_REMINDER_MIN, 30)
        self.assertEqual(WATER_REMINDER_OPTIONS[0], 20)
        self.assertIn(30, WATER_REMINDER_OPTIONS)

    def test_interval_validation_accepts_user_range(self):
        self.assertEqual(validate_water_reminder("20"), 20)
        self.assertEqual(validate_water_reminder(180), 180)
        for value in (None, "abc", 19, 181):
            self.assertIsNone(validate_water_reminder(value))

    def test_missing_or_invalid_settings_use_default(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            self.assertEqual(load_water_reminder(path), 30)
            path.write_text(json.dumps({"water_reminder_minutes": 5}), encoding="utf-8")
            self.assertEqual(load_water_reminder(path), 30)

    def test_selected_interval_is_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            save_water_reminder(path, 20)
            self.assertEqual(load_water_reminder(path), 20)

    def test_saving_interval_preserves_onboarding_state(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps({"onboarding_version": 1}), encoding="utf-8")
            save_water_reminder(path, 45)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["onboarding_version"], 1)
            self.assertEqual(data["water_reminder_minutes"], 45)

    def test_reminder_repeats_from_the_latest_drink_or_nudge(self):
        self.assertFalse(reminder_due(1799, 0, 0, 30, 0, 2000))
        self.assertTrue(reminder_due(1800, 0, 0, 30, 0, 2000))
        self.assertFalse(reminder_due(2000, 0, 1900, 30, 0, 2000))
        self.assertTrue(reminder_due(3700, 0, 1900, 30, 0, 2000))
        self.assertFalse(reminder_due(9999, 0, 0, 30, 2000, 2000))


if __name__ == "__main__":
    unittest.main()

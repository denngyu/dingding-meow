import json
import tempfile
import unittest
from pathlib import Path

import cat_visual
import center_nudge


class CenterNudgeSettingsTests(unittest.TestCase):
    def test_missing_setting_defaults_to_enabled(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(center_nudge.load_enabled(Path(folder) / "settings.json"))

    def test_saving_setting_preserves_other_features(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps({"water_reminder_min": 45}), encoding="utf-8")
            center_nudge.save_enabled(path, False)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(data[center_nudge.SETTINGS_KEY])
            self.assertEqual(data["water_reminder_min"], 45)


class CenterNudgeTriggerTests(unittest.TestCase):
    def test_starts_once_at_one_hour_and_defaults_on(self):
        self.assertFalse(center_nudge.should_start(3599, "over", True, False, False))
        self.assertTrue(center_nudge.should_start(3600, "over", True, False, False))
        self.assertFalse(center_nudge.should_start(3600, "over", False, False, False))
        self.assertFalse(center_nudge.should_start(3600, "over", True, True, False))

    def test_cancels_for_absence_lock_pause_or_disabled_setting(self):
        self.assertTrue(center_nudge.should_cancel("away", False, False, True))
        self.assertTrue(center_nudge.should_cancel("over", True, False, True))
        self.assertTrue(center_nudge.should_cancel("over", False, True, True))
        self.assertTrue(center_nudge.should_cancel("over", False, False, False))


class CenterNudgeTimelineTests(unittest.TestCase):
    def test_center_target_changes_only_x(self):
        self.assertEqual(
            center_nudge.cat_center_target(
                screen_width=1920,
                start_y=640,
                cat_local_x=118,
            ),
            (842,640),
        )

    def test_full_reminder_keeps_the_original_y_coordinate(self):
        start=(1600,640); target=(842,640)
        checkpoints=(
            0.0,
            center_nudge.ROLL_SEC*0.5,
            center_nudge.KNOCK_START+0.2,
            center_nudge.KNOCK_END+0.2,
            center_nudge.ROLL_BACK_START+center_nudge.ROLL_SEC*0.5,
            center_nudge.TOTAL_DURATION,
        )
        samples=[center_nudge.sample_trip(value,start,target) for value in checkpoints]

        self.assertTrue(all(sample.y==start[1] for sample in samples))
        self.assertEqual(samples[0].x,start[0])
        self.assertEqual(samples[-1].x,start[0])

    def test_rolls_slowly_to_center_and_back_with_angry_steam(self):
        start=(1600,640); target=(842,640)
        going=center_nudge.sample_trip(center_nudge.ROLL_SEC*0.5,start,target)
        returning=center_nudge.sample_trip(
            center_nudge.ROLL_BACK_START+center_nudge.ROLL_SEC*0.5,
            start,
            target,
        )

        self.assertEqual(center_nudge.ROLL_SEC,3.2)
        self.assertEqual(going.phase,"roll-in")
        self.assertEqual(returning.phase,"roll-back")
        self.assertEqual(going.sprite,"roll")
        self.assertEqual(returning.sprite,"roll")
        self.assertGreater(going.steam,0.8)
        self.assertGreater(returning.steam,0.8)
        self.assertNotEqual(going.rotation_degrees,0.0)
        self.assertNotEqual(returning.rotation_degrees,0.0)
        self.assertGreater(going.x,target[0])
        self.assertLess(going.x,start[0])
        self.assertGreater(returning.x,target[0])
        self.assertLess(returning.x,start[0])

    def test_steam_eases_in_without_a_hard_pop(self):
        levels=[
            center_nudge.sample_trip(
                progress*center_nudge.ROLL_SEC,
                (1000,600),
                (842,600),
            ).steam
            for progress in (0.0,0.02,0.05,0.10)
        ]
        self.assertEqual(levels[0],0.0)
        self.assertLess(levels[1],0.03)
        self.assertLess(levels[2],0.10)
        self.assertEqual(levels,sorted(levels))

    def test_roll_boundaries_are_upright_and_position_continuous(self):
        start=(1600,640); target=(842,640)
        arrived=center_nudge.sample_trip(center_nudge.KNOCK_START,start,target)
        leaving=center_nudge.sample_trip(center_nudge.ROLL_BACK_START,start,target)
        done=center_nudge.sample_trip(center_nudge.TOTAL_DURATION,start,target)

        self.assertEqual((arrived.x,arrived.y),target)
        self.assertEqual(arrived.phase,"knock")
        self.assertEqual(arrived.rotation_degrees,0.0)
        self.assertEqual((leaving.x,leaving.y),target)
        self.assertEqual(leaving.phase,"roll-back")
        self.assertEqual(leaving.rotation_degrees,0.0)
        self.assertEqual((done.x,done.y),start)
        self.assertEqual(done.rotation_degrees,0.0)
        self.assertTrue(done.done)

    def test_three_knocks_keep_the_paw_visible_at_contact(self):
        self.assertEqual(center_nudge.KNOCK_COUNT,3)
        for knock_index in range(center_nudge.KNOCK_COUNT):
            elapsed=center_nudge.KNOCK_START+(knock_index+0.5)*center_nudge.KNOCK_CYCLE_SEC
            sample=center_nudge.sample_trip(elapsed,(1000,600),(842,600))
            self.assertEqual(sample.phase,"knock")
            self.assertEqual(
                sample.frame_progress,
                center_nudge.KNOCK_CONTACT_PROGRESS,
            )

    def test_contact_window_stays_on_the_same_knock_frame(self):
        for cycle_progress in (0.32,0.45,0.58):
            elapsed=(
                center_nudge.KNOCK_START
                + cycle_progress * center_nudge.KNOCK_CYCLE_SEC
            )
            sample=center_nudge.sample_trip(elapsed,(1000,600),(842,600))
            self.assertEqual(
                sample.frame_progress,
                center_nudge.KNOCK_CONTACT_PROGRESS,
            )

    def test_last_knock_retracts_to_the_same_image_used_by_hold(self):
        before=center_nudge.sample_trip(
            center_nudge.KNOCK_END-0.001,
            (1000,600),
            (842,600),
        )
        after=center_nudge.sample_trip(
            center_nudge.KNOCK_END+0.001,
            (1000,600),
            (842,600),
        )
        self.assertEqual(before.sprite,"knock")
        self.assertEqual(after.sprite,"knock")
        self.assertEqual(before.frame_progress,1.0)
        self.assertEqual(after.frame_progress,0.0)
        before_index=cat_visual.action_frame_index(before.frame_progress,5,1.0)
        after_index=cat_visual.action_frame_index(after.frame_progress,5,1.0)
        self.assertEqual((before_index,after_index),(4,0))

    def test_full_timeline_has_exactly_three_knock_contacts(self):
        step=1.0/25.0
        elapsed=0.0
        previous=False
        rising_edges=0
        while elapsed<center_nudge.TOTAL_DURATION:
            sample=center_nudge.sample_trip(
                elapsed,
                (1000,600),
                (842,600),
            )
            touching=(
                sample.phase=="knock"
                and sample.frame_progress==center_nudge.KNOCK_CONTACT_PROGRESS
            )
            if touching and not previous:
                rising_edges+=1
            previous=touching
            elapsed+=step
        self.assertEqual(rising_edges,center_nudge.KNOCK_COUNT)


if __name__ == "__main__":
    unittest.main()

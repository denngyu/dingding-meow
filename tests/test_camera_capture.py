import unittest

import numpy as np

from camera_capture import (
    CAMERA_RETRY_SEC,
    CAMERA_WAKE_DELAY_SEC,
    CameraCapture,
    camera_needs_manual_restart,
    is_camera_signal_missing,
)


class FakeCapture:
    def __init__(self, opened=True, reads=None):
        self.opened = opened
        self.reads = list(reads or [])
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        return self.reads.pop(0) if self.reads else (False, None)

    def release(self):
        self.released = True


class FakeCV2:
    CAP_DSHOW = 700

    def __init__(self, captures):
        self.captures = list(captures)
        self.calls = []

    def VideoCapture(self, *args):
        self.calls.append(args)
        return self.captures.pop(0)


class CameraCaptureTests(unittest.TestCase):
    def test_digital_black_feed_is_distinguished_from_an_ordinary_dark_scene(self):
        digital_black = np.zeros((48, 64, 3), dtype=np.uint8)
        dark_scene = np.zeros((48, 64, 3), dtype=np.uint8)
        dark_scene[:, ::2] = 8

        self.assertTrue(is_camera_signal_missing(digital_black))
        self.assertFalse(is_camera_signal_missing(dark_scene))

    def test_camera_failure_requires_a_short_confirmation_before_manual_restart(self):
        self.assertFalse(camera_needs_manual_restart(read_failures=7))
        self.assertTrue(camera_needs_manual_restart(read_failures=8))
        self.assertFalse(camera_needs_manual_restart(no_signal_frames=2))
        self.assertTrue(camera_needs_manual_restart(no_signal_frames=3))

    def test_defaults_leave_time_for_windows_to_restore_the_device(self):
        self.assertGreaterEqual(CAMERA_WAKE_DELAY_SEC, 1.0)
        self.assertGreaterEqual(CAMERA_RETRY_SEC, 0.5)

    def test_failed_directshow_read_releases_and_falls_back_to_default_backend(self):
        failed = FakeCapture(reads=[(False, None)])
        fallback = FakeCapture(reads=[(True, "frame")])
        cv2 = FakeCV2([failed, fallback])
        camera = CameraCapture(cv2, retry_seconds=1.0)

        self.assertEqual(camera.read(0), (False, None))
        self.assertTrue(failed.released)
        self.assertEqual(camera.read(0.5), (False, None))
        self.assertEqual(camera.read(1.0), (True, "frame"))
        self.assertEqual(cv2.calls, [(0, cv2.CAP_DSHOW), (0,)])

    def test_lock_releases_handle_and_unlock_waits_before_reopening(self):
        first = FakeCapture(reads=[(True, "before")])
        after = FakeCapture(reads=[(True, "after")])
        cv2 = FakeCV2([first, after])
        camera = CameraCapture(cv2, wake_delay_seconds=1.5)

        self.assertEqual(camera.read(0), (True, "before"))
        camera.set_locked(True, 10)
        self.assertTrue(first.released)
        camera.set_locked(False, 20)
        self.assertEqual(camera.read(21.4), (False, None))
        self.assertEqual(camera.read(21.5), (True, "after"))
        self.assertEqual(cv2.calls[-1], (0, cv2.CAP_DSHOW))

    def test_unopened_device_is_retried_instead_of_becoming_permanently_dead(self):
        unavailable = FakeCapture(opened=False)
        recovered = FakeCapture(reads=[(True, "restored")])
        camera = CameraCapture(FakeCV2([unavailable, recovered]), retry_seconds=1)

        self.assertEqual(camera.read(0), (False, None))
        self.assertEqual(camera.read(1), (True, "restored"))


if __name__ == "__main__":
    unittest.main()

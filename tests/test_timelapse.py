import tempfile
import unittest
from pathlib import Path

import numpy as np

from timelapse import DEFAULT_TIMELAPSE_INTERVAL_SEC, TimelapseRecorder


class FakeWriter:
    def __init__(self, path, opened=True):
        self.path = Path(path)
        self.opened = opened
        self.frames = []
        if opened:
            self.path.write_bytes(b"mp4")

    def isOpened(self):
        return self.opened

    def write(self, frame):
        self.frames.append(frame.copy())

    def release(self):
        pass


class FakeCV2:
    FONT_HERSHEY_SIMPLEX = 0
    LINE_AA = 0

    def __init__(self):
        self.writer = None

    @staticmethod
    def VideoWriter_fourcc(*letters):
        return 1234

    def VideoWriter(self, path, fourcc, fps, size):
        self.writer = FakeWriter(path)
        return self.writer

    @staticmethod
    def resize(frame, size):
        return np.zeros((size[1], size[0], 3), dtype=np.uint8)

    @staticmethod
    def putText(frame, *args, **kwargs):
        return frame


class TimelapseTests(unittest.TestCase):
    def test_default_interval_is_one_minute(self):
        self.assertEqual(DEFAULT_TIMELAPSE_INTERVAL_SEC, 60)

    def test_capture_requires_manual_start_and_respects_interval(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder = TimelapseRecorder(FakeCV2(), folder, interval_seconds=60)
            frame = np.zeros((48, 64, 3), dtype=np.uint8)
            self.assertFalse(recorder.capture(frame, now=100, eligible=True))
            self.assertTrue(recorder.start(now=100))
            self.assertTrue(recorder.capture(frame, now=100, eligible=True))
            self.assertFalse(recorder.capture(frame, now=159, eligible=True))
            self.assertTrue(recorder.capture(frame, now=160, eligible=True))
            self.assertEqual(recorder.frame_count, 2)

    def test_locked_away_or_paused_frames_can_be_marked_ineligible(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder = TimelapseRecorder(FakeCV2(), folder)
            recorder.start(now=100)
            frame = np.zeros((48, 64, 3), dtype=np.uint8)
            self.assertFalse(recorder.capture(frame, now=100, eligible=False))
            self.assertEqual(recorder.frame_count, 0)

    def test_stop_moves_local_video_into_timelapse_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder = TimelapseRecorder(FakeCV2(), folder)
            recorder.start(now=100)
            recorder.capture(np.zeros((48, 64, 3), dtype=np.uint8), now=100)
            result = recorder.stop(now=220)
            self.assertIsNotNone(result)
            self.assertEqual(result.frame_count, 1)
            self.assertTrue(result.path.exists())
            self.assertEqual(result.path.parent, Path(folder))
            self.assertFalse(recorder.active)


if __name__ == "__main__":
    unittest.main()

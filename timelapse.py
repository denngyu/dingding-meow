"""纯本地延时摄影录制器：按间隔取帧，停止时保存为 MP4。"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import os
import shutil
import tempfile
import threading
import time


DEFAULT_TIMELAPSE_INTERVAL_SEC = 60
DEFAULT_TIMELAPSE_FPS = 10.0


@dataclass(frozen=True)
class TimelapseResult:
    path: Path
    frame_count: int
    started_at: float
    ended_at: float


class TimelapseRecorder:
    def __init__(
        self,
        cv2_module,
        output_dir,
        interval_seconds=DEFAULT_TIMELAPSE_INTERVAL_SEC,
        fps=DEFAULT_TIMELAPSE_FPS,
    ):
        self.cv2 = cv2_module
        self.output_dir = Path(output_dir)
        self.interval_seconds = max(1, int(interval_seconds))
        self.fps = max(1.0, float(fps))
        self._lock = threading.RLock()
        self._active = False
        self._writer = None
        self._temp_path = None
        self._frame_size = None
        self._frame_count = 0
        self._last_capture_ts = None
        self._started_at = None

    @property
    def active(self):
        with self._lock:
            return self._active

    @property
    def frame_count(self):
        with self._lock:
            return self._frame_count

    def start(self, now=None):
        with self._lock:
            if self._active:
                return False
            self._active = True
            self._writer = None
            self._temp_path = None
            self._frame_size = None
            self._frame_count = 0
            self._last_capture_ts = None
            self._started_at = float(time.time() if now is None else now)
            return True

    def _open_writer(self, frame):
        height, width = frame.shape[:2]
        stamp = datetime.fromtimestamp(self._started_at).strftime("%Y%m%d_%H%M%S")
        temp_name = "dingdingmeow_timelapse_%s_%d.mp4" % (stamp, os.getpid())
        self._temp_path = Path(tempfile.gettempdir()) / temp_name
        try:
            self._temp_path.unlink(missing_ok=True)
        except TypeError:
            if self._temp_path.exists():
                self._temp_path.unlink()
        fourcc = self.cv2.VideoWriter_fourcc(*"mp4v")
        writer = self.cv2.VideoWriter(
            str(self._temp_path),
            fourcc,
            self.fps,
            (width, height),
        )
        if not writer.isOpened():
            writer.release()
            self._temp_path = None
            raise RuntimeError("无法创建延时摄影视频文件")
        self._writer = writer
        self._frame_size = (width, height)

    def capture(self, frame, now=None, eligible=True):
        now = float(time.time() if now is None else now)
        with self._lock:
            if not self._active or not eligible or frame is None:
                return False
            if (
                self._last_capture_ts is not None
                and now - self._last_capture_ts < self.interval_seconds
            ):
                return False
            if self._writer is None:
                self._open_writer(frame)

            width, height = self._frame_size
            shot = frame.copy()
            if (shot.shape[1], shot.shape[0]) != self._frame_size:
                shot = self.cv2.resize(shot, (width, height))
            timestamp = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M")
            self.cv2.putText(
                shot,
                timestamp,
                (12, max(24, height - 14)),
                self.cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                self.cv2.LINE_AA,
            )
            self._writer.write(shot)
            self._last_capture_ts = now
            self._frame_count += 1
            return True

    def _target_path(self, ended_at):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        start_stamp = datetime.fromtimestamp(self._started_at).strftime("%Y%m%d_%H%M")
        end_stamp = datetime.fromtimestamp(ended_at).strftime("%H%M")
        candidate = self.output_dir / ("盯盯喵延时_%s-%s.mp4" % (start_stamp, end_stamp))
        suffix = 2
        while candidate.exists():
            candidate = self.output_dir / (
                "盯盯喵延时_%s-%s_%d.mp4" % (start_stamp, end_stamp, suffix)
            )
            suffix += 1
        return candidate

    def stop(self, now=None):
        ended_at = float(time.time() if now is None else now)
        with self._lock:
            if not self._active:
                return None
            self._active = False
            writer = self._writer
            self._writer = None
            if writer is not None:
                writer.release()

            result = None
            if (
                self._frame_count > 0
                and self._temp_path is not None
                and self._temp_path.exists()
            ):
                target = self._target_path(ended_at)
                shutil.move(str(self._temp_path), str(target))
                result = TimelapseResult(
                    path=target,
                    frame_count=self._frame_count,
                    started_at=self._started_at,
                    ended_at=ended_at,
                )
            elif self._temp_path is not None:
                try:
                    self._temp_path.unlink(missing_ok=True)
                except TypeError:
                    if self._temp_path.exists():
                        self._temp_path.unlink()

            self._temp_path = None
            self._frame_size = None
            self._last_capture_ts = None
            self._started_at = None
            return result

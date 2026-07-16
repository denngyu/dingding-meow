"""摄像头连接管理：休眠释放、唤醒延迟重连、后端自动回退。"""


CAMERA_RETRY_SEC = 1.0
CAMERA_WAKE_DELAY_SEC = 1.5


class CameraCapture:
    def __init__(
        self,
        cv2_module,
        index=0,
        retry_seconds=CAMERA_RETRY_SEC,
        wake_delay_seconds=CAMERA_WAKE_DELAY_SEC,
    ):
        self.cv2 = cv2_module
        self.index = int(index)
        self.retry_seconds = max(0.0, float(retry_seconds))
        self.wake_delay_seconds = max(0.0, float(wake_delay_seconds))
        self._capture = None
        self._backend_index = 0
        self._next_open_at = 0.0
        self._locked = False
        self._backends = self._backend_candidates()

    def _backend_candidates(self):
        candidates = []
        directshow = getattr(self.cv2, "CAP_DSHOW", None)
        if directshow is not None:
            candidates.append(directshow)
        candidates.append(None)
        unique = []
        for backend in candidates:
            if backend not in unique:
                unique.append(backend)
        return tuple(unique)

    @property
    def connected(self):
        return self._capture is not None

    @property
    def backend(self):
        return self._backends[self._backend_index]

    def _release(self):
        capture = self._capture
        self._capture = None
        if capture is not None:
            try:
                capture.release()
            except Exception:
                pass

    def close(self):
        self._release()

    def set_locked(self, locked, now):
        locked = bool(locked)
        now = float(now)
        if locked:
            if not self._locked:
                self._release()
            self._locked = True
            return
        if self._locked:
            self._locked = False
            self._backend_index = 0
            self._next_open_at = now + self.wake_delay_seconds

    def suspend(self, now, retry_delay=None):
        self._release()
        delay = self.retry_seconds if retry_delay is None else max(0.0, float(retry_delay))
        self._next_open_at = float(now) + delay

    def _open(self):
        backend = self.backend
        if backend is None:
            capture = self.cv2.VideoCapture(self.index)
        else:
            capture = self.cv2.VideoCapture(self.index, backend)
        try:
            opened = bool(capture is not None and capture.isOpened())
        except Exception:
            opened = False
        if not opened:
            try:
                capture.release()
            except Exception:
                pass
            return False
        self._capture = capture
        return True

    def _schedule_retry(self, now):
        self._release()
        self._backend_index = (self._backend_index + 1) % len(self._backends)
        self._next_open_at = float(now) + self.retry_seconds

    def read(self, now):
        now = float(now)
        if self._locked or now < self._next_open_at:
            return False, None
        if self._capture is None and not self._open():
            self._schedule_retry(now)
            return False, None
        try:
            ok, frame = self._capture.read()
        except Exception:
            ok, frame = False, None
        if not ok or frame is None:
            self._schedule_retry(now)
            return False, None
        return True, frame

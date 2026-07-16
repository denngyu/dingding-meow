"""不保存画面，验证真实摄像头能够释放并重新连接。"""

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2

from camera_capture import CameraCapture


def wait_for_frame(camera, seconds):
    deadline = time.time() + float(seconds)
    while time.time() < deadline:
        ok, frame = camera.read(time.time())
        if ok and frame is not None:
            return frame.shape
        time.sleep(0.25)
    return None


def main():
    camera = CameraCapture(cv2, index=0)
    try:
        before = wait_for_frame(camera, 8)
        print("initial:", before)
        if before is None:
            return 2

        now = time.time()
        camera.set_locked(True, now)
        time.sleep(0.25)
        camera.set_locked(False, time.time())
        after = wait_for_frame(camera, 10)
        print("reconnected:", after)
        return 0 if after is not None else 3
    finally:
        camera.close()


if __name__ == "__main__":
    raise SystemExit(main())

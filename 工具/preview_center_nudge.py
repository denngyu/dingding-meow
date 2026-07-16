"""启动真实 Pet 窗口预览中央叩屏；不启摄像头、不写业务日志。"""

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import pet


def preview_loop():
    session_start = time.time() - 3600
    deadline = time.monotonic() + 15.0
    while not pet.STATE.get("_quit") and time.monotonic() < deadline:
        pet.STATE.update(
            mode="over",
            sit=time.time() - session_start,
            away=0,
            sit_session_start=session_start,
            locked=False,
            paused=False,
            center_nudge_enabled=True,
        )
        time.sleep(0.1)
    pet.STATE["_quit"] = True


def main():
    pet.loop = preview_loop
    pet.start_tray = lambda pet_ref: None
    pet.should_show_onboarding = lambda path: False
    # 验收截图必须只含应用自身，禁止透明窗把真实桌面内容透进来。
    original_wm_attributes = pet.tk.Tk.wm_attributes
    def opaque_preview(window, *args):
        if args and args[0] == "-transparentcolor":
            return None
        return original_wm_attributes(window, *args)
    pet.tk.Tk.wm_attributes = opaque_preview
    pet.TRANS = pet.PAPER
    pet.Pet()


if __name__ == "__main__":
    main()

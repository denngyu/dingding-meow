"""预览高帧行走、稳定叩屏和悬停起身；不启摄像头、不写业务日志。"""

from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import center_nudge
import pet


def preview_loop():
    session_start = time.time() - center_nudge.TRIGGER_AFTER_SEC
    deadline = time.monotonic() + center_nudge.TOTAL_DURATION + 5.0
    while not pet.STATE.get("_quit") and time.monotonic() < deadline:
        wake_phase = pet.STATE.get("_preview_wake", False)
        pet.STATE.update(
            mode="seated" if wake_phase else "over",
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

    original_finish = pet.Pet._finish_center_nudge

    def finish_then_wake(window):
        original_finish(window)
        pet.STATE.update(mode="seated", _preview_wake=True)
        window._details_visible = True
        window._start_wake_animation()
        window.r.after(1800, lambda: pet.STATE.update(_quit=True))

    pet.Pet._finish_center_nudge = finish_then_wake

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

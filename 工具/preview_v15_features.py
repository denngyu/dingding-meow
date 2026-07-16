"""预览暖橘皮肤和圆润喝水框；不启摄像头、不写业务日志。"""

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pet


def preview_loop():
    deadline = time.monotonic() + 9.0
    while time.monotonic() < deadline and not pet.STATE.get("_quit"):
        pet.STATE.update(
            mode="seated",
            sit=28 * 60,
            away=0,
            locked=False,
            paused=False,
            frame=None,
        )
        time.sleep(0.1)
    pet.STATE["_quit"] = True


original_tick = pet.Pet.tick


def preview_tick(window):
    if not getattr(window, "_v15_preview_scheduled", False):
        window._v15_preview_scheduled = True
        window.r.after(350, lambda: window._set_skin("orange"))
        window.r.after(1300, lambda: window._request_water_dialog(immediate=True))
        window.r.after(7800, window._quit)
    original_tick(window)


pet.loop = preview_loop
pet.start_tray = lambda _pet: None
pet.should_show_onboarding = lambda _path: False
pet.skin_system.save_skin = lambda _settings, _root, skin_id: skin_id
pet.Pet.tick = preview_tick
pet.Pet()

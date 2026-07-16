"""Preview the orange open-eye pose across several blink cycles without camera access."""

from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pet


def preview_loop():
    deadline = time.monotonic() + 13.0
    while time.monotonic() < deadline and not pet.STATE.get("_quit"):
        pet.STATE.update(
            mode="seated",
            sit=12 * 60,
            away=0,
            locked=False,
            paused=False,
            frame=None,
        )
        time.sleep(0.1)
    pet.STATE["_quit"] = True


original_tick = pet.Pet.tick


def preview_tick(window):
    if not getattr(window, "_orange_preview_scheduled", False):
        window._orange_preview_scheduled = True
        window.r.after(300, lambda: window._set_skin("orange"))
        window.r.after(700, window.toggle_eyes)
        window.r.after(12000, window._quit)
    original_tick(window)


pet.loop = preview_loop
pet.start_tray = lambda _pet: None
pet.should_show_onboarding = lambda _path: False
pet.skin_system.save_skin = lambda _settings, _root, skin_id: skin_id
pet.Pet.tick = preview_tick
pet.Pet()
